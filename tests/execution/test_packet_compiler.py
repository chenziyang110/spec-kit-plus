import json
from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import (
    _ui_context_nav,
    _ui_contract_from_task_entry,
    compile_worker_task_packet,
)
from specify_cli.execution.packet_schema import UIContract
from specify_cli.execution.packet_validator import PacketValidationError
from specify_cli.execution.result_schema import (
    RuleAcknowledgement,
    UIVerification,
    ValidationResult,
    WorkerTaskResult,
)
from specify_cli.execution.result_validator import validate_worker_task_result
from specify_cli.task_authoring import _render_tasks_markdown


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


def _interaction_contract(row_id: str, input_method: str) -> dict[str, object]:
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


def _editing_contract(row_id: str) -> dict[str, object]:
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


def test_task_markdown_projects_professional_ui_contract_without_breaking_table() -> None:
    task_index = {
        "tasks": [
            {
                "id": "T001",
                "objective": "Implement settings UI",
                "status": "pending",
                "parallel": False,
                "story_id": "US1",
                "read_scope": [],
                "expected_write_scope": ["src/settings.tsx"],
                "required_refs": [],
                "test_case_refs": [],
                "test_data_refs": [],
                "dependencies": [],
                "acceptance": [],
                "verification": [],
                "consequence_obligation_ids": [],
                "ui_contract": {
                    "fidelity_level": "high",
                    "interaction_matrix": [{"immediate_feedback": "screen | dialog"}],
                    "editing_matrix": [{"surface": "settings | form"}],
                    "required_states": ["ready"],
                    "data_state_matrix": [{"state": "ready"}],
                    "accessibility_matrix": [{"surface": "settings form"}],
                    "navigation_matrix": [{"entry": "settings index"}],
                    "content_matrix": [{"copy": "Saved | retry"}],
                    "component_contracts": [{"component": "settings form"}],
                    "responsive_matrix": [{"viewport": "390"}],
                    "motion_contract": {"purpose": "feedback | continuity"},
                    "usability_validation": {"risk_level": "medium"},
                    "visual_acceptance_matrix": [{"viewport": "390"}],
                    "required_evidence": ["visual_capture"],
                },
            }
        ]
    }

    markdown = _render_tasks_markdown(task_index, title="Settings")

    for field in (
        "accessibility_matrix",
        "navigation_matrix",
        "content_matrix",
        "editing_matrix",
        "motion_contract",
        "usability_validation",
    ):
        assert f"| {field} |" in markdown
    assert "screen \\| dialog" in markdown
    assert "Saved \\| retry" in markdown
    assert "settings \\| form" in markdown


def test_compile_worker_task_packet_prefers_canonical_task_index_for_jit_packet(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    memory_dir = project_root / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve public behavior and prove validation.\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "user_confirmed_deferral_refs": ["DEC-001"],
                "tasks": [
                    {
                        "id": "T017",
                        "objective": "Implement auth flow",
                        "expected_write_scope": ["src/services/auth_service.py"],
                        "read_scope": ["src/contracts/auth.py"],
                        "required_refs": ["src/contracts/auth.py"],
                        "forbidden_drift": ["Do not create a parallel auth stack"],
                        "acceptance": ["Auth flow passes the real service test"],
                        "verification": ["pytest tests/unit/test_auth_service.py -q"],
                        "must_preserve_refs": ["MP-001"],
                        "consequence_obligation_refs": ["CA-001"],
                        "capability_operation_refs": ["CAP-auth"],
                        "required_consumer_evidence": ["real_entrypoint_evidence"],
                        "user_confirmed_deferral_refs": ["DEC-002"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.objective == "Implement auth flow"
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert "src/contracts/auth.py" in packet.scope.read_scope
    assert packet.validation_gates == ["pytest tests/unit/test_auth_service.py -q"]
    assert packet.acceptance_criteria == ["Auth flow passes the real service test"]
    assert packet.capability_operations == ["CAP-auth"]
    assert packet.required_evidence == ["real_entrypoint_evidence"]
    assert packet.user_confirmed_deferral_refs == ["DEC-001", "DEC-002"]
    assert [item.id for item in packet.must_preserve_obligations] == ["MP-001"]
    assert [item.obligation_id for item in packet.consequence_obligations] == ["CA-001"]


@pytest.mark.parametrize(
    ("bypass_visual_ref", "bypass_handoff_ref"),
    [
        (
            ".specify/design/changes/UD-0042/previews/custom.html#direction-x",
            ".specify/design/changes/UD-0042/previews/custom.handoff.json",
        ),
        (
            ".specify/design/changes/UD-0042/previews/round-01.html?view=1#direction-x",
            ".specify/design/changes/UD-0042/previews/round-01.handoff.json",
        ),
        (
            ".specify/design/changes/UD-0042/previews/round-01.html#direction-x",
            ".specify/design/changes/UD-0042/previews/round-99.handoff.json",
        ),
        (
            ".specify/design/changes/UD-0042/archive/round-01.html#direction-x",
            ".specify/design/changes/UD-0042/archive/round-99.handoff.json",
        ),
    ],
)
def test_compile_worker_task_packet_prefers_structured_task_index_ui_contract(
    tmp_path: Path,
    bypass_visual_ref: str,
    bypass_handoff_ref: str,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-ui-feature"
    feature_dir.mkdir(parents=True)
    memory_dir = project_root / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve the approved UI contract.\n",
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "ui_design_contract": {
                    "ui_applicable": True,
                    "entry_points": ["/settings"],
                    "token_strategy": ["reuse settings tokens"],
                    "component_strategy": ["reuse settings form controls"],
                },
                "context_capsule": {
                    "minimal_live_reads": ["src/ui/theme.ts"],
                    "validation_routes": ["tests/e2e/settings.spec.ts"],
                },
            }
        ),
        encoding="utf-8",
    )
    task_index = {
                "version": 2,
                "status": "ready",
                "tasks": [
                    {
                        "id": "T021",
                        "objective": "Implement the responsive settings surface",
                        "expected_write_scope": ["src/ui/settings.tsx"],
                        "verification": ["npm test -- settings-ui"],
                        "acceptance": ["Desktop and mobile states match the UI brief"],
                        "ui_contract": {
                            "design_change_id": "UD-0042",
                            "design_change_ref": ".specify/design/changes/UD-0042/design-change.md",
                            "design_change_sha256": "a" * 64,
                            "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
                            "ui_work_type": "feature-extension",
                            "surface_type": "product-workspace",
                            "platforms": ["web"],
                            "style_authority": {
                                "mode": "inherit-existing",
                                "scope_level": "feature-partial",
                                "source_refs": [
                                    "src/ui/theme.ts",
                                    "src/ui/settings.tsx",
                                ],
                                "protected_surfaces": [
                                    "global-shell",
                                    "shared-components",
                                ],
                                "allowed_style_delta_surfaces": [],
                                "authorization_source": None,
                            },
                            "subject": "account settings",
                            "audience": "signed-in account owners",
                            "single_job": "review and update account preferences",
                            "visual_thesis": "compact hierarchy keeps settings scannable",
                            "content_thesis": "render real preference labels and saved values",
                            "interaction_thesis": "changes provide immediate local feedback",
                            "signature_element": "persistent section progress rail",
                            "approved_visual_ref": ".specify/design/changes/UD-0042/previews/round-01.html#settings-direction",
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
                            "design_sources": [
                                ".specify/design/changes/UD-0042/design-change.md",
                                ".specify/design/changes/UD-0042/design-contract.json",
                                "specs/001-ui-feature/ui-brief.md",
                            ],
                            "reference_notes": "specs/001-ui-feature/ui-reference-notes.md",
                            "visual_target": "specs/001-ui-feature/ui-target.html",
                            "reference_intents": [
                                {
                                    "ref": "specs/001-ui-feature/ui-target.html",
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
                            "surface_catalog": [
                                {
                                    "id": "DH-SURFACE-WEB-001",
                                    "profile_id": "web",
                                    "name": "Settings",
                                    "kind": "web",
                                    "entrypoint_id": "EP-WEB-SETTINGS",
                                    "source_refs": ["src/ui/settings.tsx"],
                                    "specimen_ids": ["SP-WEB-SETTINGS-001"],
                                    "component_ids": ["DH-COMP-001"],
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
                                    "id": "DH-SCENARIO-WEB-001",
                                    "surface_id": "DH-SURFACE-WEB-001",
                                    "name": "Settings loading mouse save",
                                    "risk": "medium",
                                    "required": True,
                                    "interaction_script": {
                                        "preconditions": [
                                            "The settings form is rendered at the compact viewport.",
                                            "Settings data is loading.",
                                        ],
                                        "start_state_id": "DH-DATA-001",
                                        "branches": [
                                            {
                                                "conditions": ["success"],
                                                "setup": "Complete the save once.",
                                                "expected_state_id": "DH-DATA-001",
                                                "expected_feedback": "Show the saved values and confirmation.",
                                                "focus_behavior": "Keep visible focus on the Save control.",
                                                "announcement": "Announce that the settings were saved.",
                                                "continuation": "Remain on the settings form.",
                                            },
                                            {
                                                "conditions": ["failure", "timeout", "cancel"],
                                                "setup": "Fail, time out, or cancel the save before completion.",
                                                "expected_state_id": "DH-DATA-001",
                                                "expected_feedback": "Keep the unsaved values and show recovery.",
                                                "focus_behavior": "Move focus only for correction.",
                                                "announcement": "Announce failure without stealing focus.",
                                                "continuation": "Retry without losing entered values.",
                                            },
                                            {
                                                "conditions": ["retry", "duplicate", "out_of_order"],
                                                "setup": "Repeat, retry, or resolve saves out of order.",
                                                "expected_state_id": "DH-DATA-001",
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
                                    "interaction_ids": ["DH-INT-001"],
                                    "editing_ids": ["DH-EDIT-001"],
                                    "data_state_ids": ["DH-DATA-001"],
                                    "accessibility_ids": ["DH-A11Y-001"],
                                    "navigation_ids": ["DH-NAV-001"],
                                    "content_ids": ["DH-CONTENT-001"],
                                    "responsive_ids": ["DH-RESP-001"],
                                    "motion_transition_ids": ["DH-MOTION-001"],
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
                                _interaction_contract("DH-INT-001", "mouse"),
                                _interaction_contract("DH-INT-002", "keyboard"),
                            ],
                            "editing_matrix": [_editing_contract("DH-EDIT-001")],
                            "data_state_matrix": [
                                {
                                    "id": "DH-DATA-001",
                                    "surface": "settings form",
                                    "state": "loading",
                                    "data_condition": "settings are still being fetched",
                                    "expectation": "show skeleton rows in the final layout",
                                    "decision_ids": ["DS-DATA-001"],
                                },
                                {
                                    "id": "DH-DATA-002",
                                    "surface": "settings form",
                                    "state": "success",
                                    "data_condition": "settings data is available",
                                    "expectation": "render saved values and section summaries",
                                    "decision_ids": ["DS-DATA-001"],
                                }
                            ],
                            "accessibility_matrix": [
                                {
                                    "id": "DH-A11Y-001",
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
                                    "id": "DH-NAV-001",
                                    "surface": "settings section",
                                    "entry": "settings index",
                                    "destination": "selected settings section",
                                    "trigger": "activate section link",
                                    "back_behavior": "return to the prior section and scroll position",
                                    "deep_link_behavior": "open the addressed settings section",
                                    "interruption_recovery": "restore unsaved values after reauthentication",
                                    "decision_ids": ["DS-NAV-001"],
                                }
                            ],
                            "content_matrix": [
                                {
                                    "id": "DH-CONTENT-001",
                                    "surface": "settings save feedback",
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
                                    "id": "DH-COMP-001",
                                    "component": "settings form",
                                    "anatomy": ["section heading", "fields", "actions"],
                                    "decision_ids": ["DS-COMP-001"],
                                    "interaction_modes": ["mouse", "keyboard"],
                                    "data_scenarios": [
                                        {
                                            "state": "loading",
                                            "data_condition": "settings are still loading",
                                            "expectation": "reserve layout with skeleton rows",
                                        },
                                        {
                                            "state": "success",
                                            "data_condition": "settings data is available",
                                            "expectation": "render saved values and section summaries",
                                        }
                                    ],
                                    "required_states": ["loading", "error", "success"],
                                    "variants": ["default", "compact"],
                                    "content_constraints": ["labels wrap without truncation"],
                                    "semantic_token_refs": ["color.feedback.success"],
                                    "governance": "extend",
                                    "iconography": "status icons include accessible text",
                                    "adoption": {
                                        "resource_id": "material-ui",
                                        "action": "extend",
                                        "package": "@mui/material",
                                        "version": "^7.0.0",
                                        "license": "MIT",
                                        "source_ref": "package.json#/dependencies/@mui/material",
                                        "component_refs": ["@mui/material/TextField"],
                                        "reason_codes": ["installed", "live-style-authority"],
                                        "selection_basis_refs": [
                                            "professional_skill_route.mature_web_ui_selection"
                                        ],
                                        "permission_gate": "not-required",
                                        "permission_status": "authorized",
                                    },
                                }
                            ],
                            "responsive_matrix": [
                                {
                                    "id": "DH-RESP-001",
                                    "viewport": "390",
                                    "state": "loading",
                                    "adaptation": "stack settings sections",
                                    "stretch_behavior": "grow field rows without clipping labels",
                                    "overflow_behavior": "keep the page scrollable with sticky actions intact",
                                    "decision_ids": ["DS-RESP-001"],
                                }
                            ],
                            "motion_contract": {
                                "purpose": "show saved-state feedback",
                                "transitions": [
                                    {
                                        "id": "DH-MOTION-001",
                                        "surface": "save feedback",
                                        "trigger": "save succeeds",
                                        "response": "show confirmation without moving focus",
                                        "duration_ms": 180,
                                        "easing": "ease-out",
                                        "interrupt_behavior": "replace with the latest save result",
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
                                "human_review_required": False,
                                "smoothness_acceptance_ids": [
                                    "focus-continuity",
                                    "pending-cancel-feedback",
                                    "duplicate-activation",
                                    "reduced-motion",
                                ],
                            },
                            "visual_acceptance_matrix": [
                                {
                                    "id": "DH-VA-001",
                                    "viewport": "390",
                                    "state": "loading",
                                    "evidence": "visual_capture",
                                    "decision_ids": ["DS-RESP-001"],
                                }
                            ],
                            "comparison_tolerance": COMPARISON_TOLERANCE,
                            "accepted_deviations": [],
                            "fidelity_level": "high",
                            "must_preserve": ["compact two-column hierarchy"],
                            "may_adapt": ["framework markup"],
                            "must_not": ["collapse settings into cards"],
                            "required_states": ["loading", "error", "success"],
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
    task_index_path = feature_dir / "task-index.json"
    task_index_path.write_text(
        json.dumps(task_index),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T021 Implement UI without duplicated markdown contract\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError, match="change-local visual round"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T021",
        )

    ui_contract = task_index["tasks"][0]["ui_contract"]
    ui_contract.update(
        {
            "approved_visual_ref": bypass_visual_ref,
            "approved_preview_sha256": "b" * 64,
            "approved_manifest_sha256": "c" * 64,
            "approved_handoff_ref": bypass_handoff_ref,
            "approved_handoff_sha256": "d" * 64,
            "handoff_contract_ids": [
                "DH-SURFACE-WEB-001",
                "DH-SCENARIO-WEB-001",
                "DH-INT-001",
                "DH-INT-002",
                "DH-EDIT-001",
                "DH-DATA-001",
                "DH-DATA-002",
                "DH-A11Y-001",
                "DH-NAV-001",
                "DH-CONTENT-001",
                "DH-COMP-001",
                "DH-RESP-001",
                "DH-MOTION-001",
                "DH-VA-001",
            ],
        }
    )
    task_index_path.write_text(json.dumps(task_index), encoding="utf-8")
    with pytest.raises(PacketValidationError, match="change-local visual round"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T021",
        )

    ui_contract.update(
        {
            "approved_visual_ref": ".specify/design/changes/UD-0042/previews/round-01.html#direction-settings",
            "approved_preview_sha256": "b" * 64,
            "approved_manifest_sha256": "c" * 64,
            "approved_handoff_ref": ".specify/design/changes/UD-0042/previews/round-01.handoff.json",
            "approved_handoff_sha256": "d" * 64,
            "handoff_contract_ids": [
                "DH-SURFACE-WEB-001",
                "DH-SCENARIO-WEB-001",
                "DH-INT-001",
                "DH-INT-002",
                "DH-EDIT-001",
                "DH-DATA-001",
                "DH-DATA-002",
                "DH-A11Y-001",
                "DH-NAV-001",
                "DH-CONTENT-001",
                "DH-COMP-001",
                "DH-RESP-001",
                "DH-MOTION-001",
                "DH-VA-001",
            ],
        }
    )
    task_index_path.write_text(json.dumps(task_index), encoding="utf-8")

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T021",
    )

    assert packet.ui_contract.fidelity_level == "high"
    assert packet.ui_contract.surface_type == "product-workspace"
    assert packet.ui_contract.style_authority == {
        "mode": "inherit-existing",
        "scope_level": "feature-partial",
        "source_refs": ["src/ui/theme.ts", "src/ui/settings.tsx"],
        "protected_surfaces": ["global-shell", "shared-components"],
        "allowed_style_delta_surfaces": [],
        "authorization_source": None,
    }
    assert packet.ui_contract.design_change_id == "UD-0042"
    assert (
        packet.ui_contract.design_change_ref
        == ".specify/design/changes/UD-0042/design-change.md"
    )
    assert packet.ui_contract.design_change_sha256 == "a" * 64
    assert (
        packet.ui_contract.design_contract_ref
        == ".specify/design/changes/UD-0042/design-contract.json"
    )
    assert (
        packet.ui_contract.approved_visual_ref
        == ".specify/design/changes/UD-0042/previews/round-01.html#direction-settings"
    )
    assert packet.ui_contract.reference_intents[0]["intent"] == "preserve-structure"
    assert (
        packet.ui_contract.real_content_plan[0]["source_ref"]
        == "src/settings/schema.ts"
    )
    assert packet.ui_contract.interaction_matrix[0]["input"] == "mouse"
    assert packet.ui_contract.editing_matrix[0]["composition_behavior"]
    assert packet.ui_contract.data_state_matrix[0]["state"] == "loading"
    assert packet.ui_contract.accessibility_matrix[0]["id"] == "DH-A11Y-001"
    assert packet.ui_contract.navigation_matrix[0]["id"] == "DH-NAV-001"
    assert packet.ui_contract.content_matrix[0]["id"] == "DH-CONTENT-001"
    assert packet.ui_contract.motion_contract["transitions"][0]["duration_ms"] == 180
    assert packet.ui_contract.usability_validation["risk_level"] == "medium"
    assert packet.ui_contract.usability_validation["smoothness_acceptance_ids"] == [
        "focus-continuity",
        "pending-cancel-feedback",
        "duplicate-activation",
        "reduced-motion",
    ]
    assert packet.ui_contract.component_contracts[0]["governance"] == "extend"
    assert packet.ui_contract.component_contracts[0]["adoption"] == {
        "resource_id": "material-ui",
        "action": "extend",
        "package": "@mui/material",
        "version": "^7.0.0",
        "license": "MIT",
        "source_ref": "package.json#/dependencies/@mui/material",
        "component_refs": ["@mui/material/TextField"],
        "reason_codes": ["installed", "live-style-authority"],
        "selection_basis_refs": [
            "professional_skill_route.mature_web_ui_selection"
        ],
        "permission_gate": "not-required",
        "permission_status": "authorized",
    }
    assert packet.ui_contract.required_states == ["loading", "error", "success"]
    assert packet.ui_contract.must_not == ["collapse settings into cards"]
    assert packet.ui_contract.required_evidence == [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
    assert {item["kind"] for item in packet.context_nav} >= {
        "ui_entrypoint",
        "design_source",
        "minimal_live_read",
        "visual_test_route",
    }
    assert "src/ui/theme.ts" in {item.path for item in packet.context_bundle}
    assert all("#" not in item.path for item in packet.context_bundle)
    reference_paths = [item.path for item in packet.required_references]
    assert ".specify/design/changes/UD-0042/design-change.md" in reference_paths
    assert (
        ".specify/design/changes/UD-0042/design-contract.json" in reference_paths
    )
    assert "specs/001-ui-feature/ui-brief.md" in reference_paths

    documented_result = WorkerTaskResult(
        task_id="T021",
        status="success",
        changed_files=["src/ui/settings.tsx"],
        validation_results=[
            ValidationResult(
                command="npm test -- settings-ui",
                status="passed",
                output="settings UI tests passed",
            )
        ],
        ui_evidence=[
            {
                "kind": "structure_snapshot",
                "ref": "artifacts/ui/settings-structure.json",
            },
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/settings.png",
            },
            {
                "kind": "runtime_diagnostics",
                "ref": "artifacts/ui/settings-runtime.txt",
            },
        ],
        ui_verification=UIVerification(
            contract_check="pass",
            runtime_evidence="pass",
            visual_comparison="passed",
            fidelity_status="passed",
            approved_visual_ref=".specify/design/changes/UD-0042/previews/round-01.html#direction-settings",
            approved_preview_sha256="b" * 64,
            approved_manifest_sha256="c" * 64,
            approved_handoff_ref=".specify/design/changes/UD-0042/previews/round-01.handoff.json",
            approved_handoff_sha256="d" * 64,
            comparison_report_ref="artifacts/ui/settings-comparison.json",
            comparison_report_sha256="c" * 64,
            smoothness_lab_report_ref="implementation-review/smoothness/smoothness-lab-T021.json",
            smoothness_lab_report_sha256="e" * 64,
            implementation_capture_refs=["artifacts/ui/settings.png"],
            covered_decision_ids=list(packet.ui_contract.design_decision_ids),
            covered_handoff_contract_ids=list(packet.ui_contract.handoff_contract_ids),
            covered_smoothness_acceptance_ids=list(
                packet.ui_contract.usability_validation["smoothness_acceptance_ids"]
            ),
            comparison_tolerance=COMPARISON_TOLERANCE,
        ),
        summary="Implemented and visually verified the settings surface.",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[item.path for item in packet.context_bundle if item.must_read],
        ),
    )

    assert validate_worker_task_result(documented_result, packet) is documented_result


def test_current_ui_contract_rejects_obsolete_version_and_duplicate_payload() -> None:
    with pytest.raises(PacketValidationError, match="contract_version"):
        _ui_contract_from_task_entry({"ui_contract": {"contract_version": 2}})

    with pytest.raises(PacketValidationError, match="ui_fidelity_requirements"):
        _ui_contract_from_task_entry(
            {"ui_contract": {"fidelity_level": "high"}, "ui_fidelity_requirements": {}}
        )


def test_ui_context_nav_exposes_the_immutable_handoff_as_a_first_class_read() -> None:
    handoff_ref = ".specify/design/previews/round-01.handoff.json"
    context_nav = _ui_context_nav(
        {"ui_design_contract": {"entry_points": ["/settings"]}},
        UIContract(
            fidelity_level="high",
            design_sources=["design-change.md"],
            approved_handoff_ref=handoff_ref,
        ),
    )

    assert {(item["kind"], item["value"]) for item in context_nav} >= {
        ("design_source", "design-change.md"),
        ("design_handoff", handoff_ref),
    }


def test_compile_worker_task_packet_rejects_malformed_canonical_task_index(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text("{not-json", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T017 Implement fallback behavior in src/fallback.py\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError, match="task-index.json is malformed"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )


def test_compile_worker_task_packet_rejects_task_missing_from_canonical_index(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps({"version": 2, "status": "ready", "tasks": []}),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T017 Implement stale rendered behavior in src/stale.py\n",
        encoding="utf-8",
    )

    with pytest.raises(
        PacketValidationError, match="T017 is missing from canonical task-index.json"
    ):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )


def test_compile_worker_task_packet_merges_constitution_plan_and_task_sources(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
                "",
                "### Platform Guardrails",
                "",
                "- supported_platforms: windows, linux",
                "- require conditional compilation for unix-only APIs",
                "",
                "### Completion Handoff Protocol",
                "",
                "- send task_started before long-running work",
                "- write structured result handoff before idling",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "## Consequence Obligation Mapping",
                "",
                "| Obligation ID | Task IDs | Affected State/Dependency | Required References | Validation | Stop/Reopen Condition |",
                "| --- | --- | --- | --- | --- | --- |",
                "| CA-001 | T017 | team, worker | src/contracts/auth.py | pytest tests/unit/test_auth_service.py -q | No validation proves drain behavior |",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.task_id == "T017"
    assert packet.story_id == "US1"
    assert "src/contracts/auth.py" in [ref.path for ref in packet.required_references]
    assert any("public behavior" in rule.lower() for rule in packet.hard_rules)
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.validation_gates == ["pytest tests/unit/test_auth_service.py -q"]
    assert [item.path for item in packet.context_bundle] == ["src/contracts/auth.py"]
    assert [item.read_order for item in packet.context_bundle] == [1]
    assert packet.context_bundle[0].kind == "task_reference"
    assert ".specify/project-cognition/status.json" not in packet.scope.read_scope
    assert (
        ".specify/project-cognition/project-cognition.db" not in packet.scope.read_scope
    )
    assert (
        ".specify/project-cognition/slices/change.json" not in packet.scope.read_scope
    )
    assert ".specify/project-cognition/slices/debug.json" not in packet.scope.read_scope
    assert "PROJECT-HANDBOOK.md" not in packet.scope.read_scope
    assert packet.platform_guardrails == [
        "supported_platforms: windows, linux",
        "require conditional compilation for unix-only APIs",
    ]
    assert packet.handoff_requirements[-2:] == [
        "send task_started before long-running work",
        "write structured result handoff before idling",
    ]
    assert packet.consequence_obligations[0].obligation_id == "CA-001"
    assert packet.consequence_obligations[0].affected_objects == ["team", "worker"]
    assert packet.consequence_obligations[0].recovery_validation_refs == [
        "pytest tests/unit/test_auth_service.py -q"
    ]


def test_compile_worker_task_packet_carries_capability_operation_guards(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/cli/new.ts`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not add public commands beyond jx-skills/check/publish",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- tests/cli/new.test.ts",
                "",
                "## Capability Operation Coverage",
                "",
                "| Operation | Upstream Source | Selected Entry Point | Task IDs / Packet Fields | Validation | Degradation Check |",
                "| --- | --- | --- | --- | --- | --- |",
                "| create/scaffold skill | spec.md#capability-preservation-ledger | TUI route | T017, does_not_remove, capability_operations | npm test -- tests/cli/new.test.ts | not template-only / not manual-copy-only |",
                "",
                "## Task Guardrail Index",
                "",
                "- T017 -> does-not-remove guard: preserve create/scaffold skill via TUI route",
                "",
                "- [ ] T017 [US1] Implement authoring route in src/cli/new.ts",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.does_not_remove == ["preserve create/scaffold skill via TUI route"]
    assert packet.capability_operations == ["create/scaffold skill -> TUI route"]


def test_compile_worker_task_packet_reads_enriched_task_contract_fields(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/cli/router.ts`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not add public commands beyond check and publish",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- tests/cli/router.test.ts",
                "",
                "## T018: Wire authoring route",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/cli/router.ts] |",
                "| read_scope | [src/cli/new.ts] |",
                "| forbidden | [.env] |",
                "| does_not_remove | [scaffold capability via TUI route] |",
                "| capability_operations | [create/scaffold skill -> TUI route] |",
                "| consumer_surfaces | [OpenTUI Inspector renders TargetSelectionPanel] |",
                "| required_evidence | [consumer_evidence, real_entrypoint_evidence] |",
                "",
                "### Anti-Goals",
                "- Do not add public commands beyond check and publish",
                "",
                "- [ ] T018 [US1] Wire authoring route",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T018",
    )

    assert packet.anti_goals == ["Do not add public commands beyond check and publish"]
    assert packet.scope.write_scope == ["src/cli/router.ts"]
    assert "src/cli/new.ts" in packet.scope.read_scope
    assert ".env" in packet.forbidden_drift
    assert ".env" in packet.intent.constraints
    assert packet.does_not_remove == ["scaffold capability via TUI route"]
    assert packet.capability_operations == ["create/scaffold skill -> TUI route"]
    assert packet.consumer_surfaces == [
        "OpenTUI Inspector renders TargetSelectionPanel"
    ]
    assert packet.required_evidence == ["consumer_evidence", "real_entrypoint_evidence"]


def test_compile_worker_task_packet_compiles_review_contract_fields(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `design-change.md`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not change generated settings routes",
                "",
                "## Global Constraints",
                "",
                "- Preserve current keyboard navigation",
                "- Keep settings changes local to the panel",
                "",
                "## Review-Risk Notes",
                "",
                "- Screenshot drift can hide responsive regressions",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- tests/settings-panel.test.ts",
                "",
                "## T021: Build settings panel",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/ui/settings-panel.tsx] |",
                "| read_scope | [src/ui/settings-state.ts] |",
                "| consumes | [settings_state, design_tokens] |",
                "| produces | [settings_panel_events, responsive_settings_markup] |",
                "| review_inputs | [design-change.md, screenshots/settings-panel.png] |",
                "| review_risks | [Keyboard shortcuts may regress] |",
                "| controller_checks_required | [keyboard_navigation_check, state_persistence_check] |",
                "| global_constraints | [Do not introduce a new state store] |",
                "",
                "- [ ] T021 [US2] Build settings panel",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T021",
    )

    reference_paths = [ref.path for ref in packet.required_references]
    assert reference_paths == [
        "design-change.md",
        "screenshots/settings-panel.png",
    ]
    assert packet.forbidden_drift == ["Do not change generated settings routes"]
    assert "Do not change generated settings routes" in packet.intent.constraints
    assert packet.scope.write_scope == ["src/ui/settings-panel.tsx"]
    assert "src/ui/settings-state.ts" in packet.scope.read_scope
    assert packet.global_constraints == [
        "Preserve current keyboard navigation",
        "Keep settings changes local to the panel",
        "Do not introduce a new state store",
    ]
    assert packet.interfaces.consumes == ["settings_state", "design_tokens"]
    assert packet.interfaces.produces == [
        "settings_panel_events",
        "responsive_settings_markup",
    ]
    assert packet.review_inputs == ["design-change.md", "screenshots/settings-panel.png"]
    assert packet.review_risks == [
        "Screenshot drift can hide responsive regressions",
        "Keyboard shortcuts may regress",
    ]
    assert packet.controller_checks_required == [
        "keyboard_navigation_check",
        "state_persistence_check",
    ]
    assert "screenshots/settings-panel.png" in packet.scope.read_scope


def test_compile_worker_task_packet_rejects_markdown_only_ui_contract(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-ui-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve UI implementation contracts\n",
        encoding="utf-8",
    )
    design_ref = ".specify/design/changes/UD-0042/design-change.md"
    design_path = project_root / design_ref
    design_path.parent.mkdir(parents=True)
    design_path.write_text("# Design change\n", encoding="utf-8")
    (feature_dir / "ui-reference-notes.md").write_text(
        "# UI Reference Notes\n", encoding="utf-8"
    )
    (feature_dir / "ui-brief.md").write_text("# UI Brief\n", encoding="utf-8")
    (feature_dir / "ui-target.html").write_text("<!doctype html>\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text(
        f"## Required Implementation References\n\n- {design_ref}\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- exceptions",
                "",
                "## T021: Implement exception panel UI",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/app/exceptions/page.tsx] |",
                f"| read_scope | [{design_ref}, specs/001-ui-feature/ui-brief.md] |",
                "| required_evidence | [reference_source_evidence, ui_fidelity_criteria, real_entrypoint_ui_evidence, visual_comparison_or_human_review] |",
                "",
                "### UI Implementation Contract",
                "| Field | Value |",
                "|-------|-------|",
                f"| design_sources | [{design_ref}, specs/001-ui-feature/ui-brief.md] |",
                "| reference_notes | specs/001-ui-feature/ui-reference-notes.md |",
                "| visual_target | specs/001-ui-feature/ui-target.html |",
                "| ui_fidelity_mode | approximate |",
                "| must_preserve | [three-column layout, compact table density] |",
                "| may_adapt | [icons, minor spacing] |",
                "| must_not | [copy third-party source, turn table into cards] |",
                "| required_states | [loading, empty, error] |",
                "| required_evidence | [desktop screenshot, mobile screenshot] |",
                "",
                "- [ ] T021 [US1] Implement exception panel UI",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        PacketValidationError, match="no canonical task-index ui_contract"
    ):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T021",
        )


def test_compile_worker_task_packet_accepts_materialized_task_input(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve the runtime contract\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_bll_manager.py -q",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="BLL-lane",
        task_body="[US1] Refactor BLL lane in src/bll_manager.py",
    )

    assert packet.task_id == "BLL-lane"
    assert packet.story_id == "US1"
    assert packet.scope.write_scope == ["src/bll_manager.py"]
    assert packet.context_bundle[0].path == "src/contracts/auth.py"
    assert packet.validation_gates == ["pytest tests/unit/test_bll_manager.py -q"]


@pytest.mark.parametrize(
    "scope_path",
    [
        ".specify/project-cognition/status.json",
        "SPEC.md",
        "specs/001-test-feature/plan.md",
    ],
)
def test_compile_worker_task_packet_rejects_cli_owned_artifacts_in_task_scope(
    tmp_path: Path, scope_path: str
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    memory_dir = project_root / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve runtime ownership\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "tasks": [
                    {
                        "id": "T017",
                        "objective": "Do not bypass the runtime",
                        "expected_write_scope": ["src/service.py"],
                        "read_scope": [scope_path],
                        "required_refs": ["src/contracts/service.py"],
                        "forbidden_drift": ["Preserve runtime ownership"],
                        "acceptance": ["Runtime state stays CLI-owned"],
                        "verification": ["pytest -q"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError, match="CLI-owned workflow artifacts"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )


def test_compile_worker_task_packet_accepts_short_consequence_mapping_rows(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "## Consequence Obligation Mapping",
                "",
                "| Obligation ID | Task IDs | Validation |",
                "| --- | --- | --- |",
                "| CA-001 | T017 | pytest tests/unit/test_auth_service.py -q |",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    obligation = packet.consequence_obligations[0]
    assert obligation.obligation_id == "CA-001"
    assert obligation.claim == "CA-001 consequence obligation for T017"
    assert obligation.affected_objects == ["T017"]
    assert obligation.recovery_validation_refs == [
        "pytest tests/unit/test_auth_service.py -q"
    ]
    assert (
        obligation.stop_and_reopen_condition
        == "No validation evidence supplied for CA-001"
    )


def test_compile_worker_task_packet_requires_explicit_validation_gates(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (
        project_root / ".specify" / "project-cognition" / "project-cognition.db"
    ).write_bytes(b"SQLite test database marker")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
                "",
                "### Platform Guardrails",
                "",
                "- supported_platforms: windows, linux",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError) as exc:
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )

    assert exc.value.code == "DP1"
    assert "validation_gates" in exc.value.message
