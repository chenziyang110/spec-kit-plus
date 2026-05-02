"""Shared workflow-policy evaluation and enforcement classification."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_POLICY_EVALUATE
from .session_state import session_state_hook
from .state_validation import validate_state_hook
from .types import HookResult, QualityHookError


HARD_BLOCKABLE_PHASE_JUMPS = {
    "jump_to_implement",
    "jump_to_code",
    "skip_to_implement",
    "implement_directly",
}


def workflow_policy_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    trigger = str(payload.get("trigger") or "unknown").strip().lower() or "unknown"
    requested_action = str(payload.get("requested_action") or "").strip().lower()

    if not command_name:
        raise QualityHookError("command_name is required")

    if requested_action in HARD_BLOCKABLE_PHASE_JUMPS:
        return HookResult(
            event=WORKFLOW_POLICY_EVALUATE,
            status="blocked",
            severity="critical",
            errors=["requested action attempts to skip required workflow phases"],
            data={
                "policy": {
                    "classification": "hard-blockable",
                    "trigger": trigger,
                    "command_name": command_name,
                    "repairable": False,
                    "requested_action": requested_action,
                }
            },
        )

    state_result = validate_state_hook(project_root, payload)
    if state_result.status == "blocked":
        return HookResult(
            event=WORKFLOW_POLICY_EVALUATE,
            status="repairable-block",
            severity="warning",
            actions=[
                *state_result.errors,
                "repair or recreate the required workflow state before continuing, including workflow-state.md or the command-specific tracker",
            ],
            errors=list(state_result.errors),
            data={
                "policy": {
                    "classification": "soft-enforced",
                    "trigger": trigger,
                    "command_name": command_name,
                    "repairable": True,
                    "state_result": state_result.to_dict(),
                }
            },
        )

    if command_name in {"implement", "quick", "debug"}:
        session_result = session_state_hook(project_root, payload)
        if session_result.status == "blocked":
            return HookResult(
                event=WORKFLOW_POLICY_EVALUATE,
                status="repairable-block",
                severity="warning",
                actions=[
                    *session_result.errors,
                    "repair the resumable workflow session state before continuing, including workflow-state.md or the command-specific tracker",
                ],
                errors=list(session_result.errors),
                data={
                    "policy": {
                        "classification": "soft-enforced",
                        "trigger": trigger,
                        "command_name": command_name,
                        "repairable": True,
                        "session_result": session_result.to_dict(),
                    }
                },
            )
        if session_result.status == "warn":
            return HookResult(
                event=WORKFLOW_POLICY_EVALUATE,
                status="warn",
                severity="warning",
                warnings=list(session_result.warnings),
                actions=[
                    "refresh tracker and workflow state before the next phase-sensitive action"
                ],
                data={
                    "policy": {
                        "classification": "soft-enforced",
                        "trigger": trigger,
                        "command_name": command_name,
                        "repairable": False,
                        "session_result": session_result.to_dict(),
                    }
                },
            )

    return HookResult(
        event=WORKFLOW_POLICY_EVALUATE,
        status="ok",
        severity="info",
        data={
            "policy": {
                "classification": "allow",
                "trigger": trigger,
                "command_name": command_name,
                "repairable": False,
            }
        },
    )
