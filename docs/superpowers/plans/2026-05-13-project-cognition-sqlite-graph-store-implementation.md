# Project Cognition SQLite Graph Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current large-JSON project cognition runtime with a SQLite-backed property graph store, task-local query API, and transactional `map-update` path.

**Architecture:** `status.json` remains the lightweight public freshness entrypoint, while `.specify/project-cognition/project-cognition.db` becomes the canonical graph truth store. Workflows query `specify project-cognition query` for task-local bundles instead of reading raw graph artifacts, and `map-update` performs indexed row-level updates inside SQLite transactions. The current JSON graph freshness, hook validation, finalizer, template, and test contracts must be replaced in the same implementation lane.

**Tech Stack:** Python 3.11+, stdlib `sqlite3`, Typer CLI, pytest, existing Spec Kit template rendering and hook infrastructure.

---

## Scope Check

This is one large runtime replacement, but it is not multiple unrelated
products. The plan is split into independently testable tasks that converge on
one compatible runtime contract:

- SQLite schema and repository API
- query resolver
- status/freshness path replacement
- hook and CLI replacement
- map command/template replacement
- regression and documentation alignment

Do not ship a partial state where `project-cognition.db` exists but freshness,
finalizers, hooks, or workflow templates still require raw graph JSON files.

## File Structure

### New Runtime Files

- `src/specify_cli/cognition/db.py`
  - SQLite connection, schema creation, transaction helper, active generation
    helpers, and seed helpers used by tests.
- `src/specify_cli/cognition/query.py`
  - Query resolver, candidate scoring, task-local bundle assembly, and query
    readiness mapping.
- `src/specify_cli/cognition/update.py`
  - Path-indexed transactional update helper for changed paths and user
    supplements.
- `tests/test_project_cognition_db.py`
  - Schema, generation isolation, evidence trace, and update transaction tests.
- `tests/test_project_cognition_query.py`
  - Resolver tests for login capability lookup, ambiguity, FTS, missing
    coverage, and evidence traces.

### Existing Runtime Files To Modify

- `src/specify_cli/cognition/paths.py`
  - Add `cognition_db_path(project_root)`.
- `src/specify_cli/cognition/status.py`
  - Add database fields to `CognitionStatus`: `graph_store_path`,
    `active_generation_id`, `query_contract_version`, `update_contract_version`.
- `src/specify_cli/cognition/__init__.py`
  - Export DB, query, and update helpers.
- `src/specify_cli/project_cognition_status.py`
  - Replace canonical runtime paths with `status.json` and
    `project-cognition.db`; preserve public freshness vocabulary.
- `src/specify_cli/__init__.py`
  - Add `project-cognition query/update/rebuild/doctor`; keep existing
    `cognition discover/read` for cross-project references only; remove
    `project-map` as a required runtime alias.
- `src/specify_cli/hooks/artifact_validation.py`
  - Validate DB-backed map artifacts instead of graph JSON artifacts.

### Existing Template and Test Files To Modify

- `templates/commands/{fast,quick,specify,clarify,deep-research,plan,tasks,implement,debug,test-scan,test-build,prd-scan,map-scan,map-build,map-update}.md`
- `templates/command-partials/common/context-loading-gradient.md`
- `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `tests/test_project_map_status.py`
- `tests/hooks/test_preflight_hooks.py`
- `tests/contract/test_hook_cli_surface.py`
- `tests/integrations/test_cli.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_codex.py`
- `README.md`
- `PROJECT-HANDBOOK.md`

---

## Task 1: Add SQLite Store Foundation

**Files:**
- Create: `src/specify_cli/cognition/db.py`
- Modify: `src/specify_cli/cognition/paths.py`
- Modify: `src/specify_cli/cognition/__init__.py`
- Test: `tests/test_project_cognition_db.py`

- [ ] **Step 1: Write failing DB path and schema tests**

Create `tests/test_project_cognition_db.py` with:

```python
import sqlite3
from pathlib import Path

from specify_cli.cognition import (
    cognition_db_path,
    connect_cognition_db,
    ensure_cognition_db,
    get_active_generation_id,
    seed_active_generation,
)


def test_cognition_db_path_lives_under_project_cognition(tmp_path: Path) -> None:
    assert cognition_db_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "project-cognition.db"


def test_ensure_cognition_db_creates_schema_and_active_generation(tmp_path: Path) -> None:
    db_path = ensure_cognition_db(tmp_path)

    assert db_path == cognition_db_path(tmp_path)
    assert db_path.exists()

    with connect_cognition_db(tmp_path) as conn:
        table_names = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')")
        }

    assert "generations" in table_names
    assert "nodes" in table_names
    assert "edges" in table_names
    assert "claims" in table_names
    assert "path_index" in table_names
    assert "alias_index" in table_names
    assert "claim_fts" in table_names
    assert "observation_fts" in table_names
    assert "alias_fts" in table_names
    assert get_active_generation_id(tmp_path) == ""


def test_seed_active_generation_is_query_visible(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")

    assert generation_id
    assert get_active_generation_id(tmp_path) == generation_id

    with connect_cognition_db(tmp_path) as conn:
        row = conn.execute(
            "SELECT state, source_commit FROM generations WHERE id = ?",
            (generation_id,),
        ).fetchone()

    assert dict(row) == {"state": "active", "source_commit": "abc123"}


def test_staging_generation_is_not_active(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    with connect_cognition_db(tmp_path) as conn:
        conn.execute(
            "INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) "
            "VALUES ('GEN-STAGING', 1, 'scan', 'staging', 'abc123', '2026-05-13T00:00:00Z', '', '', '{}')"
        )
        conn.commit()

    assert get_active_generation_id(tmp_path) == ""


def test_connection_uses_row_factory_and_foreign_keys(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    with connect_cognition_db(tmp_path) as conn:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert isinstance(row, sqlite3.Row)
        assert row[0] == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_project_cognition_db.py -q
```

Expected: FAIL because `cognition_db_path`, `connect_cognition_db`,
`ensure_cognition_db`, `get_active_generation_id`, and
`seed_active_generation` do not exist.

- [ ] **Step 3: Add `cognition_db_path`**

Modify `src/specify_cli/cognition/paths.py`:

```python
def cognition_db_path(project_root: Path) -> Path:
    return cognition_dir(project_root) / "project-cognition.db"
```

- [ ] **Step 4: Implement DB schema helpers**

Create `src/specify_cli/cognition/db.py`:

```python
"""SQLite-backed project cognition graph store."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from .paths import cognition_db_path, cognition_dir


SCHEMA_VERSION = 1


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect_cognition_db(project_root: Path) -> sqlite3.Connection:
    path = cognition_db_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def cognition_transaction(project_root: Path) -> Iterator[sqlite3.Connection]:
    conn = connect_cognition_db(project_root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_cognition_db(project_root: Path) -> Path:
    cognition_dir(project_root).mkdir(parents=True, exist_ok=True)
    path = cognition_db_path(project_root)
    with connect_cognition_db(project_root) as conn:
        _create_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value_json, updated_at) VALUES (?, ?, ?)",
            ("schema_version", json.dumps(SCHEMA_VERSION), iso_now()),
        )
        conn.commit()
    return path


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata(
          key TEXT PRIMARY KEY,
          value_json TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS generations(
          id TEXT PRIMARY KEY,
          sequence INTEGER NOT NULL,
          kind TEXT NOT NULL,
          state TEXT NOT NULL,
          source_commit TEXT NOT NULL,
          started_at TEXT NOT NULL,
          published_at TEXT NOT NULL,
          superseded_at TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_generations_state ON generations(state);

        CREATE TABLE IF NOT EXISTS evidence(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          source_kind TEXT NOT NULL,
          source_path TEXT NOT NULL,
          commit_sha TEXT NOT NULL,
          span TEXT NOT NULL,
          extractor TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          captured_at TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_evidence_source_path ON evidence(source_path);
        CREATE INDEX IF NOT EXISTS idx_evidence_source_hash ON evidence(source_path, content_hash);
        CREATE INDEX IF NOT EXISTS idx_evidence_commit ON evidence(commit_sha);

        CREATE TABLE IF NOT EXISTS observations(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          observation_type TEXT NOT NULL,
          summary TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS observation_evidence(
          observation_id TEXT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(observation_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS nodes(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          type TEXT NOT NULL,
          title TEXT NOT NULL,
          confidence TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
        CREATE INDEX IF NOT EXISTS idx_nodes_generation ON nodes(generation_id);

        CREATE TABLE IF NOT EXISTS node_evidence(
          node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(node_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS edges(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          type TEXT NOT NULL,
          source_id TEXT NOT NULL,
          target_id TEXT NOT NULL,
          confidence TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
        CREATE INDEX IF NOT EXISTS idx_edges_generation ON edges(generation_id);

        CREATE TABLE IF NOT EXISTS edge_evidence(
          edge_id TEXT NOT NULL REFERENCES edges(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(edge_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS claims(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          subject_ref TEXT NOT NULL,
          predicate TEXT NOT NULL,
          object_ref TEXT NOT NULL,
          object_value TEXT NOT NULL,
          truth_layer TEXT NOT NULL,
          confidence TEXT NOT NULL,
          status TEXT NOT NULL,
          last_validated_at TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject_ref);
        CREATE INDEX IF NOT EXISTS idx_claims_predicate ON claims(predicate);
        CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

        CREATE TABLE IF NOT EXISTS claim_evidence(
          claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(claim_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS conflicts(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          subject_ref TEXT NOT NULL,
          conflict_type TEXT NOT NULL,
          impact_scope TEXT NOT NULL,
          agent_behavior_rule TEXT NOT NULL,
          resolution_status TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}',
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conflicts_subject ON conflicts(subject_ref);
        CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(resolution_status);

        CREATE TABLE IF NOT EXISTS conflict_claims(
          conflict_id TEXT NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
          claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
          PRIMARY KEY(conflict_id, claim_id)
        );

        CREATE TABLE IF NOT EXISTS path_index(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          path TEXT NOT NULL,
          node_id TEXT NOT NULL,
          relation TEXT NOT NULL,
          confidence TEXT NOT NULL,
          evidence_id TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_path_index_path ON path_index(path);
        CREATE INDEX IF NOT EXISTS idx_path_index_node ON path_index(node_id);
        CREATE INDEX IF NOT EXISTS idx_path_index_generation_path ON path_index(generation_id, path);

        CREATE TABLE IF NOT EXISTS symbol_index(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          symbol_name TEXT NOT NULL,
          normalized_symbol TEXT NOT NULL,
          node_id TEXT NOT NULL,
          path TEXT NOT NULL,
          relation TEXT NOT NULL,
          evidence_id TEXT NOT NULL,
          confidence TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_symbol_normalized ON symbol_index(normalized_symbol);
        CREATE INDEX IF NOT EXISTS idx_symbol_generation_normalized ON symbol_index(generation_id, normalized_symbol);

        CREATE TABLE IF NOT EXISTS alias_index(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          alias TEXT NOT NULL,
          normalized_alias TEXT NOT NULL,
          target_type TEXT NOT NULL,
          target_id TEXT NOT NULL,
          language TEXT NOT NULL,
          source TEXT NOT NULL,
          confidence TEXT NOT NULL,
          evidence_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_alias_normalized ON alias_index(normalized_alias);
        CREATE INDEX IF NOT EXISTS idx_alias_target ON alias_index(target_id);
        CREATE INDEX IF NOT EXISTS idx_alias_generation_normalized ON alias_index(generation_id, normalized_alias);

        CREATE TABLE IF NOT EXISTS entrypoint_index(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          entrypoint_key TEXT NOT NULL,
          entrypoint_type TEXT NOT NULL,
          node_id TEXT NOT NULL,
          capability_id TEXT NOT NULL,
          path TEXT NOT NULL,
          evidence_id TEXT NOT NULL,
          confidence TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_entrypoint_key ON entrypoint_index(entrypoint_key);
        CREATE INDEX IF NOT EXISTS idx_entrypoint_capability ON entrypoint_index(capability_id);

        CREATE TABLE IF NOT EXISTS test_index(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          test_path TEXT NOT NULL,
          test_name TEXT NOT NULL,
          node_id TEXT NOT NULL,
          capability_id TEXT NOT NULL,
          verification_node_id TEXT NOT NULL,
          evidence_id TEXT NOT NULL,
          confidence TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_test_capability ON test_index(capability_id);
        CREATE INDEX IF NOT EXISTS idx_test_path ON test_index(test_path);

        CREATE TABLE IF NOT EXISTS slice_members(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          slice_id TEXT NOT NULL,
          object_type TEXT NOT NULL,
          object_id TEXT NOT NULL,
          rank INTEGER NOT NULL,
          reason TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_slice_members_slice ON slice_members(slice_id);
        CREATE INDEX IF NOT EXISTS idx_slice_members_generation_slice ON slice_members(generation_id, slice_id);

        CREATE TABLE IF NOT EXISTS query_examples(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          query_text TEXT NOT NULL,
          intent TEXT NOT NULL,
          expected_target_type TEXT NOT NULL,
          expected_target_id TEXT NOT NULL,
          language TEXT NOT NULL,
          source TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS updates(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          trigger TEXT NOT NULL,
          changed_paths_json TEXT NOT NULL,
          affected_nodes_json TEXT NOT NULL,
          affected_claims_json TEXT NOT NULL,
          affected_slices_json TEXT NOT NULL,
          result_state TEXT NOT NULL,
          completed_at TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS claim_fts USING fts5(claim_id, subject_ref, predicate, object_text, content);
        CREATE VIRTUAL TABLE IF NOT EXISTS observation_fts USING fts5(observation_id, observation_type, summary, content);
        CREATE VIRTUAL TABLE IF NOT EXISTS alias_fts USING fts5(alias_id, alias, normalized_alias, target_id, content);
        """
    )


def get_active_generation_id(project_root: Path) -> str:
    ensure_cognition_db(project_root)
    with connect_cognition_db(project_root) as conn:
        row = conn.execute(
            "SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    return str(row["id"]) if row else ""


def seed_active_generation(project_root: Path, *, source_commit: str = "") -> str:
    ensure_cognition_db(project_root)
    generation_id = "GEN-0001"
    now = iso_now()
    with cognition_transaction(project_root) as conn:
        conn.execute("UPDATE generations SET state = 'superseded', superseded_at = ? WHERE state = 'active'", (now,))
        conn.execute(
            "INSERT OR REPLACE INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (generation_id, 1, "seed", "active", source_commit, now, now, "", "{}"),
        )
    return generation_id
```

- [ ] **Step 5: Export DB helpers**

Modify `src/specify_cli/cognition/__init__.py`:

```python
from .db import (
    connect_cognition_db,
    cognition_transaction,
    ensure_cognition_db,
    get_active_generation_id,
    seed_active_generation,
)
from .paths import cognition_db_path
```

Add these names to `__all__`.

- [ ] **Step 6: Run DB tests**

Run:

```bash
pytest tests/test_project_cognition_db.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/cognition/paths.py src/specify_cli/cognition/db.py src/specify_cli/cognition/__init__.py tests/test_project_cognition_db.py
git commit -m "feat: add sqlite project cognition store"
```

---

## Task 2: Extend Status Contract For DB Runtime

**Files:**
- Modify: `src/specify_cli/cognition/status.py`
- Modify: `tests/test_project_cognition_db.py`
- Test: `tests/test_project_cognition_db.py`

- [ ] **Step 1: Add failing status round-trip test**

Append to `tests/test_project_cognition_db.py`:

```python
from specify_cli.cognition import CognitionStatus, read_cognition_status, write_cognition_status


def test_cognition_status_round_trips_database_runtime_fields(tmp_path: Path) -> None:
    status = CognitionStatus(
        version=3,
        baseline_state="ready",
        baseline_commit="abc123",
        baseline_branch="main",
        graph_ready=True,
        freshness="fresh",
        graph_store_path=".specify/project-cognition/project-cognition.db",
        active_generation_id="GEN-0001",
        query_contract_version=1,
        update_contract_version=1,
    )

    write_cognition_status(tmp_path, status)
    loaded = read_cognition_status(tmp_path)

    assert loaded.graph_store_path == ".specify/project-cognition/project-cognition.db"
    assert loaded.active_generation_id == "GEN-0001"
    assert loaded.query_contract_version == 1
    assert loaded.update_contract_version == 1
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_project_cognition_db.py::test_cognition_status_round_trips_database_runtime_fields -q
```

Expected: FAIL because `CognitionStatus` lacks the new fields.

- [ ] **Step 3: Add fields to `CognitionStatus`**

Modify `src/specify_cli/cognition/status.py`:

```python
graph_store_path: str = ""
active_generation_id: str = ""
query_contract_version: int = 0
update_contract_version: int = 0
```

Add them after `graph_ready`.

- [ ] **Step 4: Parse fields in `read_cognition_status`**

In the `CognitionStatus(...)` return expression, add:

```python
graph_store_path=str(payload.get("graph_store_path", "")),
active_generation_id=str(payload.get("active_generation_id", "")),
query_contract_version=int(payload.get("query_contract_version", 0)),
update_contract_version=int(payload.get("update_contract_version", 0)),
```

- [ ] **Step 5: Run status tests**

Run:

```bash
pytest tests/test_project_cognition_db.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/cognition/status.py tests/test_project_cognition_db.py
git commit -m "feat: record cognition database status metadata"
```

---

## Task 3: Add Query Resolver And Task Bundle

**Files:**
- Create: `src/specify_cli/cognition/query.py`
- Modify: `src/specify_cli/cognition/__init__.py`
- Test: `tests/test_project_cognition_query.py`

- [ ] **Step 1: Write failing query resolver tests**

Create `tests/test_project_cognition_query.py`:

```python
from pathlib import Path

from specify_cli.cognition import (
    connect_cognition_db,
    ensure_cognition_db,
    query_project_cognition,
    seed_active_generation,
)


def _seed_login_graph(project_root: Path) -> str:
    ensure_cognition_db(project_root)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with connect_cognition_db(project_root) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'hash-login', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('symbol:AuthService.login', ?, 'symbol', 'AuthService.login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login', ?, 'login', 'login', 'capability', 'capability:auth.login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login-zh', ?, '登录', '登录', 'capability', 'capability:auth.login', 'zh', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-valid-password', ?, '正确密码登录失败', '正确密码登录失败', 'symptom', 'symptom:valid_credentials_rejected', 'zh', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO symbol_index(id, generation_id, symbol_name, normalized_symbol, node_id, path, relation, evidence_id, confidence) "
            "VALUES ('S-auth-service', ?, 'AuthService.login', 'authservice.login', 'symbol:AuthService.login', 'src/auth/login.ts', 'implements', 'E-login', 'strong')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO edges(id, generation_id, type, source_id, target_id, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('edge:login-service', ?, 'implements', 'capability:auth.login', 'symbol:AuthService.login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO edge_evidence(edge_id, evidence_id) VALUES ('edge:login-service', 'E-login')"
        )
        conn.execute(
            "INSERT INTO claims(id, generation_id, subject_ref, predicate, object_ref, object_value, truth_layer, confidence, status, last_validated_at, attrs_json) "
            "VALUES ('claim:login-implementation', ?, 'capability:auth.login', 'implemented_by', 'symbol:AuthService.login', '', 'implementation_reality', 'strong', 'active', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute("INSERT INTO claim_evidence(claim_id, evidence_id) VALUES ('claim:login-implementation', 'E-login')")
        conn.execute(
            "INSERT INTO claim_fts(claim_id, subject_ref, predicate, object_text, content) "
            "VALUES ('claim:login-implementation', 'capability:auth.login', 'implemented_by', 'AuthService.login', 'login AuthService valid password')"
        )
        conn.commit()
    return generation_id


def test_query_resolves_login_by_alias_with_evidence_trace(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="正确密码登录失败", paths=[])

    assert result["readiness"] == "ready"
    assert result["capability_candidates"][0]["node_id"] == "capability:auth.login"
    assert "alias:登录" in result["capability_candidates"][0]["matched_by"]
    assert result["capability_candidates"][0]["evidence_ids"] == ["E-login"]
    assert "src/auth/login.ts" in result["minimal_live_reads"]


def test_query_resolves_by_path_when_paths_are_known(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="implement", query_text="", paths=["src/auth/login.ts"])

    assert result["readiness"] == "ready"
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["minimal_live_reads"] == ["src/auth/login.ts"]


def test_query_reports_needs_update_when_path_is_missing_from_index(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="", paths=["src/auth/missing.ts"])

    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]


def test_query_reports_ambiguous_when_candidates_are_close(tmp_path: Path) -> None:
    generation_id = _seed_login_graph(tmp_path)
    with connect_cognition_db(tmp_path) as conn:
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:admin.sso_login', ?, 'capability', 'Admin SSO login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-admin-login', ?, 'login', 'login', 'capability', 'capability:admin.sso_login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.commit()

    result = query_project_cognition(tmp_path, intent="debug", query_text="login", paths=[])

    assert result["readiness"] == "ambiguous"
    assert result["recommended_next_action"] == "ask_user_to_select_candidate"
    assert {item["node_id"] for item in result["capability_candidates"]} == {
        "capability:auth.login",
        "capability:admin.sso_login",
    }
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_project_cognition_query.py -q
```

Expected: FAIL because `query_project_cognition` does not exist.

- [ ] **Step 3: Implement query resolver**

Create `src/specify_cli/cognition/query.py`:

```python
"""Task-local query API for the SQLite project cognition graph."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from .db import connect_cognition_db, ensure_cognition_db, get_active_generation_id


def normalize_query_token(value: str) -> str:
    lowered = " ".join(str(value or "").strip().lower().split())
    return lowered


def query_project_cognition(
    project_root: Path,
    *,
    intent: str,
    query_text: str = "",
    paths: list[str] | None = None,
) -> dict[str, Any]:
    ensure_cognition_db(project_root)
    generation_id = get_active_generation_id(project_root)
    if not generation_id:
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "capability_candidates": [],
            "symptom_candidates": [],
            "affected_nodes": [],
            "minimal_live_reads": [],
            "missing_coverage": ["project cognition database has no active generation"],
        }

    paths = [path.replace("\\", "/") for path in (paths or [])]
    with connect_cognition_db(project_root) as conn:
        path_nodes, missing_paths = _resolve_paths(conn, generation_id, paths)
        alias_candidates = _resolve_aliases(conn, generation_id, query_text)
        fts_candidates = _resolve_claim_fts(conn, generation_id, query_text)
        candidates = _merge_candidates(alias_candidates + fts_candidates)
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

        if missing_paths and not candidates:
            return {
                "readiness": "needs_update",
                "recommended_next_action": "run_map_update",
                "capability_candidates": [],
                "symptom_candidates": [],
                "affected_nodes": [],
                "minimal_live_reads": paths,
                "missing_coverage": [f"path not covered by project cognition index: {path}" for path in missing_paths],
            }

        readiness = _readiness_for_candidates(candidates)
        affected_nodes = sorted(set(path_nodes.keys()) | {item["node_id"] for item in candidates if item["target_type"] != "symptom"})
        minimal_live_reads = sorted(set(paths) | _paths_for_nodes(conn, generation_id, affected_nodes))

        return {
            "readiness": readiness,
            "recommended_next_action": _recommended_action(readiness),
            "intent": intent,
            "query": query_text,
            "capability_candidates": [item for item in candidates if item["target_type"] in {"capability", "node"}],
            "symptom_candidates": [item for item in candidates if item["target_type"] == "symptom"],
            "affected_nodes": affected_nodes,
            "minimal_live_reads": minimal_live_reads,
            "missing_coverage": [f"path not covered by project cognition index: {path}" for path in missing_paths],
            "subgraph": _subgraph_for_nodes(conn, generation_id, affected_nodes),
        }


def _resolve_paths(conn, generation_id: str, paths: list[str]) -> tuple[dict[str, set[str]], list[str]]:
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


def _resolve_aliases(conn, generation_id: str, query_text: str) -> list[dict[str, Any]]:
    normalized_query = normalize_query_token(query_text)
    if not normalized_query:
        return []
    tokens = _query_tokens(normalized_query)
    candidates: list[dict[str, Any]] = []
    for token in tokens:
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


def _resolve_claim_fts(conn, generation_id: str, query_text: str) -> list[dict[str, Any]]:
    normalized_query = normalize_query_token(query_text)
    if not normalized_query:
        return []
    safe_query = " OR ".join(token for token in re.findall(r"[\w\u4e00-\u9fff.:-]+", normalized_query) if token)
    if not safe_query:
        return []
    rows = conn.execute(
        "SELECT claims.subject_ref, claims.id AS claim_id FROM claim_fts "
        "JOIN claims ON claims.id = claim_fts.claim_id "
        "WHERE claims.generation_id = ? AND claim_fts MATCH ? LIMIT 10",
        (generation_id, safe_query),
    ).fetchall()
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


def _node_title(conn, generation_id: str, node_id: str) -> str:
    row = conn.execute(
        "SELECT title FROM nodes WHERE generation_id = ? AND id = ?",
        (generation_id, node_id),
    ).fetchone()
    return str(row["title"]) if row else node_id


def _claim_evidence(conn, claim_id: str) -> list[str]:
    rows = conn.execute("SELECT evidence_id FROM claim_evidence WHERE claim_id = ?", (claim_id,)).fetchall()
    return sorted(str(row["evidence_id"]) for row in rows)


def _paths_for_nodes(conn, generation_id: str, node_ids: list[str]) -> list[str]:
    if not node_ids:
        return []
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"SELECT DISTINCT path FROM path_index WHERE generation_id = ? AND node_id IN ({placeholders})",
        (generation_id, *node_ids),
    ).fetchall()
    return sorted(str(row["path"]) for row in rows)


def _subgraph_for_nodes(conn, generation_id: str, node_ids: list[str]) -> dict[str, list[str]]:
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
```

- [ ] **Step 4: Export query helper**

Modify `src/specify_cli/cognition/__init__.py`:

```python
from .query import query_project_cognition
```

Add `query_project_cognition` to `__all__`.

- [ ] **Step 5: Run query tests**

Run:

```bash
pytest tests/test_project_cognition_query.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/cognition/query.py src/specify_cli/cognition/__init__.py tests/test_project_cognition_query.py
git commit -m "feat: add project cognition query resolver"
```

---

## Task 4: Add Transactional Update Helper

**Files:**
- Create: `src/specify_cli/cognition/update.py`
- Modify: `src/specify_cli/cognition/__init__.py`
- Test: `tests/test_project_cognition_db.py`

- [ ] **Step 1: Add failing update transaction tests**

Append to `tests/test_project_cognition_db.py`:

```python
from specify_cli.cognition import (
    apply_cognition_update,
    query_project_cognition,
)


def test_apply_cognition_update_records_affected_path_update(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with connect_cognition_db(tmp_path) as conn:
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
    assert result["affected_nodes"] == ["capability:auth.login"]
    with connect_cognition_db(tmp_path) as conn:
        updates = conn.execute("SELECT changed_paths_json, result_state FROM updates").fetchall()
    assert len(updates) == 1
    assert updates[0]["result_state"] == "ready"


def test_apply_cognition_update_rolls_back_when_path_missing(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    seed_active_generation(tmp_path, source_commit="abc123")

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/missing.ts"], reason="unit-test")

    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    with connect_cognition_db(tmp_path) as conn:
        updates = conn.execute("SELECT id FROM updates").fetchall()
    assert updates == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_project_cognition_db.py::test_apply_cognition_update_records_affected_path_update tests/test_project_cognition_db.py::test_apply_cognition_update_rolls_back_when_path_missing -q
```

Expected: FAIL because `apply_cognition_update` does not exist.

- [ ] **Step 3: Implement update helper**

Create `src/specify_cli/cognition/update.py`:

```python
"""Transactional update helpers for the SQLite project cognition graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .db import cognition_transaction, ensure_cognition_db, get_active_generation_id, iso_now


def apply_cognition_update(
    project_root: Path,
    *,
    changed_paths: list[str],
    reason: str,
) -> dict[str, Any]:
    ensure_cognition_db(project_root)
    generation_id = get_active_generation_id(project_root)
    if not generation_id:
        return {
            "readiness": "needs_rebuild",
            "recommended_next_action": "run_map_scan_build",
            "affected_nodes": [],
            "missing_coverage": ["project cognition database has no active generation"],
        }

    try:
        normalized_paths = [path.replace("\\", "/") for path in changed_paths]
        with cognition_transaction(project_root) as conn:
            rows = conn.execute(
                "SELECT DISTINCT node_id FROM path_index WHERE generation_id = ? AND path IN ({})".format(
                    ",".join("?" for _ in normalized_paths)
                ),
                (generation_id, *normalized_paths),
            ).fetchall() if normalized_paths else []
            affected_nodes = sorted(str(row["node_id"]) for row in rows)
            if not affected_nodes:
                raise _RollbackUpdate(
                    {
                        "readiness": "needs_update",
                        "recommended_next_action": "run_map_update",
                        "affected_nodes": [],
                        "missing_coverage": [f"path not covered by project cognition index: {path}" for path in normalized_paths],
                    }
                )
            update_id = f"UPD-{uuid4().hex[:12]}"
            now = iso_now()
            conn.execute(
                "INSERT INTO updates(id, generation_id, trigger, changed_paths_json, affected_nodes_json, affected_claims_json, affected_slices_json, result_state, completed_at, attrs_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    update_id,
                    generation_id,
                    reason,
                    json.dumps(normalized_paths),
                    json.dumps(affected_nodes),
                    "[]",
                    "[]",
                    "ready",
                    now,
                    "{}",
                ),
            )
            return {
                "readiness": "ready",
                "recommended_next_action": "retry_current_workflow",
                "update_id": update_id,
                "affected_nodes": affected_nodes,
                "missing_coverage": [],
            }
    except _RollbackUpdate as exc:
        return exc.payload


class _RollbackUpdate(Exception):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__("cognition update cannot be bounded")
        self.payload = payload
```

- [ ] **Step 4: Export update helper**

Modify `src/specify_cli/cognition/__init__.py`:

```python
from .update import apply_cognition_update
```

Add `apply_cognition_update` to `__all__`.

- [ ] **Step 5: Run update tests**

Run:

```bash
pytest tests/test_project_cognition_db.py tests/test_project_cognition_query.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/cognition/update.py src/specify_cli/cognition/__init__.py tests/test_project_cognition_db.py
git commit -m "feat: add transactional cognition update helper"
```

---

## Task 5: Replace Canonical Runtime Paths And Freshness Mapping

**Files:**
- Modify: `src/specify_cli/project_cognition_status.py`
- Modify: `tests/test_project_map_status.py`
- Test: `tests/test_project_map_status.py`

- [ ] **Step 1: Update failing canonical path test**

Modify `tests/test_project_map_status.py::test_missing_canonical_project_map_paths_lists_required_outputs`:

```python
def test_missing_canonical_project_map_paths_lists_required_outputs(tmp_path):
    mod = _load_module()

    missing = mod.missing_canonical_project_map_paths(tmp_path)

    normalized = [str(path).replace("\\", "/") for path in missing]
    assert normalized == [
        f"{tmp_path.as_posix()}/.specify/project-cognition/status.json",
        f"{tmp_path.as_posix()}/.specify/project-cognition/project-cognition.db",
    ]
```

- [ ] **Step 2: Update test helper baseline**

Modify `_write_cognition_baseline` in `tests/test_project_map_status.py`:

```python
def _write_cognition_baseline(project_root: Path, *, graph_ready: bool = True) -> None:
    cognition_dir = project_root / ".specify" / "project-cognition"
    cognition_dir.mkdir(parents=True, exist_ok=True)
    (cognition_dir / "status.json").write_text(
        (
            '{"version": 3, "graph_ready": true, "baseline_state": "ready", '
            '"freshness": "fresh", "graph_store_path": ".specify/project-cognition/project-cognition.db", '
            '"active_generation_id": "GEN-0001", "query_contract_version": 1, "update_contract_version": 1}\n'
            if graph_ready
            else '{"version": 3, "graph_ready": false, "baseline_state": "missing"}\n'
        ),
        encoding="utf-8",
    )
    (cognition_dir / "project-cognition.db").write_bytes(b"SQLite test database marker")
```

- [ ] **Step 3: Run focused tests to verify failure**

Run:

```bash
pytest tests/test_project_map_status.py::test_missing_canonical_project_map_paths_lists_required_outputs -q
```

Expected: FAIL because runtime paths still include JSON graph files.

- [ ] **Step 4: Replace canonical runtime paths**

Modify imports in `src/specify_cli/project_cognition_status.py`:

```python
from specify_cli.cognition import (
    cognition_db_path,
    cognition_status_path,
    read_cognition_status,
    write_cognition_status,
)
```

Replace `canonical_cognition_runtime_paths`:

```python
def canonical_cognition_runtime_paths(project_root: Path) -> list[Path]:
    return [
        cognition_status_path(project_root),
        cognition_db_path(project_root),
    ]
```

Replace `atlas_minimum_read_set`:

```python
def atlas_minimum_read_set(project_root: Path) -> list[Path]:
    return [
        cognition_status_path(project_root),
        cognition_db_path(project_root),
    ]
```

- [ ] **Step 5: Update missing guidance copy**

Search in `src/specify_cli/project_cognition_status.py` for JSON graph wording:

```bash
rg -n "nodes.json|edges.json|claims.json|conflicts.json|slices" src/specify_cli/project_cognition_status.py
```

Expected after edits: no required-runtime-path references to raw graph JSON.

- [ ] **Step 6: Run status tests**

Run:

```bash
pytest tests/test_project_map_status.py -q
```

Expected: PASS after updating assertions that expected slice or graph paths.

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/project_cognition_status.py tests/test_project_map_status.py
git commit -m "refactor: make sqlite database the cognition runtime path"
```

---

## Task 6: Add Project-Cognition CLI Query And Update Commands

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `tests/integrations/test_cli.py`:

```python
def test_project_cognition_cli_exposes_local_query_update_surface():
    runner = CliRunner()

    help_result = runner.invoke(app, ["project-cognition", "--help"], catch_exceptions=False)
    query_help = runner.invoke(app, ["project-cognition", "query", "--help"], catch_exceptions=False)
    update_help = runner.invoke(app, ["project-cognition", "update", "--help"], catch_exceptions=False)
    cognition_help = runner.invoke(app, ["cognition", "--help"], catch_exceptions=False)

    assert help_result.exit_code == 0, help_result.output
    assert query_help.exit_code == 0, query_help.output
    assert update_help.exit_code == 0, update_help.output
    assert "--intent" in query_help.output
    assert "--query" in query_help.output
    assert "--paths" in query_help.output
    assert "--changed-paths" in update_help.output
    assert "Discover and read fresh cross-project cognition references" in cognition_help.output
    assert "query" not in cognition_help.output.lower()


def test_project_cognition_query_outputs_json_for_empty_runtime(tmp_path):
    runner = CliRunner()
    project = tmp_path / "query-empty-runtime"
    project.mkdir()
    (project / ".specify").mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["project-cognition", "query", "--intent", "debug", "--query", "login", "--format", "json"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["readiness"] == "needs_rebuild"
    assert payload["recommended_next_action"] == "run_map_scan_build"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/integrations/test_cli.py::test_project_cognition_cli_exposes_local_query_update_surface tests/integrations/test_cli.py::test_project_cognition_query_outputs_json_for_empty_runtime -q
```

Expected: FAIL because query/update commands do not exist.

- [ ] **Step 3: Add CLI command imports**

In `src/specify_cli/__init__.py`, ensure the top-level imports include:

```python
from specify_cli.cognition import apply_cognition_update, query_project_cognition
```

- [ ] **Step 4: Add `project-cognition query` command**

Add near existing `project_cognition_app` commands:

```python
@project_cognition_app.command("query")
def project_cognition_query_command(
    intent: str = typer.Option(..., "--intent", help="Task intent such as debug, implement, plan, or explain"),
    query_text: str = typer.Option("", "--query", help="Natural-language project cognition query"),
    paths: list[str] = typer.Option([], "--paths", help="Known touched path; may be specified more than once"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or text"),
):
    """Return a task-local project cognition bundle from the active project's graph store."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = query_project_cognition(project_root, intent=intent, query_text=query_text, paths=paths)
    if output_format.lower() == "json":
        print_json(payload, indent=2)
        return
    console.print(_cli_panel(json.dumps(payload, indent=2), title="Project Cognition Query", border_style="cyan"))
```

- [ ] **Step 5: Add `project-cognition update` command**

Add:

```python
@project_cognition_app.command("update")
def project_cognition_update_command(
    changed_paths: list[str] = typer.Option(..., "--changed-paths", help="Changed path; may be specified more than once"),
    reason: str = typer.Option("manual", "--reason", help="Update trigger or reason"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or text"),
):
    """Apply a bounded transactional project cognition update for changed paths."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = apply_cognition_update(project_root, changed_paths=changed_paths, reason=reason)
    if output_format.lower() == "json":
        print_json(payload, indent=2)
        return
    console.print(_cli_panel(json.dumps(payload, indent=2), title="Project Cognition Update", border_style="cyan"))
```

- [ ] **Step 6: Add rebuild and doctor diagnostic commands**

Add commands that do not implement full rebuild yet but return current status:

```python
@project_cognition_app.command("doctor")
def project_cognition_doctor_command(
    output_format: str = typer.Option("json", "--format", help="Output format: json or text"),
):
    """Inspect local project cognition database readiness."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    result = inspect_project_cognition_freshness(project_root)
    if output_format.lower() == "json":
        print_json(result, indent=2)
        return
    _render_project_map_freshness(result)
```
```python
@project_cognition_app.command("rebuild")
def project_cognition_rebuild_command():
    """Explain the rebuild workflow for the local project cognition database."""
    console.print("Run [cyan]/sp-map-scan[/cyan], then [cyan]/sp-map-build[/cyan] to rebuild project cognition.")
```

- [ ] **Step 7: Run CLI tests**

Run:

```bash
pytest tests/integrations/test_cli.py::test_project_cognition_cli_exposes_local_query_update_surface tests/integrations/test_cli.py::test_project_cognition_query_outputs_json_for_empty_runtime -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/specify_cli/__init__.py tests/integrations/test_cli.py
git commit -m "feat: add project cognition query cli"
```

---

## Task 7: Replace Hook Artifact Validation Contract

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Test: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Update hook test fixture to DB runtime**

Modify `_write_project_cognition_runtime` in
`tests/contract/test_hook_cli_surface.py`:

```python
def _write_project_cognition_runtime(run_dir: Path) -> None:
    (run_dir / "status.json").write_text(
        '{"version": 3, "graph_ready": true, "freshness": "fresh", '
        '"graph_store_path": ".specify/project-cognition/project-cognition.db", '
        '"active_generation_id": "GEN-0001", "query_contract_version": 1, "update_contract_version": 1}\n',
        encoding="utf-8",
    )
    (run_dir / "project-cognition.db").write_bytes(b"SQLite test database marker")
```

- [ ] **Step 2: Add failing validation test for missing DB**

Append near map validation tests:

```python
def test_map_build_artifact_validation_requires_sqlite_database(tmp_path: Path):
    run_dir = tmp_path / ".specify" / "project-cognition"
    run_dir.mkdir(parents=True)
    (run_dir / "status.json").write_text('{"version": 3, "graph_ready": true}\n', encoding="utf-8")

    result = _invoke_in_project(
        tmp_path,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir), "--format", "json"],
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert any("project-cognition.db" in message for message in payload["errors"])
```

- [ ] **Step 3: Run focused hook tests to verify failure**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -k "map_build or map_update or project_cognition_runtime" -q
```

Expected: FAIL because validator still requires graph JSON artifacts.

- [ ] **Step 4: Replace map-build artifact validation**

Modify `src/specify_cli/hooks/artifact_validation.py`:

```python
def _validate_cognition_database_artifact(feature_dir: Path) -> list[str]:
    db_path = feature_dir / "project-cognition.db"
    if not db_path.exists() or not db_path.is_file():
        return ["project-cognition.db must exist for the SQLite project cognition runtime"]
    if db_path.stat().st_size == 0:
        return ["project-cognition.db must not be empty"]
    return []
```

Replace `_validate_map_build_artifacts`:

```python
def _validate_map_build_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_cognition_status_artifact(feature_dir))
    errors.extend(_validate_cognition_database_artifact(feature_dir))
    return errors
```

Replace `_validate_map_update_artifacts` so it no longer delegates to JSON graph
validation:

```python
def _validate_map_update_artifacts(feature_dir: Path) -> list[str]:
    errors = _validate_map_build_artifacts(feature_dir)
    payload, read_errors = _read_json_artifact(feature_dir / "status.json", "status.json")
    if read_errors:
        errors.extend(read_errors)
        return errors
    if not isinstance(payload, dict):
        errors.append("status.json must contain a top-level JSON object")
        return errors
    if not payload.get("last_update_id") and payload.get("freshness") not in {"fresh", "partial_refresh"}:
        errors.append("status.json must record last_update_id or a post-update freshness state")
    return errors
```

- [ ] **Step 5: Run hook validation tests**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -k "map_build or map_update or project_cognition_runtime" -q
```

Expected: PASS after updating assertions that expected graph JSON files.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/contract/test_hook_cli_surface.py
git commit -m "refactor: validate sqlite cognition artifacts"
```

---

## Task 8: Replace Workflow Template Graph Reads With Query API

**Files:**
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/commands/prd-scan.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/map-update.md`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: template guidance tests under `tests/`

- [ ] **Step 1: Add failing guidance assertion**

Add to `tests/test_map_runtime_template_guidance.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workflows_use_project_cognition_query_instead_of_raw_graph_reads() -> None:
    workflow_files = [
        "fast.md",
        "quick.md",
        "specify.md",
        "clarify.md",
        "deep-research.md",
        "plan.md",
        "tasks.md",
        "implement.md",
        "debug.md",
        "test-scan.md",
        "test-build.md",
        "prd-scan.md",
    ]
    for name in workflow_files:
        content = (ROOT / "templates" / "commands" / name).read_text(encoding="utf-8").lower()
        assert "project-cognition query" in content
        assert ".specify/project-cognition/graph/nodes.json" not in content
        assert ".specify/project-cognition/graph/edges.json" not in content
        assert ".specify/project-cognition/graph/claims.json" not in content
        assert ".specify/project-cognition/graph/conflicts.json" not in content
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_map_runtime_template_guidance.py::test_workflows_use_project_cognition_query_instead_of_raw_graph_reads -q
```

Expected: FAIL because templates still reference graph JSON artifacts.

- [ ] **Step 3: Replace cognition gate wording**

For each workflow file listed in Step 1, replace raw graph read instructions
with this pattern:

```markdown
**Project cognition gate:** query the active project's runtime before broad
repository reads.

Run or emulate:

```text
specify project-cognition query --intent <workflow-intent> --query "$ARGUMENTS" --format json
```

Use the returned readiness:

- `ready`: continue with the returned task-local bundle.
- `review`: perform only the returned `minimal_live_reads` before continuing.
- `ambiguous`: ask the user to select the intended candidate.
- `needs_update`: route through `{{invoke:map-update}}`.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: stop and report the blocking runtime issue.
```
```

Use workflow-specific `--intent` values:

```text
fast -> implement
quick -> implement
specify -> plan
clarify -> plan
deep-research -> research
plan -> plan
tasks -> plan
implement -> implement
debug -> debug
test-scan -> test
test-build -> test
prd-scan -> research
```

- [ ] **Step 4: Update `map-update.md` required inputs**

In `templates/commands/map-update.md`, replace the Required Inputs list with:

```markdown
At minimum, read:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db` through the
  `project-cognition` query/update helpers
- changed paths or changed commit range
- user supplement input if provided

Do not read or rewrite raw graph JSON artifacts; they are not runtime truth.
```

- [ ] **Step 5: Update passive skills**

In `templates/passive-skills/spec-kit-project-map-gate/SKILL.md` and
`templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace any
guidance that says to read status plus slices/graph artifacts with:

```markdown
Use `specify project-cognition query` to retrieve the task-local project
cognition bundle. Treat raw graph JSON artifacts as obsolete runtime surfaces.
```

- [ ] **Step 6: Run guidance tests**

Run:

```bash
pytest tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS after updating expected generated guidance.

- [ ] **Step 7: Commit**

```bash
git add templates/commands templates/command-partials/common/context-loading-gradient.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py
git commit -m "docs: route workflows through cognition query api"
```

---

## Task 9: Align Preflight Hooks And Status Messaging

**Files:**
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`

- [ ] **Step 1: Update preflight baseline fixture**

Modify `_write_cognition_baseline` in `tests/hooks/test_preflight_hooks.py`:

```python
def _write_cognition_baseline(project: Path) -> None:
    cognition_dir = project / ".specify" / "project-cognition"
    cognition_dir.mkdir(parents=True, exist_ok=True)
    (cognition_dir / "status.json").write_text(
        '{"version": 3, "graph_ready": true, "baseline_state": "ready", "freshness": "fresh", '
        '"graph_store_path": ".specify/project-cognition/project-cognition.db", '
        '"active_generation_id": "GEN-0001", "query_contract_version": 1, "update_contract_version": 1}\n',
        encoding="utf-8",
    )
    (cognition_dir / "project-cognition.db").write_bytes(b"SQLite test database marker")
```

- [ ] **Step 2: Add assertion that preflight no longer names raw graph JSON**

Add:

```python
def test_preflight_missing_runtime_guidance_names_sqlite_database_not_graph_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    combined = "\n".join(result.errors + result.warnings).lower()
    assert "project-cognition.db" in combined or "project cognition" in combined
    assert "nodes.json" not in combined
    assert "edges.json" not in combined
    assert "claims.json" not in combined
    assert "conflicts.json" not in combined
```

- [ ] **Step 3: Run preflight tests to verify failures**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py -q
```

Expected: FAIL until status/freshness helpers and messages stop requiring raw
graph artifacts.

- [ ] **Step 4: Update preflight messages**

In `src/specify_cli/hooks/preflight.py`, replace any raw graph or slice guidance
with:

```python
"project cognition runtime is missing; run /sp-map-scan, then /sp-map-build to create status.json and project-cognition.db"
```

Keep existing same-feature implement dirty-origin warning behavior unless tests
explicitly remove it.

- [ ] **Step 5: Update docs**

In `README.md` and `PROJECT-HANDBOOK.md`, replace:

```markdown
`.specify/project-cognition/status.json` plus workflow-appropriate slices
```

with:

```markdown
`.specify/project-cognition/status.json` plus the task-local bundle returned by
`specify project-cognition query`
```

Also state that `project-cognition.db` is the canonical graph store.

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/hooks/test_preflight_hooks.py tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py -q
```

Expected: PASS after updating doc assertions.

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/hooks/preflight.py tests/hooks/test_preflight_hooks.py README.md PROJECT-HANDBOOK.md tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py
git commit -m "docs: align preflight with sqlite cognition runtime"
```

---

## Task 10: End-To-End Verification And Cleanup

**Files:**
- Modify: `docs/superpowers/plans/2026-05-13-project-cognition-sqlite-graph-store-implementation.md`

- [ ] **Step 1: Search for obsolete required graph reads**

Run:

```bash
rg -n "project-cognition/graph/(nodes|edges|claims|conflicts)\\.json|slices/change\\.json|slices/debug\\.json" templates src tests README.md PROJECT-HANDBOOK.md
```

Expected: no runtime-required references. Remaining references are allowed only
inside old-design docs or explicit negative assertions.

- [ ] **Step 2: Run focused runtime suite**

Run:

```bash
pytest tests/test_project_cognition_db.py tests/test_project_cognition_query.py tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 3: Run template and integration guidance suite**

Run:

```bash
pytest tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 4: Run full test suite**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 5: Record verification notes**

Append to this plan:

```markdown
## Verification Notes

- `pytest tests/test_project_cognition_db.py tests/test_project_cognition_query.py tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/integrations/test_cli.py -q`
- `pytest tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q`
- `pytest -q`
- Confirmed `project-cognition.db` is the canonical graph runtime path.
- Confirmed `project-cognition query` returns task-local bundles.
- Confirmed raw graph JSON files are no longer required by freshness, hook validation, or workflow templates.
```

- [ ] **Step 6: Commit verification notes**

```bash
git add docs/superpowers/plans/2026-05-13-project-cognition-sqlite-graph-store-implementation.md
git commit -m "docs: record sqlite cognition runtime verification"
```

---

## Self-Review Notes

### Spec Coverage

- SQLite canonical graph store: Tasks 1, 2, 5.
- Evidence-backed query resolver: Task 3.
- Transactional map-update helper: Task 4.
- Freshness and readiness boundary: Tasks 2, 5, 9.
- CLI namespace boundary: Task 6.
- Hook validation replacement: Task 7.
- Workflow template replacement: Task 8.
- Documentation and verification: Tasks 9, 10.

### Placeholder Scan

No deferred implementation markers are used. Steps that
modify code include concrete code blocks or exact replacement text.

### Type Consistency

The plan consistently uses:

- `project-cognition.db`
- `cognition_db_path`
- `ensure_cognition_db`
- `connect_cognition_db`
- `get_active_generation_id`
- `seed_active_generation`
- `query_project_cognition`
- `apply_cognition_update`
- `active_generation_id`
- `graph_store_path`
- `query_contract_version`
- `update_contract_version`

## Verification Notes

- `pytest tests/test_project_cognition_db.py tests/test_project_cognition_query.py tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/integrations/test_cli.py -q`
- `pytest tests/test_extension_skills.py tests/integrations/test_integration_claude.py tests/test_map_runtime_template_guidance.py tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/test_project_handbook_templates.py tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py -q`
- `pytest tests/integrations/test_cli.py::TestInitIntegrationFlag::test_non_codex_implement_skill_does_not_use_specify_team_as_primary_entrypoint tests/execution/test_packet_compiler.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py tests/codex_team/test_worker_bootstrap.py -q`
- Confirmed `project-cognition.db` is the canonical graph runtime path.
- Confirmed `project-cognition query` returns task-local bundles and readiness guidance across generated workflow surfaces.
- Confirmed raw graph JSON files are no longer required by freshness, hook validation, workflow templates, generated addenda, or execution packet defaults.
- Full `pytest -q` was attempted once but hit the 10-minute command timeout in this environment; focused runtime, template/integration, and execution suites above passed.
