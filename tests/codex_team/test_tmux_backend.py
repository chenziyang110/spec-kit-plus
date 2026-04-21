"""Tests for the tmux/worktree backend planning helpers."""

from pathlib import Path

import pytest

from specify_cli.codex_team import tmux_backend
from specify_cli.orchestration.backends.base import BackendDescriptor


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


def test_detect_team_runtime_backend_uses_orchestration_registry(monkeypatch):
    called = {"value": False}

    def _detect_backends():
        called["value"] = True
        return {
            "tmux": BackendDescriptor(
                name="tmux",
                available=True,
                interactive=True,
                binary="/usr/bin/tmux",
                reason="tmux detected on PATH",
            ),
            "psmux": BackendDescriptor(
                name="psmux",
                available=False,
                interactive=True,
                binary=None,
                reason="psmux not found on PATH",
            ),
            "process": BackendDescriptor(
                name="process",
                available=True,
                interactive=False,
                binary=None,
                reason="portable subprocess backend",
            ),
        }

    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.detect_available_backends",
        _detect_backends,
        raising=False,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)

    backend = tmux_backend.detect_team_runtime_backend()

    assert called["value"] is True
    assert backend.available is True
    assert backend.name == "tmux"


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
