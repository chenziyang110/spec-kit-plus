import json
from pathlib import Path

import pytest

from specify_cli.codex_team.auto_dispatch import (
    AutoDispatchUnavailableError,
    find_next_ready_parallel_batch,
    parse_tasks_markdown,
    route_ready_parallel_batch,
)
from specify_cli.codex_team.state_paths import batch_record_path, dispatch_record_path, runtime_session_path
from specify_cli.codex_team.task_ops import claim_task, get_task, transition_task_status


def _write_feature_tasks(project_root: Path, content: str) -> Path:
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    tasks_path = feature_dir / "tasks.md"
    tasks_path.write_text(content, encoding="utf-8")
    return feature_dir


def test_parse_tasks_markdown_finds_parallel_batches_and_statuses(codex_team_project_root: Path):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert [task.task_id for task in parsed.tasks] == ["T001", "T002", "T003"]
    assert parsed.tasks[0].completed is True
    assert parsed.tasks[1].parallel is True
    assert parsed.parallel_batches[0].batch_name == "Parallel Batch 1.1"
    assert parsed.parallel_batches[0].task_ids == ["T002", "T003"]


def test_find_next_ready_parallel_batch_requires_prior_tasks_complete(codex_team_project_root: Path):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [ ] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B
- [X] T004 Done later

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert find_next_ready_parallel_batch(parsed) is None


def test_route_ready_parallel_batch_dispatches_each_task(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B
- [ ] T004 Sequential follow-up

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    result = route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    assert result.batch_name == "Parallel Batch 1.1"
    assert result.dispatched_task_ids == ["T002", "T003"]
    assert json.loads(runtime_session_path(codex_team_project_root, "default").read_text(encoding="utf-8"))["status"] == "running"
    assert dispatch_record_path(codex_team_project_root, "default-parallel-batch-1-1-t002").exists()
    assert dispatch_record_path(codex_team_project_root, "default-parallel-batch-1-1-t003").exists()
    batch_payload = json.loads(batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["batch_name"] == "Parallel Batch 1.1"
    assert batch_payload["join_point_name"] == "Join Point 1.1"
    assert batch_payload["status"] == "dispatched"
    assert batch_payload["task_ids"] == ["T002", "T003"]
    assert batch_payload["request_ids"] == [
        "default-parallel-batch-1-1-t002",
        "default-parallel-batch-1-1-t003",
    ]
    task = get_task(codex_team_project_root, "T002")
    assert task.metadata["join_points"]["Join Point 1.1"]["status"] == "pending"
    assert task.metadata["join_points"]["Join Point 1.1"]["details"]["batch_name"] == "Parallel Batch 1.1"


def test_route_ready_parallel_batch_requires_runtime_backend(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    with pytest.raises(AutoDispatchUnavailableError):
        route_ready_parallel_batch(
            codex_team_project_root,
            feature_dir=feature_dir,
            session_id="default",
        )


def test_terminal_task_completion_auto_completes_batch(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    for task_id in ("T002", "T003"):
        record = get_task(codex_team_project_root, task_id)
        token = claim_task(
            codex_team_project_root,
            task_id=task_id,
            worker_id=f"{task_id.lower()}-worker",
            expected_version=record.version,
        )
        in_progress = transition_task_status(
            codex_team_project_root,
            task_id=task_id,
            new_status="in_progress",
            owner=f"{task_id.lower()}-worker",
            expected_version=record.version + 1,
            claim_token=token,
        )
        transition_task_status(
            codex_team_project_root,
            task_id=task_id,
            new_status="completed",
            owner=f"{task_id.lower()}-worker",
            expected_version=in_progress.version,
            claim_token=token,
        )

    batch_payload = json.loads(batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["status"] == "completed"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "complete"


def test_terminal_task_failure_marks_batch_failed(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    record = get_task(codex_team_project_root, "T002")
    token = claim_task(
        codex_team_project_root,
        task_id="T002",
        worker_id="t002-worker",
        expected_version=record.version,
    )
    in_progress = transition_task_status(
        codex_team_project_root,
        task_id="T002",
        new_status="in_progress",
        owner="t002-worker",
        expected_version=record.version + 1,
        claim_token=token,
    )
    transition_task_status(
        codex_team_project_root,
        task_id="T002",
        new_status="failed",
        owner="t002-worker",
        expected_version=in_progress.version,
        claim_token=token,
    )

    batch_payload = json.loads(batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["status"] == "failed"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "failed"
