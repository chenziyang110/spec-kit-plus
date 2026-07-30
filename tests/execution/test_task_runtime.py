import json
from pathlib import Path

import pytest

from specify_cli.execution.task_runtime import (
    TaskRuntimeError,
    accept_task,
    compile_task_packet,
    next_task,
    record_task_result,
    start_task,
)


def _write_feature(tmp_path: Path, *, task_count: int = 2) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / "specs" / "001-control-plane"
    feature.mkdir(parents=True)
    (project / ".specify" / "memory").mkdir(parents=True)
    (project / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- Preserve behavior.\n",
        encoding="utf-8",
    )
    tasks = [
        {
            "id": f"T{index:03d}",
            "objective": f"Implement task {index}",
            "expected_write_scope": [f"src/task_{index}.py"],
            "read_scope": ["src/contracts.py"],
            "required_refs": ["src/contracts.py"],
            "verification": [f"pytest tests/test_task_{index}.py -q"],
            "acceptance": [f"Task {index} works"],
        }
        for index in range(1, task_count + 1)
    ]
    (feature / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "source_revision": 7,
                "validation_policy": {
                    "mode": "feature_epochs",
                    "max_epochs": 3,
                    "budget_scope": "implement-review",
                    "budget_ref": "implementation-review/validation-runs.json",
                    "heavy_gate_owner": "leader",
                },
                "tasks": tasks,
            }
        ),
        encoding="utf-8",
    )
    (project / "src").mkdir()
    (project / "src" / "contracts.py").write_text(
        "# authoritative contract\n", encoding="utf-8"
    )
    (feature / "tasks.md").write_text(
        "# Tasks\n\n"
        + "".join(
            f"- [ ] T{index:03d} Implement task {index}\n"
            for index in range(1, task_count + 1)
        ),
        encoding="utf-8",
    )
    return project, feature


def test_compile_packet_writes_canonical_packet_and_returns_compact_receipt(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path)

    receipt = compile_task_packet(project, feature, "T001")

    packet_path = feature / "implementation-review" / "packets" / "T001.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["task_id"] == "T001"
    assert receipt["path"].replace("\\", "/").endswith(
        "implementation-review/packets/T001.json"
    )
    assert receipt["sha256"]
    assert "data" not in receipt
    assert len(json.dumps(receipt)) < 4096


def test_task_lifecycle_is_cli_owned_and_keeps_all_projections_aligned(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path)

    start_receipt = start_task(project, feature, "T001", execution_mode="leader-direct")
    lifecycle_path = feature / "implementation-review" / "tasks" / "T001.json"
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    task_index = json.loads((feature / "task-index.json").read_text(encoding="utf-8"))
    execution = json.loads(
        (feature / "implementation-review" / "execution-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert lifecycle["status"] == "in_progress"
    assert task_index["tasks"][0]["status"] == "in_progress"
    assert execution["current_task"] == "T001"
    assert start_receipt["revision"] == 1
    assert "- [ ] T001" in (feature / "tasks.md").read_text(encoding="utf-8")

    result_receipt = record_task_result(
        project,
        feature,
        "T001",
        {
            "task_id": "T001",
            "status": "success",
            "changed_files": ["src/task_1.py"],
            "validation_results": [
                {"command": "python -m compileall src", "status": "passed"}
            ],
            "summary": "Implemented task 1",
        },
    )
    assert result_receipt["worker_status"] == "success"
    assert "payload" not in result_receipt

    accepted = accept_task(project, feature, "T001")
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    task_index = json.loads((feature / "task-index.json").read_text(encoding="utf-8"))
    execution = json.loads(
        (feature / "implementation-review" / "execution-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert lifecycle["status"] == "accepted"
    assert task_index["tasks"][0]["status"] == "accepted"
    assert execution["completed_task_ids"] == ["T001"]
    assert execution["current_task"] is None
    assert "- [x] T001" in (feature / "tasks.md").read_text(encoding="utf-8")
    assert accepted["transaction_id"]
    assert accepted["next_task_id"] == "T002"


def test_accept_rejects_success_without_validation_evidence(tmp_path: Path) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    start_task(project, feature, "T001", execution_mode="delegated")
    record_task_result(
        project,
        feature,
        "T001",
        {
            "task_id": "T001",
            "status": "success",
            "changed_files": ["src/task_1.py"],
            "validation_results": [],
            "summary": "Changed code without evidence",
        },
    )

    with pytest.raises(TaskRuntimeError, match="validation"):
        accept_task(project, feature, "T001")

    assert "- [ ] T001" in (feature / "tasks.md").read_text(encoding="utf-8")


def test_accept_requires_every_task_check_to_have_a_passed_result(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    task_index_path = feature / "task-index.json"
    task_index = json.loads(task_index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["task_checks"] = ["pytest tests/unit -q"]
    task_index_path.write_text(json.dumps(task_index), encoding="utf-8")

    start_task(project, feature, "T001", execution_mode="leader-direct")
    record_task_result(
        project,
        feature,
        "T001",
        {
            "task_id": "T001",
            "status": "success",
            "changed_files": ["src/task_1.py"],
            "validation_results": [
                {"command": "python -m compileall src", "status": "passed"}
            ],
        },
    )

    with pytest.raises(TaskRuntimeError, match="task_checks"):
        accept_task(project, feature, "T001")


def test_blocked_result_gets_deterministic_recovery_instructions(tmp_path: Path) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    start_task(project, feature, "T001", execution_mode="leader-direct")

    record_task_result(
        project,
        feature,
        "T001",
        {
            "task_id": "T001",
            "status": "blocked",
            "blockers": ["Dependency unavailable"],
            "suggested_recovery_actions": [],
        },
    )

    result = json.loads(
        (feature / "worker-results" / "T001.json").read_text(encoding="utf-8")
    )
    assert result["suggested_recovery_actions"] == [
        "inspect the blocker details and resubmit the delegated task"
    ]


def test_next_task_returns_a_small_semantic_projection(tmp_path: Path) -> None:
    project, feature = _write_feature(tmp_path)

    projection = next_task(project, feature)

    assert projection == {
        "task_id": "T001",
        "status": "pending",
        "objective": "Implement task 1",
        "dependencies": [],
        "lifecycle_ref": "implementation-review/tasks/T001.json",
    }
