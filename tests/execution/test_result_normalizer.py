import json

import pytest

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


def test_normalize_worker_task_result_payload_preserves_consequence_evidence() -> None:
    result = normalize_worker_task_result_payload(
        {
            "task_id": "T104",
            "status": "success",
            "summary": "validated consequence obligation",
            "consequence_evidence": [
                {
                    "obligation_id": "CA-001",
                    "validation_ref": "pytest tests/unit/test_auth_service.py -q",
                    "outcome": "recovery path validated",
                }
            ],
        }
    )

    assert result.consequence_evidence == [
        {
            "obligation_id": "CA-001",
            "validation_ref": "pytest tests/unit/test_auth_service.py -q",
            "outcome": "recovery path validated",
        }
    ]


def test_normalize_worker_task_result_payload_preserves_must_preserve_evidence() -> None:
    result = normalize_worker_task_result_payload(
        {
            "task_id": "T105",
            "status": "success",
            "summary": "validated must-preserve obligation",
            "must_preserve_evidence": [
                {
                    "mp_id": "MP-001",
                    "validation_ref": "pytest tests/unit/test_auth_service.py -q",
                    "outcome": "existing token refresh behavior remains intact",
                }
            ],
        }
    )

    assert result.must_preserve_evidence == [
        {
            "mp_id": "MP-001",
            "validation_ref": "pytest tests/unit/test_auth_service.py -q",
            "outcome": "existing token refresh behavior remains intact",
        }
    ]


def test_normalize_review_worker_result_preserves_review_contract_fields() -> None:
    observations = [
        {
            "obligation_id": "RO-UI-001",
            "action": "Select Save from the settings screen.",
            "observed_result": "The control does not invoke the save handler.",
            "evidence_ref": "review-evidence/RO-UI-001/runtime.json",
        }
    ]
    findings = [
        {
            "id": "RF-001",
            "obligation_id": "RO-UI-001",
            "classification": "wiring",
            "summary": "The Save control is disconnected from its handler.",
            "status": "open",
        }
    ]

    result = normalize_worker_task_result_payload(
        {
            "task_id": "review-primary-journey",
            "status": "success",
            "wave": "review",
            "packet_id": "SRP-REVIEW-001",
            "obligation_ids": ["RO-UI-001", "RO-WIRE-002"],
            "observations": observations,
            "findings": findings,
            "summary": "Reviewed the primary settings journey.",
        }
    )

    assert result.wave == "review"
    assert result.packet_id == "SRP-REVIEW-001"
    assert result.obligation_ids == ["RO-UI-001", "RO-WIRE-002"]
    assert result.observations == observations
    assert result.findings == findings


def test_normalize_worker_task_result_payload_rejects_obsolete_ui_evidence() -> None:
    with pytest.raises(ValueError, match="uiFidelityEvidence"):
        normalize_worker_task_result_payload(
            {
                "task_id": "T105",
                "status": "success",
                "summary": "validated UI fidelity",
                "uiFidelityEvidence": [
                    {
                        "kind": "visual_comparison",
                        "artifact": "artifacts/auth-flow-diff.png",
                    }
                ],
            }
        )


def test_normalize_worker_task_result_payload_preserves_ui_fields() -> None:
    result = normalize_worker_task_result_payload(
        {
            "task_id": "T105",
            "status": "success",
            "summary": "validated UI fidelity",
            "ui_evidence": [
                {
                    "kind": "visual_capture",
                    "ref": "artifacts/ui/desktop-1440.png",
                    "viewport": "1440",
                }
            ],
            "ui_verification": {
                "contract_check": "pass",
                "runtime_evidence": "pass",
                "visual_comparison": "unavailable",
                "fidelity_status": "pending-human-review",
                "reviewer": "agent",
            },
        }
    )

    assert result.ui_evidence == [
        {
            "kind": "visual_capture",
            "ref": "artifacts/ui/desktop-1440.png",
            "viewport": "1440",
        }
    ]
    assert result.ui_verification.fidelity_status == "pending-human-review"


def test_normalize_worker_task_result_payload_rejects_camel_case_ui_evidence() -> None:
    with pytest.raises(ValueError, match="uiEvidence"):
        normalize_worker_task_result_payload(
            {
                "taskId": "T106",
                "status": "success",
                "summary": "validated UI fidelity",
                "uiEvidence": [
                    {
                        "kind": "screenshot",
                        "path": "artifacts/ui/mobile-390.png",
                        "viewport": "390",
                    }
                ],
                "uiVerification": {
                    "fidelityStatus": "pending-human-review",
                    "visualComparison": "unavailable",
                },
            }
        )


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
