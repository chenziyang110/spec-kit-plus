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
    )
    dispatch = DispatchRecord(
        request_id="req-1",
        target_worker="worker-a",
        status="dispatched",
    )

    payload = runtime_state_payload(session, [dispatch])

    assert payload["session"]["session_id"] == "session-1"
    assert payload["session"]["status"] == "ready"
    assert payload["dispatches"][0]["request_id"] == "req-1"
    assert payload["dispatches"][0]["target_worker"] == "worker-a"


def test_runtime_session_round_trips_from_json():
    raw = json.dumps(
        {
            "session_id": "session-2",
            "status": "failed",
            "environment_check": "fail",
            "created_at": "2026-04-10T00:00:00+00:00",
            "finished_at": "2026-04-10T00:10:00+00:00",
        }
    )

    session = runtime_session_from_json(raw)

    assert session.session_id == "session-2"
    assert session.status == "failed"
    assert session.finished_at == "2026-04-10T00:10:00+00:00"


def test_dispatch_record_round_trips_from_json():
    raw = json.dumps(
        {
            "request_id": "req-2",
            "target_worker": "worker-b",
            "status": "completed",
            "reason": "",
            "created_at": "2026-04-10T00:00:00+00:00",
            "updated_at": "2026-04-10T00:05:00+00:00",
        }
    )

    record = dispatch_record_from_json(raw)

    assert record.request_id == "req-2"
    assert record.target_worker == "worker-b"
    assert record.status == "completed"


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
