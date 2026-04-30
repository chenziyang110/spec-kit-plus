"""Shared subagent-dispatch policy for orchestration-aware commands."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from .models import (
    BatchExecutionPolicy,
    CapabilitySnapshot,
    ExecutionDecision,
    ReviewGatePolicy,
    should_attempt_one_subagent,
)

_SAFE_SUBAGENT_LANE_COUNT_KEYS = (
    "safe_subagent_lanes",
    "subagent_lane_count",
    "ready_subagent_lanes",
)
_PACKET_READY_KEYS = (
    "packet_ready",
    "packets_ready",
    "has_validated_packet",
    "has_validated_packets",
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
    """Choose the dispatch shape using the shared subagents-first policy."""

    command = command_name.strip().lower()
    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_lanes = _get_shape_int(shape, _SAFE_SUBAGENT_LANE_COUNT_KEYS) or 0
    fallback_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
    has_overlapping_write_sets = _get_shape_flag(
        shape,
        _OVERLAPPING_WRITE_SET_KEYS,
        default=False,
    )

    if has_overlapping_write_sets:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            reason="unsafe-write-sets",
            fallback_from=fallback_shape,
            execution_surface="leader-inline",
        )

    if safe_lanes <= 0:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            reason="no-safe-delegated-lane",
            fallback_from="one-subagent" if should_attempt_one_subagent(command) else None,
            execution_surface="leader-inline",
        )

    packet_ready = _get_shape_flag(shape, _PACKET_READY_KEYS, default=False)
    if should_attempt_one_subagent(command) and not packet_ready:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            reason="packet-not-ready",
            fallback_from=fallback_shape,
            execution_surface="leader-inline",
        )

    low_confidence = (
        snapshot.native_subagents
        and snapshot.runtime_probe_succeeded
        and snapshot.delegation_confidence == "low"
    )
    if low_confidence:
        if command != "implement" and snapshot.managed_team_supported and safe_lanes > 1:
            return ExecutionDecision(
                command_name=command_name,
                dispatch_shape="parallel-subagents",
                reason="managed-team-supported",
                fallback_from="parallel-subagents",
                execution_surface="managed-team",
            )
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline-fallback",
            reason="low-delegation-confidence",
            fallback_from=fallback_shape,
            execution_surface="leader-inline",
        )

    if snapshot.native_subagents:
        dispatch_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape=dispatch_shape,
            reason="safe-parallel-subagents" if safe_lanes > 1 else "safe-one-subagent",
            execution_surface="native-subagents",
        )

    if command != "implement" and snapshot.managed_team_supported and safe_lanes > 1:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="parallel-subagents",
            reason="managed-team-supported",
            fallback_from="parallel-subagents",
            execution_surface="managed-team",
        )

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape="leader-inline-fallback",
        reason="runtime-no-subagents",
        fallback_from=fallback_shape,
        execution_surface="leader-inline",
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
