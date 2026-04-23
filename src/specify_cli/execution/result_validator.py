"""Validation helpers for delegated worker results."""

from __future__ import annotations

from .packet_schema import WorkerTaskPacket
from .packet_validator import PacketValidationError
from .result_schema import WorkerTaskResult


def validate_worker_task_result(
    result: WorkerTaskResult,
    packet: WorkerTaskPacket,
) -> WorkerTaskResult:
    """Return the result when it satisfies the packet's handoff contract."""

    if result.status == "pending":
        return result

    if packet.dispatch_policy.must_acknowledge_rules:
        if not result.rule_acknowledgement.required_references_read:
            raise PacketValidationError("DP3", "worker did not acknowledge required references")
        if not result.rule_acknowledgement.forbidden_drift_respected:
            raise PacketValidationError("DP3", "worker did not acknowledge forbidden drift")
    if result.status == "blocked":
        if not result.blockers:
            raise PacketValidationError("DP3", "blocked worker result is missing blocker evidence")
        if not result.failed_assumptions:
            raise PacketValidationError("DP3", "blocked worker result is missing failed assumptions")
        if not result.suggested_recovery_actions:
            raise PacketValidationError("DP3", "blocked worker result is missing recovery guidance")
        return result
    if packet.validation_gates and not result.validation_results:
        raise PacketValidationError("DP3", "worker result is missing validation evidence")
    return result
