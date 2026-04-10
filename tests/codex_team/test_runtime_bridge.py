from pathlib import Path

import pytest

from specify_cli.codex_team.runtime_bridge import (
    RuntimeEnvironmentError,
    codex_team_runtime_status,
    ensure_tmux_available,
)


def test_ensure_tmux_available_raises_when_tmux_missing(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    assert "tmux is required" in str(excinfo.value)


def test_runtime_status_reports_codex_availability(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["available"] is True
    assert status["tmux_available"] is True
    assert status["runtime_state"]["session"]["environment_check"] == "pass"


def test_runtime_status_reports_non_codex_as_unavailable(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="claude")

    assert status["available"] is False
    assert status["runtime_state"]["session"]["status"] == "created"
