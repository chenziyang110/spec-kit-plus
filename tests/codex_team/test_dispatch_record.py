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
    )
    stored = json.loads(dispatch_record_path(codex_team_project_root, "req-3").read_text(encoding="utf-8"))
    session = json.loads(runtime_session_path(codex_team_project_root, "session-3").read_text(encoding="utf-8"))

    assert record.status == "dispatched"
    assert stored["target_worker"] == "worker-a"
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
    )
    stored_record = json.loads(dispatch_record_path(codex_team_project_root, "req-4").read_text(encoding="utf-8"))
    stored_session = json.loads(runtime_session_path(codex_team_project_root, "session-4").read_text(encoding="utf-8"))

    assert session.status == "failed"
    assert record.status == "failed"
    assert stored_record["reason"] == "synthetic failure"
    assert stored_session["finished_at"]
