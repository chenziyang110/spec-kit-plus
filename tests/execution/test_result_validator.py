import pytest

from specify_cli.execution.packet_schema import (
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    PacketReference,
    PacketScope,
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
                path="PROJECT-HANDBOOK.md",
                kind="handbook",
                purpose="Route the worker to the canonical project navigation entrypoint",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="root navigation artifact",
            ),
            ContextBundleItem(
                path=".specify/project-map/WORKFLOWS.md",
                kind="project_map",
                purpose="Describe when to use teams and when to fall back to leader-local closure",
                required_for=["workflow_boundary", "runtime_constraints"],
                read_order=2,
                must_read=True,
                selection_reason="teams execution policy lives here",
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
            paths_read=["PROJECT-HANDBOOK.md", ".specify/project-map/WORKFLOWS.md"],
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
            paths_read=["PROJECT-HANDBOOK.md", ".specify/project-map/WORKFLOWS.md"],
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
            paths_read=["PROJECT-HANDBOOK.md", ".specify/project-map/WORKFLOWS.md"],
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
            paths_read=["PROJECT-HANDBOOK.md"],
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
            paths_read=["PROJECT-HANDBOOK.md", ".specify/project-map/WORKFLOWS.md"],
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
            paths_read=["PROJECT-HANDBOOK.md", ".specify/project-map/WORKFLOWS.md"],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "validation gate" in exc.value.message
