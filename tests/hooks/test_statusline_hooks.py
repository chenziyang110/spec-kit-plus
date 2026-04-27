from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-statusline-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_quick_status(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260427-003"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                'strategy: "single-lane"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: finish validation",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
                "join_point: none",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_implement_tracker(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: validating",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-b",
                "goal: verify all checks",
                "next_action: run targeted tests",
                "",
                "## Execution State",
                "retry_attempts: 1",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_statusline_renders_quick_summary(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-003-demo-quick-task"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.statusline.render",
        {"command_name": "quick", "workspace": str(workspace)},
    )

    assert result.status == "ok"
    line = result.data["statusline"]
    assert "quick:executing" in line
    assert "lane:worker-a" in line
    assert "next:finish validation" in line


def test_statusline_renders_implement_summary(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.statusline.render",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    line = result.data["statusline"]
    assert "implement:validating" in line
    assert "batch:batch-b" in line
    assert "retry:1" in line

