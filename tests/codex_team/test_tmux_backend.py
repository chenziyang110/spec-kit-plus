"""Tests for the tmux/worktree backend planning helpers."""

from pathlib import Path

import pytest

from specify_cli.codex_team import tmux_backend


def _stub_detect(backend_name: str):
    return {"available": True, "name": backend_name, "binary": f"/fake/{backend_name}"}


def test_detect_team_runtime_backend_prefers_tmux(monkeypatch):
    monkeypatch.setattr(
        "specify_cli.codex_team.tmux_backend.runtime_bridge.detect_team_runtime_backend",
        lambda: _stub_detect("tmux"),
    )

    backend = tmux_backend.detect_team_runtime_backend()

    assert backend.available
    assert backend.name == "tmux"
    assert "tmux" in backend.install_instructions.lower()


def test_detect_team_runtime_backend_falls_back_to_psmux_on_windows(monkeypatch):
    monkeypatch.setattr(
        "specify_cli.codex_team.tmux_backend.runtime_bridge.detect_team_runtime_backend",
        lambda: _stub_detect("psmux"),
    )

    backend = tmux_backend.detect_team_runtime_backend()

    assert backend.available
    assert backend.name == "psmux"
    assert "psmux" in backend.install_instructions.lower()


def test_plan_worker_launch_requires_backend_available():
    backend = tmux_backend.TeamRuntimeBackend(
        name=None,
        binary=None,
        available=False,
        description="missing",
        install_instructions=None,
    )

    with pytest.raises(tmux_backend.RuntimeEnvironmentError):
        tmux_backend.plan_worker_launch(
            backend,
            session_id="sess",
            worker_id="worker-1",
            launch_command="echo hi",
            worktree=Path("/tmp/worktree"),
        )


def test_plan_worker_launch_builds_spec_with_env(tmp_path):
    backend = tmux_backend.TeamRuntimeBackend(
        name="tmux",
        binary="/usr/bin/tmux",
        available=True,
        description="tmux backend",
        install_instructions="install tmux",
    )

    worktree = tmp_path / "worktrees" / "sess" / "worker-1"
    pane_spec = tmux_backend.plan_worker_launch(
        backend,
        session_id="sess",
        worker_id="worker-1",
        launch_command="python -m specify_cli team",
        worktree=worktree,
        env={"EXTRA": "value"},
    )

    assert pane_spec.session == "codex-team-sess"
    assert pane_spec.pane_title == "worker-worker-1"
    assert pane_spec.worktree == str(worktree)
    assert pane_spec.env["WORKER_ID"] == "worker-1"
    assert pane_spec.env["SESSION_ID"] == "sess"
    assert pane_spec.env["WORKTREE_PATH"] == str(worktree)
    assert pane_spec.env["EXTRA"] == "value"
