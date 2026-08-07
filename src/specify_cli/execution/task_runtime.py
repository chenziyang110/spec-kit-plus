"""CLI-owned task packets, lifecycle transitions, and state projections."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from specify_cli.atomic_io import (
    read_local_state_bytes,
    read_local_state_text,
    safe_local_state_path,
)
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
    try:
        root = safe_local_state_path(Path(project_root))
        candidate = Path(feature_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        feature = safe_local_state_path(candidate, root=root)
    except ValueError as exc:
        raise TaskRuntimeError(str(exc)) from exc
    if not feature.is_dir():
        raise TaskRuntimeError(f"feature directory does not exist: {feature}")
    return root, feature


def _read_json_object(path: Path, *, root: Path) -> dict[str, Any]:
    try:
        payload = json.loads(read_local_state_text(path, root=root))
    except FileNotFoundError as exc:
        raise TaskRuntimeError(
            f"required workflow artifact is missing: {path}"
        ) from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise TaskRuntimeError(f"cannot read workflow artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskRuntimeError(f"workflow artifact must contain an object: {path}")
    return payload


def _read_state_bytes(path: Path, *, root: Path, label: str) -> bytes:
    try:
        return read_local_state_bytes(path, root=root)
    except FileNotFoundError as exc:
        raise TaskRuntimeError(f"{label} is missing: {path}") from exc
    except (OSError, ValueError) as exc:
        raise TaskRuntimeError(f"cannot read {label}: {exc}") from exc


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
        "reopen_history": [],
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


def _validate_task_acceptance_evidence(
    task: Mapping[str, Any],
    validation: object,
    blockers: object,
) -> None:
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
    if isinstance(blockers, list) and blockers:
        raise TaskRuntimeError("task acceptance is blocked by unresolved blockers")


def _workflow_snapshot(root: Path, feature: Path) -> dict[str, Any]:
    path = feature / "workflow.json"
    feature_ref = feature.relative_to(root).as_posix()
    if not path.is_file():
        return {
            "present": False,
            "raw": None,
            "revision": 0,
            "stage": "",
            "status": "",
            "summary": "",
            "blocker": None,
            "resolution_action": None,
        }
    try:
        raw = _read_state_bytes(path, root=root, label="workflow state")
        payload = json.loads(raw)
    except (TaskRuntimeError, json.JSONDecodeError) as exc:
        raise TaskRuntimeError(f"workflow state is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskRuntimeError("workflow state must contain an object")
    revision = payload.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise TaskRuntimeError("workflow state has no valid revision")
    stage = str(payload.get("stage") or "").strip().lower()
    status = str(payload.get("status") or "").strip().lower()
    if stage not in {
        "discussion",
        "specify",
        "plan",
        "tasks",
        "implement",
        "review",
        "accept",
    }:
        raise TaskRuntimeError(
            f"workflow state has invalid stage: {stage or '<blank>'}"
        )
    if status not in {"active", "completed", "blocked", "closed"}:
        raise TaskRuntimeError(
            f"workflow state has invalid status: {status or '<blank>'}"
        )
    resolution_action = None
    if status == "blocked":
        resolution_action = {
            "capability_id": "workflow.resolve",
            "base_argv": [
                "specify-runtime",
                "workflow",
                "resolve",
                "--feature-dir",
                feature_ref,
                "--expected-revision",
                str(revision),
                "--format",
                "json",
            ],
            "required_inputs": [
                {
                    "field": "resolution_evidence",
                    "flag": "--resolution-evidence",
                    "repeatable": True,
                    "min_items": 1,
                }
            ],
        }
    return {
        "present": True,
        "raw": raw,
        "revision": revision,
        "stage": stage,
        "status": status,
        "summary": str(payload.get("summary") or "").strip(),
        "blocker": deepcopy(payload.get("blocker")),
        "resolution_action": resolution_action,
    }


def _task_reopen_decision(
    *,
    root: Path,
    feature: Path,
    task_id: str,
    task_revision: int,
    workflow_revision: int,
    acceptance_error: str,
) -> dict[str, Any]:
    feature_ref = feature.relative_to(root).as_posix()
    return {
        "status": "blocked",
        "reason_code": "task-reopen-required",
        "task": None,
        "blocked_task_id": task_id,
        "task_revision": task_revision,
        "workflow_revision": workflow_revision,
        "acceptance_error": acceptance_error,
        "recommended_next_action": (
            f"Reopen {task_id} with an explicit reason and evidence, then submit "
            "corrected validation evidence."
        ),
        "recovery_action": {
            "capability_id": "implement.task-reopen",
            "base_argv": [
                "specify-runtime",
                "implement",
                "task-reopen",
                "--feature-dir",
                feature_ref,
                "--task-id",
                task_id,
                "--expected-task-revision",
                str(task_revision),
                "--expected-workflow-revision",
                str(workflow_revision),
                "--format",
                "json",
            ],
            "required_inputs": [
                {"field": "reason", "flag": "--reason", "min_items": 1},
                {
                    "field": "evidence",
                    "flag": "--evidence",
                    "repeatable": True,
                    "min_items": 1,
                },
            ],
        },
    }


def _task_state_invalid_decision(
    *,
    feature: Path,
    task_id: str,
    workflow_revision: int,
    lifecycle_ref: str,
    state_error: str,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason_code": "task-state-invalid",
        "task": None,
        "blocked_task_id": task_id,
        "workflow_revision": workflow_revision,
        "lifecycle_ref": lifecycle_ref,
        "state_error": state_error,
        "recommended_next_action": (
            f"Recover {lifecycle_ref} from a trusted backup or CLI transaction "
            "history before continuing; task-reopen requires a valid revisioned "
            "implemented lifecycle."
        ),
    }


def next_task_decision(project_root: Path, feature_dir: Path | str) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    workflow = _workflow_snapshot(root, feature)
    if workflow["status"] == "blocked":
        return {
            "status": "blocked",
            "reason_code": "workflow-blocked",
            "task": None,
            "workflow_revision": workflow["revision"],
            "workflow_stage": workflow["stage"],
            "workflow_blocker": workflow["blocker"],
            "resolution_action": workflow["resolution_action"],
            "recommended_next_action": workflow["summary"]
            or "Resolve the persisted workflow blocker before continuing implementation.",
        }
    task_index = _task_index(root, feature)
    projection = next_task_from_index(task_index)
    if projection is not None:
        return {"status": "ok", "task": projection}
    tasks = [item for item in task_index["tasks"] if isinstance(item, dict)]
    if not tasks:
        return {
            "status": "blocked",
            "reason_code": "task-graph-invalid",
            "task": None,
            "blocked_tasks": [],
            "recommended_next_action": (
                "Recover tasks.md and task-index.json before continuing implementation."
            ),
        }
    for task in tasks:
        if _task_status(task) != "implemented":
            continue
        task_id = str(task.get("task_id", task.get("id")) or "").strip().upper()
        lifecycle_ref = f"implementation-review/tasks/{task_id}.json"
        try:
            lifecycle = _read_lifecycle(root, feature, task_id)
        except TaskRuntimeError as exc:
            return _task_state_invalid_decision(
                feature=feature,
                task_id=task_id,
                workflow_revision=int(workflow["revision"]),
                lifecycle_ref=lifecycle_ref,
                state_error=str(exc),
            )
        raw_revision = lifecycle.get("revision")
        revision = (
            raw_revision
            if isinstance(raw_revision, int) and not isinstance(raw_revision, bool)
            else 0
        )
        lifecycle_task_id = str(lifecycle.get("task_id") or "").strip().upper()
        lifecycle_status = str(lifecycle.get("status") or "").strip().lower()
        if (
            revision < 1
            or lifecycle_task_id != task_id
            or lifecycle_status != "implemented"
        ):
            return _task_state_invalid_decision(
                feature=feature,
                task_id=task_id,
                workflow_revision=int(workflow["revision"]),
                lifecycle_ref=lifecycle_ref,
                state_error=(
                    f"task lifecycle must identify {task_id} at status implemented "
                    "with a positive revision"
                ),
            )
        try:
            _validate_task_acceptance_evidence(
                task, lifecycle.get("validation"), lifecycle.get("blockers")
            )
        except TaskRuntimeError as exc:
            return _task_reopen_decision(
                root=root,
                feature=feature,
                task_id=task_id,
                task_revision=revision,
                workflow_revision=int(workflow["revision"]),
                acceptance_error=str(exc),
            )
        return {
            "status": "blocked",
            "reason_code": "task-accept-required",
            "task": {
                "task_id": task_id,
                "status": "implemented",
                "revision": revision,
                "lifecycle_ref": f"implementation-review/tasks/{task_id}.json",
            },
            "workflow_revision": workflow["revision"],
            "recommended_next_action": f"Accept {task_id} before selecting another task.",
            "next_argv": [
                "specify-runtime",
                "implement",
                "task-accept",
                "--feature-dir",
                feature.relative_to(root).as_posix(),
                "--task-id",
                task_id,
                "--format",
                "json",
            ],
        }
    if all(_task_status(task) in _TERMINAL_TASK_STATUSES for task in tasks):
        return {
            "status": "complete",
            "task": None,
            "recommended_next_action": "Run implementation convergence and closeout.",
        }
    statuses = {
        str(task.get("task_id", task.get("id")) or "").upper(): _task_status(task)
        for task in tasks
    }
    blocked_tasks = []
    for task in tasks:
        if _task_status(task) in _TERMINAL_TASK_STATUSES:
            continue
        task_id = str(task.get("task_id", task.get("id")) or "").upper()
        unmet = [
            dependency
            for dependency in _dependencies(task)
            if statuses.get(dependency) not in _TERMINAL_TASK_STATUSES
        ]
        blocked_tasks.append(
            {
                "task_id": task_id,
                "status": _task_status(task),
                "unmet_dependencies": unmet,
            }
        )
    return {
        "status": "blocked",
        "reason_code": "no-dependency-ready-task",
        "task": None,
        "blocked_tasks": blocked_tasks,
        "recommended_next_action": (
            "Recover the recorded in-progress, blocked, or failed task before "
            "requesting the next task."
        ),
    }


def next_task(project_root: Path, feature_dir: Path | str) -> dict[str, Any] | None:
    decision = next_task_decision(project_root, feature_dir)
    if decision["status"] == "ok":
        return decision["task"]
    if decision["status"] == "complete":
        return None
    raise TaskRuntimeError(
        str(decision.get("recommended_next_action") or "task selection is blocked")
    )


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
        raise TaskRuntimeError(
            "execution_mode must be leader-direct, delegated, or managed-team"
        )
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
    if result.status == "success":
        try:
            _validate_task_acceptance_evidence(
                task,
                result_payload.get("validation_results"),
                result_payload.get("blockers"),
            )
        except TaskRuntimeError as exc:
            raise TaskRuntimeError(
                "successful worker result is not acceptance-ready: "
                f"{exc}; task {normalized_id} remains {lifecycle.get('status')}"
            ) from exc
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
    _validate_task_acceptance_evidence(
        task, lifecycle.get("validation"), lifecycle.get("blockers")
    )

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


def reopen_task(
    project_root: Path,
    feature_dir: Path | str,
    task_id: str,
    *,
    expected_task_revision: int,
    expected_workflow_revision: int,
    reason: str,
    evidence: list[str],
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    normalized_id = _normalize_task_id(task_id)
    if expected_task_revision < 1:
        raise TaskRuntimeError("expected_task_revision must be a positive integer")
    if expected_workflow_revision < 0:
        raise TaskRuntimeError("expected_workflow_revision must be non-negative")
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise TaskRuntimeError("task reopen requires a reason")
    normalized_evidence: list[str] = []
    for item in evidence:
        value = str(item).strip()
        if value and value not in normalized_evidence:
            normalized_evidence.append(value)
    if not normalized_evidence:
        raise TaskRuntimeError("task reopen requires at least one evidence item")

    index_path = feature / "task-index.json"
    index_before = _read_state_bytes(index_path, root=feature, label="task-index.json")
    task_index = _task_index(root, feature)
    position, task = _task_entry(task_index, normalized_id)
    if _task_status(task) != "implemented":
        raise TaskRuntimeError(
            f"task {normalized_id} can reopen only when task-index.json records "
            "status implemented"
        )
    lifecycle_path = _lifecycle_path(feature, normalized_id)
    lifecycle_before = _read_state_bytes(
        lifecycle_path, root=feature, label="task lifecycle"
    )
    lifecycle = _read_lifecycle(root, feature, normalized_id)
    if lifecycle.get("status") != "implemented":
        raise TaskRuntimeError(
            f"task {normalized_id} can reopen only from status implemented"
        )
    if str(lifecycle.get("task_id") or "").strip().upper() != normalized_id:
        raise TaskRuntimeError(
            f"task lifecycle identity does not match {normalized_id}"
        )
    current_revision = int(lifecycle.get("revision") or 0)
    if current_revision != expected_task_revision:
        raise TaskRuntimeError(
            "task revision is stale: "
            f"expected {expected_task_revision} but current revision is {current_revision}"
        )

    workflow = _workflow_snapshot(root, feature)
    if int(workflow["revision"]) != expected_workflow_revision:
        raise TaskRuntimeError(
            "workflow revision is stale: "
            f"expected {expected_workflow_revision} but current revision is "
            f"{workflow['revision']}"
        )
    if workflow["present"] and workflow["stage"] not in {"tasks", "implement"}:
        raise TaskRuntimeError(
            "task reopen requires workflow stage tasks or implement, found "
            f"{workflow['stage']}"
        )
    if workflow["present"] and workflow["status"] not in {
        "active",
        "completed",
        "blocked",
    }:
        raise TaskRuntimeError(
            f"task reopen cannot run from workflow status {workflow['status']}"
        )

    acceptance_error: TaskRuntimeError | None = None
    try:
        _validate_task_acceptance_evidence(
            task, lifecycle.get("validation"), lifecycle.get("blockers")
        )
    except TaskRuntimeError as exc:
        acceptance_error = exc
    raw_result_ref = str(lifecycle.get("result_ref") or "").strip()
    expected_result_ref = f"worker-results/{normalized_id}.json"
    indexed_result_ref = str(task.get("result_ref") or "").strip()
    if indexed_result_ref and indexed_result_ref != expected_result_ref:
        raise TaskRuntimeError(
            f"task {normalized_id} task-index result_ref must be "
            f"{expected_result_ref} before it can be reopened"
        )
    if raw_result_ref and raw_result_ref != expected_result_ref:
        raise TaskRuntimeError(
            f"task {normalized_id} result_ref must be {expected_result_ref} "
            "before it can be reopened"
        )
    result_ref = expected_result_ref
    try:
        # Resolve path only when the result exists; a missing path (or a
        # symlinked missing path) must still allow reopen without failing the
        # symlink policy before FileNotFound handling.
        result_path = safe_local_state_path(feature / Path(result_ref), root=feature)
        result_before = read_local_state_bytes(result_path, root=feature)
    except FileNotFoundError:
        result_path = feature / Path(result_ref)
        result_before = None
        previous_result = None
    except (OSError, ValueError) as exc:
        raise TaskRuntimeError(f"cannot read current worker result: {exc}") from exc
    else:
        try:
            previous_result = json.loads(result_before)
        except json.JSONDecodeError as exc:
            raise TaskRuntimeError(
                "current worker result is invalid and cannot be archived safely"
            ) from exc
        if not isinstance(previous_result, dict):
            raise TaskRuntimeError(
                "current worker result is invalid and cannot be archived safely"
            )
    if acceptance_error is None:
        raise TaskRuntimeError(
            f"task {normalized_id} is acceptance-ready; use task-accept instead"
        )

    tasks_path = feature / "tasks.md"
    tasks_before = _read_state_bytes(tasks_path, root=feature, label="tasks.md")
    try:
        tasks_text = tasks_before.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskRuntimeError("tasks.md must be UTF-8") from exc
    projected_tasks = _checkbox_projection(tasks_text, normalized_id, checked=False)
    state_path = _execution_state_path(feature)
    try:
        state_before = read_local_state_bytes(state_path, root=feature)
    except FileNotFoundError:
        state_before = None
    except (OSError, ValueError) as exc:
        raise TaskRuntimeError(f"cannot read execution-state.json: {exc}") from exc
    state = _execution_state(root, feature, task_index)

    history_ref = (
        "implementation-review/task-reopen-history/"
        f"{normalized_id}/revision-{current_revision}.json"
    )
    history_path = feature / Path(history_ref)
    previous = {
        "revision": current_revision,
        "status": lifecycle.get("status"),
        "result_ref": lifecycle.get("result_ref"),
        "result_sha256": _sha256(result_before) if result_before is not None else None,
        "changed_paths": deepcopy(lifecycle.get("changed_paths")),
        "validation": deepcopy(lifecycle.get("validation")),
        "review": deepcopy(lifecycle.get("review")),
        "ui_verification": deepcopy(lifecycle.get("ui_verification")),
        "obligation_evidence": deepcopy(lifecycle.get("obligation_evidence")),
        "blockers": deepcopy(lifecycle.get("blockers")),
        "recovery": deepcopy(lifecycle.get("recovery")),
        "worker_result": deepcopy(previous_result),
    }
    history = {
        "version": 1,
        "task_id": normalized_id,
        "superseded_task_revision": current_revision,
        "workflow_revision": workflow["revision"],
        "workflow_stage": workflow["stage"] or None,
        "workflow_status": workflow["status"] or None,
        "reason": normalized_reason,
        "evidence": normalized_evidence,
        "previous": previous,
    }
    history_content = _json_bytes(history)
    history_sha256 = _sha256(history_content)
    reopened_history = lifecycle.get("reopen_history")
    if not isinstance(reopened_history, list):
        reopened_history = []
    reset_ui = _lifecycle_template(task_index, position, normalized_id)[
        "ui_verification"
    ]
    if isinstance(lifecycle.get("ui_verification"), dict):
        reset_ui["applicable"] = bool(
            lifecycle["ui_verification"].get("applicable", False)
        )
        if reset_ui["applicable"]:
            reset_ui["visual_comparison"] = "unavailable"
            reset_ui["fidelity_status"] = "pending-human-review"
    lifecycle.update(
        {
            "revision": current_revision + 1,
            "status": "ready",
            "result_ref": None,
            "changed_paths": [],
            "validation": [],
            "review": None,
            "ui_verification": reset_ui,
            "obligation_evidence": [],
            "blockers": [],
            "recovery": {
                "history_ref": history_ref,
                "history_sha256": history_sha256,
                "reason": normalized_reason,
                "evidence": normalized_evidence,
            },
            "reopen_history": [
                *deepcopy(reopened_history),
                {
                    "superseded_task_revision": current_revision,
                    "history_ref": history_ref,
                    "history_sha256": history_sha256,
                    "workflow_revision": workflow["revision"],
                    "reason": normalized_reason,
                    "evidence": normalized_evidence,
                },
            ],
        }
    )
    task["status"] = "ready"
    task["result_ref"] = None
    state["revision"] = int(state.get("revision") or 0) + 1
    state["status"] = "executing"
    state["current_task"] = None
    state["next_action"] = (
        f"Start {normalized_id} and submit corrected acceptance-ready validation evidence."
    )
    state["retry_count"] = int(state.get("retry_count") or 0) + 1
    state["completed_task_ids"] = [
        value
        for value in state.get("completed_task_ids", [])
        if str(value) != normalized_id
    ]
    state["failed_task_ids"] = [
        value
        for value in state.get("failed_task_ids", [])
        if str(value) != normalized_id
    ]
    marker = {
        "version": 1,
        "task_id": normalized_id,
        "status": "superseded",
        "history_ref": history_ref,
        "history_sha256": history_sha256,
        "superseded_task_revision": current_revision,
    }
    workflow_path = feature / "workflow.json"
    try:
        receipt = apply_workflow_transaction(
            root,
            kind="implement.task.reopen",
            updates={
                history_path: history_content,
                result_path: _json_bytes(marker),
                lifecycle_path: _json_bytes(lifecycle),
                index_path: _json_bytes(task_index),
                tasks_path: projected_tasks.encode("utf-8"),
                state_path: _json_bytes(state),
                feature / "implement-tracker.md": _render_tracker(feature, state),
            },
            expected_before={
                history_path: None,
                result_path: result_before,
                lifecycle_path: lifecycle_before,
                index_path: index_before,
                tasks_path: tasks_before,
                state_path: state_before,
                workflow_path: workflow["raw"],
            },
        )
    except WorkflowTransactionError as exc:
        raise TaskRuntimeError(str(exc)) from exc
    return {
        **_transaction_receipt(
            receipt,
            task_id=normalized_id,
            revision=current_revision + 1,
            status="ready",
        ),
        "workflow_revision": workflow["revision"],
        "history_ref": history_ref,
        "history_sha256": history_sha256,
        "workflow_resolution_required": workflow["status"] == "blocked",
        **(
            {"resolution_action": workflow["resolution_action"]}
            if workflow["status"] == "blocked"
            else {}
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
        if any(
            statuses.get(value) not in _TERMINAL_TASK_STATUSES for value in dependencies
        ):
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
    "next_task_decision",
    "record_task_result",
    "reopen_task",
    "start_task",
]
