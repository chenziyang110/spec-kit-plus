import json
from pathlib import Path
import re

import pytest

from specify_cli.codex_team.auto_dispatch import (
    AutoDispatchUnavailableError,
    find_next_ready_parallel_batch,
    launch_dispatched_worker,
    parse_tasks_markdown,
    route_ready_parallel_batch,
)
from specify_cli.codex_team.state_paths import (
    batch_record_path,
    dispatch_record_path,
    runtime_session_path,
    worker_heartbeat_path,
)
from specify_cli.codex_team.task_ops import claim_task, get_task, transition_task_status


def _write_feature_tasks(project_root: Path, content: str) -> Path:
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for delegated public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
            ]
        ),
        encoding="utf-8",
    )
    normalized_lines: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^(- \[[ xX]\] (T\d+)(?: \[P\])? .+)$", line)
        if match and "/" not in line:
            normalized_lines.append(f"{match.group(1)} in src/{match.group(2).lower()}.py")
        else:
            normalized_lines.append(line)
    normalized = "\n".join(normalized_lines)
    tasks_path = feature_dir / "tasks.md"
    tasks_path.write_text(normalized, encoding="utf-8")
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
    launched: list[tuple[str, str]] = []

    def _launch(project_root: Path, *, session_id: str, worker_id: str, task_id: str) -> None:
        launched.append((worker_id, task_id))
        worker_heartbeat_path(project_root, worker_id).parent.mkdir(parents=True, exist_ok=True)
        worker_heartbeat_path(project_root, worker_id).write_text(
            '{"worker_id":"%s","status":"ready","details":{},"schema_version":"1.0","created_at":"2026-04-13T00:00:00+00:00"}'
            % worker_id,
            encoding="utf-8",
        )

    monkeypatch.setattr("specify_cli.codex_team.auto_dispatch.launch_dispatched_worker", _launch)

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
    assert batch_payload["batch_classification"] == "strict"
    assert batch_payload["safe_preparation"] is False
    assert batch_payload["status"] == "dispatched"
    assert batch_payload["task_ids"] == ["T002", "T003"]
    assert batch_payload["request_ids"] == [
        "default-parallel-batch-1-1-t002",
        "default-parallel-batch-1-1-t003",
    ]
    assert launched == [("t002", "T002"), ("t003", "T003")]
    assert worker_heartbeat_path(codex_team_project_root, "t002").exists()
    assert worker_heartbeat_path(codex_team_project_root, "t003").exists()
    dispatch_payload = json.loads(
        dispatch_record_path(
            codex_team_project_root,
            "default-parallel-batch-1-1-t002",
        ).read_text(encoding="utf-8")
    )
    assert dispatch_payload["packet_path"]
    assert dispatch_payload["packet_summary"]["task_id"] == "T002"
    task = get_task(codex_team_project_root, "T002")
    assert task.metadata["join_points"]["Join Point 1.1"]["status"] == "pending"
    assert task.metadata["join_points"]["Join Point 1.1"]["details"]["batch_name"] == "Parallel Batch 1.1"
    assert task.metadata["join_points"]["Join Point 1.1"]["details"]["batch_classification"] == "strict"


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


def test_non_critical_failure_blocks_mixed_tolerance_batch_without_failing_session(monkeypatch, codex_team_project_root: Path):
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

    batch_path = batch_record_path(codex_team_project_root, "default-parallel-batch-1-1")
    batch_payload = json.loads(batch_path.read_text(encoding="utf-8"))
    batch_payload["batch_classification"] = "mixed_tolerance"
    batch_path.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
        failure_class="non_critical",
    )

    updated_batch = json.loads(batch_path.read_text(encoding="utf-8"))
    session_payload = json.loads(runtime_session_path(codex_team_project_root, "default").read_text(encoding="utf-8"))
    task_payload = get_task(codex_team_project_root, "T002")

    assert updated_batch["status"] == "blocked"
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "blocked"
    assert session_payload["status"] == "running"
