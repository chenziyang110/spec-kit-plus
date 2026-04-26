"""Typed delegated-worker result contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Literal

from specify_cli.verification import ValidationResult


WorkerStatus = Literal["pending", "success", "blocked", "failed"]


@dataclass(slots=True)
class RuleAcknowledgement:
    required_references_read: bool = False
    forbidden_drift_respected: bool = False
    context_bundle_read: bool = False
    paths_read: list[str] = field(default_factory=list)
    critical_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkerTaskResult:
    task_id: str
    status: WorkerStatus
    changed_files: list[str] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    summary: str = ""
    concerns: list[str] = field(default_factory=list)
    reported_status: str = ""
    blockers: list[str] = field(default_factory=list)
    failed_assumptions: list[str] = field(default_factory=list)
    suggested_recovery_actions: list[str] = field(default_factory=list)
    rule_acknowledgement: RuleAcknowledgement = field(default_factory=RuleAcknowledgement)


def _filter_dataclass_payload(cls: type, payload: dict[str, object]) -> dict[str, object]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in payload.items() if key in allowed}


def worker_task_result_payload(result: WorkerTaskResult) -> dict[str, object]:
    """Return a JSON-serializable payload for a worker result."""

    return asdict(result)


def worker_task_result_from_json(text: str) -> WorkerTaskResult:
    """Parse a worker result from JSON text."""

    payload = json.loads(text)
    validation_results = [
        ValidationResult(**_filter_dataclass_payload(ValidationResult, item))
        for item in payload.get("validation_results", [])
        if isinstance(item, dict)
    ]
    raw_ack = _filter_dataclass_payload(
        RuleAcknowledgement,
        payload.get("rule_acknowledgement", {}),
    )
    raw_ack["paths_read"] = [
        str(item).strip()
        for item in raw_ack.get("paths_read", [])
        if str(item).strip()
    ]
    raw_ack["critical_notes"] = [
        str(item).strip()
        for item in raw_ack.get("critical_notes", [])
        if str(item).strip()
    ]
    rule_acknowledgement = RuleAcknowledgement(**raw_ack)
    result_payload = _filter_dataclass_payload(WorkerTaskResult, payload)
    result_payload["validation_results"] = validation_results
    result_payload["rule_acknowledgement"] = rule_acknowledgement
    return WorkerTaskResult(**result_payload)
