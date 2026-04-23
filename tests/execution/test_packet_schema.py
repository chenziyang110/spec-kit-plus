from specify_cli.execution.packet_schema import (
    DispatchPolicy,
    PacketReference,
    PacketScope,
    WorkerTaskPacket,
    worker_task_packet_from_json,
    worker_task_packet_payload,
)
from specify_cli.execution.result_schema import (
    ValidationResult,
    WorkerTaskResult,
    worker_task_result_from_json,
    worker_task_result_payload,
)
import json


def test_worker_task_packet_captures_required_execution_contract() -> None:
    packet = WorkerTaskPacket(
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

    assert packet.packet_version == 1
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.dispatch_policy.mode == "hard_fail"


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

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.task_id == "T017"
    assert restored.scope.write_scope == ["src/services/auth_service.py"]
    assert restored.required_references[0].path == "src/contracts/auth.py"


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
    )

    restored = worker_task_result_from_json(json.dumps(worker_task_result_payload(result)))

    assert restored.task_id == "T017"
    assert restored.summary == "Implemented auth flow"
    assert restored.validation_results[0].output == "1 passed"
