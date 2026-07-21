"""Shared workflow and phase boundary validation hooks."""

from __future__ import annotations

from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_BOUNDARY_VALIDATE, WORKFLOW_PHASE_BOUNDARY_VALIDATE
from .types import HookResult, QualityHookError


ALLOWED_WORKFLOW_TRANSITIONS = {
    ("specify", "plan"),
    ("specify", "clarify"),
    ("specify", "deep-research"),
    ("clarify", "plan"),
    ("clarify", "deep-research"),
    ("deep-research", "plan"),
    ("deep-research", "clarify"),
    ("plan", "tasks"),
    ("plan", "checklist"),
    ("tasks", "implement"),
    ("tasks", "analyze"),
    ("analyze", "implement"),
    ("implement", "review"),
    ("implement", "debug"),
    ("review", "accept"),
    ("review", "plan"),
    ("review", "clarify"),
    ("review", "specify"),
    ("review", "design"),
    ("accept", "review"),
    ("accept", "integrate"),
    ("quick", "debug"),
    ("fast", "quick"),
}

ALLOWED_PHASE_TRANSITIONS = {
    ("planning-only", "design-only"),
    ("planning-only", "research-only"),
    ("research-only", "design-only"),
    ("design-only", "task-generation-only"),
    ("task-generation-only", "execution-only"),
    ("task-generation-only", "analysis-only"),
    ("analysis-only", "execution-only"),
    ("execution-only", "review-and-repair"),
    ("review-and-repair", "acceptance-only"),
    ("review-and-repair", "planning-only"),
    ("acceptance-only", "review-and-repair"),
}


def workflow_boundary_hook(_project_root, payload: dict[str, object]) -> HookResult:
    from_command = normalize_command_name(str(payload.get("from_command") or ""))
    to_command = normalize_command_name(str(payload.get("to_command") or ""))

    transition = (from_command, to_command)
    if transition not in ALLOWED_WORKFLOW_TRANSITIONS:
        return HookResult(
            event=WORKFLOW_BOUNDARY_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"workflow transition is not allowed: {from_command} -> {to_command}"],
        )

    if from_command == "review" and to_command in {
        "plan",
        "clarify",
        "specify",
        "design",
    }:
        reason_category = str(payload.get("reason_category") or "").strip().lower()
        if reason_category != "upstream_truth_gap":
            return HookResult(
                event=WORKFLOW_BOUNDARY_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[
                    "review keeps diagnosis and approved-scope fixes inside its Fix wave; "
                    "upstream transitions require reason_category upstream_truth_gap"
                ],
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

    if from_phase == "review-and-repair" and to_phase == "planning-only":
        reason_category = str(payload.get("reason_category") or "").strip().lower()
        if reason_category != "upstream_truth_gap":
            return HookResult(
                event=WORKFLOW_PHASE_BOUNDARY_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[
                    "review-and-repair may return to planning only for an upstream_truth_gap"
                ],
            )

    return HookResult(
        event=WORKFLOW_PHASE_BOUNDARY_VALIDATE,
        status="ok",
        severity="info",
        data={"from_phase_mode": from_phase, "to_phase_mode": to_phase},
    )
