from pathlib import Path
from specify_cli.hooks.engine import run_quality_hook
from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import write_lane_record


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


def test_validate_state_accepts_legacy_fixed_lifecycle_shape_for_specify(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Fixed Lifecycle State",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "- phase_mode: `planning-only`",
                "- summary: draft specification",
                "- current_stage: `intent-analysis`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Refine scope.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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
    assert checkpoint["active_command"] == "sp-specify"
    assert checkpoint["phase_mode"] == "planning-only"
    assert checkpoint["current_stage"] == "intent-analysis"
    assert checkpoint["current_domain"] == "goal-and-users"


def test_validate_state_accepts_frontmatter_fallback_for_required_sections(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "---",
                "active_command: sp-specify",
                "status: active",
                "phase_mode: planning-only",
                "summary: draft specification",
                "current_stage: intent-analysis",
                "current_domain: goal-and-users",
                "next_action: Refine scope.",
                "blocker_reason: none",
                "final_handoff_decision: pending",
                "allowed_artifact_writes:",
                "  - spec.md",
                "  - workflow-state.md",
                "forbidden_actions:",
                "  - edit source code",
                "authoritative_files:",
                "  - spec.md",
                "next_command: /sp.plan",
                "---",
                "",
                "# Workflow State: Demo",
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
    assert checkpoint["active_command"] == "sp-specify"
    assert checkpoint["phase_mode"] == "planning-only"
    assert checkpoint["allowed_artifact_writes"] == ["spec.md", "workflow-state.md"]
    assert checkpoint["forbidden_actions"] == ["edit source code"]
    assert checkpoint["authoritative_files"] == ["spec.md"]
    assert checkpoint["next_command"] == "/sp.plan"


def test_validate_state_reports_validated_path_and_autofix_command(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "workflow-state.md"
    target.write_text(
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
    assert result.data["validated_path"] == str(target.resolve())
    assert result.data["autofix"]["available"] is True
    assert "--autofix" in result.data["autofix"]["command"]
    assert "Allowed Artifact Writes" in result.data["autofix"]["snippet"]


def test_validate_state_autofix_repairs_missing_sections(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "workflow-state.md"
    target.write_text(
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
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir), "autofix": True},
    )

    assert result.status == "repaired"
    assert result.writes["workflow_state"] == str(target.resolve())
    updated = target.read_text(encoding="utf-8")
    assert "## Allowed Artifact Writes" in updated
    assert "## Forbidden Actions" in updated
    assert "## Authoritative Files" in updated
    assert "## Next Command" in updated


def test_validate_state_reports_lane_worktree_diagnostics(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "workflow-state.md"
    target.write_text(
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
            ]
        ),
        encoding="utf-8",
    )
    write_lane_record(
        project,
        LaneRecord(
            lane_id="lane-001",
            feature_id="001-demo",
            feature_dir="specs/001-demo",
            branch_name="001-demo",
            worktree_path=".specify/lanes/worktrees/lane-001",
            last_command="specify",
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    lane_context = result.data["lane_context"]
    assert lane_context["lane_id"] == "lane-001"
    assert lane_context["worktree_path"] == ".specify/lanes/worktrees/lane-001"
    assert lane_context["worktree_state_path"].endswith(".specify/lanes/worktrees/lane-001/specs/001-demo/workflow-state.md")
