"""Batch record synchronization helpers for Codex team runtime."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.codex_team.manifests import runtime_session_from_json, runtime_state_payload
from specify_cli.codex_team.runtime_state import BatchRecord, batch_record_from_json, task_record_from_json
from specify_cli.codex_team.state_paths import batch_record_path, runtime_session_path, task_record_path
from specify_cli.orchestration.state_store import write_json


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_batch(project_root: Path, batch_id: str) -> BatchRecord | None:
    path = batch_record_path(project_root, batch_id)
    if not path.exists():
        return None
    return batch_record_from_json(path.read_text(encoding="utf-8"))


def _save_batch(project_root: Path, batch: BatchRecord) -> None:
    path = batch_record_path(project_root, batch.batch_id)
    write_json(path, asdict(batch))


def _load_task(project_root: Path, task_id: str):
    path = task_record_path(project_root, task_id)
    if not path.exists():
        return None
    return task_record_from_json(path.read_text(encoding="utf-8"))


def _save_task(project_root: Path, record) -> None:
    path = task_record_path(project_root, record.task_id)
    write_json(path, asdict(record))


def _load_runtime_session(project_root: Path, session_id: str):
    path = runtime_session_path(project_root, session_id)
    if not path.exists():
        return None
    return runtime_session_from_json(path.read_text(encoding="utf-8"))


def _save_runtime_session(project_root: Path, session) -> None:
    path = runtime_session_path(project_root, session.session_id)
    write_json(path, runtime_state_payload(session)["session"])


def _set_join_point_status(project_root: Path, task_id: str, join_point_name: str, status: str) -> None:
    record = _load_task(project_root, task_id)
    if record is None:
        return
    metadata = record.metadata or {}
    join_points = metadata.get("join_points", {})
    entry = join_points.get(join_point_name)
    if not entry:
        return
    entry["status"] = status
    entry["updated_at"] = _utc_now()
    record.metadata = metadata
    record.version += 1
    record.updated_at = _utc_now()
    _save_task(project_root, record)


def sync_batch_for_task(project_root: Path, task_id: str) -> None:
    """Update owning batch state after a task reaches a terminal state."""
    record = _load_task(project_root, task_id)
    if record is None or not record.metadata:
        return
    join_points = record.metadata.get("join_points", {})
    for join_point_name, join_point in join_points.items():
        details = join_point.get("details") or {}
        batch_id = details.get("batch_id")
        if not batch_id:
            continue
        batch = _load_batch(project_root, batch_id)
        if batch is None or batch.status in {"completed", "failed"}:
            continue
        task_records = [_load_task(project_root, member_id) for member_id in batch.task_ids]
        statuses = {task.status for task in task_records if task is not None}
        if "failed" in statuses:
            failed_tasks = [task for task in task_records if task is not None and task.status == "failed"]
            failure_classes = {
                (task.metadata or {}).get("failure_class", "critical")
                for task in failed_tasks
            }
            non_critical_only = (
                batch.batch_classification == "mixed_tolerance"
                and failure_classes
                and failure_classes <= {"non_critical", "transient"}
            )

            if non_critical_only:
                batch.status = "blocked"
                batch.updated_at = _utc_now()
                _save_batch(project_root, batch)
                for member_id in batch.task_ids:
                    _set_join_point_status(project_root, member_id, join_point_name, "blocked")
                continue

            batch.status = "failed"
            batch.updated_at = _utc_now()
            _save_batch(project_root, batch)
            for member_id in batch.task_ids:
                _set_join_point_status(project_root, member_id, join_point_name, "failed")
            session = _load_runtime_session(project_root, batch.session_id)
            if session is not None:
                session.status = "blocked"
                session.blocker_id = f"batch-{batch.batch_id}"
                session.finished_at = _utc_now()
                _save_runtime_session(project_root, session)
            continue
        if statuses and statuses == {"completed"}:
            batch.status = "completed"
            batch.updated_at = _utc_now()
            _save_batch(project_root, batch)
            for member_id in batch.task_ids:
                _set_join_point_status(project_root, member_id, join_point_name, "complete")
