import json

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team.state_paths import dispatch_record_path, runtime_session_path


def test_team_command_bootstrap_dispatch_fail_cleanup(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    specify_dir = codex_team_project_root / ".specify"
    specify_dir.mkdir()
    (specify_dir / "integration.json").write_text(
        json.dumps({"integration": "codex"}, indent=2),
        encoding="utf-8",
    )

    runner = CliRunner()

    with monkeypatch.context() as m:
        m.chdir(codex_team_project_root)
        result = runner.invoke(app, ["team", "--bootstrap", "--session-id", "smoke"], catch_exceptions=False)
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            app,
            ["team", "--dispatch", "req-smoke", "--worker", "worker-smoke", "--session-id", "smoke"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            app,
            ["team", "--fail", "--dispatch", "req-smoke", "--reason", "boom", "--session-id", "smoke"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(app, ["team", "--cleanup", "--session-id", "smoke"], catch_exceptions=False)
        assert result.exit_code == 0, result.output

    session_payload = json.loads(runtime_session_path(codex_team_project_root, "smoke").read_text(encoding="utf-8"))
    dispatch_payload = json.loads(dispatch_record_path(codex_team_project_root, "req-smoke").read_text(encoding="utf-8"))

    assert dispatch_payload["status"] == "failed"
    assert session_payload["status"] == "cleaned"
