"""Contract tests for the Codex team CLI API surface."""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team import task_ops
from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, dispatch_runtime_task
from specify_cli.codex_team.state_paths import dispatch_record_path, result_record_path
from specify_cli.execution import worker_task_result_payload
from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult


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


def _seed_runtime_dispatch(project: Path, *, request_id: str = "req-submit", session_id: str = "default") -> Path:
    bootstrap_runtime_session(project, session_id)
    packet_path = project / ".specify" / "codex-team" / "state" / "packets" / f"{request_id}.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        """
{
  "feature_id": "001-feature",
  "task_id": "T001",
  "story_id": "US1",
  "objective": "Implement thing",
  "scope": {"write_scope": ["src/app.py"], "read_scope": ["src/contracts.py"]},
  "required_references": [{"path": "src/contracts.py", "reason": "preserve contract"}],
  "hard_rules": ["do not drift"],
  "forbidden_drift": ["no parallel stack"],
  "validation_gates": ["pytest -q"],
  "done_criteria": ["works"],
  "handoff_requirements": ["return changed files"],
  "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": true},
  "packet_version": 1
}
""".strip(),
        encoding="utf-8",
    )
    dispatch_runtime_task(
        project,
        session_id=session_id,
        request_id=request_id,
        target_worker="worker-1",
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True},
    )
    result = WorkerTaskResult(
        task_id="T001",
        status="success",
        changed_files=["src/app.py"],
        validation_results=[ValidationResult(command="pytest -q", status="passed", output="1 passed")],
        summary="done",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
        ),
    )
    result_file = project / "result.json"
    result_file.write_text(
        json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result_file


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


def test_api_submit_result_returns_json_and_persists_result(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result_file = _seed_runtime_dispatch(project)

    result = _invoke_in_project(
        project,
        ["team", "api", "submit-result", "--request-id", "req-submit", "--result-file", str(result_file)],
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["operation"] == "submit-result"
    assert envelope["status"] == "ok"
    assert envelope["payload"]["request_id"] == "req-submit"
    assert envelope["payload"]["status"] == "completed"
    assert dispatch_record_path(project, "req-submit").exists()
    assert result_record_path(project, "req-submit").exists()


def test_team_submit_result_command_accepts_worker_result_file(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    result_file = _seed_runtime_dispatch(project)

    result = _invoke_in_project(
        project,
        ["team", "submit-result", "--request-id", "req-submit", "--result-file", str(result_file)],
    )

    assert result.exit_code == 0, result.output
    assert "Submitted result for" in result.output


def test_team_submit_result_command_normalizes_done_with_concerns_payload(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    _seed_runtime_dispatch(project, request_id="req-alias")

    result_file = project / "alias-result.json"
    result_file.write_text(
        json.dumps(
            {
                "taskId": "T001",
                "status": "DONE_WITH_CONCERNS",
                "files_changed": ["src/app.py"],
                "message": "done with concerns",
                "issues": ["follow-up cleanup remains"],
                "validationResults": [
                    {"command": "pytest -q", "status": "passed", "output": "1 passed"}
                ],
                "ruleAcknowledgement": {
                    "required_references_read": True,
                    "forbidden_drift_respected": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["team", "submit-result", "--request-id", "req-alias", "--result-file", str(result_file)],
    )

    assert result.exit_code == 0, result.output
    stored = json.loads(dispatch_record_path(project, "req-alias").read_text(encoding="utf-8"))
    assert stored["status"] == "completed"
