"""Promote worker worktree outputs back into the leader workspace."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .worktree_ops import codex_team_worktrees_root


def workspace_has_uncommitted_changes(project_root: Path) -> bool:
    repo_probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if repo_probe.returncode != 0 or repo_probe.stdout.strip().lower() != "true":
        return False
    status_probe = subprocess.run(
        ["git", "status", "--short"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(status_probe.stdout.strip())


def collect_sync_back_candidates(project_root: Path, *, session_id: str) -> list[dict[str, object]]:
    session_root = codex_team_worktrees_root(project_root) / session_id
    if not session_root.is_dir():
        return []

    candidates: list[dict[str, object]] = []
    for worker_root in sorted(path for path in session_root.iterdir() if path.is_dir()):
        for source_path in sorted(path for path in worker_root.rglob("*") if path.is_file()):
            relative_path = source_path.relative_to(worker_root)
            if any(part in {".git", ".specify"} for part in relative_path.parts):
                continue
            target_path = project_root / relative_path
            candidates.append(
                {
                    "worker_id": worker_root.name,
                    "source_path": str(source_path),
                    "target_path": str(target_path),
                    "relative_path": relative_path.as_posix(),
                }
            )
    return candidates


def plan_sync_back(
    project_root: Path,
    *,
    session_id: str,
    allow_dirty: bool = False,
) -> dict[str, Any]:
    dirty = workspace_has_uncommitted_changes(project_root)
    candidates = collect_sync_back_candidates(project_root, session_id=session_id)
    return {
        "session_id": session_id,
        "dirty_workspace": dirty,
        "allow_dirty": allow_dirty,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def apply_sync_back(
    project_root: Path,
    *,
    session_id: str,
    allow_dirty: bool = False,
) -> dict[str, Any]:
    plan = plan_sync_back(project_root, session_id=session_id, allow_dirty=allow_dirty)
    if plan["dirty_workspace"] and not allow_dirty:
        raise RuntimeError("Main workspace is dirty; rerun sync-back with --allow-dirty to override.")

    copied: list[dict[str, object]] = []
    for candidate in plan["candidates"]:
        source_path = Path(str(candidate["source_path"]))
        target_path = Path(str(candidate["target_path"]))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied.append(candidate)

    return {
        **plan,
        "copied_count": len(copied),
        "copied": copied,
    }
