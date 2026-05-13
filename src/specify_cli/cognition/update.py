"""Transactional update helpers for the SQLite project cognition graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .db import cognition_transaction, ensure_cognition_db, get_active_generation_id, iso_now


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
            "changed_paths": _normalize_paths(changed_paths),
            "affected_nodes": [],
            "missing_coverage": ["project cognition database has no active generation"],
        }

    normalized_paths = _normalize_paths(changed_paths)
    with cognition_transaction(project_root) as conn:
        affected_nodes = _affected_nodes_for_paths(conn, generation_id, normalized_paths)
        if not affected_nodes:
            conn.rollback()
            return {
                "readiness": "needs_update",
                "recommended_next_action": "run_map_update",
                "changed_paths": normalized_paths,
                "affected_nodes": [],
                "missing_coverage": [
                    f"path not covered by project cognition index: {path}" for path in normalized_paths
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

    return {
        "readiness": "ready",
        "recommended_next_action": "retry_current_workflow",
        "update_id": update_id,
        "changed_paths": normalized_paths,
        "affected_nodes": affected_nodes,
        "missing_coverage": [],
    }


def _normalize_paths(paths: list[str]) -> list[str]:
    return [path.replace("\\", "/") for path in paths]


def _affected_nodes_for_paths(conn: Any, generation_id: str, paths: list[str]) -> list[str]:
    if not paths:
        return []
    placeholders = ",".join("?" for _ in paths)
    rows = conn.execute(
        f"SELECT DISTINCT node_id FROM path_index WHERE generation_id = ? AND path IN ({placeholders})",
        (generation_id, *paths),
    ).fetchall()
    return sorted(str(row["node_id"]) for row in rows)
