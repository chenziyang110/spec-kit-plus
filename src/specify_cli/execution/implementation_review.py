"""Embedded implementation review records and repair helpers."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field, fields
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
TaskReviewSpecVerdict = Literal["pass", "fail", "cannot_verify_from_diff"]
TaskReviewQualityVerdict = Literal["pass", "fail", "concerns"]
TaskReviewFindingCategory = Literal[
    "spec",
    "quality",
    "evidence",
    "ui_fidelity",
    "plan_mandated_defect",
]
TaskReviewFindingDisposition = Literal["open", "fixed", "accepted_residual_risk", "follow_up"]
TaskReviewUiFidelityResult = Literal[
    "not_applicable",
    "pass",
    "fail",
    "needs_visual_or_human_review",
]
TaskReviewFinalAssessment = Literal["accepted", "fixes_required", "controller_check_required"]
TaskReviewFindingSource = Literal["findings", "plan_mandated_defects"]
TaskLedgerStatus = Literal[
    "pending",
    "brief_written",
    "worker_done",
    "review_package_written",
    "review_pending",
    "fixes_required",
    "controller_check_required",
    "accepted",
    "blocked",
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

WORKFLOW_STATE_REVIEW_ALLOWED_NEXT_COMMANDS = frozenset(
    {
        "/sp.implement",
        "/sp.debug",
        "/sp.tasks",
        "/sp.plan",
        "/sp.clarify",
        "/sp.deep-research",
    }
)

SNAPSHOT_ALLOWED_EXACT_PATHS = frozenset(
    {
        "tasks.md",
        "task-index.json",
        "handoff-to-implement.json",
        "implement-tracker.md",
        "workflow-state.md",
    }
)

SNAPSHOT_ALLOWED_DIRECTORIES = frozenset(
    {
        "task-packets",
        "worker-results",
    }
)


TASK_ID_RE = re.compile(r"^T(?P<number>\d+)$")
SNAPSHOT_TOKEN_RE = re.compile(r"[^A-Za-z0-9_.-]+")


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


@dataclass(slots=True)
class TaskReviewFinding:
    severity: ReviewSeverity
    category: TaskReviewFindingCategory
    file: str
    line: int
    summary: str
    required_fix: str
    disposition: TaskReviewFindingDisposition = "open"


@dataclass(slots=True)
class ControllerCheck:
    check: str
    reason: str
    evidence_required: str


@dataclass(slots=True)
class AcceptedResidualRisk:
    finding_index: int
    reason: str
    owner: str
    finding_source: TaskReviewFindingSource = "findings"


@dataclass(slots=True)
class FollowUpWork:
    finding_index: int
    description: str
    target: str
    finding_source: TaskReviewFindingSource = "findings"


@dataclass(slots=True)
class TaskReviewRecord:
    task_id: str
    spec_verdict: TaskReviewSpecVerdict
    quality_verdict: TaskReviewQualityVerdict
    findings: list[TaskReviewFinding] = field(default_factory=list)
    controller_checks: list[ControllerCheck] = field(default_factory=list)
    plan_mandated_defects: list[TaskReviewFinding] = field(default_factory=list)
    accepted_residual_risks: list[AcceptedResidualRisk] = field(default_factory=list)
    follow_up_work: list[FollowUpWork] = field(default_factory=list)
    ui_fidelity_result: TaskReviewUiFidelityResult = "not_applicable"
    final_assessment: TaskReviewFinalAssessment = "fixes_required"
    created_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class TaskLedgerEntry:
    task_id: str
    status: TaskLedgerStatus
    task_brief: str = ""
    worker_result: str = ""
    review_package: str = ""
    task_review: str = ""
    controller_checks_open: list[str] = field(default_factory=list)
    controller_checks_closed: list[str] = field(default_factory=list)
    last_evidence: list[str] = field(default_factory=list)


def implementation_review_root(feature_dir: Path) -> Path:
    return feature_dir / "implementation-review"


def reviews_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "reviews.ndjson"


def repairs_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "repairs.ndjson"


def snapshots_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "snapshots"


def task_briefs_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "task-briefs"


def review_packages_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "review-packages"


def task_reviews_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "task-reviews"


def _validate_task_artifact_id(task_id: str) -> str:
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError(f"invalid task_id for implementation review artifact path: {task_id}")
    return task_id


def task_brief_path(feature_dir: Path, task_id: str) -> Path:
    return task_briefs_dir(feature_dir) / f"{_validate_task_artifact_id(task_id)}.md"


def review_package_path(feature_dir: Path, task_id: str) -> Path:
    return review_packages_dir(feature_dir) / f"{_validate_task_artifact_id(task_id)}.md"


def task_review_path(feature_dir: Path, task_id: str) -> Path:
    return task_reviews_dir(feature_dir) / f"{_validate_task_artifact_id(task_id)}.json"


def ledger_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "ledger.json"


def branch_review_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "branch-review.md"


def implementation_review_record_payload(record: ImplementationReviewRecord) -> dict[str, object]:
    return asdict(record)


def implementation_repair_record_payload(record: ImplementationRepairRecord) -> dict[str, object]:
    return asdict(record)


def task_review_record_payload(record: TaskReviewRecord) -> dict[str, object]:
    return asdict(record)


def task_ledger_payload(entries: list[TaskLedgerEntry]) -> dict[str, list[dict[str, object]]]:
    return {"tasks": [asdict(entry) for entry in entries]}


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


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return path


def write_task_review_record(feature_dir: Path, record: TaskReviewRecord) -> Path:
    return _write_json(task_review_path(feature_dir, record.task_id), task_review_record_payload(record))


def write_task_ledger(feature_dir: Path, entries: list[TaskLedgerEntry]) -> Path:
    return _write_json(ledger_path(feature_dir), task_ledger_payload(entries))


def _field_names(dataclass_type: type[object]) -> set[str]:
    return {item.name for item in fields(dataclass_type)}


def _task_ledger_entry_from_payload(payload: dict[str, object]) -> TaskLedgerEntry:
    allowed = _field_names(TaskLedgerEntry)
    return TaskLedgerEntry(**{key: value for key, value in payload.items() if key in allowed})  # type: ignore[arg-type]


def load_task_ledger(feature_dir: Path) -> list[TaskLedgerEntry]:
    path = ledger_path(feature_dir)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        raise ValueError(f"{path} must contain a JSON object with a tasks array")
    entries: list[TaskLedgerEntry] = []
    for item in payload["tasks"]:
        if not isinstance(item, dict):
            raise ValueError(f"{path} contains a non-object ledger entry")
        entries.append(_task_ledger_entry_from_payload(item))
    return entries


def task_review_acceptance_errors(record: TaskReviewRecord) -> list[str]:
    errors: list[str] = []

    if record.spec_verdict == "fail":
        errors.append("spec_verdict fail blocks acceptance")
    if record.quality_verdict == "fail":
        errors.append("quality_verdict fail blocks acceptance")
    if record.quality_verdict == "concerns" and not record.findings:
        errors.append("quality concerns require findings")

    accepted_residual_risk_refs = {
        (risk.finding_source, risk.finding_index) for risk in record.accepted_residual_risks
    }
    follow_up_refs = {(work.finding_source, work.finding_index) for work in record.follow_up_work}
    review_findings = [
        ("findings", "finding", index, finding) for index, finding in enumerate(record.findings)
    ]
    review_findings.extend(
        ("plan_mandated_defects", "plan_mandated_defects", index, finding)
        for index, finding in enumerate(record.plan_mandated_defects)
    )
    findings_by_ref = {
        (source, index): finding for source, _label, index, finding in review_findings
    }
    for source, label, index, finding in review_findings:
        if source == "plan_mandated_defects" and finding.category != "plan_mandated_defect":
            errors.append(f"{label} {index} category must be plan_mandated_defect")
        if finding.disposition == "open":
            errors.append(f"{label} {index} is open")
        elif (
            finding.disposition == "accepted_residual_risk"
            and (source, index) not in accepted_residual_risk_refs
        ):
            errors.append(
                f"{label} {index} accepted_residual_risk has no matching accepted_residual_risks"
            )
        elif finding.disposition == "follow_up" and (source, index) not in follow_up_refs:
            errors.append(f"{label} {index} follow_up has no matching follow_up_work")

    for risk in record.accepted_residual_risks:
        target = findings_by_ref.get((risk.finding_source, risk.finding_index))
        if target is None:
            errors.append(
                "accepted_residual_risks references missing "
                f"{risk.finding_source} {risk.finding_index}"
            )
        elif target.disposition != "accepted_residual_risk":
            errors.append(
                "accepted_residual_risks references "
                f"{risk.finding_source} {risk.finding_index} with disposition {target.disposition}"
            )
    for work in record.follow_up_work:
        target = findings_by_ref.get((work.finding_source, work.finding_index))
        if target is None:
            errors.append(
                f"follow_up_work references missing {work.finding_source} {work.finding_index}"
            )
        elif target.disposition != "follow_up":
            errors.append(
                "follow_up_work references "
                f"{work.finding_source} {work.finding_index} with disposition {target.disposition}"
            )

    if record.ui_fidelity_result == "fail":
        errors.append("ui_fidelity_result fail blocks acceptance")
    elif record.ui_fidelity_result == "needs_visual_or_human_review":
        errors.append("needs_visual_or_human_review cannot be accepted")

    if record.spec_verdict == "cannot_verify_from_diff":
        if not record.controller_checks:
            errors.append("cannot_verify_from_diff requires controller checks")
        if record.final_assessment != "controller_check_required":
            errors.append("cannot_verify_from_diff requires final_assessment=controller_check_required")
        if record.final_assessment == "accepted":
            errors.append(
                "cannot_verify_from_diff cannot be accepted; convert to pass after controller evidence closes"
            )

    if record.final_assessment == "accepted" and record.controller_checks:
        errors.append("accepted assessment cannot have open controller checks")

    return errors


def task_review_is_accepted(record: TaskReviewRecord) -> bool:
    return record.final_assessment == "accepted" and not task_review_acceptance_errors(record)


def _snapshot_name(relative_path: str, review_id: str) -> str:
    source = Path(relative_path)
    suffix = source.suffix
    stem = source.as_posix().replace("/", "__")
    if suffix:
        stem = stem[: -len(suffix)]
    safe_review_id = SNAPSHOT_TOKEN_RE.sub("_", review_id).strip("._-") or "review"
    return f"{stem}.before-{safe_review_id}{suffix}"


def _safe_snapshot_relative_path(relative_path: str) -> Path | None:
    source = Path(relative_path)
    if source.is_absolute():
        return None
    if any(part in {"", ".", ".."} for part in source.parts):
        return None
    normalized = source.as_posix()
    if normalized in SNAPSHOT_ALLOWED_EXACT_PATHS:
        return source
    if (
        len(source.parts) == 2
        and source.parts[0] in SNAPSHOT_ALLOWED_DIRECTORIES
        and source.suffix == ".json"
    ):
        return source
    return None


def snapshot_artifacts(feature_dir: Path, *, review_id: str, relative_paths: list[str]) -> list[str]:
    output_dir = snapshots_dir(feature_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_root = output_dir.resolve(strict=False)
    copied: list[str] = []
    feature_root = feature_dir.resolve(strict=False)
    for relative_path in relative_paths:
        safe_relative_path = _safe_snapshot_relative_path(relative_path)
        if safe_relative_path is None:
            continue
        source = (feature_dir / safe_relative_path).resolve(strict=False)
        try:
            source.relative_to(feature_root)
        except ValueError:
            continue
        if not source.exists() or not source.is_file():
            continue
        target = output_dir / _snapshot_name(relative_path, review_id)
        try:
            target.resolve(strict=False).relative_to(output_root)
        except ValueError:
            continue
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
        elif key == "next_command":
            next_command = after.get(key)
            if next_command not in WORKFLOW_STATE_REVIEW_ALLOWED_NEXT_COMMANDS:
                errors.append(f"{key} has invalid embedded review route: {next_command}")
    return errors
