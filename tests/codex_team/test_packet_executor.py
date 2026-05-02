import json
from pathlib import Path

from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult


def _write_packet(path: Path, *, task_id: str = "T900") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
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


def test_execute_packet_returns_blocked_result_when_no_packet_executor_is_configured(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.packet_executor import execute_packet, load_packet

    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-no-exec.json"
    _write_packet(packet_path, task_id="T901")
    monkeypatch.delenv("SPECIFY_CODEX_TEAM_PACKET_EXECUTOR", raising=False)

    outcome = execute_packet(
        load_packet(packet_path),
        project_root=codex_team_project_root,
        session_id="default",
        request_id="req-no-exec",
        worker_id="worker-1",
        worktree=codex_team_project_root / ".specify" / "codex-team" / "worktrees" / "default" / "worker-1",
    )

    assert outcome.result.status == "blocked"
    assert outcome.result.blockers
    assert outcome.result.failed_assumptions
    assert outcome.result.suggested_recovery_actions
    assert outcome.result.validation_results[0].status == "skipped"


def test_execute_packet_uses_configured_packet_executor_command(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.packet_executor import execute_packet, load_packet

    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-exec.json"
    _write_packet(packet_path, task_id="T902")

    executor = codex_team_project_root / "fake-packet-executor.py"
    result_payload = {
        "task_id": "T902",
        "status": "success",
        "changed_files": ["src/t902.py"],
        "validation_results": [{"command": "pytest -q", "status": "passed", "output": "1 passed"}],
        "summary": "executed",
        "rule_acknowledgement": {
            "required_references_read": True,
            "forbidden_drift_respected": True,
        },
    }
    WorkerTaskResult(
        task_id="T902",
        status="success",
        changed_files=["src/t902.py"],
        validation_results=[ValidationResult(command="pytest -q", status="passed", output="1 passed")],
        summary="executed",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
        ),
    )
    executor.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "payload = json.loads(sys.stdin.read())",
                "assert payload['request_id'] == 'req-exec'",
                f"print({json.dumps(json.dumps(result_payload))})",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_PACKET_EXECUTOR", str(executor))

    outcome = execute_packet(
        load_packet(packet_path),
        project_root=codex_team_project_root,
        session_id="default",
        request_id="req-exec",
        worker_id="worker-2",
        worktree=codex_team_project_root / ".specify" / "codex-team" / "worktrees" / "default" / "worker-2",
    )

    assert outcome.result.status == "success"
    assert outcome.result.changed_files == ["src/t902.py"]
    assert outcome.result.validation_results[0].status == "passed"
