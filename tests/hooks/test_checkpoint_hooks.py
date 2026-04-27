from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-checkpoint-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_checkpoint_blocks_when_quick_status_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-001-demo"
    workspace.mkdir(parents=True, exist_ok=True)

    result = run_quality_hook(
        project,
        "workflow.checkpoint",
        {"command_name": "quick", "workspace": str(workspace)},
    )

    assert result.status == "blocked"
    assert any("STATUS.md" in message for message in result.errors)


def test_checkpoint_returns_implement_tracker_resume_fields(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: executing",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: keep tracker honest",
                "next_action: wait for worker handoff",
                "",
                "## Execution State",
                "retry_attempts: 1",
                "",
                "## Open Gaps",
                "- type: execution_gap",
                "  summary: waiting on validation evidence",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.checkpoint",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["state_kind"] == "implement-tracker"
    assert checkpoint["status"] == "executing"
    assert checkpoint["current_batch"] == "batch-a"
    assert checkpoint["next_action"] == "wait for worker handoff"
    assert checkpoint["resume_decision"] == "resume-here"
