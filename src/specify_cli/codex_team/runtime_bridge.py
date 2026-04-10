"""Environment validation and runtime status helpers for Codex team."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .manifests import (
    DispatchRecord,
    RuntimeSession,
    dispatch_record_from_json,
    runtime_session_from_json,
    runtime_state_payload,
)
from .state_paths import codex_team_state_root, dispatch_record_path, runtime_session_path


class RuntimeEnvironmentError(RuntimeError):
    """Raised when the runtime cannot be used in the current environment."""


def ensure_tmux_available() -> None:
    """Fail visibly when tmux is unavailable."""
    if shutil.which("tmux") is None:
        raise RuntimeEnvironmentError(
            "tmux is required for the Codex team runtime in first-release environments."
        )


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _load_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    path = runtime_session_path(project_root, session_id)
    return runtime_session_from_json(path.read_text(encoding="utf-8"))


def _load_dispatch_record(project_root: Path, request_id: str) -> DispatchRecord:
    path = dispatch_record_path(project_root, request_id)
    return dispatch_record_from_json(path.read_text(encoding="utf-8"))


def bootstrap_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    """Validate the environment and persist a ready runtime session."""
    ensure_tmux_available()
    session = RuntimeSession(
        session_id=session_id,
        status="ready",
        environment_check="pass",
    )
    _write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    return session


def dispatch_runtime_task(
    project_root: Path,
    *,
    session_id: str,
    request_id: str,
    target_worker: str,
) -> DispatchRecord:
    """Persist a dispatched task and advance the session to running."""
    session = _load_runtime_session(project_root, session_id)
    session.status = "running"
    record = DispatchRecord(
        request_id=request_id,
        target_worker=target_worker,
        status="dispatched",
    )
    _write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    _write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return record


def mark_runtime_failure(
    project_root: Path,
    *,
    session_id: str,
    request_id: str,
    reason: str,
) -> tuple[RuntimeSession, DispatchRecord]:
    """Persist a visible failure state for the session and dispatch."""
    session = _load_runtime_session(project_root, session_id)
    record = _load_dispatch_record(project_root, request_id)
    session.status = "failed"
    session.finished_at = record.updated_at
    record.status = "failed"
    record.reason = reason
    _write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    _write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return session, record


def cleanup_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    """Persist a cleaned terminal state for the runtime session."""
    session = _load_runtime_session(project_root, session_id)
    session.status = "cleaned"
    session.finished_at = session.finished_at or session.created_at
    _write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    return session


def codex_team_runtime_status(project_root: Path, *, integration_key: str | None) -> dict[str, object]:
    """Return a compact runtime status payload for help text and tests."""
    available = integration_key == "codex"
    tmux_available = shutil.which("tmux") is not None
    state_root = codex_team_state_root(project_root)
    session = RuntimeSession(
        session_id="preview",
        status="ready" if available and tmux_available else "created",
        environment_check="pass" if tmux_available else "fail",
    )
    dispatch = DispatchRecord(
        request_id="preview-request",
        target_worker="preview-worker",
        status="pending",
    )
    return {
        "available": available,
        "tmux_available": tmux_available,
        "state_root": state_root,
        "runtime_state": runtime_state_payload(session, [dispatch]),
    }
