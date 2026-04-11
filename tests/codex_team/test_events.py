import json
from datetime import datetime, timezone

from specify_cli.codex_team.events import (
    append_event,
    event_log_path,
    event_record_from_json,
    iter_event_log,
)
from specify_cli.codex_team.schema import SCHEMA_VERSION


def test_append_event_records_line(tmp_path):
    log_path = event_log_path(tmp_path, session_id="session-1")

    append_event(
        log_path,
        event_id="evt-1",
        kind="task.created",
        payload={"task_id": "task-1"},
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    record = event_record_from_json(lines[0])
    assert record.event_id == "evt-1"
    assert record.kind == "task.created"
    assert record.payload["task_id"] == "task-1"


def test_iter_event_log_returns_all_events(tmp_path):
    log_path = event_log_path(tmp_path, session_id="session-2")

    append_event(log_path, event_id="evt-2", kind="worker.heartbeat", payload={"worker_id": "worker-a"})
    append_event(log_path, event_id="evt-3", kind="worker.started", payload={"worker_id": "worker-a"})

    records = list(iter_event_log(log_path))

    assert len(records) == 2
    assert records[1].event_id == "evt-3"
    assert records[1].kind == "worker.started"


def test_event_record_parser_ignores_unknown_fields():
    created_at = datetime.now(timezone.utc).isoformat()
    raw = {
        "event_id": "evt-extra",
        "kind": "worker.test",
        "payload": {"worker_id": "worker-a"},
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "extra": "ignored",
    }

    record = event_record_from_json(json.dumps(raw))

    assert record.event_id == "evt-extra"
    assert record.kind == "worker.test"
    assert record.schema_version == SCHEMA_VERSION


def test_iter_event_log_handles_missing_file(tmp_path):
    log_path = event_log_path(tmp_path, session_id="missing")

    assert list(iter_event_log(log_path)) == []
