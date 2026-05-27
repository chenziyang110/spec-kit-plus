"""Validation helpers for worker task packets."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .packet_schema import WorkerTaskPacket


MP_ID_RE = re.compile(r"^MP-\d{3}$")
SURFACE_LIMIT_ANTI_GOAL_RE = re.compile(
    r"\b(do not|don't|must not)\b.*\b(add|introduce|modify|change|expand)\b.*\b(public\s+)?(command|commands|api|apis|route|routes|surface|surfaces|lifecycle)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class PacketValidationError(ValueError):
    code: str
    message: str

    def __post_init__(self) -> None:
        ValueError.__init__(self, self.message)


def validate_worker_task_packet(packet: WorkerTaskPacket) -> WorkerTaskPacket:
    """Return the packet when its hard-fail execution contract is complete."""

    if not packet.intent.outcome or not packet.intent.constraints or not packet.intent.success_signals:
        raise PacketValidationError("DP1", "execution intent contract must be present in the packet")
    if not packet.scope.write_scope:
        raise PacketValidationError("DP1", "write_scope is required for delegated execution")
    if not packet.context_bundle:
        raise PacketValidationError("DP2", "context_bundle must be compiled into the packet")
    if not packet.required_references:
        raise PacketValidationError("DP2", "required_references must be compiled into the packet")
    if not packet.hard_rules:
        raise PacketValidationError("DP1", "hard_rules must be present in the packet")
    if not packet.validation_gates:
        raise PacketValidationError("DP1", "validation_gates must be present in the packet")
    if not packet.done_criteria:
        raise PacketValidationError("DP1", "done_criteria must be present in the packet")
    if not packet.handoff_requirements:
        raise PacketValidationError("DP1", "handoff_requirements must be present in the packet")
    if not packet.platform_guardrails:
        raise PacketValidationError("DP2", "platform_guardrails must be compiled into the packet")
    if any(SURFACE_LIMIT_ANTI_GOAL_RE.search(goal) for goal in packet.anti_goals):
        if not packet.does_not_remove:
            raise PacketValidationError(
                "DP1",
                "surface-limiting anti-goals require a does-not-remove guard",
            )
    for obligation in packet.must_preserve_obligations:
        if not MP_ID_RE.match(obligation.id):
            raise PacketValidationError("DP1", "must-preserve obligation id must use MP-### format")
        if (
            not obligation.type
            or not obligation.claim
            or not obligation.source
            or not obligation.downstream_requirement
        ):
            raise PacketValidationError("DP1", "must-preserve obligation is missing required fields")
    for obligation in packet.consequence_obligations:
        if not obligation.obligation_id.strip():
            raise PacketValidationError("DP2", "consequence obligation is missing obligation_id")
        if not obligation.claim.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing claim",
            )
        if not obligation.affected_objects:
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing affected_objects",
            )
        if not obligation.stop_and_reopen_condition.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing stop_and_reopen_condition",
            )
    return packet
