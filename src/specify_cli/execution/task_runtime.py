"""CLI-owned task packets, lifecycle transitions, and state projections."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from specify_cli.atomic_io import read_local_state_text, safe_local_state_path
from specify_cli.workflow_transaction import (
    WorkflowTransactionError,
    apply_workflow_transaction,
)

from .packet_compiler import compile_worker_task_packet
from .packet_schema import worker_task_packet_payload
from .result_normalizer import normalize_worker_task_result_payload
from .result_schema import worker_task_result_payload


class TaskRuntimeError(RuntimeError):
    """Raised when a task lifecycle transition is invalid or unsafe."""


_TASK_ID = re.compile(r"^T\d+$")
_TASK_CHECKBOX = re.compile(
    r"(?m)^(?P<prefix>\s*-\s*\[)[ xX](?P<suffix>\]\s+{task_id}\b)"
)
_TERMINAL_TASK_STATUSES = {"accepted", "deferred"}


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _project_feature(project_root: Path, feature_dir: Path | str) -> tuple[Path, Path]:
    root = safe_local_state_path(Path(project_root))
    candidate = Path(feature_dir)
    if not candidate.is_absolute():
        candidate = root / candidate
    feature = safe_local_state_path(candidate, root=root)
    if not feature.is_dir():
        raise TaskRuntimeError(f"feature directory does not exist: {feature}")
    return root, feature


def _read_json_object(path: Path, *, root: Path) -> dict[str, Any]:
    try:
        payload = json.loads(read_local_state_text(path, root=root))
    except FileNotFoundError as exc:
        raise TaskRuntimeError(f"required workflow artifact is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskRuntimeError(f"cannot read workflow artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskRuntimeError(f"workflow artifact must contain an object: {path}")
    return payload


def _task_index(root: Path, feature: Path) -> dict[str, Any]:
    payload = _read_json_object(feature / "task-index.json", root=root)
    if payload.get("version") != 2 or payload.get("status") != "ready":
        raise TaskRuntimeError("task-index.json must use version 2 with status ready")
    if not isinstance(payload.get("tasks"), list):
        raise TaskRuntimeError("task-index.json tasks must be a list")
    return payload


def _normalize_task_id(task_id: str) -> str:
    normalized = task_id.strip().upper()
    if not _TASK_ID.fullmatch(normalized):
        raise TaskRuntimeError(f"invalid task id: {task_id}")
    return normalized


def _task_entry(
    task_index: Mapping[str, Any], task_id: str
) -> tuple[int, dict[str, Any]]:
    tasks = task_index.get("tasks")
    if not isinstance(tasks, list):
        raise TaskRuntimeError("task-index.json tasks must be a list")
    for index, raw_task in enumerate(tasks):
        if not isinstance(raw_task, dict):
            continue
        current_id = str(raw_task.get("task_id", raw_task.get("id")) or "").upper()
        if current_id == task_id:
            return index, raw_task
    raise TaskRuntimeError(f"task {task_id} is not present in task-index.json")


def _task_status(task: Mapping[str, Any]) -> str:
    value = str(task.get("status") or "pending").strip().lower()
    return value or "pending"


def _dependencies(task: Mapping[str, Any]) -> list[str]:
    raw = task.get("dependencies", task.get("depends_on", []))
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for value in raw:
        normalized = str(value).strip().upper()
        if _TASK_ID.fullmatch(normalized) and normalized not in result:
            result.append(normalized)
    return result


def _lifecycle_path(feature: Path, task_id: str) -> Path:
    return feature / "implementation-review" / "tasks" / f"{task_id}.json"


def _packet_path(feature: Path, task_id: str) -> Path:
    return feature / "implementation-review" / "packets" / f"{task_id}.json"


def _result_path(feature: Path, task_id: str) -> Path:
    return feature / "worker-results" / f"{task_id}.json"


def _execution_state_path(feature: Path) -> Path:
    return feature / "implementation-review" / "execution-state.json"


def _default_execution_state(task_index: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": 3,
        "revision": 0,
        "status": "gathering",
        "source_contract": "task-index.json",
        "source_revision": task_index.get("source_revision"),
        "current_batch": None,
        "current_task": None,
        "next_action": "Start the next dependency-ready task.",
        "completed_task_ids": [],
        "failed_task_ids": [],
        "retry_count": 0,
        "active_packet_refs": [],
        "blockers": [],
        "recovery": None,
        "open_gaps": [],
        "validation": [],
    }


def _execution_state(
    root: Path, feature: Path, task_index: Mapping[str, Any]
) -> dict[str, Any]:
    path = _execution_state_path(feature)
    if not path.is_file():
        return _default_execution_state(task_index)
    payload = _read_json_object(path, root=root)
    if payload.get("version") != 3:
        raise TaskRuntimeError("execution-state.json must use version 3")
    return payload


def _read_lifecycle(root: Path, feature: Path, task_id: str) -> dict[str, Any]:
    return _read_json_object(_lifecycle_path(feature, task_id), root=root)


def _render_tracker(feature: Path, state: Mapping[str, Any]) -> bytes:
    completed = [str(value) for value in state.get("completed_task_ids", [])]
    failed = [str(value) for value in state.get("failed_task_ids", [])]
    status = str(state.get("status") or "executing")
    resume = "resolved" if status == "resolved" else "continue"
    if status == "blocked":
        resume = "blocked"
    current_task = str(state.get("current_task") or "none")
    next_action = str(state.get("next_action") or "Resume the canonical task state.")
    content = "\n".join(
        [
            "---",
            f"status: {status}",
            f"feature: {feature.name}",
            f"resume_decision: {resume}",
            "---",
            "",
            "## Current Focus",
            f"current_batch: {state.get('current_batch') or 'canonical task graph'}",
            f"goal: execute {current_task}",
            f"next_action: {next_action}",
            "",
            "## Execution State",
            "completed_tasks:",
            *[f"  - {task_id}" for task_id in completed],
            "in_progress_tasks:",
            *([f"  - {current_task}"] if current_task != "none" else []),
            "failed_tasks:",
            *[f"  - {task_id}" for task_id in failed],
            f"retry_attempts: {state.get('retry_count', 0)}",
            "",
            "## Open Gaps",
            *[f"- {gap}" for gap in state.get("open_gaps", [])],
            "",
        ]
    )
    return content.encode("utf-8")


def _checkbox_projection(tasks_text: str, task_id: str, *, checked: bool) -> str:
    pattern = re.compile(
        _TASK_CHECKBOX.pattern.format(task_id=re.escape(task_id)),
        _TASK_CHECKBOX.flags,
    )
    replacement = rf"\g<prefix>{'x' if checked else ' '}\g<suffix>"
    updated, count = pattern.subn(replacement, tasks_text, count=1)
    if count != 1:
        raise TaskRuntimeError(f"tasks.md has no unique checkbox for {task_id}")
    return updated


def _lifecycle_template(
    task_index: Mapping[str, Any], task_position: int, task_id: str
) -> dict[str, Any]:
    return {
        "version": 1,
        "revision": 0,
        "task_id": task_id,
        "task_ref": f"task-index.json#/tasks/{task_position}",
        "source_revision": task_index.get("source_revision"),
        "execution_mode": "leader-direct",
        "packet_ref": None,
        "result_ref": None,
        "status": "pending",
        "changed_paths": [],
        "validation": [],
        "review": None,
        "ui_verification": {
            "applicable": False,
            "evidence_scope": "integrated",
            "evidence": [],
            "contract_check": "not-run",
            "runtime_evidence": "not-run",
            "visual_comparison": "not-applicable",
            "fidelity_status": "not-applicable",
            "reviewer": "agent",
        },
        "obligation_evidence": [],
        "blockers": [],
        "recovery": None,
    }


def _transaction_receipt(
    receipt: Mapping[str, Any] | Any,
    *,
    task_id: str,
    revision: int,
    status: str,
) -> dict[str, Any]:
    base = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
    return {
        "status": "ok",
        "task_id": task_id,
        "task_status": status,
        "revision": revision,
        **base,
    }


def next_task(project_root: Path, feature_dir: Path | str) -> dict[str, Any] | None:
    root, feature = _project_feature(project_root, feature_dir)
    task_index = _task_index(root, feature)
    tasks = [item for item in task_index["tasks"] if isinstance(item, dict)]
    statuses = {
        str(item.get("task_id", item.get("id")) or "").upper(): _task_status(item)
        for item in tasks
    }
    for task in tasks:
        task_id = str(task.get("task_id", task.get("id")) or "").upper()
        if not _TASK_ID.fullmatch(task_id) or _task_status(task) not in {
            "pending",
            "ready",
        }:
            continue
        dependencies = _dependencies(task)
        if any(statuses.get(dependency) not in _TERMINAL_TASK_STATUSES for dependency in dependencies):
            continue
        return {
            "task_id": task_id,
            "status": _task_status(task),
            "objective": str(task.get("objective") or "").strip(),
            "dependencies": dependencies,
            "lifecycle_ref": f"implementation-review/tasks/{task_id}.json",
        }
    return None


def compile_task_packet(
    project_root: Path, feature_dir: Path | str, task_id: str
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    normalized_id = _normalize_task_id(task_id)
    task_index = _task_index(root, feature)
    _position, task = _task_entry(task_index, normalized_id)
    packet = compile_worker_task_packet(
        project_root=root,
        feature_dir=feature,
        task_id=normalized_id,
    )
    packet_payload = worker_task_packet_payload(packet)
    packet_content = _json_bytes(packet_payload)
    packet_path = _packet_path(feature, normalized_id)
    packet_ref = packet_path.relative_to(feature).as_posix()
    task["packet_ref"] = packet_ref
    receipt = apply_workflow_transaction(
        root,
        kind="implement.packet.compile",
        updates={
            packet_path: packet_content,
            feature / "task-index.json": _json_bytes(task_index),
        },
    )
    return {
        "status": "ok",
        "task_id": normalized_id,
        "path": str(packet_path),
        "sha256": _sha256(packet_content),
        **receipt.to_dict(),
    }


def start_task(
    project_root: Path,
    feature_dir: Path | str,
    task_id: str,
    *,
    execution_mode: str,
    packet_ref: str | None = None,
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    normalized_id = _normalize_task_id(task_id)
    mode = execution_mode.strip().lower()
    if mode not in {"leader-direct", "delegated", "managed-team"}:
        raise TaskRuntimeError("execution_mode must be leader-direct, delegated, or managed-team")
    task_index = _task_index(root, feature)
    position, task = _task_entry(task_index, normalized_id)
    current_status = _task_status(task)
    if current_status not in {"pending", "ready", "blocked", "failed"}:
        raise TaskRuntimeError(
            f"task {normalized_id} cannot start from status {current_status}"
        )
    statuses = {
        str(item.get("task_id", item.get("id")) or "").upper(): _task_status(item)
        for item in task_index["tasks"]
        if isinstance(item, dict)
    }
    unmet = [
        dependency
        for dependency in _dependencies(task)
        if statuses.get(dependency) not in _TERMINAL_TASK_STATUSES
    ]
    if unmet:
        raise TaskRuntimeError(
            f"task {normalized_id} has unmet dependencies: {', '.join(unmet)}"
        )
    lifecycle_path = _lifecycle_path(feature, normalized_id)
    if lifecycle_path.is_file():
        lifecycle = _read_lifecycle(root, feature, normalized_id)
    else:
        lifecycle = _lifecycle_template(task_index, position, normalized_id)
    revision = int(lifecycle.get("revision") or 0) + 1
    lifecycle.update(
        {
            "revision": revision,
            "execution_mode": mode,
            "packet_ref": packet_ref or task.get("packet_ref"),
            "status": "in_progress",
            "blockers": [],
            "recovery": None,
        }
    )
    task["status"] = "in_progress"
    task["lifecycle_ref"] = lifecycle_path.relative_to(feature).as_posix()
    state = _execution_state(root, feature, task_index)
    state["revision"] = int(state.get("revision") or 0) + 1
    state["status"] = "executing"
    state["current_task"] = normalized_id
    state["next_action"] = f"Complete {normalized_id} and record its structured result."
    updates = {
        lifecycle_path: _json_bytes(lifecycle),
        feature / "task-index.json": _json_bytes(task_index),
        _execution_state_path(feature): _json_bytes(state),
        feature / "implement-tracker.md": _render_tracker(feature, state),
    }
    try:
        receipt = apply_workflow_transaction(
            root, kind="implement.task.start", updates=updates
        )
    except WorkflowTransactionError as exc:
        raise TaskRuntimeError(str(exc)) from exc
    return _transaction_receipt(
        receipt, task_id=normalized_id, revision=revision, status="in_progress"
    )


def record_task_result(
    project_root: Path,
    feature_dir: Path | str,
    task_id: str,
    raw_result: object,
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    normalized_id = _normalize_task_id(task_id)
    task_index = _task_index(root, feature)
    _position, task = _task_entry(task_index, normalized_id)
    lifecycle = _read_lifecycle(root, feature, normalized_id)
    if lifecycle.get("status") not in {"in_progress", "blocked", "failed"}:
        raise TaskRuntimeError(
            f"task {normalized_id} cannot record a result from status {lifecycle.get('status')}"
        )
    try:
        result = normalize_worker_task_result_payload(raw_result)
    except Exception as exc:
        raise TaskRuntimeError(f"worker result is invalid: {exc}") from exc
    if result.task_id.strip().upper() != normalized_id:
        raise TaskRuntimeError(
            f"worker result task_id {result.task_id} does not match {normalized_id}"
        )
    if result.status == "pending":
        raise TaskRuntimeError("pending worker results cannot be merged")
    if result.status == "blocked" and (
        not result.blockers or not result.suggested_recovery_actions
    ):
        raise TaskRuntimeError(
            "blocked worker results require blockers and suggested_recovery_actions"
        )
    if result.status == "success" and result.blockers:
        raise TaskRuntimeError("successful worker results cannot contain blockers")
    result_payload = worker_task_result_payload(result)
    result_path = _result_path(feature, normalized_id)
    result_ref = result_path.relative_to(feature).as_posix()
    status_map = {"success": "implemented", "blocked": "blocked", "failed": "failed"}
    lifecycle_status = status_map[result.status]
    revision = int(lifecycle.get("revision") or 0) + 1
    lifecycle.update(
        {
            "revision": revision,
            "status": lifecycle_status,
            "result_ref": result_ref,
            "changed_paths": list(result.changed_files),
            "validation": [asdict(item) for item in result.validation_results],
            "blockers": list(result.blockers),
            "recovery": (
                {"actions": list(result.suggested_recovery_actions)}
                if result.suggested_recovery_actions
                else None
            ),
        }
    )
    task["status"] = lifecycle_status
    task["result_ref"] = result_ref
    state = _execution_state(root, feature, task_index)
    state["revision"] = int(state.get("revision") or 0) + 1
    state["status"] = "validating" if result.status == "success" else lifecycle_status
    state["current_task"] = normalized_id
    state["next_action"] = (
        f"Validate and accept {normalized_id}."
        if result.status == "success"
        else f"Recover {normalized_id} before continuing."
    )
    failed = [str(value) for value in state.get("failed_task_ids", [])]
    if result.status == "failed" and normalized_id not in failed:
        failed.append(normalized_id)
    if result.status != "failed":
        failed = [value for value in failed if value != normalized_id]
    state["failed_task_ids"] = failed
    try:
        receipt = apply_workflow_transaction(
            root,
            kind="implement.result.merge",
            updates={
                result_path: _json_bytes(result_payload),
                _lifecycle_path(feature, normalized_id): _json_bytes(lifecycle),
                feature / "task-index.json": _json_bytes(task_index),
                _execution_state_path(feature): _json_bytes(state),
                feature / "implement-tracker.md": _render_tracker(feature, state),
            },
        )
    except WorkflowTransactionError as exc:
        raise TaskRuntimeError(str(exc)) from exc
    return {
        **_transaction_receipt(
            receipt,
            task_id=normalized_id,
            revision=revision,
            status=lifecycle_status,
        ),
        "worker_status": result.status,
        "result_ref": result_ref,
    }


def accept_task(
    project_root: Path, feature_dir: Path | str, task_id: str
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    normalized_id = _normalize_task_id(task_id)
    task_index = _task_index(root, feature)
    _position, task = _task_entry(task_index, normalized_id)
    lifecycle = _read_lifecycle(root, feature, normalized_id)
    if lifecycle.get("status") != "implemented":
        raise TaskRuntimeError(
            f"task {normalized_id} must be implemented before acceptance"
        )
    validation = lifecycle.get("validation")
    if not isinstance(validation, list) or not validation:
        raise TaskRuntimeError("task acceptance requires validation evidence")
    if any(
        not isinstance(item, dict) or item.get("status") != "passed"
        for item in validation
    ):
        raise TaskRuntimeError("task acceptance requires passed validation evidence")
    required_checks = [
        str(value).strip()
        for value in task.get("task_checks", [])
        if str(value).strip()
    ]
    passed_checks = {
        str(item.get("command", item.get("check")) or "").strip()
        for item in validation
        if isinstance(item, dict) and item.get("status") == "passed"
    }
    missing_checks = [check for check in required_checks if check not in passed_checks]
    if missing_checks:
        raise TaskRuntimeError(
            "task acceptance is missing passed task_checks: "
            + ", ".join(missing_checks)
        )
    blockers = lifecycle.get("blockers")
    if isinstance(blockers, list) and blockers:
        raise TaskRuntimeError("task acceptance is blocked by unresolved blockers")

    revision = int(lifecycle.get("revision") or 0) + 1
    lifecycle["revision"] = revision
    lifecycle["status"] = "accepted"
    task["status"] = "accepted"
    tasks_text = read_local_state_text(feature / "tasks.md", root=root)
    projected_tasks = _checkbox_projection(tasks_text, normalized_id, checked=True)

    state = _execution_state(root, feature, task_index)
    state["revision"] = int(state.get("revision") or 0) + 1
    completed = [str(value) for value in state.get("completed_task_ids", [])]
    if normalized_id not in completed:
        completed.append(normalized_id)
    state["completed_task_ids"] = completed
    state["current_task"] = None
    next_projection = next_task_from_index(task_index)
    if next_projection is None:
        state["status"] = "resolved"
        state["next_action"] = "Run implementation convergence and closeout."
    else:
        state["status"] = "executing"
        state["next_action"] = f"Start {next_projection['task_id']}."
    try:
        receipt = apply_workflow_transaction(
            root,
            kind="implement.task.accept",
            updates={
                _lifecycle_path(feature, normalized_id): _json_bytes(lifecycle),
                feature / "task-index.json": _json_bytes(task_index),
                feature / "tasks.md": projected_tasks.encode("utf-8"),
                _execution_state_path(feature): _json_bytes(state),
                feature / "implement-tracker.md": _render_tracker(feature, state),
            },
        )
    except WorkflowTransactionError as exc:
        raise TaskRuntimeError(str(exc)) from exc
    return {
        **_transaction_receipt(
            receipt,
            task_id=normalized_id,
            revision=revision,
            status="accepted",
        ),
        "next_task_id": (
            next_projection["task_id"] if next_projection is not None else None
        ),
    }


def next_task_from_index(task_index: Mapping[str, Any]) -> dict[str, Any] | None:
    tasks = [item for item in task_index.get("tasks", []) if isinstance(item, dict)]
    statuses = {
        str(item.get("task_id", item.get("id")) or "").upper(): _task_status(item)
        for item in tasks
    }
    for task in tasks:
        task_id = str(task.get("task_id", task.get("id")) or "").upper()
        if _task_status(task) not in {"pending", "ready"}:
            continue
        dependencies = _dependencies(task)
        if any(statuses.get(value) not in _TERMINAL_TASK_STATUSES for value in dependencies):
            continue
        return {
            "task_id": task_id,
            "status": _task_status(task),
            "objective": str(task.get("objective") or "").strip(),
            "dependencies": dependencies,
            "lifecycle_ref": f"implementation-review/tasks/{task_id}.json",
        }
    return None


__all__ = [
    "TaskRuntimeError",
    "accept_task",
    "compile_task_packet",
    "next_task",
    "record_task_result",
    "start_task",
]
