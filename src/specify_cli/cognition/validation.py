"""Acceptance gates for project cognition scan and SQLite build outputs."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

from .db import SCHEMA_VERSION
from .paths import cognition_db_path, cognition_dir


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

EXPECTED_GRAPH_STORE_PATH = ".specify/project-cognition/project-cognition.db"


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


def _require_list(payload: dict[str, Any], key: str, label: str, errors: list[str]) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        errors.append(f"{label} must define a top-level {key} array")
        return []
    return value


def _require_non_empty_list(payload: dict[str, Any], key: str, label: str, errors: list[str]) -> list[Any]:
    value = _require_list(payload, key, label, errors)
    if not value:
        errors.append(f"{label} must define a non-empty {key} array")
    return value


def _directory_has_files(path: Path) -> bool:
    return path.exists() and path.is_dir() and any(child.is_file() for child in path.iterdir())


def validate_scan_acceptance(project_root: Path) -> dict[str, object]:
    """Validate that map-scan produced a buildable project cognition package."""

    root = project_root.resolve()
    run_dir = cognition_dir(root)
    errors: list[str] = []
    warnings: list[str] = []
    checked_paths: list[str] = []
    details: dict[str, object] = {}

    status_path = run_dir / "status.json"
    checked_paths.append(_relative(root, status_path))
    _read_json_object(status_path, ".specify/project-cognition/status.json", errors)

    evidence_path = run_dir / "evidence"
    checked_paths.append(_relative(root, evidence_path))
    if not _directory_has_files(evidence_path):
        errors.append(".specify/project-cognition/evidence/ must exist and contain at least one file")

    for relative_path, key in (
        ("provisional/nodes.json", "nodes"),
        ("provisional/edges.json", "edges"),
        ("provisional/observations.json", "observations"),
    ):
        path = run_dir / relative_path
        label = f".specify/project-cognition/{relative_path}"
        checked_paths.append(_relative(root, path))
        payload = _read_json_object(path, label, errors)
        if payload:
            rows = _require_list(payload, key, label, errors)
            details[f"{key}_count"] = len(rows)

    coverage_path = run_dir / "coverage.json"
    checked_paths.append(_relative(root, coverage_path))
    coverage = _read_json_object(coverage_path, ".specify/project-cognition/coverage.json", errors)
    if coverage:
        rows = _require_non_empty_list(coverage, "rows", ".specify/project-cognition/coverage.json", errors)
        details["coverage_rows"] = len(rows)

    ledger_path = run_dir / "workbench" / "coverage-ledger.json"
    checked_paths.append(_relative(root, ledger_path))
    ledger = _read_json_object(ledger_path, ".specify/project-cognition/workbench/coverage-ledger.json", errors)
    if ledger:
        rows = _require_non_empty_list(
            ledger,
            "rows",
            ".specify/project-cognition/workbench/coverage-ledger.json",
            errors,
        )
        details["ledger_rows"] = len(rows)
        _check_unresolved_scan_gaps(rows, ledger, warnings, errors)

    packets_path = run_dir / "workbench" / "scan-packets"
    checked_paths.append(_relative(root, packets_path))
    if not _directory_has_files(packets_path):
        errors.append(".specify/project-cognition/workbench/scan-packets/ must exist and contain at least one file")

    return _result(
        gate="scan",
        ready_readiness="scan_ready",
        errors=errors,
        warnings=warnings,
        checked_paths=checked_paths,
        details=details,
    )


def _check_unresolved_scan_gaps(
    rows: list[Any],
    ledger: dict[str, Any],
    warnings: list[str],
    errors: list[str],
) -> None:
    unresolved_critical_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("criticality", "")).lower() == "critical"
        and str(row.get("coverage_state", row.get("state", ""))).lower() not in {"accepted", "complete", "covered"}
    ]
    if unresolved_critical_rows:
        errors.append("coverage-ledger.json has unresolved critical rows")

    if "open_gaps" not in ledger:
        return

    open_gaps = ledger["open_gaps"]
    if not isinstance(open_gaps, list):
        errors.append("coverage-ledger.json open_gaps must be an array")
        return

    valid_noncritical_count = 0
    for index, gap in enumerate(open_gaps, start=1):
        if not isinstance(gap, dict):
            errors.append(f"coverage-ledger.json open gap {index} must be an object")
            continue

        criticality = str(gap.get("criticality", "")).strip().lower()
        if criticality not in {"critical", "important", "low-risk"}:
            errors.append(f"coverage-ledger.json open gap {index} has missing or unknown criticality")
            continue

        if criticality == "critical":
            errors.append("coverage-ledger.json has unresolved critical open gaps")
            continue

        missing_metadata = [
            field
            for field in ("owner", "reason")
            if not str(gap.get(field, "")).strip()
        ]
        if not (str(gap.get("revisit_condition", "")).strip() or str(gap.get("revisit", "")).strip()):
            missing_metadata.append("revisit_condition")
        if missing_metadata:
            errors.append(
                f"coverage-ledger.json non-critical open gap {index} is missing "
                f"required metadata: {', '.join(missing_metadata)}"
            )
            continue

        valid_noncritical_count += 1

    if valid_noncritical_count:
        warnings.append("coverage-ledger.json records non-critical open gaps")


def validate_build_acceptance(project_root: Path) -> dict[str, object]:
    """Validate that map-build published a query-ready project cognition runtime."""

    root = project_root.resolve()
    run_dir = cognition_dir(root)
    errors: list[str] = []
    warnings: list[str] = []
    checked_paths: list[str] = []
    details: dict[str, object] = {}

    status_path = run_dir / "status.json"
    checked_paths.append(_relative(root, status_path))
    status_payload = _read_json_object(status_path, ".specify/project-cognition/status.json", errors)
    minimal_baseline = status_payload.get("minimal_baseline") is True

    db_path = cognition_db_path(root)
    checked_paths.append(_relative(root, db_path))
    if not db_path.exists() or not db_path.is_file():
        errors.append(".specify/project-cognition/project-cognition.db must exist")
        return _result(
            gate="build",
            ready_readiness="query_ready",
            errors=errors,
            warnings=warnings,
            checked_paths=checked_paths,
            details=details,
        )
    if db_path.stat().st_size == 0:
        errors.append(".specify/project-cognition/project-cognition.db must not be empty")
        return _result(
            gate="build",
            ready_readiness="query_ready",
            errors=errors,
            warnings=warnings,
            checked_paths=checked_paths,
            details=details,
        )

    try:
        with closing(_connect_readonly_cognition_db(db_path)) as conn:
            _validate_db_schema(conn, errors, details)
            active_generation_id = _validate_active_generation(conn, warnings, errors, details)
            if active_generation_id:
                _validate_generation_content(
                    conn,
                    active_generation_id,
                    minimal_baseline,
                    warnings,
                    errors,
                    details,
                )
            if active_generation_id and not errors:
                _validate_readonly_smoke_query(conn, active_generation_id, minimal_baseline, errors, details)
    except sqlite3.Error as exc:
        errors.append(f".specify/project-cognition/project-cognition.db must open as SQLite: {exc}")
        active_generation_id = ""

    _validate_status(status_payload, active_generation_id, errors)

    return _result(
        gate="build",
        ready_readiness="query_ready",
        errors=errors,
        warnings=warnings,
        checked_paths=checked_paths,
        details=details,
    )


def _connect_readonly_cognition_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_db_schema(conn: sqlite3.Connection, errors: list[str], details: dict[str, object]) -> None:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    tables = {str(row["name"]) for row in rows}
    details["tables"] = sorted(tables)

    missing_tables = sorted(REQUIRED_TABLES - tables)
    if missing_tables:
        errors.append(f"project-cognition.db is missing required tables: {', '.join(missing_tables)}")

    try:
        row = conn.execute("SELECT value_json FROM metadata WHERE key = 'schema_version'").fetchone()
    except sqlite3.Error as exc:
        errors.append(f"metadata.schema_version could not be read: {exc}")
        return
    if row is None:
        errors.append("metadata.schema_version must exist")
        return

    try:
        schema_version = json.loads(str(row["value_json"]))
    except json.JSONDecodeError:
        errors.append("metadata.schema_version must be valid JSON")
        return

    details["schema_version"] = schema_version
    if schema_version != SCHEMA_VERSION:
        errors.append(f"metadata.schema_version must equal {SCHEMA_VERSION}")


def _validate_active_generation(
    conn: sqlite3.Connection,
    warnings: list[str],
    errors: list[str],
    details: dict[str, object],
) -> str:
    try:
        rows = conn.execute(
            "SELECT id, sequence FROM generations WHERE state = 'active' ORDER BY sequence DESC"
        ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"active generation could not be read: {exc}")
        return ""

    if not rows:
        errors.append("project-cognition.db must have an active generation")
        return ""

    if len(rows) > 1:
        warnings.append("project-cognition.db has multiple active generations; using newest sequence")

    generation_id = str(rows[0]["id"])
    details["active_generation_id"] = generation_id
    details["active_generation_sequence"] = int(rows[0]["sequence"])
    return generation_id


def _validate_generation_content(
    conn: sqlite3.Connection,
    generation_id: str,
    minimal_baseline: bool,
    warnings: list[str],
    errors: list[str],
    details: dict[str, object],
) -> None:
    node_count = _count_generation_rows(conn, "nodes", generation_id)
    path_count = _count_generation_rows(conn, "path_index", generation_id)
    claim_count = _count_generation_rows(conn, "claims", generation_id)
    details["node_count"] = node_count
    details["path_index_count"] = path_count
    details["claim_count"] = claim_count

    if node_count < 1:
        errors.append("active generation must have at least one node")
    if path_count < 1:
        errors.append("active generation must have at least one path_index row")
    if claim_count < 1:
        if minimal_baseline:
            warnings.append("active generation has no claims because status.json declares a minimal baseline")
        else:
            errors.append("active generation must contain at least one claim or an explicit minimal-baseline marker")


def _validate_readonly_smoke_query(
    conn: sqlite3.Connection,
    generation_id: str,
    minimal_baseline: bool,
    errors: list[str],
    details: dict[str, object],
) -> None:
    if minimal_baseline:
        details["smoke_query_readiness"] = "ready"
        details["smoke_query_signal"] = "minimal_baseline"
        return

    alias_count = _count_generation_rows(conn, "alias_index", generation_id)
    claim_fts_count = _count_claim_fts_rows(conn, generation_id)
    details["smoke_alias_count"] = alias_count
    details["smoke_claim_fts_count"] = claim_fts_count
    if alias_count > 0 or claim_fts_count > 0:
        details["smoke_query_readiness"] = "ready"
        details["smoke_query_signal"] = "alias_index" if alias_count > 0 else "claim_fts"
        return

    details["smoke_query_readiness"] = "needs_rebuild"
    errors.append("read-only smoke query readiness probe found no alias_index rows or claim_fts active-claim signal")


def _count_claim_fts_rows(conn: sqlite3.Connection, generation_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM claim_fts "
        "JOIN claims ON claims.id = claim_fts.claim_id "
        "WHERE claims.generation_id = ? AND claims.status = 'active'",
        (generation_id,),
    ).fetchone()
    return int(row["count"]) if row else 0


def _count_generation_rows(
    conn: sqlite3.Connection,
    table: str,
    generation_id: str,
    extra_where: str = "",
) -> int:
    where_clause = f"generation_id = ? AND {extra_where}" if extra_where else "generation_id = ?"
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE {where_clause}", (generation_id,)).fetchone()
    return int(row["count"]) if row else 0


def _validate_status(status: dict[str, Any], active_generation_id: str, errors: list[str]) -> None:
    if status.get("graph_ready") is not True:
        errors.append(".specify/project-cognition/status.json graph_ready must be true")
    if status.get("graph_store_path") != EXPECTED_GRAPH_STORE_PATH:
        errors.append(
            ".specify/project-cognition/status.json graph_store_path must be "
            f"{EXPECTED_GRAPH_STORE_PATH}"
        )
    status_generation_id = str(status.get("active_generation_id", ""))
    if status_generation_id and active_generation_id and status_generation_id != active_generation_id:
        errors.append(
            ".specify/project-cognition/status.json active_generation_id "
            f"does not match database active generation {active_generation_id}"
        )
