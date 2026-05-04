from __future__ import annotations

import json
import time
import secrets
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.codex_team.events import append_event, event_log_path
from specify_cli.codex_team.batch_ops import sync_batch_for_task
from specify_cli.codex_team.runtime_state import (
    task_claim_payload,
    task_record_from_json,
    task_record_payload,
)
from specify_cli.codex_team.state_paths import codex_team_state_root, task_claim_path, task_record_path
from specify_cli.orchestration.state_store import write_json

TASK_STATUS_PENDING = "pending"
TASK_STATUS_IN_PROGRESS = "in_progress"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    TASK_STATUS_PENDING: {TASK_STATUS_IN_PROGRESS},
    TASK_STATUS_IN_PROGRESS: {TASK_STATUS_COMPLETED, TASK_STATUS_FAILED},
    TASK_STATUS_COMPLETED: set(),
    TASK_STATUS_FAILED: set(),
}

TERMINAL_STATUSES = {TASK_STATUS_COMPLETED, TASK_STATUS_FAILED}


class TaskOpsError(RuntimeError):
    """Base exception for task operation failures."""


class ClaimConflictError(TaskOpsError):
    """Raised when a task is already claimed but another claim is attempted."""


class ClaimValidationError(TaskOpsError):
    """Raised when a claim token fails validation."""


class TransitionError(TaskOpsError):
    """Raised when an invalid status transition is requested."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_record_path(project_root: Path, task_id: str) -> Path:
    return task_record_path(project_root, task_id)


def _claim_record_path(project_root: Path, claim_id: str) -> Path:
    return task_claim_path(project_root, claim_id)


def _load_claim_record(project_root: Path, claim_id: str) -> dict[str, Any]:
    path = _claim_record_path(project_root, claim_id)
    if not path.exists():
        raise ClaimValidationError(f"claim {claim_id} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_claim_for_record(project_root: Path, record: Any) -> dict[str, Any] | None:
    metadata = _ensure_metadata(record)
    current_claim = metadata.get("current_claim")
    if not current_claim:
        return None
    claim_id = current_claim.get("claim_id")
    if not claim_id:
        return None
    try:
        return _load_claim_record(project_root, claim_id)
    except ClaimValidationError:
        return None


def _save_task_record(project_root: Path, record: Any) -> None:
    path = _task_record_path(project_root, record.task_id)
    payload = asdict(record)
    write_json(path, payload)


def _log_task_event(project_root: Path, *, kind: str, payload: dict[str, Any]) -> None:
    log_path = event_log_path(project_root, session_id=None)
    append_event(
        log_path,
        event_id=f"task-{payload.get('task_id', 'unknown')}-{uuid.uuid4().hex}",
        kind=kind,
        payload=payload,
    )


def _ensure_metadata(record: Any) -> dict[str, Any]:
    metadata = getattr(record, "metadata", None)
    if metadata is None:
        metadata = {}
        setattr(record, "metadata", metadata)
    return metadata


def _ensure_expected_version(record: Any, expected_version: int | None) -> None:
    if expected_version is not None and record.version != expected_version:
        raise TaskOpsError(f"expected version {expected_version}, found {record.version}")


def _validate_claim(
    project_root: Path,
    record: Any,
    claim_token: str | None,
    worker_id: str,
) -> dict[str, Any]:
    if not claim_token:
        raise ClaimValidationError("claim token is required")
    metadata = _ensure_metadata(record)
    current_claim = metadata.get("current_claim")
    if not current_claim or current_claim.get("claim_id") != claim_token:
        raise ClaimValidationError("no active claim")
    claim_record = _load_claim_record(project_root, claim_token)
    if claim_record.get("claim_id") != claim_token:
        raise ClaimValidationError("claim id mismatch")
    if claim_record.get("task_id") != record.task_id:
        raise ClaimValidationError("claim task mismatch")
    if claim_record.get("worker_id") != worker_id:
        raise ClaimValidationError("claim token mismatch")
    # keep metadata aligned with canonical claim record
    metadata["current_claim"] = {
        "claim_id": claim_record.get("claim_id"),
        "worker_id": claim_record.get("worker_id"),
        "version": claim_record.get("version"),
        "created_at": claim_record.get("created_at"),
    }
    return claim_record


def create_task(
    project_root: Path,
    *,
    task_id: str,
    summary: str = "",
    metadata: dict[str, Any] | None = None,
) -> Any:
    path = _task_record_path(project_root, task_id)
    if path.exists():
        raise TaskOpsError(f"task {task_id} already exists")

    payload = task_record_payload(
        task_id=task_id,
        summary=summary,
        metadata=metadata,
    )
    write_json(path, payload)

    record = task_record_from_json(path.read_text(encoding="utf-8"))
    _log_task_event(
        project_root,
        kind="task.created",
        payload={"task_id": task_id, "summary": summary},
    )
    return record


def get_task(project_root: Path, task_id: str) -> Any:
    path = _task_record_path(project_root, task_id)
    if not path.exists():
        raise TaskOpsError(f"task {task_id} not found")
    last_error: json.JSONDecodeError | None = None
    for _ in range(5):
        text = path.read_text(encoding="utf-8")
        try:
            return task_record_from_json(text)
        except json.JSONDecodeError as exc:
            last_error = exc
            if text.strip():
                raise
            time.sleep(0.02)
    if last_error is not None:
        raise last_error
    return task_record_from_json(path.read_text(encoding="utf-8"))


def list_tasks(project_root: Path) -> list[Any]:
    base = codex_team_state_root(project_root) / "tasks"
    if not base.exists():
        return []
    records: list[Any] = []
    for file in sorted(base.glob("*.json")):
        records.append(task_record_from_json(file.read_text(encoding="utf-8")))
    return records


def update_task_metadata(
    project_root: Path,
    task_id: str,
    *,
    summary: str | None = None,
    owner: str | None = None,
    metadata: dict[str, Any] | None = None,
    expected_version: int | None = None,
) -> Any:
    record = get_task(project_root, task_id)
    _ensure_expected_version(record, expected_version)

    changed = False
    if summary is not None and summary != record.summary:
        record.summary = summary
        changed = True
    if owner is not None and owner != record.owner:
        record.owner = owner
        changed = True
    if metadata:
        existing = _ensure_metadata(record)
        existing.update(metadata)
        changed = True

    if not changed:
        return record

    record.version += 1
    record.updated_at = _now()
    _save_task_record(project_root, record)
    _log_task_event(
        project_root,
        kind="task.metadata.updated",
        payload={"task_id": task_id, "summary": record.summary},
    )
    return record


def claim_task(
    project_root: Path,
    *,
    task_id: str,
    worker_id: str,
    expected_version: int | None = None,
) -> str:
    record = get_task(project_root, task_id)
    _ensure_expected_version(record, expected_version)

    if record.status != TASK_STATUS_PENDING:
        raise TaskOpsError("only pending tasks can be claimed")

    metadata = _ensure_metadata(record)
    if metadata.get("current_claim"):
        raise ClaimConflictError("task already has an active claim")

    claim_id = secrets.token_urlsafe(32)
    claim_payload = task_claim_payload(
        claim_id=claim_id,
        task_id=task_id,
        worker_id=worker_id,
        version=record.version,
    )

    claim_path = _claim_record_path(project_root, claim_id)
    write_json(claim_path, claim_payload)

    metadata["current_claim"] = {
        "claim_id": claim_payload["claim_id"],
        "worker_id": claim_payload["worker_id"],
        "version": claim_payload["version"],
        "created_at": claim_payload["created_at"],
    }

    record.version += 1
    record.updated_at = _now()
    _save_task_record(project_root, record)
    _log_task_event(
        project_root,
        kind="task.claimed",
        payload={
            "task_id": task_id,
            "worker_id": worker_id,
            "claim_id": claim_id,
        },
    )
    return claim_id


def transition_task_status(
    project_root: Path,
    *,
    task_id: str,
    new_status: str,
    owner: str,
    expected_version: int | None = None,
    claim_token: str | None = None,
    failure_class: str = "",
) -> Any:
    record = get_task(project_root, task_id)
    _ensure_expected_version(record, expected_version)

    if new_status not in ALLOWED_TRANSITIONS.get(record.status, set()):
        raise TransitionError(f"cannot move from {record.status} to {new_status}")

    _validate_claim(project_root, record, claim_token, owner)
    metadata = _ensure_metadata(record)

    record.status = new_status
    record.owner = owner
    if failure_class:
        metadata["failure_class"] = failure_class
    record.version += 1
    record.updated_at = _now()
    if new_status in TERMINAL_STATUSES:
        metadata.pop("current_claim", None)
    _save_task_record(project_root, record)
    _log_task_event(
        project_root,
        kind="task.status.updated",
        payload={
            "task_id": task_id,
            "status": new_status,
            "owner": owner,
        },
    )
    if new_status in TERMINAL_STATUSES:
        sync_batch_for_task(project_root, task_id)
    return record


def record_task_approval(
    project_root: Path,
    *,
    task_id: str,
    decision: str,
    worker_id: str,
    claim_token: str,
    expected_version: int | None = None,
    reason: str = "",
) -> dict[str, Any]:
    record = get_task(project_root, task_id)
    _ensure_expected_version(record, expected_version)
    metadata = _ensure_metadata(record)
    if record.status in TERMINAL_STATUSES:
        raise TaskOpsError("cannot record approvals on terminal tasks")
    claim_record = _validate_claim(project_root, record, claim_token, worker_id)

    normalized = decision.lower()
    if normalized not in {"approved", "rejected"}:
        raise TaskOpsError("decision must be 'approved' or 'rejected'")

    approvals = metadata.setdefault("approvals", [])
    entry = {
        "approval_id": secrets.token_urlsafe(16),
        "task_version": record.version,
        "task_status": record.status,
        "worker_id": worker_id,
        "decision": normalized,
        "reason": reason,
        "created_at": _now(),
        "claim_id": claim_record.get("claim_id"),
        "claim_worker_id": claim_record.get("worker_id"),
        "claim_version": claim_record.get("version"),
        "claim_created_at": claim_record.get("created_at"),
    }
    approvals.append(entry)

    record.version += 1
    record.updated_at = _now()
    _save_task_record(project_root, record)
    _log_task_event(
        project_root,
        kind=f"task.{normalized}",
        payload={"task_id": task_id, "worker_id": worker_id, "decision": normalized},
    )
    return entry


def mark_join_point(
    project_root: Path,
    *,
    task_id: str,
    join_point_name: str,
    expected_version: int,
    status: str = "complete",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = get_task(project_root, task_id)
    _ensure_expected_version(record, expected_version)
    metadata = _ensure_metadata(record)

    join_points = metadata.setdefault("join_points", {})
    claim_data = _canonical_claim_for_record(project_root, record)
    entry: dict[str, Any] = {
        "join_point_id": secrets.token_urlsafe(16),
        "name": join_point_name,
        "status": status,
        "task_version": record.version,
        "task_status": record.status,
        "created_at": _now(),
        "claim_id": claim_data.get("claim_id") if claim_data else None,
        "claim_worker_id": claim_data.get("worker_id") if claim_data else None,
        "claim_version": claim_data.get("version") if claim_data else None,
        "claim_created_at": claim_data.get("created_at") if claim_data else None,
    }
    if details:
        entry["details"] = details

    join_points[join_point_name] = entry

    record.version += 1
    record.updated_at = _now()
    _save_task_record(project_root, record)
    _log_task_event(
        project_root,
        kind="task.join_point",
        payload={"task_id": task_id, "join_point": join_point_name, "status": status},
    )
    return entry
