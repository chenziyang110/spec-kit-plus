"""State aggregation for the `sp-teams watch` surface."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifests import DispatchRecord, dispatch_record_from_json, runtime_session_from_json
from .runtime_state import (
    BatchRecord,
    TaskRecord,
    WorkerHeartbeat,
    batch_record_from_json,
    task_record_from_json,
    worker_heartbeat_from_json,
)
from .state_paths import codex_team_state_root, runtime_session_path


@dataclass(slots=True)
class WatchProblem:
    source: str
    kind: str
    message: str


@dataclass(slots=True)
class FailedDispatchSummary:
    request_id: str
    target_worker: str
    reason: str
    status: str


@dataclass(slots=True)
class WatchMemberSummary:
    worker_id: str
    status: str
    task_id: str
    task_summary: str
    freshness: str
    activity_age_seconds: int | None


@dataclass(slots=True)
class WatchFlowSummary:
    task_status_counts: dict[str, int]
    blocked_batch_ids: list[str]
    awaiting_review_batch_ids: list[str]
    failed_dispatches: list[FailedDispatchSummary]


@dataclass(slots=True)
class WatchSnapshot:
    session_id: str
    session_status: str
    member_count: int
    task_count: int
    members: list[WatchMemberSummary]
    flow: WatchFlowSummary
    problems: list[WatchProblem]


def _normalize_timestamp(raw: str) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _read_json_record(path: Path, parser, problems: list[WatchProblem], *, kind: str):
    try:
        return parser(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:  # pragma: no cover - defensive, covered by problem assertions
        problems.append(WatchProblem(source=str(path), kind=kind, message=str(exc)))
        return None


def _list_task_records(state_root: Path, problems: list[WatchProblem]) -> list[TaskRecord]:
    tasks_root = state_root / "tasks"
    if not tasks_root.exists():
        return []
    records: list[TaskRecord] = []
    for path in sorted(tasks_root.glob("*.json")):
        record = _read_json_record(path, task_record_from_json, problems, kind="corrupt-task")
        if record is not None:
            records.append(record)
    return records


def _list_batch_records(state_root: Path, problems: list[WatchProblem]) -> list[BatchRecord]:
    batches_root = state_root / "batches"
    if not batches_root.exists():
        return []
    records: list[BatchRecord] = []
    for path in sorted(batches_root.glob("*.json")):
        record = _read_json_record(path, batch_record_from_json, problems, kind="corrupt-batch")
        if record is not None:
            records.append(record)
    return records


def _list_dispatch_records(state_root: Path, problems: list[WatchProblem]) -> list[DispatchRecord]:
    dispatch_root = state_root / "dispatch"
    if not dispatch_root.exists():
        return []
    records: list[DispatchRecord] = []
    for path in sorted(dispatch_root.glob("*.json")):
        record = _read_json_record(path, dispatch_record_from_json, problems, kind="corrupt-dispatch")
        if record is not None:
            records.append(record)
    return records


def _list_worker_heartbeats(state_root: Path, problems: list[WatchProblem]) -> dict[str, WorkerHeartbeat]:
    heartbeats_root = state_root / "workers" / "heartbeat"
    if not heartbeats_root.exists():
        return {}
    records: dict[str, WorkerHeartbeat] = {}
    for path in sorted(heartbeats_root.glob("*.json")):
        record = _read_json_record(path, worker_heartbeat_from_json, problems, kind="corrupt-heartbeat")
        if record is not None:
            records[record.worker_id] = record
    return records


def build_watch_snapshot(
    project_root: Path,
    *,
    session_id: str,
    now: datetime | None = None,
    stale_after_seconds: int = 90,
) -> WatchSnapshot:
    now_value = now or datetime.now(timezone.utc)
    state_root = codex_team_state_root(project_root)
    problems: list[WatchProblem] = []

    session = _read_json_record(
        runtime_session_path(project_root, session_id),
        runtime_session_from_json,
        problems,
        kind="corrupt-session",
    )
    if session is None:
        problems.append(
            WatchProblem(
                source=f"session:{session_id}",
                kind="missing-session",
                message=f"Runtime session '{session_id}' is missing.",
            )
        )
        session_status = "unknown"
    else:
        session_status = session.status

    task_records = _list_task_records(state_root, problems)
    batch_records = _list_batch_records(state_root, problems)
    dispatch_records = _list_dispatch_records(state_root, problems)
    heartbeats = _list_worker_heartbeats(state_root, problems)

    task_by_owner: dict[str, TaskRecord] = {}
    for task in task_records:
        if task.owner and task.owner not in task_by_owner:
            task_by_owner[task.owner] = task

    member_ids = sorted(set(heartbeats) | set(task_by_owner))
    members: list[WatchMemberSummary] = []
    for worker_id in member_ids:
        heartbeat = heartbeats.get(worker_id)
        task = task_by_owner.get(worker_id)
        freshness = "fresh"
        activity_age_seconds: int | None = None
        status = heartbeat.status if heartbeat is not None else (task.status if task is not None else "unknown")

        if heartbeat is None:
            freshness = "missing"
            problems.append(
                WatchProblem(
                    source=f"worker:{worker_id}",
                    kind="missing-heartbeat",
                    message=f"Worker '{worker_id}' has no heartbeat record.",
                )
            )
        else:
            timestamp = _normalize_timestamp(heartbeat.timestamp)
            if timestamp is None:
                freshness = "unknown"
                problems.append(
                    WatchProblem(
                        source=f"worker:{worker_id}",
                        kind="invalid-heartbeat-timestamp",
                        message=f"Worker '{worker_id}' heartbeat timestamp is invalid.",
                    )
                )
            else:
                activity_age_seconds = max(0, int((now_value - timestamp).total_seconds()))
                if activity_age_seconds > stale_after_seconds:
                    freshness = "stale"
                    problems.append(
                        WatchProblem(
                            source=f"worker:{worker_id}",
                            kind="stale-heartbeat",
                            message=f"Worker '{worker_id}' heartbeat is stale.",
                        )
                    )

        members.append(
            WatchMemberSummary(
                worker_id=worker_id,
                status=status,
                task_id=task.task_id if task is not None else "",
                task_summary=task.summary if task is not None else "",
                freshness=freshness,
                activity_age_seconds=activity_age_seconds,
            )
        )

    task_status_counts = dict(Counter(task.status for task in task_records))
    blocked_batch_ids = sorted(batch.batch_id for batch in batch_records if batch.status == "blocked")
    awaiting_review_batch_ids = sorted(
        batch.batch_id for batch in batch_records if batch.review_status == "awaiting_review"
    )
    failed_dispatches = [
        FailedDispatchSummary(
            request_id=dispatch.request_id,
            target_worker=dispatch.target_worker,
            reason=dispatch.reason,
            status=dispatch.status,
        )
        for dispatch in dispatch_records
        if dispatch.status in {"failed", "retry_pending"}
    ]

    return WatchSnapshot(
        session_id=session_id,
        session_status=session_status,
        member_count=len(members),
        task_count=len(task_records),
        members=members,
        flow=WatchFlowSummary(
            task_status_counts=task_status_counts,
            blocked_batch_ids=blocked_batch_ids,
            awaiting_review_batch_ids=awaiting_review_batch_ids,
            failed_dispatches=failed_dispatches,
        ),
        problems=problems,
    )
