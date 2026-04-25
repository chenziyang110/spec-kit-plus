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
    assert "executor available" in result.output
    assert "git HEAD available" in result.output
    assert "worktree-ready" in result.output
    assert "native build shell" in result.output.lower()
    assert "baseline build" in result.output.lower()


def test_team_status_subcommand_surfaces_missing_prerequisite_next_steps(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result = _invoke_in_project(project, ["team", "status"])

    assert result.exit_code == 0, result.output
    assert "Next steps" in result.output
    assert "initial commit" in result.output.lower()


def test_team_doctor_subcommand_shows_diagnostics(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result = _invoke_in_project(project, ["team", "doctor"])

    assert result.exit_code == 0, result.output
    lowered = result.output.lower()
    assert "executor available" in lowered
    assert "baseline build" in lowered
    assert "native build shell" in lowered
    assert "latest transcript" in lowered
    assert "failed dispatches" in lowered


def test_team_live_probe_subcommand_shows_probe_result(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    runtime_cli = project / "fake-runtime-cli.py"
    runtime_cli.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "payload = json.loads(sys.stdin.read())",
                "state_root = Path(os.environ['OMX_TEAM_STATE_ROOT'])",
                "tasks_dir = state_root / 'team' / payload['teamName'] / 'tasks'",
                "tasks_dir.mkdir(parents=True, exist_ok=True)",
                "task = payload['tasks'][0]",
                "start_marker = 'BEGIN_WORKER_TASK_RESULT_JSON'",
                "end_marker = 'END_WORKER_TASK_RESULT_JSON'",
                "start = task['description'].index(start_marker) + len(start_marker)",
                "end = task['description'].index(end_marker)",
                "result_payload = json.loads(task['description'][start:end].strip())",
                "(tasks_dir / 'task-1.json').write_text(json.dumps({'id': '1', 'subject': task['subject'], 'description': task['description'], 'status': 'completed', 'result': start_marker + '\\n' + json.dumps(result_payload, ensure_ascii=False, indent=2) + '\\n' + end_marker, 'created_at': '2026-04-26T00:00:00Z'}, ensure_ascii=False, indent=2), encoding='utf-8')",
                "(tasks_dir.parent / 'phase.json').write_text(json.dumps({'current_phase': 'complete', 'updated_at': '2026-04-26T00:00:00Z'}, ensure_ascii=False, indent=2), encoding='utf-8')",
                "(tasks_dir.parent / 'monitor-snapshot.json').write_text(json.dumps({'taskStatusById': {'1': 'completed'}, 'workerAliveByName': {'worker-1': True}, 'workerStateByName': {'worker-1': 'done'}, 'workerTurnCountByName': {'worker-1': 1}, 'workerTaskIdByName': {'worker-1': '1'}, 'mailboxNotifiedByMessageId': {}, 'completedEventTaskIds': {'1': True}}, ensure_ascii=False, indent=2), encoding='utf-8')",
                "json.dump({'status': 'completed', 'teamName': payload['teamName'], 'taskResults': [], 'duration': 0, 'workerCount': len(payload['tasks'])}, sys.stdout)",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["SPECIFY_CODEX_TEAM_RUNTIME_CLI"] = str(runtime_cli)
    result = _invoke_in_project(project, ["team", "live-probe"], env=env)

    assert result.exit_code == 0, result.output
    lowered = result.output.lower()
    assert "probe status: passed" in lowered
    assert "transcript path:" in lowered


def test_team_sync_back_subcommand_shows_candidate_files_in_dry_run(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    worker_file = project / ".specify" / "codex-team" / "worktrees" / "default" / "worker-a" / "src" / "app.py"
    worker_file.parent.mkdir(parents=True, exist_ok=True)
    worker_file.write_text("print('candidate')\n", encoding="utf-8")

    result = _invoke_in_project(project, ["team", "sync-back", "--dry-run"])

    assert result.exit_code == 0, result.output
    lowered = result.output.lower()
    assert "sync-back candidates" in lowered
    assert "src/app.py" in lowered


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
