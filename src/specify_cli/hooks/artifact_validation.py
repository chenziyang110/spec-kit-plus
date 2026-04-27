"""Validation hooks for workflow artifact completeness."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_ARTIFACTS_VALIDATE
from .types import HookResult, QualityHookError


REQUIRED_ARTIFACTS = {
    "specify": ("spec.md", "alignment.md", "context.md", "workflow-state.md"),
    "plan": ("plan.md", "workflow-state.md"),
    "tasks": ("tasks.md", "workflow-state.md"),
    "analyze": ("workflow-state.md",),
}


def validate_artifacts_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    if command_name not in REQUIRED_ARTIFACTS:
        raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.artifacts.validate")

    raw = str(payload.get("feature_dir") or "").strip()
    if not raw:
        raise QualityHookError("feature_dir is required")
    feature_dir = Path(raw)
    if not feature_dir.is_absolute():
        feature_dir = (project_root / feature_dir).resolve()

    missing = [name for name in REQUIRED_ARTIFACTS[command_name] if not (feature_dir / name).exists()]
    if missing:
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"missing required artifact: {name}" for name in missing],
            data={"feature_dir": str(feature_dir)},
        )
    return HookResult(
        event=WORKFLOW_ARTIFACTS_VALIDATE,
        status="ok",
        severity="info",
        data={"feature_dir": str(feature_dir)},
    )

