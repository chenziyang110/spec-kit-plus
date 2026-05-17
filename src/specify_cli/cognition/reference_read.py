"""Fresh-only reference reads for project cognition artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import cognition_db_path, cognition_status_path, graph_dir, graph_slices_dir


class ReferenceProjectReadError(RuntimeError):
    """Raised when a reference project's cognition artifacts cannot be read."""


def _read_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReferenceProjectReadError(
            f"{kind} artifact is missing: {path.as_posix()}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ReferenceProjectReadError(
            f"{kind} artifact is malformed: {path.as_posix()}"
        ) from exc
    if not isinstance(payload, dict):
        raise ReferenceProjectReadError(
            f"{kind} artifact must contain a JSON object: {path.as_posix()}"
        )
    return payload


def _relative_cognition_path(path: Path, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _freshness_from_status(payload: dict[str, Any]) -> str:
    freshness = payload.get("freshness", payload.get("baseline_state", "missing"))
    return str(freshness).strip().lower()


def _json_artifact_name(name: str, *, kind: str) -> str:
    value = name.strip()
    if not value:
        raise ReferenceProjectReadError(f"{kind} name must not be empty")
    path = Path(value)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise ReferenceProjectReadError(f"{kind} name must stay within project cognition")
    if path.suffix != ".json":
        path = path.with_suffix(".json")
    if len(path.parts) != 1:
        raise ReferenceProjectReadError(f"{kind} name must be a single artifact name")
    return path.name


def read_reference_project_cognition(
    project_root: Path,
    *,
    slice_name: str,
    include_graph: list[str] | None = None,
) -> dict[str, Any]:
    """Read the minimal fresh project-cognition artifacts for a reference project."""
    status_path = cognition_status_path(project_root)
    status_payload = _read_json(status_path, kind="status")
    freshness = _freshness_from_status(status_payload)
    if freshness != "fresh":
        raise ReferenceProjectReadError(
            f"fresh-only reference read rejected: project cognition freshness is {freshness}"
        )
    if status_payload.get("graph_ready") is not True:
        raise ReferenceProjectReadError(
            "fresh-only reference read rejected: project cognition graph_ready is not true"
        )
    db_path = cognition_db_path(project_root)
    if not db_path.is_file():
        raise ReferenceProjectReadError(
            f"fresh-only reference read rejected: project-cognition.db is missing: {db_path.as_posix()}"
        )

    slice_artifact = _json_artifact_name(slice_name, kind="slice")
    slice_path = graph_slices_dir(project_root) / slice_artifact
    slice_payload = _read_json(slice_path, kind="slice")
    slice_record = dict(slice_payload.get("slice", {}))
    slice_record.setdefault("slice_id", Path(slice_artifact).stem)

    graph_payload: dict[str, Any] = {}
    minimal_read_order = [
        _relative_cognition_path(status_path, project_root),
        _relative_cognition_path(slice_path, project_root),
    ]
    for graph_name in include_graph or []:
        graph_artifact = _json_artifact_name(graph_name, kind="graph")
        graph_path = graph_dir(project_root) / graph_artifact
        graph_key = Path(graph_artifact).stem
        graph_payload[graph_key] = _read_json(graph_path, kind="graph")
        minimal_read_order.append(_relative_cognition_path(graph_path, project_root))

    return {
        "admission": {
            "freshness": freshness,
        },
        "slice": slice_record,
        "graph": graph_payload,
        "provenance": {
            "project_root": str(project_root),
            "status_path": str(status_path),
        },
        "minimal_read_order": minimal_read_order,
    }
