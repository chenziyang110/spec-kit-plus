"""Classify missing path-index coverage for project cognition queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
import sqlite3
from typing import Sequence


AUTO_ADOPT_LIMIT = 10
REVIEW_LIMIT = 5

_CORE_LIVE_SURFACE_PREFIXES = (
    ".github/",
    ".github\\",
    "scripts/",
    "scripts\\",
)
_CORE_LIVE_SURFACE_FILENAMES = {
    "cargo.toml",
    "docker-compose.yaml",
    "docker-compose.yml",
    "dockerfile",
    "go.mod",
    "makefile",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
}
_CORE_LIVE_SURFACE_PARTS = {
    "build",
    "build_modules",
    "ci",
    "command",
    "commands",
    "config",
    "configs",
    "dispatch",
    "packaging",
    "release",
    "releases",
    "route",
    "routes",
    "schema",
    "schemas",
    "workflow",
    "workflows",
}


@dataclass(frozen=True)
class IndexedPathRecord:
    path: str
    node_id: str
    relation: str
    confidence: str
    evidence_id: str


@dataclass(frozen=True)
class AdoptablePath:
    path: str
    node_id: str
    nearest_indexed_sibling: str
    confidence: str = "weak"
    reason: str = "same_directory_indexed_sibling"


@dataclass(frozen=True)
class PathCoverageClassification:
    query_coverage: str
    recommended_next_action: str
    adoptable_paths: list[AdoptablePath] = field(default_factory=list)
    review_paths: list[str] = field(default_factory=list)
    unadoptable_paths: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def classify_path_coverage(
    conn: sqlite3.Connection,
    generation_id: str,
    *,
    missing_paths: Sequence[str],
    requested_paths: Sequence[str] | None = None,
) -> PathCoverageClassification:
    """Classify missing path-index rows without mutating the cognition DB."""

    del requested_paths
    normalized_missing_paths = _normalize_unique_paths(missing_paths)
    if not normalized_missing_paths:
        return PathCoverageClassification(
            query_coverage="covered",
            recommended_next_action="none",
        )

    indexed_paths = _load_indexed_paths(conn, generation_id)
    if not indexed_paths:
        return PathCoverageClassification(
            query_coverage="unadoptable_path_gap",
            recommended_next_action="run_map_scan_build",
            unadoptable_paths=normalized_missing_paths,
            reasons=["active generation has no path_index rows to adopt from"],
        )

    adoptable_paths: list[AdoptablePath] = []
    uncertain_paths: list[str] = []
    reasons: list[str] = []

    for path in normalized_missing_paths:
        adoptable = _find_adoptable_path(path, indexed_paths)
        if adoptable is not None:
            adoptable_paths.append(adoptable)
        elif _is_core_live_surface(path):
            uncertain_paths.append(path)
            reasons.append(f"core live surface path needs review before adoption: {path}")
        else:
            uncertain_paths.append(path)

    review_reasons = _review_reasons(
        missing_paths=normalized_missing_paths,
        indexed_paths=indexed_paths,
        uncertain_paths=uncertain_paths,
    )

    if uncertain_paths:
        return PathCoverageClassification(
            query_coverage="uncertain_path_gap",
            recommended_next_action="perform_minimal_live_reads",
            adoptable_paths=adoptable_paths,
            review_paths=uncertain_paths,
            reasons=[*reasons, *review_reasons],
        )

    if len(adoptable_paths) <= AUTO_ADOPT_LIMIT:
        return PathCoverageClassification(
            query_coverage="adoptable_path_gap",
            recommended_next_action="run_map_update",
            adoptable_paths=adoptable_paths,
            reasons=reasons,
        )

    return PathCoverageClassification(
        query_coverage="uncertain_path_gap",
        recommended_next_action="perform_minimal_live_reads",
        adoptable_paths=adoptable_paths,
        review_paths=[],
        reasons=[*reasons, f"more than {AUTO_ADOPT_LIMIT} adoptable paths require review before update"],
    )


def _load_indexed_paths(conn: sqlite3.Connection, generation_id: str) -> list[IndexedPathRecord]:
    rows = conn.execute(
        "SELECT path, node_id, relation, confidence, evidence_id "
        "FROM path_index WHERE generation_id = ? ORDER BY path",
        (generation_id,),
    ).fetchall()
    return [
        IndexedPathRecord(
            path=_normalize_path(row["path"]),
            node_id=row["node_id"],
            relation=row["relation"],
            confidence=row["confidence"],
            evidence_id=row["evidence_id"],
        )
        for row in rows
    ]


def _find_adoptable_path(path: str, indexed_paths: Sequence[IndexedPathRecord]) -> AdoptablePath | None:
    same_directory = [record for record in indexed_paths if _parent(record.path) == _parent(path)]
    if same_directory:
        record = same_directory[0]
        return AdoptablePath(
            path=path,
            node_id=record.node_id,
            nearest_indexed_sibling=record.path,
        )

    ancestor_candidates = sorted(
        (
            (ancestor_distance, record.path, record)
            for record in indexed_paths
            if (ancestor_distance := _indexed_ancestor_distance(record.path, path)) is not None
        ),
        key=lambda candidate: (candidate[0], candidate[1]),
    )
    if ancestor_candidates:
        record = ancestor_candidates[0][2]
        return AdoptablePath(
            path=path,
            node_id=record.node_id,
            nearest_indexed_sibling=record.path,
            reason="nearest_indexed_ancestor_within_two_levels",
        )

    return None


def _review_reasons(
    *,
    missing_paths: Sequence[str],
    indexed_paths: Sequence[IndexedPathRecord],
    uncertain_paths: Sequence[str],
) -> list[str]:
    reasons: list[str] = []
    if len(uncertain_paths) > REVIEW_LIMIT:
        reasons.append(f"more than {REVIEW_LIMIT} uncertain missing paths need review")
    if len(uncertain_paths) > 25:
        reasons.append("more than 25 missing paths are unclassified")

    unrelated_top_levels = _unrelated_top_level_count(missing_paths, indexed_paths)
    if unrelated_top_levels > 3:
        reasons.append("more than 3 unrelated top-level live-surface directories are missing")

    return reasons


def _unrelated_top_level_count(
    missing_paths: Sequence[str],
    indexed_paths: Sequence[IndexedPathRecord],
) -> int:
    indexed_top_levels = {_top_level(record.path) for record in indexed_paths}
    missing_top_levels = {_top_level(path) for path in missing_paths}
    return len(missing_top_levels - indexed_top_levels)


def _indexed_ancestor_distance(indexed_path: str, missing_path: str) -> int | None:
    indexed_parent = _parent(indexed_path)
    if not indexed_parent:
        return None
    current = _parent(missing_path)
    for distance in range(3):
        if current == indexed_parent:
            return distance
        next_parent = _parent(current)
        if next_parent == current:
            break
        current = next_parent
    return None


def _is_core_live_surface(path: str) -> bool:
    lower_path = path.lower()
    if any(
        path == prefix.rstrip("/\\") or path.startswith(prefix)
        for prefix in _CORE_LIVE_SURFACE_PREFIXES
    ):
        return True
    pure_path = PurePosixPath(lower_path)
    if pure_path.name in _CORE_LIVE_SURFACE_FILENAMES:
        return True
    return any(part in _CORE_LIVE_SURFACE_PARTS for part in pure_path.parts)


def _top_level(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if parts else ""


def _parent(path: str) -> str:
    parent = str(PurePosixPath(path).parent)
    return "" if parent == "." else parent


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _normalize_unique_paths(paths: Sequence[str]) -> list[str]:
    normalized_paths: list[str] = []
    seen_paths: set[str] = set()
    for path in paths:
        normalized_path = _normalize_path(path)
        if not normalized_path or normalized_path in seen_paths:
            continue
        normalized_paths.append(normalized_path)
        seen_paths.add(normalized_path)
    return normalized_paths
