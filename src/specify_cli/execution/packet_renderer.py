"""Helpers for rendering packet summaries into transport-safe text."""

from __future__ import annotations

from .packet_schema import WorkerTaskPacket


def render_packet_summary(packet: WorkerTaskPacket) -> str:
    """Render a compact summary suitable for prompts or runtime metadata."""

    return (
        f"task_id: {packet.task_id}\n"
        f"objective: {packet.objective}\n"
        f"write_scope: {', '.join(packet.scope.write_scope)}\n"
        f"required_references: {', '.join(ref.path for ref in packet.required_references)}\n"
        f"validation_gates: {', '.join(packet.validation_gates)}"
    )
