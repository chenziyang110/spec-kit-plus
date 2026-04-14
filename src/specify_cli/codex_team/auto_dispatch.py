"""Deterministic routing of ready parallel batches into the Codex team runtime."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from specify_cli.codex_team import task_ops
from specify_cli.codex_team.state_paths import worker_heartbeat_path
from specify_cli.codex_team.runtime_bridge import dispatch_runtime_task, ensure_tmux_available
from specify_cli.codex_team.runtime_state import batch_record_payload
from specify_cli.codex_team.session_ops import bootstrap_session, monitor_summary
from specify_cli.codex_team.worktree_ops import worker_worktree_path
from specify_cli.codex_team.state_paths import batch_record_path
from specify_cli.orchestration.backends.process_backend import ProcessBackend


TASK_LINE_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<task_id>T\d+)(?P<rest>.*)$")
PARALLEL_BATCH_RE = re.compile(r"^\*\*(?P<name>Parallel Batch [^*]+)\*\*$")
JOIN_POINT_RE = re.compile(r"^\*\*(?P<name>Join Point [^*]+)\*\*")
INLINE_TASK_ID_RE = re.compile(r"`(T\d+)`")


class AutoDispatchError(RuntimeError):
    """Base exception for ready-batch auto dispatch failures."""


class AutoDispatchUnavailableError(AutoDispatchError):
    """Raised when the runtime backend is unavailable."""


@dataclass(slots=True)
class ParsedTask:
    task_id: str
    completed: bool
    parallel: bool
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


@dataclass(slots=True)
class PassiveParallelismLane:
    """A candidate unit of passive parallel work for higher-level command logic."""

    lane_id: str
    summary: str
    references: tuple[str, ...] = ()
    write_scopes: tuple[str, ...] = ()


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
                    parallel="[P]" in rest,
                    summary=rest.strip(),
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


def find_next_ready_parallel_batch(parsed: ParsedTasksDocument) -> ParsedParallelBatch | None:
    """Return the first explicit or inferred parallel batch whose prerequisites are complete.

    Prefers explicit batches defined by **Parallel Batch** headers.
    Falls back to grouping adjacent ready [P] tasks into an inferred batch.
    """
    tasks_by_id = {task.task_id: task for task in parsed.tasks}

    # 1. Try explicit batches first
    for batch in parsed.parallel_batches:
        members = [tasks_by_id[task_id] for task_id in batch.task_ids if task_id in tasks_by_id]
        pending_members = [task for task in members if not task.completed]
        if not pending_members:
            continue

        first_index = min(task.order_index for task in members)
        blocked = any(
            not task.completed and task.task_id not in batch.task_ids
            for task in parsed.tasks
            if task.order_index < first_index
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
) -> None:
    path = batch_record_path(project_root, batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            batch_record_payload(
                batch_id=batch_id,
                batch_name=batch_name,
                session_id=session_id,
                feature_dir=feature_dir.as_posix(),
                task_ids=task_ids,
                request_ids=request_ids,
                join_point_name=join_point_name,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _load_batch_record(project_root: Path, batch_id: str) -> dict[str, object]:
    path = batch_record_path(project_root, batch_id)
    if not path.exists():
        raise AutoDispatchError(f"batch {batch_id} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def launch_dispatched_worker(
    project_root: Path,
    *,
    session_id: str,
    worker_id: str,
    task_id: str,
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
        "PYTHONPATH": str((project_root / "src").resolve()),
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
        "--worktree",
        str(worktree),
    ]
    ProcessBackend().launch(command, cwd=project_root, env=env)


def route_ready_parallel_batch(
    project_root: Path,
    *,
    feature_dir: Path,
    session_id: str = "default",
) -> AutoDispatchResult:
    """Dispatch the next ready explicit parallel batch into the team runtime."""
    try:
        ensure_tmux_available()
    except RuntimeError as exc:  # RuntimeEnvironmentError subclass
        raise AutoDispatchUnavailableError(str(exc)) from exc

    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.exists():
        raise AutoDispatchError(f"tasks.md not found in {feature_dir}")

    parsed = parse_tasks_markdown(tasks_path)
    batch = find_next_ready_parallel_batch(parsed)
    if batch is None:
        raise AutoDispatchError("no ready parallel batch found")

    tasks_by_id = {task.task_id: task for task in parsed.tasks}

    try:
        bootstrap_session(project_root, session_id=session_id)
    except Exception as exc:
        if "already active" not in str(exc):
            raise

    request_ids: list[str] = []
    dispatched_task_ids: list[str] = []
    batch_id = _batch_id_for(session_id, batch.batch_name)
    for task_id in batch.task_ids:
        task = tasks_by_id.get(task_id)
        if task is None or task.completed:
            continue
        try:
            task_ops.create_task(
                project_root,
                task_id=task_id,
                summary=task.summary,
                metadata={
                    "feature_dir": feature_dir.as_posix(),
                    "batch_name": batch.batch_name,
                    "source": "auto_dispatch",
                },
            )
        except task_ops.TaskOpsError:
            pass

        request_id = _request_id_for(session_id, batch.batch_name, task_id)
        dispatch_runtime_task(
            project_root,
            session_id=session_id,
            request_id=request_id,
            target_worker=task_id.lower(),
        )
        launch_dispatched_worker(
            project_root,
            session_id=session_id,
            worker_id=task_id.lower(),
            task_id=task_id,
        )
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
                },
            )
        request_ids.append(request_id)
        dispatched_task_ids.append(task_id)

    _write_batch_record(
        project_root,
        batch_id=batch_id,
        batch_name=batch.batch_name,
        session_id=session_id,
        feature_dir=feature_dir,
        task_ids=dispatched_task_ids,
        request_ids=request_ids,
        join_point_name=batch.join_point_name,
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
    join_point_name = str(payload.get("join_point_name") or "")

    if not task_ids:
        raise AutoDispatchError(f"batch {batch_id} has no task ids")

    for task_id in task_ids:
        record = task_ops.get_task(project_root, task_id)
        if join_point_name:
            task_ops.mark_join_point(
                project_root,
                task_id=task_id,
                join_point_name=join_point_name,
                expected_version=record.version,
                status="complete",
                details={
                    "batch_id": batch_id,
                    "batch_name": payload.get("batch_name", ""),
                    "feature_dir": payload.get("feature_dir", ""),
                },
            )

    payload["status"] = "completed"
    path = batch_record_path(project_root, batch_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    monitor_summary(project_root, session_id=session_id)

    return BatchCompletionResult(
        batch_id=batch_id,
        batch_name=str(payload.get("batch_name", "")),
        status=str(payload.get("status", "completed")),
        join_point_name=join_point_name,
        task_ids=task_ids,
    )
