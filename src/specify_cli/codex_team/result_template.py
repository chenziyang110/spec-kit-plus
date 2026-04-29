"""Template and validation helpers for structured Codex team results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from specify_cli.codex_team.packet_executor import build_result_template
from specify_cli.codex_team.state_paths import dispatch_record_path
from specify_cli.execution import (
    PacketValidationError,
    WorkerTaskPacket,
    WorkerTaskResult,
    normalize_worker_task_result_payload,
    validate_worker_task_result,
    worker_task_packet_from_json,
)


def _load_dispatch_payload(project_root: Path, request_id: str) -> dict[str, Any]:
    path = dispatch_record_path(project_root, request_id)
    if not path.exists():
        raise ValueError(f"Dispatch request {request_id} was not found.")
    return json.loads(path.read_text(encoding="utf-8"))


def load_request_packet(project_root: Path, request_id: str) -> WorkerTaskPacket:
    dispatch = _load_dispatch_payload(project_root, request_id)
    packet_path = Path(str(dispatch.get("packet_path", "")).strip())
    if not packet_path or not packet_path.exists():
        raise ValueError(f"Packet for request {request_id} is unavailable.")
    return worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))


def build_request_result_template(project_root: Path, request_id: str) -> dict[str, object]:
    return build_result_template(load_request_packet(project_root, request_id))


def worker_result_schema_hint() -> dict[str, object]:
    return {
        "required_fields": ["task_id", "status"],
        "recommended_fields": [
            "changed_files",
            "validation_results",
            "summary",
            "rule_acknowledgement",
        ],
        "accepted_status_values": ["pending", "success", "blocked", "failed"],
        "canonical_template_defaults": {
            "status": "pending",
            "validation_results": "skipped until real execution occurs",
            "rule_acknowledgement": "all false until the worker has actually read and verified the packet context",
        },
        "submission_rules": [
            "Do not submit the canonical pending template unchanged.",
            "Replace pending/skipped placeholder values with the real success, blocked, or failed result before submit-result.",
        ],
        "validation_result_item": {
            "command": "pytest -q",
            "status": "passed | failed | skipped",
            "output": "command output",
        },
        "rule_acknowledgement": {
            "required_references_read": True,
            "forbidden_drift_respected": True,
            "context_bundle_read": True,
            "paths_read": ["PROJECT-HANDBOOK.md"],
            "critical_notes": ["what key boundary or verification rule you confirmed before execution"],
        },
        "aliases": {
            "taskId": "task_id",
            "files_changed": "changed_files",
            "validationResults": "validation_results",
            "ruleAcknowledgement": "rule_acknowledgement",
        },
    }


def render_schema_help() -> str:
    return json.dumps(worker_result_schema_hint(), ensure_ascii=False, indent=2)


def normalize_result_submission(
    project_root: Path,
    request_id: str,
    payload: WorkerTaskResult | dict[str, Any] | str,
) -> WorkerTaskResult:
    if isinstance(payload, str):
        if payload.startswith("\ufeff"):
            raise ValueError(
                "Result file contains a UTF-8 BOM. Re-save it without BOM and retry. "
                f"Use `sp-teams result-template --request-id {request_id}` for a canonical payload."
            )
        try:
            raw_payload: WorkerTaskResult | dict[str, Any] | str = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Result file is not valid JSON: {exc}") from exc
    else:
        raw_payload = payload

    if isinstance(raw_payload, WorkerTaskResult):
        normalized = raw_payload
        raw_dict = {
            "task_id": raw_payload.task_id,
            "status": raw_payload.status,
        }
    elif isinstance(raw_payload, dict):
        raw_dict = raw_payload
        normalized = normalize_worker_task_result_payload(raw_payload)
    else:
        raise TypeError("worker result payload must be a WorkerTaskResult, dict, or JSON text")

    missing_fields: list[str] = []
    if not str(raw_dict.get("task_id") or raw_dict.get("taskId") or "").strip():
        missing_fields.append("task_id")
    if not str(
        raw_dict.get("status") or raw_dict.get("reported_status") or raw_dict.get("result_status") or ""
    ).strip():
        missing_fields.append("status")
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(
            f"Result file is missing required fields: {missing}. "
            f"Use `sp-teams result-template --request-id {request_id}` or `sp-teams submit-result --print-schema`."
        )

    packet = load_request_packet(project_root, request_id)
    if normalized.task_id != packet.task_id:
        raise ValueError(
            f"Result task_id {normalized.task_id!r} does not match dispatched packet task_id {packet.task_id!r}. "
            f"Use `sp-teams result-template --request-id {request_id}`."
        )
    if normalized.status == "pending":
        raise ValueError(
            "Pending result templates cannot be submitted. Replace the canonical placeholder "
            "with a real success, blocked, or failed result first."
        )

    try:
        return validate_worker_task_result(normalized, packet)
    except PacketValidationError as exc:
        raise ValueError(
            f"{exc}. Use `sp-teams result-template --request-id {request_id}` or `sp-teams submit-result --print-schema`."
        ) from exc
