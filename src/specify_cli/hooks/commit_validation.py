"""Shared commit validation hook."""

from __future__ import annotations

import json
from pathlib import Path
import re

from .checkpoint_serializers import serialize_implement_tracker
from .events import WORKFLOW_COMMIT_VALIDATE
from .types import HookResult, QualityHookError


COMMIT_MESSAGE_RE = re.compile(r"^(feat|fix|docs|refactor|test|chore)(\([^)]+\))?:\s+\S", re.IGNORECASE)
TASK_RE = re.compile(r"(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b")
TERMINAL_TRACKER_STATUSES = {"resolved"}
VALID_TRACKER_STATUSES = {
    "gathering",
    "executing",
    "recovering",
    "replanning",
    "validating",
    "blocked",
    "resolved",
}
VALID_COMMIT_INTENTS = {"finalize", "external-evidence-checkpoint"}


def _is_nonempty_evidence(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and all(isinstance(item, str) and item.strip() for item in value)
    return False


def _task_states(feature_dir: Path) -> dict[str, bool]:
    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.is_file():
        return {}
    try:
        text = tasks_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return {
        match.group("task_id").upper(): match.group("checked").lower() == "x"
        for match in TASK_RE.finditer(text)
    }


def _task_index_bindings(feature_dir: Path) -> tuple[set[str] | None, str]:
    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return None, ""
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set(), ""
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        return set(), ""
    task_ids = {
        str(item.get("task_id") or item.get("id") or "").strip().upper()
        for item in payload["tasks"]
        if isinstance(item, dict)
    }
    task_ids.discard("")
    return task_ids, str(payload.get("source_revision") or "").strip()


def _valid_mandatory_external_blocker(blocker: object) -> bool:
    if not isinstance(blocker, dict):
        return False
    required_fields = {
        "classification",
        "owner",
        "evidence",
        "exact_next_action",
        "approval_question",
        "unblock_criteria",
        "implementation_can_continue",
        "completion_impact",
    }
    if not required_fields.issubset(blocker):
        return False
    if blocker.get("classification") not in {
        "external",
        "human-action",
        "verification_policy",
    }:
        return False
    if blocker.get("owner") not in {"user", "maintainer", "external-system"}:
        return False
    if blocker.get("completion_impact") != "mandatory_for_completion":
        return False
    if not _is_nonempty_evidence(blocker.get("evidence")):
        return False
    if not str(blocker.get("exact_next_action") or "").strip():
        return False
    if not str(blocker.get("unblock_criteria") or "").strip():
        return False
    if not isinstance(blocker.get("implementation_can_continue"), bool):
        return False
    approval_question = blocker.get("approval_question")
    if approval_question is not None and not isinstance(approval_question, str):
        return False
    return not (
        blocker.get("owner") in {"user", "maintainer"}
        and not str(approval_question or "").strip()
    )


def _mandatory_external_evidence_tasks(feature_dir: Path) -> list[str]:
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    if not lifecycle_dir.is_dir():
        return []

    task_states = _task_states(feature_dir)
    indexed_task_ids, index_revision = _task_index_bindings(feature_dir)
    task_ids: list[str] = []
    for path in sorted(lifecycle_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or str(payload.get("status") or "").lower() != "blocked":
            continue
        task_id = str(payload.get("task_id") or "").strip().upper()
        if not task_id or task_id != path.stem.upper():
            continue
        if task_id not in task_states or task_states[task_id]:
            continue
        if indexed_task_ids is not None and task_id not in indexed_task_ids:
            continue
        if index_revision and str(payload.get("source_revision") or "").strip() != index_revision:
            continue
        blockers = payload.get("blockers")
        if not isinstance(blockers, list) or not blockers:
            continue
        for blocker in blockers:
            if _valid_mandatory_external_blocker(blocker):
                task_ids.append(task_id)
                break
    return task_ids


def commit_validation_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    commit_message = str(payload.get("commit_message") or "").strip()
    if not commit_message:
        raise QualityHookError("commit_message is required")

    errors: list[str] = []
    commit_intent = str(payload.get("commit_intent") or "finalize").strip().lower()
    if commit_intent not in VALID_COMMIT_INTENTS:
        errors.append(
            "commit_intent must be finalize or external-evidence-checkpoint"
        )
    if not COMMIT_MESSAGE_RE.match(commit_message):
        errors.append("commit message must follow conventional commit format")

    raw_feature_dir = str(payload.get("feature_dir") or "").strip()
    checkpoint_tasks: list[str] = []
    if raw_feature_dir:
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()
        else:
            feature_dir = feature_dir.resolve()
        try:
            feature_dir.relative_to(project_root.resolve())
        except ValueError:
            errors.append("feature_dir must resolve inside project_root")
            feature_dir = project_root.resolve() / ".invalid-feature-dir"
        tracker_path = feature_dir / "implement-tracker.md"
        if tracker_path.exists():
            tracker = serialize_implement_tracker(tracker_path)
            tracker_status = str(tracker.get("status") or "").strip().lower()
            if tracker_status not in VALID_TRACKER_STATUSES:
                errors.append(
                    "implement-tracker status must be one of: "
                    + ", ".join(sorted(VALID_TRACKER_STATUSES))
                )
            elif tracker_status not in TERMINAL_TRACKER_STATUSES:
                if commit_intent == "external-evidence-checkpoint":
                    checkpoint_tasks = _mandatory_external_evidence_tasks(feature_dir)
                    if not checkpoint_tasks:
                        errors.append(
                            "external-evidence-checkpoint requires a task-local mandatory external "
                            "or human verification blocker"
                        )
                else:
                    errors.append(
                        f"implement-tracker is still {tracker_status}; commit should not finalize this workflow yet"
                    )
            elif commit_intent == "external-evidence-checkpoint":
                errors.append(
                    "external-evidence-checkpoint requires a nonterminal implement-tracker"
                )
        elif commit_intent == "external-evidence-checkpoint":
            errors.append(
                "external-evidence-checkpoint requires a nonterminal implement-tracker"
            )
    elif commit_intent == "external-evidence-checkpoint":
        errors.append(
            "external-evidence-checkpoint requires feature_dir and a task-local mandatory external blocker"
        )

    if errors:
        return HookResult(
            event=WORKFLOW_COMMIT_VALIDATE,
            status="blocked",
            severity="critical",
            errors=errors,
        )

    return HookResult(
        event=WORKFLOW_COMMIT_VALIDATE,
        status="ok",
        severity="info",
        data={
            "commit_message": commit_message,
            "commit_intent": commit_intent,
            "workflow_finalized": commit_intent == "finalize",
            "checkpoint_task_ids": checkpoint_tasks,
        },
    )
