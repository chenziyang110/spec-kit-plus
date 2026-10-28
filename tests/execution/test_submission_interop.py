"""Producer serialization and runtime history survive the compatibility reader."""

import copy
import hashlib
import json

import pytest

from specify_cli.execution.submission_history import (
    append_submission,
    bind_result_acceptance,
    read_result_owner,
    retained_submission_paths,
)


def _go_serialized_result(*, retained_paths=None):
    result = append_submission(
        None,
        {"task_id": "T001", "status": "success", "summary": "<>&中文",
         "observed": {"count": 9007199254740993123456789, "passed": True}},
        result_ref="feature/worker-results/T001.json", attempt_id="T001:revision-1",
        lifecycle_revision=2,
    )
    row = result["submission_history"][0]
    # Go escapes HTML by default while retaining Unicode. These are producer
    # bytes, whose digest must survive consumption without reserialization.
    row["result_json"] = row["result_json"].replace("<", r"\u003c").replace(
        ">", r"\u003e"
    ).replace("&", r"\u0026")
    row["result_sha256"] = hashlib.sha256(row["result_json"].encode()).hexdigest()
    row["retained_paths"] = retained_paths
    result["cognition_result_binding"]["result_sha256"] = row["result_sha256"]
    return result


@pytest.mark.parametrize("retained_paths", [None, [], ["src/retained.py"]])
def test_go_history_read_and_accept_keeps_exact_producer_bytes(retained_paths):
    original = _go_serialized_result(retained_paths=retained_paths)
    decoded = read_result_owner(json.dumps(original, ensure_ascii=False).encode())
    assert decoded == original
    accepted = bind_result_acceptance(
        decoded, acceptance_ref="feature/tasks/T001.json", acceptance_revision=3
    )
    assert accepted["submission_history"] == original["submission_history"]
    assert accepted["cognition_result_binding"]["result_sha256"] == original["cognition_result_binding"]["result_sha256"]
    assert accepted["observed"]["count"] == 9007199254740993123456789
    assert accepted["summary"] == "<>&中文"
    assert retained_submission_paths(accepted) == (retained_paths or [], [])


@pytest.mark.parametrize("tamper", ["summary", "number", "boolean", "attempt", "digest", "sequence", "binding_version"])
def test_cross_language_acceptance_refuses_changed_current_binding(tamper):
    result = _go_serialized_result()
    if tamper == "summary":
        result["summary"] = "modified"
    elif tamper == "number":
        result["observed"]["count"] += 1
    elif tamper == "boolean":
        result["observed"]["passed"] = 1
    else:
        field = {"attempt": "attempt_id", "digest": "result_sha256",
                 "sequence": "sequence", "binding_version": "version"}[tamper]
        result["cognition_result_binding"][field] = {"attempt": "foreign-attempt", "digest": "0" * 64,
                                                   "sequence": True, "binding_version": True}[tamper]
    before = copy.deepcopy(result)
    with pytest.raises(ValueError, match="exact current submission"):
        read_result_owner(json.dumps(result).encode())
    with pytest.raises(ValueError, match="exact current submission"):
        bind_result_acceptance(result, acceptance_ref="forged", acceptance_revision=4)
    assert result == before


@pytest.mark.parametrize("retained_paths", ["src/a.py", ["../outside.py"], [False]])
def test_runtime_retained_paths_are_known_bounded_array_metadata(retained_paths):
    result = _go_serialized_result(retained_paths=retained_paths)
    with pytest.raises(ValueError):
        read_result_owner(json.dumps(result).encode())


def test_unknown_history_fields_still_refuse():
    result = _go_serialized_result()
    result["submission_history"][0]["accepted_by_worker"] = True
    with pytest.raises(ValueError, match="invalid sequence or digest"):
        read_result_owner(json.dumps(result).encode())


def test_invalid_raw_report_keeps_runtime_retained_paths_and_unknown_obligation():
    result = _go_serialized_result(retained_paths=["src/accepted.py"])
    result = append_submission(
        result, {}, result_ref="feature/worker-results/T001.json", attempt_id="T001:revision-2",
        rejection_reason="malformed input", raw_input="{invalid",
    )
    result["submission_history"][1]["retained_paths"] = ["src/rejected.py"]
    stored = read_result_owner(json.dumps(result).encode())
    assert retained_submission_paths(stored) == (["src/accepted.py", "src/rejected.py"], [2])
