from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.codex_team.manifests import DispatchRecord, RuntimeSession, runtime_state_payload
from specify_cli.codex_team.runtime_state import batch_record_payload, task_record_payload, worker_heartbeat_payload
from specify_cli.codex_team.state_paths import (
    batch_record_path,
    dispatch_record_path,
    runtime_session_path,
    task_record_path,
    worker_heartbeat_path,
)
from specify_cli.codex_team.watch_state import build_watch_snapshot


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_watch_snapshot_summarizes_members_and_flow(codex_team_project_root: Path) -> None:
    project_root = codex_team_project_root

    session_payload = runtime_state_payload(RuntimeSession(session_id="default", status="running"))
    _write_json(runtime_session_path(project_root, "default"), session_payload["session"])

    _write_json(
        task_record_path(project_root, "T001"),
        task_record_payload(
            task_id="T001",
            summary="Implement watch snapshot aggregation",
            status="in_progress",
            owner="worker-1",
        ),
    )
    _write_json(
        task_record_path(project_root, "T002"),
        task_record_payload(
            task_id="T002",
            summary="Fix blocked dispatch",
            status="pending",
            owner="worker-2",
        ),
    )
    _write_json(
        batch_record_path(project_root, "batch-1"),
        batch_record_payload(
            batch_id="batch-1",
            batch_name="Parallel watch batch",
            session_id="default",
            feature_dir="specs/001-watch",
            task_ids=["T001", "T002"],
            request_ids=["req-1"],
            status="blocked",
            review_status="awaiting_review",
        ),
    )

    heartbeat_1 = worker_heartbeat_payload(worker_id="worker-1", status="executing")
    heartbeat_1["timestamp"] = "2026-04-26T00:00:45+00:00"
    _write_json(worker_heartbeat_path(project_root, "worker-1"), heartbeat_1)

    heartbeat_2 = worker_heartbeat_payload(worker_id="worker-2", status="blocked")
    heartbeat_2["timestamp"] = "2026-04-26T00:00:40+00:00"
    _write_json(worker_heartbeat_path(project_root, "worker-2"), heartbeat_2)

    dispatch = DispatchRecord(
        request_id="req-1",
        target_worker="worker-2",
        status="failed",
        reason="leader pane missing",
        packet_summary={"task_id": "T002", "summary": "Fix blocked dispatch"},
    )
    _write_json(
        dispatch_record_path(project_root, "req-1"),
        runtime_state_payload(RuntimeSession(session_id="default"), [dispatch])["dispatches"][0],
    )

    snapshot = build_watch_snapshot(
        project_root,
        session_id="default",
        now=datetime(2026, 4, 26, 0, 1, 0, tzinfo=timezone.utc),
    )

    assert snapshot.session_id == "default"
    assert snapshot.session_status == "running"
    assert snapshot.member_count == 2
    assert snapshot.task_count == 2

    worker_1 = next(member for member in snapshot.members if member.worker_id == "worker-1")
    assert worker_1.status == "executing"
    assert worker_1.task_id == "T001"
    assert worker_1.task_summary == "Implement watch snapshot aggregation"

    worker_2 = next(member for member in snapshot.members if member.worker_id == "worker-2")
    assert worker_2.status == "blocked"
    assert worker_2.task_id == "T002"

    assert snapshot.flow.task_status_counts == {"in_progress": 1, "pending": 1}
    assert snapshot.flow.blocked_batch_ids == ["batch-1"]
    assert snapshot.flow.awaiting_review_batch_ids == ["batch-1"]
    assert snapshot.flow.failed_dispatches[0].request_id == "req-1"
    assert snapshot.flow.failed_dispatches[0].reason == "leader pane missing"


def test_build_watch_snapshot_marks_stale_and_missing_state(codex_team_project_root: Path) -> None:
    project_root = codex_team_project_root

    _write_json(
        task_record_path(project_root, "T010"),
        task_record_payload(
            task_id="T010",
            summary="Watch a worker with stale heartbeat",
            status="in_progress",
            owner="worker-9",
        ),
    )

    heartbeat = worker_heartbeat_payload(worker_id="worker-9", status="executing")
    heartbeat["timestamp"] = "2026-04-26T00:00:00+00:00"
    _write_json(worker_heartbeat_path(project_root, "worker-9"), heartbeat)

    snapshot = build_watch_snapshot(
        project_root,
        session_id="missing-session",
        now=datetime(2026, 4, 26, 0, 2, 0, tzinfo=timezone.utc),
        stale_after_seconds=30,
    )

    assert snapshot.session_status == "unknown"
    assert any(problem.kind == "missing-session" for problem in snapshot.problems)

    worker = next(member for member in snapshot.members if member.worker_id == "worker-9")
    assert worker.freshness == "stale"
    assert any(problem.kind == "stale-heartbeat" for problem in snapshot.problems)
