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


def test_workflow_boundary_allows_tasks_to_implement_mainline(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "tasks", "to_command": "implement"},
    )

    assert result.status == "ok"
    assert result.data == {"from_command": "tasks", "to_command": "implement"}


def test_workflow_boundary_requires_review_between_implement_and_accept(tmp_path: Path):
    project = _create_project(tmp_path)

    implement_to_review = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "implement", "to_command": "review"},
    )
    review_to_accept = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "review", "to_command": "accept"},
    )
    skipped_review = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "implement", "to_command": "accept"},
    )

    assert implement_to_review.status == "ok"
    assert review_to_accept.status == "ok"
    assert skipped_review.status == "blocked"
    assert skipped_review.errors == [
        "workflow transition is not allowed: implement -> accept"
    ]


def test_workflow_boundary_keeps_approved_scope_diagnosis_and_fix_inside_review(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    for target in ("debug", "implement", "tasks"):
        result = run_quality_hook(
            project,
            "workflow.boundary.validate",
            {"from_command": "review", "to_command": target},
        )
        assert result.status == "blocked", target


def test_workflow_boundary_allows_review_upstream_only_for_truth_gap(tmp_path: Path):
    project = _create_project(tmp_path)

    for target in ("plan", "clarify", "specify", "design"):
        without_truth_gap = run_quality_hook(
            project,
            "workflow.boundary.validate",
            {"from_command": "review", "to_command": target},
        )
        with_truth_gap = run_quality_hook(
            project,
            "workflow.boundary.validate",
            {
                "from_command": "review",
                "to_command": target,
                "reason_category": "upstream_truth_gap",
            },
        )
        assert without_truth_gap.status == "blocked", target
        assert with_truth_gap.status == "ok", target
        for local_gap in ("implementation_gap", "traceability_gap"):
            local_route = run_quality_hook(
                project,
                "workflow.boundary.validate",
                {
                    "from_command": "review",
                    "to_command": target,
                    "reason_category": local_gap,
                },
            )
            assert local_route.status == "blocked", (target, local_gap)


def test_workflow_boundary_sends_acceptance_failures_to_review_first(tmp_path: Path):
    project = _create_project(tmp_path)

    for target in ("review", "integrate"):
        result = run_quality_hook(
            project,
            "workflow.boundary.validate",
            {"from_command": "accept", "to_command": target},
        )
        assert result.status == "ok", target

    for target in ("debug", "implement", "clarify", "specify"):
        direct = run_quality_hook(
            project,
            "workflow.boundary.validate",
            {"from_command": "accept", "to_command": target},
        )
        assert direct.status == "blocked", target


def test_workflow_boundary_keeps_tasks_to_analyze_legacy_route(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "tasks", "to_command": "analyze"},
    )

    assert result.status == "ok"
    assert result.data == {"from_command": "tasks", "to_command": "analyze"}


def test_workflow_boundary_normalizes_research_alias(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "research", "to_command": "plan"},
    )

    assert result.status == "ok"
    assert result.data == {"from_command": "deep-research", "to_command": "plan"}


def test_workflow_boundary_blocks_skipping_directly_to_implement(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "specify", "to_command": "implement"},
    )

    assert result.status == "blocked"
    assert any("implement" in message for message in result.errors)
