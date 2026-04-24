"""Validation helpers for worker task packets."""

from __future__ import annotations

from dataclasses import dataclass

from .packet_schema import WorkerTaskPacket


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
    if not packet.required_references:
        raise PacketValidationError("DP2", "required_references must be compiled into the packet")
    if not packet.hard_rules:
        raise PacketValidationError("DP1", "hard_rules must be present in the packet")
    if not packet.validation_gates:
        raise PacketValidationError("DP1", "validation_gates must be present in the packet")
    if not packet.done_criteria:
        raise PacketValidationError("DP1", "done_criteria must be present in the packet")
    return packet
