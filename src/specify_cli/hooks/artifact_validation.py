"""Validation hooks for workflow artifact completeness."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from specify_cli.design import (
    DESIGN_CHANGE_SCOPE_RE,
    DesignLintError,
    _active_design_adoption_record,
    _current_design_adoption,
    _load_design_change_index,
    _load_registered_design_change,
    _planning_ready_spec_binding,
)
from specify_cli.design_intelligence import validate_ui_source_continuity
from specify_cli.execution.implementation_review import task_review_is_accepted
from specify_cli.execution.packet_schema import UI_CONTRACT_FIELDS
from specify_cli.execution.ui_validation import (
    markdown_ui_task_ids,
    resolve_feature_artifact_ref,
    task_index_ui_contracts,
    ui_task_ids,
    validate_accepted_task_lifecycle,
    validate_lifecycle_ui_verification,
)
from specify_cli.implement_audit import (
    _packetized_task_ids,
    _task_review_record_from_payload,
)
from specify_cli.specify_runtime import SpecifyRuntimeError, run_specify_runtime
from specify_cli.workflow_runtime import (
    MissingWorkflowState,
    WorkflowRuntimeError,
    show_workflow,
)

from .checkpoint_serializers import (
    extract_field,
    normalize_command_name,
    serialize_workflow_state,
)
from .events import WORKFLOW_ARTIFACTS_VALIDATE
from .types import HookResult, QualityHookError

DEEP_RESEARCH_LEGACY_REQUIRED_FILES = ("deep-research.md", "workflow-state.md")
DEEP_RESEARCH_RUNTIME_REQUIRED_FILES = (
    "deep-research.md",
    "workflow-state.md",
    "research/state.json",
    "research/track-manifest.json",
    "research/synthesis.json",
    "research/handoff-to-plan.json",
)

FILE_REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": (
        "spec-contract.json",
        "spec.md",
        "workflow-state.md",
    ),
    "deep-research": DEEP_RESEARCH_RUNTIME_REQUIRED_FILES,
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
    "review": (
        "review-state.json",
        "implementation-summary.md",
        "human-acceptance.json",
        "workflow-state.md",
    ),
    "accept": (
        "implementation-summary.md",
        "human-acceptance.json",
        "workflow-state.md",
    ),
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
    "plan": (),
    "tasks": (),
    "review": ("review-evidence",),
    "accept": (),
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
    "deep-research": DEEP_RESEARCH_RUNTIME_REQUIRED_FILES,
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
    "review": (
        "review-state.json",
        "implementation-summary.md",
        "human-acceptance.json",
        "workflow-state.md",
        "review-evidence",
    ),
    "accept": (
        "implementation-summary.md",
        "human-acceptance.json",
        "workflow-state.md",
    ),
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

PRD_BUILD_OUTPUT_ARTIFACTS = (
    "master/master-pack.md",
    "exports/README.md",
    "exports/prd.md",
    *PRD_BUILD_REQUIRED_EXPORTS,
    *PRD_BUILD_REQUIRED_HEAVY_EXPORTS,
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


def _has_nonempty_prd_evidence(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and all(
            isinstance(item, str) and item.strip() for item in value
        )
    return False


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
IMPLEMENT_TASK_RE = re.compile(
    r"(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b"
)


def _extract_markdown_section(content: str, heading: str) -> str:
    heading_match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", content)
    if not heading_match:
        return ""

    section_body = content[heading_match.end() :]
    next_heading = re.search(r"(?m)^##\s+", section_body)
    if next_heading:
        return section_body[: next_heading.start()]
    return section_body


def _validate_markdown_contains(
    path: Path, required_items: tuple[str, ...], label: str
) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    return [
        f"{label} is missing required section: {item}"
        for item in required_items
        if item not in content
    ]


def _validate_markdown_headings(
    path: Path, required_headings: tuple[str, ...], label: str
) -> list[str]:
    if path.exists() and path.is_dir():
        return [f"{label} must be a file, not a directory"]
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"{label} could not be read: {exc}"]
    present_headings = {
        match.group(0).strip() for match in re.finditer(r"(?m)^#{1,6}\s+.+$", content)
    }
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


def _validate_json_object_with_array_key(
    feature_dir: Path, filename: str, array_key: str
) -> list[str]:
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
    required_keys = (
        "field",
        "question",
        "blocking_level",
        "resolver",
        "latest_resolve_phase",
        "status",
    )
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
    return {
        match.group("task_id").upper() for match in IMPLEMENT_TASK_RE.finditer(content)
    }


def _validate_accepted_task_review(
    feature_dir: Path, task_id: str, review_relative: str
) -> list[str]:
    review_path = feature_dir / review_relative
    if not review_path.is_file():
        return [f"{review_relative} is missing for accepted packetized task {task_id}"]
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("task review must contain a JSON object")
        record = _task_review_record_from_payload(payload)
        if not isinstance(record.task_id, str) or record.task_id.upper() != task_id:
            return [
                f"{task_id} task review has mismatched task_id at {review_relative}"
            ]
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
        return [
            f"{expected_relative} is missing for accepted packetized task {task_id}"
        ]
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
        errors.extend(validate_accepted_task_lifecycle(payload, relative, task_id))
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
        reason = (
            "unchecked in tasks.md"
            if packet_task_id in all_task_ids
            else "missing checked task in tasks.md"
        )
        errors.append(f"{packet_task_id} packetized task is not checked: {reason}")

    if not checked_task_ids:
        return errors

    ledger_relative = "implementation-review/ledger.json"
    branch_review_relative = "implementation-review/branch-review.md"
    ledger_path = feature_dir / ledger_relative
    if not ledger_path.is_file():
        errors.append(
            f"{ledger_relative} is missing for packetized checked implement tasks"
        )
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
            feature_dir,
            ledger_relative,
            task_id,
            entry,
            "review_package",
            expected_package,
        )
        review_errors = _validate_accepted_ledger_artifact_reference(
            feature_dir, ledger_relative, task_id, entry, "task_review", expected_review
        )
        errors.extend(brief_errors)
        errors.extend(package_errors)
        errors.extend(review_errors)
        if not review_errors:
            errors.extend(
                _validate_accepted_task_review(feature_dir, task_id, expected_review)
            )

    if not (feature_dir / branch_review_relative).is_file():
        errors.append(
            f"{branch_review_relative} is missing for packetized checked implement tasks"
        )
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
            key
            for key in MP_REQUIRED_KEYS
            if key != "mapped_to" and not str(item.get(key, "")).strip()
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
        if (
            coverage_status == "complete"
            and status in MP_ACTIVE_STATUSES
            and not mapped_to
        ):
            errors.append(
                f"{item_label} {mp_id} is active but missing mapped_to coverage"
            )
        if status == "deferred":
            for key in (
                "deferred_to",
                "owner",
                "latest_resolve_phase",
                "stop_and_reopen_condition",
            ):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{item_label} {mp_id} deferred item missing {key}")
            if not str(item.get("approved_risk_contract") or "").strip():
                errors.append(
                    f"{item_label} {mp_id} deferred item missing approved_risk_contract"
                )
        if status == "superseded" and not str(item.get("superseded_by") or "").strip():
            errors.append(f"{item_label} {mp_id} superseded item missing superseded_by")
        if (
            status == "resolved"
            and not str(item.get("resolution_evidence") or "").strip()
        ):
            errors.append(
                f"{item_label} {mp_id} resolved item missing resolution_evidence"
            )
        if status == "dropped":
            if not str(item.get("user_decision_source") or "").strip():
                errors.append(
                    f"{item_label} {mp_id} dropped item missing user_decision_source"
                )
            if not str(item.get("approved_risk_contract") or "").strip():
                errors.append(
                    f"{item_label} {mp_id} dropped item missing approved_risk_contract"
                )
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
                errors.append(
                    f"{conflict_label} closed conflict missing user_decision_source"
                )
            if (
                resolution == "revise"
                and not str(item.get("superseded_by") or "").strip()
            ):
                errors.append(
                    f"{conflict_label} revise resolution missing superseded_by"
                )
            if (
                resolution in {"drop", "defer"}
                and not str(item.get("approved_risk_contract") or "").strip()
            ):
                errors.append(
                    f"{conflict_label} {resolution} resolution missing approved_risk_contract"
                )
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
    if not source_evidence and (
        status in {"ready", "user-confirmed"}
        or (version == 2 and coverage_status == "complete")
        or (version == 2 and planning_gate_status == "ready")
        or (version == 2 and payload.get("compile_ready") is True)
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
                errors.append(
                    f"{item_label}.{field} must be an array of non-empty strings"
                )

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
        discussion_slug = str(payload.get("discussion_slug") or "").strip()
        if not discussion_slug:
            errors.append(f"{label} discussion_slug is required")
        elif not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", discussion_slug):
            errors.append(f"{label} discussion_slug must be a normalized slug")
        else:
            expected_source = (
                f".specify/discussions/{discussion_slug}/handoff-to-specify.json"
            )
            if source_contract != expected_source:
                errors.append(
                    f"{label} source_contract must match discussion_slug"
                )
        if payload.get("version") != 3:
            errors.append(f"{label} version must be 3")
        if payload.get("entry_source") != "sp-discussion":
            errors.append(f"{label} entry_source must be sp-discussion")
        if payload.get("status") not in {"ready", "blocked"}:
            errors.append(f"{label} status must be ready or blocked")
        if payload.get("recommended_consumer") != "sp-specify":
            errors.append(f"{label} recommended_consumer must be sp-specify")
        review_digest = str(payload.get("review_digest") or "").strip()
        if not re.fullmatch(r"[0-9a-f]{64}", review_digest):
            errors.append(f"{label} review_digest must be a sha256 digest")
        state_sha256 = str(payload.get("state_sha256") or "").strip()
        if not re.fullmatch(r"[0-9a-f]{64}", state_sha256):
            errors.append(f"{label} state_sha256 must be a sha256 digest")
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
    if (
        planning_gate_status
        and planning_gate_status not in MP_VALID_PLANNING_GATE_STATUSES
    ):
        errors.append(f"{label} has invalid planning_gate_status")

    errors.extend(_validate_must_preserve_items(payload, label))
    errors.extend(_validate_conflict_records(payload, label))
    errors.extend(_validate_source_evidence_entries(payload, label))
    errors.extend(_validate_source_signal_disposition(payload, label))

    hard_unknown_count = payload.get("hard_unknown_count", 0)
    open_conflict_count = payload.get("open_conflict_count", 0)
    derived_hard_unknown_count = _derived_hard_unknown_count(payload)
    derived_open_conflict_count = _derived_open_conflict_count(payload)
    if (
        isinstance(hard_unknown_count, int)
        and hard_unknown_count != derived_hard_unknown_count
    ):
        errors.append(
            f"{label} hard_unknown_count does not match open hard unknowns ({derived_hard_unknown_count})"
        )
    if (
        isinstance(open_conflict_count, int)
        and open_conflict_count != derived_open_conflict_count
    ):
        errors.append(
            f"{label} open_conflict_count does not match open conflicts ({derived_open_conflict_count})"
        )
    if planning_gate_status == "ready":
        if isinstance(hard_unknown_count, int) and hard_unknown_count > 0:
            errors.append(
                f"{label} planning_gate_status ready is invalid with open hard unknowns"
            )
        if derived_hard_unknown_count > 0:
            errors.append(
                f"{label} planning_gate_status ready is invalid with open hard unknowns"
            )
        if isinstance(open_conflict_count, int) and open_conflict_count > 0:
            errors.append(
                f"{label} planning_gate_status ready is invalid with open conflicts"
            )
        if derived_open_conflict_count > 0:
            errors.append(
                f"{label} planning_gate_status ready is invalid with open conflicts"
            )
        if coverage_status != "complete":
            errors.append(
                f"{label} planning_gate_status ready requires coverage_status complete"
            )
    if (
        coverage_status == "blocked_by_handoff_integrity"
        and planning_gate_status != "blocked_by_handoff_integrity"
    ):
        errors.append(
            f"{label} handoff integrity blocks must also set planning_gate_status blocked_by_handoff_integrity"
        )
    return errors


def _validate_source_signal_disposition(
    payload: dict[str, Any], label: str
) -> list[str]:
    errors: list[str] = []
    source_files_read = payload.get("source_files_read", [])
    if source_files_read is None:
        source_files_read = []
    if not isinstance(source_files_read, list):
        errors.append(f"{label} source_files_read must be a list")
    elif any(
        not isinstance(item, str) or not item.strip() for item in source_files_read
    ):
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
            errors.append(
                f"{label} source_files_read is required for discussion-originated specify handoff"
            )
        if not dispositions:
            errors.append(
                f"{label} source_signal_disposition is required for discussion-originated specify handoff"
            )

    allowed = {"preserved", "in_scope", "deferred", "dropped", "clarification_blocker"}
    required = (
        "signal",
        "source",
        "disposition",
        "artifact_location",
        "user_confirmed",
        "reopen_trigger",
    )
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
        return [
            f"{label} consequence_analysis must be an object when consequence_gate.triggered is true"
        ]

    for key in CONSEQUENCE_ANALYSIS_REQUIRED_KEYS:
        value = analysis.get(key)
        if not isinstance(value, list) or not value:
            errors.append(
                f"{label} consequence_analysis.{key} must be a non-empty array when the gate is triggered"
            )

    obligations = payload.get("consequence_obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append(
            f"{label} consequence_obligations must be a non-empty array when the gate is triggered"
        )
        return errors

    for index, obligation in enumerate(obligations):
        if not isinstance(obligation, dict):
            errors.append(f"{label} consequence_obligations[{index}] must be an object")
            continue
        for key in CONSEQUENCE_OBLIGATION_REQUIRED_KEYS:
            value = obligation.get(key)
            if isinstance(value, list):
                if not value:
                    errors.append(
                        f"{label} consequence_obligations[{index}].{key} must not be empty"
                    )
            elif not str(value or "").strip():
                errors.append(
                    f"{label} consequence_obligations[{index}].{key} must not be empty"
                )

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


ENTRYPOINT_OUTCOME_CLASSIFICATIONS = {
    "terminal-success",
    "terminal-failure",
    "cancelled",
    "recoverable-user-input",
    "recoverable-automatic",
    "partial-success",
}
ENTRYPOINT_OUTCOME_DISPOSITIONS = {
    "preserve",
    "adapt",
    "not_applicable",
    "deferred",
}
ENTRYPOINT_OUTCOME_LEARNING_CONTEXT_KEYS = {
    "components",
    "operation_owners",
    "consumer_owners",
    "outcomes",
    "states",
    "entrypoints",
    "validation_surfaces",
}
ENTRYPOINT_OUTCOME_LEARNING_DISPOSITIONS = {
    "applied",
    "not_applicable",
    "deferred",
}
ENTRYPOINT_OUTCOME_PLAN_FIELDS = (
    "decision_id",
    "decision",
    "producer_result_ref",
    "consumer_owner",
    "state_transition",
    "interaction_owner",
    "interaction_policy",
    "request_retention",
    "retry_identity",
    "cancel_behavior",
)


def _entrypoint_outcome_string_list(
    value: Any, field: str, label: str, *, required: bool = True
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [], [f"{label}.{field} must be a string array"]
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}.{field}[{index}] must be a non-empty string")
            continue
        normalized.append(item.strip())
    if required and not normalized:
        errors.append(f"{label}.{field} must be non-empty")
    duplicates = sorted(item for item in set(normalized) if normalized.count(item) > 1)
    if duplicates:
        errors.append(
            f"{label}.{field} must contain unique values: " + ", ".join(duplicates)
        )
    return normalized, errors


def _entrypoint_outcome_spec_payload(
    feature_dir: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    payload, read_errors = _read_json_artifact(
        feature_dir / "spec-contract.json", "spec-contract.json"
    )
    if read_errors:
        return None, None, read_errors
    if not isinstance(payload, dict):
        return None, None, ["spec-contract.json must contain a top-level object"]
    contract = payload.get("entrypoint_outcome_contract")
    if not isinstance(contract, dict):
        return (
            payload,
            None,
            ["spec-contract.json entrypoint_outcome_contract must be an object"],
        )
    return payload, contract, []


def _entrypoint_outcome_inventory_by_id(
    contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    inventory = contract.get("result_inventory")
    if not isinstance(inventory, list):
        return {}
    return {
        str(item.get("outcome_id") or "").strip(): item
        for item in inventory
        if isinstance(item, dict) and str(item.get("outcome_id") or "").strip()
    }


def _entrypoint_outcome_active_dispositions(
    contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    dispositions = contract.get("outcome_dispositions")
    if not isinstance(dispositions, list):
        return {}
    return {
        str(item.get("outcome_id") or "").strip(): item
        for item in dispositions
        if isinstance(item, dict)
        and str(item.get("outcome_id") or "").strip()
        and str(item.get("disposition") or "").strip() in {"preserve", "adapt"}
    }


def _validate_entrypoint_outcome_learning(
    contract: dict[str, Any], label: str
) -> list[str]:
    errors: list[str] = []
    raw_context = contract.get("learning_context")
    if not isinstance(raw_context, dict) or not raw_context:
        errors.append(f"{label}.learning_context must be a non-empty object")
    else:
        unknown_keys = sorted(
            str(key)
            for key in raw_context
            if key not in ENTRYPOINT_OUTCOME_LEARNING_CONTEXT_KEYS
        )
        if unknown_keys:
            errors.append(
                f"{label}.learning_context contains unknown facets: "
                + ", ".join(unknown_keys)
            )
        populated_facets = 0
        for key, value in raw_context.items():
            if key not in ENTRYPOINT_OUTCOME_LEARNING_CONTEXT_KEYS:
                continue
            values, list_errors = _entrypoint_outcome_string_list(
                value,
                str(key),
                f"{label}.learning_context",
                required=False,
            )
            errors.extend(list_errors)
            if values:
                populated_facets += 1
        if not populated_facets:
            errors.append(
                f"{label}.learning_context must contain at least one non-empty facet"
            )

    _search_refs, list_errors = _entrypoint_outcome_string_list(
        contract.get("learning_search_refs"), "learning_search_refs", label
    )
    errors.extend(list_errors)
    candidate_refs, list_errors = _entrypoint_outcome_string_list(
        contract.get("learning_candidate_refs"),
        "learning_candidate_refs",
        label,
        required=False,
    )
    errors.extend(list_errors)
    candidate_set = set(candidate_refs)

    raw_dispositions = contract.get("learning_dispositions")
    if not isinstance(raw_dispositions, list):
        errors.append(f"{label}.learning_dispositions must be an array")
        raw_dispositions = []

    disposition_by_ref: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(raw_dispositions):
        item_label = f"{label}.learning_dispositions[{index}]"
        if not isinstance(raw_item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        learning_ref = str(raw_item.get("learning_ref") or "").strip()
        if not learning_ref:
            errors.append(f"{item_label}.learning_ref must be a non-empty string")
            continue
        if learning_ref in disposition_by_ref:
            errors.append(f"{label} duplicate learning disposition for {learning_ref}")
            continue
        disposition_by_ref[learning_ref] = raw_item
        if learning_ref not in candidate_set:
            errors.append(
                f"{item_label} references unknown learning candidate {learning_ref}"
            )

        disposition = str(raw_item.get("disposition") or "").strip()
        if disposition not in ENTRYPOINT_OUTCOME_LEARNING_DISPOSITIONS:
            errors.append(
                f"{item_label}.disposition must be one of: "
                + ", ".join(sorted(ENTRYPOINT_OUTCOME_LEARNING_DISPOSITIONS))
            )
            continue
        if not str(raw_item.get("rationale") or "").strip():
            errors.append(f"{item_label}.rationale must be a non-empty string")
        _match_basis, list_errors = _entrypoint_outcome_string_list(
            raw_item.get("match_basis"), "match_basis", item_label
        )
        errors.extend(list_errors)
        requirement_refs, list_errors = _entrypoint_outcome_string_list(
            raw_item.get("requirement_refs"),
            "requirement_refs",
            item_label,
            required=False,
        )
        errors.extend(list_errors)
        consequence_refs, list_errors = _entrypoint_outcome_string_list(
            raw_item.get("consequence_refs"),
            "consequence_refs",
            item_label,
            required=False,
        )
        errors.extend(list_errors)
        evidence_refs, list_errors = _entrypoint_outcome_string_list(
            raw_item.get("evidence_refs"),
            "evidence_refs",
            item_label,
            required=False,
        )
        errors.extend(list_errors)

        if disposition == "applied" and not (requirement_refs or consequence_refs):
            errors.append(
                f"{label} learning {learning_ref} applied disposition requires "
                "requirement_refs or consequence_refs"
            )
        elif disposition == "not_applicable" and not evidence_refs:
            errors.append(
                f"{label} learning {learning_ref} not_applicable disposition "
                "requires evidence_refs"
            )
        elif (
            disposition == "deferred"
            and not str(raw_item.get("deferral_ref") or "").strip()
        ):
            errors.append(
                f"{label} learning {learning_ref} deferred disposition requires "
                "deferral_ref"
            )

    missing_dispositions = sorted(candidate_set - set(disposition_by_ref))
    if missing_dispositions:
        errors.append(
            f"{label} is missing learning disposition for candidates: "
            + ", ".join(missing_dispositions)
        )
    return errors


def _validate_spec_entrypoint_outcome_contract(feature_dir: Path) -> list[str]:
    payload, contract, errors = _entrypoint_outcome_spec_payload(feature_dir)
    if errors or payload is None or contract is None:
        return errors

    label = "spec-contract.json entrypoint_outcome_contract"
    acceptance_criteria = payload.get("acceptance_criteria")
    canonical_acceptance_refs = {
        f"spec-contract.json#/acceptance_criteria/{index}"
        for index in range(
            len(acceptance_criteria) if isinstance(acceptance_criteria, list) else 0
        )
    }
    triggered = contract.get("triggered")
    if not isinstance(triggered, bool):
        return [f"{label}.triggered must be a boolean"]
    if not triggered:
        if not str(contract.get("stand_down_reason") or "").strip():
            errors.append(
                f"{label}.stand_down_reason must be non-empty when triggered is false"
            )
        return errors

    trigger_reasons, list_errors = _entrypoint_outcome_string_list(
        contract.get("trigger_reasons"), "trigger_reasons", label
    )
    errors.extend(list_errors)
    if not trigger_reasons:
        errors.append(f"{label} requires at least one trigger reason")
    if contract.get("inventory_complete") is not True:
        errors.append(f"{label}.inventory_complete must be true before planning-ready")
    _inventory_refs, list_errors = _entrypoint_outcome_string_list(
        contract.get("inventory_evidence_refs"), "inventory_evidence_refs", label
    )
    errors.extend(list_errors)
    errors.extend(_validate_entrypoint_outcome_learning(contract, label))

    raw_inventory = contract.get("result_inventory")
    if not isinstance(raw_inventory, list) or not raw_inventory:
        errors.append(f"{label}.result_inventory must be a non-empty array")
        raw_inventory = []
    inventory_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(raw_inventory):
        item_label = f"{label}.result_inventory[{index}]"
        if not isinstance(raw_item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        for field in (
            "outcome_id",
            "entrypoint_id",
            "operation",
            "result_family",
            "classification",
        ):
            if not str(raw_item.get(field) or "").strip():
                errors.append(f"{item_label}.{field} must be a non-empty string")
        outcome_id = str(raw_item.get("outcome_id") or "").strip()
        if outcome_id:
            if outcome_id in inventory_by_id:
                errors.append(f"{label} duplicate outcome_id: {outcome_id}")
            else:
                inventory_by_id[outcome_id] = raw_item
        classification = str(raw_item.get("classification") or "").strip()
        if classification and classification not in ENTRYPOINT_OUTCOME_CLASSIFICATIONS:
            errors.append(
                f"{item_label}.classification must be one of: "
                + ", ".join(sorted(ENTRYPOINT_OUTCOME_CLASSIFICATIONS))
            )
        for field in ("reachable", "material"):
            if not isinstance(raw_item.get(field), bool):
                errors.append(f"{item_label}.{field} must be a boolean")
        _evidence_refs, list_errors = _entrypoint_outcome_string_list(
            raw_item.get("evidence_refs"), "evidence_refs", item_label
        )
        errors.extend(list_errors)

    raw_dispositions = contract.get("outcome_dispositions")
    if not isinstance(raw_dispositions, list) or not raw_dispositions:
        errors.append(f"{label}.outcome_dispositions must be a non-empty array")
        raw_dispositions = []
    disposition_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(raw_dispositions):
        item_label = f"{label}.outcome_dispositions[{index}]"
        if not isinstance(raw_item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        outcome_id = str(raw_item.get("outcome_id") or "").strip()
        if not outcome_id:
            errors.append(f"{item_label}.outcome_id must be a non-empty string")
            continue
        if outcome_id in disposition_by_id:
            errors.append(f"{label} duplicate disposition for {outcome_id}")
            continue
        disposition_by_id[outcome_id] = raw_item
        inventory_item = inventory_by_id.get(outcome_id)
        if inventory_item is None:
            errors.append(f"{item_label} references unknown outcome {outcome_id}")

        disposition = str(raw_item.get("disposition") or "").strip()
        if disposition not in ENTRYPOINT_OUTCOME_DISPOSITIONS:
            errors.append(
                f"{item_label}.disposition must be one of: "
                + ", ".join(sorted(ENTRYPOINT_OUTCOME_DISPOSITIONS))
            )
            continue
        rationale = str(raw_item.get("rationale") or "").strip()
        if not rationale:
            errors.append(f"{item_label}.rationale must be a non-empty string")

        if disposition in {"preserve", "adapt"}:
            if not str(raw_item.get("observable_behavior") or "").strip():
                errors.append(
                    f"{label} outcome {outcome_id} observable_behavior must be non-empty"
                )
            acceptance_refs, list_errors = _entrypoint_outcome_string_list(
                raw_item.get("acceptance_refs"),
                "acceptance_refs",
                f"{label} outcome {outcome_id}",
            )
            errors.extend(list_errors)
            invalid_acceptance_refs = sorted(
                ref for ref in acceptance_refs if ref not in canonical_acceptance_refs
            )
            if invalid_acceptance_refs:
                errors.append(
                    f"{label} outcome {outcome_id} acceptance_refs must point to top-level acceptance_criteria: "
                    + ", ".join(invalid_acceptance_refs)
                )
            consequence_refs, list_errors = _entrypoint_outcome_string_list(
                raw_item.get("consequence_refs"),
                "consequence_refs",
                f"{label} outcome {outcome_id}",
            )
            errors.extend(list_errors)
            invalid_consequence_refs = sorted(
                ref for ref in consequence_refs if not ref.startswith("CA-")
            )
            if invalid_consequence_refs:
                errors.append(
                    f"{label} outcome {outcome_id} consequence_refs must use CA- IDs: "
                    + ", ".join(invalid_consequence_refs)
                )
        elif disposition == "not_applicable":
            if inventory_item is not None and (
                inventory_item.get("reachable") is True
                and inventory_item.get("material") is True
            ):
                errors.append(
                    f"{label} outcome {outcome_id} cannot be not_applicable while reachable and material"
                )
            _evidence_refs, list_errors = _entrypoint_outcome_string_list(
                raw_item.get("evidence_refs"),
                "evidence_refs",
                f"{label} outcome {outcome_id}",
            )
            errors.extend(list_errors)
        elif disposition == "deferred":
            if not str(raw_item.get("deferral_ref") or "").strip():
                errors.append(
                    f"{label} outcome {outcome_id} deferral_ref must be non-empty when deferred"
                )

    missing_dispositions = sorted(set(inventory_by_id) - set(disposition_by_id))
    if missing_dispositions:
        errors.append(
            f"{label} is missing disposition for outcomes: "
            + ", ".join(missing_dispositions)
        )

    declared_consequence_refs = payload.get("consequence_obligation_refs")
    if isinstance(declared_consequence_refs, list):
        declared = {
            str(item).strip()
            for item in declared_consequence_refs
            if isinstance(item, str) and item.strip()
        }
        active_refs = {
            str(ref).strip()
            for item in disposition_by_id.values()
            if str(item.get("disposition") or "").strip() in {"preserve", "adapt"}
            for ref in item.get("consequence_refs", [])
            if isinstance(ref, str) and ref.strip()
        }
        missing_declared_refs = sorted(active_refs - declared)
        if missing_declared_refs:
            errors.append(
                "spec-contract.json consequence_obligation_refs must include entrypoint outcomes: "
                + ", ".join(missing_declared_refs)
            )
    return errors


def _entrypoint_outcome_plan_payload(
    feature_dir: Path,
) -> tuple[dict[str, Any] | None, str, list[str]]:
    for contract_path, label in _consequence_contract_paths(feature_dir):
        if not contract_path.exists():
            continue
        payload, read_errors = _read_json_artifact(contract_path, label)
        if read_errors:
            return None, label, read_errors
        if not isinstance(payload, dict):
            return None, label, [f"{label} must contain a top-level object"]
        return payload, label, []
    return (
        None,
        "plan-contract.json",
        ["plan-contract.json is required for triggered entrypoint outcomes"],
    )


def _validate_plan_entrypoint_outcome_contract(feature_dir: Path) -> list[str]:
    if not (feature_dir / "spec-contract.json").is_file():
        # Legacy feature packages can still complete their existing CA chain. New
        # Specify output always carries the explicit outcome gate.
        return []
    errors = _validate_spec_entrypoint_outcome_contract(feature_dir)
    payload, contract, read_errors = _entrypoint_outcome_spec_payload(feature_dir)
    if read_errors or payload is None or contract is None:
        return errors or read_errors
    if contract.get("triggered") is not True:
        return errors
    if errors:
        return errors

    inventory_by_id = _entrypoint_outcome_inventory_by_id(contract)
    active_dispositions = _entrypoint_outcome_active_dispositions(contract)
    if not active_dispositions:
        return errors
    plan_payload, plan_label, plan_errors = _entrypoint_outcome_plan_payload(
        feature_dir
    )
    errors.extend(plan_errors)
    if plan_payload is None:
        return errors

    obligation_ids = _consequence_obligation_ids(plan_payload)
    decisions = plan_payload.get("operational_consequence_decisions")
    if not isinstance(decisions, list) or not decisions:
        errors.append(
            f"{plan_label} operational_consequence_decisions must cover triggered entrypoint outcomes"
        )
        return errors

    decisions_by_ref: dict[str, list[dict[str, Any]]] = {}
    for index, raw_decision in enumerate(decisions):
        if not isinstance(raw_decision, dict):
            errors.append(
                f"{plan_label} operational_consequence_decisions[{index}] must be an object"
            )
            continue
        for consequence_ref in _decision_consequence_obligation_ids(raw_decision):
            decisions_by_ref.setdefault(consequence_ref, []).append(raw_decision)

    for outcome_id, disposition in active_dispositions.items():
        consequence_refs = {
            str(item).strip()
            for item in disposition.get("consequence_refs", [])
            if isinstance(item, str) and item.strip()
        }
        missing_obligations = sorted(consequence_refs - obligation_ids)
        if missing_obligations:
            errors.append(
                f"{plan_label} outcome {outcome_id} is missing consequence obligations: "
                + ", ".join(missing_obligations)
            )
        relevant_decisions = [
            decision
            for consequence_ref in consequence_refs
            for decision in decisions_by_ref.get(consequence_ref, [])
        ]
        if not relevant_decisions:
            errors.append(
                f"{plan_label} outcome {outcome_id} has no operational_consequence_decision"
            )
            continue
        inventory_item = inventory_by_id.get(outcome_id, {})
        for decision in relevant_decisions:
            for field in ENTRYPOINT_OUTCOME_PLAN_FIELDS:
                if not str(decision.get(field) or "").strip():
                    errors.append(
                        f"{plan_label} outcome {outcome_id} operational decision {field} must be non-empty"
                    )
            _validation_refs, list_errors = _entrypoint_outcome_string_list(
                decision.get("validation_refs"),
                "validation_refs",
                f"{plan_label} outcome {outcome_id} operational decision",
            )
            errors.extend(list_errors)
            if inventory_item.get("classification") == "recoverable-user-input":
                _security_constraints, list_errors = _entrypoint_outcome_string_list(
                    decision.get("security_constraints"),
                    "security_constraints",
                    f"{plan_label} outcome {outcome_id} operational decision",
                )
                errors.extend(list_errors)
    return errors


def _review_obligation_consequence_ids(obligation: Any) -> set[str]:
    if not isinstance(obligation, dict):
        return set()
    ids = _decision_consequence_obligation_ids(obligation)
    source_ref = str(obligation.get("source_ref") or "").strip()
    if source_ref.startswith("CA-"):
        ids.add(source_ref)
    return ids


def _validate_tasks_entrypoint_outcome_contract(feature_dir: Path) -> list[str]:
    if not (feature_dir / "spec-contract.json").is_file():
        return []
    errors = _validate_plan_entrypoint_outcome_contract(feature_dir)
    _payload, contract, read_errors = _entrypoint_outcome_spec_payload(feature_dir)
    if read_errors or contract is None:
        return errors or read_errors
    if contract.get("triggered") is not True:
        return errors
    if errors:
        return errors

    active_dispositions = _entrypoint_outcome_active_dispositions(contract)
    required_ids = {
        str(ref).strip()
        for disposition in active_dispositions.values()
        for ref in disposition.get("consequence_refs", [])
        if isinstance(ref, str) and ref.strip()
    }
    task_index_payload, task_errors = _read_json_artifact(
        feature_dir / "task-index.json", "task-index.json"
    )
    if task_errors:
        return [*errors, *task_errors]
    if not isinstance(task_index_payload, dict):
        return [*errors, "task-index.json must contain a top-level object"]

    declared_refs = task_index_payload.get("consequence_obligation_refs")
    declared_ids = (
        {
            str(item).strip()
            for item in declared_refs
            if isinstance(item, str) and item.strip()
        }
        if isinstance(declared_refs, list)
        else set()
    )
    missing_declared = sorted(required_ids - declared_ids)
    if missing_declared:
        errors.append(
            "task-index.json consequence_obligation_refs is missing entrypoint outcomes: "
            + ", ".join(missing_declared)
        )

    task_ids = _task_index_consequence_ids(task_index_payload)
    missing_task_ids = sorted(required_ids - task_ids)
    if missing_task_ids:
        errors.append(
            "task-index.json tasks are missing entrypoint outcome consequence mappings: "
            + ", ".join(missing_task_ids)
        )

    raw_scenarios = task_index_payload.get("system_review_scenarios")
    scenario_by_id = (
        {
            str(item.get("id") or "").strip(): item
            for item in raw_scenarios
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        if isinstance(raw_scenarios, list)
        else {}
    )
    raw_review_obligations = task_index_payload.get("review_obligations")
    review_obligations = (
        [item for item in raw_review_obligations if isinstance(item, dict)]
        if isinstance(raw_review_obligations, list)
        else []
    )
    review_by_ref: dict[str, list[dict[str, Any]]] = {}
    for obligation in review_obligations:
        for consequence_ref in _review_obligation_consequence_ids(obligation):
            review_by_ref.setdefault(consequence_ref, []).append(obligation)

    for consequence_ref in sorted(required_ids):
        matching_obligations = review_by_ref.get(consequence_ref, [])
        if not matching_obligations:
            errors.append(
                f"task-index.json review_obligations is missing entrypoint outcome {consequence_ref}"
            )
            continue
        for obligation in matching_obligations:
            scenario_ids, list_errors = _entrypoint_outcome_string_list(
                obligation.get("scenario_ids"),
                "scenario_ids",
                f"task-index.json review obligation {consequence_ref}",
            )
            errors.extend(list_errors)
            unknown_scenarios = sorted(
                scenario_id
                for scenario_id in scenario_ids
                if scenario_id not in scenario_by_id
            )
            if unknown_scenarios:
                errors.append(
                    f"task-index.json review obligation {consequence_ref} references unknown system review scenarios: "
                    + ", ".join(unknown_scenarios)
                )
            if obligation.get("required") is not True:
                errors.append(
                    f"task-index.json review obligation {consequence_ref} must be required"
                )
            for scenario_id in scenario_ids:
                scenario = scenario_by_id.get(scenario_id)
                if scenario is not None and scenario.get("required") is not True:
                    errors.append(
                        f"task-index.json system review scenario {scenario_id} for {consequence_ref} must be required"
                    )
    return errors


def _decision_consequence_obligation_ids(decision: Any) -> set[str]:
    if not isinstance(decision, dict):
        return set()
    ids: set[str] = set()
    raw_id = decision.get("obligation_id")
    if isinstance(raw_id, str) and raw_id.strip():
        ids.add(raw_id.strip())
    raw_ids = decision.get("consequence_obligation_ids")
    if isinstance(raw_ids, list):
        ids.update(
            item.strip() for item in raw_ids if isinstance(item, str) and item.strip()
        )
    elif isinstance(raw_ids, str) and raw_ids.strip():
        ids.add(raw_ids.strip())
    return ids


def _validate_brainstorming_json_artifact(
    feature_dir: Path, relative_path: str, *, validate_unknowns: bool
) -> list[str]:
    payload, read_errors = _read_json_artifact(
        feature_dir / relative_path, relative_path
    )
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


def _require_payload_keys(
    payload: dict[str, Any], label: str, keys: tuple[str, ...]
) -> list[str]:
    return [
        f"{label} payload missing {key}"
        for key in keys
        if not _is_non_empty_text(payload.get(key))
    ]


def _require_payload_any_key(
    payload: dict[str, Any], label: str, keys: tuple[str, ...], description: str
) -> list[str]:
    if _has_any_non_empty_key(payload, keys):
        return []
    return [f"{label} payload missing {description}"]


def _require_payload_basis_or_evidence_ids(
    payload: dict[str, Any], label: str
) -> list[str]:
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


def _validate_journal_event_payload(
    event: dict[str, Any], line_label: str
) -> list[str]:
    event_type = str(event.get("type") or "").strip()
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return [f"{line_label} payload must be an object"]

    errors: list[str] = []
    payload_label = f"{line_label} {event_type}"
    if event_type in {
        "session_started",
        "feature_workspace_created",
        "reopen_requested",
    }:
        return errors
    if event_type == "user_input_captured":
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("raw_excerpt", "excerpt"), "raw excerpt"
            )
        )
        errors.extend(_require_payload_keys(payload, payload_label, ("content_hash",)))
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("input_role", "role"), "input role"
            )
        )
    elif event_type == "question_asked":
        errors.extend(
            _require_payload_keys(
                payload, payload_label, ("question_id", "domain", "blocking_level")
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("field", "unknown_id"), "field or unknown_id"
            )
        )
    elif event_type == "answer_recorded":
        errors.extend(
            _require_payload_keys(
                payload,
                payload_label,
                ("question_id", "content_hash", "interpretation_summary", "confidence"),
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("answer_excerpt", "excerpt"), "answer excerpt"
            )
        )
    elif event_type == "repo_evidence_captured":
        errors.extend(
            _require_payload_keys(
                payload, payload_label, ("evidence_id", "relevance", "claim")
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("source_path", "path"), "source path"
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("excerpt_hash", "content_hash"),
                "excerpt or content hash",
            )
        )
    elif event_type == "research_evidence_captured":
        errors.extend(
            _require_payload_keys(payload, payload_label, ("evidence_id", "confidence"))
        )
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("source_url", "url", "source_path", "spike_path"),
                "source url/path/spike path",
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("excerpt_hash", "content_hash"),
                "excerpt or content hash",
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("relevance", "claim"), "relevance or claim"
            )
        )
    elif event_type == "unknown_opened":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("field", "domain", "question"),
                "field, domain, or question",
            )
        )
    elif event_type == "unknown_resolved":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("resolution", "resolved_value", "disposition"),
                "resolution",
            )
        )
    elif event_type == "unknown_deferred":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("deferred_to", "owner", "disposition"),
                "defer disposition",
            )
        )
    elif event_type == "unknown_waived":
        errors.extend(_require_payload_keys(payload, payload_label, ("unknown_id",)))
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("waiver_reason", "risk_acceptance", "disposition"),
                "waiver disposition",
            )
        )
    elif event_type == "decision_locked":
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("decision_id", "stable_id"),
                "stable decision ID",
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("locked_value", "selected_value", "decision"),
                "locked value",
            )
        )
        errors.extend(_require_payload_basis_or_evidence_ids(payload, payload_label))
    elif event_type == "route_selected":
        errors.extend(
            _require_payload_any_key(
                payload, payload_label, ("route_id", "stable_id"), "stable route ID"
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("selected_route", "selected_value", "route"),
                "selected route",
            )
        )
        errors.extend(_require_payload_basis_or_evidence_ids(payload, payload_label))
    elif event_type == "complexity_selected":
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("complexity_id", "stable_id"),
                "stable complexity ID",
            )
        )
        errors.extend(
            _require_payload_any_key(
                payload,
                payload_label,
                ("selected_complexity", "complexity_level", "selected_value"),
                "selected complexity",
            )
        )
        errors.extend(_require_payload_basis_or_evidence_ids(payload, payload_label))
    elif event_type == "stage_artifact_compiled":
        errors.extend(
            _require_payload_keys(
                payload, payload_label, ("artifact_path", "stage", "output_hash")
            )
        )
        errors.extend(
            _validate_event_reference_list(
                payload.get("input_event_range"),
                f"{payload_label} payload.input_event_range",
                None,
                exact_len=2,
            )
        )
        errors.extend(
            _validate_event_reference_list(
                payload.get("key_event_ids"),
                f"{payload_label} payload.key_event_ids",
                None,
            )
        )
        if not isinstance(payload.get("evidence_ids"), list):
            errors.append(f"{payload_label} payload.evidence_ids must be a list")
    elif event_type == "artifact_compiled":
        errors.extend(
            _require_payload_keys(
                payload,
                payload_label,
                ("artifact_path", "output_hash", "source_map_reference"),
            )
        )
        if not isinstance(payload.get("input_stage_artifacts"), list):
            errors.append(
                f"{payload_label} payload.input_stage_artifacts must be a list"
            )
        errors.extend(
            _validate_event_reference_list(
                payload.get("input_event_range"),
                f"{payload_label} payload.input_event_range",
                None,
                exact_len=2,
            )
        )
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
            errors.append(
                f"{payload_label} payload.checkpoint_event_id must equal event_id"
            )
    elif event_type == "legacy_state_imported":
        if not isinstance(payload.get("legacy_source_files"), list) or not payload.get(
            "legacy_source_files"
        ):
            errors.append(
                f"{payload_label} payload.legacy_source_files must be a non-empty list"
            )
        if not isinstance(
            payload.get("imported_artifact_hashes"), dict
        ) or not payload.get("imported_artifact_hashes"):
            errors.append(
                f"{payload_label} payload.imported_artifact_hashes must be a non-empty object"
            )
        errors.extend(
            _require_payload_keys(
                payload, payload_label, ("reconstruction_limits", "warning")
            )
        )
    return errors


def _validate_journal_event_payload_references(
    event: dict[str, Any], line_label: str, event_ids: set[str]
) -> list[str]:
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
            *_validate_event_reference_list(
                payload.get("key_event_ids"),
                f"{payload_label} payload.key_event_ids",
                event_ids,
            ),
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
            errors.append(
                f"brainstorming/journal.ndjson line {index} is invalid JSON: {exc.msg}"
            )
            continue
        if not isinstance(event, dict):
            errors.append(
                f"brainstorming/journal.ndjson line {index} must be an object"
            )
            continue

        event_id = str(event.get("event_id") or "").strip()
        event_type = str(event.get("type") or "").strip()
        stage = str(event.get("stage") or "").strip()
        if not event_id:
            errors.append(f"brainstorming/journal.ndjson line {index} missing event_id")
        if not event_type:
            errors.append(f"brainstorming/journal.ndjson line {index} missing type")
        elif event_type not in LOSSLESS_SPECIFY_EVENT_TYPES:
            errors.append(
                f"brainstorming/journal.ndjson line {index} unknown event type: {event_type}"
            )
        if type(event.get("schema_version")) is not int:
            errors.append(
                f"brainstorming/journal.ndjson line {index} schema_version must be an integer"
            )
        if not _is_non_empty_text(event.get("created_at")):
            errors.append(
                f"brainstorming/journal.ndjson line {index} missing created_at"
            )
        if not stage:
            errors.append(f"brainstorming/journal.ndjson line {index} missing stage")
        if stage and stage not in LOSSLESS_SPECIFY_STAGES:
            errors.append(
                f"brainstorming/journal.ndjson line {index} uses non-canonical stage: {stage}"
            )
        if not isinstance(event.get("source"), dict):
            errors.append(
                f"brainstorming/journal.ndjson line {index} source must be an object"
            )
        if not isinstance(event.get("payload"), dict):
            errors.append(
                f"brainstorming/journal.ndjson line {index} payload must be an object"
            )
        if not isinstance(event.get("writes"), list):
            errors.append(
                f"brainstorming/journal.ndjson line {index} writes must be a list"
            )
        supersedes_event_id = event.get("supersedes_event_id")
        if supersedes_event_id is not None and not isinstance(supersedes_event_id, str):
            errors.append(
                f"brainstorming/journal.ndjson line {index} supersedes_event_id must be null or string"
            )
        if event_type in LOSSLESS_SPECIFY_EVENT_TYPES:
            errors.extend(
                _validate_journal_event_payload(
                    event, f"brainstorming/journal.ndjson line {index}"
                )
            )
        events.append(event)

    return events, errors


def _validate_journal_event_references(
    events: list[dict[str, Any]], event_ids: set[str]
) -> list[str]:
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
        errors.append(
            f"{label} must contain exactly {exact_len} event IDs when non-empty"
        )
    for index, item in enumerate(value):
        if not _is_non_empty_text(item):
            errors.append(f"{label}[{index}] must be a non-empty event ID")
            continue
        if event_ids is not None and item.strip() not in event_ids:
            errors.append(
                f"{label}[{index}] references unknown journal event: {item.strip()}"
            )
    return errors


def _validate_compiled_from(
    payload: dict[str, Any], label: str, event_ids: set[str]
) -> list[str]:
    compiled_from = payload.get("compiled_from")
    if not isinstance(compiled_from, dict):
        return [f"{label} missing compiled_from"]

    errors: list[str] = []
    if (
        str(compiled_from.get("journal") or "").strip()
        != "brainstorming/journal.ndjson"
    ):
        errors.append(
            f"{label} compiled_from.journal must be brainstorming/journal.ndjson"
        )
    errors.extend(
        _validate_event_reference_list(
            compiled_from.get("event_range"),
            f"{label} compiled_from.event_range",
            event_ids,
            exact_len=2,
        )
    )
    errors.extend(
        _validate_event_reference_list(
            compiled_from.get("key_events"),
            f"{label} compiled_from.key_events",
            event_ids,
        )
    )
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
        workflow_state_content = workflow_state_path.read_text(
            encoding="utf-8", errors="replace"
        )
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
            errors.append(
                f"workflow-state.md Lossless Resume State {field} is required"
            )
    if journal_file != "brainstorming/journal.ndjson":
        errors.append(
            "workflow-state.md Lossless Resume State journal_file must be brainstorming/journal.ndjson"
        )
    if stage_manifest != "brainstorming/stage-manifest.json":
        errors.append(
            "workflow-state.md Lossless Resume State stage_manifest must be brainstorming/stage-manifest.json"
        )
    if last_event_id and last_event_id != "none" and last_event_id not in event_ids:
        errors.append(
            f"workflow-state.md Lossless Resume State last_event_id not found in journal: {last_event_id}"
        )
    if (
        last_checkpoint_id
        and last_checkpoint_id != "none"
        and last_checkpoint_id not in checkpoint_ids
    ):
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
    event_ids = {
        str(event.get("event_id") or "").strip()
        for event in events
        if str(event.get("event_id") or "").strip()
    }
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
        errors.append(
            "brainstorming/stage-manifest.json must contain a top-level object"
        )
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
                errors.append(
                    f"brainstorming/stage-manifest.json uses non-canonical stage: {stage}"
                )
                continue
            entry = stages[stage]
            if not isinstance(entry, dict):
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage} must be an object"
                )
                continue
            expected_artifact = LOSSLESS_SPECIFY_STAGE_ARTIFACTS[stage]
            actual_artifact = str(entry.get("artifact") or "").strip()
            if actual_artifact != expected_artifact:
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage}.artifact must be "
                    f"{expected_artifact}, found {actual_artifact or 'missing'}"
                )
            if "event_range" not in entry:
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage}.event_range is required"
                )
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
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage}.last_compiled_event_id is required"
                )
            elif entry.get("last_compiled_event_id") is not None:
                last_compiled_event_id = str(
                    entry.get("last_compiled_event_id") or ""
                ).strip()
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
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage}.artifact_hash is required"
                )
            elif entry.get("artifact_hash") is not None and not isinstance(
                entry.get("artifact_hash"), str
            ):
                errors.append(
                    f"brainstorming/stage-manifest.json stages.{stage}.artifact_hash must be a string or null"
                )

    canonical_stage_enum = manifest.get("canonical_stage_enum")
    if not isinstance(canonical_stage_enum, list):
        errors.append(
            "brainstorming/stage-manifest.json canonical_stage_enum must be a list"
        )
    else:
        canonical_stage_set = {str(item) for item in canonical_stage_enum}
        missing = sorted(LOSSLESS_SPECIFY_STAGES - canonical_stage_set)
        extra = sorted(canonical_stage_set - LOSSLESS_SPECIFY_STAGES)
        if missing:
            errors.append(
                f"brainstorming/stage-manifest.json canonical_stage_enum missing: {', '.join(missing)}"
            )
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
            errors.append(
                f"brainstorming/stage-manifest.json last_event_id not found in journal: {last_event_id}"
            )
        if last_checkpoint_id and last_checkpoint_id not in checkpoint_ids:
            errors.append(
                "brainstorming/stage-manifest.json last_checkpoint_id not found as checkpoint_written "
                f"event in journal: {last_checkpoint_id}"
            )
    errors.extend(
        _validate_lossless_resume_state(
            feature_dir, event_ids, checkpoint_ids, manifest_last_checkpoint_id
        )
    )

    for relative_path in (
        "brainstorming/facts.json",
        "brainstorming/route.json",
        "brainstorming/intent.json",
        "brainstorming/complexity.json",
        "brainstorming/domains.json",
        "brainstorming/evidence-index.json",
        "brainstorming/handoff-to-specify.json",
    ):
        payload, read_errors = _read_json_artifact(
            feature_dir / relative_path, relative_path
        )
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
    payload, read_errors = _read_json_artifact(
        feature_dir / "capability-ledger.json", "capability-ledger.json"
    )
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["capability-ledger.json must contain a top-level JSON object"]
    if not isinstance(payload.get("capabilities"), list):
        return ["capability-ledger.json must define a top-level capabilities array"]
    return []


def _validate_control_ledger(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(
        feature_dir / "control-ledger.json", "control-ledger.json"
    )
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
            errors.append(
                f"deep-research.md not-needed output is missing required section: {section}"
            )

    feasibility_section = _extract_markdown_section(content, "Feasibility Decision")
    handoff_section = _extract_markdown_section(content, "Planning Handoff")
    next_command_section = _extract_markdown_section(content, "Next Command")

    if "**Recommendation**" not in feasibility_section:
        errors.append(
            "deep-research.md not-needed Feasibility Decision is missing **Recommendation**"
        )
    elif "/sp.plan" not in feasibility_section:
        errors.append(
            "deep-research.md not-needed Feasibility Decision must recommend `/sp.plan`"
        )

    if "**Reason**" not in feasibility_section:
        errors.append(
            "deep-research.md not-needed Feasibility Decision is missing **Reason**"
        )

    if "**Handoff IDs**" not in handoff_section:
        errors.append(
            "deep-research.md not-needed Planning Handoff is missing **Handoff IDs**"
        )
    elif "not needed" not in handoff_section.lower():
        errors.append(
            "deep-research.md not-needed Planning Handoff must mark handoff IDs as Not needed"
        )

    if "**Recommended approach**" not in handoff_section:
        errors.append(
            "deep-research.md not-needed Planning Handoff is missing **Recommended approach**"
        )
    if "**Constraints `/sp.plan` must preserve**" not in handoff_section:
        errors.append(
            "deep-research.md not-needed Planning Handoff is missing **Constraints `/sp.plan` must preserve**"
        )

    if "/sp.plan" not in next_command_section:
        errors.append("deep-research.md not-needed Next Command must be `/sp.plan`")

    return errors


DEEP_RESEARCH_CAPABILITY_REF_RE = re.compile(r"^CAP-[0-9]{3,}$")
DEEP_RESEARCH_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _deep_research_gate_contract_present(feature_dir: Path) -> bool:
    """Return whether the feature uses the runtime-owned Deep Research contract."""

    spec_path = feature_dir / "spec-contract.json"
    if not spec_path.exists():
        return False
    if not spec_path.is_file():
        return True
    try:
        payload = _read_json(spec_path)
    except (OSError, json.JSONDecodeError):
        return True
    return not isinstance(payload, dict) or "feasibility_gate" in payload


def _deep_research_string_array(
    value: Any, label: str, *, required: bool = False
) -> tuple[list[str], list[str]]:
    if not isinstance(value, list):
        return [], [f"{label} must be an array"]
    values: list[str] = []
    errors: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}[{index}] must be a non-empty string")
            continue
        values.append(item.strip())
    duplicates = sorted(value for value in set(values) if values.count(value) > 1)
    if duplicates:
        errors.append(f"{label} must be unique: " + ", ".join(duplicates))
    if required and not values:
        errors.append(f"{label} must not be empty")
    return values, errors


def _read_deep_research_feasibility_gate(
    feature_dir: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    spec_path = feature_dir / "spec-contract.json"
    payload, errors = _read_json_artifact(spec_path, "spec-contract.json")
    if errors:
        return None, errors
    if not isinstance(payload, dict):
        return None, ["spec-contract.json must contain a top-level JSON object"]
    gate = payload.get("feasibility_gate")
    if not isinstance(gate, dict):
        return None, ["spec-contract.json feasibility_gate must be an object"]

    decision = str(gate.get("decision") or "").strip().lower()
    result: dict[str, Any] = {"decision": decision}
    gate_errors: list[str] = []
    if decision not in {"required", "not_selected"}:
        gate_errors.append(
            "spec-contract.json feasibility_gate.decision must be required or not_selected"
        )

    capability_refs, capability_errors = _deep_research_string_array(
        gate.get("capability_refs"),
        "spec-contract.json feasibility_gate.capability_refs",
        required=decision == "required",
    )
    gate_errors.extend(capability_errors)
    invalid_capability_refs = sorted(
        ref
        for ref in capability_refs
        if DEEP_RESEARCH_CAPABILITY_REF_RE.fullmatch(ref) is None
    )
    if invalid_capability_refs:
        gate_errors.append(
            "spec-contract.json feasibility_gate.capability_refs contains invalid refs: "
            + ", ".join(invalid_capability_refs)
        )
    if decision == "not_selected" and capability_refs:
        gate_errors.append(
            "spec-contract.json not_selected feasibility_gate cannot carry capability refs"
        )

    reason_refs, reason_errors = _deep_research_string_array(
        gate.get("reason_refs"),
        "spec-contract.json feasibility_gate.reason_refs",
    )
    gate_errors.extend(reason_errors)
    result["capability_refs"] = capability_refs
    result["reason_refs"] = reason_refs
    return result, gate_errors


def _deep_research_feature_ref(
    project_root: Path, feature_dir: Path
) -> tuple[str, list[str]]:
    try:
        feature_ref = feature_dir.resolve().relative_to(project_root.resolve())
    except ValueError:
        return "", ["feature_dir must stay within the project root"]
    return feature_ref.as_posix(), []


def _runtime_deep_research_handoff(
    project_root: Path,
    feature_dir: Path,
    *,
    handoff_ref: str = "",
    handoff_sha256: str = "",
) -> tuple[dict[str, Any] | None, list[str]]:
    feature_ref, errors = _deep_research_feature_ref(project_root, feature_dir)
    if errors:
        return None, errors
    extra_args: list[str] = []
    if handoff_ref:
        extra_args.extend(("--handoff-ref", handoff_ref))
    if handoff_sha256:
        extra_args.extend(("--expected-sha256", handoff_sha256))
    try:
        envelope = run_specify_runtime(
            [
                "deep-research",
                "verify-handoff",
                "--feature-dir",
                feature_ref,
                *extra_args,
                "--format",
                "json",
            ],
            cwd=project_root,
            check=False,
        )
    except SpecifyRuntimeError as exc:
        return None, [f"Deep Research runtime verification is unavailable: {exc}"]

    if str(envelope.get("status") or "").strip().lower() != "ok":
        summary = str(envelope.get("summary") or "handoff verification failed").strip()
        messages = [f"Deep Research runtime verification failed: {summary}"]
        blockers = envelope.get("blockers")
        if isinstance(blockers, list):
            messages.extend(
                f"Deep Research runtime blocker: {blocker}"
                for blocker in blockers
                if str(blocker).strip()
            )
        return None, messages
    data = envelope.get("data")
    if not isinstance(data, dict):
        return None, ["Deep Research runtime verification returned no binding data"]
    return data, []


def _validate_runtime_deep_research_artifact(
    project_root: Path, feature_dir: Path
) -> list[str]:
    gate, errors = _read_deep_research_feasibility_gate(feature_dir)
    if errors or gate is None:
        return errors
    if gate["decision"] != "required":
        return ["deep-research validation requires feasibility_gate.decision=required"]
    _binding, verify_errors = _runtime_deep_research_handoff(project_root, feature_dir)
    return verify_errors


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
            errors.append(
                f"deep-research.md Planning Handoff is missing field: {field}"
            )

    if "CAP-" not in content:
        errors.append(
            "deep-research.md is missing capability traceability IDs such as CAP-001"
        )
    if "TRK-" not in content:
        errors.append("deep-research.md is missing research track IDs such as TRK-001")
    if "EVD-" not in content and "SPK-" not in content:
        errors.append(
            "deep-research.md is missing evidence or spike IDs such as EVD-001 or SPK-001"
        )
    if "PH-" not in handoff_section and "not needed" not in handoff_section.lower():
        errors.append("deep-research.md is missing Planning Handoff IDs such as PH-001")

    return errors


def _validate_plan_consumes_deep_research(feature_dir: Path) -> list[str]:
    deep_research_path = feature_dir / "deep-research.md"
    plan_path = feature_dir / "plan.md"
    if not deep_research_path.exists() or not plan_path.exists():
        return []

    deep_research_content = deep_research_path.read_text(
        encoding="utf-8", errors="replace"
    )
    handoff_section = _extract_markdown_section(
        deep_research_content, "Planning Handoff"
    )
    handoff_ids = _extract_handoff_ids(handoff_section)
    if not handoff_ids:
        return []

    plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    if "Deep Research Traceability Matrix" not in plan_content:
        errors.append(
            "plan.md is missing Deep Research Traceability Matrix for deep-research handoff IDs"
        )

    traceability_section = _extract_markdown_section(
        plan_content, "Deep Research Traceability Matrix"
    )
    if not traceability_section and "Deep Research Traceability Matrix" in plan_content:
        errors.append(
            "plan.md Deep Research Traceability Matrix must be a level-2 markdown section"
        )

    missing_columns = [
        column
        for column in PLAN_DEEP_RESEARCH_TRACEABILITY_COLUMNS
        if column not in traceability_section
    ]
    if missing_columns:
        joined = ", ".join(missing_columns)
        errors.append(
            f"plan.md Deep Research Traceability Matrix is missing required columns: {joined}"
        )

    missing_ids = sorted(
        handoff_id
        for handoff_id in handoff_ids
        if handoff_id not in traceability_section
    )
    if missing_ids:
        joined = ", ".join(missing_ids)
        errors.append(
            f"plan.md does not consume deep-research Planning Handoff IDs: {joined}"
        )

    return errors


def _validate_plan_deep_research_binding(
    project_root: Path, feature_dir: Path
) -> list[str]:
    gate, errors = _read_deep_research_feasibility_gate(feature_dir)
    if errors or gate is None:
        return errors

    plan_payload: Any | None = None
    plan_label = "plan-contract.json"
    for candidate, label in _consequence_contract_paths(feature_dir):
        if not candidate.is_file():
            continue
        plan_payload, read_errors = _read_json_artifact(candidate, label)
        if read_errors:
            return read_errors
        plan_label = label
        break
    if not isinstance(plan_payload, dict):
        return [f"{plan_label} must contain a top-level JSON object"]

    binding = plan_payload.get("deep_research_binding")
    if not isinstance(binding, dict):
        return [f"{plan_label} deep_research_binding must be an object"]
    decision = str(binding.get("decision") or "").strip().lower()
    if decision != gate["decision"]:
        errors.append(
            f"{plan_label} deep_research_binding.decision must match the specification feasibility gate"
        )

    handoff_ids, id_errors = _deep_research_string_array(
        binding.get("handoff_ids"),
        f"{plan_label} deep_research_binding.handoff_ids",
    )
    errors.extend(id_errors)
    if gate["decision"] == "not_selected":
        if handoff_ids:
            errors.append(
                f"{plan_label} not_selected deep_research_binding cannot carry handoff IDs"
            )
        for field in (
            "handoff_ref",
            "handoff_sha256",
            "source_spec_sha256",
            "state_revision",
            "claim_status",
        ):
            value = binding.get(field)
            if value is not None and str(value).strip():
                errors.append(
                    f"{plan_label} not_selected deep_research_binding.{field} must be null"
                )
        return errors

    handoff_ref = str(binding.get("handoff_ref") or "").strip()
    handoff_sha256 = str(binding.get("handoff_sha256") or "").strip()
    source_spec_sha256 = str(binding.get("source_spec_sha256") or "").strip()
    claim_status = str(binding.get("claim_status") or "").strip()
    state_revision = binding.get("state_revision")
    if not handoff_ref:
        errors.append(
            f"{plan_label} required deep_research_binding.handoff_ref must be non-empty"
        )
    if DEEP_RESEARCH_SHA256_RE.fullmatch(handoff_sha256) is None:
        errors.append(
            f"{plan_label} required deep_research_binding.handoff_sha256 must be a SHA-256 digest"
        )
    if DEEP_RESEARCH_SHA256_RE.fullmatch(source_spec_sha256) is None:
        errors.append(
            f"{plan_label} required deep_research_binding.source_spec_sha256 must be a SHA-256 digest"
        )
    if (
        not isinstance(state_revision, int)
        or isinstance(state_revision, bool)
        or state_revision < 1
    ):
        errors.append(
            f"{plan_label} required deep_research_binding.state_revision must be a positive integer"
        )
    if not claim_status:
        errors.append(
            f"{plan_label} required deep_research_binding.claim_status must be non-empty"
        )
    if errors:
        return errors

    verified, verify_errors = _runtime_deep_research_handoff(
        project_root,
        feature_dir,
        handoff_ref=handoff_ref,
        handoff_sha256=handoff_sha256,
    )
    if verify_errors or verified is None:
        return [*errors, *verify_errors]

    expected_scalars = {
        "handoff_ref": handoff_ref,
        "handoff_sha256": handoff_sha256,
        "source_spec_sha256": source_spec_sha256,
        "state_revision": state_revision,
        "claim_status": claim_status,
    }
    for field, expected in expected_scalars.items():
        if verified.get(field) != expected:
            errors.append(
                f"{plan_label} Deep Research binding {field} does not match the verified runtime handoff"
            )
    verified_ids = verified.get("handoff_ids")
    if not isinstance(verified_ids, list) or set(verified_ids) != set(handoff_ids):
        errors.append(
            f"{plan_label} Deep Research binding handoff_ids do not match the verified runtime handoff"
        )
    return errors


def _validate_plan_test_design_gate(feature_dir: Path) -> list[str]:
    from ..task_authoring import TaskAuthoringError, _parse_plan_test_design_gate

    decisions: list[tuple[str, str, dict[str, Any] | None]] = []
    for candidate, label in _consequence_contract_paths(feature_dir):
        if not candidate.is_file():
            continue
        plan_payload, read_errors = _read_json_artifact(candidate, label)
        if read_errors:
            return read_errors
        if not isinstance(plan_payload, dict):
            return [f"{label} must contain a top-level JSON object"]
        try:
            decision, binding = _parse_plan_test_design_gate(
                plan_payload, label=label
            )
        except TaskAuthoringError as exc:
            return [str(exc)]
        decisions.append((label, decision, binding))
    if not decisions:
        return ["plan-contract.json or plan/plan-contract.json is required"]
    if len({decision for _, decision, _ in decisions}) != 1:
        rendered = ", ".join(
            f"{label}={decision}" for label, decision, _ in decisions
        )
        return ["conflicting plan-contract test_design_gate decisions: " + rendered]
    first_binding = decisions[0][2]
    if any(binding != first_binding for _, _, binding in decisions[1:]):
        rendered = ", ".join(
            f"{label}={binding!r}" for label, _, binding in decisions
        )
        return ["conflicting plan-contract test_design_gate bindings: " + rendered]
    return []


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
            errors.append(
                f"plan.md is missing {CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION} for {ids}"
            )

        operational_decisions = (
            payload.get("operational_consequence_decisions")
            if isinstance(payload, dict)
            else None
        )
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


UI_CONTRACT_SCALAR_FIELDS = (
    "subject",
    "audience",
    "single_job",
    "visual_thesis",
    "content_thesis",
    "interaction_thesis",
    "signature_element",
    "approved_visual_ref",
)
UI_CONTRACT_LIST_FIELDS = (
    "platforms",
    "design_decision_ids",
    "handoff_contract_ids",
    "reference_intents",
    "real_content_plan",
    "image_plan",
    "surface_catalog",
    "scenario_matrix",
    "interaction_matrix",
    "editing_matrix",
    "data_state_matrix",
    "accessibility_matrix",
    "navigation_matrix",
    "content_matrix",
    "color_modes",
    "component_contracts",
    "responsive_matrix",
    "visual_acceptance_matrix",
    "accepted_deviations",
    "required_evidence",
)
UI_CONTRACT_OBJECT_FIELDS = (
    "style_authority",
    "motion_contract",
    "usability_validation",
    "comparison_tolerance",
)
UI_APPROVAL_DIGEST_FIELDS = (
    "approved_preview_sha256",
    "approved_manifest_sha256",
    "approved_handoff_sha256",
)
UI_APPROVAL_REFERENCE_FIELDS = ("approved_handoff_ref",)
UI_DESIGN_CHANGE_BINDING_FIELDS = (
    "design_change_id",
    "design_change_ref",
    "design_change_sha256",
    "design_contract_ref",
)
UI_SPEC_PLAN_CONTINUITY_LIST_FIELDS = (
    "entry_points",
    "required_states",
    "must_preserve",
    "may_adapt",
    "must_not",
    "visual_acceptance",
)
UI_CONTINUITY_LIST_FIELDS = frozenset(
    (*UI_CONTRACT_LIST_FIELDS, *UI_SPEC_PLAN_CONTINUITY_LIST_FIELDS)
)
UI_ACTIVE_FIDELITY_MODES = {"approximate", "high", "inspiration"}
UI_CONTRACT_SURFACE_TYPES = {
    "landing",
    "product-workspace",
    "hybrid",
    "existing-pattern-maintenance",
}
UI_CONTRACT_PLATFORMS = {"web", "mobile", "desktop", "tui", "cli"}
UI_CONTRACT_REFERENCE_INTENTS = {
    "exact",
    "preserve-structure",
    "inspiration",
    "extract-tokens",
    "do-not-copy",
}
UI_CONTRACT_EVIDENCE = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
    "visual_comparison_or_human_review",
}
UI_DESIGN_DECISION_ID_RE = re.compile(r"^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
UI_DESIGN_HANDOFF_ID_RE = re.compile(r"^DH-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
UI_DESIGN_CHANGE_ID_RE = re.compile(r"^UD-\d{4}$")
UI_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UI_APPROVED_PREVIEW_REF_RE = re.compile(
    r"round-\d+\.(?:html|png|jpe?g|webp)#direction-[a-z0-9-]+$", re.IGNORECASE
)


def _ui_contract_has_nonblank_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(
        isinstance(item, str) and item.strip() for item in value
    ) and not any(not isinstance(item, str) or not item.strip() for item in value)


def _ui_contract_valid_data_scenario(item: Any) -> bool:
    return isinstance(item, dict) and all(
        str(item.get(field) or "").strip()
        for field in ("state", "data_condition", "expectation")
    )


def _ui_contract_valid_component_adoption(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not str(value.get("resource_id") or "").strip():
        return False
    if value.get("action") not in {"reuse", "extend", "add", "custom"}:
        return False
    if any(
        not isinstance(value.get(field), str)
        or not str(value.get(field) or "").strip()
        for field in ("package", "version", "license", "source_ref")
    ):
        return False
    if any(
        not _ui_contract_has_nonblank_string_list(value.get(field))
        for field in ("component_refs", "reason_codes", "selection_basis_refs")
    ):
        return False
    gate = value.get("permission_gate")
    status = value.get("permission_status")
    return (
        gate in {"required", "not-required"}
        and status in {"authorized", "not-authorized"}
        and (value.get("action") != "add" or gate == "required")
        and (gate != "not-required" or status == "authorized")
    )


def _ui_contract_valid_row_refs(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    if not isinstance(item, dict):
        return False
    row_id = str(item.get("id") or "").strip()
    row_decisions = item.get("decision_ids")
    if not row_id or not _ui_contract_has_nonblank_string_list(row_decisions):
        return False
    assert isinstance(row_decisions, list)
    if any(decision_id not in decision_ids for decision_id in row_decisions):
        return False
    if handoff_ids:
        return row_id in handoff_ids
    return not UI_DESIGN_HANDOFF_ID_RE.fullmatch(row_id)


def _ui_contract_valid_surface_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
    component_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        and bool(str(item.get("profile_id") or "").strip())
        and bool(str(item.get("name") or "").strip())
        and bool(str(item.get("kind") or "").strip())
        and bool(str(item.get("entrypoint_id") or "").strip())
        and _ui_contract_has_nonblank_string_list(item.get("source_refs"))
        and _ui_contract_has_nonblank_string_list(item.get("specimen_ids"))
        and _ui_contract_has_nonblank_string_list(item.get("component_ids"))
        and set(item.get("component_ids") or []) <= component_ids
    )


def _ui_contract_valid_interaction_script(
    value: Any,
    data_state_ids: set[str],
) -> bool:
    required_fields = {
        "preconditions",
        "start_state_id",
        "steps",
        "branches",
        "focus_checkpoint",
        "announcement_checkpoint",
        "completion_checkpoint",
        "recovery_checkpoint",
    }
    if not isinstance(value, dict) or set(value) != required_fields:
        return False
    steps = value.get("steps")
    branches = value.get("branches")
    allowed_conditions = {
        "success",
        "failure",
        "timeout",
        "cancel",
        "retry",
        "duplicate",
        "out_of_order",
    }
    seen_conditions: set[str] = set()
    valid_branches = isinstance(branches, list) and bool(branches)
    for branch in branches if isinstance(branches, list) else []:
        if (
            not isinstance(branch, dict)
            or set(branch)
            != {
                "conditions",
                "setup",
                "expected_state_id",
                "expected_feedback",
                "focus_behavior",
                "announcement",
                "continuation",
            }
            or not _ui_contract_has_nonblank_string_list(
                branch.get("conditions")
            )
        ):
            valid_branches = False
            continue
        conditions = set(branch.get("conditions") or [])
        if (
            not conditions <= allowed_conditions
            or conditions & seen_conditions
            or str(branch.get("expected_state_id") or "").strip()
            not in data_state_ids
            or any(
                not str(branch.get(field) or "").strip()
                for field in (
                    "setup",
                    "expected_feedback",
                    "focus_behavior",
                    "announcement",
                    "continuation",
                )
            )
        ):
            valid_branches = False
        seen_conditions.update(conditions)
    valid_branches = (
        valid_branches
        and "success" in seen_conditions
        and bool(seen_conditions & {"failure", "timeout", "cancel"})
        and bool(seen_conditions & {"retry", "duplicate", "out_of_order"})
    )
    return (
        _ui_contract_has_nonblank_string_list(value.get("preconditions"))
        and str(value.get("start_state_id") or "").strip() in data_state_ids
        and isinstance(steps, list)
        and bool(steps)
        and all(
            isinstance(step, dict)
            and set(step) == {"input", "action", "expected_feedback"}
            and all(
                str(step.get(field) or "").strip()
                for field in ("input", "action", "expected_feedback")
            )
            for step in steps
        )
        and valid_branches
        and all(
            str(value.get(field) or "").strip()
            for field in (
                "focus_checkpoint",
                "announcement_checkpoint",
                "completion_checkpoint",
                "recovery_checkpoint",
            )
        )
    )


def _ui_contract_valid_editing_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    required_fields = {
        "id",
        "surface",
        "input_methods",
        "composition_behavior",
        "paste_autofill_behavior",
        "selection_caret_behavior",
        "formatting_behavior",
        "validation_timing",
        "validation_feedback",
        "dirty_state_behavior",
        "persistence_behavior",
        "undo_redo_behavior",
        "conflict_behavior",
        "read_only_disabled_behavior",
        "submission_behavior",
        "decision_ids",
    }
    return (
        isinstance(item, dict)
        and set(item) == required_fields
        and _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        and _ui_contract_has_nonblank_string_list(item.get("input_methods"))
        and all(
            str(item.get(field) or "").strip()
            for field in required_fields
            - {"input_methods", "decision_ids"}
        )
    )


def _ui_contract_valid_scenario_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
    surface_ids: set[str],
    rows_by_field: dict[str, dict[str, dict[str, Any]]],
) -> bool:
    if (
        not isinstance(item, dict)
        or not _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        or str(item.get("surface_id") or "").strip() not in surface_ids
        or not str(item.get("name") or "").strip()
        or item.get("risk") not in {"low", "medium", "high"}
        or item.get("required") is not True
        or not _ui_contract_valid_interaction_script(
            item.get("interaction_script"),
            {
                str(state_id).strip()
                for state_id in item.get("data_state_ids") or []
                if isinstance(state_id, str) and state_id.strip()
            },
        )
    ):
        return False
    referenced_decisions: set[str] = set()
    for field, rows_by_id in rows_by_field.items():
        refs = item.get(field)
        if not _ui_contract_has_nonblank_string_list(refs):
            return False
        assert isinstance(refs, list)
        if any(ref not in rows_by_id for ref in refs):
            return False
        referenced_decisions.update(
            decision_id
            for row_id in refs
            for decision_id in rows_by_id[row_id].get("decision_ids") or []
            if isinstance(decision_id, str) and decision_id.strip()
        )
    return set(item.get("decision_ids") or []) == referenced_decisions


def _ui_contract_valid_responsive_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    if (
        not isinstance(item, dict)
        or not _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        or not str(item.get("state") or "").strip()
        or not str(item.get("adaptation") or "").strip()
        or not str(item.get("stretch_behavior") or "").strip()
        or not str(item.get("overflow_behavior") or "").strip()
        or not _ui_contract_has_nonblank_string_list(item.get("decision_ids"))
    ):
        return False
    if str(item.get("viewport") or "").strip():
        return True
    target = item.get("target")
    return (
        isinstance(target, dict)
        and isinstance(target.get("width"), (int, float))
        and not isinstance(target.get("width"), bool)
        and target.get("width") > 0
        and isinstance(target.get("height"), (int, float))
        and not isinstance(target.get("height"), bool)
        and target.get("height") > 0
        and target.get("unit") in {"px", "cell", "point"}
    )


def _ui_contract_valid_accessibility_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        and bool(str(item.get("surface") or "").strip())
        and _ui_contract_has_nonblank_string_list(item.get("semantics"))
        and bool(str(item.get("reading_order") or "").strip())
        and bool(str(item.get("focus_order") or "").strip())
        and _ui_contract_has_nonblank_string_list(item.get("keyboard"))
        and _ui_contract_has_nonblank_string_list(item.get("announcements"))
        and bool(str(item.get("target_size") or "").strip())
        and bool(str(item.get("contrast") or "").strip())
        and bool(str(item.get("zoom_reflow") or "").strip())
        and _ui_contract_has_nonblank_string_list(item.get("alternatives"))
    )


def _ui_contract_valid_visual_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    if not isinstance(item, dict) or not _ui_contract_valid_row_refs(
        item, decision_ids, handoff_ids
    ):
        return False
    if (
        str(item.get("viewport") or "").strip()
        and str(item.get("state") or "").strip()
        and str(item.get("evidence") or "").strip()
    ):
        return True
    target_id = str(item.get("target_id") or "").strip()
    if not target_id or not all(
        isinstance(item.get(field), list) and bool(item.get(field))
        for field in (
            "states",
            "color_modes",
            "motion_modes",
            "decision_ids",
            "must_match",
            "evidence",
        )
    ):
        return False
    if handoff_ids:
        return target_id in handoff_ids
    return not UI_DESIGN_HANDOFF_ID_RE.fullmatch(target_id)


def _ui_contract_valid_navigation_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        and all(
            str(item.get(field) or "").strip()
            for field in (
                "surface",
                "entry",
                "destination",
                "trigger",
                "back_behavior",
                "deep_link_behavior",
                "interruption_recovery",
            )
        )
    )


def _ui_contract_valid_content_row(
    item: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
        and all(
            str(item.get(field) or "").strip()
            for field in (
                "surface",
                "state",
                "purpose",
                "copy",
                "primary_action",
                "trust_requirement",
                "localization",
            )
        )
        and _ui_contract_has_nonblank_string_list(item.get("content_limits"))
    )


def _ui_contract_valid_motion(
    value: Any,
    decision_ids: set[str],
    handoff_ids: set[str],
) -> bool:
    if (
        not isinstance(value, dict)
        or not str(value.get("purpose") or "").strip()
        or not str(value.get("reduced_motion") or "").strip()
    ):
        return False
    transitions = value.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        return False
    for item in transitions:
        if (
            not isinstance(item, dict)
            or not _ui_contract_valid_row_refs(item, decision_ids, handoff_ids)
            or not all(
                str(item.get(field) or "").strip()
                for field in (
                    "surface",
                    "trigger",
                    "response",
                    "easing",
                    "interrupt_behavior",
                )
            )
        ):
            return False
        duration = item.get("duration_ms")
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or duration < 0
        ):
            return False
    timing = value.get("feedback_timing")
    if not isinstance(timing, dict):
        return False
    values: list[float] = []
    for field in ("immediate_ms", "progress_ms", "timeout_ms"):
        raw = timing.get(field)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw < 0:
            return False
        values.append(float(raw))
    return values == sorted(values)


def _ui_contract_valid_usability(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("risk_level") not in {
        "low",
        "medium",
        "high",
    }:
        return False
    if not all(
        _ui_contract_has_nonblank_string_list(value.get(field))
        for field in ("methods", "critical_tasks", "success_criteria")
    ):
        return False
    human_review_required = value.get("human_review_required")
    if not isinstance(human_review_required, bool):
        return False
    smoothness_ids = value.get("smoothness_acceptance_ids")
    if smoothness_ids is not None:
        if not isinstance(smoothness_ids, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in smoothness_ids
        ):
            return False
        normalized_ids = [item.strip() for item in smoothness_ids]
        if len(normalized_ids) != len(set(normalized_ids)):
            return False
    budgets = value.get("performance_budgets")
    if budgets is not None:
        expected = {
            "inp_ms",
            "long_task_ms",
            "cls",
            "animation_dropped_frame_pct",
            "bundle_delta_kb",
        }
        if not isinstance(budgets, dict) or set(budgets) != expected:
            return False
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or item < 0
            for item in budgets.values()
        ):
            return False
    return value.get("risk_level") != "high" or human_review_required


def _canonical_ui_continuity_value(field: str, value: Any) -> Any:
    """Normalize order-insensitive UI collections for continuity checks."""

    if field in UI_DESIGN_CHANGE_BINDING_FIELDS:
        return str(value or "").strip()

    if (
        field not in UI_CONTINUITY_LIST_FIELDS
        and field not in UI_CONTRACT_OBJECT_FIELDS
    ):
        return value

    def canonical(item: Any) -> Any:
        if isinstance(item, dict):
            return tuple(
                sorted((str(key), canonical(nested)) for key, nested in item.items())
            )
        if isinstance(item, list):
            normalized = [canonical(nested) for nested in item]
            return tuple(sorted(normalized, key=repr))
        if isinstance(item, str):
            return item.strip()
        return item

    if isinstance(value, list):
        normalized = [canonical(item) for item in value]
        return tuple(sorted(normalized, key=repr))
    if isinstance(value, dict):
        return canonical(value)
    return value


def _normalized_ui_string_values(field: str, contract: dict[str, Any]) -> set[str]:
    value = contract.get(field)
    if not isinstance(value, list):
        return set()
    return {
        str(item).strip() for item in value if isinstance(item, str) and item.strip()
    }


def _validate_ui_style_authority(value: Any, label: str) -> list[str]:
    expected_fields = {
        "mode",
        "scope_level",
        "source_refs",
        "protected_surfaces",
        "allowed_style_delta_surfaces",
        "authorization_source",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        return [f"{label}.style_authority must contain the current exact fields"]
    mode = str(value.get("mode") or "").strip()
    scope_level = str(value.get("scope_level") or "").strip()
    lists: dict[str, list[str]] = {}
    errors: list[str] = []
    for field in (
        "source_refs",
        "protected_surfaces",
        "allowed_style_delta_surfaces",
    ):
        raw = value.get(field)
        if not isinstance(raw, list) or any(
            not isinstance(item, str) or not item.strip() for item in raw
        ) or len(raw) != len(set(raw)):
            errors.append(f"{label}.style_authority.{field} must be a string list")
            lists[field] = []
        else:
            lists[field] = [item.strip() for item in raw]
    if errors:
        return errors
    if mode not in {
        "greenfield",
        "inherit-existing",
        "page-overhaul-authorized",
    }:
        errors.append(f"{label}.style_authority.mode must be resolved")
    if scope_level not in {"feature-partial", "page"}:
        errors.append(f"{label}.style_authority.scope_level must be valid")
    authorization = value.get("authorization_source")
    authorization_claimed = authorization is not None and authorization != ""
    protected = set(lists["protected_surfaces"])
    allowed = set(lists["allowed_style_delta_surfaces"])
    guards = {"global-shell", "shared-components"}
    if mode == "greenfield":
        if authorization_claimed:
            errors.append(
                f"{label}.style_authority greenfield cannot claim overhaul authorization"
            )
    elif mode == "inherit-existing":
        if (
            scope_level != "feature-partial"
            or not lists["source_refs"]
            or not guards <= protected
            or allowed
            or authorization_claimed
        ):
            errors.append(
                f"{label}.style_authority inherit-existing must preserve live UI, global-shell, and shared-components without a style delta"
            )
    elif mode == "page-overhaul-authorized":
        if (
            scope_level != "page"
            or not lists["source_refs"]
            or not guards <= protected
            or not allowed
            or bool(allowed & guards)
            or not isinstance(authorization, str)
            or not authorization.strip()
        ):
            errors.append(
                f"{label}.style_authority page overhaul requires an exact page delta and explicit authorization while protecting shared UI"
            )
    return errors


def _validate_ui_contract_shape(contract: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    obsolete_fields = {"ui_contract_version", "contract_version"} & set(contract)
    if obsolete_fields:
        errors.append(
            f"{label} contains obsolete UI fields: {', '.join(sorted(obsolete_fields))}"
        )
    if str(contract.get("ui_work_type") or "").strip() not in {
        "existing-pattern",
        "feature-extension",
        "reference-implementation",
    }:
        errors.append(f"{label}.ui_work_type must be valid")
    if str(contract.get("surface_type") or "").strip() not in UI_CONTRACT_SURFACE_TYPES:
        errors.append(f"{label}.surface_type must be a supported UI surface type")
    platforms = contract.get("platforms")
    if (
        not isinstance(platforms, list)
        or not platforms
        or any(str(item).strip() not in UI_CONTRACT_PLATFORMS for item in platforms)
    ):
        errors.append(f"{label}.platforms must contain supported UI platforms")
    errors.extend(_validate_ui_style_authority(contract.get("style_authority"), label))
    for field in UI_CONTRACT_SCALAR_FIELDS:
        if not str(contract.get(field) or "").strip():
            errors.append(f"{label}.{field} must be non-empty")
    for field in UI_CONTRACT_LIST_FIELDS:
        if not isinstance(contract.get(field), list):
            errors.append(f"{label}.{field} must be a list")
    for field in UI_CONTRACT_OBJECT_FIELDS:
        if not isinstance(contract.get(field), dict):
            errors.append(f"{label}.{field} must be an object")
    binding_values = tuple(
        str(contract.get(field) or "").strip()
        for field in UI_DESIGN_CHANGE_BINDING_FIELDS
    )
    if any(binding_values) and not all(binding_values):
        errors.append(
            f"{label} design change ID, ref, SHA-256, and machine contract ref must be present together"
        )
    if all(binding_values):
        change_id, design_ref, design_sha256, contract_ref = binding_values
        expected_workspace = f".specify/design/changes/{change_id}"
        expected_design_ref = f"{expected_workspace}/design-change.md"
        expected_contract_ref = f"{expected_workspace}/design-contract.json"
        if not UI_DESIGN_CHANGE_ID_RE.fullmatch(change_id):
            errors.append(f"{label}.design_change_id must be a canonical UD-#### ID")
        if design_ref != expected_design_ref:
            errors.append(f"{label}.design_change_ref must match its UD-* workspace")
        if contract_ref != expected_contract_ref:
            errors.append(f"{label}.design_contract_ref must match its UD-* workspace")
        if not UI_SHA256_RE.fullmatch(design_sha256):
            errors.append(f"{label}.design_change_sha256 must be a SHA-256 digest")
        source_values: list[Any] | None = None
        for source_field in ("design_sources", "source_refs", "design_source_refs"):
            candidate = contract.get(source_field)
            if isinstance(candidate, list):
                source_values = candidate
                break
        if source_values is not None:
            normalized_sources = {str(item).strip() for item in source_values}
            for required_ref in (expected_design_ref, expected_contract_ref):
                if required_ref not in normalized_sources:
                    errors.append(f"{label} design sources must include {required_ref}")
    approved_ref = str(contract.get("approved_visual_ref") or "").strip()
    for field in UI_APPROVAL_DIGEST_FIELDS:
        digest = str(contract.get(field) or "").strip()
        if digest and not UI_SHA256_RE.fullmatch(digest):
            errors.append(f"{label}.{field} must be a SHA-256 digest")
    if UI_APPROVED_PREVIEW_REF_RE.search(approved_ref) and any(
        not UI_SHA256_RE.fullmatch(str(contract.get(field) or "").strip())
        for field in UI_APPROVAL_DIGEST_FIELDS
    ):
        errors.append(
            f"{label} approved visual round requires preview, manifest, and handoff SHA-256 digests"
        )
    if UI_APPROVED_PREVIEW_REF_RE.search(approved_ref):
        if (
            not str(contract.get("approved_handoff_ref") or "")
            .strip()
            .lower()
            .endswith(".handoff.json")
        ):
            errors.append(
                f"{label}.approved_handoff_ref must identify the immutable design handoff"
            )
        handoff_contract_ids = contract.get("handoff_contract_ids")
        if (
            not isinstance(handoff_contract_ids, list)
            or not handoff_contract_ids
            or any(
                not isinstance(item, str)
                or not UI_DESIGN_HANDOFF_ID_RE.fullmatch(item.strip())
                for item in handoff_contract_ids
            )
        ):
            errors.append(
                f"{label}.handoff_contract_ids must contain approved DH-* IDs"
            )
    design_decision_ids = contract.get("design_decision_ids")
    if (
        not isinstance(design_decision_ids, list)
        or not design_decision_ids
        or any(
            not isinstance(item, str)
            or not UI_DESIGN_DECISION_ID_RE.fullmatch(item.strip())
            for item in design_decision_ids
        )
    ):
        errors.append(f"{label}.design_decision_ids must contain canonical DS-* IDs")
    handoff_contract_ids = contract.get("handoff_contract_ids")
    if isinstance(handoff_contract_ids, list) and any(
        not isinstance(item, str) or not UI_DESIGN_HANDOFF_ID_RE.fullmatch(item.strip())
        for item in handoff_contract_ids
    ):
        errors.append(f"{label}.handoff_contract_ids must contain canonical DH-* IDs")
    handoff_id_set = {
        str(item).strip()
        for item in handoff_contract_ids or []
        if isinstance(item, str) and item.strip()
    }
    reference_intents = contract.get("reference_intents")
    if isinstance(reference_intents, list):
        for item in reference_intents:
            if (
                not isinstance(item, dict)
                or not str(item.get("ref") or "").strip()
                or str(item.get("intent") or "").strip()
                not in UI_CONTRACT_REFERENCE_INTENTS
            ):
                errors.append(
                    f"{label}.reference_intents entries require ref and valid intent"
                )
                break
    real_content_plan = contract.get("real_content_plan")
    if not isinstance(real_content_plan, list) or not real_content_plan:
        errors.append(f"{label}.real_content_plan must be non-empty")
    elif any(
        not isinstance(item, dict) or not str(item.get("source_ref") or "").strip()
        for item in real_content_plan
    ):
        errors.append(f"{label}.real_content_plan entries require source_ref")
    image_plan = contract.get("image_plan")
    if isinstance(image_plan, list) and any(
        not isinstance(item, dict)
        or not str(item.get("ref") or "").strip()
        or not str(item.get("role") or "").strip()
        for item in image_plan
    ):
        errors.append(f"{label}.image_plan entries require ref and role")
    continuity_result = validate_ui_source_continuity(
        contract.get("source_continuity"),
        require_ready=True,
    )
    errors.extend(
        f"{label}.source_continuity{error.path.removeprefix('$')}: {error.message}"
        for error in continuity_result.errors
    )
    color_modes = contract.get("color_modes")
    if not isinstance(color_modes, list) or not any(
        isinstance(item, str) and item.strip() for item in color_modes
    ):
        errors.append(f"{label}.color_modes must be non-empty")
    component_contracts = contract.get("component_contracts")
    decision_id_set = {
        str(item).strip()
        for item in design_decision_ids or []
        if isinstance(item, str) and item.strip()
    }
    component_ids = {
        str(item.get("id") or "").strip()
        for item in component_contracts or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    surface_catalog = contract.get("surface_catalog")
    if not isinstance(surface_catalog, list) or not surface_catalog:
        errors.append(f"{label}.surface_catalog must be non-empty")
    elif any(
        not _ui_contract_valid_surface_row(
            item, decision_id_set, handoff_id_set, component_ids
        )
        for item in surface_catalog
    ):
        errors.append(
            f"{label}.surface_catalog entries require stable identity, an official entrypoint binding, profile, source/specimen/component coverage, and known references"
        )
    surface_ids = {
        str(item.get("id") or "").strip()
        for item in surface_catalog or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    motion_value = contract.get("motion_contract")
    motion_transitions = (
        motion_value.get("transitions") or []
        if isinstance(motion_value, dict)
        else []
    )
    scenario_rows_by_field = {
        field: {
            str(item.get("id") or "").strip(): item
            for item in collection
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        for field, collection in {
            "interaction_ids": contract.get("interaction_matrix") or [],
            "editing_ids": contract.get("editing_matrix") or [],
            "data_state_ids": contract.get("data_state_matrix") or [],
            "accessibility_ids": contract.get("accessibility_matrix") or [],
            "navigation_ids": contract.get("navigation_matrix") or [],
            "content_ids": contract.get("content_matrix") or [],
            "responsive_ids": contract.get("responsive_matrix") or [],
            "motion_transition_ids": motion_transitions,
        }.items()
        if isinstance(collection, list)
    }
    scenario_matrix = contract.get("scenario_matrix")
    if not isinstance(scenario_matrix, list) or not scenario_matrix:
        errors.append(f"{label}.scenario_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_scenario_row(
            item,
            decision_id_set,
            handoff_id_set,
            surface_ids,
            scenario_rows_by_field,
        )
        for item in scenario_matrix
    ):
        errors.append(
            f"{label}.scenario_matrix entries must bind a stable surface to known interaction/editing/data/accessibility/navigation/content/responsive/motion rows, an executable interaction_script, and exact decisions"
        )
    if not isinstance(component_contracts, list) or not component_contracts:
        errors.append(f"{label}.component_contracts must be non-empty")
    elif any(
        not isinstance(item, dict)
        or not _ui_contract_valid_row_refs(
            item, decision_id_set, handoff_id_set
        )
        or not str(item.get("component") or "").strip()
        or not _ui_contract_has_nonblank_string_list(item.get("anatomy"))
        or not _ui_contract_has_nonblank_string_list(item.get("required_states"))
        or not _ui_contract_has_nonblank_string_list(item.get("interaction_modes"))
        or not isinstance(item.get("data_scenarios"), list)
        or not item.get("data_scenarios")
        or any(
            not _ui_contract_valid_data_scenario(scenario)
            for scenario in item.get("data_scenarios") or []
        )
        or not _ui_contract_has_nonblank_string_list(item.get("variants"))
        or not _ui_contract_has_nonblank_string_list(item.get("content_constraints"))
        or not _ui_contract_has_nonblank_string_list(item.get("semantic_token_refs"))
        or item.get("governance") not in {"reuse", "extend", "new"}
        or not str(item.get("iconography") or "").strip()
        or (
            item.get("adoption") is not None
            and not _ui_contract_valid_component_adoption(item.get("adoption"))
        )
        for item in component_contracts
    ):
        errors.append(
            f"{label}.component_contracts entries require immutable identity, anatomy, states, "
            "interaction/data variants, content/token governance, iconography, and known references"
        )
    interaction_matrix = contract.get("interaction_matrix")
    if not isinstance(interaction_matrix, list) or not interaction_matrix:
        errors.append(f"{label}.interaction_matrix must be non-empty")
    elif any(
        not isinstance(item, dict)
        or set(item)
        != {
            "id",
            "surface",
            "input",
            "trigger",
            "event_sequence",
            "immediate_feedback",
            "focus_behavior",
            "repeat_behavior",
            "cancellation_behavior",
            "pending_behavior",
            "decision_ids",
        }
        or not _ui_contract_valid_row_refs(item, decision_id_set, handoff_id_set)
        or any(
            not str(item.get(field) or "").strip()
            for field in (
                "surface",
                "input",
                "trigger",
                "event_sequence",
                "immediate_feedback",
                "focus_behavior",
                "repeat_behavior",
                "cancellation_behavior",
                "pending_behavior",
            )
        )
        for item in interaction_matrix
    ):
        errors.append(
            f"{label}.interaction_matrix entries require the complete event, feedback, focus, repeat, cancellation, pending, and known-reference lifecycle"
        )
    editing_matrix = contract.get("editing_matrix")
    if not isinstance(editing_matrix, list) or not editing_matrix:
        errors.append(f"{label}.editing_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_editing_row(
            item, decision_id_set, handoff_id_set
        )
        for item in editing_matrix
    ):
        errors.append(
            f"{label}.editing_matrix entries require the complete input, composition, validation, persistence, history, conflict, state, submission, and known-reference contract"
        )
    data_state_matrix = contract.get("data_state_matrix")
    if not isinstance(data_state_matrix, list) or not data_state_matrix:
        errors.append(f"{label}.data_state_matrix must be non-empty")
    elif any(
        not isinstance(item, dict)
        or not _ui_contract_valid_row_refs(item, decision_id_set, handoff_id_set)
        or not str(item.get("surface") or "").strip()
        or not str(item.get("state") or "").strip()
        or not str(item.get("data_condition") or "").strip()
        or not str(item.get("expectation") or "").strip()
        for item in data_state_matrix
    ):
        errors.append(
            f"{label}.data_state_matrix entries require id, surface, state, data_condition, expectation, and known references"
        )
    accessibility_matrix = contract.get("accessibility_matrix")
    if not isinstance(accessibility_matrix, list) or not accessibility_matrix:
        errors.append(f"{label}.accessibility_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_accessibility_row(
            item, decision_id_set, handoff_id_set
        )
        for item in accessibility_matrix
    ):
        errors.append(
            f"{label}.accessibility_matrix entries require semantic, focus, keyboard, announcement, target, contrast, zoom, alternative, and known-reference fields"
        )
    navigation_matrix = contract.get("navigation_matrix")
    if not isinstance(navigation_matrix, list) or not navigation_matrix:
        errors.append(f"{label}.navigation_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_navigation_row(item, decision_id_set, handoff_id_set)
        for item in navigation_matrix
    ):
        errors.append(
            f"{label}.navigation_matrix entries require entry/destination, trigger, back/deep-link/interruption behavior, and known references"
        )
    content_matrix = contract.get("content_matrix")
    if not isinstance(content_matrix, list) or not content_matrix:
        errors.append(f"{label}.content_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_content_row(item, decision_id_set, handoff_id_set)
        for item in content_matrix
    ):
        errors.append(
            f"{label}.content_matrix entries require state-specific copy, action, trust, localization, limits, and known references"
        )
    responsive_matrix = contract.get("responsive_matrix")
    if not isinstance(responsive_matrix, list) or not responsive_matrix:
        errors.append(f"{label}.responsive_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_responsive_row(
            item, decision_id_set, handoff_id_set
        )
        for item in responsive_matrix
    ):
        errors.append(
            f"{label}.responsive_matrix entries require state, stretch/overflow behavior, decision_ids, and viewport or immutable target plus adaptation"
        )
    motion_contract = contract.get("motion_contract")
    if not _ui_contract_valid_motion(
        motion_contract, decision_id_set, handoff_id_set
    ):
        errors.append(
            f"{label}.motion_contract requires transitions, reduced motion, ordered feedback timing, and known references"
        )
    if not _ui_contract_valid_usability(contract.get("usability_validation")):
        errors.append(
            f"{label}.usability_validation requires risk, methods, critical tasks, success criteria, and human-review decision"
        )
    visual_matrix = contract.get("visual_acceptance_matrix")
    if not isinstance(visual_matrix, list) or not visual_matrix:
        errors.append(f"{label}.visual_acceptance_matrix must be non-empty")
    elif any(
        not _ui_contract_valid_visual_row(item, decision_id_set, handoff_id_set)
        for item in visual_matrix
    ):
        errors.append(
            f"{label}.visual_acceptance_matrix entries require viewport, state, and evidence"
        )
    accepted_deviations = contract.get("accepted_deviations")
    if isinstance(accepted_deviations, list) and any(
        not isinstance(item, dict)
        or not str(item.get("decision_id") or "").strip()
        or not str(item.get("reason") or "").strip()
        for item in accepted_deviations
    ):
        errors.append(
            f"{label}.accepted_deviations entries require decision_id and reason"
        )
    required_evidence = contract.get("required_evidence")
    evidence = (
        {
            str(item).strip()
            for item in required_evidence
            if isinstance(item, str) and item.strip()
        }
        if isinstance(required_evidence, list)
        else set()
    )
    if evidence != UI_CONTRACT_EVIDENCE:
        errors.append(
            f"{label}.required_evidence must be exactly: "
            + ", ".join(sorted(UI_CONTRACT_EVIDENCE))
        )
    fidelity_field = (
        "fidelity_mode" if "ui_applicable" in contract else "fidelity_level"
    )
    fidelity = str(contract.get(fidelity_field) or "none").strip().lower()
    if fidelity not in UI_ACTIVE_FIDELITY_MODES:
        errors.append(
            f"{label}.{fidelity_field} must be approximate, high, or inspiration for active UI work"
        )
    continuity = contract.get("source_continuity")
    if isinstance(continuity, dict) and continuity.get("applicability") == "required":
        coverage = continuity.get("coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        actual_coverage = {
            "surface_ids": surface_ids,
            "interaction_ids": {
                str(item.get("id") or "").strip()
                for item in interaction_matrix or []
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            },
            "component_ids": component_ids,
        }
        for field, actual_ids in actual_coverage.items():
            declared_ids = {
                str(item).strip()
                for item in coverage.get(field) or []
                if isinstance(item, str) and item.strip()
            }
            if declared_ids != actual_ids:
                errors.append(
                    f"{label}.source_continuity.coverage.{field} must exactly cover the selected UI contract IDs"
                )
    return errors


def _validate_ui_handoff_binding(
    feature_dir: Path,
    contract: dict[str, Any],
    label: str,
) -> list[str]:
    """Bind an active UI contract to the immutable approved design handoff."""

    approved_ref = str(contract.get("approved_visual_ref") or "").strip()
    if not UI_APPROVED_PREVIEW_REF_RE.search(approved_ref):
        return []
    errors: list[str] = []
    handoff_ref = str(contract.get("approved_handoff_ref") or "").strip()
    if not handoff_ref:
        return [f"{label}.approved_handoff_ref is required"]
    raw_handoff_path = Path(handoff_ref)
    if raw_handoff_path.is_absolute():
        return [f"{label}.approved_handoff_ref must be project-relative"]
    project_root = feature_dir.parents[2]
    handoff_path = (project_root / raw_handoff_path).resolve(strict=False)
    try:
        handoff_path.relative_to(project_root.resolve())
    except ValueError:
        return [f"{label}.approved_handoff_ref must stay inside the project"]
    if not handoff_path.is_file():
        return [f"{label}.approved_handoff_ref does not exist: {handoff_ref}"]
    try:
        handoff_bytes = handoff_path.read_bytes()
        handoff = json.loads(handoff_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{label}.approved_handoff_ref is unreadable: {exc}"]
    actual_digest = hashlib.sha256(handoff_bytes).hexdigest()
    if actual_digest != str(contract.get("approved_handoff_sha256") or "").strip():
        errors.append(
            f"{label}.approved_handoff_sha256 must bind the immutable handoff bytes"
        )
    if (
        not isinstance(handoff, dict)
        or handoff.get("schema") != "spec-kit-design-handoff-v1"
    ):
        errors.append(
            f"{label}.approved_handoff_ref must contain spec-kit-design-handoff-v1"
        )
        return errors

    approval = handoff.get("approval")
    approval = approval if isinstance(approval, dict) else {}
    preview_ref, _, direction_id = approved_ref.partition("#")
    expected_local_preview_ref = f"{Path(preview_ref).name}#{direction_id}"
    expected_pairs = (
        ("preview_ref", expected_local_preview_ref),
        ("direction_id", direction_id),
        ("preview_sha256", str(contract.get("approved_preview_sha256") or "").strip()),
        (
            "manifest_sha256",
            str(contract.get("approved_manifest_sha256") or "").strip(),
        ),
    )
    for field, expected in expected_pairs:
        if str(approval.get(field) or "").strip() != expected:
            errors.append(
                f"{label} immutable handoff approval.{field} must preserve the UI contract"
            )

    approved_decisions = {
        str(item).strip()
        for item in approval.get("decision_ids") or []
        if isinstance(item, str) and item.strip()
    }
    selected_decisions = _normalized_ui_string_values("design_decision_ids", contract)
    if not selected_decisions or not selected_decisions <= approved_decisions:
        errors.append(
            f"{label}.design_decision_ids must be a non-empty immutable handoff subset"
        )

    reproduction = handoff.get("reproduction")
    reproduction = reproduction if isinstance(reproduction, dict) else {}
    approved_contract_ids = {
        str(item).strip()
        for item in reproduction.get("contract_ids") or []
        if isinstance(item, str) and item.strip()
    }
    selected_contract_ids = _normalized_ui_string_values(
        "handoff_contract_ids", contract
    )
    if not selected_contract_ids or not selected_contract_ids <= approved_contract_ids:
        errors.append(
            f"{label}.handoff_contract_ids must be a non-empty immutable handoff subset"
        )

    for field in (
        "surface_catalog",
        "scenario_matrix",
        "interaction_matrix",
        "data_state_matrix",
        "accessibility_matrix",
        "navigation_matrix",
        "content_matrix",
        "component_contracts",
        "responsive_matrix",
        "visual_acceptance_matrix",
        "accepted_deviations",
    ):
        handoff_rows = reproduction.get(field)
        handoff_rows = handoff_rows if isinstance(handoff_rows, list) else []
        rows_by_id = {
            str(row.get("id") or "").strip(): row
            for row in handoff_rows
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        expected_ids = selected_contract_ids & set(rows_by_id)
        contract_rows = contract.get(field)
        contract_rows = contract_rows if isinstance(contract_rows, list) else []
        actual_ids: set[str] = set()
        for index, row in enumerate(contract_rows):
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("id") or "").strip()
            if not row_id:
                errors.append(
                    f"{label}.{field}[{index}] must preserve its immutable DH-* id"
                )
                continue
            actual_ids.add(row_id)
            if row_id not in expected_ids:
                errors.append(
                    f"{label}.{field}[{index}] is not selected by handoff_contract_ids"
                )
                continue
            if row != rows_by_id[row_id]:
                errors.append(
                    f"{label}.{field}[{index}] must exactly preserve immutable handoff row {row_id}"
                )
        if actual_ids != expected_ids:
            errors.append(
                f"{label}.{field} must exactly materialize its selected immutable handoff rows"
            )

    if contract.get("comparison_tolerance") != reproduction.get("comparison_tolerance"):
        errors.append(
            f"{label}.comparison_tolerance must exactly preserve the immutable handoff"
        )
    for field in ("motion_contract", "usability_validation"):
        if contract.get(field) != reproduction.get(field):
            errors.append(
                f"{label}.{field} must exactly preserve the immutable handoff"
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


def _spec_design_gate_requires_design(feature_dir: Path) -> bool:
    path = feature_dir / "spec-contract.json"
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return _spec_gate_decision(payload, "design_gate") == "required"


def _feature_project_root(feature_dir: Path) -> Path:
    if feature_dir.parent.name == "specs":
        return feature_dir.parent.parent.resolve()
    if (
        feature_dir.parent.name == "features"
        and feature_dir.parent.parent.name == ".specify"
    ):
        return feature_dir.parent.parent.parent.resolve()
    return feature_dir.parent.resolve()


def _plan_ui_design_contract(feature_dir: Path) -> tuple[dict[str, Any] | None, str]:
    for contract_path, label in _consequence_contract_paths(feature_dir):
        if not contract_path.is_file():
            continue
        try:
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, label
        contract = (
            payload.get("ui_design_contract") if isinstance(payload, dict) else None
        )
        return (contract if isinstance(contract, dict) else None), label
    return None, "plan-contract.json"


def _validate_plan_ui_contract(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    spec_contract = _spec_ui_design_contract(feature_dir)
    plan_contract, label = _plan_ui_design_contract(feature_dir)
    spec_applies = (
        isinstance(spec_contract, dict) and spec_contract.get("ui_applicable") is True
    )
    plan_applies = (
        isinstance(plan_contract, dict) and plan_contract.get("ui_applicable") is True
    )

    if spec_applies and not plan_applies:
        errors.append(
            f"{label} must set ui_design_contract.ui_applicable true because spec-contract.json is UI-bearing"
        )
        return errors
    if not plan_applies:
        return errors

    assert isinstance(plan_contract, dict)
    errors.extend(
        _validate_ui_contract_shape(plan_contract, f"{label} ui_design_contract")
    )
    errors.extend(
        _validate_ui_handoff_binding(
            feature_dir,
            plan_contract,
            f"{label} ui_design_contract",
        )
    )
    current_overlay, adoption_errors = _validate_plan_design_adoption_binding(
        feature_dir, plan_contract, label
    )
    errors.extend(adoption_errors)
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

    design_gate_required = _spec_design_gate_requires_design(feature_dir)
    post_specify_design_overlay = current_overlay is not None and design_gate_required
    if current_overlay is not None and not design_gate_required:
        errors.append(
            f"{label} formal-post-specify design_adoption_binding requires source spec design_gate.required"
        )
    if design_gate_required and not post_specify_design_overlay:
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding must carry the verified formal-post-specify receipt"
        )
    if (
        spec_applies
        and isinstance(spec_contract, dict)
        and post_specify_design_overlay
        and _spec_design_gate_requires_design(feature_dir)
    ):
        errors.extend(
            _spec_owned_pending_ui_fields_match(spec_contract, plan_contract, label)
        )
    if spec_applies and isinstance(spec_contract, dict) and not post_specify_design_overlay:
        spec_brief_ref = str(spec_contract.get("ui_brief_ref") or "").strip()
        if spec_brief_ref and ui_brief_ref and spec_brief_ref != ui_brief_ref:
            spec_path = resolve_feature_artifact_ref(feature_dir, spec_brief_ref)
            plan_path = resolve_feature_artifact_ref(feature_dir, ui_brief_ref)
            if spec_path is None or plan_path is None or spec_path != plan_path:
                errors.append(
                    f"{label} ui_design_contract.ui_brief_ref must preserve the specification UI brief"
                )
        if _spec_design_gate_requires_design(feature_dir):
            errors.extend(
                _spec_owned_pending_ui_fields_match(spec_contract, plan_contract, label)
            )
        else:
            for field in (
                "ui_work_type",
                "surface_type",
                "fidelity_mode",
                "source_continuity",
                *UI_DESIGN_CHANGE_BINDING_FIELDS,
                *UI_CONTRACT_SCALAR_FIELDS,
                *UI_CONTRACT_LIST_FIELDS,
                *UI_CONTRACT_OBJECT_FIELDS,
                *UI_APPROVAL_DIGEST_FIELDS,
                *UI_APPROVAL_REFERENCE_FIELDS,
                *UI_SPEC_PLAN_CONTINUITY_LIST_FIELDS,
            ):
                if _canonical_ui_continuity_value(
                    field, plan_contract.get(field)
                ) != _canonical_ui_continuity_value(field, spec_contract.get(field)):
                    errors.append(
                        f"{label} ui_design_contract.{field} must preserve the specification UI contract"
                    )
    return errors


def _ui_source_continuity_coverage(
    continuity: object,
) -> dict[str, set[str]]:
    if not isinstance(continuity, dict):
        return {field: set() for field in ("surface_ids", "interaction_ids", "component_ids")}
    coverage = continuity.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    return {
        field: {
            str(item).strip()
            for item in coverage.get(field) or []
            if isinstance(item, str) and item.strip()
        }
        for field in ("surface_ids", "interaction_ids", "component_ids")
    }


def _validate_task_source_continuity_subset(
    plan_continuity: object,
    task_continuity: object,
    label: str,
) -> tuple[list[str], dict[str, set[str]]]:
    errors: list[str] = []
    empty = _ui_source_continuity_coverage(None)
    if not isinstance(plan_continuity, dict) or not isinstance(task_continuity, dict):
        return [f"{label} source_continuity must preserve the plan contract"], empty
    if plan_continuity.get("applicability") != "required":
        if task_continuity != plan_continuity:
            errors.append(f"{label} source_continuity must preserve plan source_continuity")
        return errors, _ui_source_continuity_coverage(task_continuity)

    for field in ("schema", "applicability", "mode", "reason"):
        if task_continuity.get(field) != plan_continuity.get(field):
            errors.append(f"{label} source_continuity.{field} must preserve the plan")
    plan_authority = {
        str(item).strip()
        for item in plan_continuity.get("authority_refs") or []
        if isinstance(item, str) and item.strip()
    }
    task_authority = {
        str(item).strip()
        for item in task_continuity.get("authority_refs") or []
        if isinstance(item, str) and item.strip()
    }
    if not task_authority or not task_authority <= plan_authority:
        errors.append(f"{label} source_continuity.authority_refs must be a non-empty plan subset")

    plan_coverage = _ui_source_continuity_coverage(plan_continuity)
    task_coverage = _ui_source_continuity_coverage(task_continuity)
    for field, task_ids in task_coverage.items():
        if not task_ids or not task_ids <= plan_coverage[field]:
            errors.append(f"{label} source_continuity.coverage.{field} must be a non-empty plan subset")

    for field in ("surface_bindings", "action_bindings", "asset_bindings"):
        plan_rows = {
            str(row.get("id") or "").strip(): row
            for row in plan_continuity.get(field) or []
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        task_rows = task_continuity.get(field)
        task_rows = task_rows if isinstance(task_rows, list) else []
        for index, row in enumerate(task_rows):
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("id") or "").strip()
            if row_id not in plan_rows or row != plan_rows[row_id]:
                errors.append(
                    f"{label} source_continuity.{field}[{index}] must exactly preserve a plan binding row"
                )
    if task_continuity.get("unresolved_gaps") != []:
        errors.append(f"{label} source_continuity.unresolved_gaps must remain empty")
    return errors, task_coverage


def _validate_tasks_ui_contract(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    plan_contract, label = _plan_ui_design_contract(feature_dir)
    plan_applies = (
        isinstance(plan_contract, dict) and plan_contract.get("ui_applicable") is True
    )
    plan_declares_not_ui = (
        isinstance(plan_contract, dict) and plan_contract.get("ui_applicable") is False
    )
    markdown_ids = markdown_ui_task_ids(feature_dir)
    indexed_ids = set(task_index_ui_contracts(feature_dir))
    task_index_payload, _ = _read_json_artifact(
        feature_dir / "task-index.json", "task-index.json"
    )
    raw_tasks = (
        task_index_payload.get("tasks")
        if isinstance(task_index_payload, dict)
        else None
    )
    official_entrypoint_ids = {
        str(item.get("id") or "").strip()
        for item in (
            task_index_payload.get("official_entrypoints", [])
            if isinstance(task_index_payload, dict)
            else []
        )
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if isinstance(raw_tasks, list):
        for task_entry in raw_tasks:
            if (
                not isinstance(task_entry, dict)
                or "ui_fidelity_requirements" not in task_entry
            ):
                continue
            task_id = str(
                task_entry.get("id") or task_entry.get("task_id") or "<unknown>"
            )
            errors.append(
                f"task-index.json task {task_id} contains obsolete ui_fidelity_requirements"
            )
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
    if plan_applies and isinstance(plan_contract, dict):
        covered_required_states: set[str] = set()
        covered_design_decisions: set[str] = set()
        covered_handoff_contracts: set[str] = set()
        covered_color_modes: set[str] = set()
        covered_surface_catalog: set[Any] = set()
        covered_scenario_matrix: set[Any] = set()
        covered_interaction_matrix: set[Any] = set()
        covered_editing_matrix: set[Any] = set()
        covered_data_state_matrix: set[Any] = set()
        covered_accessibility_matrix: set[Any] = set()
        covered_navigation_matrix: set[Any] = set()
        covered_content_matrix: set[Any] = set()
        covered_component_contracts: set[Any] = set()
        covered_responsive_matrix: set[Any] = set()
        covered_visual_acceptance_matrix: set[Any] = set()
        covered_source_continuity = {
            field: set()
            for field in ("surface_ids", "interaction_ids", "component_ids")
        }
        for task_id, task_entry in task_index_ui_contracts(feature_dir).items():
            task_contract = task_entry.get("ui_contract")
            if not isinstance(task_contract, dict):
                continue
            missing_fields = UI_CONTRACT_FIELDS - set(task_contract)
            unsupported_fields = set(task_contract) - UI_CONTRACT_FIELDS
            if missing_fields:
                errors.append(
                    f"task-index.json UI task {task_id} ui_contract is missing current fields: "
                    + ", ".join(sorted(missing_fields))
                )
            if unsupported_fields:
                errors.append(
                    f"task-index.json UI task {task_id} ui_contract contains unsupported fields: "
                    + ", ".join(sorted(unsupported_fields))
                )
            errors.extend(
                _validate_ui_contract_shape(
                    task_contract,
                    f"task-index.json UI task {task_id} ui_contract",
                )
            )
            continuity_errors, task_source_coverage = (
                _validate_task_source_continuity_subset(
                    plan_contract.get("source_continuity"),
                    task_contract.get("source_continuity"),
                    f"task-index.json UI task {task_id}",
                )
            )
            errors.extend(continuity_errors)
            for field, values in task_source_coverage.items():
                covered_source_continuity[field].update(values)
            surface_entrypoint_ids = [
                str(surface.get("entrypoint_id") or "").strip()
                for surface in task_contract.get("surface_catalog") or []
                if isinstance(surface, dict)
                and str(surface.get("entrypoint_id") or "").strip()
            ]
            unknown_entrypoint_ids = sorted(
                set(surface_entrypoint_ids) - official_entrypoint_ids
            )
            if unknown_entrypoint_ids:
                errors.append(
                    f"task-index.json UI task {task_id} surface_catalog references unknown official entrypoint IDs: "
                    + ", ".join(unknown_entrypoint_ids)
                )
            usability = task_contract.get("usability_validation")
            smoothness_ids = (
                usability.get("smoothness_acceptance_ids")
                if isinstance(usability, dict)
                else None
            )
            if smoothness_ids and len(set(surface_entrypoint_ids)) != 1:
                errors.append(
                    f"task-index.json UI task {task_id} Smoothness Lab surfaces must bind exactly one official entrypoint"
                )
            for field in ("design_sources", "required_states"):
                value = task_contract.get(field)
                if not isinstance(value, list) or not any(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    errors.append(
                        f"task-index.json UI task {task_id} ui_contract.{field} must be non-empty"
                    )
            for field in (
                "ui_work_type",
                "surface_type",
                *UI_DESIGN_CHANGE_BINDING_FIELDS,
                *UI_CONTRACT_SCALAR_FIELDS,
                *UI_CONTRACT_OBJECT_FIELDS,
                *UI_APPROVAL_DIGEST_FIELDS,
                *UI_APPROVAL_REFERENCE_FIELDS,
            ):
                if task_contract.get(field) != plan_contract.get(field):
                    errors.append(
                        f"task-index.json UI task {task_id} must preserve plan {field}"
                    )
            task_platforms = set(task_contract.get("platforms") or [])
            plan_platforms = set(plan_contract.get("platforms") or [])
            if not task_platforms or not task_platforms <= plan_platforms:
                errors.append(
                    f"task-index.json UI task {task_id} platforms must be a non-empty plan subset"
                )
            plan_fidelity = str(plan_contract.get("fidelity_mode") or "none").strip()
            task_fidelity = str(task_contract.get("fidelity_level") or "none").strip()
            if task_fidelity != plan_fidelity:
                errors.append(
                    f"task-index.json UI task {task_id} fidelity_level must preserve plan fidelity_mode"
                )

            plan_states = _normalized_ui_string_values("required_states", plan_contract)
            task_states = _normalized_ui_string_values("required_states", task_contract)
            covered_required_states.update(task_states)
            if not task_states <= plan_states:
                errors.append(
                    f"task-index.json UI task {task_id} required_states must be a plan subset"
                )

            for field, covered in (
                ("design_decision_ids", covered_design_decisions),
                ("handoff_contract_ids", covered_handoff_contracts),
                ("color_modes", covered_color_modes),
            ):
                plan_values = _normalized_ui_string_values(field, plan_contract)
                task_values = _normalized_ui_string_values(field, task_contract)
                covered.update(task_values)
                if field == "handoff_contract_ids" and not plan_values:
                    if task_values:
                        errors.append(
                            f"task-index.json UI task {task_id} handoff_contract_ids must be empty when the plan has no immutable handoff"
                        )
                    continue
                if not task_values or not task_values <= plan_values:
                    errors.append(
                        f"task-index.json UI task {task_id} {field} must be a non-empty plan subset"
                    )

            for field, covered in (
                ("surface_catalog", covered_surface_catalog),
                ("scenario_matrix", covered_scenario_matrix),
                ("interaction_matrix", covered_interaction_matrix),
                ("editing_matrix", covered_editing_matrix),
                ("data_state_matrix", covered_data_state_matrix),
                ("accessibility_matrix", covered_accessibility_matrix),
                ("navigation_matrix", covered_navigation_matrix),
                ("content_matrix", covered_content_matrix),
                ("component_contracts", covered_component_contracts),
                ("responsive_matrix", covered_responsive_matrix),
                ("visual_acceptance_matrix", covered_visual_acceptance_matrix),
            ):
                raw_plan_values = plan_contract.get(field)
                raw_task_values = task_contract.get(field)
                plan_values = set(
                    _canonical_ui_continuity_value(field, raw_plan_values) or ()
                )
                task_values = set(
                    _canonical_ui_continuity_value(field, raw_task_values) or ()
                )
                covered.update(task_values)
                if not task_values or not task_values <= plan_values:
                    errors.append(
                        f"task-index.json UI task {task_id} {field} must be a non-empty plan subset"
                    )

            plan_preserve = _normalized_ui_string_values("must_preserve", plan_contract)
            task_preserve = _normalized_ui_string_values("must_preserve", task_contract)
            if not plan_preserve <= task_preserve:
                errors.append(
                    f"task-index.json UI task {task_id} must_preserve must include plan constraints"
                )

            plan_may_adapt = _normalized_ui_string_values("may_adapt", plan_contract)
            task_may_adapt = _normalized_ui_string_values("may_adapt", task_contract)
            if not task_may_adapt <= plan_may_adapt:
                errors.append(
                    f"task-index.json UI task {task_id} may_adapt must not exceed plan permissions"
                )

            plan_must_not = _normalized_ui_string_values("must_not", plan_contract)
            task_must_not = _normalized_ui_string_values("must_not", task_contract)
            if not plan_must_not <= task_must_not:
                errors.append(
                    f"task-index.json UI task {task_id} must_not must include plan prohibitions"
                )
            if _canonical_ui_continuity_value(
                "accepted_deviations", task_contract.get("accepted_deviations")
            ) != _canonical_ui_continuity_value(
                "accepted_deviations", plan_contract.get("accepted_deviations")
            ):
                errors.append(
                    f"task-index.json UI task {task_id} accepted_deviations must preserve plan approvals"
                )
        plan_required_states = {
            str(item).strip()
            for item in plan_contract.get("required_states") or []
            if isinstance(item, str) and item.strip()
        }
        missing_states = sorted(plan_required_states - covered_required_states)
        if missing_states:
            errors.append(
                "task-index.json UI tasks must cover plan required_states: "
                + ", ".join(missing_states)
            )
        for field, covered in (
            ("design_decision_ids", covered_design_decisions),
            ("handoff_contract_ids", covered_handoff_contracts),
            ("color_modes", covered_color_modes),
            ("surface_catalog", covered_surface_catalog),
            ("scenario_matrix", covered_scenario_matrix),
            ("interaction_matrix", covered_interaction_matrix),
            ("editing_matrix", covered_editing_matrix),
            ("data_state_matrix", covered_data_state_matrix),
            ("accessibility_matrix", covered_accessibility_matrix),
            ("navigation_matrix", covered_navigation_matrix),
            ("content_matrix", covered_content_matrix),
            ("component_contracts", covered_component_contracts),
            ("responsive_matrix", covered_responsive_matrix),
            ("visual_acceptance_matrix", covered_visual_acceptance_matrix),
        ):
            expected = _canonical_ui_continuity_value(field, plan_contract.get(field))
            expected_set = set(expected or ())
            missing = expected_set - covered
            if missing:
                errors.append(f"task-index.json UI tasks must cover plan {field}")
        plan_source_coverage = _ui_source_continuity_coverage(
            plan_contract.get("source_continuity")
        )
        for field, expected in plan_source_coverage.items():
            if expected - covered_source_continuity[field]:
                errors.append(
                    f"task-index.json UI tasks must cover plan source_continuity.coverage.{field}"
                )
    return errors


def _json_pointer_escape_token(value: object) -> str:
    """Escape one RFC 6901 JSON Pointer token."""

    return str(value).replace("~", "~0").replace("/", "~1")


def _validate_spec_acceptance_coverage(payload: dict[str, Any]) -> list[str]:
    """Require exact machine-readable closure from Spec requirements to acceptance."""

    errors: list[str] = []
    requirement_refs: list[str] = []

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        errors.append(
            "spec-contract.json scope must be an object for acceptance_coverage"
        )
    else:
        scope_in = scope.get("in")
        if not isinstance(scope_in, list):
            errors.append(
                "spec-contract.json scope.in must be an array for acceptance_coverage"
            )
        else:
            requirement_refs.extend(
                f"spec-contract.json#/scope/in/{index}"
                for index in range(len(scope_in))
            )

    capability_operations = payload.get("capability_operations")
    if isinstance(capability_operations, list):
        requirement_refs.extend(
            f"spec-contract.json#/capability_operations/{index}"
            for index in range(len(capability_operations))
        )
    elif isinstance(capability_operations, dict):
        requirement_refs.extend(
            "spec-contract.json#/capability_operations/"
            + _json_pointer_escape_token(key)
            for key in capability_operations
        )
    else:
        errors.append(
            "spec-contract.json capability_operations must be an array or object "
            "for acceptance_coverage"
        )

    acceptance_criteria = payload.get("acceptance_criteria")
    acceptance_refs = (
        [
            f"spec-contract.json#/acceptance_criteria/{index}"
            for index in range(len(acceptance_criteria))
        ]
        if isinstance(acceptance_criteria, list)
        else []
    )
    expected_requirement_refs = set(requirement_refs)
    expected_acceptance_refs = set(acceptance_refs)

    raw_coverage = payload.get("acceptance_coverage")
    if not isinstance(raw_coverage, list) or not raw_coverage:
        errors.append(
            "spec-contract.json acceptance_coverage must be a non-empty array"
        )
        return errors

    coverage_pairs: list[tuple[str, str]] = []
    for index, value in enumerate(raw_coverage):
        prefix = f"spec-contract.json acceptance_coverage[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{prefix} must be an object")
            continue
        requirement_ref = value.get("requirement_ref")
        acceptance_ref = value.get("acceptance_ref")
        if not isinstance(requirement_ref, str) or not requirement_ref.strip():
            errors.append(f"{prefix}.requirement_ref must be a non-empty string")
            continue
        if not isinstance(acceptance_ref, str) or not acceptance_ref.strip():
            errors.append(f"{prefix}.acceptance_ref must be a non-empty string")
            continue
        coverage_pairs.append((requirement_ref.strip(), acceptance_ref.strip()))

    duplicate_pairs = sorted(
        pair for pair in set(coverage_pairs) if coverage_pairs.count(pair) > 1
    )
    if duplicate_pairs:
        errors.append(
            "spec-contract.json acceptance_coverage must contain unique "
            "requirement_ref/acceptance_ref pairs: "
            + ", ".join(
                f"{requirement_ref} -> {acceptance_ref}"
                for requirement_ref, acceptance_ref in duplicate_pairs
            )
        )

    actual_requirement_refs = {pair[0] for pair in coverage_pairs}
    actual_acceptance_refs = {pair[1] for pair in coverage_pairs}
    unknown_requirement_refs = sorted(
        actual_requirement_refs - expected_requirement_refs
    )
    unknown_acceptance_refs = sorted(actual_acceptance_refs - expected_acceptance_refs)
    if unknown_requirement_refs:
        errors.append(
            "spec-contract.json acceptance_coverage contains unknown requirement_ref values: "
            + ", ".join(unknown_requirement_refs)
        )
    if unknown_acceptance_refs:
        errors.append(
            "spec-contract.json acceptance_coverage contains unknown acceptance_ref values: "
            + ", ".join(unknown_acceptance_refs)
        )

    missing_requirement_refs = sorted(
        expected_requirement_refs - actual_requirement_refs
    )
    missing_acceptance_refs = sorted(expected_acceptance_refs - actual_acceptance_refs)
    if missing_requirement_refs:
        errors.append(
            "spec-contract.json requirements are missing acceptance_coverage: "
            + ", ".join(missing_requirement_refs)
        )
    if missing_acceptance_refs:
        errors.append(
            "spec-contract.json acceptance criteria are missing acceptance_coverage: "
            + ", ".join(missing_acceptance_refs)
        )

    multiply_mapped_acceptance_refs = sorted(
        acceptance_ref
        for acceptance_ref in expected_acceptance_refs
        if sum(pair[1] == acceptance_ref for pair in coverage_pairs) > 1
    )
    if multiply_mapped_acceptance_refs:
        errors.append(
            "spec-contract.json each acceptance criterion must map to exactly one "
            "requirement_ref; multiply mapped acceptance refs: "
            + ", ".join(multiply_mapped_acceptance_refs)
        )
    return errors


def _validate_plan_human_acceptance_contract(feature_dir: Path) -> list[str]:
    """Require Plan to preserve the complete Spec acceptance denominator."""

    spec_path = feature_dir / "spec-contract.json"
    if not spec_path.is_file():
        return ["spec-contract.json is required to define the acceptance denominator"]
    spec_payload, spec_errors = _read_json_artifact(spec_path, "spec-contract.json")
    if spec_errors:
        return spec_errors
    if not isinstance(spec_payload, dict):
        return ["spec-contract.json must contain a top-level object"]
    raw_criteria = spec_payload.get("acceptance_criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        return ["spec-contract.json acceptance_criteria must be a non-empty array"]
    errors: list[str] = []
    for index, criterion in enumerate(raw_criteria):
        if not isinstance(criterion, str) or not criterion.strip():
            errors.append(
                f"spec-contract.json acceptance_criteria[{index}] must be a non-empty string"
            )
    errors.extend(_validate_spec_acceptance_coverage(spec_payload))

    plan_path: Path | None = None
    plan_label = "plan-contract.json"
    for candidate, label in _consequence_contract_paths(feature_dir):
        if candidate.is_file():
            plan_path = candidate
            plan_label = label
            break
    if plan_path is None:
        return [
            *errors,
            "plan-contract.json is required to preserve acceptance criteria",
        ]
    plan_payload, plan_errors = _read_json_artifact(plan_path, plan_label)
    if plan_errors:
        return plan_errors
    if not isinstance(plan_payload, dict):
        return [f"{plan_label} must contain a top-level object"]

    raw_refs = plan_payload.get("acceptance_refs")
    if not isinstance(raw_refs, list):
        return [f"{plan_label} acceptance_refs must be an array"]
    refs: list[str] = []
    for index, value in enumerate(raw_refs):
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"{plan_label} acceptance_refs[{index}] must be a non-empty string"
            )
            continue
        refs.append(value.strip())
    duplicate_refs = sorted(ref for ref in set(refs) if refs.count(ref) > 1)
    if duplicate_refs:
        errors.append(
            f"{plan_label} acceptance_refs must be unique: " + ", ".join(duplicate_refs)
        )
    expected_ref_list = [
        f"spec-contract.json#/acceptance_criteria/{index}"
        for index in range(len(raw_criteria))
    ]
    expected_refs = set(expected_ref_list)
    actual_refs = set(refs)
    missing_refs = sorted(expected_refs - actual_refs)
    unknown_refs = sorted(actual_refs - expected_refs)
    if missing_refs:
        errors.append(
            f"{plan_label} acceptance_refs are missing spec acceptance criteria: "
            + ", ".join(missing_refs)
        )
    if unknown_refs:
        errors.append(
            f"{plan_label} acceptance_refs contain unknown spec acceptance criteria: "
            + ", ".join(unknown_refs)
        )
    if not missing_refs and not unknown_refs and refs != expected_ref_list:
        errors.append(f"{plan_label} acceptance_refs must preserve specification order")
    return errors


def _validate_tasks_human_acceptance_contract(feature_dir: Path) -> list[str]:
    """Validate the task-owned, executable human acceptance universe."""

    errors: list[str] = _validate_plan_human_acceptance_contract(feature_dir)
    plan_acceptance_refs: list[str] = []
    plan_label = "plan-contract.json"
    for plan_path, plan_label in _consequence_contract_paths(feature_dir):
        if not plan_path.is_file():
            continue
        plan_payload, plan_read_errors = _read_json_artifact(plan_path, plan_label)
        if plan_read_errors:
            errors.extend(plan_read_errors)
            break
        if isinstance(plan_payload, dict):
            raw_plan_refs = plan_payload.get("acceptance_refs")
            if not isinstance(raw_plan_refs, list):
                errors.append(f"{plan_label} acceptance_refs must be an array")
            else:
                for index, value in enumerate(raw_plan_refs):
                    if not isinstance(value, str) or not value.strip():
                        errors.append(
                            f"{plan_label} acceptance_refs[{index}] must be a non-empty string"
                        )
                        continue
                    plan_acceptance_refs.append(value.strip())
        break

    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        if plan_acceptance_refs:
            errors.append(
                "task-index.json is required when Plan defines acceptance_refs so "
                "Tasks can freeze the Human Acceptance Universe"
            )
        return errors
    payload, read_errors = _read_json_artifact(task_index_path, "task-index.json")
    if read_errors:
        return [*errors, *read_errors]
    if not isinstance(payload, dict):
        return [*errors, "task-index.json must contain a top-level object"]
    if plan_acceptance_refs and payload.get("version") != 2:
        errors.append(
            "task-index.json version must equal 2 when Plan defines acceptance_refs"
        )
    if plan_acceptance_refs and payload.get("status") != "ready":
        errors.append(
            "task-index.json status must be ready when Plan defines acceptance_refs"
        )

    raw_acceptance_refs = payload.get("acceptance_refs", [])
    if not isinstance(raw_acceptance_refs, list):
        return [*errors, "task-index.json acceptance_refs must be an array"]
    acceptance_refs: list[str] = []
    for index, value in enumerate(raw_acceptance_refs):
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"task-index.json acceptance_refs[{index}] must be a non-empty string"
            )
            continue
        acceptance_refs.append(value.strip())
    duplicate_acceptance_refs = sorted(
        ref for ref in set(acceptance_refs) if acceptance_refs.count(ref) > 1
    )
    if duplicate_acceptance_refs:
        errors.append(
            "task-index.json acceptance_refs must be unique: "
            + ", ".join(duplicate_acceptance_refs)
        )
    pointer_to_value: dict[str, str] = {}
    if plan_acceptance_refs:
        # Canonical form is an exact ordered copy of plan-contract.acceptance_refs
        # values (usually spec-contract.json#/acceptance_criteria/i). The older
        # agent pointer form plan-contract.json#/acceptance_refs/N is accepted
        # and expanded for validation so hooks and tasks CLI stay aligned.
        pointer_to_value = {
            f"{plan_label}#/acceptance_refs/{index}": value
            for index, value in enumerate(plan_acceptance_refs)
        }
        pointer_to_value.update(
            {
                f"plan-contract.json#/acceptance_refs/{index}": value
                for index, value in enumerate(plan_acceptance_refs)
            }
        )
        expanded_acceptance_refs: list[str] = []
        for ref in acceptance_refs:
            expanded_acceptance_refs.append(pointer_to_value.get(ref, ref))
        expected_task_refs = set(plan_acceptance_refs)
        task_ref_set = set(expanded_acceptance_refs)
        missing_plan_refs = sorted(expected_task_refs - task_ref_set)
        unknown_task_refs = sorted(task_ref_set - expected_task_refs)
        if missing_plan_refs:
            errors.append(
                "task-index.json human acceptance universe is missing plan acceptance_refs: "
                + ", ".join(missing_plan_refs)
                + f" (copy plan-contract.acceptance_refs values exactly, or use {plan_label}#/acceptance_refs/N)"
            )
        if unknown_task_refs:
            errors.append(
                "task-index.json human acceptance universe contains acceptance_refs not present in the plan: "
                + ", ".join(unknown_task_refs)
                + "; expected the plan values "
                + ", ".join(plan_acceptance_refs)
            )
        if (
            not missing_plan_refs
            and not unknown_task_refs
            and expanded_acceptance_refs != plan_acceptance_refs
        ):
            errors.append(
                "task-index.json acceptance_refs must preserve plan-contract.acceptance_refs order"
            )
        # Downstream obligation source_ref checks use the expanded value set.
        acceptance_refs = expanded_acceptance_refs

    def _expand_acceptance_ref(ref: str) -> str:
        text = str(ref or "").strip()
        return pointer_to_value.get(text, text)

    expected_source_refs = set(acceptance_refs)

    raw_obligations = payload.get("human_acceptance_obligations", [])
    raw_scenarios = payload.get("human_acceptance_scenarios", [])
    modern_ready = payload.get("version") == 2 and payload.get("status") == "ready"
    universe_declared = bool(
        acceptance_refs
        or plan_acceptance_refs
        or raw_obligations
        or raw_scenarios
        or "human_acceptance_obligations" in payload
        or "human_acceptance_scenarios" in payload
        or modern_ready
    )
    if not universe_declared:
        return errors
    if not isinstance(raw_obligations, list):
        errors.append("task-index.json human_acceptance_obligations must be an array")
        raw_obligations = []
    if not isinstance(raw_scenarios, list):
        errors.append("task-index.json human_acceptance_scenarios must be an array")
        raw_scenarios = []
    if acceptance_refs and not raw_obligations:
        errors.append(
            "task-index.json human_acceptance_obligations must be non-empty when acceptance_refs are present"
        )
    if acceptance_refs and not raw_scenarios:
        errors.append(
            "task-index.json human_acceptance_scenarios must be non-empty when acceptance_refs are present"
        )
    if modern_ready and (not raw_obligations or not raw_scenarios):
        errors.append(
            "ready task-index.json version 2 requires a non-empty Human Acceptance Universe"
        )

    official_entrypoints = payload.get("official_entrypoints", [])
    if not isinstance(official_entrypoints, list):
        errors.append("task-index.json official_entrypoints must be an array")
        official_entrypoints = []
    entrypoints_by_id: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(official_entrypoints):
        prefix = f"task-index.json official_entrypoints[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{prefix} must be an object")
            continue
        entrypoint_id = _required_contract_text(value, "id", prefix, errors)
        _required_contract_text(value, "command", prefix, errors)
        _required_contract_text(value, "ready_signal", prefix, errors)
        if not entrypoint_id:
            continue
        if entrypoint_id in entrypoints_by_id:
            errors.append(
                f"task-index.json official entrypoint id must be unique: {entrypoint_id}"
            )
            continue
        entrypoints_by_id[entrypoint_id] = value

    system_review_scenarios = payload.get("system_review_scenarios", [])
    if not isinstance(system_review_scenarios, list):
        errors.append("task-index.json system_review_scenarios must be an array")
        system_review_scenarios = []
    review_scenarios_by_id: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(system_review_scenarios):
        prefix = f"task-index.json system_review_scenarios[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = _required_contract_text(value, "id", prefix, errors)
        entrypoint_id = _required_contract_text(value, "entrypoint_id", prefix, errors)
        if not isinstance(value.get("required"), bool):
            errors.append(f"{prefix}.required must be a boolean")
        if entrypoint_id and entrypoint_id not in entrypoints_by_id:
            errors.append(
                f"{prefix}.entrypoint_id references unknown official entrypoint: {entrypoint_id}"
            )
        if not scenario_id:
            continue
        if scenario_id in review_scenarios_by_id:
            errors.append(
                f"task-index.json system review scenario id must be unique: {scenario_id}"
            )
            continue
        review_scenarios_by_id[scenario_id] = value

    required_review_entrypoint_ids = {
        str(scenario.get("entrypoint_id") or "").strip()
        for scenario in review_scenarios_by_id.values()
        if scenario.get("required") is True
        and str(scenario.get("entrypoint_id") or "").strip() in entrypoints_by_id
    }
    missing_review_entrypoints = sorted(
        set(entrypoints_by_id) - required_review_entrypoint_ids
    )
    if missing_review_entrypoints:
        errors.append(
            "task-index.json official entrypoints are missing required system review scenarios: "
            + ", ".join(missing_review_entrypoints)
        )

    raw_review_obligations = payload.get("review_obligations", [])
    if not isinstance(raw_review_obligations, list):
        errors.append("task-index.json review_obligations must be an array")
        raw_review_obligations = []
    review_obligations_by_id: dict[str, dict[str, Any]] = {}
    required_review_source_refs: set[str] = set()
    required_review_sources_by_scenario: dict[str, set[str]] = {}
    for index, value in enumerate(raw_review_obligations):
        prefix = f"task-index.json review_obligations[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{prefix} must be an object")
            continue
        obligation_id = _required_contract_text(value, "id", prefix, errors)
        source_ref = _expand_acceptance_ref(
            _required_contract_text(value, "source_ref", prefix, errors)
        )
        required = value.get("required")
        if not isinstance(required, bool):
            errors.append(f"{prefix}.required must be a boolean")
        scenario_ids = _required_contract_string_list(
            value, "scenario_ids", prefix, errors
        )
        unknown_scenario_ids = sorted(
            scenario_id
            for scenario_id in scenario_ids
            if scenario_id not in review_scenarios_by_id
        )
        if unknown_scenario_ids:
            errors.append(
                f"{prefix} references unknown system review scenarios: "
                + ", ".join(unknown_scenario_ids)
            )
        if obligation_id:
            if obligation_id in review_obligations_by_id:
                errors.append(
                    "task-index.json review obligation id must be unique: "
                    + obligation_id
                )
            else:
                review_obligations_by_id[obligation_id] = {
                    **value,
                    "source_ref": source_ref,
                    "scenario_ids": scenario_ids,
                }
                if required is True and source_ref in expected_source_refs:
                    required_review_source_refs.add(source_ref)
                    required_scenario_ids = [
                        scenario_id
                        for scenario_id in scenario_ids
                        if scenario_id in review_scenarios_by_id
                        and review_scenarios_by_id[scenario_id].get("required") is True
                    ]
                    if not required_scenario_ids:
                        errors.append(
                            "task-index.json required review obligation "
                            f"{obligation_id} must map to at least one required "
                            "system review scenario"
                        )
                    for scenario_id in required_scenario_ids:
                        required_review_sources_by_scenario.setdefault(
                            scenario_id, set()
                        ).add(source_ref)

    missing_review_source_refs = sorted(
        expected_source_refs - required_review_source_refs
    )
    if missing_review_source_refs:
        errors.append(
            "task-index.json required review_obligations are missing acceptance_refs: "
            + ", ".join(missing_review_source_refs)
        )
    dedicated_review_scenarios_by_source: dict[str, set[str]] = {}
    for source_ref in sorted(expected_source_refs):
        dedicated_scenario_ids = {
            scenario_id
            for scenario_id, source_refs in required_review_sources_by_scenario.items()
            if source_refs == {source_ref}
        }
        dedicated_review_scenarios_by_source[source_ref] = dedicated_scenario_ids
        if source_ref in required_review_source_refs and not dedicated_scenario_ids:
            errors.append(
                "task-index.json acceptance_ref "
                f"{source_ref} must map to at least one dedicated required system "
                "review scenario"
            )

    obligations_by_id: dict[str, dict[str, Any]] = {}
    obligation_source_refs: list[str] = []
    for index, value in enumerate(raw_obligations):
        prefix = f"task-index.json human_acceptance_obligations[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{prefix} must be an object")
            continue
        obligation_id = _required_contract_text(value, "id", prefix, errors)
        source_ref = _expand_acceptance_ref(
            _required_contract_text(value, "source_ref", prefix, errors)
        )
        change_kind = _required_contract_text(value, "change_kind", prefix, errors)
        if change_kind and change_kind not in {"new", "changed"}:
            errors.append(f"{prefix}.change_kind must be new or changed")
        _required_contract_text(value, "user_outcome", prefix, errors)
        if not isinstance(value.get("required"), bool):
            errors.append(f"{prefix}.required must be a boolean")
        scenario_ids = _required_contract_string_list(
            value, "scenario_ids", prefix, errors
        )
        if source_ref:
            obligation_source_refs.append(source_ref)
        if obligation_id:
            if obligation_id in obligations_by_id:
                errors.append(
                    f"task-index.json human acceptance obligation id must be unique: {obligation_id}"
                )
            else:
                # Store expanded source_ref so later scenario/dedication checks
                # compare against the same canonical acceptance_refs set.
                obligations_by_id[obligation_id] = {
                    **value,
                    "source_ref": source_ref,
                    "scenario_ids": scenario_ids,
                }

    actual_source_refs = set(obligation_source_refs)
    missing_source_refs = sorted(expected_source_refs - actual_source_refs)
    unknown_source_refs = sorted(actual_source_refs - expected_source_refs)
    if missing_source_refs:
        errors.append(
            "task-index.json human acceptance obligations are missing acceptance_refs: "
            + ", ".join(missing_source_refs)
        )
    if unknown_source_refs:
        errors.append(
            "task-index.json human acceptance obligations contain unknown source_ref values: "
            + ", ".join(unknown_source_refs)
        )
    for source_ref in sorted(expected_source_refs):
        matching = [
            obligation
            for obligation in obligations_by_id.values()
            if str(obligation.get("source_ref") or "").strip() == source_ref
        ]
        if matching and not any(item.get("required") is True for item in matching):
            errors.append(
                f"task-index.json acceptance_ref {source_ref} must be covered by at least one required human acceptance obligation"
            )

    scenarios_by_id: dict[str, dict[str, Any]] = {}
    step_ids: set[str] = set()
    for index, value in enumerate(raw_scenarios):
        prefix = f"task-index.json human_acceptance_scenarios[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = _required_contract_text(value, "id", prefix, errors)
        for field in ("title", "user_value", "start_state"):
            _required_contract_text(value, field, prefix, errors)
        _required_contract_text(value, "actor", prefix, errors)
        required = value.get("required")
        if not isinstance(required, bool):
            errors.append(f"{prefix}.required must be a boolean")
        entrypoint_id = _required_contract_text(value, "entrypoint_id", prefix, errors)
        if entrypoint_id and entrypoint_id not in entrypoints_by_id:
            errors.append(
                f"{prefix}.entrypoint_id references unknown official entrypoint: {entrypoint_id}"
            )
        obligation_ids = _required_contract_string_list(
            value, "obligation_ids", prefix, errors
        )
        review_scenario_ids = _required_contract_string_list(
            value, "review_scenario_ids", prefix, errors
        )
        steps = value.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{prefix}.steps must be a non-empty array")
        else:
            for step_index, step in enumerate(steps):
                step_prefix = f"{prefix}.steps[{step_index}]"
                if not isinstance(step, dict):
                    errors.append(f"{step_prefix} must be an object")
                    continue
                step_id = _required_contract_text(step, "id", step_prefix, errors)
                for field in (
                    "action",
                    "expected_result",
                    "evidence_requirement",
                    "risk",
                ):
                    _required_contract_text(step, field, step_prefix, errors)
                risk = str(step.get("risk") or "").strip()
                if risk and risk not in {"low", "medium", "high"}:
                    errors.append(f"{step_prefix}.risk must be low, medium, or high")
                if step_id:
                    if step_id in step_ids:
                        errors.append(
                            f"task-index.json human acceptance step id must be unique: {step_id}"
                        )
                    step_ids.add(step_id)
        if not scenario_id:
            continue
        if scenario_id in scenarios_by_id:
            errors.append(
                f"task-index.json human acceptance scenario id must be unique: {scenario_id}"
            )
            continue
        scenarios_by_id[scenario_id] = {
            **value,
            "obligation_ids": obligation_ids,
            "review_scenario_ids": review_scenario_ids,
        }

    for obligation_id, obligation in obligations_by_id.items():
        scenario_ids = obligation.get("scenario_ids") or []
        unknown_scenario_ids = sorted(
            scenario_id
            for scenario_id in scenario_ids
            if scenario_id not in scenarios_by_id
        )
        if unknown_scenario_ids:
            errors.append(
                f"task-index.json human acceptance obligation {obligation_id} references unknown scenarios: "
                + ", ".join(unknown_scenario_ids)
            )
        referenced_scenarios = [
            scenarios_by_id[scenario_id]
            for scenario_id in scenario_ids
            if scenario_id in scenarios_by_id
        ]
        if obligation.get("required") is True and not any(
            scenario.get("required") is True for scenario in referenced_scenarios
        ):
            errors.append(
                f"task-index.json required human acceptance obligation {obligation_id} must map to at least one required scenario"
            )
        for scenario in referenced_scenarios:
            if obligation_id not in scenario.get("obligation_ids", []):
                errors.append(
                    f"task-index.json human acceptance obligation {obligation_id} and scenario {scenario.get('id')} must reference each other"
                )

    required_human_sources_by_scenario: dict[str, set[str]] = {}
    for scenario_id, scenario in scenarios_by_id.items():
        obligation_ids = scenario.get("obligation_ids") or []
        unknown_obligation_ids = sorted(
            obligation_id
            for obligation_id in obligation_ids
            if obligation_id not in obligations_by_id
        )
        if unknown_obligation_ids:
            errors.append(
                f"task-index.json human acceptance scenario {scenario_id} references unknown obligations: "
                + ", ".join(unknown_obligation_ids)
            )
        for obligation_id in obligation_ids:
            obligation = obligations_by_id.get(obligation_id)
            if obligation is not None and scenario_id not in obligation.get(
                "scenario_ids", []
            ):
                errors.append(
                    f"task-index.json human acceptance scenario {scenario_id} and obligation {obligation_id} must reference each other"
                )

        scenario_acceptance_refs = {
            str(obligation.get("source_ref") or "").strip()
            for obligation_id in obligation_ids
            if (obligation := obligations_by_id.get(obligation_id)) is not None
            and obligation.get("required") is True
            and str(obligation.get("source_ref") or "").strip() in expected_source_refs
        }
        if scenario.get("required") is True:
            required_human_sources_by_scenario[scenario_id] = scenario_acceptance_refs
            if len(scenario_acceptance_refs) > 1:
                errors.append(
                    "task-index.json required human acceptance scenario "
                    f"{scenario_id} must not span multiple acceptance_refs: "
                    + ", ".join(sorted(scenario_acceptance_refs))
                )

        review_scenario_ids = scenario.get("review_scenario_ids") or []
        unknown_review_ids = sorted(
            review_id
            for review_id in review_scenario_ids
            if review_id not in review_scenarios_by_id
        )
        if unknown_review_ids:
            errors.append(
                f"task-index.json human acceptance scenario {scenario_id} references unknown system review scenarios: "
                + ", ".join(unknown_review_ids)
            )
        referenced_review_scenarios = [
            review_scenarios_by_id[review_id]
            for review_id in review_scenario_ids
            if review_id in review_scenarios_by_id
        ]
        if scenario.get("required") is True and not any(
            review_scenario.get("required") is True
            for review_scenario in referenced_review_scenarios
        ):
            errors.append(
                f"task-index.json required human acceptance scenario {scenario_id} must reference at least one required system review scenario"
            )
        if scenario.get("required") is True and len(scenario_acceptance_refs) == 1:
            source_ref = next(iter(scenario_acceptance_refs))
            if not any(
                review_scenario.get("required") is True
                and str(review_scenario.get("id") or "").strip()
                in dedicated_review_scenarios_by_source.get(source_ref, set())
                for review_scenario in referenced_review_scenarios
            ):
                errors.append(
                    "task-index.json required human acceptance scenario "
                    f"{scenario_id} must reference a dedicated required system review "
                    f"scenario covering the same acceptance_ref: {source_ref}"
                )
        entrypoint_id = str(scenario.get("entrypoint_id") or "").strip()
        mismatched_review_ids = sorted(
            str(review_scenario.get("id") or "")
            for review_scenario in referenced_review_scenarios
            if str(review_scenario.get("entrypoint_id") or "").strip() != entrypoint_id
        )
        if mismatched_review_ids:
            errors.append(
                f"task-index.json human acceptance scenario {scenario_id} has system review scenarios for a different entrypoint: "
                + ", ".join(mismatched_review_ids)
            )

    for source_ref in sorted(expected_source_refs):
        required_obligations = [
            obligation
            for obligation in obligations_by_id.values()
            if obligation.get("required") is True
            and str(obligation.get("source_ref") or "").strip() == source_ref
        ]
        required_scenario_ids = {
            scenario_id
            for obligation in required_obligations
            for scenario_id in obligation.get("scenario_ids") or []
            if scenario_id in scenarios_by_id
            and scenarios_by_id[scenario_id].get("required") is True
        }
        if required_obligations and not any(
            required_human_sources_by_scenario.get(scenario_id) == {source_ref}
            for scenario_id in required_scenario_ids
        ):
            errors.append(
                "task-index.json acceptance_ref "
                f"{source_ref} must map to at least one dedicated required human "
                "acceptance scenario"
            )
    return errors


def _required_contract_text(
    payload: dict[str, Any], field: str, prefix: str, errors: list[str]
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}.{field} must be a non-empty string")
        return ""
    return value.strip()


def _required_contract_string_list(
    payload: dict[str, Any], field: str, prefix: str, errors: list[str]
) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{field} must be a non-empty string array")
        return []
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{prefix}.{field}[{index}] must be a non-empty string")
            continue
        normalized.append(item.strip())
    duplicates = sorted(item for item in set(normalized) if normalized.count(item) > 1)
    if duplicates:
        errors.append(
            f"{prefix}.{field} must contain unique values: " + ", ".join(duplicates)
        )
    return normalized


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


def _triggered_task_consequence_sources(
    feature_dir: Path,
) -> tuple[tuple[tuple[Any, str], ...], list[str]]:
    sources: list[tuple[Any, str]] = []
    errors: list[str] = []
    for source_path, label in (
        (feature_dir / "handoff-to-tasks.json", "handoff-to-tasks.json"),
        *(_consequence_contract_paths(feature_dir)),
        (
            feature_dir / "brainstorming" / "handoff-to-tasks.json",
            "brainstorming/handoff-to-tasks.json",
        ),
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
        errors.append(
            "task-index.json is required when upstream artifacts carry triggered consequence obligations"
        )
        return errors

    task_index_payload, task_index_errors = _read_json_artifact(
        task_index_path, "task-index.json"
    )
    if task_index_errors:
        errors.extend(task_index_errors)
        return errors

    mapped_ids = _task_index_consequence_ids(task_index_payload)
    missing_ids = sorted(required_ids - mapped_ids)
    if missing_ids:
        errors.append(
            "task-index.json is missing consequence mapping for: "
            + ", ".join(missing_ids)
        )

    tasks_content = (feature_dir / "tasks.md").read_text(
        encoding="utf-8", errors="replace"
    )
    if CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION not in tasks_content:
        errors.append(
            f"tasks.md is missing {CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION}"
        )

    return errors


def _validate_prd_scan_artifacts(
    feature_dir: Path, *, require_heavy_scan_json: bool = False
) -> list[str]:
    errors: list[str] = []
    for directory_name in ("scan-packets", "evidence", "worker-results"):
        target = feature_dir / directory_name
        if target.exists() and not target.is_dir():
            errors.append(f"{directory_name} must be a directory")

    coverage_payload, coverage_errors = _read_json_artifact(
        feature_dir / "coverage-ledger.json", "coverage-ledger.json"
    )
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
        errors.append(
            "capability-ledger.json must define a top-level capabilities array"
        )

    artifact_payload, artifact_errors = _read_json_artifact(
        feature_dir / "artifact-contracts.json", "artifact-contracts.json"
    )
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
        errors.append(
            "reconstruction-checklist.json must contain a top-level JSON object"
        )
    elif not isinstance(checklist_payload.get("checks"), list):
        errors.append(
            "reconstruction-checklist.json must define a top-level checks array"
        )

    if require_heavy_scan_json:
        for filename, array_key in PRD_HEAVY_SCAN_JSON_ARTIFACTS.items():
            errors.extend(
                _validate_json_object_with_array_key(feature_dir, filename, array_key)
            )

    return errors


def _validate_prd_worker_results(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    worker_results_dir = feature_dir / "worker-results"
    if not worker_results_dir.is_dir():
        return errors

    result_paths = sorted(
        path for path in worker_results_dir.iterdir() if path.suffix == ".json"
    )
    if not result_paths:
        return ["worker-results must contain at least one JSON result file"]

    for result_path in result_paths:
        relative_label = result_path.relative_to(feature_dir).as_posix()
        payload, read_errors = _read_json_artifact(result_path, relative_label)
        if read_errors:
            errors.extend(read_errors)
            continue
        if not isinstance(payload, dict):
            errors.append(f"{relative_label} must contain a top-level JSON object")
            continue

        for key in sorted(PRD_WORKER_RESULT_REQUIRED_KEYS - payload.keys()):
            errors.append(
                f"{relative_label} is missing required worker result key: {key}"
            )
        paths_read = payload.get("paths_read")
        if (
            not isinstance(paths_read, list)
            or not paths_read
            or not all(isinstance(item, str) and item.strip() for item in paths_read)
        ):
            errors.append(
                f"{relative_label} paths_read must be a non-empty string array"
            )
        for key in ("unknowns", "recommended_ledger_updates"):
            if key in payload and not isinstance(payload.get(key), list):
                errors.append(f"{relative_label} {key} must be an array")
        if "confidence" in payload and not str(payload.get("confidence") or "").strip():
            errors.append(f"{relative_label} confidence must be non-empty")

    return errors


def _validate_graph_artifact(
    feature_dir: Path, relative_path: str, required_keys: frozenset[str]
) -> list[str]:
    payload, read_errors = _read_json_artifact(
        feature_dir / relative_path, relative_path
    )
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
    payload, read_errors = _read_json_artifact(
        feature_dir / "status.json", "status.json"
    )
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
    if (
        feature_dir.name == "project-cognition"
        and feature_dir.parent.name == ".specify"
    ):
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


def _run_project_cognition_validation(
    project_root: Path, command: str
) -> dict[str, object]:
    try:
        return run_specify_runtime(
            ["cognition", command, "--format", "json"],
            cwd=project_root,
        )
    except SpecifyRuntimeError as exc:
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
    payload, read_errors = _read_json_artifact(
        feature_dir / "status.json", "status.json"
    )
    if read_errors:
        errors.extend(read_errors)
        return errors
    if not isinstance(payload, dict):
        errors.append("status.json must contain a top-level JSON object")
        return errors
    result_state = str(
        payload.get("last_update_outcome") or payload.get("result_state") or ""
    ).strip()
    freshness = str(payload.get("freshness") or "").strip()
    readiness = str(payload.get("readiness") or "").strip()
    recommended = str(payload.get("recommended_next_action") or "").strip()
    valid_states = {"ready", "no_op", "partial_refresh", "needs_rebuild", "blocked"}
    if result_state not in valid_states:
        errors.append(
            "status.json must record last_update_outcome/result_state as ready, no_op, partial_refresh, needs_rebuild, or blocked"
        )
        return errors
    if result_state == "ready" and (
        freshness != "fresh"
        or readiness != "query_ready"
        or recommended != "use_project_cognition"
    ):
        errors.append(
            "ready map-update result_state requires freshness=fresh, readiness=query_ready, and recommended_next_action=use_project_cognition"
        )
    if result_state == "partial_refresh" and freshness != "partial_refresh":
        errors.append(
            "partial_refresh map-update result_state requires freshness=partial_refresh"
        )
    if result_state == "needs_rebuild" and readiness != "needs_rebuild":
        errors.append(
            "needs_rebuild map-update result_state requires readiness=needs_rebuild"
        )
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
    for key in (
        "deep_workflow_path",
        "deep_workflow_page",
        "deep_workflow",
        "page",
        "path",
    ):
        value = capability.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resolve_map_build_page_path(
    feature_dir: Path, page: str
) -> tuple[Path | None, str | None]:
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


def _missing_rendered_mermaid_fields(
    content: str, capability: dict[str, object]
) -> list[str]:
    normalized_blocks = [
        _normalize_mermaid_content(block) for block in _extract_mermaid_blocks(content)
    ]
    missing: list[str] = []
    for field in ("lifecycle_mermaid", "flow_mermaid"):
        value = capability.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        normalized_value = _normalize_mermaid_content(value)
        if not any(
            normalized_value and normalized_value in block
            for block in normalized_blocks
        ):
            missing.append(field)
    return missing


def _validate_map_build_capability_diagrams(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(
        feature_dir / "index" / "capabilities.json", "index/capabilities.json"
    )
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


def _validate_prd_build_input_contracts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    coverage_payload, coverage_errors = _read_json_artifact(
        feature_dir / "coverage-ledger.json", "coverage-ledger.json"
    )
    if coverage_errors:
        return coverage_errors
    if not isinstance(coverage_payload, dict):
        return ["coverage-ledger.json must contain a top-level JSON object"]
    coverage_rows = coverage_payload.get("rows")
    if not isinstance(coverage_rows, list):
        return ["coverage-ledger.json must define a top-level rows array"]
    if not coverage_rows:
        errors.append(
            "coverage-ledger.json must include at least one substantive coverage row"
        )
    for index, row in enumerate(coverage_rows, start=1):
        label = f"coverage-ledger.json row {index}"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        subject = next(
            (
                str(row.get(key) or "").strip()
                for key in ("id", "surface", "path", "capability_id", "capability_ref")
                if str(row.get(key) or "").strip()
            ),
            "",
        )
        status = str(row.get("status") or row.get("coverage_state") or "").strip()
        evidence = row.get("evidence")
        reason = str(row.get("reason") or row.get("notes") or "").strip()
        if not subject:
            errors.append(f"{label} must identify a surface, path, or capability")
        if not status:
            errors.append(f"{label} must record status or coverage_state")
        if status.lower() in {"n/a", "na", "not-applicable", "not_applicable"}:
            if not reason and not _has_nonempty_prd_evidence(evidence):
                errors.append(
                    f"{label} not-applicable status requires evidence or a reason"
                )
        elif not _has_nonempty_prd_evidence(evidence):
            errors.append(f"{label} must record non-empty evidence")

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

    critical_capabilities = [
        item
        for item in capabilities
        if isinstance(item, dict) and item.get("tier") == "critical"
    ]
    if not critical_capabilities:
        errors.append(
            "capability-ledger.json must include at least one critical capability before prd-build can pass"
        )
    else:
        non_ready = [
            str(item.get("status") or "").strip() or "missing"
            for item in critical_capabilities
            if str(item.get("status") or "").strip().lower()
            not in PRD_RECONSTRUCTION_READY_STATUSES
        ]
        if non_ready:
            joined = ", ".join(sorted(set(non_ready)))
            errors.append(
                "prd-build is blocked because critical capabilities must be reconstruction-ready; "
                f"found: {joined}"
            )

    artifact_payload, artifact_errors = _read_json_artifact(
        feature_dir / "artifact-contracts.json", "artifact-contracts.json"
    )
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
        errors.append(
            "artifact-contracts.json must include at least one artifact before prd-build can pass"
        )
    else:
        for index, artifact in enumerate(artifacts, start=1):
            if not isinstance(artifact, dict):
                errors.append(
                    f"artifact-contracts.json artifact {index} must be an object"
                )
                continue
            for field in ("id", "status"):
                if not str(artifact.get(field) or "").strip():
                    errors.append(
                        f"artifact-contracts.json artifact {index} must define non-empty {field}"
                    )

    checklist_payload, checklist_errors = _read_json_artifact(
        feature_dir / "reconstruction-checklist.json", "reconstruction-checklist.json"
    )
    if checklist_errors:
        errors.extend(checklist_errors)
        return errors
    if not isinstance(checklist_payload, dict):
        errors.append(
            "reconstruction-checklist.json must contain a top-level JSON object"
        )
        return errors
    checks = checklist_payload.get("checks")
    if not isinstance(checks, list):
        errors.append(
            "reconstruction-checklist.json must define a top-level checks array"
        )
    elif not checks:
        errors.append(
            "reconstruction-checklist.json must include at least one check before prd-build can pass"
        )
    else:
        for index, check in enumerate(checks, start=1):
            if not isinstance(check, dict):
                errors.append(
                    f"reconstruction-checklist.json check {index} must be an object"
                )
                continue
            for field in ("id", "status"):
                if not str(check.get(field) or "").strip():
                    errors.append(
                        f"reconstruction-checklist.json check {index} must define non-empty {field}"
                    )

    scan_packets_dir = feature_dir / "scan-packets"
    if not scan_packets_dir.is_dir():
        errors.append("scan-packets must be a directory")
    elif not any(
        path.is_file() and path.stat().st_size > 0
        for path in scan_packets_dir.rglob("*")
    ):
        errors.append(
            "scan-packets must contain at least one packet file before prd-build can pass"
        )

    worker_results_dir = feature_dir / "worker-results"
    if not worker_results_dir.is_dir():
        errors.append("worker-results must be a directory")
    elif not any(worker_results_dir.iterdir()):
        errors.append(
            "worker-results must contain at least one result file before prd-build can pass"
        )
    else:
        errors.extend(_validate_prd_worker_results(feature_dir))

    evidence_dir = feature_dir / "evidence"
    if not evidence_dir.is_dir():
        errors.append("evidence must be a directory")
    elif not any(
        path.is_file() and path.stat().st_size > 0 for path in evidence_dir.rglob("*")
    ):
        errors.append(
            "evidence must contain at least one file or subdirectory entry before prd-build can pass"
        )

    return errors


def _validate_prd_build_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    missing_exports = [
        relative_path
        for relative_path in PRD_BUILD_REQUIRED_HEAVY_EXPORTS
        if not (feature_dir / relative_path).exists()
    ]
    errors.extend(
        f"missing required artifact: {relative_path}"
        for relative_path in missing_exports
    )
    for relative_path in PRD_BUILD_REQUIRED_HEAVY_EXPORTS:
        target = feature_dir / relative_path
        if target.exists() and not target.is_file():
            errors.append(f"required artifact must be a file: {relative_path}")
    for relative_path in PRD_BUILD_OUTPUT_ARTIFACTS:
        target = feature_dir / relative_path
        if not target.is_file():
            continue
        content = target.read_text(encoding="utf-8", errors="replace")
        substantive_lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip()
            and not line.lstrip().startswith("#")
            and not line.lstrip().startswith("<!--")
        ]
        if not substantive_lines:
            errors.append(
                f"required build output must contain substantive content beyond headings: {relative_path}"
            )

    prd_path = feature_dir / "exports" / "prd.md"
    if prd_path.is_file():
        errors.extend(
            _validate_markdown_contains(
                prd_path,
                PRD_EXPORT_REQUIRED_SECTIONS,
                "exports/prd.md",
            )
        )

    workflow_state_path = feature_dir / "workflow-state.md"
    if workflow_state_path.is_file():
        checkpoint = serialize_workflow_state(workflow_state_path)
        workflow_content = workflow_state_path.read_text(
            encoding="utf-8", errors="replace"
        )
        if (
            str(checkpoint.get("active_command") or "").strip().lower()
            != "sp-prd-build"
        ):
            errors.append(
                "workflow-state.md active_command must be sp-prd-build at completion"
            )
        if str(checkpoint.get("status") or "").strip().lower() != "complete":
            errors.append(
                "workflow-state.md status must be complete at prd-build completion"
            )
        if (
            extract_field(workflow_content, "build_status").strip().lower()
            != "complete"
        ):
            errors.append(
                "workflow-state.md build_status must be complete at prd-build completion"
            )
    errors.extend(_validate_prd_build_input_contracts(feature_dir))
    return errors


def _is_legacy_specify_package(feature_dir: Path, workflow_state_content: str) -> bool:
    return (
        feature_dir / "brainstorming" / "legacy-state.json"
    ).exists() or "## Fixed Lifecycle State" in workflow_state_content


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
            errors.append(f"{label} next_action must be a non-empty string when ready")
        blockers = payload.get("blockers")
        if isinstance(blockers, list) and blockers:
            errors.append(f"{label} blockers must be empty when ready")
    return errors


SPEC_DESIGN_GATE_DECISIONS = {
    "not_required",
    "required",
    "satisfied",
    "narrow_existing_pattern_exception",
}


def _spec_gate_decision(payload: dict[str, Any], field: str) -> str:
    gate = payload.get(field)
    if not isinstance(gate, dict):
        return ""
    return str(gate.get("decision") or "").strip()


def _validate_spec_design_gate(payload: dict[str, Any]) -> list[str]:
    gate = payload.get("design_gate")
    if gate is None:
        return []
    errors: list[str] = []
    if not isinstance(gate, dict):
        return ["spec-contract.json design_gate must be an object"]
    decision = str(gate.get("decision") or "").strip()
    if decision not in SPEC_DESIGN_GATE_DECISIONS:
        errors.append(
            "spec-contract.json design_gate.decision must be not_required, required, satisfied, or narrow_existing_pattern_exception"
        )
    scope = gate.get("scope")
    if scope is not None and not isinstance(scope, str):
        errors.append("spec-contract.json design_gate.scope must be null or a string")
    reason_codes = gate.get("reason_codes")
    if not isinstance(reason_codes, list) or any(
        not isinstance(item, str) or not item.strip() for item in reason_codes
    ):
        errors.append(
            "spec-contract.json design_gate.reason_codes must be a list of non-empty strings"
        )
    return_target = gate.get("return_target")
    if return_target is not None and return_target != "/sp.plan":
        errors.append("spec-contract.json design_gate.return_target must be /sp.plan")
    if decision == "required":
        if (
            not isinstance(scope, str)
            or not scope.strip()
            or DESIGN_CHANGE_SCOPE_RE.fullmatch(scope.strip()) is None
        ):
            errors.append(
                "spec-contract.json required design_gate must name an exact scope"
            )
        if not isinstance(reason_codes, list) or not reason_codes:
            errors.append(
                "spec-contract.json required design_gate must include reason_codes"
            )
        if return_target != "/sp.plan":
            errors.append(
                "spec-contract.json required design_gate must return to /sp.plan"
            )
    return errors


def _spec_transition_next_action_allowed(
    payload: dict[str, Any], next_action: object
) -> bool:
    if isinstance(next_action, dict):
        token = str(next_action.get("command") or "").strip()
    else:
        token = str(next_action or "").strip()
    design_required = _spec_gate_decision(payload, "design_gate") == "required"
    feasibility_required = (
        _spec_gate_decision(payload, "feasibility_gate") == "required"
    )
    if design_required and feasibility_required:
        return False
    if design_required:
        return token == "/sp.design"
    if feasibility_required:
        return token == "/sp.plan"
    return token == "/sp.plan"


def _validate_pending_spec_design_contract(
    feature_dir: Path, design_contract: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if any(str(design_contract.get(field) or "").strip() for field in UI_DESIGN_CHANGE_BINDING_FIELDS):
        errors.append(
            "spec-contract.json pending Design route must not carry registered design binding fields before approval"
        )
    ui_brief_ref = str(design_contract.get("ui_brief_ref") or "").strip()
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
    if str(design_contract.get("surface_type") or "").strip() not in UI_CONTRACT_SURFACE_TYPES:
        errors.append(
            "spec-contract.json design_contract.surface_type must be a supported UI surface type"
        )
    platforms = design_contract.get("platforms")
    if (
        not isinstance(platforms, list)
        or not platforms
        or any(str(item).strip() not in UI_CONTRACT_PLATFORMS for item in platforms)
    ):
        errors.append(
            "spec-contract.json design_contract.platforms must contain supported UI platforms"
        )
    for field in (
        "entry_points",
        "required_states",
        "must_preserve",
        "may_adapt",
        "must_not",
        "validation_refs",
        "visual_acceptance",
    ):
        value = design_contract.get(field)
        if not isinstance(value, list) or not any(
            isinstance(item, str) and item.strip() for item in value
        ):
            errors.append(
                f"spec-contract.json pending Design route requires non-empty design_contract.{field}"
            )
    errors.extend(
        _validate_ui_style_authority(
            design_contract.get("style_authority"), "spec-contract.json design_contract"
        )
    )
    for field in (
        "subject",
        "audience",
        "single_job",
    ):
        if not str(design_contract.get(field) or "").strip():
            errors.append(
                f"spec-contract.json pending Design route requires non-empty design_contract.{field}"
            )
    forbidden_scalar_fields = (
        "design_change_id",
        "design_change_ref",
        "design_change_sha256",
        "design_contract_ref",
        "approved_visual_ref",
        "approved_preview_sha256",
        "approved_manifest_sha256",
        "approved_handoff_ref",
        "approved_handoff_sha256",
    )
    for field in forbidden_scalar_fields:
        if str(design_contract.get(field) or "").strip():
            errors.append(
                f"spec-contract.json pending Design route must not prefill design_contract.{field}"
            )
    forbidden_list_fields = (
        "design_decision_ids",
        "handoff_contract_ids",
        "surface_catalog",
        "scenario_matrix",
        "interaction_matrix",
        "editing_matrix",
        "accessibility_matrix",
        "navigation_matrix",
        "content_matrix",
        "data_state_matrix",
        "color_modes",
        "component_contracts",
        "responsive_matrix",
        "visual_acceptance_matrix",
        "accepted_deviations",
    )
    for field in forbidden_list_fields:
        value = design_contract.get(field)
        if isinstance(value, list) and value:
            errors.append(
                f"spec-contract.json pending Design route must not prefill design_contract.{field}"
            )
    for field in ("motion_contract", "usability_validation", "comparison_tolerance"):
        value = design_contract.get(field)
        if isinstance(value, dict) and value:
            errors.append(
                f"spec-contract.json pending Design route must not prefill design_contract.{field}"
            )
    return errors


def _spec_owned_pending_ui_fields_match(
    spec_contract: dict[str, Any], plan_contract: dict[str, Any], label: str
) -> list[str]:
    errors: list[str] = []
    for field in (
        "ui_work_type",
        "surface_type",
        "style_authority",
        "subject",
        "audience",
        "single_job",
        "reference_intents",
        "real_content_plan",
        "image_plan",
        "entry_points",
        "required_states",
        "must_preserve",
        "may_adapt",
        "must_not",
        "validation_refs",
        "visual_acceptance",
    ):
        if _canonical_ui_continuity_value(
            field, plan_contract.get(field)
        ) != _canonical_ui_continuity_value(field, spec_contract.get(field)):
            errors.append(
                f"{label} ui_design_contract.{field} must preserve the specification UI contract"
            )
    spec_platforms = set(_normalized_ui_string_values("platforms", spec_contract))
    plan_platforms = set(_normalized_ui_string_values("platforms", plan_contract))
    if spec_platforms and spec_platforms != plan_platforms:
        errors.append(
            f"{label} ui_design_contract.platforms must preserve the specification UI contract"
        )
    return errors


def _verify_current_formal_post_specify_adoption(
    feature_dir: Path, plan_contract: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    binding = plan_contract.get("design_adoption_binding")
    label = "plan-contract.json"
    if not isinstance(binding, dict):
        return None, [f"{label} ui_design_contract.design_adoption_binding must be an object"]
    mode = str(binding.get("mode") or "").strip()
    consumer_ref = str(binding.get("consumer_ref") or "").strip()
    scope = str(binding.get("scope") or "").strip()
    change_id = str(binding.get("change_id") or "").strip()
    binding_ref = str(binding.get("binding_ref") or "").strip()
    binding_sha256 = str(binding.get("binding_sha256") or "").strip()
    impact_sha256 = str(binding.get("impact_sha256") or "").strip()
    revision = binding.get("revision")
    errors: list[str] = []
    if mode != "formal-post-specify":
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.mode must be formal-post-specify"
        )
    feature_id = feature_dir.name
    expected_consumer = f"feature:{feature_id}"
    if consumer_ref != expected_consumer:
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.consumer_ref must be {expected_consumer}"
        )
    spec_path = feature_dir / "spec-contract.json"
    try:
        spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        spec_payload = {}
    expected_scope = ""
    if isinstance(spec_payload, dict):
        gate = spec_payload.get("design_gate")
        if isinstance(gate, dict):
            expected_scope = str(gate.get("scope") or "").strip()
    if not DESIGN_CHANGE_SCOPE_RE.fullmatch(scope):
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.scope must be a stable path-like identifier"
        )
    elif expected_scope and scope != expected_scope:
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.scope must match spec-contract.json design_gate.scope"
        )
    if not UI_DESIGN_CHANGE_ID_RE.fullmatch(change_id):
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.change_id must be a canonical UD-#### ID"
        )
    elif change_id != str(plan_contract.get("design_change_id") or "").strip():
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.change_id must match ui_design_contract.design_change_id"
        )
    if not isinstance(revision, int) or revision <= 0:
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.revision must be a positive integer"
        )
    if UI_SHA256_RE.fullmatch(binding_sha256) is None:
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.binding_sha256 must be a SHA-256 digest"
        )
    if UI_SHA256_RE.fullmatch(impact_sha256) is None:
        errors.append(
            f"{label} ui_design_contract.design_adoption_binding.impact_sha256 must be a SHA-256 digest"
        )
    if errors:
        return None, errors

    project_root = _feature_project_root(feature_dir)
    try:
        index, _, records = _load_design_change_index(project_root.resolve())
        _, current = _current_design_adoption(
            index, consumer_ref=consumer_ref, scope=scope
        )
        if current is None:
            raise DesignLintError(
                "no current design adoption exists for the feature and scope"
            )
        if str(current.get("mode") or "").strip() != "formal-post-specify":
            raise DesignLintError(
                "current design adoption is not a formal-post-specify overlay"
            )
        current_binding_ref = str(current.get("binding_ref") or "").strip()
        if binding_ref != current_binding_ref:
            raise DesignLintError(
                "plan binding_ref does not match the current design adoption receipt"
            )
        binding_path = (project_root / binding_ref).resolve()
        try:
            binding_path.relative_to(project_root)
        except ValueError as exc:
            raise DesignLintError(
                "current design adoption binding_ref must stay inside the project"
            ) from exc
        binding_bytes = binding_path.read_bytes()
        actual_digest = hashlib.sha256(binding_bytes).hexdigest()
        if not _planning_ready_spec_binding(binding_bytes):
            raise DesignLintError(
                "formal-post-specify adoption requires the unchanged planning-ready source spec"
            )
        if (
            str(current.get("binding_sha256") or "").strip() != binding_sha256
            or actual_digest != binding_sha256
        ):
            raise DesignLintError(
                "source spec binding does not match the current design adoption receipt"
            )
        if int(current.get("revision") or 0) != revision:
            raise DesignLintError("current design adoption revision does not match the plan binding")
        if str(current.get("change_id") or "").strip() != change_id:
            raise DesignLintError("current design adoption change_id does not match the plan binding")
        if str(current.get("impact_sha256") or "").strip() != impact_sha256:
            raise DesignLintError("current design adoption impact_sha256 does not match the plan binding")
        record = _active_design_adoption_record(records, change_id=change_id, scope=scope)
        _, registered_digest, _, registered_record = _load_registered_design_change(
            project_root, change_id
        )
        if (
            str(current.get("design_change_sha256") or "").strip()
            != registered_digest
            or str(current.get("design_change_ref") or "").strip()
            != str(registered_record.get("design_ref") or "").strip()
            or str(record.get("approval_sha256") or "").strip()
            != registered_digest
        ):
            raise DesignLintError(
                "current design adoption does not match the active registered design"
            )
        contract_ref = str(current.get("design_contract_ref") or "").strip()
        contract_path = (project_root / contract_ref).resolve()
        try:
            contract_path.relative_to(project_root)
        except ValueError as exc:
            raise DesignLintError(
                "current design adoption design_contract_ref must stay inside the project"
            ) from exc
        if not contract_path.is_file():
            raise DesignLintError(
                "current design adoption design_contract_ref does not exist"
            )
        if (
            str(current.get("design_change_ref") or "").strip()
            != str(plan_contract.get("design_change_ref") or "").strip()
            or str(current.get("design_change_sha256") or "").strip()
            != str(plan_contract.get("design_change_sha256") or "").strip()
            or str(current.get("design_contract_ref") or "").strip()
            != str(plan_contract.get("design_contract_ref") or "").strip()
        ):
            raise DesignLintError(
                "current design adoption does not match ui_design_contract binding fields"
            )
        return current, []
    except (DesignLintError, OSError) as exc:
        return None, [
            f"{label} ui_design_contract.design_adoption_binding must match the current formal-post-specify adoption: {exc}"
        ]


def _validate_plan_design_adoption_binding(
    feature_dir: Path, plan_contract: dict[str, Any], label: str
) -> tuple[dict[str, Any] | None, list[str]]:
    binding = plan_contract.get("design_adoption_binding")
    if binding is None:
        return None, []
    current, errors = _verify_current_formal_post_specify_adoption(
        feature_dir, plan_contract
    )
    if errors:
        return None, errors
    return current, []


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
        "acceptance_coverage",
        "decisions",
        "semantic_delta",
        "capability_operations",
        "must_preserve_refs",
        "consequence_obligation_refs",
        "entrypoint_outcome_contract",
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
        "must_preserve_refs",
        "consequence_obligation_refs",
        "open_items",
    ):
        if field in payload and not isinstance(payload.get(field), list):
            errors.append(f"spec-contract.json {field} must be a list")
    if "capability_operations" in payload and not isinstance(
        payload.get("capability_operations"), (list, dict)
    ):
        errors.append(
            "spec-contract.json capability_operations must be an array or object"
        )
    acceptance = payload.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance:
        errors.append("spec-contract.json acceptance_criteria must be a non-empty list")
    elif any(not isinstance(item, str) or not item.strip() for item in acceptance):
        errors.append(
            "spec-contract.json acceptance_criteria must contain only non-empty strings"
        )
    errors.extend(_validate_spec_acceptance_coverage(payload))
    errors.extend(_validate_spec_design_gate(payload))
    if (
        _spec_gate_decision(payload, "design_gate") == "required"
        and _spec_gate_decision(payload, "feasibility_gate") == "required"
    ):
        errors.append(
            "spec-contract.json cannot require design_gate and feasibility_gate at the same time until that combined route is wired"
        )
    semantic_delta = payload.get("semantic_delta")
    if isinstance(semantic_delta, list) and semantic_delta:
        workflow_state_path = feature_dir / "workflow-state.md"
        workflow_state = (
            workflow_state_path.read_text(encoding="utf-8", errors="replace")
            if workflow_state_path.is_file()
            else ""
        )
        review_state = _extract_markdown_section(workflow_state, "Review State")
        if (
            extract_field(review_state, "last_user_reviewed_artifact_state")
            != "approved"
        ):
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
        ui_brief_signaled = (
            bool(ui_brief_ref) or (feature_dir / "ui-brief.md").is_file()
        )
        for field in ("design_source_refs", "fidelity_refs", "validation_refs"):
            value = design_contract.get(field)
            if isinstance(value, list) and any(
                isinstance(item, str) and "ui-brief.md" in item for item in value
            ):
                ui_brief_signaled = True
        if ui_brief_signaled and ui_applicable is not True:
            errors.append(
                "spec-contract.json carries ui-brief.md but design_contract.ui_applicable is not true"
            )
        pending_design_route = _spec_gate_decision(payload, "design_gate") == "required"
        if pending_design_route and ui_applicable is not True:
            errors.append(
                "spec-contract.json design_gate.required requires design_contract.ui_applicable true"
            )
        if ui_applicable is True and pending_design_route:
            errors.extend(
                _validate_pending_spec_design_contract(feature_dir, design_contract)
            )
        elif ui_applicable is True:
            errors.extend(
                _validate_ui_contract_shape(
                    design_contract,
                    "spec-contract.json design_contract",
                )
            )
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
            if not isinstance(
                design_contract.get("entry_points"), list
            ) or not design_contract.get("entry_points"):
                errors.append(
                    "spec-contract.json UI work requires design_contract.entry_points"
                )
            if not isinstance(
                design_contract.get("visual_acceptance"), list
            ) or not design_contract.get("visual_acceptance"):
                errors.append(
                    "spec-contract.json UI work requires design_contract.visual_acceptance"
                )
            fidelity_mode = str(design_contract.get("fidelity_mode") or "none").strip()
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
    errors.extend(
        _validate_agent_transition(
            payload.get("transition"), "spec-contract.json transition"
        )
    )
    errors.extend(_validate_spec_entrypoint_outcome_contract(feature_dir))
    transition = payload.get("transition")
    if isinstance(transition, dict) and transition.get("status") == "ready":
        if (
            _spec_gate_decision(payload, "design_gate") == "required"
            and _spec_gate_decision(payload, "feasibility_gate") == "required"
        ):
            errors.append(
                "spec-contract.json cannot mark transition ready when design_gate and feasibility_gate are both required; resolve the combined route before Plan"
            )
        if not _spec_transition_next_action_allowed(
            payload, transition.get("next_action")
        ):
            errors.append(
                "spec-contract.json transition.next_action must be /sp.design with design_gate.required, otherwise /sp.plan when planning-ready"
            )

    artifact_refs = payload.get("artifact_refs")
    if isinstance(artifact_refs, dict):
        for name, relative_path in artifact_refs.items():
            if relative_path is None:
                if name == "spec":
                    errors.append(
                        "spec-contract.json artifact_refs.spec must not be null"
                    )
                continue
            if not isinstance(relative_path, str) or not relative_path.strip():
                errors.append(
                    f"spec-contract.json artifact_refs.{name} must be a path or null"
                )
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


def _validate_specify_draft_artifacts(
    feature_dir: Path, *, validate_lossless_state: bool = True
) -> list[str]:
    errors: list[str] = []
    if (feature_dir / "spec-contract.json").is_file():
        return _validate_spec_contract_artifacts(feature_dir)
    alignment_path = feature_dir / "alignment.md"
    context_path = feature_dir / "context.md"
    workflow_state_path = feature_dir / "workflow-state.md"
    workflow_state_content = workflow_state_path.read_text(
        encoding="utf-8", errors="replace"
    )

    if _is_legacy_specify_package(feature_dir, workflow_state_content):
        draft_path = feature_dir / "specify-draft.md"
        errors.extend(
            _validate_markdown_headings(
                draft_path, SPECIFY_LEGACY_DRAFT_REQUIRED_HEADINGS, "specify-draft.md"
            )
        )
        errors.extend(
            _validate_markdown_headings(
                alignment_path,
                SPECIFY_LEGACY_ALIGNMENT_REQUIRED_HEADINGS,
                "alignment.md",
            )
        )
        errors.extend(
            _validate_markdown_headings(
                context_path, SPECIFY_LEGACY_CONTEXT_REQUIRED_HEADINGS, "context.md"
            )
        )

        fixed_lifecycle_state = _extract_markdown_section(
            workflow_state_content, "Fixed Lifecycle State"
        )
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
                errors.append(
                    f"workflow-state.md is missing Fixed Lifecycle State field: {field}"
                )

        for legacy_field in (
            "coverage_mode",
            "observer_status",
            "last_observer_pass",
            "draft_file",
        ):
            if re.search(
                rf"(?im)^\s*-\s*{re.escape(legacy_field)}\s*:", workflow_state_content
            ):
                errors.append(
                    f"workflow-state.md still uses legacy sp-specify state field: {legacy_field}"
                )

        if validate_lossless_state:
            errors.extend(
                _validate_brainstorming_json_artifact(
                    feature_dir, "brainstorming/facts.json", validate_unknowns=True
                )
            )
            errors.extend(
                _validate_brainstorming_json_artifact(
                    feature_dir, "brainstorming/route.json", validate_unknowns=False
                )
            )
            errors.extend(
                _validate_brainstorming_json_artifact(
                    feature_dir, "brainstorming/intent.json", validate_unknowns=False
                )
            )
            errors.extend(
                _validate_brainstorming_json_artifact(
                    feature_dir,
                    "brainstorming/complexity.json",
                    validate_unknowns=False,
                )
            )
            errors.extend(_validate_lossless_specify_state(feature_dir))

        handoff_payload, handoff_errors = _read_json_artifact(
            feature_dir / "brainstorming" / "handoff-to-specify.json",
            "brainstorming/handoff-to-specify.json",
        )
        if handoff_errors:
            errors.extend(handoff_errors)
        else:
            errors.extend(
                _validate_handoff_to_specify_payload(
                    handoff_payload, "brainstorming/handoff-to-specify.json"
                )
            )
            errors.extend(
                _validate_consequence_json_payload(
                    handoff_payload, "brainstorming/handoff-to-specify.json"
                )
            )
        return errors

    errors.extend(
        _validate_markdown_headings(
            alignment_path, SPECIFY_ALIGNMENT_REQUIRED_HEADINGS, "alignment.md"
        )
    )
    errors.extend(
        _validate_markdown_headings(
            context_path, SPECIFY_CONTEXT_REQUIRED_HEADINGS, "context.md"
        )
    )

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
    for field in (
        "last_user_reviewed_artifact_state",
        "source_files_read",
        "source_signal_disposition_status",
    ):
        value = extract_field(review_state, field)
        if not value.strip():
            errors.append(f"workflow-state.md is missing Review State field: {field}")

    for legacy_field in (
        "coverage_mode",
        "observer_status",
        "last_observer_pass",
        "draft_file",
    ):
        if re.search(
            rf"(?im)^\s*-\s*{re.escape(legacy_field)}\s*:", workflow_state_content
        ):
            errors.append(
                f"workflow-state.md still uses legacy sp-specify state field: {legacy_field}"
            )

    handoff_payload, handoff_errors = _read_json_artifact(
        feature_dir / "brainstorming" / "handoff-to-specify.json",
        "brainstorming/handoff-to-specify.json",
    )
    if handoff_errors:
        errors.extend(handoff_errors)
    else:
        errors.extend(
            _validate_handoff_to_specify_payload(
                handoff_payload, "brainstorming/handoff-to-specify.json"
            )
        )
        errors.extend(
            _validate_consequence_json_payload(
                handoff_payload, "brainstorming/handoff-to-specify.json"
            )
        )

    if validate_lossless_state:
        legacy_paths = (
            "brainstorming/journal.ndjson",
            "brainstorming/stage-manifest.json",
            "brainstorming/facts.json",
            "brainstorming/route.json",
            "brainstorming/intent.json",
            "brainstorming/complexity.json",
        )
        if any(
            (feature_dir / relative_path).exists() for relative_path in legacy_paths
        ):
            errors.extend(_validate_lossless_specify_state(feature_dir))

    return errors


def _workflow_state_active_profile(feature_dir: Path) -> str:
    workflow_state_path = feature_dir / "workflow-state.md"
    if not workflow_state_path.exists() or not workflow_state_path.is_file():
        return ""
    workflow_state_content = workflow_state_path.read_text(
        encoding="utf-8", errors="replace"
    )
    match = re.search(
        r"(?im)^\s*-\s*active_profile\s*:\s*`?([^`\r\n]+)`?\s*$", workflow_state_content
    )
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


def validate_artifacts_hook(
    project_root: Path, payload: dict[str, object]
) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    if command_name not in REQUIRED_ARTIFACTS:
        raise QualityHookError(
            f"unsupported command_name '{command_name}' for workflow.artifacts.validate"
        )

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

    uses_runtime_deep_research = _deep_research_gate_contract_present(feature_dir)
    required_artifacts = REQUIRED_ARTIFACTS[command_name]
    required_files = FILE_REQUIRED_ARTIFACTS.get(command_name, ())
    if command_name == "deep-research" and not uses_runtime_deep_research:
        required_artifacts = DEEP_RESEARCH_LEGACY_REQUIRED_FILES
        required_files = DEEP_RESEARCH_LEGACY_REQUIRED_FILES
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
    if command_name == "implement":
        try:
            show_workflow(feature_dir)
        except MissingWorkflowState:
            pass
        except WorkflowRuntimeError as exc:
            return HookResult(
                event=WORKFLOW_ARTIFACTS_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[f"workflow state could not be validated: {exc}"],
                data={"feature_dir": str(feature_dir)},
            )
        except ValueError:
            # Legacy projects may still keep feature artifacts under specs/.
            # They have no unified .specify/features workflow state to inspect,
            # so retain the pre-runtime artifact validation path.
            pass
        else:
            if not (feature_dir / "implementation-handoff.json").is_file():
                missing.append("implementation-handoff.json")
    type_errors: list[str] = []
    if command_name == "plan":
        contract_paths = _consequence_contract_paths(feature_dir)
        if not any(path.exists() for path, _label in contract_paths):
            missing.append("plan-contract.json or plan/plan-contract.json")
        for path, label in contract_paths:
            if path.exists() and not path.is_file():
                type_errors.append(f"required artifact must be a file: {label}")
    for relative_path in required_files:
        target = feature_dir / relative_path
        if target.exists() and not target.is_file():
            type_errors.append(f"required artifact must be a file: {relative_path}")
    for relative_path in DIRECTORY_REQUIRED_ARTIFACTS.get(command_name, ()):
        target = feature_dir / relative_path
        if target.exists() and not target.is_dir():
            type_errors.append(
                f"required artifact must be a directory: {relative_path}"
            )
    if command_name == "constitution":
        constitution_path = project_root / ".specify" / "memory" / "constitution.md"
        if not constitution_path.exists():
            missing.append(".specify/memory/constitution.md")
    legacy_lossless_missing = (
        command_name == "specify"
        and (feature_dir / "brainstorming" / "legacy-state.json").exists()
        and not missing
        and not type_errors
        and any(
            not (feature_dir / name).exists()
            for name in SPECIFY_LOSSLESS_REQUIRED_ARTIFACTS
        )
    )
    if missing or type_errors:
        if not legacy_lossless_missing:
            return HookResult(
                event=WORKFLOW_ARTIFACTS_VALIDATE,
                status="blocked",
                severity="critical",
                errors=[
                    *([f"missing required artifact: {name}" for name in missing]),
                    *type_errors,
                ],
                data={"feature_dir": str(feature_dir)},
            )
    validation_errors: list[str] = []
    if command_name == "specify":
        validation_errors.extend(
            _validate_specify_draft_artifacts(
                feature_dir, validate_lossless_state=not legacy_lossless_missing
            )
        )
        validation_errors.extend(_validate_reference_implementation_spec(feature_dir))
    if command_name == "deep-research":
        if uses_runtime_deep_research:
            validation_errors.extend(
                _validate_runtime_deep_research_artifact(project_root, feature_dir)
            )
        else:
            validation_errors.extend(_validate_deep_research_artifact(feature_dir))
    if command_name == "plan":
        if uses_runtime_deep_research:
            validation_errors.extend(
                _validate_plan_deep_research_binding(project_root, feature_dir)
            )
        else:
            validation_errors.extend(_validate_plan_consumes_deep_research(feature_dir))
        validation_errors.extend(_validate_plan_test_design_gate(feature_dir))
        validation_errors.extend(_validate_plan_consequence_contract(feature_dir))
        validation_errors.extend(
            _validate_plan_entrypoint_outcome_contract(feature_dir)
        )
        validation_errors.extend(_validate_plan_ui_contract(feature_dir))
        validation_errors.extend(_validate_plan_human_acceptance_contract(feature_dir))
    if command_name == "tasks":
        validation_errors.extend(_validate_tasks_consequence_contract(feature_dir))
        validation_errors.extend(
            _validate_tasks_entrypoint_outcome_contract(feature_dir)
        )
        validation_errors.extend(_validate_tasks_ui_contract(feature_dir))
        validation_errors.extend(_validate_tasks_human_acceptance_contract(feature_dir))
    if command_name == "implement":
        if any(
            path.is_file()
            for path in (
                feature_dir / "spec-contract.json",
                feature_dir / "plan-contract.json",
                feature_dir / "plan" / "plan-contract.json",
                feature_dir / "task-index.json",
            )
        ):
            validation_errors.extend(
                _validate_tasks_human_acceptance_contract(feature_dir)
            )
        validation_errors.extend(
            _validate_packetized_implement_review_artifacts(feature_dir)
        )
        try:
            workflow = show_workflow(feature_dir)
        except (MissingWorkflowState, ValueError):
            workflow = None
        except WorkflowRuntimeError as exc:
            validation_errors.append(f"workflow state could not be validated: {exc}")
            workflow = None
        if workflow is not None:
            from specify_cli.implement_audit import audit_implement_resume
            from specify_cli.review_runtime import (
                implementation_handoff_completion_errors,
            )

            audit = audit_implement_resume(project_root, feature_dir)
            if audit.get("status") in {"fail", "conflict"} or not audit.get(
                "trusted_terminal_state", False
            ):
                gaps = [
                    str(item)
                    for item in audit.get("open_gaps", [])
                    if str(item).strip()
                ]
                validation_errors.append(
                    "Implement stage completion requires a trusted resume audit"
                    + (": " + "; ".join(gaps) if gaps else "")
                )
            workflow_data = workflow.get("data")
            if not isinstance(workflow_data, Mapping):
                validation_errors.append(
                    "Implement stage completion cannot read workflow ownership"
                )
            elif workflow_data.get("stage") != "implement" or workflow_data.get(
                "status"
            ) not in {"active", "completed"}:
                validation_errors.append(
                    "Implement artifact validation requires active or completed "
                    "Implement workflow ownership"
                )
            else:
                revision = workflow_data.get("revision")
                if isinstance(revision, bool) or not isinstance(revision, int):
                    validation_errors.append(
                        "Implement workflow revision must be an integer"
                    )
                else:
                    expected_review_revision = revision + (
                        2 if workflow_data.get("status") == "active" else 1
                    )
                    validation_errors.extend(
                        implementation_handoff_completion_errors(
                            project_root,
                            feature_dir,
                            expected_review_revision=expected_review_revision,
                        )
                    )
    if command_name == "review":
        from specify_cli.review_runtime import validate_review

        review = validate_review(project_root, feature_dir)
        validation_errors.extend(str(error) for error in review["errors"])
        state = review.get("state")
        if not isinstance(state, dict) or state.get("status") != "approved":
            validation_errors.append(
                "review-state.json status must be approved before stage completion"
            )
    if command_name == "accept":
        from specify_cli.human_acceptance import validate_human_acceptance

        acceptance = validate_human_acceptance(
            project_root,
            feature_dir,
            require_accepted=bool(payload.get("require_accepted", False)),
        )
        validation_errors.extend(str(error) for error in acceptance["errors"])
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
                require_heavy_scan_json=_workflow_state_mentions_heavy_prd_scan(
                    feature_dir
                ),
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


def validate_prd_build_readiness(run_dir: Path) -> list[str]:
    """Return semantic scan-package blockers before PRD export synthesis."""

    scan_errors = _validate_prd_scan_artifacts(
        run_dir,
        require_heavy_scan_json=True,
    )
    if scan_errors:
        return scan_errors
    return _validate_prd_build_input_contracts(run_dir)
