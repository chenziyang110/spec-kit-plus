"""Worktree naming and safety helpers for Codex team workers."""

from __future__ import annotations

import os
from pathlib import Path

from specify_cli.lanes.worktree import lane_worktree_path

WORKTREE_RELATIVE_ROOT = Path(".specify") / "teams" / "worktrees"


def codex_team_worktrees_root(project_root: Path) -> Path:
    return project_root / WORKTREE_RELATIVE_ROOT


def _ensure_within_root(project_root: Path, candidate: Path) -> Path:
    root = codex_team_worktrees_root(project_root).resolve(strict=False)
    resolved = candidate.resolve(strict=False)

    if os.path.commonpath([str(root), str(resolved)]) != str(root):
        raise ValueError(f"Worktree path {candidate} escapes {root}")

    return candidate


def worker_worktree_path(project_root: Path, *, session_id: str, worker_id: str) -> Path:
    candidate = codex_team_worktrees_root(project_root) / session_id / worker_id
    return _ensure_within_root(project_root, candidate)


__all__ = [
    "WORKTREE_RELATIVE_ROOT",
    "codex_team_worktrees_root",
    "lane_worktree_path",
    "worker_worktree_path",
]
