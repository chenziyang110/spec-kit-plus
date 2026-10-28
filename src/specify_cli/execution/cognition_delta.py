"""Lossless worker candidates for the runtime-owned cognition handoff.

This contract reports observations. It does not certify source, acceptance, or
freshness; those authorities stay with the workflow and cognition owners.
"""

from __future__ import annotations

import copy
import json
import math
from typing import Any

DELTA_SCHEMA = "spec-kit-cognition-delta-v1"
DELTA_VERSION = 1
PATH_ALIASES = (
    "changed_files", "changedFiles", "files_changed", "changed_paths", "changedPaths"
)
DELTA_ARRAYS = (
    "changed_paths", "path_changes", "behavior_surfaces", "owner_surfaces",
    "consumer_surfaces", "interfaces", "generated_surfaces",
    "generated_surface_notes", "state_contracts", "evidence_refs",
    "verification_evidence", "invalidated_claim_refs", "known_unknowns",
    "confidence_notes",
)
IDENTITY_FIELDS = {"task_ref", "task_id", "packet_id", "attempt_id"}
PATH_KINDS = {"added", "modified", "deleted", "renamed", "retained", "unknown"}
RUNTIME_RESULT_FIELDS = {"submission_history", "cognition_result_binding"}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def decode_result_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_object,
                      parse_float=_finite_float,
                      parse_constant=lambda value: _invalid_number(value))


def _invalid_number(value: str) -> Any:
    raise ValueError(f"non-finite JSON number: {value}")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _invalid_number(value)
    return number


def _json_value(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{label}[{index}]")
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for key, item in value.items():
            _json_value(item, f"{label}.{key}")
        return
    raise ValueError(f"{label} must contain finite JSON values")


def _paths(value: Any, label: str, *, legacy: bool = False) -> list[str]:
    if legacy and isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be an array of paths")
    result: list[str] = []
    for item in value:
        path = item.strip().replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        if (not path or path == "." or path.startswith("/") or ":" in path
                or any(char in path for char in ("\x00", "\r", "\n"))
                or ".." in path.split("/")):
            raise ValueError(f"{label} contains an invalid project-relative path")
        if path not in result:
            result.append(path)
    return result


def _same_json(left: Any, right: Any) -> bool:
    # JSON types matter (True must not equal 1); array order retains semantics.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False
    )


def normalize_cognition_delta(
    payload: dict[str, Any], *, allow_runtime_fields: bool = False
) -> tuple[list[str], dict[str, Any]]:
    """Validate candidates, migrate promised legacy fields and reject conflicts."""
    if not allow_runtime_fields and RUNTIME_RESULT_FIELDS & payload.keys():
        raise ValueError("worker cannot supply runtime-owned result history or binding")
    for canonical, alias in (("task_id", "taskId"), ("packet_id", "packetId")):
        if canonical in payload and alias in payload and str(payload[canonical]).strip() != str(payload[alias]).strip():
            raise ValueError(f"conflicting {canonical} aliases")
    present = [(key, _paths(payload[key], key, legacy=True))
               for key in PATH_ALIASES if key in payload]
    paths = present[0][1] if present else []
    if any(set(value) != set(paths) for _, value in present[1:]):
        raise ValueError("conflicting changed path aliases")
    raw = payload.get("cognition_delta")
    # Empty optional defaults preserve older packets/results as legacy input.
    explicit = raw is not None and raw != {}
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("cognition_delta must be an object")
    delta = copy.deepcopy(raw or {})
    if "path_changes" in payload:
        rows = payload["path_changes"]
        _json_value(rows, "path_changes")
        if "path_changes" in delta and not _same_json(delta["path_changes"], rows):
            raise ValueError("conflicting cognition_delta and path_changes")
        delta["path_changes"] = copy.deepcopy(rows)
        if not explicit:
            delta.update(schema=DELTA_SCHEMA, version=DELTA_VERSION, changed_paths=list(paths))
            explicit = True
    if explicit:
        unknown = set(delta) - {"schema", "version", "identity", "recovery", *DELTA_ARRAYS}
        if unknown:
            raise ValueError("unsupported cognition_delta fields: " + ", ".join(sorted(unknown)))
        if delta.get("schema") != DELTA_SCHEMA or type(delta.get("version")) is not int or delta["version"] != DELTA_VERSION:
            raise ValueError("unsupported cognition_delta schema/version")
        identity = delta.get("identity", {})
        if not isinstance(identity, dict) or set(identity) - IDENTITY_FIELDS:
            raise ValueError("cognition_delta.identity has unsupported shape")
        if any(not isinstance(value, str) or not value.strip() for value in identity.values()):
            raise ValueError("cognition_delta.identity values must be nonblank strings")
        identity = {key: value.strip() for key, value in identity.items()}
        if "identity" in delta:
            delta["identity"] = identity
        for field, aliases in (("task_id", ("task_id", "taskId")), ("packet_id", ("packet_id", "packetId"))):
            outer = next((payload[key] for key in aliases if key in payload), "")
            if field in identity and outer and identity[field] != str(outer).strip():
                raise ValueError(f"cognition_delta.identity.{field} conflicts with result")
        if "changed_paths" in delta:
            delta_paths = _paths(delta["changed_paths"], "cognition_delta.changed_paths")
            if present and set(delta_paths) != set(paths):
                raise ValueError("cognition_delta conflicts with changed path aliases")
            paths = delta_paths
        for key in DELTA_ARRAYS:
            if key in delta and not isinstance(delta[key], list):
                raise ValueError(f"cognition_delta.{key} must be an array")
        for row in delta.get("path_changes", []):
            if not isinstance(row, dict) or row.get("kind") not in PATH_KINDS:
                raise ValueError("cognition_delta.path_changes has invalid kind")
            keys = {"kind", "old_path", "new_path"} if row["kind"] == "renamed" else {"kind", "path"}
            if set(row) != keys:
                raise ValueError("cognition_delta.path_changes has invalid shape")
            endpoint_keys = ("old_path", "new_path") if row["kind"] == "renamed" else ("path",)
            endpoints = [_paths([row[key]], "path_changes")[0] for key in endpoint_keys]
            if row["kind"] == "renamed" and endpoints[0] == endpoints[1]:
                raise ValueError("rename endpoints must be distinct")
            if any(path not in paths for path in endpoints):
                raise ValueError("path_changes endpoints must be included in changed_paths")
            for key, path in zip(endpoint_keys, endpoints):
                row[key] = path
        if "recovery" in delta:
            recovery = delta["recovery"]
            if (not isinstance(recovery, dict) or set(recovery) - {"state", "actions"}
                    or not isinstance(recovery.get("state", ""), str)
                    or not isinstance(recovery.get("actions", []), list)):
                raise ValueError("cognition_delta.recovery has invalid shape")
    legacy_keys = {key: key for key in DELTA_ARRAYS if key not in {"changed_paths", "path_changes"}}
    legacy_keys["verification"] = "verification_evidence"
    for old, key in legacy_keys.items():
        if old not in payload:
            continue
        value = payload[old]
        if not isinstance(value, list):
            raise ValueError(f"{old} must be an array")
        _json_value(value, old)
        if key in delta and not _same_json(delta[key], value):
            raise ValueError(f"conflicting cognition_delta and {old}")
        delta[key] = copy.deepcopy(value)
    if delta or paths:
        delta.update(schema=DELTA_SCHEMA, version=DELTA_VERSION, changed_paths=list(paths))
        delta.setdefault("identity", {})
        delta.setdefault("path_changes", [{"kind": "unknown", "path": path} for path in paths])
        _json_value(delta, "cognition_delta")
    return list(paths), delta


def cognition_delta_contract(task_id: str) -> dict[str, Any]:
    return {
        "schema": DELTA_SCHEMA, "version": DELTA_VERSION, "task_id": task_id,
        "authority": "worker_candidate", "retained_failure_edits": True,
        "rename_endpoints": True, "acceptance_owner": "runtime",
        "source_binding_owner": "runtime",
    }
