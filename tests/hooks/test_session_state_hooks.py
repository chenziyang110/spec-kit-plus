from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-session-state-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_workflow_state(feature_dir: Path, next_command: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-analyze`",
                "- status: `completed`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: demo",
                "",
                "## Next Action",
                "",
                "- continue",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_implement_tracker(feature_dir: Path, status: str = "executing") -> None:
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                f"status: {status}",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: execute batch",
                "next_action: collect worker result",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_session_state_accepts_consistent_implement_resume_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.implement")
    _write_implement_tracker(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.session_state.validate",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.data["state_summary"]["next_command"] == "/sp.implement"
    assert result.data["state_summary"]["tracker_status"] == "executing"


def test_session_state_warns_when_implement_tracker_conflicts_with_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.tasks")
    _write_implement_tracker(feature_dir, status="executing")

    result = run_quality_hook(
        project,
        "workflow.session_state.validate",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert any("/sp.tasks" in message for message in result.warnings)


def test_session_state_warns_when_lane_recovery_is_uncertain(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.tasks")
    _write_implement_tracker(feature_dir, status="executing")

    result = run_quality_hook(
        project,
        "workflow.session_state.validate",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert any("/sp.tasks" in message for message in result.warnings)
