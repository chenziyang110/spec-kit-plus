"""Shared subagent-dispatch policy for orchestration-aware commands."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from .models import (
    BatchExecutionPolicy,
    CapabilitySnapshot,
    ExecutionDecision,
    ReviewGatePolicy,
)

_SAFE_SUBAGENT_LANE_COUNT_KEYS = (
    "safe_subagent_lanes",
    "subagent_lane_count",
    "ready_subagent_lanes",
)
_OVERLAPPING_WRITE_SET_KEYS = (
    "overlapping_write_sets",
    "has_overlapping_write_sets",
    "write_sets_overlap",
)
_HIGH_RISK_REVIEW_KEY_GROUPS = (
    (("touches_shared_surface", "touches_shared_registration"), "shared_surface"),
    (("touches_schema", "touches_migration"), "schema_change"),
    (
        ("touches_protocol_boundary", "touches_native_bridge", "touches_generated_api"),
        "boundary_contract",
    ),
)


def _to_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Collection) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _to_int(value: object, *, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _get_shape_flag(
    workload_shape: Mapping[str, object],
    keys: tuple[str, ...],
    *,
    default: bool,
) -> bool:
    for key in keys:
        if key in workload_shape:
            return _to_bool(workload_shape[key], default=default)
    return default


def _get_shape_int(
    workload_shape: Mapping[str, object],
    keys: tuple[str, ...],
) -> int | None:
    for key in keys:
        if key in workload_shape:
            return _to_int(workload_shape[key], default=None)
    return None


def choose_subagent_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> ExecutionDecision:
    """Choose the mandatory subagent dispatch shape for ordinary sp-* commands."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_lanes = _get_shape_int(shape, _SAFE_SUBAGENT_LANE_COUNT_KEYS) or 0
    dispatch_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
    reason = "mandatory-parallel-subagents" if safe_lanes > 1 else "mandatory-one-subagent"

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape=dispatch_shape,
        reason=reason,
        execution_surface="native-subagents",
    )


def classify_batch_execution_policy(
    *,
    workload_shape: dict[str, object],
) -> BatchExecutionPolicy:
    """Classify how a batch should converge and whether safe preparation is allowed."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_preparation = _get_shape_flag(shape, ("safe_preparation",), default=False)
    preparation_scope = str(shape.get("preparation_scope", "")).strip().lower()
    overlapping = _get_shape_flag(shape, _OVERLAPPING_WRITE_SET_KEYS, default=False)

    if safe_preparation and not overlapping and preparation_scope in {
        "analysis",
        "scaffolding",
        "docs",
        "documentation",
        "config",
        "configuration",
    }:
        return BatchExecutionPolicy(
            batch_classification="mixed_tolerance",
            safe_preparation_allowed=True,
            reason="low_risk_preparation",
        )

    return BatchExecutionPolicy(
        batch_classification="strict",
        safe_preparation_allowed=False,
        reason="full_success_required",
    )


def classify_review_gate_policy(
    *,
    workload_shape: dict[str, object],
) -> ReviewGatePolicy:
    """Classify whether a batch needs a mandatory review checkpoint."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    reasons: list[str] = []

    for keys, reason in _HIGH_RISK_REVIEW_KEY_GROUPS:
        if _get_shape_flag(shape, keys, default=False):
            reasons.append(reason)

    if not reasons:
        return ReviewGatePolicy(
            requires_review_gate=False,
            peer_review_lane_recommended=False,
            reason="low_risk_batch",
        )

    peer_review_lane_recommended = _get_shape_flag(
        shape,
        ("can_peer_review", "review_lane_available", "independent_read_only_review"),
        default=False,
    )
    return ReviewGatePolicy(
        requires_review_gate=True,
        peer_review_lane_recommended=peer_review_lane_recommended,
        reason="+".join(reasons),
    )
