#!/usr/bin/env python3
"""Typed, cross-platform state runtime for ``sp-discussion``."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_VERSION = 2
HANDOFF_VERSION = 4
TERMINAL_STATUSES = {"completed", "abandoned"}
INCOMPLETE_STATUSES = {"active", "blocked", "handoff-ready"}
LIFECYCLE_PHASES = {
    "explore",
    "ground",
    "decide",
    "prepare",
    "review",
    "ready",
    "consumed",
    "closed",
}
FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$")
ROLE_FIELDS = {"role", "scope", "evidence_source", "notes"}
EVIDENCE_FIELDS = {"source_type", "evidence_status", "source", "claim"}
MUST_PRESERVE_FIELDS = {
    "id",
    "type",
    "claim",
    "source",
    "downstream_requirement",
    "blocking_level",
    "owner",
    "latest_resolve_phase",
    "status",
}


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def slugify(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.strip().lower()).strip("-")
    return (slug or "discussion")[:72].rstrip("-")


def discussion_root(project_root: Path) -> Path:
    return project_root.resolve() / ".specify" / "discussions"


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _clean_markdown_value(value: str) -> str:
    cleaned = value.strip()
    if (
        len(cleaned) >= 2
        and cleaned[0] == cleaned[-1]
        and cleaned[0] in {'"', "'", "`"}
    ):
        return cleaned[1:-1].strip()
    return cleaned


def _extract_markdown_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = FIELD_RE.match(raw_line)
        if match:
            fields[match.group(1).strip().lower()] = _clean_markdown_value(
                match.group(2)
            )
    return fields


def _default_turn_packet(slug: str, topic: str) -> dict[str, Any]:
    return {
        "version": 1,
        "discussion_slug": slug,
        "lifecycle_phase": "explore",
        "turn_class": "product_intent",
        "user_goal": topic,
        "current_decision_frame": topic,
        "confirmed_decisions": [],
        "changed_recommendations": [],
        "context_boundary": {"status": "not-started"},
        "verified_fact_refs": [],
        "open_assumptions": [],
        "open_questions": [],
        "current_recommendation": "Shape the goal and context boundary.",
        "allowed_actions": ["discuss", "ground", "checkpoint", "close"],
        "persistence_mode": "frontstage-only",
        "next_gate": "context-boundary",
    }


def _new_state(slug: str, topic: str) -> dict[str, Any]:
    timestamp = now_utc()
    return {
        "version": STATE_VERSION,
        "status_family": "discussion",
        "slug": slug,
        "topic": topic,
        "status": "active",
        "lifecycle_phase": "explore",
        "summary": topic,
        "created_at": timestamp,
        "updated_at": timestamp,
        "closed_at": None,
        "archived_at": None,
        "blocker_reason": None,
        "turn_packet": _default_turn_packet(slug, topic),
        "latest_checkpoint": None,
        "handoff": {
            "review_status": "not-started",
            "quality_gate_status": "draft",
            "review_digest": None,
            "contract_path": None,
            "recommended_consumer": "continue-discussion",
        },
        "consumption": {
            "status": "not_consumed",
            "consumed_at": None,
            "consumer_path": None,
        },
        "next_command": "none",
    }


def _legacy_state(workspace: Path, text: str) -> dict[str, Any]:
    fields = _extract_markdown_fields(text)
    slug = fields.get("slug") or workspace.name
    topic = fields.get("current_topic") or fields.get("summary") or slug
    state = _new_state(slug, topic)
    status = fields.get("status", "active").lower()
    state["status"] = (
        status if status in INCOMPLETE_STATUSES | TERMINAL_STATUSES else "active"
    )
    state["summary"] = fields.get("summary") or topic
    state["updated_at"] = fields.get("updated_at") or state["updated_at"]
    state["closed_at"] = (
        fields.get("closed_at")
        if fields.get("closed_at") not in {None, "none"}
        else None
    )
    state["archived_at"] = (
        fields.get("archived_at")
        if fields.get("archived_at") not in {None, "none"}
        else None
    )
    phase = fields.get("lifecycle_phase") or _legacy_phase(
        fields.get("current_stage", ""), state["status"]
    )
    state["lifecycle_phase"] = phase
    state["turn_packet"]["lifecycle_phase"] = phase
    state["turn_packet"]["current_decision_frame"] = (
        fields.get("current_decision_frame") or state["summary"]
    )
    state["next_command"] = fields.get("next_command") or "none"
    state["handoff"]["review_status"] = (
        fields.get("handoff_review_status") or "not-started"
    )
    state["handoff"]["quality_gate_status"] = (
        fields.get("quality_gate_status") or "draft"
    )
    state["handoff"]["contract_path"] = _none_if_placeholder(
        fields.get("handoff_contract")
        or fields.get("handoff_to_specify_json")
        or fields.get("handoff_to_specify")
    )
    state["consumption"]["status"] = (
        fields.get("handoff_consumption_status") or "not_consumed"
    )
    state["consumption"]["consumed_at"] = _none_if_placeholder(
        fields.get("consumed_at")
    )
    state["consumption"]["consumer_path"] = _none_if_placeholder(
        fields.get("consumed_by_feature_dir")
    )
    return state


def _none_if_placeholder(value: str | None) -> str | None:
    if value is None or value.strip().lower() in {"", "none"} or "[" in value:
        return None
    return value.strip()


def _legacy_phase(stage: str, status: str) -> str:
    if status == "handoff-ready":
        return "ready"
    if status in TERMINAL_STATUSES:
        return "closed"
    mapping = {
        "context-intake": "explore",
        "product-framing": "explore",
        "context-grounding": "ground",
        "question-loop": "decide",
        "technical-options": "decide",
        "readiness-summary": "prepare",
        "ui-interaction-discussion": "decide",
        "handoff-preview": "prepare",
        "handoff-assessment": "prepare",
        "handoff-draft": "prepare",
        "handoff-self-review": "review",
        "handoff-review": "review",
        "handoff-ready": "ready",
    }
    return mapping.get(stage, "explore")


def _render_state_markdown(state: dict[str, Any]) -> str:
    handoff = state["handoff"]
    consumption = state["consumption"]
    packet = state["turn_packet"]
    lines = [
        f"# Discussion State: {state['topic']}",
        "",
        "## Session",
        "",
        "- active_command: sp-discussion",
        "- state_surface: discussion-state",
        f"- status: {state['status']}",
        f"- lifecycle_phase: {state['lifecycle_phase']}",
        f"- slug: {state['slug']}",
        f"- updated_at: {state['updated_at']}",
        f"- closed_at: {state['closed_at'] or 'none'}",
        f"- archived_at: {state['archived_at'] or 'none'}",
        f"- summary: {state['summary']}",
        "",
        "## Decision Context",
        "",
        f"- current_decision_frame: {packet['current_decision_frame']}",
        f"- current_recommendation: {packet['current_recommendation']}",
        f"- next_gate: {packet['next_gate']}",
        f"- blocker_reason: {state['blocker_reason'] or 'none'}",
        "",
        "## Handoff",
        "",
        f"- handoff_review_status: {handoff['review_status']}",
        f"- quality_gate_status: {handoff['quality_gate_status']}",
        f"- handoff_review_digest: {handoff['review_digest'] or 'none'}",
        f"- handoff_contract: {handoff['contract_path'] or 'none'}",
        f"- recommended_consumer: {handoff['recommended_consumer']}",
        "",
        "## Consumption",
        "",
        f"- handoff_consumption_status: {consumption['status']}",
        f"- consumed_at: {consumption['consumed_at'] or 'none'}",
        f"- consumed_by_feature_dir: {consumption['consumer_path'] or 'none'}",
        f"- next_command: {state['next_command']}",
        "",
        "Canonical machine state: `discussion-state.json`.",
        "",
    ]
    return "\n".join(lines)


def _load_state(workspace: Path) -> tuple[dict[str, Any], bool]:
    json_path = workspace / "discussion-state.json"
    if json_path.is_file():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"invalid discussion state: {json_path}")
        handoff = payload.get("handoff")
        if isinstance(handoff, dict) and "contract_path" not in handoff:
            handoff["contract_path"] = handoff.get("json_path") or handoff.get(
                "markdown_path"
            )
        if isinstance(handoff, dict):
            handoff.pop("json_path", None)
            handoff.pop("markdown_path", None)
        return payload, False
    markdown_path = workspace / "discussion-state.md"
    if not markdown_path.is_file():
        raise ValueError(f"discussion state not found: {workspace.name}")
    return _legacy_state(workspace, markdown_path.read_text(encoding="utf-8")), True


def _persist_state(workspace: Path, state: dict[str, Any]) -> None:
    _validate_state(state)
    _atomic_write_json(workspace / "discussion-state.json", state)
    _atomic_write_text(workspace / "discussion-state.md", _render_state_markdown(state))


def _validate_state(state: dict[str, Any]) -> None:
    if (
        state.get("version") != STATE_VERSION
        or state.get("status_family") != "discussion"
    ):
        raise ValueError("unsupported discussion state version")
    if state.get("lifecycle_phase") not in LIFECYCLE_PHASES:
        raise ValueError(
            f"invalid discussion lifecycle phase: {state.get('lifecycle_phase')}"
        )
    if state.get("status") not in INCOMPLETE_STATUSES | TERMINAL_STATUSES:
        raise ValueError(f"invalid discussion status: {state.get('status')}")
    packet = state.get("turn_packet")
    if not isinstance(packet, dict) or packet.get("discussion_slug") != state.get(
        "slug"
    ):
        raise ValueError("discussion turn packet does not match state slug")


def _workspace_candidates(
    project_root: Path, include_archived: bool = True
) -> list[tuple[Path, bool]]:
    root = discussion_root(project_root)
    candidates: list[tuple[Path, bool]] = []
    if root.is_dir():
        candidates.extend(
            (path, False)
            for path in root.iterdir()
            if path.is_dir() and path.name != "archive"
        )
    archive_root = root / "archive"
    if include_archived and archive_root.is_dir():
        candidates.extend(
            (path, True) for path in archive_root.iterdir() if path.is_dir()
        )
    return candidates


def _record(workspace: Path, state: dict[str, Any], archived: bool) -> dict[str, Any]:
    return {
        "slug": state["slug"],
        "workspace": workspace.name,
        "workspace_path": str(workspace.resolve()),
        "status": state["status"],
        "lifecycle_phase": state["lifecycle_phase"],
        "summary": state["summary"],
        "updated_at": state["updated_at"],
        "closed_at": state.get("closed_at"),
        "archived_at": state.get("archived_at"),
        "next_command": state.get("next_command", "none"),
        "handoff_consumption_status": state["consumption"]["status"],
        "consumed_at": state["consumption"].get("consumed_at"),
        "consumed_by_feature_dir": state["consumption"].get("consumer_path"),
        "archived": archived,
    }


def _scan(project_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for workspace, archived in _workspace_candidates(project_root):
        try:
            state, _legacy = _load_state(workspace)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        records.append(_record(workspace, state, archived))
    return sorted(
        records, key=lambda item: (item["updated_at"], item["slug"]), reverse=True
    )


def _write_index(project_root: Path) -> dict[str, Any]:
    root = discussion_root(project_root)
    payload = {
        "version": 2,
        "generated_at": now_utc(),
        "discussions": _scan(project_root),
    }
    _atomic_write_json(root / "index.json", payload)
    return payload


def _find_workspace(
    project_root: Path, slug: str, include_archived: bool = True
) -> tuple[Path, bool]:
    if not slug.strip() or Path(slug).name != slug:
        raise ValueError("a safe discussion slug is required")
    matches: list[tuple[Path, bool]] = []
    for workspace, archived in _workspace_candidates(project_root, include_archived):
        state, _legacy = _load_state(workspace)
        if workspace.name == slug or state["slug"] == slug:
            matches.append((workspace, archived))
    if not matches:
        raise ValueError(f"discussion not found: {slug}")
    if len(matches) > 1:
        raise ValueError(f"discussion slug is ambiguous: {slug}")
    return matches[0]


def initialize_discussion(
    project_root: Path, requested_slug: str, topic: str = ""
) -> dict[str, Any]:
    root = discussion_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    base_slug = slugify(requested_slug or topic)
    slug = base_slug
    suffix = 2
    existing_names = {
        path.name for path, _archived in _workspace_candidates(project_root)
    }
    while slug in existing_names:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    discussion_topic = topic.strip() or requested_slug.strip() or slug
    workspace = root / slug
    workspace.mkdir()
    state = _new_state(slug, discussion_topic)
    _persist_state(workspace, state)
    _atomic_write_text(workspace / "discussion-log.jsonl", "")
    _write_index(project_root)
    return {
        "discussion": _record(workspace, state, False),
        "slug": slug,
        "workspace_path": str(workspace.resolve()),
    }


def list_discussions(project_root: Path, include_all: bool = False) -> dict[str, Any]:
    records = _scan(project_root)
    if not include_all:
        records = [
            record
            for record in records
            if not record["archived"] and record["status"] in INCOMPLETE_STATUSES
        ]
    return {"discussions": records}


def discussion_status(project_root: Path, slug: str) -> dict[str, Any]:
    workspace, archived = _find_workspace(project_root, slug)
    state, _legacy = _load_state(workspace)
    return {
        "discussion": {**_record(workspace, state, archived), **copy.deepcopy(state)}
    }


def _read_events(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / "discussion-log.jsonl"
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid discussion event at line {line_number}") from exc
        if isinstance(event, dict):
            events.append(event)
    return events


def resume_context(project_root: Path, slug: str) -> dict[str, Any]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot be resumed")
    state, _legacy = _load_state(workspace)
    checkpoint = state.get("latest_checkpoint") or {}
    checkpoint_id = checkpoint.get("event_id") if isinstance(checkpoint, dict) else None
    events = _read_events(workspace)
    if checkpoint_id:
        positions = [
            index
            for index, event in enumerate(events)
            if event.get("event_id") == checkpoint_id
        ]
        recent_events = events[positions[-1] + 1 :] if positions else events
    else:
        recent_events = events
    return {
        "discussion": _record(workspace, state, False),
        "turn_packet": copy.deepcopy(state["turn_packet"]),
        "recent_events": recent_events,
        "legacy_state": _legacy,
    }


def checkpoint_discussion(
    project_root: Path, slug: str, changes: dict[str, Any]
) -> dict[str, Any]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot be checkpointed")
    state, _legacy = _load_state(workspace)
    phase = changes.get("lifecycle_phase", state["lifecycle_phase"])
    if phase not in LIFECYCLE_PHASES - {"ready", "consumed", "closed"}:
        raise ValueError(f"invalid checkpoint lifecycle phase: {phase}")
    timestamp = now_utc()
    event_id = uuid.uuid4().hex
    summary = str(changes.get("summary") or state["summary"]).strip()
    packet = state["turn_packet"]
    for key in (
        "confirmed_decisions",
        "changed_recommendations",
        "context_boundary",
        "verified_fact_refs",
        "open_assumptions",
        "open_questions",
        "current_recommendation",
        "allowed_actions",
        "next_gate",
        "current_decision_frame",
    ):
        if key in changes:
            packet[key] = copy.deepcopy(changes[key])
    packet["lifecycle_phase"] = phase
    packet["persistence_mode"] = "durable-checkpoint"
    state.update(
        {"summary": summary, "lifecycle_phase": phase, "updated_at": timestamp}
    )
    state["latest_checkpoint"] = {"event_id": event_id, "timestamp": timestamp}
    event = {
        "version": 1,
        "event_id": event_id,
        "timestamp": timestamp,
        "kind": "durable-checkpoint",
        "lifecycle_phase": phase,
        "summary": summary,
        "confirmed_decisions": copy.deepcopy(packet["confirmed_decisions"]),
        "open_questions": copy.deepcopy(packet["open_questions"]),
    }
    with (workspace / "discussion-log.jsonl").open(
        "a", encoding="utf-8", newline="\n"
    ) as log_file:
        log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    _persist_state(workspace, state)
    _write_index(project_root)
    return {
        "discussion": {**_record(workspace, state, False), **copy.deepcopy(state)},
        "event": event,
    }


def compute_review_digest(payload: dict[str, Any]) -> str:
    protected = copy.deepcopy(payload)
    for field in ("review_digest", "status", "handoff_integrity", "updated_at"):
        protected.pop(field, None)
    protected.pop("quality_gate", None)
    canonical = json.dumps(
        protected, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_handoff(
    project_root: Path, slug: str, handoff_payload: dict[str, Any]
) -> dict[str, Any]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot write a handoff")
    state, _legacy = _load_state(workspace)
    payload = copy.deepcopy(handoff_payload)
    payload.update(
        {
            "version": HANDOFF_VERSION,
            "handoff_kind": "discussion_requirement_contract",
            "entry_source": "sp-discussion",
            "discussion_slug": slug,
            "source_contract": f".specify/discussions/{slug}/handoff-to-specify.json",
        }
    )
    review_digest = compute_review_digest(payload)
    payload["review_digest"] = review_digest
    quality_gate = payload.get("quality_gate")
    if isinstance(quality_gate, dict) and quality_gate.get("status") in {
        "user_confirmed",
        "user-confirmed",
    }:
        quality_gate["confirmed_digest"] = review_digest
    json_path = workspace / "handoff-to-specify.json"
    _atomic_write_json(json_path, payload)
    timestamp = now_utc()
    state.update(
        {"status": "active", "lifecycle_phase": "review", "updated_at": timestamp}
    )
    state["turn_packet"].update(
        {
            "lifecycle_phase": "review",
            "persistence_mode": "lifecycle-transition",
            "allowed_actions": ["review-handoff", "request-changes", "mark-ready"],
            "next_gate": "handoff-validation",
        }
    )
    state["handoff"].update(
        {
            "review_status": "user-confirmed"
            if isinstance(quality_gate, dict)
            and quality_gate.get("status") in {"user_confirmed", "user-confirmed"}
            else "draft",
            "quality_gate_status": quality_gate.get("status", "draft")
            if isinstance(quality_gate, dict)
            else "draft",
            "review_digest": review_digest,
            "contract_path": payload["source_contract"],
            "recommended_consumer": payload.get(
                "recommended_consumer", "continue-discussion"
            ),
        }
    )
    _persist_state(workspace, state)
    _write_index(project_root)
    return {
        "discussion": {**_record(workspace, state, False), **copy.deepcopy(state)},
        "review_digest": review_digest,
        "json_path": str(json_path.resolve()),
    }


def _validate_object_list(
    payload: Any,
    required_fields: set[str],
    label: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(payload, list):
        errors.append(_error(f"invalid_{label}", f"{label} must be a list"))
        return
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            errors.append(
                _error(f"invalid_{label}_item", f"{label}[{index}] must be an object")
            )
            continue
        missing = sorted(required_fields - set(item))
        if missing:
            errors.append(
                _error(
                    f"incomplete_{label}_item",
                    f"{label}[{index}] missing {', '.join(missing)}",
                )
            )


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _handoff_paths(project_root: Path, slug: str) -> tuple[Path, Path]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion has no active handoff")
    return workspace, workspace / "handoff-to-specify.json"


def validate_handoff(project_root: Path, slug: str) -> dict[str, Any]:
    workspace, json_path = _handoff_paths(project_root, slug)
    errors: list[dict[str, str]] = []
    if not json_path.is_file():
        errors.append(_error("missing_handoff_json", "handoff JSON is required"))
    if errors:
        return _validation_payload(workspace, errors, None)
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append(_error("invalid_handoff_json", "handoff JSON is not valid JSON"))
        return _validation_payload(workspace, errors, None)
    if not isinstance(payload, dict):
        errors.append(
            _error("invalid_handoff_payload", "handoff JSON must be an object")
        )
        return _validation_payload(workspace, errors, None)
    _validate_handoff_fields(payload, slug, errors)
    return _validation_payload(workspace, errors, payload)


def _validate_handoff_fields(
    payload: dict[str, Any],
    slug: str,
    errors: list[dict[str, str]],
) -> None:
    expected_values = {
        "version": HANDOFF_VERSION,
        "handoff_kind": "discussion_requirement_contract",
        "entry_source": "sp-discussion",
        "discussion_slug": slug,
        "source_contract": f".specify/discussions/{slug}/handoff-to-specify.json",
        "coverage_status": "complete",
        "planning_gate_status": "ready",
        "hard_unknown_count": 0,
        "open_conflict_count": 0,
    }
    for field, expected in expected_values.items():
        if payload.get(field) != expected:
            errors.append(_error(f"invalid_{field}", f"{field} must be {expected!r}"))
    if not str(payload.get("handoff_goal") or "").strip():
        errors.append(_error("missing_handoff_goal", "handoff_goal is required"))
    _validate_boundary(payload.get("context_boundary"), errors)
    _validate_object_list(
        payload.get("source_evidence"), EVIDENCE_FIELDS, "source_evidence", errors
    )
    _validate_object_list(
        payload.get("must_preserve"), MUST_PRESERVE_FIELDS, "must_preserve", errors
    )
    if not payload.get("must_preserve"):
        errors.append(
            _error("empty_must_preserve", "Must-Preserve coverage is required")
        )
    downstream = payload.get("downstream_instructions")
    if not isinstance(downstream, dict) or "planning_constraints" not in downstream:
        errors.append(
            _error("missing_planning_constraints", "planning_constraints are required")
        )
    elif "recommended_sequence" in downstream:
        errors.append(
            _error("legacy_recommended_sequence", "recommended_sequence is not allowed")
        )
    _validate_consumers(payload, errors)
    _validate_review_digest(payload, errors)


def _validate_boundary(boundary: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(boundary, dict) or boundary.get("status") != "locked":
        errors.append(
            _error("unlocked_context_boundary", "context boundary must be locked")
        )
        return
    _validate_object_list(
        boundary.get("current_project_roles"),
        ROLE_FIELDS,
        "current_project_roles",
        errors,
    )
    if boundary.get("target_project_root"):
        _validate_object_list(
            boundary.get("target_project_roles"),
            ROLE_FIELDS,
            "target_project_roles",
            errors,
        )


def _validate_consumers(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    eligibility = payload.get("consumer_eligibility")
    if not isinstance(eligibility, dict):
        errors.append(
            _error(
                "invalid_consumer_eligibility", "consumer_eligibility must be an object"
            )
        )
        return
    ready = [
        name
        for name in ("sp-specify", "sp-quick")
        if isinstance(eligibility.get(name), dict)
        and eligibility[name].get("status") == "ready"
    ]
    if not ready:
        errors.append(
            _error("no_ready_consumer", "at least one consumer must be ready")
        )
    if payload.get("recommended_consumer") not in ready:
        errors.append(
            _error("invalid_recommended_consumer", "recommended_consumer must be ready")
        )


def _validate_review_digest(
    payload: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    review_digest = str(payload.get("review_digest") or "")
    computed_digest = compute_review_digest(payload)
    if not review_digest or review_digest != computed_digest:
        errors.append(
            _error(
                "review_digest_mismatch",
                "review_digest does not match protected content",
            )
        )
    quality_gate = payload.get("quality_gate")
    if not isinstance(quality_gate, dict) or quality_gate.get("status") not in {
        "user_confirmed",
        "user-confirmed",
    }:
        errors.append(
            _error(
                "handoff_not_user_confirmed",
                "quality gate must record user confirmation",
            )
        )
        return
    if not quality_gate.get("self_reviewed_at") or not quality_gate.get(
        "user_confirmed_at"
    ):
        errors.append(
            _error(
                "incomplete_quality_gate",
                "self-review and user confirmation evidence are required",
            )
        )
    if quality_gate.get("confirmed_digest") != review_digest:
        errors.append(
            _error(
                "review_digest_confirmation_mismatch",
                "confirmation does not match review_digest",
            )
        )


def _validation_payload(
    workspace: Path,
    errors: list[dict[str, str]],
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "valid": not errors,
        "workspace_path": str(workspace.resolve()),
        "review_digest": payload.get("review_digest") if payload else None,
        "error_codes": [error["code"] for error in errors],
        "errors": errors,
    }


def mark_ready(project_root: Path, slug: str) -> dict[str, Any]:
    validation = validate_handoff(project_root, slug)
    if not validation["valid"]:
        codes = ", ".join(validation["error_codes"])
        raise ValueError(f"discussion handoff is not ready: {codes}")
    workspace, json_path = _handoff_paths(project_root, slug)
    state, _legacy = _load_state(workspace)
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    handoff["status"] = "handoff-ready"
    handoff["handoff_integrity"] = "validated"
    _atomic_write_json(json_path, handoff)
    timestamp = now_utc()
    state.update(
        {"status": "handoff-ready", "lifecycle_phase": "ready", "updated_at": timestamp}
    )
    state["turn_packet"].update(
        {
            "lifecycle_phase": "ready",
            "persistence_mode": "lifecycle-transition",
            "allowed_actions": ["consume", "request-changes", "close"],
            "next_gate": "downstream-consumption",
        }
    )
    state["handoff"] = {
        "review_status": "user-confirmed",
        "quality_gate_status": "user_confirmed",
        "review_digest": validation["review_digest"],
        "contract_path": f".specify/discussions/{slug}/handoff-to-specify.json",
        "recommended_consumer": handoff["recommended_consumer"],
    }
    state["next_command"] = handoff["recommended_consumer"]
    _persist_state(workspace, state)
    _write_index(project_root)
    return {
        "discussion": {**_record(workspace, state, False), **copy.deepcopy(state)},
        "validation": validation,
    }


def _safe_consumer_path(project_root: Path, raw_path: str) -> Path:
    root = project_root.resolve()
    candidate = Path(raw_path)
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    )
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("consumer path must stay inside the project root") from exc
    return resolved


def _consumer_evidence_path(consumer_path: Path) -> Path:
    if consumer_path.is_file():
        return consumer_path
    candidates = [
        consumer_path / "brainstorming" / "handoff-to-specify.json",
        consumer_path / "handoff-to-specify.json",
        consumer_path / "STATUS.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError("consumer evidence is missing")


def _validate_consumer_evidence(
    project_root: Path,
    slug: str,
    review_digest: str,
    evidence_path: Path,
) -> None:
    expected_contract = f".specify/discussions/{slug}/handoff-to-specify.json"
    if evidence_path.suffix.lower() == ".md":
        text = evidence_path.read_text(encoding="utf-8")
        scalar_fields = {
            match.group("key"): match.group("value").strip().strip("'\"")
            for match in re.finditer(
                r"(?m)^\s*(?P<key>[a-zA-Z0-9_]+):\s*(?P<value>[^\r\n#]+)",
                text,
            )
        }
        if (
            scalar_fields.get("source_discussion_slug") != slug
            or scalar_fields.get("review_digest") != review_digest
        ):
            raise ValueError(
                "consumer evidence does not reference the reviewed discussion"
            )
        if scalar_fields.get("source_contract") != expected_contract:
            raise ValueError(
                "consumer evidence does not bind the source contract"
            )
        return
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("consumer evidence is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("consumer evidence must be an object")
    expected = {
        "discussion_slug": slug,
        "source_contract": expected_contract,
        "review_digest": review_digest,
    }
    mismatched = [
        field for field, value in expected.items() if payload.get(field) != value
    ]
    if mismatched:
        raise ValueError(
            f"consumer evidence does not reference the reviewed discussion: {', '.join(mismatched)}"
        )


def mark_consumed(
    project_root: Path, slug: str, consumer_path_value: str
) -> dict[str, Any]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot be consumed")
    state, _legacy = _load_state(workspace)
    if state["status"] != "handoff-ready" or state["lifecycle_phase"] != "ready":
        raise ValueError("only a validated handoff-ready discussion can be consumed")
    review_digest = str(state["handoff"].get("review_digest") or "")
    if not review_digest:
        raise ValueError("ready discussion is missing a reviewed digest")
    consumer_path = _safe_consumer_path(project_root, consumer_path_value)
    evidence_path = _consumer_evidence_path(consumer_path)
    _validate_consumer_evidence(project_root, slug, review_digest, evidence_path)
    timestamp = now_utc()
    state.update(
        {
            "status": "completed",
            "lifecycle_phase": "consumed",
            "updated_at": timestamp,
            "closed_at": timestamp,
            "next_command": "none",
        }
    )
    state["turn_packet"].update(
        {
            "lifecycle_phase": "consumed",
            "persistence_mode": "lifecycle-transition",
            "allowed_actions": ["archive"],
            "next_gate": "archive",
        }
    )
    relative_consumer = (
        consumer_path.resolve().relative_to(project_root.resolve()).as_posix()
    )
    state["consumption"] = {
        "status": "consumed",
        "consumed_at": timestamp,
        "consumer_path": relative_consumer,
        "evidence_path": evidence_path.resolve()
        .relative_to(project_root.resolve())
        .as_posix(),
        "review_digest": review_digest,
    }
    _persist_state(workspace, state)
    _write_index(project_root)
    return {"discussion": {**_record(workspace, state, False), **copy.deepcopy(state)}}


def close_discussion(
    project_root: Path, slug: str, status_value: str
) -> dict[str, Any]:
    if status_value not in TERMINAL_STATUSES:
        raise ValueError("close requires status completed or abandoned")
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot be closed")
    state, _legacy = _load_state(workspace)
    timestamp = now_utc()
    state.update(
        {
            "status": status_value,
            "lifecycle_phase": "closed",
            "updated_at": timestamp,
            "closed_at": timestamp,
            "next_command": "none",
        }
    )
    state["turn_packet"].update(
        {
            "lifecycle_phase": "closed",
            "persistence_mode": "lifecycle-transition",
            "allowed_actions": ["archive"],
            "next_gate": "archive",
        }
    )
    _persist_state(workspace, state)
    _write_index(project_root)
    return {"discussion": {**_record(workspace, state, False), **copy.deepcopy(state)}}


def archive_discussion(project_root: Path, slug: str) -> dict[str, Any]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("discussion is already archived")
    state, _legacy = _load_state(workspace)
    if state["status"] not in TERMINAL_STATUSES or not state.get("closed_at"):
        raise ValueError(
            "only closed completed or abandoned discussions can be archived"
        )
    archive_root = discussion_root(project_root) / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / workspace.name
    if destination.exists():
        raise ValueError(f"archive destination already exists: {destination.name}")
    shutil.move(str(workspace), str(destination))
    state["archived_at"] = now_utc()
    state["updated_at"] = state["archived_at"]
    _persist_state(destination, state)
    _write_index(project_root)
    return {"discussion": {**_record(destination, state, True), **copy.deepcopy(state)}}


def rebuild_index(project_root: Path) -> dict[str, Any]:
    return _write_index(project_root)


def main() -> int:
    project_root = Path(sys.argv[1]).resolve()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "list").strip().lower()
    slug = (sys.argv[3] if len(sys.argv) > 3 else "").strip()
    value = (sys.argv[4] if len(sys.argv) > 4 else "").strip()
    include_all = (
        sys.argv[5] if len(sys.argv) > 5 else "false"
    ).strip().lower() == "true"
    if mode == "init":
        result = initialize_discussion(project_root, slug, value)
    elif mode == "list":
        result = list_discussions(project_root, include_all)
    elif mode == "status":
        result = discussion_status(project_root, slug)
    elif mode == "resume-context":
        result = resume_context(project_root, slug)
    elif mode == "checkpoint":
        changes = json.loads(value or "{}")
        if not isinstance(changes, dict):
            raise ValueError("checkpoint payload must be an object")
        result = checkpoint_discussion(project_root, slug, changes)
    elif mode == "write-handoff":
        input_path = _safe_consumer_path(project_root, value)
        if not input_path.is_file():
            raise ValueError("handoff input must be an existing JSON file")
        try:
            handoff_payload = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("handoff input is not valid JSON") from exc
        if not isinstance(handoff_payload, dict):
            raise ValueError("handoff input must be a JSON object")
        result = write_handoff(project_root, slug, handoff_payload)
    elif mode == "validate-handoff":
        result = validate_handoff(project_root, slug)
    elif mode == "mark-ready":
        result = mark_ready(project_root, slug)
    elif mode == "mark-consumed":
        result = mark_consumed(project_root, slug, value)
    elif mode == "close":
        result = close_discussion(project_root, slug, value.lower())
    elif mode == "archive":
        result = archive_discussion(project_root, slug)
    elif mode == "rebuild-index":
        result = rebuild_index(project_root)
    else:
        raise ValueError(f"unknown mode: {mode}")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
