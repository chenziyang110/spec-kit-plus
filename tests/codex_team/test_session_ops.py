import json
from pathlib import Path

import pytest

from specify_cli.codex_team.session_ops import (
    SessionLifecycleError,
    acknowledge_shutdown,
    bootstrap_session,
    cleanup_session,
    monitor_summary,
    request_shutdown,
)
from specify_cli.codex_team.state_paths import (
    monitor_snapshot_path,
    phase_path,
    runtime_session_path,
    shutdown_path,
    team_config_path,
    worker_heartbeat_path,
    worker_identity_path,
)
from specify_cli.codex_team.task_ops import create_task


@pytest.fixture(autouse=True)
def allow_tmux(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.ensure_tmux_available", lambda: None)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_session_status(project_root: Path, session_id: str, status: str) -> None:
    path = runtime_session_path(project_root, session_id)
    payload = _read_json(path)
    payload["status"] = status
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_bootstrap_writes_config_phase_worker_monitor(codex_team_project_root: Path):
    session = bootstrap_session(codex_team_project_root, session_id="session-ops")

    config_payload = _read_json(team_config_path(codex_team_project_root))
    assert config_payload["session_id"] == session.session_id
    assert config_payload["team_name"] == session.session_id

    phase_payload = _read_json(phase_path(codex_team_project_root, "bootstrap"))
    assert phase_payload["phase"] == "bootstrap"
    assert phase_payload["session_id"] == session.session_id

    identity_payload = _read_json(worker_identity_path(codex_team_project_root, "leader"))
    assert identity_payload["worker_id"] == "leader"

    heartbeat_payload = _read_json(worker_heartbeat_path(codex_team_project_root, "leader"))
    assert heartbeat_payload["status"] == "ready"

    snapshot_path = monitor_snapshot_path(codex_team_project_root, f"monitor-{session.session_id}")
    snapshot_payload = _read_json(snapshot_path)
    assert snapshot_payload["snapshot_id"] == f"monitor-{session.session_id}"


def test_bootstrap_rejects_duplicate_active_team(codex_team_project_root: Path):
    bootstrap_session(codex_team_project_root, session_id="session-ops")
    with pytest.raises(SessionLifecycleError):
        bootstrap_session(codex_team_project_root, session_id="session-ops")


def test_shutdown_request_and_acknowledge_flow(codex_team_project_root: Path):
    session = bootstrap_session(codex_team_project_root, session_id="session-ops")

    request_payload = request_shutdown(
        codex_team_project_root,
        session_id=session.session_id,
        reason="finished",
        requested_by="leader",
    )
    assert request_payload["status"] == "requested"
    assert request_payload["reason"] == "finished"

    requested = _read_json(shutdown_path(codex_team_project_root, session.session_id))
    assert requested["status"] == "requested"

    acknowledged_payload = acknowledge_shutdown(
        codex_team_project_root,
        session_id=session.session_id,
        acknowledged_by="leader",
    )
    assert acknowledged_payload["status"] == "acknowledged"

    shutdown_payload = _read_json(shutdown_path(codex_team_project_root, session.session_id))
    assert shutdown_payload["status"] == "acknowledged"

    session_payload = _read_json(runtime_session_path(codex_team_project_root, session.session_id))
    assert session_payload["status"] == "shutdown_acknowledged"


def test_cleanup_requires_terminal_state(codex_team_project_root: Path):
    session = bootstrap_session(codex_team_project_root, session_id="session-ops")
    with pytest.raises(SessionLifecycleError):
        cleanup_session(codex_team_project_root, session_id=session.session_id)

    _write_session_status(codex_team_project_root, session.session_id, "failed")
    cleaned = cleanup_session(codex_team_project_root, session_id=session.session_id)
    payload = _read_json(runtime_session_path(codex_team_project_root, session.session_id))
    assert payload["status"] == "cleaned"

    cleanup_phase = _read_json(phase_path(codex_team_project_root, "cleanup"))
    assert cleanup_phase["phase"] == "cleanup"


def test_monitor_summary_reflects_tasks_and_workers(codex_team_project_root: Path):
    session = bootstrap_session(codex_team_project_root, session_id="session-ops")

    snapshot = monitor_summary(codex_team_project_root, session_id=session.session_id)
    assert snapshot.task_count == 0
    assert snapshot.worker_count == 1
    assert snapshot.status_breakdown.get("ready") == 1

    create_task(codex_team_project_root, task_id="task-1", summary="seed")
    snapshot = monitor_summary(codex_team_project_root, session_id=session.session_id)
    assert snapshot.task_count == 1


def test_bootstrap_session_uses_canonical_write_json(monkeypatch, codex_team_project_root: Path):
    write_calls: list[Path] = []

    def _tracking_write_json(path: Path, payload: dict) -> Path:
        write_calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    monkeypatch.setattr(
        "specify_cli.codex_team.session_ops.write_json",
        _tracking_write_json,
        raising=False,
    )

    bootstrap_session(codex_team_project_root, session_id="session-ops")

    assert team_config_path(codex_team_project_root) in write_calls
    assert phase_path(codex_team_project_root, "bootstrap") in write_calls
