"""Shared types for first-party workflow quality hooks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from ..launcher import render_command


HookStatus = Literal["ok", "warn", "blocked", "repaired", "repairable-block"]
HookSeverity = Literal["info", "warning", "critical"]

_HOOK_COMMAND_IDS = {
    "workflow.preflight": "hook.preflight",
    "workflow.state.validate": "hook.validate-state",
    "workflow.artifacts.validate": "hook.validate-artifacts",
    "workflow.checkpoint": "hook.checkpoint",
    "workflow.context.monitor": "hook.monitor-context",
    "workflow.session_state.validate": "hook.validate-session-state",
    "workflow.statusline.render": "hook.render-statusline",
    "workflow.read_guard.validate": "hook.validate-read-path",
    "workflow.prompt_guard.validate": "hook.validate-prompt",
    "workflow.boundary.validate": "hook.validate-boundary",
    "workflow.phase_boundary.validate": "hook.validate-phase-boundary",
    "workflow.commit.validate": "hook.validate-commit",
    "workflow.policy.evaluate": "hook.workflow-policy",
    "workflow.compaction.build": "hook.build-compaction",
    "workflow.compaction.read": "hook.read-compaction",
    "workflow.learning.signal": "hook.signal-learning",
    "workflow.learning.review": "hook.review-learning",
    "workflow.learning.capture": "hook.capture-learning",
    "workflow.learning.inject": "hook.inject-learning",
    "delegation.packet.validate": "hook.validate-packet",
    "delegation.join.validate": "hook.validate-result",
    "project_cognition.mark_dirty": "hook.mark-dirty",
    "project_cognition.complete_refresh": "hook.complete-refresh",
}


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
        command_id = _HOOK_COMMAND_IDS.get(self.event)
        resume_argv = (
            ["specify", "api", "command", command_id, "--format", "json"]
            if command_id
            else [
                "specify",
                "api",
                "commands",
                "--query",
                self.event,
                "--format",
                "json",
            ]
        )
        resume_command = render_command(tuple(resume_argv))
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
                "instruction": (
                    f"Inspect the exact installed hook command contract, then rerun "
                    f"the owning workflow action guarded by {self.event}: {resume_command}"
                ),
                "command": resume_command,
                "argv": resume_argv,
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
