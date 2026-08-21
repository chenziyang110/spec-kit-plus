from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
    PacketReference,
    PacketScope,
    UIContract,
    WorkerTaskPacket,
)
from specify_cli.execution.packet_validator import (
    DESIGN_DECISION_ID_RE,
    PacketValidationError,
    _valid_component_adoption,
    _valid_usability_validation,
    validate_worker_task_packet,
)


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

VALID_COMPONENT_ADOPTION = {
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
def test_component_adoption_contract_rejects_incomplete_or_unauthorized_rows(
    patch: dict[str, object],
) -> None:
    assert not _valid_component_adoption({**VALID_COMPONENT_ADOPTION, **patch})


def test_component_adoption_contract_accepts_complete_reuse_row() -> None:
    assert _valid_component_adoption(VALID_COMPONENT_ADOPTION)


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
def test_usability_contract_rejects_invalid_smoothness_budgets(
    budgets: object,
) -> None:
    assert not _valid_usability_validation(
        {
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["save settings"],
            "success_criteria": ["preserve context"],
            "human_review_required": True,
            "performance_budgets": budgets,
        }
    )


def test_usability_contract_accepts_complete_smoothness_budgets() -> None:
    assert _valid_usability_validation(
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
        "validation_timing": "Validate syntax after composition ends and validate remote rules on submit.",
        "validation_feedback": "Associate a specific inline message and summary link with the invalid field.",
        "dirty_state_behavior": "Expose unsaved state and warn before destructive navigation.",
        "persistence_behavior": "Keep unsaved values through retry and restore the last confirmed value on reload.",
        "undo_redo_behavior": "Keep native undo and redo history across formatting and validation feedback.",
        "conflict_behavior": "Show local and remote values and require an explicit conflict choice.",
        "read_only_disabled_behavior": "Keep read-only values selectable and explain why disabled controls are unavailable.",
        "submission_behavior": "Prevent duplicate submission while preserving focus and announce one final result.",
        "decision_ids": ["DS-INT-001"],
    }


def test_design_decision_ids_allow_stable_multi_segment_names() -> None:
    assert DESIGN_DECISION_ID_RE.fullmatch("DS-COLOR-BRAND-001")
    assert DESIGN_DECISION_ID_RE.fullmatch("DS-DATA-EMPTY-STATE-002")


@pytest.fixture
def sample_packet() -> WorkerTaskPacket:
    return WorkerTaskPacket(
        feature_id="001-feature",
        task_id="T017",
        story_id="US1",
        objective="Implement auth flow",
        intent=ExecutionIntent(
            outcome="Implement auth flow without changing the public contract shape",
            constraints=["Do not create a parallel auth stack"],
            success_signals=["login/logout behavior implemented"],
        ),
        scope=PacketScope(
            write_scope=["src/services/auth_service.py"],
            read_scope=["src/contracts/auth.py"],
        ),
        context_bundle=[
            ContextBundleItem(
                path=".specify/project-cognition/status.json",
                kind="project_cognition",
                purpose="Project cognition freshness entrypoint for query-backed readiness and refresh metadata.",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="project status is the lightweight entrypoint before requesting a task-local cognition query bundle for downstream execution work",
            ),
            ContextBundleItem(
                path=".specify/project-cognition/project-cognition.db",
                kind="project_cognition",
                purpose="Query-backed cognition graph store for the active implementation lane.",
                required_for=["implementation_scope"],
                read_order=2,
                must_read=True,
                selection_reason="specify-runtime cognition query narrows the runtime context to touched surfaces without raw slice reads",
            ),
        ],
        required_references=[
            PacketReference(
                path="src/contracts/auth.py",
                reason="public contract compatibility must be preserved",
            )
        ],
        hard_rules=["Every public function changed must have tests"],
        forbidden_drift=["Do not create a parallel auth stack"],
        validation_gates=["pytest tests/unit/test_auth_service.py -q"],
        done_criteria=["login/logout behavior implemented"],
        handoff_requirements=["return changed files"],
        platform_guardrails=["supported_platforms: windows, linux"],
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
        consequence_obligations=[
            ConsequenceObligation(
                obligation_id="CA-001",
                claim="Running workers drain before close completes",
                affected_objects=["team", "worker"],
                recovery_validation_refs=["pytest tests/test_team_close.py -q"],
                owner="sp-tasks",
                latest_resolve_phase="tasks",
                status="open",
                stop_and_reopen_condition="No validation proves drain behavior",
            )
        ],
    )


def test_validate_worker_task_packet_accepts_complete_packet(
    sample_packet: WorkerTaskPacket,
) -> None:
    validated = validate_worker_task_packet(sample_packet)

    assert validated.task_id == "T017"


def test_validate_worker_task_packet_rejects_missing_required_references(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_references = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"


def test_validate_worker_task_packet_rejects_missing_validation_gates(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.validation_gates = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"


def test_validate_worker_task_packet_rejects_missing_intent_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.intent = ExecutionIntent()

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"


def test_validate_worker_task_packet_rejects_missing_context_bundle(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.context_bundle = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"


def test_validate_worker_task_packet_rejects_missing_handoff_requirements(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.handoff_requirements = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"


def test_validate_worker_task_packet_rejects_missing_platform_guardrails(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.platform_guardrails = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"


def test_validate_worker_task_packet_rejects_malformed_must_preserve_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="002",
            type="decision",
            claim="",
            source="handoff-to-specify.json",
            downstream_requirement="Preserve this decision.",
        )
    ]

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "must-preserve" in exc.value.message.lower()


def test_validate_worker_task_packet_rejects_incomplete_consequence_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consequence_obligations[0].claim = ""

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"
    assert "consequence obligation" in exc.value.message


def test_validate_worker_task_packet_requires_does_not_remove_guard_for_surface_antigoal(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.anti_goals = ["Do not add public commands beyond check and publish"]
    sample_packet.does_not_remove = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "does-not-remove" in exc.value.message


def test_validate_worker_task_packet_rejects_incomplete_current_ui_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_contract = UIContract(fidelity_level="high")

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "ui contract" in exc.value.message.lower()


def test_validate_worker_task_packet_rejects_obsolete_ui_evidence_labels(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["real_entrypoint_ui_evidence"]

    with pytest.raises(PacketValidationError, match="obsolete UI evidence labels"):
        validate_worker_task_packet(sample_packet)


def test_validate_worker_task_packet_rejects_blank_controller_check_entries(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.controller_checks_required = ["verify screenshot diff", "  "]

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "controller checks" in exc.value.message.lower()


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
def test_validate_worker_task_packet_requires_complete_current_ui_contract(
    sample_packet: WorkerTaskPacket,
    bypass_visual_ref: str,
    bypass_handoff_ref: str,
) -> None:
    sample_packet.context_nav = [
        {"kind": "ui_entrypoint", "value": "/settings", "source": "plan-contract.json"},
        {"kind": "design_source", "value": "DESIGN.md", "source": "task-index.json"},
    ]
    sample_packet.ui_contract = UIContract(
        fidelity_level="approximate",
        ui_work_type="feature-extension",
        surface_type="product-workspace",
        platforms=["web"],
        style_authority={
            "mode": "inherit-existing",
            "scope_level": "feature-partial",
            "source_refs": ["src/ui/theme.ts", "src/ui/settings.tsx"],
            "protected_surfaces": ["global-shell", "shared-components"],
            "allowed_style_delta_surfaces": [],
            "authorization_source": None,
        },
        subject="settings",
        audience="account owners",
        single_job="update preferences",
        visual_thesis="compact hierarchy",
        content_thesis="real preference labels and values",
        interaction_thesis="immediate local feedback",
        signature_element="persistent section progress",
        approved_visual_ref="DESIGN.md#settings",
        design_decision_ids=[
            "DS-COMP-001",
            "DS-RESP-001",
            "DS-INT-001",
            "DS-DATA-001",
            "DS-ACCESS-001",
            "DS-NAV-001",
            "DS-CONTENT-001",
            "DS-MOTION-001",
        ],
        design_sources=["DESIGN.md", "ui-brief.md"],
        real_content_plan=[{"source_ref": "src/settings/schema.ts"}],
        surface_catalog=[
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
        scenario_matrix=[
            {
                "id": "SCENARIO-001",
                "surface_id": "SURFACE-001",
                "name": "Settings ready keyboard save",
                "risk": "medium",
                "required": True,
                "interaction_script": {
                    "preconditions": [
                        "The settings form is rendered at the compact viewport.",
                        "Representative settings data is available.",
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
                            "expected_feedback": "Keep the unsaved values and show a specific recovery message.",
                            "focus_behavior": "Move focus only when the error needs correction.",
                            "announcement": "Announce the failure without stealing focus.",
                            "continuation": "Retry or cancel without losing entered values.",
                        },
                        {
                            "conditions": ["retry", "duplicate", "out_of_order"],
                            "setup": "Repeat, retry, or resolve concurrent saves out of order.",
                            "expected_state_id": "DATA-001",
                            "expected_feedback": "Apply one authoritative result without duplicate effects.",
                            "focus_behavior": "Preserve the active control and selection.",
                            "announcement": "Announce only the authoritative final result.",
                            "continuation": "Reconcile stale completion before another edit.",
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
                    "completion_checkpoint": "Saved values and specific confirmation remain visible.",
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
        interaction_matrix=[
            _interaction_contract("INT-001", "mouse"),
            _interaction_contract("INT-002", "keyboard"),
        ],
        editing_matrix=[_editing_contract()],
        data_state_matrix=[
            {
                "id": "DATA-001",
                "surface": "settings form",
                "state": "ready",
                "data_condition": "settings data is present",
                "expectation": "render saved values and action controls",
                "decision_ids": ["DS-DATA-001"],
            },
            {
                "id": "DATA-002",
                "surface": "settings form",
                "state": "error",
                "data_condition": "settings request fails",
                "expectation": "keep the layout stable and show inline recovery guidance",
                "decision_ids": ["DS-DATA-001"],
            },
        ],
        accessibility_matrix=[
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
        navigation_matrix=[
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
        content_matrix=[
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
        color_modes=["light", "dark"],
        component_contracts=[
            {
                "id": "COMP-001",
                "component": "settings form",
                "anatomy": ["heading", "fields", "actions"],
                "decision_ids": ["DS-COMP-001"],
                "interaction_modes": ["mouse", "keyboard"],
                "data_scenarios": [
                    {
                        "state": "ready",
                        "data_condition": "settings data is present",
                        "expectation": "render saved values and controls",
                    },
                    {
                        "state": "error",
                        "data_condition": "settings request fails",
                        "expectation": "keep the layout stable and show inline recovery guidance",
                    },
                ],
                "required_states": ["ready", "error"],
                "variants": ["default", "compact"],
                "content_constraints": ["labels wrap without truncation"],
                "semantic_token_refs": ["color.feedback.success"],
                "governance": "extend",
                "iconography": "status icons include accessible text",
            }
        ],
        responsive_matrix=[
            {
                "id": "RESP-001",
                "viewport": "390",
                "state": "ready",
                "adaptation": "stack settings sections",
                "stretch_behavior": "grow field rows for long labels without clipping",
                "overflow_behavior": "keep the page scrollable with actions pinned",
                "decision_ids": ["DS-RESP-001"],
            }
        ],
        motion_contract={
            "purpose": "show saved-state feedback",
            "transitions": [
                {
                    "id": "MOTION-001",
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
        usability_validation={
            "risk_level": "medium",
            "methods": ["cognitive walkthrough"],
            "critical_tasks": ["update and save one preference"],
            "success_criteria": ["save without losing section context"],
            "human_review_required": True,
            "smoothness_acceptance_ids": [
                "focus-continuity",
                "pending-cancel-feedback",
                "duplicate-activation",
                "reduced-motion",
            ],
        },
        visual_acceptance_matrix=[
            {
                "id": "VA-001",
                "viewport": "390",
                "state": "ready",
                "evidence": "visual_capture",
                "decision_ids": ["DS-RESP-001"],
            }
        ],
        comparison_tolerance=COMPARISON_TOLERANCE,
        required_states=["ready", "error"],
        required_evidence=[
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
            "visual_comparison_or_human_review",
        ],
    )
    assert validate_worker_task_packet(sample_packet) is sample_packet

    sample_packet.ui_contract.usability_validation[
        "smoothness_acceptance_ids"
    ] = ["focus-continuity", "focus-continuity"]
    with pytest.raises(PacketValidationError, match="usability_validation"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.usability_validation[
        "smoothness_acceptance_ids"
    ] = []
    assert validate_worker_task_packet(sample_packet) is sample_packet
    sample_packet.ui_contract.usability_validation[
        "smoothness_acceptance_ids"
    ] = [
        "focus-continuity",
        "pending-cancel-feedback",
        "duplicate-activation",
        "reduced-motion",
    ]

    sample_packet.ui_contract.style_authority["allowed_style_delta_surfaces"] = [
        "web:settings"
    ]
    with pytest.raises(PacketValidationError, match="style_authority"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.style_authority["allowed_style_delta_surfaces"] = []

    sample_packet.ui_contract.style_authority.update(
        {
            "mode": "page-overhaul-authorized",
            "scope_level": "feature-partial",
            "authorization_source": None,
            "allowed_style_delta_surfaces": ["global-shell"],
        }
    )
    with pytest.raises(PacketValidationError, match="style_authority"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.style_authority = {
        "mode": "inherit-existing",
        "scope_level": "feature-partial",
        "source_refs": ["src/ui/theme.ts", "src/ui/settings.tsx"],
        "protected_surfaces": ["global-shell", "shared-components"],
        "allowed_style_delta_surfaces": [],
        "authorization_source": None,
    }

    sample_packet.ui_contract.approved_handoff_ref = (
        ".specify/design/previews/round-01.handoff.json"
    )
    with pytest.raises(PacketValidationError, match="must be present together"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.approved_handoff_ref = ""

    sample_packet.ui_contract.approved_visual_ref = (
        ".specify/design/previews/round-01.html#direction-clarity"
    )
    sample_packet.ui_contract.approved_preview_sha256 = "a" * 64
    sample_packet.ui_contract.approved_manifest_sha256 = "b" * 64
    sample_packet.ui_contract.approved_handoff_ref = (
        ".specify/design/previews/round-01.handoff.json"
    )
    sample_packet.ui_contract.approved_handoff_sha256 = "c" * 64
    sample_packet.ui_contract.handoff_contract_ids = [
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
        "DH-RESP-COMPACT-001",
        "DH-MOTION-001",
        "DH-VA-COMPACT-001",
    ]
    sample_packet.ui_contract.interaction_matrix[0]["id"] = "DH-INT-001"
    sample_packet.ui_contract.interaction_matrix[1]["id"] = "DH-INT-002"
    sample_packet.ui_contract.editing_matrix[0]["id"] = "DH-EDIT-001"
    sample_packet.ui_contract.data_state_matrix[0]["id"] = "DH-DATA-001"
    sample_packet.ui_contract.data_state_matrix[1]["id"] = "DH-DATA-002"
    sample_packet.ui_contract.accessibility_matrix[0]["id"] = "DH-A11Y-001"
    sample_packet.ui_contract.navigation_matrix[0]["id"] = "DH-NAV-001"
    sample_packet.ui_contract.content_matrix[0]["id"] = "DH-CONTENT-001"
    sample_packet.ui_contract.motion_contract["transitions"][0]["id"] = (
        "DH-MOTION-001"
    )
    sample_packet.ui_contract.surface_catalog[0]["id"] = "DH-SURFACE-WEB-001"
    sample_packet.ui_contract.surface_catalog[0]["component_ids"] = ["DH-COMP-001"]
    sample_packet.ui_contract.scenario_matrix[0].update(
        {
            "id": "DH-SCENARIO-WEB-001",
            "surface_id": "DH-SURFACE-WEB-001",
            "interaction_ids": ["DH-INT-001"],
            "editing_ids": ["DH-EDIT-001"],
            "data_state_ids": ["DH-DATA-001"],
            "accessibility_ids": ["DH-A11Y-001"],
            "navigation_ids": ["DH-NAV-001"],
            "content_ids": ["DH-CONTENT-001"],
            "responsive_ids": ["DH-RESP-COMPACT-001"],
            "motion_transition_ids": ["DH-MOTION-001"],
            "decision_ids": [
                "DS-INT-001",
                "DS-DATA-001",
                "DS-ACCESS-001",
                "DS-NAV-001",
                "DS-CONTENT-001",
                "DS-RESP-001",
                "DS-COMP-001",
                "DS-MOTION-001",
            ],
        }
    )
    scenario_script = sample_packet.ui_contract.scenario_matrix[0][
        "interaction_script"
    ]
    scenario_script["start_state_id"] = "DH-DATA-001"
    for branch in scenario_script["branches"]:
        branch["expected_state_id"] = "DH-DATA-001"
    sample_packet.context_nav.append(
        {
            "kind": "design_handoff",
            "value": sample_packet.ui_contract.approved_handoff_ref,
            "source": "task-index.json#/ui_contract",
        }
    )
    sample_packet.ui_contract.component_contracts = [
        {
            "id": "DH-COMP-001",
            "component": "settings form",
            "anatomy": ["heading", "fields", "actions"],
            "required_states": ["ready", "error"],
            "interaction_modes": ["mouse", "keyboard"],
            "data_scenarios": [
                {
                    "state": "ready",
                    "data_condition": "settings data is present",
                    "expectation": "render saved values and controls",
                }
            ],
            "decision_ids": ["DS-COMP-001"],
            "must_match": ["anatomy", "hierarchy"],
            "variants": ["default", "compact"],
            "content_constraints": ["labels wrap without truncation"],
            "semantic_token_refs": ["color.feedback.success"],
            "governance": "extend",
            "iconography": "status icons include accessible text",
        }
    ]
    sample_packet.ui_contract.responsive_matrix = [
        {
            "id": "DH-RESP-COMPACT-001",
            "label": "compact",
            "target": {"width": 390, "height": 844, "unit": "px"},
            "state": "ready",
            "adaptation": "stack settings sections",
            "stretch_behavior": "grow field rows for long labels without clipping",
            "overflow_behavior": "keep the page scrollable with actions pinned",
            "decision_ids": ["DS-RESP-001", "DS-COMP-001"],
        }
    ]
    sample_packet.ui_contract.visual_acceptance_matrix = [
        {
            "id": "DH-VA-COMPACT-001",
            "target_id": "DH-RESP-COMPACT-001",
            "states": ["ready", "error"],
            "color_modes": ["light", "dark"],
            "motion_modes": ["full", "reduced"],
            "decision_ids": ["DS-COMP-001", "DS-RESP-001"],
            "must_match": ["structure", "tokens", "content"],
            "evidence": [
                "structure_snapshot",
                "visual_capture",
                "runtime_diagnostics",
                "visual_comparison_or_human_review",
            ],
        }
    ]
    assert validate_worker_task_packet(sample_packet) is sample_packet

    entrypoint_id = sample_packet.ui_contract.surface_catalog[0].pop(
        "entrypoint_id"
    )
    with pytest.raises(PacketValidationError, match="surface_catalog"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.surface_catalog[0]["entrypoint_id"] = entrypoint_id

    sample_packet.ui_contract.scenario_matrix[0]["data_state_ids"] = [
        "DH-DATA-404"
    ]
    with pytest.raises(PacketValidationError, match="scenario_matrix"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.scenario_matrix[0]["data_state_ids"] = [
        "DH-DATA-001"
    ]

    scenario = sample_packet.ui_contract.scenario_matrix[0]
    scenario["interaction_ids"], scenario["data_state_ids"] = (
        scenario["data_state_ids"],
        scenario["interaction_ids"],
    )
    with pytest.raises(PacketValidationError, match="scenario_matrix"):
        validate_worker_task_packet(sample_packet)
    scenario["interaction_ids"], scenario["data_state_ids"] = (
        scenario["data_state_ids"],
        scenario["interaction_ids"],
    )

    interaction_script = scenario["interaction_script"]
    interaction_script["focus_checkpoint"] = ""
    with pytest.raises(PacketValidationError, match="scenario_matrix"):
        validate_worker_task_packet(sample_packet)
    interaction_script["focus_checkpoint"] = (
        "Focus remains visible on the invoking control."
    )
    interaction_script["branches"][0]["expected_state_id"] = "DH-DATA-UNKNOWN"
    with pytest.raises(PacketValidationError, match="scenario_matrix"):
        validate_worker_task_packet(sample_packet)
    interaction_script["branches"][0]["expected_state_id"] = "DH-DATA-001"

    accessibility_matrix = sample_packet.ui_contract.accessibility_matrix
    sample_packet.ui_contract.accessibility_matrix = []
    with pytest.raises(PacketValidationError, match="accessibility_matrix"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.accessibility_matrix = accessibility_matrix

    sample_packet.ui_contract.navigation_matrix[0]["decision_ids"] = [
        "DS-UNKNOWN-999"
    ]
    with pytest.raises(PacketValidationError, match="navigation_matrix"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.navigation_matrix[0]["decision_ids"] = ["DS-NAV-001"]

    sample_packet.ui_contract.motion_contract["transitions"][0]["duration_ms"] = -1
    with pytest.raises(PacketValidationError, match="motion_contract"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.motion_contract["transitions"][0]["duration_ms"] = 180

    sample_packet.ui_contract.component_contracts[0]["variants"] = []
    with pytest.raises(PacketValidationError, match="component_contracts"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.component_contracts[0]["variants"] = [
        "default",
        "compact",
    ]

    sample_packet.ui_contract.component_contracts[0]["adoption"] = {
        "resource_id": "material-ui",
        "action": "replace",
        "package": "@mui/material",
        "version": "^7.0.0",
        "license": "MIT",
        "source_ref": "package.json#/dependencies/@mui/material",
        "component_refs": ["@mui/material/TextField"],
        "reason_codes": ["installed"],
        "selection_basis_refs": [
            "professional_skill_route.mature_web_ui_selection"
        ],
        "permission_gate": "not-required",
        "permission_status": "authorized",
    }
    with pytest.raises(PacketValidationError, match="component_contracts"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.component_contracts[0]["adoption"]["action"] = "extend"
    assert validate_worker_task_packet(sample_packet) is sample_packet

    sample_packet.ui_contract.interaction_matrix = []
    with pytest.raises(PacketValidationError, match="interaction_matrix"):
        validate_worker_task_packet(sample_packet)

    sample_packet.ui_contract.interaction_matrix = [
        _interaction_contract("DH-INT-001", "keyboard")
    ]
    sample_packet.ui_contract.interaction_matrix[0]["event_sequence"] = ""
    with pytest.raises(PacketValidationError, match="interaction_matrix"):
        validate_worker_task_packet(sample_packet)
    sample_packet.ui_contract.interaction_matrix[0]["event_sequence"] = (
        "Resolve keydown and keyup as one activation."
    )
    sample_packet.ui_contract.data_state_matrix = []
    with pytest.raises(PacketValidationError, match="data_state_matrix"):
        validate_worker_task_packet(sample_packet)

    sample_packet.ui_contract.data_state_matrix = [
        {
            "id": "DH-DATA-001",
            "surface": "settings form",
            "state": "ready",
            "data_condition": "settings data is present",
            "expectation": "render saved values and controls",
            "decision_ids": ["DS-DATA-001"],
        }
    ]
    assert validate_worker_task_packet(sample_packet) is sample_packet

    sample_packet.ui_contract.fidelity_level = "none"
    with pytest.raises(PacketValidationError, match="fidelity_level"):
        validate_worker_task_packet(sample_packet)

    sample_packet.ui_contract.fidelity_level = "approximate"
    sample_packet.ui_contract.approved_visual_ref = ""
    with pytest.raises(PacketValidationError, match="approved_visual_ref"):
        validate_worker_task_packet(sample_packet)

    sample_packet.ui_contract.ui_work_type = "existing-pattern"
    sample_packet.ui_contract.approved_visual_ref = "src/ui/settings.tsx#existing-pattern"
    assert validate_worker_task_packet(sample_packet) is sample_packet

    sample_packet.ui_contract.ui_work_type = "feature-extension"
    sample_packet.ui_contract.design_change_id = "UD-0042"
    sample_packet.ui_contract.design_change_ref = (
        ".specify/design/changes/UD-0042/DESIGN.md"
    )
    sample_packet.ui_contract.design_change_sha256 = "a" * 64
    sample_packet.ui_contract.design_contract_ref = (
        ".specify/design/changes/UD-0042/design-contract.json"
    )
    sample_packet.ui_contract.design_sources = [
        ".specify/design/changes/UD-0042/DESIGN.md",
        ".specify/design/changes/UD-0042/design-contract.json",
    ]
    sample_packet.ui_contract.approved_visual_ref = (
        ".specify/design/changes/UD-0042/previews/round-01.png#direction-settings"
    )
    sample_packet.ui_contract.approved_handoff_ref = (
        ".specify/design/changes/UD-0042/previews/round-01.handoff.json"
    )
    next(
        item
        for item in sample_packet.context_nav
        if item["kind"] == "design_handoff"
    )["value"] = sample_packet.ui_contract.approved_handoff_ref
    assert validate_worker_task_packet(sample_packet) is sample_packet

    sample_packet.ui_contract.approved_visual_ref = (
        ".specify/design/changes/UD-0042/previews/round-01.html#settings-direction"
    )
    with pytest.raises(PacketValidationError, match="change-local visual round"):
        validate_worker_task_packet(sample_packet)

    sample_packet.ui_contract.approved_visual_ref = bypass_visual_ref
    sample_packet.ui_contract.approved_handoff_ref = bypass_handoff_ref
    with pytest.raises(PacketValidationError, match="change-local visual round"):
        validate_worker_task_packet(sample_packet)


def test_compile_worker_task_packet_collects_must_preserve_obligations(
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
        "# Constitution\n\n- MUST preserve public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "## Must-Preserve Carry-Forward",
                "",
                "- MP-002: Keep auth implementation inside existing service boundary",
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
                "## Task Guardrail Index",
                "",
                "- MP-003: Do not add a new auth provider abstraction",
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

    assert [item.id for item in packet.must_preserve_obligations] == [
        "MP-002",
        "MP-003",
    ]
    assert packet.must_preserve_obligations[0].source == "plan.md"
    assert packet.must_preserve_obligations[1].source == "tasks.md"


def test_compile_worker_task_packet_keeps_unrelated_must_preserve_obligations_out_of_packet(
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
        "# Constitution\n\n- MUST preserve public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "## Must-Preserve Carry-Forward",
                "",
                "- MP-001: Applies to all implementation tasks: Keep the agreed product outcome.",
                "- MP-002: Keep auth implementation inside existing service boundary.",
                "- MP-003: Keep billing implementation inside existing service boundary.",
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
                "## Task Guardrail Index",
                "",
                "- T017: MP-002",
                "- T018: MP-003",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
                "- [ ] T018 [US2] Implement billing flow in src/services/billing_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert [item.id for item in packet.must_preserve_obligations] == [
        "MP-001",
        "MP-002",
    ]
