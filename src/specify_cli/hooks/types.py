"""Shared types for first-party workflow quality hooks."""

from __future__ import annotations

import re
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
    blockers: list[dict[str, Any]] = field(default_factory=list)

    def _fallback_blocker(self) -> dict[str, Any]:
        evidence = [*self.errors, *self.warnings]
        if not evidence:
            evidence = [f"{self.event} returned status {self.status}"]
        summary = self.errors[0] if self.errors else (
            self.actions[0] if self.actions else evidence[0]
        )
        next_action = self.actions[0] if self.actions else (
            "Inspect the reported evidence, repair the owning state or artifact "
            "within the active workflow boundary, then rerun this hook."
        )
        blocker_id = re.sub(r"[^a-z0-9]+", "-", self.event.lower()).strip("-")
        return {
            "version": 1,
            "blocker_id": blocker_id or "workflow-hook-blocker",
            "workflow": "shared-hook-runtime",
            "stage": self.event,
            "category": "workflow-validation",
            "owner": "agent",
            "summary": summary,
            "details": "The shared workflow hook denied safe continuation at this event.",
            "evidence": evidence,
            "attempted_recovery": [],
            "exact_next_action": next_action,
            "approval_question": None,
            "unblock_criteria": (
                f"Rerunning {self.event} returns ok, warn, or repaired instead of "
                f"{self.status}."
            ),
            "affected_scope": [self.event],
            "can_continue": False,
            "human_action_required": False,
            "human_action_guide": None,
            "resume": {
                "instruction": f"Rerun the workflow action guarded by {self.event}.",
                "command": None,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "event": self.event,
            "status": self.status,
            "severity": self.severity,
            "actions": list(self.actions),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "writes": dict(self.writes),
            "data": dict(self.data),
        }
        if self.blockers or self.status in {"blocked", "repairable-block"}:
            payload["blockers"] = [
                dict(blocker) for blocker in (self.blockers or [self._fallback_blocker()])
            ]
        return payload


class QualityHookError(ValueError):
    """Raised when a hook event or payload is invalid."""
