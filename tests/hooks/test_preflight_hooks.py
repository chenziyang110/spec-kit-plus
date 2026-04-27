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
