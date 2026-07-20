"""Preflight hooks for workflow entry integrity."""

from __future__ import annotations

from pathlib import Path

from specify_cli.lanes.state_store import iter_lane_records

from .checkpoint_serializers import normalize_command_name, serialize_workflow_state
from .events import WORKFLOW_PREFLIGHT
from .project_cognition import project_cognition_freshness_result
from .types import HookResult, QualityHookError


def workflow_preflight_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    freshness = project_cognition_freshness_result(project_root, command_name=command_name)

    errors: list[str] = []
    warnings = list(freshness.warnings)
    if freshness.errors:
        warnings.extend(freshness.errors)

    if command_name == "implement":
        raw_feature_dir = str(payload.get("feature_dir") or "").strip()
        if not raw_feature_dir:
            raise QualityHookError("feature_dir is required for implement preflight")
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()
        state_path = feature_dir / "workflow-state.md"
        current_lane_id = ""
        if state_path.exists():
            preview_checkpoint = serialize_workflow_state(state_path)
            current_lane_id = str(preview_checkpoint.get("lane_id") or "").strip()
        if not state_path.exists():
            errors.append(f"workflow-state.md is missing at {state_path}")
        else:
            checkpoint = preview_checkpoint if current_lane_id else serialize_workflow_state(state_path)
            next_command = str(checkpoint.get("next_command") or "").strip()
            if next_command and next_command != "/sp.implement":
                tracker_summary = ""
                tracker_path = feature_dir / "implement-tracker.md"
                if tracker_path.exists():
                    from .checkpoint_serializers import serialize_implement_tracker

                    tracker = serialize_implement_tracker(tracker_path)
                    tracker_bits = [
                        f"tracker_status={tracker.get('status', '')}",
                        f"current_batch={tracker.get('current_batch', '')}",
                        f"resume_decision={tracker.get('resume_decision', '')}",
                    ]
                    tracker_summary = " | " + ", ".join(bit for bit in tracker_bits if not bit.endswith("="))
                errors.append(
                    "workflow-state requires "
                    f"{next_command} before /sp.implement may continue "
                    f"(active_command={checkpoint.get('active_command', '')}, "
                    f"workflow_status={checkpoint.get('status', '')}, "
                    f"phase_mode={checkpoint.get('phase_mode', '')}, "
                    f"next_action={checkpoint.get('next_action', '')})"
                    f"{tracker_summary}"
                )
            if checkpoint.get("active_command") == "sp-analyze" and checkpoint.get("status") != "completed":
                errors.append("analyze gate is still active and has not been cleared")

    if command_name == "integrate":
        from specify_cli.lanes.integration import assess_integration_readiness

        raw_feature_dir = str(payload.get("feature_dir") or "").strip()
        if not raw_feature_dir:
            raise QualityHookError("feature_dir is required for integrate preflight")
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()

        lane = next(
            (
                record
                for record in iter_lane_records(project_root)
                if (project_root / record.feature_dir).resolve() == feature_dir.resolve()
            ),
            None,
        )
        if lane is None:
            errors.append(f"no lane record found for feature dir {feature_dir}")
        else:
            readiness = assess_integration_readiness(project_root, lane)
            if not readiness.ready:
                for check in readiness.checks:
                    if check["status"] != "pass":
                        errors.append(f"integrate precheck failed: {check['name']} ({check['detail']})")

    if command_name == "review":
        raw_feature_dir = str(payload.get("feature_dir") or "").strip()
        if not raw_feature_dir:
            raise QualityHookError("feature_dir is required for review preflight")
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()
        handoff_path = feature_dir / "implementation-handoff.json"
        if not handoff_path.is_file():
            errors.append(f"implementation-handoff.json is missing at {handoff_path}")
        try:
            from specify_cli.workflow_runtime import show_workflow

            workflow = show_workflow(feature_dir)["data"]
            if workflow.get("stage") != "review" or workflow.get("status") != "active":
                errors.append(
                    "review preflight requires active workflow stage review after implement completion"
                )
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"review workflow runtime is unavailable: {exc}")

    if errors:
        return HookResult(
            event=WORKFLOW_PREFLIGHT,
            status="blocked",
            severity="critical",
            errors=errors,
            warnings=warnings,
            data={"project_cognition": freshness.to_dict()},
        )
    if warnings:
        return HookResult(
            event=WORKFLOW_PREFLIGHT,
            status="warn",
            severity="warning",
            warnings=warnings,
            data={"project_cognition": freshness.to_dict()},
        )
    return HookResult(
        event=WORKFLOW_PREFLIGHT,
        status="ok",
        severity="info",
        data={"project_cognition": freshness.to_dict()},
    )
