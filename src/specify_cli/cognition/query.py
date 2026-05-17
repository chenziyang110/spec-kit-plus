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
    selected_concepts: list[str] | None = None,
    rejected_concepts: list[str] | None = None,
    selection_reason: str = "",
) -> dict[str, Any]:
    ensure_cognition_db(project_root)
    normalized_selected_concepts = _normalize_concept_ids(selected_concepts)
    normalized_rejected_concepts = _normalize_concept_ids(rejected_concepts)
    normalized_selection_reason = str(selection_reason or "").strip()
    query_plan = _query_plan_payload(
        query_text=query_text,
        expanded_queries=expanded_queries,
        paths=paths,
        selected_concepts=normalized_selected_concepts,
        rejected_concepts=normalized_rejected_concepts,
        selection_reason=normalized_selection_reason,
    )
    generation_id = get_active_generation_id(project_root)
    if not generation_id:
        minimal_live_reads: list[str] = []
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "intent": intent,
            "query": query_text,
            "query_plan": query_plan,
            "selected_concepts": normalized_selected_concepts,
            "rejected_concepts": normalized_rejected_concepts,
            "selection_reason": normalized_selection_reason,
            "capability_candidates": [],
            "symptom_candidates": [],
            "affected_nodes": [],
            "minimal_live_reads": minimal_live_reads,
            "missing_coverage": ["project cognition database has no active generation"],
            "route_pack": _route_pack(items=[], minimal_live_reads=minimal_live_reads),
            "subgraph": {"nodes": [], "edges": [], "claims": [], "conflicts": []},
        }

    with closing(connect_cognition_db(project_root)) as conn:
        return _query_project_cognition_payload(
            conn,
            generation_id,
            intent=intent,
            query_text=query_text,
            expanded_queries=list(query_plan["expanded_queries"]),
            query_plan=query_plan,
        )


def _query_project_cognition_payload(
    conn: Any,
    generation_id: str,
    *,
    intent: str,
    query_text: str,
    expanded_queries: list[str],
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    normalized_selected_concepts = list(query_plan["selected_concepts"])
    normalized_rejected_concepts = list(query_plan["rejected_concepts"])
    normalized_selection_reason = str(query_plan["selection_reason"])
    normalized_paths = list(query_plan["paths"])
    rejected_concept_set = set(normalized_rejected_concepts)
    concept_conflicts = sorted(set(normalized_selected_concepts) & rejected_concept_set)
    if concept_conflicts:
        minimal_live_reads: list[str] = []
        return {
            "readiness": "ambiguous",
            "recommended_next_action": "ask_user_to_select_candidate",
            "intent": intent,
            "query": query_text,
            "query_plan": query_plan,
            "selected_concepts": normalized_selected_concepts,
            "rejected_concepts": normalized_rejected_concepts,
            "selection_reason": normalized_selection_reason,
            "capability_candidates": [],
            "symptom_candidates": [],
            "affected_nodes": [],
            "minimal_live_reads": minimal_live_reads,
            "missing_coverage": [f"concept selected and rejected: {concept_id}" for concept_id in concept_conflicts],
            "route_pack": _route_pack(items=[], minimal_live_reads=minimal_live_reads),
            "subgraph": {"nodes": [], "edges": [], "claims": [], "conflicts": []},
        }

    selected_node_records = _node_records_by_id(conn, generation_id, normalized_selected_concepts)
    known_selected_concepts = [
        concept_id for concept_id in normalized_selected_concepts if concept_id in selected_node_records
    ]
    unknown_selected_concepts = [
        concept_id for concept_id in normalized_selected_concepts if concept_id not in selected_node_records
    ]
    path_nodes, missing_paths = _resolve_paths(conn, generation_id, normalized_paths)
    filtered_path_nodes = {
        node_id: evidence_ids for node_id, evidence_ids in path_nodes.items() if node_id not in rejected_concept_set
    }
    suppressed_by_rejection = len(filtered_path_nodes) != len(path_nodes)
    path_nodes = filtered_path_nodes

    resolved_candidates = (
        _resolve_aliases(conn, generation_id, query_text)
        + _resolve_claim_fts(conn, generation_id, query_text)
        + _resolve_expanded_queries(conn, generation_id, expanded_queries)
    )
    filtered_resolved_candidates = [
        candidate for candidate in resolved_candidates if candidate["node_id"] not in rejected_concept_set
    ]
    suppressed_by_rejection = suppressed_by_rejection or len(filtered_resolved_candidates) != len(resolved_candidates)
    candidates = _merge_candidates(
        _selected_concept_candidates(conn, generation_id, selected_node_records, known_selected_concepts)
        + filtered_resolved_candidates
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
    affected_nodes = sorted(
        set(path_nodes.keys()) | {item["node_id"] for item in candidates if item["target_type"] != "symptom"}
    )
    route_items = _route_items_for_nodes(conn, generation_id, affected_nodes, candidates)
    route_item_node_ids = {
        str(item.get("node_id"))
        for item in route_items
        if str(item.get("node_id", "")).strip()
    }
    route_missing_nodes = sorted(node_id for node_id in affected_nodes if node_id not in route_item_node_ids)

    if unknown_selected_concepts:
        readiness = "needs_update" if missing_paths else "review"
    elif missing_paths:
        readiness = "needs_update"
    elif affected_nodes and not route_items:
        readiness = "review"
    elif query_missed_runtime_index or (suppressed_by_rejection and not path_nodes and not candidates):
        readiness = "review"
    elif known_selected_concepts:
        readiness = "ready"
    else:
        readiness = _readiness_for_candidates(candidates)
    minimal_live_reads = sorted(
        set(_allowed_path_hints(conn, generation_id, normalized_paths, missing_paths, rejected_concept_set))
        | set(_paths_for_nodes(conn, generation_id, affected_nodes))
    )
    if query_missed_runtime_index or (
        readiness == "review" and not missing_paths and not minimal_live_reads
    ):
        minimal_live_reads = _fallback_review_paths(conn, generation_id, rejected_concept_set)
    missing_coverage = [f"path not covered by project cognition index: {path}" for path in missing_paths]
    if query_missed_runtime_index:
        missing_coverage.append(
            "query did not match project cognition aliases or claims; use minimal live reads or ask a clarifying question"
        )
    missing_coverage.extend(
        f"selected concept not covered by active generation: {concept_id}"
        for concept_id in unknown_selected_concepts
    )
    if affected_nodes and not route_items:
        missing_coverage.append("route_pack has no evidence-backed route items for affected nodes")
    missing_coverage.extend(
        f"route_pack missing evidence-backed route item for affected node: {node_id}"
        for node_id in route_missing_nodes
    )

    return {
        "readiness": readiness,
        "recommended_next_action": _recommended_action(readiness),
        "intent": intent,
        "query": query_text,
        "query_plan": query_plan,
        "selected_concepts": normalized_selected_concepts,
        "rejected_concepts": normalized_rejected_concepts,
        "selection_reason": normalized_selection_reason,
        "capability_candidates": [item for item in candidates if item["target_type"] in {"capability", "node"}],
        "symptom_candidates": [item for item in candidates if item["target_type"] == "symptom"],
        "affected_nodes": affected_nodes,
        "minimal_live_reads": minimal_live_reads,
        "missing_coverage": missing_coverage,
        "route_pack": _route_pack(items=route_items, minimal_live_reads=minimal_live_reads),
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
    selected_concepts: list[str] | None,
    rejected_concepts: list[str] | None,
    selection_reason: str,
) -> dict[str, Any]:
    return {
        "raw_query": query_text,
        "expanded_queries": [query for query in (expanded_queries or []) if normalize_query_token(query)],
        "paths": [path.replace("\\", "/") for path in (paths or []) if normalize_query_token(path)],
        "selected_concepts": list(selected_concepts or []),
        "rejected_concepts": list(rejected_concepts or []),
        "selection_reason": selection_reason,
    }


def _normalize_concept_ids(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        concept_id = str(value or "").strip()
        if concept_id and concept_id not in seen:
            normalized.append(concept_id)
            seen.add(concept_id)
    return normalized


def _node_records_by_id(conn: Any, generation_id: str, node_ids: list[str]) -> dict[str, dict[str, str]]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"SELECT id, type, title, confidence FROM nodes WHERE generation_id = ? AND id IN ({placeholders})",
        (generation_id, *node_ids),
    ).fetchall()
    return {
        str(row["id"]): {
            "type": str(row["type"]),
            "title": str(row["title"]),
            "confidence": str(row["confidence"]),
        }
        for row in rows
    }


def _selected_concept_candidates(
    conn: Any,
    generation_id: str,
    node_records: dict[str, dict[str, str]],
    selected_concepts: list[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for concept_id in selected_concepts:
        record = node_records.get(concept_id)
        if not record:
            continue
        candidates.append(
            {
                "node_id": concept_id,
                "label": record["title"],
                "target_type": record["type"],
                "score": 0.99,
                "matched_by": [f"selected_concept:{concept_id}"],
                "evidence_ids": _evidence_for_node(conn, generation_id, concept_id),
            }
        )
    return candidates


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


def _evidence_for_node(conn: Any, generation_id: str, node_id: str) -> list[str]:
    evidence_ids: set[str] = set()
    rows = conn.execute(
        "SELECT evidence_id FROM node_evidence WHERE node_id = ?",
        (node_id,),
    ).fetchall()
    evidence_ids.update(str(row["evidence_id"]).strip() for row in rows if str(row["evidence_id"]).strip())
    rows = conn.execute(
        "SELECT evidence_id FROM alias_index WHERE generation_id = ? AND target_id = ?",
        (generation_id, node_id),
    ).fetchall()
    evidence_ids.update(str(row["evidence_id"]).strip() for row in rows if str(row["evidence_id"]).strip())
    rows = conn.execute(
        "SELECT evidence_id FROM path_index WHERE generation_id = ? AND node_id = ?",
        (generation_id, node_id),
    ).fetchall()
    evidence_ids.update(str(row["evidence_id"]).strip() for row in rows if str(row["evidence_id"]).strip())
    rows = conn.execute(
        "SELECT claim_evidence.evidence_id FROM claims "
        "JOIN claim_evidence ON claim_evidence.claim_id = claims.id "
        "WHERE claims.generation_id = ? AND claims.subject_ref = ?",
        (generation_id, node_id),
    ).fetchall()
    evidence_ids.update(str(row["evidence_id"]).strip() for row in rows if str(row["evidence_id"]).strip())
    return sorted(evidence_ids)


def _paths_for_nodes(conn: Any, generation_id: str, node_ids: list[str]) -> list[str]:
    if not node_ids:
        return []
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"SELECT DISTINCT path FROM path_index WHERE generation_id = ? AND node_id IN ({placeholders})",
        (generation_id, *node_ids),
    ).fetchall()
    return sorted(str(row["path"]) for row in rows)


def _allowed_path_hints(
    conn: Any,
    generation_id: str,
    paths: list[str],
    missing_paths: list[str],
    rejected_concepts: set[str],
) -> list[str]:
    missing_path_set = set(missing_paths)
    allowed_paths: list[str] = []
    for path in paths:
        if path in missing_path_set:
            allowed_paths.append(path)
            continue
        rows = conn.execute(
            "SELECT node_id FROM path_index WHERE generation_id = ? AND path = ?",
            (generation_id, path),
        ).fetchall()
        if rows and all(str(row["node_id"]) in rejected_concepts for row in rows):
            continue
        allowed_paths.append(path)
    return sorted(set(allowed_paths))


def _fallback_review_paths(conn: Any, generation_id: str, rejected_concepts: set[str] | None = None) -> list[str]:
    rejected_concepts = rejected_concepts or set()
    if rejected_concepts:
        placeholders = ",".join("?" for _ in rejected_concepts)
        rows = conn.execute(
            f"SELECT DISTINCT path FROM path_index "
            f"WHERE generation_id = ? AND node_id NOT IN ({placeholders}) ORDER BY path LIMIT 10",
            (generation_id, *sorted(rejected_concepts)),
        ).fetchall()
        return sorted(str(row["path"]) for row in rows)
    rows = conn.execute(
        "SELECT DISTINCT path FROM path_index WHERE generation_id = ? ORDER BY path LIMIT 10",
        (generation_id,),
    ).fetchall()
    return sorted(str(row["path"]) for row in rows)


def _route_items_for_nodes(
    conn: Any,
    generation_id: str,
    node_ids: list[str],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not node_ids:
        return []
    candidate_reasons = {
        str(candidate["node_id"]): ", ".join(str(item) for item in candidate.get("matched_by", []))
        for candidate in candidates
    }
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"SELECT path, node_id, relation, confidence, evidence_id FROM path_index "
        f"WHERE generation_id = ? AND node_id IN ({placeholders}) ORDER BY path, node_id",
        (generation_id, *node_ids),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        node_id = str(row["node_id"])
        items.append(
            {
                "path": str(row["path"]),
                "node_id": node_id,
                "relation": str(row["relation"]),
                "reason": candidate_reasons.get(node_id) or f"path_index:{row['relation']}",
                "evidence_ids": [str(row["evidence_id"])],
                "confidence": str(row["confidence"]),
            }
        )
    entrypoint_rows = conn.execute(
        f"SELECT path, node_id, capability_id, entrypoint_type, entrypoint_key, confidence, evidence_id "
        f"FROM entrypoint_index WHERE generation_id = ? "
        f"AND (node_id IN ({placeholders}) OR capability_id IN ({placeholders})) "
        f"ORDER BY path, entrypoint_key",
        (generation_id, *node_ids, *node_ids),
    ).fetchall()
    for row in entrypoint_rows:
        node_id = str(row["capability_id"] or row["node_id"])
        items.append(
            {
                "path": str(row["path"]),
                "node_id": node_id,
                "relation": f"entry:{row['entrypoint_type']}",
                "reason": candidate_reasons.get(node_id) or f"entrypoint:{row['entrypoint_key']}",
                "evidence_ids": [str(row["evidence_id"])],
                "confidence": str(row["confidence"]),
            }
        )
    test_rows = conn.execute(
        f"SELECT test_path, test_name, node_id, capability_id, confidence, evidence_id "
        f"FROM test_index WHERE generation_id = ? "
        f"AND (node_id IN ({placeholders}) OR capability_id IN ({placeholders})) "
        f"ORDER BY test_path, test_name",
        (generation_id, *node_ids, *node_ids),
    ).fetchall()
    for row in test_rows:
        node_id = str(row["capability_id"] or row["node_id"])
        items.append(
            {
                "path": str(row["test_path"]),
                "node_id": node_id,
                "relation": "test",
                "reason": candidate_reasons.get(node_id) or f"test:{row['test_name']}",
                "evidence_ids": [str(row["evidence_id"])],
                "confidence": str(row["confidence"]),
            }
        )
    claim_rows = conn.execute(
        f"SELECT claims.id AS claim_id, claims.subject_ref, claims.predicate, claims.confidence, "
        f"claim_evidence.evidence_id FROM claims "
        f"LEFT JOIN claim_evidence ON claim_evidence.claim_id = claims.id "
        f"WHERE claims.generation_id = ? AND claims.subject_ref IN ({placeholders}) "
        f"ORDER BY claims.id, claim_evidence.evidence_id",
        (generation_id, *node_ids),
    ).fetchall()
    claim_items: dict[str, dict[str, Any]] = {}
    for row in claim_rows:
        claim_id = str(row["claim_id"])
        item = claim_items.setdefault(
            claim_id,
            {
                "path": "",
                "claim_id": claim_id,
                "node_id": str(row["subject_ref"]),
                "relation": str(row["predicate"]),
                "reason": candidate_reasons.get(str(row["subject_ref"])) or f"claim:{claim_id}",
                "evidence_ids": [],
                "confidence": str(row["confidence"]),
            },
        )
        if row["evidence_id"]:
            item["evidence_ids"].append(str(row["evidence_id"]))
    for item in claim_items.values():
        item["evidence_ids"] = sorted(set(item["evidence_ids"]))
        if not item["path"]:
            item["path"] = _first_path_for_node(conn, generation_id, str(item["node_id"]))
        if item["path"] and item["evidence_ids"]:
            items.append(item)
    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in items:
        key = (
            str(item.get("path", "")),
            str(item.get("node_id", "")),
            str(item.get("claim_id", "")),
            str(item["relation"]),
        )
        current = deduped.get(key)
        evidence_ids = sorted(evidence_id for evidence_id in set(item["evidence_ids"]) if evidence_id)
        if not str(item.get("path", "")).strip() or not evidence_ids:
            continue
        if current is None:
            deduped[key] = {**item, "evidence_ids": evidence_ids}
            continue
        current["evidence_ids"] = sorted(set(current["evidence_ids"]) | set(evidence_ids))
    return list(deduped.values())


def _first_path_for_node(conn: Any, generation_id: str, node_id: str) -> str:
    row = conn.execute(
        "SELECT path FROM path_index WHERE generation_id = ? AND node_id = ? ORDER BY path LIMIT 1",
        (generation_id, node_id),
    ).fetchone()
    return str(row["path"]) if row else ""


def _route_pack(*, items: list[dict[str, Any]], minimal_live_reads: list[str]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "entry_files": [],
        "owner_files": [],
        "consumer_files": [],
        "state_surfaces": [],
        "workflow_surfaces": [],
        "tests": [],
        "docs": [],
    }
    for item in items:
        buckets[_route_bucket(item)].append(item)
    return {
        **buckets,
        "items": items,
        "routes": items,
        "minimal_live_reads": minimal_live_reads,
        "why_these_reads": [
            f"{path}: {_read_reason_for_path(path, items)}"
            for path in minimal_live_reads
        ],
    }


def _route_bucket(item: dict[str, Any]) -> str:
    relation = normalize_query_token(str(item.get("relation", "")))
    path = normalize_query_token(str(item.get("path", "")))
    if "entry" in relation or "handler" in relation or "command" in relation:
        return "entry_files"
    if "consumer" in relation or "call" in relation or "used" in relation:
        return "consumer_files"
    if "state" in relation or any(token in path for token in ("status", "config", "session", "database", "db")):
        return "state_surfaces"
    if "workflow" in relation or any(token in path for token in ("templates/commands", "command-partials", "passive-skills")):
        return "workflow_surfaces"
    if "test" in relation or "/test" in path or path.startswith("test") or "/tests/" in path:
        return "tests"
    if "doc" in relation or path.endswith(".md") or "/docs/" in path:
        return "docs"
    return "owner_files"


def _read_reason_for_path(path: str, items: list[dict[str, Any]]) -> str:
    reasons = [str(item["reason"]) for item in items if item.get("path") == path and item.get("reason")]
    if reasons:
        return "; ".join(sorted(set(reasons)))
    return "fallback minimal live read for project cognition readiness"


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
