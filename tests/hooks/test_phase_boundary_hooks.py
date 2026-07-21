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


def test_phase_boundary_allows_task_generation_to_execution(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "task-generation-only", "to_phase_mode": "execution-only"},
    )

    assert result.status == "ok"


def test_phase_boundary_allows_execution_to_system_review(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "execution-only", "to_phase_mode": "review-and-repair"},
    )

    assert result.status == "ok"


def test_phase_boundary_allows_system_review_to_human_acceptance(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "review-and-repair", "to_phase_mode": "acceptance-only"},
    )

    assert result.status == "ok"


def test_phase_boundary_keeps_fix_execution_inside_review_mode(tmp_path: Path):
    project = _create_project(tmp_path)

    for target in ("execution-only", "task-generation-only"):
        result = run_quality_hook(
            project,
            "workflow.phase_boundary.validate",
            {"from_phase_mode": "review-and-repair", "to_phase_mode": target},
        )
        assert result.status == "blocked", target


def test_phase_boundary_allows_acceptance_to_review_repair(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "acceptance-only", "to_phase_mode": "review-and-repair"},
    )

    assert result.status == "ok"


def test_phase_boundary_blocks_acceptance_from_diagnosing_upstream(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "acceptance-only", "to_phase_mode": "planning-only"},
    )

    assert result.status == "blocked"


def test_phase_boundary_blocks_planning_to_execution_jump(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "planning-only", "to_phase_mode": "execution-only"},
    )

    assert result.status == "blocked"
    assert any("planning-only" in message for message in result.errors)
