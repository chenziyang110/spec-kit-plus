"""Codex team session lifecycle helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.codex_team.manifests import (
    RuntimeSession,
    runtime_session_from_json,
    runtime_state_payload,
)
from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session
from specify_cli.codex_team.runtime_state import (
    MonitorSnapshot,
    team_config_payload,
)
from specify_cli.codex_team.state_paths import (
    monitor_snapshot_path,
    phase_path,
    runtime_session_path,
    shutdown_path,
    team_config_path,
)
from specify_cli.codex_team.task_ops import list_tasks
from specify_cli.codex_team.worker_ops import (
    bootstrap_worker_identity,
    write_worker_heartbeat,
    worker_status_snapshot,
)


class SessionLifecycleError(RuntimeError):
    """Raised when a requested session transition is invalid."""


TERMINAL_SESSION_STATUSES = {"failed", "shutdown_acknowledged", "cleaned"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _load_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    path = runtime_session_path(project_root, session_id)
    if not path.exists():
        raise SessionLifecycleError(f"session {session_id} not found")
    return runtime_session_from_json(path.read_text(encoding="utf-8"))


def _persist_runtime_session(project_root: Path, session: RuntimeSession) -> Path:
    payload = runtime_state_payload(session)["session"]
    return _write_json(runtime_session_path(project_root, session.session_id), payload)


def _write_phase(project_root: Path, phase: str, session: RuntimeSession) -> Path:
    payload = {
        "phase": phase,
        "session_id": session.session_id,
        "status": session.status,
        "created_at": _utc_now(),
    }
    return _write_json(phase_path(project_root, phase), payload)


def bootstrap_session(project_root: Path, *, session_id: str) -> RuntimeSession:
    path = runtime_session_path(project_root, session_id)
    if path.exists():
        existing = runtime_session_from_json(path.read_text(encoding="utf-8"))
        if existing.status not in TERMINAL_SESSION_STATUSES:
            raise SessionLifecycleError(f"session {session_id} already active")

    session = bootstrap_runtime_session(project_root, session_id)
    _write_json(team_config_path(project_root), team_config_payload(team_name=session.session_id, session_id=session.session_id))
    _write_phase(project_root, "bootstrap", session)
    bootstrap_worker_identity(project_root, worker_id="leader", hostname="leader")
    write_worker_heartbeat(project_root, worker_id="leader", status="ready")
    monitor_summary(project_root, session_id=session.session_id)
    return session


def monitor_summary(project_root: Path, *, session_id: str) -> MonitorSnapshot:
    tasks = list_tasks(project_root)
    snapshot = worker_status_snapshot(
        project_root,
        snapshot_id=f"monitor-{session_id}",
        task_count=len(tasks),
    )
    payload = asdict(snapshot)
    _write_json(
        monitor_snapshot_path(project_root, snapshot.snapshot_id),
        payload,
    )
    return snapshot


def request_shutdown(
    project_root: Path,
    *,
    session_id: str,
    reason: str,
    requested_by: str,
) -> dict[str, Any]:
    session = _load_runtime_session(project_root, session_id)
    payload: dict[str, Any] = {
        "session_id": session_id,
        "status": "requested",
        "reason": reason,
        "requested_by": requested_by,
        "created_at": _utc_now(),
    }
    _write_json(shutdown_path(project_root, session_id), payload)
    session.status = "shutdown_requested"
    _persist_runtime_session(project_root, session)
    return payload


def acknowledge_shutdown(
    project_root: Path,
    *,
    session_id: str,
    acknowledged_by: str,
) -> dict[str, Any]:
    path = shutdown_path(project_root, session_id)
    if not path.exists():
        raise SessionLifecycleError("shutdown request not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "requested":
        raise SessionLifecycleError("shutdown already acknowledged")
    payload["status"] = "acknowledged"
    payload["acknowledged_by"] = acknowledged_by
    payload["acknowledged_at"] = _utc_now()
    _write_json(path, payload)
    session = _load_runtime_session(project_root, session_id)
    session.status = "shutdown_acknowledged"
    session.finished_at = payload["acknowledged_at"]
    _persist_runtime_session(project_root, session)
    return payload


def cleanup_session(project_root: Path, *, session_id: str) -> RuntimeSession:
    session = _load_runtime_session(project_root, session_id)
    if session.status not in TERMINAL_SESSION_STATUSES:
        raise SessionLifecycleError("session is not in a terminal state")
    session.status = "cleaned"
    if not session.finished_at:
        session.finished_at = _utc_now()
    _persist_runtime_session(project_root, session)
    _write_phase(project_root, "cleanup", session)
    monitor_summary(project_root, session_id=session.session_id)
    return session
