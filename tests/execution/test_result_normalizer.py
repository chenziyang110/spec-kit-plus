import json

from specify_cli.execution.result_normalizer import normalize_worker_task_result_payload


def test_normalize_worker_task_result_payload_accepts_canonical_payload() -> None:
    result = normalize_worker_task_result_payload(
        {
            "task_id": "T100",
            "status": "success",
            "changed_files": ["src/app.py"],
            "summary": "implemented",
            "validation_results": [
                {"command": "pytest -q", "status": "passed", "output": "1 passed"}
            ],
        }
    )

    assert result.task_id == "T100"
    assert result.status == "success"
    assert result.reported_status == "success"
    assert result.changed_files == ["src/app.py"]


def test_normalize_worker_task_result_payload_maps_done_with_concerns_to_success() -> None:
    result = normalize_worker_task_result_payload(
        {
            "taskId": "T101",
            "status": "DONE_WITH_CONCERNS",
            "files_changed": ["src/feature.py"],
            "message": "completed with follow-up concerns",
            "issues": ["existing file is oversized"],
            "validationResults": [
                {"command": "pytest -q", "status": "passed", "output": "1 passed"}
            ],
        }
    )

    assert result.task_id == "T101"
    assert result.status == "success"
    assert result.reported_status == "done_with_concerns"
    assert result.concerns == ["existing file is oversized"]


def test_normalize_worker_task_result_payload_maps_needs_context_to_blocked_with_defaults() -> None:
    result = normalize_worker_task_result_payload(
        {
            "task_id": "T102",
            "status": "NEEDS_CONTEXT",
            "summary": "Need exact migration requirement before editing schema",
            "missing_context": ["migration compatibility expectation"],
        }
    )

    assert result.status == "blocked"
    assert result.reported_status == "needs_context"
    assert result.blockers == ["Need exact migration requirement before editing schema"]
    assert result.failed_assumptions == ["migration compatibility expectation"]
    assert result.suggested_recovery_actions


def test_normalize_worker_task_result_payload_accepts_json_text() -> None:
    payload = json.dumps(
        {
            "task_id": "T103",
            "status": "blocked",
            "summary": "blocked on contract mismatch",
            "blocker": "contract mismatch",
            "failedAssumptions": ["expected v2 payload"],
            "recovery_actions": ["clarify contract"],
        }
    )

    result = normalize_worker_task_result_payload(payload)

    assert result.task_id == "T103"
    assert result.status == "blocked"
    assert result.blockers == ["contract mismatch"]
