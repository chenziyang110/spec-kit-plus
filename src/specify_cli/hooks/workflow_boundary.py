"""Shared workflow and phase boundary validation hooks."""

from __future__ import annotations

from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_BOUNDARY_VALIDATE, WORKFLOW_PHASE_BOUNDARY_VALIDATE
from .types import HookResult, QualityHookError


ALLOWED_WORKFLOW_TRANSITIONS = {
    ("specify", "plan"),
    ("specify", "clarify"),
    ("clarify", "plan"),
    ("plan", "tasks"),
    ("plan", "checklist"),
    ("tasks", "analyze"),
    ("analyze", "implement"),
    ("implement", "debug"),
    ("quick", "debug"),
    ("fast", "quick"),
}

ALLOWED_PHASE_TRANSITIONS = {
    ("planning-only", "design-only"),
    ("design-only", "task-generation-only"),
    ("task-generation-only", "analysis-only"),
    ("analysis-only", "execution-only"),
}


def workflow_boundary_hook(_project_root, payload: dict[str, object]) -> HookResult:
    from_command = normalize_command_name(str(payload.get("from_command") or ""))
    to_command = normalize_command_name(str(payload.get("to_command") or ""))

    if (from_command, to_command) not in ALLOWED_WORKFLOW_TRANSITIONS:
        return HookResult(
            event=WORKFLOW_BOUNDARY_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"workflow transition is not allowed: {from_command} -> {to_command}"],
        )

    return HookResult(
        event=WORKFLOW_BOUNDARY_VALIDATE,
        status="ok",
        severity="info",
        data={"from_command": from_command, "to_command": to_command},
    )


def phase_boundary_hook(_project_root, payload: dict[str, object]) -> HookResult:
    from_phase = str(payload.get("from_phase_mode") or "").strip().lower()
    to_phase = str(payload.get("to_phase_mode") or "").strip().lower()
    if not from_phase or not to_phase:
        raise QualityHookError("from_phase_mode and to_phase_mode are required")

    if (from_phase, to_phase) not in ALLOWED_PHASE_TRANSITIONS:
        return HookResult(
            event=WORKFLOW_PHASE_BOUNDARY_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"phase transition is not allowed: {from_phase} -> {to_phase}"],
        )

    return HookResult(
        event=WORKFLOW_PHASE_BOUNDARY_VALIDATE,
        status="ok",
        severity="info",
        data={"from_phase_mode": from_phase, "to_phase_mode": to_phase},
    )

