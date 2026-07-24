import json
from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_schema import ValidationPolicy
from specify_cli.execution.packet_validator import (
    PacketValidationError,
    validate_worker_task_packet,
)
from specify_cli.execution.result_schema import WorkerTaskResult
from specify_cli.execution.result_validator import validate_worker_task_result
from specify_cli.validation_budget import (
    ValidationBudgetError,
    complete_validation_epoch,
    reserve_validation_epoch,
    validation_budget_status,
)


def _write_packet_project(
    tmp_path: Path, *, feature_epochs: bool, task_checks: list[str] | None = None
) -> tuple[Path, Path]:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-batched-validation"
    feature_dir.mkdir(parents=True)
    memory_dir = project_root / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve public behavior.\n", encoding="utf-8"
    )
    (feature_dir / "plan.md").write_text(
        "## Required Implementation References\n\n"
        "- src/contracts/service.py\n\n"
        "## Platform Guardrails\n\n"
        "- Support Windows and Linux.\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "## Validation Gates\n\n"
        "- pytest -q\n\n"
        "## T001 Implement service\n\n"
        "Change `src/service.py`.\n",
        encoding="utf-8",
    )
    task_index: dict[str, object] = {
        "version": 2,
        "status": "ready",
        "tasks": [
            {
                "id": "T001",
                "objective": "Implement service",
                "expected_write_scope": ["src/service.py"],
                "required_refs": ["src/contracts/service.py"],
                "verification": ["pytest tests/service -q"],
                "required_validation": ["ruff check src/service.py"],
                "task_checks": task_checks or [],
            }
        ],
    }
    if feature_epochs:
        task_index["validation_policy"] = {
            "mode": "feature_epochs",
            "max_epochs": 3,
            "budget_scope": "implement-review",
            "budget_ref": "implementation-review/validation-runs.json",
            "heavy_gate_owner": "leader",
        }
    (feature_dir / "task-index.json").write_text(
        json.dumps(task_index), encoding="utf-8"
    )
    return project_root, feature_dir


def test_feature_epoch_packet_only_dispatches_task_local_checks(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path,
        feature_epochs=True,
        task_checks=["python -m py_compile src/service.py"],
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T001",
    )

    assert packet.validation_policy == ValidationPolicy(
        mode="feature_epochs",
        max_epochs=3,
        budget_scope="implement-review",
        budget_ref="implementation-review/validation-runs.json",
        heavy_gate_owner="leader",
    )
    assert packet.validation_gates == ["python -m py_compile src/service.py"]
    assert packet.verify_commands == ["python -m py_compile src/service.py"]
    assert "pytest -q" not in packet.validation_gates
    assert "pytest tests/service -q" not in packet.validation_gates


def test_feature_epoch_packet_can_defer_all_validation_to_leader(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True, task_checks=[]
    )
    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T001",
    )

    assert packet.validation_gates == []
    assert validate_worker_task_packet(packet) is packet
    result = WorkerTaskResult(
        task_id="T001",
        status="success",
        changed_files=["src/service.py"],
        summary="Implemented service; shared validation is owned by the leader.",
    )
    packet.dispatch_policy.must_acknowledge_rules = False
    assert validate_worker_task_result(result, packet) is result


def test_legacy_packet_keeps_per_task_validation_behavior(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=False, task_checks=[]
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T001",
    )

    assert packet.validation_policy.mode == "task"
    assert packet.validation_gates == [
        "pytest -q",
        "pytest tests/service -q",
        "ruff check src/service.py",
    ]
    packet.validation_gates = []
    with pytest.raises(PacketValidationError, match="validation_gates"):
        validate_worker_task_packet(packet)


def test_validation_budget_counts_logical_gates_and_retries_inside_delivery(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )

    first = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="baseline",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    duplicate = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="baseline",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    assert duplicate["run_id"] == first["run_id"]
    assert duplicate["reused"] is True

    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=first["run_id"],
        status="passed",
        evidence_refs=["logs/validation-v1.txt"],
        summary="Baseline passed",
    )
    for purpose, fingerprint in (("convergence", "sha-b"), ("delivery", "sha-c")):
        run = reserve_validation_epoch(
            project_root,
            feature_dir,
            stage="review" if purpose == "delivery" else "implement",
            purpose=purpose,
            fingerprint=fingerprint,
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )
        complete_validation_epoch(
            project_root,
            feature_dir,
            run_id=run["run_id"],
            status="passed",
            evidence_refs=[f"logs/{purpose}.txt"],
            summary=f"{purpose} passed",
        )

    retry = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="review",
        purpose="delivery",
        fingerprint="sha-d",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    assert retry["run_id"] == "V3"
    assert retry["attempt_id"] == "V3-A2"
    assert retry["used_epochs"] == 3
    assert retry["used_attempts"] == 4

    status = validation_budget_status(project_root, feature_dir)
    assert status["used_epochs"] == 3
    assert status["remaining_epochs"] == 0
    assert status["used_attempts"] == 4
    assert [run["purpose"] for run in status["runs"]] == [
        "baseline",
        "convergence",
        "delivery",
    ]


def test_failed_epoch_cannot_be_retried_without_a_new_fingerprint(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    run = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    failed = complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=run["run_id"],
        status="failed",
        evidence_refs=["logs/failure.txt"],
        summary="One test failed",
    )
    assert "Diagnose and repair" in failed["next_action"]

    with pytest.raises(ValidationBudgetError, match="unchanged fingerprint"):
        reserve_validation_epoch(
            project_root,
            feature_dir,
            stage="review",
            purpose="delivery",
            fingerprint="sha-a",
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )


def test_interrupted_attempt_retries_same_logical_epoch_without_consuming_review(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    first = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    interrupted = complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=first["run_id"],
        status="interrupted",
        failure_kind="runner_timeout",
        evidence_refs=["logs/runner-timeout.txt"],
        summary="The execution host terminated the command before a verdict.",
    )
    assert "Do not rerun the whole gate blindly" in interrupted["next_action"]
    assert "bounded shards" in interrupted["next_action"]

    retry = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )

    assert retry["run_id"] == first["run_id"]
    assert retry["attempt_id"] == "V1-A2"
    assert retry["used_epochs"] == 1
    assert retry["used_attempts"] == 2
    assert retry["remaining_epochs"] == 2

    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=retry["run_id"],
        status="passed",
        evidence_refs=["logs/convergence-pass.txt"],
        summary="Convergence passed after runner recovery.",
    )
    delivery = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="review",
        purpose="delivery",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    assert delivery["run_id"] == "V2"
    assert delivery["remaining_epochs"] == 1


@pytest.mark.parametrize(
    ("status", "failure_kind", "message"),
    (
        ("failed", "runner_timeout", "runner, harness, and environment loss"),
        ("interrupted", "assertion", "must be failed, not interrupted"),
    ),
)
def test_validation_outcome_rejects_failure_kind_misclassification(
    tmp_path: Path,
    status: str,
    failure_kind: str,
    message: str,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    run = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )

    with pytest.raises(ValidationBudgetError, match=message):
        complete_validation_epoch(
            project_root,
            feature_dir,
            run_id=run["run_id"],
            status=status,
            failure_kind=failure_kind,
            evidence_refs=["logs/outcome.txt"],
            summary="The caller supplied the wrong outcome class.",
        )


def test_validation_rejects_a_nonlatest_running_attempt(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    run = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=run["run_id"],
        status="interrupted",
        failure_kind="runner_timeout",
        evidence_refs=["logs/runner-timeout.txt"],
        summary="The runner timed out.",
    )
    reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    ledger_path = (
        feature_dir / "implementation-review" / "validation-runs.json"
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["runs"][0]["attempts"][0]["status"] = "running"
    ledger["runs"][0]["attempts"][0]["failure_kind"] = None
    ledger["runs"][0]["attempts"][0]["evidence_refs"] = []
    ledger["runs"][0]["attempts"][0]["summary"] = ""
    ledger["runs"][0]["attempts"][0]["completed_at"] = ""
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ValidationBudgetError, match="latest attempt may be running"):
        validation_budget_status(project_root, feature_dir)


def test_validation_rejects_late_baseline_and_non_three_gate_policy(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    convergence = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=convergence["run_id"],
        status="passed",
        evidence_refs=["logs/convergence.txt"],
        summary="Convergence passed.",
    )
    with pytest.raises(ValidationBudgetError, match="early optional gate"):
        reserve_validation_epoch(
            project_root,
            feature_dir,
            stage="implement",
            purpose="baseline",
            fingerprint="sha-a",
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )

    task_index_path = feature_dir / "task-index.json"
    task_index = json.loads(task_index_path.read_text(encoding="utf-8"))
    task_index["validation_policy"]["max_epochs"] = 2
    task_index_path.write_text(json.dumps(task_index), encoding="utf-8")
    with pytest.raises(ValidationBudgetError, match="must equal 3"):
        validation_budget_status(project_root, feature_dir)


@pytest.mark.parametrize(
    ("active_stage", "requested_stage", "purpose"),
    (
        ("review", "implement", "convergence"),
        ("implement", "review", "delivery"),
    ),
)
def test_validation_gate_requires_active_stage_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    active_stage: str,
    requested_stage: str,
    purpose: str,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    (feature_dir / "workflow.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        "specify_cli.workflow_runtime.show_workflow",
        lambda _feature: {
            "data": {"stage": active_stage, "status": "active"}
        },
    )

    with pytest.raises(ValidationBudgetError, match="workflow ownership"):
        reserve_validation_epoch(
            project_root,
            feature_dir,
            stage=requested_stage,
            purpose=purpose,
            fingerprint="sha-a",
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )


def test_running_attempt_cannot_be_finished_after_stage_ownership_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    attempt = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    (feature_dir / "workflow.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        "specify_cli.workflow_runtime.show_workflow",
        lambda _feature: {
            "data": {"stage": "review", "status": "active"}
        },
    )

    with pytest.raises(ValidationBudgetError, match="workflow ownership"):
        complete_validation_epoch(
            project_root,
            feature_dir,
            run_id=attempt["run_id"],
            status="passed",
            evidence_refs=["logs/convergence.txt"],
            summary="Convergence passed.",
        )


def test_assertion_failure_retries_same_gate_only_after_fingerprint_changes(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    first = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=first["run_id"],
        status="failed",
        failure_kind="assertion",
        evidence_refs=["logs/assertion.txt"],
        summary="One assertion failed.",
    )

    retry = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-b",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )

    assert retry["run_id"] == "V1"
    assert retry["attempt_id"] == "V1-A2"
    assert retry["used_epochs"] == 1
    assert retry["used_attempts"] == 2


def test_legacy_timeout_status_is_migrated_to_retryable_interruption(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    ledger_path = feature_dir / "implementation-review" / "validation-runs.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "feature_epochs",
                "budget_scope": "implement-review",
                "max_epochs": 3,
                "runs": [
                    {
                        "run_id": "V1",
                        "stage": "implement",
                        "purpose": "convergence-and-available-real-evidence",
                        "fingerprint": "sha-a",
                        "commands": ["pytest -q"],
                        "covered_task_ids": ["T001"],
                        "status": "failed-timeout",
                        "evidence_refs": ["logs/timeout.txt"],
                        "summary": "Runner stopped after 124 seconds.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = validation_budget_status(project_root, feature_dir)

    assert status["version"] == 2
    assert status["runs"][0]["purpose"] == "convergence"
    assert status["runs"][0]["status"] == "interrupted"
    assert status["runs"][0]["failure_kind"] == "runner_timeout"
    retry = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    assert retry["run_id"] == "V1"
    assert retry["attempt_id"] == "V1-A2"


def test_migrated_legacy_history_cannot_be_rewritten(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    ledger_path = feature_dir / "implementation-review" / "validation-runs.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "feature_epochs",
                "budget_scope": "implement-review",
                "max_epochs": 3,
                "runs": [
                    {
                        "run_id": "V1",
                        "stage": "implement",
                        "purpose": "convergence",
                        "fingerprint": "sha-a",
                        "commands": ["pytest -q"],
                        "covered_task_ids": ["T001"],
                        "status": "failed-timeout",
                        "evidence_refs": ["logs/timeout.txt"],
                        "summary": "Runner stopped after 124 seconds.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["runs"][0]["attempts"][0]["fingerprint"] = "rewritten"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ValidationBudgetError, match="migrated attempt history"):
        validation_budget_status(project_root, feature_dir)


def test_validation_ledger_rejects_reordered_logical_gates(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    for purpose, stage, fingerprint in (
        ("convergence", "implement", "sha-a"),
        ("delivery", "review", "sha-b"),
    ):
        run = reserve_validation_epoch(
            project_root,
            feature_dir,
            stage=stage,
            purpose=purpose,
            fingerprint=fingerprint,
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )
        complete_validation_epoch(
            project_root,
            feature_dir,
            run_id=run["run_id"],
            status="passed",
            evidence_refs=[f"logs/{purpose}.txt"],
            summary=f"{purpose} passed.",
        )
    ledger_path = feature_dir / "implementation-review" / "validation-runs.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["runs"].reverse()
    for index, run in enumerate(ledger["runs"], start=1):
        run["run_id"] = f"V{index}"
        for attempt_index, attempt in enumerate(run["attempts"], start=1):
            attempt["attempt_id"] = f"V{index}-A{attempt_index}"
        run["attempt_id"] = run["attempts"][-1]["attempt_id"]
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ValidationBudgetError, match="must remain ordered"):
        validation_budget_status(project_root, feature_dir)


def test_validation_ledger_rejects_unknown_run_status(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    ledger_path = feature_dir / "implementation-review" / "validation-runs.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "version": 2,
                "mode": "feature_epochs",
                "budget_scope": "implement-review",
                "max_epochs": 3,
                "runs": [
                    {
                        "run_id": "V1",
                        "stage": "implement",
                        "purpose": "convergence",
                        "fingerprint": "sha-a",
                        "commands": ["pytest -q"],
                        "covered_task_ids": ["T001"],
                        "status": "failed-timeout",
                        "failure_kind": None,
                        "evidence_refs": [],
                        "summary": "",
                        "attempts": [
                            {
                                "attempt_id": "V1-A1",
                                "fingerprint": "sha-a",
                                "commands": ["pytest -q"],
                                "covered_task_ids": ["T001"],
                                "status": "failed-timeout",
                                "failure_kind": None,
                                "evidence_refs": [],
                                "summary": "",
                                "started_at": "",
                                "completed_at": "",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationBudgetError, match="unsupported status"):
        validation_budget_status(project_root, feature_dir)


def test_validation_budget_allows_only_one_running_epoch(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )

    with pytest.raises(ValidationBudgetError, match="already running"):
        reserve_validation_epoch(
            project_root,
            feature_dir,
            stage="review",
            purpose="delivery",
            fingerprint="sha-b",
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )


def test_validation_budget_rejects_reset_below_implementation_handoff_floor(
    tmp_path: Path,
) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    run = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=run["run_id"],
        status="passed",
        evidence_refs=["logs/convergence.txt"],
        summary="Convergence passed",
    )
    status = validation_budget_status(project_root, feature_dir)
    (feature_dir / "implementation-handoff.json").write_text(
        json.dumps(
            {
                "validation_policy": {
                    "mode": "feature_epochs",
                    "max_epochs": 3,
                    "budget_scope": "implement-review",
                    "budget_ref": "implementation-review/validation-runs.json",
                    "heavy_gate_owner": "leader",
                },
                "validation_budget": {
                    "ledger_ref": status["ledger_ref"],
                    "max_epochs": status["max_epochs"],
                    "used_epochs": status["used_epochs"],
                    "consumed_runs_sha256": status["runs_sha256"],
                },
            }
        ),
        encoding="utf-8",
    )
    ledger_path = feature_dir / "implementation-review" / "validation-runs.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["runs"] = []
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ValidationBudgetError, match="handoff floor"):
        validation_budget_status(project_root, feature_dir)


def test_validation_budget_rejects_rewritten_handoff_history(tmp_path: Path) -> None:
    project_root, feature_dir = _write_packet_project(
        tmp_path, feature_epochs=True
    )
    run = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint="sha-a",
        commands=["pytest -q"],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=run["run_id"],
        status="passed",
        evidence_refs=["logs/convergence.txt"],
        summary="Convergence passed",
    )
    status = validation_budget_status(project_root, feature_dir)
    (feature_dir / "implementation-handoff.json").write_text(
        json.dumps(
            {
                "validation_policy": {
                    "mode": "feature_epochs",
                    "max_epochs": 3,
                    "budget_scope": "implement-review",
                    "budget_ref": "implementation-review/validation-runs.json",
                    "heavy_gate_owner": "leader",
                },
                "validation_budget": {
                    "ledger_ref": status["ledger_ref"],
                    "max_epochs": status["max_epochs"],
                    "used_epochs": status["used_epochs"],
                    "consumed_runs_sha256": status["runs_sha256"],
                },
            }
        ),
        encoding="utf-8",
    )
    ledger_path = feature_dir / "implementation-review" / "validation-runs.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["runs"][0]["summary"] = "rewritten history"
    ledger["runs"][0]["attempts"][-1]["summary"] = "rewritten history"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ValidationBudgetError, match="history digest"):
        validation_budget_status(project_root, feature_dir)


def test_structured_templates_share_one_three_epoch_validation_budget() -> None:
    project_root = Path(__file__).resolve().parents[2]
    template_dir = project_root / "templates"
    task_index = json.loads(
        (template_dir / "task-index-template.json").read_text(encoding="utf-8")
    )
    task_packet = json.loads(
        (template_dir / "task-packet-template.json").read_text(encoding="utf-8")
    )
    implement_state = json.loads(
        (template_dir / "implement-execution-state-template.json").read_text(
            encoding="utf-8"
        )
    )
    expected_policy = {
        "mode": "feature_epochs",
        "max_epochs": 3,
        "budget_scope": "implement-review",
        "budget_ref": "implementation-review/validation-runs.json",
        "heavy_gate_owner": "leader",
    }

    assert task_index["validation_policy"] == expected_policy
    assert task_packet["validation_policy"] == expected_policy
    assert task_packet["task_checks"] == []
    assert implement_state["validation_budget"] == {
        "budget_ref": "implementation-review/validation-runs.json",
        "max_epochs": 3,
        "used_epochs": 0,
        "used_attempts": 0,
        "active_run_id": None,
        "active_attempt_id": None,
    }


def test_task_generation_surfaces_separate_task_checks_from_shared_gates() -> None:
    project_root = Path(__file__).resolve().parents[2]
    classic = "\n".join(
        (project_root / path).read_text(encoding="utf-8")
        for path in (
            "templates/commands/tasks.md",
            "templates/command-references/tasks/task-packet-schema.md",
            "templates/tasks-template.md",
        )
    ).lower()
    advanced = (
        project_root / "templates/advanced-skills/spx-tasks/SKILL.md"
    ).read_text(encoding="utf-8").lower()

    for surface in (classic, advanced):
        assert "validation_policy" in surface
        assert "feature_epochs" in surface
        assert "task_checks" in surface
        assert "max_epochs" in surface
        assert "implement-review" in surface
        assert "logical" in surface
        assert "attempt" in surface
        assert "timeout" in surface
