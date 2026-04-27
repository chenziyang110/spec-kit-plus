import json
from pathlib import Path

import pytest

from specify_cli.hooks.engine import QualityHookError, run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-engine-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_workflow_state(
    feature_dir: Path,
    *,
    active_command: str,
    status: str,
    phase_mode: str,
    next_action: str,
    next_command: str,
) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "workflow-state.md"
    target.write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                f"- active_command: `{active_command}`",
                f"- status: `{status}`",
                "",
                "## Phase Mode",
                "",
                f"- phase_mode: `{phase_mode}`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Exit Criteria",
                "",
                "- done",
                "",
                "## Next Action",
                "",
                f"- {next_action}",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def _write_quick_status(workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "STATUS.md"
    target.write_text(
        "\n".join(
            [
                "---",
                'id: "260427-001"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                'strategy: "single-lane"',
                "---",
                "",
                "## Current Focus",
                "",
                "goal: keep resumable state accurate",
                "current_focus: validate quick checkpoint",
                "next_action: collect worker result",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
                "join_point: none",
                "execution_fallback: none",
                "retry_attempts: 0",
                "blocker_reason:",
                "",
                "## Summary Pointer",
                "",
                "summary_path: .planning/quick/260427-001-demo-quick-task/SUMMARY.md",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def test_run_quality_hook_rejects_unknown_event(tmp_path: Path):
    project = _create_project(tmp_path)

    with pytest.raises(QualityHookError, match="Unknown hook event"):
        run_quality_hook(project, "unknown.event", {})


def test_workflow_state_validate_blocks_missing_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert result.severity == "critical"
    assert any("workflow-state.md" in message for message in result.errors)


def test_project_map_mark_dirty_hook_updates_status_file(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "project_map.mark_dirty",
        {"reason": "shared surface changed"},
    )

    assert result.status == "ok"
    assert result.severity == "info"
    status_path = project / ".specify" / "project-map" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["dirty"] is True
    assert payload["freshness"] == "stale"
    assert payload["dirty_reasons"] == ["shared_surface_changed"]


def test_workflow_checkpoint_returns_resume_payload_for_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-plan",
        status="active",
        phase_mode="design-only",
        next_action="finish constitution checks",
        next_command="/sp.tasks",
    )

    result = run_quality_hook(
        project,
        "workflow.checkpoint",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.severity == "info"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["state_kind"] == "workflow-state"
    assert checkpoint["active_command"] == "sp-plan"
    assert checkpoint["phase_mode"] == "design-only"
    assert checkpoint["next_action"] == "finish constitution checks"
    assert checkpoint["next_command"] == "/sp.tasks"


def test_workflow_checkpoint_returns_resume_payload_for_quick_status(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-001-demo-quick-task"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.checkpoint",
        {"command_name": "quick", "workspace": str(workspace)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["state_kind"] == "quick-status"
    assert checkpoint["active_lane"] == "worker-a"
    assert checkpoint["next_action"] == "collect worker result"
    assert checkpoint["resume_decision"] == "resume here"
