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


def test_validation_budget_reuses_identical_epoch_and_blocks_a_fourth(
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

    with pytest.raises(ValidationBudgetError, match="maximum of 3"):
        reserve_validation_epoch(
            project_root,
            feature_dir,
            stage="review",
            purpose="delivery",
            fingerprint="sha-d",
            commands=["pytest -q"],
            covered_task_ids=["T001"],
        )

    status = validation_budget_status(project_root, feature_dir)
    assert status["used_epochs"] == 3
    assert status["remaining_epochs"] == 0
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
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=run["run_id"],
        status="failed",
        evidence_refs=["logs/failure.txt"],
        summary="One test failed",
    )

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
        "active_run_id": None,
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
