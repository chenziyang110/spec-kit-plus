"""Hooks that reconcile resume-critical workflow session state."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import (
    normalize_command_name,
    serialize_debug_session,
    serialize_implement_tracker,
    serialize_quick_status,
    serialize_workflow_state,
)
from .events import WORKFLOW_SESSION_STATE_VALIDATE
from .types import HookResult, QualityHookError


def session_state_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))

    if command_name == "implement":
        feature_dir = _required_path(project_root, payload, "feature_dir")
        workflow_path = feature_dir / "workflow-state.md"
        tracker_path = feature_dir / "implement-tracker.md"
        if not workflow_path.exists():
            return HookResult(
                event=WORKFLOW_SESSION_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"workflow-state.md is missing at {workflow_path}"],
            )
        if not tracker_path.exists():
            return HookResult(
                event=WORKFLOW_SESSION_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"implement-tracker.md is missing at {tracker_path}"],
            )

        workflow = serialize_workflow_state(workflow_path)
        tracker = serialize_implement_tracker(tracker_path)
        warnings: list[str] = []
        next_command = str(workflow.get("next_command") or "")
        if next_command and next_command != "/sp.implement" and tracker.get("status") not in {"blocked", "resolved"}:
            warnings.append(
                f"workflow-state next_command is {next_command}, but implement-tracker still reports active execution"
            )

        result_status = "warn" if warnings else "ok"
        severity = "warning" if warnings else "info"
        return HookResult(
            event=WORKFLOW_SESSION_STATE_VALIDATE,
            status=result_status,
            severity=severity,
            warnings=warnings,
            data={
                "state_summary": {
                    "next_command": next_command,
                    "workflow_status": workflow.get("status", ""),
                    "tracker_status": tracker.get("status", ""),
                    "current_batch": tracker.get("current_batch", ""),
                    "resume_decision": tracker.get("resume_decision", ""),
                }
            },
        )

    if command_name == "quick":
        workspace = _required_path(project_root, payload, "workspace")
        target = workspace / "STATUS.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_SESSION_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"STATUS.md is missing at {target}"],
            )
        summary = serialize_quick_status(target)
        return HookResult(
            event=WORKFLOW_SESSION_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"state_summary": summary},
        )

    if command_name == "debug":
        session_file = _required_path(project_root, payload, "session_file")
        if not session_file.exists():
            return HookResult(
                event=WORKFLOW_SESSION_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"debug session file is missing at {session_file}"],
            )
        summary = serialize_debug_session(session_file)
        return HookResult(
            event=WORKFLOW_SESSION_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"state_summary": summary},
        )

    raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.session_state.validate")


def _required_path(project_root: Path, payload: dict[str, object], key: str) -> Path:
    raw = str(payload.get(key) or "").strip()
    if not raw:
        raise QualityHookError(f"{key} is required")
    path = Path(raw)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path

