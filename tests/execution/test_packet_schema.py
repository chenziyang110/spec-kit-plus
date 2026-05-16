from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
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
    assert restored.consequence_obligations[0].obligation_id == "CA-001"
    assert restored.consequence_obligations[0].claim == "Running workers drain before close completes"


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
