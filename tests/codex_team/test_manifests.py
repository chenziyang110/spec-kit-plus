import json

from specify_cli.codex_team.manifests import (
    DispatchRecord,
    RuntimeSession,
    dispatch_record_from_json,
    runtime_session_from_json,
    runtime_state_payload,
)
from specify_cli.codex_team.schema import SCHEMA_VERSION


def test_runtime_state_payload_serializes_session_and_dispatches():
    session = RuntimeSession(
        session_id="session-1",
        status="ready",
        environment_check="pass",
        blocker_id="",
    )
    dispatch = DispatchRecord(
        request_id="req-1",
        target_worker="worker-a",
        status="dispatched",
        failure_class="",
        retry_count=0,
        retry_budget=0,
        delegation_metadata={"native_surface": "spawn_agent"},
    )

    payload = runtime_state_payload(session, [dispatch])

    assert payload["session"]["session_id"] == "session-1"
    assert payload["session"]["status"] == "ready"
    assert payload["session"]["blocker_id"] == ""
    assert payload["dispatches"][0]["request_id"] == "req-1"
    assert payload["dispatches"][0]["target_worker"] == "worker-a"
    assert payload["dispatches"][0]["failure_class"] == ""
    assert payload["dispatches"][0]["delegation_metadata"]["native_surface"] == "spawn_agent"


def test_runtime_session_round_trips_from_json():
    raw = json.dumps(
        {
            "session_id": "session-2",
            "status": "failed",
            "environment_check": "fail",
            "blocker_id": "blk-1",
            "created_at": "2026-04-10T00:00:00+00:00",
            "finished_at": "2026-04-10T00:10:00+00:00",
        }
    )

    session = runtime_session_from_json(raw)

    assert session.session_id == "session-2"
    assert session.status == "failed"
    assert session.blocker_id == "blk-1"
    assert session.finished_at == "2026-04-10T00:10:00+00:00"


def test_dispatch_record_round_trips_from_json():
    raw = json.dumps(
        {
            "request_id": "req-2",
            "target_worker": "worker-b",
            "status": "completed",
            "reason": "",
            "failure_class": "transient",
            "retry_count": 1,
            "retry_budget": 2,
            "delegation_metadata": {"native_surface": "spawn_agent"},
            "created_at": "2026-04-10T00:00:00+00:00",
            "updated_at": "2026-04-10T00:05:00+00:00",
        }
    )

    record = dispatch_record_from_json(raw)

    assert record.request_id == "req-2"
    assert record.target_worker == "worker-b"
    assert record.status == "completed"
    assert record.failure_class == "transient"
    assert record.retry_count == 1
    assert record.retry_budget == 2
    assert record.delegation_metadata["native_surface"] == "spawn_agent"


def test_runtime_session_parser_ignores_unknown_fields():
    raw = json.dumps(
        {
            "session_id": "session-3",
            "status": "created",
            "extra": "ignored",
        }
    )

    session = runtime_session_from_json(raw)

    assert session.session_id == "session-3"
    assert session.schema_version == SCHEMA_VERSION
    assert not hasattr(session, "extra")


def test_dispatch_record_parser_ignores_unknown_fields():
    raw = json.dumps(
        {
            "request_id": "req-4",
            "target_worker": "worker-c",
            "extra": "ignored",
        }
    )

    record = dispatch_record_from_json(raw)

    assert record.request_id == "req-4"
    assert record.schema_version == SCHEMA_VERSION
    assert not hasattr(record, "extra")
