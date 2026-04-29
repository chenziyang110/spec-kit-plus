from pathlib import Path

from specify_cli.orchestration.state_store import orchestration_root
from specify_cli.codex_team.state_paths import (
    batch_record_path,
    codex_team_state_root,
    dispatch_record_path,
    event_log_path,
    mailbox_path,
    phase_path,
    runtime_session_path,
    shutdown_path,
    task_record_path,
    worker_heartbeat_path,
    worker_identity_path,
)


def test_codex_team_state_root_is_under_specify_state(codex_team_project_root: Path):
    root = codex_team_state_root(codex_team_project_root)

    assert root == codex_team_project_root / ".specify" / "teams" / "state"
    assert root.parent.parent == orchestration_root(codex_team_project_root).parent


def test_codex_team_state_root_delegates_specify_namespace(monkeypatch, codex_team_project_root: Path):
    delegated_orchestration_root = codex_team_project_root / ".specify" / "delegated" / "orchestration"

    monkeypatch.setattr(
        "specify_cli.codex_team.state_paths.orchestration_root",
        lambda _: delegated_orchestration_root,
        raising=False,
    )

    root = codex_team_state_root(codex_team_project_root)

    assert root == delegated_orchestration_root.parent / "teams" / "state"


def test_runtime_session_path_uses_session_prefix(codex_team_project_root: Path):
    path = runtime_session_path(codex_team_project_root, "abc123")

    assert path == codex_team_project_root / ".specify" / "teams" / "state" / "session-abc123.json"


def test_canonical_runtime_paths_are_under_state_root(codex_team_project_root: Path):
    root = codex_team_state_root(codex_team_project_root)

    assert task_record_path(codex_team_project_root, "task-123") == root / "tasks" / "task-123.json"
    assert batch_record_path(codex_team_project_root, "batch-1") == root / "batches" / "batch-1.json"
    assert worker_identity_path(codex_team_project_root, "worker-a") == root / "workers" / "identity" / "worker-a.json"
    assert worker_heartbeat_path(codex_team_project_root, "worker-a") == root / "workers" / "heartbeat" / "worker-a.json"
    assert mailbox_path(codex_team_project_root, "worker-a") == root / "mailboxes" / "worker-a.json"
    assert dispatch_record_path(codex_team_project_root, "req-1") == root / "dispatch" / "req-1.json"
    assert phase_path(codex_team_project_root, "execute") == root / "phases" / "execute.json"
    assert event_log_path(codex_team_project_root, session_id="session-1") == root / "events" / "events-session-1.log"
    assert shutdown_path(codex_team_project_root, session_id="session-1") == root / "shutdown" / "session-1.json"


def test_event_log_path_defaults_to_generic_session(codex_team_project_root: Path):
    root = codex_team_state_root(codex_team_project_root)

    assert event_log_path(codex_team_project_root) == root / "events" / "events-default.log"


def test_shutdown_path_defaults_to_request_placeholder(codex_team_project_root: Path):
    root = codex_team_state_root(codex_team_project_root)

    assert shutdown_path(codex_team_project_root) == root / "shutdown" / "request.json"
