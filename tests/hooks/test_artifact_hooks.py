import json
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-artifact-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_minimal_task_generation_outputs(feature_dir: Path) -> None:
    handoff_path = feature_dir / "handoff-to-tasks.json"
    if not handoff_path.exists():
        handoff_path.write_text('{"version": 1, "status": "ready"}\n', encoding="utf-8")
    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.exists():
        task_index_path.write_text(
            '{"version": 1, "status": "ready", "tasks": [], "parallel_batches": [], "join_points": []}\n',
            encoding="utf-8",
        )
    task_generation_dir = feature_dir / "task-generation"
    task_generation_dir.mkdir(exist_ok=True)
    (task_generation_dir / "evidence-index.json").write_text('{"version": 1, "lanes": []}\n', encoding="utf-8")
    (task_generation_dir / "checkpoints.ndjson").write_text("", encoding="utf-8")
    (task_generation_dir / "handoffs").mkdir(exist_ok=True)
    (feature_dir / "task-packets").mkdir(exist_ok=True)


def _write_minimal_planning_outputs(feature_dir: Path) -> None:
    plan_contract_path = feature_dir / "plan-contract.json"
    if not plan_contract_path.exists() and not (feature_dir / "plan" / "plan-contract.json").exists():
        plan_contract_path.write_text('{"version": 1, "status": "ready"}\n', encoding="utf-8")
    for filename in ("research.md", "quickstart.md"):
        path = feature_dir / filename
        if not path.exists():
            path.write_text(f"# {path.stem.title()}\n", encoding="utf-8")
    planning_dir = feature_dir / "planning"
    planning_dir.mkdir(exist_ok=True)
    (planning_dir / "evidence-index.json").write_text('{"version": 1, "lanes": []}\n', encoding="utf-8")
    (planning_dir / "checkpoints.ndjson").write_text("", encoding="utf-8")
    (planning_dir / "handoffs").mkdir(exist_ok=True)


def _write_minimal_clarification_outputs(feature_dir: Path) -> None:
    for filename in ("spec.md", "alignment.md", "context.md", "references.md", "workflow-state.md"):
        path = feature_dir / filename
        if not path.exists():
            path.write_text(f"# {path.stem.title()}\n", encoding="utf-8")
    clarification_dir = feature_dir / "clarification"
    clarification_dir.mkdir(exist_ok=True)
    (clarification_dir / "evidence-index.json").write_text('{"version": 1, "lanes": []}\n', encoding="utf-8")
    (clarification_dir / "checkpoints.ndjson").write_text("", encoding="utf-8")
    (clarification_dir / "handoffs").mkdir(exist_ok=True)


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
        "## Semantic Term Decisions\n\n"
        "- Term: capability\n"
        "- Possible Meanings: config write; endpoint probe\n"
        "- Selected Meanings: config write\n"
        "- Excluded Meanings: endpoint probe\n"
        "- User Confirmation: test fixture\n\n"
        "## Upstream Intent Disposition\n\n"
        "- Signal: provider capability\n"
        "- Source: discussion-log.md\n"
        "- Disposition: in_scope\n"
        "- Artifact Location: spec.md#confirmed-scope\n"
        "- User Confirmed: yes\n"
        "- Reopen Trigger: user asks for endpoint probe\n\n"
        "## Out-Of-Scope Conflicts\n\n"
        "- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n"
        "## Planning Context\n\n"
        "- Simplified specify fixture.\n\n"
        "## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
    brainstorming_dir = feature_dir / "brainstorming"
    brainstorming_dir.mkdir(parents=True, exist_ok=True)
    (brainstorming_dir / "handoff-to-specify.json").write_text(_valid_must_preserve_handoff_payload(), encoding="utf-8")


def _write_valid_brainstorming_truth_files(feature_dir: Path) -> None:
    brainstorming_dir = feature_dir / "brainstorming"
    brainstorming_dir.mkdir(parents=True, exist_ok=True)
    compiled_from = {
        "journal": "brainstorming/journal.ndjson",
        "event_range": ["EVT-000001", "EVT-000001"],
        "key_events": ["EVT-000001"],
        "evidence_ids": [],
        "compiled_at": "2026-05-16T00:00:00Z",
    }
    journal_event = {
        "event_id": "EVT-000001",
        "schema_version": 1,
        "created_at": "2026-05-16T00:00:00Z",
        "stage": "facts-lock",
        "domain": "goal-and-users",
        "type": "checkpoint_written",
        "source": {"kind": "test-fixture", "path": "tests/hooks/test_artifact_hooks.py"},
        "payload": {
            "checkpoint_event_id": "EVT-000001",
            "current_stage": "facts-lock",
            "current_domain": "goal-and-users",
            "manifest_hash": "sha256:test-manifest",
            "workflow_state_hash": "sha256:test-workflow-state",
            "next_action": "Continue fixture validation.",
        },
        "writes": [],
        "supersedes_event_id": None,
    }
    canonical_stage_enum = [
        "intake",
        "evidence-intake",
        "facts-lock",
        "route-lock",
        "intent-lock",
        "complexity-lock",
        "domain-clarification",
        "consequence-risk",
        "specify-compile",
        "release-decision",
    ]
    stage_artifacts = {
        "intake": "workflow-state.md",
        "evidence-intake": "brainstorming/evidence-index.json",
        "facts-lock": "brainstorming/facts.json",
        "route-lock": "brainstorming/route.json",
        "intent-lock": "brainstorming/intent.json",
        "complexity-lock": "brainstorming/complexity.json",
        "domain-clarification": "brainstorming/domains.json",
        "consequence-risk": "brainstorming/handoff-to-specify.json",
        "specify-compile": "spec.md",
        "release-decision": "workflow-state.md",
    }
    stage_manifest_entries = {
        stage: {
            "artifact": stage_artifacts[stage],
            "status": "pending",
            "event_range": [],
            "artifact_hash": None,
            "last_compiled_event_id": None,
            "recoverable": False,
        }
        for stage in canonical_stage_enum
    }
    stage_manifest_entries["facts-lock"] = {
        "status": "closed",
        "artifact": "brainstorming/facts.json",
        "artifact_hash": None,
        "recoverable": True,
        "event_range": ["EVT-000001", "EVT-000001"],
        "last_compiled_event_id": "EVT-000001",
    }
    valid_unknown = (
        '{"field":"route.primary_route","question":"Which route applies?",'
        '"blocking_level":"soft","resolver":"user","latest_resolve_phase":"specify","status":"deferred"}'
    )
    (brainstorming_dir / "facts.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "active",
                "stage": "facts-lock",
                "fields": {},
                "unknowns": [],
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "route.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "closed",
                "stage": "route-lock",
                "primary_route": "greenfield",
                "matched_rules": [],
                "rejected_routes": [],
                "blocking_unknowns": [],
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "intent.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "closed",
                "stage": "intent-lock",
                "goal": "Demo",
                "non_goals": [],
                "success_criteria": [],
                "must_preserve": [],
                "allowed_optimization_scope": [],
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "complexity.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "closed",
                "stage": "complexity-lock",
                "complexity_level": "T1 Local",
                "scope": "capability",
                "matched_rules": [],
                "execution_mode": "single",
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "stage": "consequence-risk",
                "facts_file": "brainstorming/facts.json",
                "route_file": "brainstorming/route.json",
                "intent_file": "brainstorming/intent.json",
                "complexity_file": "brainstorming/complexity.json",
                "unknowns": [json.loads(valid_unknown)],
                "compile_ready": True,
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "journal.ndjson").write_text(json.dumps(journal_event) + "\n", encoding="utf-8")
    (brainstorming_dir / "stage-manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "active",
                "canonical_stage_enum": canonical_stage_enum,
                "journal": {
                    "path": "brainstorming/journal.ndjson",
                    "last_event_id": "EVT-000001",
                    "last_checkpoint_id": "EVT-000001",
                },
                "stages": stage_manifest_entries,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "domains.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "active",
                "stage": "domain-clarification",
                "domains": {},
                "questions": [],
                "reopens": [],
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "evidence-index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "active",
                "stage": "evidence-intake",
                "evidence": [],
                "accepted_use": [],
                "compiled_from": compiled_from,
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "evidence").mkdir(exist_ok=True)


def _valid_must_preserve_handoff_payload() -> str:
    return """{
      "version": 2,
      "status": "ready",
      "entry_source": "sp-discussion",
      "source_handoff": ".specify/discussions/demo/handoff-to-specify.md",
      "source_handoff_json": ".specify/discussions/demo/handoff-to-specify.json",
      "soft_unknowns": [],
      "unknowns": [],
      "compile_ready": true,
      "coverage_status": "complete",
      "planning_gate_status": "ready",
      "source_files_read": [
        "discussion-log.md",
        "requirements.md",
        "open-questions.md"
      ],
      "source_signal_disposition": [
        {
          "signal": "provider capability",
          "source": "discussion-log.md",
          "disposition": "in_scope",
          "artifact_location": "spec.md#confirmed-scope",
          "user_confirmed": true,
          "reopen_trigger": "user asks for endpoint probe"
        }
      ],
      "source_evidence": [
        {
          "source_type": "user_confirmation",
          "evidence_status": "proven",
          "source": "requirements.md#feature-goal",
          "claim": "The user confirmed the product outcome to preserve."
        }
      ],
      "stage": "consequence-risk",
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
                "## Stage State",
                "",
                "- current_stage: `artifact-review`",
                "- current_domain: `scope`",
                "- next_action: `Ask the user to review the written artifacts.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `/sp.plan`",
                "",
                "## Review State",
                "",
                "- last_user_reviewed_artifact_state: `requested`",
                "- source_files_read: `discussion source files read`",
                "- source_signal_disposition_status: `complete`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- alignment.md",
                "- context.md",
                "- workflow-state.md",
                "- checklists/requirements.md",
                "- brainstorming/handoff-to-specify.json",
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
                "- workflow-state.md",
                "- brainstorming/handoff-to-specify.json",
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
    _write_valid_specify_workflow_state(feature_dir)
    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state = workflow_state_path.read_text(encoding="utf-8")
    workflow_state = workflow_state.replace(
        "## Next Command\n\n- `/sp.plan`\n",
        "## Scenario Profile\n\n"
        "- active_profile: `reference-implementation`\n"
        "- routing_reason: Existing implementation must remain the behavioral source of truth.\n\n"
        "## Next Command\n\n"
        "- `/sp.plan`\n",
    )
    workflow_state_path.write_text(workflow_state, encoding="utf-8")


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
                "## Lossless Resume State",
                "",
                "- journal_file: `brainstorming/journal.ndjson`",
                "- stage_manifest: `brainstorming/stage-manifest.json`",
                "- last_event_id: `EVT-000001`",
                "- last_checkpoint_id: `EVT-000001`",
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


def _write_valid_legacy_specify_package(feature_dir: Path) -> None:
    if not (feature_dir / "spec.md").exists():
        (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Alignment Summary\n\n- Legacy specify package fixture.\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Change Propagation Matrix\n\n"
        "| Change Surface | Direct Consumers | Indirect Consumers | Risk |\n"
        "| --- | --- | --- | --- |\n"
        "| legacy specify | plan | implementation | medium |\n",
        encoding="utf-8",
    )
    _write_fixed_lifecycle_specify_workflow_state(feature_dir)
    _write_fixed_lifecycle_specify_draft(feature_dir)
    _write_valid_brainstorming_truth_files(feature_dir)


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


def test_specify_artifact_validation_requires_compatibility_handoff(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "brainstorming" / "handoff-to-specify.json").unlink()

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("brainstorming/handoff-to-specify.json" in message for message in result.errors)


def test_specify_artifact_validation_requires_source_signal_disposition(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_files_read"] = []
    payload["source_signal_disposition"] = []
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(json.dumps(payload), encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("source_files_read is required" in message for message in result.errors)
    assert any("source_signal_disposition is required" in message for message in result.errors)


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


def test_specify_artifact_validation_accepts_structured_source_evidence(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_evidence"] = [
        {
            "source_type": "project_cognition_route",
            "evidence_status": "inferred",
            "source": "brainstorming/route.json",
            "claim": "Route identifies the likely implementation target.",
            "project_cognition_route": ["brainstorming/route.json"],
            "notes": "Navigation evidence only.",
        },
        {
            "source_type": "live_code_evidence",
            "evidence_status": "proven",
            "source": "src/specify_cli/hooks/artifact_validation.py",
            "claim": "Live repository evidence proves current validator behavior.",
            "live_code_evidence": ["src/specify_cli/hooks/artifact_validation.py"],
            "needs_refresh": False,
        },
    ]
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_specify_artifact_validation_blocks_invalid_structured_source_evidence(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_evidence"] = [
        {
            "source_type": "memory",
            "evidence_status": "verified",
            "source": " ",
            "claim": "",
            "project_cognition_route": ["brainstorming/route.json", ""],
            "live_code_evidence": "src/specify_cli/hooks/artifact_validation.py",
            "needs_refresh": "false",
        },
        "legacy source note",
    ]
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("source_evidence[0].source is required" in message for message in result.errors)
    assert any("source_evidence[0].claim is required" in message for message in result.errors)
    assert any("source_evidence[0].source_type is invalid" in message for message in result.errors)
    assert any("source_evidence[0].evidence_status is invalid" in message for message in result.errors)
    assert any(
        "source_evidence[0].project_cognition_route must be an array of non-empty strings" in message
        for message in result.errors
    )
    assert any(
        "source_evidence[0].live_code_evidence must be an array of non-empty strings" in message
        for message in result.errors
    )
    assert any("source_evidence[0].needs_refresh must be a boolean" in message for message in result.errors)
    assert any("source_evidence[1] must be an object" in message for message in result.errors)


def test_specify_artifact_validation_blocks_ready_handoff_without_source_evidence(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_evidence"] = []
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("source_evidence must include at least one entry" in message for message in result.errors)


def test_specify_artifact_validation_blocks_non_string_source_evidence_claim(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_evidence"] = [
        {
            "source_type": "live_code_evidence",
            "evidence_status": "proven",
            "source": ["src/specify_cli/hooks/artifact_validation.py"],
            "claim": 123,
        }
    ]
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("source_evidence[0].source must be a non-empty string" in message for message in result.errors)
    assert any("source_evidence[0].claim must be a non-empty string" in message for message in result.errors)


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


def test_validate_artifacts_blocks_specify_when_handoff_artifact_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n"
        "## Semantic Term Decisions\n\n- None\n\n"
        "## Upstream Intent Disposition\n\n- None\n\n"
        "## Out-Of-Scope Conflicts\n\n- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text("# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8")
    _write_valid_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("brainstorming/handoff-to-specify.json" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_semantic_alignment_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Upstream Intent Disposition\n\n- Demo\n\n## Out-Of-Scope Conflicts\n\n- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text("# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8")
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "brainstorming").mkdir(exist_ok=True)
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        _valid_must_preserve_handoff_payload(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Semantic Term Decisions" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_stage_state_fields_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n"
        "## Semantic Term Decisions\n\n- None\n\n"
        "## Upstream Intent Disposition\n\n- None\n\n"
        "## Out-Of-Scope Conflicts\n\n- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text("# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Stage State\n\n- blocker_reason: `none`\n\n## Review State\n\n"
        "- last_user_reviewed_artifact_state: `requested`\n"
        "- source_files_read: `discussion source files read`\n"
        "- source_signal_disposition_status: `complete`\n",
        encoding="utf-8",
    )
    (feature_dir / "brainstorming").mkdir(exist_ok=True)
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        _valid_must_preserve_handoff_payload(),
        encoding="utf-8",
    )

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
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state_path.write_text(
        workflow_state_path.read_text(encoding="utf-8")
        + "\n## Legacy Resume Checklist\n\n"
        "- draft_file: `specify-draft.md`\n"
        "- coverage_mode: `core`\n"
        "- observer_status: `blocked`\n",
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("legacy sp-specify state field: coverage_mode" in message for message in result.errors)
    assert any("legacy sp-specify state field: observer_status" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_upstream_intent_disposition_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Semantic Term Decisions\n\n- None\n\n## Out-Of-Scope Conflicts\n\n- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text("# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8")
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "brainstorming").mkdir(exist_ok=True)
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        _valid_must_preserve_handoff_payload(),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Upstream Intent Disposition" in message for message in result.errors)


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

    assert result.status == "blocked"
    assert any("Fidelity Requirements" in message for message in result.errors)


def test_workflow_state_template_records_simplified_specify_review_contract() -> None:
    workflow_state_template = (Path(__file__).resolve().parents[2] / "templates" / "workflow-state-template.md").read_text(
        encoding="utf-8"
    )

    assert "## Stage State" in workflow_state_template
    assert "## Review State" in workflow_state_template
    assert "current_stage" in workflow_state_template
    assert "context-intake" in workflow_state_template
    assert "artifact-review" in workflow_state_template
    assert "user-review" in workflow_state_template
    assert "last_user_reviewed_artifact_state" in workflow_state_template
    assert "source_files_read" in workflow_state_template
    assert "source_signal_disposition_status" in workflow_state_template
    assert "next_action" in workflow_state_template
    assert "blocker_reason" in workflow_state_template
    assert "final_handoff_decision" in workflow_state_template
    assert "## Fixed Lifecycle State" not in workflow_state_template
    assert "active_profile" not in workflow_state_template
    assert "coverage_mode" not in workflow_state_template
    assert "observer_status" not in workflow_state_template


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
    _write_valid_legacy_specify_package(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_validate_artifacts_blocks_specify_when_lossless_journal_is_missing(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    (feature_dir / "brainstorming" / "journal.ndjson").unlink()

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("brainstorming/journal.ndjson" in message for message in result.errors)


def test_validate_artifacts_warns_for_legacy_specify_package_without_lossless_files(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    for relative in (
        "journal.ndjson",
        "stage-manifest.json",
        "domains.json",
        "evidence-index.json",
    ):
        path = feature_dir / "brainstorming" / relative
        if path.exists():
            path.unlink()
    evidence_dir = feature_dir / "brainstorming" / "evidence"
    if evidence_dir.exists():
        evidence_dir.rmdir()
    legacy_marker = feature_dir / "brainstorming" / "legacy-state.json"
    legacy_marker.write_text('{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert any("legacy" in message.lower() and "lossless" in message.lower() for message in result.warnings)


def test_validate_artifacts_blocks_legacy_specify_package_when_non_lossless_artifact_is_missing(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    (feature_dir / "spec.md").unlink()
    for relative in (
        "journal.ndjson",
        "stage-manifest.json",
        "domains.json",
        "evidence-index.json",
    ):
        path = feature_dir / "brainstorming" / relative
        if path.exists():
            path.unlink()
    evidence_dir = feature_dir / "brainstorming" / "evidence"
    if evidence_dir.exists():
        evidence_dir.rmdir()
    legacy_marker = feature_dir / "brainstorming" / "legacy-state.json"
    legacy_marker.write_text('{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("missing required artifact: spec.md" in message for message in result.errors)


def test_validate_artifacts_blocks_legacy_specify_package_when_existing_artifact_is_invalid(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    for relative in (
        "journal.ndjson",
        "stage-manifest.json",
        "domains.json",
        "evidence-index.json",
    ):
        path = feature_dir / "brainstorming" / relative
        if path.exists():
            path.unlink()
    evidence_dir = feature_dir / "brainstorming" / "evidence"
    if evidence_dir.exists():
        evidence_dir.rmdir()
    legacy_marker = feature_dir / "brainstorming" / "legacy-state.json"
    legacy_marker.write_text('{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("alignment.md" in message and "Alignment Summary" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_checkpoint_pointer_is_not_in_journal(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["journal"]["last_checkpoint_id"] = "EVT-999999"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("last_checkpoint_id" in message and "EVT-999999" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_workflow_checkpoint_is_not_checkpoint_event(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    events.append(
        {
            "event_id": "EVT-000002",
            "schema_version": 1,
            "created_at": "2026-05-16T00:01:00Z",
            "stage": "facts-lock",
            "type": "user_input_captured",
            "source": {"kind": "test-fixture"},
            "payload": {
                "raw_excerpt": "demo",
                "content_hash": "sha256:demo",
                "input_role": "user",
            },
            "writes": [],
            "supersedes_event_id": None,
        }
    )
    journal_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state_path.write_text(
        workflow_state_path.read_text(encoding="utf-8").replace(
            "- last_checkpoint_id: `EVT-000001`",
            "- last_checkpoint_id: `EVT-000002`",
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("workflow-state.md" in message and "last_checkpoint_id" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_lossless_resume_state_field_is_missing(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state_path.write_text(
        workflow_state_path.read_text(encoding="utf-8").replace("- last_event_id: `EVT-000001`\n", ""),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Lossless Resume State last_event_id" in message and "required" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_journal_event_type_is_unknown(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    event = json.loads(journal_path.read_text(encoding="utf-8").strip())
    event["type"] = "made_up_event"
    journal_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("unknown event type" in message and "made_up_event" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_journal_schema_version_is_boolean(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    event = json.loads(journal_path.read_text(encoding="utf-8").strip())
    event["schema_version"] = True
    journal_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("schema_version" in message and "integer" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_checkpoint_payload_is_incomplete(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    event = json.loads(journal_path.read_text(encoding="utf-8").strip())
    event["payload"].pop("manifest_hash")
    event["payload"]["checkpoint_event_id"] = "EVT-999999"
    journal_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("checkpoint_written" in message and "manifest_hash" in message for message in result.errors)
    assert any("checkpoint_event_id" in message and "event_id" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_stage_artifact_event_references_unknown_event(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    events.append(
        {
            "event_id": "EVT-000002",
            "schema_version": 1,
            "created_at": "2026-05-16T00:01:00Z",
            "stage": "facts-lock",
            "type": "stage_artifact_compiled",
            "source": {"kind": "test-fixture"},
            "payload": {
                "artifact_path": "brainstorming/facts.json",
                "stage": "facts-lock",
                "input_event_range": ["EVT-000001", "EVT-999999"],
                "key_event_ids": ["EVT-999998"],
                "evidence_ids": [],
                "output_hash": "sha256:facts",
            },
            "writes": ["brainstorming/facts.json"],
            "supersedes_event_id": None,
        }
    )
    journal_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("payload.input_event_range" in message and "EVT-999999" in message for message in result.errors)
    assert any("payload.key_event_ids" in message and "EVT-999998" in message for message in result.errors)


def test_validate_artifacts_accepts_decision_events_with_evidence_ids_without_basis(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_payloads = [
        (
            "decision_locked",
            {
                "decision_id": "DEC-001",
                "locked_value": "Keep fixed lifecycle state.",
                "evidence_ids": ["EVD-001"],
            },
        ),
        (
            "route_selected",
            {
                "route_id": "ROUTE-001",
                "selected_route": "greenfield",
                "evidence_ids": ["EVD-001"],
            },
        ),
        (
            "complexity_selected",
            {
                "complexity_id": "CPLX-001",
                "selected_complexity": "T1 Local",
                "evidence_ids": ["EVD-001"],
            },
        ),
    ]
    for index, (event_type, payload) in enumerate(event_payloads, start=2):
        events.append(
            {
                "event_id": f"EVT-{index:06d}",
                "schema_version": 1,
                "created_at": f"2026-05-16T00:0{index}:00Z",
                "stage": "facts-lock",
                "type": event_type,
                "source": {"kind": "test-fixture"},
                "payload": payload,
                "writes": [],
                "supersedes_event_id": None,
            }
        )
    journal_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_specify_when_compiled_from_references_unknown_event(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    facts_path = feature_dir / "brainstorming" / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["compiled_from"]["key_events"] = ["EVT-999998"]
    facts["compiled_from"]["event_range"] = ["EVT-000001", "EVT-999999"]
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("compiled_from.key_events" in message and "EVT-999998" in message for message in result.errors)
    assert any("compiled_from.event_range" in message and "EVT-999999" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_manifest_stage_references_unknown_event(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stages"]["facts-lock"]["event_range"] = ["EVT-000001", "EVT-999999"]
    manifest["stages"]["facts-lock"]["last_compiled_event_id"] = "EVT-999998"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("stages.facts-lock.event_range" in message and "EVT-999999" in message for message in result.errors)
    assert any(
        "stages.facts-lock.last_compiled_event_id" in message and "EVT-999998" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_manifest_stage_source_map_keys_are_missing(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stages"]["facts-lock"].pop("event_range")
    manifest["stages"]["facts-lock"].pop("last_compiled_event_id")
    manifest["stages"]["facts-lock"].pop("artifact_hash")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("stages.facts-lock.event_range" in message and "required" in message for message in result.errors)
    assert any(
        "stages.facts-lock.last_compiled_event_id" in message and "required" in message
        for message in result.errors
    )
    assert any("stages.facts-lock.artifact_hash" in message and "required" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_stage_enum_drifts(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stages"]["question-batch"] = manifest["stages"].pop("facts-lock")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("canonical stage" in message.lower() or "question-batch" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_manifest_stage_keys_are_incomplete(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stages"].pop("release-decision")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("stages missing" in message.lower() and "release-decision" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_manifest_stage_artifact_path_drifts(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stages"]["facts-lock"]["artifact"] = "brainstorming/route.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "facts-lock" in message
        and "artifact" in message
        and "brainstorming/facts.json" in message
        and "brainstorming/route.json" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_canonical_stage_enum_is_missing(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("canonical_stage_enum")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("canonical_stage_enum" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_canonical_stage_enum_is_not_a_list(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    manifest_path = feature_dir / "brainstorming" / "stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["canonical_stage_enum"] = "facts-lock"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("canonical_stage_enum" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_stage_artifact_uses_wrong_stage(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    facts_path = feature_dir / "brainstorming" / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["stage"] = "route-lock"
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "brainstorming/facts.json" in message
        and "stage" in message
        and "facts-lock" in message
        and "route-lock" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_handoff_artifact_uses_compile_stage(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    handoff_path = feature_dir / "brainstorming" / "handoff-to-specify.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["stage"] = "specify-compile"
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "brainstorming/handoff-to-specify.json" in message
        and "stage" in message
        and "consequence-risk" in message
        and "specify-compile" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_closed_stage_lacks_compiled_from(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)
    facts_path = feature_dir / "brainstorming" / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts.pop("compiled_from")
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("brainstorming/facts.json" in message and "compiled_from" in message for message in result.errors)


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
    _write_minimal_task_generation_outputs(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_tasks_without_task_generation_evidence_outputs(tmp_path: Path):
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

    assert result.status == "blocked"
    assert any("handoff-to-tasks.json" in message for message in result.errors)
    assert any("task-generation/evidence-index.json" in message for message in result.errors)
    assert any("task-generation/handoffs" in message for message in result.errors)


def test_validate_artifacts_accepts_clarify_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_minimal_clarification_outputs(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "clarify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_plan_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    _write_minimal_planning_outputs(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_plan_without_planning_evidence_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (feature_dir / "quickstart.md").write_text("# Quickstart\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan-contract.json").write_text('{"version": 1, "status": "ready"}\n', encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("planning/evidence-index.json" in message for message in result.errors)
    assert any("planning/checkpoints.ndjson" in message for message in result.errors)
    assert any("planning/handoffs" in message for message in result.errors)


def test_validate_artifacts_accepts_plan_with_nested_plan_contract(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan").mkdir()
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    _write_minimal_planning_outputs(feature_dir)
    (feature_dir / "plan-contract.json").unlink()
    (feature_dir / "plan" / "plan-contract.json").write_text('{"version": 1, "status": "ready"}\n', encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_clarify_without_clarification_evidence_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("spec.md", "alignment.md", "context.md", "references.md", "workflow-state.md"):
        (feature_dir / filename).write_text(f"# {filename}\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "clarify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("clarification/evidence-index.json" in message for message in result.errors)
    assert any("clarification/checkpoints.ndjson" in message for message in result.errors)
    assert any("clarification/handoffs" in message for message in result.errors)


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
    _write_minimal_planning_outputs(feature_dir)

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
    _write_minimal_planning_outputs(feature_dir)

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
    _write_minimal_planning_outputs(feature_dir)

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
    _write_minimal_planning_outputs(feature_dir)

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
    _write_minimal_planning_outputs(feature_dir)
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
    _write_minimal_planning_outputs(feature_dir)
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
    _write_minimal_planning_outputs(feature_dir)
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
    _write_minimal_planning_outputs(feature_dir)
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
    _write_minimal_task_generation_outputs(feature_dir)

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
    _write_minimal_task_generation_outputs(feature_dir)

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
    _write_minimal_task_generation_outputs(feature_dir)

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
    _write_minimal_task_generation_outputs(feature_dir)

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
    _write_minimal_task_generation_outputs(feature_dir)

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
    _write_minimal_task_generation_outputs(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
