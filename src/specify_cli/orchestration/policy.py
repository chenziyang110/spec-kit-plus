"""Shared subagent-dispatch policy for orchestration-aware commands."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from .models import (
    BatchExecutionPolicy,
    CapabilitySnapshot,
    EvidenceLaneDecision,
    ExecutionDecision,
    ReviewGatePolicy,
)

_SAFE_SUBAGENT_LANE_COUNT_KEYS = (
    "safe_subagent_lanes",
    "subagent_lane_count",
    "ready_subagent_lanes",
)
_SAFE_EVIDENCE_LANE_COUNT_KEYS = (
    "safe_evidence_lanes",
    "read_only_evidence_lanes",
    "evidence_lane_count",
    "ready_evidence_lanes",
)
_EVIDENCE_CONTRACT_READY_KEYS = (
    "evidence_contract_ready",
    "evidence_packet_ready",
    "query_packet_ready",
    "packet_ready",
)
_EVIDENCE_REQUIRED_KEYS = (
    "evidence_lane_required",
    "read_only_evidence_required",
    "delegation_required",
)
_OVERLAPPING_WRITE_SET_KEYS = (
    "overlapping_write_sets",
    "has_overlapping_write_sets",
    "write_sets_overlap",
)
_ADAPTIVE_COMMANDS = {"plan", "tasks"}
_HIGH_RISK_KEYS = (
    "high_risk",
    "touches_schema_or_migration",
    "touches_schema",
    "touches_migration",
    "touches_security_sensitive_surface",
    "touches_protocol_or_generated_api",
    "touches_protocol_boundary",
    "touches_generated_api",
    "touches_native_or_plugin_bridge",
    "touches_native_bridge",
    "touches_plugin_bridge",
    "touches_shared_registration_surface",
    "touches_shared_surface",
    "touches_shared_registration",
    "cross_project_target",
    "reference_fidelity_required",
    "deep_research_handoff_required",
    "consequence_obligations_require_independent_synthesis",
)
_HIGH_RISK_REVIEW_KEY_GROUPS = (
    (("high_risk",), "general_high_risk"),
    (
        (
            "touches_shared_registration_surface",
            "touches_shared_surface",
            "touches_shared_registration",
        ),
        "shared_surface",
    ),
    (("touches_schema_or_migration", "touches_schema", "touches_migration"), "schema_change"),
    (("cross_project_target",), "cross_project"),
    (("reference_fidelity_required",), "reference_fidelity"),
    (("deep_research_handoff_required",), "deep_research_handoff"),
    (
        ("consequence_obligations_require_independent_synthesis",),
        "independent_synthesis_required",
    ),
    (
        (
            "touches_protocol_or_generated_api",
            "touches_protocol_boundary",
            "touches_generated_api",
            "touches_native_or_plugin_bridge",
            "touches_native_bridge",
            "touches_plugin_bridge",
        ),
        "boundary_contract",
    ),
    (("touches_security_sensitive_surface",), "security_sensitive"),
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


def _any_shape_flag(workload_shape: Mapping[str, object], keys: tuple[str, ...]) -> bool:
    return any(_to_bool(workload_shape[key], default=False) for key in keys if key in workload_shape)


def _get_shape_int(
    workload_shape: Mapping[str, object],
    keys: tuple[str, ...],
) -> int | None:
    for key in keys:
        if key in workload_shape:
            return _to_int(workload_shape[key], default=None)
    return None


def _command_is_adaptive(command_name: str) -> bool:
    return command_name.strip().lower() in _ADAPTIVE_COMMANDS


def _command_work_label(command_name: str) -> str:
    command = command_name.strip().lower()
    if command == "tasks":
        return "task generation"
    return "plan work"


def _has_high_risk_trigger(shape: Mapping[str, object]) -> bool:
    return _any_shape_flag(shape, _HIGH_RISK_KEYS)


def _packet_ready(shape: Mapping[str, object]) -> bool:
    return _get_shape_flag(shape, ("packet_ready", "delegation_packet_ready"), default=False)


def _native_subagents_available(snapshot: CapabilitySnapshot, shape: Mapping[str, object]) -> bool:
    if "native_subagents_available" in shape:
        return _to_bool(shape["native_subagents_available"], default=snapshot.native_subagents)
    return snapshot.native_subagents


def _derive_lightweight_safe(shape: Mapping[str, object], safe_lanes: int) -> bool:
    if "lightweight_safe" in shape:
        return _to_bool(shape["lightweight_safe"], default=False)
    return safe_lanes <= 1 and not _has_high_risk_trigger(shape)


def _adaptive_mode(shape: Mapping[str, object], safe_lanes: int) -> str:
    if _has_high_risk_trigger(shape):
        return "heavy"
    if _derive_lightweight_safe(shape, safe_lanes):
        return "light"
    return "standard"


def _choose_mandatory_subagent_dispatch(
    *,
    command_name: str,
    safe_lanes: int,
) -> ExecutionDecision:
    dispatch_shape = "parallel-subagents" if safe_lanes > 1 else "one-subagent"
    reason = "mandatory-parallel-subagents" if safe_lanes > 1 else "mandatory-one-subagent"

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape=dispatch_shape,
        reason=reason,
        execution_surface="native-subagents",
    )


def _choose_adaptive_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    shape: Mapping[str, object],
    safe_lanes: int,
) -> ExecutionDecision:
    mode = _adaptive_mode(shape, safe_lanes)
    native_available = _native_subagents_available(snapshot, shape)
    packet_ready = _packet_ready(shape)
    work_label = _command_work_label(command_name)

    if mode == "light":
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="leader-inline",
            reason="adaptive-light-leader-inline",
            execution_model="adaptive",
            execution_mode="light",
        )

    if mode == "standard":
        if not native_available:
            return ExecutionDecision(
                command_name=command_name,
                dispatch_shape="leader-inline",
                reason="adaptive-standard-native-unavailable-leader-inline",
                execution_model="adaptive",
                execution_mode="standard",
                capability_degraded=True,
            )
        if safe_lanes < 1 or not packet_ready:
            return ExecutionDecision(
                command_name=command_name,
                dispatch_shape="subagent-blocked",
                reason="adaptive-standard-subagent-blocked",
                execution_model="adaptive",
                execution_mode="standard",
                workflow_status="blocked",
                blocked_reason=f"standard adaptive {work_label} cannot be packetized safely",
            )
        if safe_lanes > 1:
            return ExecutionDecision(
                command_name=command_name,
                dispatch_shape="parallel-subagents",
                reason="adaptive-standard-parallel-subagents",
                execution_model="adaptive",
                execution_mode="standard",
            )
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="one-subagent",
            reason="adaptive-standard-one-subagent",
            execution_model="adaptive",
            execution_mode="standard",
        )

    if not native_available:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="subagent-blocked",
            reason="adaptive-heavy-subagent-blocked",
            execution_model="adaptive",
            execution_mode="heavy",
            workflow_status="blocked",
            blocked_reason=f"heavy or safety-critical {work_label} requires native subagents",
        )

    if safe_lanes < 1 or not packet_ready:
        return ExecutionDecision(
            command_name=command_name,
            dispatch_shape="subagent-blocked",
            reason="adaptive-heavy-subagent-blocked",
            execution_model="adaptive",
            execution_mode="heavy",
            workflow_status="blocked",
            blocked_reason=f"heavy or safety-critical {work_label} cannot be packetized safely",
        )

    return ExecutionDecision(
        command_name=command_name,
        dispatch_shape="parallel-subagents" if safe_lanes > 1 else "one-subagent",
        reason="adaptive-heavy-parallel-subagents" if safe_lanes > 1 else "adaptive-heavy-one-subagent",
        execution_model="adaptive",
        execution_mode="heavy",
    )


def choose_subagent_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> ExecutionDecision:
    """Choose the dispatch shape for orchestration-aware sp-* commands."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_lanes = _get_shape_int(shape, _SAFE_SUBAGENT_LANE_COUNT_KEYS) or 0

    if _command_is_adaptive(command_name):
        return _choose_adaptive_dispatch(
            command_name=command_name,
            snapshot=snapshot,
            shape=shape,
            safe_lanes=safe_lanes,
        )

    return _choose_mandatory_subagent_dispatch(
        command_name=command_name,
        safe_lanes=safe_lanes,
    )


def choose_evidence_lane_dispatch(
    *,
    command_name: str,
    snapshot: CapabilitySnapshot,
    workload_shape: dict[str, object],
) -> EvidenceLaneDecision:
    """Choose optional read-only evidence-lane dispatch for Q&A and discussion workflows."""

    shape = workload_shape if isinstance(workload_shape, Mapping) else {}
    safe_lanes = _get_shape_int(shape, _SAFE_EVIDENCE_LANE_COUNT_KEYS) or 0
    contract_ready = _get_shape_flag(shape, _EVIDENCE_CONTRACT_READY_KEYS, default=False)
    required = _any_shape_flag(shape, _EVIDENCE_REQUIRED_KEYS)
    leader_inline_allowed = _get_shape_flag(shape, ("leader_inline_allowed",), default=True)
    native_available = _native_subagents_available(snapshot, shape)

    def _leader_inline(reason: str, *, capability_degraded: bool = False) -> EvidenceLaneDecision:
        return EvidenceLaneDecision(
            command_name=command_name,
            dispatch_shape="leader-inline",
            reason=reason,
            execution_surface="leader-inline",
            capability_degraded=capability_degraded,
        )

    def _blocked(reason: str) -> EvidenceLaneDecision:
        return EvidenceLaneDecision(
            command_name=command_name,
            dispatch_shape="subagent-blocked",
            reason="read-only-evidence-subagent-blocked",
            execution_surface="none",
            workflow_status="blocked",
            blocked_reason=reason,
        )

    if safe_lanes < 1:
        if required or not leader_inline_allowed:
            return _blocked("no safe read-only evidence lane is available")
        return _leader_inline("read-only-evidence-leader-inline-no-safe-lane")

    if not contract_ready:
        if required or not leader_inline_allowed:
            return _blocked("read-only evidence lane contract is not ready")
        return _leader_inline("read-only-evidence-leader-inline-contract-missing")

    if not native_available:
        if required or not leader_inline_allowed:
            return _blocked("read-only evidence lanes require native subagents")
        return _leader_inline(
            "read-only-evidence-native-unavailable-leader-inline",
            capability_degraded=True,
        )

    if safe_lanes > 1:
        return EvidenceLaneDecision(
            command_name=command_name,
            dispatch_shape="parallel-subagents",
            reason="read-only-evidence-parallel-subagents",
            execution_surface="native-subagents",
        )

    return EvidenceLaneDecision(
        command_name=command_name,
        dispatch_shape="one-subagent",
        reason="read-only-evidence-one-subagent",
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
        if _any_shape_flag(shape, keys):
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
