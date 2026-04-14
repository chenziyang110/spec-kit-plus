"""Environment validation and runtime status helpers for Codex team."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

from specify_cli.orchestration.backends.detect import detect_available_backends
from specify_cli.orchestration.state_store import write_json

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


def is_wsl() -> bool:
    """Return whether the current process is running inside WSL."""
    return bool(
        os.environ.get("WSL_INTEROP")
        or os.environ.get("WSL_DISTRO_NAME")
        or "microsoft" in platform.uname().release.lower()
    )


def is_msys_or_git_bash() -> bool:
    """Return whether the shell is an MSYS/Git Bash environment on Windows."""
    return bool(os.environ.get("MSYSTEM"))


def is_native_windows() -> bool:
    """Return whether the current process is running on native Windows."""
    return sys.platform == "win32" and not is_wsl() and not is_msys_or_git_bash()


def detect_team_runtime_backend() -> dict[str, object]:
    """Detect the available runtime backend for team-mode coordination."""
    backend_descriptors = detect_available_backends()

    tmux = backend_descriptors.get("tmux")
    if tmux and tmux.available:
        return {"available": True, "name": tmux.name, "binary": tmux.binary}

    if is_native_windows():
        psmux = backend_descriptors.get("psmux")
        if psmux and psmux.available:
            return {"available": True, "name": psmux.name, "binary": psmux.binary}

    return {"available": False, "name": None, "binary": None}


def ensure_tmux_available() -> None:
    """Fail visibly when no supported team runtime backend is available."""
    backend = detect_team_runtime_backend()
    if backend["available"]:
        return

    if is_native_windows():
        raise RuntimeEnvironmentError(
            "A tmux-compatible team runtime backend is required on native Windows. "
            "Install psmux with: winget install psmux"
        )

    raise RuntimeEnvironmentError(
        "tmux is required for the Codex team runtime in first-release environments."
    )


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
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
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
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return record


def mark_runtime_failure(
    project_root: Path,
    *,
    session_id: str,
    request_id: str,
    reason: str,
    failure_class: str = "critical",
    blocker_id: str = "",
    retry_count: int = 0,
    retry_budget: int = 0,
) -> tuple[RuntimeSession, DispatchRecord]:
    """Persist a visible failure state for the session and dispatch."""
    session = _load_runtime_session(project_root, session_id)
    record = _load_dispatch_record(project_root, request_id)
    record.failure_class = failure_class
    record.retry_count = retry_count
    record.retry_budget = retry_budget

    retryable = (
        failure_class == "transient"
        and retry_budget > 0
        and retry_count < retry_budget
    )

    if retryable:
        session.status = "retry_pending"
        record.status = "retry_pending"
    else:
        session.status = "failed"
        session.blocker_id = blocker_id
        session.finished_at = record.updated_at
        record.status = "failed"
    record.reason = reason
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return session, record


def cleanup_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    """Persist a cleaned terminal state for the runtime session."""
    session = _load_runtime_session(project_root, session_id)
    session.status = "cleaned"
    session.finished_at = session.finished_at or session.created_at
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    return session


def codex_team_runtime_status(project_root: Path, *, integration_key: str | None) -> dict[str, object]:
    """Return a compact runtime status payload for help text and tests."""
    available = integration_key == "codex"
    backend = detect_team_runtime_backend()
    state_root = codex_team_state_root(project_root)
    session = RuntimeSession(
        session_id="preview",
        status="ready" if available and backend["available"] else "created",
        environment_check="pass" if backend["available"] else "fail",
    )
    dispatch = DispatchRecord(
        request_id="preview-request",
        target_worker="preview-worker",
        status="pending",
    )
    return {
        "available": available,
        "runtime_backend_available": backend["available"],
        "runtime_backend": backend["name"],
        "tmux_available": backend["name"] == "tmux",
        "native_windows": is_native_windows(),
        "state_root": state_root,
        "runtime_state": runtime_state_payload(session, [dispatch]),
        "runtime_state_summary": (
            "Runtime state surfaces worker outcomes, join points, retry-pending work, and blockers."
        ),
    }
