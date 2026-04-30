import json

from specify_cli.codex_team.runtime_bridge import (
    bootstrap_runtime_session,
    dispatch_runtime_task,
    mark_runtime_failure,
)
from specify_cli.codex_team.state_paths import dispatch_record_path, runtime_session_path


def test_dispatch_runtime_task_writes_record(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    bootstrap_runtime_session(codex_team_project_root, "session-3")

    record = dispatch_runtime_task(
        codex_team_project_root,
        session_id="session-3",
        request_id="req-3",
        target_worker="worker-a",
        packet_path="F:/tmp/packets/req-3.json",
        packet_summary={"task_id": "T002", "write_scope": ["src/t002.py"]},
        delegation_metadata={
            "native_subagent_surface": "spawn_agent",
            "result_contract": "WorkerTaskResult contract",
            "structured_results_expected": True,
        },
    )
    stored = json.loads(dispatch_record_path(codex_team_project_root, "req-3").read_text(encoding="utf-8"))
    session = json.loads(runtime_session_path(codex_team_project_root, "session-3").read_text(encoding="utf-8"))

    assert record.status == "dispatched"
    assert stored["target_worker"] == "worker-a"
    assert stored["packet_path"] == "F:/tmp/packets/req-3.json"
    assert stored["packet_summary"]["task_id"] == "T002"
    assert stored["delegation_metadata"]["native_subagent_surface"] == "spawn_agent"
    assert stored["delegation_metadata"]["structured_results_expected"] is True
    assert session["status"] == "running"


def test_mark_runtime_failure_preserves_failed_state(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    bootstrap_runtime_session(codex_team_project_root, "session-4")
    dispatch_runtime_task(
        codex_team_project_root,
        session_id="session-4",
        request_id="req-4",
        target_worker="worker-b",
    )

    session, record = mark_runtime_failure(
        codex_team_project_root,
        session_id="session-4",
        request_id="req-4",
        reason="synthetic failure",
        failure_class="critical",
        blocker_id="blk-req-4",
    )
    stored_record = json.loads(dispatch_record_path(codex_team_project_root, "req-4").read_text(encoding="utf-8"))
    stored_session = json.loads(runtime_session_path(codex_team_project_root, "session-4").read_text(encoding="utf-8"))

    assert session.status == "failed"
    assert record.status == "failed"
    assert stored_record["reason"] == "synthetic failure"
    assert stored_record["failure_class"] == "critical"
    assert stored_session["blocker_id"] == "blk-req-4"
    assert stored_session["finished_at"]


def test_mark_runtime_failure_keeps_transient_failure_retryable_until_budget_exhausted(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    bootstrap_runtime_session(codex_team_project_root, "session-5")
    dispatch_runtime_task(
        codex_team_project_root,
        session_id="session-5",
        request_id="req-5",
        target_worker="worker-c",
    )

    session, record = mark_runtime_failure(
        codex_team_project_root,
        session_id="session-5",
        request_id="req-5",
        reason="temporary backend timeout",
        failure_class="transient",
        retry_count=1,
        retry_budget=2,
    )

    stored_record = json.loads(dispatch_record_path(codex_team_project_root, "req-5").read_text(encoding="utf-8"))
    stored_session = json.loads(runtime_session_path(codex_team_project_root, "session-5").read_text(encoding="utf-8"))

    assert session.status == "retry_pending"
    assert record.status == "retry_pending"
    assert stored_record["failure_class"] == "transient"
    assert stored_record["retry_count"] == 1
    assert stored_record["retry_budget"] == 2
    assert stored_session["status"] == "retry_pending"
