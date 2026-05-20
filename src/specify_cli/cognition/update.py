"""Transactional update helpers for the SQLite project cognition graph."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .db import cognition_transaction, ensure_cognition_db, get_active_generation_id, iso_now
from .path_adoption import AdoptablePath, PathCoverageClassification, classify_path_coverage
from .status import read_cognition_status, write_cognition_status
from specify_cli.scan_freshness import cognition_ignored_paths, filter_cognition_ignored_paths


SCAN_BUILD_REASON_TOKENS = {
    "baseline_identity_invalid",
    "explicit_rebuild_requested",
}


def apply_cognition_update(
    project_root: Path,
    *,
    changed_paths: list[str],
    reason: str,
) -> dict[str, Any]:
    """Record a bounded project cognition update for indexed changed paths."""

    ensure_cognition_db(project_root)
    generation_id = get_active_generation_id(project_root)
    normalized_paths = _normalize_paths(changed_paths)
    ignored_paths = cognition_ignored_paths(project_root, normalized_paths)
    update_paths = filter_cognition_ignored_paths(project_root, normalized_paths)
    if not generation_id:
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "update_id": "",
            "changed_paths": update_paths,
            "ignored_paths": ignored_paths,
            "affected_nodes": [],
            "missing_coverage": ["project cognition database has no active generation"],
            "adopted_paths": [],
            "review_paths": [],
            "unadoptable_paths": update_paths,
            "known_unknowns": ["project cognition database has no active generation"],
            "minimal_live_reads": update_paths,
        }

    update_id = f"UPDATE-{uuid4().hex}"
    with cognition_transaction(project_root) as conn:
        affected_nodes, missing_paths, affected_route_records, patched_retrieval_signals = _resolve_path_coverage(
            conn,
            generation_id,
            update_paths,
        )
        affected_node_set = set(affected_nodes)
        affected_route_record_set = set(affected_route_records)
        classification = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=missing_paths,
            requested_paths=update_paths,
        )
        result_state = _result_state_for_update(missing_paths, classification)
        adoptable_paths = list(classification.adoptable_paths)
        adopted_items = adoptable_paths if classification.query_coverage == "adoptable_path_gap" else []
        review_paths = _review_paths_for_update(classification)
        unadoptable_paths = list(classification.unadoptable_paths)
        adopted_route_records = _adopt_paths(
            conn,
            project_root,
            generation_id,
            update_id,
            adopted_items,
        )
        affected_node_set.update(path.node_id for path in adopted_items)
        affected_route_record_set.update(adopted_route_records)
        affected_nodes = sorted(affected_node_set)
        affected_route_records = sorted(affected_route_record_set)
        adopted_paths = [path.path for path in adopted_items]
        minimal_live_reads = sorted(set(review_paths + unadoptable_paths))
        missing_coverage = _missing_coverage_for_gaps(
            review_paths=review_paths,
            unadoptable_paths=unadoptable_paths,
        )
        known_unknowns = list(missing_coverage)
        attrs = {
            "publishing_model": "patch-in-active-generation",
            "patched_retrieval_signals": patched_retrieval_signals,
            "invalidated_retrieval_signals": minimal_live_reads,
            "affected_route_records": affected_route_records,
            "path_adoption": {
                "query_coverage": classification.query_coverage,
                "adopted_paths": adopted_paths,
                "review_paths": review_paths,
                "unadoptable_paths": unadoptable_paths,
                "reasons": list(classification.reasons),
            },
            "adopted_paths": adopted_paths,
            "known_unknowns": known_unknowns,
            "minimal_live_reads": minimal_live_reads,
            "ignored_paths": ignored_paths,
            "confidence": "weak" if adopted_paths or review_paths else "strong",
        }

        conn.execute(
            "INSERT INTO updates("
            "id, generation_id, trigger, changed_paths_json, affected_nodes_json, "
            "affected_claims_json, affected_slices_json, result_state, completed_at, attrs_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                update_id,
                generation_id,
                reason,
                json.dumps(update_paths, separators=(",", ": ")),
                json.dumps(affected_nodes, separators=(",", ": ")),
                "[]",
                "[]",
                result_state,
                iso_now(),
                json.dumps(attrs, separators=(",", ": ")),
            ),
        )

    status = read_cognition_status(project_root)
    has_scan_build_allowed_reason = _has_scan_build_allowed_reason([*status.dirty_reasons, *status.stale_reasons])
    status.last_update_id = update_id
    status.last_refresh_reason = reason
    status.last_refresh_scope = "partial"
    status.last_refresh_basis = "project-cognition update"
    status.last_refresh_changed_files_basis = list(update_paths)
    if result_state == "needs_rebuild":
        status.baseline_state = "blocked"
        status.freshness = "stale"
        status.stale_paths = list(unadoptable_paths)
        status.stale_reasons = list(missing_coverage)
        status.dirty_reasons = list(missing_coverage)
        status.dirty_origin_command = "sp-map-update"
    elif result_state == "review" and not has_scan_build_allowed_reason:
        _mark_status_baseline_ready(status, generation_id)
        status.freshness = "possibly_stale"
        status.stale_paths = list(review_paths)
        status.stale_reasons = list(missing_coverage)
        status.dirty_reasons = []
        status.dirty_origin_command = ""
    elif result_state == "ready" and not has_scan_build_allowed_reason:
        _mark_status_baseline_ready(status, generation_id)
        if adopted_paths or not missing_paths:
            status.freshness = "fresh"
        status.stale_paths = []
        status.stale_reasons = []
        status.dirty_reasons = []
        status.dirty_origin_command = ""
    elif (
        status.baseline_state == "blocked"
        and status.dirty_origin_command == "sp-map-update"
        and not has_scan_build_allowed_reason
    ):
        _mark_status_baseline_ready(status, generation_id)
        status.stale_paths = []
        status.stale_reasons = []
        status.dirty_reasons = []
        status.dirty_origin_command = ""
    write_cognition_status(project_root, status)

    return {
        "readiness": result_state,
        "recommended_next_action": _recommended_action_for_update_result(result_state),
        "update_id": update_id,
        "changed_paths": update_paths,
        "ignored_paths": ignored_paths,
        "affected_nodes": affected_nodes,
        "missing_coverage": missing_coverage,
        "adopted_paths": adopted_paths,
        "review_paths": review_paths,
        "unadoptable_paths": unadoptable_paths,
        "known_unknowns": known_unknowns,
        "minimal_live_reads": minimal_live_reads,
    }


def _mark_status_baseline_ready(status: Any, generation_id: str) -> None:
    status.baseline_state = "ready"
    status.graph_ready = True
    status.graph_store_path = status.graph_store_path or ".specify/project-cognition/project-cognition.db"
    status.active_generation_id = status.active_generation_id or generation_id


def _has_scan_build_allowed_reason(reasons: list[str]) -> bool:
    reason_text = " ".join(str(reason or "") for reason in reasons).lower()
    compact_reason_text = reason_text.replace("-", "_").replace(" ", "_")
    return any(token in compact_reason_text for token in SCAN_BUILD_REASON_TOKENS)


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


def _adopt_paths(
    conn: Any,
    project_root: Path,
    generation_id: str,
    update_id: str,
    adoptable_paths: list[AdoptablePath],
) -> list[str]:
    route_records: list[str] = []
    for index, path in enumerate(adoptable_paths, start=1):
        now = iso_now()
        evidence_id = f"{update_id}-E-{index}"
        path_index_id = f"{update_id}-P-{index}"
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES (?, ?, 'path_adoption', ?, '', '', 'map-update-adoption', ?, ?, ?)",
            (
                evidence_id,
                generation_id,
                path.path,
                _adoption_content_hash(project_root, update_id, path.path),
                now,
                json.dumps(
                    {
                        "nearest_indexed_sibling": path.nearest_indexed_sibling,
                        "adoption_status": "provisional",
                        "adoption_reason": path.reason,
                        "update_id": update_id,
                    },
                    separators=(",", ": "),
                ),
            ),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES (?, ?, ?, ?, 'provisional_path', ?, ?, ?)",
            (
                path_index_id,
                generation_id,
                path.path,
                path.node_id,
                path.confidence,
                evidence_id,
                now,
            ),
        )
        route_records.append(path_index_id)
    return route_records


def _adoption_content_hash(project_root: Path, update_id: str, path: str) -> str:
    file_path = project_root / path
    if file_path.exists() and file_path.is_file():
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    return hashlib.sha256(f"{update_id}:{path}".encode("utf-8")).hexdigest()


def _result_state_for_update(
    missing_paths: list[str],
    classification: PathCoverageClassification,
) -> str:
    if not missing_paths:
        return "ready"
    if classification.query_coverage == "adoptable_path_gap":
        return "ready"
    if classification.query_coverage == "uncertain_path_gap":
        return "review"
    return "needs_rebuild"


def _review_paths_for_update(classification: PathCoverageClassification) -> list[str]:
    review_paths = list(classification.review_paths)
    if classification.query_coverage == "uncertain_path_gap":
        review_paths.extend(path.path for path in classification.adoptable_paths)
    return _unique_ordered(review_paths)


def _unique_ordered(paths: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result


def _missing_coverage_for_gaps(
    *,
    review_paths: list[str],
    unadoptable_paths: list[str],
) -> list[str]:
    return [
        *[
            f"path requires minimal live read before adoption: {path}"
            for path in review_paths
        ],
        *[
            f"path not safely adoptable by project cognition index: {path}"
            for path in unadoptable_paths
        ],
    ]


def _recommended_action_for_update_result(result_state: str) -> str:
    if result_state == "review":
        return "perform_minimal_live_reads"
    if result_state == "needs_rebuild":
        return "run_map_scan_build"
    return "retry_current_workflow"
