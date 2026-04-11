"""Worker identity, heartbeat, and status snapshot helpers for Codex team runtime."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Any

from specify_cli.codex_team.events import append_event, event_log_path
from specify_cli.codex_team.runtime_state import (
    MonitorSnapshot,
    monitor_snapshot_from_json,
    monitor_snapshot_payload,
    worker_heartbeat_from_json,
    worker_heartbeat_payload,
    worker_identity_from_json,
    worker_identity_payload,
)
from specify_cli.codex_team.state_paths import (
    codex_team_state_root,
    worker_heartbeat_path,
    worker_identity_path,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _log_worker_event(project_root: Path, *, kind: str, payload: dict[str, Any]) -> None:
    log_path = event_log_path(project_root, session_id=None)
    append_event(
        log_path,
        event_id=f"worker-{kind}-{uuid.uuid4().hex}",
        kind=kind,
        payload=payload,
    )


def bootstrap_worker_identity(
    project_root: Path,
    *,
    worker_id: str,
    hostname: str,
    metadata: dict[str, Any] | None = None,
) -> Any:
    metadata_value = metadata or {}
    payload = worker_identity_payload(
        worker_id=worker_id,
        hostname=hostname,
        metadata=metadata_value,
    )
    path = worker_identity_path(project_root, worker_id)
    if path.exists():
        existing = worker_identity_from_json(path.read_text(encoding="utf-8"))
        if existing.hostname == hostname and existing.metadata == metadata_value:
            return existing
        payload["created_at"] = existing.created_at
        _write_json(path, payload)
        identity = worker_identity_from_json(path.read_text(encoding="utf-8"))
        _log_worker_event(
            project_root,
            kind="worker.identity.updated",
            payload={"worker_id": worker_id, "hostname": hostname},
        )
        return identity
    _write_json(path, payload)
    identity = worker_identity_from_json(path.read_text(encoding="utf-8"))
    _log_worker_event(
        project_root,
        kind="worker.identity.created",
        payload={"worker_id": worker_id, "hostname": hostname},
    )
    return identity


def read_worker_identity(project_root: Path, worker_id: str) -> Any:
    path = worker_identity_path(project_root, worker_id)
    if not path.exists():
        raise FileNotFoundError(path)
    return worker_identity_from_json(path.read_text(encoding="utf-8"))


def list_worker_identities(project_root: Path) -> list[Any]:
    base = codex_team_state_root(project_root) / "workers" / "identity"
    if not base.exists():
        return []
    identities: list[Any] = []
    for file in sorted(base.glob("*.json")):
        identities.append(worker_identity_from_json(file.read_text(encoding="utf-8")))
    return identities


def write_worker_heartbeat(
    project_root: Path,
    *,
    worker_id: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> Any:
    payload = worker_heartbeat_payload(
        worker_id=worker_id,
        status=status,
        details=details,
    )
    path = worker_heartbeat_path(project_root, worker_id)
    _write_json(path, payload)
    heartbeat = worker_heartbeat_from_json(path.read_text(encoding="utf-8"))
    _log_worker_event(
        project_root,
        kind="worker.heartbeat.updated",
        payload={"worker_id": worker_id, "status": status},
    )
    return heartbeat


def read_worker_heartbeat(project_root: Path, worker_id: str) -> Any:
    path = worker_heartbeat_path(project_root, worker_id)
    if not path.exists():
        raise FileNotFoundError(path)
    return worker_heartbeat_from_json(path.read_text(encoding="utf-8"))


def _list_worker_heartbeats(project_root: Path) -> Iterable[Any]:
    base = codex_team_state_root(project_root) / "workers" / "heartbeat"
    if not base.exists():
        return []
    records = []
    for file in sorted(base.glob("*.json")):
        records.append(worker_heartbeat_from_json(file.read_text(encoding="utf-8")))
    return records


def worker_status_snapshot(
    project_root: Path,
    *,
    snapshot_id: str,
    task_count: int = 0,
) -> MonitorSnapshot:
    heartbeats = list(_list_worker_heartbeats(project_root))
    breakdown = Counter(h.status for h in heartbeats)
    payload = monitor_snapshot_payload(
        snapshot_id=snapshot_id,
        task_count=task_count,
        worker_count=len(heartbeats),
        status_breakdown=dict(breakdown),
    )
    snapshot = monitor_snapshot_from_json(json.dumps(payload))
    _log_worker_event(
        project_root,
        kind="worker.snapshot",
        payload=payload,
    )
    return snapshot
