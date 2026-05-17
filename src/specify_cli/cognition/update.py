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
        affected_nodes, missing_paths, affected_route_records, patched_retrieval_signals = _resolve_path_coverage(
            conn,
            generation_id,
            normalized_paths,
        )
        missing_coverage = [f"path not covered by project cognition index: {path}" for path in missing_paths]
        result_state = "partial_refresh" if missing_paths else "ready"
        attrs = {
            "publishing_model": "patch-in-active-generation",
            "patched_retrieval_signals": patched_retrieval_signals,
            "invalidated_retrieval_signals": missing_paths,
            "affected_route_records": affected_route_records,
            "known_unknowns": missing_coverage,
            "minimal_live_reads": missing_paths,
            "confidence": "partial" if missing_paths else "strong",
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
                result_state,
                iso_now(),
                json.dumps(attrs, separators=(",", ": ")),
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
        "readiness": result_state,
        "recommended_next_action": "review_missing_coverage" if missing_paths else "retry_current_workflow",
        "update_id": update_id,
        "changed_paths": normalized_paths,
        "affected_nodes": affected_nodes,
        "missing_coverage": missing_coverage,
        "known_unknowns": missing_coverage,
        "minimal_live_reads": missing_paths,
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


def _resolve_path_coverage(
    conn: Any,
    generation_id: str,
    paths: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    affected_nodes: set[str] = set()
    affected_route_records: set[str] = set()
    missing_paths: list[str] = []
    patched_retrieval_signals: list[str] = []
    for path in paths:
        rows = conn.execute(
            "SELECT id, node_id FROM path_index WHERE generation_id = ? AND path = ?",
            (generation_id, path),
        ).fetchall()
        if not rows:
            missing_paths.append(path)
            continue
        patched_retrieval_signals.append(path)
        affected_nodes.update(str(row["node_id"]) for row in rows)
        affected_route_records.update(str(row["id"]) for row in rows)
    return sorted(affected_nodes), missing_paths, sorted(affected_route_records), patched_retrieval_signals
