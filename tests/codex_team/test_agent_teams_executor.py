import json
import os
import sys
from pathlib import Path

import pytest

from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, dispatch_runtime_task
from specify_cli.codex_team.state_paths import dispatch_record_path, result_record_path
from specify_cli.execution import worker_task_result_payload
from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult


def _seed_dispatch(project_root: Path, *, request_id: str, task_id: str) -> None:
    bootstrap_runtime_session(project_root, "default")
    packet_path = project_root / ".specify" / "codex-team" / "state" / "packets" / f"{request_id}.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-feature",
                "task_id": task_id,
                "story_id": "US1",
                "objective": f"Implement {task_id}",
                "scope": {"write_scope": [f"src/{task_id.lower()}.py"], "read_scope": ["src/contracts.py"]},
                "required_references": [{"path": "src/contracts.py", "reason": "preserve contract"}],
                "hard_rules": ["do not drift"],
                "forbidden_drift": ["no parallel stack"],
                "validation_gates": ["pytest -q"],
                "done_criteria": ["works"],
                "handoff_requirements": ["return changed files"],
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
                "packet_version": 1,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    dispatch_runtime_task(
        project_root,
        session_id="default",
        request_id=request_id,
        target_worker=task_id.lower(),
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True, "executor_mode": "agent-teams-runtime"},
        result_path=str(result_record_path(project_root, request_id)),
    )


def _write_manifest(
    project_root: Path,
    runtime_cli: Path,
    *,
    team_name: str = "codex-team-a",
    task_specs: list[dict[str, str]],
) -> Path:
    manifest_path = project_root / ".specify" / "codex-team" / "state" / "executors" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "runtime_cli_path": str(runtime_cli),
                "state_root": str(project_root / ".specify" / "codex-team" / "state" / "agent-teams" / "team-a"),
                "team_name": team_name,
                "worker_count": len(task_specs),
                "cwd": str(project_root),
                "tasks": task_specs,
                "session_id": "default",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_fake_runtime_cli(path: Path, *, emit_results: bool, capture_path: Path | None = None) -> None:
    capture_line = (
        f"Path(r'{capture_path}').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')"
        if capture_path is not None
        else ""
    )
    path.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "payload = json.loads(sys.stdin.read())",
                capture_line,
                "state_root = Path(os.environ['SPECIFY_TEAM_STATE_ROOT'])",
                "team_name = payload['teamName']",
                "tasks_dir = state_root / 'team' / team_name / 'tasks'",
                "tasks_dir.mkdir(parents=True, exist_ok=True)",
                "for index, task in enumerate(payload['tasks'], start=1):",
                "    description = task['description']",
                "    status = 'completed' if "
                + ("True" if emit_results else "False")
                + " else 'failed'",
                "    result_text = ''",
                "    if " + ("True" if emit_results else "False") + ":",
                "        marker_start = 'BEGIN_WORKER_TASK_RESULT_JSON'",
                "        marker_end = 'END_WORKER_TASK_RESULT_JSON'",
                "        start = description.index(marker_start) + len(marker_start)",
                "        end = description.index(marker_end)",
                "        payload_text = description[start:end].strip()",
                "        result_payload = json.loads(payload_text)",
                "        json_block = json.dumps(result_payload, ensure_ascii=False, indent=2)",
                "        result_text = f'{marker_start}\\n{json_block}\\n{marker_end}'",
                "    task_payload = {",
                "        'id': str(index),",
                "        'subject': task['subject'],",
                "        'description': description,",
                "        'status': status,",
                "        'result': result_text if status == 'completed' else None,",
                "        'error': '' if status == 'completed' else 'worker failed before structured handoff',",
                "        'created_at': '2026-04-25T00:00:00Z',",
                "    }",
                "    (tasks_dir / f'task-{index}.json').write_text(json.dumps(task_payload, ensure_ascii=False, indent=2), encoding='utf-8')",
                "json.dump({'status': 'completed' if "
                + ("True" if emit_results else "False")
                + " else 'failed', 'teamName': team_name, 'taskResults': [], 'duration': 0, 'workerCount': len(payload['tasks'])}, sys.stdout)",
            ]
        ),
        encoding="utf-8",
    )


def test_agent_teams_executor_submits_structured_results(monkeypatch, codex_team_project_root: Path):
    from specify_cli.codex_team.agent_teams_executor import main

    request_id = "req-t002"
    _seed_dispatch(codex_team_project_root, request_id=request_id, task_id="T002")
    runtime_cli = codex_team_project_root / "fake-runtime-cli.py"
    _write_fake_runtime_cli(runtime_cli, emit_results=True)
    expected_result = WorkerTaskResult(
        task_id="T002",
        status="success",
        changed_files=["src/t002.py"],
        validation_results=[ValidationResult(command="pytest -q", status="passed", output="1 passed")],
        summary="T002 done",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
        ),
    )
    manifest = _write_manifest(
        codex_team_project_root,
        runtime_cli,
        task_specs=[
            {
                "task_id": "T002",
                "request_id": request_id,
                "subject": "T002",
                "description": (
                    "Task T002\n"
                    "BEGIN_WORKER_TASK_RESULT_JSON\n"
                    f"{json.dumps(worker_task_result_payload(expected_result), ensure_ascii=False, indent=2)}\n"
                    "END_WORKER_TASK_RESULT_JSON\n"
                ),
            }
        ],
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent-teams-executor",
            "--project-root",
            str(codex_team_project_root),
            "--manifest-path",
            str(manifest),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    dispatch_payload = json.loads(dispatch_record_path(codex_team_project_root, request_id).read_text(encoding="utf-8"))
    stored_result = json.loads(result_record_path(codex_team_project_root, request_id).read_text(encoding="utf-8"))
    transcript = json.loads(manifest.with_suffix(".runtime.json").read_text(encoding="utf-8"))
    assert dispatch_payload["status"] == "completed"
    assert stored_result["task_id"] == "T002"
    assert stored_result["status"] == "success"
    assert transcript["returncode"] == 0


def test_agent_teams_executor_marks_missing_structured_results_failed(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.agent_teams_executor import main

    request_id = "req-t003"
    _seed_dispatch(codex_team_project_root, request_id=request_id, task_id="T003")
    runtime_cli = codex_team_project_root / "fake-runtime-cli.py"
    _write_fake_runtime_cli(runtime_cli, emit_results=False)
    manifest = _write_manifest(
        codex_team_project_root,
        runtime_cli,
        task_specs=[
            {
                "task_id": "T003",
                "request_id": request_id,
                "subject": "T003",
                "description": "Task T003 without result block",
            }
        ],
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent-teams-executor",
            "--project-root",
            str(codex_team_project_root),
            "--manifest-path",
            str(manifest),
        ],
    )

    exit_code = main()

    assert exit_code == 1
    dispatch_payload = json.loads(dispatch_record_path(codex_team_project_root, request_id).read_text(encoding="utf-8"))
    transcript = json.loads(manifest.with_suffix(".runtime.json").read_text(encoding="utf-8"))
    assert dispatch_payload["status"] == "failed"
    assert "structured worker result" in dispatch_payload["reason"].lower()
    assert transcript["returncode"] != 0 or "structured worker result" in dispatch_payload["reason"].lower()


def test_agent_teams_executor_honors_worker_cli_env_override_in_runtime_payload(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.agent_teams_executor import main

    request_id = "req-t004"
    _seed_dispatch(codex_team_project_root, request_id=request_id, task_id="T004")
    runtime_cli = codex_team_project_root / "fake-runtime-cli.py"
    capture_path = codex_team_project_root / "runtime-payload.json"
    _write_fake_runtime_cli(runtime_cli, emit_results=False, capture_path=capture_path)
    manifest = _write_manifest(
        codex_team_project_root,
        runtime_cli,
        task_specs=[
            {
                "task_id": "T004",
                "request_id": request_id,
                "subject": "T004",
                "description": "Task T004 without result block",
            }
        ],
    )

    monkeypatch.setenv("SP_TEAMS_WORKER_CLI", "gemini")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent-teams-executor",
            "--project-root",
            str(codex_team_project_root),
            "--manifest-path",
            str(manifest),
        ],
    )

    exit_code = main()

    assert exit_code == 1
    runtime_payload = json.loads(capture_path.read_text(encoding="utf-8"))
    transcript = json.loads(manifest.with_suffix(".runtime.json").read_text(encoding="utf-8"))
    assert runtime_payload["agentTypes"] == ["gemini"]
    assert transcript["runtime_payload"]["agentTypes"] == ["gemini"]
