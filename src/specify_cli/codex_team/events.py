"\"\"\"Append-only event logging helpers for Codex team runtime.\"\"\""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from .payload_utils import filter_payload
from .schema import SCHEMA_VERSION
from .state_paths import event_log_path as canonical_event_log_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class EventRecord:
    event_id: str
    kind: str
    payload: dict[str, Any]
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _utc_now()


def event_log_path(project_root: Path, session_id: str | None = None) -> Path:
    return canonical_event_log_path(project_root, session_id=session_id)


def append_event(
    log_path: Path,
    *,
    event_id: str,
    kind: str,
    payload: dict[str, Any],
) -> EventRecord:
    record = EventRecord(event_id=event_id, kind=kind, payload=payload)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record)) + "\n")
    return record


def event_record_from_json(text: str) -> EventRecord:
    payload = json.loads(text)
    return EventRecord(**filter_payload(payload, EventRecord))


def iter_event_log(log_path: Path) -> Iterable[EventRecord]:
    if not log_path.exists():
        return
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield event_record_from_json(line)
