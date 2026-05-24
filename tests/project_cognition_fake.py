"""Test helpers for Python surfaces that call the external project-cognition tool."""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path


def write_project_cognition_status(project_root: Path, **overrides: object) -> Path:
    status_path = project_root / ".specify" / "project-cognition" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "version": 3,
        "runtime_format": "project-cognition-go",
        "runtime_schema": 1,
        "freshness": "missing",
        "state": "missing_baseline",
        "readiness": "blocked",
        "recommended_next_action": "run_map_scan_build",
        "reasons": [],
        "dirty": False,
        "dirty_reasons": [],
        "last_refresh_reason": "seeded-test",
        "status_path": ".specify/project-cognition/status.json",
        "graph_store_path": ".specify/project-cognition/project-cognition.db",
        "graph_ready": False,
    }
    payload.update(overrides)
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return status_path


def write_fake_project_cognition_script(tmp_path: Path) -> Path:
    script = tmp_path / "project_cognition_fake.py"
    script.write_text(
        textwrap.dedent(
            r'''
            import json
            import sqlite3
            import sys
            from pathlib import Path


            RUNTIME_DEFAULT = {
                "runtime_format": "project-cognition-go",
                "runtime_schema": 1,
                "status_path": ".specify/project-cognition/status.json",
                "graph_store_path": ".specify/project-cognition/project-cognition.db",
            }


            def _runtime_dir():
                return Path.cwd() / ".specify" / "project-cognition"


            def _status_path():
                return _runtime_dir() / "status.json"


            def _db_path():
                return _runtime_dir() / "project-cognition.db"


            def _write_status(payload):
                payload = _normalize(payload)
                status_path = _status_path()
                status_path.parent.mkdir(parents=True, exist_ok=True)
                status_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
                return payload


            def _read_status():
                status_path = _status_path()
                if status_path.exists():
                    try:
                        payload = json.loads(status_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        payload = _default_status()
                        payload["reasons"] = ["project cognition status is malformed"]
                    if not isinstance(payload, dict):
                        payload = _default_status()
                        payload["reasons"] = ["status.json must contain a top-level JSON object"]
                else:
                    payload = _default_status()
                return _normalize(payload)


            def _default_status():
                payload = {
                    "version": 3,
                    "freshness": "missing",
                    "state": "missing_baseline",
                    "readiness": "blocked",
                    "recommended_next_action": "run_map_scan_build",
                    "reasons": ["project cognition status missing"],
                    "dirty": False,
                    "dirty_reasons": [],
                }
                payload.update(RUNTIME_DEFAULT)
                return payload


            def _normalize(payload):
                if not isinstance(payload, dict):
                    payload = _default_status()
                for key, value in RUNTIME_DEFAULT.items():
                    payload.setdefault(key, value)
                freshness = str(payload.get("freshness") or payload.get("baseline_state") or "missing").lower()
                state = str(payload.get("state") or "").lower()
                if not state:
                    if freshness == "fresh":
                        state = "fresh"
                    elif freshness in {"stale", "runtime_stale", "possibly_stale"}:
                        state = "runtime_stale"
                    elif freshness == "support_drift":
                        state = "support_drift"
                    elif freshness == "partial_refresh":
                        state = "partial_refresh"
                    else:
                        state = "missing_baseline"
                payload["state"] = state
                payload["freshness"] = freshness
                if "readiness" not in payload:
                    payload["readiness"] = "ready" if state == "fresh" else "blocked"
                if "recommended_next_action" not in payload:
                    payload["recommended_next_action"] = "none" if state == "fresh" else "run_map_scan_build"
                reasons = payload.get("reasons")
                if not isinstance(reasons, list):
                    reasons = []
                dirty_reasons = payload.get("dirty_reasons")
                if isinstance(dirty_reasons, list):
                    reasons.extend(str(item) for item in dirty_reasons if str(item).strip())
                if not reasons and state != "fresh":
                    reasons.append(f"project cognition {state}")
                payload["reasons"] = list(dict.fromkeys(str(item) for item in reasons if str(item).strip()))
                return payload


            def _flag_value(args, name, default=""):
                if name not in args:
                    return default
                index = args.index(name)
                if index + 1 >= len(args):
                    return default
                return args[index + 1]


            def _validate_scan():
                def _normalize_path(value):
                    normalized = str(value).replace("\\", "/").strip()
                    while normalized.startswith("./"):
                        normalized = normalized[2:].strip()
                    return normalized

                required = [
                    ".specify/project-cognition/evidence",
                    ".specify/project-cognition/status.json",
                    ".specify/project-cognition/provisional/nodes.json",
                    ".specify/project-cognition/provisional/edges.json",
                    ".specify/project-cognition/provisional/observations.json",
                    ".specify/project-cognition/coverage.json",
                    ".specify/project-cognition/workbench/coverage-ledger.json",
                    ".specify/project-cognition/workbench/scan-packets",
                ]
                root = Path.cwd()
                errors = [f"missing {rel}" for rel in required if not (root / rel).exists()]
                for rel in [
                    ".specify/project-cognition/status.json",
                    ".specify/project-cognition/provisional/nodes.json",
                    ".specify/project-cognition/provisional/edges.json",
                    ".specify/project-cognition/provisional/observations.json",
                    ".specify/project-cognition/coverage.json",
                    ".specify/project-cognition/workbench/coverage-ledger.json",
                ]:
                    path = root / rel
                    if path.exists():
                        try:
                            parsed = json.loads(path.read_text(encoding="utf-8"))
                            if rel.endswith("status.json") and not isinstance(parsed, dict):
                                errors.append("status.json must contain a top-level JSON object")
                        except json.JSONDecodeError as exc:
                            errors.append(f"{rel}: {exc}")
                coverage_path = Path.cwd() / ".specify/project-cognition/coverage.json"
                coverage_paths = set()
                if coverage_path.exists():
                    try:
                        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
                        rows = coverage.get("rows") if isinstance(coverage, dict) else None
                        if not isinstance(rows, list):
                            errors.append("coverage.json must define a top-level rows array")
                        else:
                            for row in rows:
                                if isinstance(row, dict):
                                    row_path = _normalize_path(row.get("path", ""))
                                    if row_path:
                                        coverage_paths.add(row_path)
                                    if row_path.startswith(".specify/"):
                                        errors.append(".specify/** must not enter project cognition graph evidence")
                                        break
                    except json.JSONDecodeError:
                        pass
                universe_rel = ".specify/project-cognition/workbench/repository-universe.json"
                universe_path = Path.cwd() / universe_rel
                if universe_path.exists():
                    try:
                        universe = json.loads(universe_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        errors.append(f"{universe_rel}: malformed JSON")
                    else:
                        if isinstance(universe, dict):
                            excluded_paths = set()
                            for item in universe.get("excluded_paths", []):
                                value = item.get("path") if isinstance(item, dict) else item
                                path = _normalize_path(value)
                                if path:
                                    excluded_paths.add(path)
                            for path in sorted(excluded_paths & coverage_paths):
                                errors.append(f"excluded path {path} must not appear in coverage.json")
                evidence_dir = Path.cwd() / ".specify/project-cognition/evidence"
                if evidence_dir.exists():
                    for evidence_path in evidence_dir.rglob("*.json"):
                        try:
                            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                        except json.JSONDecodeError:
                            continue
                        if isinstance(evidence, dict) and str(evidence.get("source_path", "")).replace("\\\\", "/").startswith(".specify/"):
                            errors.append(".specify/** must not enter project cognition graph evidence")
                            break
                ledger_path = Path.cwd() / ".specify/project-cognition/workbench/coverage-ledger.json"
                if ledger_path.exists():
                    try:
                        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                        rows = ledger.get("rows") if isinstance(ledger, dict) else None
                        if not isinstance(rows, list):
                            errors.append("coverage-ledger.json must define a top-level rows array")
                        for gap in ledger.get("open_gaps", []) if isinstance(ledger, dict) else []:
                            if isinstance(gap, dict) and (
                                gap.get("reason") == "subagent_blocked" or gap.get("status") == "blocked"
                            ):
                                errors.append("subagent_blocked coverage gap must be resolved before project cognition acceptance")
                                break
                    except json.JSONDecodeError as exc:
                        errors.append(f".specify/project-cognition/workbench/coverage-ledger.json: {exc}")
                return {
                    "status": "blocked" if errors else "ok",
                    "gate": "scan_acceptance",
                    "readiness": "blocked" if errors else "scan_ready",
                    "errors": errors,
                    "warnings": [],
                }


            def _validate_build():
                errors = []
                status_path = _status_path()
                db_path = _db_path()
                if not status_path.exists():
                    errors.append("missing .specify/project-cognition/status.json")
                else:
                    try:
                        raw = json.loads(status_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as exc:
                        raw = {}
                        errors.append(f"status.json: {exc}")
                    if not isinstance(raw, dict):
                        errors.append("status.json must contain a top-level JSON object")
                if not db_path.exists():
                    errors.append("missing .specify/project-cognition/project-cognition.db")
                elif db_path.stat().st_size == 0:
                    errors.append("project-cognition.db must not be empty")
                else:
                    try:
                        conn = sqlite3.connect(str(db_path))
                        try:
                            conn.execute("SELECT 1")
                            table_names = {
                                row[0]
                                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            }
                            required = {
                                "metadata",
                                "generations",
                                "evidence",
                                "observations",
                                "observation_evidence",
                                "nodes",
                                "node_evidence",
                                "edges",
                                "edge_evidence",
                                "claims",
                                "claim_evidence",
                                "conflicts",
                                "conflict_claims",
                                "path_index",
                                "symbol_index",
                                "alias_index",
                                "entrypoint_index",
                                "test_index",
                                "slice_members",
                                "query_examples",
                                "updates",
                            }
                            missing_tables = sorted(required - table_names)
                            if missing_tables:
                                errors.append(
                                    "project-cognition.db missing required query tables: "
                                    + ", ".join(missing_tables)
                                )
                            elif "metadata" not in table_names and "generations" not in table_names:
                                errors.append("project-cognition.db is not query ready")
                            active_generation_id = ""
                            if "generations" in table_names:
                                row = conn.execute(
                                    "SELECT id FROM generations WHERE state = 'active' ORDER BY id LIMIT 1"
                                ).fetchone()
                                if row:
                                    active_generation_id = str(row[0])
                                else:
                                    errors.append("project-cognition.db has no active generation")
                            if active_generation_id and "path_index" in table_names:
                                path_count = conn.execute(
                                    "SELECT COUNT(*) FROM path_index WHERE generation_id = ?",
                                    (active_generation_id,),
                                ).fetchone()[0]
                                if int(path_count) == 0:
                                    errors.append("active_generation_has_no_path_index_rows")
                            if active_generation_id and "nodes" in table_names:
                                node_count = conn.execute(
                                    "SELECT COUNT(*) FROM nodes WHERE generation_id = ?",
                                    (active_generation_id,),
                                ).fetchone()[0]
                                if int(node_count) == 0:
                                    errors.append("active generation has no nodes")
                            if active_generation_id and "evidence" in table_names:
                                evidence_count = conn.execute(
                                    "SELECT COUNT(*) FROM evidence WHERE generation_id = ?",
                                    (active_generation_id,),
                                ).fetchone()[0]
                                if int(evidence_count) == 0:
                                    errors.append("active generation has no evidence rows")
                            if "path_index" in table_names:
                                for row in conn.execute("SELECT path FROM path_index"):
                                    if str(row[0]).replace("\\\\", "/").startswith(".specify/"):
                                        errors.append(".specify/** must not enter project cognition graph store")
                                        break
                            if "evidence" in table_names:
                                for row in conn.execute("SELECT source_path FROM evidence WHERE source_path IS NOT NULL"):
                                    if str(row[0]).replace("\\\\", "/").startswith(".specify/"):
                                        errors.append(".specify/** must not enter project cognition graph store")
                                        break
                            if "symbol_index" in table_names:
                                for row in conn.execute("SELECT path FROM symbol_index"):
                                    if str(row[0]).replace("\\\\", "/").startswith(".specify/"):
                                        errors.append(".specify/** must not enter project cognition graph store")
                                        break
                            if "entrypoint_index" in table_names:
                                for row in conn.execute("SELECT path FROM entrypoint_index"):
                                    if str(row[0]).replace("\\\\", "/").startswith(".specify/"):
                                        errors.append(".specify/** must not enter project cognition graph store")
                                        break
                            if "test_index" in table_names:
                                for row in conn.execute("SELECT test_path FROM test_index"):
                                    if str(row[0]).replace("\\\\", "/").startswith(".specify/"):
                                        errors.append(".specify/** must not enter project cognition graph store")
                                        break
                        finally:
                            conn.close()
                    except sqlite3.Error as exc:
                        errors.append(f"project-cognition.db is not query ready: {exc}")
                ledger_path = Path.cwd() / ".specify/project-cognition/workbench/coverage-ledger.json"
                if ledger_path.exists():
                    try:
                        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                        for gap in ledger.get("open_gaps", []) if isinstance(ledger, dict) else []:
                            if isinstance(gap, dict) and (
                                gap.get("reason") == "subagent_blocked" or gap.get("status") == "blocked"
                            ):
                                errors.append("subagent_blocked coverage gap must be resolved before project cognition acceptance")
                                break
                    except json.JSONDecodeError as exc:
                        errors.append(f".specify/project-cognition/workbench/coverage-ledger.json: {exc}")
                return {
                    "status": "blocked" if errors else "ok",
                    "gate": "build_acceptance",
                    "readiness": "blocked" if errors else "query_ready",
                    "errors": errors,
                    "warnings": [],
                }


            def _record_refresh(args):
                reason = _flag_value(args, "--reason", "manual")
                payload = _read_status()
                payload["freshness"] = "partial_refresh"
                payload["state"] = "partial_refresh"
                payload["readiness"] = "blocked"
                payload["recommended_next_action"] = "run_map_scan_build"
                payload["last_refresh_reason"] = reason
                return _write_status(payload)


            def _complete_refresh():
                payload = _read_status()
                payload["status"] = "ok"
                payload["freshness"] = "fresh"
                payload["state"] = "fresh"
                payload["readiness"] = "query_ready"
                payload["recommended_next_action"] = "use_project_cognition"
                payload["dirty"] = False
                payload["dirty_reasons"] = []
                payload["last_refresh_reason"] = "map-build"
                return _write_status(payload)


            def _mark_dirty(args):
                reason = _flag_value(args, "--reason", "manual").replace(" ", "_")
                payload = _read_status()
                payload["status"] = "stale"
                payload["freshness"] = "stale"
                payload["state"] = "runtime_stale"
                payload["readiness"] = "blocked"
                payload["recommended_next_action"] = "run_map_update"
                payload["dirty"] = True
                payload["dirty_reasons"] = [reason]
                payload["reasons"] = [reason]
                payload["dirty_origin_command"] = _flag_value(args, "--origin-command")
                payload["dirty_origin_feature_dir"] = _flag_value(args, "--origin-feature-dir")
                payload["dirty_origin_lane_id"] = _flag_value(args, "--origin-lane-id")
                scopes = []
                for index, item in enumerate(args):
                    if item == "--scope" and index + 1 < len(args):
                        scopes.append(args[index + 1].replace("\\\\", "/"))
                payload["dirty_scope_paths"] = scopes
                return _write_status(payload)


            def main():
                command = sys.argv[1] if len(sys.argv) > 1 else "check"
                args = sys.argv[1:]
                if command == "validate-scan":
                    print(json.dumps(_validate_scan()))
                    return 0
                if command == "validate-build":
                    print(json.dumps(_validate_build()))
                    return 0
                if command == "record-refresh":
                    print(json.dumps(_record_refresh(args)))
                    return 0
                if command == "complete-refresh":
                    print(json.dumps(_complete_refresh()))
                    return 0
                if command == "mark-dirty":
                    print(json.dumps(_mark_dirty(args)))
                    return 0
                if command in {"check", "status", "doctor"}:
                    print(json.dumps(_read_status()))
                    return 0
                print(json.dumps({"status": "ok", "command": command}))
                return 0


            raise SystemExit(main())
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    return script


def project_cognition_bin_value(script: Path) -> str:
    return f"{sys.executable}{os.pathsep}{script}"


def install_fake_project_cognition(monkeypatch, tmp_path: Path) -> Path:
    script = write_fake_project_cognition_script(tmp_path)
    monkeypatch.setenv("PROJECT_COGNITION_BIN", project_cognition_bin_value(script))
    return script
