"""Helpers for rendering packet summaries into transport-safe text."""

from __future__ import annotations

from .packet_schema import WorkerTaskPacket


def render_context_bundle_summary(packet: WorkerTaskPacket) -> str:
    """Render the ordered execution context bundle as a compact prompt-safe summary."""

    if not packet.context_bundle:
        return "(none)"
    ordered = sorted(packet.context_bundle, key=lambda item: (item.read_order, item.path))
    return "; ".join(
        f"{item.read_order}. {item.path} [{item.kind}]"
        for item in ordered
    )


def render_packet_summary(packet: WorkerTaskPacket) -> str:
    """Render a compact summary suitable for prompts or runtime metadata."""

    return (
        f"task_id: {packet.task_id}\n"
        f"objective: {packet.objective}\n"
        f"intent_outcome: {packet.intent.outcome}\n"
        f"write_scope: {', '.join(packet.scope.write_scope)}\n"
        f"intent_constraints: {', '.join(packet.intent.constraints)}\n"
        f"hard_rules: {', '.join(packet.hard_rules)}\n"
        f"context_bundle: {render_context_bundle_summary(packet)}\n"
        f"required_references: {', '.join(ref.path for ref in packet.required_references)}\n"
        f"validation_gates: {', '.join(packet.validation_gates)}"
    )
