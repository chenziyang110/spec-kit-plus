# Project Cognition Self-Healing Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project cognition prefer query review, `map-update` adoption, and minimal live reads over full `sp-map-scan -> sp-map-build` rebuilds for normal coverage gaps.

**Architecture:** Add one shared path-coverage classifier used by query and update runtime paths. `query` decides whether a missing path is adoptable, review-only, or unadoptable; `update` performs valid provisional graph writes for adoptable paths. Freshness helpers and generated guidance keep existing public fields stable while deriving them from the richer baseline/coverage/workflow classification.

**Tech Stack:** Python 3, SQLite, pytest, Typer CLI helpers, Markdown templates, Bash, PowerShell.

---

## Scope Check

This is one feature with several synchronized surfaces. The runtime change is the source of truth; shell helpers, templates, docs, and tests are compatibility surfaces that must be updated in the same branch.

Do not implement unrelated cognition rebuild logic. Do not change the SQLite schema. The existing graph tables are sufficient: provisional adoption writes `evidence`, optional `nodes`/`node_evidence`, and `path_index` rows.

## File Structure

- Create `src/specify_cli/cognition/path_adoption.py`
  - Owns path gap classification and threshold constants.
  - Has no dependency on query/update modules.
- Create `tests/test_project_cognition_path_adoption.py`
  - Unit tests for classifier thresholds and core-surface escalation.
- Modify `src/specify_cli/cognition/query.py`
  - Uses the classifier for missing path readiness.
  - Adds compatibility fields: `baseline_health`, `query_coverage`, `workflow_requirement`, and `path_adoption`.
- Modify `src/specify_cli/cognition/update.py`
  - Uses the classifier before deciding result state.
  - Writes provisional adoption evidence and path_index rows for adoptable paths.
- Modify `src/specify_cli/project_cognition_status.py`
  - Stops mapping every path-index gap reason to `run_map_scan_build`.
  - Keeps scan/build for unadoptable or threshold-exceeding path-index gaps.
- Modify `scripts/bash/project-map-freshness.sh`
  - Mirrors the Python freshness mapping for compatibility output.
- Modify `scripts/powershell/project-map-freshness.ps1`
  - Mirrors the Bash compatibility behavior.
- Modify generated guidance:
  - `templates/commands/map-update.md`
  - `templates/commands/discussion.md`
  - `templates/commands/specify.md`
  - `templates/commands/plan.md`
  - `templates/commands/tasks.md`
  - `templates/commands/analyze.md`
  - `templates/commands/debug.md`
  - `templates/commands/quick.md`
  - `templates/commands/prd-scan.md`
  - `templates/command-partials/common/context-loading-gradient.md`
  - `templates/command-partials/common/senior-consequence-analysis-gate.md`
  - `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
  - `templates/project-handbook-template.md`
  - `src/specify_cli/integrations/base.py`
  - `README.md`
  - `PROJECT-HANDBOOK.md`

## Task 1: Shared Path Coverage Classifier

**Files:**
- Create: `src/specify_cli/cognition/path_adoption.py`
- Create: `tests/test_project_cognition_path_adoption.py`

- [ ] **Step 1: Write failing classifier tests**

Create `tests/test_project_cognition_path_adoption.py`:

```python
from contextlib import closing
from pathlib import Path

from specify_cli.cognition import connect_cognition_db, ensure_cognition_db, seed_active_generation
from specify_cli.cognition.path_adoption import classify_path_coverage


def _seed_indexed_path(project_root: Path, *, indexed_path: str = "src/auth/login.ts") -> str:
    ensure_cognition_db(project_root)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', ?, 'abc123', '1-80', 'test', 'hash-login', '2026-05-13T00:00:00Z', '{}')",
            (generation_id, indexed_path),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, ?, 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-13T00:00:00Z')",
            (generation_id, indexed_path),
        )
        conn.commit()
    return generation_id


def test_classifies_same_directory_missing_path_as_adoptable(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/auth/session.ts"],
            requested_paths=["src/auth/session.ts"],
        )

    assert result.query_coverage == "adoptable_path_gap"
    assert result.recommended_next_action == "run_map_update"
    assert [item.path for item in result.adoptable_paths] == ["src/auth/session.ts"]
    assert result.adoptable_paths[0].node_id == "capability:auth.login"
    assert result.adoptable_paths[0].nearest_indexed_sibling == "src/auth/login.ts"
    assert result.review_paths == []
    assert result.unadoptable_paths == []


def test_classifies_small_shared_top_level_gap_as_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/payments/invoice.ts"],
            requested_paths=["src/payments/invoice.ts"],
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == ["src/payments/invoice.ts"]
    assert result.unadoptable_paths == []


def test_classifies_many_unrelated_missing_paths_as_unadoptable(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    missing_paths = [f"new_system_{index}/entry.py" for index in range(26)]
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=missing_paths,
            requested_paths=missing_paths,
        )

    assert result.query_coverage == "unadoptable_path_gap"
    assert result.recommended_next_action == "run_map_scan_build"
    assert result.adoptable_paths == []
    assert result.review_paths == []
    assert result.unadoptable_paths == missing_paths
    assert any("more than 25" in reason for reason in result.reasons)


def test_core_surface_without_indexed_sibling_is_unadoptable(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["scripts/release/package.ps1"],
            requested_paths=["scripts/release/package.ps1"],
        )

    assert result.query_coverage == "unadoptable_path_gap"
    assert result.recommended_next_action == "run_map_scan_build"
    assert result.unadoptable_paths == ["scripts/release/package.ps1"]
    assert any("core live surface" in reason for reason in result.reasons)
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
pytest tests/test_project_cognition_path_adoption.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'specify_cli.cognition.path_adoption'`.

- [ ] **Step 3: Add the classifier module**

Create `src/specify_cli/cognition/path_adoption.py`:

```python
"""Path coverage classification for project cognition update/adoption."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any


AUTO_ADOPT_LIMIT = 10
REVIEW_LIMIT = 5
UNCLASSIFIED_REBUILD_LIMIT = 25
UNRELATED_TOP_LEVEL_REBUILD_LIMIT = 3
UNADOPTABLE_RATIO_REBUILD_THRESHOLD = 0.40

CORE_SURFACE_PARTS = {
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

CORE_SURFACE_FILENAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "go.mod",
    "cargo.toml",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
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
    reason: str
    confidence: str = "weak"


@dataclass(frozen=True)
class PathCoverageClassification:
    baseline_health: str = "healthy"
    query_coverage: str = "covered"
    recommended_next_action: str = "retry_current_workflow"
    adoptable_paths: list[AdoptablePath] = field(default_factory=list)
    review_paths: list[str] = field(default_factory=list)
    unadoptable_paths: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def classify_path_coverage(
    conn: Any,
    generation_id: str,
    *,
    missing_paths: list[str],
    requested_paths: list[str] | None = None,
) -> PathCoverageClassification:
    normalized_missing = _unique_normalized_paths(missing_paths)
    if not normalized_missing:
        return PathCoverageClassification()

    indexed_records = _load_indexed_records(conn, generation_id)
    if not indexed_records:
        return PathCoverageClassification(
            query_coverage="unadoptable_path_gap",
            recommended_next_action="run_map_scan_build",
            unadoptable_paths=normalized_missing,
            reasons=["active generation has no path_index rows to adopt from"],
        )

    requested = _unique_normalized_paths(requested_paths or normalized_missing)
    requested_count = max(len(requested), 1)
    adoptable: list[AdoptablePath] = []
    review: list[str] = []
    unadoptable: list[str] = []
    reasons: list[str] = []

    for path in normalized_missing:
        nearest = _nearest_indexed_record(indexed_records, path)
        if nearest:
            adoptable.append(
                AdoptablePath(
                    path=path,
                    node_id=nearest.node_id,
                    nearest_indexed_sibling=nearest.path,
                    reason=_adoption_reason(path, nearest.path),
                )
            )
            continue
        if _has_core_surface_signal(path):
            unadoptable.append(path)
            reasons.append(f"core live surface missing from path_index: {path}")
            continue
        review.append(path)

    unrelated_top_levels = { _top_level(path) for path in normalized_missing if _top_level(path) }
    unadoptable_ratio = len(unadoptable) / requested_count
    if len(review) + len(unadoptable) > UNCLASSIFIED_REBUILD_LIMIT:
        return PathCoverageClassification(
            query_coverage="unadoptable_path_gap",
            recommended_next_action="run_map_scan_build",
            unadoptable_paths=normalized_missing,
            reasons=[f"more than {UNCLASSIFIED_REBUILD_LIMIT} missing paths are unclassified"],
        )
    if len(unrelated_top_levels) > UNRELATED_TOP_LEVEL_REBUILD_LIMIT:
        return PathCoverageClassification(
            query_coverage="unadoptable_path_gap",
            recommended_next_action="run_map_scan_build",
            unadoptable_paths=normalized_missing,
            reasons=[
                f"missing paths span more than {UNRELATED_TOP_LEVEL_REBUILD_LIMIT} unrelated top-level live-surface directories"
            ],
        )
    if unadoptable and unadoptable_ratio > UNADOPTABLE_RATIO_REBUILD_THRESHOLD:
        return PathCoverageClassification(
            query_coverage="unadoptable_path_gap",
            recommended_next_action="run_map_scan_build",
            unadoptable_paths=unadoptable,
            reasons=reasons or ["unadoptable path ratio exceeds rebuild threshold"],
        )
    if unadoptable:
        return PathCoverageClassification(
            query_coverage="unadoptable_path_gap",
            recommended_next_action="run_map_scan_build",
            unadoptable_paths=unadoptable,
            reasons=reasons,
        )
    if adoptable and not review and len(adoptable) <= AUTO_ADOPT_LIMIT:
        return PathCoverageClassification(
            query_coverage="adoptable_path_gap",
            recommended_next_action="run_map_update",
            adoptable_paths=adoptable,
            reasons=[f"path can be adopted from nearest indexed sibling: {item.path}" for item in adoptable],
        )
    if review and len(review) <= REVIEW_LIMIT:
        return PathCoverageClassification(
            query_coverage="uncertain_path_gap",
            recommended_next_action="perform_minimal_live_reads",
            adoptable_paths=adoptable,
            review_paths=review,
            reasons=[f"path requires minimal live read before adoption: {path}" for path in review],
        )
    return PathCoverageClassification(
        query_coverage="unadoptable_path_gap",
        recommended_next_action="run_map_scan_build",
        unadoptable_paths=normalized_missing,
        reasons=["missing path coverage exceeded adoption and review thresholds"],
    )


def _load_indexed_records(conn: Any, generation_id: str) -> list[IndexedPathRecord]:
    rows = conn.execute(
        "SELECT path, node_id, relation, confidence, evidence_id FROM path_index WHERE generation_id = ? ORDER BY path",
        (generation_id,),
    ).fetchall()
    return [
        IndexedPathRecord(
            path=str(row["path"]).replace("\\", "/"),
            node_id=str(row["node_id"]),
            relation=str(row["relation"]),
            confidence=str(row["confidence"]),
            evidence_id=str(row["evidence_id"]),
        )
        for row in rows
    ]


def _nearest_indexed_record(records: list[IndexedPathRecord], missing_path: str) -> IndexedPathRecord | None:
    missing_parent = _parent(missing_path)
    exact_siblings = [record for record in records if _parent(record.path) == missing_parent]
    if exact_siblings:
        return exact_siblings[0]
    ancestor_matches = [
        (distance, record)
        for record in records
        if (distance := _ancestor_distance(missing_parent, _parent(record.path))) is not None and distance <= 2
    ]
    if not ancestor_matches:
        return None
    ancestor_matches.sort(key=lambda item: (item[0], item[1].path))
    return ancestor_matches[0][1]


def _adoption_reason(path: str, sibling: str) -> str:
    if _parent(path) == _parent(sibling):
        return "same_directory_indexed_sibling"
    return "nearest_indexed_ancestor_within_two_levels"


def _ancestor_distance(child_parent: str, ancestor_parent: str) -> int | None:
    if not ancestor_parent:
        return None
    if child_parent == ancestor_parent:
        return 0
    prefix = f"{ancestor_parent}/"
    if not child_parent.startswith(prefix):
        return None
    remainder = child_parent[len(prefix):]
    return len([part for part in remainder.split("/") if part])


def _has_core_surface_signal(path: str) -> bool:
    parts = [part.lower() for part in PurePosixPath(path).parts]
    filename = parts[-1] if parts else ""
    if filename in CORE_SURFACE_FILENAMES:
        return True
    return any(part in CORE_SURFACE_PARTS for part in parts)


def _parent(path: str) -> str:
    parent = str(PurePosixPath(path).parent)
    return "" if parent == "." else parent


def _top_level(path: str) -> str:
    parts = [part for part in PurePosixPath(path).parts if part]
    return parts[0] if parts else ""


def _unique_normalized_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        value = str(path or "").strip().replace("\\", "/").strip("/")
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized
```

- [ ] **Step 4: Run classifier tests**

Run:

```bash
pytest tests/test_project_cognition_path_adoption.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/cognition/path_adoption.py tests/test_project_cognition_path_adoption.py
git commit -m "feat(cognition): classify path coverage gaps"
```

## Task 2: Query Readiness Uses Coverage Classification

**Files:**
- Modify: `src/specify_cli/cognition/query.py`
- Modify: `tests/test_project_cognition_query.py`

- [ ] **Step 1: Update query tests for adoptable, review, and unadoptable gaps**

Modify the existing missing path tests in `tests/test_project_cognition_query.py` and add one unadoptable test:

```python
def test_query_reports_needs_update_when_path_is_adoptable_from_index(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="", paths=["src/auth/missing.ts"])

    assert result["baseline_health"] == "healthy"
    assert result["query_coverage"] == "adoptable_path_gap"
    assert result["workflow_requirement"] == "planning_or_implementation"
    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    assert result["path_adoption"]["adoptable_paths"] == ["src/auth/missing.ts"]
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]


def test_query_keeps_discussion_allowed_for_uncertain_path_gap(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="discussion", query_text="", paths=["docs/future/idea.md"])

    assert result["baseline_health"] == "healthy"
    assert result["query_coverage"] == "uncertain_path_gap"
    assert result["workflow_requirement"] == "discussion"
    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["minimal_live_reads"] == ["docs/future/idea.md"]
    assert result["path_adoption"]["review_paths"] == ["docs/future/idea.md"]


def test_query_routes_unadoptable_core_surface_gap_to_rebuild(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="release packaging",
        paths=["scripts/release/package.ps1"],
    )

    assert result["baseline_health"] == "healthy"
    assert result["query_coverage"] == "unadoptable_path_gap"
    assert result["workflow_requirement"] == "planning_or_implementation"
    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
    assert result["path_adoption"]["unadoptable_paths"] == ["scripts/release/package.ps1"]
```

Remove or update old assertions that expect `needs_rebuild` for `src/auth/missing.ts`.

- [ ] **Step 2: Run query tests and verify they fail**

Run:

```bash
pytest tests/test_project_cognition_query.py -q
```

Expected: FAIL because `query_project_cognition()` still maps all missing paths to `needs_rebuild` and does not return the new compatibility fields.

- [ ] **Step 3: Implement query integration**

In `src/specify_cli/cognition/query.py`, import the classifier:

```python
from .path_adoption import PathCoverageClassification, classify_path_coverage
```

Add helpers near `_recommended_action()`:

```python
def _workflow_requirement(intent: str) -> str:
    return "discussion" if str(intent or "").strip().lower() == "discussion" else "planning_or_implementation"


def _path_adoption_payload(classification: PathCoverageClassification) -> dict[str, Any]:
    return {
        "adoptable_paths": [item.path for item in classification.adoptable_paths],
        "review_paths": list(classification.review_paths),
        "unadoptable_paths": list(classification.unadoptable_paths),
        "reasons": list(classification.reasons),
    }


def _readiness_for_path_classification(
    classification: PathCoverageClassification,
    *,
    workflow_requirement: str,
    has_known_candidates: bool,
) -> str:
    if classification.query_coverage == "unadoptable_path_gap":
        return "needs_rebuild"
    if classification.query_coverage == "adoptable_path_gap":
        return "needs_update"
    if classification.query_coverage == "uncertain_path_gap":
        return "review" if workflow_requirement == "discussion" else "needs_update"
    if has_known_candidates:
        return "ready"
    return "review"
```

Inside `_query_project_cognition_payload()`, after `path_nodes, missing_paths = _resolve_paths(...)`, compute:

```python
    workflow_requirement = _workflow_requirement(intent)
    path_classification = classify_path_coverage(
        conn,
        generation_id,
        missing_paths=missing_paths,
        requested_paths=normalized_paths,
    )
```

Replace the current missing-path readiness block:

```python
    if unknown_selected_concepts:
        readiness = "needs_rebuild" if missing_paths else "review"
    elif missing_paths:
        readiness = "needs_rebuild"
```

with:

```python
    if missing_paths:
        readiness = _readiness_for_path_classification(
            path_classification,
            workflow_requirement=workflow_requirement,
            has_known_candidates=bool(candidates or path_nodes or known_selected_concepts),
        )
    elif unknown_selected_concepts:
        readiness = "review"
```

In the returned payload, add:

```python
        "baseline_health": "healthy",
        "query_coverage": path_classification.query_coverage,
        "workflow_requirement": workflow_requirement,
        "path_adoption": _path_adoption_payload(path_classification),
```

In the no-active-generation return at lines 44-62, add:

```python
            "baseline_health": "missing",
            "query_coverage": "baseline_missing",
            "workflow_requirement": _workflow_requirement(intent),
            "path_adoption": {"adoptable_paths": [], "review_paths": [], "unadoptable_paths": [], "reasons": []},
```

In the selected/rejected conflict return, add the same fields with `baseline_health = "healthy"` and `query_coverage = "ambiguous_selection"`.

- [ ] **Step 4: Run query tests**

Run:

```bash
pytest tests/test_project_cognition_query.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/cognition/query.py tests/test_project_cognition_query.py
git commit -m "feat(cognition): route query gaps through update or review"
```

## Task 3: Map Update Adopts Safe New Paths

**Files:**
- Modify: `src/specify_cli/cognition/update.py`
- Modify: `tests/test_project_cognition_db.py`

- [ ] **Step 1: Add failing update adoption tests**

In `tests/test_project_cognition_db.py`, replace the old `test_apply_cognition_update_records_partial_refresh_when_path_missing` expectation and add these tests:

```python
def test_apply_cognition_update_adopts_same_directory_missing_path(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    source_path = tmp_path / "src" / "auth" / "session.ts"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("export const session = true\n", encoding="utf-8")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/session.ts"], reason="unit-test")

    assert result["readiness"] == "ready"
    assert result["recommended_next_action"] == "retry_current_workflow"
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["adopted_paths"] == ["src/auth/session.ts"]
    assert result["missing_coverage"] == []
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute(
            "SELECT path, node_id, relation, confidence, evidence_id FROM path_index WHERE path = 'src/auth/session.ts'"
        ).fetchone()
        evidence = conn.execute("SELECT source_kind, source_path, extractor, attrs_json FROM evidence WHERE id = ?", (row["evidence_id"],)).fetchone()
    assert dict(row) | {"evidence_id": row["evidence_id"]} == {
        "path": "src/auth/session.ts",
        "node_id": "capability:auth.login",
        "relation": "provisional_path",
        "confidence": "weak",
        "evidence_id": row["evidence_id"],
    }
    assert evidence["source_kind"] == "path_adoption"
    assert evidence["source_path"] == "src/auth/session.ts"
    assert evidence["extractor"] == "map-update-adoption"
    assert json.loads(evidence["attrs_json"])["nearest_indexed_sibling"] == "src/auth/login.ts"
    status = read_cognition_status(tmp_path)
    assert status.baseline_state in {"", "ready"}
    assert status.freshness in {"", "fresh"}
    assert status.dirty_reasons == []


def test_apply_cognition_update_returns_review_for_small_uncertain_gap(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(tmp_path, changed_paths=["docs/future/idea.md"], reason="unit-test")

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["adopted_paths"] == []
    assert result["minimal_live_reads"] == ["docs/future/idea.md"]
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute("SELECT path FROM path_index WHERE path = 'docs/future/idea.md'").fetchone()
    assert row is None
    status = read_cognition_status(tmp_path)
    assert status.baseline_state in {"", "ready"}
    assert status.freshness == "possibly_stale"
    assert status.stale_paths == ["docs/future/idea.md"]
    assert status.dirty_reasons == []


def test_apply_cognition_update_routes_unadoptable_core_surface_to_rebuild(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(tmp_path, changed_paths=["scripts/release/package.ps1"], reason="unit-test")

    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
    assert result["unadoptable_paths"] == ["scripts/release/package.ps1"]
    assert result["minimal_live_reads"] == ["scripts/release/package.ps1"]
    status = read_cognition_status(tmp_path)
    assert status.baseline_state == "blocked"
    assert status.freshness == "stale"
    assert status.dirty_origin_command == "sp-map-update"
```

Keep the no-active-generation test expecting `needs_rebuild`.

- [ ] **Step 2: Run update tests and verify they fail**

Run:

```bash
pytest tests/test_project_cognition_db.py -q
```

Expected: FAIL because `apply_cognition_update()` does not classify or adopt missing paths yet.

- [ ] **Step 3: Implement update adoption**

In `src/specify_cli/cognition/update.py`, add imports:

```python
import hashlib

from .path_adoption import AdoptablePath, PathCoverageClassification, classify_path_coverage
```

Move `update_id = f"UPDATE-{uuid4().hex}"` before the transaction writes. After `_resolve_path_coverage(...)`, call:

```python
        path_classification = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=missing_paths,
            requested_paths=update_paths,
        )
        adopted_path_index_ids = _adopt_paths(
            conn,
            project_root=project_root,
            generation_id=generation_id,
            update_id=update_id,
            adoptable_paths=path_classification.adoptable_paths,
        )
        affected_nodes.update(item.node_id for item in path_classification.adoptable_paths)
        affected_route_records.update(adopted_path_index_ids)
```

Change `affected_nodes` and `affected_route_records` in `_resolve_path_coverage()` from local sets to returned lists, or convert them to sets immediately after return:

```python
        affected_nodes = set(affected_nodes)
        affected_route_records = set(affected_route_records)
```

Add helpers at the bottom of `update.py`:

```python
def _adopt_paths(
    conn: Any,
    *,
    project_root: Path,
    generation_id: str,
    update_id: str,
    adoptable_paths: list[AdoptablePath],
) -> list[str]:
    adopted_index_ids: list[str] = []
    for item in adoptable_paths:
        evidence_id = f"E-adopt-{uuid4().hex}"
        path_index_id = f"P-adopt-{uuid4().hex}"
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES (?, ?, 'path_adoption', ?, '', '', 'map-update-adoption', ?, ?, ?)",
            (
                evidence_id,
                generation_id,
                item.path,
                _adoption_content_hash(project_root, item.path, update_id),
                iso_now(),
                json.dumps(
                    {
                        "adoption_status": "provisional",
                        "adoption_reason": item.reason,
                        "nearest_indexed_sibling": item.nearest_indexed_sibling,
                        "update_id": update_id,
                    },
                    separators=(",", ": "),
                ),
            ),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES (?, ?, ?, ?, 'provisional_path', ?, ?, ?)",
            (path_index_id, generation_id, item.path, item.node_id, item.confidence, evidence_id, iso_now()),
        )
        adopted_index_ids.append(path_index_id)
    return adopted_index_ids


def _adoption_content_hash(project_root: Path, path: str, update_id: str) -> str:
    target = project_root / path
    hasher = hashlib.sha256()
    if target.exists() and target.is_file():
        hasher.update(target.read_bytes())
    else:
        hasher.update(f"{update_id}:{path}".encode("utf-8"))
    return hasher.hexdigest()
```

Add a result-state helper:

```python
def _result_state_for_update(classification: PathCoverageClassification, original_missing_paths: list[str]) -> str:
    if not original_missing_paths:
        return "ready"
    if classification.query_coverage == "adoptable_path_gap":
        return "ready"
    if classification.query_coverage == "uncertain_path_gap":
        return "review"
    return "needs_rebuild"
```

Build missing and unknown lists like this:

```python
        result_state = _result_state_for_update(path_classification, missing_paths)
        review_paths = list(path_classification.review_paths)
        unadoptable_paths = list(path_classification.unadoptable_paths)
        adopted_paths = [item.path for item in path_classification.adoptable_paths]
        known_unknowns = [
            f"path requires minimal live read before adoption: {path}" for path in review_paths
        ] + [
            f"path not safely adoptable by project cognition index: {path}" for path in unadoptable_paths
        ]
        minimal_live_reads = sorted(set(review_paths + unadoptable_paths))
        missing_coverage = known_unknowns
```

Set update attrs:

```python
            "path_adoption": {
                "query_coverage": path_classification.query_coverage,
                "adopted_paths": adopted_paths,
                "review_paths": review_paths,
                "unadoptable_paths": unadoptable_paths,
                "reasons": list(path_classification.reasons),
            },
            "adopted_paths": adopted_paths,
            "known_unknowns": known_unknowns,
            "minimal_live_reads": minimal_live_reads,
            "confidence": "weak" if adopted_paths or review_paths else "strong",
```

Update status after the transaction:

```python
    if result_state == "needs_rebuild":
        status.baseline_state = "blocked"
        status.freshness = "stale"
        status.stale_paths = list(unadoptable_paths)
        status.stale_reasons = list(missing_coverage)
        status.dirty_reasons = list(missing_coverage)
        status.dirty_origin_command = "sp-map-update"
    elif result_state == "review":
        status.baseline_state = "ready" if status.graph_ready else status.baseline_state
        status.freshness = "possibly_stale"
        status.stale_paths = list(review_paths)
        status.stale_reasons = list(missing_coverage)
        status.dirty_reasons = []
        status.dirty_origin_command = ""
    else:
        status.baseline_state = "ready" if status.graph_ready else status.baseline_state
        status.freshness = "fresh" if (adopted_paths or not missing_paths) else status.freshness
        status.stale_paths = []
        status.stale_reasons = []
        status.dirty_reasons = []
        status.dirty_origin_command = ""
```

Return:

```python
        "readiness": result_state,
        "recommended_next_action": _recommended_action_for_update_result(result_state),
        "adopted_paths": adopted_paths,
        "review_paths": review_paths,
        "unadoptable_paths": unadoptable_paths,
```

with helper:

```python
def _recommended_action_for_update_result(result_state: str) -> str:
    return {
        "ready": "retry_current_workflow",
        "review": "perform_minimal_live_reads",
        "needs_rebuild": "run_map_scan_build",
    }.get(result_state, "perform_minimal_live_reads")
```

- [ ] **Step 4: Run update tests**

Run:

```bash
pytest tests/test_project_cognition_db.py -q
```

Expected: PASS.

- [ ] **Step 5: Run classifier and query tests again**

Run:

```bash
pytest tests/test_project_cognition_path_adoption.py tests/test_project_cognition_query.py tests/test_project_cognition_db.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/cognition/update.py tests/test_project_cognition_db.py
git commit -m "feat(cognition): adopt safe new paths during update"
```

## Task 4: Freshness Mapping and Compatibility Helpers

**Files:**
- Modify: `src/specify_cli/project_cognition_status.py`
- Modify: `scripts/bash/project-map-freshness.sh`
- Modify: `scripts/powershell/project-map-freshness.ps1`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/test_project_map_freshness_scripts.py`

- [ ] **Step 1: Update Python freshness tests**

In `tests/test_project_map_status.py`, replace the singular path gap scan/build expectation:

```python
def test_assess_project_map_freshness_routes_singular_path_gap_to_update_not_rebuild(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    mod.mark_project_map_dirty(
        tmp_path,
        "path not covered by project cognition index: src/auth/missing.ts",
        origin_command="sp-map-update",
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=[],
        has_git=True,
    )

    assert result["freshness"] == "stale"
    assert result["readiness"] == "blocked"
    assert result["recommended_next_action"] == "run_map_update"
```

Keep the existing `58 changed paths missing from project cognition path_index` test expecting `run_map_scan_build`.

Add:

```python
def test_assess_project_map_freshness_routes_unadoptable_path_gap_to_scan_build(tmp_path):
    mod = _load_module()
    _write_cognition_baseline(tmp_path)

    mod.mark_project_map_dirty(
        tmp_path,
        "path not safely adoptable by project cognition index: scripts/release/package.ps1",
        origin_command="sp-map-update",
    )

    result = mod.assess_project_map_freshness(
        tmp_path,
        head_commit="head456",
        changed_files=[],
        has_git=True,
    )

    assert result["recommended_next_action"] == "run_map_scan_build"
```

- [ ] **Step 2: Update shell helper tests**

In `tests/test_project_map_freshness_scripts.py`, add this helper after `_seed_legacy_status()`:

```python
def _write_graph_ready_status_with_dirty_reason(repo: Path, reason: str) -> None:
    status_path = _project_cognition_status_path(repo)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "version": 3,
                "baseline_state": "blocked",
                "baseline_commit": subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "baseline_branch": "main",
                "baseline_built_at": "2026-05-17T00:00:00Z",
                "graph_ready": True,
                "graph_store_path": ".specify/project-cognition/project-cognition.db",
                "active_generation_id": "GEN-0001",
                "query_contract_version": 2,
                "update_contract_version": 1,
                "freshness": "stale",
                "dirty": True,
                "dirty_reasons": [reason],
                "dirty_origin_command": "sp-map-update",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    db_path = repo / ".specify" / "project-cognition" / "project-cognition.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"SQLite test database marker")
```

Then add:

```python
def test_freshness_helpers_route_singular_path_gap_to_update(git_repo: Path):
    _write_graph_ready_status_with_dirty_reason(
        git_repo,
        "path not covered by project cognition index: src/auth/missing.ts",
    )

    bash_result = _run_bash(git_repo, "check")
    ps_result = _run_powershell(git_repo, "check")

    assert bash_result["recommended_next_action"] == "run_map_update"
    assert ps_result["recommended_next_action"] == "run_map_update"
```

- [ ] **Step 3: Run freshness tests and verify they fail**

Run:

```bash
pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q
```

Expected: FAIL because Python and shell helpers still route any path-index gap reason to scan/build.

- [ ] **Step 4: Implement Python freshness mapping**

In `src/specify_cli/project_cognition_status.py`, replace `_has_path_index_coverage_gap_reason()` usage in `recommended_next_action_for_freshness()`:

```python
    if _has_unadoptable_path_index_gap_reason(reasons):
        return NEXT_ACTION_MAP_SCAN_BUILD
```

Add:

```python
def _has_unadoptable_path_index_gap_reason(reasons: list[str]) -> bool:
    reason_text = " ".join(str(reason or "") for reason in reasons).lower()
    compact_reason_text = reason_text.replace("-", "_").replace(" ", "_")
    if "path_not_safely_adoptable_by_project_cognition_index" in compact_reason_text:
        return True
    if "unadoptable" in compact_reason_text and "path" in compact_reason_text:
        return True
    if "missing_from_project_cognition_path_index" in compact_reason_text:
        count_match = re.search(r"\b(\d+)\s+changed\s+paths?\s+missing", reason_text)
        if count_match and int(count_match.group(1)) > 25:
            return True
    return False
```

Add `import re` at the top of `src/specify_cli/project_cognition_status.py`.

Delete `_has_path_index_coverage_gap_reason()` after replacing its only call in `recommended_next_action_for_freshness()`. Verify there are no remaining references:

```bash
rg -n "_has_path_index_coverage_gap_reason" src tests
```

Expected: no matches.

- [ ] **Step 5: Implement Bash helper mapping**

In `scripts/bash/project-map-freshness.sh`, add a helper near other reason helpers:

```bash
path_gap_requires_rebuild() {
    local reasons="$1"
    local lower
    lower="$(printf '%s' "$reasons" | tr '[:upper:]' '[:lower:]')"
    if [[ "$lower" == *"path not safely adoptable by project cognition index"* ]]; then
        return 0
    fi
    if [[ "$lower" == *"unadoptable"* && "$lower" == *"path"* ]]; then
        return 0
    fi
    if [[ "$lower" =~ ([0-9]+)[[:space:]]+changed[[:space:]]+paths?[[:space:]]+missing ]]; then
        if [[ "${BASH_REMATCH[1]}" -gt 25 ]]; then
            return 0
        fi
    fi
    return 1
}
```

In `emit_check_json` or the freshness-to-action case, when freshness is `stale`, use the helper against the serialized reasons and choose `run_map_scan_build` only when it returns true; otherwise choose `run_map_update`.

- [ ] **Step 6: Implement PowerShell helper mapping**

In `scripts/powershell/project-map-freshness.ps1`, add:

```powershell
function Test-PathGapRequiresRebuild {
    param([object[]]$Reasons)
    $text = (($Reasons | ForEach-Object { [string]$_ }) -join " ").ToLowerInvariant()
    if ($text.Contains("path not safely adoptable by project cognition index")) { return $true }
    if ($text.Contains("unadoptable") -and $text.Contains("path")) { return $true }
    $match = [regex]::Match($text, '(\d+)\s+changed\s+paths?\s+missing')
    if ($match.Success -and ([int]$match.Groups[1].Value) -gt 25) { return $true }
    return $false
}
```

Where stale freshness maps `RecommendedNextAction`, use:

```powershell
if (Test-PathGapRequiresRebuild -Reasons $Reasons) {
    $recommendedNextAction = "run_map_scan_build"
} else {
    $recommendedNextAction = "run_map_update"
}
```

- [ ] **Step 7: Run freshness tests**

Run:

```bash
pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/specify_cli/project_cognition_status.py scripts/bash/project-map-freshness.sh scripts/powershell/project-map-freshness.ps1 tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py
git commit -m "fix(cognition): reserve rebuild for unadoptable path gaps"
```

## Task 5: Generated Guidance and Documentation

**Files:**
- Modify: `templates/commands/map-update.md`
- Modify: `templates/commands/discussion.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/prd-scan.md`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/senior-consequence-analysis-gate.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify tests that assert old guidance text.

- [ ] **Step 1: Find stale guidance**

Run:

```bash
rg -n "missing from `?path_index|missing from project cognition path_index|cannot create absent path coverage|changed paths are missing from `?path_index|repeating .*map-update.*cannot" templates README.md PROJECT-HANDBOOK.md src tests
```

Expected: matches in `PROJECT-HANDBOOK.md`, `README.md`, `templates/project-handbook-template.md`, `templates/command-partials/common/context-loading-gradient.md`, `templates/commands/discussion.md`, `src/specify_cli/__init__.py`, and guidance tests.

- [ ] **Step 2: Update the shared context-loading gradient**

In `templates/command-partials/common/context-loading-gradient.md`, replace:

```markdown
- `stale` with changed paths missing from `path_index` -> block and rebuild through `sp-map-scan -> sp-map-build`; repeating `sp-map-update` cannot create absent path coverage
```

with:

```markdown
- `stale` with adoptable or uncertain path-index gaps -> route through `sp-map-update` or perform returned `minimal_live_reads`; do not rebuild solely because a path is new
- `stale` with unadoptable path-index gaps, missing baseline, unusable DB, schema mismatch, explicit rebuild, or baseline identity invalidation -> rebuild through `sp-map-scan -> sp-map-build`
```

- [ ] **Step 3: Update `templates/commands/discussion.md`**

Replace the freshness handling block for stale and partial refresh with:

```markdown
- `stale`: continue discussion when the conversation is exploratory and the runtime returns `review` or `perform_minimal_live_reads`; route to `{{invoke:map-update}}` when the user asks to write project facts that need proof; route to `{{invoke:map-scan}} -> {{invoke:map-build}}` only for missing/unusable/schema-incompatible baselines, explicit rebuild, baseline identity invalidation, or unadoptable path-index gaps.
- `support_drift`: stop for support-surface cleanup without reflexively routing to `{{invoke:map-update}}`.
- `partial_refresh`: continue discussion only with unknowns and confidence labels; before handoff or source-changing planning, follow `recommended_next_action`.
```

- [ ] **Step 4: Update `templates/commands/map-update.md`**

Add under "Incremental Rule":

```markdown
- When changed paths are missing from `path_index`, classify them before escalating: adoptable paths get provisional `path_index` coverage, uncertain paths return `review` with `minimal_live_reads`, and only unadoptable gaps route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- Provisional adoption must write valid graph records: an adoption `evidence` row plus a `path_index` row with `relation="provisional_path"` and graph confidence `weak` or `partial`.
```

- [ ] **Step 5: Update planning/implementation command guidance**

In `templates/commands/specify.md`, `plan.md`, `tasks.md`, `analyze.md`, `debug.md`, `quick.md`, and `prd-scan.md`, keep `needs_rebuild` routing but clarify that path-index gaps become `needs_rebuild` only after adoption classification.

Use this wording where a concise replacement is needed:

```markdown
- `needs_update`: route through `{{invoke:map-update}}`; this includes adoptable missing path-index coverage.
- `review`: perform returned `minimal_live_reads` and carry unknowns/confidence into artifacts.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; this is reserved for missing/unusable/schema-incompatible baselines, explicit rebuild, baseline identity invalidation, or unadoptable coverage gaps.
```

- [ ] **Step 6: Update passive skill and integration renderer**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, replace any blanket rebuild instruction for missing path coverage with the same three-way adoption/review/unadoptable wording.

In `src/specify_cli/integrations/base.py`, update generated gate text that says:

```text
needs_rebuild routes through map-scan/map-build
```

so it still routes `needs_rebuild`, but does not state that every missing path-index gap is `needs_rebuild`.

- [ ] **Step 7: Update README and handbook**

In `PROJECT-HANDBOOK.md`, replace the line:

```markdown
- If changed paths are missing from project cognition `path_index`, rerun `sp-map-scan -> sp-map-build`; repeating `sp-map-update` cannot create absent path coverage.
```

with:

```markdown
- If changed paths are missing from project cognition `path_index`, let `sp-map-update` classify the gap first. Adoptable paths get provisional coverage, uncertain paths return `minimal_live_reads`, and only unadoptable gaps require `sp-map-scan -> sp-map-build`.
```

Apply the same policy to README and `templates/project-handbook-template.md`.

- [ ] **Step 8: Update guidance tests**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_specify_guidance_docs.py -q
```

Expected: FAIL on old text assertions. Update each failing assertion to check for the new policy text in that test's loaded content variable:

```python
assert "adoptable paths get provisional coverage" in content.lower()
assert "only unadoptable" in content.lower()
assert "cannot create absent path coverage" not in content.lower()
```

When a test uses a variable name other than `content`, keep the same assertions with that local variable. Do not weaken tests to generic substring checks that would allow the old blanket rebuild wording.

- [ ] **Step 9: Run guidance tests**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add templates README.md PROJECT-HANDBOOK.md src/specify_cli/integrations/base.py tests
git commit -m "docs(cognition): update refresh routing guidance"
```

## Task 6: CLI Integration and Final Verification

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Search CLI output for stale copy**

Run:

```bash
rg -n "cannot create absent path coverage|Changed paths are missing from the project cognition path_index|run_map_scan_build|partial_refresh" src/specify_cli/__init__.py tests/integrations/test_cli.py
```

Expected: matches around CLI status/preflight output and integration tests.

- [ ] **Step 2: Update CLI copy**

In `src/specify_cli/__init__.py`, replace:

```python
"Changed paths are missing from the project cognition path_index; repeating [cyan]/sp-map-update[/cyan] cannot create absent path coverage."
```

replace it with:

```python
"Changed paths are missing from the project cognition path_index. Run [cyan]/sp-map-update[/cyan] first so adoptable paths can receive provisional coverage; rebuild only when the gap is unadoptable."
```

Do not change CLI command names or Typer surfaces.

- [ ] **Step 3: Update integration tests**

In `tests/integrations/test_cli.py`, change assertions that expect `recommended_next_action == "run_map_scan_build"` for singular missing path update to:

```python
assert payload["recommended_next_action"] in {
    "run_map_update",
    "perform_minimal_live_reads",
    "retry_current_workflow",
}
```

Only keep strict `run_map_scan_build` assertions for missing active generation, schema/DB invalidity, explicit rebuild, or unadoptable coverage gap fixtures.

- [ ] **Step 4: Run focused runtime tests**

Run:

```bash
pytest tests/test_project_cognition_path_adoption.py tests/test_project_cognition_query.py tests/test_project_cognition_db.py tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Run guidance tests**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 6: Run broad verification**

Run:

```bash
pytest -q
```

Expected: PASS. If unrelated tests fail, capture the failing test names and error summaries before deciding whether to fix or report them.

- [ ] **Step 7: Inspect final diff**

Run:

```bash
git diff --stat
git diff --check
git status --short
```

Expected: no whitespace errors; only cognition runtime, tests, shell helpers, templates, and docs changed.

- [ ] **Step 8: Commit final CLI/test cleanup**

Run:

```bash
git diff --quiet -- src/specify_cli/__init__.py tests/integrations/test_cli.py
```

If the command exits with status 1, commit the Task 6 cleanup:

```bash
git add src/specify_cli/__init__.py tests/integrations/test_cli.py
git commit -m "test(cognition): verify self-healing refresh routing"
```

If the command exits with status 0, no Task 6 commit is needed.

## Final Acceptance

The branch is complete when all are true:

- Query on an adoptable missing path returns `needs_update`, not `needs_rebuild`.
- Query in `discussion` on an uncertain path returns `review` and `perform_minimal_live_reads`.
- Update on an adoptable path writes valid `evidence` and `path_index` records.
- Update on an uncertain path returns `review` without blocking the baseline.
- Update on an unadoptable core surface returns `needs_rebuild`.
- Python, Bash, and PowerShell freshness helpers no longer map every path-index gap to scan/build.
- Generated guidance tells agents to classify/adopt/review before rebuild.
- Full pytest passes, or any remaining failures are documented as unrelated with evidence.
