import json
from pathlib import Path

import pytest

import specify_cli.orchestration.state_store as state_store
from specify_cli.orchestration.state_store import (
    batch_path,
    lane_path,
    orchestration_root,
    read_json,
    session_path,
    task_path,
    write_json,
)


def test_orchestration_root_is_under_specify(tmp_path: Path):
    root = orchestration_root(tmp_path)

    assert root == tmp_path / ".specify" / "orchestration"


def test_canonical_record_paths_are_under_orchestration_root(tmp_path: Path):
    root = orchestration_root(tmp_path)

    assert session_path(tmp_path, "session-1") == root / "sessions" / "session-1.json"
    assert batch_path(tmp_path, "batch-1") == root / "batches" / "batch-1.json"
    assert lane_path(tmp_path, "lane-1") == root / "lanes" / "lane-1.json"
    assert task_path(tmp_path, "task-1") == root / "tasks" / "task-1.json"


def test_write_json_creates_parent_directories_and_trailing_newline(tmp_path: Path):
    path = session_path(tmp_path, "session-2")
    payload = {"session_id": "session-2", "dispatch_shape": "one-subagent"}

    written = write_json(path, payload)

    assert written == path
    assert path.exists()
    raw = path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert raw == json.dumps(payload, indent=2) + "\n"
    assert json.loads(raw) == payload


def test_read_json_round_trips_payload(tmp_path: Path):
    path = task_path(tmp_path, "task-42")
    expected = {"task_id": "task-42", "status": "pending"}
    write_json(path, expected)

    assert read_json(path) == expected


def test_read_json_returns_none_for_missing_files(tmp_path: Path):
    path = task_path(tmp_path, "missing")

    assert read_json(path) is None


def test_write_json_retries_transient_replace_permission_error(monkeypatch, tmp_path: Path):
    path = session_path(tmp_path, "session-locked")
    attempts = 0
    real_replace = state_store.os.replace

    def _flaky_replace(src: Path, dst: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError(13, "Permission denied", str(dst))
        real_replace(src, dst)

    monkeypatch.setattr(state_store.os, "replace", _flaky_replace)
    monkeypatch.setattr(state_store.time, "sleep", lambda _seconds: None)

    payload = {"session_id": "session-locked", "status": "running"}
    written = write_json(path, payload)

    assert written == path
    assert attempts == 2
    assert read_json(path) == payload


def test_write_json_reraises_persistent_replace_permission_error(monkeypatch, tmp_path: Path):
    path = session_path(tmp_path, "session-locked")
    attempts = 0

    def _locked_replace(src: Path, dst: Path) -> None:
        nonlocal attempts
        attempts += 1
        raise PermissionError(13, "Permission denied", str(dst))

    monkeypatch.setattr(state_store.os, "replace", _locked_replace)
    monkeypatch.setattr(state_store.time, "sleep", lambda _seconds: None)

    with pytest.raises(PermissionError):
        write_json(path, {"session_id": "session-locked"})

    assert attempts == state_store.REPLACE_RETRY_ATTEMPTS
