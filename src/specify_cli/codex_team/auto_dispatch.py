"""Deterministic routing of ready parallel batches into the Codex team runtime."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Iterable

from specify_cli.codex_team import task_ops
from specify_cli.codex_team.state_paths import (
    codex_team_state_root,
    dispatch_record_path,
    runtime_session_path,
    task_record_path,
    worker_heartbeat_path,
)
from specify_cli.codex_team.runtime_bridge import (
    dispatch_runtime_task,
    ensure_codex_team_executor_available,
    ensure_codex_team_runtime_prerequisites,
    submit_runtime_result,
)
from specify_cli.codex_team.baseline_check import classify_baseline_build_status
from specify_cli.codex_team.runtime_state import batch_record_payload
from specify_cli.codex_team.session_ops import monitor_summary, resume_session
from specify_cli.codex_team.worktree_ops import worker_worktree_path
from specify_cli.codex_team.state_paths import batch_record_path
from specify_cli.orchestration import CapabilitySnapshot, describe_delegation_surface
from specify_cli.orchestration.backends.process_backend import ProcessBackend
from specify_cli.orchestration.policy import classify_batch_execution_policy
from specify_cli.orchestration.policy import classify_review_gate_policy
from specify_cli.orchestration.state_store import write_json
from specify_cli.execution import (
    build_result_handoff_path,
    compile_worker_task_packet,
    normalize_worker_task_result_payload,
    render_packet_summary,
    validate_worker_task_result,
    worker_task_packet_from_json,
)
from specify_cli.workflow_markers import has_agent_marker, has_parallel_marker, strip_known_markers


TASK_LINE_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<task_id>T\d+)(?P<rest>.*)$")
PARALLEL_BATCH_RE = re.compile(r"^\*\*(?P<name>Parallel Batch [^*]+)\*\*$")
JOIN_POINT_RE = re.compile(r"^\*\*(?P<name>Join Point [^*]+)\*\*")
INLINE_TASK_ID_RE = re.compile(r"`(T\d+)`")
TRACKER_CURRENT_BATCH_RE = re.compile(r"(?m)^current_batch:\s*(?P<value>.+?)\s*$")
SECTION_RE = re.compile(r"(?ms)^#{2,3}\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#{2,3}\s+|\Z)")
MATERIALIZED_TASK_RE = re.compile(r"^\s*-\s+(?P<task_id>[A-Za-z0-9_-]+)\s+(?P<summary>.+?)\s*$")
RESULT_START_MARKER = "BEGIN_WORKER_TASK_RESULT_JSON"
RESULT_END_MARKER = "END_WORKER_TASK_RESULT_JSON"
PACKAGE_SRC_ROOT = Path(__file__).resolve().parents[2]


class AutoDispatchError(RuntimeError):
    """Base exception for ready-batch auto dispatch failures."""


class AutoDispatchUnavailableError(AutoDispatchError):
    """Raised when the runtime backend is unavailable."""


@dataclass(slots=True)
class ParsedTask:
    task_id: str
    completed: bool
    parallel: bool
    agent_required: bool
    summary: str
    order_index: int


@dataclass(slots=True)
class ParsedParallelBatch:
    batch_name: str
    task_ids: list[str]
    join_point_name: str = ""


@dataclass(slots=True)
class ParsedTasksDocument:
    tasks: list[ParsedTask]
    parallel_batches: list[ParsedParallelBatch]


@dataclass(slots=True)
class MaterializedTask:
    task_id: str
    summary: str
    task_body: str
    completed: bool = False
    parallel: bool = True
    agent_required: bool = True


@dataclass(slots=True)
class MaterializedBatch:
    batch_name: str
    join_point_name: str
    tasks: list[MaterializedTask]


@dataclass(slots=True)
class AutoDispatchResult:
    feature_dir: Path
    batch_id: str
    batch_name: str
    join_point_name: str
    dispatched_task_ids: list[str]
    request_ids: list[str]


@dataclass(slots=True)
class BatchCompletionResult:
    batch_id: str
    batch_name: str
    status: str
    join_point_name: str
    task_ids: list[str]
    next_batch_id: str = ""
    next_batch_name: str = ""
    next_dispatched_task_ids: list[str] | None = None
    next_batch_id: str = ""
    next_batch_name: str = ""
    next_dispatched_task_ids: list[str] | None = None


def _agent_teams_team_name(batch_id: str) -> str:
    token = sha1(batch_id.encode("utf-8")).hexdigest()[:10]
    return f"ct-{token}"


def _worker_result_template(packet: Any) -> dict[str, object]:
    return {
        "task_id": packet.task_id,
        "status": "pending",
        "changed_files": list(packet.scope.write_scope),
        "validation_results": [
            {
                "command": gate,
                "status": "skipped",
                "output": "NOT RUN - replace with actual command output after execution",
            }
            for gate in packet.validation_gates
        ],
        "summary": packet.objective,
        "concerns": [],
        "reported_status": "",
        "blockers": [],
        "failed_assumptions": [],
        "suggested_recovery_actions": [],
        "rule_acknowledgement": {
            "required_references_read": False,
            "forbidden_drift_respected": False,
            "context_bundle_read": False,
            "paths_read": [],
            "critical_notes": [
                "Replace the pending placeholder with the real RED/GREEN or validation evidence before returning success."
            ],
        },
    }


def _agent_teams_task_description(packet: Any, *, request_id: str) -> str:
    template = json.dumps(_worker_result_template(packet), ensure_ascii=False, indent=2)
    ordered_context = sorted(packet.context_bundle, key=lambda item: (item.read_order, item.path))
    lines = [
        f"Delegated task {packet.task_id}",
        f"Objective: {packet.objective}",
        "",
        "Execution context bundle (read before claiming work):",
        *[
            (
                f"{item.read_order}. {item.path} [{item.kind}] - {item.purpose}"
                + (f" (why: {item.selection_reason})" if item.selection_reason else "")
            )
            for item in ordered_context
        ],
        "",
        "Required implementation references:",
        *[f"- {reference.path}" for reference in packet.required_references],
        "",
        "Hard rules:",
        *[f"- {rule}" for rule in packet.hard_rules],
        "",
        "Forbidden implementation drift:",
        *[f"- {rule}" for rule in packet.forbidden_drift],
        "",
        "Validation gates:",
        *[f"- {gate}" for gate in packet.validation_gates],
        "",
        f"Canonical request id: {request_id}",
        "When you finish, put a machine-readable WorkerTaskResult JSON block in the task result text.",
        "Use the exact markers below and keep the JSON valid.",
        RESULT_START_MARKER,
        template,
        RESULT_END_MARKER,
        "",
        "Do not leave the placeholder JSON in a success state. Replace the pending/skipped/false placeholders with the real execution result.",
        "If this lane changes behavior, write the failing test first, verify the RED state, then rerun the same gate after the fix and report the GREEN evidence.",
        "If you are blocked or failed, keep the same JSON shape but set status to blocked/failed and fill blockers, failed_assumptions, and suggested_recovery_actions truthfully.",
        "Set changed_files to the files you actually changed and preserve rule_acknowledgement truthfully.",
        "Acknowledge the execution context bundle in `rule_acknowledgement` before you claim or complete the task.",
    ]
    return "\n".join(lines)


@dataclass(slots=True)
class PassiveParallelismLane:
    """A candidate unit of passive parallel work for higher-level command logic."""

    lane_id: str
    summary: str
    references: tuple[str, ...] = ()
    write_scopes: tuple[str, ...] = ()
    low_risk_preparation: bool = False


@dataclass(slots=True)
class PassiveParallelismRequest:
    """A conservative decision surface for non-runtime passive parallelism checks."""

    stage: str
    lanes: list[PassiveParallelismLane]
    tightly_coupled: bool = False
    scope_clear: bool = True


@dataclass(slots=True)
class PassiveParallelismDecision:
    """The reusable decision payload command-layer logic can inspect safely."""

    stage: str
    should_trigger: bool
    reason: str
    dispatch_payload: dict[str, object] | None = None


def _normalize_scope(scope: str) -> tuple[str, ...]:
    cleaned = scope.strip().strip("/")
    if not cleaned:
        return ()
    return tuple(part for part in cleaned.split("/") if part)


def _scopes_overlap(left: str, right: str) -> bool:
    left_parts = _normalize_scope(left)
    right_parts = _normalize_scope(right)
    if not left_parts or not right_parts:
        return False
    shared_length = min(len(left_parts), len(right_parts))
    return left_parts[:shared_length] == right_parts[:shared_length]


def write_scopes_overlap(lanes: Iterable[PassiveParallelismLane]) -> bool:
    """Return whether any two candidate lanes target overlapping write scopes."""

    normalized_lanes = list(lanes)
    for index, lane in enumerate(normalized_lanes):
        for other in normalized_lanes[index + 1 :]:
            if any(
                _scopes_overlap(left_scope, right_scope)
                for left_scope in lane.write_scopes
                for right_scope in other.write_scopes
            ):
                return True
    return False


def _passive_parallelism_payload(
    stage: str,
    lanes: Iterable[PassiveParallelismLane],
) -> dict[str, object]:
    return {
        "stage": stage,
        "lanes": [
            {
                "lane_id": lane.lane_id,
                "summary": lane.summary,
                "references": list(lane.references),
                "write_scopes": list(lane.write_scopes),
                "low_risk_preparation": lane.low_risk_preparation,
            }
            for lane in lanes
        ],
    }


def _lane_reference_sets(
    lanes: Iterable[PassiveParallelismLane],
) -> list[frozenset[str]]:
    return [
        frozenset(reference.strip() for reference in lane.references if reference.strip())
        for lane in lanes
    ]


def assess_passive_parallelism(
    request: PassiveParallelismRequest,
) -> PassiveParallelismDecision:
    """Assess whether passive parallelism is safe to consider for a stage.

    This helper is intentionally conservative and does not dispatch work. It only
    exposes a reusable policy surface for command-layer orchestration.
    """

    if len(request.lanes) < 2:
        return PassiveParallelismDecision(
            stage=request.stage,
            should_trigger=False,
            reason="insufficient_lanes",
        )

    if not request.scope_clear:
        return PassiveParallelismDecision(
            stage=request.stage,
            should_trigger=False,
            reason="unclear_scope",
        )

    if request.tightly_coupled:
        return PassiveParallelismDecision(
            stage=request.stage,
            should_trigger=False,
            reason="tightly_coupled",
        )

    if request.stage == "analysis":
        if any(lane.write_scopes for lane in request.lanes):
            return PassiveParallelismDecision(
                stage=request.stage,
                should_trigger=False,
                reason="analysis_has_write_scopes",
            )

        reference_sets = _lane_reference_sets(request.lanes)
        distinct_references = {reference for refs in reference_sets for reference in refs}
        if len(distinct_references) < 2:
            return PassiveParallelismDecision(
                stage=request.stage,
                should_trigger=False,
                reason="insufficient_references",
            )

        if len(set(reference_sets)) < len(reference_sets):
            return PassiveParallelismDecision(
                stage=request.stage,
                should_trigger=False,
                reason="duplicated_reference_sets",
            )

        return PassiveParallelismDecision(
            stage=request.stage,
            should_trigger=True,
            reason="multi_reference_analysis",
            dispatch_payload=_passive_parallelism_payload(request.stage, request.lanes),
        )

    if request.stage == "enhancement":
        if any(not lane.low_risk_preparation for lane in request.lanes):
            return PassiveParallelismDecision(
                stage=request.stage,
                should_trigger=False,
                reason="unsafe_preparation",
            )
        if any(not lane.write_scopes for lane in request.lanes):
            return PassiveParallelismDecision(
                stage=request.stage,
                should_trigger=False,
                reason="missing_write_scopes",
            )

        if write_scopes_overlap(request.lanes):
            return PassiveParallelismDecision(
                stage=request.stage,
                should_trigger=False,
                reason="overlapping_write_scopes",
            )

        return PassiveParallelismDecision(
            stage=request.stage,
            should_trigger=True,
            reason="independent_capability_planning",
            dispatch_payload=_passive_parallelism_payload(request.stage, request.lanes),
        )

    return PassiveParallelismDecision(
        stage=request.stage,
        should_trigger=False,
        reason="unsupported_stage",
    )


def parse_tasks_markdown(tasks_path: Path) -> ParsedTasksDocument:
    """Parse task records and explicit parallel batches from tasks.md."""
    tasks: list[ParsedTask] = []
    parallel_batches: list[ParsedParallelBatch] = []
    current_batch: ParsedParallelBatch | None = None

    for raw_line in tasks_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        task_match = TASK_LINE_RE.match(line)
        if task_match:
            rest = task_match.group("rest")
            tasks.append(
                ParsedTask(
                    task_id=task_match.group("task_id"),
                    completed=task_match.group("mark").lower() == "x",
                    parallel=has_parallel_marker(rest),
                    agent_required=has_agent_marker(rest),
                    summary=strip_known_markers(rest),
                    order_index=len(tasks),
                )
            )
            continue

        batch_match = PARALLEL_BATCH_RE.match(line)
        if batch_match:
            current_batch = ParsedParallelBatch(batch_name=batch_match.group("name"), task_ids=[])
            parallel_batches.append(current_batch)
            continue

        if current_batch is not None:
            join_match = JOIN_POINT_RE.match(line)
            if join_match:
                current_batch.join_point_name = join_match.group("name")
                current_batch = None
                continue
            task_ids = INLINE_TASK_ID_RE.findall(line)
            if task_ids:
                current_batch.task_ids.extend(task_ids)

    return ParsedTasksDocument(tasks=tasks, parallel_batches=parallel_batches)


def _overlay_task_record_statuses(project_root: Path, parsed: ParsedTasksDocument) -> ParsedTasksDocument:
    """Overlay persisted task-record terminal status onto parsed tasks.md state."""
    updated_tasks: list[ParsedTask] = []
    for task in parsed.tasks:
        try:
            record = task_ops.get_task(project_root, task.task_id)
        except task_ops.TaskOpsError:
            updated_tasks.append(task)
            continue

        updated_tasks.append(
            ParsedTask(
                task_id=task.task_id,
                completed=record.status == task_ops.TASK_STATUS_COMPLETED,
                parallel=task.parallel,
                agent_required=task.agent_required,
                summary=task.summary,
                order_index=task.order_index,
            )
        )

    return ParsedTasksDocument(tasks=updated_tasks, parallel_batches=parsed.parallel_batches)


def _extract_tracker_scalar(text: str, key: str) -> str:
    pattern = TRACKER_CURRENT_BATCH_RE if key == "current_batch" else re.compile(
        rf"(?m)^{re.escape(key)}:\s*(?P<value>.+?)\s*$"
    )
    match = pattern.search(text)
    return match.group("value").strip() if match else ""


def _candidate_phase_plan_paths(feature_dir: Path) -> list[Path]:
    patterns = ("phase*.md", "*phase*.md", "*refactor-plan*.md")
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(path for path in feature_dir.glob(pattern) if path.is_file())
    unique: dict[Path, None] = {}
    for candidate in candidates:
        unique[candidate] = None
    return list(unique.keys())


def _section_body(text: str, title: str) -> str:
    normalized_title = title.strip().lower()
    for match in SECTION_RE.finditer(text):
        heading = match.group("title").strip().lower()
        if heading == normalized_title or heading == f"batch {normalized_title}":
            return match.group("body").strip()
    return ""


def _materialized_tasks_from_phase_plan(phase_plan: Path, batch_name: str) -> list[MaterializedTask]:
    body = _section_body(phase_plan.read_text(encoding="utf-8"), batch_name)
    if not body:
        return []

    tasks: list[MaterializedTask] = []
    for raw_line in body.splitlines():
        match = MATERIALIZED_TASK_RE.match(raw_line)
        if not match:
            continue
        task_id = match.group("task_id").strip()
        summary = match.group("summary").strip()
        tasks.append(
            MaterializedTask(
                task_id=task_id,
                summary=summary,
                task_body=summary,
            )
        )
    return tasks


def materialize_runtime_batch(feature_dir: Path) -> MaterializedBatch:
    """Build a runtime batch from tracker/phase-plan state before falling back to tasks.md."""
    tracker_path = feature_dir / "implement-tracker.md"
    if tracker_path.exists():
        tracker_text = tracker_path.read_text(encoding="utf-8")
        current_batch = _extract_tracker_scalar(tracker_text, "current_batch")
        if current_batch:
            for phase_plan in _candidate_phase_plan_paths(feature_dir):
                tasks = _materialized_tasks_from_phase_plan(phase_plan, current_batch)
                if tasks:
                    return MaterializedBatch(
                        batch_name=current_batch,
                        join_point_name=f"{current_batch}-join",
                        tasks=tasks,
                    )

    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.exists():
        raise AutoDispatchError(f"tasks.md not found in {feature_dir}")

    parsed = _overlay_task_record_statuses(feature_dir.parents[1], parse_tasks_markdown(tasks_path))
    batch = find_next_ready_parallel_batch(parsed)
    if batch is None:
        raise AutoDispatchError("no ready parallel batch found")

    tasks_by_id = {task.task_id: task for task in parsed.tasks}
    return MaterializedBatch(
        batch_name=batch.batch_name,
        join_point_name=batch.join_point_name,
        tasks=[
            MaterializedTask(
                task_id=task_id,
                summary=tasks_by_id[task_id].summary,
                task_body=tasks_by_id[task_id].summary,
                completed=tasks_by_id[task_id].completed,
                parallel=tasks_by_id[task_id].parallel,
                agent_required=tasks_by_id[task_id].agent_required,
            )
            for task_id in batch.task_ids
        ],
    )


def find_next_ready_parallel_batch(parsed: ParsedTasksDocument) -> ParsedParallelBatch | None:
    """Return the first explicit or inferred parallel batch whose prerequisites are complete.

    Prefers explicit batches defined by **Parallel Batch** headers.
    Falls back to grouping adjacent ready [P] tasks into an inferred batch.
    """
    tasks_by_id = {task.task_id: task for task in parsed.tasks}

    # 1. Try explicit batches first
    for batch in parsed.parallel_batches:
        unknown_task_ids = [task_id for task_id in batch.task_ids if task_id not in tasks_by_id]
        if unknown_task_ids:
            unknown_text = ", ".join(unknown_task_ids)
            raise AutoDispatchError(
                f"explicit batch {batch.batch_name} references unknown task ids: {unknown_text}"
            )

        members = [tasks_by_id[task_id] for task_id in batch.task_ids]
        pending_members = [task for task in members if not task.completed]
        if not pending_members:
            continue

        last_pending_index = max(task.order_index for task in pending_members)
        blocked = any(
            not task.completed and task.task_id not in batch.task_ids
            for task in parsed.tasks
            if task.order_index < last_pending_index
        )
        if blocked:
            continue
        return batch

    # 2. Try inferred batches (adjacent ready tasks with [P] marker)
    ready_p_tasks = []
    for task in parsed.tasks:
        if task.completed:
            continue

        # Check if prerequisites are complete (all tasks before this one must be done or in this batch)
        is_blocked = any(
            not prev.completed and prev.task_id not in [t.task_id for t in ready_p_tasks]
            for prev in parsed.tasks
            if prev.order_index < task.order_index
        )

        if not is_blocked and task.parallel:
            ready_p_tasks.append(task)
        elif ready_p_tasks:
            # We hit a sequential/blocked task, stop and return the batch if it has > 1 task
            if len(ready_p_tasks) >= 2:
                break
            ready_p_tasks = []

    if len(ready_p_tasks) >= 2:
        return ParsedParallelBatch(
            batch_name=f"Inferred Batch {ready_p_tasks[0].task_id}-{ready_p_tasks[-1].task_id}",
            task_ids=[t.task_id for t in ready_p_tasks],
            join_point_name="Inferred Join Point",
        )

    return None


def _slugify_batch_name(batch_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", batch_name.lower()).strip("-")


def _request_id_for(session_id: str, batch_name: str, task_id: str) -> str:
    return f"{session_id}-{_slugify_batch_name(batch_name)}-{task_id.lower()}"


def _batch_id_for(session_id: str, batch_name: str) -> str:
    return f"{session_id}-{_slugify_batch_name(batch_name)}"


def _write_batch_record(
    project_root: Path,
    *,
    batch_id: str,
    batch_name: str,
    session_id: str,
    feature_dir: Path,
    task_ids: list[str],
    request_ids: list[str],
    join_point_name: str,
    batch_classification: str,
    safe_preparation: bool,
    review_required: bool,
    peer_review_lane_recommended: bool,
    review_reason: str,
    review_status: str,
) -> None:
    path = batch_record_path(project_root, batch_id)
    write_json(
        path,
        batch_record_payload(
            batch_id=batch_id,
            batch_name=batch_name,
            session_id=session_id,
            feature_dir=feature_dir.as_posix(),
            task_ids=task_ids,
            request_ids=request_ids,
            join_point_name=join_point_name,
            batch_classification=batch_classification,
            safe_preparation=safe_preparation,
            review_required=review_required,
            peer_review_lane_recommended=peer_review_lane_recommended,
            review_reason=review_reason,
            review_status=review_status,
        ),
    )


def _load_batch_record(project_root: Path, batch_id: str) -> dict[str, object]:
    path = batch_record_path(project_root, batch_id)
    if not path.exists():
        raise AutoDispatchError(f"batch {batch_id} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _cleanup_partial_dispatch_state(
    project_root: Path,
    *,
    session_id: str,
    original_session_payload: dict[str, object] | None,
    request_ids: Iterable[str],
    packet_paths: Iterable[Path],
    result_paths: Iterable[Path],
    created_task_ids: Iterable[str],
) -> None:
    for request_id in request_ids:
        dispatch_record_path(project_root, request_id).unlink(missing_ok=True)

    for path in packet_paths:
        path.unlink(missing_ok=True)

    for path in result_paths:
        path.unlink(missing_ok=True)

    for task_id in created_task_ids:
        task_record_path(project_root, task_id).unlink(missing_ok=True)

    if original_session_payload is not None:
        write_json(runtime_session_path(project_root, session_id), original_session_payload)
        monitor_summary(project_root, session_id=session_id)


def _load_expected_dispatch_records(
    project_root: Path,
    *,
    task_ids: list[str],
    request_ids: list[str],
) -> dict[str, dict[str, object]]:
    dispatch_by_task_id: dict[str, dict[str, object]] = {}

    for request_id in request_ids:
        dispatch_path = dispatch_record_path(project_root, request_id)
        if not dispatch_path.exists():
            raise AutoDispatchError(f"dispatch record for request {request_id} is missing")

        try:
            dispatch_payload = json.loads(dispatch_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AutoDispatchError(f"dispatch record for request {request_id} is corrupt") from exc

        packet_summary = dispatch_payload.get("packet_summary", {})
        if not isinstance(packet_summary, dict):
            raise AutoDispatchError(f"dispatch record for request {request_id} is corrupt")

        task_id = str(packet_summary.get("task_id", "")).strip()
        if not task_id:
            raise AutoDispatchError(f"dispatch record for request {request_id} is corrupt")
        if task_id not in task_ids:
            raise AutoDispatchError(
                f"dispatch record for request {request_id} references unexpected task {task_id}"
            )
        if task_id in dispatch_by_task_id:
            raise AutoDispatchError(f"duplicate dispatch record for task {task_id}")

        dispatch_by_task_id[task_id] = dispatch_payload

    missing_task_ids = [task_id for task_id in task_ids if task_id not in dispatch_by_task_id]
    if missing_task_ids:
        missing_text = ", ".join(missing_task_ids)
        raise AutoDispatchError(f"dispatch records are missing for tasks: {missing_text}")

    return dispatch_by_task_id


def launch_dispatched_worker(
    project_root: Path,
    *,
    session_id: str,
    worker_id: str,
    task_id: str,
    request_id: str = "",
    result_path: str = "",
) -> None:
    heartbeat = worker_heartbeat_path(project_root, worker_id)
    if heartbeat.exists():
        return

    worktree = worker_worktree_path(
        project_root,
        session_id=session_id,
        worker_id=worker_id,
    )
    worktree.mkdir(parents=True, exist_ok=True)

    env = {
        "PYTHONPATH": os.pathsep.join(
            [str(PACKAGE_SRC_ROOT), os.environ.get("PYTHONPATH", "")]
        ).strip(os.pathsep),
    }
    command = [
        sys.executable,
        "-m",
        "specify_cli.codex_team.worker_runtime",
        "--project-root",
        str(project_root),
        "--session-id",
        session_id,
        "--worker-id",
        worker_id,
        "--task-id",
        task_id,
        "--request-id",
        request_id,
        "--worktree",
        str(worktree),
        "--result-path",
        result_path,
    ]
    ProcessBackend().launch(command, cwd=project_root, env=env)


def launch_agent_teams_batch_executor(
    project_root: Path,
    *,
    session_id: str,
    batch_id: str,
    runtime_cli_path: str,
    task_specs: list[dict[str, str]],
) -> None:
    manifest_path = codex_team_state_root(project_root) / "executors" / f"{batch_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "runtime_cli_path": runtime_cli_path,
                "state_root": str(codex_team_state_root(project_root) / "agent-teams" / batch_id),
                "team_name": _agent_teams_team_name(batch_id),
                "worker_count": len(task_specs),
                "cwd": str(project_root),
                "tasks": task_specs,
                "session_id": session_id,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    env = {
        "PYTHONPATH": os.pathsep.join(
            [str(PACKAGE_SRC_ROOT), os.environ.get("PYTHONPATH", "")]
        ).strip(os.pathsep),
    }
    ProcessBackend().launch(
        [
            sys.executable,
            "-m",
            "specify_cli.codex_team.agent_teams_executor",
            "--project-root",
            str(project_root),
            "--manifest-path",
            str(manifest_path),
        ],
        cwd=project_root,
        env=env,
    )


def route_ready_parallel_batch(
    project_root: Path,
    *,
    feature_dir: Path,
    session_id: str = "default",
) -> AutoDispatchResult:
    """Dispatch the next ready explicit parallel batch into the team runtime."""
    try:
        ensure_codex_team_runtime_prerequisites()
        executor = ensure_codex_team_executor_available(project_root)
    except RuntimeError as exc:  # RuntimeEnvironmentError subclass
        raise AutoDispatchUnavailableError(str(exc)) from exc
    baseline_build = classify_baseline_build_status(project_root)
    if baseline_build["status"] == "blocked":
        raise AutoDispatchUnavailableError(
            f"Baseline build is blocked: {baseline_build['reason'] or 'unknown baseline failure'}. "
            "Resolve the baseline blocker or refresh the cached baseline assessment before auto-dispatch."
        )

    batch = materialize_runtime_batch(feature_dir)

    try:
        _, _ = resume_session(project_root, session_id=session_id)
        original_session_payload = json.loads(
            runtime_session_path(project_root, session_id).read_text(encoding="utf-8")
        )
    except Exception:
        raise

    request_ids: list[str] = []
    dispatched_task_ids: list[str] = []
    prepared_request_ids: list[str] = []
    packet_paths: list[Path] = []
    result_paths: list[Path] = []
    created_task_ids: list[str] = []
    pending_launches: list[dict[str, str]] = []
    batch_id = _batch_id_for(session_id, batch.batch_name)
    codex_snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
        managed_team_supported=True,
        structured_results=False,
        durable_coordination=True,
        native_worker_surface="spawn_agent",
        delegation_confidence="high",
        model_family="codex",
        runtime_probe_succeeded=True,
    )
    delegation_descriptor = describe_delegation_surface(
        command_name="implement",
        snapshot=codex_snapshot,
    )
    batch_policy = classify_batch_execution_policy(
        workload_shape={
            "parallel_batches": len(batch.tasks),
            "overlapping_write_sets": False,
            "safe_preparation": False,
        }
    )
    review_policy = classify_review_gate_policy(
        workload_shape={
            "parallel_batches": len(batch.tasks),
            "review_lane_available": True,
        }
    )
    try:
        for task in batch.tasks:
            if task.completed:
                continue
            task_id = task.task_id
            request_id = _request_id_for(session_id, batch.batch_name, task_id)
            packet = compile_worker_task_packet(
                project_root=project_root,
                feature_dir=feature_dir,
                task_id=task_id,
                task_body=task.task_body,
            )
            packet_path = codex_team_state_root(project_root) / "packets" / f"{request_id}.json"
            result_path = build_result_handoff_path(
                project_root,
                command_name="implement",
                integration_key="codex",
                request_id=request_id,
            )
            prepared_request_ids.append(request_id)
            packet_paths.append(packet_path)
            result_paths.append(result_path)
            write_json(packet_path, asdict(packet))

            try:
                task_ops.create_task(
                    project_root,
                    task_id=task_id,
                    summary=task.summary,
                    metadata={
                        "feature_dir": feature_dir.as_posix(),
                        "batch_name": batch.batch_name,
                        "source": "auto_dispatch",
                        "packet_path": str(packet_path),
                    },
                )
                created_task_ids.append(task_id)
            except task_ops.TaskOpsError:
                pass

            dispatch_runtime_task(
                project_root,
                session_id=session_id,
                request_id=request_id,
                target_worker=task_id.lower(),
                packet_path=str(packet_path),
                packet_summary={
                    "task_id": packet.task_id,
                    "objective": packet.objective,
                    "write_scope": packet.scope.write_scope,
                    "summary": render_packet_summary(packet),
                },
                delegation_metadata={
                    "native_subagent_surface": delegation_descriptor.native_subagent_surface,
                    "native_dispatch_hint": delegation_descriptor.native_dispatch_hint,
                    "native_join_hint": delegation_descriptor.native_join_hint,
                    "managed_team_hint": delegation_descriptor.managed_team_hint,
                    "result_contract_hint": delegation_descriptor.result_contract_hint,
                    "structured_results_expected": delegation_descriptor.structured_results_expected,
                    "executor_mode": executor["mode"],
                },
                result_path=str(result_path),
            )
            request_ids.append(request_id)
            dispatched_task_ids.append(task_id)
            pending_launches.append(
                {
                    "task_id": task_id,
                    "request_id": request_id,
                    "result_path": str(result_path),
                }
            )

    except Exception:
        _cleanup_partial_dispatch_state(
            project_root,
            session_id=session_id,
            original_session_payload=original_session_payload,
            request_ids=prepared_request_ids,
            packet_paths=packet_paths,
            result_paths=result_paths,
            created_task_ids=created_task_ids,
        )
        raise

    if executor["mode"] == "agent-teams-runtime":
        launch_agent_teams_batch_executor(
            project_root,
            session_id=session_id,
            batch_id=batch_id,
            runtime_cli_path=str(executor["runtime_cli_path"]),
            task_specs=[
                {
                    "task_id": task.task_id,
                    "request_id": _request_id_for(session_id, batch.batch_name, task.task_id),
                    "subject": task.task_id,
                    "description": _agent_teams_task_description(
                        worker_task_packet_from_json(packet_path.read_text(encoding="utf-8")),
                        request_id=_request_id_for(session_id, batch.batch_name, task.task_id),
                    ),
                }
                for task, packet_path in zip(
                    [task for task in batch.tasks if not task.completed],
                    packet_paths,
                    strict=False,
                )
            ],
        )
    else:
        for pending_launch in pending_launches:
            task_id = pending_launch["task_id"]
            request_id = pending_launch["request_id"]
            result_path = pending_launch["result_path"]
            launch_dispatched_worker(
                project_root,
                session_id=session_id,
                worker_id=task_id.lower(),
                task_id=task_id,
                request_id=request_id,
                result_path=result_path,
            )

    for task_id in dispatched_task_ids:
        current_task = task_ops.get_task(project_root, task_id)
        if batch.join_point_name:
            task_ops.mark_join_point(
                project_root,
                task_id=task_id,
                join_point_name=batch.join_point_name,
                expected_version=current_task.version,
                status="pending",
                details={
                    "batch_id": batch_id,
                    "batch_name": batch.batch_name,
                    "feature_dir": feature_dir.as_posix(),
                    "batch_classification": batch_policy.batch_classification,
                    "safe_preparation": batch_policy.safe_preparation_allowed,
                    "review_required": review_policy.requires_review_gate,
                    "review_status": "awaiting_review" if review_policy.requires_review_gate else "not_required",
                },
            )

    _write_batch_record(
        project_root,
        batch_id=batch_id,
        batch_name=batch.batch_name,
        session_id=session_id,
        feature_dir=feature_dir,
        task_ids=dispatched_task_ids,
        request_ids=request_ids,
        join_point_name=batch.join_point_name,
        batch_classification=batch_policy.batch_classification,
        safe_preparation=batch_policy.safe_preparation_allowed,
        review_required=review_policy.requires_review_gate,
        peer_review_lane_recommended=review_policy.peer_review_lane_recommended,
        review_reason=review_policy.reason,
        review_status="awaiting_review" if review_policy.requires_review_gate else "not_required",
    )
    monitor_summary(project_root, session_id=session_id)
    return AutoDispatchResult(
        feature_dir=feature_dir,
        batch_id=batch_id,
        batch_name=batch.batch_name,
        join_point_name=batch.join_point_name,
        dispatched_task_ids=dispatched_task_ids,
        request_ids=request_ids,
    )


def run_notify_hook(payload: dict[str, Any]) -> None:
    """Core logic for the Codex notify hook.

    Scans for ready parallel batches and assesses passive parallelism.
    """
    project_root = Path(payload.get("cwd", ".")).resolve()
    session_id = payload.get("session_id", "default")

    # Search for tasks.md in specs/* and docs/superpowers/specs/*
    search_dirs = [
        project_root / "specs",
        project_root / "docs" / "superpowers" / "specs",
    ]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue

        for feature_dir in search_dir.iterdir():
            if not feature_dir.is_dir():
                continue

            tasks_path = feature_dir / "tasks.md"
            if not tasks_path.exists():
                continue

            try:
                # 1. Attempt to route the next ready parallel batch
                route_ready_parallel_batch(
                    project_root,
                    feature_dir=feature_dir,
                    session_id=session_id,
                )
            except (AutoDispatchError, AutoDispatchUnavailableError):
                # 2. If no batch is ready, we could assess passive parallelism here
                # matching oh-my-codex's behavior of opportunistic triggers.
                # For now, we skip to the next directory.
                continue
            except Exception:
                # Don't let hook failures crash the CLI
                continue


def complete_dispatched_batch(
    project_root: Path,
    *,
    batch_id: str,
    session_id: str = "default",
) -> BatchCompletionResult:
    """Mark a previously dispatched batch and its join point markers complete."""
    payload = _load_batch_record(project_root, batch_id)
    task_ids = [str(task_id) for task_id in payload.get("task_ids", [])]
    request_ids = [str(request_id) for request_id in payload.get("request_ids", [])]
    join_point_name = str(payload.get("join_point_name") or "")

    if not task_ids:
        raise AutoDispatchError(f"batch {batch_id} has no task ids")

    dispatch_by_task_id = _load_expected_dispatch_records(
        project_root,
        task_ids=task_ids,
        request_ids=request_ids,
    )

    feature_dir = Path(str(payload.get("feature_dir") or "")).resolve() if payload.get("feature_dir") else None
    for task_id in task_ids:
        dispatch_payload = dispatch_by_task_id.get(task_id, {})
        packet_path = str(dispatch_payload.get("packet_path", "")).strip()
        result_path = str(dispatch_payload.get("result_path", "")).strip()
        delegation_metadata = dispatch_payload.get("delegation_metadata", {})
        dispatch_status = str(dispatch_payload.get("status", "")).strip()
        dispatch_reason = str(dispatch_payload.get("reason", "")).strip()
        structured_results_expected = bool(
            isinstance(delegation_metadata, dict)
            and delegation_metadata.get("structured_results_expected")
        )

        if dispatch_status in {"failed", "retry_pending"} and dispatch_reason:
            raise AutoDispatchError(f"dispatch result for {task_id} is unavailable: {dispatch_reason}")

        if structured_results_expected and not result_path:
            raise AutoDispatchError(f"dispatch result for {task_id} is missing structured worker result path")

        if structured_results_expected and result_path:
            result_file = Path(result_path)
            if not result_file.exists():
                raise AutoDispatchError(f"dispatch result for {task_id} is missing structured worker result")

        request_id = str(dispatch_payload.get("request_id") or "").strip()
        if result_path:
            result_file = Path(result_path)
            if result_file.exists():
                if not packet_path:
                    raise AutoDispatchError(f"dispatch result for {task_id} is missing packet_path")
                packet = worker_task_packet_from_json(Path(packet_path).read_text(encoding="utf-8"))
                result = normalize_worker_task_result_payload(result_file.read_text(encoding="utf-8"))
                validated_result = validate_worker_task_result(result, packet)
                if validated_result.status != "success":
                    raise AutoDispatchError(
                        f"dispatch result for {task_id} is not complete: {validated_result.status}"
                    )
                existing_task = task_ops.get_task(project_root, task_id)
                if (
                    request_id
                    and dispatch_status not in {"completed", "failed", "blocked"}
                    and existing_task.status not in task_ops.TERMINAL_STATUSES
                ):
                    submit_runtime_result(
                        project_root,
                        session_id=session_id,
                        request_id=request_id,
                        result=result_file.read_text(encoding="utf-8"),
                    )

        record = task_ops.get_task(project_root, task_id)
        if join_point_name:
            join_status = "review_pending" if payload.get("review_required") else "complete"
            task_ops.mark_join_point(
                project_root,
                task_id=task_id,
                join_point_name=join_point_name,
                expected_version=record.version,
                status=join_status,
                details={
                    "batch_id": batch_id,
                    "batch_name": payload.get("batch_name", ""),
                    "feature_dir": payload.get("feature_dir", ""),
                    "review_status": payload.get("review_status", "not_required"),
                },
            )

    if payload.get("review_required"):
        payload["status"] = "awaiting_review"
        payload["review_status"] = "awaiting_review"
        if join_point_name:
            for task_id in task_ids:
                task_record = task_ops.get_task(project_root, task_id)
                task_ops.mark_join_point(
                    project_root,
                    task_id=task_id,
                    join_point_name=join_point_name,
                    expected_version=task_record.version,
                    status="review_pending",
                    details={
                        "batch_id": batch_id,
                        "batch_name": payload.get("batch_name", ""),
                        "feature_dir": payload.get("feature_dir", ""),
                        "review_status": "awaiting_review",
                    },
                )
    else:
        payload["status"] = "completed"
    path = batch_record_path(project_root, batch_id)
    write_json(path, payload)
    monitor_summary(project_root, session_id=session_id)

    next_batch_id = ""
    next_batch_name = ""
    next_dispatched_task_ids: list[str] | None = None
    if not payload.get("review_required") and feature_dir is not None:
        try:
            next_batch = route_ready_parallel_batch(
                project_root,
                feature_dir=feature_dir,
                session_id=session_id,
            )
        except (AutoDispatchError, AutoDispatchUnavailableError):
            next_batch = None
        if next_batch is not None:
            next_batch_id = next_batch.batch_id
            next_batch_name = next_batch.batch_name
            next_dispatched_task_ids = next_batch.dispatched_task_ids

    return BatchCompletionResult(
        batch_id=batch_id,
        batch_name=str(payload.get("batch_name", "")),
        status=str(payload.get("status", "completed")),
        join_point_name=join_point_name,
        task_ids=task_ids,
        next_batch_id=next_batch_id,
        next_batch_name=next_batch_name,
        next_dispatched_task_ids=next_dispatched_task_ids,
    )
