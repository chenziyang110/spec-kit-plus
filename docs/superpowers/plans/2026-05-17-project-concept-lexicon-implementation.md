# Project Concept Lexicon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Project Concept Lexicon runtime contract so agents can select project concepts, query route packs, and use one shared `sp-*` consumer gate before brownfield source reads.

**Architecture:** Keep `nodes`, `edges`, `claims`, and `evidence` as canonical truth. Add concept candidates, selected/rejected concepts, route packs, and validation as projections over the existing SQLite graph indexes rather than a second concept graph. Update `sp-map-scan`, `sp-map-build`, `sp-map-update`, and shared consumer templates so the generated workflow contract matches the runtime.

**Tech Stack:** Python 3.11+, Typer CLI, SQLite FTS5, pytest, Markdown workflow templates.

---

## Scope Check

This is one integrated subsystem: the query runtime contract and its generated workflow consumers. Do not split it into unrelated branches because the public contract version, query payload shape, validation, and templates must ship together.

The current worktree contains unrelated modified files. Implementation commits must stage only files touched by each task.

## File Structure

- `src/specify_cli/cognition/db.py`: Runtime contract version constants and metadata publication.
- `src/specify_cli/cognition/query.py`: Query plan payload, selected/rejected concept resolution, readiness rules, candidate suppression, and route pack generation.
- `src/specify_cli/cognition/lexicon.py`: Concept candidate projection from nodes, aliases, paths, symbols, query examples, edges, and metadata.
- `src/specify_cli/cognition/update.py`: Patch-in-active-generation update metadata for retrieval-signal maintenance.
- `src/specify_cli/cognition/validation.py`: Read-only validation for query contract v2 and route-pack source ingredients.
- `src/specify_cli/__init__.py`: CLI query-plan parser and command payload forwarding.
- `templates/command-partials/common/context-loading-gradient.md`: Authoritative shared consumer protocol.
- `templates/command-partials/common/navigation-check.md`: Compatibility shim that points to the shared protocol.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: Skills mirror of the shared consumer protocol.
- `templates/commands/map-scan.md`: Scan duties for retrieval signals.
- `templates/commands/map-build.md`: Build duties for concept projection and route-pack ingredients.
- `templates/commands/map-update.md`: Incremental concept retrieval signal maintenance duties.
- `templates/commands/analyze.md`: `sp-analyze` consumer wording when command-specific text is needed.
- `tests/test_project_cognition_db.py`: Metadata contract tests.
- `tests/test_project_cognition_query.py`: Lexicon and query runtime behavior tests.
- `tests/test_project_cognition_validation.py`: Build validation tests.
- `tests/integrations/test_cli.py`: CLI query-plan parser and JSON output tests.
- `tests/test_map_scan_build_template_guidance.py`: Scan/build/update template guidance tests.
- `tests/test_runtime_handbook_contract.py`: Shared consumer protocol tests.
- `tests/test_project_map_hard_gate_guidance.py`: Shared gate expectations.

---

### Task 1: Bump Project Cognition Query Contract Version

**Files:**
- Modify: `src/specify_cli/cognition/db.py`
- Modify: `src/specify_cli/cognition/validation.py`
- Test: `tests/test_project_cognition_db.py`
- Test: `tests/test_project_cognition_validation.py`

- [ ] **Step 1: Write failing metadata tests**

Update `tests/test_project_cognition_db.py` contract expectations from version `1` to version `2`.

Use this assertion shape in `test_publish_cognition_runtime_metadata_writes_db_and_status_runtime_fields`:

```python
    assert status.query_contract_version == 2
    assert status.update_contract_version == 1

    with closing(connect_cognition_db(tmp_path)) as conn:
        rows = conn.execute(
            "SELECT key, value_json FROM metadata WHERE key IN "
            "('baseline_state', 'graph_ready', 'graph_store_path', 'active_generation_id', "
            "'query_contract_version', 'update_contract_version')"
        ).fetchall()

    metadata = {str(row["key"]): row["value_json"] for row in rows}
    assert metadata == {
        "baseline_state": '"ready"',
        "graph_ready": "true",
        "graph_store_path": '".specify/project-cognition/project-cognition.db"',
        "active_generation_id": '"GEN-0001"',
        "query_contract_version": "2",
        "update_contract_version": "1",
    }
```

Update helper status payloads in `tests/test_project_cognition_validation.py` from `"query_contract_version": 1` to `"query_contract_version": 2`.

- [ ] **Step 2: Add validation failure test for legacy query contract**

Add this test to `tests/test_project_cognition_validation.py`:

```python
def test_validate_build_blocks_legacy_query_contract_version(tmp_path: Path) -> None:
    generation_id = _seed_query_ready_runtime(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "UPDATE metadata SET value_json = '1' WHERE key = 'query_contract_version'"
        )
        conn.commit()
    write_cognition_status(
        tmp_path,
        CognitionStatus(
            version=3,
            baseline_state="ready",
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id=generation_id,
            query_contract_version=1,
            update_contract_version=1,
            freshness="fresh",
        ),
    )

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("metadata.query_contract_version" in message for message in result["errors"])
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_db.py::test_publish_cognition_runtime_metadata_writes_db_and_status_runtime_fields tests/test_project_cognition_validation.py::test_validate_build_blocks_legacy_query_contract_version -q
```

Expected: failures showing metadata still publishes or accepts `query_contract_version` value `1`.

- [ ] **Step 4: Add contract version constants and publish v2**

In `src/specify_cli/cognition/db.py`, add constants near `SCHEMA_VERSION`:

```python
SCHEMA_VERSION = 1
QUERY_CONTRACT_VERSION = 2
UPDATE_CONTRACT_VERSION = 1
```

In `publish_cognition_runtime_metadata`, replace literal contract versions with constants:

```python
    metadata: dict[str, object] = {
        "baseline_state": "ready",
        "graph_ready": True,
        "graph_store_path": ".specify/project-cognition/project-cognition.db",
        "active_generation_id": active_generation_id,
        "query_contract_version": QUERY_CONTRACT_VERSION,
        "update_contract_version": UPDATE_CONTRACT_VERSION,
    }
```

In the status payload update block, use the same constants:

```python
            "query_contract_version": QUERY_CONTRACT_VERSION,
            "update_contract_version": UPDATE_CONTRACT_VERSION,
```

- [ ] **Step 5: Validate v2 metadata**

In `src/specify_cli/cognition/validation.py`, import the constants:

```python
from .db import QUERY_CONTRACT_VERSION, SCHEMA_VERSION, UPDATE_CONTRACT_VERSION
```

Then update `_validate_runtime_metadata` expected values:

```python
    expected = {
        "baseline_state": "ready",
        "graph_ready": True,
        "graph_store_path": EXPECTED_GRAPH_STORE_PATH,
        "active_generation_id": active_generation_id,
        "query_contract_version": QUERY_CONTRACT_VERSION,
        "update_contract_version": UPDATE_CONTRACT_VERSION,
    }
```

- [ ] **Step 6: Run focused contract tests**

Run:

```powershell
pytest tests/test_project_cognition_db.py::test_publish_cognition_runtime_metadata_writes_db_and_status_runtime_fields tests/test_project_cognition_validation.py::test_validate_build_blocks_legacy_query_contract_version tests/test_project_cognition_validation.py::test_validate_build_accepts_query_ready_runtime -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/cognition/db.py src/specify_cli/cognition/validation.py tests/test_project_cognition_db.py tests/test_project_cognition_validation.py
git commit -m "feat: publish project cognition query contract v2"
```

---

### Task 2: Extend Query Plan Parsing for Selected and Rejected Concepts

**Files:**
- Modify: `src/specify_cli/cognition/query.py`
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/test_project_cognition_query.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add unit tests for query plan payload fields**

Add this test to `tests/test_project_cognition_query.py`:

```python
def test_query_echoes_selected_and_rejected_concepts_in_plan(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="login provider work",
        selected_concepts=["capability:auth.login"],
        rejected_concepts=["capability:llm-provider"],
        selection_reason="User is changing login behavior, not model provider settings.",
        expanded_queries=["login"],
        paths=[],
    )

    assert result["query_plan"]["selected_concepts"] == ["capability:auth.login"]
    assert result["query_plan"]["rejected_concepts"] == ["capability:llm-provider"]
    assert result["query_plan"]["selection_reason"] == (
        "User is changing login behavior, not model provider settings."
    )
    assert result["selected_concepts"] == ["capability:auth.login"]
    assert result["rejected_concepts"] == ["capability:llm-provider"]
```

- [ ] **Step 2: Add unknown and conflicting selection tests**

Add these tests to `tests/test_project_cognition_query.py`:

```python
def test_query_unknown_selected_concept_returns_review_without_paths(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="unknown concept",
        selected_concepts=["capability:missing"],
        paths=[],
    )

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert "selected concept not covered by active generation: capability:missing" in result["missing_coverage"]


def test_query_unknown_selected_concept_with_paths_returns_needs_update(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="unknown concept",
        selected_concepts=["capability:missing"],
        paths=["src/new/provider.ts"],
    )

    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    assert "selected concept not covered by active generation: capability:missing" in result["missing_coverage"]
    assert "path not covered by project cognition index: src/new/provider.ts" in result["missing_coverage"]


def test_query_conflicting_selected_and_rejected_concept_returns_ambiguous(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="login",
        selected_concepts=["capability:auth.login"],
        rejected_concepts=["capability:auth.login"],
        expanded_queries=["login"],
        paths=[],
    )

    assert result["readiness"] == "ambiguous"
    assert result["recommended_next_action"] == "ask_user_to_select_candidate"
    assert "concept selected and rejected: capability:auth.login" in result["missing_coverage"]
    assert result["affected_nodes"] == []
```

- [ ] **Step 3: Add CLI parser test**

In `tests/integrations/test_cli.py`, add a parser-focused test near existing project cognition query plan tests:

```python
def test_project_cognition_query_accepts_selected_and_rejected_concepts_in_query_plan(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from specify_cli import app
    from specify_cli.cognition import connect_cognition_db, ensure_cognition_db, seed_active_generation

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specify").mkdir()
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'hash-login', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-14T00:00:00Z', '2026-05-14T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-14T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    query_plan = json.dumps(
        {
            "raw_query": "login work",
            "selected_concepts": ["capability:auth.login"],
            "rejected_concepts": ["capability:llm-provider"],
            "selection_reason": "login scope",
            "expanded_queries": ["login"],
            "paths": ["src/auth/login.ts"],
        }
    )

    result = CliRunner().invoke(
        app,
        [
            "project-cognition",
            "query",
            "--intent",
            "implement",
            "--query-plan",
            query_plan,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["query_plan"]["selected_concepts"] == ["capability:auth.login"]
    assert payload["query_plan"]["rejected_concepts"] == ["capability:llm-provider"]
    assert payload["query_plan"]["selection_reason"] == "login scope"
```

Ensure the file already imports `json` and `closing`. If it does not, add:

```python
from contextlib import closing
import json
```

- [ ] **Step 4: Run tests and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_query.py::test_query_echoes_selected_and_rejected_concepts_in_plan tests/test_project_cognition_query.py::test_query_unknown_selected_concept_returns_review_without_paths tests/test_project_cognition_query.py::test_query_unknown_selected_concept_with_paths_returns_needs_update tests/test_project_cognition_query.py::test_query_conflicting_selected_and_rejected_concept_returns_ambiguous -q
```

Expected: failures because `query_project_cognition` does not accept selected/rejected concept parameters.

- [ ] **Step 5: Extend query function signature and payload**

In `src/specify_cli/cognition/query.py`, change `query_project_cognition` signature:

```python
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
```

Change the query plan construction call:

```python
    query_plan = _query_plan_payload(
        query_text=query_text,
        expanded_queries=expanded_queries,
        paths=paths,
        selected_concepts=selected_concepts,
        rejected_concepts=rejected_concepts,
        selection_reason=selection_reason,
    )
```

Replace `_query_plan_payload` with:

```python
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
        "selected_concepts": [
            concept for concept in (selected_concepts or []) if normalize_query_token(concept)
        ],
        "rejected_concepts": [
            concept for concept in (rejected_concepts or []) if normalize_query_token(concept)
        ],
        "selection_reason": str(selection_reason or "").strip(),
    }
```

- [ ] **Step 6: Add selected/rejected resolution helpers**

Add these helpers to `src/specify_cli/cognition/query.py`:

```python
def _resolve_selected_concepts(
    conn: Any,
    generation_id: str,
    selected_concepts: list[str],
    rejected_concepts: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    rejected = set(rejected_concepts)
    conflicts = sorted(concept for concept in selected_concepts if concept in rejected)
    valid_candidates: list[dict[str, Any]] = []
    missing: list[str] = []
    for concept_id in selected_concepts:
        if concept_id in rejected:
            continue
        row = conn.execute(
            "SELECT id, type, title, confidence FROM nodes WHERE generation_id = ? AND id = ?",
            (generation_id, concept_id),
        ).fetchone()
        if row is None:
            missing.append(concept_id)
            continue
        evidence_ids = _node_evidence(conn, concept_id)
        valid_candidates.append(
            {
                "node_id": str(row["id"]),
                "label": str(row["title"]),
                "target_type": str(row["type"]) if str(row["type"]) == "symptom" else "capability",
                "score": 0.99,
                "matched_by": [f"selected_concept:{row['id']}"],
                "evidence_ids": evidence_ids,
            }
        )
    return valid_candidates, missing, conflicts


def _node_evidence(conn: Any, node_id: str) -> list[str]:
    rows = conn.execute("SELECT evidence_id FROM node_evidence WHERE node_id = ?", (node_id,)).fetchall()
    return sorted(str(row["evidence_id"]) for row in rows)
```

Use empty evidence fallback later through route pack generation; do not block selected concept resolution solely because `node_evidence` is empty in older seeded tests.

- [ ] **Step 7: Apply selected/rejected rules in query**

Inside the database block in `query_project_cognition`, before `_merge_candidates`, add:

```python
        selected_concept_ids = list(query_plan["selected_concepts"])
        rejected_concept_ids = set(query_plan["rejected_concepts"])
        selected_candidates, missing_selected_concepts, conflicting_concepts = _resolve_selected_concepts(
            conn,
            generation_id,
            selected_concept_ids,
            list(rejected_concept_ids),
        )
```

Then build candidates as:

```python
        candidates = _merge_candidates(
            selected_candidates
            + _resolve_aliases(conn, generation_id, query_text)
            + _resolve_claim_fts(conn, generation_id, query_text)
            + _resolve_expanded_queries(conn, generation_id, expanded_queries or [])
        )
        if rejected_concept_ids:
            candidates = [
                candidate for candidate in candidates if candidate["node_id"] not in rejected_concept_ids
            ]
```

After `missing_coverage` is created, extend it:

```python
        missing_coverage.extend(
            f"selected concept not covered by active generation: {concept_id}"
            for concept_id in missing_selected_concepts
        )
        missing_coverage.extend(
            f"concept selected and rejected: {concept_id}"
            for concept_id in conflicting_concepts
        )
```

After initial readiness computation, apply:

```python
        if conflicting_concepts:
            readiness = "ambiguous"
        elif missing_selected_concepts and missing_paths:
            readiness = "needs_update"
        elif missing_selected_concepts:
            readiness = "review"
```

Include top-level echoes in every return payload:

```python
            "selected_concepts": list(query_plan["selected_concepts"]),
            "rejected_concepts": list(query_plan["rejected_concepts"]),
```

In the no-generation return payload, include the same fields from `query_plan`.

- [ ] **Step 8: Extend CLI parser and forwarding**

In `src/specify_cli/__init__.py`, update `_parse_project_cognition_query_plan` list validation:

```python
    for list_key in ("expanded_queries", "paths", "selected_concepts", "rejected_concepts"):
        value = payload.get(list_key, [])
        if value and not isinstance(value, list):
            raise typer.BadParameter(f"--query-plan {list_key} must be a list")
```

In `project_cognition_query_command`, compute:

```python
    effective_selected_concepts = [
        str(value) for value in planned_query.get("selected_concepts", []) if str(value).strip()
    ]
    effective_rejected_concepts = [
        str(value) for value in planned_query.get("rejected_concepts", []) if str(value).strip()
    ]
    effective_selection_reason = str(planned_query.get("selection_reason") or "")
```

Forward them to `query_project_cognition`:

```python
            selected_concepts=effective_selected_concepts,
            rejected_concepts=effective_rejected_concepts,
            selection_reason=effective_selection_reason,
```

Add them to the missing-DB fallback `query_plan` and top-level payload.

- [ ] **Step 9: Run focused tests**

Run:

```powershell
pytest tests/test_project_cognition_query.py::test_query_echoes_selected_and_rejected_concepts_in_plan tests/test_project_cognition_query.py::test_query_unknown_selected_concept_returns_review_without_paths tests/test_project_cognition_query.py::test_query_unknown_selected_concept_with_paths_returns_needs_update tests/test_project_cognition_query.py::test_query_conflicting_selected_and_rejected_concept_returns_ambiguous tests/integrations/test_cli.py::test_project_cognition_query_accepts_selected_and_rejected_concepts_in_query_plan -q
```

Expected: all pass.

- [ ] **Step 10: Commit**

```powershell
git add src/specify_cli/cognition/query.py src/specify_cli/__init__.py tests/test_project_cognition_query.py tests/integrations/test_cli.py
git commit -m "feat: accept project cognition concept selections"
```

---

### Task 3: Project Concept Candidate Projection in Lexicon

**Files:**
- Modify: `src/specify_cli/cognition/lexicon.py`
- Test: `tests/test_project_cognition_query.py`

- [ ] **Step 1: Add concept candidate lexicon test**

Add this helper to `tests/test_project_cognition_query.py`:

```python
def _seed_agent_teams_graph(project_root: Path) -> str:
    ensure_cognition_db(project_root)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-team-runtime', ?, 'file', 'src/specify_cli/codex_team/runtime.py', 'abc123', '1-160', 'test', 'hash-team', '2026-05-17T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:codex-team-runtime', ?, 'capability', 'Agent teams runtime', 'strong', ?, '2026-05-17T00:00:00Z', '2026-05-17T00:00:00Z')",
            (
                generation_id,
                json.dumps(
                    {
                        "domain": "agent teams",
                        "disambiguation_hint": "Provider refers to team runtime backend/provider, not LLM provider.",
                    }
                ),
            ),
        )
        conn.execute(
            "INSERT INTO node_evidence(node_id, evidence_id) VALUES ('capability:codex-team-runtime', 'E-team-runtime')"
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-team-provider', ?, 'provider', 'provider', 'capability', 'capability:codex-team-runtime', 'en', 'evidence', 'strong', 'E-team-runtime')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-sp-teams', ?, 'sp-teams', 'sp-teams', 'capability', 'capability:codex-team-runtime', 'en', 'evidence', 'strong', 'E-team-runtime')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-team-runtime', ?, 'src/specify_cli/codex_team/runtime.py', 'capability:codex-team-runtime', 'owns', 'strong', 'E-team-runtime', '2026-05-17T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO symbol_index(id, generation_id, symbol_name, normalized_symbol, node_id, path, relation, evidence_id, confidence) "
            "VALUES ('S-team-provider', ?, 'TeamProvider', 'teamprovider', 'capability:codex-team-runtime', 'src/specify_cli/codex_team/runtime.py', 'owns', 'E-team-runtime', 'strong')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO query_examples(id, generation_id, query_text, intent, expected_target_type, expected_target_id, language, source, created_at) "
            "VALUES ('Q-team-provider', ?, 'add provider support to agent teams', 'implement', 'capability', 'capability:codex-team-runtime', 'en', 'test', '2026-05-17T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()
    return generation_id
```

Add the test:

```python
def test_lexicon_returns_concept_candidates_for_project_terms(tmp_path: Path) -> None:
    _seed_agent_teams_graph(tmp_path)

    result = project_cognition_lexicon(
        tmp_path,
        intent="implement",
        query_text="I want to add provider support to agent teams",
    )

    candidate = result["concept_candidates"][0]
    assert candidate["concept_id"] == "capability:codex-team-runtime"
    assert candidate["label"] == "Agent teams runtime"
    assert candidate["kind"] == "capability"
    assert candidate["domain"] == "agent teams"
    assert "provider" in candidate["matched_terms"]
    assert "provider" in candidate["aliases"]
    assert "sp-teams" in candidate["aliases"]
    assert candidate["colloquial_matches"] == ["add provider support to agent teams"]
    assert candidate["target_nodes"] == ["capability:codex-team-runtime"]
    assert candidate["disambiguation_hint"] == "Provider refers to team runtime backend/provider, not LLM provider."
    assert candidate["confidence"] == "strong"
    assert candidate["evidence_ids"] == ["E-team-runtime"]
    assert result["query_planning_contract"]["agent_responsibility"] == (
        "select and reject concepts before querying"
    )
```

Add `import json` near the top of `tests/test_project_cognition_query.py` if it is not already present.

- [ ] **Step 2: Run lexicon test and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_query.py::test_lexicon_returns_concept_candidates_for_project_terms -q
```

Expected: failure because `concept_candidates` is missing.

- [ ] **Step 3: Enrich lexicon data collection**

In `src/specify_cli/cognition/lexicon.py`, import JSON:

```python
import json
```

Add helpers:

```python
def _node_rows(conn: Any, generation_id: str, *, limit: int) -> list[Any]:
    query = "SELECT id, type, title, confidence, attrs_json FROM nodes WHERE generation_id = ? ORDER BY title"
    params: tuple[Any, ...] = (generation_id,)
    if limit > 0:
        query = f"{query} LIMIT ?"
        params = (generation_id, limit)
    return conn.execute(query, params).fetchall()


def _node_attrs(row: Any) -> dict[str, Any]:
    try:
        payload = json.loads(str(row["attrs_json"] or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _alias_records_by_node(conn: Any, generation_id: str) -> dict[str, list[dict[str, str]]]:
    rows = conn.execute(
        "SELECT target_id, alias, confidence, evidence_id FROM alias_index "
        "WHERE generation_id = ? ORDER BY alias",
        (generation_id,),
    ).fetchall()
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        result[str(row["target_id"])].append(
            {
                "alias": str(row["alias"]),
                "confidence": str(row["confidence"]),
                "evidence_id": str(row["evidence_id"]),
            }
        )
    return result


def _query_examples_by_node(conn: Any, generation_id: str) -> dict[str, list[str]]:
    rows = conn.execute(
        "SELECT expected_target_id, query_text FROM query_examples "
        "WHERE generation_id = ? ORDER BY query_text",
        (generation_id,),
    ).fetchall()
    result: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        result[str(row["expected_target_id"])].append(str(row["query_text"]))
    return result
```

Update `_lexicon_terms` to use `_node_rows` while preserving existing output keys.

- [ ] **Step 4: Add concept candidate projection helper**

Add:

```python
def _concept_candidates(
    rows: list[Any],
    *,
    query_text: str,
    aliases: dict[str, set[str]],
    alias_records: dict[str, list[dict[str, str]]],
    paths: dict[str, set[str]],
    symbols: dict[str, set[str]],
    query_examples: dict[str, list[str]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    query_terms = set(_split_terms(query_text))
    for row in rows:
        node_id = str(row["id"])
        attrs = _node_attrs(row)
        alias_values = sorted(aliases.get(node_id, []))
        path_values = sorted(paths.get(node_id, []))
        symbol_values = sorted(symbols.get(node_id, []))
        examples = sorted(query_examples.get(node_id, []))
        candidate_terms = set(_split_terms(" ".join([str(row["title"]), *alias_values, *path_values, *symbol_values, *examples])))
        matched_terms = sorted(query_terms & candidate_terms) if query_terms else []
        evidence_ids = sorted(
            {
                record["evidence_id"]
                for record in alias_records.get(node_id, [])
                if record.get("evidence_id")
            }
        )
        if not evidence_ids:
            evidence_ids = sorted(_evidence_for_paths(paths.get(node_id, set()), alias_records.get(node_id, [])))
        candidates.append(
            {
                "concept_id": node_id,
                "label": str(row["title"]),
                "kind": str(row["type"]),
                "domain": str(attrs.get("domain") or row["type"]),
                "matched_terms": matched_terms,
                "aliases": alias_values,
                "colloquial_matches": [
                    example for example in examples if _lexicon_match_reason(query_text, title=example, aliases=set(), paths=set(), symbols=set()) != "catalog"
                ],
                "target_nodes": [node_id],
                "related_concepts": [],
                "disambiguation_hint": str(attrs.get("disambiguation_hint") or ""),
                "confidence": str(row["confidence"]),
                "evidence_ids": evidence_ids,
            }
        )
    return sorted(
        candidates,
        key=lambda item: (0 if item["matched_terms"] or item["colloquial_matches"] else 1, item["label"]),
    )
```

Add:

```python
def _evidence_for_paths(paths: set[str], alias_records: list[dict[str, str]]) -> set[str]:
    return {record["evidence_id"] for record in alias_records if record.get("evidence_id")}
```

This helper deliberately does not treat `query_examples` as standalone evidence.

- [ ] **Step 5: Return concept candidates and update contract text**

In `project_cognition_lexicon`, compute rows once:

```python
    with closing(connect_cognition_db(project_root)) as conn:
        rows = _node_rows(conn, generation_id, limit=limit)
        aliases = _aliases_by_node(conn, generation_id)
        alias_records = _alias_records_by_node(conn, generation_id)
        paths = _paths_by_node(conn, generation_id)
        symbols = _symbols_by_node(conn, generation_id)
        query_examples = _query_examples_by_node(conn, generation_id)
        terms = _lexicon_terms_from_rows(
            rows,
            query_text=query_text,
            aliases=aliases,
            paths=paths,
            symbols=symbols,
        )
        concept_candidates = _concept_candidates(
            rows,
            query_text=query_text,
            aliases=aliases,
            alias_records=alias_records,
            paths=paths,
            symbols=symbols,
            query_examples=query_examples,
        )
```

Replace the return payload to include:

```python
        "concept_candidates": concept_candidates,
```

Update `_query_planning_contract`:

```python
def _query_planning_contract() -> dict[str, str]:
    return {
        "agent_responsibility": "select and reject concepts before querying",
        "runtime_responsibility": "execute graph queries from agent-provided concept selections, expanded queries, and path hints",
    }
```

Rename existing `_lexicon_terms` to `_lexicon_terms_from_rows` and pass rows/helpers rather than re-querying.

- [ ] **Step 6: Run lexicon tests**

Run:

```powershell
pytest tests/test_project_cognition_query.py::test_lexicon_returns_concept_candidates_for_project_terms tests/test_project_cognition_query.py::test_lexicon_returns_map_terms_for_agent_query_planning tests/test_project_cognition_query.py::test_lexicon_default_returns_complete_keyword_mapping -q
```

Expected: all pass. If old tests assert the old `agent_responsibility`, update them to the new string.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/cognition/lexicon.py tests/test_project_cognition_query.py
git commit -m "feat: project concept lexicon candidates"
```

---

### Task 4: Add Route Pack Generation to Project Cognition Query

**Files:**
- Modify: `src/specify_cli/cognition/query.py`
- Test: `tests/test_project_cognition_query.py`

- [ ] **Step 1: Add route pack test**

Add this test to `tests/test_project_cognition_query.py`:

```python
def test_query_returns_route_pack_for_selected_concept(tmp_path: Path) -> None:
    _seed_agent_teams_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="add provider support to agent teams",
        selected_concepts=["capability:codex-team-runtime"],
        expanded_queries=["team runtime provider"],
        paths=[],
    )

    assert result["readiness"] == "ready"
    route_pack = result["route_pack"]
    assert route_pack["owner_files"] == [
        {
            "path": "src/specify_cli/codex_team/runtime.py",
            "node_id": "capability:codex-team-runtime",
            "claim_id": "",
            "relation": "owner",
            "reason": "Path is indexed as owns for Agent teams runtime.",
            "evidence_ids": ["E-team-runtime"],
            "confidence": "strong",
        }
    ]
    assert route_pack["minimal_live_reads"] == ["src/specify_cli/codex_team/runtime.py"]
    assert route_pack["why_these_reads"] == [
        "src/specify_cli/codex_team/runtime.py: Path is indexed as owns for Agent teams runtime."
    ]
```

- [ ] **Step 2: Add route pack shape to no-baseline response test**

Add this assertion to `test_apply_cognition_update_without_active_generation_includes_empty_update_id` only if query tests already cover no generation. If no query no-generation test exists, add:

```python
def test_query_without_active_generation_returns_empty_route_pack(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    result = query_project_cognition(tmp_path, intent="implement", query_text="anything")

    assert result["readiness"] == "needs_rebuild"
    assert result["route_pack"] == {
        "entry_files": [],
        "owner_files": [],
        "consumer_files": [],
        "state_surfaces": [],
        "workflow_surfaces": [],
        "tests": [],
        "docs": [],
        "minimal_live_reads": [],
        "why_these_reads": [],
    }
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_query.py::test_query_returns_route_pack_for_selected_concept tests/test_project_cognition_query.py::test_query_without_active_generation_returns_empty_route_pack -q
```

Expected: failures because `route_pack` is missing.

- [ ] **Step 4: Add route pack helpers**

In `src/specify_cli/cognition/query.py`, add:

```python
EMPTY_ROUTE_PACK: dict[str, list[Any]] = {
    "entry_files": [],
    "owner_files": [],
    "consumer_files": [],
    "state_surfaces": [],
    "workflow_surfaces": [],
    "tests": [],
    "docs": [],
    "minimal_live_reads": [],
    "why_these_reads": [],
}
```

Add helpers:

```python
def _empty_route_pack() -> dict[str, list[Any]]:
    return {key: list(value) for key, value in EMPTY_ROUTE_PACK.items()}


def _route_relation_bucket(relation: str) -> str:
    normalized = relation.strip().lower()
    if normalized in {"entry", "entrypoint", "command", "api"}:
        return "entry_files"
    if normalized in {"consumer", "calls", "uses", "generates"}:
        return "consumer_files"
    if normalized in {"state", "status", "queue", "cache", "database"}:
        return "state_surfaces"
    if normalized in {"workflow", "template", "skill", "prompt"}:
        return "workflow_surfaces"
    if normalized in {"test", "verifies", "verification"}:
        return "tests"
    if normalized in {"doc", "docs", "documentation"}:
        return "docs"
    return "owner_files"


def _route_pack_for_nodes(conn: Any, generation_id: str, node_ids: list[str]) -> dict[str, list[Any]]:
    route_pack = _empty_route_pack()
    if not node_ids:
        return route_pack
    bind_marks = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"SELECT path, node_id, relation, confidence, evidence_id FROM path_index "
        f"WHERE generation_id = ? AND node_id IN ({bind_marks}) ORDER BY path",
        (generation_id, *node_ids),
    ).fetchall()
    seen_reads: set[str] = set()
    for row in rows:
        node_id = str(row["node_id"])
        title = _node_title(conn, generation_id, node_id)
        relation = _route_item_relation(str(row["relation"]))
        reason = f"Path is indexed as {row['relation']} for {title}."
        item = {
            "path": str(row["path"]),
            "node_id": node_id,
            "claim_id": "",
            "relation": relation,
            "reason": reason,
            "evidence_ids": [str(row["evidence_id"])],
            "confidence": str(row["confidence"]),
        }
        route_pack[_route_relation_bucket(relation)].append(item)
        if str(row["path"]) not in seen_reads:
            seen_reads.add(str(row["path"]))
            route_pack["minimal_live_reads"].append(str(row["path"]))
            route_pack["why_these_reads"].append(f"{row['path']}: {reason}")
    return route_pack


def _route_item_relation(relation: str) -> str:
    normalized = relation.strip().lower()
    if normalized in {"owns", "implements"}:
        return "owner"
    return normalized or "owner"
```

- [ ] **Step 5: Return route pack from query**

In every no-active-generation response, include:

```python
            "route_pack": _empty_route_pack(),
```

Before the main return payload in `query_project_cognition`, compute:

```python
        route_pack = _route_pack_for_nodes(conn, generation_id, affected_nodes)
        if query_missed_runtime_index:
            route_pack["minimal_live_reads"] = list(minimal_live_reads)
            route_pack["why_these_reads"] = [
                f"{path}: fallback read because query did not match project cognition aliases or claims"
                for path in minimal_live_reads
            ]
```

Then return:

```python
            "route_pack": route_pack,
```

Keep top-level `minimal_live_reads` for compatibility by setting it from `route_pack["minimal_live_reads"]` after fallback handling:

```python
        minimal_live_reads = list(route_pack["minimal_live_reads"])
```

- [ ] **Step 6: Run route pack tests**

Run:

```powershell
pytest tests/test_project_cognition_query.py::test_query_returns_route_pack_for_selected_concept tests/test_project_cognition_query.py::test_query_without_active_generation_returns_empty_route_pack tests/test_project_cognition_query.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/cognition/query.py tests/test_project_cognition_query.py
git commit -m "feat: return project cognition route packs"
```

---

### Task 5: Record Patch-in-Active-Generation Update Metadata

**Files:**
- Modify: `src/specify_cli/cognition/update.py`
- Test: `tests/test_project_cognition_db.py`

- [ ] **Step 1: Add update metadata test**

Add this test to `tests/test_project_cognition_db.py`:

```python
def test_apply_cognition_update_records_patch_in_active_generation_metadata(tmp_path: Path) -> None:
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

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/login.ts"], reason="unit-test")

    assert result["readiness"] == "ready"
    assert get_active_generation_id(tmp_path) == generation_id
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute("SELECT attrs_json FROM updates WHERE id = ?", (result["update_id"],)).fetchone()
    attrs = json.loads(row["attrs_json"])
    assert attrs["publishing_model"] == "patch-in-active-generation"
    assert attrs["patched_retrieval_signals"] == ["path_index"]
    assert attrs["invalidated_retrieval_signals"] == []
    assert attrs["affected_route_records"] == ["src/auth/login.ts"]
    assert attrs["confidence"] == "strong"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_db.py::test_apply_cognition_update_records_patch_in_active_generation_metadata -q
```

Expected: failure because update metadata does not include these fields.

- [ ] **Step 3: Extend update attrs**

In `src/specify_cli/cognition/update.py`, replace `attrs = { ... }` with:

```python
        attrs = {
            "publishing_model": "patch-in-active-generation",
            "patched_retrieval_signals": ["path_index"] if affected_nodes else [],
            "invalidated_retrieval_signals": [],
            "affected_route_records": sorted(path for path in normalized_paths if path not in missing_paths),
            "known_unknowns": missing_coverage,
            "minimal_live_reads": missing_paths,
            "confidence": "partial" if missing_paths else "strong",
        }
```

Keep existing result payload keys unchanged.

- [ ] **Step 4: Run update tests**

Run:

```powershell
pytest tests/test_project_cognition_db.py::test_apply_cognition_update_records_patch_in_active_generation_metadata tests/test_project_cognition_db.py::test_apply_cognition_update_records_partial_refresh_when_path_missing tests/test_project_cognition_db.py::test_apply_cognition_update_records_affected_path_update -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add src/specify_cli/cognition/update.py tests/test_project_cognition_db.py
git commit -m "feat: record cognition update retrieval metadata"
```

---

### Task 6: Validate Concept Lexicon Contract and Route Ingredients

**Files:**
- Modify: `src/specify_cli/cognition/validation.py`
- Test: `tests/test_project_cognition_validation.py`

- [ ] **Step 1: Add validation test for missing route evidence**

Add this test to `tests/test_project_cognition_validation.py`:

```python
def test_validate_build_blocks_when_route_rows_have_empty_evidence(tmp_path: Path) -> None:
    generation_id = _seed_query_ready_runtime(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute("UPDATE path_index SET evidence_id = '' WHERE generation_id = ?", (generation_id,))
        conn.commit()

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("route-pack source rows" in message for message in result["errors"])
```

- [ ] **Step 2: Add validation test for query examples without target evidence**

Add:

```python
def test_validate_build_blocks_query_example_without_backed_target(tmp_path: Path) -> None:
    _seed_query_ready_runtime(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO query_examples(id, generation_id, query_text, intent, expected_target_type, expected_target_id, language, source, created_at) "
            "VALUES ('Q-missing', 'GEN-0001', 'missing target wording', 'implement', 'capability', 'capability:missing', 'en', 'test', '2026-05-17T00:00:00Z')"
        )
        conn.commit()

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("query_examples" in message and "evidence-backed target" in message for message in result["errors"])
```

- [ ] **Step 3: Run validation tests and verify failure**

Run:

```powershell
pytest tests/test_project_cognition_validation.py::test_validate_build_blocks_when_route_rows_have_empty_evidence tests/test_project_cognition_validation.py::test_validate_build_blocks_query_example_without_backed_target -q
```

Expected: failures because validation does not check these conditions.

- [ ] **Step 4: Add route source validation**

In `src/specify_cli/cognition/validation.py`, add a call inside `validate_build_acceptance` after `_validate_no_specify_graph_store_paths`:

```python
                _validate_route_pack_source_rows(conn, active_generation_id, errors, details)
                _validate_query_examples_targets(conn, active_generation_id, errors, details)
```

Add helpers:

```python
def _validate_route_pack_source_rows(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    rows = conn.execute(
        "SELECT id, path, node_id, relation, confidence, evidence_id FROM path_index "
        "WHERE generation_id = ? ORDER BY id",
        (generation_id,),
    ).fetchall()
    invalid: list[str] = []
    for row in rows:
        missing = [
            field
            for field in ("path", "node_id", "relation", "confidence", "evidence_id")
            if not str(row[field]).strip()
        ]
        if missing:
            invalid.append(f"{row['id']} missing {', '.join(missing)}")
    details["route_pack_source_row_count"] = len(rows)
    details["invalid_route_pack_source_rows"] = invalid
    if invalid:
        errors.append("route-pack source rows must have path, node_id, relation, confidence, and evidence_id: " + "; ".join(invalid[:5]))
```

Add:

```python
def _validate_query_examples_targets(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    rows = conn.execute(
        "SELECT id, expected_target_id FROM query_examples WHERE generation_id = ? ORDER BY id",
        (generation_id,),
    ).fetchall()
    invalid: list[str] = []
    for row in rows:
        target_id = str(row["expected_target_id"])
        evidence_count = conn.execute(
            "SELECT COUNT(*) AS count FROM alias_index WHERE generation_id = ? AND target_id = ? AND evidence_id != ''",
            (generation_id, target_id),
        ).fetchone()["count"]
        path_count = conn.execute(
            "SELECT COUNT(*) AS count FROM path_index WHERE generation_id = ? AND node_id = ? AND evidence_id != ''",
            (generation_id, target_id),
        ).fetchone()["count"]
        claim_count = conn.execute(
            "SELECT COUNT(*) AS count FROM claims "
            "JOIN claim_evidence ON claim_evidence.claim_id = claims.id "
            "WHERE claims.generation_id = ? AND claims.subject_ref = ?",
            (generation_id, target_id),
        ).fetchone()["count"]
        if int(evidence_count) + int(path_count) + int(claim_count) == 0:
            invalid.append(f"{row['id']} targets {target_id}")
    details["query_examples_count"] = len(rows)
    details["invalid_query_examples"] = invalid
    if invalid:
        errors.append("query_examples must annotate an evidence-backed target: " + "; ".join(invalid[:5]))
```

This keeps validation read-only and preserves `test_validation_module_does_not_import_normal_query_helper`.

- [ ] **Step 5: Run validation tests**

Run:

```powershell
pytest tests/test_project_cognition_validation.py::test_validate_build_blocks_when_route_rows_have_empty_evidence tests/test_project_cognition_validation.py::test_validate_build_blocks_query_example_without_backed_target tests/test_project_cognition_validation.py::test_validation_module_does_not_import_normal_query_helper tests/test_project_cognition_validation.py::test_validate_build_accepts_query_ready_runtime -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/cognition/validation.py tests/test_project_cognition_validation.py
git commit -m "feat: validate concept lexicon build readiness"
```

---

### Task 7: Update Shared Consumer Gate and Map Workflow Templates

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/map-update.md`
- Modify: `templates/commands/analyze.md`
- Test: `tests/test_runtime_handbook_contract.py`
- Test: `tests/test_project_map_hard_gate_guidance.py`
- Test: `tests/test_map_scan_build_template_guidance.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add shared gate tests**

In `tests/test_runtime_handbook_contract.py`, extend `test_context_loading_gradient_uses_cognition_runtime_gate`:

```python
    assert "concept_candidates" in content
    assert "selected_concepts" in content
    assert "rejected_concepts" in content
    assert "route_pack" in content
    assert "select and reject concepts" in lowered
```

Extend `test_context_loading_gradient_requires_cognition_carry_forward`:

```python
    assert "selected concepts" in content
    assert "rejected concepts" in content
    assert "route pack" in content
```

Extend `test_project_cognition_passive_skill_mirrors_query_completion_contract`:

```python
    assert "concept_candidates" in content
    assert "selected_concepts" in content
    assert "rejected_concepts" in content
    assert "route_pack" in content
```

- [ ] **Step 2: Add map workflow template tests**

In `tests/test_map_scan_build_template_guidance.py`, add:

```python
def test_map_scan_build_update_templates_define_concept_lexicon_duties() -> None:
    scan = _read("templates/commands/map-scan.md").lower()
    build = _read("templates/commands/map-build.md").lower()
    update = _read("templates/commands/map-update.md").lower()

    assert "concept retrieval signals" in scan
    assert "colloquial user phrases" in scan
    assert "domain ownership evidence" in scan
    assert "query_examples" in build
    assert "concept_candidates" in build
    assert "route_pack" in build
    assert "patch-in-active-generation" in update
    assert "stale retrieval signals" in update
    assert "selected_concepts" in update
```

In `tests/test_project_map_hard_gate_guidance.py`, extend `test_ordinary_sp_workflows_use_shared_project_cognition_gate`:

```python
    assert "concept_candidates" in shared_gate
    assert "selected_concepts" in shared_gate
    assert "rejected_concepts" in shared_gate
    assert "route_pack" in shared_gate
```

- [ ] **Step 3: Run template tests and verify failure**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py::test_context_loading_gradient_uses_cognition_runtime_gate tests/test_runtime_handbook_contract.py::test_project_cognition_passive_skill_mirrors_query_completion_contract tests/test_map_scan_build_template_guidance.py::test_map_scan_build_update_templates_define_concept_lexicon_duties tests/test_project_map_hard_gate_guidance.py::test_ordinary_sp_workflows_use_shared_project_cognition_gate -q
```

Expected: failures because templates do not mention concept selection or route packs.

- [ ] **Step 4: Update shared gate partial**

In `templates/command-partials/common/context-loading-gradient.md`, replace the "Required Project Cognition Query" paragraph with:

```markdown
Use the launcher-backed project cognition query planning flow required by this
command's workflow contract to retrieve the task-local project cognition bundle:
run `project-cognition lexicon`, review returned `concept_candidates`, select
and reject concepts with a short `selection_reason`, build a `query_plan` with
`selected_concepts`, `rejected_concepts`, `expanded_queries`, and known `paths`,
then run `project-cognition query --query-plan`. Treat raw graph JSON artifacts
as obsolete runtime surfaces.
```

In "Query Completion", replace the extraction sentence with:

```markdown
Extract and carry forward selected concepts, rejected concepts, matched
capability or symptom, affected nodes and subgraph, `route_pack`,
`minimal_live_reads`, missing coverage, evidence traces, verification routes,
ambiguity, conflicts, and weak coverage.
```

Add after "Query Completion":

```markdown
### Concept Selection

- `concept_candidates` are project-specific semantic entries, not a flat keyword
  list.
- Select concepts that match the user's intent and reject plausible wrong-domain
  concepts before querying.
- If a concept is both selected and rejected, or if the selected concept is not
  present in the active generation, follow returned readiness instead of
  continuing as ready.
- Do not broaden source reads beyond `route_pack` and `minimal_live_reads`
  unless the returned readiness explicitly requires review or update.
```

- [ ] **Step 5: Update passive skill mirror**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, update the query flow wording to include:

```markdown
Run `project-cognition lexicon` first, review `concept_candidates`, select and
reject concepts with reasons, then run `project-cognition query --query-plan`
with `selected_concepts`, `rejected_concepts`, expanded queries, and known paths.
```

Update its carry-forward wording to include `route_pack`, selected concepts, and rejected concepts.

- [ ] **Step 6: Update navigation shim**

In `templates/command-partials/common/navigation-check.md`, add one sentence:

```markdown
- Preserve concept selection (`concept_candidates`, `selected_concepts`,
  `rejected_concepts`) and `route_pack` as part of the shared gate result.
```

- [ ] **Step 7: Update map workflow templates**

In `templates/commands/map-scan.md`, add a section after "Layer 1 Route Material":

```markdown
## Concept Retrieval Signal Evidence

`sp-map-scan` must collect concept retrieval signals as evidence, not final
truth: feature names, module names, workflow names, command names, colloquial
user phrases, technical aliases, symbol names, state values, error messages,
test names, domain ownership evidence, and disambiguation evidence for
overloaded terms.
```

In `templates/commands/map-build.md`, add to "Build Duties":

```markdown
- publish `concept_candidates` as a lexicon projection over graph truth and
  indexes, not as a second concept graph
- populate `query_examples`, `alias_fts`, and `claim_fts` from evidence-backed
  scan inputs
- ensure route-pack source rows have path, node or claim backing, relation,
  reason, evidence IDs, and confidence
```

In `templates/commands/map-update.md`, add to "Update Duties":

```markdown
- maintain concept retrieval signals through the patch-in-active-generation
  model
- update or invalidate stale aliases, query examples, FTS rows, and route claims
- preserve selected_concepts and rejected_concepts from user-supplied
  corrections when they explain affected scope
```

In `templates/commands/analyze.md`, add near the project cognition query guidance:

```markdown
- Carry selected/rejected concepts and `route_pack` into the blocker bundle so
  remediation does not reinterpret the user's scope from chat history.
```

- [ ] **Step 8: Run template tests**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_project_map_hard_gate_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: all pass. If failures identify generated integration snapshots, update only the matching expected strings.

- [ ] **Step 9: Commit**

```powershell
git add templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/navigation-check.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/commands/map-scan.md templates/commands/map-build.md templates/commands/map-update.md templates/commands/analyze.md tests/test_runtime_handbook_contract.py tests/test_project_map_hard_gate_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py
git commit -m "docs: route workflows through concept lexicon gate"
```

---

### Task 8: Integration Verification and Compatibility Sweep

**Files:**
- Modify if failing: `tests/integrations/test_integration_base_markdown.py`
- Modify if failing: `tests/integrations/test_integration_base_toml.py`
- Modify if failing: `tests/integrations/test_integration_codex.py`
- Modify if failing: `tests/test_extension_skills.py`
- Modify if failing: `README.md`
- Modify if failing: `PROJECT-HANDBOOK.md`

- [ ] **Step 1: Run project cognition runtime tests**

Run:

```powershell
pytest tests/test_project_cognition_query.py tests/test_project_cognition_db.py tests/test_project_cognition_validation.py -q
```

Expected: all pass.

- [ ] **Step 2: Run CLI integration tests for project cognition query**

Run:

```powershell
pytest tests/integrations/test_cli.py -k "project_cognition_query or project_cognition_lexicon" -q
```

Expected: all pass.

- [ ] **Step 3: Run generated integration template tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/test_extension_skills.py -q
```

Expected: all pass. If generated command content tests fail because they assert old query wording, update assertions to look for `concept_candidates`, `selected_concepts`, `rejected_concepts`, `route_pack`, and `minimal_live_reads`.

Use this assertion shape when updating generated command tests:

```python
assert "concept_candidates" in content
assert "selected_concepts" in content
assert "rejected_concepts" in content
assert "route_pack" in content
assert "minimal_live_reads" in content
```

- [ ] **Step 4: Run documentation guidance tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py tests/test_project_handbook_templates.py -q
```

Expected: all pass. If README or handbook tests fail because public docs omit concept lexicon contract v2, add one concise paragraph to the relevant docs:

```markdown
Project cognition query planning now uses a concept lexicon: workflows call
`project-cognition lexicon`, select and reject `concept_candidates`, then call
`project-cognition query --query-plan` to receive a route pack and
`minimal_live_reads`.
```

- [ ] **Step 5: Run broad targeted suite**

Run:

```powershell
pytest tests/test_project_cognition_query.py tests/test_project_cognition_db.py tests/test_project_cognition_validation.py tests/test_runtime_handbook_contract.py tests/test_project_map_hard_gate_guidance.py tests/test_map_scan_build_template_guidance.py tests/integrations/test_cli.py -q
```

Expected: all pass.

- [ ] **Step 6: Inspect staged changes**

Run:

```powershell
git status --short
git diff --check
```

Expected: `git diff --check` has no output. `git status --short` shows only files intentionally modified by this plan plus any pre-existing unrelated worktree changes.

- [ ] **Step 7: Commit compatibility updates**

If Step 3 or Step 4 required assertion or doc updates, commit them:

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/test_extension_skills.py README.md PROJECT-HANDBOOK.md
git commit -m "test: align generated cognition gate expectations"
```

If no files changed in this task, do not create an empty commit.

---

## Final Verification

- [ ] **Step 1: Run final focused suite**

Run:

```powershell
pytest tests/test_project_cognition_query.py tests/test_project_cognition_db.py tests/test_project_cognition_validation.py tests/test_runtime_handbook_contract.py tests/test_project_map_hard_gate_guidance.py tests/test_map_scan_build_template_guidance.py tests/integrations/test_cli.py -q
```

Expected: all pass.

- [ ] **Step 2: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 3: Review final diff**

Run:

```powershell
git diff --stat HEAD
git diff HEAD -- src/specify_cli/cognition src/specify_cli/__init__.py templates/command-partials/common templates/passive-skills/spec-kit-project-cognition-gate templates/commands/map-scan.md templates/commands/map-build.md templates/commands/map-update.md templates/commands/analyze.md tests/test_project_cognition_query.py tests/test_project_cognition_db.py tests/test_project_cognition_validation.py tests/integrations/test_cli.py
```

Expected: diff matches this plan, with no unrelated file rewrites.

## Self-Review Notes

- Spec coverage: Tasks 1-6 implement runtime contract v2, concept candidates, selected/rejected concepts, route packs, update metadata, query example evidence handling, and validation. Task 7 implements scan/build/update and `sp-*` consumer templates. Task 8 covers generated integration and public docs.
- Type consistency: The plan uses `concept_candidates`, `selected_concepts`, `rejected_concepts`, `selection_reason`, and `route_pack` consistently across lexicon, query, CLI, validation, and templates.
- Compatibility: Existing `terms`, `available_terms`, `capability_candidates`, `symptom_candidates`, `minimal_live_reads`, and `subgraph` stay in the API for existing consumers.
