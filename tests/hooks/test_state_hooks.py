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


def test_validate_state_serializes_stage_state_fields(tmp_path: Path):
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
                "## Stage State",
                "",
                "- current_stage: `section-approval`",
                "- current_domain: `scope`",
                "- next_action: `auto-accept recommended section shape`",
                "- blocker_reason: `None`",
                "- approach_comparison_status: `auto-accepted-recommended`",
                "- section_approval_status: `auto-approved-recommended`",
                "- final_handoff_decision: `/sp.plan`",
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
    assert checkpoint["current_stage"] == "section-approval"
    assert checkpoint["current_domain"] == "scope"
    assert checkpoint["next_action"] == "auto-accept recommended section shape"
    assert checkpoint["approach_comparison_status"] == "auto-accepted-recommended"
    assert checkpoint["section_approval_status"] == "auto-approved-recommended"
    assert checkpoint["final_handoff_decision"] == "/sp.plan"


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


def test_validate_state_exposes_route_lock_and_reopen_fields(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State: Demo\n\n"
        "## Current Command\n\n"
        "- active_command: `sp-specify`\n"
        "- status: `active`\n\n"
        "## Phase Mode\n\n"
        "- phase_mode: `planning-only`\n"
        "- summary: `brainstorming route lock`\n\n"
        "## Fixed Lifecycle State\n\n"
        "- current_stage: `route-lock`\n"
        "- current_domain: `none`\n"
        "- next_action: `resolve blocking route unknowns`\n"
        "- blocker_reason: `missing route predicate`\n"
        "- final_handoff_decision: `undecided`\n\n"
        "## Brainstorming Locks\n\n"
        "- facts_lock: `closed`\n"
        "- route_lock: `active`\n"
        "- intent_lock: `pending`\n"
        "- complexity_lock: `pending`\n\n"
        "## Unknown Handling\n\n"
        "- hard_unknown_count: `1`\n"
        "- soft_unknown_count: `2`\n"
        "- next_unknown_to_resolve: `route.primary_route`\n\n"
        "## Reopen Contract\n\n"
        "- reopen_source: `plan`\n"
        "- reopen_target: `brainstorming`\n"
        "- reopen_reason: `route evidence changed`\n\n"
        "## Handoff Files\n\n"
        "- handoff_to_specify: `brainstorming/handoff-to-specify.json`\n"
        "- handoff_to_plan: `handoff-to-plan.json`\n"
        "- handoff_to_tasks: `handoff-to-tasks.json`\n"
        "- handoff_to_implement: `handoff-to-implement.json`\n\n"
        "## Allowed Artifact Writes\n\n"
        "- spec.md\n\n"
        "## Forbidden Actions\n\n"
        "- edit source code\n\n"
        "## Authoritative Files\n\n"
        "- spec.md\n\n"
        "## Next Action\n\n"
        "- resolve blocking route unknowns\n\n"
        "## Next Command\n\n"
        "- `/sp.plan`\n",
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["current_stage"] == "route-lock"
    assert checkpoint["blocker_reason"] == "missing route predicate"
    assert checkpoint["facts_lock"] == "closed"
    assert checkpoint["route_lock"] == "active"
    assert checkpoint["intent_lock"] == "pending"
    assert checkpoint["complexity_lock"] == "pending"
    assert checkpoint["hard_unknown_count"] == "1"
    assert checkpoint["soft_unknown_count"] == "2"
    assert checkpoint["next_unknown_to_resolve"] == "route.primary_route"
    assert checkpoint["reopen_source"] == "plan"
    assert checkpoint["reopen_target"] == "brainstorming"
    assert checkpoint["reopen_reason"] == "route evidence changed"
    assert checkpoint["handoff_to_specify"] == "brainstorming/handoff-to-specify.json"
    assert checkpoint["handoff_to_plan"] == "handoff-to-plan.json"
    assert checkpoint["handoff_to_tasks"] == "handoff-to-tasks.json"
    assert checkpoint["handoff_to_implement"] == "handoff-to-implement.json"


def test_validate_state_exposes_clean_tasks_to_implement_handoff(tmp_path: Path):
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
                "- active_command: `sp-tasks`",
                "- status: `completed`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `task-generation-only`",
                "- summary: `task package ready for implementation`",
                "",
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `task-generation`",
                "- current_domain: `none`",
                "- next_action: `hand off to implement`",
                "- blocker_reason: `None`",
                "- final_handoff_decision: `/sp.implement`",
                "",
                "## Analyze Gate",
                "",
                "- gate_status: `cleared`",
                "- gate_cycle: `0`",
                "- highest_invalid_stage: `none`",
                "- blocker_bundle:",
                "  - none",
                "- blocker_attribution_values: `none`",
                "",
                "## Reopen Contract",
                "",
                "- reopen_source: `none`",
                "- reopen_target: `none`",
                "- reopen_reason: `none`",
                "",
                "## Handoff Files",
                "",
                "- handoff_to_implement: `handoff-to-implement.json`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- tasks.md",
                "- handoff-to-implement.json",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- tasks.md",
                "- task-index.json",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["active_command"] == "sp-tasks"
    assert checkpoint["status"] == "completed"
    assert checkpoint["phase_mode"] == "task-generation-only"
    assert checkpoint["current_stage"] == "task-generation"
    assert checkpoint["current_domain"] == "none"
    assert checkpoint["next_action"] == "hand off to implement"
    assert checkpoint["blocker_reason"] == "None"
    assert checkpoint["final_handoff_decision"] == "/sp.implement"
    assert checkpoint["handoff_to_implement"] == "handoff-to-implement.json"
    assert checkpoint["next_command"] == "/sp.implement"
    assert checkpoint["gate_status"] == "cleared"
    assert checkpoint["gate_cycle"] == "0"
    assert checkpoint["highest_invalid_stage"] == "none"
    assert checkpoint["blocker_attribution_values"] == "none"
    assert checkpoint["reopen_source"] == "none"
    assert checkpoint["reopen_target"] == "none"
    assert checkpoint["reopen_reason"] == "none"


def test_validate_state_autofix_tasks_includes_task_generation_surfaces(tmp_path: Path):
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
                "- active_command: `sp-tasks`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `task-generation-only`",
                "- summary: demo",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir), "autofix": True},
    )

    assert result.status == "repaired"
    content = (feature_dir / "workflow-state.md").read_text(encoding="utf-8")
    assert "task-generation/handoffs/*.json" in content
    assert "task-generation/evidence-index.json" in content
    assert "task-generation/checkpoints.ndjson" in content
    assert "task-packets/*.json" in content
    assert "- `/sp.implement`" in content
    assert "- `/sp.analyze`" not in content


def test_validate_state_autofix_plan_includes_planning_surfaces(tmp_path: Path):
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
                "## Next Command",
                "",
                "- `/sp.tasks`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir), "autofix": True},
    )

    assert result.status == "repaired"
    content = (feature_dir / "workflow-state.md").read_text(encoding="utf-8")
    assert "planning/handoffs/*.json" in content
    assert "planning/evidence-index.json" in content
    assert "planning/checkpoints.ndjson" in content
    assert "plan-contract.json" in content


def test_validate_state_autofix_clarify_includes_clarification_surfaces(tmp_path: Path):
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
                "- active_command: `sp-clarify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
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
        {"command_name": "clarify", "feature_dir": str(feature_dir), "autofix": True},
    )

    assert result.status == "repaired"
    content = (feature_dir / "workflow-state.md").read_text(encoding="utf-8")
    assert "clarification/handoffs/*.json" in content
    assert "clarification/evidence-index.json" in content
    assert "clarification/checkpoints.ndjson" in content


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
