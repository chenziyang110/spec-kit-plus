from pathlib import Path

import pytest

from specify_cli.codex_team.runtime_bridge import (
    RuntimeEnvironmentError,
    codex_team_runtime_status,
    detect_team_runtime_backend,
    ensure_tmux_available,
)


def test_ensure_tmux_available_raises_when_tmux_missing(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    assert "tmux is required" in str(excinfo.value)


def test_detect_runtime_backend_uses_psmux_on_native_windows(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\psmux.exe" if name == "psmux" else None,
    )

    backend = detect_team_runtime_backend()

    assert backend["available"] is True
    assert backend["name"] == "psmux"


def test_ensure_tmux_available_mentions_psmux_on_native_windows(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    message = str(excinfo.value)
    assert "psmux" in message
    assert "winget install psmux" in message


def test_runtime_status_reports_codex_availability(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["available"] is True
    assert status["runtime_backend"] == "tmux"
    assert status["runtime_backend_available"] is True
    assert status["runtime_state"]["session"]["environment_check"] == "pass"


def test_runtime_status_reports_psmux_backend_on_native_windows(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\psmux.exe" if name == "psmux" else None,
    )

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["available"] is True
    assert status["runtime_backend"] == "psmux"
    assert status["runtime_backend_available"] is True
    assert status["runtime_state"]["session"]["environment_check"] == "pass"


def test_runtime_status_reports_non_codex_as_unavailable(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="claude")

    assert status["available"] is False
    assert status["runtime_state"]["session"]["status"] == "created"
