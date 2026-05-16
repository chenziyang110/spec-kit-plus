import json
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
            "  - Reference Behavior Inventory",
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


def _write_valid_specify_semantic_artifacts(feature_dir: Path) -> None:
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n"
        "## Alignment Summary\n\n"
        "- Discovery remains in the fixed heavy lifecycle.\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n"
        "## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n"
        "## Intent Analysis Record\n\n"
        "- initial feature hypothesis\n\n"
        "## Domain Progress Ledger\n\n"
        "- goal-and-users: closed-by-existing-evidence\n\n"
        "## Question Batch Ledger\n\n"
        "- Batch 1: answered\n\n"
        "## Adversarial Review Ledger\n\n"
        "- No contradictions recorded.\n\n"
        "## Completeness Gap Register\n\n"
        "- None recorded.\n\n"
        "## Final Audit Inputs\n\n"
        "- Ready for completeness audit.\n",
        encoding="utf-8",
    )
    _write_valid_brainstorming_truth_files(feature_dir)


def _write_valid_brainstorming_truth_files(feature_dir: Path) -> None:
    brainstorming_dir = feature_dir / "brainstorming"
    brainstorming_dir.mkdir(parents=True, exist_ok=True)
    valid_unknown = (
        '{"field":"route.primary_route","question":"Which route applies?",'
        '"blocking_level":"soft","resolver":"user","latest_resolve_phase":"specify","status":"deferred"}'
    )
    (brainstorming_dir / "facts.json").write_text(
        '{"version":1,"status":"active","fields":{},"unknowns":[]}',
        encoding="utf-8",
    )
    (brainstorming_dir / "route.json").write_text(
        '{"version":1,"status":"closed","primary_route":"greenfield","matched_rules":[],"rejected_routes":[],"blocking_unknowns":[]}',
        encoding="utf-8",
    )
    (brainstorming_dir / "intent.json").write_text(
        '{"version":1,"status":"closed","goal":"Demo","non_goals":[],"success_criteria":[],"must_preserve":[],"allowed_optimization_scope":[]}',
        encoding="utf-8",
    )
    (brainstorming_dir / "complexity.json").write_text(
        '{"version":1,"status":"closed","complexity_level":"T1 Local","scope":"capability","matched_rules":[],"execution_mode":"single"}',
        encoding="utf-8",
    )
    (brainstorming_dir / "handoff-to-specify.json").write_text(
        '{"version":1,"status":"ready","facts_file":"brainstorming/facts.json",'
        '"route_file":"brainstorming/route.json","intent_file":"brainstorming/intent.json",'
        '"complexity_file":"brainstorming/complexity.json","unknowns":[' + valid_unknown + '],"compile_ready":true}',
        encoding="utf-8",
    )


def _valid_must_preserve_handoff_payload() -> str:
    return """{
      "version": 2,
      "status": "ready",
      "entry_source": "sp-discussion",
      "source_handoff": ".specify/discussions/demo/handoff-to-specify.md",
      "source_handoff_json": ".specify/discussions/demo/handoff-to-specify.json",
      "facts_file": "brainstorming/facts.json",
      "route_file": "brainstorming/route.json",
      "intent_file": "brainstorming/intent.json",
      "complexity_file": "brainstorming/complexity.json",
      "soft_unknowns": [],
      "unknowns": [],
      "compile_ready": true,
      "coverage_status": "complete",
      "planning_gate_status": "ready",
      "hard_unknown_count": 0,
      "open_conflict_count": 0,
      "must_preserve": [
        {
          "id": "MP-001",
          "type": "goal",
          "claim": "Preserve the agreed product outcome.",
          "source": "requirements.md#feature-goal",
          "downstream_requirement": "Carry into spec.md Feature Goal and plan.md Summary.",
          "blocking_level": "hard",
          "owner": "user",
          "latest_resolve_phase": "specify-compile",
          "status": "mapped",
          "deferred_to": null,
          "stop_and_reopen_condition": null,
          "superseded_by": null,
          "mapped_to": ["spec.md#Feature Goal"]
        }
      ],
      "conflicts": []
    }"""


def _write_valid_specify_workflow_state(feature_dir: Path, *, observer_status: str = "completed") -> None:
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Ask the next bounded domain question batch.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "- workflow-state.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_valid_reference_specify_workflow_state(feature_dir: Path) -> None:
    workflow_state = "\n".join(
        [
            "# Workflow State: Demo",
            "",
            "## Current Command",
            "",
            "- active_command: `sp-specify`",
            "- status: `active`",
            "",
            "## Fixed Lifecycle State",
            "",
            "- current_stage: `completeness-audit`",
            "- current_domain: `acceptance-and-completeness-gap-closure`",
            "- next_action: `Run the completeness audit against the full discovery record.`",
            "- blocker_reason: `none`",
            "- final_handoff_decision: `pending`",
            "",
            "## Allowed Artifact Writes",
            "",
            "- spec.md",
            "- alignment.md",
            "- context.md",
            "- specify-draft.md",
            "- workflow-state.md",
            "",
            "## Forbidden Actions",
            "",
            "- edit source code",
            "",
            "## Authoritative Files",
            "",
            "- spec.md",
            "- alignment.md",
            "- context.md",
            "- specify-draft.md",
            "",
            "## Next Command",
            "",
            "- `/sp.plan`",
            "",
        ]
    )
    (feature_dir / "workflow-state.md").write_text(workflow_state, encoding="utf-8")
    (feature_dir / "context.md").write_text(
        "# Context\n\n"
        "## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n"
        "## Intent Analysis Record\n\n"
        "- initial feature hypothesis\n\n"
        "## Domain Progress Ledger\n\n"
        "- goal-and-users: closed-by-existing-evidence\n\n"
        "## Question Batch Ledger\n\n"
        "- Batch 1: answered\n\n"
        "## Adversarial Review Ledger\n\n"
        "- No contradictions recorded.\n\n"
        "## Completeness Gap Register\n\n"
        "- None recorded.\n\n"
        "## Final Audit Inputs\n\n"
        "- Ready for completeness audit.\n",
        encoding="utf-8",
    )


def _write_fixed_lifecycle_specify_workflow_state(feature_dir: Path) -> None:
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Ask the next bounded domain question batch.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "- workflow-state.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_fixed_lifecycle_specify_draft(feature_dir: Path) -> None:
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n"
        "## Intent Analysis Record\n\n"
        "- initial feature hypothesis\n\n"
        "## Domain Progress Ledger\n\n"
        "- goal-and-users: in-progress\n\n"
        "## Question Batch Ledger\n\n"
        "- Batch 1: pending\n\n"
        "## Adversarial Review Ledger\n\n"
        "- No contradictions recorded yet.\n\n"
        "## Completeness Gap Register\n\n"
        "- None recorded.\n\n"
        "## Final Audit Inputs\n\n"
        "- Pending completeness audit.\n",
        encoding="utf-8",
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


def test_specify_artifact_validation_requires_brainstorming_truth_files(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    for path in (feature_dir / "brainstorming").iterdir():
        path.unlink()

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("facts.json" in message for message in result.errors)
    assert any("route.json" in message for message in result.errors)


def test_specify_artifact_validation_requires_unknown_object_shape(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "brainstorming" / "facts.json").write_text(
        '{"version":1,"status":"active","fields":{},"unknowns":[{"field":"route.primary_route"}]}',
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("facts.json unknowns[0] missing question" in message for message in result.errors)
    assert any("facts.json unknowns[0] missing status" in message for message in result.errors)


def test_specify_artifact_validation_accepts_complete_must_preserve_handoff(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        _valid_must_preserve_handoff_payload(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_specify_artifact_validation_blocks_ready_gate_with_open_conflict(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace(
        '"open_conflict_count": 0',
        '"open_conflict_count": 1',
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("planning_gate_status" in message and "open conflicts" in message for message in result.errors)


def test_specify_artifact_validation_blocks_ready_gate_with_unreported_open_conflict(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace(
        '"conflicts": []',
        '"conflicts": [{"id": "C-001", "mp_id": "MP-001", "status": "open", "resolution": "none"}]',
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("open_conflict_count" in message and "does not match" in message for message in result.errors)
    assert any("planning_gate_status" in message and "open conflicts" in message for message in result.errors)


def test_specify_artifact_validation_blocks_ready_gate_with_unreported_hard_blocking_question(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace('"type": "goal"', '"type": "blocking_question"')
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("hard_unknown_count" in message and "does not match" in message for message in result.errors)
    assert any("planning_gate_status" in message and "hard unknowns" in message for message in result.errors)


def test_specify_artifact_validation_blocks_complete_coverage_with_unmapped_active_item(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace(
        '"mapped_to": ["spec.md#Feature Goal"]',
        '"mapped_to": []',
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("MP-001" in message and "mapped_to" in message for message in result.errors)


def test_specify_artifact_validation_blocks_malformed_must_preserve_id(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace('"id": "MP-001"', '"id": "MP-ABC"')
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("MP-ABC" in message and "MP-###" in message for message in result.errors)


def test_specify_artifact_validation_blocks_dropped_item_without_user_approval(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = (
        _valid_must_preserve_handoff_payload()
        .replace('"status": "mapped"', '"status": "dropped"')
        .replace('"mapped_to": ["spec.md#Feature Goal"]', '"mapped_to": []')
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("MP-001" in message and "user_decision_source" in message for message in result.errors)
    assert any("MP-001" in message and "approved_risk_contract" in message for message in result.errors)


def test_specify_artifact_validation_blocks_resolved_item_without_resolution_evidence(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = (
        _valid_must_preserve_handoff_payload()
        .replace('"status": "mapped"', '"status": "resolved"')
        .replace('"mapped_to": ["spec.md#Feature Goal"]', '"mapped_to": []')
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(payload, encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("MP-001" in message and "resolution_evidence" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_draft_artifact_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    _write_valid_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("specify-draft.md" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_recovery_capsule_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Alignment Summary\n\n- Demo\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "specify-draft.md").write_text("# Specification Draft Ledger: Demo\n", encoding="utf-8")
    _write_valid_brainstorming_truth_files(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Intent Analysis Record" in message for message in result.errors)

def test_validate_artifacts_blocks_specify_when_fixed_lifecycle_state_fields_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Alignment Summary\n\n- Demo\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n"
        "| API | UI | reporting | medium |\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n"
        "## Intent Analysis Record\n\n"
        "- hypothesis\n\n"
        "## Domain Progress Ledger\n\n"
        "- goal-and-users: in-progress\n\n"
        "## Question Batch Ledger\n\n"
        "- Batch 1: pending\n\n"
        "## Adversarial Review Ledger\n\n"
        "- none\n\n"
        "## Completeness Gap Register\n\n"
        "- none\n\n"
        "## Final Audit Inputs\n\n"
        "- pending\n",
        encoding="utf-8",
    )
    _write_valid_brainstorming_truth_files(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("current_stage" in message for message in result.errors)
    assert any("final_handoff_decision" in message for message in result.errors)

def test_validate_artifacts_blocks_specify_when_legacy_state_fields_are_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Alignment Summary\n\n- Demo\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Ask the next bounded domain question batch.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "- workflow-state.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
                "## Legacy Resume Checklist",
                "",
                "- draft_file: `specify-draft.md`",
                "- coverage_mode: `core`",
                "- observer_status: `blocked`",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n"
        "## Intent Analysis Record\n\n"
        "- hypothesis\n\n"
        "## Domain Progress Ledger\n\n"
        "- goal-and-users: in-progress\n\n"
        "## Question Batch Ledger\n\n"
        "- Batch 1: pending\n\n"
        "## Adversarial Review Ledger\n\n"
        "- none\n\n"
        "## Completeness Gap Register\n\n"
        "- none\n\n"
        "## Final Audit Inputs\n\n"
        "- pending\n",
        encoding="utf-8",
    )
    _write_valid_brainstorming_truth_files(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("legacy sp-specify state field: coverage_mode" in message for message in result.errors)
    assert any("legacy sp-specify state field: observer_status" in message for message in result.errors)

def test_validate_artifacts_blocks_specify_when_alignment_summary_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n"
        "| auth | api | audit-log | high |\n",
        encoding="utf-8",
    )
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Ask the next bounded domain question batch.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "- workflow-state.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- specify-draft.md",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "specify-draft.md").write_text(
        "# Specification Draft Ledger: Demo\n\n"
        "## Intent Analysis Record\n\n"
        "- hypothesis\n\n"
        "## Domain Progress Ledger\n\n"
        "- goal-and-users: in-progress\n\n"
        "## Question Batch Ledger\n\n"
        "- Batch 1: pending\n\n"
        "## Adversarial Review Ledger\n\n"
        "- none\n\n"
        "## Completeness Gap Register\n\n"
        "- none\n\n"
        "## Final Audit Inputs\n\n"
        "- pending\n",
        encoding="utf-8",
    )
    _write_valid_brainstorming_truth_files(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Alignment Summary" in message for message in result.errors)


def test_validate_artifacts_blocks_reference_implementation_spec_without_fidelity_requirements(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## User Scenarios\n\nDemo scenario.\n",
        encoding="utf-8",
    )
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_reference_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_fixed_lifecycle_templates_lock_state_and_draft_contracts() -> None:
    workflow_state_template = (Path(__file__).resolve().parents[2] / "templates" / "workflow-state-template.md").read_text(
        encoding="utf-8"
    )
    specify_draft_template = (Path(__file__).resolve().parents[2] / "templates" / "specify-draft-template.md").read_text(
        encoding="utf-8"
    )

    assert "## Fixed Lifecycle State" in workflow_state_template
    assert "current_stage" in workflow_state_template
    assert "current_domain" in workflow_state_template
    assert "next_action" in workflow_state_template
    assert "blocker_reason" in workflow_state_template
    assert "final_handoff_decision" in workflow_state_template
    assert "active_profile" not in workflow_state_template
    assert "coverage_mode" not in workflow_state_template
    assert "observer_status" not in workflow_state_template

    assert "## Intent Analysis Record" in specify_draft_template
    assert "## Domain Progress Ledger" in specify_draft_template
    assert "## Question Batch Ledger" in specify_draft_template
    assert "## Adversarial Review Ledger" in specify_draft_template
    assert "## Completeness Gap Register" in specify_draft_template
    assert "## Final Audit Inputs" in specify_draft_template
    assert "## Recovery Capsule" not in specify_draft_template
    assert "## Observer Findings" not in specify_draft_template


def test_validate_artifacts_accepts_fixed_lifecycle_state_and_draft_contract(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "# Feature Specification: Demo\n\n"
        "## Fidelity Requirements\n\n"
        "### Reference Object\n\n"
        "- Existing implementation\n\n"
        "### Required Fidelity\n\n"
        "- Preserve behavior\n\n"
        "### Reference Behavior Inventory\n\n"
        "- RB-001 Preserve primary checkout workflow -> preserve\n",
        encoding="utf-8",
    )
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_fixed_lifecycle_specify_workflow_state(feature_dir)
    _write_fixed_lifecycle_specify_draft(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_validate_artifacts_requires_reference_implementation_sections_as_headings(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        """# Spec

This prose mentions ## Fidelity Requirements but not as a heading.

The text also mentions ### Reference Object and ### Required Fidelity inline.
The text also mentions ### Reference Behavior Inventory inline.
""",
        encoding="utf-8",
    )
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_reference_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_validate_artifacts_skips_reference_sections_when_profile_is_not_active(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n\n## User Scenarios\n\nDemo scenario.\n", encoding="utf-8")
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)

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

### Reference Behavior Inventory

- RB-001 Preserve request workflow -> preserve.
""",
        encoding="utf-8",
    )
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_reference_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_reference_implementation_spec_without_reference_behavior_inventory(
    tmp_path: Path,
):
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
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_reference_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Reference Behavior Inventory" in message for message in result.errors)


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


def test_validate_artifacts_blocks_triggered_consequence_handoff_without_analysis(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "close team touches running workers",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [],
                    "state_behavior_matrix": [],
                    "dependency_impact": [],
                    "recovery_and_validation": [],
                    "coverage_gaps": [],
                },
                "consequence_obligations": [],
                "stop_and_reopen_conditions": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("affected_object_map" in message for message in result.errors)
    assert any("consequence_obligations" in message for message in result.errors)


def test_validate_artifacts_blocks_plan_when_consequence_contract_is_not_designed(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n\n## Design\n\nClose the team.\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "team close has running-worker semantics",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Define close behavior for running workers",
                        "affected_objects": ["team", "worker", "task queue"],
                        "owner": "sp-plan",
                        "latest_resolve_phase": "plan",
                        "status": "open",
                        "stop_and_reopen_condition": "No drain/cancel/force policy is chosen",
                    }
                ],
                "operational_consequence_decisions": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Operational Consequence Design" in message for message in result.errors)
    assert any("CA-001" in message for message in result.errors)


def test_validate_artifacts_blocks_plan_when_nested_consequence_contract_is_not_designed(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan").mkdir()
    (feature_dir / "plan.md").write_text("# Plan\n\n## Design\n\nClose the team.\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan" / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "team close has running-worker semantics",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Define close behavior for running workers",
                        "affected_objects": ["team", "worker", "task queue"],
                        "owner": "sp-plan",
                        "latest_resolve_phase": "plan",
                        "status": "open",
                        "stop_and_reopen_condition": "No drain/cancel/force policy is chosen",
                    }
                ],
                "operational_consequence_decisions": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("plan/plan-contract.json" in message for message in result.errors)
    assert any("CA-001" in message for message in result.errors)


def test_validate_artifacts_blocks_plan_when_consequence_decision_does_not_cover_obligation(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Operational Consequence Design\n\nDecision recorded.\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "team close has running-worker semantics",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Define close behavior for running workers",
                        "affected_objects": ["team", "worker", "task queue"],
                        "owner": "sp-plan",
                        "latest_resolve_phase": "plan",
                        "status": "open",
                        "stop_and_reopen_condition": "No drain/cancel/force policy is chosen",
                    }
                ],
                "operational_consequence_decisions": [
                    {
                        "decision_id": "OCD-001",
                        "consequence_obligation_ids": ["TEMPLATE-PLACEHOLDER"],
                        "decision": "Drain workers before close completes",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("CA-001" in message for message in result.errors)
    assert any("operational_consequence_decisions" in message for message in result.errors)


def test_validate_artifacts_accepts_plan_when_decision_covers_obligation_id(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Operational Consequence Design\n\nDecision recorded.\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "team close has running-worker semantics",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [{"object": "worker", "reason": "running workers are affected"}],
                    "state_behavior_matrix": [{"state": "running", "behavior": "drain before close completes"}],
                    "dependency_impact": [{"surface": "submit-result", "impact": "late result policy must be defined"}],
                    "recovery_and_validation": [{"validation": "pytest tests/test_team_close.py -q"}],
                    "coverage_gaps": [{"gap": "none", "decision": "covered by plan decision"}],
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Define close behavior for running workers",
                        "affected_objects": ["team", "worker", "task queue"],
                        "owner": "sp-plan",
                        "latest_resolve_phase": "plan",
                        "status": "open",
                        "stop_and_reopen_condition": "No drain/cancel/force policy is chosen",
                    }
                ],
                "operational_consequence_decisions": [
                    {
                        "decision_id": "OCD-001",
                        "obligation_id": "CA-001",
                        "decision": "Drain workers before close completes",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_tasks_when_consequence_obligation_is_unmapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "handoff-to-tasks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [{"object": "worker", "reason": "running workers are affected"}],
                    "state_behavior_matrix": [{"state": "running", "behavior": "drain before close completes"}],
                    "dependency_impact": [{"surface": "submit-result", "impact": "late result policy must be defined"}],
                    "recovery_and_validation": [{"validation": "pytest tests/test_team_close.py -q"}],
                    "coverage_gaps": [{"gap": "none", "decision": "covered by task mapping"}],
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Running workers drain before close completes",
                        "affected_objects": ["worker", "team"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates drain behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 1, "status": "ready", "tasks": [{"task_id": "T001"}], "parallel_batches": [], "join_points": []}
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("CA-001" in message for message in result.errors)
    assert any("consequence" in message.lower() and "task-index.json" in message for message in result.errors)


def test_validate_artifacts_blocks_tasks_when_triggered_handoff_has_no_consequence_details(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "handoff-to-tasks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [],
                    "state_behavior_matrix": [],
                    "dependency_impact": [],
                    "recovery_and_validation": [],
                    "coverage_gaps": [],
                },
                "consequence_obligations": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("affected_object_map" in message for message in result.errors)
    assert any("consequence_obligations" in message for message in result.errors)


def test_validate_artifacts_blocks_tasks_when_plan_contract_obligation_is_unmapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Running workers drain before close completes",
                        "affected_objects": ["worker", "team"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates drain behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 1, "status": "ready", "tasks": [{"task_id": "T001"}], "parallel_batches": [], "join_points": []}
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("CA-001" in message for message in result.errors)
    assert any("task-index.json" in message for message in result.errors)


def test_validate_artifacts_blocks_tasks_when_nested_plan_contract_obligation_is_unmapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan").mkdir()
    (feature_dir / "tasks.md").write_text("- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan" / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-002",
                        "claim": "Late worker results are handled after close",
                        "affected_objects": ["worker", "task queue"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates late result behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 1, "status": "ready", "tasks": [{"task_id": "T001"}], "parallel_batches": [], "join_points": []}
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("CA-002" in message for message in result.errors)
    assert any("task-index.json" in message for message in result.errors)


def test_validate_artifacts_blocks_tasks_when_brainstorming_handoff_obligation_is_unmapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "brainstorming").mkdir()
    (feature_dir / "tasks.md").write_text("- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "brainstorming" / "handoff-to-tasks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-003",
                        "claim": "Cancel behavior is explicit",
                        "affected_objects": ["worker", "team"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates cancel behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 1, "status": "ready", "tasks": [{"task_id": "T001"}], "parallel_batches": [], "join_points": []}
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("CA-003" in message for message in result.errors)
    assert any("task-index.json" in message for message in result.errors)


def test_validate_artifacts_accepts_tasks_when_consequence_obligation_is_mapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "## Consequence Obligation Mapping\n\n"
        "| Obligation ID | Task IDs | Validation |\n"
        "| --- | --- | --- |\n"
        "| CA-001 | T001 | pytest tests/test_team_close.py -q |\n\n"
        "- [ ] T001 Implement close team drain behavior in src/team.py\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "handoff-to-tasks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [{"object": "worker", "reason": "running workers are affected"}],
                    "state_behavior_matrix": [{"state": "running", "behavior": "drain before close completes"}],
                    "dependency_impact": [{"surface": "submit-result", "impact": "late result policy must be defined"}],
                    "recovery_and_validation": [{"validation": "pytest tests/test_team_close.py -q"}],
                    "coverage_gaps": [{"gap": "none", "decision": "covered by task mapping"}],
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Running workers drain before close completes",
                        "affected_objects": ["worker", "team"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates drain behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "tasks": [
                    {
                        "task_id": "T001",
                        "consequence_obligation_ids": ["CA-001"],
                    }
                ],
                "parallel_batches": [],
                "join_points": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
