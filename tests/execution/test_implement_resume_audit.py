import json
from pathlib import Path

from specify_cli.implement_audit import audit_implement_resume
from specify_cli.execution.implementation_review import (
    AcceptedResidualRisk,
    TaskLedgerEntry,
    TaskReviewFinding,
    TaskReviewRecord,
    branch_review_path,
    task_brief_path,
    write_task_ledger,
    write_task_review_record,
)
from specify_cli.implementation_summary import build_implementation_summary


def _write_basic_feature(feature_dir: Path, *, tracker_status: str = "resolved") -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                f"status: {tracker_status}",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: final validation",
                "goal: finish implementation",
                "next_action: report completion",
                "",
                "## Execution State",
                "completed_tasks:",
                "  - T001",
                "in_progress_tasks:",
                "failed_tasks:",
                "retry_attempts: 0",
                "",
                "## Open Gaps",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [X] T001 [US1] Create provider form in apps/web/src/features/providers/forms/ClaudeForm.tsx",
            ]
        ),
        encoding="utf-8",
    )


def _write_packetized_review_state(
    feature_dir: Path,
    *,
    ledger: bool = True,
    branch_review: bool = True,
    ledger_status: str = "accepted",
    task_review: bool = True,
) -> None:
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [X] T001 [US1] Update implementation in src/specify_cli/demo.py",
            ]
        ),
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": ["src/specify_cli/demo.py"],
  "validation_results": [{"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "PASS"}],
  "summary": "Updated demo implementation"
}
""".strip(),
        encoding="utf-8",
    )
    task_brief_path(feature_dir, "T001").parent.mkdir(parents=True, exist_ok=True)
    task_brief_path(feature_dir, "T001").write_text("# T001 Brief\n", encoding="utf-8")
    if task_review:
        write_task_review_record(
            feature_dir,
            TaskReviewRecord(
                task_id="T001",
                spec_verdict="pass",
                quality_verdict="pass",
                final_assessment="accepted",
            ),
        )
    if ledger:
        write_task_ledger(
            feature_dir,
            [
                TaskLedgerEntry(
                    task_id="T001",
                    status=ledger_status,  # type: ignore[arg-type]
                    task_brief="implementation-review/task-briefs/T001.md",
                    worker_result="worker-results/T001.json",
                    review_package="implementation-review/review-packages/T001.md",
                    task_review="implementation-review/task-reviews/T001.json" if task_review else "",
                    last_evidence=["worker-results/T001.json"],
                )
            ],
        )
    if branch_review:
        branch_review_path(feature_dir).parent.mkdir(parents=True, exist_ok=True)
        branch_review_path(feature_dir).write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")


def test_resolved_tracker_with_checked_task_but_no_worker_result_requires_audit_recovery(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["resume_classification"] == "terminal-audit-required"
    assert payload["trusted_terminal_state"] is False
    assert payload["recommended_tracker_status"] == "validating"
    assert any("missing worker result" in finding["missing_evidence"] for finding in payload["task_findings"])


def test_resolved_tracker_without_task_evidence_is_not_trusted(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").unlink()

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert "tasks.md has no task checklist evidence" in payload["open_gaps"]


def test_checked_component_task_with_result_but_no_consumer_evidence_is_gap(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": ["apps/web/src/features/providers/forms/ClaudeForm.tsx"],
  "validation_results": [{"command": "npm test -- providers", "status": "passed", "output": "PASS"}],
  "summary": "Created ClaudeForm component",
  "rule_acknowledgement": {
    "required_references_read": true,
    "forbidden_drift_respected": true,
    "context_bundle_read": true,
    "paths_read": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["recommended_tracker_status"] == "validating"
    assert any("missing consumer evidence" in finding["missing_evidence"] for finding in payload["task_findings"])


def test_resolved_tracker_with_worker_result_and_consumer_evidence_passes(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": [
    "apps/web/src/features/providers/forms/ClaudeForm.tsx",
    "apps/web/src/features/providers/DeviceProviderFormModal.tsx"
  ],
  "validation_results": [{"command": "npm test -- providers", "status": "passed", "output": "PASS"}],
  "consumer_evidence": [
    {
      "kind": "real_entrypoint",
      "entrypoint": "DeviceProviderPage",
      "producer": "provider catalog fixture",
      "transformer": "FormFactory cliToolType routing",
      "consumer": "DeviceProviderFormModal renders ClaudeForm",
      "boundary_or_executor": "React render test",
      "validation": "npm test -- providers",
      "surface": "DeviceProviderFormModal",
      "evidence": "FormFactory renders ClaudeForm for cliToolType=claude",
      "method": "focused test"
    }
  ],
  "summary": "Created and wired ClaudeForm component",
  "rule_acknowledgement": {
    "required_references_read": true,
    "forbidden_drift_respected": true,
    "context_bundle_read": true,
    "paths_read": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True
    assert payload["recommended_tracker_status"] == "resolved"


def test_resolved_packetized_state_without_ledger_fails(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, ledger=False)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert any("implementation-review/ledger.json" in gap for gap in payload["open_gaps"])


def test_resolved_packetized_state_without_branch_review_fails(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, branch_review=False)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert any("implementation-review/branch-review.md" in gap for gap in payload["open_gaps"])


def test_resolved_packetized_state_with_non_accepted_ledger_task_fails(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, ledger_status="fixes_required")

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any("T001" in gap and "accepted" in gap for gap in payload["open_gaps"])


def test_resolved_packetized_state_with_malformed_ledger_entry_fails_without_crash(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "ledger.json").write_text(
        '{"tasks":[{"task_id":123,"status":"accepted"}]}\n',
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any("implementation-review/ledger.json" in gap for gap in payload["open_gaps"])


def test_resolved_packetized_state_with_non_string_ledger_task_review_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": 123,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "task_review" in gap
        and "malformed" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_ledger_task_review_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "   ",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "task_review" in gap
        and "missing" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_missing_ledger_task_review_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "task_review" in gap
        and "missing" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_spaced_ledger_task_review_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": " implementation-review/task-reviews/T001.json ",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "task_review" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_backslash_ledger_task_review_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review\\task-reviews\\T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "task_review" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_task_packet_json_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "task-packets" / "T001.json").write_text("{not json", encoding="utf-8")

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "task-packets/T001.json" in gap and "malformed packet" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_mismatched_task_packet_id_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "task-packets" / "T001.json").write_text(
        '{"task_id":"T002"}\n',
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "task-packets/T001.json" in gap and "task_id" in gap and "T002" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_task_packet_id_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "task-packets" / "T001.json").write_text(
        '{"task_id":"   "}\n',
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "task-packets/T001.json" in gap and "task_id" in gap and "malformed packet" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_rejected_task_review_fails(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "fixes_required",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "accepted" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_rejects_absolute_task_review_reference(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    outside_review = tmp_path / "outside-task-review.json"
    outside_review.write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_packetized_review_state(feature_dir, task_review=False)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_review=str(outside_review),
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap and str(outside_review) in gap and "unsafe" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_rejects_parent_task_review_reference(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, task_review=False)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_review="../outside-task-review.json",
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap and "../outside-task-review.json" in gap and "unsafe" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_rejects_dot_segment_task_review_reference(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, task_review=False)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_review="implementation-review/./task-reviews/T001.json",
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/./task-reviews/T001.json" in gap
        and "unsafe" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_rejects_windows_drive_task_review_reference(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, task_review=False)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_review="C:/tmp/T001.json",
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap and "C:/tmp/T001.json" in gap and "unsafe" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_rejects_unc_task_review_reference(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, task_review=False)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_review="//server/share/T001.json",
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap and "//server/share/T001.json" in gap and "unsafe" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_malformed_task_review_fails_without_crash(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "findings": [{"disposition": "open"}],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap and "implementation-review/task-reviews/T001.json" in gap for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_task_review_enum_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "bogus",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "spec_verdict" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_malformed_controller_checks_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "controller_checks": {},
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "controller_checks" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_nested_finding_disposition_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": "Bogus disposition should not satisfy acceptance.",
                        "required_fix": "Reject malformed disposition values.",
                        "disposition": "bogus",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "disposition" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_residual_risk_scalar_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "concerns",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": "Residual risk is malformed.",
                        "required_fix": "Reject malformed residual risk values.",
                        "disposition": "accepted_residual_risk",
                    }
                ],
                "accepted_residual_risks": [
                    {
                        "finding_index": "0",
                        "reason": "Documented risk.",
                        "owner": "leader",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "finding_index" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_residual_risk_reason_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "concerns",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": "Residual risk is blank.",
                        "required_fix": "Reject blank residual risk values.",
                        "disposition": "accepted_residual_risk",
                    }
                ],
                "accepted_residual_risks": [
                    {
                        "finding_index": 0,
                        "reason": "   ",
                        "owner": "leader",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "reason" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_residual_risk_owner_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "concerns",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": "Residual risk owner is blank.",
                        "required_fix": "Reject blank residual risk owners.",
                        "disposition": "accepted_residual_risk",
                    }
                ],
                "accepted_residual_risks": [
                    {
                        "finding_index": 0,
                        "reason": "Documented risk.",
                        "owner": "",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "owner" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_follow_up_scalar_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "concerns",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": "Follow-up is malformed.",
                        "required_fix": "Reject malformed follow-up values.",
                        "disposition": "follow_up",
                    }
                ],
                "follow_up_work": [
                    {
                        "finding_index": 0,
                        "description": 123,
                        "target": "backlog",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "description" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_follow_up_target_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "concerns",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": "Follow-up target is blank.",
                        "required_fix": "Reject blank follow-up values.",
                        "disposition": "follow_up",
                    }
                ],
                "follow_up_work": [
                    {
                        "finding_index": 0,
                        "description": "Track cleanup.",
                        "target": " ",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "target" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_controller_check_scalar_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "controller_checks": [
                    {
                        "check": 123,
                        "reason": "Manual check required.",
                        "evidence_required": "Transcript",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "check" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_controller_check_evidence_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "controller_checks": [
                    {
                        "check": "manual smoke",
                        "reason": "Manual check required.",
                        "evidence_required": "",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "evidence_required" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_blank_finding_summary_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "implementation-review" / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "findings": [
                    {
                        "severity": "medium",
                        "category": "quality",
                        "file": "src/specify_cli/demo.py",
                        "line": 12,
                        "summary": " ",
                        "required_fix": "Reject blank finding fields.",
                        "disposition": "fixed",
                    }
                ],
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-reviews/T001.json" in gap
        and "summary" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_accepted_concern_task_review_passes(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, task_review=False)
    write_task_review_record(
        feature_dir,
        TaskReviewRecord(
            task_id="T001",
            spec_verdict="pass",
            quality_verdict="concerns",
            findings=[
                TaskReviewFinding(
                    severity="medium",
                    category="quality",
                    file="src/specify_cli/demo.py",
                    line=12,
                    summary="Existing follow-up risk remains bounded",
                    required_fix="Accept the residual risk for closeout",
                    disposition="accepted_residual_risk",
                )
            ],
            accepted_residual_risks=[
                AcceptedResidualRisk(
                    finding_index=0,
                    reason="The concern is documented and does not block this task.",
                    owner="leader",
                )
            ],
            final_assessment="accepted",
        ),
    )
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result="worker-results/T001.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=["worker-results/T001.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True


def test_resolved_packetized_state_with_accepted_ledger_and_branch_review_passes(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True
    assert payload["recommended_tracker_status"] == "resolved"


def test_resolved_packetized_state_with_unchecked_packet_task_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [ ] T001 [US1] Update implementation in src/specify_cli/demo.py",
            ]
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert any("T001" in gap and "checked" in gap for gap in payload["open_gaps"])


def test_resolved_packetized_state_with_unchecked_extra_packet_task_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "task-packets" / "T002.json").write_text('{"task_id":"T002"}\n', encoding="utf-8")
    write_task_review_record(
        feature_dir,
        TaskReviewRecord(
            task_id="T002",
            spec_verdict="pass",
            quality_verdict="pass",
            final_assessment="accepted",
        ),
    )
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result="worker-results/T001.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=["worker-results/T001.json"],
            ),
            TaskLedgerEntry(
                task_id="T002",
                status="accepted",
                task_review="implementation-review/task-reviews/T002.json",
            ),
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert any("T002" in gap and "checked" in gap for gap in payload["open_gaps"])


def test_checked_component_task_with_synthetic_only_consumer_evidence_is_gap(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "## T001: Create provider form",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| required_evidence | [consumer_evidence, real_entrypoint_evidence] |",
                "",
                "- [X] T001 [US1] Create provider form in apps/web/src/features/providers/forms/ClaudeForm.tsx",
            ]
        ),
        encoding="utf-8",
    )
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": [
    "apps/web/src/features/providers/forms/ClaudeForm.tsx",
    "apps/web/src/features/providers/DeviceProviderFormModal.tsx"
  ],
  "validation_results": [{"command": "npm test -- providers", "status": "passed", "output": "PASS"}],
  "consumer_evidence": [
    {
      "kind": "synthetic",
      "surface": "DeviceProviderFormModal",
      "evidence": "Hand-built modal state renders ClaudeForm"
    }
  ],
  "summary": "Created and wired ClaudeForm component",
  "rule_acknowledgement": {
    "required_references_read": true,
    "forbidden_drift_respected": true,
    "context_bundle_read": true,
    "paths_read": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["recommended_tracker_status"] == "validating"
    assert any("real-entrypoint consumer evidence" in finding["missing_evidence"] for finding in payload["task_findings"])


def test_explicit_real_entrypoint_requirement_is_enforced_without_consumer_keyword(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "## T001: Wire install flow",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| required_evidence | [consumer_evidence, real_entrypoint_evidence] |",
                "",
                "- [X] T001 [US1] Wire install flow in src/install.ts",
            ]
        ),
        encoding="utf-8",
    )
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": ["src/install.ts"],
  "validation_results": [{"command": "npm test -- install", "status": "passed", "output": "PASS"}],
  "consumer_evidence": [
    {
      "kind": "synthetic",
      "surface": "install plan",
      "evidence": "Hand-built install plan includes targets"
    }
  ],
  "summary": "Wired install flow",
  "rule_acknowledgement": {
    "required_references_read": true,
    "forbidden_drift_respected": true,
    "context_bundle_read": true,
    "paths_read": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any("real-entrypoint consumer evidence" in finding["missing_evidence"] for finding in payload["task_findings"])


def test_implementation_summary_records_completed_work_changes_and_verification(tmp_path: Path) -> None:
    project = tmp_path
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_basic_feature(feature_dir)
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": [
    "src/specify_cli/demo.py",
    "tests/test_demo.py"
  ],
  "validation_results": [
    {"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "1 passed"}
  ],
  "consumer_evidence": [
    {
      "kind": "real_entrypoint",
      "entrypoint": "specify demo",
      "producer": "demo command",
      "transformer": "Typer command dispatch",
      "consumer": "CLI invocation",
      "boundary_or_executor": "CliRunner",
      "validation": "pytest tests/test_demo.py -q"
    }
  ],
  "summary": "Added the demo command and regression coverage"
}
""".strip(),
        encoding="utf-8",
    )

    payload = build_implementation_summary(project, feature_dir)

    assert payload["status"] == "ok"
    assert payload["report_path"].endswith(".specify/features/001-demo/implementation-summary.md")
    assert payload["completed_work"][0]["task_id"] == "T001"
    assert payload["completed_work"][0]["summary"] == "Added the demo command and regression coverage"
    assert "src/specify_cli/demo.py" in payload["changed_paths"]["from_worker_results"]
    assert payload["verification_evidence"][0]["command"] == "pytest tests/test_demo.py -q"
    assert payload["baseline_comparison"]["commands"] == [
        "git status --short",
        "git diff --stat HEAD",
        "git diff --name-status HEAD",
    ]

    report = (feature_dir / "implementation-summary.md").read_text(encoding="utf-8")
    assert "## What Changed" in report
    assert "## How To Verify" in report
    assert "## Version Comparison" in report
    assert "Added the demo command and regression coverage" in report
    assert "src/specify_cli/demo.py" in report
    assert "pytest tests/test_demo.py -q" in report


def test_implementation_summary_includes_packetized_review_artifacts(tmp_path: Path) -> None:
    project = tmp_path
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_packetized_review_state(feature_dir)

    payload = build_implementation_summary(project, feature_dir)

    assert payload["review_artifacts"]["ledger"].endswith(
        ".specify/features/001-demo/implementation-review/ledger.json"
    )
    assert payload["review_artifacts"]["branch_review"].endswith(
        ".specify/features/001-demo/implementation-review/branch-review.md"
    )
    assert payload["completed_work"][0]["review_artifacts"]["task_review"].endswith(
        ".specify/features/001-demo/implementation-review/task-reviews/T001.json"
    )
    assert payload["completed_work"][0]["review_artifacts"]["task_review"] == payload[
        "review_artifacts"
    ]["task_reviews"]["T001"]

    report = (feature_dir / "implementation-summary.md").read_text(encoding="utf-8")
    assert "## Review Artifacts" in report
    assert "implementation-review/ledger.json" in report
    assert "implementation-review/branch-review.md" in report
    assert "implementation-review/task-reviews/T001.json" in report
