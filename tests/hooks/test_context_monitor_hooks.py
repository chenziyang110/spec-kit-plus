from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-context-monitor-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_quick_status(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260427-002"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                'dispatch_shape: "parallel-subagents"',
                'execution_surface: "native-subagents"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate worker results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "join_point: join-1",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_implement_state(feature_dir: Path) -> None:
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
                "goal: finish validation",
                "next_action: collect green evidence",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_context_monitor_warns_and_embeds_checkpoint_when_usage_is_high(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-002-demo-quick-task"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.context.monitor",
        {
            "command_name": "quick",
            "workspace": str(workspace),
            "context_usage_percent": 85,
            "trigger": "after_artifact_synthesis",
        },
    )

    assert result.status == "warn"
    assert result.severity == "warning"
    assert result.data["should_checkpoint"] is True
    assert result.data["checkpoint"]["state_kind"] == "quick-status"


def test_context_monitor_blocks_structural_transition_when_resume_state_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)

    result = run_quality_hook(
        project,
        "workflow.context.monitor",
        {
            "command_name": "implement",
            "feature_dir": str(feature_dir),
            "trigger": "before_delegation",
        },
    )

    assert result.status == "blocked"
    assert any("implement-tracker.md" in message for message in result.errors)


def test_context_monitor_stays_ok_when_pressure_is_low(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.context.monitor",
        {
            "command_name": "implement",
            "feature_dir": str(feature_dir),
            "context_usage_percent": 30,
            "trigger": "turn-progress",
        },
    )

    assert result.status == "ok"
    assert result.data["should_checkpoint"] is False
