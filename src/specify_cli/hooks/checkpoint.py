"""Checkpoint hooks for context recovery and compaction survival."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import (
    normalize_command_name,
    serialize_debug_session,
    serialize_implement_tracker,
    serialize_quick_status,
    serialize_workflow_state,
)
from .events import WORKFLOW_CHECKPOINT
from .types import HookResult, QualityHookError


def checkpoint_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))

    if command_name in {"constitution", "specify", "deep-research", "plan", "tasks", "analyze"}:
        feature_dir = _required_path(project_root, payload, "feature_dir")
        target = feature_dir / "workflow-state.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_CHECKPOINT,
                status="blocked",
                severity="critical",
                errors=[f"workflow-state.md is missing at {target}"],
            )
        return HookResult(
            event=WORKFLOW_CHECKPOINT,
            status="ok",
            severity="info",
            data={"checkpoint": serialize_workflow_state(target)},
        )

    if command_name == "implement":
        feature_dir = _required_path(project_root, payload, "feature_dir")
        target = feature_dir / "implement-tracker.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_CHECKPOINT,
                status="blocked",
                severity="critical",
                errors=[f"implement-tracker.md is missing at {target}"],
            )
        return HookResult(
            event=WORKFLOW_CHECKPOINT,
            status="ok",
            severity="info",
            data={"checkpoint": serialize_implement_tracker(target)},
        )

    if command_name == "quick":
        workspace = _required_path(project_root, payload, "workspace")
        target = workspace / "STATUS.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_CHECKPOINT,
                status="blocked",
                severity="critical",
                errors=[f"STATUS.md is missing at {target}"],
            )
        return HookResult(
            event=WORKFLOW_CHECKPOINT,
            status="ok",
            severity="info",
            data={"checkpoint": serialize_quick_status(target)},
        )

    if command_name == "debug":
        session_file = _required_path(project_root, payload, "session_file")
        if not session_file.exists():
            return HookResult(
                event=WORKFLOW_CHECKPOINT,
                status="blocked",
                severity="critical",
                errors=[f"debug session file is missing at {session_file}"],
            )
        return HookResult(
            event=WORKFLOW_CHECKPOINT,
            status="ok",
            severity="info",
            data={"checkpoint": serialize_debug_session(session_file)},
        )

    raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.checkpoint")


def _required_path(project_root: Path, payload: dict[str, object], key: str) -> Path:
    raw = str(payload.get(key) or "").strip()
    if not raw:
        raise QualityHookError(f"{key} is required")
    path = Path(raw)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path
