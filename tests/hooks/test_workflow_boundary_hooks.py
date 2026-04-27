from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-workflow-boundary-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_workflow_boundary_allows_mainline_transition(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "specify", "to_command": "plan"},
    )

    assert result.status == "ok"


def test_workflow_boundary_blocks_skipping_directly_to_implement(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "specify", "to_command": "implement"},
    )

    assert result.status == "blocked"
    assert any("implement" in message for message in result.errors)

