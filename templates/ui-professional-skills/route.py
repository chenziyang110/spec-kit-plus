from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _signal_matches(
    query: str, skill: dict[str, Any]
) -> tuple[list[str], list[str]]:
    triggers = skill.get("triggers", {})
    phrases = triggers.get("phrases", [])
    negatives = triggers.get("negative_phrases", [])
    matched = [phrase for phrase in phrases if _normalized(phrase) in query]
    blocked = [phrase for phrase in negatives if _normalized(phrase) in query]
    return matched, blocked


def _score(query: str, skill: dict[str, Any]) -> tuple[int, list[str]]:
    matched, blocked = _signal_matches(query, skill)
    return len(matched) - (2 * len(blocked)), matched


def _rank(
    query: str, skills: list[dict[str, Any]], kind: str
) -> list[tuple[int, int, dict[str, Any], list[str]]]:
    ranked: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, skill in enumerate(skills):
        if skill.get("kind") != kind:
            continue
        score, matched = _score(query, skill)
        if score > 0:
            ranked.append((score, -index, skill, matched))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked


def route(
    catalog: dict[str, Any],
    raw_query: str,
    *,
    style_authority: str = "greenfield",
) -> dict[str, Any]:
    query = _normalized(raw_query)
    skills = catalog["skills"]
    routing = catalog["routing"]
    by_id = {skill["id"]: skill for skill in skills}
    matched_signals: dict[str, list[str]] = {}
    ambiguities: list[dict[str, Any]] = []

    domains = _rank(query, skills, "domain")
    if not domains:
        domain_id = routing["fallback_domain"]
    else:
        domain_id = domains[0][2]["id"]
        matched_signals[domain_id] = domains[0][3]
        tied = [item[2]["id"] for item in domains if item[0] == domains[0][0]]
        if len(tied) > 1:
            ambiguities.append({"kind": "domain", "candidate_ids": tied})
            domain_id = routing["fallback_domain"]

    style_id: str | None = None
    if style_authority != "inherit-existing":
        direct_style_signals = []
        for skill in skills:
            if skill.get("kind") != "style":
                continue
            matched, blocked = _signal_matches(query, skill)
            if matched:
                direct_style_signals.append((skill, matched, blocked))

        explicit_style_conflict = (
            len(direct_style_signals) > 1
            and any(blocked for _, _, blocked in direct_style_signals)
        )
        styles = _rank(query, skills, "style")
        if explicit_style_conflict:
            candidate_ids = [skill["id"] for skill, _, _ in direct_style_signals]
            ambiguities.append({"kind": "style", "candidate_ids": candidate_ids})
            for skill, matched, _ in direct_style_signals:
                matched_signals[skill["id"]] = matched
        elif styles:
            top_score = styles[0][0]
            tied = [item for item in styles if item[0] == top_score]
            if len(tied) > 1:
                ambiguities.append(
                    {
                        "kind": "style",
                        "candidate_ids": [item[2]["id"] for item in tied],
                    }
                )
                for _, _, skill, matched in tied:
                    matched_signals[skill["id"]] = matched
            else:
                style_id = styles[0][2]["id"]
                matched_signals[style_id] = styles[0][3]

    specialist_limit = int(routing["specialist_limit"])
    specialist_ids: list[str] = []
    for _, _, skill, matched in _rank(query, skills, "specialist")[:specialist_limit]:
        specialist_ids.append(skill["id"])
        matched_signals[skill["id"]] = matched

    question_required = bool(ambiguities)
    if question_required:
        # A material route conflict pauses specialist/style loading. The one
        # stable domain is enough context to ask the next direction-changing
        # question without contaminating the round with competing references.
        style_id = None
        specialist_ids = []

    selected_ids = [domain_id]
    if style_id is not None:
        selected_ids.append(style_id)
    selected_ids.extend(specialist_ids)
    load_refs = [by_id[skill_id]["ref"] for skill_id in selected_ids]

    question = None
    if ambiguities:
        candidate_names = [
            by_id[skill_id]["name"]
            for ambiguity in ambiguities
            for skill_id in ambiguity["candidate_ids"]
        ]
        question = (
            "这轮最应该优先保留哪一种方向："
            + "、".join(candidate_names)
            + "？"
        )

    unresolved_candidates = [
        skill_id
        for ambiguity in ambiguities
        for skill_id in ambiguity["candidate_ids"]
    ]
    professional_skill_route = {
        "catalog_version": catalog["catalog_id"],
        "status": "question-required" if question_required else "resolved",
        "domain_skill_id": domain_id,
        "style_skill_id": style_id,
        "specialist_skill_ids": specialist_ids,
        "matched_signals": matched_signals,
        "loaded_refs": load_refs,
        "unresolved_candidates": unresolved_candidates,
    }

    return {
        "catalog_id": catalog["catalog_id"],
        "style_authority": style_authority,
        "selection": {
            "domain_skill_id": domain_id,
            "style_skill_id": style_id,
            "specialist_skill_ids": specialist_ids,
        },
        "matched_signals": matched_signals,
        "ambiguities": ambiguities,
        "question_required": question_required,
        "question": question,
        "load_refs": load_refs,
        "professional_skill_route": professional_skill_route,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Route one UI request sparsely.")
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--style-authority",
        choices=("greenfield", "inherit-existing", "page-overhaul-authorized"),
        default="greenfield",
        help="Whether a routed style may influence this exact design scope.",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).with_name("catalog.json"),
    )
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    print(
        json.dumps(
            route(catalog, args.query, style_authority=args.style_authority),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
