from pathlib import Path


def test_runtime_status_reports_agent_teams_executor_when_runtime_cli_exists(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.runtime_bridge import codex_team_runtime_status

    runtime_cli = codex_team_project_root / ".specify" / "extensions" / "agent-teams" / "engine" / "dist" / "team" / "runtime-cli.js"
    runtime_cli.parent.mkdir(parents=True, exist_ok=True)
    runtime_cli.write_text("// fake runtime cli\n", encoding="utf-8")

    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name in {"tmux", "node"} else None,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["executor_available"] is True
    assert status["executor_mode"] == "agent-teams-runtime"
    assert str(runtime_cli) == status["executor_runtime_cli_path"]
