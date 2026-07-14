"""Validation hooks for workflow artifact completeness."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from specify_cli.execution.implementation_review import task_review_is_accepted
from specify_cli.execution.ui_validation import (
    markdown_ui_task_ids,
    resolve_feature_artifact_ref,
    task_index_ui_contracts,
    ui_task_ids,
    validate_lifecycle_ui_verification,
)
from specify_cli.implement_audit import _packetized_task_ids, _task_review_record_from_payload
from specify_cli.project_cognition_tool import ProjectCognitionToolError, run_project_cognition

from .checkpoint_serializers import extract_field, normalize_command_name
from .events import WORKFLOW_ARTIFACTS_VALIDATE
from .types import HookResult, QualityHookError

FILE_REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": (
        "spec-contract.json",
        "spec.md",
        "workflow-state.md",
    ),
    "clarify": (
        "spec.md",
        "alignment.md",
        "context.md",
        "references.md",
        "workflow-state.md",
        "clarification/evidence-index.json",
        "clarification/checkpoints.ndjson",
    ),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": (
        "plan.md",
        "workflow-state.md",
    ),
    "tasks": (
        "tasks.md",
        "workflow-state.md",
    ),
    "analyze": ("workflow-state.md",),
    "implement": ("implement-tracker.md",),
    "map-scan": (
        "status.json",
        "coverage.json",
        "provisional/nodes.json",
        "provisional/edges.json",
        "provisional/observations.json",
    ),
    "map-build": (
        "status.json",
        "project-cognition.db",
    ),
    "map-update": (
        "status.json",
        "project-cognition.db",
    ),
    "prd-scan": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
    ),
    "prd-build": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "master/master-pack.md",
        "exports/README.md",
        "exports/prd.md",
        "exports/reconstruction-appendix.md",
        "exports/data-model.md",
        "exports/integration-contracts.md",
        "exports/runtime-behaviors.md",
    ),
    "prd": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
    ),
}

DIRECTORY_REQUIRED_ARTIFACTS = {
    "specify": (),
    "clarify": ("clarification/handoffs",),
    "plan": (),
    "tasks": (),
    "map-scan": ("evidence",),
    "prd-scan": ("scan-packets", "evidence", "worker-results"),
    "prd-build": ("scan-packets", "evidence", "worker-results"),
    "prd": ("scan-packets", "evidence", "worker-results"),
}


SPECIFY_LOSSLESS_REQUIRED_ARTIFACTS = frozenset(
    {
        "brainstorming/journal.ndjson",
        "brainstorming/stage-manifest.json",
        "brainstorming/domains.json",
        "brainstorming/evidence-index.json",
        "brainstorming/evidence",
    }
)


REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": (
        "spec-contract.json",
        "spec.md",
        "workflow-state.md",
    ),
    "clarify": (
        "spec.md",
        "alignment.md",
        "context.md",
        "references.md",
        "workflow-state.md",
        "clarification/evidence-index.json",
        "clarification/checkpoints.ndjson",
        "clarification/handoffs",
    ),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": (
        "plan.md",
        "workflow-state.md",
    ),
    "tasks": (
        "tasks.md",
        "workflow-state.md",
    ),
    "analyze": ("workflow-state.md",),
    "implement": ("implement-tracker.md",),
    "map-scan": (
        "status.json",
        "coverage.json",
        "provisional/nodes.json",
        "provisional/edges.json",
        "provisional/observations.json",
        "evidence",
    ),
    "map-build": (
        "status.json",
        "project-cognition.db",
    ),
    "map-update": (
        "status.json",
        "project-cognition.db",
    ),
    "prd-scan": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "scan-packets",
        "evidence",
        "worker-results",
    ),
    "prd-build": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "scan-packets",
        "evidence",
        "worker-results",
        "master/master-pack.md",
        "exports/README.md",
        "exports/prd.md",
    ),
    "prd": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "scan-packets",
        "evidence",
        "worker-results",
    ),
}

DEEP_RESEARCH_REQUIRED_SECTIONS = (
    "## Planning Handoff",
    "## Evidence Quality Rubric",
    "## Planning Traceability Index",
)

DEEP_RESEARCH_HANDOFF_FIELDS = (
    "**Handoff IDs**",
    "**Recommended approach**",
    "**Architecture implications**",
    "**Module boundaries**",
    "**API / library choices**",
    "**Data flow notes**",
    "**Demo artifacts to reference**",
    "**Constraints `/sp.plan` must preserve**",
    "**Validation implications**",
    "**Residual risks requiring design mitigation**",
    "**Decisions already proven by research**",
)

PLAN_DEEP_RESEARCH_TRACEABILITY_COLUMNS = (
    "Plan Decision",
    "Handoff ID",
    "Evidence / Spike ID",
    "Evidence Quality",
    "Plan Action",
)

DEEP_RESEARCH_NOT_NEEDED_REQUIRED_SECTIONS = (
    "## Feasibility Decision",
    "## Planning Handoff",
    "## Next Command",
)

SPECIFY_LEGACY_DRAFT_REQUIRED_HEADINGS = (
    "## Intent Analysis Record",
    "## Domain Progress Ledger",
    "## Question Batch Ledger",
    "## Adversarial Review Ledger",
    "## Completeness Gap Register",
    "## Final Audit Inputs",
)

SPECIFY_LEGACY_ALIGNMENT_REQUIRED_HEADINGS = ("## Alignment Summary",)

SPECIFY_LEGACY_CONTEXT_REQUIRED_HEADINGS = ("## Change Propagation Matrix",)

SPECIFY_ALIGNMENT_REQUIRED_HEADINGS = (
    "## Semantic Term Decisions",
    "## Upstream Intent Disposition",
    "## Out-Of-Scope Conflicts",
)

SPECIFY_CONTEXT_REQUIRED_HEADINGS = ("## Planning Context",)

PRD_BUILD_REQUIRED_EXPORTS = (
    "exports/README.md",
    "exports/reconstruction-appendix.md",
    "exports/data-model.md",
    "exports/integration-contracts.md",
    "exports/runtime-behaviors.md",
)

PRD_BUILD_REQUIRED_HEAVY_EXPORTS = (
    "exports/config-contracts.md",
    "exports/protocol-contracts.md",
    "exports/state-machines.md",
    "exports/error-semantics.md",
    "exports/verification-surface.md",
    "exports/reconstruction-risks.md",
)

PRD_HEAVY_SCAN_JSON_ARTIFACTS = {
    "entrypoint-ledger.json": "entrypoints",
    "config-contracts.json": "configs",
    "protocol-contracts.json": "protocols",
    "state-machines.json": "machines",
    "error-semantics.json": "errors",
    "verification-surfaces.json": "surfaces",
}

PRD_WORKER_RESULT_REQUIRED_KEYS = frozenset(
    {
        "paths_read",
        "unknowns",
        "confidence",
        "recommended_ledger_updates",
    }
)

GRAPH_NODE_REQUIRED_KEYS = frozenset({"nodes"})
GRAPH_EDGE_REQUIRED_KEYS = frozenset({"edges"})
GRAPH_CLAIM_REQUIRED_KEYS = frozenset({"claims"})
GRAPH_CONFLICT_REQUIRED_KEYS = frozenset({"conflicts"})
MP_REQUIRED_KEYS = frozenset(
    {
        "id",
        "type",
        "claim",
        "source",
        "downstream_requirement",
        "owner",
        "latest_resolve_phase",
        "status",
        "mapped_to",
    }
)
MP_ACTIVE_STATUSES = frozenset({"pending", "mapped"})
MP_CLOSED_STATUSES = frozenset({"resolved", "superseded", "dropped", "deferred"})
MP_VALID_STATUSES = MP_ACTIVE_STATUSES | MP_CLOSED_STATUSES
MP_ID_RE = re.compile(r"^MP-\d{3}$")
MP_VALID_TYPES = frozenset(
    {
        "goal",
        "scope",
        "non_goal",
        "scenario",
        "decision",
        "reference",
        "tradeoff",
        "blocking_question",
    }
)
MP_VALID_COVERAGE_STATUSES = frozenset(
    {"not_started", "incomplete", "complete", "blocked_by_handoff_integrity"}
)
MP_VALID_PLANNING_GATE_STATUSES = frozenset(
    {
        "ready",
        "blocked_by_hard_unknowns",
        "blocked_by_conflict",
        "blocked_by_incomplete_coverage",
        "blocked_by_handoff_integrity",
    }
)
SOURCE_EVIDENCE_REQUIRED_FIELDS = ("source_type", "evidence_status", "source", "claim")
SOURCE_EVIDENCE_ALLOWED_TYPES = frozenset(
    {
        "project_cognition_route",
        "live_code_evidence",
        "user_confirmation",
        "explicit_assumption",
        "external_source",
        "missing",
        "conflict",
    }
)
SOURCE_EVIDENCE_ALLOWED_STATUSES = frozenset(
    {
        "proven",
        "inferred",
        "stale-advisory",
        "missing",
        "conflict",
    }
)
GRAPH_UPDATE_REQUIRED_KEYS = frozenset({"updates"})

CONSEQUENCE_ANALYSIS_REQUIRED_KEYS = (
    "affected_object_map",
    "state_behavior_matrix",
    "dependency_impact",
    "recovery_and_validation",
    "coverage_gaps",
)

CONSEQUENCE_OBLIGATION_REQUIRED_KEYS = (
    "obligation_id",
    "claim",
    "affected_objects",
    "owner",
    "latest_resolve_phase",
    "status",
    "stop_and_reopen_condition",
)

CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION = "## Operational Consequence Design"
CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION = "## Consequence Obligation Mapping"

PRD_RECONSTRUCTION_READY_STATUSES = frozenset(
    {
        "reconstruction-ready",
        "l4 reconstruction-ready",
    }
)

PRD_EXPORT_REQUIRED_SECTIONS = (
    "## Capability Overview",
    "## Critical Capability Notes",
    "## Unknowns and Evidence Confidence",
)

REFERENCE_IMPLEMENTATION_PROFILE = "reference-implementation"

REFERENCE_IMPLEMENTATION_SPEC_REQUIRED_SECTIONS = (
    "## Fidelity Requirements",
    "### Reference Object",
    "### Required Fidelity",
    "### Reference Behavior Inventory",
)

REFERENCE_IMPLEMENTATION_SECTION_HEADINGS = {
    "fidelity requirements": "## Fidelity Requirements",
    "reference object": "### Reference Object",
    "required fidelity": "### Required Fidelity",
    "reference behavior inventory": "### Reference Behavior Inventory",
    "reference fidelity": "## Fidelity Requirements",
}

LOSSLESS_SPECIFY_STAGES = {
    "intake",
    "evidence-intake",
    "facts-lock",
    "route-lock",
    "intent-lock",
    "complexity-lock",
    "domain-clarification",
    "consequence-risk",
    "specify-compile",
    "release-decision",
}

LOSSLESS_SPECIFY_STAGE_ARTIFACTS = {
    "intake": "workflow-state.md",
    "evidence-intake": "brainstorming/evidence-index.json",
    "facts-lock": "brainstorming/facts.json",
    "route-lock": "brainstorming/route.json",
    "intent-lock": "brainstorming/intent.json",
    "complexity-lock": "brainstorming/complexity.json",
    "domain-clarification": "brainstorming/domains.json",
    "consequence-risk": "brainstorming/handoff-to-specify.json",
    "specify-compile": "spec.md",
    "release-decision": "workflow-state.md",
}

LOSSLESS_SPECIFY_ARTIFACT_STAGES = {
    "brainstorming/facts.json": "facts-lock",
    "brainstorming/route.json": "route-lock",
    "brainstorming/intent.json": "intent-lock",
    "brainstorming/complexity.json": "complexity-lock",
    "brainstorming/domains.json": "domain-clarification",
    "brainstorming/evidence-index.json": "evidence-intake",
    "brainstorming/handoff-to-specify.json": "consequence-risk",
}

LOSSLESS_SPECIFY_EVENT_TYPES = frozenset(
    {
        "session_started",
        "feature_workspace_created",
        "user_input_captured",
        "question_asked",
        "answer_recorded",
        "repo_evidence_captured",
        "research_evidence_captured",
        "unknown_opened",
        "unknown_resolved",
        "unknown_deferred",
        "unknown_waived",
        "decision_locked",
        "route_selected",
        "complexity_selected",
        "stage_artifact_compiled",
        "reopen_requested",
        "artifact_compiled",
        "checkpoint_written",
        "legacy_state_imported",
    }
)

PRD_COVERAGE_REQUIRED_TOKENS = (
    "Tier",
    "Depth Status",
    "Overall Status",
)

PRD_OPTIONAL_CONTROL_ARTIFACTS: dict[str, tuple[Path, tuple[str, ...]]] = {
    "capability-triage.md": (
        Path("capability-triage.md"),
        ("## Core Value Proposition", "## Capability Tiers"),
    ),
    "depth-policy.md": (
        Path("depth-policy.md"),
        ("## Tier Expectations",),
    ),
    "quality-check.md": (
        Path("quality-check.md"),
        ("## Gates",),
    ),
}
DEEP_RESEARCH_NOT_NEEDED_STATUS_RE = re.compile(
    r"(?im)^\*\*Status\*\*:\s*(?:\[)?Not needed(?:\])?\s*$"
)
IMPLEMENT_TASK_RE = re.compile(r"(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b")


def _extract_markdown_section(content: str, heading: str) -> str:
    heading_match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", content)
    if not heading_match:
        return ""

    section_body = content[heading_match.end() :]
    next_heading = re.search(r"(?m)^##\s+", section_body)
    if next_heading:
        return section_body[: next_heading.start()]
    return section_body


def _validate_markdown_contains(path: Path, required_items: tuple[str, ...], label: str) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    return [f"{label} is missing required section: {item}" for item in required_items if item not in content]


def _validate_markdown_headings(path: Path, required_headings: tuple[str, ...], label: str) -> list[str]:
    if path.exists() and path.is_dir():
        return [f"{label} must be a file, not a directory"]
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"{label} could not be read: {exc}"]
    present_headings = {match.group(0).strip() for match in re.finditer(r"(?m)^#{1,6}\s+.+$", content)}
    return [
        f"{label} is missing required heading: {heading}"
        for heading in required_headings
        if heading not in present_headings
    ]


def _normalize_bullet_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    return cleaned


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _read_json_artifact(path: Path, label: str) -> tuple[Any | None, list[str]]:
    if path.exists() and path.is_dir():
        return None, [f"{label} must be a file, not a directory"]
    try:
        return _read_json(path), []
    except OSError as exc:
        return None, [f"{label} could not be read: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label} is not valid JSON: {exc}"]


def _validate_json_object_with_array_key(feature_dir: Path, filename: str, array_key: str) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / filename, filename)
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return [f"{filename} must contain a top-level JSON object"]
    if not isinstance(payload.get(array_key), list):
        return [f"{filename} must define a top-level {array_key} array"]
    return []


def _validate_unknown_objects(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be a JSON object"]
    unknowns = payload.get("unknowns", [])
    if unknowns is None:
        return []
    if not isinstance(unknowns, list):
        return [f"{label} unknowns must be a list"]
    errors: list[str] = []
    required_keys = ("field", "question", "blocking_level", "resolver", "latest_resolve_phase", "status")
    for index, item in enumerate(unknowns):
        if not isinstance(item, dict):
            errors.append(f"{label} unknowns[{index}] must be an object")
            continue
        for key in required_keys:
            if not str(item.get(key, "")).strip():
                errors.append(f"{label} unknowns[{index}] missing {key}")
    return errors


def _checked_implement_task_ids(feature_dir: Path) -> list[str]:
    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.is_file():
        return []
    content = tasks_path.read_text(encoding="utf-8", errors="replace")
    return sorted(
        {
            match.group("task_id").upper()
            for match in IMPLEMENT_TASK_RE.finditer(content)
            if match.group("checked").lower() == "x"
        }
    )


def _all_implement_task_ids(feature_dir: Path) -> set[str]:
    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.is_file():
        return set()
    content = tasks_path.read_text(encoding="utf-8", errors="replace")
    return {match.group("task_id").upper() for match in IMPLEMENT_TASK_RE.finditer(content)}


def _validate_accepted_task_review(feature_dir: Path, task_id: str, review_relative: str) -> list[str]:
    review_path = feature_dir / review_relative
    if not review_path.is_file():
        return [f"{review_relative} is missing for accepted packetized task {task_id}"]
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("task review must contain a JSON object")
        record = _task_review_record_from_payload(payload)
        if not isinstance(record.task_id, str) or record.task_id.upper() != task_id:
            return [f"{task_id} task review has mismatched task_id at {review_relative}"]
        if not task_review_is_accepted(record):
            return [f"{task_id} task review is not accepted at {review_relative}"]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return [f"{task_id} task review is malformed at {review_relative}: {exc}"]
    return []


def _validate_accepted_ledger_artifact_reference(
    feature_dir: Path,
    ledger_relative: str,
    task_id: str,
    entry: dict[str, Any],
    field_name: str,
    expected_relative: str,
) -> list[str]:
    value = entry.get(field_name)
    if value != expected_relative:
        return [f"{task_id} in {ledger_relative} must reference {expected_relative}"]
    if not (feature_dir / expected_relative).is_file():
        return [f"{expected_relative} is missing for accepted packetized task {task_id}"]
    return []


def _validate_task_lifecycle_records(
    feature_dir: Path,
    task_ids: list[str],
) -> list[str]:
    errors: list[str] = []
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    ui_tasks = ui_task_ids(feature_dir)
    for task_id in task_ids:
        relative = f"implementation-review/tasks/{task_id}.json"
        payload, read_errors = _read_json_artifact(
            lifecycle_dir / f"{task_id}.json", relative
        )
        if read_errors:
            errors.extend(read_errors)
            continue
        if not isinstance(payload, dict):
            errors.append(f"{relative} must contain a top-level object")
            continue
        if str(payload.get("task_id") or "").upper() != task_id:
            errors.append(f"{relative} has mismatched task_id")
        if payload.get("status") != "accepted":
            errors.append(f"{relative} status must be accepted")
        if not isinstance(payload.get("changed_paths"), list):
            errors.append(f"{relative} changed_paths must be a list")
        validation = payload.get("validation")
        if not isinstance(validation, list) or not validation:
            errors.append(f"{relative} validation must be a non-empty list")
        if not isinstance(payload.get("blockers"), list):
            errors.append(f"{relative} blockers must be a list")
        review = payload.get("review")
        if review is not None and (
            not isinstance(review, dict)
            or not str(review.get("trigger") or "").strip()
            or not str(review.get("verdict") or "").strip()
        ):
            errors.append(f"{relative} review must contain trigger and verdict when present")
        if task_id in ui_tasks:
            errors.extend(
                validate_lifecycle_ui_verification(feature_dir, payload, relative)
            )
    return errors


def _uses_agent_native_task_lifecycle(feature_dir: Path) -> bool:
    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return False
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(payload, dict):
        return False
    version = payload.get("version")
    return isinstance(version, int) and not isinstance(version, bool) and version >= 2


def _validate_packetized_implement_review_artifacts(feature_dir: Path) -> list[str]:
    checked_task_id_set = set(_checked_implement_task_ids(feature_dir))
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    if lifecycle_dir.is_dir() or _uses_agent_native_task_lifecycle(feature_dir):
        return _validate_task_lifecycle_records(
            feature_dir, sorted(checked_task_id_set)
        )

    packet_task_id_list, packet_errors = _packetized_task_ids(feature_dir)
    packet_task_ids = set(packet_task_id_list)
    checked_task_ids = sorted(checked_task_id_set & packet_task_ids)

    errors: list[str] = []
    errors.extend(packet_errors)
    all_task_ids = _all_implement_task_ids(feature_dir)
    for packet_task_id in sorted(packet_task_ids - checked_task_id_set):
        reason = "unchecked in tasks.md" if packet_task_id in all_task_ids else "missing checked task in tasks.md"
        errors.append(f"{packet_task_id} packetized task is not checked: {reason}")

    if not checked_task_ids:
        return errors

    ledger_relative = "implementation-review/ledger.json"
    branch_review_relative = "implementation-review/branch-review.md"
    ledger_path = feature_dir / ledger_relative
    if not ledger_path.is_file():
        errors.append(f"{ledger_relative} is missing for packetized checked implement tasks")
        return errors

    payload, read_errors = _read_json_artifact(ledger_path, ledger_relative)
    if read_errors:
        errors.extend(read_errors)
        return errors
    if not isinstance(payload, dict):
        errors.append(f"{ledger_relative} must contain a top-level JSON object")
        return errors
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        errors.append(f"{ledger_relative} must define a top-level tasks array")
        return errors

    entries_by_task: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(tasks):
        if not isinstance(item, dict):
            errors.append(f"{ledger_relative} tasks[{index}] must be an object")
            continue
        task_id = item.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"{ledger_relative} tasks[{index}] missing task_id")
            continue
        entries_by_task[task_id.upper()] = item

    for task_id in checked_task_ids:
        entry = entries_by_task.get(task_id)
        expected_brief = f"implementation-review/task-briefs/{task_id}.md"
        expected_package = f"implementation-review/review-packages/{task_id}.md"
        expected_review = f"implementation-review/task-reviews/{task_id}.json"
        if entry is None:
            errors.append(f"{task_id} is missing from {ledger_relative}")
            continue
        if entry.get("status") != "accepted":
            errors.append(f"{task_id} in {ledger_relative} must have status accepted")
            continue
        brief_errors = _validate_accepted_ledger_artifact_reference(
            feature_dir, ledger_relative, task_id, entry, "task_brief", expected_brief
        )
        package_errors = _validate_accepted_ledger_artifact_reference(
            feature_dir, ledger_relative, task_id, entry, "review_package", expected_package
        )
        review_errors = _validate_accepted_ledger_artifact_reference(
            feature_dir, ledger_relative, task_id, entry, "task_review", expected_review
        )
        errors.extend(brief_errors)
        errors.extend(package_errors)
        errors.extend(review_errors)
        if not review_errors:
            errors.extend(_validate_accepted_task_review(feature_dir, task_id, expected_review))

    if not (feature_dir / branch_review_relative).is_file():
        errors.append(f"{branch_review_relative} is missing for packetized checked implement tasks")
    return errors


def _validate_must_preserve_items(payload: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    items = payload.get("must_preserve", [])
    if items is None:
        return errors
    if not isinstance(items, list):
        return [f"{label} must_preserve must be a list"]

    coverage_status = str(payload.get("coverage_status") or "").strip()
    for index, item in enumerate(items):
        item_label = f"{label} must_preserve[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        mp_id = str(item.get("id") or f"item {index}").strip()
        missing = sorted(
            key for key in MP_REQUIRED_KEYS if key != "mapped_to" and not str(item.get(key, "")).strip()
        )
        for key in missing:
            errors.append(f"{item_label} {mp_id} missing {key}")
        if not MP_ID_RE.match(str(item.get("id") or "").strip()):
            errors.append(f"{item_label} {mp_id} id must use MP-### format")
        if str(item.get("type") or "").strip() not in MP_VALID_TYPES:
            errors.append(f"{item_label} {mp_id} has invalid type")
        status = str(item.get("status") or "").strip()
        if status not in MP_VALID_STATUSES:
            errors.append(f"{item_label} {mp_id} has invalid status")
        mapped_to = item.get("mapped_to")
        if not isinstance(mapped_to, list):
            errors.append(f"{item_label} {mp_id} mapped_to must be a list")
            mapped_to = []
        if coverage_status == "complete" and status in MP_ACTIVE_STATUSES and not mapped_to:
            errors.append(f"{item_label} {mp_id} is active but missing mapped_to coverage")
        if status == "deferred":
            for key in ("deferred_to", "owner", "latest_resolve_phase", "stop_and_reopen_condition"):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{item_label} {mp_id} deferred item missing {key}")
            if not str(item.get("approved_risk_contract") or "").strip():
                errors.append(f"{item_label} {mp_id} deferred item missing approved_risk_contract")
        if status == "superseded" and not str(item.get("superseded_by") or "").strip():
            errors.append(f"{item_label} {mp_id} superseded item missing superseded_by")
        if status == "resolved" and not str(item.get("resolution_evidence") or "").strip():
            errors.append(f"{item_label} {mp_id} resolved item missing resolution_evidence")
        if status == "dropped":
            if not str(item.get("user_decision_source") or "").strip():
                errors.append(f"{item_label} {mp_id} dropped item missing user_decision_source")
            if not str(item.get("approved_risk_contract") or "").strip():
                errors.append(f"{item_label} {mp_id} dropped item missing approved_risk_contract")
    return errors


def _validate_conflict_records(payload: dict[str, Any], label: str) -> list[str]:
    conflicts = payload.get("conflicts", [])
    if conflicts is None:
        return []
    if not isinstance(conflicts, list):
        return [f"{label} conflicts must be a list"]

    errors: list[str] = []
    for index, item in enumerate(conflicts):
        conflict_label = f"{label} conflicts[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{conflict_label} must be an object")
            continue
        status = str(item.get("status") or "").strip()
        resolution = str(item.get("resolution") or "none").strip()
        if status not in {"open", "closed"}:
            errors.append(f"{conflict_label} has invalid status")
        if resolution not in {"keep", "revise", "drop", "defer", "none"}:
            errors.append(f"{conflict_label} has invalid resolution")
        if status == "closed":
            if resolution == "none":
                errors.append(f"{conflict_label} closed conflict missing resolution")
            if not str(item.get("user_decision_source") or "").strip():
                errors.append(f"{conflict_label} closed conflict missing user_decision_source")
            if resolution == "revise" and not str(item.get("superseded_by") or "").strip():
                errors.append(f"{conflict_label} revise resolution missing superseded_by")
            if resolution in {"drop", "defer"} and not str(item.get("approved_risk_contract") or "").strip():
                errors.append(f"{conflict_label} {resolution} resolution missing approved_risk_contract")
    return errors


def _derived_open_conflict_count(payload: dict[str, Any]) -> int:
    conflicts = payload.get("conflicts", [])
    if not isinstance(conflicts, list):
        return 0
    return sum(
        1
        for item in conflicts
        if isinstance(item, dict) and str(item.get("status") or "").strip() == "open"
    )


def _validate_source_evidence_entries(payload: dict[str, Any], label: str) -> list[str]:
    version = payload.get("version")
    if "source_evidence" not in payload:
        if version == 2:
            return [f"{label} source_evidence is required"]
        return []
    source_evidence = payload.get("source_evidence")
    if not isinstance(source_evidence, list):
        return [f"{label} source_evidence must be an array"]

    errors: list[str] = []
    status = str(payload.get("status") or "").strip()
    coverage_status = str(payload.get("coverage_status") or "").strip()
    planning_gate_status = str(payload.get("planning_gate_status") or "").strip()
    if (
        not source_evidence
        and (
            status in {"ready", "user-confirmed"}
            or (version == 2 and coverage_status == "complete")
            or (version == 2 and planning_gate_status == "ready")
            or (version == 2 and payload.get("compile_ready") is True)
        )
    ):
        errors.append(f"{label} source_evidence must include at least one entry")

    for index, item in enumerate(source_evidence):
        item_label = f"{label} source_evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue

        for field in SOURCE_EVIDENCE_REQUIRED_FIELDS:
            value = item.get(field)
            if not isinstance(value, str):
                errors.append(f"{item_label}.{field} must be a non-empty string")
                continue
            if not value.strip():
                errors.append(f"{item_label}.{field} is required")

        source_type = str(item.get("source_type") or "").strip()
        evidence_status = str(item.get("evidence_status") or "").strip()
        if source_type and source_type not in SOURCE_EVIDENCE_ALLOWED_TYPES:
            errors.append(f"{item_label}.source_type is invalid")
        if evidence_status and evidence_status not in SOURCE_EVIDENCE_ALLOWED_STATUSES:
            errors.append(f"{item_label}.evidence_status is invalid")

        for field in ("project_cognition_route", "live_code_evidence"):
            value = item.get(field)
            if value is None:
                continue
            if not (
                isinstance(value, list)
                and all(isinstance(entry, str) and entry.strip() for entry in value)
            ):
                errors.append(f"{item_label}.{field} must be an array of non-empty strings")

        needs_refresh = item.get("needs_refresh")
        if needs_refresh is not None and not isinstance(needs_refresh, bool):
            errors.append(f"{item_label}.needs_refresh must be a boolean")

    return errors


def _is_validly_closed_hard_blocking_question(item: dict[str, Any]) -> bool:
    status = str(item.get("status") or "").strip()
    if status == "resolved":
        return bool(str(item.get("resolution_evidence") or "").strip())
    if status == "superseded":
        return bool(str(item.get("superseded_by") or "").strip())
    if status == "dropped":
        return bool(
            str(item.get("user_decision_source") or "").strip()
            and str(item.get("approved_risk_contract") or "").strip()
        )
    if status == "deferred":
        return bool(
            str(item.get("deferred_to") or "").strip()
            and str(item.get("owner") or "").strip()
            and str(item.get("latest_resolve_phase") or "").strip()
            and str(item.get("stop_and_reopen_condition") or "").strip()
            and str(item.get("approved_risk_contract") or "").strip()
        )
    return False


def _derived_hard_unknown_count(payload: dict[str, Any]) -> int:
    count = 0
    unknowns = payload.get("unknowns", [])
    if isinstance(unknowns, list):
        count += sum(
            1
            for item in unknowns
            if isinstance(item, dict)
            and str(item.get("blocking_level") or "").strip() == "hard"
            and str(item.get("status") or "").strip() not in MP_CLOSED_STATUSES
        )

    must_preserve = payload.get("must_preserve", [])
    if isinstance(must_preserve, list):
        count += sum(
            1
            for item in must_preserve
            if isinstance(item, dict)
            and str(item.get("type") or "").strip() == "blocking_question"
            and str(item.get("blocking_level") or "").strip() == "hard"
            and not _is_validly_closed_hard_blocking_question(item)
        )
    return count


def _validate_handoff_to_specify_payload(payload: Any, label: str) -> list[str]:
    errors = _validate_unknown_objects(payload, label)
    if not isinstance(payload, dict):
        return errors

    source_contract = str(payload.get("source_contract") or "").strip()
    if source_contract:
        if not str(payload.get("review_digest") or "").strip():
            errors.append(f"{label} review_digest is required")
        for field in ("semantic_delta", "required_refs", "blockers"):
            if not isinstance(payload.get(field), list):
                errors.append(f"{label} {field} must be a list")
        if not str(payload.get("next_action") or "").strip():
            errors.append(f"{label} next_action is required")
        return errors

    stage = str(payload.get("stage") or "").strip()
    if stage and stage != "consequence-risk":
        errors.append(f"{label} stage must be consequence-risk, got {stage}")

    coverage_status = str(payload.get("coverage_status") or "").strip()
    planning_gate_status = str(payload.get("planning_gate_status") or "").strip()
    if coverage_status and coverage_status not in MP_VALID_COVERAGE_STATUSES:
        errors.append(f"{label} has invalid coverage_status")
    if planning_gate_status and planning_gate_status not in MP_VALID_PLANNING_GATE_STATUSES:
        errors.append(f"{label} has invalid planning_gate_status")

    errors.extend(_validate_must_preserve_items(payload, label))
    errors.extend(_validate_conflict_records(payload, label))
    errors.extend(_validate_source_evidence_entries(payload, label))
    errors.extend(_validate_source_signal_disposition(payload, label))

    hard_unknown_count = payload.get("hard_unknown_count", 0)
    open_conflict_count = payload.get("open_conflict_count", 0)
    derived_hard_unknown_count = _derived_hard_unknown_count(payload)
    derived_open_conflict_count = _derived_open_conflict_count(payload)
    if isinstance(hard_unknown_count, int) and hard_unknown_count != derived_hard_unknown_count:
        errors.append(
            f"{label} hard_unknown_count does not match open hard unknowns ({derived_hard_unknown_count})"
        )
    if isinstance(open_conflict_count, int) and open_conflict_count != derived_open_conflict_count:
        errors.append(
            f"{label} open_conflict_count does not match open conflicts ({derived_open_conflict_count})"
        )
    if planning_gate_status == "ready":
        if isinstance(hard_unknown_count, int) and hard_unknown_count > 0:
            errors.append(f"{label} planning_gate_status ready is invalid with open hard unknowns")
        if derived_hard_unknown_count > 0:
            errors.append(f"{label} planning_gate_status ready is invalid with open hard unknowns")
        if isinstance(open_conflict_count, int) and open_conflict_count > 0:
            errors.append(f"{label} planning_gate_status ready is invalid with open conflicts")
        if derived_open_conflict_count > 0:
            errors.append(f"{label} planning_gate_status ready is invalid with open conflicts")
        if coverage_status != "complete":
            errors.append(f"{label} planning_gate_status ready requires coverage_status complete")
    if coverage_status == "blocked_by_handoff_integrity" and planning_gate_status != "blocked_by_handoff_integrity":
        errors.append(
            f"{label} handoff integrity blocks must also set planning_gate_status blocked_by_handoff_integrity"
        )
    return errors


def _validate_source_signal_disposition(payload: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    source_files_read = payload.get("source_files_read", [])
    if source_files_read is None:
        source_files_read = []
    if not isinstance(source_files_read, list):
        errors.append(f"{label} source_files_read must be a list")
    elif any(not isinstance(item, str) or not item.strip() for item in source_files_read):
        errors.append(f"{label} source_files_read must contain only non-empty strings")

    dispositions = payload.get("source_signal_disposition", [])
    if dispositions is None:
        dispositions = []
    if not isinstance(dispositions, list):
        errors.append(f"{label} source_signal_disposition must be a list")
        return errors

    entry_source = str(payload.get("entry_source") or "").strip()
    source_handoff = str(payload.get("source_handoff") or "").strip()
    source_handoff_json = str(payload.get("source_handoff_json") or "").strip()
    if entry_source == "sp-discussion" or source_handoff or source_handoff_json:
        if not source_files_read:
            errors.append(f"{label} source_files_read is required for discussion-originated specify handoff")
        if not dispositions:
            errors.append(f"{label} source_signal_disposition is required for discussion-originated specify handoff")

    allowed = {"preserved", "in_scope", "deferred", "dropped", "clarification_blocker"}
    required = ("signal", "source", "disposition", "artifact_location", "user_confirmed", "reopen_trigger")
    for index, item in enumerate(dispositions):
        item_label = f"{label} source_signal_disposition[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        for field in required:
            if field not in item:
                errors.append(f"{item_label} missing {field}")
        disposition = str(item.get("disposition") or "").strip()
        if disposition and disposition not in allowed:
            errors.append(f"{item_label} has invalid disposition")
        if disposition in {"deferred", "dropped", "clarification_blocker"}:
            if not str(item.get("source") or "").strip():
                errors.append(f"{item_label} requires source for {disposition}")
            if not str(item.get("reopen_trigger") or "").strip():
                errors.append(f"{item_label} requires reopen_trigger for {disposition}")
    return errors


def _json_gate_is_triggered(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    gate = payload.get("consequence_gate")
    if not isinstance(gate, dict):
        return False
    return gate.get("triggered") is True


def _validate_consequence_json_payload(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be a JSON object before consequence validation can run"]
    if not _json_gate_is_triggered(payload):
        return []

    errors: list[str] = []
    analysis = payload.get("consequence_analysis")
    if not isinstance(analysis, dict):
        return [f"{label} consequence_analysis must be an object when consequence_gate.triggered is true"]

    for key in CONSEQUENCE_ANALYSIS_REQUIRED_KEYS:
        value = analysis.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"{label} consequence_analysis.{key} must be a non-empty array when the gate is triggered")

    obligations = payload.get("consequence_obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append(f"{label} consequence_obligations must be a non-empty array when the gate is triggered")
        return errors

    for index, obligation in enumerate(obligations):
        if not isinstance(obligation, dict):
            errors.append(f"{label} consequence_obligations[{index}] must be an object")
            continue
        for key in CONSEQUENCE_OBLIGATION_REQUIRED_KEYS:
            value = obligation.get(key)
            if isinstance(value, list):
                if not value:
                    errors.append(f"{label} consequence_obligations[{index}].{key} must not be empty")
            elif not str(value or "").strip():
                errors.append(f"{label} consequence_obligations[{index}].{key} must not be empty")

    return errors


def _consequence_obligation_ids(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    obligations = payload.get("consequence_obligations")
    if not isinstance(obligations, list):
        return set()
    return {
        str(item.get("obligation_id") or "").strip()
        for item in obligations
        if isinstance(item, dict) and str(item.get("obligation_id") or "").strip()
    }


def _consequence_contract_paths(feature_dir: Path) -> tuple[tuple[Path, str], ...]:
    return (
        (feature_dir / "plan-contract.json", "plan-contract.json"),
        (feature_dir / "plan" / "plan-contract.json", "plan/plan-contract.json"),
    )


def _decision_consequence_obligation_ids(decision: Any) -> set[str]:
    if not isinstance(decision, dict):
        return set()
    ids: set[str] = set()
    raw_id = decision.get("obligation_id")
    if isinstance(raw_id, str) and raw_id.strip():
        ids.add(raw_id.strip())
    raw_ids = decision.get("consequence_obligation_ids")
    if isinstance(raw_ids, list):
        ids.update(item.strip() for item in raw_ids if isinstance(item, str) and item.strip())
    elif isinstance(raw_ids, str) and raw_ids.strip():
        ids.add(raw_ids.strip())
    return ids


def _validate_brainstorming_json_artifact(feature_dir: Path, relative_path: str, *, validate_unknowns: bool) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / relative_path, relative_path)
    if read_errors:
        return read_errors
    if validate_unknowns:
        return _validate_unknown_objects(payload, relative_path)
    if not isinstance(payload, dict):
        return [f"{relative_path} must be a JSON object"]
    return []


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_any_non_empty_key(payload: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(_is_non_empty_text(payload.get(key)) for key in keys)


def _require_payload_keys(payload: dict[str, Any], label: str, keys: tuple[str, ...]) -> list[str]:
    return [f"{label} payload missing {key}" for key in keys if not _is_non_empty_text(payload.get(key))]


def _require_payload_any_key(payload: dict[str, Any], label: str, keys: tuple[str, ...], description: str) -> list[str]:
    if _has_any_non_empty_key(payload, keys):
        return []
    return [f"{label} payload missing {description}"]


def _require_payload_basis_or_evidence_ids(payload: dict[str, Any], label: str) -> list[str]:
    if _is_non_empty_text(payload.get("basis")):
        return []
    evidence_ids = payload.get("evidence_ids")
    if (
        isinstance(evidence_ids, list)
        and evidence_ids
        and all(isinstance(item, str) and item.strip() for item in evidence_ids)
    ):
        return []
    return [f"{label} payload missing basis or non-empty evidence_ids"]


def _validate_journal_event_payload(event: dict[str, Any], line_label: str) -> list[str]:
    event_type = str(event.get("type") or "").strip()
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return [f"{line_label} payload must be an object"]

    errors: list[str] = []
    payload_label = f"{line_label} {event_type}"
    if event_type in {"session_started", "feature_workspace_created", "reopen_requested"}:
        return errors
    if event_type == "user_input_captured":
        errors.extend(_require_payload_any_key(payload, payload_label, ("raw_excerpt", "excerpt"), "raw excerpt"))
        errors.extend(_require_payload_keys(payload, payload_label, ("content_hash",)))
        errors.extend(_require_payload_any_key(payload, payload_label, ("input_role", "role"), "input role"))
    elif event_type == "question_asked":
        errors.extend(_require_payload_keys(payload, payload_label, ("question_id", "domain", "blocking_level")))
        errors.extend(_require_payload_any_key(payload, payload_label, ("field", "unknown_id"), "field or unknown_id"))
    elif event_type == "answer_recorded":
        errors.extend(_require_payload_keys(payload, payload_label, ("question_id", "content_hash", "interpretation_summary", "confidence")))
        errors.extend(_require_payload_any_key(payload, payload_label, ("answer_excerpt", "excerpt"), "answer excerpt"))
    elif event_type == "repo_evidence_captured":
        errors.extend(_require_payload_keys(payload, payload_label, ("evidence_id", "relevance", "claim")))
        errors.extend(_require_payload_any_key(payload, payload_label, ("source_path", "path"), "source path"))
        errors.extend(_require_payload_any_key(payload, payload_label, ("excerpt_hash", "content_hash"), "excerpt or content hash"))
    elif event_type == "research_evidence_captured":
        errors.extend(_require_payload_keys(payload, payload_label, ("evidence_id", "confidence")))
        errors.extend(_require_payload_any_key(payload, payload_label, ("source_url", "url", "source_path", "spike_path"), "source url/path/spike path"))
        errors.extend(_require_payload_any_key(payload, payload_label, ("excerpt_hash", "content_hash"), "excerpt or content hash"))
        errors.extend(_require_payload_any_key(payload, payload_label, ("relevance", "claim"), "relevance or claim"))
    elif event_type == "unknown_opened":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(_require_payload_any_key(payload, payload_label, ("field", "domain", "question"), "field, domain, or question"))
    elif event_type == "unknown_resolved":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(_require_payload_any_key(payload, payload_label, ("resolution", "resolved_value", "disposition"), "resolution"))
    elif event_type == "unknown_deferred":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(_require_payload_any_key(payload, payload_label, ("deferred_to", "owner", "disposition"), "defer disposition"))
    elif event_type == "unknown_waived":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(_require_payload_any_key(payload, payload_label, ("waiver_reason", "risk_acceptance", "disposition"), "waiver disposition"))
    elif event_type == "decision_locked":
        errors.extend(_require_payload_any_key(payload, payload_label, ("decision_id", "stable_id"), "stable decision ID"))
        errors.extend(_require_payload_any_key(payload, payload_label, ("locked_value", "selected_value", "decision"), "locked value"))
        errors.extend(_require_payload_basis_or_evidence_ids(payload, payload_label))
    elif event_type == "route_selected":
        errors.extend(_require_payload_any_key(payload, payload_label, ("route_id", "stable_id"), "stable route ID"))
        errors.extend(_require_payload_any_key(payload, payload_label, ("selected_route", "selected_value", "route"), "selected route"))
        errors.extend(_require_payload_basis_or_evidence_ids(payload, payload_label))
    elif event_type == "complexity_selected":
        errors.extend(_require_payload_any_key(payload, payload_label, ("complexity_id", "stable_id"), "stable complexity ID"))
        errors.extend(_require_payload_any_key(payload, payload_label, ("selected_complexity", "complexity_level", "selected_value"), "selected complexity"))
        errors.extend(_require_payload_basis_or_evidence_ids(payload, payload_label))
    elif event_type == "stage_artifact_compiled":
        errors.extend(_require_payload_keys(payload, payload_label, ("artifact_path", "stage", "output_hash")))
        errors.extend(_validate_event_reference_list(payload.get("input_event_range"), f"{payload_label} payload.input_event_range", None, exact_len=2))
        errors.extend(_validate_event_reference_list(payload.get("key_event_ids"), f"{payload_label} payload.key_event_ids", None))
        if not isinstance(payload.get("evidence_ids"), list):
            errors.append(f"{payload_label} payload.evidence_ids must be a list")
    elif event_type == "artifact_compiled":
        errors.extend(_require_payload_keys(payload, payload_label, ("artifact_path", "output_hash", "source_map_reference")))
        if not isinstance(payload.get("input_stage_artifacts"), list):
            errors.append(f"{payload_label} payload.input_stage_artifacts must be a list")
        errors.extend(_validate_event_reference_list(payload.get("input_event_range"), f"{payload_label} payload.input_event_range", None, exact_len=2))
    elif event_type == "checkpoint_written":
        required = (
            "checkpoint_event_id",
            "current_stage",
            "current_domain",
            "manifest_hash",
            "workflow_state_hash",
            "next_action",
        )
        errors.extend(_require_payload_keys(payload, payload_label, required))
        checkpoint_event_id = str(payload.get("checkpoint_event_id") or "").strip()
        event_id = str(event.get("event_id") or "").strip()
        if checkpoint_event_id and checkpoint_event_id != event_id:
            errors.append(f"{payload_label} payload.checkpoint_event_id must equal event_id")
    elif event_type == "legacy_state_imported":
        if not isinstance(payload.get("legacy_source_files"), list) or not payload.get("legacy_source_files"):
            errors.append(f"{payload_label} payload.legacy_source_files must be a non-empty list")
        if not isinstance(payload.get("imported_artifact_hashes"), dict) or not payload.get("imported_artifact_hashes"):
            errors.append(f"{payload_label} payload.imported_artifact_hashes must be a non-empty object")
        errors.extend(_require_payload_keys(payload, payload_label, ("reconstruction_limits", "warning")))
    return errors


def _validate_journal_event_payload_references(event: dict[str, Any], line_label: str, event_ids: set[str]) -> list[str]:
    event_type = str(event.get("type") or "").strip()
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return []

    payload_label = f"{line_label} {event_type}"
    if event_type == "stage_artifact_compiled":
        return [
            *_validate_event_reference_list(
                payload.get("input_event_range"),
                f"{payload_label} payload.input_event_range",
                event_ids,
                exact_len=2,
            ),
            *_validate_event_reference_list(payload.get("key_event_ids"), f"{payload_label} payload.key_event_ids", event_ids),
        ]
    if event_type == "artifact_compiled":
        return _validate_event_reference_list(
            payload.get("input_event_range"),
            f"{payload_label} payload.input_event_range",
            event_ids,
            exact_len=2,
        )
    return []


def _read_journal_events(feature_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = journal_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return events, [f"brainstorming/journal.ndjson could not be read: {exc}"]

    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"brainstorming/journal.ndjson line {index} is invalid JSON: {exc.msg}")
            continue
        if not isinstance(event, dict):
            errors.append(f"brainstorming/journal.ndjson line {index} must be an object")
            continue

        event_id = str(event.get("event_id") or "").strip()
        event_type = str(event.get("type") or "").strip()
        stage = str(event.get("stage") or "").strip()
        if not event_id:
            errors.append(f"brainstorming/journal.ndjson line {index} missing event_id")
        if not event_type:
            errors.append(f"brainstorming/journal.ndjson line {index} missing type")
        elif event_type not in LOSSLESS_SPECIFY_EVENT_TYPES:
            errors.append(f"brainstorming/journal.ndjson line {index} unknown event type: {event_type}")
        if type(event.get("schema_version")) is not int:
            errors.append(f"brainstorming/journal.ndjson line {index} schema_version must be an integer")
        if not _is_non_empty_text(event.get("created_at")):
            errors.append(f"brainstorming/journal.ndjson line {index} missing created_at")
        if not stage:
            errors.append(f"brainstorming/journal.ndjson line {index} missing stage")
        if stage and stage not in LOSSLESS_SPECIFY_STAGES:
            errors.append(f"brainstorming/journal.ndjson line {index} uses non-canonical stage: {stage}")
        if not isinstance(event.get("source"), dict):
            errors.append(f"brainstorming/journal.ndjson line {index} source must be an object")
        if not isinstance(event.get("payload"), dict):
            errors.append(f"brainstorming/journal.ndjson line {index} payload must be an object")
        if not isinstance(event.get("writes"), list):
            errors.append(f"brainstorming/journal.ndjson line {index} writes must be a list")
        supersedes_event_id = event.get("supersedes_event_id")
        if supersedes_event_id is not None and not isinstance(supersedes_event_id, str):
            errors.append(f"brainstorming/journal.ndjson line {index} supersedes_event_id must be null or string")
        if event_type in LOSSLESS_SPECIFY_EVENT_TYPES:
            errors.extend(_validate_journal_event_payload(event, f"brainstorming/journal.ndjson line {index}"))
        events.append(event)

    return events, errors


def _validate_journal_event_references(events: list[dict[str, Any]], event_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for index, event in enumerate(events, start=1):
        if str(event.get("type") or "").strip() in LOSSLESS_SPECIFY_EVENT_TYPES:
            errors.extend(
                _validate_journal_event_payload_references(
                    event,
                    f"brainstorming/journal.ndjson line {index}",
                    event_ids,
                )
            )
    return errors


def _validate_event_reference_list(
    value: Any,
    label: str,
    event_ids: set[str] | None,
    *,
    exact_len: int | None = None,
) -> list[str]:
    if not isinstance(value, list):
        return [f"{label} must be a list"]
    errors: list[str] = []
    if exact_len is not None and value and len(value) != exact_len:
        errors.append(f"{label} must contain exactly {exact_len} event IDs when non-empty")
    for index, item in enumerate(value):
        if not _is_non_empty_text(item):
            errors.append(f"{label}[{index}] must be a non-empty event ID")
            continue
        if event_ids is not None and item.strip() not in event_ids:
            errors.append(f"{label}[{index}] references unknown journal event: {item.strip()}")
    return errors


def _validate_compiled_from(payload: dict[str, Any], label: str, event_ids: set[str]) -> list[str]:
    compiled_from = payload.get("compiled_from")
    if not isinstance(compiled_from, dict):
        return [f"{label} missing compiled_from"]

    errors: list[str] = []
    if str(compiled_from.get("journal") or "").strip() != "brainstorming/journal.ndjson":
        errors.append(f"{label} compiled_from.journal must be brainstorming/journal.ndjson")
    errors.extend(
        _validate_event_reference_list(
            compiled_from.get("event_range"),
            f"{label} compiled_from.event_range",
            event_ids,
            exact_len=2,
        )
    )
    errors.extend(_validate_event_reference_list(compiled_from.get("key_events"), f"{label} compiled_from.key_events", event_ids))
    if not isinstance(compiled_from.get("evidence_ids"), list):
        errors.append(f"{label} compiled_from.evidence_ids must be a list")
    return errors


def _validate_lossless_resume_state(
    feature_dir: Path,
    event_ids: set[str],
    checkpoint_ids: set[str],
    manifest_last_checkpoint_id: str,
) -> list[str]:
    workflow_state_path = feature_dir / "workflow-state.md"
    try:
        workflow_state_content = workflow_state_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"workflow-state.md could not be read: {exc}"]
    section = _extract_markdown_section(workflow_state_content, "Lossless Resume State")
    if not section.strip():
        return ["workflow-state.md is missing Lossless Resume State section"]

    errors: list[str] = []
    journal_file = extract_field(section, "journal_file")
    stage_manifest = extract_field(section, "stage_manifest")
    last_event_id = extract_field(section, "last_event_id")
    last_checkpoint_id = extract_field(section, "last_checkpoint_id")
    required_fields = {
        "journal_file": journal_file,
        "stage_manifest": stage_manifest,
        "last_event_id": last_event_id,
        "last_checkpoint_id": last_checkpoint_id,
    }
    for field, value in required_fields.items():
        if not value.strip():
            errors.append(f"workflow-state.md Lossless Resume State {field} is required")
    if journal_file != "brainstorming/journal.ndjson":
        errors.append("workflow-state.md Lossless Resume State journal_file must be brainstorming/journal.ndjson")
    if stage_manifest != "brainstorming/stage-manifest.json":
        errors.append("workflow-state.md Lossless Resume State stage_manifest must be brainstorming/stage-manifest.json")
    if last_event_id and last_event_id != "none" and last_event_id not in event_ids:
        errors.append(f"workflow-state.md Lossless Resume State last_event_id not found in journal: {last_event_id}")
    if last_checkpoint_id and last_checkpoint_id != "none" and last_checkpoint_id not in checkpoint_ids:
        errors.append(
            "workflow-state.md Lossless Resume State last_checkpoint_id not found as checkpoint_written "
            f"event in journal: {last_checkpoint_id}"
        )
    if (
        last_checkpoint_id
        and last_checkpoint_id != "none"
        and manifest_last_checkpoint_id
        and manifest_last_checkpoint_id != "none"
        and last_checkpoint_id != manifest_last_checkpoint_id
    ):
        errors.append(
            "workflow-state.md Lossless Resume State last_checkpoint_id must match "
            f"brainstorming/stage-manifest.json journal.last_checkpoint_id: {manifest_last_checkpoint_id}"
        )
    return errors


def _validate_lossless_specify_state(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    events, journal_errors = _read_journal_events(feature_dir)
    errors.extend(journal_errors)
    event_ids = {str(event.get("event_id") or "").strip() for event in events if str(event.get("event_id") or "").strip()}
    errors.extend(_validate_journal_event_references(events, event_ids))
    checkpoint_ids = {
        str(event.get("event_id") or "").strip()
        for event in events
        if str(event.get("type") or "").strip() == "checkpoint_written"
        and str(event.get("event_id") or "").strip()
    }

    manifest, manifest_errors = _read_json_artifact(
        feature_dir / "brainstorming" / "stage-manifest.json",
        "brainstorming/stage-manifest.json",
    )
    errors.extend(manifest_errors)
    if manifest_errors:
        return errors
    if not isinstance(manifest, dict):
        errors.append("brainstorming/stage-manifest.json must contain a top-level object")
        return errors

    stages = manifest.get("stages")
    if not isinstance(stages, dict):
        errors.append("brainstorming/stage-manifest.json stages must be an object")
    else:
        stage_keys = {str(stage) for stage in stages}
        missing_stages = sorted(LOSSLESS_SPECIFY_STAGES - stage_keys)
        if missing_stages:
            errors.append(
                "brainstorming/stage-manifest.json stages missing canonical stages: "
                f"{', '.join(missing_stages)}"
            )
        for stage in stages:
            if stage not in LOSSLESS_SPECIFY_STAGES:
                errors.append(f"brainstorming/stage-manifest.json uses non-canonical stage: {stage}")
                continue
            entry = stages[stage]
            if not isinstance(entry, dict):
                errors.append(f"brainstorming/stage-manifest.json stages.{stage} must be an object")
                continue
            expected_artifact = LOSSLESS_SPECIFY_STAGE_ARTIFACTS[stage]
            actual_artifact = str(entry.get("artifact") or "").strip()
            if actual_artifact != expected_artifact:
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage}.artifact must be "
                    f"{expected_artifact}, found {actual_artifact or 'missing'}"
                )
            if "event_range" not in entry:
                errors.append(f"brainstorming/stage-manifest.json stages.{stage}.event_range is required")
            else:
                errors.extend(
                    _validate_event_reference_list(
                        entry.get("event_range"),
                        f"brainstorming/stage-manifest.json stages.{stage}.event_range",
                        event_ids,
                        exact_len=2,
                    )
                )
            if "last_compiled_event_id" not in entry:
                errors.append(f"brainstorming/stage-manifest.json stages.{stage}.last_compiled_event_id is required")
            elif entry.get("last_compiled_event_id") is not None:
                last_compiled_event_id = str(entry.get("last_compiled_event_id") or "").strip()
                if not last_compiled_event_id:
                    errors.append(
                        f"brainstorming/stage-manifest.json stages.{stage}.last_compiled_event_id "
                        "must be a non-empty string or null"
                    )
                elif last_compiled_event_id not in event_ids:
                    errors.append(
                        f"brainstorming/stage-manifest.json stages.{stage}.last_compiled_event_id "
                        f"references unknown journal event: {last_compiled_event_id}"
                    )
            if "artifact_hash" not in entry:
                errors.append(f"brainstorming/stage-manifest.json stages.{stage}.artifact_hash is required")
            elif entry.get("artifact_hash") is not None and not isinstance(entry.get("artifact_hash"), str):
                errors.append(f"brainstorming/stage-manifest.json stages.{stage}.artifact_hash must be a string or null")

    canonical_stage_enum = manifest.get("canonical_stage_enum")
    if not isinstance(canonical_stage_enum, list):
        errors.append("brainstorming/stage-manifest.json canonical_stage_enum must be a list")
    else:
        canonical_stage_set = {str(item) for item in canonical_stage_enum}
        missing = sorted(LOSSLESS_SPECIFY_STAGES - canonical_stage_set)
        extra = sorted(canonical_stage_set - LOSSLESS_SPECIFY_STAGES)
        if missing:
            errors.append(f"brainstorming/stage-manifest.json canonical_stage_enum missing: {', '.join(missing)}")
        if extra:
            errors.append(
                "brainstorming/stage-manifest.json canonical_stage_enum has unknown stages: "
                f"{', '.join(extra)}"
            )

    journal = manifest.get("journal")
    if not isinstance(journal, dict):
        errors.append("brainstorming/stage-manifest.json journal must be an object")
        manifest_last_checkpoint_id = ""
    else:
        last_event_id = str(journal.get("last_event_id") or "").strip()
        last_checkpoint_id = str(journal.get("last_checkpoint_id") or "").strip()
        manifest_last_checkpoint_id = last_checkpoint_id
        if last_event_id and last_event_id not in event_ids:
            errors.append(f"brainstorming/stage-manifest.json last_event_id not found in journal: {last_event_id}")
        if last_checkpoint_id and last_checkpoint_id not in checkpoint_ids:
            errors.append(
                "brainstorming/stage-manifest.json last_checkpoint_id not found as checkpoint_written "
                f"event in journal: {last_checkpoint_id}"
            )
    errors.extend(_validate_lossless_resume_state(feature_dir, event_ids, checkpoint_ids, manifest_last_checkpoint_id))

    for relative_path in (
        "brainstorming/facts.json",
        "brainstorming/route.json",
        "brainstorming/intent.json",
        "brainstorming/complexity.json",
        "brainstorming/domains.json",
        "brainstorming/evidence-index.json",
        "brainstorming/handoff-to-specify.json",
    ):
        payload, read_errors = _read_json_artifact(feature_dir / relative_path, relative_path)
        errors.extend(read_errors)
        if read_errors:
            continue
        if not isinstance(payload, dict):
            errors.append(f"{relative_path} must be a JSON object")
            continue
        stage = str(payload.get("stage") or "").strip()
        expected_stage = LOSSLESS_SPECIFY_ARTIFACT_STAGES[relative_path]
        if stage != expected_stage:
            errors.append(
                f"{relative_path} stage must be {expected_stage}, found {stage or 'missing'}"
            )
        if stage and stage not in LOSSLESS_SPECIFY_STAGES:
            errors.append(f"{relative_path} uses non-canonical stage: {stage}")
        errors.extend(_validate_compiled_from(payload, relative_path, event_ids))

    return errors


def _validate_capability_ledger(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "capability-ledger.json", "capability-ledger.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["capability-ledger.json must contain a top-level JSON object"]
    if not isinstance(payload.get("capabilities"), list):
        return ["capability-ledger.json must define a top-level capabilities array"]
    return []


def _validate_control_ledger(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "control-ledger.json", "control-ledger.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["control-ledger.json must contain a top-level JSON object"]
    if not isinstance(payload.get("control_nodes"), list):
        return ["control-ledger.json must define a top-level control_nodes array"]
    return []


def _workflow_state_mentions_heavy_prd_scan(feature_dir: Path) -> bool:
    workflow_state_path = feature_dir / "workflow-state.md"
    if not workflow_state_path.exists() or not workflow_state_path.is_file():
        return False
    content = workflow_state_path.read_text(encoding="utf-8", errors="replace").lower()
    return (
        "sp-prd-scan" in content
        or "entrypoint-ledger.json" in content
        or "config-contracts.json" in content
        or "protocol-contracts.json" in content
        or "state-machines.json" in content
        or "error-semantics.json" in content
        or "verification-surfaces.json" in content
    )


def _extract_handoff_ids(content: str) -> set[str]:
    return set(re.findall(r"\bPH-\d{3}\b", content))


def _is_deep_research_not_needed(content: str) -> bool:
    return bool(DEEP_RESEARCH_NOT_NEEDED_STATUS_RE.search(content))


def _validate_deep_research_not_needed_artifact(content: str) -> list[str]:
    errors: list[str] = []

    for section in DEEP_RESEARCH_NOT_NEEDED_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"deep-research.md not-needed output is missing required section: {section}")

    feasibility_section = _extract_markdown_section(content, "Feasibility Decision")
    handoff_section = _extract_markdown_section(content, "Planning Handoff")
    next_command_section = _extract_markdown_section(content, "Next Command")

    if "**Recommendation**" not in feasibility_section:
        errors.append("deep-research.md not-needed Feasibility Decision is missing **Recommendation**")
    elif "/sp.plan" not in feasibility_section:
        errors.append("deep-research.md not-needed Feasibility Decision must recommend `/sp.plan`")

    if "**Reason**" not in feasibility_section:
        errors.append("deep-research.md not-needed Feasibility Decision is missing **Reason**")

    if "**Handoff IDs**" not in handoff_section:
        errors.append("deep-research.md not-needed Planning Handoff is missing **Handoff IDs**")
    elif "not needed" not in handoff_section.lower():
        errors.append("deep-research.md not-needed Planning Handoff must mark handoff IDs as Not needed")

    if "**Recommended approach**" not in handoff_section:
        errors.append("deep-research.md not-needed Planning Handoff is missing **Recommended approach**")
    if "**Constraints `/sp.plan` must preserve**" not in handoff_section:
        errors.append(
            "deep-research.md not-needed Planning Handoff is missing **Constraints `/sp.plan` must preserve**"
        )

    if "/sp.plan" not in next_command_section:
        errors.append("deep-research.md not-needed Next Command must be `/sp.plan`")

    return errors


def _validate_deep_research_artifact(feature_dir: Path) -> list[str]:
    deep_research_path = feature_dir / "deep-research.md"
    if not deep_research_path.exists():
        return []

    content = deep_research_path.read_text(encoding="utf-8", errors="replace")
    if _is_deep_research_not_needed(content):
        return _validate_deep_research_not_needed_artifact(content)

    errors: list[str] = []

    for section in DEEP_RESEARCH_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"deep-research.md is missing required section: {section}")

    handoff_section = _extract_markdown_section(content, "Planning Handoff")

    for field in DEEP_RESEARCH_HANDOFF_FIELDS:
        if field not in handoff_section:
            errors.append(f"deep-research.md Planning Handoff is missing field: {field}")

    if "CAP-" not in content:
        errors.append("deep-research.md is missing capability traceability IDs such as CAP-001")
    if "TRK-" not in content:
        errors.append("deep-research.md is missing research track IDs such as TRK-001")
    if "EVD-" not in content and "SPK-" not in content:
        errors.append("deep-research.md is missing evidence or spike IDs such as EVD-001 or SPK-001")
    if "PH-" not in handoff_section and "not needed" not in handoff_section.lower():
        errors.append("deep-research.md is missing Planning Handoff IDs such as PH-001")

    return errors


def _validate_plan_consumes_deep_research(feature_dir: Path) -> list[str]:
    deep_research_path = feature_dir / "deep-research.md"
    plan_path = feature_dir / "plan.md"
    if not deep_research_path.exists() or not plan_path.exists():
        return []

    deep_research_content = deep_research_path.read_text(encoding="utf-8", errors="replace")
    handoff_section = _extract_markdown_section(deep_research_content, "Planning Handoff")
    handoff_ids = _extract_handoff_ids(handoff_section)
    if not handoff_ids:
        return []

    plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    if "Deep Research Traceability Matrix" not in plan_content:
        errors.append("plan.md is missing Deep Research Traceability Matrix for deep-research handoff IDs")

    traceability_section = _extract_markdown_section(plan_content, "Deep Research Traceability Matrix")
    if not traceability_section and "Deep Research Traceability Matrix" in plan_content:
        errors.append("plan.md Deep Research Traceability Matrix must be a level-2 markdown section")

    missing_columns = [
        column for column in PLAN_DEEP_RESEARCH_TRACEABILITY_COLUMNS if column not in traceability_section
    ]
    if missing_columns:
        joined = ", ".join(missing_columns)
        errors.append(f"plan.md Deep Research Traceability Matrix is missing required columns: {joined}")

    missing_ids = sorted(handoff_id for handoff_id in handoff_ids if handoff_id not in traceability_section)
    if missing_ids:
        joined = ", ".join(missing_ids)
        errors.append(f"plan.md does not consume deep-research Planning Handoff IDs: {joined}")

    return errors


def _validate_plan_consequence_contract(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    triggered_payloads: list[tuple[Any, str]] = []
    for contract_path, label in _consequence_contract_paths(feature_dir):
        if not contract_path.exists():
            continue
        payload, read_errors = _read_json_artifact(contract_path, label)
        if read_errors:
            errors.extend(read_errors)
            continue
        errors.extend(_validate_consequence_json_payload(payload, label))
        if _json_gate_is_triggered(payload):
            triggered_payloads.append((payload, label))

    if not triggered_payloads:
        return errors

    plan_path = feature_dir / "plan.md"
    plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
    for payload, label in triggered_payloads:
        required_ids = _consequence_obligation_ids(payload)
        ids = ", ".join(sorted(required_ids)) or "triggered consequence obligations"
        if CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION not in plan_content:
            errors.append(f"plan.md is missing {CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION} for {ids}")

        operational_decisions = payload.get("operational_consequence_decisions") if isinstance(payload, dict) else None
        if not isinstance(operational_decisions, list) or not operational_decisions:
            errors.append(f"{label} operational_consequence_decisions must map {ids}")
            continue
        mapped_ids: set[str] = set()
        for decision in operational_decisions:
            mapped_ids.update(_decision_consequence_obligation_ids(decision))
        missing_ids = sorted(required_ids - mapped_ids)
        if missing_ids:
            errors.append(
                f"{label} operational_consequence_decisions must map consequence obligations: "
                + ", ".join(missing_ids)
            )

    return errors


def _spec_ui_design_contract(feature_dir: Path) -> dict[str, Any] | None:
    path = feature_dir / "spec-contract.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    contract = payload.get("design_contract") if isinstance(payload, dict) else None
    return contract if isinstance(contract, dict) else None


def _plan_ui_design_contract(feature_dir: Path) -> tuple[dict[str, Any] | None, str]:
    for contract_path, label in _consequence_contract_paths(feature_dir):
        if not contract_path.is_file():
            continue
        try:
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, label
        contract = payload.get("ui_design_contract") if isinstance(payload, dict) else None
        return (contract if isinstance(contract, dict) else None), label
    return None, "plan-contract.json"


def _validate_plan_ui_contract(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    spec_contract = _spec_ui_design_contract(feature_dir)
    plan_contract, label = _plan_ui_design_contract(feature_dir)
    spec_applies = isinstance(spec_contract, dict) and spec_contract.get("ui_applicable") is True
    plan_applies = isinstance(plan_contract, dict) and plan_contract.get("ui_applicable") is True

    if spec_applies and not plan_applies:
        errors.append(
            f"{label} must set ui_design_contract.ui_applicable true because spec-contract.json is UI-bearing"
        )
        return errors
    if not plan_applies:
        return errors

    assert isinstance(plan_contract, dict)
    ui_brief_ref = str(plan_contract.get("ui_brief_ref") or "").strip()
    if not ui_brief_ref:
        errors.append(f"{label} UI work requires ui_design_contract.ui_brief_ref")
    elif resolve_feature_artifact_ref(feature_dir, ui_brief_ref) is None:
        errors.append(
            f"{label} ui_design_contract.ui_brief_ref must reference an existing feature artifact"
        )

    readiness = str(plan_contract.get("design_readiness") or "").strip()
    if readiness not in {"approved", "narrow-existing-pattern-exception"}:
        errors.append(
            f"{label} UI work requires approved or narrow-existing-pattern-exception design_readiness"
        )

    list_fields = (
        "source_refs",
        "design_system_adoption",
        "token_strategy",
        "component_strategy",
        "entry_points",
        "required_states",
        "fidelity_refs",
        "must_preserve",
        "may_adapt",
        "must_not",
        "validation_refs",
        "visual_acceptance",
        "human_review_conditions",
    )
    for field in list_fields:
        if not isinstance(plan_contract.get(field), list):
            errors.append(f"{label} ui_design_contract.{field} must be a list")
    for field in (
        "source_refs",
        "entry_points",
        "required_states",
        "validation_refs",
        "visual_acceptance",
    ):
        value = plan_contract.get(field)
        if not isinstance(value, list) or not any(
            isinstance(item, str) and item.strip() for item in value
        ):
            errors.append(
                f"{label} UI work requires non-empty ui_design_contract.{field}"
            )

    if spec_applies and isinstance(spec_contract, dict):
        spec_brief_ref = str(spec_contract.get("ui_brief_ref") or "").strip()
        if spec_brief_ref and ui_brief_ref and spec_brief_ref != ui_brief_ref:
            spec_path = resolve_feature_artifact_ref(feature_dir, spec_brief_ref)
            plan_path = resolve_feature_artifact_ref(feature_dir, ui_brief_ref)
            if spec_path is None or plan_path is None or spec_path != plan_path:
                errors.append(
                    f"{label} ui_design_contract.ui_brief_ref must preserve the specification UI brief"
                )
    return errors


def _validate_tasks_ui_contract(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    plan_contract, label = _plan_ui_design_contract(feature_dir)
    plan_applies = isinstance(plan_contract, dict) and plan_contract.get("ui_applicable") is True
    plan_declares_not_ui = (
        isinstance(plan_contract, dict)
        and plan_contract.get("ui_applicable") is False
    )
    markdown_ids = markdown_ui_task_ids(feature_dir)
    indexed_ids = set(task_index_ui_contracts(feature_dir))

    if markdown_ids and plan_declares_not_ui:
        errors.append(
            f"tasks.md contains UI tasks but {label} ui_design_contract.ui_applicable is false"
        )
    if plan_applies and not indexed_ids:
        errors.append(
            "task-index.json must carry at least one structured ui_contract for a UI-bearing plan"
        )
    if plan_applies and not markdown_ids:
        errors.append(
            "tasks.md must render a task-local UI Implementation Contract for a UI-bearing plan"
        )
    for task_id in sorted(markdown_ids - indexed_ids):
        errors.append(
            f"task-index.json is missing structured ui_contract for UI task {task_id}"
        )
    for task_id in sorted(indexed_ids - markdown_ids):
        errors.append(
            f"tasks.md is missing task-local UI Implementation Contract for UI task {task_id}"
        )
    return errors


def _task_index_consequence_ids(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    ids: set[str] = set()
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return ids
    for task in tasks:
        if not isinstance(task, dict):
            continue
        raw_ids = task.get("consequence_obligation_ids")
        if isinstance(raw_ids, list):
            ids.update(str(item).strip() for item in raw_ids if str(item).strip())
    return ids


def _triggered_task_consequence_sources(feature_dir: Path) -> tuple[tuple[tuple[Any, str], ...], list[str]]:
    sources: list[tuple[Any, str]] = []
    errors: list[str] = []
    for source_path, label in (
        (feature_dir / "handoff-to-tasks.json", "handoff-to-tasks.json"),
        *(_consequence_contract_paths(feature_dir)),
        (feature_dir / "brainstorming" / "handoff-to-tasks.json", "brainstorming/handoff-to-tasks.json"),
    ):
        if not source_path.exists():
            continue
        payload, read_errors = _read_json_artifact(source_path, label)
        if read_errors:
            errors.extend(read_errors)
            continue
        if not _json_gate_is_triggered(payload):
            continue
        sources.append((payload, label))
    return tuple(sources), errors


def _validate_tasks_consequence_contract(feature_dir: Path) -> list[str]:
    sources, errors = _triggered_task_consequence_sources(feature_dir)
    if not sources:
        return errors

    required_ids: set[str] = set()
    for payload, label in sources:
        errors.extend(_validate_consequence_json_payload(payload, label))
        required_ids.update(_consequence_obligation_ids(payload))
    if not required_ids:
        return errors

    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.exists():
        errors.append("task-index.json is required when upstream artifacts carry triggered consequence obligations")
        return errors

    task_index_payload, task_index_errors = _read_json_artifact(task_index_path, "task-index.json")
    if task_index_errors:
        errors.extend(task_index_errors)
        return errors

    mapped_ids = _task_index_consequence_ids(task_index_payload)
    missing_ids = sorted(required_ids - mapped_ids)
    if missing_ids:
        errors.append("task-index.json is missing consequence mapping for: " + ", ".join(missing_ids))

    tasks_content = (feature_dir / "tasks.md").read_text(encoding="utf-8", errors="replace")
    if CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION not in tasks_content:
        errors.append(f"tasks.md is missing {CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION}")

    return errors


def _validate_prd_scan_artifacts(feature_dir: Path, *, require_heavy_scan_json: bool = False) -> list[str]:
    errors: list[str] = []
    for directory_name in ("scan-packets", "evidence", "worker-results"):
        target = feature_dir / directory_name
        if target.exists() and not target.is_dir():
            errors.append(f"{directory_name} must be a directory")

    coverage_payload, coverage_errors = _read_json_artifact(feature_dir / "coverage-ledger.json", "coverage-ledger.json")
    if coverage_errors:
        errors.extend(coverage_errors)
        return errors
    if not isinstance(coverage_payload, dict):
        errors.append("coverage-ledger.json must contain a top-level JSON object")
    elif not isinstance(coverage_payload.get("rows"), list):
        errors.append("coverage-ledger.json must define a top-level rows array")

    capability_payload, capability_errors = _read_json_artifact(
        feature_dir / "capability-ledger.json", "capability-ledger.json"
    )
    if capability_errors:
        errors.extend(capability_errors)
        return errors
    if not isinstance(capability_payload, dict):
        errors.append("capability-ledger.json must contain a top-level JSON object")
    elif not isinstance(capability_payload.get("capabilities"), list):
        errors.append("capability-ledger.json must define a top-level capabilities array")

    artifact_payload, artifact_errors = _read_json_artifact(feature_dir / "artifact-contracts.json", "artifact-contracts.json")
    if artifact_errors:
        errors.extend(artifact_errors)
        return errors
    if not isinstance(artifact_payload, dict):
        errors.append("artifact-contracts.json must contain a top-level JSON object")
    elif not isinstance(artifact_payload.get("artifacts"), list):
        errors.append("artifact-contracts.json must define a top-level artifacts array")

    checklist_payload, checklist_errors = _read_json_artifact(
        feature_dir / "reconstruction-checklist.json", "reconstruction-checklist.json"
    )
    if checklist_errors:
        errors.extend(checklist_errors)
        return errors
    if not isinstance(checklist_payload, dict):
        errors.append("reconstruction-checklist.json must contain a top-level JSON object")
    elif not isinstance(checklist_payload.get("checks"), list):
        errors.append("reconstruction-checklist.json must define a top-level checks array")

    if require_heavy_scan_json:
        for filename, array_key in PRD_HEAVY_SCAN_JSON_ARTIFACTS.items():
            errors.extend(_validate_json_object_with_array_key(feature_dir, filename, array_key))

    return errors


def _validate_prd_worker_results(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    worker_results_dir = feature_dir / "worker-results"
    if not worker_results_dir.is_dir():
        return errors

    for result_path in sorted(path for path in worker_results_dir.iterdir() if path.suffix == ".json"):
        relative_label = result_path.relative_to(feature_dir).as_posix()
        payload, read_errors = _read_json_artifact(result_path, relative_label)
        if read_errors:
            errors.extend(read_errors)
            continue
        if not isinstance(payload, dict):
            errors.append(f"{relative_label} must contain a top-level JSON object")
            continue

        for key in sorted(PRD_WORKER_RESULT_REQUIRED_KEYS - payload.keys()):
            errors.append(f"{relative_label} is missing required worker result key: {key}")

    return errors


def _validate_graph_artifact(feature_dir: Path, relative_path: str, required_keys: frozenset[str]) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / relative_path, relative_path)
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return [f"{relative_path} must contain a top-level JSON object"]
    errors: list[str] = []
    for key in sorted(required_keys - payload.keys()):
        errors.append(f"{relative_path} is missing required key: {key}")
    for key in required_keys:
        if key in payload and not isinstance(payload.get(key), list):
            errors.append(f"{relative_path} must define a top-level {key} array")
    return errors


def _validate_cognition_status_artifact(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "status.json", "status.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["status.json must contain a top-level JSON object"]
    return []


def _validate_cognition_database_artifact(feature_dir: Path) -> list[str]:
    validation = _run_project_cognition_validation(
        _project_root_from_cognition_dir(feature_dir),
        "validate-build",
    )
    return [str(message) for message in validation.get("errors", [])]


def _project_root_from_cognition_dir(feature_dir: Path) -> Path:
    if feature_dir.name == "project-cognition" and feature_dir.parent.name == ".specify":
        return feature_dir.parent.parent
    return feature_dir


def _normalize_result_path(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _validate_map_scan_artifacts(feature_dir: Path) -> list[str]:
    validation = _run_project_cognition_validation(
        _project_root_from_cognition_dir(feature_dir),
        "validate-scan",
    )
    return [str(message) for message in validation.get("errors", [])]


def _run_project_cognition_validation(project_root: Path, command: str) -> dict[str, object]:
    try:
        return run_project_cognition([command, "--format", "json"], cwd=project_root)
    except ProjectCognitionToolError as exc:
        return {
            "status": "blocked",
            "errors": [str(exc)],
            "warnings": [],
        }


def _validate_map_build_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_cognition_status_artifact(feature_dir))
    errors.extend(_validate_cognition_database_artifact(feature_dir))
    return errors


def _validate_map_update_artifacts(feature_dir: Path) -> list[str]:
    errors = _validate_map_build_artifacts(feature_dir)
    payload, read_errors = _read_json_artifact(feature_dir / "status.json", "status.json")
    if read_errors:
        errors.extend(read_errors)
        return errors
    if not isinstance(payload, dict):
        errors.append("status.json must contain a top-level JSON object")
        return errors
    result_state = str(payload.get("last_update_outcome") or payload.get("result_state") or "").strip()
    freshness = str(payload.get("freshness") or "").strip()
    readiness = str(payload.get("readiness") or "").strip()
    recommended = str(payload.get("recommended_next_action") or "").strip()
    valid_states = {"ready", "no_op", "partial_refresh", "needs_rebuild", "blocked"}
    if result_state not in valid_states:
        errors.append(
            "status.json must record last_update_outcome/result_state as ready, no_op, partial_refresh, needs_rebuild, or blocked"
        )
        return errors
    if (
        result_state == "ready"
        and (freshness != "fresh" or readiness != "query_ready" or recommended != "use_project_cognition")
    ):
        errors.append(
            "ready map-update result_state requires freshness=fresh, readiness=query_ready, and recommended_next_action=use_project_cognition"
        )
    if result_state == "partial_refresh" and freshness != "partial_refresh":
        errors.append("partial_refresh map-update result_state requires freshness=partial_refresh")
    if result_state == "needs_rebuild" and readiness != "needs_rebuild":
        errors.append("needs_rebuild map-update result_state requires readiness=needs_rebuild")
    if result_state == "blocked" and readiness != "blocked":
        errors.append("blocked map-update result_state requires readiness=blocked")
    if result_state == "no_op" and not payload.get("last_update_id"):
        errors.append("no_op map-update result_state requires last_update_id")
    return errors


def _capability_diagram_fields(capability: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        field
        for field in ("lifecycle_mermaid", "flow_mermaid")
        if isinstance(capability.get(field), str) and str(capability.get(field)).strip()
    )


def _capability_deep_workflow_page(capability: dict[str, object]) -> str:
    for key in ("deep_workflow_path", "deep_workflow_page", "deep_workflow", "page", "path"):
        value = capability.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resolve_map_build_page_path(feature_dir: Path, page: str) -> tuple[Path | None, str | None]:
    page_path = Path(page)
    if page_path.is_absolute():
        return None, "absolute deep workflow page paths are not allowed"

    normalized = _normalize_result_path(page)
    project_map_prefix = ".specify/project-map/"
    if normalized.lower().startswith(project_map_prefix):
        normalized = normalized[len(project_map_prefix) :]
    resolved = (feature_dir / normalized).resolve(strict=False)
    try:
        resolved.relative_to(feature_dir.resolve(strict=False))
    except ValueError:
        return None, "deep workflow page path escapes the map-build feature directory"
    return resolved, None


def _normalize_mermaid_content(content: str) -> str:
    return re.sub(r"\s+", " ", content).strip()


def _extract_mermaid_blocks(content: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(r"(?ims)^```\s*mermaid\s*\r?\n(.*?)^```\s*$", content)
    ]


def _missing_rendered_mermaid_fields(content: str, capability: dict[str, object]) -> list[str]:
    normalized_blocks = [_normalize_mermaid_content(block) for block in _extract_mermaid_blocks(content)]
    missing: list[str] = []
    for field in ("lifecycle_mermaid", "flow_mermaid"):
        value = capability.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        normalized_value = _normalize_mermaid_content(value)
        if not any(normalized_value and normalized_value in block for block in normalized_blocks):
            missing.append(field)
    return missing


def _validate_map_build_capability_diagrams(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "index" / "capabilities.json", "index/capabilities.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["index/capabilities.json must contain a top-level JSON object"]
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list):
        return ["index/capabilities.json must define a top-level capabilities array"]

    errors: list[str] = []
    for index, capability in enumerate(capabilities, start=1):
        if not isinstance(capability, dict):
            continue
        diagram_fields = _capability_diagram_fields(capability)
        if not diagram_fields:
            continue

        capability_id = str(capability.get("id") or f"capability #{index}")
        page = _capability_deep_workflow_page(capability)
        if not page:
            joined = ", ".join(diagram_fields)
            errors.append(
                f"index/capabilities.json capability {capability_id} defines {joined} but has no deep workflow page"
            )
            continue

        page_path, page_error = _resolve_map_build_page_path(feature_dir, page)
        if page_error is not None:
            errors.append(
                f"index/capabilities.json capability {capability_id} references invalid deep workflow page "
                f"{page}: {page_error}"
            )
            continue
        if page_path is None:
            continue
        if not page_path.exists() or not page_path.is_file():
            errors.append(
                f"index/capabilities.json capability {capability_id} references missing deep workflow page: {page}"
            )
            continue

        content = page_path.read_text(encoding="utf-8", errors="replace")
        missing_mermaid_fields = _missing_rendered_mermaid_fields(content, capability)
        if missing_mermaid_fields:
            joined = ", ".join(missing_mermaid_fields)
            errors.append(
                f"index/capabilities.json capability {capability_id} defines Mermaid diagram fields "
                f"but {page} does not render declared Mermaid content for: {joined}"
            )

    return errors


def _validate_prd_build_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    missing_exports = [
        relative_path
        for relative_path in PRD_BUILD_REQUIRED_HEAVY_EXPORTS
        if not (feature_dir / relative_path).exists()
    ]
    errors.extend(f"missing required artifact: {relative_path}" for relative_path in missing_exports)
    for relative_path in PRD_BUILD_REQUIRED_HEAVY_EXPORTS:
        target = feature_dir / relative_path
        if target.exists() and not target.is_file():
            errors.append(f"required artifact must be a file: {relative_path}")

    coverage_payload, coverage_errors = _read_json_artifact(feature_dir / "coverage-ledger.json", "coverage-ledger.json")
    if coverage_errors:
        return coverage_errors
    if not isinstance(coverage_payload, dict):
        return ["coverage-ledger.json must contain a top-level JSON object"]
    if not isinstance(coverage_payload.get("rows"), list):
        return ["coverage-ledger.json must define a top-level rows array"]

    capability_payload, capability_errors = _read_json_artifact(
        feature_dir / "capability-ledger.json", "capability-ledger.json"
    )
    if capability_errors:
        return capability_errors
    if not isinstance(capability_payload, dict):
        return ["capability-ledger.json must contain a top-level JSON object"]

    capabilities = capability_payload.get("capabilities")
    if not isinstance(capabilities, list):
        return ["capability-ledger.json must define a top-level capabilities array"]

    critical_capabilities = [item for item in capabilities if isinstance(item, dict) and item.get("tier") == "critical"]
    if not critical_capabilities:
        errors.append("capability-ledger.json must include at least one critical capability before prd-build can pass")
    else:
        non_ready = [
            str(item.get("status") or "").strip() or "missing"
            for item in critical_capabilities
            if str(item.get("status") or "").strip().lower() not in PRD_RECONSTRUCTION_READY_STATUSES
        ]
        if non_ready:
            joined = ", ".join(sorted(set(non_ready)))
            errors.append(
                "prd-build is blocked because critical capabilities must be reconstruction-ready; "
                f"found: {joined}"
            )

    artifact_payload, artifact_errors = _read_json_artifact(feature_dir / "artifact-contracts.json", "artifact-contracts.json")
    if artifact_errors:
        errors.extend(artifact_errors)
        return errors
    if not isinstance(artifact_payload, dict):
        errors.append("artifact-contracts.json must contain a top-level JSON object")
        return errors

    artifacts = artifact_payload.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifact-contracts.json must define a top-level artifacts array")
    elif not artifacts:
        errors.append("artifact-contracts.json must include at least one artifact before prd-build can pass")

    checklist_payload, checklist_errors = _read_json_artifact(
        feature_dir / "reconstruction-checklist.json", "reconstruction-checklist.json"
    )
    if checklist_errors:
        errors.extend(checklist_errors)
        return errors
    if not isinstance(checklist_payload, dict):
        errors.append("reconstruction-checklist.json must contain a top-level JSON object")
        return errors
    checks = checklist_payload.get("checks")
    if not isinstance(checks, list):
        errors.append("reconstruction-checklist.json must define a top-level checks array")
    elif not checks:
        errors.append("reconstruction-checklist.json must include at least one check before prd-build can pass")

    scan_packets_dir = feature_dir / "scan-packets"
    if not scan_packets_dir.is_dir():
        errors.append("scan-packets must be a directory")
    elif not any(scan_packets_dir.iterdir()):
        errors.append("scan-packets must contain at least one packet file before prd-build can pass")

    worker_results_dir = feature_dir / "worker-results"
    if not worker_results_dir.is_dir():
        errors.append("worker-results must be a directory")
    elif not any(worker_results_dir.iterdir()):
        errors.append("worker-results must contain at least one result file before prd-build can pass")
    else:
        errors.extend(_validate_prd_worker_results(feature_dir))

    evidence_dir = feature_dir / "evidence"
    if not evidence_dir.is_dir():
        errors.append("evidence must be a directory")
    elif not any(evidence_dir.iterdir()):
        errors.append("evidence must contain at least one file or subdirectory entry before prd-build can pass")

    return errors


def _is_legacy_specify_package(feature_dir: Path, workflow_state_content: str) -> bool:
    return (
        (feature_dir / "brainstorming" / "legacy-state.json").exists()
        or "## Fixed Lifecycle State" in workflow_state_content
    )


def _validate_agent_transition(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be an object"]
    errors: list[str] = []
    required = (
        "version",
        "status",
        "source_ref",
        "semantic_delta",
        "required_refs",
        "blockers",
        "next_action",
    )
    for field in required:
        if field not in payload:
            errors.append(f"{label} missing {field}")
    if payload.get("version") != 1:
        errors.append(f"{label} version must be 1")
    if payload.get("status") not in {"ready", "blocked"}:
        errors.append(f"{label} status must be ready or blocked")
    if not str(payload.get("source_ref") or "").strip():
        errors.append(f"{label} source_ref must be a non-empty string")
    for field in ("semantic_delta", "required_refs", "blockers"):
        if field in payload and not isinstance(payload.get(field), list):
            errors.append(f"{label} {field} must be a list")
    if payload.get("status") == "ready":
        if not str(payload.get("next_action") or "").strip():
            errors.append(
                f"{label} next_action must be a non-empty string when ready"
            )
        blockers = payload.get("blockers")
        if isinstance(blockers, list) and blockers:
            errors.append(f"{label} blockers must be empty when ready")
    return errors


def _validate_spec_contract_artifacts(feature_dir: Path) -> list[str]:
    path = feature_dir / "spec-contract.json"
    payload, errors = _read_json_artifact(path, "spec-contract.json")
    if errors:
        return errors
    if not isinstance(payload, dict):
        return ["spec-contract.json must contain a top-level object"]

    required = (
        "version",
        "status",
        "source_contract",
        "source_revision",
        "decision_digest_ref",
        "target_need",
        "scope",
        "constraints",
        "acceptance_criteria",
        "decisions",
        "semantic_delta",
        "capability_operations",
        "must_preserve_refs",
        "consequence_obligation_refs",
        "design_contract",
        "context_capsule",
        "open_items",
        "artifact_refs",
        "transition",
    )
    for field in required:
        if field not in payload:
            errors.append(f"spec-contract.json missing {field}")
    if payload.get("version") != 1:
        errors.append("spec-contract.json version must be 1")
    if payload.get("status") != "planning-ready":
        errors.append("spec-contract.json status must be planning-ready")
    if not str(payload.get("target_need") or "").strip():
        errors.append("spec-contract.json target_need must not be empty")
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        errors.append("spec-contract.json scope must be an object")
    else:
        for field in ("in", "out", "deferred"):
            if not isinstance(scope.get(field), list):
                errors.append(f"spec-contract.json scope.{field} must be a list")
    for field in (
        "constraints",
        "acceptance_criteria",
        "decisions",
        "semantic_delta",
        "capability_operations",
        "must_preserve_refs",
        "consequence_obligation_refs",
        "open_items",
    ):
        if field in payload and not isinstance(payload.get(field), list):
            errors.append(f"spec-contract.json {field} must be a list")
    acceptance = payload.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance:
        errors.append("spec-contract.json acceptance_criteria must be a non-empty list")
    semantic_delta = payload.get("semantic_delta")
    if isinstance(semantic_delta, list) and semantic_delta:
        workflow_state_path = feature_dir / "workflow-state.md"
        workflow_state = (
            workflow_state_path.read_text(encoding="utf-8", errors="replace")
            if workflow_state_path.is_file()
            else ""
        )
        review_state = _extract_markdown_section(workflow_state, "Review State")
        if extract_field(review_state, "last_user_reviewed_artifact_state") != "approved":
            errors.append(
                "spec-contract.json non-empty semantic_delta requires approved user review"
            )
    design_contract = payload.get("design_contract")
    if not isinstance(design_contract, dict):
        errors.append("spec-contract.json design_contract must be an object")
    else:
        for field in (
            "experience_requirements",
            "design_source_refs",
            "design_system_requirements",
            "fidelity_refs",
            "required_states",
            "validation_refs",
        ):
            if not isinstance(design_contract.get(field), list):
                errors.append(
                    f"spec-contract.json design_contract.{field} must be a list"
                )
        ui_applicable = design_contract.get("ui_applicable")
        if ui_applicable is not None and not isinstance(ui_applicable, bool):
            errors.append(
                "spec-contract.json design_contract.ui_applicable must be a boolean"
            )
        ui_brief_ref = str(design_contract.get("ui_brief_ref") or "").strip()
        ui_brief_signaled = bool(ui_brief_ref) or (feature_dir / "ui-brief.md").is_file()
        for field in ("design_source_refs", "fidelity_refs", "validation_refs"):
            value = design_contract.get(field)
            if isinstance(value, list) and any(
                isinstance(item, str) and "ui-brief.md" in item
                for item in value
            ):
                ui_brief_signaled = True
        if ui_brief_signaled and ui_applicable is not True:
            errors.append(
                "spec-contract.json carries ui-brief.md but design_contract.ui_applicable is not true"
            )
        if ui_applicable is True:
            if not ui_brief_ref:
                errors.append(
                    "spec-contract.json UI work requires design_contract.ui_brief_ref"
                )
            elif resolve_feature_artifact_ref(feature_dir, ui_brief_ref) is None:
                errors.append(
                    "spec-contract.json design_contract.ui_brief_ref must reference an existing feature artifact"
                )
            if str(design_contract.get("ui_work_type") or "").strip() not in {
                "existing-pattern",
                "feature-extension",
                "reference-implementation",
            }:
                errors.append(
                    "spec-contract.json UI work requires a valid design_contract.ui_work_type"
                )
            for field in (
                "entry_points",
                "must_preserve",
                "may_adapt",
                "must_not",
                "visual_acceptance",
            ):
                value = design_contract.get(field)
                if not isinstance(value, list):
                    errors.append(
                        f"spec-contract.json design_contract.{field} must be a list for UI work"
                    )
            if not isinstance(design_contract.get("entry_points"), list) or not design_contract.get(
                "entry_points"
            ):
                errors.append(
                    "spec-contract.json UI work requires design_contract.entry_points"
                )
            if not isinstance(design_contract.get("visual_acceptance"), list) or not design_contract.get(
                "visual_acceptance"
            ):
                errors.append(
                    "spec-contract.json UI work requires design_contract.visual_acceptance"
                )
            fidelity_mode = str(design_contract.get("fidelity_mode") or "none").strip()
            if fidelity_mode not in {"none", "approximate", "high", "inspiration"}:
                errors.append(
                    "spec-contract.json design_contract.fidelity_mode is invalid"
                )
            if fidelity_mode in {"approximate", "high"} and not design_contract.get(
                "original_reference_refs"
            ):
                errors.append(
                    "spec-contract.json approximate/high UI fidelity requires original_reference_refs"
                )
    context_capsule = payload.get("context_capsule")
    if not isinstance(context_capsule, dict):
        errors.append("spec-contract.json context_capsule must be an object")
    else:
        for field in (
            "evidence_refs",
            "selected_capabilities",
            "minimal_live_reads",
            "validation_routes",
            "stale_if",
        ):
            if not isinstance(context_capsule.get(field), list):
                errors.append(
                    f"spec-contract.json context_capsule.{field} must be a list"
                )
    errors.extend(_validate_agent_transition(payload.get("transition"), "spec-contract.json transition"))
    transition = payload.get("transition")
    if isinstance(transition, dict) and transition.get("status") == "ready":
        if transition.get("next_action") != "/sp.plan":
            errors.append(
                "spec-contract.json transition.next_action must be /sp.plan when planning-ready"
            )

    artifact_refs = payload.get("artifact_refs")
    if isinstance(artifact_refs, dict):
        for name, relative_path in artifact_refs.items():
            if relative_path is None:
                if name == "spec":
                    errors.append("spec-contract.json artifact_refs.spec must not be null")
                continue
            if not isinstance(relative_path, str) or not relative_path.strip():
                errors.append(f"spec-contract.json artifact_refs.{name} must be a path or null")
                continue
            candidate = Path(relative_path)
            try:
                resolved = (feature_dir / candidate).resolve(strict=False)
                resolved.relative_to(feature_dir.resolve(strict=False))
            except ValueError:
                errors.append(
                    f"spec-contract.json artifact_refs.{name} must stay inside the feature directory"
                )
                continue
            if candidate.is_absolute() or not resolved.is_file():
                if candidate.is_absolute():
                    errors.append(
                        f"spec-contract.json artifact_refs.{name} must stay inside the feature directory"
                    )
                else:
                    errors.append(
                        f"spec-contract.json artifact_refs.{name} is missing: {relative_path}"
                    )
    else:
        errors.append("spec-contract.json artifact_refs must be an object")
    return errors


def _validate_specify_draft_artifacts(feature_dir: Path, *, validate_lossless_state: bool = True) -> list[str]:
    errors: list[str] = []
    if (feature_dir / "spec-contract.json").is_file():
        return _validate_spec_contract_artifacts(feature_dir)
    alignment_path = feature_dir / "alignment.md"
    context_path = feature_dir / "context.md"
    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state_content = workflow_state_path.read_text(encoding="utf-8", errors="replace")

    if _is_legacy_specify_package(feature_dir, workflow_state_content):
        draft_path = feature_dir / "specify-draft.md"
        errors.extend(_validate_markdown_headings(draft_path, SPECIFY_LEGACY_DRAFT_REQUIRED_HEADINGS, "specify-draft.md"))
        errors.extend(_validate_markdown_headings(alignment_path, SPECIFY_LEGACY_ALIGNMENT_REQUIRED_HEADINGS, "alignment.md"))
        errors.extend(_validate_markdown_headings(context_path, SPECIFY_LEGACY_CONTEXT_REQUIRED_HEADINGS, "context.md"))

        fixed_lifecycle_state = _extract_markdown_section(workflow_state_content, "Fixed Lifecycle State")
        required_state_fields = (
            "current_stage",
            "current_domain",
            "next_action",
            "blocker_reason",
            "final_handoff_decision",
        )
        for field in required_state_fields:
            value = extract_field(fixed_lifecycle_state, field)
            if not value.strip():
                errors.append(f"workflow-state.md is missing Fixed Lifecycle State field: {field}")

        for legacy_field in ("coverage_mode", "observer_status", "last_observer_pass", "draft_file"):
            if re.search(rf"(?im)^\s*-\s*{re.escape(legacy_field)}\s*:", workflow_state_content):
                errors.append(f"workflow-state.md still uses legacy sp-specify state field: {legacy_field}")

        if validate_lossless_state:
            errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/facts.json", validate_unknowns=True))
            errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/route.json", validate_unknowns=False))
            errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/intent.json", validate_unknowns=False))
            errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/complexity.json", validate_unknowns=False))
            errors.extend(_validate_lossless_specify_state(feature_dir))

        handoff_payload, handoff_errors = _read_json_artifact(
            feature_dir / "brainstorming" / "handoff-to-specify.json",
            "brainstorming/handoff-to-specify.json",
        )
        if handoff_errors:
            errors.extend(handoff_errors)
        else:
            errors.extend(_validate_handoff_to_specify_payload(handoff_payload, "brainstorming/handoff-to-specify.json"))
            errors.extend(_validate_consequence_json_payload(handoff_payload, "brainstorming/handoff-to-specify.json"))
        return errors

    errors.extend(_validate_markdown_headings(alignment_path, SPECIFY_ALIGNMENT_REQUIRED_HEADINGS, "alignment.md"))
    errors.extend(_validate_markdown_headings(context_path, SPECIFY_CONTEXT_REQUIRED_HEADINGS, "context.md"))

    stage_state = _extract_markdown_section(workflow_state_content, "Stage State")
    review_state = _extract_markdown_section(workflow_state_content, "Review State")
    required_state_fields = (
        "current_stage",
        "next_action",
        "blocker_reason",
        "final_handoff_decision",
    )
    for field in required_state_fields:
        value = extract_field(stage_state, field)
        if not value.strip():
            errors.append(f"workflow-state.md is missing Stage State field: {field}")
    for field in ("last_user_reviewed_artifact_state", "source_files_read", "source_signal_disposition_status"):
        value = extract_field(review_state, field)
        if not value.strip():
            errors.append(f"workflow-state.md is missing Review State field: {field}")

    for legacy_field in ("coverage_mode", "observer_status", "last_observer_pass", "draft_file"):
        if re.search(rf"(?im)^\s*-\s*{re.escape(legacy_field)}\s*:", workflow_state_content):
            errors.append(f"workflow-state.md still uses legacy sp-specify state field: {legacy_field}")

    handoff_payload, handoff_errors = _read_json_artifact(
        feature_dir / "brainstorming" / "handoff-to-specify.json",
        "brainstorming/handoff-to-specify.json",
    )
    if handoff_errors:
        errors.extend(handoff_errors)
    else:
        errors.extend(_validate_handoff_to_specify_payload(handoff_payload, "brainstorming/handoff-to-specify.json"))
        errors.extend(_validate_consequence_json_payload(handoff_payload, "brainstorming/handoff-to-specify.json"))

    if validate_lossless_state:
        legacy_paths = (
            "brainstorming/journal.ndjson",
            "brainstorming/stage-manifest.json",
            "brainstorming/facts.json",
            "brainstorming/route.json",
            "brainstorming/intent.json",
            "brainstorming/complexity.json",
        )
        if any((feature_dir / relative_path).exists() for relative_path in legacy_paths):
            errors.extend(_validate_lossless_specify_state(feature_dir))

    return errors


def _workflow_state_active_profile(feature_dir: Path) -> str:
    workflow_state_path = feature_dir / "workflow-state.md"
    if not workflow_state_path.exists() or not workflow_state_path.is_file():
        return ""
    workflow_state_content = workflow_state_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?im)^\s*-\s*active_profile\s*:\s*`?([^`\r\n]+)`?\s*$", workflow_state_content)
    if not match:
        return ""
    return match.group(1).strip().lower()


def _validate_reference_implementation_spec(feature_dir: Path) -> list[str]:
    spec_path = feature_dir / "spec.md"
    spec_content = spec_path.read_text(encoding="utf-8", errors="replace")
    if (
        _workflow_state_active_profile(feature_dir) != REFERENCE_IMPLEMENTATION_PROFILE
        and "## Fidelity Requirements" not in spec_content
    ):
        return []

    return _validate_markdown_contains(
        spec_path,
        REFERENCE_IMPLEMENTATION_SPEC_REQUIRED_SECTIONS,
        "spec.md",
    )


def validate_artifacts_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    if command_name not in REQUIRED_ARTIFACTS:
        raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.artifacts.validate")

    raw = str(payload.get("feature_dir") or "").strip()
    if not raw:
        raise QualityHookError("feature_dir is required")
    feature_dir = Path(raw)
    if not feature_dir.is_absolute():
        feature_dir = (project_root / feature_dir).resolve()

    if command_name in {"map-scan", "map-build", "map-update"}:
        validation_errors: list[str] = []
        if command_name == "map-scan":
            validation_errors.extend(_validate_map_scan_artifacts(feature_dir))
        if command_name == "map-build":
            validation_errors.extend(_validate_map_build_artifacts(feature_dir))
        if command_name == "map-update":
            validation_errors.extend(_validate_map_update_artifacts(feature_dir))
        if validation_errors:
            return HookResult(
                event=WORKFLOW_ARTIFACTS_VALIDATE,
                status="blocked",
                severity="critical",
                errors=validation_errors,
                data={"feature_dir": str(feature_dir)},
            )
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="ok",
            severity="info",
            data={"feature_dir": str(feature_dir)},
        )

    required_artifacts = REQUIRED_ARTIFACTS[command_name]
    if command_name == "specify" and not (feature_dir / "spec-contract.json").exists():
        legacy_specify_artifacts = (
            "spec.md",
            "alignment.md",
            "context.md",
            "workflow-state.md",
            "brainstorming/handoff-to-specify.json",
        )
        if all((feature_dir / name).exists() for name in legacy_specify_artifacts):
            required_artifacts = legacy_specify_artifacts
    missing = [name for name in required_artifacts if not (feature_dir / name).exists()]
    type_errors: list[str] = []
    if command_name == "plan":
        contract_paths = _consequence_contract_paths(feature_dir)
        if not any(path.exists() for path, _label in contract_paths):
            missing.append("plan-contract.json or plan/plan-contract.json")
        for path, label in contract_paths:
            if path.exists() and not path.is_file():
                type_errors.append(f"required artifact must be a file: {label}")
    for relative_path in FILE_REQUIRED_ARTIFACTS.get(command_name, ()):
        target = feature_dir / relative_path
        if target.exists() and not target.is_file():
            type_errors.append(f"required artifact must be a file: {relative_path}")
    for relative_path in DIRECTORY_REQUIRED_ARTIFACTS.get(command_name, ()):
        target = feature_dir / relative_path
        if target.exists() and not target.is_dir():
            type_errors.append(f"required artifact must be a directory: {relative_path}")
    if command_name == "constitution":
        constitution_path = project_root / ".specify" / "memory" / "constitution.md"
        if not constitution_path.exists():
            missing.append(".specify/memory/constitution.md")
    legacy_lossless_missing = (
        command_name == "specify"
        and (feature_dir / "brainstorming" / "legacy-state.json").exists()
        and not missing
        and not type_errors
        and any(not (feature_dir / name).exists() for name in SPECIFY_LOSSLESS_REQUIRED_ARTIFACTS)
    )
    if missing or type_errors:
        if not legacy_lossless_missing:
            return HookResult(
                event=WORKFLOW_ARTIFACTS_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[*([f"missing required artifact: {name}" for name in missing]), *type_errors],
                data={"feature_dir": str(feature_dir)},
            )
    validation_errors: list[str] = []
    if command_name == "specify":
        validation_errors.extend(
            _validate_specify_draft_artifacts(feature_dir, validate_lossless_state=not legacy_lossless_missing)
        )
        validation_errors.extend(_validate_reference_implementation_spec(feature_dir))
    if command_name == "deep-research":
        validation_errors.extend(_validate_deep_research_artifact(feature_dir))
    if command_name == "plan":
        validation_errors.extend(_validate_plan_consumes_deep_research(feature_dir))
        validation_errors.extend(_validate_plan_consequence_contract(feature_dir))
        validation_errors.extend(_validate_plan_ui_contract(feature_dir))
    if command_name == "tasks":
        validation_errors.extend(_validate_tasks_consequence_contract(feature_dir))
        validation_errors.extend(_validate_tasks_ui_contract(feature_dir))
    if command_name == "implement":
        validation_errors.extend(_validate_packetized_implement_review_artifacts(feature_dir))
    if command_name == "map-scan":
        validation_errors.extend(_validate_map_scan_artifacts(feature_dir))
    if command_name == "map-build":
        validation_errors.extend(_validate_map_build_artifacts(feature_dir))
    if command_name == "map-update":
        validation_errors.extend(_validate_map_update_artifacts(feature_dir))
    if command_name == "prd-scan":
        validation_errors.extend(
            _validate_prd_scan_artifacts(
                feature_dir,
                require_heavy_scan_json=_workflow_state_mentions_heavy_prd_scan(feature_dir),
            )
        )
    if command_name == "prd-build":
        validation_errors.extend(_validate_prd_build_artifacts(feature_dir))
    if command_name == "prd":
        validation_errors.extend(_validate_prd_scan_artifacts(feature_dir))
    if validation_errors:
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="blocked",
            severity="critical",
            errors=validation_errors,
            data={"feature_dir": str(feature_dir)},
        )
    if legacy_lossless_missing:
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="warn",
            severity="warning",
            warnings=[
                "legacy sp-specify package lacks lossless state artifacts; do not treat this package as "
                "lossless unless it is repaired with legacy_state_imported"
            ],
            data={"feature_dir": str(feature_dir), "legacy_lossless_state": False},
        )
    return HookResult(
        event=WORKFLOW_ARTIFACTS_VALIDATE,
        status="ok",
        severity="info",
        data={"feature_dir": str(feature_dir)},
    )
