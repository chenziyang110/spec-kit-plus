"""Task-local query API for the SQLite project cognition graph."""

from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from typing import Any

from .db import connect_cognition_db, ensure_cognition_db, get_active_generation_id


def normalize_query_token(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def query_project_cognition(
    project_root: Path,
    *,
    intent: str,
    query_text: str = "",
    expanded_queries: list[str] | None = None,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    ensure_cognition_db(project_root)
    query_plan = _query_plan_payload(query_text=query_text, expanded_queries=expanded_queries, paths=paths)
    generation_id = get_active_generation_id(project_root)
    if not generation_id:
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "intent": intent,
            "query": query_text,
            "query_plan": query_plan,
            "capability_candidates": [],
            "symptom_candidates": [],
            "affected_nodes": [],
            "minimal_live_reads": [],
            "missing_coverage": ["project cognition database has no active generation"],
            "subgraph": {"nodes": [], "edges": [], "claims": [], "conflicts": []},
        }

    normalized_paths = [path.replace("\\", "/") for path in (paths or [])]
    with closing(connect_cognition_db(project_root)) as conn:
        path_nodes, missing_paths = _resolve_paths(conn, generation_id, normalized_paths)
        candidates = _merge_candidates(
            _resolve_aliases(conn, generation_id, query_text)
            + _resolve_claim_fts(conn, generation_id, query_text)
            + _resolve_expanded_queries(conn, generation_id, expanded_queries or [])
        )
        if not candidates and path_nodes:
            candidates = [
                {
                    "node_id": node_id,
                    "label": _node_title(conn, generation_id, node_id),
                    "target_type": "node",
                    "score": 0.8,
                    "matched_by": ["path_index"],
                    "evidence_ids": sorted(evidence_ids),
                }
                for node_id, evidence_ids in path_nodes.items()
            ]

        query_missed_runtime_index = (
            bool(normalize_query_token(query_text)) and not missing_paths and not path_nodes and not candidates
        )
        readiness = "review" if query_missed_runtime_index else (
            "needs_update" if missing_paths else _readiness_for_candidates(candidates)
        )
        affected_nodes = sorted(
            set(path_nodes.keys()) | {item["node_id"] for item in candidates if item["target_type"] != "symptom"}
        )
        minimal_live_reads = sorted(set(normalized_paths) | set(_paths_for_nodes(conn, generation_id, affected_nodes)))
        if query_missed_runtime_index:
            minimal_live_reads = _fallback_review_paths(conn, generation_id)
        missing_coverage = [f"path not covered by project cognition index: {path}" for path in missing_paths]
        if query_missed_runtime_index:
            missing_coverage.append(
                "query did not match project cognition aliases or claims; use minimal live reads or ask a clarifying question"
            )

        return {
            "readiness": readiness,
            "recommended_next_action": _recommended_action(readiness),
            "intent": intent,
            "query": query_text,
            "query_plan": query_plan,
            "capability_candidates": [item for item in candidates if item["target_type"] in {"capability", "node"}],
            "symptom_candidates": [item for item in candidates if item["target_type"] == "symptom"],
            "affected_nodes": affected_nodes,
            "minimal_live_reads": minimal_live_reads,
            "missing_coverage": missing_coverage,
            "subgraph": _subgraph_for_nodes(conn, generation_id, affected_nodes),
        }


def _resolve_paths(conn: Any, generation_id: str, paths: list[str]) -> tuple[dict[str, set[str]], list[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    missing: list[str] = []
    for path in paths:
        rows = conn.execute(
            "SELECT node_id, evidence_id FROM path_index WHERE generation_id = ? AND path = ?",
            (generation_id, path),
        ).fetchall()
        if not rows:
            missing.append(path)
            continue
        for row in rows:
            result[str(row["node_id"])].add(str(row["evidence_id"]))
    return result, missing


def _query_plan_payload(
    *,
    query_text: str,
    expanded_queries: list[str] | None,
    paths: list[str] | None,
) -> dict[str, Any]:
    return {
        "raw_query": query_text,
        "expanded_queries": [query for query in (expanded_queries or []) if normalize_query_token(query)],
        "paths": [path.replace("\\", "/") for path in (paths or []) if normalize_query_token(path)],
    }


def _resolve_aliases(conn: Any, generation_id: str, query_text: str) -> list[dict[str, Any]]:
    normalized_query = normalize_query_token(query_text)
    if not normalized_query:
        return []

    candidates: list[dict[str, Any]] = []
    for token in _query_tokens(normalized_query):
        rows = conn.execute(
            "SELECT alias, target_type, target_id, confidence, evidence_id FROM alias_index "
            "WHERE generation_id = ? AND normalized_alias = ?",
            (generation_id, token),
        ).fetchall()
        for row in rows:
            candidates.append(
                {
                    "node_id": str(row["target_id"]),
                    "label": _node_title(conn, generation_id, str(row["target_id"])),
                    "target_type": str(row["target_type"]),
                    "score": _score_for_confidence(str(row["confidence"])),
                    "matched_by": [f"alias:{row['alias']}"],
                    "evidence_ids": [str(row["evidence_id"])],
                }
            )
    return candidates


def _resolve_expanded_queries(conn: Any, generation_id: str, expanded_queries: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for expanded_query in expanded_queries:
        if not normalize_query_token(expanded_query):
            continue
        for candidate in _resolve_aliases(conn, generation_id, expanded_query):
            candidate["matched_by"] = [
                f"expanded_query:{expanded_query}" if item.startswith("alias:") else item
                for item in candidate["matched_by"]
            ]
            candidates.append(candidate)
        for candidate in _resolve_claim_fts(conn, generation_id, expanded_query):
            candidate["matched_by"] = [
                f"expanded_query:{expanded_query}" if item.startswith("claim:") else item
                for item in candidate["matched_by"]
            ]
            candidates.append(candidate)
    return candidates


def _resolve_claim_fts(conn: Any, generation_id: str, query_text: str) -> list[dict[str, Any]]:
    normalized_query = normalize_query_token(query_text)
    if not normalized_query:
        return []

    safe_query = " OR ".join(token for token in re.findall(r"\w+", normalized_query) if token)
    if not safe_query:
        return []

    try:
        rows = conn.execute(
            "SELECT claims.subject_ref, claims.id AS claim_id FROM claim_fts "
            "JOIN claims ON claims.id = claim_fts.claim_id "
            "WHERE claims.generation_id = ? AND claim_fts MATCH ? LIMIT 10",
            (generation_id, safe_query),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {
            "node_id": str(row["subject_ref"]),
            "label": _node_title(conn, generation_id, str(row["subject_ref"])),
            "target_type": "capability" if str(row["subject_ref"]).startswith("capability:") else "node",
            "score": 0.7,
            "matched_by": [f"claim:{row['claim_id']}"],
            "evidence_ids": _claim_evidence(conn, str(row["claim_id"])),
        }
        for row in rows
    ]


def _merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = f"{candidate['target_type']}:{candidate['node_id']}"
        current = merged.get(key)
        if current is None:
            merged[key] = {
                **candidate,
                "matched_by": list(candidate["matched_by"]),
                "evidence_ids": sorted(set(candidate["evidence_ids"])),
            }
            continue
        current["score"] = min(0.99, float(current["score"]) + 0.1)
        current["matched_by"] = sorted(set(current["matched_by"]) | set(candidate["matched_by"]))
        current["evidence_ids"] = sorted(set(current["evidence_ids"]) | set(candidate["evidence_ids"]))
    return sorted(merged.values(), key=lambda item: (-float(item["score"]), item["node_id"]))


def _query_tokens(normalized_query: str) -> list[str]:
    tokens = [normalized_query]
    tokens.extend(part for part in re.findall(r"[\w\u4e00-\u9fff.:-]+", normalized_query) if part not in tokens)
    if "登录" in normalized_query and "登录" not in tokens:
        tokens.append("登录")
    if "login" in normalized_query and "login" not in tokens:
        tokens.append("login")
    return tokens


def _score_for_confidence(confidence: str) -> float:
    return {
        "grounded": 0.95,
        "strong": 0.9,
        "partial": 0.7,
        "weak": 0.4,
    }.get(confidence, 0.5)


def _readiness_for_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "needs_update"
    capability_candidates = [item for item in candidates if item["target_type"] in {"capability", "node"}]
    if (
        len(capability_candidates) > 1
        and abs(float(capability_candidates[0]["score"]) - float(capability_candidates[1]["score"])) < 0.15
    ):
        return "ambiguous"
    return "ready"


def _recommended_action(readiness: str) -> str:
    return {
        "ready": "retry_current_workflow",
        "review": "perform_minimal_live_reads",
        "ambiguous": "ask_user_to_select_candidate",
        "needs_update": "run_map_update",
        "needs_rebuild": "run_map_scan_build",
        "blocked": "repair_or_rebuild_database",
    }.get(readiness, "repair_or_rebuild_database")


def _node_title(conn: Any, generation_id: str, node_id: str) -> str:
    row = conn.execute(
        "SELECT title FROM nodes WHERE generation_id = ? AND id = ?",
        (generation_id, node_id),
    ).fetchone()
    return str(row["title"]) if row else node_id


def _claim_evidence(conn: Any, claim_id: str) -> list[str]:
    rows = conn.execute("SELECT evidence_id FROM claim_evidence WHERE claim_id = ?", (claim_id,)).fetchall()
    return sorted(str(row["evidence_id"]) for row in rows)


def _paths_for_nodes(conn: Any, generation_id: str, node_ids: list[str]) -> list[str]:
    if not node_ids:
        return []
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"SELECT DISTINCT path FROM path_index WHERE generation_id = ? AND node_id IN ({placeholders})",
        (generation_id, *node_ids),
    ).fetchall()
    return sorted(str(row["path"]) for row in rows)


def _fallback_review_paths(conn: Any, generation_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT path FROM path_index WHERE generation_id = ? ORDER BY path LIMIT 10",
        (generation_id,),
    ).fetchall()
    return sorted(str(row["path"]) for row in rows)


def _subgraph_for_nodes(conn: Any, generation_id: str, node_ids: list[str]) -> dict[str, list[str]]:
    if not node_ids:
        return {"nodes": [], "edges": [], "claims": [], "conflicts": []}
    placeholders = ",".join("?" for _ in node_ids)
    edge_rows = conn.execute(
        f"SELECT id FROM edges WHERE generation_id = ? AND (source_id IN ({placeholders}) OR target_id IN ({placeholders}))",
        (generation_id, *node_ids, *node_ids),
    ).fetchall()
    claim_rows = conn.execute(
        f"SELECT id FROM claims WHERE generation_id = ? AND subject_ref IN ({placeholders})",
        (generation_id, *node_ids),
    ).fetchall()
    conflict_rows = conn.execute(
        f"SELECT id FROM conflicts WHERE generation_id = ? AND subject_ref IN ({placeholders})",
        (generation_id, *node_ids),
    ).fetchall()
    return {
        "nodes": sorted(node_ids),
        "edges": sorted(str(row["id"]) for row in edge_rows),
        "claims": sorted(str(row["id"]) for row in claim_rows),
        "conflicts": sorted(str(row["id"]) for row in conflict_rows),
    }
