"""Runtime session and dispatch record serialization helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any

from .payload_utils import filter_payload
from .schema import SCHEMA_VERSION


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RuntimeSession:
    session_id: str
    status: str = "created"
    environment_check: str = "pending"
    created_at: str = ""
    finished_at: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _utc_now()


@dataclass(slots=True)
class DispatchRecord:
    request_id: str
    target_worker: str
    status: str = "pending"
    reason: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        now = _utc_now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


def runtime_state_payload(session: RuntimeSession, dispatches: list[DispatchRecord] | None = None) -> dict[str, Any]:
    """Build a JSON-serializable payload for persisted runtime state."""
    return {
        "session": asdict(session),
        "dispatches": [asdict(record) for record in (dispatches or [])],
    }


def runtime_session_from_json(text: str) -> RuntimeSession:
    payload = json.loads(text)
    return RuntimeSession(**filter_payload(payload, RuntimeSession))


def dispatch_record_from_json(text: str) -> DispatchRecord:
    payload = json.loads(text)
    return DispatchRecord(**filter_payload(payload, DispatchRecord))
