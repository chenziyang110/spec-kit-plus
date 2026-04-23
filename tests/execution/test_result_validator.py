import pytest

from specify_cli.execution.packet_schema import (
    DispatchPolicy,
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
        scope=PacketScope(
            write_scope=["src/services/auth_service.py"],
            read_scope=["src/contracts/auth.py"],
        ),
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
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
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
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
