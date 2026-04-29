from specify_cli.execution.packet_schema import (
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    PacketReference,
    PacketScope,
    WorkerTaskPacket,
    worker_task_packet_from_json,
    worker_task_packet_payload,
)
from specify_cli.execution.result_schema import (
    RuleAcknowledgement,
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
        platform_guardrails=["supported_platforms: windows, linux"],
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )

    assert packet.packet_version == 2
    assert packet.intent.outcome == "Implement auth flow without changing the public contract shape"
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.dispatch_policy.mode == "hard_fail"
    assert packet.platform_guardrails == ["supported_platforms: windows, linux"]


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
                path="PROJECT-HANDBOOK.md",
                kind="handbook",
                purpose="Route the worker to the canonical project navigation entrypoint",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="root navigation artifact",
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
        platform_guardrails=["supported_platforms: windows, linux"],
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.task_id == "T017"
    assert restored.intent.constraints == ["Do not create a parallel auth stack"]
    assert restored.scope.write_scope == ["src/services/auth_service.py"]
    assert restored.context_bundle[0].path == "PROJECT-HANDBOOK.md"
    assert restored.required_references[0].path == "src/contracts/auth.py"
    assert restored.platform_guardrails == ["supported_platforms: windows, linux"]


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
            paths_read=["PROJECT-HANDBOOK.md", ".specify/project-map/root/WORKFLOWS.md"],
            critical_notes=["validated the canonical worker verification route before execution"],
        ),
    )

    restored = worker_task_result_from_json(json.dumps(worker_task_result_payload(result)))

    assert restored.rule_acknowledgement.context_bundle_read is True
    assert restored.rule_acknowledgement.paths_read == [
        "PROJECT-HANDBOOK.md",
        ".specify/project-map/root/WORKFLOWS.md",
    ]
    assert restored.rule_acknowledgement.critical_notes == [
        "validated the canonical worker verification route before execution"
    ]
