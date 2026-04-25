"""Contract tests for the Codex team CLI surface."""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team import task_ops
from specify_cli.codex_team.state_paths import runtime_session_path


def _create_codex_project(tmp_path: Path) -> Path:
    project = tmp_path / "codex-team-clis"
    project.mkdir()
    spec_root = project / ".specify"
    spec_root.mkdir()
    integration_json = spec_root / "integration.json"
    integration_json.write_text(json.dumps({"integration": "codex"}), encoding="utf-8")
    (spec_root / "codex-team").mkdir(parents=True, exist_ok=True)
    return project


def _fake_tmux_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "fake-tmux-bin"
    bin_dir.mkdir()
    script_name = "tmux.exe" if os.name == "nt" else "tmux"
    (bin_dir / script_name).write_text("", encoding="utf-8")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def _invoke_in_project(project: Path, args: list[str], env: dict[str, str] | None = None):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args, env=env or os.environ)
    finally:
        os.chdir(old_cwd)
    return result


def test_team_status_subcommand_shows_runtime_info(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result = _invoke_in_project(project, ["team", "status"])
    assert result.exit_code == 0, result.output
    assert "Codex team runtime" in result.output
    assert "runtime backend" in result.output
    assert "agent-teams extension installed" in result.output
    assert "git HEAD available" in result.output
    assert "worktree-ready" in result.output


def test_team_status_subcommand_surfaces_missing_prerequisite_next_steps(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result = _invoke_in_project(project, ["team", "status"])

    assert result.exit_code == 0, result.output
    assert "Next steps" in result.output
    assert "specify extension add agent-teams" in result.output
    assert "initial commit" in result.output.lower()


def test_team_await_subcommand_reports_monitor_snapshot(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    task_ops.create_task(project, task_id="await-test", summary="Await me")
    result = _invoke_in_project(project, ["team", "await"])
    assert result.exit_code == 0, result.output
    assert "monitor snapshot" in result.output.lower()
    assert "task count" in result.output.lower()


def test_team_resume_subcommand_bootstraps_session(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)
    result = _invoke_in_project(project, ["team", "resume"], env=env)
    assert result.exit_code == 0, result.output
    assert "Bootstrapped session" in result.output
    session_file = runtime_session_path(project, "default")
    assert session_file.exists()


def test_team_shutdown_subcommand_requests_and_acknowledges(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)
    first = _invoke_in_project(project, ["team", "resume"], env=env)
    assert first.exit_code == 0, first.output

    request = _invoke_in_project(
        project,
        ["team", "shutdown", "--reason", "testing", "--requested-by", "tester"],
    )
    assert request.exit_code == 0, request.output
    assert "shutdown requested" in request.output.lower()

    ack = _invoke_in_project(
        project,
        ["team", "shutdown", "--acknowledge", "--acknowledged-by", "lead"],
    )
    assert ack.exit_code == 0, ack.output
    assert "shutdown acknowledged" in ack.output.lower()


def test_team_cleanup_subcommand_requires_terminal_session(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)
    ready = _invoke_in_project(project, ["team", "resume"], env=env)
    assert ready.exit_code == 0, ready.output

    session_file = runtime_session_path(project, "default")
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    payload["finished_at"] = payload.get("updated_at", "")
    session_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = _invoke_in_project(project, ["team", "cleanup"])
    assert result.exit_code == 0, result.output
    assert "cleaned session" in result.output.lower()
