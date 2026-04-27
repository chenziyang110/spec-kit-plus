import json
from pathlib import Path

from specify_cli.execution import (
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    PacketReference,
    PacketScope,
    RuleAcknowledgement,
    WorkerTaskPacket,
    WorkerTaskResult,
    worker_task_packet_payload,
    worker_task_result_payload,
)
from specify_cli.verification import ValidationResult
from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-delegation-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_packet(project: Path, packet: WorkerTaskPacket) -> Path:
    target = project / "packet.json"
    target.write_text(json.dumps(worker_task_packet_payload(packet), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _write_result(project: Path, result: WorkerTaskResult) -> Path:
    target = project / "result.json"
    target.write_text(json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _valid_packet() -> WorkerTaskPacket:
    return WorkerTaskPacket(
        feature_id="001-demo",
        task_id="T001",
        story_id="US1",
        objective="Implement demo behavior",
        scope=PacketScope(write_scope=["src/demo.py"], read_scope=["PROJECT-HANDBOOK.md"]),
        context_bundle=[
            ContextBundleItem(
                path="PROJECT-HANDBOOK.md",
                kind="handbook",
                purpose="project routing context",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="required project navigation",
            )
        ],
        required_references=[PacketReference(path="src/demo.py", reason="canonical implementation reference")],
        hard_rules=["preserve boundary"],
        forbidden_drift=["do not skip tests"],
        validation_gates=["pytest tests/test_demo.py -q"],
        done_criteria=["feature behavior implemented"],
        handoff_requirements=["return changed files", "return validation results"],
        platform_guardrails=["respect supported platforms"],
        intent=ExecutionIntent(
            outcome="Implement demo behavior",
            constraints=["preserve boundary"],
            success_signals=["feature behavior implemented"],
        ),
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )


def test_delegation_packet_validate_accepts_complete_packet(tmp_path: Path):
    project = _create_project(tmp_path)
    packet_path = _write_packet(project, _valid_packet())

    result = run_quality_hook(
        project,
        "delegation.packet.validate",
        {"packet_file": str(packet_path)},
    )

    assert result.status == "ok"
    assert result.data["packet"]["task_id"] == "T001"


def test_delegation_join_validate_blocks_result_missing_validation_evidence(tmp_path: Path):
    project = _create_project(tmp_path)
    packet_path = _write_packet(project, _valid_packet())
    result_path = _write_result(
        project,
        WorkerTaskResult(
            task_id="T001",
            status="success",
            changed_files=["src/demo.py"],
            validation_results=[],
            summary="done",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["PROJECT-HANDBOOK.md"],
            ),
        ),
    )

    result = run_quality_hook(
        project,
        "delegation.join.validate",
        {"packet_file": str(packet_path), "result_file": str(result_path)},
    )

    assert result.status == "blocked"
    assert any("DP3" in message for message in result.errors)


def test_delegation_join_validate_accepts_packet_compliant_result(tmp_path: Path):
    project = _create_project(tmp_path)
    packet_path = _write_packet(project, _valid_packet())
    result_path = _write_result(
        project,
        WorkerTaskResult(
            task_id="T001",
            status="success",
            changed_files=["src/demo.py"],
            validation_results=[
                ValidationResult(
                    command="pytest tests/test_demo.py -q",
                    status="passed",
                    output="1 passed",
                )
            ],
            summary="done",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["PROJECT-HANDBOOK.md"],
            ),
        ),
    )

    result = run_quality_hook(
        project,
        "delegation.join.validate",
        {"packet_file": str(packet_path), "result_file": str(result_path)},
    )

    assert result.status == "ok"
    assert result.data["result"]["task_id"] == "T001"
