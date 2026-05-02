"""Lane worktree path helpers."""

from __future__ import annotations

import os
from pathlib import Path


LANE_WORKTREE_RELATIVE_ROOT = Path(".specify") / "lanes" / "worktrees"


def lane_worktrees_root(project_root: Path) -> Path:
    """Return the lane worktree root under the project."""

    return project_root / LANE_WORKTREE_RELATIVE_ROOT


def _ensure_within_lane_root(project_root: Path, candidate: Path) -> Path:
    root = lane_worktrees_root(project_root).resolve(strict=False)
    resolved = candidate.resolve(strict=False)
    if os.path.commonpath([str(root), str(resolved)]) != str(root):
        raise ValueError(f"Lane worktree path {candidate} escapes {root}")
    return candidate


def lane_worktree_path(project_root: Path, *, lane_id: str) -> Path:
    """Return the canonical worktree path for one lane."""

    return _ensure_within_lane_root(project_root, lane_worktrees_root(project_root) / lane_id)
