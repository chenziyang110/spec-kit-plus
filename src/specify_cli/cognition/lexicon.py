"""Agent-facing lexicon bundle for project cognition query planning."""

from __future__ import annotations

from collections import defaultdict
from contextlib import closing
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
            "query_planning_contract": _query_planning_contract(),
        }

    with closing(connect_cognition_db(project_root)) as conn:
        terms = _lexicon_terms(conn, generation_id, query_text=query_text, limit=limit)
    return {
        "readiness": "ready" if terms else "review",
        "recommended_next_action": "generate_query_plan" if terms else "perform_minimal_live_reads",
        "intent": intent,
        "query": query_text,
        "terms": terms,
        "available_terms": _available_terms(terms),
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
    query = "SELECT id, type, title, confidence FROM nodes WHERE generation_id = ? ORDER BY title"
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
