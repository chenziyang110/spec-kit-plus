"""Embedded implementation review records and repair helpers."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


ReviewScope = Literal["pre-implement", "join-point-drift", "sequential-window"]
ReviewDecision = Literal[
    "cleared",
    "repair-and-continue",
    "repair-and-rerun-current-window",
    "blocked-reopen-tasks",
    "blocked-reopen-plan",
    "blocked-reopen-clarify",
    "blocked-deep-research",
    "debug-required",
]
ImplementationFindingType = Literal[
    "missing_task",
    "stale_task",
    "wrong_dependency",
    "write_set_conflict",
    "missing_validation",
    "packet_field_gap",
    "join_point_gap",
    "task_order_gap",
    "implementation_gap",
    "failed_validation",
    "worker_handoff_concern",
    "consumer_wiring_gap",
    "real_entrypoint_evidence_gap",
    "spec_goal_conflict",
    "plan_architecture_conflict",
    "scope_change_required",
    "must_preserve_conflict",
    "consequence_obligation_conflict",
    "unproven_implementation_chain",
    "user_decision_required",
]
ReviewSeverity = Literal["critical", "high", "medium", "low"]
RepairOperation = Literal[
    "insert_task",
    "update_task",
    "supersede_task",
    "update_dependency",
    "regenerate_packet",
    "insert_repair_task",
    "update_tracker",
    "update_handoff",
]


WORKFLOW_STATE_REVIEW_ALLOWED_KEYS = frozenset(
    {
        "review_gate",
        "review_window_policy",
        "implementation_review",
        "next_action",
        "next_command",
        "blocker_reason",
        "blocked_reason",
    }
)


TASK_ID_RE = re.compile(r"^T(?P<number>\d+)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ImplementationReviewFinding:
    finding_id: str
    finding_type: ImplementationFindingType
    severity: ReviewSeverity
    summary: str
    affected_artifacts: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    repairable_at_task_layer: bool = False
    recommendation: str = ""
    upstream_reentry: str = ""


@dataclass(slots=True)
class ImplementationReviewRecord:
    review_id: str
    scope: ReviewScope
    trigger: str
    decision: ReviewDecision
    reviewed_tasks: list[str] = field(default_factory=list)
    remaining_tasks: list[str] = field(default_factory=list)
    findings: list[ImplementationReviewFinding] = field(default_factory=list)
    next_action: str = ""
    created_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class ImplementationRepairOperation:
    operation: RepairOperation
    task_id: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ImplementationRepairRecord:
    repair_id: str
    source_review_id: str
    changed_artifacts: list[str]
    operations: list[ImplementationRepairOperation]
    completed_tasks_preserved: bool
    next_batch: str
    created_at: str = field(default_factory=_utc_now)


def implementation_review_root(feature_dir: Path) -> Path:
    return feature_dir / "implementation-review"


def reviews_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "reviews.ndjson"


def repairs_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "repairs.ndjson"


def snapshots_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "snapshots"


def implementation_review_record_payload(record: ImplementationReviewRecord) -> dict[str, object]:
    return asdict(record)


def implementation_repair_record_payload(record: ImplementationRepairRecord) -> dict[str, object]:
    return asdict(record)


def _append_json_line(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
    return path


def write_review_record(feature_dir: Path, record: ImplementationReviewRecord) -> Path:
    return _append_json_line(reviews_path(feature_dir), implementation_review_record_payload(record))


def write_repair_record(feature_dir: Path, record: ImplementationRepairRecord) -> Path:
    return _append_json_line(repairs_path(feature_dir), implementation_repair_record_payload(record))


def _snapshot_name(relative_path: str, review_id: str) -> str:
    source = Path(relative_path)
    suffix = source.suffix
    stem = source.as_posix().replace("/", "__")
    if suffix:
        stem = stem[: -len(suffix)]
    return f"{stem}.before-{review_id}{suffix}"


def snapshot_artifacts(feature_dir: Path, *, review_id: str, relative_paths: list[str]) -> list[str]:
    output_dir = snapshots_dir(feature_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for relative_path in relative_paths:
        source = feature_dir / relative_path
        if not source.exists() or not source.is_file():
            continue
        target = output_dir / _snapshot_name(relative_path, review_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target.relative_to(feature_dir).as_posix())
    return copied


def next_append_task_id(task_ids: list[str]) -> str:
    max_value = 0
    width = 3
    for task_id in task_ids:
        match = TASK_ID_RE.match(task_id.strip())
        if not match:
            continue
        number_text = match.group("number")
        max_value = max(max_value, int(number_text))
        width = max(width, len(number_text))
    return f"T{max_value + 1:0{width}d}"


def validate_workflow_state_review_update(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    keys = set(before) | set(after)
    for key in sorted(keys):
        if before.get(key) == after.get(key):
            continue
        if key not in WORKFLOW_STATE_REVIEW_ALLOWED_KEYS:
            errors.append(f"{key} is protected for embedded review")
    return errors
