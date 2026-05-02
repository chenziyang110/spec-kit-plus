"""Shared types for first-party workflow quality hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


HookStatus = Literal["ok", "warn", "blocked", "repaired", "repairable-block"]
HookSeverity = Literal["info", "warning", "critical"]


@dataclass(slots=True)
class HookResult:
    """Normalized result returned by every quality hook."""

    event: str
    status: HookStatus
    severity: HookSeverity
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    writes: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "status": self.status,
            "severity": self.severity,
            "actions": list(self.actions),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "writes": dict(self.writes),
            "data": dict(self.data),
        }


class QualityHookError(ValueError):
    """Raised when a hook event or payload is invalid."""
