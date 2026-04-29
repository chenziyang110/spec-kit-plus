"""Normalize subagent result payloads into the canonical contract."""

from __future__ import annotations

import json
from typing import Any

from .result_schema import (
    RuleAcknowledgement,
    ValidationResult,
    WorkerTaskResult,
)

_STATUS_ALIASES = {
    "pending": "pending",
    "success": "success",
    "done": "success",
    "completed": "success",
    "done_with_concerns": "success",
    "blocked": "blocked",
    "needs_context": "blocked",
    "failed": "failed",
    "error": "failed",
}
_VALIDATION_STATUS_ALIASES = {
    "passed": "passed",
    "pass": "passed",
    "success": "passed",
    "failed": "failed",
    "fail": "failed",
    "error": "failed",
    "skipped": "skipped",
    "skip": "skipped",
}


def _as_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def _pick(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _normalize_validation_results(payload: dict[str, Any]) -> list[ValidationResult]:
    raw_items = _pick(payload, "validation_results", "validationResults")
    if not isinstance(raw_items, list):
        return []

    results: list[ValidationResult] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        command = str(_pick(item, "command", "cmd") or "").strip()
        raw_status = str(_pick(item, "status", "result") or "").strip().lower()
        status = _VALIDATION_STATUS_ALIASES.get(raw_status, "failed")
        output = str(_pick(item, "output", "details", "message") or "")
        if command:
            results.append(ValidationResult(command=command, status=status, output=output))
    return results


def _normalize_rule_acknowledgement(payload: dict[str, Any]) -> RuleAcknowledgement:
    raw = _pick(payload, "rule_acknowledgement", "ruleAcknowledgement")
    if not isinstance(raw, dict):
        return RuleAcknowledgement()
    return RuleAcknowledgement(
        required_references_read=bool(
            _pick(raw, "required_references_read", "requiredReferencesRead")
        ),
        forbidden_drift_respected=bool(
            _pick(raw, "forbidden_drift_respected", "forbiddenDriftRespected")
        ),
        context_bundle_read=bool(
            _pick(raw, "context_bundle_read", "contextBundleRead")
        ),
        paths_read=_as_str_list(_pick(raw, "paths_read", "pathsRead")),
        critical_notes=_as_str_list(_pick(raw, "critical_notes", "criticalNotes")),
    )


def normalize_worker_task_result_payload(payload: WorkerTaskResult | dict[str, Any] | str) -> WorkerTaskResult:
    """Normalize common worker result payload shapes into ``WorkerTaskResult``."""

    if isinstance(payload, WorkerTaskResult):
        return payload
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise TypeError("worker result payload must be a WorkerTaskResult, dict, or JSON text")

    raw_status = str(_pick(payload, "status", "reported_status", "result_status") or "").strip().lower()
    canonical_status = _STATUS_ALIASES.get(raw_status, "failed")
    summary = str(_pick(payload, "summary", "message", "output_summary") or "")
    blockers = _as_str_list(_pick(payload, "blockers", "blocking_reasons", "blocker"))
    failed_assumptions = _as_str_list(
        _pick(payload, "failed_assumptions", "failedAssumptions", "missing_context", "assumptions")
    )
    recovery_actions = _as_str_list(
        _pick(payload, "suggested_recovery_actions", "recovery_actions", "recoveryActions", "next_steps")
    )
    concerns = _as_str_list(_pick(payload, "concerns", "issues", "notes"))

    if raw_status == "done_with_concerns" and not concerns:
        concerns = ["worker reported follow-up concerns"]

    if raw_status == "needs_context":
        if not blockers and summary.strip():
            blockers = [summary.strip()]
        if not failed_assumptions:
            failed_assumptions = _as_str_list(_pick(payload, "missing_context")) or [
                "required execution context was not available",
            ]
        if not recovery_actions:
            recovery_actions = ["provide the missing context and resubmit the delegated task"]

    if canonical_status == "blocked":
        if not blockers and summary.strip():
            blockers = [summary.strip()]
        if not failed_assumptions:
            failed_assumptions = ["worker could not proceed with the available assumptions"]
        if not recovery_actions:
            recovery_actions = ["inspect the blocker details and resubmit the delegated task"]

    task_id = str(_pick(payload, "task_id", "taskId") or "").strip()
    changed_files = _as_str_list(_pick(payload, "changed_files", "changedFiles", "files_changed"))

    return WorkerTaskResult(
        task_id=task_id,
        status=canonical_status,
        changed_files=changed_files,
        validation_results=_normalize_validation_results(payload),
        summary=summary,
        concerns=concerns,
        reported_status=raw_status or canonical_status,
        blockers=blockers,
        failed_assumptions=failed_assumptions,
        suggested_recovery_actions=recovery_actions,
        rule_acknowledgement=_normalize_rule_acknowledgement(payload),
    )
