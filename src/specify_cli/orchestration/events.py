"""Append-only event writing and replay helpers for orchestration state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from .models import utc_now
from .state_store import event_log_path as canonical_event_log_path


@dataclass(slots=True)
class OrchestrationEvent:
    """Single append-only orchestration event."""

    event_id: str
    event_name: str
    payload: dict[str, Any]
    created_at: str


def event_log_path(project_root: Path, session_id: str | None = None) -> Path:
    """Expose canonical event log path helper."""
    return canonical_event_log_path(project_root, session_id=session_id)


def append_event(
    log_path: Path,
    *,
    event_name: str,
    payload: dict[str, Any],
    event_id: str | None = None,
) -> OrchestrationEvent:
    """Append an event to the JSONL event log and return the recorded event."""
    record = OrchestrationEvent(
        event_id=event_id or str(uuid4()),
        event_name=event_name,
        payload=payload,
        created_at=utc_now(),
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return record


def replay_events(log_path: Path) -> Iterable[OrchestrationEvent]:
    """Yield events in append order from a JSONL event log."""
    if not log_path.exists():
        return []

    records: list[OrchestrationEvent] = []
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            records.append(OrchestrationEvent(**payload))
    return records
