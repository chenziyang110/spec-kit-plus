import pytest

from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
    PacketReference,
    PacketScope,
    ValidationPolicy,
    WorkerTaskPacket,
)
from specify_cli.execution.packet_validator import PacketValidationError
from specify_cli.execution.result_schema import (
    RuleAcknowledgement,
    UIVerification,
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


def test_validate_worker_task_result_rejects_obsolete_real_entrypoint_ui_alias(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["real_entrypoint_ui_evidence"]
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
    assert "obsolete" in exc.value.message


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


def test_validate_worker_task_result_accepts_ui_human_review_fidelity_status(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
    sample_packet.ui_contract.fidelity_level = "approximate"
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
        manual_evidence=[
            {
                "kind": "pending review",
                "path": "artifacts/ui/pending-review.md",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.ui_verification.fidelity_status == "pending-human-review"


def test_validate_worker_task_result_enforces_ui_contract_required_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.required_evidence = ["visual_comparison_or_human_review"]
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
    assert (
        exc.value.message
        == "visual_comparison_or_human_review requires ui_verification fidelity_status"
    )


def test_feature_epoch_worker_defers_integrated_ui_evidence_to_leader(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.validation_policy = ValidationPolicy(
        mode="feature_epochs",
        max_epochs=3,
        budget_scope="implement-review",
        budget_ref="implementation-review/validation-runs.json",
        heavy_gate_owner="leader",
    )
    sample_packet.validation_gates = []
    sample_packet.task_checks = []
    sample_packet.consumer_surfaces = ["Settings page"]
    sample_packet.required_evidence = [
        "consumer_evidence",
        "real_entrypoint_evidence",
    ]
    sample_packet.ui_contract.fidelity_level = "high"
    sample_packet.ui_contract.required_evidence = [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[],
        summary="Implemented UI changes; integrated capture is leader-owned.",
        consumer_evidence=[
            {
                "kind": "wiring",
                "surface": "Settings page",
                "consumer": "SettingsRoute",
            }
        ],
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

    assert validate_worker_task_result(result, sample_packet) is result


def test_feature_epoch_worker_still_requires_cheap_consumer_wiring_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.validation_policy = ValidationPolicy(
        mode="feature_epochs",
        max_epochs=3,
        budget_scope="implement-review",
        budget_ref="implementation-review/validation-runs.json",
        heavy_gate_owner="leader",
    )
    sample_packet.validation_gates = []
    sample_packet.consumer_surfaces = ["Settings page"]
    sample_packet.required_evidence = ["consumer_evidence"]
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        summary="Implemented the surface but omitted its wiring evidence.",
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

    with pytest.raises(PacketValidationError, match="consumer evidence"):
        validate_worker_task_result(result, sample_packet)


def test_validate_worker_task_result_requires_current_ui_evidence_triad(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_contract.required_evidence = [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
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
        summary="Implemented auth UI",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
        ui_verification=UIVerification(
            contract_check="pass",
            runtime_evidence="pass",
            visual_comparison="passed",
            fidelity_status="passed",
        ),
        ui_evidence=[
            {"kind": "structure_snapshot", "ref": "artifacts/ui/a11y.json"},
            {"kind": "visual_capture", "ref": "artifacts/ui/settings.png"},
        ],
    )

    with pytest.raises(PacketValidationError, match="runtime_diagnostics"):
        validate_worker_task_result(result, sample_packet)

    result.ui_evidence.append(
        {"kind": "runtime_diagnostics", "ref": "artifacts/ui/console.txt"}
    )
    assert validate_worker_task_result(result, sample_packet) is result


def test_validate_worker_task_result_rejects_missing_ui_evidence_for_approximate_ui_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.fidelity_level = "approximate"
    sample_packet.ui_contract.required_evidence = [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "ui evidence" in exc.value.message.lower()


def test_validate_worker_task_result_accepts_ui_contract_required_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
        ),
        manual_evidence=[
            {
                "kind": "human review",
                "path": "artifacts/ui/review-notes.md",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.ui_verification.fidelity_status == "pending-human-review"


def test_validate_worker_task_result_accepts_needs_human_review_visual_comparison(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="needs-human-review",
            fidelity_status="pending-human-review",
        ),
        manual_evidence=[
            {
                "kind": "review tracking",
                "path": "artifacts/ui/review-tracking.md",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.ui_verification.visual_comparison == "needs-human-review"
    assert validated.ui_verification.fidelity_status == "pending-human-review"


def test_validate_worker_task_result_rejects_pending_human_review_without_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "review evidence" in exc.value.message


def test_validate_worker_task_result_rejects_pending_human_review_with_only_screenshot_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "review evidence" in exc.value.message


def test_validate_worker_task_result_accepts_pending_human_review_with_manual_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="pending-human-review",
        ),
        manual_evidence=[
            {
                "kind": "human review",
                "path": "artifacts/ui/manual-review.md",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.ui_verification.fidelity_status == "pending-human-review"


@pytest.mark.parametrize("reviewer", ["human", "manual"])
def test_validate_worker_task_result_accepts_human_reviewer_ui_pass_without_comparison(
    sample_packet: WorkerTaskPacket,
    reviewer: str,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="passed",
            reviewer=reviewer,
        ),
        manual_evidence=[
            {
                "kind": "human approval",
                "path": f"artifacts/ui/{reviewer}-approval.md",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.ui_verification.reviewer == reviewer


def test_validate_worker_task_result_rejects_human_reviewer_ui_pass_without_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="passed",
            reviewer="human",
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "manual evidence" in exc.value.message


def test_validate_worker_task_result_rejects_failed_ui_fidelity_status(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="failed",
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "fidelity status" in exc.value.message


def test_validate_worker_task_result_rejects_skipped_ui_fidelity_status(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="passed",
            fidelity_status="skipped",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "unknown ui fidelity status" in exc.value.message


def test_validate_worker_task_result_rejects_failed_ui_visual_comparison(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="failed",
            fidelity_status="passed",
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "visual comparison" in exc.value.message


def test_validate_worker_task_result_rejects_skipped_ui_visual_comparison(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="skipped",
            fidelity_status="passed",
            reviewer="human",
        ),
        manual_evidence=[
            {
                "kind": "human approval",
                "path": "artifacts/ui/human-approval.md",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "unknown visual comparison status" in exc.value.message


def test_validate_worker_task_result_rejects_pending_human_review_visual_comparison(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="pending-human-review",
            fidelity_status="pending-human-review",
        ),
        manual_evidence=[
            {
                "kind": "review tracking",
                "path": "artifacts/ui/review-tracking.md",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "unknown visual comparison status" in exc.value.message


def test_validate_worker_task_result_rejects_failed_ui_fidelity_status_for_ui_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.fidelity_level = "approximate"
    sample_packet.ui_contract.required_evidence = ["visual_capture"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="failed",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "fidelity status" in exc.value.message


def test_validate_worker_task_result_rejects_failed_ui_visual_comparison_for_ui_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.fidelity_level = "approximate"
    sample_packet.ui_contract.required_evidence = ["visual_capture"]
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
        ui_verification=UIVerification(
            visual_comparison="failed",
            fidelity_status="passed",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "visual comparison" in exc.value.message


def test_validate_worker_task_result_rejects_agent_ui_pass_without_comparison_for_ui_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.fidelity_level = "approximate"
    sample_packet.ui_contract.required_evidence = ["visual_capture"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="passed",
            reviewer="agent",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "human approval" in exc.value.message


def test_validate_worker_task_result_rejects_human_ui_pass_with_only_screenshot_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = []
    sample_packet.ui_contract.fidelity_level = "approximate"
    sample_packet.ui_contract.required_evidence = ["visual_capture"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="passed",
            reviewer="human",
        ),
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "manual evidence" in exc.value.message


def test_validate_worker_task_result_rejects_agent_reviewer_claiming_ui_pass_without_comparison(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
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
        ui_verification=UIVerification(
            visual_comparison="unavailable",
            fidelity_status="passed",
            reviewer="vision-subagent",
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "human approval" in exc.value.message


@pytest.mark.parametrize("fidelity_status", [None, "", "not-run", "unavailable", "none"])
def test_validate_worker_task_result_rejects_missing_ui_fidelity_status(
    sample_packet: WorkerTaskPacket,
    fidelity_status: str | None,
) -> None:
    sample_packet.required_evidence = ["visual_comparison_or_human_review"]
    sample_packet.ui_contract.fidelity_level = "approximate"
    ui_verification = (
        UIVerification(fidelity_status=fidelity_status)
        if fidelity_status is not None
        else UIVerification()
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
        ui_verification=ui_verification,
        ui_evidence=[
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/desktop.png",
            }
        ],
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert (
        exc.value.message
        == "visual_comparison_or_human_review requires ui_verification fidelity_status"
    )


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


def test_validate_worker_task_result_rejects_obsolete_ui_evidence_kind(
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
        ui_evidence=[
            {"kind": "desktop_screenshot", "ref": "artifacts/auth-flow.png"}
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

    with pytest.raises(PacketValidationError, match="unsupported UI evidence kind"):
        validate_worker_task_result(result, sample_packet)


def test_validate_worker_task_result_rejects_obsolete_ui_evidence_kind_when_blocked(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="blocked",
        blockers=["dependency unavailable"],
        failed_assumptions=["dependency was expected to be available"],
        suggested_recovery_actions=["restore the dependency"],
        ui_evidence=[
            {"kind": "desktop_screenshot", "ref": "artifacts/auth-flow.png"}
        ],
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

    with pytest.raises(PacketValidationError, match="unsupported UI evidence kind"):
        validate_worker_task_result(result, sample_packet)


def test_validate_worker_task_result_rejects_obsolete_ui_evidence_kind_when_pending(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="pending",
        ui_evidence=[
            {"kind": "desktop_screenshot", "ref": "artifacts/auth-flow.png"}
        ],
    )

    with pytest.raises(PacketValidationError, match="unsupported UI evidence kind"):
        validate_worker_task_result(result, sample_packet)


def test_validate_worker_task_result_rejects_obsolete_ui_evidence_kind_when_failed(
    sample_packet: WorkerTaskPacket,
) -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="failed",
        ui_evidence=[
            {"kind": "desktop_screenshot", "ref": "artifacts/auth-flow.png"}
        ],
    )

    with pytest.raises(PacketValidationError, match="unsupported UI evidence kind"):
        validate_worker_task_result(result, sample_packet)
