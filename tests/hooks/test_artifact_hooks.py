from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-artifact-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _valid_deep_research_artifact() -> str:
    return """# Deep Research

## Capability Feasibility Matrix

| Capability ID | Capability | Unknown Link | Evidence Needed | Proof Method | Result |
| --- | --- | --- | --- | --- | --- |
| CAP-001 | Demo capability | API behavior | Runnable proof | EVD-001 / SPK-001 | proven |

## Research Agent Findings

| Track ID | Agent / Mode | Question | Evidence IDs | Confidence | Exit State | Planning Implication |
| --- | --- | --- | --- | --- | --- | --- |
| TRK-001 | one-subagent research | Can it work? | EVD-001, SPK-001 | high | enough-to-plan | Use PH-001 |

## Evidence Quality Rubric

| Evidence ID | Supports | Source Tier | Source / Path | Reproduced Locally | Recency / Version | Confidence | Plan Impact | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVD-001 | CAP-001 / PH-001 | runnable-spike | research-spikes/demo | yes | not time-sensitive | high | constraining | Does not prove production scale |

## Synthesis Decisions

- **Recommended approach**: PH-001 -> Use the proven API path.

## Planning Handoff

- **Handoff IDs**: PH-001
- **Recommended approach**: PH-001 -> Use the proven API path; trace to CAP-001 / TRK-001 / EVD-001 / SPK-001.
- **Architecture implications**: PH-001 -> Preserve the adapter boundary.
- **Module boundaries**: PH-001 -> Keep ownership in the existing module.
- **API / library choices**: PH-001 -> Use the tested API.
- **Data flow notes**: PH-001 -> Input to adapter, output to service.
- **Demo artifacts to reference**: PH-001 -> research-spikes/demo, SPK-001.
- **Constraints `/sp.plan` must preserve**:
  - PH-001 -> Keep the adapter boundary.
- **Validation implications**: PH-001 -> Add a targeted integration check.
- **Residual risks requiring design mitigation**:
  - PH-001 -> Production scale remains unproven.
- **Decisions already proven by research**:
  - PH-001 -> API call shape works.

## Planning Traceability Index

| Handoff ID | Plan Consumer | Supported By | Evidence Quality | Required Plan Action |
| --- | --- | --- | --- | --- |
| PH-001 | architecture | CAP-001, TRK-001, EVD-001, SPK-001 | high / constraining | Preserve adapter boundary |
"""


def _not_needed_deep_research_artifact() -> str:
    return """# Deep Research: Demo capability

**Status**: Not needed

## Feasibility Decision

- **Recommendation**: Proceed to `/sp.plan`
- **Reason**: Repository evidence already proves the implementation chain, so no feasibility research or spike is needed.
- **Planning handoff readiness**: Not needed

## Planning Handoff

- **Handoff IDs**: Not needed
- **Recommended approach**: Use the existing repository implementation path during `/sp.plan`.
- **Reason**: No planning-critical capability has an unproven implementation-chain link.
- **Constraints `/sp.plan` must preserve**: Preserve the existing implementation boundary already captured in `context.md`.

## Next Command

- `/sp.plan`
"""


def _reference_implementation_workflow_state(active_profile: str = "reference-implementation") -> str:
    return "\n".join(
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
            f"- active_profile: `{active_profile}`" if active_profile else "- routing_reason: no active profile",
            "- routing_reason: Existing implementation must remain the behavioral source of truth.",
            "- confidence_level: `high`",
            "",
            "## Profile Obligations",
            "",
            "- required_sections:",
            "  - Fidelity Requirements",
            "  - Reference Object",
            "  - Required Fidelity",
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
    )


def test_validate_artifacts_blocks_when_specify_outputs_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("alignment.md" in message for message in result.errors)
    assert any("context.md" in message for message in result.errors)


def test_validate_artifacts_blocks_reference_implementation_spec_without_fidelity_requirements(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## User Scenarios\n\nDemo scenario.\n",
        encoding="utf-8",
    )
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        _reference_implementation_workflow_state(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Fidelity Requirements" in message for message in result.errors)
    assert any("Reference Object" in message for message in result.errors)
    assert any("Required Fidelity" in message for message in result.errors)


def test_validate_artifacts_requires_reference_implementation_sections_as_headings(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        """# Spec

This prose mentions ## Fidelity Requirements but not as a heading.

The text also mentions ### Reference Object and ### Required Fidelity inline.
""",
        encoding="utf-8",
    )
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        _reference_implementation_workflow_state(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("## Fidelity Requirements" in message for message in result.errors)
    assert any("### Reference Object" in message for message in result.errors)
    assert any("### Required Fidelity" in message for message in result.errors)


def test_validate_artifacts_skips_reference_sections_when_profile_is_not_active(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n\n## User Scenarios\n\nDemo scenario.\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        _reference_implementation_workflow_state(active_profile="greenfield-api"),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_reference_implementation_spec_with_fidelity_requirements(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        """# Spec

## Fidelity Requirements

### Reference Object

- Existing checkout behavior.

### Required Fidelity

- Preserve request and response behavior.
""",
        encoding="utf-8",
    )
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        _reference_implementation_workflow_state(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_tasks_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("- [ ] T001 Demo task in src/demo.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_deep_research_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(_valid_deep_research_artifact(), encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_deep_research_not_needed_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(_not_needed_deep_research_artifact(), encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_research_alias_for_deep_research_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(_not_needed_deep_research_artifact(), encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_ambiguous_deep_research_not_needed_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        "# Deep Research\n\n**Status**: Not needed\n\nNo research needed.\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Feasibility Decision" in message for message in result.errors)
    assert any("Planning Handoff" in message for message in result.errors)


def test_validate_artifacts_blocks_deep_research_without_planning_handoff_schema(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text("# Deep Research\n\nRaw notes only.\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Planning Handoff" in message for message in result.errors)
    assert any("Evidence Quality Rubric" in message for message in result.errors)
    assert any("CAP-001" in message for message in result.errors)


def test_validate_artifacts_blocks_plan_when_deep_research_handoff_is_not_consumed(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(_valid_deep_research_artifact(), encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n\n## Design\n\nUse the adapter boundary.\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Deep Research Traceability Matrix" in message for message in result.errors)
    assert any("PH-001" in message for message in result.errors)


def test_validate_artifacts_accepts_plan_consuming_deep_research_handoff(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(_valid_deep_research_artifact(), encoding="utf-8")
    (feature_dir / "plan.md").write_text(
        """# Plan

## Deep Research Traceability Matrix

| Plan Decision | Handoff ID | Capability ID | Track ID | Evidence / Spike ID | Evidence Quality | Plan Action |
| --- | --- | --- | --- | --- | --- | --- |
| Preserve adapter boundary | PH-001 | CAP-001 | TRK-001 | EVD-001, SPK-001 | high / constraining | Implement the adapter boundary in design |
""",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_plan_when_handoff_id_is_outside_traceability_matrix(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(_valid_deep_research_artifact(), encoding="utf-8")
    (feature_dir / "plan.md").write_text(
        """# Plan

This prose mentions PH-001 but does not consume it in the required matrix.

## Deep Research Traceability Matrix

| Plan Decision | Handoff ID | Capability ID | Track ID | Evidence / Spike ID | Evidence Quality | Plan Action |
| --- | --- | --- | --- | --- | --- | --- |
| Preserve adapter boundary | missing | CAP-001 | TRK-001 | EVD-001, SPK-001 | high / constraining | Implement the adapter boundary in design |
""",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("PH-001" in message for message in result.errors)


def test_validate_artifacts_ignores_non_handoff_ph_ids_when_validating_plan(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    deep_research = _valid_deep_research_artifact().replace(
        "## Planning Handoff",
        "Historical note: PH-999 was only an abandoned example and is not a handoff item.\n\n## Planning Handoff",
    )
    (feature_dir / "deep-research.md").write_text(deep_research, encoding="utf-8")
    (feature_dir / "plan.md").write_text(
        """# Plan

## Deep Research Traceability Matrix

| Plan Decision | Handoff ID | Capability ID | Track ID | Evidence / Spike ID | Evidence Quality | Plan Action |
| --- | --- | --- | --- | --- | --- | --- |
| Preserve adapter boundary | PH-001 | CAP-001 | TRK-001 | EVD-001, SPK-001 | high / constraining | Implement the adapter boundary in design |
""",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_constitution_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    memory_dir = project / ".specify" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "constitution.md").write_text("# Demo Constitution\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "constitution", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
