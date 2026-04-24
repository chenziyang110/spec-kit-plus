import pytest

from specify_cli.execution.packet_schema import (
    DispatchPolicy,
    ExecutionIntent,
    PacketReference,
    PacketScope,
    WorkerTaskPacket,
)
from specify_cli.execution.packet_validator import (
    PacketValidationError,
    validate_worker_task_packet,
)


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
