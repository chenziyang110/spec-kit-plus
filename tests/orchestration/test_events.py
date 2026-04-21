from pathlib import Path

from specify_cli.orchestration.events import append_event, event_log_path, replay_events


def test_append_event_writes_jsonl_record(tmp_path: Path):
    log_path = event_log_path(tmp_path, session_id="session-a")

    record = append_event(
        log_path,
        event_name="batch.started",
        payload={"batch_id": "batch-1"},
        event_id="evt-1",
    )

    assert record.event_id == "evt-1"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "batch.started" in lines[0]


def test_replay_events_returns_records_in_append_order(tmp_path: Path):
    log_path = event_log_path(tmp_path, session_id="session-b")

    append_event(log_path, event_name="lane.created", payload={"lane_id": "lane-1"}, event_id="evt-1")
    append_event(log_path, event_name="task.queued", payload={"task_id": "task-1"}, event_id="evt-2")

    events = list(replay_events(log_path))

    assert [event.event_id for event in events] == ["evt-1", "evt-2"]
    assert [event.event_name for event in events] == ["lane.created", "task.queued"]


def test_replay_events_returns_empty_iterator_when_log_is_missing(tmp_path: Path):
    log_path = event_log_path(tmp_path, session_id="missing")

    assert list(replay_events(log_path)) == []
