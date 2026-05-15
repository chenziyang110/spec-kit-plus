"""Transactional update helpers for the SQLite project cognition graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .db import cognition_transaction, ensure_cognition_db, get_active_generation_id, iso_now
from .status import read_cognition_status, write_cognition_status


def apply_cognition_update(
    project_root: Path,
    *,
    changed_paths: list[str],
    reason: str,
) -> dict[str, Any]:
    """Record a bounded project cognition update for indexed changed paths."""

    ensure_cognition_db(project_root)
    generation_id = get_active_generation_id(project_root)
    if not generation_id:
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "update_id": "",
            "changed_paths": _normalize_paths(changed_paths),
            "affected_nodes": [],
            "missing_coverage": ["project cognition database has no active generation"],
        }

    normalized_paths = _normalize_paths(changed_paths)
    with cognition_transaction(project_root) as conn:
        affected_nodes, missing_paths = _resolve_path_coverage(conn, generation_id, normalized_paths)
        if missing_paths:
            conn.rollback()
            return {
                "readiness": "needs_update",
                "recommended_next_action": "run_map_update",
                "update_id": "",
                "changed_paths": normalized_paths,
                "affected_nodes": [],
                "missing_coverage": [
                    f"path not covered by project cognition index: {path}" for path in missing_paths
                ],
            }

        update_id = f"UPDATE-{uuid4().hex}"
        conn.execute(
            "INSERT INTO updates("
            "id, generation_id, trigger, changed_paths_json, affected_nodes_json, "
            "affected_claims_json, affected_slices_json, result_state, completed_at, attrs_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                update_id,
                generation_id,
                reason,
                json.dumps(normalized_paths, separators=(",", ": ")),
                json.dumps(affected_nodes, separators=(",", ": ")),
                "[]",
                "[]",
                "ready",
                iso_now(),
                "{}",
            ),
        )

    status = read_cognition_status(project_root)
    status.last_update_id = update_id
    status.stale_paths = []
    status.stale_reasons = []
    status.last_refresh_reason = reason
    status.last_refresh_scope = "partial"
    status.last_refresh_basis = "project-cognition update"
    status.last_refresh_changed_files_basis = list(normalized_paths)
    write_cognition_status(project_root, status)

    return {
        "readiness": "ready",
        "recommended_next_action": "retry_current_workflow",
        "update_id": update_id,
        "changed_paths": normalized_paths,
        "affected_nodes": affected_nodes,
        "missing_coverage": [],
    }


def _normalize_paths(paths: list[str]) -> list[str]:
    normalized_paths: list[str] = []
    seen: set[str] = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_paths.append(normalized)
    return normalized_paths


def _resolve_path_coverage(conn: Any, generation_id: str, paths: list[str]) -> tuple[list[str], list[str]]:
    affected_nodes: set[str] = set()
    missing_paths: list[str] = []
    for path in paths:
        rows = conn.execute(
            "SELECT node_id FROM path_index WHERE generation_id = ? AND path = ?",
            (generation_id, path),
        ).fetchall()
        if not rows:
            missing_paths.append(path)
            continue
        affected_nodes.update(str(row["node_id"]) for row in rows)
    return sorted(affected_nodes), missing_paths
