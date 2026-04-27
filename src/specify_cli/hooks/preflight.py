"""Preflight hooks for workflow entry integrity."""

from __future__ import annotations

from pathlib import Path

from .checkpoint_serializers import normalize_command_name, serialize_workflow_state
from .events import WORKFLOW_PREFLIGHT
from .project_map import project_map_freshness_result
from .types import HookResult, QualityHookError


def workflow_preflight_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    freshness = project_map_freshness_result(project_root, command_name=command_name)

    errors = list(freshness.errors)
    warnings = list(freshness.warnings)

    if command_name == "implement":
        raw_feature_dir = str(payload.get("feature_dir") or "").strip()
        if not raw_feature_dir:
            raise QualityHookError("feature_dir is required for implement preflight")
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()
        state_path = feature_dir / "workflow-state.md"
        if not state_path.exists():
            errors.append(f"workflow-state.md is missing at {state_path}")
        else:
            checkpoint = serialize_workflow_state(state_path)
            next_command = str(checkpoint.get("next_command") or "").strip()
            if next_command and next_command != "/sp.implement":
                errors.append(
                    f"workflow-state requires {next_command} before /sp.implement may continue"
                )
            if checkpoint.get("active_command") == "sp-analyze" and checkpoint.get("status") != "completed":
                errors.append("analyze gate is still active and has not been cleared")

    if errors:
        return HookResult(
            event=WORKFLOW_PREFLIGHT,
            status="blocked",
            severity="critical",
            errors=errors,
            warnings=warnings,
            data={"project_map": freshness.to_dict()},
        )
    if warnings:
        return HookResult(
            event=WORKFLOW_PREFLIGHT,
            status="warn",
            severity="warning",
            warnings=warnings,
            data={"project_map": freshness.to_dict()},
        )
    return HookResult(
        event=WORKFLOW_PREFLIGHT,
        status="ok",
        severity="info",
        data={"project_map": freshness.to_dict()},
    )

