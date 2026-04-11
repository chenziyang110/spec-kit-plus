"""Tests for worktree planning and bootstrap instructions."""

from pathlib import Path

import pytest

from specify_cli.codex_team import tmux_backend, worktree_ops, worker_bootstrap


def test_worker_worktree_path_is_rooted_within_project(codex_team_project_root):
    expected = codex_team_project_root / ".specify" / "codex-team" / "worktrees" / "sess" / "worker"
    actual = worktree_ops.worker_worktree_path(codex_team_project_root, session_id="sess", worker_id="worker")
    assert actual == expected


def test_worker_worktree_path_rejects_escape(codex_team_project_root):
    with pytest.raises(ValueError):
        worktree_ops.worker_worktree_path(
            codex_team_project_root,
            session_id="..",
            worker_id="worker",
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
