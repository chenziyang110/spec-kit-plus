import pytest

from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
    PacketReference,
    PacketScope,
    UiFidelityRequirements,
    WorkerTaskPacket,
)
from specify_cli.execution.packet_validator import PacketValidationError
from specify_cli.execution.result_schema import (
    RuleAcknowledgement,
    ValidationResult,
    WorkerTaskResult,
)
from specify_cli.execution.result_validator import validate_worker_task_result


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
                selection_reason="project-cognition query returns touched-scope context and conflict signals",
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
    )


def _add_sample_consequence_obligation(packet: WorkerTaskPacket) -> WorkerTaskPacket:
    packet.consequence_obligations = [
        ConsequenceObligation(
            obligation_id="CA-001",
            claim="Running workers drain before close completes",
            affected_objects=["team", "worker"],
            recovery_validation_refs=["pytest tests/unit/test_auth_service.py -q"],
            owner="sp-tasks",
            latest_resolve_phase="tasks",
            status="open",
            stop_and_reopen_condition="No validation proves drain behavior",
        )
    ]
    return packet


def test_validate_worker_task_result_accepts_acknowledged_result(
    sample_packet: WorkerTaskPacket,
) -> None:
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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.status == "success"


def test_validate_worker_task_result_rejects_missing_rule_acknowledgement(
    sample_packet: WorkerTaskPacket,
) -> None:
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

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"


def test_validate_worker_task_result_accepts_blocked_result_with_fail_fast_context(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="blocked",
        summary="Blocked waiting on missing auth contract field",
        blockers=["auth contract does not define refresh token semantics"],
        failed_assumptions=["expected refresh token field in src/contracts/auth.py"],
        suggested_recovery_actions=["clarify the contract and regenerate the packet"],
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.status == "blocked"


def test_validate_worker_task_result_accepts_pending_placeholder_without_rule_acknowledgement(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="pending",
        summary="Pending result placeholder",
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.status == "pending"


def test_validate_worker_task_result_rejects_blocked_result_without_recovery_context(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="blocked",
        summary="Blocked waiting on missing auth contract field",
        blockers=["auth contract does not define refresh token semantics"],
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"


def test_validate_worker_task_result_rejects_missing_context_bundle_receipts(
    sample_packet: WorkerTaskPacket,
) -> None:
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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[".specify/project-cognition/status.json"],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "context bundle" in exc.value.message


def test_validate_worker_task_result_rejects_success_without_truthful_validation_output(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="",
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "validation output" in exc.value.message


def test_validate_worker_task_result_rejects_success_when_a_validation_gate_is_missing(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_different_target.py -q",
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "validation gate" in exc.value.message


def test_validate_worker_task_result_rejects_missing_required_consumer_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consumer_surfaces = ["DeviceProviderPage renders ClaudeForm"]
    sample_packet.required_evidence = ["consumer_evidence"]
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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "consumer evidence" in exc.value.message


def test_validate_worker_task_result_rejects_synthetic_only_real_entrypoint_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consumer_surfaces = ["OpenTUI Inspector renders TargetSelectionPanel"]
    sample_packet.required_evidence = ["consumer_evidence", "real_entrypoint_evidence"]
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
        consumer_evidence=[
            {
                "kind": "synthetic",
                "surface": "TargetSelectionPanel",
                "evidence": "Hand-built plan renders target rows",
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "real-entrypoint" in exc.value.message


@pytest.mark.parametrize(
    "invalid_value",
    [
        None,
        True,
        False,
        [],
        {},
        "TODO",
        "TBD",
        "N/A",
        "none",
    ],
)
def test_validate_worker_task_result_rejects_blank_real_entrypoint_fields(
    sample_packet: WorkerTaskPacket,
    invalid_value: object,
) -> None:
    sample_packet.consumer_surfaces = ["OpenTUI Inspector renders TargetSelectionPanel"]
    sample_packet.required_evidence = ["consumer_evidence", "real_entrypoint_evidence"]
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
        consumer_evidence=[
            {
                "kind": "real_entrypoint",
                "entrypoint": invalid_value,
                "producer": invalid_value,
                "transformer": invalid_value,
                "consumer": invalid_value,
                "boundary_or_executor": invalid_value,
                "validation": invalid_value,
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "real-entrypoint" in exc.value.message


def test_validate_worker_task_result_accepts_real_entrypoint_consumer_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consumer_surfaces = ["OpenTUI Inspector renders TargetSelectionPanel"]
    sample_packet.required_evidence = ["consumer_evidence", "real_entrypoint_evidence"]
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
        consumer_evidence=[
            {
                "kind": "real_entrypoint",
                "entrypoint": "OpenTUI browse/install",
                "producer": "catalog supported_agents",
                "transformer": "createProjectTuiState -> createInstallPlan",
                "consumer": "Inspector renders TargetSelectionPanel",
                "boundary_or_executor": "install runner receives selected targets",
                "validation": "open-tui-copy regression",
            }
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
        ),
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.status == "success"


def test_validate_worker_task_result_rejects_success_without_applicable_ui_fidelity_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "ui fidelity evidence" in exc.value.message


def test_validate_worker_task_result_requires_visual_comparison_ui_fidelity_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "manual_review",
                "artifact": "artifacts/auth-flow-notes.md",
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "visual comparison" in exc.value.message


def test_validate_worker_task_result_rejects_visual_comparison_without_payload(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "visual_comparison",
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "visual comparison" in exc.value.message


def test_validate_worker_task_result_rejects_visual_comparison_placeholder_payload(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "visual_comparison",
                "artifact": "TODO",
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "visual comparison" in exc.value.message


@pytest.mark.parametrize("placeholder", ["placeholder", "unknown", "replace_me"])
def test_validate_worker_task_result_rejects_common_visual_comparison_placeholders(
    sample_packet: WorkerTaskPacket,
    placeholder: str,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "visual_comparison",
                "artifact": placeholder,
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "visual comparison" in exc.value.message


def test_validate_worker_task_result_accepts_required_ui_fidelity_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "visual_comparison",
                "artifact": "artifacts/auth-flow-diff.png",
            }
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
        ),
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.ui_fidelity_evidence[0]["kind"] == "visual_comparison"


def test_validate_worker_task_result_rejects_required_screenshots_when_only_notes_exist(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["desktop_screenshot", "mobile_screenshot"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "notes",
                "artifact": "artifacts/auth-flow-notes.md",
            }
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "desktop_screenshot" in exc.value.message


def test_validate_worker_task_result_accepts_required_screenshot_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["designs/auth-flow.png"],
        required_evidence=["desktop_screenshot", "mobile_screenshot"],
    )
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
        ui_fidelity_evidence=[
            {
                "kind": "desktop_screenshot",
                "screenshot": "artifacts/auth-flow-desktop.png",
            },
            {
                "kind": "mobile_screenshot",
                "screenshot": "artifacts/auth-flow-mobile.png",
            },
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
        ),
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert [item["kind"] for item in validated.ui_fidelity_evidence] == [
        "desktop_screenshot",
        "mobile_screenshot",
    ]


def test_validate_worker_task_result_requires_must_preserve_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="MP-002",
            type="non_goal",
            claim="Do not create a parallel auth stack.",
            source="handoff-to-specify.json",
            downstream_requirement="Keep auth implementation inside existing service boundary.",
            mapped_to=["tasks.md#Task Guardrail Index"],
            stop_and_reopen_condition="Implementation requires a parallel auth stack.",
        )
    ]
    sample_packet.required_evidence = ["must_preserve_evidence"]

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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "must-preserve evidence" in exc.value.message


def test_validate_worker_task_result_rejects_success_without_consequence_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet = _add_sample_consequence_obligation(sample_packet)

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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "consequence evidence" in exc.value.message


def test_validate_worker_task_result_accepts_must_preserve_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="MP-002",
            type="non_goal",
            claim="Do not create a parallel auth stack.",
            source="handoff-to-specify.json",
            downstream_requirement="Keep auth implementation inside existing service boundary.",
            mapped_to=["tasks.md#Task Guardrail Index"],
            stop_and_reopen_condition="Implementation requires a parallel auth stack.",
        )
    ]
    sample_packet.required_evidence = ["must_preserve_evidence"]

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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
        must_preserve_evidence=[
            {
                "mp_id": "MP-002",
                "evidence": "No new auth stack files were added; implementation stayed in src/services/auth_service.py.",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.status == "success"


def test_validate_worker_task_result_accepts_success_with_consequence_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet = _add_sample_consequence_obligation(sample_packet)

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
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
        consequence_evidence=[
            {
                "obligation_id": "CA-001",
                "evidence": "pytest tests/unit/test_auth_service.py -q passed",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.consequence_evidence[0]["obligation_id"] == "CA-001"
