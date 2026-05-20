"""Acceptance gates for project cognition scan and SQLite build outputs."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

from .db import QUERY_CONTRACT_VERSION, SCHEMA_VERSION, UPDATE_CONTRACT_VERSION
from .lexicon import _project_cognition_lexicon_payload
from .paths import cognition_db_path, cognition_dir
from .query import _query_plan_payload, _query_project_cognition_payload
from specify_cli.scan_freshness import cognition_ignored_paths


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
ACCEPTED_COVERAGE_STATES = {"accepted", "complete", "covered", "excluded", "low_risk_open_gap"}
BLOCKING_CRITICALITIES = {"critical", "important"}
LOW_RISK_CRITICALITIES = {"low-risk", "low_risk"}
REQUIRED_LOW_RISK_GAP_FIELDS = ("owner", "reason", "evidence_expectation", "revisit_condition")
REQUIRED_SUBAGENT_BLOCKED_FIELDS = (
    "reason",
    "lane_id",
    "packet_id",
    "blocked_scope",
    "criticality",
    "owner",
    "status",
    "recovery_condition",
)


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


def _is_specify_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().replace("\\", "/")
    return normalized == ".specify" or normalized.startswith(".specify/")


def _collect_specify_paths(value: Any, *, parent_key: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in {
                "path",
                "paths",
                "source_path",
                "target_path",
                "file",
                "files",
                "source",
                "target",
                "object_ref",
                "subject_ref",
            }:
                matches.extend(_collect_specify_paths(item, parent_key=key_text))
            elif isinstance(item, (dict, list)):
                matches.extend(_collect_specify_paths(item, parent_key=key_text))
    elif isinstance(value, list):
        for item in value:
            matches.extend(_collect_specify_paths(item, parent_key=parent_key))
    elif _is_specify_path(value) and parent_key:
        matches.append(str(value).strip().replace("\\", "/"))
    return matches


def _collect_graph_paths(value: Any, *, parent_key: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in {
                "path",
                "paths",
                "source_path",
                "target_path",
                "file",
                "files",
                "source",
                "target",
                "object_ref",
                "subject_ref",
                "test_path",
            }:
                matches.extend(_collect_graph_paths(item, parent_key=key_text))
            elif isinstance(item, (dict, list)):
                matches.extend(_collect_graph_paths(item, parent_key=key_text))
    elif isinstance(value, list):
        for item in value:
            matches.extend(_collect_graph_paths(item, parent_key=parent_key))
    elif isinstance(value, str) and parent_key:
        normalized = value.strip().replace("\\", "/").strip("/")
        if normalized:
            matches.append(normalized)
    return matches


def _reject_specify_graph_paths(payload: dict[str, Any], label: str, errors: list[str]) -> None:
    paths = sorted(set(_collect_specify_paths(payload)))
    if paths:
        errors.append(
            f"{label} contains .specify/** paths: {', '.join(paths)}; "
            ".specify/** must not enter project cognition graph evidence"
        )


def _reject_cognitionignored_graph_paths(
    project_root: Path,
    payload: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    ignored = sorted(set(cognition_ignored_paths(project_root, _collect_graph_paths(payload))))
    if ignored:
        errors.append(
            f"{label} contains paths excluded by .cognitionignore: {', '.join(ignored)}; "
            ".cognitionignore paths must not enter project cognition graph evidence"
        )


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
    else:
        _reject_specify_evidence_file_paths(evidence_path, root, errors, checked_paths)

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
            _reject_specify_graph_paths(payload, label, errors)
            _reject_cognitionignored_graph_paths(root, payload, label, errors)
            rows = _require_list(payload, key, label, errors)
            details[f"{key}_count"] = len(rows)

    coverage_path = run_dir / "coverage.json"
    checked_paths.append(_relative(root, coverage_path))
    coverage = _read_json_object(coverage_path, ".specify/project-cognition/coverage.json", errors)
    if coverage:
        _reject_specify_graph_paths(coverage, ".specify/project-cognition/coverage.json", errors)
        _reject_cognitionignored_graph_paths(root, coverage, ".specify/project-cognition/coverage.json", errors)
        rows = _require_non_empty_list(coverage, "rows", ".specify/project-cognition/coverage.json", errors)
        details["coverage_rows"] = len(rows)

    _validate_coverage_ledger(
        root,
        run_dir,
        required=True,
        checked_paths=checked_paths,
        warnings=warnings,
        errors=errors,
        details=details,
    )

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


def _reject_specify_evidence_file_paths(
    evidence_path: Path,
    root: Path,
    errors: list[str],
    checked_paths: list[str],
) -> None:
    for evidence_file in sorted(path for path in evidence_path.rglob("*") if path.is_file()):
        checked_paths.append(_relative(root, evidence_file))
        try:
            payload = json.loads(evidence_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            _reject_specify_graph_paths(payload, _relative(root, evidence_file), errors)
            _reject_cognitionignored_graph_paths(root, payload, _relative(root, evidence_file), errors)


def _check_unresolved_scan_gaps(
    rows: list[Any],
    ledger: dict[str, Any],
    warnings: list[str],
    errors: list[str],
) -> None:
    unresolved_blocking_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("criticality", "")).lower() in BLOCKING_CRITICALITIES
        and str(row.get("coverage_state", row.get("state", ""))).lower() not in ACCEPTED_COVERAGE_STATES
    ]
    if unresolved_blocking_rows:
        errors.append("coverage-ledger.json has unresolved critical or important rows")

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

        reason = str(gap.get("reason", "")).strip().lower()
        status = str(gap.get("status", "")).strip().lower()
        if reason == "subagent_blocked" or status == "blocked":
            missing = [
                field
                for field in REQUIRED_SUBAGENT_BLOCKED_FIELDS
                if field != "blocked_scope" and not str(gap.get(field, "")).strip()
            ]
            blocked_scope = gap.get("blocked_scope")
            if not (
                isinstance(blocked_scope, list)
                and blocked_scope
                and all(isinstance(scope, str) and scope.strip() for scope in blocked_scope)
            ):
                missing.append("blocked_scope (must be a non-empty list of non-empty strings)")
            if missing:
                errors.append(
                    f"coverage-ledger.json subagent_blocked open gap {index} is missing "
                    f"required metadata: {', '.join(missing)}"
                )
            else:
                errors.append("coverage-ledger.json has subagent_blocked open gaps")
            continue

        criticality = str(gap.get("criticality", "")).strip().lower()
        if criticality not in BLOCKING_CRITICALITIES | LOW_RISK_CRITICALITIES:
            errors.append(f"coverage-ledger.json open gap {index} has missing or unknown criticality")
            continue

        if criticality in BLOCKING_CRITICALITIES:
            errors.append("coverage-ledger.json has unresolved critical or important open gaps")
            continue

        missing_metadata = [
            field
            for field in REQUIRED_LOW_RISK_GAP_FIELDS
            if not str(gap.get(field, "")).strip()
        ]
        if missing_metadata:
            errors.append(
                f"coverage-ledger.json low-risk open gap {index} is missing "
                f"required metadata: {', '.join(missing_metadata)}"
            )
            continue

        valid_noncritical_count += 1

    if valid_noncritical_count:
        warnings.append("coverage-ledger.json records non-critical open gaps")


def _validate_coverage_ledger(
    root: Path,
    run_dir: Path,
    *,
    required: bool,
    checked_paths: list[str],
    warnings: list[str],
    errors: list[str],
    details: dict[str, object],
) -> None:
    ledger_path = run_dir / "workbench" / "coverage-ledger.json"
    if not required and not ledger_path.exists():
        return

    checked_paths.append(_relative(root, ledger_path))
    ledger = _read_json_object(ledger_path, ".specify/project-cognition/workbench/coverage-ledger.json", errors)
    if not ledger:
        return

    _reject_specify_graph_paths(ledger, ".specify/project-cognition/workbench/coverage-ledger.json", errors)
    _reject_cognitionignored_graph_paths(
        root,
        ledger,
        ".specify/project-cognition/workbench/coverage-ledger.json",
        errors,
    )
    rows = _require_non_empty_list(
        ledger,
        "rows",
        ".specify/project-cognition/workbench/coverage-ledger.json",
        errors,
    )
    details["ledger_rows"] = len(rows)
    _validate_coverage_ledger_rows(rows, errors)
    _check_unresolved_scan_gaps(rows, ledger, warnings, errors)


def _validate_coverage_ledger_rows(rows: list[Any], errors: list[str]) -> None:
    known_criticalities = BLOCKING_CRITICALITIES | LOW_RISK_CRITICALITIES
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"coverage-ledger.json ledger row {index} must be an object")
            continue

        criticality = str(row.get("criticality", "")).strip().lower()
        if criticality not in known_criticalities:
            errors.append(f"coverage-ledger.json ledger row {index} has missing or unknown criticality")

        coverage_state = str(row.get("coverage_state", row.get("state", ""))).strip().lower()
        if not coverage_state:
            errors.append(f"coverage-ledger.json ledger row {index} is missing coverage_state")


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
                _validate_runtime_metadata(conn, active_generation_id, errors, details)
            if active_generation_id:
                _validate_query_contract_v2_smoke(root, conn, active_generation_id, errors, details)
                _validate_generation_content(
                    conn,
                    active_generation_id,
                    minimal_baseline,
                    warnings,
                    errors,
                    details,
                )
                _validate_route_pack_source_rows(conn, active_generation_id, errors, details)
                _validate_query_examples(conn, active_generation_id, errors, details)
                _validate_no_specify_graph_store_paths(conn, active_generation_id, errors, details)
                _validate_no_cognitionignored_graph_store_paths(root, conn, active_generation_id, errors, details)
            if active_generation_id and not errors:
                _validate_readonly_smoke_query(conn, active_generation_id, minimal_baseline, errors, details)
    except sqlite3.Error as exc:
        errors.append(f".specify/project-cognition/project-cognition.db must open as SQLite: {exc}")
        active_generation_id = ""

    _validate_coverage_ledger(
        root,
        run_dir,
        required=False,
        checked_paths=checked_paths,
        warnings=warnings,
        errors=errors,
        details=details,
    )
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


def _validate_runtime_metadata(
    conn: sqlite3.Connection,
    active_generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    expected = {
        "baseline_state": "ready",
        "graph_ready": True,
        "graph_store_path": EXPECTED_GRAPH_STORE_PATH,
        "active_generation_id": active_generation_id,
        "query_contract_version": QUERY_CONTRACT_VERSION,
        "update_contract_version": UPDATE_CONTRACT_VERSION,
    }
    try:
        rows = conn.execute(
            "SELECT key, value_json FROM metadata WHERE key IN "
            "('baseline_state', 'graph_ready', 'graph_store_path', 'active_generation_id', "
            "'query_contract_version', 'update_contract_version')"
        ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"runtime metadata could not be read: {exc}")
        return

    actual: dict[str, object] = {}
    for row in rows:
        key = str(row["key"])
        value_json = str(row["value_json"])
        try:
            actual[key] = json.loads(value_json)
        except json.JSONDecodeError:
            actual[key] = value_json
    details["runtime_metadata"] = actual

    for key, expected_value in expected.items():
        if key not in actual:
            errors.append(f"metadata.{key} must exist")
            continue
        if actual[key] != expected_value:
            errors.append(f"metadata.{key} must equal {expected_value!r}")


def _validate_query_contract_v2_smoke(
    project_root: Path,
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    details["query_contract_version"] = QUERY_CONTRACT_VERSION
    details["query_contract_v2_fields"] = [
        "concept_candidates",
        "selected_concepts",
        "rejected_concepts",
        "selection_reason",
        "route_pack",
    ]
    lexicon = _project_cognition_lexicon_payload(
        conn,
        generation_id,
        intent="validation",
        query_text="",
        limit=1,
    )
    candidates = lexicon.get("concept_candidates")
    details["query_contract_v2_lexicon_smoke"] = bool(candidates)
    if not isinstance(candidates, list) or not candidates:
        errors.append("query contract v2 smoke requires project-cognition lexicon concept_candidates")
        return
    candidate = candidates[0]
    required_candidate_fields = {
        "concept_id",
        "label",
        "kind",
        "domain",
        "matched_terms",
        "aliases",
        "colloquial_matches",
        "target_nodes",
        "related_concepts",
        "disambiguation_hint",
        "confidence",
        "evidence_ids",
    }
    missing_candidate_fields = sorted(required_candidate_fields - set(candidate.keys()))
    if missing_candidate_fields:
        errors.append(
            "query contract v2 smoke concept_candidates missing fields: "
            + ", ".join(missing_candidate_fields)
        )
        return

    selected_concept = str(candidate["concept_id"])
    query_plan = _query_plan_payload(
        project_root=project_root,
        query_text=str(candidate["label"]),
        expanded_queries=list(candidate.get("matched_terms", []))[:3],
        paths=[],
        selected_concepts=[selected_concept],
        rejected_concepts=[],
        selection_reason="validation smoke",
    )
    query_payload = _query_project_cognition_payload(
        conn,
        generation_id,
        intent="validation",
        query_text=str(query_plan["raw_query"]),
        expanded_queries=list(query_plan["expanded_queries"]),
        query_plan=query_plan,
    )
    details["query_contract_v2_query_smoke_readiness"] = query_payload.get("readiness")
    for field in ("selected_concepts", "rejected_concepts", "selection_reason", "route_pack"):
        if field not in query_payload:
            errors.append(f"query contract v2 smoke query payload missing {field}")
            return
    if query_payload["selected_concepts"] != [selected_concept]:
        errors.append("query contract v2 smoke query payload must echo selected_concepts")
        return
    route_pack = query_payload.get("route_pack")
    if not isinstance(route_pack, dict):
        errors.append("query contract v2 smoke query payload route_pack must be an object")
        return
    route_items = route_pack.get("items")
    details["query_contract_v2_route_item_count"] = len(route_items) if isinstance(route_items, list) else 0
    if query_payload.get("readiness") == "ready" and not route_items:
        errors.append("query contract v2 smoke ready payload must include evidence-backed route_pack items")
        return
    if isinstance(route_items, list):
        for item in route_items:
            if not isinstance(item, dict):
                errors.append("query contract v2 smoke route_pack items must be objects")
                return
            missing_route_fields = [
                field
                for field in ("path", "relation", "reason", "evidence_ids", "confidence")
                if field not in item or not item[field]
            ]
            if not (item.get("node_id") or item.get("claim_id")):
                missing_route_fields.append("node_id or claim_id")
            if missing_route_fields:
                errors.append(
                    "query contract v2 smoke route_pack item missing fields: "
                    + ", ".join(missing_route_fields)
                )
                return


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


def _validate_route_pack_source_rows(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    invalid_rows: list[str] = []
    try:
        rows = conn.execute(
            "SELECT id, path, node_id, relation, confidence, evidence_id "
            "FROM path_index WHERE generation_id = ? AND ("
            "trim(path) = '' OR trim(node_id) = '' OR trim(relation) = '' OR "
            "trim(confidence) = '' OR trim(evidence_id) = ''"
            ") ORDER BY id LIMIT 10",
            (generation_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"route-pack source rows could not be validated: {exc}")
        return

    for row in rows:
        missing_fields = [
            field
            for field in ("path", "node_id", "relation", "confidence", "evidence_id")
            if not str(row[field]).strip()
        ]
        invalid_rows.append(f"path_index.{row['id']} missing {', '.join(missing_fields)}")

    invalid_rows.extend(_invalid_entrypoint_route_source_rows(conn, generation_id, errors))
    invalid_rows.extend(_invalid_test_route_source_rows(conn, generation_id, errors))
    details["route_pack_source_row_count"] = _count_generation_rows(conn, "path_index", generation_id)
    details["route_pack_entrypoint_row_count"] = _count_generation_rows(conn, "entrypoint_index", generation_id)
    details["route_pack_test_row_count"] = _count_generation_rows(conn, "test_index", generation_id)
    details["route_pack_source_row_offenders"] = invalid_rows
    if invalid_rows:
        errors.append(
            "route-pack source rows must have path, node or claim backing, relation, "
            f"confidence, and evidence_id: {', '.join(invalid_rows)}"
        )


def _invalid_entrypoint_route_source_rows(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
) -> list[str]:
    try:
        rows = conn.execute(
            "SELECT id, path, node_id, capability_id, entrypoint_type, confidence, evidence_id "
            "FROM entrypoint_index WHERE generation_id = ? AND ("
            "trim(path) = '' OR (trim(node_id) = '' AND trim(capability_id) = '') OR "
            "trim(entrypoint_type) = '' OR trim(confidence) = '' OR trim(evidence_id) = ''"
            ") ORDER BY id LIMIT 10",
            (generation_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"entrypoint route-pack source rows could not be validated: {exc}")
        return []

    invalid: list[str] = []
    for row in rows:
        missing_fields: list[str] = []
        if not str(row["path"]).strip():
            missing_fields.append("path")
        if not (str(row["node_id"]).strip() or str(row["capability_id"]).strip()):
            missing_fields.append("node_id or capability_id")
        if not str(row["entrypoint_type"]).strip():
            missing_fields.append("entrypoint_type")
        if not str(row["confidence"]).strip():
            missing_fields.append("confidence")
        if not str(row["evidence_id"]).strip():
            missing_fields.append("evidence_id")
        invalid.append(f"entrypoint_index.{row['id']} missing {', '.join(missing_fields)}")
    return invalid


def _invalid_test_route_source_rows(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
) -> list[str]:
    try:
        rows = conn.execute(
            "SELECT id, test_path, test_name, node_id, capability_id, confidence, evidence_id "
            "FROM test_index WHERE generation_id = ? AND ("
            "trim(test_path) = '' OR trim(test_name) = '' OR "
            "(trim(node_id) = '' AND trim(capability_id) = '') OR "
            "trim(confidence) = '' OR trim(evidence_id) = ''"
            ") ORDER BY id LIMIT 10",
            (generation_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"test route-pack source rows could not be validated: {exc}")
        return []

    invalid: list[str] = []
    for row in rows:
        missing_fields: list[str] = []
        if not str(row["test_path"]).strip():
            missing_fields.append("test_path")
        if not str(row["test_name"]).strip():
            missing_fields.append("test_name")
        if not (str(row["node_id"]).strip() or str(row["capability_id"]).strip()):
            missing_fields.append("node_id or capability_id")
        if not str(row["confidence"]).strip():
            missing_fields.append("confidence")
        if not str(row["evidence_id"]).strip():
            missing_fields.append("evidence_id")
        invalid.append(f"test_index.{row['id']} missing {', '.join(missing_fields)}")
    return invalid


def _validate_query_examples(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    try:
        rows = conn.execute(
            "SELECT id, expected_target_id FROM query_examples WHERE generation_id = ? ORDER BY id",
            (generation_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"query_examples could not be validated for evidence-backed target coverage: {exc}")
        return

    invalid_examples: list[str] = []
    for row in rows:
        target_id = str(row["expected_target_id"])
        if not _has_evidence_backed_target(conn, generation_id, target_id):
            invalid_examples.append(f"{row['id']}->{target_id}")

    details["query_examples_count"] = len(rows)
    details["query_examples_without_evidence_backed_target"] = invalid_examples
    if invalid_examples:
        errors.append(
            "query_examples expected_target_id must resolve to an evidence-backed target via "
            f"alias_index, path_index, or claims + claim_evidence: {', '.join(invalid_examples[:10])}"
        )


def _has_evidence_backed_target(conn: sqlite3.Connection, generation_id: str, target_id: str) -> bool:
    checks = (
        (
            "SELECT 1 FROM alias_index WHERE generation_id = ? AND target_id = ? "
            "AND trim(evidence_id) <> '' LIMIT 1",
            (generation_id, target_id),
        ),
        (
            "SELECT 1 FROM path_index WHERE generation_id = ? AND node_id = ? "
            "AND trim(evidence_id) <> '' LIMIT 1",
            (generation_id, target_id),
        ),
        (
            "SELECT 1 FROM node_evidence "
            "JOIN nodes ON nodes.id = node_evidence.node_id "
            "WHERE nodes.generation_id = ? AND node_evidence.node_id = ? "
            "AND trim(node_evidence.evidence_id) <> '' LIMIT 1",
            (generation_id, target_id),
        ),
        (
            "SELECT 1 FROM claims "
            "JOIN claim_evidence ON claim_evidence.claim_id = claims.id "
            "WHERE claims.generation_id = ? AND claims.id = ? "
            "AND trim(claim_evidence.evidence_id) <> '' LIMIT 1",
            (generation_id, target_id),
        ),
        (
            "SELECT 1 FROM claims "
            "JOIN claim_evidence ON claim_evidence.claim_id = claims.id "
            "WHERE claims.generation_id = ? AND claims.subject_ref = ? "
            "AND trim(claim_evidence.evidence_id) <> '' LIMIT 1",
            (generation_id, target_id),
        ),
    )
    for query, params in checks:
        if conn.execute(query, params).fetchone():
            return True
    return False


def _validate_no_specify_graph_store_paths(
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    checks = (
        ("evidence", "source_path"),
        ("path_index", "path"),
        ("symbol_index", "path"),
        ("entrypoint_index", "path"),
        ("test_index", "test_path"),
        ("claims", "subject_ref"),
        ("claims", "object_ref"),
        ("claims", "object_value"),
    )
    offenders: list[str] = []
    for table, column in checks:
        try:
            rows = conn.execute(
                f"SELECT {column} AS value FROM {table} WHERE generation_id = ? AND "
                f"({column} = '.specify' OR {column} LIKE '.specify/%') "
                f"ORDER BY {column} LIMIT 5",
                (generation_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            errors.append(f"{table}.{column} could not be checked for .specify/** paths: {exc}")
            continue
        for row in rows:
            offenders.append(f"{table}.{column}={row['value']}")

    details["specify_graph_store_path_offenders"] = offenders
    if offenders:
        errors.append(
            ".specify/** must not enter project cognition graph store; offending rows: "
            + ", ".join(offenders[:10])
        )


def _validate_no_cognitionignored_graph_store_paths(
    project_root: Path,
    conn: sqlite3.Connection,
    generation_id: str,
    errors: list[str],
    details: dict[str, object],
) -> None:
    checks = (
        ("evidence", "source_path"),
        ("path_index", "path"),
        ("symbol_index", "path"),
        ("entrypoint_index", "path"),
        ("test_index", "test_path"),
        ("claims", "object_ref"),
        ("claims", "object_value"),
    )
    candidates: list[str] = []
    for table, column in checks:
        try:
            rows = conn.execute(
                f"SELECT {column} AS value FROM {table} WHERE generation_id = ? "
                f"AND trim({column}) <> '' ORDER BY {column}",
                (generation_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            errors.append(f"{table}.{column} could not be checked against .cognitionignore: {exc}")
            continue
        candidates.extend(str(row["value"]) for row in rows)

    offenders = sorted(set(cognition_ignored_paths(project_root, candidates)))
    details["cognitionignored_graph_store_path_offenders"] = offenders
    if offenders:
        errors.append(
            ".cognitionignore paths must not enter project cognition graph store; offending rows: "
            + ", ".join(offenders[:10])
        )


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
    if status.get("query_contract_version") != QUERY_CONTRACT_VERSION:
        errors.append(
            ".specify/project-cognition/status.json query_contract_version must equal "
            f"{QUERY_CONTRACT_VERSION!r}"
        )
    if status.get("update_contract_version") != UPDATE_CONTRACT_VERSION:
        errors.append(
            ".specify/project-cognition/status.json update_contract_version must equal "
            f"{UPDATE_CONTRACT_VERSION!r}"
        )
    status_generation_id = str(status.get("active_generation_id", ""))
    if status_generation_id and active_generation_id and status_generation_id != active_generation_id:
        errors.append(
            ".specify/project-cognition/status.json active_generation_id "
            f"does not match database active generation {active_generation_id}"
        )
