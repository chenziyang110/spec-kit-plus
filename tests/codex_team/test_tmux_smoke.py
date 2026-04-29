import json

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team.runtime_bridge import RuntimeEnvironmentError
from specify_cli.codex_team.state_paths import dispatch_record_path, runtime_session_path


def test_team_command_bootstrap_dispatch_fail_cleanup(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    specify_dir = codex_team_project_root / ".specify"
    specify_dir.mkdir(exist_ok=True)
    (specify_dir / "integration.json").write_text(
        json.dumps({"integration": "codex"}, indent=2),
        encoding="utf-8",
    )

    runner = CliRunner()

    with monkeypatch.context() as m:
        m.chdir(codex_team_project_root)
        result = runner.invoke(app, ["sp-teams", "--bootstrap", "--session-id", "smoke"], catch_exceptions=False)
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            app,
            ["sp-teams", "--dispatch", "req-smoke", "--worker", "worker-smoke", "--session-id", "smoke"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            app,
            ["sp-teams", "--fail", "--dispatch", "req-smoke", "--reason", "boom", "--session-id", "smoke"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(app, ["sp-teams", "--cleanup", "--session-id", "smoke"], catch_exceptions=False)
        assert result.exit_code == 0, result.output

    session_payload = json.loads(runtime_session_path(codex_team_project_root, "smoke").read_text(encoding="utf-8"))
    dispatch_payload = json.loads(dispatch_record_path(codex_team_project_root, "req-smoke").read_text(encoding="utf-8"))

    assert dispatch_payload["status"] == "failed"
    assert session_payload["status"] == "cleaned"


def test_team_command_status_guides_native_windows_users_to_psmux(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})
    monkeypatch.setattr(
        "specify_cli.ensure_tmux_available",
        lambda: (_ for _ in ()).throw(
            RuntimeEnvironmentError(
                "A tmux-compatible team runtime backend is required on native Windows. Install psmux with: winget install psmux"
            )
        ),
    )

    specify_dir = codex_team_project_root / ".specify"
    specify_dir.mkdir(exist_ok=True)
    (specify_dir / "integration.json").write_text(
        json.dumps({"integration": "codex"}, indent=2),
        encoding="utf-8",
    )

    runner = CliRunner()

    with monkeypatch.context() as m:
        m.chdir(codex_team_project_root)
        result = runner.invoke(app, ["sp-teams"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "psmux" in result.output


def test_team_command_dispatch_blocks_when_project_map_is_dirty(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    specify_dir = codex_team_project_root / ".specify"
    specify_dir.mkdir(exist_ok=True)
    (specify_dir / "integration.json").write_text(
        json.dumps({"integration": "codex"}, indent=2),
        encoding="utf-8",
    )

    status_path = specify_dir / "project-map" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["freshness"] = "stale"
    payload["dirty"] = True
    payload["dirty_reasons"] = ["shared_surface_changed"]
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()

    with monkeypatch.context() as m:
        m.chdir(codex_team_project_root)
        result = runner.invoke(app, ["sp-teams", "--bootstrap", "--session-id", "smoke"], catch_exceptions=False)
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            app,
            ["sp-teams", "--dispatch", "req-smoke", "--worker", "worker-smoke", "--session-id", "smoke"],
            catch_exceptions=False,
        )

    assert result.exit_code != 0
    assert "Project-map freshness is stale" in result.output
    assert "map-codebase" in result.output
