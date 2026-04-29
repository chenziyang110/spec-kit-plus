import json

from specify_cli.codex_team.runtime_state import (
    SCHEMA_VERSION,
    monitor_snapshot_from_json,
    monitor_snapshot_payload,
    task_claim_from_json,
    task_claim_payload,
    task_record_from_json,
    task_record_payload,
    team_config_from_json,
    team_config_payload,
    worker_heartbeat_from_json,
    worker_heartbeat_payload,
    worker_identity_from_json,
    worker_identity_payload,
)
from specify_cli.codex_team.state_paths import (
    codex_team_state_root,
    dispatch_record_path,
    event_log_path,
    mailbox_path,
    phase_path,
    result_record_path,
    shutdown_path,
    task_record_path,
    worker_heartbeat_path,
    worker_identity_path,
)


def test_state_root_is_under_specify_state(codex_team_project_root):
    root = codex_team_state_root(codex_team_project_root)

    assert root == codex_team_project_root / ".specify" / "teams" / "state"


def test_canonical_runtime_paths_are_under_state_root(codex_team_project_root):
    root = codex_team_state_root(codex_team_project_root)

    assert task_record_path(codex_team_project_root, "task-123") == root / "tasks" / "task-123.json"
    assert worker_identity_path(codex_team_project_root, "worker-a") == root / "workers" / "identity" / "worker-a.json"
    assert worker_heartbeat_path(codex_team_project_root, "worker-a") == root / "workers" / "heartbeat" / "worker-a.json"
    assert mailbox_path(codex_team_project_root, "worker-a") == root / "mailboxes" / "worker-a.json"
    assert dispatch_record_path(codex_team_project_root, "req-1") == root / "dispatch" / "req-1.json"
    assert result_record_path(codex_team_project_root, "req-1") == root / "results" / "req-1.json"
    assert phase_path(codex_team_project_root, "execute") == root / "phases" / "execute.json"
    assert event_log_path(codex_team_project_root, session_id="session-1") == root / "events" / "events-session-1.log"
    assert shutdown_path(codex_team_project_root, session_id="session-1") == root / "shutdown" / "session-1.json"


def test_team_config_payload_round_trips_through_json():
    payload = team_config_payload(team_name="codex", session_id="session-root")
    parsed = team_config_from_json(json.dumps(payload))

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["team_name"] == "codex"
    assert parsed.session_id == "session-root"
    assert parsed.schema_version == SCHEMA_VERSION


def test_team_config_payload_uses_orchestration_utc_now(monkeypatch):
    fixed_now = "2026-04-13T00:00:00+00:00"
    monkeypatch.setattr("specify_cli.codex_team.runtime_state.utc_now", lambda: fixed_now, raising=False)

    payload = team_config_payload(team_name="codex", session_id="session-root")

    assert payload["created_at"] == fixed_now


def test_schema_version_constant_matches_shared_value():
    from specify_cli.codex_team.schema import SCHEMA_VERSION as base_schema_version

    assert SCHEMA_VERSION == base_schema_version


def test_team_config_parser_is_forward_compatible():
    payload = team_config_payload(team_name="codex", session_id="session-root")
    payload["extra_field"] = {"foo": "bar"}

    parsed = team_config_from_json(json.dumps(payload))

    assert not hasattr(parsed, "extra_field")


def test_task_record_payload_round_trips_through_json():
    payload = task_record_payload(task_id="task-42", summary="fix bug", owner="worker-a", status="running")
    parsed = task_record_from_json(json.dumps(payload))

    assert payload["task_id"] == "task-42"
    assert parsed.status == "running"
    assert parsed.owner == "worker-a"
    assert parsed.schema_version == SCHEMA_VERSION


def test_task_record_parser_ignores_unknown_fields():
    payload = task_record_payload(task_id="task-99")
    payload["unexpected"] = "value"

    parsed = task_record_from_json(json.dumps(payload))

    assert parsed.task_id == "task-99"
    assert not hasattr(parsed, "unexpected")


def test_task_claim_payload_round_trips_through_json():
    payload = task_claim_payload(claim_id="claim-1", task_id="task-42", worker_id="worker-a")
    parsed = task_claim_from_json(json.dumps(payload))

    assert payload["claim_id"] == "claim-1"
    assert parsed.task_id == "task-42"
    assert parsed.worker_id == "worker-a"
    assert parsed.schema_version == SCHEMA_VERSION


def test_task_claim_parser_ignores_unknown_fields():
    payload = task_claim_payload(claim_id="claim-2", task_id="task-42", worker_id="worker-a")
    payload["extra"] = 1

    parsed = task_claim_from_json(json.dumps(payload))

    assert parsed.claim_id == "claim-2"
    assert not hasattr(parsed, "extra")


def test_worker_identity_payload_round_trips_through_json():
    payload = worker_identity_payload(worker_id="worker-a", hostname="host.local")
    parsed = worker_identity_from_json(json.dumps(payload))

    assert payload["worker_id"] == "worker-a"
    assert parsed.hostname == "host.local"
    assert parsed.schema_version == SCHEMA_VERSION


def test_worker_identity_parser_ignores_unknown_fields():
    payload = worker_identity_payload(worker_id="worker-b", hostname="host.alt")
    payload["metadata"] = {"tags": ["alpha"]}

    parsed = worker_identity_from_json(json.dumps(payload))

    assert parsed.hostname == "host.alt"
    assert parsed.metadata == {"tags": ["alpha"]}


def test_worker_heartbeat_payload_round_trips_through_json():
    payload = worker_heartbeat_payload(worker_id="worker-a", status="ready")
    parsed = worker_heartbeat_from_json(json.dumps(payload))

    assert payload["worker_id"] == "worker-a"
    assert parsed.status == "ready"
    assert parsed.schema_version == SCHEMA_VERSION


def test_worker_heartbeat_parser_ignores_unknown_fields():
    payload = worker_heartbeat_payload(worker_id="worker-a", status="ready")
    payload["extra"] = "ignored"

    parsed = worker_heartbeat_from_json(json.dumps(payload))

    assert parsed.worker_id == "worker-a"
    assert not hasattr(parsed, "extra")


def test_monitor_snapshot_payload_round_trips_through_json():
    details = {"pending": 1, "running": 2}
    payload = monitor_snapshot_payload(
        snapshot_id="snapshot-1",
        task_count=3,
        worker_count=2,
        status_breakdown=details,
    )
    parsed = monitor_snapshot_from_json(json.dumps(payload))

    assert payload["snapshot_id"] == "snapshot-1"
    assert parsed.task_count == 3
    assert parsed.worker_count == 2
    assert parsed.status_breakdown == details
    assert parsed.schema_version == SCHEMA_VERSION


def test_monitor_snapshot_parser_ignores_unknown_fields():
    payload = monitor_snapshot_payload(snapshot_id="snapshot-2", task_count=1, worker_count=1)
    payload["extra"] = {"foo": "bar"}

    parsed = monitor_snapshot_from_json(json.dumps(payload))

    assert parsed.snapshot_id == "snapshot-2"
    assert not hasattr(parsed, "extra")


def test_dispatch_record_path_contract_stays_under_dispatch_root(codex_team_project_root):
    payload = dispatch_record_path(codex_team_project_root, "req-contract")
    assert str(payload).endswith(".specify\\teams\\state\\dispatch\\req-contract.json") or str(payload).endswith(".specify/teams/state/dispatch/req-contract.json")
