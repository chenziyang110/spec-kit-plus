"""Tests for worktree planning and bootstrap instructions."""

import subprocess
from pathlib import Path

import pytest

from specify_cli.codex_team import tmux_backend, worktree_ops, worker_bootstrap
from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.worktree import materialize_lane_worktree


def test_worker_worktree_path_is_rooted_within_project(codex_team_project_root):
    expected = codex_team_project_root / ".specify" / "teams" / "worktrees" / "sess" / "worker"
    actual = worktree_ops.worker_worktree_path(codex_team_project_root, session_id="sess", worker_id="worker")
    assert actual == expected


def test_lane_worktree_path_is_rooted_within_project(codex_team_project_root):
    expected = codex_team_project_root / ".specify" / "lanes" / "worktrees" / "lane-001"
    actual = worktree_ops.lane_worktree_path(codex_team_project_root, lane_id="lane-001")
    assert actual == expected


def test_worker_worktree_path_rejects_escape(codex_team_project_root):
    with pytest.raises(ValueError):
        worktree_ops.worker_worktree_path(
            codex_team_project_root,
            session_id="..",
            worker_id="worker",
        )


def test_lane_worktree_path_rejects_escape(codex_team_project_root):
    with pytest.raises(ValueError):
        worktree_ops.lane_worktree_path(
            codex_team_project_root,
            lane_id="../escape",
        )


def test_build_worker_bootstrap_includes_role_overlays(tmp_path):
    backend = tmux_backend.TeamRuntimeBackend(
        name="tmux",
        binary="/usr/bin/tmux",
        available=True,
        description="tmux backend",
        install_instructions="install tmux",
    )
    pane_spec = tmux_backend.plan_worker_launch(
        backend,
        session_id="sess",
        worker_id="worker-1",
        launch_command="python -m specify_cli team --role code",
        worktree=tmp_path / "wt",
        env={},
    )

    payload = worker_bootstrap.build_worker_bootstrap_payload(
        pane_spec,
        role="code-review",
        instructions_prefix="bootstrap:",
    )

    overlay = payload.role_overlay
    assert overlay["role"] == "code-review"
    assert overlay["session_id"] == pane_spec.session
    assert overlay["worker_id"] == pane_spec.worker_id
    assert overlay["worktree_path"] == pane_spec.worktree
    assert payload.instructions.startswith("bootstrap:")
    assert pane_spec.launch_command in payload.instructions


def test_materialize_lane_worktree_skips_without_git_head(tmp_path):
    project = tmp_path / "lane-no-head"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        last_command="specify",
    )

    result = materialize_lane_worktree(project, lane)

    assert result.status == "skipped"
    assert "HEAD" in result.reason


def test_materialize_lane_worktree_creates_worktree_when_head_exists(tmp_path):
    project = tmp_path / "lane-head"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=project, check=True)

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        last_command="specify",
    )

    result = materialize_lane_worktree(project, lane)

    assert result.status == "created"
    assert result.checkout_mode == "branch"
    assert (project / ".specify" / "lanes" / "worktrees" / "lane-001").exists()
