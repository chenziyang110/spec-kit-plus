import json
import os
from pathlib import Path

import pytest

from specify_cli.execution.task_runtime import (
    TaskRuntimeError,
    accept_task,
    compile_task_packet,
    next_task,
    next_task_decision,
    record_task_result,
    reopen_task,
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
    assert (
        receipt["path"]
        .replace("\\", "/")
        .endswith("implementation-review/packets/T001.json")
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
    with pytest.raises(TaskRuntimeError, match="validation"):
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

    assert "- [ ] T001" in (feature / "tasks.md").read_text(encoding="utf-8")
    lifecycle = json.loads(
        (feature / "implementation-review" / "tasks" / "T001.json").read_text(
            encoding="utf-8"
        )
    )
    assert lifecycle["status"] == "in_progress"
    assert not (feature / "worker-results" / "T001.json").exists()


def test_accept_requires_every_task_check_to_have_a_passed_result(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    task_index_path = feature / "task-index.json"
    task_index = json.loads(task_index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["task_checks"] = ["pytest tests/unit -q"]
    task_index_path.write_text(json.dumps(task_index), encoding="utf-8")

    start_task(project, feature, "T001", execution_mode="leader-direct")
    with pytest.raises(TaskRuntimeError, match="task_checks"):
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


def test_success_result_rejects_failed_known_followup_before_mutation(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    start_task(project, feature, "T001", execution_mode="leader-direct")

    with pytest.raises(TaskRuntimeError, match="passed validation"):
        record_task_result(
            project,
            feature,
            "T001",
            {
                "task_id": "T001",
                "status": "success",
                "changed_files": ["src/task_1.py"],
                "validation_results": [
                    {"command": "python -m compileall src", "status": "passed"},
                    {
                        "kind": "known-followup",
                        "status": "failed",
                        "summary": "Refresh the downstream baseline later.",
                    },
                ],
            },
        )

    lifecycle = json.loads(
        (feature / "implementation-review" / "tasks" / "T001.json").read_text(
            encoding="utf-8"
        )
    )
    assert lifecycle["status"] == "in_progress"
    assert not (feature / "worker-results" / "T001.json").exists()


def test_blocked_result_gets_deterministic_recovery_instructions(
    tmp_path: Path,
) -> None:
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


def test_task_reopen_archives_old_result_and_preserves_dependency_graph(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=3)
    index_path = feature / "task-index.json"
    task_index = json.loads(index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0].update({"status": "accepted"})
    task_index["tasks"][1].update(
        {
            "status": "implemented",
            "dependencies": ["T001"],
            "task_checks": ["required check"],
            "result_ref": "worker-results/T002.json",
        }
    )
    task_index["tasks"][2].update({"status": "pending", "dependencies": ["T002"]})
    index_path.write_text(json.dumps(task_index), encoding="utf-8")
    (feature / "tasks.md").write_text(
        "# Tasks\n\n- [x] T001 accepted\n- [ ] T002 repair\n- [ ] T003 dependent\n",
        encoding="utf-8",
    )
    lifecycle_dir = feature / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T002.json").write_text(
        json.dumps(
            {
                "version": 1,
                "revision": 2,
                "task_id": "T002",
                "task_ref": "task-index.json#/tasks/1",
                "source_revision": 7,
                "execution_mode": "leader-direct",
                "packet_ref": None,
                "result_ref": "worker-results/T002.json",
                "status": "implemented",
                "changed_paths": ["src/task_2.py"],
                "validation": [{"command": "other check", "status": "passed"}],
                "review": None,
                "ui_verification": {"applicable": False},
                "obligation_evidence": [],
                "blockers": [],
                "recovery": None,
            }
        ),
        encoding="utf-8",
    )
    result_dir = feature / "worker-results"
    result_dir.mkdir()
    (result_dir / "T002.json").write_text(
        json.dumps(
            {
                "version": 1,
                "task_id": "T002",
                "status": "success",
                "changed_files": ["src/task_2.py"],
                "validation_results": [{"command": "other check", "status": "passed"}],
                "blockers": [],
                "suggested_recovery_actions": [],
            }
        ),
        encoding="utf-8",
    )
    execution_dir = feature / "implementation-review"
    (execution_dir / "execution-state.json").write_text(
        json.dumps(
            {
                "version": 3,
                "revision": 5,
                "status": "validating",
                "source_contract": "task-index.json",
                "source_revision": 7,
                "current_batch": None,
                "current_task": "T002",
                "next_action": "Validate and accept T002.",
                "completed_task_ids": ["T001"],
                "failed_task_ids": [],
                "retry_count": 0,
                "active_packet_refs": [],
                "blockers": [],
                "recovery": None,
                "open_gaps": [],
                "validation": [],
            }
        ),
        encoding="utf-8",
    )
    (feature / "workflow.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": feature.name,
                "revision": 7,
                "stage": "implement",
                "status": "active",
                "summary": "Implement tasks.",
                "blocker": None,
            }
        ),
        encoding="utf-8",
    )

    decision = next_task_decision(project, feature)
    assert decision["reason_code"] == "task-reopen-required"
    assert decision["blocked_task_id"] == "T002"
    with pytest.raises(TaskRuntimeError, match="revision"):
        reopen_task(
            project,
            feature,
            "T002",
            expected_task_revision=1,
            expected_workflow_revision=7,
            reason="Replace incomplete evidence.",
            evidence=["task-accept rejected the result"],
        )

    receipt = reopen_task(
        project,
        feature,
        "T002",
        expected_task_revision=2,
        expected_workflow_revision=7,
        reason="Replace incomplete evidence.",
        evidence=["task-accept rejected the result"],
    )
    assert receipt["task_status"] == "ready"
    history = json.loads((feature / receipt["history_ref"]).read_text(encoding="utf-8"))
    assert history["previous"]["validation"] == [
        {"command": "other check", "status": "passed"}
    ]
    marker = json.loads((result_dir / "T002.json").read_text(encoding="utf-8"))
    assert marker["status"] == "superseded"
    current_index = json.loads(index_path.read_text(encoding="utf-8"))
    assert [task.get("status", "pending") for task in current_index["tasks"]] == [
        "accepted",
        "ready",
        "pending",
    ]

    assert next_task_decision(project, feature)["task"]["task_id"] == "T002"
    start_task(project, feature, "T002", execution_mode="leader-direct")
    record_task_result(
        project,
        feature,
        "T002",
        {
            "task_id": "T002",
            "status": "success",
            "changed_files": ["src/task_2.py"],
            "validation_results": [{"command": "required check", "status": "passed"}],
        },
    )
    accept_task(project, feature, "T002")
    assert next_task_decision(project, feature)["task"]["task_id"] == "T003"


def test_task_reopen_rejects_symlinked_worker_result(tmp_path: Path) -> None:
    project, feature = _write_feature(tmp_path, task_count=2)
    index_path = feature / "task-index.json"
    task_index = json.loads(index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["status"] = "accepted"
    task_index["tasks"][1].update(
        {
            "status": "implemented",
            "dependencies": ["T001"],
            "task_checks": ["required check"],
            "result_ref": "worker-results/T002.json",
        }
    )
    index_path.write_text(json.dumps(task_index), encoding="utf-8")
    (feature / "tasks.md").write_text(
        "# Tasks\n\n- [x] T001 accepted\n- [ ] T002 repair\n", encoding="utf-8"
    )
    lifecycle_dir = feature / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True, exist_ok=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "version": 1,
                "revision": 1,
                "task_id": "T001",
                "status": "accepted",
                "validation": [{"command": "accepted check", "status": "passed"}],
                "blockers": [],
            }
        ),
        encoding="utf-8",
    )
    (lifecycle_dir / "T002.json").write_text(
        json.dumps(
            {
                "version": 1,
                "revision": 2,
                "task_id": "T002",
                "task_ref": "task-index.json#/tasks/1",
                "source_revision": 7,
                "execution_mode": "leader-direct",
                "packet_ref": None,
                "result_ref": "worker-results/T002.json",
                "status": "implemented",
                "changed_paths": ["src/task_2.py"],
                "validation": [{"command": "other check", "status": "passed"}],
                "review": None,
                "ui_verification": {"applicable": False},
                "obligation_evidence": [],
                "blockers": [],
                "recovery": None,
            }
        ),
        encoding="utf-8",
    )
    (feature / "workflow.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": feature.name,
                "revision": 7,
                "stage": "implement",
                "status": "active",
                "summary": "Implement tasks.",
                "blocker": None,
            }
        ),
        encoding="utf-8",
    )
    result_dir = feature / "worker-results"
    result_dir.mkdir()
    outside = project / "outside-result.json"
    outside.write_text('{"task_id":"T002","status":"success"}', encoding="utf-8")
    result_path = result_dir / "T002.json"
    try:
        os.symlink(outside, result_path)
    except (AttributeError, NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(
        TaskRuntimeError, match="symlink|cannot read current worker result"
    ):
        reopen_task(
            project,
            feature,
            "T002",
            expected_task_revision=2,
            expected_workflow_revision=7,
            reason="Replace incomplete evidence.",
            evidence=["task-accept rejected the recorded result"],
        )


def test_task_reopen_rejects_index_lifecycle_status_mismatch(tmp_path: Path) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
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
    index_path = feature / "task-index.json"
    task_index = json.loads(index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["status"] = "accepted"
    index_path.write_text(json.dumps(task_index), encoding="utf-8")

    with pytest.raises(TaskRuntimeError, match="task-index.json records status"):
        reopen_task(
            project,
            feature,
            "T001",
            expected_task_revision=2,
            expected_workflow_revision=0,
            reason="Attempt unsafe rollback.",
            evidence=["index and lifecycle disagree"],
        )


def test_task_next_never_offers_task_reopen_without_a_valid_revision(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    index_path = feature / "task-index.json"
    task_index = json.loads(index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["status"] = "implemented"
    index_path.write_text(json.dumps(task_index), encoding="utf-8")

    decision = next_task_decision(project, feature)

    assert decision["status"] == "blocked"
    assert decision["reason_code"] == "task-state-invalid"
    assert decision["blocked_task_id"] == "T001"
    assert decision["lifecycle_ref"] == "implementation-review/tasks/T001.json"
    assert "recovery_action" not in decision
    assert "--expected-task-revision" not in json.dumps(decision)


def test_task_next_rejects_symlinked_lifecycle_without_following_it(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    index_path = feature / "task-index.json"
    task_index = json.loads(index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["status"] = "implemented"
    index_path.write_text(json.dumps(task_index), encoding="utf-8")
    lifecycle_dir = feature / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    outside = project / "outside-lifecycle.json"
    outside.write_text(
        json.dumps(
            {
                "version": 1,
                "revision": 9,
                "task_id": "T001",
                "status": "implemented",
                "validation": [{"command": "outside", "status": "passed"}],
                "blockers": [],
            }
        ),
        encoding="utf-8",
    )
    try:
        os.symlink(outside, lifecycle_dir / "T001.json")
    except (AttributeError, NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    decision = next_task_decision(project, feature)

    assert decision["reason_code"] == "task-state-invalid"
    assert "symlink" in decision["state_error"].lower()
    assert "recovery_action" not in decision


def test_task_next_surfaces_workflow_blocker_instead_of_empty_task(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=1)
    (feature / "workflow.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": feature.name,
                "revision": 4,
                "stage": "implement",
                "status": "blocked",
                "summary": "Repair the recorded task state.",
                "blocker": {"blocker_id": "IMPLEMENT-RECOVERY"},
            }
        ),
        encoding="utf-8",
    )

    decision = next_task_decision(project, feature)

    assert decision["status"] == "blocked"
    assert decision["reason_code"] == "workflow-blocked"
    assert decision["task"] is None
    assert decision["resolution_action"]["capability_id"] == "workflow.resolve"


def test_task_next_reports_an_empty_task_graph_instead_of_an_empty_task(
    tmp_path: Path,
) -> None:
    project, feature = _write_feature(tmp_path, task_count=0)

    decision = next_task_decision(project, feature)

    assert decision["status"] == "blocked"
    assert decision["reason_code"] == "task-graph-invalid"
    assert decision["task"] is None
    assert decision["blocked_tasks"] == []
