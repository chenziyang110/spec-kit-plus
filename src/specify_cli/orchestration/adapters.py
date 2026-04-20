"""Adapter protocol for per-integration multi-agent capability detection."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import CapabilitySnapshot

FIRST_RELEASE_WORKFLOW_COMMANDS = frozenset(
    {
        "specify",
        "spec-extend",
        "explain",
        "debug",
        "plan",
        "tasks",
        "implement",
        "analyze",
        "constitution",
        "checklist",
        "map-codebase",
        "taskstoissues",
    }
)


def normalize_command_name(command_name: str) -> str:
    """Normalize workflow command names for adapter support checks."""
    normalized = command_name.strip().lower()
    while normalized.startswith("/"):
        normalized = normalized[1:]
    if normalized.startswith("sp-"):
        normalized = normalized[3:]
    elif normalized.startswith("sp."):
        normalized = normalized[3:]
    return normalized


def supports_workflow_command(
    command_name: str,
    supported_commands: frozenset[str] = FIRST_RELEASE_WORKFLOW_COMMANDS,
) -> bool:
    """Return ``True`` when a normalized command is in the allowed set."""
    return normalize_command_name(command_name) in supported_commands


@runtime_checkable
class MultiAgentAdapter(Protocol):
    """Contract implemented by integration-specific multi-agent adapters."""

    def detect_capabilities(self) -> CapabilitySnapshot:
        """Return the current capability snapshot for this integration."""

    def supports_command(self, command_name: str) -> bool:
        """Return ``True`` when the command is supported by the adapter."""
