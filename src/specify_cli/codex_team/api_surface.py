"""Reusable structured control surface for Codex team operations."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from specify_cli.project_map_status import inspect_project_map_freshness

from . import task_ops
from .auto_dispatch import AutoDispatchError, complete_dispatched_batch, route_ready_parallel_batch
from .doctor import codex_team_doctor
from .live_probe import codex_team_live_probe
from .result_template import build_request_result_template, normalize_result_submission
from .runtime_bridge import (
    RuntimeEnvironmentError,
    codex_team_runtime_status,
    submit_runtime_result,
)

INTEGRATION_JSON = ".specify/integration.json"


class TeamApiError(ValueError):
    """Raised when a structured Codex team operation cannot be executed."""


def _require_spec_kit_plus_project(project_root: Path) -> None:
    if not (project_root / ".specify").exists():
        raise TeamApiError("Not a Spec Kit Plus project (no .specify/ directory).")


def _read_integration_json(project_root: Path) -> dict[str, Any]:
    path = project_root / INTEGRATION_JSON
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TeamApiError(f"{path} contains invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise TeamApiError(f"{path} must contain a JSON object.")
    return data


def _require_codex_team_project(project_root: Path) -> str:
    _require_spec_kit_plus_project(project_root)
    current = _read_integration_json(project_root)
    integration_key = str(current.get("integration") or "").strip()
    if integration_key != "codex":
        raise TeamApiError("Codex team runtime is only available for Codex integration projects.")
    return integration_key


def run_team_api_operation(
    project_root: Path,
    operation: str,
    *,
    feature_dir: str | None = None,
    batch_id: str | None = None,
    request_id: str | None = None,
    result_file: str | None = None,
    session_id: str = "default",
) -> dict[str, Any]:
    """Run a structured Codex team control-plane operation and return a JSON envelope."""

    integration_key = _require_codex_team_project(project_root)
    envelope: dict[str, Any] = {"operation": operation, "status": "ok", "payload": {}}

    if operation == "status":
        envelope["payload"] = codex_team_runtime_status(
            project_root,
            integration_key=integration_key,
            session_id=session_id,
        )
        return envelope

    if operation == "doctor":
        envelope["payload"] = codex_team_doctor(
            project_root,
            session_id=session_id,
            integration_key=integration_key,
        )
        return envelope

    if operation == "live-probe":
        try:
            envelope["payload"] = codex_team_live_probe(
                project_root,
                session_id=session_id,
                integration_key=integration_key,
            )
        except RuntimeEnvironmentError as exc:
            envelope["status"] = "error"
            envelope["payload"] = {"message": str(exc)}
        return envelope

    if operation == "tasks":
        records = task_ops.list_tasks(project_root)
        envelope["payload"] = {"tasks": [asdict(record) for record in records]}
        return envelope

    if operation == "auto-dispatch":
        if not feature_dir:
            raise TeamApiError("--feature-dir is required for auto-dispatch.")
        freshness = inspect_project_map_freshness(project_root)
        if freshness["freshness"] in {"missing", "stale"}:
            envelope["status"] = "error"
            envelope["payload"] = {
                "message": f"Project-map freshness is {freshness['freshness']}. Run map-scan then map-build before auto-dispatch.",
                "freshness": freshness["freshness"],
                "reasons": freshness.get("reasons", []),
            }
            return envelope
        try:
            result = route_ready_parallel_batch(
                project_root,
                feature_dir=(project_root / feature_dir).resolve(),
                session_id=session_id,
            )
        except AutoDispatchError as exc:
            envelope["status"] = "error"
            envelope["payload"] = {"message": str(exc)}
        else:
            envelope["payload"] = {
                "feature_dir": str(result.feature_dir),
                "batch_id": result.batch_id,
                "batch_name": result.batch_name,
                "join_point_name": result.join_point_name,
                "dispatched_task_ids": result.dispatched_task_ids,
                "request_ids": result.request_ids,
            }
        return envelope

    if operation == "complete-batch":
        if not batch_id:
            raise TeamApiError("--batch-id is required for complete-batch.")
        try:
            result = complete_dispatched_batch(
                project_root,
                batch_id=batch_id,
                session_id=session_id,
            )
        except AutoDispatchError as exc:
            envelope["status"] = "error"
            envelope["payload"] = {"message": str(exc)}
        else:
            envelope["payload"] = {
                "batch_id": result.batch_id,
                "batch_name": result.batch_name,
                "status": result.status,
                "join_point_name": result.join_point_name,
                "task_ids": result.task_ids,
                "next_batch_id": result.next_batch_id,
                "next_batch_name": result.next_batch_name,
                "next_dispatched_task_ids": result.next_dispatched_task_ids or [],
            }
        return envelope

    if operation == "submit-result":
        if not request_id:
            raise TeamApiError("--request-id is required for submit-result.")
        if not result_file:
            raise TeamApiError("--result-file is required for submit-result.")
        result_path = Path(result_file)
        if not result_path.is_absolute():
            result_path = (project_root / result_path).resolve()
        if not result_path.exists():
            envelope["status"] = "error"
            envelope["payload"] = {"message": f"Result file not found: {result_path}"}
            return envelope
        try:
            result = normalize_result_submission(
                project_root,
                request_id,
                result_path.read_text(encoding="utf-8"),
            )
            record = submit_runtime_result(
                project_root,
                session_id=session_id,
                request_id=request_id,
                result=result,
            )
        except Exception as exc:
            envelope["status"] = "error"
            envelope["payload"] = {"message": str(exc)}
        else:
            envelope["payload"] = {
                "request_id": record.request_id,
                "target_worker": record.target_worker,
                "status": record.status,
                "result_path": record.result_path,
            }
        return envelope

    if operation == "result-template":
        if not request_id:
            raise TeamApiError("--request-id is required for result-template.")
        try:
            envelope["payload"] = build_request_result_template(project_root, request_id)
        except Exception as exc:
            envelope["status"] = "error"
            envelope["payload"] = {"message": str(exc)}
        return envelope

    raise TeamApiError(f"Unknown API operation '{operation}'.")


__all__ = ["TeamApiError", "run_team_api_operation"]
