"""Filesystem and JSON persistence helpers for orchestration state."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


def orchestration_root(project_root: Path) -> Path:
    """Return the root directory for generic orchestration state."""
    return project_root / ".specify" / "orchestration"


def session_path(project_root: Path, session_id: str) -> Path:
    """Return the canonical session record path."""
    return orchestration_root(project_root) / "sessions" / f"{session_id}.json"


def batch_path(project_root: Path, batch_id: str) -> Path:
    """Return the canonical batch record path."""
    return orchestration_root(project_root) / "batches" / f"{batch_id}.json"


def lane_path(project_root: Path, lane_id: str) -> Path:
    """Return the canonical lane record path."""
    return orchestration_root(project_root) / "lanes" / f"{lane_id}.json"


def task_path(project_root: Path, task_id: str) -> Path:
    """Return the canonical task record path."""
    return orchestration_root(project_root) / "tasks" / f"{task_id}.json"


def milestone_state_path(project_root: Path, phase_number: str) -> Path:
    """Return the canonical milestone phase-state record path."""
    return orchestration_root(project_root) / "milestones" / f"phase-{phase_number}.json"


def decision_path(project_root: Path, decision_id: str) -> Path:
    """Return the canonical milestone decision record path."""
    return orchestration_root(project_root) / "decisions" / f"{decision_id}.json"


def event_log_path(project_root: Path, session_id: str | None = None) -> Path:
    """Return the append-only orchestration event log path."""
    suffix = session_id or "default"
    return orchestration_root(project_root) / "events" / f"events-{suffix}.log"


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    """Write JSON payload to path using UTF-8 encoding and a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(json.dumps(payload, indent=2) + "\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    return path


def read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON payload from path if present."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
