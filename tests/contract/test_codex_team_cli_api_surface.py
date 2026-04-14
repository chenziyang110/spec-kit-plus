"""Contract tests for the Codex team CLI API surface."""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team import task_ops


def _create_codex_project(tmp_path: Path) -> Path:
    project = tmp_path / "codex-team-api"
    project.mkdir()
    spec_root = project / ".specify"
    spec_root.mkdir()
    integration_json = spec_root / "integration.json"
    integration_json.write_text(json.dumps({"integration": "codex"}), encoding="utf-8")
    (spec_root / "codex-team").mkdir(parents=True, exist_ok=True)
    return project


def _invoke_in_project(project: Path, args: list[str]):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args)
    finally:
        os.chdir(old_cwd)
    return result


def test_api_status_returns_json(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result = _invoke_in_project(project, ["team", "api", "status"])
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["operation"] == "status"
    assert envelope["status"] == "ok"
    assert "payload" in envelope
    assert envelope["payload"]["runtime_state"]["session"]["session_id"] == "preview"
    assert "runtime_state_summary" in envelope["payload"]
    assert "join points" in envelope["payload"]["runtime_state_summary"].lower()
    assert "blockers" in envelope["payload"]["runtime_state_summary"].lower()
    assert "retry-pending" in envelope["payload"]["runtime_state_summary"].lower() or "retry pending" in envelope["payload"]["runtime_state_summary"].lower()


def test_api_tasks_reports_existing_task(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    task_ops.create_task(project, task_id="api-task", summary="API task")
    result = _invoke_in_project(project, ["team", "api", "tasks"])
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    tasks = envelope["payload"]["tasks"]
    assert any(task["task_id"] == "api-task" for task in tasks)
