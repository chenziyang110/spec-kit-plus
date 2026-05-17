"""Discovery helpers for cross-project cognition references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def discover_reference_projects(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Find nested Spec Kit projects and report reference-cognition readiness."""
    projects_by_root: dict[Path, dict[str, Any]] = {}
    specify_dirs = [specify_dir for specify_dir in sorted(root.rglob(".specify")) if specify_dir.is_dir()]
    for specify_dir in specify_dirs:
        project_root = specify_dir.parent
        candidate = _reference_project_candidate(project_root)
        if candidate["has_project_cognition_status"]:
            projects_by_root[project_root] = candidate

    projects = [projects_by_root[project_root] for project_root in sorted(projects_by_root)]
    specify_candidates = [_reference_project_candidate(specify_dir.parent) for specify_dir in specify_dirs]
    return {"projects": projects, "specify_candidates": specify_candidates}


def _reference_project_candidate(project_root: Path) -> dict[str, Any]:
    status_path = project_root / ".specify" / "project-cognition" / "status.json"
    db_path = project_root / ".specify" / "project-cognition" / "project-cognition.db"
    status_payload, status_error = _read_status_payload(status_path)
    freshness = _freshness_from_status(status_payload)
    graph_ready = status_payload.get("graph_ready") is True
    has_status = status_path.is_file()
    has_db = db_path.is_file()
    blockers = _reference_readiness_blockers(
        has_status=has_status,
        status_error=status_error,
        freshness=freshness,
        graph_ready=graph_ready,
        has_db=has_db,
    )
    return {
        "root": str(project_root),
        "has_specify_dir": (project_root / ".specify").is_dir(),
        "has_project_cognition_status": has_status,
        "has_project_cognition_db": has_db,
        "status_path": str(status_path) if has_status else None,
        "db_path": str(db_path),
        "freshness": freshness,
        "graph_ready": graph_ready,
        "reference_readiness": "ready" if not blockers else "blocked",
        "blockers": blockers,
    }


def _read_status_payload(status_path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, None
    except json.JSONDecodeError:
        return {}, "status artifact is malformed"
    if not isinstance(payload, dict):
        return {}, "status artifact must contain a JSON object"
    return payload, None


def _freshness_from_status(payload: dict[str, Any]) -> str:
    if not payload:
        return "missing"
    return str(payload.get("freshness", payload.get("baseline_state", "missing"))).strip().lower()


def _reference_readiness_blockers(
    *,
    has_status: bool,
    status_error: str | None,
    freshness: str,
    graph_ready: bool,
    has_db: bool,
) -> list[str]:
    blockers: list[str] = []
    if not has_status:
        blockers.append(".specify/project-cognition/status.json is missing")
    if status_error is not None:
        blockers.append(status_error)
    if has_status and status_error is None and freshness != "fresh":
        blockers.append(f"freshness is {freshness}")
    if has_status and status_error is None and not graph_ready:
        blockers.append("graph_ready is not true")
    if not has_db:
        blockers.append(".specify/project-cognition/project-cognition.db is missing")
    return blockers
