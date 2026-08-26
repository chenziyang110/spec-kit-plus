import json

import pytest

from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
    PacketInterfaces,
    PacketReference,
    PacketScope,
    UIContract,
    WorkerTaskPacket,
    worker_task_packet_from_json,
    worker_task_packet_payload,
)
from specify_cli.execution.result_schema import (
    RuleAcknowledgement,
    UIVerification,
    ValidationResult,
    WorkerTaskResult,
    worker_task_result_from_json,
    worker_task_result_payload,
)


def test_current_ui_contract_includes_stable_surface_and_scenario_graph() -> None:
    from specify_cli.execution.packet_schema import UI_CONTRACT_FIELDS

    assert {
        "source_continuity",
        "surface_catalog",
        "scenario_matrix",
        "editing_matrix",
    } <= UI_CONTRACT_FIELDS


def test_current_ui_packet_and_result_parsers_reject_obsolete_fields() -> None:
    with pytest.raises(ValueError, match="ui_fidelity_requirements"):
        worker_task_packet_from_json(json.dumps({"ui_fidelity_requirements": {}}))

    with pytest.raises(ValueError, match="contract_version"):
        worker_task_packet_from_json(
            json.dumps({"ui_contract": {"contract_version": 2}})
        )

    with pytest.raises(ValueError, match="ui_fidelity_evidence"):
        worker_task_result_from_json(json.dumps({"ui_fidelity_evidence": []}))

    with pytest.raises(ValueError, match="uiVerification"):
        worker_task_result_from_json(json.dumps({"uiVerification": {}}))

    with pytest.raises(ValueError, match="unsupported kind"):
        worker_task_result_from_json(
            json.dumps(
                {
                    "task_id": "T001",
                    "status": "blocked",
                    "ui_evidence": [
                        {"kind": "desktop_screenshot", "ref": "evidence/ui.png"}
                    ],
                }
            )
        )


def test_worker_task_packet_captures_required_execution_contract() -> None:
    packet = WorkerTaskPacket(
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
                purpose="Project cognition freshness entrypoint for query-backed planning and implementation work",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="status is the lightweight entrypoint before requesting a task-local cognition query bundle",
            ),
            ContextBundleItem(
                path=".specify/project-cognition/project-cognition.db",
                kind="project_cognition",
                purpose="Query-backed cognition graph store for touched-scope routing",
                required_for=["workflow_boundary", "architecture_boundary", "forbidden_drift"],
                read_order=2,
                must_read=True,
                selection_reason="specify-runtime cognition query returns touched-scope context and conflict signals",
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
        test_design_handoff_ref="test-design/handoff-to-tasks.json",
        test_design_handoff_sha256="1" * 64,
        test_design_source_fingerprint="2" * 64,
        test_design_state_revision=9,
        test_design_artifact_digests={
            "state": "3" * 64,
            "universe": "4" * 64,
        },
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

    assert packet.packet_version == 2
    assert packet.intent.outcome == "Implement auth flow without changing the public contract shape"
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.dispatch_policy.mode == "hard_fail"
    assert packet.platform_guardrails == ["supported_platforms: windows, linux"]
    assert packet.consequence_obligations[0].obligation_id == "CA-001"
    assert packet.consequence_obligations[0].affected_objects == ["team", "worker"]
    payload = worker_task_packet_payload(packet)
    restored = worker_task_packet_from_json(json.dumps(payload))
    assert restored.test_design_handoff_ref == packet.test_design_handoff_ref
    assert restored.test_design_handoff_sha256 == packet.test_design_handoff_sha256
    assert (
        restored.test_design_source_fingerprint
        == packet.test_design_source_fingerprint
    )
    assert restored.test_design_state_revision == 9
    assert restored.test_design_artifact_digests == packet.test_design_artifact_digests


def test_worker_task_packet_captures_ui_contract_and_result_verification() -> None:
    design_ref = ".specify/design/changes/UD-0042/design-change.md"
    packet = WorkerTaskPacket(
        feature_id="001-feature",
        task_id="T021",
        story_id="US1",
        objective="Implement exception panel UI",
        intent=ExecutionIntent(outcome="Implement UI from ui-brief.md"),
        scope=PacketScope(write_scope=["src/app/exceptions/page.tsx"]),
        context_bundle=[],
        required_references=[
            PacketReference(
                path=design_ref, reason="registered design change contract"
            ),
            PacketReference(
                path="specs/001-feature/ui-brief.md", reason="feature UI contract"
            ),
        ],
        hard_rules=["Follow ui_contract"],
        forbidden_drift=["Do not replace dense table with cards"],
        validation_gates=["npm test -- exceptions"],
        done_criteria=["UI evidence returned"],
        handoff_requirements=["return ui_evidence and ui_verification"],
        ui_contract=UIContract(
            ui_work_type="feature-extension",
            surface_type="product-workspace",
            platforms=["web"],
            subject="exception management",
            audience="operations staff",
            single_job="resolve one exception safely",
            visual_thesis="dense but calm operational hierarchy",
            content_thesis="show real exception data and recovery context",
            interaction_thesis="keep triage actions local and reversible",
            signature_element="persistent exception context rail",
            approved_visual_ref=f"{design_ref}#exception-direction",
            design_sources=[design_ref, "specs/001-feature/ui-brief.md"],
            reference_notes="specs/001-feature/ui-reference-notes.md",
            visual_target="specs/001-feature/ui-target.html",
            reference_intents=[
                {
                    "ref": "specs/001-feature/ui-target.html",
                    "intent": "preserve-structure",
                }
            ],
            real_content_plan=[
                {
                    "source_ref": "src/exceptions/schema.py",
                    "applies_to_states": ["ready"],
                }
            ],
            image_plan=[],
            interaction_matrix=[
                {
                    "surface": "exception table row",
                    "input": "mouse",
                    "trigger": "hover a row action cluster",
                    "expectation": "show inline recovery actions without shifting layout",
                },
                {
                    "surface": "exception table row",
                    "input": "keyboard",
                    "trigger": "tab to a row action and press Enter",
                    "expectation": "run the same recovery action with visible focus feedback",
                },
            ],
            data_state_matrix=[
                {
                    "state": "empty",
                    "data_condition": "no exceptions match the active filters",
                    "expectation": "show a no-results message with filter reset affordance",
                },
                {
                    "state": "ready",
                    "data_condition": "exceptions are loaded",
                    "expectation": "render live exception rows and recovery context",
                },
            ],
            accessibility_matrix=[
                {
                    "id": "DH-A11Y-001",
                    "surface": "exception table",
                    "semantics": ["table", "row", "button"],
                    "reading_order": "heading, filters, table, row actions",
                    "focus_order": "filters then rows then row actions",
                    "keyboard": ["Tab moves between controls", "Enter activates"],
                    "announcements": ["announce filter result count"],
                    "target_size": "24x24 CSS px minimum",
                    "contrast": "WCAG 2.2 AA",
                    "zoom_reflow": "reflows without loss at 400%",
                    "alternatives": ["text label accompanies status icon"],
                    "decision_ids": ["DS-ACCESS-001"],
                }
            ],
            navigation_matrix=[
                {
                    "id": "DH-NAV-001",
                    "surface": "exception detail",
                    "entry": "exception table row",
                    "destination": "exception detail panel",
                    "trigger": "activate row",
                    "back_behavior": "return to the same filtered row",
                    "deep_link_behavior": "open the requested exception directly",
                    "interruption_recovery": "restore unsaved recovery notes",
                    "decision_ids": ["DS-NAV-001"],
                }
            ],
            content_matrix=[
                {
                    "id": "DH-CONTENT-001",
                    "surface": "empty exception table",
                    "state": "empty",
                    "purpose": "explain why no exceptions are shown",
                    "copy": "No exceptions match these filters.",
                    "primary_action": "Reset filters",
                    "trust_requirement": "do not imply that all exceptions are resolved",
                    "localization": "support RTL and translated expansion",
                    "content_limits": ["title 80 characters", "one primary action"],
                    "decision_ids": ["DS-CONTENT-001"],
                }
            ],
            motion_contract={
                "purpose": "connect row selection to the detail panel",
                "transitions": [
                    {
                        "id": "DH-MOTION-001",
                        "surface": "exception detail panel",
                        "trigger": "open detail",
                        "response": "panel enters without moving table context",
                        "duration_ms": 180,
                        "easing": "ease-out",
                        "interrupt_behavior": "reverse from the current position",
                        "decision_ids": ["DS-MOTION-001"],
                    }
                ],
                "reduced_motion": "show the final panel state without translation",
                "feedback_timing": {
                    "immediate_ms": 100,
                    "progress_ms": 1000,
                    "timeout_ms": 10000,
                },
            },
            usability_validation={
                "risk_level": "high",
                "methods": ["target-user task test", "cognitive walkthrough"],
                "critical_tasks": ["recover one failed exception safely"],
                "success_criteria": ["complete without losing table context"],
                "human_review_required": True,
            },
            component_contracts=[
                {
                    "id": "DH-COMP-001",
                    "component": "exception table",
                    "anatomy": ["filters", "header", "rows", "row actions"],
                    "required_states": ["loading", "empty", "ready", "error"],
                    "interaction_modes": ["mouse", "keyboard"],
                    "data_scenarios": [
                        {
                            "state": "ready",
                            "data_condition": "exceptions are loaded",
                            "expectation": "render rows and recovery actions",
                        }
                    ],
                    "variants": ["compact", "comfortable"],
                    "content_constraints": ["long identifiers must wrap safely"],
                    "semantic_token_refs": ["color.status.critical"],
                    "governance": "extend",
                    "iconography": "icons require visible text or an accessible name",
                    "decision_ids": ["DS-COMP-001"],
                }
            ],
            fidelity_level="approximate",
            must_preserve=["three-column layout", "compact table density"],
            may_adapt=["icons", "minor spacing"],
            must_not=["copy third-party source", "turn table into cards"],
            required_states=["loading", "empty", "error"],
            required_evidence=[
                "structure_snapshot",
                "visual_capture",
                "runtime_diagnostics",
                "visual_comparison_or_human_review",
            ],
        ),
    )

    payload = worker_task_packet_payload(packet)
    round_tripped = worker_task_packet_from_json(json.dumps(payload))

    assert round_tripped.ui_contract.fidelity_level == "approximate"
    assert round_tripped.ui_contract.surface_type == "product-workspace"
    assert (
        round_tripped.ui_contract.reference_intents[0]["intent"] == "preserve-structure"
    )
    assert (
        round_tripped.ui_contract.real_content_plan[0]["source_ref"]
        == "src/exceptions/schema.py"
    )
    assert round_tripped.ui_contract.accessibility_matrix[0]["id"] == "DH-A11Y-001"
    assert round_tripped.ui_contract.navigation_matrix[0]["id"] == "DH-NAV-001"
    assert round_tripped.ui_contract.content_matrix[0]["id"] == "DH-CONTENT-001"
    assert round_tripped.ui_contract.motion_contract["feedback_timing"]["progress_ms"] == 1000
    assert round_tripped.ui_contract.usability_validation["risk_level"] == "high"
    assert round_tripped.ui_contract.component_contracts[0]["governance"] == "extend"
    assert "compact table density" in round_tripped.ui_contract.must_preserve
    assert "visual_capture" in round_tripped.ui_contract.required_evidence

    result = WorkerTaskResult(
        task_id="T021",
        status="success",
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop-1440.png",
                "viewport": "1440",
            }
        ],
        ui_verification=UIVerification(
            contract_check="pass",
            runtime_evidence="pass",
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
            reviewer="agent",
        ),
    )
    result_payload = worker_task_result_payload(result)
    parsed_result = worker_task_result_from_json(json.dumps(result_payload))

    assert parsed_result.ui_evidence[0]["kind"] == "visual_capture"
    assert parsed_result.ui_verification.fidelity_status == "pending-human-review"


def test_worker_task_result_requires_validation_records() -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
            )
        ],
        summary="Implemented auth flow",
    )

    assert result.status == "success"
    assert result.validation_results[0].status == "passed"


def test_worker_task_packet_round_trips_through_json() -> None:
    packet = WorkerTaskPacket(
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
                purpose="Project cognition freshness entrypoint for query-backed planning and implementation work",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="status is the lightweight entrypoint before requesting a task-local cognition query bundle",
            ),
            ContextBundleItem(
                path=".specify/project-cognition/project-cognition.db",
                kind="project_cognition",
                purpose="Query-backed cognition graph store for touched-scope routing",
                required_for=["workflow_boundary", "architecture_boundary", "forbidden_drift"],
                read_order=2,
                must_read=True,
                selection_reason="specify-runtime cognition query returns touched-scope context and conflict signals",
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
        does_not_remove=["scaffold capability via TUI route"],
        capability_operations=["implements check command", "does not own scaffold operation"],
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

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.task_id == "T017"
    assert restored.intent.constraints == ["Do not create a parallel auth stack"]
    assert restored.scope.write_scope == ["src/services/auth_service.py"]
    assert restored.context_bundle[0].path == ".specify/project-cognition/status.json"
    assert restored.context_bundle[1].path == ".specify/project-cognition/project-cognition.db"
    assert restored.required_references[0].path == "src/contracts/auth.py"
    assert restored.platform_guardrails == ["supported_platforms: windows, linux"]
    assert restored.does_not_remove == ["scaffold capability via TUI route"]
    assert restored.capability_operations == ["implements check command", "does not own scaffold operation"]
    assert restored.consequence_obligations[0].obligation_id == "CA-001"
    assert restored.consequence_obligations[0].claim == "Running workers drain before close completes"


def test_worker_task_packet_round_trips_review_and_ui_contract_fields() -> None:
    packet = WorkerTaskPacket(
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
                purpose="Project cognition freshness entrypoint",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="required runtime readiness source",
            )
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
        global_constraints=["do not edit generated hooks"],
        interfaces=PacketInterfaces(
            consumes=["auth contract"],
            produces=["auth service"],
        ),
        review_inputs=["design-review.md"],
        review_risks=["layout regression"],
        ui_contract=UIContract(
            fidelity_level="high",
            design_sources=["designs/auth-flow.png"],
            required_evidence=[
                "structure_snapshot",
                "visual_capture",
                "runtime_diagnostics",
                "visual_comparison_or_human_review",
            ],
        ),
        controller_checks_required=["verify screenshot diff"],
    )

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.global_constraints == ["do not edit generated hooks"]
    assert restored.interfaces.consumes == ["auth contract"]
    assert restored.interfaces.produces == ["auth service"]
    assert restored.review_inputs == ["design-review.md"]
    assert restored.review_risks == ["layout regression"]
    assert restored.ui_contract.fidelity_level == "high"
    assert restored.ui_contract.design_sources == ["designs/auth-flow.png"]
    assert restored.ui_contract.required_evidence == [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
    assert restored.controller_checks_required == ["verify screenshot diff"]


def test_worker_task_packet_preserves_must_preserve_obligations() -> None:
    packet = WorkerTaskPacket(
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
                purpose="Project cognition freshness entrypoint",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="required runtime readiness source",
            )
        ],
        required_references=[
            PacketReference(path="src/contracts/auth.py", reason="preserve MP-002")
        ],
        hard_rules=["Every public function changed must have tests"],
        forbidden_drift=["MP-002: Do not create a parallel auth stack"],
        validation_gates=["pytest tests/unit/test_auth_service.py -q"],
        done_criteria=["login/logout behavior implemented"],
        handoff_requirements=["return changed files"],
        must_preserve_obligations=[
            MustPreserveObligation(
                id="MP-002",
                type="non_goal",
                claim="Do not create a parallel auth stack.",
                source="handoff-to-specify.json",
                downstream_requirement="Keep auth implementation inside existing service boundary.",
                mapped_to=["tasks.md#Task Guardrail Index"],
                stop_and_reopen_condition="Implementation requires a parallel auth stack.",
            )
        ],
    )

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.must_preserve_obligations[0].id == "MP-002"
    assert restored.must_preserve_obligations[0].type == "non_goal"
    assert restored.must_preserve_obligations[0].mapped_to == ["tasks.md#Task Guardrail Index"]


def test_worker_task_packet_from_json_normalizes_legacy_project_map_context_kind() -> None:
    payload = {
        "feature_id": "001-feature",
        "task_id": "T017",
        "story_id": "US1",
        "objective": "Implement auth flow",
        "intent": {
            "outcome": "Implement auth flow",
            "constraints": ["Do not create a parallel auth stack"],
            "success_signals": ["login/logout behavior implemented"],
        },
        "scope": {
            "write_scope": ["src/services/auth_service.py"],
            "read_scope": [".specify/project-cognition/status.json"],
        },
        "context_bundle": [
            {
                "path": ".specify/project-cognition/status.json",
                "kind": "project_map",
                "purpose": "legacy packet from older runtime",
                "required_for": ["workflow_boundary"],
                "read_order": 1,
                "must_read": True,
                "selection_reason": "legacy packet compatibility",
            }
        ],
        "required_references": [
            {
                "path": "src/contracts/auth.py",
                "reason": "public contract compatibility must be preserved",
            }
        ],
        "hard_rules": ["Every public function changed must have tests"],
        "forbidden_drift": ["Do not create a parallel auth stack"],
        "validation_gates": ["pytest tests/unit/test_auth_service.py -q"],
        "done_criteria": ["login/logout behavior implemented"],
        "handoff_requirements": ["return changed files"],
        "platform_guardrails": ["supported_platforms: windows, linux"],
    }

    restored = worker_task_packet_from_json(json.dumps(payload))

    assert restored.context_bundle[0].kind == "project_cognition"


def test_context_bundle_item_normalizes_legacy_project_map_kind_on_construction() -> None:
    item = ContextBundleItem(
        path=".specify/project-cognition/status.json",
        kind="project_map",
    )

    assert item.kind == "project_cognition"


def test_worker_task_result_round_trips_through_json() -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        must_preserve_evidence=[
            {
                "mp_id": "MP-002",
                "evidence": "No new auth stack files were added.",
            }
        ],
        consequence_evidence=[
            {
                "obligation_id": "CA-001",
                "validation_ref": "pytest tests/unit/test_auth_service.py -q",
                "outcome": "recovery path validated",
            }
        ],
    )

    restored = worker_task_result_from_json(json.dumps(worker_task_result_payload(result)))

    assert restored.task_id == "T017"
    assert restored.summary == "Implemented auth flow"
    assert restored.validation_results[0].output == "1 passed"
    assert restored.must_preserve_evidence == [
        {
            "mp_id": "MP-002",
            "evidence": "No new auth stack files were added.",
        }
    ]
    assert restored.consequence_evidence == [
        {
            "obligation_id": "CA-001",
            "validation_ref": "pytest tests/unit/test_auth_service.py -q",
            "outcome": "recovery path validated",
        }
    ]


def test_worker_task_result_round_trips_context_read_receipts() -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
            critical_notes=["validated query readiness, task-local bundle, and minimal_live_reads before execution"],
        ),
    )

    restored = worker_task_result_from_json(json.dumps(worker_task_result_payload(result)))

    assert restored.rule_acknowledgement.context_bundle_read is True
    assert restored.rule_acknowledgement.paths_read == [
        ".specify/project-cognition/status.json",
        ".specify/project-cognition/project-cognition.db",
    ]
    assert restored.rule_acknowledgement.critical_notes == [
        "validated query readiness, task-local bundle, and minimal_live_reads before execution"
    ]
