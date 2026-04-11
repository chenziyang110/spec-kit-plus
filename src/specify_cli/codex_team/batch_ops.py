"""Batch record synchronization helpers for Codex team runtime."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.codex_team.runtime_state import BatchRecord, batch_record_from_json, task_record_from_json
from specify_cli.codex_team.state_paths import batch_record_path, task_record_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_batch(project_root: Path, batch_id: str) -> BatchRecord | None:
    path = batch_record_path(project_root, batch_id)
    if not path.exists():
        return None
    return batch_record_from_json(path.read_text(encoding="utf-8"))


def _save_batch(project_root: Path, batch: BatchRecord) -> None:
    path = batch_record_path(project_root, batch.batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(batch), ensure_ascii=False, indent=2), encoding="utf-8")


def _load_task(project_root: Path, task_id: str):
    path = task_record_path(project_root, task_id)
    if not path.exists():
        return None
    return task_record_from_json(path.read_text(encoding="utf-8"))


def _save_task(project_root: Path, record) -> None:
    path = task_record_path(project_root, record.task_id)
    path.write_text(json.dumps(asdict(record), ensure_ascii=False), encoding="utf-8")


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
            batch.status = "failed"
            batch.updated_at = _utc_now()
            _save_batch(project_root, batch)
            for member_id in batch.task_ids:
                _set_join_point_status(project_root, member_id, join_point_name, "failed")
            continue
        if statuses and statuses == {"completed"}:
            batch.status = "completed"
            batch.updated_at = _utc_now()
            _save_batch(project_root, batch)
            for member_id in batch.task_ids:
                _set_join_point_status(project_root, member_id, join_point_name, "complete")
