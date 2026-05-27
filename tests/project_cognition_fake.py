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
            VALID_PACKET_ACCEPTANCE = {"pass", "fail_gap", "fail_quality", "fail_contract", "fail_systemic"}
            FAILED_PACKET_ACCEPTANCE = {"fail_gap", "fail_quality", "fail_contract", "fail_systemic"}
            VALID_PACKET_OUTCOME = {"read", "deep_read", "sampled", "inventory_only", "blocked", "excluded", "overflow"}


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


            def _normalize_path(value):
                normalized = str(value).replace("\\", "/").strip()
                while normalized.startswith("./"):
                    normalized = normalized[2:].strip()
                return normalized


            def _normalize_path_field(value, label, errors):
                if value is None:
                    return ""
                if not isinstance(value, str):
                    errors.append(f"{label} must be a string")
                    return ""
                return _normalize_path(value)


            def _path_values(items, label="", errors=None):
                paths = set()
                if not isinstance(items, list):
                    return paths
                for index, item in enumerate(items):
                    value = item.get("path") if isinstance(item, dict) else item
                    if errors is not None and not isinstance(value, str):
                        field_label = f"{label}[{index}] path" if label else f"paths[{index}] path"
                        errors.append(f"{field_label} must be a string")
                        continue
                    path = _normalize_path(value)
                    if path:
                        paths.add(path)
                return paths


            def _array_rows_for_keys(raw, *keys):
                if isinstance(raw, list):
                    return [row for row in raw if isinstance(row, dict)]
                if not isinstance(raw, dict):
                    return []
                for key in keys:
                    value = raw.get(key)
                    if isinstance(value, list):
                        return [row for row in value if isinstance(row, dict)]
                return []


            def _canonical_worker_result_path(result_file_name):
                return ".specify/project-cognition/workbench/worker-results/" + result_file_name


            def _worker_result_path_matches(path, result_file_name):
                normalized = _normalize_path(path)
                return normalized in {
                    _canonical_worker_result_path(result_file_name),
                    "workbench/worker-results/" + result_file_name,
                }


            def _worker_result_id_from_path(path):
                normalized = _normalize_path(path)
                for prefix in (
                    ".specify/project-cognition/workbench/worker-results/",
                    "workbench/worker-results/",
                ):
                    if normalized.startswith(prefix) and normalized.endswith(".json"):
                        return normalized.removeprefix(prefix).removesuffix(".json")
                return ""


            def _packet_ledger_accounts_for_path(ledger, path):
                if not isinstance(ledger, dict):
                    return False
                for state in ("done", "blocked", "overflow"):
                    if path in _path_values(ledger.get(state)):
                        return True
                return False


            def _validate_packet_ledger(packet_id, assigned_paths, ledger, errors):
                if not isinstance(ledger, dict):
                    errors.append(f"packet {packet_id} must define ledger object")
                    return
                accounted = {}
                for state in ("todo", "doing", "done", "blocked", "overflow"):
                    rows = ledger.get(state)
                    if not isinstance(rows, list):
                        errors.append(f"packet {packet_id} ledger.{state} must be an array")
                        continue
                    for path in _path_values(rows, f"packet {packet_id} ledger.{state}", errors):
                        if path not in assigned_paths:
                            errors.append(f"packet {packet_id} ledger path {path} is not in assigned_paths")
                        previous = accounted.get(path)
                        if previous:
                            errors.append(f"packet {packet_id} ledger path {path} appears in both {previous} and {state}")
                        accounted[path] = state
                for path in sorted(assigned_paths):
                    if path not in accounted:
                        errors.append(f"packet {packet_id} assigned path {path} is missing from packet-local ledger")


            def _universe_criticality(universe):
                if not isinstance(universe, dict):
                    return {}
                criticality = universe.get("criticality")
                if isinstance(criticality, dict):
                    return {
                        _normalize_path(path): str(value).strip().lower()
                        for path, value in criticality.items()
                        if _normalize_path(path)
                    }
                by_path = {}
                for row in universe.get("candidate_universe", []):
                    if not isinstance(row, dict):
                        continue
                    path = _normalize_path(row.get("path", ""))
                    if path:
                        by_path[path] = str(row.get("criticality") or "").strip().lower()
                return by_path


            def _accepted_nonblocking_gap_paths(ledger, criticality_by_path):
                if not isinstance(ledger, dict):
                    return set()
                accepted = set()
                for gap in ledger.get("open_gaps", []):
                    if not isinstance(gap, dict):
                        continue
                    status = str(gap.get("status") or "").strip().lower()
                    coverage_state = str(gap.get("coverage_state") or "").strip().lower()
                    reason = str(gap.get("reason") or "").strip().lower()
                    if "blocked" in {status, coverage_state, reason}:
                        continue
                    if status != "low_risk_open_gap" and coverage_state != "low_risk_open_gap":
                        continue
                    if (
                        not str(gap.get("owner") or "").strip()
                        or not reason
                        or not str(gap.get("evidence_expectation") or "").strip()
                        or not str(gap.get("revisit_condition") or "").strip()
                    ):
                        continue
                    paths = _path_values(gap.get("paths"))
                    path = _normalize_path(gap.get("path", ""))
                    if path:
                        paths.add(path)
                    accepted.update(path for path in paths if criticality_by_path.get(path) == "low_risk")
                return accepted


            def _open_coverage_gap_paths(ledger):
                if not isinstance(ledger, dict):
                    return set()
                open_paths = set()
                for gap in ledger.get("open_gaps", []):
                    if not isinstance(gap, dict):
                        continue
                    paths = _path_values(gap.get("paths"))
                    path = _normalize_path(gap.get("path", ""))
                    if path:
                        paths.add(path)
                    blocked_scope = _path_values(gap.get("blocked_scope"))
                    open_paths.update(paths)
                    open_paths.update(blocked_scope)
                return open_paths


            def _queue_row_has_child_continuation(packet_id, queue_row, queue_rows):
                child_ids = set()
                for field in ("child_packet_ids", "children", "continuation_packet_ids", "split_packet_ids"):
                    value = queue_row.get(field)
                    if isinstance(value, list):
                        for item in value:
                            child_id = _normalize_path(item.get("packet_id", "") if isinstance(item, dict) else item)
                            if child_id:
                                child_ids.add(child_id)
                continuation = _normalize_path(queue_row.get("continuation_packet_id", ""))
                if continuation:
                    child_ids.add(continuation)
                if any(child_id in queue_rows for child_id in child_ids):
                    return True
                for candidate_id, candidate in queue_rows.items():
                    if candidate_id == packet_id or not isinstance(candidate, dict):
                        continue
                    if _normalize_path(candidate.get("parent_packet_id", "")) == packet_id:
                        return True
                    parent_ids = set()
                    value = candidate.get("parent_packet_ids")
                    if isinstance(value, list):
                        parent_ids = {
                            _normalize_path(item.get("packet_id", "") if isinstance(item, dict) else item)
                            for item in value
                        }
                    if packet_id in parent_ids:
                        return True
                return False


            def _validate_scan():
                required = [
                    ".specify/project-cognition/evidence",
                    ".specify/project-cognition/status.json",
                    ".specify/project-cognition/provisional/nodes.json",
                    ".specify/project-cognition/provisional/edges.json",
                    ".specify/project-cognition/provisional/observations.json",
                    ".specify/project-cognition/coverage.json",
                    ".specify/project-cognition/workbench/coverage-ledger.json",
                    ".specify/project-cognition/workbench/scan-queue.json",
                    ".specify/project-cognition/workbench/handoff-ledger.json",
                    ".specify/project-cognition/workbench/scan-packets",
                    ".specify/project-cognition/workbench/worker-results",
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
                    ".specify/project-cognition/workbench/scan-queue.json",
                    ".specify/project-cognition/workbench/handoff-ledger.json",
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
                        rows = []
                        found_rows = False
                        if isinstance(coverage, list):
                            rows = coverage
                            found_rows = True
                        elif isinstance(coverage, dict):
                            for key in ("rows", "coverage"):
                                value = coverage.get(key)
                                if isinstance(value, list):
                                    rows.extend(value)
                                    found_rows = True
                        if not found_rows:
                            errors.append("coverage.json must define a top-level rows or coverage array")
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
                            excluded_paths = _path_values(universe.get("excluded_paths", []))
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
                open_coverage_gap_paths = set()
                if ledger_path.exists():
                    try:
                        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                        open_coverage_gap_paths = _open_coverage_gap_paths(ledger)
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
                scan_packet_ids = set()
                scan_packets_dir = Path.cwd() / ".specify/project-cognition/workbench/scan-packets"
                if scan_packets_dir.is_dir():
                    scan_packet_ids = {path.stem for path in scan_packets_dir.glob("*.md")}
                queue_rows = {}
                queue_path = Path.cwd() / ".specify/project-cognition/workbench/scan-queue.json"
                if queue_path.exists():
                    try:
                        queue = json.loads(queue_path.read_text(encoding="utf-8"))
                        for index, row in enumerate(_array_rows_for_keys(queue, "packets", "rows", "queue")):
                            packet_id = _normalize_path(row.get("packet_id", ""))
                            if not packet_id:
                                errors.append(f"scan-queue.json rows[{index}] is missing packet_id")
                                continue
                            if packet_id in queue_rows:
                                errors.append(f"scan-queue.json packet_id {packet_id} appears more than once")
                                continue
                            queue_rows[packet_id] = row
                    except json.JSONDecodeError:
                        pass
                returned_packets = set()
                return_paths_by_packet = {}
                expected_queue_results = {}
                expected_handoff_results = {}
                handoff_path = Path.cwd() / ".specify/project-cognition/workbench/handoff-ledger.json"
                if handoff_path.exists():
                    try:
                        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
                        return_counts = {}
                        for index, event in enumerate(_array_rows_for_keys(handoff, "events", "rows", "handoffs")):
                            packet_id = _normalize_path(event.get("packet_id", ""))
                            if not packet_id:
                                errors.append(f"handoff-ledger.json events[{index}] is missing packet_id")
                                continue
                            event_type = _normalize_path(event.get("event_type", ""))
                            if event_type in {"returned", "return"}:
                                returned_packets.add(packet_id)
                                return_counts[packet_id] = return_counts.get(packet_id, 0) + 1
                                if return_counts[packet_id] > 1:
                                    errors.append(f"handoff-ledger packet {packet_id} has duplicate return events")
                                result_file_name = packet_id + ".json"
                                worker_result_path = _normalize_path_field(
                                    event.get("worker_result_path", ""),
                                    f"handoff-ledger return for packet {packet_id} worker_result_path",
                                    errors,
                                )
                                result_handoff_path = _normalize_path_field(
                                    event.get("result_handoff_path", ""),
                                    f"handoff-ledger return for packet {packet_id} result_handoff_path",
                                    errors,
                                )
                                if not worker_result_path and not result_handoff_path:
                                    errors.append(
                                        f"handoff-ledger return for packet {packet_id} worker_result_path must match "
                                        f"{_canonical_worker_result_path(result_file_name)}"
                                    )
                                for field, path_value in (
                                    ("worker_result_path", worker_result_path),
                                    ("result_handoff_path", result_handoff_path),
                                ):
                                    if path_value and not _worker_result_path_matches(path_value, result_file_name):
                                        errors.append(
                                            f"handoff-ledger return for packet {packet_id} {field} must match "
                                            f"{_canonical_worker_result_path(result_file_name)}"
                                        )
                                if worker_result_path:
                                    return_paths_by_packet[packet_id] = worker_result_path
                                    result_id = _worker_result_id_from_path(worker_result_path)
                                    if result_id:
                                        expected_handoff_results[result_id] = (
                                            packet_id,
                                            "worker_result_path",
                                            worker_result_path,
                                        )
                                elif result_handoff_path:
                                    return_paths_by_packet[packet_id] = result_handoff_path
                                    result_id = _worker_result_id_from_path(result_handoff_path)
                                    if result_id:
                                        expected_handoff_results[result_id] = (
                                            packet_id,
                                            "result_handoff_path",
                                            result_handoff_path,
                                        )
                    except json.JSONDecodeError:
                        pass
                for packet_id, queue_row in sorted(queue_rows.items()):
                    state = str(queue_row.get("state") or queue_row.get("status") or "").strip().lower()
                    result_handoff_path = _normalize_path_field(
                        queue_row.get("result_handoff_path", ""),
                        f"scan-queue packet {packet_id} result_handoff_path",
                        errors,
                    )
                    if result_handoff_path:
                        result_id = _worker_result_id_from_path(result_handoff_path)
                        if result_id:
                            expected_queue_results[result_id] = (packet_id, result_handoff_path)
                    assigned_paths = _path_values(queue_row.get("assigned_paths"), f"scan-queue packet {packet_id} assigned_paths", errors)
                    if state not in {"overflow", "blocked", "repack_required"}:
                        continue
                    has_open_gap = bool(assigned_paths & open_coverage_gap_paths)
                    if not has_open_gap and not _queue_row_has_child_continuation(packet_id, queue_row, queue_rows):
                        errors.append(
                            f"scan-queue packet {packet_id} state {state} must have an open coverage gap or child continuation packet"
                        )
                worker_results_dir = Path.cwd() / ".specify/project-cognition/workbench/worker-results"
                actual_worker_result_ids = set()
                if worker_results_dir.is_dir():
                    for result_path in sorted(worker_results_dir.glob("*.json")):
                        actual_worker_result_ids.add(result_path.stem)
                        try:
                            result_payload = json.loads(result_path.read_text(encoding="utf-8"))
                        except json.JSONDecodeError as exc:
                            errors.append(f"{result_path.name}: {exc}")
                            continue
                        if not isinstance(result_payload, dict):
                            errors.append(f"{result_path.name} must contain a top-level JSON object")
                            continue
                        packet_id = _normalize_path(result_payload.get("packet_id", "")) or result_path.stem
                        if packet_id != result_path.stem:
                            errors.append(
                                f"worker result {result_path.name} packet_id {packet_id} must match file stem {result_path.stem}"
                            )
                        if scan_packet_ids and packet_id not in scan_packet_ids:
                            errors.append(f"worker result {result_path.name} has no matching scan packet")
                        queue_row = queue_rows.get(packet_id)
                        if not isinstance(queue_row, dict):
                            errors.append(f"worker result {packet_id} has no matching scan-queue row")
                        else:
                            queue_assigned = _path_values(queue_row.get("assigned_paths"), f"scan-queue packet {packet_id} assigned_paths", errors)
                            worker_assigned = _path_values(result_payload.get("assigned_paths"), f"worker result {packet_id} assigned_paths", errors)
                            if queue_assigned != worker_assigned:
                                errors.append(
                                    f"scan-queue packet {packet_id} assigned_paths must match worker result assigned_paths"
                                )
                            result_handoff_path = _normalize_path_field(
                                queue_row.get("result_handoff_path", ""),
                                f"scan-queue packet {packet_id} result_handoff_path",
                                errors,
                            )
                            if not result_handoff_path or not _worker_result_path_matches(result_handoff_path, result_path.name):
                                errors.append(
                                    f"scan-queue packet {packet_id} result_handoff_path must match "
                                    f"{_canonical_worker_result_path(result_path.name)}"
                                )
                        if packet_id not in returned_packets:
                            errors.append(f"worker result {packet_id} has no matching return event in handoff-ledger.json")
                        else:
                            return_path = return_paths_by_packet.get(packet_id, "")
                            if not return_path or not _worker_result_path_matches(return_path, result_path.name):
                                errors.append(
                                    f"handoff-ledger return for packet {packet_id} worker_result_path must match "
                                    f"{_canonical_worker_result_path(result_path.name)}"
                                )
                        assigned_paths = _path_values(result_payload.get("assigned_paths"), f"worker result {packet_id} assigned_paths", errors)
                        if not assigned_paths:
                            errors.append(f"packet {packet_id} must define assigned_paths")
                        paths_read = _path_values(result_payload.get("paths_read"), f"worker result {packet_id} paths_read", errors)
                        ledger = result_payload.get("ledger")
                        _validate_packet_ledger(packet_id, assigned_paths, ledger, errors)
                        acceptance = str(result_payload.get("acceptance") or result_payload.get("outcome") or "").strip()
                        if not acceptance:
                            errors.append(f"packet {packet_id} must define acceptance")
                        elif acceptance not in VALID_PACKET_ACCEPTANCE:
                            errors.append(f"packet {packet_id} has invalid acceptance {acceptance}")
                        elif acceptance in FAILED_PACKET_ACCEPTANCE:
                            errors.append(
                                f"packet {packet_id} failed acceptance/coverage gate with {acceptance}"
                            )
                        coverage_rows = result_payload.get("coverage")
                        coverage_by_path = {}
                        if isinstance(coverage_rows, list):
                            for row_index, row in enumerate(coverage_rows):
                                if not isinstance(row, dict):
                                    continue
                                path = _normalize_path_field(
                                    row.get("path", ""),
                                    f"packet {packet_id} coverage[{row_index}].path",
                                    errors,
                                )
                                if path and path not in assigned_paths:
                                    errors.append(f"packet {packet_id} coverage path {path} is not in assigned_paths")
                                outcome = str(row.get("outcome") or "").strip()
                                if not outcome:
                                    errors.append(f"packet {packet_id} path {path} coverage outcome is required")
                                elif outcome not in VALID_PACKET_OUTCOME:
                                    errors.append(
                                        f"packet {packet_id} path {path} has invalid coverage outcome {outcome}"
                                    )
                                elif outcome in {"read", "deep_read"}:
                                    evidence_ids = [str(item).strip() for item in row.get("evidence_ids", []) if str(item).strip()] if isinstance(row.get("evidence_ids"), list) else []
                                    if not evidence_ids:
                                        errors.append(f"packet {packet_id} path {path} read outcome must include evidence_ids")
                                if path:
                                    coverage_by_path[path] = row
                        else:
                            errors.append(f"packet {packet_id} must define coverage array")
                        for path in sorted(assigned_paths):
                            if path not in coverage_by_path and not _packet_ledger_accounts_for_path(ledger, path):
                                errors.append(f"packet {packet_id} assigned path {path} has no declared final outcome")
                        for path in sorted(paths_read):
                            if path not in assigned_paths:
                                errors.append(f"packet {packet_id} paths_read path {path} is not in assigned_paths")
                        if acceptance == "pass":
                            if not paths_read:
                                errors.append(f"packet {packet_id} pass acceptance must include non-empty paths_read")
                            if not str(result_payload.get("confidence") or result_payload.get("confidence_level") or "").strip():
                                errors.append(f"packet {packet_id} pass acceptance must include confidence")
                            for path in sorted(assigned_paths):
                                row = coverage_by_path.get(path)
                                outcome = str(row.get("outcome") or "").strip() if isinstance(row, dict) else ""
                                if outcome in {"", "blocked", "overflow", "excluded"}:
                                    errors.append(f"packet {packet_id} cannot pass with unresolved path {path}")
                for result_id, (packet_id, result_path) in sorted(expected_queue_results.items()):
                    if result_id not in actual_worker_result_ids:
                        errors.append(
                            f"scan-queue packet {packet_id} result_handoff_path references missing worker result {result_path}"
                        )
                for result_id, (packet_id, field, result_path) in sorted(expected_handoff_results.items()):
                    if result_id not in actual_worker_result_ids:
                        errors.append(
                            f"handoff-ledger return for packet {packet_id} {field} references missing worker result {result_path}"
                        )
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
                                universe_path = Path.cwd() / ".specify/project-cognition/workbench/repository-universe.json"
                                if universe_path.exists():
                                    try:
                                        universe = json.loads(universe_path.read_text(encoding="utf-8"))
                                    except json.JSONDecodeError as exc:
                                        errors.append(f".specify/project-cognition/workbench/repository-universe.json: {exc}")
                                    else:
                                        included_paths = _path_values(
                                            universe.get("included_paths", []) if isinstance(universe, dict) else []
                                        )
                                        criticality_by_path = _universe_criticality(universe)
                                        ledger_path = (
                                            Path.cwd()
                                            / ".specify/project-cognition/workbench/coverage-ledger.json"
                                        )
                                        accepted_gap_paths = set()
                                        if ledger_path.exists():
                                            try:
                                                accepted_gap_paths = _accepted_nonblocking_gap_paths(
                                                    json.loads(ledger_path.read_text(encoding="utf-8")),
                                                    criticality_by_path,
                                                )
                                            except json.JSONDecodeError:
                                                accepted_gap_paths = set()
                                        required_paths = included_paths - accepted_gap_paths
                                        if required_paths:
                                            indexed_paths = {
                                                _normalize_path(row[0])
                                                for row in conn.execute(
                                                    "SELECT DISTINCT path FROM path_index WHERE generation_id = ?",
                                                    (active_generation_id,),
                                                )
                                            }
                                            matched_paths = indexed_paths & required_paths
                                            ratio = float(len(matched_paths)) / float(len(required_paths))
                                            if ratio < 0.70:
                                                errors.append(
                                                    f"path_index_to_included_ratio {ratio:.2f} is below hard threshold 0.70"
                                                )
                                            missing_required_paths = required_paths - indexed_paths
                                            for path in sorted(missing_required_paths):
                                                criticality = criticality_by_path.get(path, "")
                                                if criticality in {"important", "critical"}:
                                                    errors.append(f"{criticality}_missing_path_index: {path}")
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
