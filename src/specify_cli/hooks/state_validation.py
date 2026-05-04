"""Validation hooks for workflow source-of-truth state files."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import (
    normalize_command_name,
    serialize_debug_session,
    serialize_implement_tracker,
    serialize_quick_status,
    serialize_workflow_state,
)
from .events import WORKFLOW_STATE_VALIDATE
from .types import HookResult, QualityHookError


EXPECTED_WORKFLOW_STATE = {
    "constitution": ("sp-constitution", "planning-only"),
    "specify": ("sp-specify", "planning-only"),
    "deep-research": ("sp-deep-research", "research-only"),
    "plan": ("sp-plan", "design-only"),
    "tasks": ("sp-tasks", "task-generation-only"),
    "analyze": ("sp-analyze", "analysis-only"),
    "prd": ("sp-prd", "analysis-only"),
}


def validate_state_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))

    if command_name in EXPECTED_WORKFLOW_STATE:
        feature_dir = _required_path(project_root, payload, "feature_dir")
        target = feature_dir / "workflow-state.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"workflow-state.md is missing at {target}"],
            )
        checkpoint = serialize_workflow_state(target)
        expected_command, expected_phase = EXPECTED_WORKFLOW_STATE[command_name]
        errors: list[str] = []
        if checkpoint["active_command"] != expected_command:
            errors.append(
                f"active_command mismatch: expected {expected_command}, got {checkpoint['active_command'] or 'missing'}"
            )
        if checkpoint["phase_mode"] != expected_phase:
            errors.append(
                f"phase_mode mismatch: expected {expected_phase}, got {checkpoint['phase_mode'] or 'missing'}"
            )
        if not checkpoint["allowed_artifact_writes"]:
            errors.append("workflow-state is missing allowed_artifact_writes")
        if not checkpoint["forbidden_actions"]:
            errors.append("workflow-state is missing forbidden_actions")
        if not checkpoint["authoritative_files"]:
            errors.append("workflow-state is missing authoritative_files")
        if not checkpoint["next_command"]:
            errors.append("workflow-state is missing next_command")
        if errors:
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=errors,
                data={"checkpoint": checkpoint},
            )
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint},
        )

    if command_name == "implement":
        feature_dir = _required_path(project_root, payload, "feature_dir")
        target = feature_dir / "implement-tracker.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"implement-tracker.md is missing at {target}"],
            )
        checkpoint = serialize_implement_tracker(target)
        errors = []
        if not checkpoint["status"]:
            errors.append("implement-tracker is missing frontmatter status")
        if not checkpoint["next_action"]:
            errors.append("implement-tracker is missing next_action")
        if errors:
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=errors,
                data={"checkpoint": checkpoint},
            )
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint},
        )

    if command_name == "quick":
        workspace = _required_path(project_root, payload, "workspace")
        target = workspace / "STATUS.md"
        if not target.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"STATUS.md is missing at {target}"],
            )
        checkpoint = serialize_quick_status(target)
        errors = []
        if not checkpoint["status"]:
            errors.append("quick STATUS.md is missing frontmatter status")
        if not checkpoint["next_action"]:
            errors.append("quick STATUS.md is missing next_action")
        if errors:
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=errors,
                data={"checkpoint": checkpoint},
            )
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint},
        )

    if command_name == "debug":
        session_file = _required_path(project_root, payload, "session_file")
        if not session_file.exists():
            return HookResult(
                event=WORKFLOW_STATE_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"debug session file is missing at {session_file}"],
            )
        checkpoint = serialize_debug_session(session_file)
        return HookResult(
            event=WORKFLOW_STATE_VALIDATE,
            status="ok",
            severity="info",
            data={"checkpoint": checkpoint},
        )

    raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.state.validate")


def _required_path(project_root: Path, payload: dict[str, object], key: str) -> Path:
    raw = str(payload.get(key) or "").strip()
    if not raw:
        raise QualityHookError(f"{key} is required")
    path = Path(raw)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path
