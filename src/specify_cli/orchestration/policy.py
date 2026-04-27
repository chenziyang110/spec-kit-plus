"""Shared execution-strategy policy for orchestration-aware commands."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from .models import (
    BatchExecutionPolicy,
    CapabilitySnapshot,
    ExecutionDecision,
    ReviewGatePolicy,
    single_worker_delegation_default,
)

_PARALLEL_BATCH_COUNT_KEYS = (
    "parallel_batches",
    "ready_parallel_batches",
    "parallel_batch_count",
)
_SAFE_PARALLEL_BATCH_KEYS = (
    "safe_parallel_batch",
    "has_safe_parallel_batch",
    "ready_parallel_batch",
    "has_ready_parallel_batch",
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


def choose_execution_strategy(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> ExecutionDecision:
    """Choose the execution strategy using the shared first-release policy."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    single_worker_delegates = single_worker_delegation_default(command_name)
    single_worker_strategy = "single-lane"
    parallel_batches = _get_shape_int(shape, _PARALLEL_BATCH_COUNT_KEYS)
    if parallel_batches is None:
        # Backward compatibility: derive batch count from older boolean surfaces.
        has_safe_parallel_batch = _get_shape_flag(
            shape,
            _SAFE_PARALLEL_BATCH_KEYS,
            default=False,
        )
        parallel_batches = 1 if has_safe_parallel_batch else 0

    has_overlapping_write_sets = _get_shape_flag(
        shape,
        _OVERLAPPING_WRITE_SET_KEYS,
        default=False,
    )

    if parallel_batches <= 0 or has_overlapping_write_sets:
        if single_worker_delegates:
            if (
                snapshot.native_multi_agent
                and not (
                    snapshot.runtime_probe_succeeded
                    and snapshot.delegation_confidence == "low"
                )
            ):
                return ExecutionDecision(
                    command_name=command_name,
                    strategy=single_worker_strategy,
                    reason="no-safe-batch",
                    lane_topology="single-lane",
                    execution_surface="native-delegation",
                )
            if snapshot.sidecar_runtime_supported:
                return ExecutionDecision(
                    command_name=command_name,
                    strategy="sidecar-runtime",
                    reason="no-safe-batch",
                    lane_topology="single-lane",
                    execution_surface="sidecar-runtime",
                )
        return ExecutionDecision(
            command_name=command_name,
            strategy=single_worker_strategy,
            reason="no-safe-batch",
            lane_topology="single-lane",
            execution_surface="leader-local",
        )

    if (
        snapshot.native_multi_agent
        and snapshot.runtime_probe_succeeded
        and snapshot.delegation_confidence == "low"
    ):
        if snapshot.sidecar_runtime_supported:
            return ExecutionDecision(
                command_name=command_name,
                strategy="sidecar-runtime",
                reason="native-low-confidence",
                lane_topology="multi-lane",
                execution_surface="sidecar-runtime",
            )
        return ExecutionDecision(
            command_name=command_name,
            strategy=single_worker_strategy,
            reason="fallback-low-confidence",
            lane_topology="single-lane",
            execution_surface="leader-local",
        )

    if snapshot.native_multi_agent:
        return ExecutionDecision(
            command_name=command_name,
            strategy="native-multi-agent",
            reason="native-supported",
            lane_topology="multi-lane",
            execution_surface="native-delegation",
        )

    if snapshot.sidecar_runtime_supported:
        return ExecutionDecision(
            command_name=command_name,
            strategy="sidecar-runtime",
            reason="native-missing",
            lane_topology="multi-lane",
            execution_surface="sidecar-runtime",
        )

    return ExecutionDecision(
        command_name=command_name,
        strategy=single_worker_strategy,
        reason="fallback",
        lane_topology="single-lane",
        execution_surface="leader-local",
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
