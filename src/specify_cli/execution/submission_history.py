"""Append-only submission evidence embedded in the existing result owner."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from .cognition_delta import PATH_ALIASES, RUNTIME_RESULT_FIELDS, _paths, _same_json, decode_result_json

SUBMISSION_SCHEMA = "spec-kit-worker-submission-v1"
_ENTRY_FIELDS = {"schema", "version", "sequence", "attempt_id", "status", "result_json", "result_sha256", "rejection_reason"}
_OPTIONAL_ENTRY_FIELDS = {"retained_paths"}
_ENTRY_STATUSES = {"pending", "success", "blocked", "failed", "rejected", "legacy"}


def result_bytes_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        {key: value for key, value in payload.items() if key not in RUNTIME_RESULT_FIELDS},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_result_owner(content: bytes | None) -> dict[str, Any] | None:
    if content is None:
        return None
    result = decode_result_json(content.decode("utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("stored result must be an object")
    history = result.get("submission_history", [])
    if not isinstance(history, list):
        raise ValueError("stored submission_history must be an array")
    for index, row in enumerate(history, 1):
        if (not isinstance(row, dict) or row.get("schema") != SUBMISSION_SCHEMA
                or not _ENTRY_FIELDS <= row.keys()
                or row.keys() - _ENTRY_FIELDS - _OPTIONAL_ENTRY_FIELDS
                or type(row.get("version")) is not int or row["version"] != 1
                or type(row.get("sequence")) is not int or row["sequence"] != index
                or not isinstance(row.get("attempt_id"), str) or not row["attempt_id"].strip()
                or not isinstance(row.get("status"), str) or row["status"] not in _ENTRY_STATUSES
                or not isinstance(row.get("rejection_reason"), str)
                or not isinstance(row.get("result_json"), str)
                or _digest(row["result_json"]) != row.get("result_sha256")):
            raise ValueError("stored submission history has an invalid sequence or digest")
        retained = row.get("retained_paths")
        if retained is not None:
            _paths(retained, "stored retained_paths")
    if result.get("cognition_result_binding") is not None:
        _bound_submission(result)
    return result


def _bound_submission(result: dict[str, Any]) -> dict[str, Any]:
    """Check exact producer bytes, then compare decoded current JSON values.

    JSON escaping belongs to the producer. Re-encoding an unchanged Go result
    with Python must not change the immutable submission digest.
    """
    binding = result.get("cognition_result_binding")
    history = result.get("submission_history", [])
    if (not isinstance(binding, dict)
            or binding.get("schema") != "spec-kit-cognition-result-binding-v1"
            or type(binding.get("version")) is not int or binding["version"] != 1
            or type(binding.get("sequence")) is not int
            or not isinstance(history, list)
            or not 1 <= binding["sequence"] <= len(history)):
        raise ValueError("acceptance does not match the exact current submission")
    matching = history[binding["sequence"] - 1]
    if (not isinstance(matching, dict)
            or matching.get("sequence") != binding["sequence"]
            or matching.get("status") == "rejected"
            or matching.get("attempt_id") != binding.get("attempt_id")
            or not isinstance(matching.get("result_json"), str)
            or _digest(matching["result_json"]) != matching.get("result_sha256")
            or binding.get("result_sha256") != matching.get("result_sha256")
            or binding.get("acceptance_state") not in ("submitted", "accepted")):
        raise ValueError("acceptance does not match the exact current submission")
    submitted = decode_result_json(matching["result_json"])
    projection = {key: value for key, value in result.items() if key not in RUNTIME_RESULT_FIELDS}
    if not isinstance(submitted, dict) or not _same_json(submitted, projection):
        raise ValueError("acceptance does not match the exact current submission")
    return matching


def _entry(payload_json: str, sequence: int, status: str, attempt_id: str,
           rejection_reason: str = "") -> dict[str, Any]:
    return {
        "schema": SUBMISSION_SCHEMA, "version": 1, "sequence": sequence,
        "attempt_id": attempt_id, "status": status, "result_json": payload_json,
        "result_sha256": _digest(payload_json), "rejection_reason": rejection_reason,
    }


def append_submission(
    previous: dict[str, Any] | None, candidate: dict[str, Any], *,
    result_ref: str, attempt_id: str, lifecycle_revision: int = 0,
    rejection_reason: str = "", raw_input: object = None,
) -> dict[str, Any]:
    history = copy.deepcopy((previous or {}).get("submission_history", []))
    if previous and not history:
        old_json = result_bytes_json(previous)
        prior_status = str(previous.get("status", "legacy"))
        history.append(_entry(old_json, 1, prior_status if prior_status in _ENTRY_STATUSES else "legacy", "legacy"))
    if rejection_reason:
        # Preserve exact string input even when it is not parseable JSON.
        submitted = raw_input if isinstance(raw_input, str) else json.dumps(
            raw_input, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=repr
        )
        history.append(_entry(submitted, len(history) + 1, "rejected", attempt_id, rejection_reason))
        projection = copy.deepcopy(previous or candidate)
    else:
        submitted = result_bytes_json(candidate)
        history.append(_entry(submitted, len(history) + 1, str(candidate["status"]), attempt_id))
        projection = copy.deepcopy(candidate)
        projection["cognition_result_binding"] = {
            "schema": "spec-kit-cognition-result-binding-v1", "version": 1,
            "result_ref": result_ref, "result_sha256": history[-1]["result_sha256"],
            "sequence": history[-1]["sequence"], "attempt_id": attempt_id,
            "lifecycle_revision": lifecycle_revision, "acceptance_state": "submitted",
            "acceptance_ref": "", "acceptance_revision": 0,
        }
    projection["submission_history"] = history
    return projection


def bind_result_acceptance(result: dict[str, Any], *, acceptance_ref: str,
                           acceptance_revision: int) -> dict[str, Any]:
    """Bind the existing owner acceptance to the exact current submission."""
    projection = copy.deepcopy(result)
    binding = projection.get("cognition_result_binding")
    if binding is None:
        # Historical results remain audit input; accepting them cannot mint proof.
        return projection
    matching = _bound_submission(projection)
    if matching.get("status") != "success":
        raise ValueError("acceptance does not match the exact current submission")
    binding.update(acceptance_state="accepted", acceptance_ref=acceptance_ref,
                   acceptance_revision=acceptance_revision)
    return projection


def retained_submission_paths(result: dict[str, Any]) -> tuple[list[str], list[int]]:
    """Union candidate reports, including conflicting aliases on rejected input.

    This is invalidation accounting, not proof that any reported edit occurred.
    Unparseable reports remain explicit obligations for the source-owning check.
    """
    paths: list[str] = []
    unknown: list[int] = []
    for row in result.get("submission_history", []):
        sequence = row["sequence"]
        for path in _paths(row.get("retained_paths") or [], "stored retained_paths"):
            if path not in paths:
                paths.append(path)
        try:
            payload = decode_result_json(row["result_json"])
            if not isinstance(payload, dict):
                raise ValueError("submission is not an object")
            reports = [payload[key] for key in PATH_ALIASES if key in payload]
            delta = payload.get("cognition_delta")
            if delta is not None:
                if not isinstance(delta, dict):
                    raise ValueError("delta is not an object")
                if "changed_paths" in delta:
                    reports.append(delta["changed_paths"])
            for source in (payload, delta or {}):
                if "path_changes" not in source:
                    continue
                if not isinstance(source["path_changes"], list):
                    raise ValueError("path_changes is not an array")
                for change in source["path_changes"]:
                    if not isinstance(change, dict):
                        raise ValueError("path change is not an object")
                    reports.extend([change[key]] for key in ("path", "old_path", "new_path") if key in change)
            for report in reports:
                for path in _paths(report, "submission paths", legacy=True):
                    if path not in paths:
                        paths.append(path)
        except (TypeError, ValueError, KeyError):
            unknown.append(sequence)
    return paths, unknown
