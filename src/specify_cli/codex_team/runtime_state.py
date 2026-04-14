"""Builders and parsers for Codex team runtime JSON records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from specify_cli.orchestration.models import utc_now

from .payload_utils import filter_payload
from .schema import SCHEMA_VERSION


@dataclass(slots=True)
class TeamConfig:
    team_name: str
    session_id: str
    config_version: str = "1"
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = utc_now()


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    summary: str = ""
    status: str = "pending"
    owner: str = ""
    version: int = 1
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        now = utc_now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if self.metadata is None:
            self.metadata = {}


@dataclass(slots=True)
class TaskClaim:
    claim_id: str
    task_id: str
    worker_id: str
    version: int = 1
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = utc_now()


@dataclass(slots=True)
class WorkerIdentity:
    worker_id: str
    hostname: str
    schema_version: str = SCHEMA_VERSION
    metadata: dict[str, Any] | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = utc_now()


@dataclass(slots=True)
class WorkerHeartbeat:
    worker_id: str
    status: str
    version: int = 1
    schema_version: str = SCHEMA_VERSION
    details: dict[str, Any] | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = {}
        if not self.timestamp:
            self.timestamp = utc_now()


@dataclass(slots=True)
class MonitorSnapshot:
    snapshot_id: str
    task_count: int = 0
    worker_count: int = 0
    status_breakdown: dict[str, int] | None = None
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.status_breakdown is None:
            self.status_breakdown = {}
        if not self.created_at:
            self.created_at = utc_now()


@dataclass(slots=True)
class BatchRecord:
    batch_id: str
    batch_name: str
    session_id: str
    feature_dir: str
    task_ids: list[str]
    request_ids: list[str]
    join_point_name: str = ""
    batch_classification: str = "strict"
    safe_preparation: bool = False
    status: str = "dispatched"
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = utc_now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


def team_config_payload(*, team_name: str, session_id: str, config_version: str = "1") -> dict[str, Any]:
    return asdict(
        TeamConfig(
            team_name=team_name,
            session_id=session_id,
            config_version=config_version,
        )
    )


def team_config_from_json(text: str) -> TeamConfig:
    payload = json.loads(text)
    return TeamConfig(**filter_payload(payload, TeamConfig))


def task_record_payload(
    *,
    task_id: str,
    summary: str = "",
    status: str = "pending",
    owner: str = "",
    version: int = 1,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return asdict(
        TaskRecord(
            task_id=task_id,
            summary=summary,
            status=status,
            owner=owner,
            version=version,
            metadata=metadata,
        )
    )


def task_record_from_json(text: str) -> TaskRecord:
    payload = json.loads(text)
    return TaskRecord(**filter_payload(payload, TaskRecord))


def task_claim_payload(
    *,
    claim_id: str,
    task_id: str,
    worker_id: str,
    version: int = 1,
) -> dict[str, Any]:
    return asdict(
        TaskClaim(
            claim_id=claim_id,
            task_id=task_id,
            worker_id=worker_id,
            version=version,
        )
    )


def task_claim_from_json(text: str) -> TaskClaim:
    payload = json.loads(text)
    return TaskClaim(**filter_payload(payload, TaskClaim))


def worker_identity_payload(
    *,
    worker_id: str,
    hostname: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return asdict(
        WorkerIdentity(
            worker_id=worker_id,
            hostname=hostname,
            metadata=metadata,
        )
    )


def worker_identity_from_json(text: str) -> WorkerIdentity:
    payload = json.loads(text)
    return WorkerIdentity(**filter_payload(payload, WorkerIdentity))


def worker_heartbeat_payload(
    *,
    worker_id: str,
    status: str,
    version: int = 1,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return asdict(
        WorkerHeartbeat(
            worker_id=worker_id,
            status=status,
            version=version,
            details=details,
        )
    )


def worker_heartbeat_from_json(text: str) -> WorkerHeartbeat:
    payload = json.loads(text)
    return WorkerHeartbeat(**filter_payload(payload, WorkerHeartbeat))


def monitor_snapshot_payload(
    *,
    snapshot_id: str,
    task_count: int = 0,
    worker_count: int = 0,
    status_breakdown: dict[str, int] | None = None,
) -> dict[str, Any]:
    return asdict(
        MonitorSnapshot(
            snapshot_id=snapshot_id,
            task_count=task_count,
            worker_count=worker_count,
            status_breakdown=status_breakdown,
        )
    )


def monitor_snapshot_from_json(text: str) -> MonitorSnapshot:
    payload = json.loads(text)
    return MonitorSnapshot(**filter_payload(payload, MonitorSnapshot))


def batch_record_payload(
    *,
    batch_id: str,
    batch_name: str,
    session_id: str,
    feature_dir: str,
    task_ids: list[str],
    request_ids: list[str],
    join_point_name: str = "",
    batch_classification: str = "strict",
    safe_preparation: bool = False,
    status: str = "dispatched",
) -> dict[str, Any]:
    return asdict(
        BatchRecord(
            batch_id=batch_id,
            batch_name=batch_name,
            session_id=session_id,
            feature_dir=feature_dir,
            task_ids=task_ids,
            request_ids=request_ids,
            join_point_name=join_point_name,
            batch_classification=batch_classification,
            safe_preparation=safe_preparation,
            status=status,
        )
    )


def batch_record_from_json(text: str) -> BatchRecord:
    payload = json.loads(text)
    return BatchRecord(**filter_payload(payload, BatchRecord))
