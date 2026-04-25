"""Diagnostics helpers for the Codex team runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline_check import classify_baseline_build_status, detect_native_build_shell
from .runtime_bridge import codex_team_runtime_status
from .state_paths import codex_team_state_root, executor_record_root, task_record_path


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _tail_text(text: str, *, max_chars: int = 400) -> str:
    normalized = text.strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[-max_chars:]


def _latest_executor_transcript(project_root: Path) -> dict[str, Any] | None:
    root = executor_record_root(project_root)
    candidates = sorted(root.glob("*.runtime.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return None

    path = candidates[0]
    payload = _read_json(path)
    if payload is None:
        return {"path": str(path), "error": "corrupt transcript"}

    state_probe: dict[str, Any] | None = None
    state_root = Path(str(payload.get("state_root", "")).strip()) if payload.get("state_root") else None
    runtime_payload = payload.get("runtime_payload", {})
    if isinstance(runtime_payload, dict) and state_root is not None:
        team_name = str(runtime_payload.get("teamName", "")).strip()
        if team_name:
            team_root = state_root / "team" / team_name
            phase_payload = _read_json(team_root / "phase.json") or {}
            monitor_payload = _read_json(team_root / "monitor-snapshot.json") or {}
            state_probe = {
                "team_name": team_name,
                "state_root": str(state_root),
                "phase": phase_payload.get("current_phase"),
                "phase_updated_at": phase_payload.get("updated_at"),
                "worker_alive_breakdown": monitor_payload.get("workerAliveByName", {}),
                "worker_state_breakdown": monitor_payload.get("workerStateByName", {}),
                "task_status_by_id": monitor_payload.get("taskStatusById", {}),
            }

    return {
        "path": str(path),
        "returncode": payload.get("returncode"),
        "runtime_command": payload.get("runtime_command", []),
        "stderr_tail": _tail_text(str(payload.get("stderr", ""))),
        "stdout_tail": _tail_text(str(payload.get("stdout", ""))),
        "state_probe": state_probe,
    }


def _recent_failed_dispatches(project_root: Path, *, limit: int = 5) -> list[dict[str, Any]]:
    dispatch_root = codex_team_state_root(project_root) / "dispatch"
    candidates = sorted(dispatch_root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    failures: list[dict[str, Any]] = []

    for path in candidates:
        payload = _read_json(path)
        if payload is None:
            continue
        if str(payload.get("status", "")).strip() not in {"failed", "retry_pending"}:
            continue
        failures.append(
            {
                "request_id": payload.get("request_id", path.stem),
                "target_worker": payload.get("target_worker", ""),
                "status": payload.get("status", ""),
                "reason": str(payload.get("reason", "")),
                "updated_at": payload.get("updated_at", ""),
            }
        )
        if len(failures) >= limit:
            break

    return failures


def _recent_batches(project_root: Path, *, limit: int = 5) -> list[dict[str, Any]]:
    batches_root = codex_team_state_root(project_root) / "batches"
    candidates = sorted(batches_root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    batches: list[dict[str, Any]] = []
    baseline = classify_baseline_build_status(project_root)

    for path in candidates[:limit]:
        payload = _read_json(path)
        if payload is None:
            continue
        lane_status = _lane_status_for_batch(project_root, payload)
        repo_verification_status = _repo_verification_status_for_batch(payload, baseline)
        batches.append(
            {
                "batch_id": payload.get("batch_id", path.stem),
                "batch_name": payload.get("batch_name", ""),
                "status": payload.get("status", ""),
                "review_status": payload.get("review_status", ""),
                "task_ids": payload.get("task_ids", []),
                "lane_status": lane_status,
                "repo_verification_status": repo_verification_status,
            }
        )

    return batches


def _lane_status_for_batch(project_root: Path, payload: dict[str, Any]) -> str:
    raw_status = str(payload.get("status", "")).strip()
    if raw_status == "completed":
        for task_id in payload.get("task_ids", []):
            task_payload = _read_json(task_record_path(project_root, str(task_id)))
            metadata = task_payload.get("metadata", {}) if isinstance(task_payload, dict) else {}
            if metadata.get("concerns_present"):
                return "completed_with_concerns"
        return "completed"
    if raw_status in {"failed", "blocked"}:
        return "failed"
    return "unknown"


def _repo_verification_status_for_batch(payload: dict[str, Any], baseline: dict[str, Any]) -> str:
    if baseline["status"] == "blocked":
        return "blocked_by_baseline"
    if baseline["status"] == "clean":
        return "passed"
    if str(payload.get("status", "")).strip() == "failed":
        return "failed"
    return "unknown"


def codex_team_doctor(
    project_root: Path,
    *,
    session_id: str = "default",
    integration_key: str = "codex",
) -> dict[str, Any]:
    """Return a compact diagnostics payload for the Codex team runtime."""

    return {
        "status": codex_team_runtime_status(
            project_root,
            integration_key=integration_key,
            session_id=session_id,
        ),
        "native_build_shell": detect_native_build_shell(project_root),
        "baseline_build": classify_baseline_build_status(project_root),
        "transcript": _latest_executor_transcript(project_root),
        "failed_dispatches": _recent_failed_dispatches(project_root),
        "recent_batches": _recent_batches(project_root),
    }
