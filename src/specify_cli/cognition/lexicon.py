"""Agent-facing lexicon bundle for project cognition query planning."""

from __future__ import annotations

from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path
import re
from typing import Any

from .db import connect_cognition_db, ensure_cognition_db, get_active_generation_id
from .query import normalize_query_token


def project_cognition_lexicon(
    project_root: Path,
    *,
    intent: str,
    query_text: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    ensure_cognition_db(project_root)
    generation_id = get_active_generation_id(project_root)
    if not generation_id:
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "intent": intent,
            "query": query_text,
            "terms": [],
            "available_terms": [],
            "concept_candidates": [],
            "query_planning_contract": _query_planning_contract(),
        }

    with closing(connect_cognition_db(project_root)) as conn:
        return _project_cognition_lexicon_payload(
            conn,
            generation_id,
            intent=intent,
            query_text=query_text,
            limit=limit,
        )


def _project_cognition_lexicon_payload(
    conn: Any,
    generation_id: str,
    *,
    intent: str,
    query_text: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    terms = _lexicon_terms(conn, generation_id, query_text=query_text, limit=limit)
    concept_candidates = _concept_candidates(conn, generation_id, terms)
    return {
        "readiness": "ready" if terms else "review",
        "recommended_next_action": "generate_query_plan" if terms else "perform_minimal_live_reads",
        "intent": intent,
        "query": query_text,
        "terms": terms,
        "available_terms": _available_terms(terms),
        "concept_candidates": concept_candidates,
        "query_planning_contract": _query_planning_contract(),
    }


def _query_planning_contract() -> dict[str, str]:
    return {
        "agent_responsibility": "translate raw user intent using this lexicon",
        "runtime_responsibility": "execute graph queries from agent-provided expanded queries and path hints",
    }


def _lexicon_terms(conn: Any, generation_id: str, *, query_text: str, limit: int) -> list[dict[str, Any]]:
    aliases = _aliases_by_node(conn, generation_id)
    paths = _paths_by_node(conn, generation_id)
    symbols = _symbols_by_node(conn, generation_id)
    query = "SELECT id, type, title, confidence, attrs_json FROM nodes WHERE generation_id = ? ORDER BY title"
    params: tuple[Any, ...] = (generation_id,)
    if limit > 0:
        query = f"{query} LIMIT ?"
        params = (generation_id, limit)
    rows = conn.execute(query, params).fetchall()
    terms = [
        {
            "node_id": str(row["id"]),
            "type": str(row["type"]),
            "title": str(row["title"]),
            "confidence": str(row["confidence"]),
            "attrs": _json_object(str(row["attrs_json"])),
            "aliases": sorted(aliases.get(str(row["id"]), [])),
            "paths": sorted(paths.get(str(row["id"]), [])),
            "symbols": sorted(symbols.get(str(row["id"]), [])),
            "match_reason": _lexicon_match_reason(
                query_text,
                title=str(row["title"]),
                aliases=aliases.get(str(row["id"]), []),
                paths=paths.get(str(row["id"]), []),
                symbols=symbols.get(str(row["id"]), []),
            ),
        }
        for row in rows
    ]
    return sorted(terms, key=lambda item: (0 if item["match_reason"] != "catalog" else 1, item["title"]))


def _json_object(raw_value: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _aliases_by_node(conn: Any, generation_id: str) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT target_id, alias FROM alias_index WHERE generation_id = ? ORDER BY alias",
        (generation_id,),
    ).fetchall()
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        result[str(row["target_id"])].add(str(row["alias"]))
    return result


def _paths_by_node(conn: Any, generation_id: str) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT node_id, path FROM path_index WHERE generation_id = ? ORDER BY path",
        (generation_id,),
    ).fetchall()
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        result[str(row["node_id"])].add(str(row["path"]))
    return result


def _symbols_by_node(conn: Any, generation_id: str) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT node_id, symbol_name FROM symbol_index WHERE generation_id = ? ORDER BY symbol_name",
        (generation_id,),
    ).fetchall()
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        result[str(row["node_id"])].add(str(row["symbol_name"]))
    return result


def _query_examples_by_node(conn: Any, generation_id: str) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT expected_target_id, query_text FROM query_examples WHERE generation_id = ? ORDER BY query_text",
        (generation_id,),
    ).fetchall()
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        result[str(row["expected_target_id"])].add(str(row["query_text"]))
    return result


def _evidence_by_node(conn: Any, generation_id: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    rows = conn.execute(
        "SELECT node_id, evidence_id FROM node_evidence "
        "JOIN nodes ON nodes.id = node_evidence.node_id "
        "WHERE nodes.generation_id = ?",
        (generation_id,),
    ).fetchall()
    for row in rows:
        evidence_id = str(row["evidence_id"]).strip()
        if evidence_id:
            result[str(row["node_id"])].add(evidence_id)
    rows = conn.execute(
        "SELECT target_id, evidence_id FROM alias_index WHERE generation_id = ?",
        (generation_id,),
    ).fetchall()
    for row in rows:
        evidence_id = str(row["evidence_id"]).strip()
        if evidence_id:
            result[str(row["target_id"])].add(evidence_id)
    rows = conn.execute(
        "SELECT node_id, evidence_id FROM path_index WHERE generation_id = ?",
        (generation_id,),
    ).fetchall()
    for row in rows:
        evidence_id = str(row["evidence_id"]).strip()
        if evidence_id:
            result[str(row["node_id"])].add(evidence_id)
    rows = conn.execute(
        "SELECT claims.subject_ref, claim_evidence.evidence_id FROM claims "
        "JOIN claim_evidence ON claim_evidence.claim_id = claims.id "
        "WHERE claims.generation_id = ?",
        (generation_id,),
    ).fetchall()
    for row in rows:
        evidence_id = str(row["evidence_id"]).strip()
        if evidence_id:
            result[str(row["subject_ref"])].add(evidence_id)
    return result


def _concept_candidates(conn: Any, generation_id: str, terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_examples = _query_examples_by_node(conn, generation_id)
    evidence = _evidence_by_node(conn, generation_id)
    related = _related_concepts_by_node(conn, generation_id)
    candidates: list[dict[str, Any]] = []
    for term in terms:
        concept_id = str(term["node_id"])
        target_type = str(term["type"])
        aliases = sorted(str(alias) for alias in term["aliases"])
        colloquial_matches = sorted(query_examples.get(concept_id, []))
        matched_terms = _matched_terms(term, colloquial_matches)
        domain = _domain_for_term(term)
        candidates.append(
            {
                "concept_id": concept_id,
                "label": str(term["title"]),
                "target_type": target_type,
                "kind": _candidate_kind(target_type),
                "domain": domain,
                "matched_terms": matched_terms,
                "aliases": aliases,
                "colloquial_matches": colloquial_matches,
                "query_examples": colloquial_matches,
                "target_nodes": [concept_id],
                "related_concepts": sorted(related.get(concept_id, [])),
                "disambiguation_hint": _disambiguation_hint(term, aliases, domain),
                "evidence_ids": sorted(evidence.get(concept_id, [])),
                "confidence": str(term["confidence"]),
                "agent_responsibility": "select concept_id values for query_plan selected_concepts or rejected_concepts",
            }
        )
    return candidates


def _related_concepts_by_node(conn: Any, generation_id: str) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT source_id, target_id FROM edges WHERE generation_id = ? ORDER BY source_id, target_id",
        (generation_id,),
    ).fetchall()
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        source_id = str(row["source_id"])
        target_id = str(row["target_id"])
        result[source_id].add(target_id)
        result[target_id].add(source_id)
    return result


def _candidate_kind(node_type: str) -> str:
    normalized = normalize_query_token(node_type)
    allowed = {
        "capability",
        "module",
        "workflow",
        "runtime",
        "api",
        "state",
        "test",
        "symptom",
        "integration",
        "documentation",
    }
    if normalized in allowed:
        return normalized
    if normalized == "symbol":
        return "module"
    return "capability"


def _matched_terms(term: dict[str, Any], colloquial_matches: list[str]) -> list[str]:
    values: set[str] = set()
    values.update(_split_terms(str(term["title"])))
    for key in ("aliases", "symbols"):
        for value in term[key]:
            values.update(_split_terms(str(value)))
    for value in colloquial_matches:
        values.update(_split_terms(value))
    return sorted(values)


def _domain_for_term(term: dict[str, Any]) -> str:
    attrs = term.get("attrs", {})
    if isinstance(attrs, dict):
        for key in ("domain", "owner", "bounded_context", "module"):
            value = str(attrs.get(key, "")).strip()
            if value:
                return value
    aliases = [str(alias) for alias in term["aliases"]]
    title_terms = _split_terms(str(term["title"]))
    if len(title_terms) >= 2:
        return " ".join(title_terms[:2])
    if aliases:
        alias_terms = _split_terms(aliases[0])
        if alias_terms:
            return " ".join(alias_terms[:2])
    paths = [str(path) for path in term["paths"]]
    if paths:
        parts = [part for part in paths[0].split("/") if part and "." not in part]
        if parts:
            return parts[-1]
    return str(term["title"])


def _disambiguation_hint(term: dict[str, Any], aliases: list[str], domain: str) -> str:
    attrs = term.get("attrs", {})
    if isinstance(attrs, dict):
        for key in ("disambiguation_hint", "disambiguation", "hint"):
            value = str(attrs.get(key, "")).strip()
            if value:
                return value
    label = str(term["title"])
    if aliases:
        return f"Use {label} when the request refers to {domain}; reject it when those aliases point to another project domain."
    return f"Use {label} when the request fits the {domain} project domain."


def _lexicon_match_reason(
    query_text: str,
    *,
    title: str,
    aliases: set[str],
    paths: set[str],
    symbols: set[str],
) -> str:
    query_terms = set(_split_terms(query_text))
    if not query_terms:
        return "catalog"
    candidate_text = " ".join([title, *aliases, *paths, *symbols])
    candidate_terms = set(_split_terms(candidate_text))
    if query_terms & candidate_terms:
        return "query_term_overlap"
    return "catalog"


def _available_terms(terms: list[dict[str, Any]]) -> list[str]:
    values: set[str] = set()
    for term in terms:
        values.update(_split_terms(str(term["title"])))
        for key in ("aliases", "paths", "symbols"):
            for value in term[key]:
                values.update(_split_terms(str(value)))
    return sorted(values)


def _split_terms(value: str) -> list[str]:
    normalized = normalize_query_token(value)
    return [term for term in re.findall(r"[\w\u4e00-\u9fff]+", normalized) if term]
