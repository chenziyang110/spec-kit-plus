"""Compact operator-facing statusline rendering from workflow state."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import (
    normalize_command_name,
    serialize_debug_session,
    serialize_implement_tracker,
    serialize_quick_status,
    serialize_workflow_state,
)
from .events import WORKFLOW_STATUSLINE_RENDER
from .types import HookResult, QualityHookError


def statusline_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))

    if command_name == "quick":
        workspace = _required_path(project_root, payload, "workspace")
        checkpoint = serialize_quick_status(workspace / "STATUS.md")
        line = " ".join(
            part
            for part in [
                f"quick:{checkpoint.get('status', '')}",
                f"lane:{checkpoint.get('active_lane', '')}" if checkpoint.get("active_lane") else "",
                f"next:{checkpoint.get('next_action', '')}" if checkpoint.get("next_action") else "",
            ]
            if part
        )
        return HookResult(
            event=WORKFLOW_STATUSLINE_RENDER,
            status="ok",
            severity="info",
            data={"statusline": line, "checkpoint": checkpoint},
        )

    if command_name == "implement":
        feature_dir = _required_path(project_root, payload, "feature_dir")
        checkpoint = serialize_implement_tracker(feature_dir / "implement-tracker.md")
        line = " ".join(
            part
            for part in [
                f"implement:{checkpoint.get('status', '')}",
                f"batch:{checkpoint.get('current_batch', '')}" if checkpoint.get("current_batch") else "",
                f"retry:{checkpoint.get('retry_attempts', '')}" if checkpoint.get("retry_attempts") else "",
                f"next:{checkpoint.get('next_action', '')}" if checkpoint.get("next_action") else "",
            ]
            if part
        )
        return HookResult(
            event=WORKFLOW_STATUSLINE_RENDER,
            status="ok",
            severity="info",
            data={"statusline": line, "checkpoint": checkpoint},
        )

    if command_name in {"specify", "plan", "tasks", "analyze"}:
        feature_dir = _required_path(project_root, payload, "feature_dir")
        checkpoint = serialize_workflow_state(feature_dir / "workflow-state.md")
        line = " ".join(
            part
            for part in [
                f"{command_name}:{checkpoint.get('phase_mode', '')}",
                f"status:{checkpoint.get('status', '')}" if checkpoint.get("status") else "",
                f"next:{checkpoint.get('next_action', '')}" if checkpoint.get("next_action") else "",
            ]
            if part
        )
        return HookResult(
            event=WORKFLOW_STATUSLINE_RENDER,
            status="ok",
            severity="info",
            data={"statusline": line, "checkpoint": checkpoint},
        )

    if command_name == "debug":
        session_file = _required_path(project_root, payload, "session_file")
        checkpoint = serialize_debug_session(session_file)
        line = " ".join(
            part
            for part in [
                "debug:active",
                f"next:{checkpoint.get('next_action', '')}" if checkpoint.get("next_action") else "",
            ]
            if part
        )
        return HookResult(
            event=WORKFLOW_STATUSLINE_RENDER,
            status="ok",
            severity="info",
            data={"statusline": line, "checkpoint": checkpoint},
        )

    raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.statusline.render")


def _required_path(project_root: Path, payload: dict[str, object], key: str) -> Path:
    raw = str(payload.get(key) or "").strip()
    if not raw:
        raise QualityHookError(f"{key} is required")
    path = Path(raw)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path

