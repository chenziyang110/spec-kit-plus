from pathlib import Path
from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-state-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_validate_state_accepts_matching_specify_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_state_exposes_profile_contract_fields(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Scenario Profile",
                "",
                "- active_profile: `greenfield-api`",
                "- routing_reason: Requirements create a new API boundary.",
                "- confidence_level: `high`",
                "",
                "## Profile Obligations",
                "",
                "- required_sections:",
                "  - API contract",
                "- activated_gates:",
                "  - security-review",
                "- task_shaping_rules:",
                "  - Split schema and route work.",
                "- required_evidence:",
                "  - Contract test output",
                "- transition_policy: Do not enter plan until API errors are specified.",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["active_profile"] == "greenfield-api"
    assert checkpoint["routing_reason"] == "Requirements create a new API boundary."
    assert checkpoint["confidence_level"] == "high"
    assert checkpoint["required_sections"] == ["API contract"]
    assert checkpoint["activated_gates"] == ["security-review"]
    assert checkpoint["task_shaping_rules"] == ["Split schema and route work."]
    assert checkpoint["required_evidence"] == ["Contract test output"]
    assert checkpoint["transition_policy"] == "Do not enter plan until API errors are specified."


def test_validate_state_profile_obligation_lists_respect_label_boundaries(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Profile Obligations",
                "",
                "- required_sections:",
                "  - API contract",
                "    - Nested detail that must not become a sibling.",
                "- activated_gates:",
                "  - security-review",
                "- task_shaping_rules:",
                "- required_evidence:",
                "  - Contract test output",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["required_sections"] == ["API contract"]
    assert checkpoint["activated_gates"] == ["security-review"]
    assert checkpoint["task_shaping_rules"] == []


def test_validate_state_accepts_matching_deep_research_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-deep-research`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `research-only`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- deep-research.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- deep-research.md",
                "",
                "## Next Action",
                "",
                "- prove integration path",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_state_accepts_research_alias_for_deep_research_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-deep-research`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `research-only`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- deep-research.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- deep-research.md",
                "",
                "## Next Action",
                "",
                "- prove integration path",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_state_blocks_when_active_command_does_not_match(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-plan`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `design-only`",
                "- summary: demo",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("active_command" in message for message in result.errors)


def test_validate_state_blocks_when_required_phase_contract_sections_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("allowed_artifact_writes" in message for message in result.errors)
    assert any("forbidden_actions" in message for message in result.errors)
