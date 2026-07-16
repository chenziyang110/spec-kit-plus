"""Compact, progressively disclosed contracts for agent-facing CLI use.

This module intentionally has no Typer or Rich dependency.  Command adapters may
render its JSON-serializable payloads without importing the main CLI module.
"""

from __future__ import annotations

from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


AGENT_PROTOCOL_VERSION = "1.0"
SCHEMA_VERSIONS: dict[str, int] = {
    "agent-capability": 1,
    "agent-envelope": 1,
    "workflow-blocker": 1,
    "workflow-state": 1,
}

_SUCCESS_STATUSES = frozenset({"ok", "warn", "repaired"})
_BLOCKED_STATUSES = frozenset({"blocked", "repairable-block"})
_USAGE_STATUSES = frozenset({"invalid", "usage-error"})
_ERROR_STATUSES = frozenset({"error"})
_ENVELOPE_STATUSES = (
    _SUCCESS_STATUSES | _BLOCKED_STATUSES | _USAGE_STATUSES | _ERROR_STATUSES
)


class AgentApiError(ValueError):
    """Raised when an agent asks for an unknown or malformed API record."""


def envelope(
    status: str,
    summary: str,
    *,
    data: Mapping[str, Any] | None = None,
    items: list[Mapping[str, Any]] | None = None,
    blockers: list[Mapping[str, Any]] | None = None,
    show_argv: list[str] | None = None,
    next_argv: list[str] | None = None,
) -> dict[str, Any]:
    """Return the one compact JSON envelope shared by agent-facing commands."""

    normalized_status = str(status or "").strip().lower()
    if normalized_status not in _ENVELOPE_STATUSES:
        raise AgentApiError(f"unsupported agent status '{status}'")
    normalized_summary = str(summary or "").strip()
    if not normalized_summary:
        raise AgentApiError("summary is required")
    return {
        "status": normalized_status,
        "summary": normalized_summary,
        "data": dict(data or {}),
        "items": [dict(item) for item in (items or [])],
        "blockers": [dict(blocker) for blocker in (blockers or [])],
        "show_argv": list(show_argv or []),
        "next_argv": list(next_argv or []),
    }


def classify_exit(status_or_payload: str | Mapping[str, Any]) -> int:
    """Map the stable envelope status taxonomy to a process exit code.

    ``0`` means the command completed, ``10`` is a resumable business block,
    ``2`` is invalid agent usage, and ``1`` is an execution failure.
    """

    raw_status = (
        status_or_payload.get("status")
        if isinstance(status_or_payload, Mapping)
        else status_or_payload
    )
    status = str(raw_status or "").strip().lower()
    if status in _SUCCESS_STATUSES:
        return 0
    if status in _BLOCKED_STATUSES:
        return 10
    if status in _USAGE_STATUSES:
        return 2
    if status in _ERROR_STATUSES:
        return 1
    raise AgentApiError(f"unsupported agent status '{raw_status}'")


def _object_schema(
    schema_id: str,
    *,
    properties: Mapping[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"specify://schemas/{schema_id}/v1",
        "type": "object",
        "additionalProperties": False,
        "required": list(required or []),
        "properties": dict(properties),
    }


_STRING = {"type": "string", "minLength": 1}
_PATH = {"type": "string", "minLength": 1}
_REVISION = {"type": "integer", "minimum": 0}


def _load_workflow_blocker_schema() -> dict[str, Any]:
    candidates = (
        Path(__file__).resolve().parents[2]
        / "templates"
        / "workflow-blocker-schema.json",
        Path(__file__).resolve().parent
        / "core_pack"
        / "templates"
        / "workflow-blocker-schema.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
    raise RuntimeError("packaged workflow blocker schema is missing")


_SCHEMAS: dict[str, dict[str, Any]] = {
    "agent-handshake-input": _object_schema(
        "agent-handshake-input",
        properties={
            "require": {
                "type": "array",
                "items": _STRING,
                "uniqueItems": True,
            }
        },
    ),
    "capability-list-input": _object_schema(
        "capability-list-input",
        properties={
            "cursor": {"type": "integer", "minimum": 0, "default": 0},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 200,
                "default": 20,
            },
        },
    ),
    "capability-show-input": _object_schema(
        "capability-show-input",
        properties={"capability_id": _STRING},
        required=["capability_id"],
    ),
    "schema-show-input": _object_schema(
        "schema-show-input",
        properties={"schema_id": _STRING},
        required=["schema_id"],
    ),
    "command-catalog-list-input": _object_schema(
        "command-catalog-list-input",
        properties={
            "cursor": {"type": "integer", "minimum": 0, "default": 0},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 200,
                "default": 20,
            },
            "query": {"type": "string", "default": ""},
        },
    ),
    "command-catalog-show-input": _object_schema(
        "command-catalog-show-input",
        properties={"command_id": _STRING},
        required=["command_id"],
    ),
    "workflow-show-input": _object_schema(
        "workflow-show-input",
        properties={"feature_dir": _PATH},
        required=["feature_dir"],
    ),
    "workflow-enter-input": _object_schema(
        "workflow-enter-input",
        properties={
            "feature_dir": _PATH,
            "command": {"enum": ["discussion", "specify"], "default": "specify"},
            "expected_revision": _REVISION,
            "summary": {"type": "string"},
        },
        required=["feature_dir", "expected_revision"],
    ),
    "workflow-transition-input": _object_schema(
        "workflow-transition-input",
        properties={
            "feature_dir": _PATH,
            "to": {
                "enum": [
                    "specify",
                    "plan",
                    "tasks",
                    "implement",
                    "accept",
                ]
            },
            "expected_revision": _REVISION,
            "summary": {"type": "string"},
            "resolution_evidence": {
                "type": "array",
                "items": _STRING,
            },
        },
        required=["feature_dir", "to", "expected_revision"],
    ),
    "workflow-next-input": _object_schema(
        "workflow-next-input",
        properties={"feature_dir": _PATH},
        required=["feature_dir"],
    ),
    "workflow-block-input": _object_schema(
        "workflow-block-input",
        properties={
            "feature_dir": _PATH,
            "expected_revision": _REVISION,
            "category": _STRING,
            "owner": {"enum": ["agent", "user", "maintainer", "external-system"]},
            "cause": _STRING,
            "evidence": {"type": "array", "minItems": 1, "items": _STRING},
            "attempted_recovery": {"type": "array", "items": {"type": "object"}},
            "affected_scope": {"type": "array", "minItems": 1, "items": _STRING},
            "exact_next_action": _STRING,
            "unblock_criteria": _STRING,
            "resume_argv": {"type": "array", "minItems": 1, "items": _STRING},
            "human_action": {"type": ["object", "null"]},
            "human_action_required": {"type": ["boolean", "null"]},
        },
        required=[
            "feature_dir",
            "expected_revision",
            "category",
            "owner",
            "cause",
            "evidence",
            "attempted_recovery",
            "affected_scope",
            "exact_next_action",
            "unblock_criteria",
            "resume_argv",
        ],
    ),
    "workflow-closeout-input": _object_schema(
        "workflow-closeout-input",
        properties={
            "feature_dir": _PATH,
            "expected_revision": _REVISION,
            "summary": {"type": "string"},
        },
        required=["feature_dir", "expected_revision"],
    ),
    "learning-start-input": _object_schema(
        "learning-start-input",
        properties={"command": _STRING},
        required=["command"],
    ),
    "workflow-blocker": _load_workflow_blocker_schema(),
}

_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "id": "agent.handshake",
        "summary": "Negotiate the compact Agent API and its schema versions.",
        "input_schema": "agent-handshake-input",
        "side_effect": "none",
        "command": ["specify", "api", "handshake"],
    },
    {
        "id": "agent.capabilities.list",
        "summary": "List compact capability summaries with cursor pagination.",
        "input_schema": "capability-list-input",
        "side_effect": "none",
        "command": ["specify", "api", "list"],
    },
    {
        "id": "agent.capabilities.show",
        "summary": "Expand one selected capability record.",
        "input_schema": "capability-show-input",
        "side_effect": "none",
        "command": ["specify", "api", "show"],
    },
    {
        "id": "agent.schemas.show",
        "summary": "Expand one selected JSON input schema.",
        "input_schema": "schema-show-input",
        "side_effect": "none",
        "command": ["specify", "api", "schema"],
    },
    {
        "id": "agent.commands.list",
        "summary": "List every installed CLI operation as compact summary records.",
        "input_schema": "command-catalog-list-input",
        "side_effect": "none",
        "command": ["specify", "api", "commands"],
    },
    {
        "id": "agent.commands.show",
        "summary": "Expand parameters and machine-output metadata for one CLI operation.",
        "input_schema": "command-catalog-show-input",
        "side_effect": "none",
        "command": ["specify", "api", "command"],
    },
    {
        "id": "workflow.show",
        "summary": "Read the compact current workflow state.",
        "input_schema": "workflow-show-input",
        "side_effect": "none",
        "command": ["specify", "workflow", "show"],
    },
    {
        "id": "workflow.enter",
        "summary": "Create a guarded workflow at discussion or specify.",
        "input_schema": "workflow-enter-input",
        "side_effect": "writes-workflow-state",
        "command": ["specify", "workflow", "enter"],
    },
    {
        "id": "workflow.transition",
        "summary": "Advance exactly one required workflow stage.",
        "input_schema": "workflow-transition-input",
        "side_effect": "writes-workflow-state",
        "command": ["specify", "workflow", "transition"],
    },
    {
        "id": "workflow.next",
        "summary": "Resolve the next legal stage and exact transition argv.",
        "input_schema": "workflow-next-input",
        "side_effect": "none",
        "command": ["specify", "workflow", "next"],
    },
    {
        "id": "workflow.block",
        "summary": "Record a resumable blocker and novice human action guide.",
        "input_schema": "workflow-block-input",
        "side_effect": "writes-workflow-state",
        "command": ["specify", "workflow", "block"],
    },
    {
        "id": "workflow.closeout",
        "summary": "Complete an accepted workflow with a revision guard.",
        "input_schema": "workflow-closeout-input",
        "side_effect": "writes-workflow-state",
        "command": ["specify", "workflow", "closeout"],
    },
    {
        "id": "learning.start",
        "summary": "Read compact Learning context relevant to one workflow command.",
        "input_schema": "learning-start-input",
        "side_effect": "none",
        "command": ["specify", "learning", "start"],
    },
)

CAPABILITY_IDS = tuple(record["id"] for record in _CAPABILITIES)
_CAPABILITY_BY_ID = {record["id"]: record for record in _CAPABILITIES}
_SCHEMA_OWNER = {record["input_schema"]: record["id"] for record in _CAPABILITIES}


def _current_version() -> str:
    source_pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if source_pyproject.is_file():
        try:
            import tomllib

            payload = tomllib.loads(source_pyproject.read_text(encoding="utf-8"))
            version = str(payload.get("project", {}).get("version") or "").strip()
            if version:
                return version
        except (OSError, ValueError):
            pass
    try:
        return importlib.metadata.version("specify-cli")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def capabilities_handshake(
    *,
    version: str | None = None,
    required: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return the minimum information needed to negotiate Agent API use."""

    if isinstance(required, (str, bytes)):
        raise AgentApiError("required capabilities must be a sequence, not a string")
    normalized_required = list(
        dict.fromkeys(str(item).strip() for item in (required or []) if str(item).strip())
    )
    missing = [item for item in normalized_required if item not in CAPABILITY_IDS]

    return envelope(
        "ok" if not missing else "error",
        "Agent API ready." if not missing else "Required Agent API capabilities are missing.",
        data={
            "cli_version": str(version or _current_version()),
            "protocol_version": AGENT_PROTOCOL_VERSION,
            "capability_ids": list(CAPABILITY_IDS),
            "required_capabilities": normalized_required,
            "missing_capabilities": missing,
            "schema_versions": dict(SCHEMA_VERSIONS),
        },
        next_argv=["specify", "api", "list", "--format", "json"],
    )


def list_capabilities(*, cursor: int = 0, limit: int = 20) -> dict[str, Any]:
    """List summary cards; callers expand only selected records with ``show``."""

    if not isinstance(cursor, int) or cursor < 0:
        raise AgentApiError("cursor must be a non-negative integer")
    if not isinstance(limit, int) or limit < 1 or limit > 200:
        raise AgentApiError("limit must be an integer between 1 and 200")
    page = _CAPABILITIES[cursor : cursor + limit]
    items = [
        {
            "id": record["id"],
            "summary": record["summary"],
            "schema_version": SCHEMA_VERSIONS["agent-capability"],
            "show_argv": [
                "specify",
                "api",
                "show",
                record["id"],
                "--format",
                "json",
            ],
        }
        for record in page
    ]
    next_cursor = cursor + len(page)
    next_argv = (
        [
            "specify",
            "api",
            "list",
            "--cursor",
            str(next_cursor),
            "--limit",
            str(limit),
            "--format",
            "json",
        ]
        if next_cursor < len(_CAPABILITIES)
        else []
    )
    return envelope(
        "ok",
        f"Returned {len(items)} of {len(_CAPABILITIES)} capabilities.",
        data={"cursor": cursor, "limit": limit, "total": len(_CAPABILITIES)},
        items=items,
        next_argv=next_argv,
    )


def show_capability(capability_id: str) -> dict[str, Any]:
    """Expand one capability after the caller selected it from ``list``."""

    normalized = str(capability_id or "").strip()
    record = _CAPABILITY_BY_ID.get(normalized)
    if record is None:
        raise AgentApiError(f"unknown capability '{capability_id}'")
    detail = deepcopy(record)
    detail["schema_version"] = SCHEMA_VERSIONS["agent-capability"]
    detail["argv"] = [*record["command"], "--format", "json"]
    return envelope(
        "ok",
        f"Capability {normalized} expanded.",
        data=detail,
        next_argv=[
            "specify",
            "api",
            "schema",
            record["input_schema"],
            "--format",
            "json",
        ],
    )


def capability_schema(schema_id: str) -> dict[str, Any]:
    """Expand one selected schema without dumping the complete schema catalog."""

    normalized = str(schema_id or "").strip()
    schema = _SCHEMAS.get(normalized)
    if schema is None:
        raise AgentApiError(f"unknown schema '{schema_id}'")
    owner = _SCHEMA_OWNER.get(normalized)
    return envelope(
        "ok",
        f"Schema {normalized} expanded.",
        data={"schema_id": normalized, "schema_version": 1, "schema": deepcopy(schema)},
        show_argv=(
            [
                "specify",
                "api",
                "show",
                owner,
                "--format",
                "json",
            ]
            if owner is not None
            else []
        ),
    )


# Readable aliases for adapters that prefer noun-first names.
agent_envelope = envelope
exit_code_for_status = classify_exit


__all__ = [
    "AGENT_PROTOCOL_VERSION",
    "CAPABILITY_IDS",
    "SCHEMA_VERSIONS",
    "AgentApiError",
    "agent_envelope",
    "capabilities_handshake",
    "capability_schema",
    "classify_exit",
    "envelope",
    "exit_code_for_status",
    "list_capabilities",
    "show_capability",
]
