from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-preflight-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_workflow_state(
    feature_dir: Path,
    *,
    active_command: str,
    status: str,
    phase_mode: str,
    next_command: str,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
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


def test_preflight_blocks_implement_when_workflow_state_requires_analyze(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_command="/sp.analyze",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert result.severity == "critical"
    assert any("/sp.analyze" in message for message in result.errors)


def test_preflight_warns_when_project_map_status_is_missing_for_brownfield_work(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.severity == "warning"
    assert any("project-map" in message for message in result.warnings)


def test_preflight_blocks_integrate_when_lane_is_not_ready(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "lanes" / "lane-001").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "lanes" / "lane-001" / "lane.json").write_text(
        "\n".join(
            [
                "{",
                '  "lane_id": "lane-001",',
                '  "feature_id": "001-demo",',
                '  "feature_dir": "specs/001-demo",',
                '  "branch_name": "001-demo",',
                '  "worktree_path": ".specify/lanes/worktrees/lane-001",',
                '  "lifecycle_state": "implementing",',
                '  "recovery_state": "blocked",',
                '  "last_command": "implement",',
                '  "last_stable_checkpoint": "",',
                '  "recovery_reason": "missing verification",',
                '  "verification_status": "failed",',
                '  "created_at": "2026-05-02T00:00:00+00:00",',
                '  "updated_at": "2026-05-02T00:00:00+00:00"',
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: blocked",
                "feature: 001-demo",
                "resume_decision: blocked-waiting",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: blocked",
                "next_action: fix verification",
                "",
                "## Execution State",
                "retry_attempts: 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "integrate", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("integrate precheck failed" in message for message in result.errors)
