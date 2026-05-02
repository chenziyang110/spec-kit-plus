"""Lane worktree path helpers."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .models import LaneRecord

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


@dataclass(slots=True)
class LaneWorktreeResult:
    """Structured result of lane worktree materialization."""

    lane_id: str
    worktree_path: str
    status: Literal["created", "existing", "skipped", "blocked"]
    checkout_mode: Literal["branch", "detached", "none"]
    reason: str = ""


def _git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _is_git_repo(project_root: Path) -> bool:
    probe = _git(project_root, "rev-parse", "--is-inside-work-tree")
    return probe.returncode == 0 and probe.stdout.strip().lower() == "true"


def _has_head(project_root: Path) -> bool:
    probe = _git(project_root, "rev-parse", "--verify", "HEAD")
    return probe.returncode == 0


def _branch_exists(project_root: Path, branch_name: str) -> bool:
    probe = _git(project_root, "show-ref", "--verify", f"refs/heads/{branch_name}")
    return probe.returncode == 0


def _branch_checked_out_elsewhere(project_root: Path, branch_name: str) -> bool:
    probe = _git(project_root, "worktree", "list", "--porcelain")
    if probe.returncode != 0:
        return False
    needle = f"refs/heads/{branch_name}"
    return any(line.strip() == f"branch {needle}" for line in probe.stdout.splitlines())


def _worktree_checkout_mode(worktree_root: Path) -> Literal["branch", "detached", "none"]:
    probe = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=worktree_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if probe.returncode != 0:
        return "none"
    return "branch" if probe.stdout.strip() else "detached"


def materialize_lane_worktree(project_root: Path, lane: LaneRecord) -> LaneWorktreeResult:
    """Ensure a real git worktree exists for the lane when git state permits it."""

    target = lane_worktree_path(project_root, lane_id=lane.lane_id)

    if target.exists():
        return LaneWorktreeResult(
            lane_id=lane.lane_id,
            worktree_path=str(target),
            status="existing",
            checkout_mode=_worktree_checkout_mode(target),
        )

    if not _is_git_repo(project_root):
        return LaneWorktreeResult(
            lane_id=lane.lane_id,
            worktree_path=str(target),
            status="skipped",
            checkout_mode="none",
            reason="git repository not detected",
        )

    if not _has_head(project_root):
        return LaneWorktreeResult(
            lane_id=lane.lane_id,
            worktree_path=str(target),
            status="skipped",
            checkout_mode="none",
            reason="git HEAD is unavailable",
        )

    target.parent.mkdir(parents=True, exist_ok=True)

    if _branch_exists(project_root, lane.branch_name):
        if _branch_checked_out_elsewhere(project_root, lane.branch_name):
            cmd = ["git", "worktree", "add", "--detach", str(target), lane.branch_name]
            checkout_mode: Literal["branch", "detached", "none"] = "detached"
        else:
            cmd = ["git", "worktree", "add", str(target), lane.branch_name]
            checkout_mode = "branch"
    else:
        cmd = ["git", "worktree", "add", "-b", lane.branch_name, str(target), "HEAD"]
        checkout_mode = "branch"

    result = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return LaneWorktreeResult(
            lane_id=lane.lane_id,
            worktree_path=str(target),
            status="blocked",
            checkout_mode="none",
            reason=result.stderr.strip() or result.stdout.strip() or "git worktree add failed",
        )

    return LaneWorktreeResult(
        lane_id=lane.lane_id,
        worktree_path=str(target),
        status="created",
        checkout_mode=checkout_mode,
    )
