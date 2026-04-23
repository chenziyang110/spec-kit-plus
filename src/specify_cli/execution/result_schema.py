"""Typed delegated-worker result contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Literal


WorkerStatus = Literal["pending", "success", "blocked", "failed"]
ValidationStatus = Literal["passed", "failed", "skipped"]


@dataclass(slots=True)
class ValidationResult:
    command: str
    status: ValidationStatus
    output: str = ""


@dataclass(slots=True)
class RuleAcknowledgement:
    required_references_read: bool = False
    forbidden_drift_respected: bool = False


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
    rule_acknowledgement = RuleAcknowledgement(
        **_filter_dataclass_payload(
            RuleAcknowledgement,
            payload.get("rule_acknowledgement", {}),
        )
    )
    result_payload = _filter_dataclass_payload(WorkerTaskResult, payload)
    result_payload["validation_results"] = validation_results
    result_payload["rule_acknowledgement"] = rule_acknowledgement
    return WorkerTaskResult(**result_payload)
