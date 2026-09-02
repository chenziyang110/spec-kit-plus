import hashlib
import json
from pathlib import Path

import pytest

from specify_cli.hooks import artifact_validation
from specify_cli.hooks.engine import run_quality_hook
from specify_cli.hooks.artifact_validation import (
    _ui_contract_valid_component_adoption,
    _validate_spec_contract_artifacts,
    _ui_contract_valid_usability,
    _validate_plan_human_acceptance_contract,
    _validate_plan_ui_contract,
    _validate_task_lifecycle_records,
    _validate_tasks_human_acceptance_contract,
    _validate_tasks_ui_contract,
    _validate_ui_handoff_binding,
)
from specify_cli.workflow_runtime import WorkflowRuntimeError


COMPARISON_TOLERANCE = {
    "structure": "exact",
    "content": "exact",
    "tokens": "exact",
    "geometry": {"unit": "px", "max_delta": 2},
    "color": {"method": "delta-e-2000", "max_delta": 2},
    "text_wrap": "exact",
    "motion": {"unit": "ms", "max_delta": 16},
    "platform_variance": "approved-deviation-only",
}


@pytest.mark.parametrize(
    "patch",
    [
        {"resource_id": ""},
        {"action": "replace"},
        {"package": None},
        {"version": ""},
        {"source_ref": " "},
        {"component_refs": []},
        {"permission_gate": "later"},
        {"permission_status": "pending"},
        {"action": "add", "permission_gate": "not-required"},
        {"permission_gate": "not-required", "permission_status": "not-authorized"},
    ],
)
def test_ui_artifact_component_adoption_rejects_incomplete_or_unauthorized_rows(
    patch: dict[str, object],
) -> None:
    row = {
        "resource_id": "material-ui",
        "action": "reuse",
        "package": "@mui/material",
        "version": "^7.0.0",
        "license": "MIT",
        "source_ref": "package.json#/dependencies/@mui/material",
        "component_refs": ["@mui/material/TextField"],
        "reason_codes": ["installed"],
        "selection_basis_refs": ["package.json"],
        "permission_gate": "not-required",
        "permission_status": "authorized",
        **patch,
    }
    assert not _ui_contract_valid_component_adoption(row)


def test_ui_artifact_component_adoption_accepts_complete_reuse_row() -> None:
    assert _ui_contract_valid_component_adoption(
        {
            "resource_id": "material-ui",
            "action": "reuse",
            "package": "@mui/material",
            "version": "^7.0.0",
            "license": "MIT",
            "source_ref": "package.json#/dependencies/@mui/material",
            "component_refs": ["@mui/material/TextField"],
            "reason_codes": ["installed"],
            "selection_basis_refs": ["package.json"],
            "permission_gate": "not-required",
            "permission_status": "authorized",
        }
    )


@pytest.mark.parametrize(
    "budgets",
    [
        [],
        {"inp_ms": 200},
        {
            "inp_ms": True,
            "long_task_ms": 50,
            "cls": 0.1,
            "animation_dropped_frame_pct": 5,
            "bundle_delta_kb": 30,
        },
    ],
)
def test_ui_artifact_usability_rejects_invalid_smoothness_budgets(
    budgets: object,
) -> None:
    assert not _ui_contract_valid_usability(
        {
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["save settings"],
            "success_criteria": ["preserve context"],
            "human_review_required": True,
            "performance_budgets": budgets,
        }
    )


def test_ui_artifact_usability_accepts_complete_smoothness_budgets() -> None:
    assert _ui_contract_valid_usability(
        {
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["save settings"],
            "success_criteria": ["preserve context"],
            "human_review_required": True,
            "performance_budgets": {
                "inp_ms": 200,
                "long_task_ms": 50,
                "cls": 0.1,
                "animation_dropped_frame_pct": 5,
                "bundle_delta_kb": 30,
            },
        }
    )


def _interaction_contract(
    row_id: str = "INT-001", input_method: str = "mouse"
) -> dict[str, object]:
    return {
        "id": row_id,
        "surface": "settings form",
        "input": input_method,
        "trigger": "activate Save through the documented input",
        "event_sequence": "Resolve input start, movement or key state, and release as one activation.",
        "immediate_feedback": "Show pressed or focused feedback before completion.",
        "focus_behavior": "Preserve visible focus, selection, and the invoking control.",
        "repeat_behavior": "Prevent repeated single-submit activation while allowing documented repeat.",
        "cancellation_behavior": "Cancel at the input boundary and restore the last committed state.",
        "pending_behavior": "Block conflicting activation, prevent duplicates, and expose safe cancel or retry.",
        "decision_ids": ["DS-INT-001"],
    }


def _editing_contract(row_id: str = "EDIT-001") -> dict[str, object]:
    return {
        "id": row_id,
        "surface": "settings form",
        "input_methods": ["keyboard", "IME", "paste", "autofill"],
        "composition_behavior": "Do not validate or submit while IME composition is active.",
        "paste_autofill_behavior": "Accept paste and autofill, then normalize once without clearing the value.",
        "selection_caret_behavior": "Preserve caret and selection across validation and responsive reflow.",
        "formatting_behavior": "Apply display formatting without changing the underlying editable value.",
        "validation_timing": "Validate syntax after composition ends and remote rules on submit.",
        "validation_feedback": "Associate an inline message and summary link with the invalid field.",
        "dirty_state_behavior": "Expose unsaved state and warn before destructive navigation.",
        "persistence_behavior": "Keep unsaved values through retry and restore the last confirmed value on reload.",
        "undo_redo_behavior": "Keep native undo and redo history across formatting and feedback.",
        "conflict_behavior": "Show local and remote values and require an explicit conflict choice.",
        "read_only_disabled_behavior": "Keep read-only values selectable and explain unavailable disabled controls.",
        "submission_behavior": "Prevent duplicate submission, preserve focus, and announce one final result.",
        "decision_ids": ["DS-INT-001"],
    }


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-artifact-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _publish_runtime_not_needed_deep_research(
    project: Path, feature_dir: Path
) -> dict[str, object]:
    proof_path = project / "docs" / "deep-research-proof.txt"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(
        "The existing adapter already covers CAP-001.\n", encoding="utf-8"
    )
    published = artifact_validation.run_specify_runtime(
        [
            "deep-research",
            "not-needed",
            "--feature-dir",
            feature_dir.relative_to(project).as_posix(),
            "--leader-id",
            "leader-1",
            "--input-json",
            json.dumps(
                {
                    "capability_dispositions": [
                        {
                            "capability_ref": "CAP-001",
                            "reason": "The repository proof closes the feasibility question.",
                            "evidence_refs": ["docs/deep-research-proof.txt"],
                        }
                    ]
                }
            ),
            "--format",
            "json",
        ],
        cwd=project,
    )
    assert published["status"] == "ok"
    data = published.get("data")
    assert isinstance(data, dict)
    return data


def _write_runtime_deep_research_spec(feature_dir: Path) -> None:
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "planning-ready",
                "target_need": "Use the existing adapter when it is proven sufficient.",
                "scope": {
                    "in": ["Preserve adapter behavior"],
                    "out": [],
                    "deferred": [],
                },
                "acceptance_criteria": ["The adapter behavior remains verifiable."],
                "feasibility_gate": {
                    "decision": "required",
                    "capability_refs": ["CAP-001"],
                    "reason_refs": ["spec-contract.json#/scope/in/0"],
                },
                "entrypoint_outcome_contract": {
                    "triggered": False,
                    "stand_down_reason": "No entrypoint behavior changes.",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


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
    (task_generation_dir / "evidence-index.json").write_text(
        '{"version": 1, "lanes": []}\n', encoding="utf-8"
    )
    (task_generation_dir / "checkpoints.ndjson").write_text("", encoding="utf-8")
    (task_generation_dir / "handoffs").mkdir(exist_ok=True)
    (feature_dir / "task-packets").mkdir(exist_ok=True)


def _write_minimal_planning_outputs(feature_dir: Path) -> None:
    plan_contract_path = feature_dir / "plan-contract.json"
    if (
        not plan_contract_path.exists()
        and not (feature_dir / "plan" / "plan-contract.json").exists()
    ):
        plan_contract_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "status": "ready",
                    "test_design_gate": _unselected_test_design_gate(),
                }
            )
            + "\n",
            encoding="utf-8",
        )
    for filename in ("research.md", "quickstart.md"):
        path = feature_dir / filename
        if not path.exists():
            path.write_text(f"# {path.stem.title()}\n", encoding="utf-8")
    planning_dir = feature_dir / "planning"
    planning_dir.mkdir(exist_ok=True)
    (planning_dir / "evidence-index.json").write_text(
        '{"version": 1, "lanes": []}\n', encoding="utf-8"
    )
    (planning_dir / "checkpoints.ndjson").write_text("", encoding="utf-8")
    (planning_dir / "handoffs").mkdir(exist_ok=True)


def _unselected_test_design_gate() -> dict[str, object]:
    return {
        "decision": "not_selected",
        "reason_refs": ["fixture:no-test-design-selected"],
        "projection_binding": {
            "publication_ref": None,
            "publication_sha256": None,
            "projection_ref": None,
            "projection_sha256": None,
            "source_fingerprint": None,
            "state_revision": None,
        },
    }


def _write_minimal_acceptance_denominator(
    feature_dir: Path, *, include_tasks: bool = False
) -> None:
    spec_path = feature_dir / "spec-contract.json"
    if spec_path.is_file():
        spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    else:
        spec_payload = {
            "version": 2,
            "status": "ready",
            "acceptance_criteria": ["A human can verify the demo behavior."],
        }
    criteria = spec_payload.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        criteria = ["A human can verify the demo behavior."]
        spec_payload["acceptance_criteria"] = criteria
    scope = spec_payload.get("scope")
    if not isinstance(scope, dict):
        scope = {"in": [], "out": [], "deferred": []}
        spec_payload["scope"] = scope
    scope_in = scope.get("in")
    if not isinstance(scope_in, list):
        scope_in = []
        scope["in"] = scope_in
    capability_operations = spec_payload.get("capability_operations")
    if not isinstance(capability_operations, (list, dict)):
        capability_operations = []
        spec_payload["capability_operations"] = capability_operations
    requirement_refs = [
        f"spec-contract.json#/scope/in/{index}" for index in range(len(scope_in))
    ]
    if isinstance(capability_operations, list):
        requirement_refs.extend(
            f"spec-contract.json#/capability_operations/{index}"
            for index in range(len(capability_operations))
        )
    else:
        requirement_refs.extend(
            "spec-contract.json#/capability_operations/"
            + str(key).replace("~", "~0").replace("/", "~1")
            for key in capability_operations
        )
    if not requirement_refs:
        scope_in.extend(
            f"Fixture requirement {index + 1}" for index in range(len(criteria))
        )
        requirement_refs = [
            f"spec-contract.json#/scope/in/{index}" for index in range(len(scope_in))
        ]
    while len(criteria) < len(requirement_refs):
        criteria.append(f"Fixture requirement {len(criteria) + 1} is verifiable.")
    spec_payload["acceptance_coverage"] = [
        {
            "requirement_ref": requirement_refs[min(index, len(requirement_refs) - 1)],
            "acceptance_ref": f"spec-contract.json#/acceptance_criteria/{index}",
        }
        for index in range(len(criteria))
    ]
    spec_payload.setdefault(
        "entrypoint_outcome_contract",
        {
            "triggered": False,
            "stand_down_reason": (
                "The test fixture changes no entrypoint, reused operation, or "
                "consumer owner."
            ),
        },
    )
    spec_path.write_text(json.dumps(spec_payload), encoding="utf-8")

    plan_path = feature_dir / "plan-contract.json"
    nested_plan_path = feature_dir / "plan" / "plan-contract.json"
    if not plan_path.is_file() and nested_plan_path.is_file():
        plan_path = nested_plan_path
    plan_payload = (
        json.loads(plan_path.read_text(encoding="utf-8"))
        if plan_path.is_file()
        else {"version": 2, "status": "ready"}
    )
    plan_payload["acceptance_refs"] = [
        f"spec-contract.json#/acceptance_criteria/{index}"
        for index in range(len(criteria))
    ]
    plan_path.write_text(json.dumps(plan_payload), encoding="utf-8")

    if not include_tasks:
        return
    task_path = feature_dir / "task-index.json"
    task_payload = (
        json.loads(task_path.read_text(encoding="utf-8")) if task_path.is_file() else {}
    )
    task_payload["version"] = 2
    task_payload["status"] = "ready"
    task_payload["acceptance_refs"] = [
        f"plan-contract.json#/acceptance_refs/{index}" for index in range(len(criteria))
    ]
    task_payload.setdefault(
        "official_entrypoints",
        [{"id": "EP-001", "command": "python -m app", "ready_signal": "ready"}],
    )
    entrypoint_id = task_payload["official_entrypoints"][0]["id"]
    task_payload.setdefault(
        "system_review_scenarios",
        [{"id": "SR-001", "entrypoint_id": entrypoint_id, "required": True}],
    )
    review_scenario_id = task_payload["system_review_scenarios"][0]["id"]
    task_payload["review_obligations"] = [
        {
            "id": f"RO-{index + 1:03d}",
            "kind": "user-journey",
            "source_ref": acceptance_ref,
            "surface": f"Outcome {index + 1}",
            "required": True,
            "scenario_ids": [review_scenario_id],
        }
        for index, acceptance_ref in enumerate(task_payload["acceptance_refs"])
    ]
    task_payload["human_acceptance_obligations"] = [
        {
            "id": f"HAO-{index + 1:03d}",
            "source_ref": acceptance_ref,
            "change_kind": "new",
            "user_outcome": f"Outcome {index + 1}",
            "required": True,
            "scenario_ids": [f"HA-{index + 1:03d}"],
        }
        for index, acceptance_ref in enumerate(task_payload["acceptance_refs"])
    ]
    task_payload["human_acceptance_scenarios"] = [
        {
            "id": f"HA-{index + 1:03d}",
            "title": f"Verify outcome {index + 1}",
            "user_value": f"Outcome {index + 1} works.",
            "actor": "human user",
            "required": True,
            "obligation_ids": [f"HAO-{index + 1:03d}"],
            "entrypoint_id": entrypoint_id,
            "review_scenario_ids": [review_scenario_id],
            "start_state": "The reviewed application is ready.",
            "steps": [
                {
                    "id": f"HAS-{index + 1:03d}",
                    "action": "Perform the changed workflow.",
                    "expected_result": "The changed outcome is visible.",
                    "evidence_requirement": "Human observation.",
                    "risk": "low",
                }
            ],
        }
        for index, _ in enumerate(task_payload["acceptance_refs"])
    ]
    task_path.write_text(json.dumps(task_payload), encoding="utf-8")


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


def _reference_implementation_workflow_state(
    active_profile: str = "reference-implementation",
) -> str:
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
            f"- active_profile: `{active_profile}`"
            if active_profile
            else "- routing_reason: no active profile",
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
    (brainstorming_dir / "handoff-to-specify.json").write_text(
        _valid_must_preserve_handoff_payload(), encoding="utf-8"
    )


def _write_valid_spec_contract(feature_dir: Path) -> None:
    payload = {
        "version": 1,
        "status": "planning-ready",
        "source_contract": None,
        "source_revision": None,
        "decision_digest_ref": None,
        "target_need": "Demo need",
        "scope": {"in": ["Demo behavior"], "out": [], "deferred": []},
        "constraints": [],
        "acceptance_criteria": ["Demo behavior is verifiable"],
        "acceptance_coverage": [
            {
                "requirement_ref": "spec-contract.json#/scope/in/0",
                "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
            }
        ],
        "decisions": [],
        "semantic_delta": [],
        "capability_operations": [],
        "must_preserve_refs": [],
        "consequence_obligation_refs": [],
        "entrypoint_outcome_contract": {
            "triggered": False,
            "stand_down_reason": "The test fixture changes no entrypoint, reused operation, or consumer owner.",
        },
        "design_contract": {
            "experience_requirements": [],
            "design_source_refs": [],
            "design_system_requirements": [],
            "design_system_status": "not-applicable",
            "design_risk_level": "none",
            "fidelity_refs": [],
            "required_states": [],
            "validation_refs": [],
        },
        "context_capsule": {
            "boundary_ref": None,
            "evidence_refs": [],
            "selected_capabilities": [],
            "minimal_live_reads": [],
            "validation_routes": [],
            "stale_if": [],
        },
        "open_items": [],
        "artifact_refs": {
            "spec": "spec.md",
            "alignment": None,
            "context": None,
            "references": None,
        },
        "transition": {
            "version": 1,
            "status": "ready",
            "source_ref": "spec-contract.json",
            "semantic_delta": [],
            "required_refs": [],
            "blockers": [],
            "next_action": "/sp.plan",
            "recovery": None,
        },
    }
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_pending_ui_spec_contract(feature_dir: Path) -> dict[str, object]:
    _write_valid_spec_contract(feature_dir)
    payload = json.loads((feature_dir / "spec-contract.json").read_text(encoding="utf-8"))
    payload["design_gate"] = {
        "decision": "required",
        "scope": "web:settings/page",
        "reason_codes": ["new-surface", "high-visibility"],
        "return_target": "/sp.plan",
    }
    payload["design_contract"] = {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        "ui_work_type": "feature-extension",
        "surface_type": "product-workspace",
        "platforms": ["web"],
        "subject": "settings workspace",
        "audience": "signed-in operators",
        "single_job": "review and save a preference",
        "visual_thesis": "compact settings hierarchy with clear status states",
        "content_thesis": "explain side effects inline without expanding the layout",
        "interaction_thesis": "save feedback stays local and preserves focus",
        "signature_element": "section-scoped save feedback rail",
        "experience_requirements": ["keep settings dense and scannable"],
        "design_source_refs": ["ui-brief.md"],
        "design_system_requirements": ["preserve existing settings hierarchy"],
        "design_system_status": "design-required",
        "design_risk_level": "high",
        "fidelity_refs": [],
        "fidelity_mode": "none",
        "original_reference_refs": [],
        "reference_intents": [],
        "real_content_plan": [],
        "image_plan": [],
        "surface_catalog": [],
        "scenario_matrix": [],
        "color_modes": [],
        "component_contracts": [],
        "responsive_matrix": [],
        "motion_contract": {},
        "visual_acceptance_matrix": [],
        "comparison_tolerance": None,
        "accepted_deviations": [],
        "entry_points": ["/settings"],
        "interaction_matrix": [],
        "editing_matrix": [],
        "accessibility_matrix": [],
        "navigation_matrix": [],
        "content_matrix": [],
        "must_preserve": ["compact hierarchy", "local save feedback"],
        "may_adapt": ["framework markup"],
        "must_not": ["invent a new navigation shell"],
        "required_states": ["loading", "ready", "error"],
        "data_state_matrix": [],
        "usability_validation": {},
        "validation_refs": ["ui-brief.md#validation"],
        "visual_acceptance": ["design review must happen before planning"],
        "required_evidence": ["pending-design-review"],
        "style_authority": {
            "mode": "inherit-existing",
            "scope_level": "feature-partial",
            "source_refs": ["src/ui/settings.tsx"],
            "protected_surfaces": ["global-shell", "shared-components"],
            "allowed_style_delta_surfaces": [],
            "authorization_source": None,
        },
    }
    payload["transition"]["next_action"] = "/sp.design"
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    return payload


def _write_design_index_for_formal_post_specify(
    root: Path,
    *,
    feature_id: str,
    scope: str,
    change_id: str,
    binding_ref: str,
    binding_sha256: str,
    impact_sha256: str,
    revision: int = 1,
) -> str:
    design_root = root / ".specify" / "design"
    design_root.mkdir(parents=True, exist_ok=True)
    change_root = root / ".specify" / "design" / "changes" / change_id
    change_root.mkdir(parents=True, exist_ok=True)
    design_change = (
        "---\n"
        "design_change:\n"
        "  schema: spec-kit-ui-design-change-v1\n"
        f"  id: {change_id}\n"
        "---\n"
        "# Registered Design\n"
    )
    design_change_bytes = design_change.encode("utf-8")
    design_change_sha256 = hashlib.sha256(design_change_bytes).hexdigest()
    (change_root / "design-change.md").write_bytes(design_change_bytes)
    (change_root / "design-contract.json").write_text("{}\n", encoding="utf-8")
    index = {
        "schema": "spec-kit-ui-design-index-v1",
        "changes": [
            {
                "id": change_id,
                "status": "approved",
                "title": "Settings overlay",
                "type": "extension",
                "scope": [scope],
                "profiles": ["developer-tool-sharp"],
                "design_ref": f".specify/design/changes/{change_id}/design-change.md",
                "approval_sha256": design_change_sha256,
                "iteration_of": None,
                "basis_sha256": None,
                "supersedes": [],
                "superseded_scopes": [],
                "consumers": [
                    {
                        "consumer_ref": f"feature:{feature_id}",
                        "scope": scope,
                        "revision": revision,
                        "change_id": change_id,
                    }
                ],
            }
        ],
        "adoptions": [
            {
                "consumer_ref": f"feature:{feature_id}",
                "scope": scope,
                "mode": "formal-post-specify",
                "revision": revision,
                "status": "current",
                "change_id": change_id,
                "design_change_id": change_id,
                "design_change_ref": f".specify/design/changes/{change_id}/design-change.md",
                "design_change_sha256": design_change_sha256,
                "design_contract_ref": f".specify/design/changes/{change_id}/design-contract.json",
                "binding_ref": binding_ref,
                "binding_sha256": binding_sha256,
                "impact_sha256": impact_sha256,
            }
        ],
    }
    (design_root / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return design_change_sha256


def _write_pending_ui_spec_contract_from_plan(
    feature_dir: Path, plan_design: dict[str, object]
) -> None:
    payload = _write_pending_ui_spec_contract(feature_dir)
    design_contract = payload["design_contract"]
    assert isinstance(design_contract, dict)
    for field in (
        "ui_work_type",
        "surface_type",
        "platforms",
        "style_authority",
        "subject",
        "audience",
        "single_job",
        "reference_intents",
        "real_content_plan",
        "image_plan",
        "entry_points",
        "required_states",
        "must_preserve",
        "may_adapt",
        "must_not",
        "validation_refs",
        "visual_acceptance",
    ):
        design_contract[field] = json.loads(json.dumps(plan_design.get(field)))
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


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
        "source": {
            "kind": "test-fixture",
            "path": "tests/hooks/test_artifact_hooks.py",
        },
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
    (brainstorming_dir / "journal.ndjson").write_text(
        json.dumps(journal_event) + "\n", encoding="utf-8"
    )
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


def _write_valid_specify_workflow_state(
    feature_dir: Path, *, observer_status: str = "completed"
) -> None:
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
    assert any("spec-contract.json" in message for message in result.errors)
    assert any("workflow-state.md" in message for message in result.errors)


def test_specify_artifact_validation_does_not_require_compatibility_handoff(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "brainstorming" / "handoff-to-specify.json").unlink()
    _write_valid_spec_contract(feature_dir)

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_bound_discussion_consumer_pointer_requires_exact_lineage_fields() -> None:
    payload = {
        "version": 3,
        "status": "ready",
        "entry_source": "sp-discussion",
        "source_contract": ".specify/discussions/checkout/handoff-to-specify.json",
        "review_digest": "a" * 64,
        "semantic_delta": [],
        "required_refs": [],
        "blockers": [],
        "next_action": "/sp.plan",
    }

    errors = artifact_validation._validate_handoff_to_specify_payload(
        payload, "brainstorming/handoff-to-specify.json"
    )
    assert any("discussion_slug is required" in error for error in errors)
    assert any("recommended_consumer must be sp-specify" in error for error in errors)
    assert any("state_sha256 must be a sha256 digest" in error for error in errors)

    payload.update(
        {
            "discussion_slug": "checkout",
            "recommended_consumer": "sp-specify",
            "state_sha256": "b" * 64,
        }
    )
    assert (
        artifact_validation._validate_handoff_to_specify_payload(
            payload, "brainstorming/handoff-to-specify.json"
        )
        == []
    )

    payload["source_contract"] = (
        ".specify/discussions/search/handoff-to-specify.json"
    )
    errors = artifact_validation._validate_handoff_to_specify_payload(
        payload, "brainstorming/handoff-to-specify.json"
    )
    assert any("source_contract must match discussion_slug" in error for error in errors)


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            lambda payload: payload.pop("capability_operations"),
            "missing capability_operations",
        ),
        (
            lambda payload: payload.pop("acceptance_coverage"),
            "missing acceptance_coverage",
        ),
        (
            lambda payload: payload["transition"].update({"next_action": None}),
            "transition next_action must be a non-empty string when ready",
        ),
        (
            lambda payload: payload["artifact_refs"].update(
                {"context": "../../outside-context.md"}
            ),
            "artifact_refs.context must stay inside the feature directory",
        ),
        (
            lambda payload: payload.update(
                {"semantic_delta": [{"ref": "DEC-001", "change": "Changed scope"}]}
            ),
            "non-empty semantic_delta requires approved user review",
        ),
    ],
)
def test_spec_contract_validation_rejects_incomplete_or_unsafe_agent_contract(
    tmp_path: Path,
    mutation,
    expected_error: str,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _write_valid_spec_contract(feature_dir)
    contract_path = feature_dir / "spec-contract.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    mutation(payload)
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    (project / "outside-context.md").write_text("# Outside\n", encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(expected_error in message for message in result.errors)


@pytest.mark.parametrize("task_index_version", [2, 3])
def test_agent_native_implement_artifacts_require_checked_task_lifecycle(
    tmp_path: Path,
    task_index_version: int,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: resolved\n---\n\nnext_action: complete\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [X] T001 Implement the canonical path\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": task_index_version,
                "status": "ready",
                "tasks": [{"id": "T001"}],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "implementation-review/tasks/T001.json" in message for message in result.errors
    )


def test_implement_artifacts_block_when_workflow_runtime_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: resolved\n---\n\nnext_action: complete\n",
        encoding="utf-8",
    )

    def fail_workflow_validation(_feature_dir: Path) -> dict[str, object]:
        raise WorkflowRuntimeError(
            "runtime returned an invalid envelope",
            code="invalid-workflow-runtime-response",
            status="error",
        )

    monkeypatch.setattr(artifact_validation, "show_workflow", fail_workflow_validation)

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert result.severity == "critical"
    assert result.errors == [
        "workflow state could not be validated: runtime returned an invalid envelope"
    ]


def test_agent_native_ui_task_lifecycle_requires_visual_acceptance(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "design_sources": ["design-change.md", "ui-brief.md"],
                            "required_states": ["loading", "error"],
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    lifecycle = {
        "task_id": "T001",
        "status": "accepted",
        "changed_paths": ["src/ui/page.tsx"],
        "validation": [{"command": "npm test", "status": "passed"}],
        "review": None,
        "blockers": [],
    }
    lifecycle_path = lifecycle_dir / "T001.json"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])

    assert any("ui_verification is required" in error for error in errors)

    lifecycle["ui_verification"] = {
        "applicable": True,
        "evidence_scope": "task",
        "contract_check": "passed",
        "evidence": [
            {"kind": "structure_snapshot", "ref": "evidence/settings-structure.json"},
            {"kind": "visual_capture", "ref": "evidence/settings-desktop.png"},
            {"kind": "runtime_diagnostics", "ref": "evidence/settings-runtime.txt"},
        ],
        "runtime_evidence": "passed",
        "visual_comparison": "matched",
        "fidelity_status": "passed",
        "reviewer": "agent",
        "human_review_ref": None,
    }
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])
    assert any("evidence is missing" in error for error in errors)

    evidence_dir = feature_dir / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "settings-structure.json").write_text("{}\n", encoding="utf-8")
    (evidence_dir / "settings-desktop.png").write_bytes(b"visual evidence")
    (evidence_dir / "settings-runtime.txt").write_text("passed\n", encoding="utf-8")

    assert _validate_task_lifecycle_records(feature_dir, ["T001"]) == []


def test_tasks_markdown_only_ui_task_still_requires_lifecycle_ui_verification(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "- [X] T001 Implement the settings surface\n\n"
        "## T001: Settings surface\n\n"
        "### UI Implementation Contract\n\n"
        "| Field | Value |\n| --- | --- |\n"
        "| design_sources | [design-change.md, ui-brief.md] |\n"
        "| required_evidence | [desktop_screenshot] |\n",
        encoding="utf-8",
    )
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": ["src/ui/page.tsx"],
                "validation": [{"command": "npm test", "status": "passed"}],
                "review": None,
                "blockers": [],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])

    assert any("ui_verification is required" in error for error in errors)


def test_incomplete_ui_contract_is_not_accepted_as_a_legacy_shape(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "ui-brief.md").write_text("# UI Brief\n", encoding="utf-8")
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "design_contract": {
                    "ui_applicable": True,
                    "ui_brief_ref": "ui-brief.md",
                }
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": {"ui_applicable": False}}),
        encoding="utf-8",
    )

    errors = _validate_plan_ui_contract(feature_dir)
    assert any("ui_applicable true" in error for error in errors)

    ui_plan_contract = {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        "design_readiness": "approved",
        "source_refs": ["design-change.md", "ui-brief.md"],
        "design_system_adoption": ["settings controls"],
        "token_strategy": ["reuse approved tokens"],
        "component_strategy": ["reuse settings form"],
        "entry_points": ["/settings"],
        "interaction_matrix": [
            {
                "surface": "settings form",
                "input": "mouse",
                "trigger": "click Save",
                "expectation": "persist the current section and show inline feedback",
            }
        ],
        "required_states": ["loading", "ready", "error"],
        "data_state_matrix": [
            {
                "state": "loading",
                "data_condition": "settings are fetching",
                "expectation": "reserve layout with skeleton rows",
            }
        ],
        "fidelity_refs": [],
        "must_preserve": ["compact hierarchy"],
        "may_adapt": ["framework markup"],
        "must_not": ["hide errors"],
        "validation_refs": ["browser settings route"],
        "visual_acceptance": ["desktop and mobile states inspected"],
        "human_review_conditions": ["comparison unavailable"],
    }
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": ui_plan_contract}),
        encoding="utf-8",
    )
    errors = _validate_plan_ui_contract(feature_dir)
    assert any("visual_thesis" in error for error in errors)
    assert any("required_evidence" in error for error in errors)


def test_pending_ui_spec_contract_accepts_pre_design_route(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "007-ui-pending-spec"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "ui-brief.md").write_text(
        "# UI Brief\n\n## Validation\n\n- Await sp-design.\n", encoding="utf-8"
    )
    _write_pending_ui_spec_contract(feature_dir)

    assert _validate_spec_contract_artifacts(feature_dir) == []


def test_pending_ui_spec_contract_rejects_fake_registered_design_binding(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "008-ui-pending-binding"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "ui-brief.md").write_text(
        "# UI Brief\n\n## Validation\n\n- Await sp-design.\n", encoding="utf-8"
    )
    payload = _write_pending_ui_spec_contract(feature_dir)
    design_contract = payload["design_contract"]
    assert isinstance(design_contract, dict)
    design_contract.update(
        {
            "design_change_id": "UD-0042",
            "design_change_ref": ".specify/design/changes/UD-0042/design-change.md",
            "design_change_sha256": "a" * 64,
            "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
        }
    )
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    errors = _validate_spec_contract_artifacts(feature_dir)

    assert any("design_change_id" in error or "pending" in error for error in errors)


def test_required_design_gate_rejects_plan_next_action(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "009-ui-pending-transition"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "ui-brief.md").write_text(
        "# UI Brief\n\n## Validation\n\n- Await sp-design.\n", encoding="utf-8"
    )
    payload = _write_pending_ui_spec_contract(feature_dir)
    payload["transition"]["next_action"] = "/sp.plan"
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    errors = _validate_spec_contract_artifacts(feature_dir)

    assert any("transition.next_action" in error for error in errors)


def test_not_required_design_gate_rejects_design_next_action(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "010-ui-direct-transition"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _write_valid_spec_contract(feature_dir)
    payload = json.loads((feature_dir / "spec-contract.json").read_text(encoding="utf-8"))
    payload["design_gate"] = {
        "decision": "not_required",
        "scope": None,
        "reason_codes": [],
        "return_target": "/sp.plan",
    }
    payload["transition"]["next_action"] = "/sp.design"
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    errors = _validate_spec_contract_artifacts(feature_dir)

    assert any("transition.next_action" in error for error in errors)


def test_feasibility_only_gate_preserves_existing_plan_next_action(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "011-feasibility-only-transition"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _write_valid_spec_contract(feature_dir)
    payload = json.loads(
        (feature_dir / "spec-contract.json").read_text(encoding="utf-8")
    )
    payload["feasibility_gate"] = {
        "decision": "required",
        "capability_refs": ["CAP-001"],
        "reason_refs": ["spec-contract.json#/scope/in/0"],
    }
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    errors = _validate_spec_contract_artifacts(feature_dir)

    assert not any("transition.next_action" in error for error in errors)


@pytest.mark.parametrize("visual_extension", ["html", "png"])
def test_ui_contract_binds_exact_immutable_design_handoff(
    tmp_path: Path,
    visual_extension: str,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-ui-handoff"
    feature_dir.mkdir(parents=True)
    handoff_path = (
        project / ".specify" / "design" / "previews" / "round-01.handoff.json"
    )
    handoff_path.parent.mkdir(parents=True)
    preview_ref = f"round-01.{visual_extension}#direction-a"
    approved_visual_ref = (
        f".specify/design/previews/round-01.{visual_extension}#direction-a"
    )
    component_row = {
        "id": "DH-COMP-001",
        "component": "settings form",
        "anatomy": ["label", "control", "feedback"],
        "required_states": ["default", "error"],
        "interaction_modes": ["mouse", "keyboard"],
        "data_scenarios": [
            {
                "state": "default",
                "data_condition": "settings data is present",
                "expectation": "render saved values and available controls",
            }
        ],
        "decision_ids": ["DS-COMP-001"],
        "must_match": ["anatomy", "state language"],
    }
    accessibility_row = {
        "id": "DH-ACCESS-001",
        "surface": "settings form",
        "semantics": ["form", "group", "button"],
        "reading_order": "heading, fields, actions",
        "focus_order": "fields then Save",
        "keyboard": ["Tab moves focus", "Enter activates Save"],
        "announcements": ["announce save result"],
        "target_size": "24x24 CSS px minimum",
        "contrast": "WCAG 2.2 AA",
        "zoom_reflow": "reflows without loss at 400%",
        "alternatives": ["text accompanies status icon"],
        "decision_ids": ["DS-COMP-001"],
    }
    motion_contract = {
        "purpose": "show saved-state feedback",
        "transitions": [
            {
                "id": "DH-MOTION-001",
                "surface": "save feedback",
                "trigger": "save succeeds",
                "response": "show confirmation without moving focus",
                "duration_ms": 180,
                "easing": "ease-out",
                "interrupt_behavior": "replace with latest result",
                "decision_ids": ["DS-COMP-001"],
            }
        ],
        "reduced_motion": "instant state change",
        "feedback_timing": {
            "immediate_ms": 100,
            "progress_ms": 1000,
            "timeout_ms": 10000,
        },
    }
    usability_validation = {
        "risk_level": "medium",
        "methods": ["cognitive walkthrough"],
        "critical_tasks": ["save one preference"],
        "success_criteria": ["save without losing section context"],
        "human_review_required": False,
    }
    visual_row = {
        "id": "DH-VA-001",
        "target_id": "DH-RESP-001",
        "states": ["default", "error"],
        "color_modes": ["light"],
        "motion_modes": ["reduced"],
        "decision_ids": ["DS-COMP-001"],
        "must_match": ["structure", "state"],
        "evidence": [
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
            "visual_comparison_or_human_review",
        ],
        "approved_targets": [
            {
                "ref": preview_ref,
                "color_mode": "light",
                "motion_mode": "reduced",
            }
        ],
    }
    tolerance = {
        "structure": "exact",
        "content": "exact",
        "geometry": {"unit": "px", "max_delta": 2},
    }
    handoff = {
        "schema": "spec-kit-design-handoff-v1",
        "approval": {
            "preview_ref": preview_ref,
            "direction_id": "direction-a",
            "preview_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
            "decision_ids": ["DS-COMP-001", "DS-RESP-001"],
        },
        "reproduction": {
            "contract_ids": [
                "DH-ACCESS-001",
                "DH-COMP-001",
                "DH-RESP-001",
                "DH-MOTION-001",
                "DH-VA-001",
            ],
            "accessibility_matrix": [accessibility_row],
            "component_contracts": [component_row],
            "responsive_matrix": [],
            "motion_contract": motion_contract,
            "usability_validation": usability_validation,
            "visual_acceptance_matrix": [visual_row],
            "comparison_tolerance": tolerance,
            "accepted_deviations": [],
        },
    }
    handoff_bytes = json.dumps(
        handoff, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8")
    handoff_path.write_bytes(handoff_bytes)
    contract = {
        "approved_visual_ref": approved_visual_ref,
        "approved_preview_sha256": "a" * 64,
        "approved_manifest_sha256": "b" * 64,
        "approved_handoff_ref": ".specify/design/previews/round-01.handoff.json",
        "approved_handoff_sha256": hashlib.sha256(handoff_bytes).hexdigest(),
        "design_decision_ids": ["DS-COMP-001"],
        "handoff_contract_ids": [
            "DH-ACCESS-001",
            "DH-COMP-001",
            "DH-MOTION-001",
            "DH-VA-001",
        ],
        "accessibility_matrix": [accessibility_row],
        "component_contracts": [component_row],
        "responsive_matrix": [],
        "motion_contract": motion_contract,
        "usability_validation": usability_validation,
        "visual_acceptance_matrix": [visual_row],
        "comparison_tolerance": tolerance,
        "accepted_deviations": [],
    }

    assert _validate_ui_handoff_binding(feature_dir, contract, "plan") == []

    contract["approved_handoff_sha256"] = "c" * 64
    errors = _validate_ui_handoff_binding(feature_dir, contract, "plan")
    assert any("bind the immutable handoff bytes" in error for error in errors)

    contract["approved_handoff_sha256"] = hashlib.sha256(handoff_bytes).hexdigest()
    contract["component_contracts"] = [
        {**component_row, "anatomy": ["agent-authored substitute"]}
    ]
    errors = _validate_ui_handoff_binding(feature_dir, contract, "plan")
    assert any("exactly preserve immutable handoff row" in error for error in errors)

    contract["component_contracts"] = [component_row]
    contract["accessibility_matrix"] = [
        {**accessibility_row, "reading_order": "agent-authored substitute"}
    ]
    errors = _validate_ui_handoff_binding(feature_dir, contract, "plan")
    assert any("exactly preserve immutable handoff row" in error for error in errors)

    contract["accessibility_matrix"] = [accessibility_row]
    contract["usability_validation"] = {
        **usability_validation,
        "risk_level": "low",
    }
    errors = _validate_ui_handoff_binding(feature_dir, contract, "plan")
    assert any("usability_validation" in error for error in errors)


def test_ui_contract_rejects_reauthored_handoff_ids(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-ui-handoff"
    feature_dir.mkdir(parents=True)
    handoff_path = (
        project / ".specify" / "design" / "previews" / "round-01.handoff.json"
    )
    handoff_path.parent.mkdir(parents=True)
    handoff = {
        "schema": "spec-kit-design-handoff-v1",
        "approval": {
            "preview_ref": "round-01.html#direction-a",
            "direction_id": "direction-a",
            "preview_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
            "decision_ids": ["DS-COMP-001"],
        },
        "reproduction": {"contract_ids": ["DH-COMP-001"]},
    }
    handoff_bytes = json.dumps(handoff, sort_keys=True).encode("utf-8")
    handoff_path.write_bytes(handoff_bytes)
    contract = {
        "approved_visual_ref": ".specify/design/previews/round-01.html#direction-a",
        "approved_preview_sha256": "a" * 64,
        "approved_manifest_sha256": "b" * 64,
        "approved_handoff_ref": ".specify/design/previews/round-01.handoff.json",
        "approved_handoff_sha256": hashlib.sha256(handoff_bytes).hexdigest(),
        "design_decision_ids": ["DS-INVENTED-999"],
        "handoff_contract_ids": ["DH-INVENTED-999"],
    }

    errors = _validate_ui_handoff_binding(feature_dir, contract, "plan")

    assert any("design_decision_ids" in error for error in errors)
    assert any("handoff_contract_ids" in error for error in errors)


def _ui_source_continuity_fixture() -> dict[str, object]:
    return {
        "schema": "spec-kit-ui-source-continuity-v1",
        "applicability": "required",
        "mode": "implementation-backed",
        "reason": "The existing settings implementation governs behavior and assets.",
        "coverage": {
            "surface_ids": ["SURFACE-001"],
            "interaction_ids": ["INT-001"],
            "component_ids": ["COMP-001"],
        },
        "authority_refs": ["src/settings/page.tsx", "src/settings/schema.ts"],
        "surface_bindings": [
            {
                "id": "SC-SURFACE-001",
                "surface_id": "SURFACE-001",
                "source_refs": ["src/settings/page.tsx"],
                "discovery": "measured",
                "disposition": "adapt",
                "rationale": "Preserve the settings job while adapting the approved surface.",
            }
        ],
        "action_bindings": [
            {
                "id": "SC-ACTION-001",
                "interaction_id": "INT-001",
                "source_refs": ["src/settings/page.tsx#save"],
                "user_promise": "Save the current preferences.",
                "business_outcome": "The preferences persist once.",
                "side_effects": ["write the current preferences once"],
                "final_state": "Saved values and confirmation remain visible.",
                "verification": "Run source and target save paths with equal input.",
            }
        ],
        "asset_bindings": [
            {
                "id": "SC-ASSET-001",
                "component_id": "COMP-001",
                "semantic_role": "save status",
                "source_refs": ["src/settings/page.tsx"],
                "target_strategy": "preserve",
                "target_ref": "src/assets/status-save.svg",
                "provenance": "project-owned",
                "fallback": "Visible saved text and accessible name.",
                "placeholder_policy": "forbid-character-substitution",
            }
        ],
        "unresolved_gaps": [],
    }


def _not_applicable_ui_source_continuity_fixture() -> dict[str, object]:
    return {
        "schema": "spec-kit-ui-source-continuity-v1",
        "applicability": "not-applicable",
        "mode": "none",
        "reason": "Drifted source-continuity disposition.",
        "coverage": {
            "surface_ids": [],
            "interaction_ids": [],
            "component_ids": [],
        },
        "authority_refs": [],
        "surface_bindings": [],
        "action_bindings": [],
        "asset_bindings": [],
        "unresolved_gaps": [],
    }


def test_current_ui_direction_contract_continues_from_spec_to_task_index(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "002-ui-current"
    feature_dir.mkdir(parents=True)
    (feature_dir / "ui-brief.md").write_text("# UI Brief\n", encoding="utf-8")
    direction = {
        "design_change_id": "UD-0042",
        "design_change_ref": ".specify/design/changes/UD-0042/design-change.md",
        "design_change_sha256": "d" * 64,
        "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
        "ui_work_type": "feature-extension",
        "surface_type": "product-workspace",
        "platforms": ["web", "mobile"],
        "style_authority": {
            "mode": "inherit-existing",
            "scope_level": "feature-partial",
            "source_refs": ["src/settings/page.tsx"],
            "protected_surfaces": ["global-shell", "shared-components"],
            "allowed_style_delta_surfaces": [],
            "authorization_source": None,
        },
        "subject": "account settings",
        "audience": "account owners",
        "single_job": "update preferences",
        "visual_thesis": "compact hierarchy",
        "content_thesis": "real preference labels and values",
        "interaction_thesis": "immediate local feedback",
        "signature_element": "persistent section progress",
        "approved_visual_ref": ".specify/design/changes/UD-0042/design-change.md#settings",
        "approved_preview_sha256": "",
        "approved_manifest_sha256": "",
        "approved_handoff_ref": "",
        "approved_handoff_sha256": "",
        "design_decision_ids": [
            "DS-COMP-001",
            "DS-RESP-001",
            "DS-INT-001",
            "DS-DATA-001",
            "DS-ACCESS-001",
            "DS-NAV-001",
            "DS-CONTENT-001",
            "DS-MOTION-001",
        ],
        "handoff_contract_ids": [],
        "reference_intents": [
            {
                "ref": ".specify/design/changes/UD-0042/design-change.md#settings",
                "intent": "preserve-structure",
            },
            {"ref": "ui-brief.md#interaction", "intent": "exact"},
        ],
        "real_content_plan": [
            {
                "source_ref": "src/settings/schema.ts",
                "applies_to_states": ["ready", "error"],
            }
        ],
        "image_plan": [],
        "source_continuity": _ui_source_continuity_fixture(),
        "surface_catalog": [
            {
                "id": "SURFACE-001",
                "profile_id": "web",
                "name": "Settings",
                "kind": "web",
                "entrypoint_id": "EP-WEB-SETTINGS",
                "source_refs": ["src/settings/page.tsx"],
                "specimen_ids": ["SP-WEB-SETTINGS-001"],
                "component_ids": ["COMP-001"],
                "decision_ids": [
                    "DS-COMP-001",
                    "DS-RESP-001",
                    "DS-INT-001",
                    "DS-DATA-001",
                    "DS-ACCESS-001",
                    "DS-NAV-001",
                    "DS-CONTENT-001",
                    "DS-MOTION-001",
                ],
            }
        ],
        "scenario_matrix": [
            {
                "id": "SCENARIO-001",
                "surface_id": "SURFACE-001",
                "name": "Settings loading mouse save",
                "risk": "medium",
                "required": True,
                "interaction_script": {
                    "preconditions": [
                        "The settings form is rendered at the compact viewport.",
                        "Settings data is loading.",
                    ],
                    "start_state_id": "DATA-001",
                    "branches": [
                        {
                            "conditions": ["success"],
                            "setup": "Complete the save once.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Show the saved values and confirmation.",
                            "focus_behavior": "Keep visible focus on the Save control.",
                            "announcement": "Announce that the settings were saved.",
                            "continuation": "Remain on the settings form.",
                        },
                        {
                            "conditions": ["failure", "timeout", "cancel"],
                            "setup": "Fail, time out, or cancel the save before completion.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Keep unsaved values and show recovery.",
                            "focus_behavior": "Move focus only for correction.",
                            "announcement": "Announce failure without stealing focus.",
                            "continuation": "Retry without losing entered values.",
                        },
                        {
                            "conditions": ["retry", "duplicate", "out_of_order"],
                            "setup": "Repeat, retry, or resolve saves out of order.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Apply one authoritative result.",
                            "focus_behavior": "Preserve active focus and selection.",
                            "announcement": "Announce only the authoritative result.",
                            "continuation": "Reconcile stale completion before editing.",
                        },
                    ],
                    "steps": [
                        {
                            "input": "pointer",
                            "action": "Activate Save once.",
                            "expected_feedback": "Show pending feedback and preserve context.",
                        }
                    ],
                    "focus_checkpoint": "Focus remains visible on the invoking control.",
                    "announcement_checkpoint": "The save result is announced without stealing focus.",
                    "completion_checkpoint": "The final state and specific confirmation remain visible.",
                    "recovery_checkpoint": "Unsaved values survive retry or reauthentication.",
                },
                "interaction_ids": ["INT-001"],
                "editing_ids": ["EDIT-001"],
                "data_state_ids": ["DATA-001"],
                "accessibility_ids": ["A11Y-001"],
                "navigation_ids": ["NAV-001"],
                "content_ids": ["CONTENT-001"],
                "responsive_ids": ["RESP-001"],
                "motion_transition_ids": ["MOTION-001"],
                "decision_ids": [
                    "DS-INT-001",
                    "DS-DATA-001",
                    "DS-ACCESS-001",
                    "DS-NAV-001",
                    "DS-CONTENT-001",
                    "DS-RESP-001",
                    "DS-MOTION-001",
                ],
            }
        ],
        "interaction_matrix": [
            _interaction_contract("INT-001", "mouse"),
            _interaction_contract("INT-002", "keyboard"),
        ],
        "editing_matrix": [_editing_contract()],
        "data_state_matrix": [
            {
                "id": "DATA-001",
                "surface": "settings form",
                "state": "loading",
                "data_condition": "settings data is loading",
                "expectation": "show skeleton rows in the final layout",
                "decision_ids": ["DS-DATA-001"],
            },
            {
                "id": "DATA-002",
                "surface": "settings form",
                "state": "ready",
                "data_condition": "settings data is available",
                "expectation": "render saved values and per-section summaries",
                "decision_ids": ["DS-DATA-001"],
            },
        ],
        "accessibility_matrix": [
            {
                "id": "A11Y-001",
                "surface": "settings form",
                "semantics": ["form", "group", "button"],
                "reading_order": "heading, section summary, fields, actions",
                "focus_order": "section navigation then fields then Save",
                "keyboard": ["Tab moves focus", "Enter activates Save"],
                "announcements": ["announce save result"],
                "target_size": "24x24 CSS px minimum",
                "contrast": "WCAG 2.2 AA",
                "zoom_reflow": "reflows without loss at 400%",
                "alternatives": ["text accompanies status icon"],
                "decision_ids": ["DS-ACCESS-001"],
            }
        ],
        "navigation_matrix": [
            {
                "id": "NAV-001",
                "surface": "settings section",
                "entry": "settings index",
                "destination": "selected section",
                "trigger": "activate section link",
                "back_behavior": "return to prior section and scroll position",
                "deep_link_behavior": "open the addressed section",
                "interruption_recovery": "restore unsaved values after reauthentication",
                "decision_ids": ["DS-NAV-001"],
            }
        ],
        "content_matrix": [
            {
                "id": "CONTENT-001",
                "surface": "save feedback",
                "state": "success",
                "purpose": "confirm the exact preference saved",
                "copy": "Preferences saved.",
                "primary_action": "Continue editing",
                "trust_requirement": "do not claim unrelated settings were saved",
                "localization": "support RTL and translated expansion",
                "content_limits": ["message 120 characters"],
                "decision_ids": ["DS-CONTENT-001"],
            }
        ],
        "color_modes": ["light", "dark"],
        "component_contracts": [
            {
                "id": "COMP-001",
                "component": "settings form",
                "anatomy": ["heading", "fields", "actions"],
                "decision_ids": ["DS-COMP-001"],
                "interaction_modes": ["mouse", "keyboard"],
                "data_scenarios": [
                    {
                        "state": "loading",
                        "data_condition": "settings are still loading",
                        "expectation": "reserve layout with skeleton rows",
                    },
                    {
                        "state": "ready",
                        "data_condition": "settings data is available",
                        "expectation": "render saved values and per-section summaries",
                    },
                ],
                "required_states": ["loading", "ready", "error"],
                "variants": ["default", "compact"],
                "content_constraints": ["labels wrap without truncation"],
                "semantic_token_refs": ["color.feedback.success"],
                "governance": "extend",
                "iconography": "status icons include accessible text",
            }
        ],
        "responsive_matrix": [
            {
                "id": "RESP-001",
                "viewport": "390",
                "state": "loading",
                "adaptation": "stack settings sections",
                "stretch_behavior": "grow field rows for long labels without clipping",
                "overflow_behavior": "keep the page scrollable with sticky actions intact",
                "decision_ids": ["DS-RESP-001"],
            }
        ],
        "motion_contract": {
            "purpose": "show preference save feedback",
            "transitions": [
                {
                    "id": "MOTION-001",
                    "surface": "save feedback",
                    "trigger": "save succeeds",
                    "response": "show confirmation without moving focus",
                    "duration_ms": 180,
                    "easing": "ease-out",
                    "interrupt_behavior": "replace with latest save result",
                    "decision_ids": ["DS-MOTION-001"],
                }
            ],
            "reduced_motion": "instant state change",
            "feedback_timing": {
                "immediate_ms": 100,
                "progress_ms": 1000,
                "timeout_ms": 10000,
            },
        },
        "usability_validation": {
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["update and save one preference"],
            "success_criteria": ["save without losing section context"],
            "human_review_required": True,
        },
        "visual_acceptance_matrix": [
            {
                "id": "VA-001",
                "viewport": "390",
                "state": "ready",
                "evidence": "visual_capture",
                "decision_ids": ["DS-RESP-001"],
            }
        ],
        "comparison_tolerance": COMPARISON_TOLERANCE,
        "accepted_deviations": [],
        "required_evidence": [
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
            "visual_comparison_or_human_review",
        ],
    }
    constraints = {
        "entry_points": ["/settings"],
        "interaction_matrix": [_interaction_contract()],
        "required_states": ["loading", "ready", "error"],
        "data_state_matrix": [
            {
                "id": "DATA-001",
                "surface": "settings form",
                "state": "loading",
                "data_condition": "settings are fetching",
                "expectation": "reserve layout with skeleton rows",
                "decision_ids": ["DS-DATA-001"],
            }
        ],
        "fidelity_mode": "approximate",
        "must_preserve": ["compact hierarchy"],
        "may_adapt": ["framework markup"],
        "must_not": ["hide errors"],
        "visual_acceptance": ["desktop and mobile states inspected"],
    }
    spec_design = {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        **direction,
        **constraints,
    }
    (feature_dir / "spec-contract.json").write_text(
        json.dumps({"design_contract": spec_design}), encoding="utf-8"
    )
    plan_design = {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        "design_readiness": "approved",
        "source_refs": [
            ".specify/design/changes/UD-0042/design-change.md",
            ".specify/design/changes/UD-0042/design-contract.json",
            "ui-brief.md",
        ],
        "design_system_adoption": ["settings controls"],
        "token_strategy": ["reuse approved tokens"],
        "component_strategy": ["reuse settings form"],
        "fidelity_refs": [],
        "validation_refs": ["browser settings route"],
        "human_review_conditions": ["comparison unavailable"],
        **direction,
        **constraints,
    }
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )
    assert _validate_plan_ui_contract(feature_dir) == []

    plan_design["ui_contract_version"] = 2
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )
    assert any(
        "obsolete UI fields" in error
        for error in _validate_plan_ui_contract(feature_dir)
    )
    plan_design.pop("ui_contract_version")

    plan_design["platforms"] = list(reversed(plan_design["platforms"]))
    plan_design["reference_intents"] = list(reversed(plan_design["reference_intents"]))
    plan_design["real_content_plan"] = [
        {
            "source_ref": "src/settings/schema.ts",
            "applies_to_states": ["error", "ready"],
        }
    ]
    plan_design["required_evidence"] = list(reversed(plan_design["required_evidence"]))
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )
    assert _validate_plan_ui_contract(feature_dir) == []

    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Implement settings UI\n\n"
        "## T001: Settings UI\n\n### UI Implementation Contract\n\n"
        "| Field | Value |\n| --- | --- |\n| ui_contract_ref | task-index.json#/tasks/T001/ui_contract |\n",
        encoding="utf-8",
    )
    task_contract = {
        **direction,
        "design_sources": [
            ".specify/design/changes/UD-0042/design-change.md",
            ".specify/design/changes/UD-0042/design-contract.json",
            "ui-brief.md",
        ],
        "reference_notes": "",
        "visual_target": "",
        "fidelity_level": "approximate",
        "must_preserve": ["compact hierarchy"],
        "may_adapt": ["framework markup"],
        "must_not": ["hide errors"],
        "interaction_matrix": constraints["interaction_matrix"],
        "required_states": ["loading", "ready", "error"],
        "data_state_matrix": constraints["data_state_matrix"],
    }
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "official_entrypoints": [
                    {
                        "id": "EP-WEB-SETTINGS",
                        "command": "npm run dev",
                        "ready_signal": "The settings route is ready.",
                    }
                ],
                "tasks": [{"id": "T001", "ui_contract": task_contract}],
            }
        ),
        encoding="utf-8",
    )
    assert _validate_tasks_ui_contract(feature_dir) == []

    task_contract["contract_version"] = 2
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "official_entrypoints": [
                    {
                        "id": "EP-WEB-SETTINGS",
                        "command": "npm run dev",
                        "ready_signal": "The settings route is ready.",
                    }
                ],
                "tasks": [{"id": "T001", "ui_contract": task_contract}],
            }
        ),
        encoding="utf-8",
    )
    assert any(
        "obsolete UI fields" in error
        for error in _validate_tasks_ui_contract(feature_dir)
    )
    task_contract.pop("contract_version")

    task_contract["visual_thesis"] = "unapproved reinterpretation"
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 2, "tasks": [{"id": "T001", "ui_contract": task_contract}]}
        ),
        encoding="utf-8",
    )
    assert any(
        "must preserve plan visual_thesis" in error
        for error in _validate_tasks_ui_contract(feature_dir)
    )


def _write_ui_continuity_fixture(
    feature_dir: Path,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    feature_dir.mkdir(parents=True)
    (feature_dir / "ui-brief.md").write_text("# UI Brief\n", encoding="utf-8")
    direction: dict[str, object] = {
        "design_change_id": "UD-0042",
        "design_change_ref": ".specify/design/changes/UD-0042/design-change.md",
        "design_change_sha256": "d" * 64,
        "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
        "ui_work_type": "feature-extension",
        "surface_type": "product-workspace",
        "platforms": ["web"],
        "style_authority": {
            "mode": "inherit-existing",
            "scope_level": "feature-partial",
            "source_refs": ["src/settings/page.tsx"],
            "protected_surfaces": ["global-shell", "shared-components"],
            "allowed_style_delta_surfaces": [],
            "authorization_source": None,
        },
        "subject": "account settings",
        "audience": "account owners",
        "single_job": "update preferences",
        "visual_thesis": "compact hierarchy",
        "content_thesis": "real preference labels and values",
        "interaction_thesis": "immediate local feedback",
        "signature_element": "persistent section progress",
        "approved_visual_ref": ".specify/design/changes/UD-0042/design-change.md#settings",
        "approved_preview_sha256": "",
        "approved_manifest_sha256": "",
        "approved_handoff_ref": "",
        "approved_handoff_sha256": "",
        "design_decision_ids": [
            "DS-COMP-001",
            "DS-RESP-001",
            "DS-INT-001",
            "DS-DATA-001",
            "DS-ACCESS-001",
            "DS-NAV-001",
            "DS-CONTENT-001",
            "DS-MOTION-001",
        ],
        "handoff_contract_ids": [],
        "reference_intents": [
            {
                "ref": ".specify/design/changes/UD-0042/design-change.md#settings",
                "intent": "preserve-structure",
            }
        ],
        "real_content_plan": [
            {
                "source_ref": "src/settings/schema.ts",
                "applies_to_states": ["ready", "error"],
            }
        ],
        "image_plan": [],
        "source_continuity": _ui_source_continuity_fixture(),
        "surface_catalog": [
            {
                "id": "SURFACE-001",
                "profile_id": "web",
                "name": "Settings",
                "kind": "web",
                "entrypoint_id": "EP-WEB-SETTINGS",
                "source_refs": ["src/settings/page.tsx"],
                "specimen_ids": ["SP-WEB-SETTINGS-001"],
                "component_ids": ["COMP-001"],
                "decision_ids": [
                    "DS-COMP-001",
                    "DS-RESP-001",
                    "DS-INT-001",
                    "DS-DATA-001",
                    "DS-ACCESS-001",
                    "DS-NAV-001",
                    "DS-CONTENT-001",
                    "DS-MOTION-001",
                ],
            }
        ],
        "scenario_matrix": [
            {
                "id": "SCENARIO-001",
                "surface_id": "SURFACE-001",
                "name": "Settings loading mouse save",
                "risk": "medium",
                "required": True,
                "interaction_script": {
                    "preconditions": [
                        "The settings form is rendered at the compact viewport.",
                        "Settings data is loading.",
                    ],
                    "start_state_id": "DATA-001",
                    "branches": [
                        {
                            "conditions": ["success"],
                            "setup": "Complete the save once.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Show the saved values and confirmation.",
                            "focus_behavior": "Keep visible focus on the Save control.",
                            "announcement": "Announce that the settings were saved.",
                            "continuation": "Remain on the settings form.",
                        },
                        {
                            "conditions": ["failure", "timeout", "cancel"],
                            "setup": "Fail, time out, or cancel the save before completion.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Keep unsaved values and show recovery.",
                            "focus_behavior": "Move focus only for correction.",
                            "announcement": "Announce failure without stealing focus.",
                            "continuation": "Retry without losing entered values.",
                        },
                        {
                            "conditions": ["retry", "duplicate", "out_of_order"],
                            "setup": "Repeat, retry, or resolve saves out of order.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Apply one authoritative result.",
                            "focus_behavior": "Preserve active focus and selection.",
                            "announcement": "Announce only the authoritative result.",
                            "continuation": "Reconcile stale completion before editing.",
                        },
                    ],
                    "steps": [
                        {
                            "input": "pointer",
                            "action": "Activate Save once.",
                            "expected_feedback": "Show pending feedback and preserve context.",
                        }
                    ],
                    "focus_checkpoint": "Focus remains visible on the invoking control.",
                    "announcement_checkpoint": "The save result is announced without stealing focus.",
                    "completion_checkpoint": "The final state and specific confirmation remain visible.",
                    "recovery_checkpoint": "Unsaved values survive retry or reauthentication.",
                },
                "interaction_ids": ["INT-001"],
                "editing_ids": ["EDIT-001"],
                "data_state_ids": ["DATA-001"],
                "accessibility_ids": ["A11Y-001"],
                "navigation_ids": ["NAV-001"],
                "content_ids": ["CONTENT-001"],
                "responsive_ids": ["RESP-001"],
                "motion_transition_ids": ["MOTION-001"],
                "decision_ids": [
                    "DS-INT-001",
                    "DS-DATA-001",
                    "DS-ACCESS-001",
                    "DS-NAV-001",
                    "DS-CONTENT-001",
                    "DS-RESP-001",
                    "DS-MOTION-001",
                ],
            }
        ],
        "interaction_matrix": [_interaction_contract()],
        "editing_matrix": [_editing_contract()],
        "data_state_matrix": [
            {
                "id": "DATA-001",
                "surface": "settings form",
                "state": "loading",
                "data_condition": "settings are fetching",
                "expectation": "reserve layout with skeleton rows",
                "decision_ids": ["DS-DATA-001"],
            }
        ],
        "accessibility_matrix": [
            {
                "id": "A11Y-001",
                "surface": "settings form",
                "semantics": ["form", "group", "button"],
                "reading_order": "heading, section summary, fields, actions",
                "focus_order": "section navigation then fields then Save",
                "keyboard": ["Tab moves focus", "Enter activates Save"],
                "announcements": ["announce save result"],
                "target_size": "24x24 CSS px minimum",
                "contrast": "WCAG 2.2 AA",
                "zoom_reflow": "reflows without loss at 400%",
                "alternatives": ["text accompanies status icon"],
                "decision_ids": ["DS-ACCESS-001"],
            }
        ],
        "navigation_matrix": [
            {
                "id": "NAV-001",
                "surface": "settings section",
                "entry": "settings index",
                "destination": "selected section",
                "trigger": "activate section link",
                "back_behavior": "return to prior section and scroll position",
                "deep_link_behavior": "open the addressed section",
                "interruption_recovery": "restore unsaved values after reauthentication",
                "decision_ids": ["DS-NAV-001"],
            }
        ],
        "content_matrix": [
            {
                "id": "CONTENT-001",
                "surface": "save feedback",
                "state": "success",
                "purpose": "confirm the exact preference saved",
                "copy": "Preferences saved.",
                "primary_action": "Continue editing",
                "trust_requirement": "do not claim unrelated settings were saved",
                "localization": "support RTL and translated expansion",
                "content_limits": ["message 120 characters"],
                "decision_ids": ["DS-CONTENT-001"],
            }
        ],
        "color_modes": ["light", "dark"],
        "component_contracts": [
            {
                "id": "COMP-001",
                "component": "settings form",
                "anatomy": ["heading", "fields", "actions"],
                "decision_ids": ["DS-COMP-001"],
                "interaction_modes": ["mouse", "keyboard"],
                "data_scenarios": [
                    {
                        "state": "loading",
                        "data_condition": "settings are still loading",
                        "expectation": "reserve layout with skeleton rows",
                    },
                    {
                        "state": "ready",
                        "data_condition": "settings data is available",
                        "expectation": "render saved values and per-section summaries",
                    },
                ],
                "required_states": ["loading", "ready", "error"],
                "variants": ["default", "compact"],
                "content_constraints": ["labels wrap without truncation"],
                "semantic_token_refs": ["color.feedback.success"],
                "governance": "extend",
                "iconography": "status icons include accessible text",
            }
        ],
        "responsive_matrix": [
            {
                "id": "RESP-001",
                "viewport": "390",
                "state": "loading",
                "adaptation": "stack settings sections",
                "stretch_behavior": "grow field rows for long labels without clipping",
                "overflow_behavior": "keep the page scrollable with sticky actions intact",
                "decision_ids": ["DS-RESP-001"],
            }
        ],
        "motion_contract": {
            "purpose": "show preference save feedback",
            "transitions": [
                {
                    "id": "MOTION-001",
                    "surface": "save feedback",
                    "trigger": "save succeeds",
                    "response": "show confirmation without moving focus",
                    "duration_ms": 180,
                    "easing": "ease-out",
                    "interrupt_behavior": "replace with latest save result",
                    "decision_ids": ["DS-MOTION-001"],
                }
            ],
            "reduced_motion": "instant state change",
            "feedback_timing": {
                "immediate_ms": 100,
                "progress_ms": 1000,
                "timeout_ms": 10000,
            },
        },
        "usability_validation": {
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["update and save one preference"],
            "success_criteria": ["save without losing section context"],
            "human_review_required": True,
        },
        "visual_acceptance_matrix": [
            {
                "id": "VA-001",
                "viewport": "390",
                "state": "ready",
                "evidence": "visual_capture",
                "decision_ids": ["DS-RESP-001"],
            }
        ],
        "comparison_tolerance": COMPARISON_TOLERANCE,
        "accepted_deviations": [],
        "required_evidence": [
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
            "visual_comparison_or_human_review",
        ],
    }
    constraints: dict[str, object] = {
        "entry_points": ["/settings"],
        "interaction_matrix": [_interaction_contract()],
        "required_states": ["loading", "ready", "error"],
        "data_state_matrix": [
            {
                "id": "DATA-001",
                "surface": "settings form",
                "state": "loading",
                "data_condition": "settings are fetching",
                "expectation": "reserve layout with skeleton rows",
                "decision_ids": ["DS-DATA-001"],
            }
        ],
        "must_preserve": ["compact hierarchy"],
        "may_adapt": ["framework markup"],
        "must_not": ["hide errors"],
        "visual_acceptance": ["desktop settings states inspected"],
        "fidelity_mode": "high",
    }
    spec_design: dict[str, object] = {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        "original_reference_refs": [
            ".specify/design/changes/UD-0042/design-change.md#settings"
        ],
        **direction,
        **constraints,
    }
    plan_design: dict[str, object] = {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        "design_readiness": "approved",
        "source_refs": [
            ".specify/design/changes/UD-0042/design-change.md",
            ".specify/design/changes/UD-0042/design-contract.json",
            "ui-brief.md",
        ],
        "design_system_adoption": ["settings controls"],
        "token_strategy": ["reuse approved tokens"],
        "component_strategy": ["reuse settings form"],
        "fidelity_refs": [".specify/design/changes/UD-0042/design-change.md#settings"],
        "validation_refs": ["browser settings route"],
        "human_review_conditions": ["comparison unavailable"],
        **direction,
        **constraints,
    }
    task_contract: dict[str, object] = {
        **direction,
        "design_sources": [
            ".specify/design/changes/UD-0042/design-change.md",
            ".specify/design/changes/UD-0042/design-contract.json",
            "ui-brief.md",
        ],
        "reference_notes": "",
        "visual_target": "",
        "fidelity_level": "high",
        "must_preserve": constraints["must_preserve"],
        "may_adapt": constraints["may_adapt"],
        "must_not": constraints["must_not"],
        "required_states": constraints["required_states"],
    }
    (feature_dir / "spec-contract.json").write_text(
        json.dumps({"design_contract": spec_design}), encoding="utf-8"
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Implement settings UI\n\n"
        "## T001: Settings UI\n\n### UI Implementation Contract\n\n"
        "| Field | Value |\n| --- | --- |\n"
        "| ui_contract_ref | task-index.json#/tasks/T001/ui_contract |\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "official_entrypoints": [
                    {
                        "id": "EP-WEB-SETTINGS",
                        "command": "npm run dev",
                        "ready_signal": "The settings route is ready.",
                    }
                ],
                "tasks": [{"id": "T001", "ui_contract": task_contract}],
            }
        ),
        encoding="utf-8",
    )
    return spec_design, plan_design, task_contract


def _late_overlay_plan_design_contract() -> dict[str, object]:
    direction: dict[str, object] = {
        "ui_work_type": "feature-extension",
        "surface_type": "product-workspace",
        "platforms": ["web"],
        "style_authority": {
            "mode": "inherit-existing",
            "scope_level": "feature-partial",
            "source_refs": ["src/ui/settings.tsx"],
            "protected_surfaces": ["global-shell", "shared-components"],
            "allowed_style_delta_surfaces": [],
            "authorization_source": None,
        },
        "subject": "settings workspace",
        "audience": "signed-in operators",
        "single_job": "review and save a preference",
        "visual_thesis": "compact settings hierarchy with clear local save states",
        "content_thesis": "preserve dense operator copy with inline rationale",
        "interaction_thesis": "keep focus in place while save state resolves",
        "signature_element": "section-scoped feedback rail",
        "design_change_id": "UD-0042",
        "design_change_ref": ".specify/design/changes/UD-0042/design-change.md",
        "design_change_sha256": "a" * 64,
        "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
        "approved_visual_ref": ".specify/design/changes/UD-0042/previews/round-01.png#direction-main",
        "approved_preview_sha256": "b" * 64,
        "approved_manifest_sha256": "c" * 64,
        "approved_handoff_ref": ".specify/design/changes/UD-0042/previews/round-01.handoff.json",
        "approved_handoff_sha256": "d" * 64,
        "design_decision_ids": ["DS-COMP-001"],
        "handoff_contract_ids": ["DH-COMP-001"],
        "reference_intents": [],
        "real_content_plan": [],
        "image_plan": [],
        "surface_catalog": [
            {"id": "SURF-001", "surface": "settings page", "entrypoint_id": "EP-WEB-SETTINGS"}
        ],
        "scenario_matrix": [
            {
                "id": "SCN-001",
                "surface_id": "SURF-001",
                "interaction_ids": ["INT-001"],
                "editing_ids": [],
                "data_state_ids": ["DATA-001"],
                "accessibility_ids": [],
                "navigation_ids": [],
                "content_ids": [],
                "preconditions": ["user is on settings"],
                "start_state_id": "DATA-001",
                "steps": [{"input": "mouse", "action": "click Save", "expected_feedback": "inline pending feedback"}],
                "branches": [],
                "focus_checkpoint": "save button remains in context",
                "announcement_checkpoint": "status is announced",
                "completion_checkpoint": "saved state appears",
                "recovery_checkpoint": "retry remains available",
            }
        ],
        "interaction_matrix": [_interaction_contract()],
        "editing_matrix": [],
        "accessibility_matrix": [],
        "navigation_matrix": [],
        "content_matrix": [],
        "required_states": ["loading", "ready", "error"],
        "data_state_matrix": [
            {
                "id": "DATA-001",
                "surface": "settings page",
                "state": "ready",
                "data_condition": "settings data is loaded",
                "expectation": "current values render before edits",
                "decision_ids": ["DS-COMP-001"],
            }
        ],
        "fidelity_refs": [".specify/design/changes/UD-0042/design-change.md#settings"],
        "fidelity_mode": "approximate",
        "source_continuity": {
            "schema": "spec-kit-ui-source-continuity-v1",
            "applicability": "not-assessed",
            "mode": "none",
            "reason": None,
            "coverage": {
                "surface_ids": [],
                "interaction_ids": [],
                "component_ids": [],
            },
            "authority_refs": [],
            "surface_bindings": [],
            "action_bindings": [],
            "asset_bindings": [],
            "unresolved_gaps": [],
        },
        "color_modes": ["light"],
        "component_contracts": [],
        "responsive_matrix": [],
        "motion_contract": {},
        "usability_validation": {
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["save one preference"],
            "success_criteria": ["save without losing section context"],
            "human_review_required": False,
        },
        "visual_acceptance_matrix": [],
        "comparison_tolerance": COMPARISON_TOLERANCE,
        "accepted_deviations": [],
        "must_preserve": ["compact hierarchy", "local save feedback"],
        "may_adapt": ["framework markup"],
        "must_not": ["invent a new navigation shell"],
        "validation_refs": ["browser settings route"],
        "visual_acceptance": ["desktop settings route inspected"],
        "human_review_conditions": ["visual comparison unavailable"],
        "required_evidence": [
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
            "visual_comparison_or_human_review",
        ],
    }
    return {
        "ui_applicable": True,
        "ui_brief_ref": "ui-brief.md",
        "design_readiness": "approved",
        "source_refs": [
            ".specify/design/changes/UD-0042/design-change.md",
            ".specify/design/changes/UD-0042/design-contract.json",
            "ui-brief.md",
        ],
        "design_system_adoption": ["reuse approved settings design"],
        "token_strategy": ["reuse registered color and spacing tokens"],
        "component_strategy": ["reuse registered settings shell"],
        "entry_points": ["/settings"],
        **direction,
    }


def test_task_ui_contract_surface_entrypoint_must_bind_official_entrypoint(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "002-ui-entrypoint"
    _write_ui_continuity_fixture(feature_dir)
    task_index_path = feature_dir / "task-index.json"
    task_index = json.loads(task_index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["ui_contract"]["surface_catalog"][0][
        "entrypoint_id"
    ] = "EP-UNKNOWN"
    task_index_path.write_text(json.dumps(task_index), encoding="utf-8")

    errors = _validate_tasks_ui_contract(feature_dir)

    assert any("unknown official entrypoint" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    [
        ("entry_points", ["/different"]),
        ("required_states", ["ready"]),
        ("must_preserve", ["replace the information hierarchy"]),
        ("may_adapt", ["change the navigation model"]),
        ("must_not", ["a different prohibition"]),
        ("visual_acceptance", ["inspect an unrelated route"]),
        ("fidelity_mode", "approximate"),
        ("design_change_sha256", "e" * 64),
        ("editing_matrix", []),
        ("accessibility_matrix", []),
        ("navigation_matrix", []),
        ("content_matrix", []),
        ("source_continuity", _not_applicable_ui_source_continuity_fixture()),
        (
            "usability_validation",
            {
                "risk_level": "low",
                "methods": ["heuristic review"],
                "critical_tasks": ["a different task"],
                "success_criteria": ["a different outcome"],
                "human_review_required": False,
            },
        ),
    ],
)
def test_plan_ui_contract_rejects_specification_constraint_drift(
    tmp_path: Path,
    field: str,
    drifted_value: object,
) -> None:
    feature_dir = tmp_path / "specs" / "003-ui-continuity"
    _, plan_design, _ = _write_ui_continuity_fixture(feature_dir)
    assert _validate_plan_ui_contract(feature_dir) == []
    plan_design[field] = drifted_value
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )

    errors = _validate_plan_ui_contract(feature_dir)

    assert any(field in error and "preserve" in error.lower() for error in errors)


def test_plan_ui_contract_accepts_formal_post_specify_overlay_binding(
    tmp_path: Path,
) -> None:
    root = tmp_path
    feature_dir = root / "specs" / "007-ui-plan-overlay"
    _, plan_design, _ = _write_ui_continuity_fixture(feature_dir)
    _write_pending_ui_spec_contract_from_plan(feature_dir, plan_design)
    binding_sha256 = hashlib.sha256(
        (feature_dir / "spec-contract.json").read_bytes()
    ).hexdigest()
    impact_sha256 = "f" * 64
    design_change_sha256 = _write_design_index_for_formal_post_specify(
        root,
        feature_id=feature_dir.name,
        scope="web:settings/page",
        change_id="UD-0042",
        binding_ref="specs/007-ui-plan-overlay/spec-contract.json",
        binding_sha256=binding_sha256,
        impact_sha256=impact_sha256,
    )
    plan_design["design_change_sha256"] = design_change_sha256
    plan_design["design_adoption_binding"] = {
        "mode": "formal-post-specify",
        "consumer_ref": "feature:007-ui-plan-overlay",
        "scope": "web:settings/page",
        "revision": 1,
        "change_id": "UD-0042",
        "binding_ref": "specs/007-ui-plan-overlay/spec-contract.json",
        "binding_sha256": binding_sha256,
        "impact_sha256": impact_sha256,
    }
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )

    assert _validate_plan_ui_contract(feature_dir) == []


def test_plan_rejects_formal_post_specify_overlay_without_required_design_gate(
    tmp_path: Path,
) -> None:
    root = tmp_path
    feature_dir = root / "specs" / "009-ui-plan-overlay-bypass"
    _, plan_design, _ = _write_ui_continuity_fixture(feature_dir)
    _write_pending_ui_spec_contract_from_plan(feature_dir, plan_design)
    spec_payload = json.loads(
        (feature_dir / "spec-contract.json").read_text(encoding="utf-8")
    )
    spec_payload.pop("design_gate", None)
    spec_payload["transition"]["next_action"] = "/sp.plan"
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(spec_payload), encoding="utf-8"
    )
    binding_ref = "specs/009-ui-plan-overlay-bypass/spec-contract.json"
    binding_sha256 = hashlib.sha256(
        (feature_dir / "spec-contract.json").read_bytes()
    ).hexdigest()
    impact_sha256 = "f" * 64
    design_change_sha256 = _write_design_index_for_formal_post_specify(
        root,
        feature_id=feature_dir.name,
        scope="web:settings/page",
        change_id="UD-0042",
        binding_ref=binding_ref,
        binding_sha256=binding_sha256,
        impact_sha256=impact_sha256,
    )
    plan_design["design_change_sha256"] = design_change_sha256
    plan_design["must_preserve"] = ["replace the approved hierarchy"]
    plan_design["design_adoption_binding"] = {
        "mode": "formal-post-specify",
        "consumer_ref": f"feature:{feature_dir.name}",
        "scope": "web:settings/page",
        "revision": 1,
        "change_id": "UD-0042",
        "binding_ref": binding_ref,
        "binding_sha256": binding_sha256,
        "impact_sha256": impact_sha256,
    }
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )

    errors = _validate_plan_ui_contract(feature_dir)

    assert any("design_gate.required" in error for error in errors)


def test_plan_rejects_formal_post_specify_overlay_when_registered_design_mutates(
    tmp_path: Path,
) -> None:
    root = tmp_path
    feature_dir = root / "specs" / "010-ui-plan-overlay-tampered"
    _, plan_design, _ = _write_ui_continuity_fixture(feature_dir)
    _write_pending_ui_spec_contract_from_plan(feature_dir, plan_design)
    binding_ref = "specs/010-ui-plan-overlay-tampered/spec-contract.json"
    binding_sha256 = hashlib.sha256(
        (feature_dir / "spec-contract.json").read_bytes()
    ).hexdigest()
    impact_sha256 = "f" * 64
    design_change_sha256 = _write_design_index_for_formal_post_specify(
        root,
        feature_id=feature_dir.name,
        scope="web:settings/page",
        change_id="UD-0042",
        binding_ref=binding_ref,
        binding_sha256=binding_sha256,
        impact_sha256=impact_sha256,
    )
    plan_design["design_change_sha256"] = design_change_sha256
    plan_design["design_adoption_binding"] = {
        "mode": "formal-post-specify",
        "consumer_ref": f"feature:{feature_dir.name}",
        "scope": "web:settings/page",
        "revision": 1,
        "change_id": "UD-0042",
        "binding_ref": binding_ref,
        "binding_sha256": binding_sha256,
        "impact_sha256": impact_sha256,
    }
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )
    design_path = root / ".specify" / "design" / "changes" / "UD-0042" / "design-change.md"
    design_path.write_text(design_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")

    errors = _validate_plan_ui_contract(feature_dir)

    assert any("registered design" in error.lower() for error in errors)


def test_plan_ui_contract_requires_formal_post_specify_overlay_binding(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "008-ui-plan-overlay"
    feature_dir.mkdir(parents=True)
    _write_pending_ui_spec_contract(feature_dir)
    plan_design = _late_overlay_plan_design_contract()
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )

    errors = _validate_plan_ui_contract(feature_dir)

    assert any("design_adoption_binding" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    [
        ("fidelity_level", "none"),
        ("required_states", ["unknown-state"]),
        ("must_preserve", []),
        ("may_adapt", ["replace the approved hierarchy"]),
        ("must_not", []),
        ("design_change_sha256", "e" * 64),
        ("editing_matrix", []),
        ("accessibility_matrix", []),
        ("navigation_matrix", []),
        ("content_matrix", []),
        ("source_continuity", _not_applicable_ui_source_continuity_fixture()),
        (
            "usability_validation",
            {
                "risk_level": "low",
                "methods": ["self review"],
                "critical_tasks": ["a different task"],
                "success_criteria": ["a different outcome"],
                "human_review_required": False,
            },
        ),
    ],
)
def test_task_ui_contract_rejects_plan_constraint_drift(
    tmp_path: Path,
    field: str,
    drifted_value: object,
) -> None:
    feature_dir = tmp_path / "specs" / "004-ui-task-continuity"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    assert _validate_tasks_ui_contract(feature_dir) == []
    task_contract[field] = drifted_value
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 2, "tasks": [{"id": "T001", "ui_contract": task_contract}]}
        ),
        encoding="utf-8",
    )

    errors = _validate_tasks_ui_contract(feature_dir)

    assert any(field in error for error in errors)


def test_task_ui_contract_requires_exact_design_decision_coverage(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-ui-decision-coverage"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    task_contract["design_decision_ids"] = ["DS-COMP-001"]
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {"version": 2, "tasks": [{"id": "T001", "ui_contract": task_contract}]}
        ),
        encoding="utf-8",
    )

    errors = _validate_tasks_ui_contract(feature_dir)

    assert any("must cover plan design_decision_ids" in error for error in errors)


def test_ui_scenario_matrix_rejects_cross_category_contract_refs(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-ui-scenario-ref-kinds"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    scenario = task_contract["scenario_matrix"][0]
    scenario["interaction_ids"], scenario["data_state_ids"] = (
        scenario["data_state_ids"],
        scenario["interaction_ids"],
    )

    errors = artifact_validation._validate_ui_contract_shape(
        task_contract, "task T001 ui_contract"
    )

    assert any("scenario_matrix" in error for error in errors)


def test_ui_scenario_matrix_requires_executable_interaction_checkpoints(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-ui-scenario-execution"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    task_contract["scenario_matrix"][0]["interaction_script"][
        "announcement_checkpoint"
    ] = ""

    errors = artifact_validation._validate_ui_contract_shape(
        task_contract, "task T001 ui_contract"
    )

    assert any("scenario_matrix" in error for error in errors)


def test_ui_editing_matrix_requires_the_complete_editing_lifecycle(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-ui-editing-lifecycle"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    task_contract["editing_matrix"][0]["composition_behavior"] = ""

    errors = artifact_validation._validate_ui_contract_shape(
        task_contract, "task T001 ui_contract"
    )

    assert any("editing_matrix" in error for error in errors)


def test_ui_interaction_matrix_requires_the_complete_event_lifecycle(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-ui-interaction-lifecycle"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    task_contract["interaction_matrix"][0]["event_sequence"] = ""

    errors = artifact_validation._validate_ui_contract_shape(
        task_contract, "task T001 ui_contract"
    )

    assert any("interaction_matrix" in error for error in errors)


def test_ui_scenario_matrix_rejects_branch_state_outside_selected_data(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-ui-scenario-branch-state"
    _, _, task_contract = _write_ui_continuity_fixture(feature_dir)
    errors = artifact_validation._validate_ui_contract_shape(
        task_contract, "task T001 ui_contract"
    )
    assert not any("scenario_matrix" in error for error in errors)

    task_contract["scenario_matrix"][0]["interaction_script"]["branches"][0][
        "expected_state_id"
    ] = "DATA-UNKNOWN"
    errors = artifact_validation._validate_ui_contract_shape(
        task_contract, "task T001 ui_contract"
    )

    assert any("scenario_matrix" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "extra_row"),
    [
        (
            "interaction_matrix",
            _interaction_contract("INT-002", "keyboard"),
        ),
        ("editing_matrix", _editing_contract("EDIT-002")),
        (
            "data_state_matrix",
            {
                "id": "DATA-002",
                "surface": "settings form",
                "state": "empty",
                "data_condition": "no configurable settings are available",
                "expectation": "explain the empty condition and keep navigation usable",
                "decision_ids": ["DS-DATA-001"],
            },
        ),
        (
            "accessibility_matrix",
            {
                "id": "A11Y-002",
                "surface": "settings error summary",
                "semantics": ["alert", "link"],
                "reading_order": "summary before invalid fields",
                "focus_order": "focus summary then linked invalid fields",
                "keyboard": ["Enter follows an error link"],
                "announcements": ["announce error count"],
                "target_size": "24x24 CSS px minimum",
                "contrast": "WCAG 2.2 AA",
                "zoom_reflow": "reflows without loss at 400%",
                "alternatives": ["text identifies every error"],
                "decision_ids": ["DS-ACCESS-001"],
            },
        ),
        (
            "navigation_matrix",
            {
                "id": "NAV-002",
                "surface": "settings search result",
                "entry": "settings search",
                "destination": "matching field",
                "trigger": "activate search result",
                "back_behavior": "restore the search query and result position",
                "deep_link_behavior": "open and focus the addressed field",
                "interruption_recovery": "restore the query after reauthentication",
                "decision_ids": ["DS-NAV-001"],
            },
        ),
        (
            "content_matrix",
            {
                "id": "CONTENT-002",
                "surface": "save failure",
                "state": "error",
                "purpose": "explain that the preference was not saved",
                "copy": "We could not save this preference.",
                "primary_action": "Try again",
                "trust_requirement": "preserve the unsaved value",
                "localization": "support RTL and translated expansion",
                "content_limits": ["message 160 characters"],
                "decision_ids": ["DS-CONTENT-001"],
            },
        ),
    ],
)
def test_task_ui_contract_requires_professional_matrix_coverage(
    tmp_path: Path,
    field: str,
    extra_row: dict[str, object],
) -> None:
    feature_dir = tmp_path / "specs" / "006-ui-scenario-coverage"
    _, plan_design, _ = _write_ui_continuity_fixture(feature_dir)
    plan_design[field] = [*plan_design[field], extra_row]
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"ui_design_contract": plan_design}), encoding="utf-8"
    )

    errors = _validate_tasks_ui_contract(feature_dir)

    assert any(f"must cover plan {field}" in error for error in errors)


def _write_human_acceptance_universe(
    feature_dir: Path, *, task_acceptance_refs: list[str]
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    plan_refs = [
        "spec-contract.json#/acceptance_criteria/0",
        "spec-contract.json#/acceptance_criteria/1",
    ]
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Outcome 1", "Outcome 2"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": [
                    "A human can complete outcome 1.",
                    "A human can complete outcome 2.",
                ],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    },
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/1",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/1",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps({"version": 2, "status": "ready", "acceptance_refs": plan_refs}),
        encoding="utf-8",
    )
    obligations = [
        {
            "id": f"HAO-{index + 1:03d}",
            "source_ref": source_ref,
            "change_kind": "new",
            "user_outcome": f"Outcome {index + 1}",
            "required": True,
            "scenario_ids": [f"HA-{index + 1:03d}"],
        }
        for index, source_ref in enumerate(task_acceptance_refs)
    ]
    review_scenarios = [
        {
            "id": f"SR-{index + 1:03d}",
            "entrypoint_id": "EP-001",
            "required": True,
        }
        for index, _ in enumerate(task_acceptance_refs)
    ]
    review_obligations = [
        {
            "id": f"RO-{index + 1:03d}",
            "kind": "user-journey",
            "source_ref": source_ref,
            "surface": f"Outcome {index + 1}",
            "required": True,
            "scenario_ids": [f"SR-{index + 1:03d}"],
        }
        for index, source_ref in enumerate(task_acceptance_refs)
    ]
    scenarios = [
        {
            "id": f"HA-{index + 1:03d}",
            "title": f"Journey {index + 1}",
            "user_value": f"Value {index + 1}",
            "actor": "human user",
            "start_state": "Application ready",
            "required": True,
            "entrypoint_id": "EP-001",
            "obligation_ids": [f"HAO-{index + 1:03d}"],
            "review_scenario_ids": [f"SR-{index + 1:03d}"],
            "steps": [
                {
                    "id": f"HAS-{index + 1:03d}",
                    "action": "Perform the changed workflow",
                    "expected_result": "The changed outcome is visible",
                    "evidence_requirement": "human observation",
                    "risk": "low",
                }
            ],
        }
        for index, _ in enumerate(task_acceptance_refs)
    ]
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": task_acceptance_refs,
                "official_entrypoints": [
                    {
                        "id": "EP-001",
                        "command": "python -m app",
                        "ready_signal": "ready",
                    }
                ],
                "system_review_scenarios": review_scenarios,
                "review_obligations": review_obligations,
                "human_acceptance_obligations": obligations,
                "human_acceptance_scenarios": scenarios,
            }
        ),
        encoding="utf-8",
    )


def test_human_acceptance_universe_preserves_all_plan_acceptance_refs(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "005-human-acceptance"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )

    assert _validate_tasks_human_acceptance_contract(feature_dir) == []


def test_human_acceptance_universe_rejects_plan_acceptance_ref_omission(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "006-human-acceptance-omission"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=["plan-contract.json#/acceptance_refs/0"],
    )

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any(
        "missing plan acceptance_refs" in error
        and "spec-contract.json#/acceptance_criteria/1" in error
        for error in errors
    )


def test_plan_acceptance_refs_must_cover_every_spec_acceptance_criterion(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "007-plan-acceptance-denominator"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Primary journey", "Terminal result"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": [
                    "A human can complete the new primary journey.",
                    "A human sees the changed terminal result.",
                ],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    },
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/1",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/1",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_plan_human_acceptance_contract(feature_dir)

    assert any(
        "missing spec acceptance criteria" in error
        and "spec-contract.json#/acceptance_criteria/1" in error
        for error in errors
    )


def test_spec_acceptance_coverage_is_required_for_machine_readable_closure(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "007b-spec-scope-closure"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Export reports", "Import reports"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": ["The reporting feature works."],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_plan_human_acceptance_contract(feature_dir)

    assert any(
        "acceptance_coverage must be a non-empty array" in error for error in errors
    )


def test_spec_acceptance_coverage_rejects_one_criterion_shared_by_multiple_requirements(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "007c-spec-duplicate-criteria"
    feature_dir.mkdir(parents=True)
    criteria = ["The reporting feature works."]
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Export reports", "Import reports"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": criteria,
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    },
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/1",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_plan_human_acceptance_contract(feature_dir)

    assert any(
        "acceptance criterion must map to exactly one requirement_ref" in error
        for error in errors
    )


@pytest.mark.parametrize(
    ("coverage", "expected_error"),
    (
        (
            [
                {
                    "requirement_ref": "spec-contract.json#/scope/in/0",
                    "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                }
            ],
            "requirements are missing acceptance_coverage",
        ),
        (
            [
                {
                    "requirement_ref": "spec-contract.json#/scope/in/0",
                    "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                },
                {
                    "requirement_ref": "spec-contract.json#/scope/in/1",
                    "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                },
            ],
            "acceptance criteria are missing acceptance_coverage",
        ),
        (
            [
                {
                    "requirement_ref": "spec-contract.json#/scope/in/0",
                    "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                },
                {
                    "requirement_ref": "spec-contract.json#/scope/in/1",
                    "acceptance_ref": "spec-contract.json#/acceptance_criteria/1",
                },
                {
                    "requirement_ref": "spec-contract.json#/scope/in/99",
                    "acceptance_ref": "spec-contract.json#/acceptance_criteria/1",
                },
            ],
            "unknown requirement_ref values",
        ),
    ),
)
def test_spec_acceptance_coverage_requires_bidirectional_exact_set_closure(
    tmp_path: Path,
    coverage: list[dict[str, str]],
    expected_error: str,
) -> None:
    feature_dir = tmp_path / "specs" / "007d-spec-exact-closure"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Export reports", "Import reports"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": [
                    "A human can export a report.",
                    "A human can import a report.",
                ],
                "acceptance_coverage": coverage,
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": [
                    "spec-contract.json#/acceptance_criteria/0",
                    "spec-contract.json#/acceptance_criteria/1",
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_plan_human_acceptance_contract(feature_dir)

    assert any(expected_error in error for error in errors)


def test_spec_acceptance_coverage_uses_escaped_canonical_json_pointer_tokens(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "007e-spec-pointer-escaping"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {"in": [], "out": [], "deferred": []},
                "capability_operations": {
                    "ops/export~v1": {"id": "CAP-EXPORT", "operation": "export"}
                },
                "acceptance_criteria": ["A human can export a report."],
                "acceptance_coverage": [
                    {
                        "requirement_ref": (
                            "spec-contract.json#/capability_operations/ops~1export~0v1"
                        ),
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    assert _validate_plan_human_acceptance_contract(feature_dir) == []


def test_specify_templates_require_exact_acceptance_coverage() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template = json.loads(
        (repo_root / "templates" / "spec-contract-template.json").read_text(
            encoding="utf-8"
        )
    )
    assert template["acceptance_coverage"] == []

    prompt_paths = (
        repo_root / "templates" / "commands" / "specify.md",
        repo_root
        / "templates"
        / "command-references"
        / "specify"
        / "artifact-package.md",
        repo_root
        / "templates"
        / "command-references"
        / "specify"
        / "self-review-and-quality-gates.md",
        repo_root / "templates" / "advanced-skills" / "spx-specify" / "SKILL.md",
        repo_root
        / "templates"
        / "advanced-skills"
        / "spx-specify"
        / "references"
        / "requirements-contract.md",
    )
    for path in prompt_paths:
        content = path.read_text(encoding="utf-8")
        assert "acceptance_coverage" in content, path


def test_tasks_templates_require_dedicated_acceptance_review_scenarios() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    prompt_paths = (
        repo_root / "templates" / "commands" / "tasks.md",
        repo_root / "templates" / "advanced-skills" / "spx-tasks" / "SKILL.md",
        repo_root
        / "templates"
        / "advanced-skills"
        / "spx-tasks"
        / "references"
        / "task-graph-contract.md",
    )
    for path in prompt_paths:
        content = path.read_text(encoding="utf-8").lower()
        assert "dedicated required" in content, path
        assert "broad regression" in content, path
        assert "own `acceptance_ref`" in content, path


@pytest.mark.parametrize("acceptance_refs", ([], [""], [42]))
def test_plan_acceptance_denominator_fails_closed_when_malformed(
    tmp_path: Path, acceptance_refs: list[object]
) -> None:
    feature_dir = tmp_path / "specs" / "008-malformed-plan-acceptance"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Changed outcome"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": ["The changed outcome is visible."],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {"version": 2, "status": "ready", "acceptance_refs": acceptance_refs}
        ),
        encoding="utf-8",
    )

    assert _validate_plan_human_acceptance_contract(feature_dir)


def test_tasks_require_task_index_when_plan_has_acceptance_refs(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "009-missing-task-index"
    feature_dir.mkdir(parents=True)
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any("task-index.json is required" in error for error in errors)


def test_ready_modern_task_index_rejects_empty_human_acceptance_universe(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "010-empty-human-acceptance"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": [],
                "human_acceptance_obligations": [],
                "human_acceptance_scenarios": [],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any("non-empty Human Acceptance Universe" in error for error in errors)


def test_tasks_acceptance_denominator_fails_closed_without_spec_contract(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "011-missing-spec-denominator"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )
    (feature_dir / "spec-contract.json").unlink()

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any("spec-contract.json is required" in error for error in errors)


@pytest.mark.parametrize("criterion", (None, "", 42, {}))
def test_spec_acceptance_denominator_rejects_empty_or_non_string_criteria(
    tmp_path: Path, criterion: object
) -> None:
    feature_dir = tmp_path / "specs" / "012-invalid-spec-denominator"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["Changed outcome"],
                    "out": [],
                    "deferred": [],
                },
                "capability_operations": [],
                "acceptance_criteria": [criterion],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_plan_human_acceptance_contract(feature_dir)

    assert any("acceptance_criteria[0]" in error for error in errors)


def test_tasks_reject_version_downgrade_when_plan_has_acceptance_refs(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "013-task-index-version-downgrade"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )
    task_path = feature_dir / "task-index.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["version"] = 1
    task_path.write_text(json.dumps(task), encoding="utf-8")

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any("version must equal 2" in error for error in errors)


@pytest.mark.parametrize("required", (True, False))
def test_tasks_require_required_review_obligations_for_every_acceptance_ref(
    tmp_path: Path, required: bool
) -> None:
    feature_dir = tmp_path / "specs" / f"014-review-obligation-{required}"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )
    task_path = feature_dir / "task-index.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    if required:
        task["review_obligations"] = task["review_obligations"][:1]
    else:
        task["review_obligations"][1]["required"] = False
    task_path.write_text(json.dumps(task), encoding="utf-8")

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any(
        "required review_obligations are missing acceptance_refs" in error
        # Obligations are validated against expanded plan/spec acceptance refs.
        and "spec-contract.json#/acceptance_criteria/1" in error
        for error in errors
    )


def test_tasks_require_a_dedicated_required_review_scenario_per_acceptance_ref(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "014b-dedicated-review-scenario"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )
    task_path = feature_dir / "task-index.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["system_review_scenarios"] = [
        {
            "id": "SR-GENERIC-001",
            "entrypoint_id": "EP-001",
            "required": True,
        }
    ]
    for obligation in task["review_obligations"]:
        obligation["scenario_ids"] = ["SR-GENERIC-001"]
    for scenario in task["human_acceptance_scenarios"]:
        scenario["review_scenario_ids"] = ["SR-GENERIC-001"]
    task_path.write_text(json.dumps(task), encoding="utf-8")

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any(
        "must map to at least one dedicated required system review scenario" in error
        for error in errors
    )
    assert any(
        "must reference a dedicated required system review scenario" in error
        for error in errors
    )


@pytest.mark.parametrize("scenario_required", (None, False))
def test_tasks_require_a_required_system_review_scenario_for_every_official_entrypoint(
    tmp_path: Path, scenario_required: bool | None
) -> None:
    feature_dir = tmp_path / "specs" / f"015-entrypoint-review-{scenario_required}"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )
    task_path = feature_dir / "task-index.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["official_entrypoints"].append(
        {
            "id": "EP-002",
            "command": "python -m admin",
            "ready_signal": "admin ready",
        }
    )
    if scenario_required is not None:
        task["system_review_scenarios"].append(
            {
                "id": "SR-ADMIN-001",
                "entrypoint_id": "EP-002",
                "required": scenario_required,
            }
        )
    task_path.write_text(json.dumps(task), encoding="utf-8")

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any(
        "official entrypoints are missing required system review scenarios" in error
        and "EP-002" in error
        for error in errors
    )


def test_tasks_reject_one_generic_human_scenario_for_multiple_acceptance_refs(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "016-generic-human-scenario"
    _write_human_acceptance_universe(
        feature_dir,
        task_acceptance_refs=[
            "plan-contract.json#/acceptance_refs/0",
            "plan-contract.json#/acceptance_refs/1",
        ],
    )
    task_path = feature_dir / "task-index.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    obligation_ids = [item["id"] for item in task["human_acceptance_obligations"]]
    for obligation in task["human_acceptance_obligations"]:
        obligation["scenario_ids"] = ["HA-GENERIC-001"]
    task["human_acceptance_scenarios"] = [
        {
            "id": "HA-GENERIC-001",
            "title": "Verify the feature",
            "user_value": "Everything works",
            "actor": "human user",
            "start_state": "Application ready",
            "required": True,
            "entrypoint_id": "EP-001",
            "obligation_ids": obligation_ids,
            "review_scenario_ids": ["SR-001", "SR-002"],
            "steps": [
                {
                    "id": "HAS-GENERIC-001",
                    "action": "Use the feature",
                    "expected_result": "The feature works",
                    "evidence_requirement": "human observation",
                    "risk": "low",
                }
            ],
        }
    ]
    task_path.write_text(json.dumps(task), encoding="utf-8")

    errors = _validate_tasks_human_acceptance_contract(feature_dir)

    assert any(
        "must not span multiple acceptance_refs" in error and "HA-GENERIC-001" in error
        for error in errors
    )


def test_agent_native_ui_task_lifecycle_blocks_pending_human_review(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "fidelity_level": "high",
                            "design_sources": ["design-change.md", "ui-brief.md"],
                            "required_states": ["ready"],
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": ["src/ui/page.tsx"],
                "validation": [{"command": "npm test", "status": "passed"}],
                "review": None,
                "blockers": [],
                "ui_verification": {
                    "applicable": True,
                    "evidence_scope": "task",
                    "contract_check": "passed",
                    "evidence": [],
                    "visual_comparison": "needs-human-review",
                    "fidelity_status": "pending-human-review",
                    "reviewer": "agent",
                    "human_review_ref": "evidence/review.md",
                },
            }
        ),
        encoding="utf-8",
    )

    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])

    assert any("pending-human-review blocks" in error for error in errors)


def test_ui_lifecycle_enforces_required_human_usability_validation(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui-usability"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    evidence_dir = feature_dir / "evidence"
    lifecycle_dir.mkdir(parents=True)
    evidence_dir.mkdir()
    for name in ("a11y.json", "screen.png", "console.txt"):
        (evidence_dir / name).write_text("evidence\n", encoding="utf-8")
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                            "usability_validation": {
                                "risk_level": "high",
                                "methods": ["moderated task-based usability test"],
                                "critical_tasks": ["Complete the irreversible action"],
                                "success_criteria": [
                                    "Every participant completes without a critical error"
                                ],
                                "human_review_required": True,
                            },
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    lifecycle = {
        "task_id": "T001",
        "status": "accepted",
        "changed_paths": ["src/ui/page.tsx"],
        "validation": [{"command": "npm test", "status": "passed"}],
        "review": None,
        "blockers": [],
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "task",
            "evidence": [
                {"kind": "structure_snapshot", "ref": "evidence/a11y.json"},
                {"kind": "visual_capture", "ref": "evidence/screen.png"},
                {"kind": "runtime_diagnostics", "ref": "evidence/console.txt"},
            ],
            "contract_check": "passed",
            "runtime_evidence": "passed",
            "visual_comparison": "passed",
            "fidelity_status": "passed",
            "reviewer": "agent",
            "human_review_ref": "evidence/usability-review.md",
        },
    }
    lifecycle_path = lifecycle_dir / "T001.json"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])
    assert any("human usability validation requires a human reviewer" in error for error in errors)

    lifecycle["ui_verification"]["reviewer"] = "human"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])
    assert any("human_review_ref must reference an existing artifact" in error for error in errors)

    (evidence_dir / "usability-review.md").write_text("", encoding="utf-8")
    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])
    assert any("human_review_ref artifact must be non-empty" in error for error in errors)

    (evidence_dir / "usability-review.md").write_text(
        "# Human usability review\n\nPASS: the critical task met the approved success criteria.\n",
        encoding="utf-8",
    )
    assert _validate_task_lifecycle_records(feature_dir, ["T001"]) == []


def test_ui_lifecycle_accepts_equivalent_comparison_tolerance_with_reordered_keys(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui-comparison-tolerance"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    evidence_dir = feature_dir / "evidence"
    lifecycle_dir.mkdir(parents=True)
    evidence_dir.mkdir()
    for name in ("a11y.json", "screen.png", "console.txt"):
        (evidence_dir / name).write_text("evidence\n", encoding="utf-8")

    task_tolerance = {
        "structure": "exact",
        "geometry": {"unit": "px", "max_delta": 2},
        "motion": {"unit": "ms", "max_delta": 16},
    }
    lifecycle_tolerance = {
        "motion": {"max_delta": 16, "unit": "ms"},
        "geometry": {"max_delta": 2, "unit": "px"},
        "structure": "exact",
    }

    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                            "design_decision_ids": ["DS-001"],
                            "handoff_contract_ids": ["DH-001"],
                            "approved_visual_ref": "design/approved.html#direction-a",
                            "approved_preview_sha256": "a" * 64,
                            "approved_manifest_sha256": "b" * 64,
                            "approved_handoff_ref": "design/handoff.json",
                            "approved_handoff_sha256": "c" * 64,
                            "comparison_tolerance": task_tolerance,
                            "accepted_deviations": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    comparison_report = {
        "schema": "spec-kit-visual-comparison-v1",
        "task_id": "T001",
        "approved": {
            "visual_ref": "design/approved.html#direction-a",
            "preview_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
            "handoff_ref": "design/handoff.json",
            "handoff_sha256": "c" * 64,
            "decision_ids": ["DS-001"],
            "handoff_contract_ids": ["DH-001"],
        },
        "implementation": {"capture_refs": ["evidence/screen.png"]},
        "matrix": [
            {
                "viewport": "desktop",
                "state": "ready",
                "implementation_capture_ref": "evidence/screen.png",
                "covered_decision_ids": ["DS-001"],
                "covered_handoff_contract_ids": ["DH-001"],
                "result": "passed",
            }
        ],
        "comparison_tolerance": task_tolerance,
        "accepted_deviations": [],
        "verdict": "passed",
    }
    comparison_report_bytes = json.dumps(
        comparison_report, ensure_ascii=False, indent=2
    ).encode("utf-8")
    (evidence_dir / "comparison-report.json").write_bytes(comparison_report_bytes)

    lifecycle = {
        "task_id": "T001",
        "status": "accepted",
        "changed_paths": ["src/ui/page.tsx"],
        "validation": [{"command": "npm test", "status": "passed"}],
        "review": None,
        "blockers": [],
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "task",
            "evidence": [
                {"kind": "structure_snapshot", "ref": "evidence/a11y.json"},
                {"kind": "visual_capture", "ref": "evidence/screen.png"},
                {"kind": "runtime_diagnostics", "ref": "evidence/console.txt"},
            ],
            "contract_check": "passed",
            "runtime_evidence": "passed",
            "visual_comparison": "passed",
            "fidelity_status": "passed",
            "reviewer": "agent",
            "approved_visual_ref": "design/approved.html#direction-a",
            "approved_preview_sha256": "a" * 64,
            "approved_manifest_sha256": "b" * 64,
            "approved_handoff_ref": "design/handoff.json",
            "approved_handoff_sha256": "c" * 64,
            "comparison_tolerance": lifecycle_tolerance,
            "accepted_deviations": [],
            "covered_decision_ids": ["DS-001"],
            "covered_handoff_contract_ids": ["DH-001"],
            "implementation_capture_refs": ["evidence/screen.png"],
            "comparison_report_ref": "evidence/comparison-report.json",
            "comparison_report_sha256": hashlib.sha256(
                comparison_report_bytes
            ).hexdigest(),
        },
    }
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(lifecycle), encoding="utf-8"
    )

    assert _validate_task_lifecycle_records(feature_dir, ["T001"]) == []


def test_agent_native_current_ui_lifecycle_requires_typed_evidence_triad(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    evidence_dir = feature_dir / "evidence"
    lifecycle_dir.mkdir(parents=True)
    evidence_dir.mkdir()
    for name in ("a11y.json", "screen.png", "console.txt"):
        (evidence_dir / name).write_text("evidence\n", encoding="utf-8")
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    lifecycle = {
        "task_id": "T001",
        "status": "accepted",
        "changed_paths": ["src/ui/page.tsx"],
        "validation": [{"command": "npm test", "status": "passed"}],
        "review": None,
        "blockers": [],
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "task",
            "evidence": [
                {"kind": "structure_snapshot", "ref": "evidence/a11y.json"},
                {"kind": "visual_capture", "ref": "evidence/screen.png"},
            ],
            "contract_check": "passed",
            "runtime_evidence": "passed",
            "visual_comparison": "passed",
            "fidelity_status": "passed",
            "reviewer": "agent",
        },
    }
    lifecycle_path = lifecycle_dir / "T001.json"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    errors = _validate_task_lifecycle_records(feature_dir, ["T001"])
    assert any("runtime_diagnostics" in error for error in errors)

    lifecycle["ui_verification"]["evidence"].append(
        {"kind": "runtime_diagnostics", "ref": "evidence/console.txt"}
    )
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    assert _validate_task_lifecycle_records(feature_dir, ["T001"]) == []

    lifecycle["ui_verification"]["evidence_refs"] = [
        "evidence/a11y.json",
        "evidence/screen.png",
        "evidence/console.txt",
    ]
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    assert any(
        "evidence_refs is obsolete" in error
        for error in _validate_task_lifecycle_records(feature_dir, ["T001"])
    )


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
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("source_files_read is required" in message for message in result.errors)
    assert any(
        "source_signal_disposition is required" in message for message in result.errors
    )


def test_specify_artifact_validation_accepts_complete_must_preserve_handoff(
    tmp_path: Path,
) -> None:
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


def test_specify_artifact_validation_accepts_structured_source_evidence(
    tmp_path: Path,
) -> None:
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


def test_specify_artifact_validation_blocks_invalid_structured_source_evidence(
    tmp_path: Path,
) -> None:
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
    assert any(
        "source_evidence[0].source is required" in message for message in result.errors
    )
    assert any(
        "source_evidence[0].claim is required" in message for message in result.errors
    )
    assert any(
        "source_evidence[0].source_type is invalid" in message
        for message in result.errors
    )
    assert any(
        "source_evidence[0].evidence_status is invalid" in message
        for message in result.errors
    )
    assert any(
        "source_evidence[0].project_cognition_route must be an array of non-empty strings"
        in message
        for message in result.errors
    )
    assert any(
        "source_evidence[0].live_code_evidence must be an array of non-empty strings"
        in message
        for message in result.errors
    )
    assert any(
        "source_evidence[0].needs_refresh must be a boolean" in message
        for message in result.errors
    )
    assert any(
        "source_evidence[1] must be an object" in message for message in result.errors
    )


def test_specify_artifact_validation_blocks_ready_handoff_without_source_evidence(
    tmp_path: Path,
) -> None:
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
    assert any(
        "source_evidence must include at least one entry" in message
        for message in result.errors
    )


def test_specify_artifact_validation_blocks_non_string_source_evidence_claim(
    tmp_path: Path,
) -> None:
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
    assert any(
        "source_evidence[0].source must be a non-empty string" in message
        for message in result.errors
    )
    assert any(
        "source_evidence[0].claim must be a non-empty string" in message
        for message in result.errors
    )


def test_specify_artifact_validation_blocks_ready_gate_with_open_conflict(
    tmp_path: Path,
) -> None:
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
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "planning_gate_status" in message and "open conflicts" in message
        for message in result.errors
    )


def test_specify_artifact_validation_blocks_ready_gate_with_unreported_open_conflict(
    tmp_path: Path,
) -> None:
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
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "open_conflict_count" in message and "does not match" in message
        for message in result.errors
    )
    assert any(
        "planning_gate_status" in message and "open conflicts" in message
        for message in result.errors
    )


def test_specify_artifact_validation_blocks_ready_gate_with_unreported_hard_blocking_question(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace(
        '"type": "goal"', '"type": "blocking_question"'
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "hard_unknown_count" in message and "does not match" in message
        for message in result.errors
    )
    assert any(
        "planning_gate_status" in message and "hard unknowns" in message
        for message in result.errors
    )


def test_specify_artifact_validation_blocks_complete_coverage_with_unmapped_active_item(
    tmp_path: Path,
) -> None:
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
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "MP-001" in message and "mapped_to" in message for message in result.errors
    )


def test_specify_artifact_validation_blocks_malformed_must_preserve_id(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    payload = _valid_must_preserve_handoff_payload().replace(
        '"id": "MP-001"', '"id": "MP-ABC"'
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("MP-ABC" in message and "MP-###" in message for message in result.errors)


def test_specify_artifact_validation_blocks_dropped_item_without_user_approval(
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
        .replace('"status": "mapped"', '"status": "dropped"')
        .replace('"mapped_to": ["spec.md#Feature Goal"]', '"mapped_to": []')
    )
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "MP-001" in message and "user_decision_source" in message
        for message in result.errors
    )
    assert any(
        "MP-001" in message and "approved_risk_contract" in message
        for message in result.errors
    )


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
    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        payload, encoding="utf-8"
    )

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "MP-001" in message and "resolution_evidence" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_canonical_contract_is_missing(
    tmp_path: Path,
):
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
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8"
    )
    _write_valid_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("spec-contract.json" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_semantic_alignment_is_missing(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Upstream Intent Disposition\n\n- Demo\n\n## Out-Of-Scope Conflicts\n\n- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8"
    )
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


def test_validate_artifacts_blocks_specify_when_stage_state_fields_are_missing(
    tmp_path: Path,
):
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
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8"
    )
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


def test_validate_artifacts_blocks_specify_when_legacy_state_fields_are_present(
    tmp_path: Path,
):
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
    assert any(
        "legacy sp-specify state field: coverage_mode" in message
        for message in result.errors
    )
    assert any(
        "legacy sp-specify state field: observer_status" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_upstream_intent_disposition_is_missing(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text(
        "# Alignment\n\n## Semantic Term Decisions\n\n- None\n\n## Out-Of-Scope Conflicts\n\n- None\n",
        encoding="utf-8",
    )
    (feature_dir / "context.md").write_text(
        "# Context\n\n## Planning Context\n\n- Demo\n", encoding="utf-8"
    )
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


def test_validate_artifacts_blocks_reference_implementation_spec_without_fidelity_requirements(
    tmp_path: Path,
):
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
    workflow_state_template = (
        Path(__file__).resolve().parents[2] / "templates" / "workflow-state-template.md"
    ).read_text(encoding="utf-8")

    assert "## Stage State" in workflow_state_template
    assert "## Review State" in workflow_state_template
    assert "current_stage" in workflow_state_template
    assert "context-intake" in workflow_state_template
    assert "artifact-review" in workflow_state_template
    assert "user-review" in workflow_state_template
    assert "last_user_reviewed_artifact_state" in workflow_state_template
    assert "canonical_contract_ref" in workflow_state_template
    assert "canonical_contract_revision" in workflow_state_template
    assert "semantic_delta" in workflow_state_template
    assert "next_action" in workflow_state_template
    assert "blocker_reason" in workflow_state_template
    assert "final_handoff_decision" in workflow_state_template
    assert "## Fixed Lifecycle State" not in workflow_state_template
    assert "active_profile" not in workflow_state_template
    assert "coverage_mode" not in workflow_state_template
    assert "observer_status" not in workflow_state_template


def test_validate_artifacts_accepts_fixed_lifecycle_state_and_draft_contract(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_blocks_specify_when_lossless_journal_is_missing(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_warns_for_legacy_specify_package_without_lossless_files(
    tmp_path: Path,
) -> None:
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
    legacy_marker.write_text(
        '{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert any(
        "legacy" in message.lower() and "lossless" in message.lower()
        for message in result.warnings
    )


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
    legacy_marker.write_text(
        '{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "missing required artifact: spec.md" in message for message in result.errors
    )


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
    legacy_marker.write_text(
        '{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "alignment.md" in message and "Alignment Summary" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_checkpoint_pointer_is_not_in_journal(
    tmp_path: Path,
) -> None:
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
    assert any(
        "last_checkpoint_id" in message and "EVT-999999" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_workflow_checkpoint_is_not_checkpoint_event(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
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
    journal_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )

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
    assert any(
        "workflow-state.md" in message and "last_checkpoint_id" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_lossless_resume_state_field_is_missing(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state_path.write_text(
        workflow_state_path.read_text(encoding="utf-8").replace(
            "- last_event_id: `EVT-000001`\n", ""
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "Lossless Resume State last_event_id" in message and "required" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_journal_event_type_is_unknown(
    tmp_path: Path,
) -> None:
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
    assert any(
        "unknown event type" in message and "made_up_event" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_journal_schema_version_is_boolean(
    tmp_path: Path,
) -> None:
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
    assert any(
        "schema_version" in message and "integer" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_checkpoint_payload_is_incomplete(
    tmp_path: Path,
) -> None:
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
    assert any(
        "checkpoint_written" in message and "manifest_hash" in message
        for message in result.errors
    )
    assert any(
        "checkpoint_event_id" in message and "event_id" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_stage_artifact_event_references_unknown_event(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
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
    journal_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "payload.input_event_range" in message and "EVT-999999" in message
        for message in result.errors
    )
    assert any(
        "payload.key_event_ids" in message and "EVT-999998" in message
        for message in result.errors
    )


def test_validate_artifacts_accepts_decision_events_with_evidence_ids_without_basis(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_legacy_specify_package(feature_dir)

    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
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
    journal_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )

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
    assert any(
        "compiled_from.key_events" in message and "EVT-999998" in message
        for message in result.errors
    )
    assert any(
        "compiled_from.event_range" in message and "EVT-999999" in message
        for message in result.errors
    )


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
    assert any(
        "stages.facts-lock.event_range" in message and "EVT-999999" in message
        for message in result.errors
    )
    assert any(
        "stages.facts-lock.last_compiled_event_id" in message
        and "EVT-999998" in message
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
    assert any(
        "stages.facts-lock.event_range" in message and "required" in message
        for message in result.errors
    )
    assert any(
        "stages.facts-lock.last_compiled_event_id" in message and "required" in message
        for message in result.errors
    )
    assert any(
        "stages.facts-lock.artifact_hash" in message and "required" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_stage_enum_drifts(
    tmp_path: Path,
) -> None:
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
    assert any(
        "canonical stage" in message.lower() or "question-batch" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_manifest_stage_keys_are_incomplete(
    tmp_path: Path,
) -> None:
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
    assert any(
        "stages missing" in message.lower() and "release-decision" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_specify_when_manifest_stage_artifact_path_drifts(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_blocks_specify_when_canonical_stage_enum_is_missing(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_blocks_specify_when_canonical_stage_enum_is_not_a_list(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_blocks_specify_when_stage_artifact_uses_wrong_stage(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_blocks_specify_when_handoff_artifact_uses_compile_stage(
    tmp_path: Path,
) -> None:
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


def test_validate_artifacts_blocks_specify_when_closed_stage_lacks_compiled_from(
    tmp_path: Path,
) -> None:
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
    assert any(
        "brainstorming/facts.json" in message and "compiled_from" in message
        for message in result.errors
    )


def test_validate_artifacts_requires_reference_implementation_sections_as_headings(
    tmp_path: Path,
):
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


def test_validate_artifacts_skips_reference_sections_when_profile_is_not_active(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## User Scenarios\n\nDemo scenario.\n", encoding="utf-8"
    )
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_reference_implementation_spec_with_fidelity_requirements(
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
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Demo task in src/demo.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_task_generation_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir, include_tasks=True)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_tasks_without_unused_lane_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Demo task in src/demo.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_acceptance_denominator(feature_dir, include_tasks=True)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_plan_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_plan_without_unused_lane_outputs(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (feature_dir / "quickstart.md").write_text("# Quickstart\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "test_design_gate": _unselected_test_design_gate(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_minimal_acceptance_denominator(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_plan_with_nested_plan_contract(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan").mkdir()
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    (feature_dir / "plan-contract.json").unlink()
    (feature_dir / "plan" / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "test_design_gate": _unselected_test_design_gate(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_minimal_acceptance_denominator(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_deep_research_outputs_when_present(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        _valid_deep_research_artifact(), encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )

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
    (feature_dir / "deep-research.md").write_text(
        _not_needed_deep_research_artifact(), encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_accepts_runtime_owned_deep_research_package(
    tmp_path: Path, unified_runtime_env: None
):
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_runtime_deep_research_spec(feature_dir)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _publish_runtime_not_needed_deep_research(project, feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_tampered_runtime_deep_research_evidence(
    tmp_path: Path, unified_runtime_env: None
):
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_runtime_deep_research_spec(feature_dir)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _publish_runtime_not_needed_deep_research(project, feature_dir)
    (project / "docs" / "deep-research-proof.txt").write_text(
        "tampered proof\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("runtime" in message.lower() for message in result.errors)
    assert any("digest changed" in message.lower() for message in result.errors)


def test_validate_artifacts_accepts_research_alias_for_deep_research_outputs(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        _not_needed_deep_research_artifact(), encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_ambiguous_deep_research_not_needed_outputs(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        "# Deep Research\n\n**Status**: Not needed\n\nNo research needed.\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Feasibility Decision" in message for message in result.errors)
    assert any("Planning Handoff" in message for message in result.errors)


def test_validate_artifacts_blocks_deep_research_without_planning_handoff_schema(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        "# Deep Research\n\nRaw notes only.\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "deep-research", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Planning Handoff" in message for message in result.errors)
    assert any("Evidence Quality Rubric" in message for message in result.errors)
    assert any("CAP-001" in message for message in result.errors)


def test_validate_artifacts_blocks_plan_when_deep_research_handoff_is_not_consumed(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        _valid_deep_research_artifact(), encoding="utf-8"
    )
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Design\n\nUse the adapter boundary.\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "Deep Research Traceability Matrix" in message for message in result.errors
    )
    assert any("PH-001" in message for message in result.errors)


def test_validate_artifacts_accepts_plan_consuming_deep_research_handoff(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        _valid_deep_research_artifact(), encoding="utf-8"
    )
    (feature_dir / "plan.md").write_text(
        """# Plan

## Deep Research Traceability Matrix

| Plan Decision | Handoff ID | Capability ID | Track ID | Evidence / Spike ID | Evidence Quality | Plan Action |
| --- | --- | --- | --- | --- | --- | --- |
| Preserve adapter boundary | PH-001 | CAP-001 | TRK-001 | EVD-001, SPK-001 | high / constraining | Implement the adapter boundary in design |
""",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_plan_without_test_design_gate(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)
    plan_path = feature_dir / "plan-contract.json"
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_payload.pop("test_design_gate")
    plan_path.write_text(json.dumps(plan_payload) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("test_design_gate is required" in error for error in result.errors)
    assert any("sp-plan" in error for error in result.errors)


def test_validate_artifacts_blocks_plan_with_invalid_test_design_gate_decision(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)
    plan_path = feature_dir / "plan-contract.json"
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_payload["test_design_gate"]["decision"] = "implicit"
    plan_path.write_text(json.dumps(plan_payload) + "\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any(
        "test_design_gate.decision" in error
        and "not_selected, selected, or required" in error
        for error in result.errors
    )


def test_validate_artifacts_requires_exact_runtime_deep_research_plan_binding(
    tmp_path: Path, unified_runtime_env: None
):
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_runtime_deep_research_spec(feature_dir)
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)
    published = _publish_runtime_not_needed_deep_research(project, feature_dir)
    plan_path = feature_dir / "plan-contract.json"
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_payload["deep_research_binding"] = {
        "decision": "required",
        "handoff_ref": published["handoff_ref"],
        "handoff_sha256": published["handoff_sha256"],
        "source_spec_sha256": published["source_spec_sha256"],
        "state_revision": published["state_revision"],
        "claim_status": published["claim_status"],
        "handoff_ids": published["handoff_ids"],
    }
    plan_path.write_text(json.dumps(plan_payload) + "\n", encoding="utf-8")

    accepted = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert accepted.status == "ok"
    assert accepted.errors == []

    plan_payload["deep_research_binding"]["source_spec_sha256"] = "0" * 64
    plan_path.write_text(json.dumps(plan_payload) + "\n", encoding="utf-8")
    rejected = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert rejected.status == "blocked"
    assert any(
        "source_spec_sha256 does not match" in message for message in rejected.errors
    )


def test_validate_artifacts_requires_empty_binding_when_deep_research_is_not_selected(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_runtime_deep_research_spec(feature_dir)
    spec_path = feature_dir / "spec-contract.json"
    spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_payload["feasibility_gate"] = {
        "decision": "not_selected",
        "capability_refs": [],
        "reason_refs": [],
    }
    spec_path.write_text(json.dumps(spec_payload) + "\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)
    plan_path = feature_dir / "plan-contract.json"
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_payload["deep_research_binding"] = {
        "decision": "not_selected",
        "handoff_ref": None,
        "handoff_sha256": None,
        "source_spec_sha256": None,
        "state_revision": None,
        "claim_status": None,
        "handoff_ids": [],
    }
    plan_path.write_text(json.dumps(plan_payload) + "\n", encoding="utf-8")

    accepted = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert accepted.status == "ok"
    assert accepted.errors == []

    plan_payload["deep_research_binding"]["handoff_ref"] = (
        ".specify/features/001-demo/research/handoff-to-plan.json"
    )
    plan_path.write_text(json.dumps(plan_payload) + "\n", encoding="utf-8")
    rejected = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert rejected.status == "blocked"
    assert any("handoff_ref must be null" in message for message in rejected.errors)


def test_validate_artifacts_blocks_plan_when_handoff_id_is_outside_traceability_matrix(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "deep-research.md").write_text(
        _valid_deep_research_artifact(), encoding="utf-8"
    )
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
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("PH-001" in message for message in result.errors)


def test_validate_artifacts_ignores_non_handoff_ph_ids_when_validating_plan(
    tmp_path: Path,
):
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
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    _write_minimal_acceptance_denominator(feature_dir)

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
    (memory_dir / "constitution.md").write_text(
        "# Demo Constitution\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "constitution", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_triggered_consequence_handoff_without_analysis(
    tmp_path: Path,
):
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


def test_validate_artifacts_blocks_plan_when_consequence_contract_is_not_designed(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Design\n\nClose the team.\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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


def test_validate_artifacts_blocks_plan_when_nested_consequence_contract_is_not_designed(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan").mkdir()
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Design\n\nClose the team.\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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


def test_validate_artifacts_blocks_plan_when_consequence_decision_does_not_cover_obligation(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Operational Consequence Design\n\nDecision recorded.\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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
    assert any(
        "operational_consequence_decisions" in message for message in result.errors
    )


def test_validate_artifacts_accepts_plan_when_decision_covers_obligation_id(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(
        "# Plan\n\n## Operational Consequence Design\n\nDecision recorded.\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    _write_minimal_planning_outputs(feature_dir)
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "test_design_gate": _unselected_test_design_gate(),
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "team close has running-worker semantics",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [
                        {"object": "worker", "reason": "running workers are affected"}
                    ],
                    "state_behavior_matrix": [
                        {"state": "running", "behavior": "drain before close completes"}
                    ],
                    "dependency_impact": [
                        {
                            "surface": "submit-result",
                            "impact": "late result policy must be defined",
                        }
                    ],
                    "recovery_and_validation": [
                        {"validation": "pytest tests/test_team_close.py -q"}
                    ],
                    "coverage_gaps": [
                        {"gap": "none", "decision": "covered by plan decision"}
                    ],
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
    _write_minimal_acceptance_denominator(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_validate_artifacts_blocks_tasks_when_consequence_obligation_is_unmapped(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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
                    "affected_object_map": [
                        {"object": "worker", "reason": "running workers are affected"}
                    ],
                    "state_behavior_matrix": [
                        {"state": "running", "behavior": "drain before close completes"}
                    ],
                    "dependency_impact": [
                        {
                            "surface": "submit-result",
                            "impact": "late result policy must be defined",
                        }
                    ],
                    "recovery_and_validation": [
                        {"validation": "pytest tests/test_team_close.py -q"}
                    ],
                    "coverage_gaps": [
                        {"gap": "none", "decision": "covered by task mapping"}
                    ],
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
                "tasks": [{"task_id": "T001"}],
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

    assert result.status == "blocked"
    assert any("CA-001" in message for message in result.errors)
    assert any(
        "consequence" in message.lower() and "task-index.json" in message
        for message in result.errors
    )


def test_validate_artifacts_blocks_tasks_when_triggered_handoff_has_no_consequence_details(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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


def test_validate_artifacts_blocks_tasks_when_plan_contract_obligation_is_unmapped(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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
            {
                "version": 1,
                "status": "ready",
                "tasks": [{"task_id": "T001"}],
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

    assert result.status == "blocked"
    assert any("CA-001" in message for message in result.errors)
    assert any("task-index.json" in message for message in result.errors)


def test_validate_artifacts_blocks_tasks_when_nested_plan_contract_obligation_is_unmapped(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan").mkdir()
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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
            {
                "version": 1,
                "status": "ready",
                "tasks": [{"task_id": "T001"}],
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

    assert result.status == "blocked"
    assert any("CA-002" in message for message in result.errors)
    assert any("task-index.json" in message for message in result.errors)


def test_validate_artifacts_blocks_tasks_when_brainstorming_handoff_obligation_is_unmapped(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "brainstorming").mkdir()
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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
            {
                "version": 1,
                "status": "ready",
                "tasks": [{"task_id": "T001"}],
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

    assert result.status == "blocked"
    assert any("CA-003" in message for message in result.errors)
    assert any("task-index.json" in message for message in result.errors)


def test_validate_artifacts_accepts_tasks_when_consequence_obligation_is_mapped(
    tmp_path: Path,
):
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
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
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
                    "affected_object_map": [
                        {"object": "worker", "reason": "running workers are affected"}
                    ],
                    "state_behavior_matrix": [
                        {"state": "running", "behavior": "drain before close completes"}
                    ],
                    "dependency_impact": [
                        {
                            "surface": "submit-result",
                            "impact": "late result policy must be defined",
                        }
                    ],
                    "recovery_and_validation": [
                        {"validation": "pytest tests/test_team_close.py -q"}
                    ],
                    "coverage_gaps": [
                        {"gap": "none", "decision": "covered by task mapping"}
                    ],
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
    _write_minimal_acceptance_denominator(feature_dir, include_tasks=True)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
