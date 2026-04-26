"""Shared delegated-result handoff path helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .result_normalizer import normalize_worker_task_result_payload
from .result_schema import WorkerTaskResult, worker_task_result_payload


def describe_result_handoff_template(*, command_name: str, integration_key: str) -> str:
    """Return the canonical result handoff template string for a workflow."""

    normalized_command = command_name.strip().lower()
    normalized_integration = integration_key.strip().lower()

    if normalized_integration == "codex":
        return ".specify/codex-team/state/results/<request-id>.json"
    if normalized_command == "implement":
        return "FEATURE_DIR/worker-results/<task-id>.json"
    if normalized_command == "quick":
        return ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json"
    if normalized_command == "debug":
        return ".planning/debug/results/<session-slug>/<lane-id>.json"
    return ".specify/worker-results/<lane-id>.json"


def build_result_handoff_path(
    project_root: Path,
    *,
    command_name: str,
    integration_key: str,
    request_id: str | None = None,
    feature_dir: Path | None = None,
    task_id: str | None = None,
    quick_workspace: Path | None = None,
    debug_session_slug: str | None = None,
    lane_id: str | None = None,
) -> Path:
    """Build the canonical delegated-result handoff path for a workflow."""

    normalized_command = command_name.strip().lower()
    normalized_integration = integration_key.strip().lower()

    if normalized_integration == "codex":
        if not request_id:
            raise ValueError("request_id is required for codex result handoff paths")
        return project_root / ".specify" / "codex-team" / "state" / "results" / f"{request_id}.json"

    if normalized_command == "implement":
        if feature_dir is None or not task_id:
            raise ValueError("feature_dir and task_id are required for implement result handoff paths")
        return Path(feature_dir) / "worker-results" / f"{task_id}.json"

    if normalized_command == "quick":
        if quick_workspace is None or not lane_id:
            raise ValueError("quick_workspace and lane_id are required for quick result handoff paths")
        return Path(quick_workspace) / "worker-results" / f"{lane_id}.json"

    if normalized_command == "debug":
        if not debug_session_slug or not lane_id:
            raise ValueError("debug_session_slug and lane_id are required for debug result handoff paths")
        return project_root / ".planning" / "debug" / "results" / debug_session_slug / f"{lane_id}.json"

    if not lane_id:
        raise ValueError("lane_id is required for generic result handoff paths")
    return project_root / ".specify" / "worker-results" / f"{lane_id}.json"


def write_normalized_result_handoff(
    project_root: Path,
    *,
    command_name: str,
    integration_key: str,
    raw_result: object,
    request_id: str | None = None,
    feature_dir: Path | None = None,
    task_id: str | None = None,
    quick_workspace: Path | None = None,
    debug_session_slug: str | None = None,
    lane_id: str | None = None,
) -> tuple[Path, WorkerTaskResult]:
    """Normalize a worker result and persist it to the canonical handoff path."""

    normalized = normalize_worker_task_result_payload(raw_result)
    if normalized.status == "pending":
        raise ValueError(
            "Pending result templates cannot be written to the canonical handoff path. "
            "Replace the placeholder with a real success, blocked, or failed result first."
        )
    target_path = build_result_handoff_path(
        project_root,
        command_name=command_name,
        integration_key=integration_key,
        request_id=request_id,
        feature_dir=feature_dir,
        task_id=task_id,
        quick_workspace=quick_workspace,
        debug_session_slug=debug_session_slug,
        lane_id=lane_id,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(
            worker_task_result_payload(normalized),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return target_path, normalized
