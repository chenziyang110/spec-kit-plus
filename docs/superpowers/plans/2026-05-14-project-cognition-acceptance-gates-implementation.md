# Project Cognition Acceptance Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-checkable acceptance gates so first-time `sp-map-scan -> sp-map-build` creates a complete query-ready cognition baseline, and later changes use `sp-map-update` without allowing false `fresh` states.

**Architecture:** Add a focused validation module under `src/specify_cli/cognition/` that owns scan and build acceptance. Expose it through `project-cognition validate-scan` and `validate-build`, reuse it from artifact validation and refresh finalizers, then update workflow templates so agents must run those gates before claiming completion.

**Tech Stack:** Python 3.11, Typer CLI, SQLite, existing `specify_cli.cognition` runtime helpers, project cognition status helpers, pytest integration and contract tests, Markdown workflow templates.

---

## File Structure

```text
CREATE
  src/specify_cli/cognition/validation.py
    Purpose: single source of truth for scan acceptance, build acceptance, JSON payload shape, and validation error messages.

  tests/test_project_cognition_validation.py
    Purpose: unit coverage for validation helpers without going through Typer or hooks.

MODIFY
  src/specify_cli/cognition/__init__.py
    Purpose: export validate_scan_acceptance and validate_build_acceptance.

  src/specify_cli/__init__.py
    Purpose: add project-cognition validate-scan/validate-build CLI commands; make complete-refresh validate build acceptance before writing fresh; make record-refresh avoid false fresh when build acceptance fails; improve query missing-baseline reason.

  src/specify_cli/hooks/artifact_validation.py
    Purpose: reuse the cognition validation helpers for map-scan, map-build, and map-update artifact validation.

  src/specify_cli/hooks/project_cognition.py
    Purpose: make hook complete-refresh enforce build acceptance before finalizing fresh.

  templates/commands/map-scan.md
    Purpose: require validate-scan before scan completion and before handoff to map-build.

  templates/commands/map-build.md
    Purpose: require validate-build before completion and before complete-refresh.

  templates/commands/map-update.md
    Purpose: require validate-build after update records and forbid complete-refresh when update returns needs_rebuild.

  README.md
  docs/quickstart.md
  PROJECT-HANDBOOK.md
    Purpose: document the accepted lifecycle: first scan/build baseline, later map-update incrementals, rebuild only for missing/unusable baselines.

TESTS TO MODIFY
  tests/integrations/test_cli.py
    Purpose: CLI command exposure, complete-refresh blocking, record-refresh partial behavior, query reason specificity.

  tests/contract/test_hook_cli_surface.py
    Purpose: hook artifact validation and complete-refresh hook now require real query-ready SQLite DB, not marker bytes.

  tests/test_map_scan_build_template_guidance.py
  tests/test_map_runtime_template_guidance.py
  tests/test_command_surface_semantics.py
    Purpose: generated workflow guidance requires validate-scan/validate-build and preserves map-update-first maintenance semantics.
```

## Validation Payload Contract

Every validator returns this shape:

```python
{
    "status": "ok" | "blocked",
    "gate": "scan" | "build",
    "readiness": "scan_ready" | "query_ready" | "blocked",
    "errors": ["human-readable blocking reason"],
    "warnings": ["human-readable non-blocking note"],
    "checked_paths": [".specify/project-cognition/status.json"],
    "details": {"key": "value"},
}
```

The implementation should build this with small helpers:

```python
def _result(gate: str, ready_readiness: str, errors: list[str], warnings: list[str], checked_paths: list[str], details: dict[str, object]) -> dict[str, object]:
    return {
        "status": "blocked" if errors else "ok",
        "gate": gate,
        "readiness": "blocked" if errors else ready_readiness,
        "errors": errors,
        "warnings": warnings,
        "checked_paths": checked_paths,
        "details": details,
    }
```

---

### Task 1: Add Validation Helper Unit Tests

**Files:**
- Create: `tests/test_project_cognition_validation.py`
- Read: `tests/test_project_cognition_query.py`
- Read: `tests/test_project_cognition_db.py`

- [ ] **Step 1: Write failing tests for scan acceptance**

Create `tests/test_project_cognition_validation.py` with these imports and helpers:

```python
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path

from specify_cli.cognition import (
    CognitionStatus,
    connect_cognition_db,
    ensure_cognition_db,
    seed_active_generation,
    validate_build_acceptance,
    validate_scan_acceptance,
    write_cognition_status,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_complete_scan_package(project_root: Path) -> None:
    run_dir = project_root / ".specify" / "project-cognition"
    _write_json(run_dir / "status.json", {"version": 3, "graph_ready": False})
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "E-001.json").write_text('{"id": "E-001"}\n', encoding="utf-8")
    _write_json(run_dir / "provisional" / "nodes.json", {"nodes": [{"id": "capability:auth.login"}]})
    _write_json(run_dir / "provisional" / "edges.json", {"edges": []})
    _write_json(run_dir / "provisional" / "observations.json", {"observations": [{"id": "OBS-001"}]})
    _write_json(run_dir / "coverage.json", {"rows": [{"path": "src/auth/login.ts", "criticality": "critical"}]})
    _write_json(
        run_dir / "workbench" / "coverage-ledger.json",
        {
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "covered",
                }
            ],
            "open_gaps": [],
        },
    )
    packets_dir = run_dir / "workbench" / "scan-packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    (packets_dir / "core.md").write_text("# Core scan packet\n", encoding="utf-8")
```

Add these tests:

```python
def test_validate_scan_blocks_when_required_artifacts_are_missing(tmp_path: Path) -> None:
    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert result["gate"] == "scan"
    assert result["readiness"] == "blocked"
    assert any("status.json" in message for message in result["errors"])
    assert any("coverage-ledger.json" in message for message in result["errors"])


def test_validate_scan_accepts_complete_scan_package(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert result["readiness"] == "scan_ready"
    assert result["errors"] == []
    assert ".specify/project-cognition/workbench/coverage-ledger.json" in result["checked_paths"]
```

- [ ] **Step 2: Write failing tests for build acceptance**

Append this helper:

```python
def _seed_query_ready_runtime(project_root: Path) -> str:
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
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
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login', ?, 'login', 'login', 'capability', 'capability:auth.login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO claims(id, generation_id, subject_ref, predicate, object_ref, object_value, truth_layer, confidence, status, last_validated_at, attrs_json) "
            "VALUES ('claim:login', ?, 'capability:auth.login', 'implemented_by', 'src/auth/login.ts', '', 'implementation_reality', 'strong', 'active', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.commit()
    write_cognition_status(
        project_root,
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
    return generation_id
```

Append these tests:

```python
def test_validate_build_blocks_when_db_is_missing(tmp_path: Path) -> None:
    write_cognition_status(tmp_path, CognitionStatus(version=3, graph_ready=True))

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("project-cognition.db" in message and "must exist" in message for message in result["errors"])


def test_validate_build_blocks_when_db_has_no_active_generation(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    write_cognition_status(tmp_path, CognitionStatus(version=3, graph_ready=True))

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("active generation" in message for message in result["errors"])


def test_validate_build_blocks_when_status_generation_conflicts_with_db(tmp_path: Path) -> None:
    _seed_query_ready_runtime(tmp_path)
    write_cognition_status(
        tmp_path,
        CognitionStatus(
            version=3,
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id="GEN-WRONG",
        ),
    )

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("active_generation_id" in message and "does not match" in message for message in result["errors"])


def test_validate_build_accepts_query_ready_runtime(tmp_path: Path) -> None:
    _seed_query_ready_runtime(tmp_path)

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert result["readiness"] == "query_ready"
    assert result["errors"] == []
    assert result["details"]["active_generation_id"] == "GEN-0001"
```

- [ ] **Step 3: Run the new tests and verify they fail on missing imports**

Run:

```bash
pytest tests/test_project_cognition_validation.py -q
```

Expected: FAIL with `ImportError` or `cannot import name 'validate_build_acceptance'`.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_project_cognition_validation.py
git commit -m "test: define project cognition acceptance gates"
```

Expected: commit succeeds with only the new test file.

---

### Task 2: Implement Acceptance Validation Module

**Files:**
- Create: `src/specify_cli/cognition/validation.py`
- Modify: `src/specify_cli/cognition/__init__.py`
- Test: `tests/test_project_cognition_validation.py`

- [ ] **Step 1: Implement validation helpers**

Create `src/specify_cli/cognition/validation.py`:

```python
"""Acceptance gates for project cognition scan and SQLite build outputs."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

from .db import SCHEMA_VERSION, connect_cognition_db
from .paths import cognition_db_path, cognition_dir
from .query import query_project_cognition
from .status import read_cognition_status


REQUIRED_TABLES = {
    "metadata",
    "generations",
    "nodes",
    "edges",
    "claims",
    "path_index",
    "alias_index",
    "updates",
}


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _result(
    *,
    gate: str,
    ready_readiness: str,
    errors: list[str],
    warnings: list[str],
    checked_paths: list[str],
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "status": "blocked" if errors else "ok",
        "gate": gate,
        "readiness": "blocked" if errors else ready_readiness,
        "errors": errors,
        "warnings": warnings,
        "checked_paths": checked_paths,
        "details": details,
    }


def _read_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        errors.append(f"{label} must exist")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label} must be valid JSON: {exc.msg}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a top-level JSON object")
        return {}
    return payload


def _list_payload(payload: dict[str, Any], key: str, label: str, errors: list[str]) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{label} must define a top-level {key} array")
        return []
    return value


def _directory_has_files(path: Path) -> bool:
    return path.exists() and path.is_dir() and any(child.is_file() for child in path.iterdir())


def validate_scan_acceptance(project_root: Path) -> dict[str, object]:
    root = project_root.resolve()
    run_dir = cognition_dir(root)
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    details: dict[str, object] = {}

    status_path = run_dir / "status.json"
    checked.append(_relative(root, status_path))
    _read_json_object(status_path, ".specify/project-cognition/status.json", errors)

    evidence_dir = run_dir / "evidence"
    checked.append(_relative(root, evidence_dir))
    if not _directory_has_files(evidence_dir):
        errors.append(".specify/project-cognition/evidence/ must exist and contain evidence files")

    provisional_specs = (
        ("provisional/nodes.json", "nodes"),
        ("provisional/edges.json", "edges"),
        ("provisional/observations.json", "observations"),
    )
    for relative_path, key in provisional_specs:
        path = run_dir / relative_path
        checked.append(_relative(root, path))
        payload = _read_json_object(path, f".specify/project-cognition/{relative_path}", errors)
        if payload:
            rows = _list_payload(payload, key, f".specify/project-cognition/{relative_path}", errors)
            details[f"{key}_count"] = len(rows)

    coverage_path = run_dir / "coverage.json"
    checked.append(_relative(root, coverage_path))
    coverage = _read_json_object(coverage_path, ".specify/project-cognition/coverage.json", errors)
    if coverage:
        coverage_rows = _list_payload(coverage, "rows", ".specify/project-cognition/coverage.json", errors)
        details["coverage_rows"] = len(coverage_rows)
        if not coverage_rows:
            warnings.append(".specify/project-cognition/coverage.json contains no coverage rows")

    ledger_path = run_dir / "workbench" / "coverage-ledger.json"
    checked.append(_relative(root, ledger_path))
    ledger = _read_json_object(
        ledger_path,
        ".specify/project-cognition/workbench/coverage-ledger.json",
        errors,
    )
    if ledger:
        ledger_rows = _list_payload(
            ledger,
            "rows",
            ".specify/project-cognition/workbench/coverage-ledger.json",
            errors,
        )
        details["ledger_rows"] = len(ledger_rows)
        unresolved_critical = [
            row
            for row in ledger_rows
            if isinstance(row, dict)
            and str(row.get("criticality", "")).lower() == "critical"
            and str(row.get("coverage_state", row.get("state", ""))).lower() not in {"covered", "accepted", "complete"}
        ]
        if unresolved_critical:
            errors.append("coverage-ledger.json has unresolved critical coverage rows")
        open_gaps = ledger.get("open_gaps", [])
        if isinstance(open_gaps, list):
            critical_gaps = [
                gap
                for gap in open_gaps
                if isinstance(gap, dict) and str(gap.get("criticality", "")).lower() == "critical"
            ]
            if critical_gaps:
                errors.append("coverage-ledger.json records unresolved critical open gaps")

    packets_dir = run_dir / "workbench" / "scan-packets"
    checked.append(_relative(root, packets_dir))
    if not _directory_has_files(packets_dir):
        errors.append(".specify/project-cognition/workbench/scan-packets/ must contain at least one scan packet")

    return _result(
        gate="scan",
        ready_readiness="scan_ready",
        errors=errors,
        warnings=warnings,
        checked_paths=checked,
        details=details,
    )


def _sqlite_scalar(conn: sqlite3.Connection, query: str, params: tuple[object, ...] = ()) -> object:
    row = conn.execute(query, params).fetchone()
    if row is None:
        return None
    return row[0]


def validate_build_acceptance(project_root: Path) -> dict[str, object]:
    root = project_root.resolve()
    run_dir = cognition_dir(root)
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    details: dict[str, object] = {}

    status_path = run_dir / "status.json"
    checked.append(_relative(root, status_path))
    status_payload = _read_json_object(status_path, ".specify/project-cognition/status.json", errors)
    status = read_cognition_status(root)

    db_path = cognition_db_path(root)
    checked.append(_relative(root, db_path))
    if not db_path.exists() or not db_path.is_file():
        errors.append(".specify/project-cognition/project-cognition.db must exist")
        return _result(
            gate="build",
            ready_readiness="query_ready",
            errors=errors,
            warnings=warnings,
            checked_paths=checked,
            details=details,
        )
    if db_path.stat().st_size == 0:
        errors.append(".specify/project-cognition/project-cognition.db must not be empty")
        return _result(
            gate="build",
            ready_readiness="query_ready",
            errors=errors,
            warnings=warnings,
            checked_paths=checked,
            details=details,
        )

    try:
        with closing(connect_cognition_db(root)) as conn:
            table_rows = conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')").fetchall()
            tables = {str(row["name"]) for row in table_rows}
            missing_tables = sorted(REQUIRED_TABLES - tables)
            if missing_tables:
                errors.append(f"project-cognition.db is missing required table(s): {', '.join(missing_tables)}")

            schema_row = conn.execute("SELECT value_json FROM metadata WHERE key = 'schema_version'").fetchone()
            if schema_row is None:
                errors.append("project-cognition.db metadata.schema_version is missing")
            else:
                try:
                    schema_version = int(json.loads(str(schema_row["value_json"])))
                except (TypeError, ValueError, json.JSONDecodeError):
                    schema_version = -1
                details["schema_version"] = schema_version
                if schema_version != SCHEMA_VERSION:
                    errors.append(
                        f"project-cognition.db schema_version {schema_version} is not supported; expected {SCHEMA_VERSION}"
                    )

            active_rows = conn.execute(
                "SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC"
            ).fetchall()
            if not active_rows:
                errors.append("project-cognition.db must contain an active generation")
                active_generation_id = ""
            else:
                active_generation_id = str(active_rows[0]["id"])
                details["active_generation_id"] = active_generation_id
                if len(active_rows) > 1:
                    warnings.append("project-cognition.db contains multiple active generations; newest sequence is used")

            if active_generation_id:
                expected_generation_id = str(status_payload.get("active_generation_id") or status.active_generation_id or "")
                if expected_generation_id and expected_generation_id != active_generation_id:
                    errors.append(
                        f"status.json active_generation_id {expected_generation_id} does not match DB active generation {active_generation_id}"
                    )

                node_count = int(_sqlite_scalar(conn, "SELECT COUNT(*) FROM nodes WHERE generation_id = ?", (active_generation_id,)) or 0)
                path_count = int(_sqlite_scalar(conn, "SELECT COUNT(*) FROM path_index WHERE generation_id = ?", (active_generation_id,)) or 0)
                claim_count = int(_sqlite_scalar(conn, "SELECT COUNT(*) FROM claims WHERE generation_id = ?", (active_generation_id,)) or 0)
                details["node_count"] = node_count
                details["path_index_count"] = path_count
                details["claim_count"] = claim_count
                if node_count == 0:
                    errors.append("active generation must contain at least one node")
                if path_count == 0:
                    errors.append("active generation must contain at least one path_index row")
                if claim_count == 0:
                    warnings.append("active generation contains no claims")
    except sqlite3.DatabaseError as exc:
        errors.append(f"project-cognition.db must be readable SQLite: {exc}")
        return _result(
            gate="build",
            ready_readiness="query_ready",
            errors=errors,
            warnings=warnings,
            checked_paths=checked,
            details=details,
        )

    if status_payload and not status.graph_ready:
        errors.append("status.json graph_ready must be true")
    if status_payload:
        graph_store_path = str(status_payload.get("graph_store_path") or status.graph_store_path or "")
        if graph_store_path and graph_store_path.replace("\\", "/") != ".specify/project-cognition/project-cognition.db":
            errors.append("status.json graph_store_path must point to .specify/project-cognition/project-cognition.db")
        if not graph_store_path:
            errors.append("status.json graph_store_path must be set")

    if not errors:
        smoke = query_project_cognition(root, intent="implement", query_text="login", paths=[])
        details["smoke_query_readiness"] = smoke.get("readiness")
        if smoke.get("readiness") == "needs_rebuild":
            errors.append("project-cognition query smoke check returned needs_rebuild")

    return _result(
        gate="build",
        ready_readiness="query_ready",
        errors=errors,
        warnings=warnings,
        checked_paths=checked,
        details=details,
    )
```

- [ ] **Step 2: Export the helpers**

Modify `src/specify_cli/cognition/__init__.py`:

```python
from .validation import validate_build_acceptance, validate_scan_acceptance
```

Add these names to `__all__`:

```python
"validate_build_acceptance",
"validate_scan_acceptance",
```

- [ ] **Step 3: Run validation unit tests**

Run:

```bash
pytest tests/test_project_cognition_validation.py -q
```

Expected: PASS.

- [ ] **Step 4: Run existing cognition tests**

Run:

```bash
pytest tests/test_project_cognition_db.py tests/test_project_cognition_query.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit validation module**

```bash
git add src/specify_cli/cognition/validation.py src/specify_cli/cognition/__init__.py tests/test_project_cognition_validation.py
git commit -m "feat: add project cognition acceptance validators"
```

Expected: commit succeeds.

---

### Task 3: Add CLI Gates And Harden Refresh Finalizers

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add failing CLI tests**

In `tests/integrations/test_cli.py`, add imports near the top if not already present:

```python
from specify_cli.cognition import (
    CognitionStatus,
    connect_cognition_db,
    ensure_cognition_db,
    seed_active_generation,
    write_cognition_status,
)
```

Add helper near existing project cognition tests:

```python
def _seed_cli_query_ready_runtime(project: Path) -> None:
    generation_id = seed_active_generation(project, source_commit="abc123")
    with closing(connect_cognition_db(project)) as conn:
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
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login', ?, 'login', 'login', 'capability', 'capability:auth.login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO claims(id, generation_id, subject_ref, predicate, object_ref, object_value, truth_layer, confidence, status, last_validated_at, attrs_json) "
            "VALUES ('claim:login', ?, 'capability:auth.login', 'implemented_by', 'src/auth/login.ts', '', 'implementation_reality', 'strong', 'active', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.commit()
    write_cognition_status(
        project,
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
```

If `closing` is not imported in this file, add:

```python
from contextlib import closing
```

Add tests:

```python
def test_project_cognition_validate_build_blocks_empty_runtime(tmp_path):
    project = tmp_path / "project-cognition-validate-build-empty"
    project.mkdir()
    (project / ".specify").mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["project-cognition", "validate-build", "--format", "json"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["gate"] == "build"
    assert any("project-cognition.db" in message for message in payload["errors"])


def test_project_cognition_validate_build_accepts_query_ready_runtime(tmp_path):
    project = tmp_path / "project-cognition-validate-build-ready"
    project.mkdir()
    (project / ".specify").mkdir()
    _seed_cli_query_ready_runtime(project)
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["project-cognition", "validate-build", "--format", "json"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["readiness"] == "query_ready"


def test_project_cognition_complete_refresh_blocks_without_query_ready_runtime(tmp_path):
    project = tmp_path / "project-cognition-complete-refresh-blocked"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        init_result = runner.invoke(
            app,
            ["init", "--here", "--ai", "claude", "--script", "sh", "--no-git", "--ignore-agent-tools"],
            catch_exceptions=False,
        )
        _create_git_head(project)
        complete_result = runner.invoke(
            app,
            ["project-cognition", "complete-refresh", "--format", "json"],
            catch_exceptions=False,
        )
        status_result = runner.invoke(app, ["project-cognition", "status", "--format", "json"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert init_result.exit_code == 0, init_result.output
    assert complete_result.exit_code == 0, complete_result.output
    complete_payload = json.loads(complete_result.output)
    status_payload = json.loads(status_result.output)
    assert complete_payload["status"] == "blocked"
    assert complete_payload["freshness"] == "partial_refresh"
    assert status_payload["freshness"] != "fresh"
```

Update existing `test_project_cognition_complete_refresh_records_map_build_reason_without_project_map_outputs` so it seeds a query-ready runtime before invoking `complete-refresh`:

```python
_seed_cli_query_ready_runtime(project)
```

Expected assertions stay:

```python
assert complete_payload["freshness"] == "fresh"
assert status_payload["last_refresh_reason"] == "map-build"
```

- [ ] **Step 2: Run the targeted tests and verify failure**

Run:

```bash
pytest tests/integrations/test_cli.py -q -k "project_cognition_validate_build or complete_refresh"
```

Expected: FAIL because `validate-build` command does not exist and `complete-refresh` still writes fresh.

- [ ] **Step 3: Import validators in CLI**

Modify the import from `specify_cli.cognition` in `src/specify_cli/__init__.py`:

```python
from specify_cli.cognition import (
    apply_cognition_update,
    cognition_db_path,
    cognition_status_path,
    query_project_cognition,
    validate_build_acceptance,
    validate_scan_acceptance,
)
```

- [ ] **Step 4: Add CLI commands**

After `project_map_status_command`, add:

```python
@project_cognition_app.command("validate-scan")
def project_cognition_validate_scan_command(
    output_format: str = typer.Option("json", "--format", help="Output format: json or text"),
):
    """Validate that map-scan produced a buildable project cognition scan package."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = validate_scan_acceptance(project_root)
    if output_format.lower() == "json":
        print_json(payload, indent=2)
        return
    console.print(_cli_panel(json.dumps(payload, indent=2), title="Project Cognition Scan Acceptance", border_style="cyan"))


@project_cognition_app.command("validate-build")
def project_cognition_validate_build_command(
    output_format: str = typer.Option("json", "--format", help="Output format: json or text"),
):
    """Validate that map-build published a query-ready project cognition runtime."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = validate_build_acceptance(project_root)
    if output_format.lower() == "json":
        print_json(payload, indent=2)
        return
    console.print(_cli_panel(json.dumps(payload, indent=2), title="Project Cognition Build Acceptance", border_style="cyan"))
```

- [ ] **Step 5: Harden complete-refresh and record-refresh**

Replace `project_map_record_refresh` body after `_require_spec_kit_plus_project(project_root)` with:

```python
    build_acceptance = validate_build_acceptance(project_root)
    if build_acceptance["status"] != "ok":
        mark_project_map_refreshed(
            project_root,
            head_commit=git_head_commit(project_root),
            branch=git_branch_name(project_root),
            reason=reason,
        )
        mark_project_map_dirty(
            project_root,
            "project cognition refresh recorded but build acceptance did not pass",
        )
        result = inspect_project_cognition_freshness(project_root)
        result["freshness"] = "partial_refresh"
        result["state"] = "partial_refresh"
        result["readiness"] = "blocked"
        result["recommended_next_action"] = "run_map_scan_build"
        result["validation"] = build_acceptance
        if output_format.lower() == "json":
            print_json(result, indent=2)
            return
        _render_project_map_freshness(result)
        return
```

Keep the existing `mark_project_map_refreshed(...)` success path after this block.

Replace `project_map_complete_refresh` body after `_require_spec_kit_plus_project(project_root)` with:

```python
    build_acceptance = validate_build_acceptance(project_root)
    if build_acceptance["status"] != "ok":
        result = inspect_project_cognition_freshness(project_root)
        result["status"] = "blocked"
        result["freshness"] = "partial_refresh"
        result["state"] = "partial_refresh"
        result["readiness"] = "blocked"
        result["recommended_next_action"] = "run_map_scan_build"
        result["validation"] = build_acceptance
        if output_format.lower() == "json":
            print_json(result, indent=2)
            return
        console.print(_cli_panel(json.dumps(result, indent=2), title="Project Cognition Complete Refresh Blocked", border_style="red"))
        return
```

Keep the existing success path after this block:

```python
complete_project_map_refresh(project_root)
result = inspect_project_cognition_freshness(project_root)
```

- [ ] **Step 6: Improve query missing DB reason**

In `project_cognition_query_command`, replace the DB-missing payload's `missing_coverage` value:

```python
"missing_coverage": [
    ".specify/project-cognition/project-cognition.db is missing; run sp-map-scan followed by sp-map-build"
],
```

- [ ] **Step 7: Run targeted CLI tests**

Run:

```bash
pytest tests/integrations/test_cli.py -q -k "project_cognition_validate_build or complete_refresh or query_outputs_json_for_empty_runtime"
```

Expected: PASS. If `test_project_cognition_query_outputs_json_for_empty_runtime` still expects the old generic message, update it to assert `"project-cognition.db is missing"` appears.

- [ ] **Step 8: Commit CLI changes**

```bash
git add src/specify_cli/__init__.py tests/integrations/test_cli.py
git commit -m "feat: expose project cognition acceptance gates"
```

Expected: commit succeeds.

---

### Task 4: Reuse Acceptance Gates From Hooks And Artifact Validation

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `src/specify_cli/hooks/project_cognition.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Update hook test helpers to create real SQLite DBs**

In `tests/contract/test_hook_cli_surface.py`, add imports:

```python
from specify_cli.cognition import (
    CognitionStatus,
    connect_cognition_db,
    seed_active_generation,
    write_cognition_status,
)
```

Replace `_write_project_cognition_runtime` with:

```python
def _write_project_cognition_runtime(run_dir: Path) -> None:
    project_root = run_dir.parents[1]
    run_dir.mkdir(parents=True, exist_ok=True)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
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
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login', ?, 'login', 'login', 'capability', 'capability:auth.login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO claims(id, generation_id, subject_ref, predicate, object_ref, object_value, truth_layer, confidence, status, last_validated_at, attrs_json) "
            "VALUES ('claim:login', ?, 'capability:auth.login', 'implemented_by', 'src/auth/login.ts', '', 'implementation_reality', 'strong', 'active', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.commit()
    write_cognition_status(
        project_root,
        CognitionStatus(
            version=3,
            baseline_state="ready",
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id=generation_id,
            query_contract_version=1,
            update_contract_version=1,
            freshness="fresh",
            last_update_id="UPD-001",
        ),
    )
```

Add:

```python
from contextlib import closing
```

if it is not already imported.

- [ ] **Step 2: Add failing hook artifact tests**

Add tests near map-build artifact validation tests:

```python
def test_hook_validate_artifacts_blocks_map_build_when_database_has_no_active_generation(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    run_dir.mkdir(parents=True, exist_ok=True)
    ensure_cognition_db(project)
    write_cognition_status(
        project,
        CognitionStatus(
            version=3,
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
        ),
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("active generation" in message for message in payload["errors"])
```

Add a complete-refresh hook blocked test near existing complete-refresh hook tests:

```python
def test_hook_complete_refresh_blocks_when_build_acceptance_fails(tmp_path: Path):
    project = _create_project(tmp_path)
    _create_git_head(project)

    result = _invoke_in_project(
        project,
        ["hook", "complete-refresh", "--format", "json"],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("project-cognition.db" in message for message in payload["errors"])
```

If `ensure_cognition_db` is not imported, add it to the cognition imports.

- [ ] **Step 3: Run hook tests and verify failure**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -q -k "map_build or map_update or complete_refresh"
```

Expected: FAIL because marker DB assumptions and hook finalizer have not been updated yet.

- [ ] **Step 4: Reuse validators in artifact validation**

In `src/specify_cli/hooks/artifact_validation.py`, add imports:

```python
from specify_cli.cognition import validate_build_acceptance, validate_scan_acceptance
```

Replace `_validate_map_scan_artifacts` with:

```python
def _validate_map_scan_artifacts(feature_dir: Path) -> list[str]:
    project_root = feature_dir.parents[1] if feature_dir.name == "project-cognition" else feature_dir.parent
    result = validate_scan_acceptance(project_root)
    return [str(message) for message in result["errors"]]
```

Replace `_validate_map_build_artifacts` with:

```python
def _validate_map_build_artifacts(feature_dir: Path) -> list[str]:
    project_root = feature_dir.parents[1] if feature_dir.name == "project-cognition" else feature_dir.parent
    result = validate_build_acceptance(project_root)
    return [str(message) for message in result["errors"]]
```

Keep `_validate_map_update_artifacts` but let it call the new `_validate_map_build_artifacts`. Leave the `last_update_id` / `freshness` metadata check in place.

- [ ] **Step 5: Harden hook complete-refresh**

In `src/specify_cli/hooks/project_cognition.py`, import:

```python
from specify_cli.cognition import validate_build_acceptance
```

In `complete_refresh_hook`, after the git baseline check and before `complete_project_map_refresh(project_root)`, add:

```python
    build_acceptance = validate_build_acceptance(project_root)
    if build_acceptance["status"] != "ok":
        return HookResult(
            event=PROJECT_COGNITION_COMPLETE_REFRESH,
            status="blocked",
            severity="critical",
            errors=[str(message) for message in build_acceptance["errors"]],
            data={"validation": build_acceptance},
        )
```

- [ ] **Step 6: Run hook tests**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py -q -k "map_scan or map_build or map_update or complete_refresh"
```

Expected: PASS. If old tests that overwrite `project-cognition.db` with marker bytes still fail, update those tests to expect blocked for unreadable SQLite, or avoid overwriting the real DB except in tests specifically checking corruption.

- [ ] **Step 7: Commit hook validation changes**

```bash
git add src/specify_cli/hooks/artifact_validation.py src/specify_cli/hooks/project_cognition.py tests/contract/test_hook_cli_surface.py
git commit -m "fix: enforce cognition acceptance in hooks"
```

Expected: commit succeeds.

---

### Task 5: Update Workflow Templates And Docs

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/map-update.md`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Add failing template assertions**

In `tests/test_map_scan_build_template_guidance.py`, add assertions to `test_map_scan_template_defines_complete_scan_package_contract`:

```python
assert "project-cognition validate-scan --format json" in content
assert "validate-scan" in lowered
assert "may report complete only after" in lowered
```

Add assertions to `test_map_build_template_refuses_incomplete_scan_packages`:

```python
assert "project-cognition validate-build --format json" in content
assert "validate-build" in lowered
assert "complete-refresh" in content
assert "only after `validate-build`" in lowered or "only after validate-build" in lowered
```

In `tests/test_map_runtime_template_guidance.py`, add to `test_map_update_template_exists_and_is_incremental`:

```python
assert "project-cognition validate-build --format json" in content
assert "must not call" in content.lower()
assert "needs_rebuild" in content
assert "complete-refresh" in content
```

- [ ] **Step 2: Run template tests and verify failure**

Run:

```bash
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py -q
```

Expected: FAIL because templates do not yet mention the new validation commands.

- [ ] **Step 3: Update map-scan template**

In `templates/commands/map-scan.md`, add under `## Completion Rule` or before final reporting:

```markdown
- Run `{{specify-subcmd:project-cognition validate-scan --format json}}` before handoff to `sp-map-build`.
- `sp-map-scan` may report complete only after `validate-scan` returns `status=ok` and `readiness=scan_ready`.
- If `validate-scan` returns `status=blocked`, report the blocking errors and do not claim the scan package is build-ready.
```

- [ ] **Step 4: Update map-build template**

In `templates/commands/map-build.md`, replace the completion bullets around `complete-refresh` with:

```markdown
- run `{{specify-subcmd:project-cognition validate-build --format json}}` after publishing `.specify/project-cognition/project-cognition.db`
- use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only after `validate-build` returns `status=ok` and `readiness=query_ready`
- confirm that `.specify/project-cognition/project-cognition.db` was written and can be queried through `{{specify-subcmd:project-cognition query --intent implement --query "$ARGUMENTS" --format json}}`
- if `validate-build` returns `status=blocked`, report the specific DB, schema, active generation, status, or smoke-query error and do not mark the baseline fresh
```

- [ ] **Step 5: Update map-update template**

In `templates/commands/map-update.md`, add under `## Incremental Rule`:

```markdown
- After applying update records, run `{{specify-subcmd:project-cognition validate-build --format json}}`.
- If the update helper returns `needs_rebuild`, `sp-map-update` must not call `complete-refresh`; report that the baseline is unusable and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- If `validate-build` is blocked after update recording, report `partial_refresh` and preserve the validation errors instead of claiming the runtime is fresh.
```

- [ ] **Step 6: Update lifecycle docs**

In `README.md`, `docs/quickstart.md`, and `PROJECT-HANDBOOK.md`, add or adjust the brownfield cognition paragraph to include:

```markdown
For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build`. That pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. After that, normal code changes should use `sp-map-update` for bounded incremental refresh. Return to `sp-map-scan -> sp-map-build` only when the baseline is missing, unusable, schema-incompatible, or the changed closure cannot be bounded safely.
```

- [ ] **Step 7: Run template/docs tests**

Run:

```bash
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_command_surface_semantics.py -q
```

Expected: PASS. If docs tests assert older wording, update them to accept the new acceptance-gate language while preserving existing no-project-map runtime assertions.

- [ ] **Step 8: Commit template/docs changes**

```bash
git add templates/commands/map-scan.md templates/commands/map-build.md templates/commands/map-update.md README.md docs/quickstart.md PROJECT-HANDBOOK.md tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_command_surface_semantics.py
git commit -m "docs: require cognition acceptance gates in workflows"
```

Expected: commit succeeds.

---

### Task 6: Final Regression And Cleanup

**Files:**
- Verify only; modify any tests or imports revealed by full regression failures.

- [ ] **Step 1: Run focused cognition and hook regression**

Run:

```bash
pytest tests/test_project_cognition_validation.py tests/test_project_cognition_db.py tests/test_project_cognition_query.py tests/integrations/test_cli.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 2: Run template regression**

Run:

```bash
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_command_surface_semantics.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 3: Run import/type smoke**

Run:

```bash
python -m compileall src/specify_cli
```

Expected: PASS with no syntax errors.

- [ ] **Step 4: Search for stale false-fresh guidance**

Run:

```bash
rg -n "record-refresh.*fresh|complete-refresh.*recording a fresh|status.*fresh.*query|map-build.*database exists" src templates tests README.md docs PROJECT-HANDBOOK.md
```

Expected: No guidance remains that says DB existence alone is enough for build completion. Any hits should either be test names for blocked behavior or explicit acceptance-gate wording.

- [ ] **Step 5: Check git diff**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional modified files if earlier tasks were not committed.

- [ ] **Step 6: Commit any final cleanup**

If Step 1-5 required small follow-up edits:

```bash
git add <changed-files>
git commit -m "test: cover cognition acceptance gate regressions"
```

Expected: commit succeeds or no changes remain.

---

## Self-Review

Spec coverage:

- First `sp-map-scan -> sp-map-build` baseline is covered by Tasks 1, 2, 5.
- Fast later `sp-map-update` maintenance is covered by Tasks 4 and 5.
- `complete-refresh` cannot false-mark fresh is covered by Tasks 3 and 4.
- Hook/artifact validation reuse is covered by Task 4.
- User-facing lifecycle guidance is covered by Task 5.
- Regression coverage and smoke checks are covered by Task 6.

No placeholders remain. Function names are consistent across tasks:
`validate_scan_acceptance`, `validate_build_acceptance`, `project-cognition validate-scan`, and `project-cognition validate-build`.
