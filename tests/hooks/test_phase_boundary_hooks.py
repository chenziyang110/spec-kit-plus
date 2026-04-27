from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-phase-boundary-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_phase_boundary_allows_analysis_to_execution(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "analysis-only", "to_phase_mode": "execution-only"},
    )

    assert result.status == "ok"


def test_phase_boundary_blocks_planning_to_execution_jump(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "planning-only", "to_phase_mode": "execution-only"},
    )

    assert result.status == "blocked"
    assert any("planning-only" in message for message in result.errors)

