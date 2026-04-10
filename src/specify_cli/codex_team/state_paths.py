"""Filesystem locations for Codex team runtime state."""

from __future__ import annotations

from pathlib import Path


def codex_team_state_root(project_root: Path) -> Path:
    """Return the root directory for Codex team runtime state."""
    return project_root / ".specify" / "codex-team" / "state"


def runtime_session_path(project_root: Path, session_id: str) -> Path:
    """Return the persisted runtime session path."""
    return codex_team_state_root(project_root) / f"session-{session_id}.json"


def dispatch_record_path(project_root: Path, request_id: str) -> Path:
    """Return the persisted dispatch record path."""
    return codex_team_state_root(project_root) / f"dispatch-{request_id}.json"
