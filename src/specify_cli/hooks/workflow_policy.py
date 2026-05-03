"""Shared workflow-policy evaluation and enforcement classification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

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
SOFT_REDIRECT_ACTIONS = {
    "start_editing_code",
    "start_implementation",
    "run_fix_loop",
    "jump_to_testing",
}
REDIRECTABLE_WORKFLOW_COMMANDS = {
    "constitution",
    "specify",
    "deep-research",
    "plan",
    "tasks",
    "analyze",
    "prd",
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

    if (
        requested_action in SOFT_REDIRECT_ACTIONS
        and command_name in REDIRECTABLE_WORKFLOW_COMMANDS
    ):
        checkpoint = state_result.data.get("checkpoint", {})
        recovery_summary = _build_recovery_summary(
            checkpoint
        )
        policy = {
            "classification": "redirect",
            "trigger": trigger,
            "command_name": command_name,
            "repairable": False,
            "requested_action": requested_action,
            "recovery_summary": recovery_summary,
        }
        count_override = payload.get("prior_redirect_count")
        redirect_store = _redirect_store_path(
            project_root,
            checkpoint,
            recovery_summary,
            requested_action,
        )
        prior_redirect_count = (
            int(count_override)
            if count_override is not None
            else _read_redirect_count(redirect_store)
        )
        if prior_redirect_count >= 1:
            return HookResult(
                event=WORKFLOW_POLICY_EVALUATE,
                status="blocked",
                severity="critical",
                errors=[
                    "requested action repeats a phase drift after redirect; return to the recorded workflow phase before continuing"
                ],
                data={"policy": policy},
            )
        _write_redirect_count(redirect_store, 1)
        return HookResult(
            event=WORKFLOW_POLICY_EVALUATE,
            status="warn",
            severity="warning",
            warnings=[
                "requested action conflicts with the active workflow phase; redirect before continuing"
            ],
            actions=[
                "re-read the authoritative workflow state and continue from the recorded next action"
            ],
            data={"policy": policy},
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


def _build_recovery_summary(checkpoint: object) -> dict[str, object]:
    if not isinstance(checkpoint, dict):
        checkpoint = {}
    return {
        "phase_mode": checkpoint.get("phase_mode", ""),
        "summary": checkpoint.get("summary", ""),
        "forbidden_actions": list(checkpoint.get("forbidden_actions", [])),
        "authoritative_files": list(checkpoint.get("authoritative_files", [])),
        "next_action": checkpoint.get("next_action", ""),
        "next_command": checkpoint.get("next_command", ""),
        "route_reason": checkpoint.get("route_reason", ""),
    }


def _redirect_store_path(
    project_root: Path,
    checkpoint: object,
    recovery_summary: dict[str, object],
    requested_action: str,
) -> Path:
    checkpoint_path = ""
    if isinstance(checkpoint, dict):
        checkpoint_path = str(checkpoint.get("path") or "")
    scope = {
        "checkpoint_path": checkpoint_path,
        "phase_mode": recovery_summary["phase_mode"],
        "next_action": recovery_summary["next_action"],
        "next_command": recovery_summary["next_command"],
        "route_reason": recovery_summary["route_reason"],
        "requested_action": requested_action,
    }
    digest = hashlib.sha256(
        json.dumps(scope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return project_root / ".specify" / "runtime" / "workflow-policy" / f"{digest}.json"


def _read_redirect_count(path: Path) -> int:
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return 0
    if not isinstance(data, dict):
        return 0
    try:
        return int(data.get("count") or 0)
    except (TypeError, ValueError):
        return 0


def _write_redirect_count(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"count": count}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
