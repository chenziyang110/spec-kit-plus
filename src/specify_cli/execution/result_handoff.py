"""Shared delegated-result handoff path helpers."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.input_transport import resolve_agent_text_input

from .result_normalizer import normalize_worker_task_result_payload
from .result_schema import WorkerTaskResult, worker_task_result_payload


FEATURE_LANE_RESULT_DIRECTORIES = {
    "review": "review-results",
    "plan": "planning/handoffs",
    "tasks": "task-generation/handoffs",
}
WORKSPACE_LANE_RESULT_COMMANDS = frozenset({"quick", "prd-scan"})
STAGE_OWNED_RESULT_COMMANDS = frozenset(
    {*FEATURE_LANE_RESULT_DIRECTORIES, *WORKSPACE_LANE_RESULT_COMMANDS, "debug"}
)


def uses_stage_owned_result_channel(command_name: str) -> bool:
    """Return whether a workflow owns native lane results outside durable teams."""

    return command_name.strip().lower() in STAGE_OWNED_RESULT_COMMANDS


def describe_result_handoff_template(*, command_name: str, integration_key: str) -> str:
    """Return the canonical result handoff template string for a workflow."""

    normalized_command = command_name.strip().lower()
    normalized_integration = integration_key.strip().lower()

    if normalized_command == "deep-research":
        return "FEATURE_DIR/research/handoffs/<track-id>.json"
    if normalized_command in FEATURE_LANE_RESULT_DIRECTORIES:
        directory = FEATURE_LANE_RESULT_DIRECTORIES[normalized_command]
        return f"FEATURE_DIR/{directory}/<lane-id>.json"
    if normalized_command in WORKSPACE_LANE_RESULT_COMMANDS:
        if normalized_command == "prd-scan":
            return "PRD_SCAN_WORKSPACE/worker-results/<lane-id>.json"
        return ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json"
    if normalized_command == "debug":
        return ".planning/debug/results/<session-slug>/<lane-id>.json"
    if normalized_integration == "codex":
        return ".specify/teams/state/results/<request-id>.json"
    if normalized_command == "implement":
        return "FEATURE_DIR/worker-results/<task-id>.json"
    return ".specify/worker-results/<lane-id>.json"


def describe_result_submit_template(*, command_name: str, integration_key: str) -> str:
    """Return the CLI-owned submission route for a delegated result."""

    normalized_command = command_name.strip().lower()
    normalized_integration = integration_key.strip().lower()

    if normalized_command == "deep-research":
        return (
            "`specify-runtime deep-research track-submit "
            "--feature-dir <feature-dir> --track-id <track-id> "
            "--attempt-id <attempt-id> --expected-revision <revision> "
            "--result-json <inline-json|@path|->`"
        )
    if normalized_command == "implement":
        return (
            "return the WorkerTaskResult inline; the leader runs "
            "`specify-runtime implement result-merge --feature-dir <feature-dir> "
            "--result-json <inline-json|@path|-> --format json`"
        )
    if normalized_command in FEATURE_LANE_RESULT_DIRECTORIES:
        return (
            f"`specify-runtime result submit --command {normalized_command} "
            "--feature-dir <feature-dir> "
            "--lane-id <lane-id> --result-json <inline-json|@path|->`"
        )
    if normalized_command in WORKSPACE_LANE_RESULT_COMMANDS:
        return (
            f"`specify-runtime result submit --command {normalized_command} "
            "--workspace <workspace> --lane-id <lane-id> "
            "--result-json <inline-json|@path|->`"
        )
    if normalized_command == "debug":
        return (
            "`specify-runtime result submit --command debug --session-slug "
            "<session-slug> --lane-id <lane-id> --result-json <inline-json|@path|->`"
        )
    if normalized_integration == "codex":
        return (
            "`specify-runtime sp-teams submit-result --request-id <request-id> "
            "--result-json <inline-json|@path|->`"
        )
    return (
        f"`specify-runtime result submit --command {normalized_command or '<command>'} "
        "--lane-id <lane-id> --result-json <inline-json|@path|->`"
    )


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

    if normalized_command == "deep-research":
        raise ValueError(
            "Deep Research track results are runtime-owned; use "
            "specify-runtime deep-research track-submit"
        )
    if normalized_command in FEATURE_LANE_RESULT_DIRECTORIES:
        if feature_dir is None or not lane_id:
            raise ValueError(
                "feature_dir and lane_id are required for "
                f"{normalized_command} result handoff paths"
            )
        directory = FEATURE_LANE_RESULT_DIRECTORIES[normalized_command]
        return Path(feature_dir) / directory / f"{lane_id}.json"

    if normalized_command in WORKSPACE_LANE_RESULT_COMMANDS:
        if quick_workspace is None or not lane_id:
            raise ValueError(
                "quick_workspace and lane_id are required for "
                f"{normalized_command} result handoff paths"
            )
        return Path(quick_workspace) / "worker-results" / f"{lane_id}.json"

    if normalized_command == "debug":
        if not debug_session_slug or not lane_id:
            raise ValueError(
                "debug_session_slug and lane_id are required for debug result handoff paths"
            )
        return (
            project_root
            / ".planning"
            / "debug"
            / "results"
            / debug_session_slug
            / f"{lane_id}.json"
        )

    if normalized_integration == "codex":
        if not request_id:
            raise ValueError("request_id is required for codex result handoff paths")
        return (
            project_root
            / ".specify"
            / "teams"
            / "state"
            / "results"
            / f"{request_id}.json"
        )

    if normalized_command == "implement":
        if feature_dir is None or not task_id:
            raise ValueError(
                "feature_dir and task_id are required for implement result handoff paths"
            )
        return Path(feature_dir) / "worker-results" / f"{task_id}.json"

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

    if isinstance(raw_result, str):
        raw_result = resolve_agent_text_input(
            raw_result,
            project_root=project_root,
            label="result_json",
        )
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
