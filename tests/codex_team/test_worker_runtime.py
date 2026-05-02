import json
import sys

from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, dispatch_runtime_task
from specify_cli.codex_team.state_paths import worker_heartbeat_path
from specify_cli.codex_team.worker_runtime import main


def test_worker_runtime_writes_blocked_result_when_packet_executor_is_not_configured(
    monkeypatch,
    codex_team_project_root,
):
    result_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "results" / "req-runtime.json"
    bootstrap_runtime_session(codex_team_project_root, "session-runtime")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-runtime.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-feature",
                "task_id": "T123",
                "story_id": "US1",
                "objective": "Implement T123",
                "scope": {"write_scope": ["src/t123.py"], "read_scope": ["src/contracts.py"]},
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
        codex_team_project_root,
        session_id="session-runtime",
        request_id="req-runtime",
        target_worker="worker-runtime-1",
        packet_path=str(packet_path),
        result_path=str(result_path),
    )
    monkeypatch.delenv("SPECIFY_CODEX_TEAM_PACKET_EXECUTOR", raising=False)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker-runtime",
            "--project-root",
            str(codex_team_project_root),
            "--session-id",
            "session-runtime",
            "--worker-id",
            "worker-runtime-1",
            "--task-id",
            "T123",
            "--request-id",
            "req-runtime",
            "--worktree",
            str(codex_team_project_root / ".specify" / "codex-team" / "worktrees" / "session-runtime" / "worker-runtime-1"),
            "--result-path",
            str(result_path),
            "--heartbeat-interval",
            "1",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    result = json.loads(result_path.read_text(encoding="utf-8"))
    heartbeat = json.loads(
        worker_heartbeat_path(codex_team_project_root, "worker-runtime-1").read_text(encoding="utf-8")
    )
    assert result["status"] == "blocked"
    assert heartbeat["status"] == "blocked"
    assert "packet executor" in heartbeat["details"]["reason"].lower()


def test_worker_runtime_executes_configured_packet_executor_and_writes_result(
    monkeypatch,
    codex_team_project_root,
):
    result_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "results" / "req-runtime-ok.json"
    bootstrap_runtime_session(codex_team_project_root, "session-runtime-ok")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-runtime-ok.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-feature",
                "task_id": "T124",
                "story_id": "US1",
                "objective": "Implement T124",
                "scope": {"write_scope": ["src/t124.py"], "read_scope": ["src/contracts.py"]},
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
        codex_team_project_root,
        session_id="session-runtime-ok",
        request_id="req-runtime-ok",
        target_worker="worker-runtime-2",
        packet_path=str(packet_path),
        result_path=str(result_path),
    )

    executor = codex_team_project_root / "fake-packet-executor.py"
    executor.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "payload = json.loads(sys.stdin.read())",
                "print(json.dumps({",
                "  'task_id': payload['packet']['task_id'],",
                "  'status': 'success',",
                "  'changed_files': ['src/t124.py'],",
                "  'validation_results': [{'command': 'pytest -q', 'status': 'passed', 'output': '1 passed'}],",
                "  'summary': 'executed by fake worker',",
                "  'rule_acknowledgement': {",
                "    'required_references_read': True,",
                "    'forbidden_drift_respected': True",
                "  }",
                "}))",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_PACKET_EXECUTOR", str(executor))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker-runtime",
            "--project-root",
            str(codex_team_project_root),
            "--session-id",
            "session-runtime-ok",
            "--worker-id",
            "worker-runtime-2",
            "--task-id",
            "T124",
            "--request-id",
            "req-runtime-ok",
            "--worktree",
            str(codex_team_project_root / ".specify" / "codex-team" / "worktrees" / "session-runtime-ok" / "worker-runtime-2"),
            "--result-path",
            str(result_path),
            "--heartbeat-interval",
            "1",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    result = json.loads(result_path.read_text(encoding="utf-8"))
    heartbeat = json.loads(
        worker_heartbeat_path(codex_team_project_root, "worker-runtime-2").read_text(encoding="utf-8")
    )
    assert result["status"] == "success"
    assert result["changed_files"] == ["src/t124.py"]
    assert heartbeat["status"] == "completed"
