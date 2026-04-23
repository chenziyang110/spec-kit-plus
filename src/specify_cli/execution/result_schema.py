"""Typed delegated-worker result contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


WorkerStatus = Literal["success", "blocked", "failed"]
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
    blockers: list[str] = field(default_factory=list)
    failed_assumptions: list[str] = field(default_factory=list)
    suggested_recovery_actions: list[str] = field(default_factory=list)
    rule_acknowledgement: RuleAcknowledgement = field(default_factory=RuleAcknowledgement)
