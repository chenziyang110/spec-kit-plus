import pytest

from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
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
                selection_reason="project-cognition query narrows the runtime context to touched surfaces without raw slice reads",
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


def test_validate_worker_task_packet_rejects_incomplete_consequence_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consequence_obligations[0].claim = ""

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"
    assert "consequence obligation" in exc.value.message
