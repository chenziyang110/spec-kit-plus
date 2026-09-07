#!/usr/bin/env python3
"""Typed, cross-platform state runtime for ``sp-discussion``."""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt
else:
    import fcntl


STATE_VERSION = 3
HANDOFF_VERSION = 5
TERMINAL_STATUSES = {"completed", "abandoned"}
INCOMPLETE_STATUSES = {"active", "blocked", "handoff-ready"}
HANDOFF_VALIDATION_MODES = {"draft", "ready"}
TOPIC_ROUTES = {"continue_current", "branch_new", "link_existing", "defer"}
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
SOURCE_EVIDENCE_STATUSES = {
    "assumption",
    "confirmed",
    "conflict",
    "inferred",
    "missing",
    "proven",
    "stale-advisory",
    "verified",
}
SOURCE_MATERIAL_FIELDS = {
    "id",
    "material_type",
    "locator",
    "summary",
    "inspection_status",
    "claims",
    "coverage_gaps",
    "sensitivity",
}
SOURCE_MATERIAL_STATUSES = {
    "conflict",
    "inspected",
    "partial",
    "pending",
    "stale",
    "unavailable",
}
SOURCE_MATERIAL_SENSITIVITIES = {"restricted", "safe", "sanitized"}
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
MUTATION_MODES = {
    "init",
    "checkpoint",
    "write-handoff-json",
    "confirm-handoff",
    "mark-ready",
    "mark-consumed",
    "close",
    "archive",
    "rebuild-index",
}
CHECKPOINT_ENUM_FIELDS = {
    "truth_pass_status": {"not-needed", "needed", "in-progress", "complete", "blocked"},
    "discussion_compass_status": {"current", "stale", "missing"},
    "ui_discussion_status": {
        "not_applicable",
        "offered",
        "accepted",
        "skipped",
        "completed",
        "deferred",
    },
}
ADVICE_CONFIDENCE_LEVELS = {"high", "medium", "low", "blocked", "none"}
CHECKPOINT_STRING_LIST_FIELDS = {
    "confirmed_decisions",
    "changed_recommendations",
    "next_discussion_paths",
    "allowed_actions",
    "artifact_refs",
    "verified_project_facts",
    "evidence_checked",
}
CHECKPOINT_ARRAY_FIELDS = (
    "blocking_unknowns",
    "soft_unknowns",
    "conflicts",
    "open_assumptions",
    "open_questions",
    "verified_fact_refs",
)
CHECKPOINT_OBJECT_FIELDS = (
    "context_boundary",
    "implementation_target",
    "downstream_instructions",
    "discussion_decision_digest",
    "design_context",
)
LOCK_RETRY_SECONDS = 0.05
LOCK_TIMEOUT_SECONDS = 30.0


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


def _discussion_mutation_lock_path(project_root: Path) -> Path:
    return (
        project_root.resolve()
        / ".specify"
        / "runtime"
        / "discussion"
        / "mutation.lock"
    )


@contextmanager
def _discussion_mutation_lock(project_root: Path):
    lock_path = _discussion_mutation_lock_path(project_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
            os.fsync(lock_file.fileno())
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                lock_file.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"timed out acquiring discussion mutation lock: {lock_path}"
                    )
                time.sleep(LOCK_RETRY_SECONDS)
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"timed out acquiring discussion mutation lock: {lock_path}"
                    ) from exc
                time.sleep(LOCK_RETRY_SECONDS)
        try:
            yield
        finally:
            lock_file.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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


def _compact_list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    rendered: list[str] = []
    for item in value:
        if isinstance(item, dict):
            label = item.get("id") or item.get("claim") or item.get("topic") or item.get("source") or item.get("summary")
            rendered.append(str(label or "[object]").strip())
        else:
            rendered.append(str(item).strip())
    return "; ".join(item for item in rendered if item) or "none"


def _source_materials_summary(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    summaries: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        material_id = str(item.get("id") or "MAT-???")
        status = str(item.get("inspection_status") or "unknown")
        if item.get("sensitivity") == "restricted":
            summaries.append(f"{material_id}({status}) [restricted]")
            continue
        summary = str(item.get("summary") or item.get("locator") or "").strip()
        suffix = f": {summary[:120]}" if summary else ""
        summaries.append(f"{material_id}({status}){suffix}")
    return "; ".join(summaries) or "none"


def _requirements_summary(requirements: Any) -> dict[str, str]:
    if not isinstance(requirements, dict):
        return {
            "target": "none",
            "scope_in": "none",
            "success": "none",
            "optimal": "none",
        }
    scope = requirements.get("scope") if isinstance(requirements.get("scope"), dict) else {}
    return {
        "target": str(requirements.get("target_need") or "none"),
        "scope_in": _compact_list(scope.get("in")),
        "success": _compact_list(requirements.get("success_criteria")),
        "optimal": _compact_list(requirements.get("optimal_solution_approach")),
    }


def _default_turn_packet(slug: str, topic: str) -> dict[str, Any]:
    return {
        "version": 2,
        "discussion_slug": slug,
        "lifecycle_phase": "explore",
        "turn_class": "product_intent",
        "user_goal": topic,
        "current_decision_frame": topic,
        "requirements_snapshot": {
            "target_need": topic,
            "actors": [],
            "scenarios": [],
            "constraints": [],
            "success_criteria": [],
            "design_direction": [],
            "optimal_solution_approach": [],
            "non_goals": [],
            "scope": {"in": [], "out": [], "deferred": []},
        },
        "implementation_target": {
            "actual_project": None,
            "target_root": None,
            "target_paths": [],
            "required_target_paths_to_verify": [],
        },
        "source_evidence": [],
        "source_materials": [],
        "blocking_unknowns": [],
        "soft_unknowns": [],
        "conflicts": [],
        "downstream_instructions": {
            "settled_decisions": [],
            "preserved_assumptions": [],
            "conflicts_requiring_return": [],
            "capability_map": [],
            "dependencies": [],
            "planning_constraints": [],
            "deferred_scope": [],
            "reopen_conditions": [],
        },
        "discussion_decision_digest": {
            "locked_direction": [],
            "rejected_alternatives": [],
            "accepted_tradeoffs": [],
            "experience_commitments": [],
            "design_system_requirements": [],
            "design_system_status": "not-applicable",
            "design_risk_level": "none",
            "review_criteria_carried_forward": [],
            "must_not_dilute": [],
        },
        "must_preserve": [],
        "truth_pass_status": "not-needed",
        "verified_project_facts": [],
        "evidence_checked": [],
        "advice_confidence": "none",
        "discussion_compass_status": "missing",
        "next_discussion_paths": [],
        "ui_discussion_status": "not_applicable",
        "design_context": {"ui_involved": False},
        "artifact_refs": [],
        "confirmed_decisions": [],
        "changed_recommendations": [],
        "context_boundary": {
            "status": "not-started",
            "current_project_root": None,
            "current_project_roles": [],
            "target_project_root": None,
            "target_project_roles": [],
            "reference_sources": [],
            "external_systems": [],
            "boundary_blockers": [],
            "path_status": "unknown",
            "boundary_confidence": "unknown",
        },
        "verified_fact_refs": [],
        "open_assumptions": [],
        "open_questions": [],
        "current_recommendation": "Shape the goal and context boundary.",
        "allowed_actions": ["discuss", "ground", "checkpoint", "close"],
        "persistence_mode": "frontstage-only",
        "next_gate": "context-boundary",
        "topic_ownership": {
            "owner_slug": slug,
            "anchor": slug,
            "owned_scope": [topic],
            "routed_topics": [],
        },
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
    requirements = _requirements_summary(packet.get("requirements_snapshot"))
    checkpoint = state.get("latest_checkpoint") if isinstance(state.get("latest_checkpoint"), dict) else {}
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
        f"- confirmed_decisions: {_compact_list(packet.get('confirmed_decisions'))}",
        f"- open_questions: {_compact_list(packet.get('open_questions'))}",
        f"- blocking_unknown_count: {_derived_hard_unknown_count(packet)}",
        f"- soft_unknown_count: {len(packet.get('soft_unknowns') or [])}",
        f"- open_conflict_count: {_derived_open_conflict_count(packet)}",
        "",
        "## Requirements Snapshot",
        "",
        f"- target_need: {requirements['target']}",
        f"- scope_in: {requirements['scope_in']}",
        f"- success_criteria: {requirements['success']}",
        f"- optimal_solution_approach: {requirements['optimal']}",
        "",
        "## Grounding",
        "",
        f"- truth_pass_status: {packet.get('truth_pass_status') or 'none'}",
        f"- advice_confidence: {packet.get('advice_confidence') or 'none'}",
        f"- evidence_checked: {_compact_list(packet.get('evidence_checked'))}",
        f"- source_evidence: {_compact_list(packet.get('source_evidence'))}",
        f"- source_materials: {_source_materials_summary(packet.get('source_materials'))}",
        f"- latest_snapshot_sha256: {checkpoint.get('snapshot_sha256') or 'none'}",
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
        packet = payload.get("turn_packet")
        if isinstance(packet, dict):
            _ensure_turn_packet_defaults(
                packet,
                str(payload.get("slug") or workspace.name),
                str(
                    payload.get("topic")
                    or payload.get("summary")
                    or payload.get("slug")
                    or workspace.name
                ),
            )
            packet["topic_ownership"] = _normalize_topic_ownership(
                packet.get("topic_ownership"),
                str(payload.get("slug") or workspace.name),
                str(
                    payload.get("topic")
                    or payload.get("summary")
                    or payload.get("slug")
                    or workspace.name
                ),
            )
        if int(payload.get("version") or 0) < STATE_VERSION:
            payload["version"] = STATE_VERSION
        _validate_state(payload)
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
    _normalize_topic_ownership(
        packet.get("topic_ownership"),
        state.get("slug", ""),
        state.get("topic") or state.get("summary") or state.get("slug", ""),
    )
    _validate_checkpoint_semantics(
        {key: packet[key] for key in CHECKPOINT_PACKET_KEYS if key in packet}
    )


def _ensure_turn_packet_defaults(packet: dict[str, Any], slug: str, topic: str) -> None:
    defaults = _default_turn_packet(slug, topic)
    packet["version"] = 2
    packet.setdefault("discussion_slug", slug)

    def merge_defaults(target: dict[str, Any], fallback: dict[str, Any]) -> None:
        for key, value in fallback.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
            elif isinstance(target[key], dict) and isinstance(value, dict):
                merge_defaults(target[key], value)

    merge_defaults(packet, defaults)
    packet["source_materials"] = _normalize_source_materials(
        packet.get("source_materials", [])
    )


def _state_sha256(workspace: Path) -> str:
    json_path = workspace / "discussion-state.json"
    if json_path.is_file():
        return hashlib.sha256(json_path.read_bytes()).hexdigest()
    return hashlib.sha256((workspace / "discussion-state.md").read_bytes()).hexdigest()


def _focus_binding(workspace: Path, state: dict[str, Any]) -> dict[str, Any]:
    ownership = _normalize_topic_ownership(
        state.get("turn_packet", {}).get("topic_ownership"),
        state["slug"],
        state.get("topic") or state.get("summary") or state["slug"],
    )
    return {
        "binding_kind": "discussion_focus",
        "discussion_slug": state["slug"],
        "selected_slug": state["slug"],
        "state_sha256": _state_sha256(workspace),
        "topic": state.get("topic"),
        "current_decision_frame": state.get("turn_packet", {}).get(
            "current_decision_frame"
        ),
        "topic_ownership": ownership,
    }


def _normalize_topic_ownership(
    value: Any,
    slug: str,
    topic: str,
) -> dict[str, Any]:
    if value is None:
        ownership: dict[str, Any] = {}
    elif isinstance(value, dict):
        ownership = copy.deepcopy(value)
    else:
        raise ValueError("topic_ownership must be an object")

    owner_slug = ownership.get("owner_slug")
    if owner_slug is not None and owner_slug != slug:
        raise ValueError("topic_ownership.owner_slug must match discussion slug")

    anchor = str(ownership.get("anchor") or slug).strip()
    if not anchor:
        raise ValueError("topic_ownership.anchor is required")
    owned_scope = ownership.get("owned_scope")
    if owned_scope is None:
        owned_scope = [topic]
    if not isinstance(owned_scope, list) or not owned_scope or not all(
        isinstance(item, str) and item.strip() for item in owned_scope
    ):
        raise ValueError("topic_ownership.owned_scope must be a non-empty string list")
    routed_topics = ownership.get("routed_topics")
    if routed_topics is None:
        routed_topics = []
    if not isinstance(routed_topics, list):
        raise ValueError("topic_ownership.routed_topics must be a list")
    normalized_routes: list[dict[str, Any]] = []
    for index, item in enumerate(routed_topics):
        if not isinstance(item, dict):
            raise ValueError(f"topic_ownership.routed_topics[{index}] must be an object")
        route = str(item.get("route") or "").strip()
        if route not in TOPIC_ROUTES:
            raise ValueError(
                "topic_ownership.routed_topics route must be one of "
                + ", ".join(sorted(TOPIC_ROUTES))
            )
        if not str(item.get("topic") or "").strip():
            raise ValueError(
                f"topic_ownership.routed_topics[{index}].topic is required"
            )
        if route in {"branch_new", "link_existing"} and not str(
            item.get("target_slug") or ""
        ).strip():
            raise ValueError(
                f"topic_ownership.routed_topics[{index}].target_slug is required for {route}"
            )
        normalized_routes.append(copy.deepcopy(item))

    normalized: dict[str, Any] = {
        "anchor": anchor,
        "owned_scope": list(owned_scope),
        "routed_topics": normalized_routes,
    }
    normalized["owner_slug"] = slug
    return normalized


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
    packet = state.get("turn_packet", {})
    handoff = state.get("handoff", {})
    return {
        "slug": state["slug"],
        "workspace": workspace.name,
        "workspace_path": str(workspace.resolve()),
        "status": state["status"],
        "lifecycle_phase": state["lifecycle_phase"],
        "summary": state["summary"],
        "topic": state.get("topic"),
        "current_decision_frame": packet.get("current_decision_frame"),
        "topic_ownership": packet.get("topic_ownership"),
        "state_sha256": _state_sha256(workspace),
        "updated_at": state["updated_at"],
        "closed_at": state.get("closed_at"),
        "archived_at": state.get("archived_at"),
        "next_command": state.get("next_command", "none"),
        "recommended_consumer": handoff.get("recommended_consumer"),
        "review_digest": handoff.get("review_digest"),
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


def _incomplete_discussion_count(project_root: Path) -> int:
    return sum(
        1
        for record in _scan(project_root)
        if not record.get("archived") and record.get("status") in INCOMPLETE_STATUSES
    )


def _require_expected_state_sha256(
    project_root: Path,
    workspace: Path,
    expected_state_sha256: str | None,
) -> None:
    expected = str(expected_state_sha256 or "").strip()
    current = _state_sha256(workspace)
    if expected:
        if expected != current:
            raise ValueError(
                "discussion focus binding is stale or belongs to a different "
                "discussion; refresh --expected-state-sha256 from discussion "
                f"resolve or resume: expected state_sha256 {expected}, current {current}"
            )
        return
    if _incomplete_discussion_count(project_root) > 1:
        raise ValueError(
            "multiple incomplete discussions require --expected-state-sha256 "
            "from discussion resolve or resume"
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
    project_root: Path,
    requested_slug: str,
    topic: str = "",
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return initialize_discussion(
                project_root,
                requested_slug,
                topic,
                _lock_held=True,
            )
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
    binding = _focus_binding(workspace, state)
    return {
        "discussion": _record(workspace, state, False),
        "slug": slug,
        "workspace_path": str(workspace.resolve()),
        "binding": binding,
        "focus_binding": binding,
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
    binding = _focus_binding(workspace, state)
    return {
        "discussion": {
            **_record(workspace, state, archived),
            **copy.deepcopy(state),
            "focus_binding": binding,
        },
        "focus_binding": binding,
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
        "discussion": {
            **_record(workspace, state, False),
            "focus_binding": _focus_binding(workspace, state),
        },
        "turn_packet": copy.deepcopy(state["turn_packet"]),
        "recent_events": recent_events,
        "legacy_state": _legacy,
        "focus_binding": _focus_binding(workspace, state),
    }


CHECKPOINT_PACKET_KEYS = (
    "user_goal",
    "turn_class",
    "requirements_snapshot",
    "implementation_target",
    "source_evidence",
    "source_materials",
    "blocking_unknowns",
    "soft_unknowns",
    "conflicts",
    "downstream_instructions",
    "discussion_decision_digest",
    "must_preserve",
    "truth_pass_status",
    "verified_project_facts",
    "evidence_checked",
    "advice_confidence",
    "discussion_compass_status",
    "next_discussion_paths",
    "ui_discussion_status",
    "design_context",
    "artifact_refs",
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
    "topic_ownership",
)
CHECKPOINT_META_KEYS = frozenset({"summary", "lifecycle_phase", "phase"})


def _validate_checkpoint_fields(changes: dict[str, Any]) -> None:
    known = set(CHECKPOINT_PACKET_KEYS) | CHECKPOINT_META_KEYS
    unknown = sorted(str(key) for key in changes if key not in known)
    if unknown:
        accepted = sorted(known)
        raise ValueError(
            "discussion checkpoint unknown fields: "
            + ", ".join(unknown)
            + "; accepted fields: "
            + ", ".join(accepted)
            + " (unknown fields are rejected instead of silently dropped)"
        )


def _extend_error_messages(
    errors: list[str], structured_errors: list[dict[str, str]]
) -> None:
    errors.extend(item["message"] for item in structured_errors)


def _is_non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _validate_checkpoint_semantics(changes: dict[str, Any]) -> None:
    errors: list[str] = []
    for field in (
        "user_goal",
        "turn_class",
        "current_decision_frame",
        "current_recommendation",
        "next_gate",
    ):
        if field in changes and not str(changes[field] or "").strip():
            errors.append(f"{field} must be a non-empty string")
    for field, allowed in CHECKPOINT_ENUM_FIELDS.items():
        if field in changes and changes[field] not in allowed:
            errors.append(f"{field} must be one of {', '.join(sorted(allowed))}")

    confidence = changes.get("advice_confidence")
    if confidence is not None:
        if isinstance(confidence, str):
            if confidence not in ADVICE_CONFIDENCE_LEVELS:
                errors.append("advice_confidence has an invalid level")
        elif isinstance(confidence, dict):
            if confidence.get("level") not in ADVICE_CONFIDENCE_LEVELS:
                errors.append("advice_confidence.level has an invalid value")
            if not str(confidence.get("reason") or "").strip():
                errors.append("advice_confidence.reason is required")
        else:
            errors.append("advice_confidence must be a level string or object")

    for field in CHECKPOINT_STRING_LIST_FIELDS:
        if field in changes and not _is_non_empty_string_list(changes[field]):
            errors.append(f"{field} must be an array of non-empty strings")

    for field in CHECKPOINT_ARRAY_FIELDS:
        if field in changes and not isinstance(changes[field], list):
            errors.append(f"{field} must be an array")

    for field in CHECKPOINT_OBJECT_FIELDS:
        if field in changes and not isinstance(changes[field], dict):
            errors.append(f"{field} must be an object")

    requirements = changes.get("requirements_snapshot")
    if requirements is not None:
        if not isinstance(requirements, dict):
            errors.append("requirements_snapshot must be an object")
        else:
            if "target_need" in requirements and not str(requirements["target_need"] or "").strip():
                errors.append("requirements_snapshot.target_need must be non-empty")
            for field in (
                "actors",
                "scenarios",
                "constraints",
                "success_criteria",
                "design_direction",
                "optimal_solution_approach",
                "non_goals",
            ):
                if field in requirements and not _is_non_empty_string_list(requirements[field]):
                    errors.append(f"requirements_snapshot.{field} must be an array of non-empty strings")
            scope = requirements.get("scope")
            if scope is not None:
                if not isinstance(scope, dict):
                    errors.append("requirements_snapshot.scope must be an object")
                else:
                    for field in ("in", "out", "deferred"):
                        if field in scope and not _is_non_empty_string_list(scope[field]):
                            errors.append(f"requirements_snapshot.scope.{field} must be an array of non-empty strings")

    if "source_evidence" in changes:
        evidence_errors: list[dict[str, str]] = []
        _validate_object_list(
            changes["source_evidence"], EVIDENCE_FIELDS, "source_evidence", evidence_errors
        )
        if isinstance(changes["source_evidence"], list):
            for index, item in enumerate(changes["source_evidence"]):
                if isinstance(item, dict) and item.get("evidence_status") not in SOURCE_EVIDENCE_STATUSES:
                    evidence_errors.append(
                        _error(
                            "invalid_source_evidence_status",
                            f"source_evidence[{index}].evidence_status is invalid",
                        )
                    )
        _extend_error_messages(errors, evidence_errors)

    if "source_materials" in changes:
        material_errors: list[dict[str, str]] = []
        normalized = _normalize_source_materials(changes["source_materials"])
        _validate_source_materials(normalized, "in_progress", material_errors)
        _extend_error_messages(errors, material_errors)

    if "must_preserve" in changes:
        preserve_errors: list[dict[str, str]] = []
        _validate_must_preserve(changes["must_preserve"], preserve_errors)
        _extend_error_messages(errors, preserve_errors)

    for field in ("blocking_unknowns", "soft_unknowns"):
        if field in changes:
            unknown_errors: list[dict[str, str]] = []
            _validate_unknown_records(changes[field], field, unknown_errors)
            _extend_error_messages(errors, unknown_errors)
    if "conflicts" in changes:
        conflict_errors: list[dict[str, str]] = []
        _validate_conflict_records(changes["conflicts"], conflict_errors)
        _extend_error_messages(errors, conflict_errors)

    if errors:
        raise ValueError("discussion checkpoint invalid semantic fields: " + "; ".join(errors))


def checkpoint_discussion(
    project_root: Path,
    slug: str,
    changes: dict[str, Any],
    expected_state_sha256: str | None = None,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return checkpoint_discussion(
                project_root,
                slug,
                changes,
                expected_state_sha256,
                _lock_held=True,
            )
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot be checkpointed")
    if not isinstance(changes, dict):
        raise ValueError("checkpoint payload must be an object")
    _validate_checkpoint_fields(changes)
    _validate_checkpoint_semantics(changes)
    state, _legacy = _load_state(workspace)
    _require_expected_state_sha256(project_root, workspace, expected_state_sha256)
    phase = changes.get("lifecycle_phase", changes.get("phase", state["lifecycle_phase"]))
    if isinstance(phase, str):
        phase = phase.strip().lower()
    if phase not in LIFECYCLE_PHASES - {"ready", "consumed", "closed"}:
        raise ValueError(f"invalid checkpoint lifecycle phase: {phase}")
    timestamp = now_utc()
    event_id = uuid.uuid4().hex
    summary = str(changes.get("summary") or state["summary"]).strip()
    packet = state["turn_packet"]
    changed_fields: list[str] = []
    for key in CHECKPOINT_PACKET_KEYS:
        if key in changes:
            if key == "topic_ownership":
                packet[key] = _normalize_topic_ownership(
                    changes[key],
                    state["slug"],
                    state.get("topic") or state.get("summary") or state["slug"],
                )
            elif key == "source_materials":
                packet[key] = _normalize_source_materials(changes[key])
            else:
                packet[key] = copy.deepcopy(changes[key])
            changed_fields.append(key)
    packet["lifecycle_phase"] = phase
    packet["persistence_mode"] = "durable-checkpoint"
    state.update(
        {"summary": summary, "lifecycle_phase": phase, "updated_at": timestamp}
    )
    _ensure_turn_packet_defaults(
        packet,
        state["slug"],
        state.get("topic") or state.get("summary") or state["slug"],
    )
    snapshot = _discussion_semantic_snapshot(packet)
    snapshot_sha256 = _snapshot_digest(snapshot)
    changed_fields = sorted(changed_fields)
    state["latest_checkpoint"] = {
        "event_id": event_id,
        "timestamp": timestamp,
        "snapshot_sha256": snapshot_sha256,
        "changed_fields": changed_fields,
    }
    event = {
        "version": 2,
        "event_id": event_id,
        "timestamp": timestamp,
        "kind": "durable-checkpoint",
        "lifecycle_phase": phase,
        "summary": summary,
        "snapshot_sha256": snapshot_sha256,
        "changed_fields": changed_fields,
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
        "turn_packet": copy.deepcopy(packet),
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


def _canonical_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _material_digest(material: dict[str, Any]) -> str:
    protected = copy.deepcopy(material)
    protected.pop("material_digest", None)
    return _canonical_digest(protected)


def _normalize_source_materials(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return value
    normalized: list[Any] = []
    for item in value:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        material = copy.deepcopy(item)
        if not material.get("material_type") and material.get("source_type"):
            material["material_type"] = material.pop("source_type")
        if not material.get("locator") and material.get("source"):
            material["locator"] = material.pop("source")
        material["material_digest"] = _material_digest(material)
        normalized.append(material)
    return normalized


def _discussion_semantic_snapshot(packet: dict[str, Any]) -> dict[str, Any]:
    excluded = {"allowed_actions", "lifecycle_phase", "next_gate", "persistence_mode", "turn_class"}
    snapshot = {
        key: copy.deepcopy(packet[key])
        for key in CHECKPOINT_PACKET_KEYS
        if key in packet and key not in excluded
    }
    snapshot["discussion_slug"] = packet.get("discussion_slug")
    return snapshot


def _snapshot_digest(snapshot: dict[str, Any]) -> str:
    return _canonical_digest(snapshot)


def write_handoff(
    project_root: Path,
    slug: str,
    handoff_payload: dict[str, Any],
    expected_state_sha256: str | None = None,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return write_handoff(
                project_root,
                slug,
                handoff_payload,
                expected_state_sha256,
                _lock_held=True,
            )
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot write a handoff")
    state, _legacy = _load_state(workspace)
    _require_expected_state_sha256(project_root, workspace, expected_state_sha256)
    payload = _merge_handoff_template(project_root, handoff_payload)
    payload.update(
        {
            "version": HANDOFF_VERSION,
            "handoff_kind": "discussion_requirement_contract",
            "status": "draft",
            "entry_source": "sp-discussion",
            "discussion_slug": slug,
            "source_contract": f".specify/discussions/{slug}/handoff-to-specify.json",
            "handoff_integrity": "not-checked",
        }
    )
    payload["topic_ownership"] = _normalize_topic_ownership(
        state.get("turn_packet", {}).get("topic_ownership"),
        slug,
        state.get("topic") or state.get("summary") or slug,
    )
    packet = state["turn_packet"]
    checkpoint = state.get("latest_checkpoint") if isinstance(state.get("latest_checkpoint"), dict) else None
    snapshot = _discussion_semantic_snapshot(packet)
    current_snapshot_sha256 = _snapshot_digest(snapshot)
    if not isinstance(checkpoint, dict) or not checkpoint.get("snapshot_sha256"):
        raise ValueError(
            "missing_semantic_checkpoint: write-handoff requires a current checkpoint before handoff"
        )
    if checkpoint.get("snapshot_sha256") != current_snapshot_sha256:
        raise ValueError(
            "stale_semantic_checkpoint: latest_checkpoint.snapshot_sha256 does not match current discussion state"
        )
    _overlay_handoff_from_state(payload, packet)
    payload["source_materials"] = _normalize_source_materials(
        payload.get("source_materials", [])
    )
    payload["discussion_snapshot_digest"] = current_snapshot_sha256
    payload["hard_unknown_count"] = _derived_hard_unknown_count(payload)
    payload["open_conflict_count"] = _derived_open_conflict_count(payload)
    if payload["hard_unknown_count"] == 0 and payload["open_conflict_count"] == 0:
        payload["coverage_status"] = "complete"
        payload["planning_gate_status"] = "ready"
    else:
        payload["coverage_status"] = "blocked_by_handoff_integrity"
        payload["planning_gate_status"] = "blocked_by_handoff_integrity"
        raise ValueError(
            "discussion handoff is not ready: blocking_unknowns and conflicts must be resolved before write-handoff"
        )
    quality_gate = payload.get("quality_gate")
    if not isinstance(quality_gate, dict):
        quality_gate = {}
        payload["quality_gate"] = quality_gate
    quality_gate.update(
        {
            "status": "self_reviewed"
            if quality_gate.get("self_reviewed_at")
            else "draft",
            "user_review_required": True,
            "user_confirmed_at": None,
            "confirmed_digest": None,
        }
    )
    review_digest = compute_review_digest(payload)
    payload["review_digest"] = review_digest
    preflight_errors: list[dict[str, str]] = []
    _validate_handoff_fields(payload, slug, preflight_errors, "draft", state)
    if preflight_errors:
        raise ValueError(
            "discussion handoff draft is invalid: "
            + ", ".join(error["code"] for error in preflight_errors)
        )
    json_path = workspace / "handoff-to-specify.json"
    _atomic_write_json(json_path, payload)
    timestamp = now_utc()
    state.update(
        {"status": "active", "lifecycle_phase": "review", "updated_at": timestamp}
    )
    state["turn_packet"].update(
        {
            "lifecycle_phase": "review",
            "context_boundary": copy.deepcopy(payload.get("context_boundary")),
            "persistence_mode": "lifecycle-transition",
            "allowed_actions": ["review-handoff", "request-changes", "mark-ready"],
            "next_gate": "handoff-draft-validation",
        }
    )
    state["handoff"].update(
        {
            "review_status": "self-reviewed"
            if quality_gate.get("status") == "self_reviewed"
            else "draft",
            "quality_gate_status": quality_gate.get("status", "draft"),
            "review_digest": review_digest,
            "contract_path": payload["source_contract"],
            "recommended_consumer": payload.get(
                "recommended_consumer", "continue-discussion"
            ),
        }
    )
    state["next_command"] = "none"
    _persist_state(workspace, state)
    _write_index(project_root)
    return {
        "discussion": {**_record(workspace, state, False), **copy.deepcopy(state)},
        "review_digest": review_digest,
        "json_path": str(json_path.resolve()),
    }


def _merge_dict(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _merge_handoff_template(project_root: Path, handoff_payload: dict[str, Any]) -> dict[str, Any]:
    template_path = project_root / ".specify" / "templates" / "discussion-handoff-template.json"
    if not template_path.is_file():
        raise ValueError(f"discussion handoff template is unavailable: {template_path}")
    template = json.loads(template_path.read_text(encoding="utf-8"))
    if not isinstance(template, dict):
        raise ValueError("discussion handoff template must be an object")
    if template.get("version") != HANDOFF_VERSION or template.get("handoff_kind") != "discussion_requirement_contract":
        raise ValueError("discussion handoff template must use version 5 discussion_requirement_contract")
    return _merge_dict(template, handoff_payload)


def _overlay_handoff_from_state(payload: dict[str, Any], packet: dict[str, Any]) -> None:
    payload["agent_requirement_contract"] = copy.deepcopy(packet.get("requirements_snapshot"))
    payload.pop("requirements_snapshot", None)
    for key in (
        "implementation_target",
        "source_evidence",
        "source_materials",
        "blocking_unknowns",
        "soft_unknowns",
        "conflicts",
        "downstream_instructions",
        "discussion_decision_digest",
        "must_preserve",
        "truth_pass_status",
        "verified_project_facts",
        "evidence_checked",
        "advice_confidence",
        "ui_discussion_status",
        "artifact_refs",
    ):
        if key in packet:
            payload[key] = copy.deepcopy(packet[key])
    if "context_boundary" in packet:
        payload["context_boundary"] = copy.deepcopy(packet["context_boundary"])
    decision_digest = payload.get("discussion_decision_digest")
    if isinstance(decision_digest, dict):
        decision_digest["design_context"] = copy.deepcopy(packet.get("design_context"))


_CLOSED_DISCUSSION_ITEM_STATUSES = {
    "closed",
    "resolved",
    "deferred",
    "superseded",
    "dropped",
}


def _is_unresolved_discussion_item(item: Any) -> bool:
    if not isinstance(item, dict):
        return True
    return str(item.get("status") or "").strip().lower() not in _CLOSED_DISCUSSION_ITEM_STATUSES


def _derived_hard_unknown_count(payload: dict[str, Any]) -> int:
    return sum(
        1
        for item in payload.get("blocking_unknowns") or []
        if _is_unresolved_discussion_item(item)
    )


def _derived_open_conflict_count(payload: dict[str, Any]) -> int:
    downstream = payload.get("downstream_instructions")
    conflicts = sum(
        1
        for item in payload.get("conflicts") or []
        if _is_unresolved_discussion_item(item)
    )
    if isinstance(downstream, dict):
        conflicts += len(downstream.get("conflicts_requiring_return") or [])
    return conflicts


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
        missing = sorted(
            field
            for field in required_fields
            if field not in item or not str(item.get(field) or "").strip()
        )
        if missing:
            errors.append(
                _error(
                    f"incomplete_{label}_item",
                    f"{label}[{index}] missing {', '.join(missing)}",
                )
            )


def _validate_must_preserve(value: Any, errors: list[dict[str, str]]) -> None:
    _validate_object_list(value, MUST_PRESERVE_FIELDS, "must_preserve", errors)
    if not isinstance(value, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "")
        if not re.fullmatch(r"(?:MP|CA)-[0-9]{3}", item_id):
            errors.append(
                _error(
                    "invalid_must_preserve_id",
                    f"must_preserve[{index}].id must match MP-### or CA-###",
                )
            )
        if item_id in seen:
            errors.append(
                _error(
                    "duplicate_must_preserve_id",
                    f"must_preserve[{index}].id duplicates {item_id}",
                )
            )
        seen.add(item_id)
        if item.get("blocking_level") not in {"hard", "soft"}:
            errors.append(
                _error(
                    "invalid_must_preserve_blocking_level",
                    f"must_preserve[{index}].blocking_level is invalid",
                )
            )
        status = str(item.get("status") or "").strip().lower()
        if status not in {"active", "confirmed", "resolved", "deferred", "superseded", "dropped"}:
            errors.append(
                _error(
                    "invalid_must_preserve_status",
                    f"must_preserve[{index}].status is invalid",
                )
            )
        if status == "resolved" and not str(item.get("resolution_evidence") or "").strip():
            errors.append(_error("incomplete_must_preserve_resolution", f"must_preserve[{index}].resolution_evidence is required"))
        if status == "deferred" and not str(item.get("stop_and_reopen_condition") or "").strip():
            errors.append(_error("incomplete_must_preserve_deferral", f"must_preserve[{index}].stop_and_reopen_condition is required"))
        if status == "superseded" and not str(item.get("superseded_by") or "").strip():
            errors.append(_error("incomplete_must_preserve_supersession", f"must_preserve[{index}].superseded_by is required"))
        if status == "dropped" and not str(item.get("user_decision_source") or "").strip():
            errors.append(_error("incomplete_must_preserve_drop", f"must_preserve[{index}].user_decision_source is required"))


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _handoff_paths(project_root: Path, slug: str) -> tuple[Path, Path]:
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion has no active handoff")
    return workspace, workspace / "handoff-to-specify.json"


def validate_handoff(
    project_root: Path,
    slug: str,
    *,
    validation_mode: str = "ready",
) -> dict[str, Any]:
    normalized_mode = str(validation_mode or "ready").strip().lower()
    if normalized_mode not in HANDOFF_VALIDATION_MODES:
        raise ValueError("handoff validation mode must be 'draft' or 'ready'")
    workspace, json_path = _handoff_paths(project_root, slug)
    errors: list[dict[str, str]] = []
    if not json_path.is_file():
        errors.append(_error("missing_handoff_json", "handoff JSON is required"))
    if errors:
        return _validation_payload(workspace, errors, None, normalized_mode)
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append(_error("invalid_handoff_json", "handoff JSON is not valid JSON"))
        return _validation_payload(workspace, errors, None, normalized_mode)
    if not isinstance(payload, dict):
        errors.append(
            _error("invalid_handoff_payload", "handoff JSON must be an object")
        )
        return _validation_payload(workspace, errors, None, normalized_mode)
    state, _legacy = _load_state(workspace)
    _validate_handoff_fields(payload, slug, errors, normalized_mode, state)
    return _validation_payload(workspace, errors, payload, normalized_mode)


def _validate_handoff_fields(
    payload: dict[str, Any],
    slug: str,
    errors: list[dict[str, str]],
    validation_mode: str,
    state: dict[str, Any],
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
    topic_ownership = payload.get("topic_ownership")
    if not isinstance(topic_ownership, dict) or topic_ownership.get("owner_slug") != slug:
        errors.append(
            _error(
                "invalid_topic_ownership",
                "topic_ownership.owner_slug must match discussion_slug",
            )
        )
    try:
        _normalize_topic_ownership(
            topic_ownership,
            slug,
            str(payload.get("handoff_goal") or slug),
        )
    except ValueError as exc:
        errors.append(_error("invalid_topic_ownership", str(exc)))
    if not str(payload.get("handoff_goal") or "").strip():
        errors.append(_error("missing_handoff_goal", "handoff_goal is required"))
    _validate_requirements(payload.get("agent_requirement_contract"), errors)
    _validate_implementation_target(payload.get("implementation_target"), errors)
    _validate_boundary(payload.get("context_boundary"), errors)
    _validate_object_list(
        payload.get("source_evidence"), EVIDENCE_FIELDS, "source_evidence", errors
    )
    if not payload.get("source_evidence"):
        errors.append(_error("empty_source_evidence", "source_evidence must record at least one checked claim"))
    _validate_source_evidence(payload.get("source_evidence"), errors)
    _validate_source_materials(payload.get("source_materials"), payload.get("coverage_status"), errors)
    _validate_source_material_evidence_links(payload.get("source_materials"), payload.get("source_evidence"), errors)
    _validate_must_preserve(payload.get("must_preserve"), errors)
    if not payload.get("must_preserve"):
        errors.append(
            _error("empty_must_preserve", "Must-Preserve coverage is required")
        )
    _validate_unknown_records(payload.get("blocking_unknowns"), "blocking_unknowns", errors)
    _validate_unknown_records(payload.get("soft_unknowns"), "soft_unknowns", errors)
    _validate_conflict_records(payload.get("conflicts"), errors)
    _validate_downstream_instructions(payload.get("downstream_instructions"), errors)
    _validate_decision_digest(payload.get("discussion_decision_digest"), errors)
    if payload.get("hard_unknown_count") != _derived_hard_unknown_count(payload):
        errors.append(_error("hard_unknown_count_mismatch", "hard_unknown_count must equal unresolved blocking_unknowns"))
    if payload.get("open_conflict_count") != _derived_open_conflict_count(payload):
        errors.append(_error("open_conflict_count_mismatch", "open_conflict_count must equal unresolved conflicts"))
    _validate_discussion_snapshot_digest(payload, state, errors)
    _validate_consumers(payload, errors)
    _validate_review_digest(payload, errors, validation_mode)


def _validate_source_evidence(value: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        status = str(item.get("evidence_status") or "").strip()
        if status and status not in SOURCE_EVIDENCE_STATUSES:
            errors.append(
                _error(
                    "invalid_source_evidence_status",
                    f"source_evidence[{index}].evidence_status is invalid",
                )
            )
        elif status in {"missing", "conflict", "stale-advisory"}:
            errors.append(
                _error(
                    "unresolved_source_evidence",
                    f"source_evidence[{index}] is not ready for handoff",
                )
            )


def _validate_unknown_records(
    value: Any, label: str, errors: list[dict[str, str]]
) -> None:
    if not isinstance(value, list):
        errors.append(_error(f"invalid_{label}", f"{label} must be a list"))
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            if label == "blocking_unknowns":
                errors.append(
                    _error(
                        f"invalid_{label}_item",
                        f"{label}[{index}] must be a structured object",
                    )
                )
            continue
        for field in ("id", "question", "owner", "status", "latest_resolve_phase"):
            if not str(item.get(field) or "").strip():
                errors.append(
                    _error(
                        f"incomplete_{label}_item",
                        f"{label}[{index}].{field} is required",
                    )
                )
        status = str(item.get("status") or "").strip().lower()
        if status not in {"open", "resolved", "closed", "deferred", "superseded", "dropped"}:
            errors.append(
                _error(
                    f"invalid_{label}_status",
                    f"{label}[{index}].status is invalid",
                )
            )
        if status in {"resolved", "closed"} and not str(
            item.get("resolution_evidence") or ""
        ).strip():
            errors.append(
                _error(
                    f"incomplete_{label}_resolution",
                    f"{label}[{index}].resolution_evidence is required",
                )
            )
        if status == "deferred" and not str(
            item.get("stop_and_reopen_condition") or ""
        ).strip():
            errors.append(
                _error(
                    f"incomplete_{label}_deferral",
                    f"{label}[{index}].stop_and_reopen_condition is required",
                )
            )
        if status == "superseded" and not str(item.get("superseded_by") or "").strip():
            errors.append(
                _error(
                    f"incomplete_{label}_supersession",
                    f"{label}[{index}].superseded_by is required",
                )
            )
        if status == "dropped" and not str(item.get("user_decision_source") or "").strip():
            errors.append(
                _error(
                    f"incomplete_{label}_drop",
                    f"{label}[{index}].user_decision_source is required",
                )
            )


def _validate_conflict_records(value: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, list):
        errors.append(_error("invalid_conflicts", "conflicts must be a list"))
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(
                _error("invalid_conflicts_item", f"conflicts[{index}] must be an object")
            )
            continue
        for field in ("id", "claim", "status"):
            if not str(item.get(field) or "").strip():
                errors.append(
                    _error(
                        "incomplete_conflicts_item",
                        f"conflicts[{index}].{field} is required",
                    )
                )
        status = str(item.get("status") or "").strip().lower()
        if status not in {"open", "resolved", "closed", "deferred", "superseded", "dropped"}:
            errors.append(
                _error(
                    "invalid_conflicts_status",
                    f"conflicts[{index}].status is invalid",
                )
            )
        if status in _CLOSED_DISCUSSION_ITEM_STATUSES:
            if not str(item.get("resolution") or "").strip():
                errors.append(
                    _error(
                        "incomplete_conflicts_resolution",
                        f"conflicts[{index}].resolution is required",
                    )
                )
            if not str(item.get("resolution_evidence") or "").strip():
                errors.append(
                    _error(
                        "incomplete_conflicts_resolution",
                        f"conflicts[{index}].resolution_evidence is required",
                    )
                )


def _validate_downstream_instructions(
    value: Any, errors: list[dict[str, str]]
) -> None:
    fields = (
        "settled_decisions",
        "preserved_assumptions",
        "conflicts_requiring_return",
        "capability_map",
        "dependencies",
        "planning_constraints",
        "deferred_scope",
        "reopen_conditions",
    )
    if not isinstance(value, dict):
        errors.append(
            _error("missing_downstream_instructions", "downstream_instructions is required")
        )
        return
    if "recommended_sequence" in value:
        errors.append(
            _error("legacy_recommended_sequence", "recommended_sequence is not allowed")
        )
    for field in fields:
        if not isinstance(value.get(field), list):
            errors.append(
                _error(
                    "invalid_downstream_instructions",
                    f"downstream_instructions.{field} must be a list",
                )
            )
    if not value.get("settled_decisions"):
        errors.append(
            _error(
                "empty_settled_decisions",
                "downstream_instructions.settled_decisions must not be empty",
            )
        )


def _validate_decision_digest(value: Any, errors: list[dict[str, str]]) -> None:
    fields = (
        "locked_direction",
        "rejected_alternatives",
        "accepted_tradeoffs",
        "experience_commitments",
        "design_system_requirements",
        "review_criteria_carried_forward",
        "must_not_dilute",
    )
    if not isinstance(value, dict):
        errors.append(
            _error("missing_discussion_decision_digest", "discussion_decision_digest is required")
        )
        return
    for field in fields:
        if not isinstance(value.get(field), list):
            errors.append(
                _error(
                    "invalid_discussion_decision_digest",
                    f"discussion_decision_digest.{field} must be a list",
                )
            )
    for field in ("locked_direction", "review_criteria_carried_forward"):
        if not value.get(field):
            errors.append(
                _error(
                    "incomplete_discussion_decision_digest",
                    f"discussion_decision_digest.{field} must not be empty",
                )
            )
    if not str(value.get("design_system_status") or "").strip():
        errors.append(
            _error(
                "incomplete_discussion_decision_digest",
                "discussion_decision_digest.design_system_status is required",
            )
        )
    if value.get("design_risk_level") not in {"none", "low", "medium", "high"}:
        errors.append(
            _error(
                "invalid_discussion_decision_digest",
                "discussion_decision_digest.design_risk_level is invalid",
            )
        )
    if not isinstance(value.get("design_context"), dict):
        errors.append(
            _error(
                "incomplete_discussion_decision_digest",
                "discussion_decision_digest.design_context is required",
            )
        )


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
    if not boundary.get("current_project_roles"):
        errors.append(
            _error(
                "empty_current_project_roles",
                "context_boundary.current_project_roles must not be empty",
            )
        )
    if boundary.get("target_project_root"):
        _validate_object_list(
            boundary.get("target_project_roles"),
            ROLE_FIELDS,
            "target_project_roles",
            errors,
        )
        if not boundary.get("target_project_roles"):
            errors.append(
                _error(
                    "empty_target_project_roles",
                    "context_boundary.target_project_roles must not be empty when target_project_root is set",
                )
            )


def _validate_requirements(requirements: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(requirements, dict):
        errors.append(_error("missing_requirements_snapshot", "agent_requirement_contract is required"))
        return
    if not str(requirements.get("target_need") or "").strip():
        errors.append(_error("missing_requirements_target_need", "agent_requirement_contract.target_need is required"))
    scope = requirements.get("scope")
    if (
        not isinstance(scope, dict)
        or not scope.get("in")
        or not _is_non_empty_string_list(scope.get("in"))
    ):
        errors.append(_error("missing_requirements_scope", "agent_requirement_contract.scope.in is required"))
    for field in ("actors", "scenarios", "success_criteria", "optimal_solution_approach"):
        if not requirements.get(field) or not _is_non_empty_string_list(requirements.get(field)):
            errors.append(_error(f"missing_requirements_{field}", f"agent_requirement_contract.{field} is required"))
    for field in ("constraints", "design_direction", "non_goals"):
        if not _is_non_empty_string_list(requirements.get(field)):
            errors.append(_error(f"invalid_requirements_{field}", f"agent_requirement_contract.{field} must be an array of non-empty strings"))
    if isinstance(scope, dict):
        for field in ("out", "deferred"):
            if not _is_non_empty_string_list(scope.get(field)):
                errors.append(_error(f"invalid_requirements_scope_{field}", f"agent_requirement_contract.scope.{field} must be an array of non-empty strings"))


def _validate_implementation_target(target: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(target, dict):
        errors.append(_error("missing_implementation_target", "implementation_target is required"))
        return
    if not str(target.get("target_root") or target.get("actual_project") or target.get("target_project_root") or "").strip():
        errors.append(_error("missing_implementation_target_root", "implementation_target must identify the actual project or target_root"))
    if not (target.get("target_paths") or target.get("required_target_paths_to_verify")):
        errors.append(_error("missing_implementation_target_paths", "implementation_target must name target paths or required verification paths"))
    for field in ("target_paths", "required_target_paths_to_verify"):
        if not _is_non_empty_string_list(target.get(field)):
            errors.append(
                _error(
                    "invalid_implementation_target_paths",
                    f"implementation_target.{field} must be an array of non-empty strings",
                )
            )


def _validate_source_materials(value: Any, coverage_status: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, list):
        errors.append(_error("invalid_source_materials", "source_materials must be a list"))
        return
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(_error("invalid_source_materials_item", f"source_materials[{index}] must be an object"))
            continue
        missing = sorted(SOURCE_MATERIAL_FIELDS - set(item))
        if missing:
            errors.append(_error("incomplete_source_materials_item", f"source_materials[{index}] missing {', '.join(missing)}"))
        if not re.match(r"^MAT-[0-9]{3}$", str(item.get("id") or "")):
            errors.append(_error("invalid_source_materials_id", f"source_materials[{index}].id must match MAT-###"))
        material_id = str(item.get("id") or "")
        if material_id in seen:
            errors.append(_error("duplicate_source_materials_id", f"source_materials[{index}].id duplicates {material_id}"))
        seen.add(material_id)
        for field in ("material_type", "locator", "summary"):
            if not str(item.get(field) or "").strip():
                errors.append(_error(f"empty_source_materials_{field}", f"source_materials[{index}].{field} must be non-empty"))
        if not _is_non_empty_string_list(item.get("claims")) or not item.get("claims"):
            errors.append(_error("empty_source_materials_claims", f"source_materials[{index}].claims must not be empty"))
        if not _is_non_empty_string_list(item.get("coverage_gaps")):
            errors.append(_error("invalid_source_materials_coverage_gaps", f"source_materials[{index}].coverage_gaps must be an array of non-empty strings"))
        status = str(item.get("inspection_status") or "")
        if status not in SOURCE_MATERIAL_STATUSES:
            errors.append(_error("invalid_source_materials_status", f"source_materials[{index}].inspection_status is invalid"))
        if item.get("sensitivity") not in SOURCE_MATERIAL_SENSITIVITIES:
            errors.append(_error("invalid_source_materials_sensitivity", f"source_materials[{index}].sensitivity is invalid"))
        content_sha256 = item.get("content_sha256")
        if content_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", str(content_sha256)):
            errors.append(_error("invalid_source_materials_content_sha256", f"source_materials[{index}].content_sha256 must be a sha256 digest"))
        if coverage_status == "complete" and (status != "inspected" or item.get("coverage_gaps")):
            errors.append(_error("unresolved_source_materials", f"source_materials[{index}] must be inspected with no coverage gaps before handoff-ready"))
        if item.get("material_digest") != _material_digest(item):
            errors.append(_error("source_materials_digest_mismatch", f"source_materials[{index}].material_digest does not match protected material content"))


def _validate_source_material_evidence_links(
    materials: Any, evidence: Any, errors: list[dict[str, str]]
) -> None:
    if not isinstance(materials, list) or not materials:
        return
    material_ids = {
        str(item.get("id"))
        for item in materials
        if isinstance(item, dict) and item.get("id")
    }
    referenced: set[str] = set()
    for index, item in enumerate(evidence if isinstance(evidence, list) else []):
        if not isinstance(item, dict) or not item.get("material_id"):
            continue
        material_id = str(item["material_id"])
        if material_id not in material_ids:
            errors.append(_error("unknown_source_evidence_material", f"source_evidence[{index}].material_id references unknown material {material_id}"))
            continue
        referenced.add(material_id)
    for material_id in sorted(material_ids - referenced):
        errors.append(_error("unreferenced_source_material", f"{material_id} must be referenced by source_evidence.material_id"))


def _validate_discussion_snapshot_digest(
    payload: dict[str, Any], state: dict[str, Any], errors: list[dict[str, str]]
) -> None:
    checkpoint = state.get("latest_checkpoint")
    if not isinstance(checkpoint, dict) or not checkpoint.get("snapshot_sha256"):
        errors.append(_error("missing_semantic_checkpoint", "latest_checkpoint.snapshot_sha256 is required before handoff"))
        return
    packet = state.get("turn_packet")
    if not isinstance(packet, dict):
        errors.append(_error("invalid_discussion_snapshot", "state turn_packet is required"))
        return
    digest = _snapshot_digest(_discussion_semantic_snapshot(packet))
    if checkpoint.get("snapshot_sha256") != digest:
        errors.append(_error("stale_semantic_checkpoint", "latest_checkpoint.snapshot_sha256 must match the current discussion semantic snapshot"))
    if payload.get("discussion_snapshot_digest") != digest:
        errors.append(_error("discussion_snapshot_digest_mismatch", "discussion_snapshot_digest must match the current discussion semantic snapshot"))


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
    validation_mode: str,
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
    if not isinstance(quality_gate, dict):
        errors.append(_error("missing_quality_gate", "quality gate is required"))
        return
    if quality_gate.get("status") not in {
        "self_reviewed",
        "self-reviewed",
        "user_confirmed",
        "user-confirmed",
    } or not quality_gate.get("self_reviewed_at"):
        errors.append(
            _error(
                "handoff_not_self_reviewed",
                "quality gate must record agent self-review",
            )
        )
    if validation_mode == "draft":
        return
    if quality_gate.get("status") not in {"user_confirmed", "user-confirmed"}:
        errors.append(
            _error(
                "handoff_not_user_confirmed",
                "quality gate must record user confirmation",
            )
        )
        return
    if not quality_gate.get("user_confirmed_at"):
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
    validation_mode: str,
) -> dict[str, Any]:
    return {
        "valid": not errors,
        "validation_mode": validation_mode,
        "workspace_path": str(workspace.resolve()),
        "review_digest": payload.get("review_digest") if payload else None,
        "error_codes": [error["code"] for error in errors],
        "errors": errors,
    }


def confirm_handoff(
    project_root: Path,
    slug: str,
    review_digest: str,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return confirm_handoff(
                project_root,
                slug,
                review_digest,
                _lock_held=True,
            )
    expected_digest = str(review_digest or "").strip()
    if not expected_digest:
        raise ValueError("review digest is required")
    validation = validate_handoff(
        project_root,
        slug,
        validation_mode="draft",
    )
    if not validation["valid"]:
        codes = ", ".join(validation["error_codes"])
        raise ValueError(f"discussion handoff draft is not reviewable: {codes}")
    if validation["review_digest"] != expected_digest:
        raise ValueError("review digest does not match the current handoff revision")

    workspace, json_path = _handoff_paths(project_root, slug)
    state, _legacy = _load_state(workspace)
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    quality_gate = handoff["quality_gate"]
    if (
        quality_gate.get("status") in {"user_confirmed", "user-confirmed"}
        and quality_gate.get("user_confirmed_at")
        and quality_gate.get("confirmed_digest") == expected_digest
    ):
        return {
            "discussion": {
                **_record(workspace, state, False),
                **copy.deepcopy(state),
            },
            "review_digest": expected_digest,
            "json_path": str(json_path.resolve()),
        }
    quality_gate.update(
        {
            "status": "user_confirmed",
            "user_confirmed_at": now_utc(),
            "confirmed_digest": expected_digest,
        }
    )
    _atomic_write_json(json_path, handoff)
    timestamp = now_utc()
    state.update(
        {"status": "active", "lifecycle_phase": "review", "updated_at": timestamp}
    )
    state["turn_packet"].update(
        {
            "lifecycle_phase": "review",
            "persistence_mode": "lifecycle-transition",
            "allowed_actions": ["mark-ready", "request-changes", "review-handoff"],
            "next_gate": "handoff-ready-validation",
        }
    )
    state["handoff"].update(
        {
            "review_status": "user-confirmed",
            "quality_gate_status": "user_confirmed",
            "review_digest": expected_digest,
            "contract_path": handoff["source_contract"],
            "recommended_consumer": handoff.get(
                "recommended_consumer", "continue-discussion"
            ),
        }
    )
    state["next_command"] = "none"
    _persist_state(workspace, state)
    _write_index(project_root)
    return {
        "discussion": {**_record(workspace, state, False), **copy.deepcopy(state)},
        "review_digest": expected_digest,
        "json_path": str(json_path.resolve()),
    }


def mark_ready(
    project_root: Path,
    slug: str,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return mark_ready(project_root, slug, _lock_held=True)
    validation = validate_handoff(
        project_root,
        slug,
        validation_mode="ready",
    )
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
    state_sha256: str,
    recommended_consumer: str,
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
        expected = {
            "source_discussion_slug": slug,
            "source_contract": expected_contract,
            "review_digest": review_digest,
            "state_sha256": state_sha256,
            "recommended_consumer": recommended_consumer,
        }
        mismatched = [
            field for field, value in expected.items() if scalar_fields.get(field) != value
        ]
        if mismatched:
            raise ValueError(
                "consumer evidence does not bind the source contract or required "
                "lineage fields: "
                + ", ".join(mismatched)
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
        "state_sha256": state_sha256,
        "recommended_consumer": recommended_consumer,
    }
    mismatched = [
        field for field, value in expected.items() if payload.get(field) != value
    ]
    if mismatched:
        raise ValueError(
            "consumer evidence does not bind the source contract or required "
            f"lineage fields: {', '.join(mismatched)}"
        )


def mark_consumed(
    project_root: Path,
    slug: str,
    consumer_path_value: str,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return mark_consumed(
                project_root,
                slug,
                consumer_path_value,
                _lock_held=True,
            )
    workspace, archived = _find_workspace(project_root, slug, include_archived=False)
    if archived:
        raise ValueError("archived discussion cannot be consumed")
    state, _legacy = _load_state(workspace)
    if state["status"] != "handoff-ready" or state["lifecycle_phase"] != "ready":
        raise ValueError("only a validated handoff-ready discussion can be consumed")
    if state.get("consumption", {}).get("status") != "not_consumed":
        raise ValueError("discussion source must be not_consumed before consumption")
    validation = validate_handoff(project_root, slug, validation_mode="ready")
    if not validation.get("valid"):
        codes = ", ".join(str(code) for code in validation.get("error_codes", []))
        raise ValueError(f"discussion handoff is not ready: {codes}")
    handoff_payload = _load_handoff_payload(workspace)
    if not isinstance(handoff_payload, dict):
        raise ValueError("discussion handoff is not valid JSON")
    if handoff_payload.get("status") != "handoff-ready":
        raise ValueError("discussion source contract is not handoff-ready")
    state_handoff = state.get("handoff", {})
    if not isinstance(state_handoff, dict):
        raise ValueError("discussion state handoff lineage is invalid")
    review_digest = str(state_handoff.get("review_digest") or "")
    if not review_digest:
        raise ValueError("ready discussion is missing a reviewed digest")
    expected_contract = f".specify/discussions/{slug}/handoff-to-specify.json"
    recommended_consumer = str(state_handoff.get("recommended_consumer") or "")
    if (
        state_handoff.get("contract_path") != expected_contract
        or handoff_payload.get("source_contract") != expected_contract
        or handoff_payload.get("review_digest") != review_digest
        or handoff_payload.get("recommended_consumer") != recommended_consumer
    ):
        raise ValueError("discussion state and handoff contract lineage do not match")
    state_sha256 = _state_sha256(workspace)
    consumer_path = _safe_consumer_path(project_root, consumer_path_value)
    evidence_path = _consumer_evidence_path(consumer_path)
    _validate_consumer_evidence(
        project_root,
        slug,
        review_digest,
        state_sha256,
        recommended_consumer,
        evidence_path,
    )
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
        "source_contract": expected_contract,
        "review_digest": review_digest,
        "state_sha256": state_sha256,
        "recommended_consumer": recommended_consumer,
    }
    _persist_state(workspace, state)
    _write_index(project_root)
    return {"discussion": {**_record(workspace, state, False), **copy.deepcopy(state)}}


def close_discussion(
    project_root: Path,
    slug: str,
    status_value: str,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return close_discussion(
                project_root,
                slug,
                status_value,
                _lock_held=True,
            )
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


def archive_discussion(
    project_root: Path,
    slug: str,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return archive_discussion(project_root, slug, _lock_held=True)
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


def rebuild_index(
    project_root: Path,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if not _lock_held:
        with _discussion_mutation_lock(project_root):
            return rebuild_index(project_root, _lock_held=True)
    return _write_index(project_root)


def _discussion_candidate(
    workspace: Path,
    state: dict[str, Any],
    *,
    handoff_payload: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    consumer: dict[str, Any] = {
        "source_contract": None,
        "review_digest": None,
        "recommended_consumer": state.get("handoff", {}).get("recommended_consumer"),
    }
    if handoff_payload:
        consumer.update(
            {
                "source_contract": handoff_payload.get("source_contract"),
                "review_digest": handoff_payload.get("review_digest"),
                "recommended_consumer": handoff_payload.get("recommended_consumer"),
            }
        )
    elif state.get("handoff"):
        consumer.update(
            {
                "source_contract": state["handoff"].get("contract_path"),
                "review_digest": state["handoff"].get("review_digest"),
            }
        )
    if validation is not None:
        consumer["ready_validation"] = {
            "valid": validation.get("valid") is True,
            "error_codes": list(validation.get("error_codes") or []),
        }
    return {
        "slug": state["slug"],
        "summary": state["summary"],
        "status": state["status"],
        "lifecycle_phase": state["lifecycle_phase"],
        "workspace_path": str(workspace.resolve()),
        "focus_binding": _focus_binding(workspace, state),
        "consumer": consumer,
    }


def _load_handoff_payload(workspace: Path) -> dict[str, Any] | None:
    path = workspace / "handoff-to-specify.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def _normalized_resolve_intent(intent: str) -> str:
    normalized = str(intent or "").strip().lower()
    aliases = {
        "resume": "continue",
        "continue_current": "continue",
        "specify": "sp-specify",
        "quick": "sp-quick",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"continue", "sp-specify", "sp-quick"}:
        raise ValueError("discussion resolve intent must be continue, sp-specify, or sp-quick")
    return normalized


def resolve_discussion(
    project_root: Path,
    intent: str,
    slug: str = "",
) -> dict[str, Any]:
    normalized_intent = _normalized_resolve_intent(intent)
    requested_slug = str(slug or "").strip()
    if requested_slug:
        workspace, _archived = _find_workspace(
            project_root, requested_slug, include_archived=False
        )
        state, _legacy = _load_state(workspace)
        handoff_payload = _load_handoff_payload(workspace)
        validation = None
        eligible = state.get("status") in INCOMPLETE_STATUSES
        if normalized_intent in {"sp-specify", "sp-quick"}:
            eligible = (
                state.get("status") == "handoff-ready"
                and state.get("lifecycle_phase") == "ready"
                and state.get("consumption", {}).get("status") == "not_consumed"
                and handoff_payload is not None
                and handoff_payload.get("status") == "handoff-ready"
            )
            if eligible:
                validation = validate_handoff(
                    project_root, state["slug"], validation_mode="ready"
                )
                state_handoff = state.get("handoff", {})
                eligible = (
                    validation.get("valid") is True
                    and handoff_payload.get("recommended_consumer")
                    == normalized_intent
                    and state_handoff.get("recommended_consumer")
                    == normalized_intent
                    and state_handoff.get("review_digest")
                    == handoff_payload.get("review_digest")
                    and state_handoff.get("contract_path")
                    == handoff_payload.get("source_contract")
                )
        candidate = _discussion_candidate(
            workspace,
            state,
            handoff_payload=handoff_payload,
            validation=validation,
        )
        if not eligible:
            return {
                "resolved": False,
                "ambiguous": False,
                "intent": normalized_intent,
                "resolution": "explicit_slug_not_eligible",
                "binding": None,
                "discussion": None,
                "consumer": None,
                "candidates": [],
                "reason": "explicit_slug_not_eligible",
            }
        binding = candidate["focus_binding"]
        if normalized_intent != "continue":
            binding["consumer"] = copy.deepcopy(candidate["consumer"])
        return {
            "resolved": True,
            "ambiguous": False,
            "intent": normalized_intent,
            "resolution": "resolved",
            "binding": binding,
            "discussion": candidate,
            "consumer": candidate["consumer"],
            "candidates": [candidate],
        }

    candidates: list[dict[str, Any]] = []
    for workspace, archived in _workspace_candidates(project_root, include_archived=False):
        if archived:
            continue
        try:
            state, _legacy = _load_state(workspace)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if normalized_intent == "continue":
            if state.get("status") in INCOMPLETE_STATUSES:
                candidates.append(_discussion_candidate(workspace, state))
            continue
        if (
            state.get("status") != "handoff-ready"
            or state.get("lifecycle_phase") != "ready"
            or state.get("consumption", {}).get("status") != "not_consumed"
        ):
            continue
        try:
            validation = validate_handoff(
                project_root, state["slug"], validation_mode="ready"
            )
            handoff_payload = _load_handoff_payload(workspace)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not validation.get("valid") or not handoff_payload:
            continue
        if handoff_payload.get("status") != "handoff-ready":
            continue
        if handoff_payload.get("recommended_consumer") != normalized_intent:
            continue
        state_handoff = state.get("handoff", {})
        if (
            state_handoff.get("recommended_consumer") != normalized_intent
            or state_handoff.get("review_digest")
            != handoff_payload.get("review_digest")
            or state_handoff.get("contract_path")
            != handoff_payload.get("source_contract")
        ):
            continue
        candidates.append(
            _discussion_candidate(
                workspace,
                state,
                handoff_payload=handoff_payload,
                validation=validation,
            )
        )

    candidates = sorted(candidates, key=lambda item: (item["slug"], item["summary"]))
    if len(candidates) == 1:
        candidate = candidates[0]
        binding = candidate["focus_binding"]
        if normalized_intent != "continue":
            binding["consumer"] = copy.deepcopy(candidate["consumer"])
        return {
            "resolved": True,
            "ambiguous": False,
            "intent": normalized_intent,
            "resolution": "resolved",
            "binding": binding,
            "discussion": candidate,
            "consumer": candidate["consumer"],
            "candidates": candidates,
        }
    return {
        "resolved": False,
        "ambiguous": len(candidates) > 1,
        "intent": normalized_intent,
        "resolution": "ambiguous" if len(candidates) > 1 else "none",
        "binding": None,
        "discussion": None,
        "consumer": None,
        "candidates": candidates,
        "reason": "ambiguous_candidates" if len(candidates) > 1 else "no_matching_discussion",
    }


def _main_dispatch(
    project_root: Path,
    mode: str,
    slug: str,
    value: str,
    include_all: bool,
    expected_state_sha256: str,
    *,
    _lock_held: bool = False,
) -> dict[str, Any]:
    if mode == "init":
        result = initialize_discussion(
            project_root,
            slug,
            value,
            _lock_held=_lock_held,
        )
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
        result = checkpoint_discussion(
            project_root,
            slug,
            changes,
            expected_state_sha256,
            _lock_held=_lock_held,
        )
    elif mode == "write-handoff":
        raise ValueError(
            "write-handoff file input is disabled; pass the in-memory draft through "
            "write-handoff-json"
        )
    elif mode == "write-handoff-json":
        try:
            handoff_payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("handoff input is not valid JSON") from exc
        if not isinstance(handoff_payload, dict):
            raise ValueError("handoff input must be a JSON object")
        result = write_handoff(
            project_root,
            slug,
            handoff_payload,
            expected_state_sha256,
            _lock_held=_lock_held,
        )
    elif mode == "validate-handoff":
        result = validate_handoff(
            project_root,
            slug,
            validation_mode=value or "ready",
        )
    elif mode == "confirm-handoff":
        result = confirm_handoff(
            project_root,
            slug,
            value,
            _lock_held=_lock_held,
        )
    elif mode == "mark-ready":
        result = mark_ready(project_root, slug, _lock_held=_lock_held)
    elif mode == "mark-consumed":
        result = mark_consumed(project_root, slug, value, _lock_held=_lock_held)
    elif mode == "close":
        result = close_discussion(
            project_root,
            slug,
            value.lower(),
            _lock_held=_lock_held,
        )
    elif mode == "archive":
        result = archive_discussion(project_root, slug, _lock_held=_lock_held)
    elif mode == "rebuild-index":
        result = rebuild_index(project_root, _lock_held=_lock_held)
    elif mode == "resolve":
        result = resolve_discussion(project_root, value or "continue", slug)
    else:
        raise ValueError(f"unknown mode: {mode}")
    return result


def main() -> int:
    project_root = Path(sys.argv[1]).resolve()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "list").strip().lower()
    slug = (sys.argv[3] if len(sys.argv) > 3 else "").strip()
    value = (sys.argv[4] if len(sys.argv) > 4 else "").strip()
    include_all = (
        sys.argv[5] if len(sys.argv) > 5 else "false"
    ).strip().lower() == "true"
    expected_state_sha256 = (sys.argv[6] if len(sys.argv) > 6 else "").strip()
    if mode in MUTATION_MODES:
        with _discussion_mutation_lock(project_root):
            result = _main_dispatch(
                project_root,
                mode,
                slug,
                value,
                include_all,
                expected_state_sha256,
                _lock_held=True,
            )
    else:
        result = _main_dispatch(
            project_root,
            mode,
            slug,
            value,
            include_all,
            expected_state_sha256,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
