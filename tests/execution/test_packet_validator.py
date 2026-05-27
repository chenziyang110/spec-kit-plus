from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
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


def test_validate_worker_task_packet_rejects_malformed_must_preserve_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.must_preserve_obligations = [
        MustPreserveObligation(
            id="002",
            type="decision",
            claim="",
            source="handoff-to-specify.json",
            downstream_requirement="Preserve this decision.",
        )
    ]

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "must-preserve" in exc.value.message.lower()


def test_validate_worker_task_packet_rejects_incomplete_consequence_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consequence_obligations[0].claim = ""

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"
    assert "consequence obligation" in exc.value.message


def test_validate_worker_task_packet_requires_does_not_remove_guard_for_surface_antigoal(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.anti_goals = ["Do not add public commands beyond check and publish"]
    sample_packet.does_not_remove = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP1"
    assert "does-not-remove" in exc.value.message


def test_compile_worker_task_packet_collects_must_preserve_obligations(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "## Must-Preserve Carry-Forward",
                "",
                "- MP-002: Keep auth implementation inside existing service boundary",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "## Task Guardrail Index",
                "",
                "- MP-003: Do not add a new auth provider abstraction",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert [item.id for item in packet.must_preserve_obligations] == ["MP-002", "MP-003"]
    assert packet.must_preserve_obligations[0].source == "plan.md"
    assert packet.must_preserve_obligations[1].source == "tasks.md"


def test_compile_worker_task_packet_keeps_unrelated_must_preserve_obligations_out_of_packet(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "## Must-Preserve Carry-Forward",
                "",
                "- MP-001: Applies to all implementation tasks: Keep the agreed product outcome.",
                "- MP-002: Keep auth implementation inside existing service boundary.",
                "- MP-003: Keep billing implementation inside existing service boundary.",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "## Task Guardrail Index",
                "",
                "- T017: MP-002",
                "- T018: MP-003",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
                "- [ ] T018 [US2] Implement billing flow in src/services/billing_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert [item.id for item in packet.must_preserve_obligations] == ["MP-001", "MP-002"]
