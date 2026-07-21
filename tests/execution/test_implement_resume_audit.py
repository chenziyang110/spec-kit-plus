import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import specify_cli.implement_audit as implement_audit_module
from specify_cli.implement_audit import audit_implement_resume
from specify_cli.execution.implementation_review import (
    AcceptedResidualRisk,
    TaskLedgerEntry,
    TaskReviewFinding,
    TaskReviewRecord,
    branch_review_path,
    review_package_path,
    task_brief_path,
    write_task_ledger,
    write_task_review_record,
)
from specify_cli.implementation_summary import (
    build_implementation_summary,
    implementation_closeout_blockers,
)
from specify_cli.review_runtime import implementation_snapshot_sha256
from specify_cli.validation_budget import (
    complete_validation_epoch,
    reserve_validation_epoch,
)


def _write_basic_feature(
    feature_dir: Path, *, tracker_status: str = "resolved"
) -> None:
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
    review_package_path(feature_dir, "T001").parent.mkdir(parents=True, exist_ok=True)
    review_package_path(feature_dir, "T001").write_text(
        "# T001 Review Package\n", encoding="utf-8"
    )
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
                    task_review="implementation-review/task-reviews/T001.json"
                    if task_review
                    else "",
                    last_evidence=["worker-results/T001.json"],
                )
            ],
        )
    if branch_review:
        branch_review_path(feature_dir).parent.mkdir(parents=True, exist_ok=True)
        branch_review_path(feature_dir).write_text(
            "# Branch Review\n\nAccepted.\n", encoding="utf-8"
        )


def test_resolved_state_accepts_single_task_lifecycle_without_legacy_review_fanout(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [X] T001 [US1] Update implementation in src/demo.py\n",
        encoding="utf-8",
    )
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "success",
                "changed_files": ["src/demo.py"],
                "validation_results": [
                    {
                        "command": "pytest tests/test_demo.py -q",
                        "status": "passed",
                        "output": "PASS",
                    }
                ],
                "summary": "Updated demo implementation",
            }
        ),
        encoding="utf-8",
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "version": 1,
                "task_id": "T001",
                "task_ref": "task-index.json#/tasks/T001",
                "source_revision": "r1",
                "execution_mode": "leader-direct",
                "packet_ref": None,
                "status": "accepted",
                "changed_paths": ["src/demo.py"],
                "validation": [
                    {"command": "pytest tests/test_demo.py -q", "status": "passed"}
                ],
                "review": None,
                "obligation_evidence": [],
                "blockers": [],
                "recovery": None,
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is True, payload
    assert not any(
        "implementation-review/ledger.json" in gap for gap in payload["open_gaps"]
    )
    assert not any("branch-review.md" in gap for gap in payload["open_gaps"])


def test_resume_audit_accepts_one_shared_convergence_epoch_for_all_tasks(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [X] T001 [US1] Update API implementation in src/demo.py\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "validation_policy": {
                    "mode": "feature_epochs",
                    "max_epochs": 3,
                    "budget_scope": "implement-review",
                    "budget_ref": "implementation-review/validation-runs.json",
                    "heavy_gate_owner": "leader",
                },
                "tasks": [{"id": "T001", "task_checks": []}],
            }
        ),
        encoding="utf-8",
    )
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    result_path = result_dir / "T001.json"
    result_payload = {
        "task_id": "T001",
        "status": "success",
        "changed_files": ["src/demo.py"],
        "validation_results": [],
        "summary": "Implemented the task; leader owns shared validation.",
    }
    result_path.write_text(json.dumps(result_payload), encoding="utf-8")
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "version": 1,
                "task_id": "T001",
                "task_ref": "task-index.json#/tasks/T001",
                "source_revision": "r1",
                "execution_mode": "leader-direct",
                "packet_ref": None,
                "status": "accepted",
                "changed_paths": ["src/demo.py"],
                "validation": [
                    {
                        "validation_run_ref": "implementation-review/validation-runs.json#V1",
                        "status": "passed",
                    }
                ],
                "review": None,
                "obligation_evidence": [],
                "blockers": [],
                "recovery": None,
            }
        ),
        encoding="utf-8",
    )
    missing_wiring = audit_implement_resume(tmp_path, feature_dir)
    assert missing_wiring["trusted_terminal_state"] is False
    assert any(
        "missing consumer evidence" in finding["missing_evidence"]
        for finding in missing_wiring["task_findings"]
    )

    result_payload["consumer_evidence"] = [
        {
            "kind": "wiring",
            "surface": "API implementation",
            "consumer": "demo entrypoint",
        }
    ]
    result_path.write_text(json.dumps(result_payload), encoding="utf-8")
    fingerprint = implementation_snapshot_sha256(tmp_path, feature_dir)
    run = reserve_validation_epoch(
        tmp_path,
        feature_dir,
        stage="implement",
        purpose="convergence",
        fingerprint=fingerprint,
        commands=["pytest -q", "ruff check ."],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        tmp_path,
        feature_dir,
        run_id=run["run_id"],
        status="passed",
        evidence_refs=["implementation-review/validation-evidence/V1.txt"],
        summary="Shared convergence gates passed.",
    )
    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is True, payload
    assert payload["open_gaps"] == []


def test_feature_epoch_lifecycle_requires_integrated_ui_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "validation_policy": {"mode": "feature_epochs"},
                "tasks": [{"id": "T001"}],
            }
        ),
        encoding="utf-8",
    )
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": ["src/ui/settings.tsx"],
                "validation": [{"validation_run_ref": "ledger#V1"}],
                "blockers": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(implement_audit_module, "ui_task_ids", lambda _: {"T001"})
    monkeypatch.setattr(
        implement_audit_module, "obsolete_task_ui_contract_fields", lambda _: {}
    )
    monkeypatch.setattr(
        implement_audit_module, "invalid_task_ui_contracts", lambda _: {}
    )
    observed: list[bool] = []

    def _capture_scope(*args: object, require_integrated: bool = False) -> list[str]:
        observed.append(require_integrated)
        return []

    monkeypatch.setattr(
        implement_audit_module,
        "validate_lifecycle_ui_verification",
        _capture_scope,
    )

    implement_audit_module._packetized_review_gaps(
        feature_dir,
        [{"task_id": "T001"}],
        [{"task_id": "T001"}],
        terminal=True,
    )

    assert observed == [True]


def test_resume_audit_blocks_ui_lifecycle_without_visual_acceptance(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "- [X] T001 Implement settings UI in src/ui/settings.tsx\n\n"
        "## T001: Settings UI\n\n"
        "### UI Implementation Contract\n\n"
        "| Field | Value |\n| --- | --- |\n"
        "| design_sources | [DESIGN.md, ui-brief.md] |\n"
        "| required_evidence | [desktop_screenshot] |\n",
        encoding="utf-8",
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": ["src/ui/settings.tsx"],
                "validation": [{"command": "npm test", "status": "passed"}],
                "review": None,
                "blockers": [],
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any("ui_verification is required" in gap for gap in payload["open_gaps"])


def test_resume_audit_rejects_obsolete_ui_task_contract(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    _write_basic_feature(feature_dir)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_fidelity_requirements": {"level": "high"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": ["src/ui/settings.tsx"],
                "validation": [{"command": "npm test", "status": "passed"}],
                "review": None,
                "blockers": [],
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any(
        "obsolete UI fields" in gap and "ui_fidelity_requirements" in gap
        for gap in payload["open_gaps"]
    )


def test_resume_audit_rejects_partial_current_ui_task_contract(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    _write_basic_feature(feature_dir)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [{"id": "T001", "ui_contract": {"subject": "settings"}}],
            }
        ),
        encoding="utf-8",
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": ["src/ui/settings.tsx"],
                "validation": [{"command": "npm test", "status": "passed"}],
                "review": None,
                "blockers": [],
                "ui_verification": {},
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any(
        "invalid current UI contract" in gap and "missing current fields" in gap
        for gap in payload["open_gaps"]
    )


def test_active_resume_audit_surfaces_mandatory_external_task_blocker(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-external-ci"
    _write_basic_feature(feature_dir, tracker_status="validating")
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Validate protected pipeline\n", encoding="utf-8"
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "changed_paths": [".gitlab-ci.yml"],
                "validation": [{"command": "tsc --noEmit", "status": "passed"}],
                "blockers": [
                    {
                        "classification": "external",
                        "owner": "external-system",
                        "evidence": "Protected pipeline has not run",
                        "exact_next_action": "Run the protected pipeline from the checkpoint",
                        "approval_question": None,
                        "unblock_criteria": "Protected pipeline succeeds",
                        "implementation_can_continue": True,
                        "completion_impact": "mandatory_for_completion",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any(
        "T001" in gap and "mandatory_for_completion" in gap
        for gap in payload["open_gaps"]
    )


def test_resume_audit_rejects_unstructured_task_blocker(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-external-ci"
    _write_basic_feature(feature_dir)
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "accepted",
                "changed_paths": [".gitlab-ci.yml"],
                "validation": [{"command": "tsc --noEmit", "status": "passed"}],
                "blockers": ["pipeline has not run"],
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any("blocker 1 must be an object" in gap for gap in payload["open_gaps"])


def test_active_resume_audit_rejects_blocked_task_without_blocker_details(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-external-ci"
    _write_basic_feature(feature_dir, tracker_status="blocked")
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps({"task_id": "T001", "status": "blocked", "blockers": []}),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any(
        "blocked task T001 must record blockers" in gap for gap in payload["open_gaps"]
    )


def test_active_resume_audit_rejects_malformed_task_lifecycle(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-external-ci"
    _write_basic_feature(feature_dir, tracker_status="blocked")
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text("{not-json", encoding="utf-8")

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any(
        "implementation-review/tasks/T001.json is malformed" in gap
        for gap in payload["open_gaps"]
    )


@pytest.mark.parametrize("task_index_version", [2, 3])
def test_agent_native_task_index_requires_lifecycle_for_each_checked_task(
    tmp_path: Path,
    task_index_version: int,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": task_index_version,
                "status": "ready",
                "tasks": [{"id": "T001"}],
            }
        ),
        encoding="utf-8",
    )
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "success",
                "changed_files": [
                    "apps/web/src/features/providers/forms/ClaudeForm.tsx"
                ],
                "validation_results": [
                    {"command": "pytest -q", "status": "passed", "output": "PASS"}
                ],
                "summary": "Implemented the task",
            }
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["trusted_terminal_state"] is False
    assert any(
        "implementation-review/tasks/T001.json is missing" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_tracker_with_checked_task_but_no_worker_result_requires_audit_recovery(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["resume_classification"] == "terminal-audit-required"
    assert payload["trusted_terminal_state"] is False
    assert payload["recommended_tracker_status"] == "validating"
    assert any(
        "missing worker result" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


def test_resolved_tracker_without_task_evidence_is_not_trusted(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "tasks.md").unlink()

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert "tasks.md has no task checklist evidence" in payload["open_gaps"]


def test_checked_component_task_with_result_but_no_consumer_evidence_is_gap(
    tmp_path: Path,
) -> None:
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
    assert any(
        "missing consumer evidence" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


def test_resolved_tracker_with_worker_result_and_consumer_evidence_passes(
    tmp_path: Path,
) -> None:
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
    assert any(
        "implementation-review/ledger.json" in gap for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_without_branch_review_fails(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, branch_review=False)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["trusted_terminal_state"] is False
    assert any(
        "implementation-review/branch-review.md" in gap for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_non_accepted_ledger_task_fails(
    tmp_path: Path,
) -> None:
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
    assert any(
        "implementation-review/ledger.json" in gap for gap in payload["open_gaps"]
    )


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


def test_resolved_packetized_state_with_missing_task_brief_file_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    task_brief_path(feature_dir, "T001").unlink()

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/task-briefs/T001.md" in gap
        and "missing" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_non_canonical_task_brief_reference_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/./task-briefs/T001.md",
                worker_result="worker-results/T001.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=["worker-results/T001.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "task_brief" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_missing_review_package_file_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    review_package_path(feature_dir, "T001").unlink()

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "T001" in gap
        and "implementation-review/review-packages/T001.md" in gap
        and "missing" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_non_canonical_review_package_reference_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result="worker-results/T001.json",
                review_package="implementation-review/review-packages/../review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=["worker-results/T001.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "implementation-review/ledger.json" in gap
        and "T001" in gap
        and "review_package" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_invalid_task_packet_json_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "task-packets" / "T001.json").write_text(
        "{not json", encoding="utf-8"
    )

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
        "task-packets/T001.json" in gap
        and "task_id" in gap
        and "malformed packet" in gap
        for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_rejected_task_review_fails(
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


def test_resolved_packetized_state_rejects_absolute_task_review_reference(
    tmp_path: Path,
) -> None:
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


def test_resolved_packetized_state_rejects_parent_task_review_reference(
    tmp_path: Path,
) -> None:
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


def test_resolved_packetized_state_rejects_dot_segment_task_review_reference(
    tmp_path: Path,
) -> None:
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


def test_resolved_packetized_state_rejects_windows_drive_task_review_reference(
    tmp_path: Path,
) -> None:
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


def test_resolved_packetized_state_rejects_unc_task_review_reference(
    tmp_path: Path,
) -> None:
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
        "T001" in gap and "implementation-review/task-reviews/T001.json" in gap
        for gap in payload["open_gaps"]
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


def test_resolved_packetized_state_loads_runtime_managed_worker_result_from_ledger(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "worker-results" / "T001.json").unlink()
    runtime_result = (
        tmp_path / ".specify" / "teams" / "state" / "results" / "request-123.json"
    )
    runtime_result.parent.mkdir(parents=True)
    runtime_result.write_text(
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
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result=".specify/teams/state/results/request-123.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=[".specify/teams/state/results/request-123.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True
    assert (
        payload["task_findings"][0]["result_path"]
        .replace("\\", "/")
        .endswith(".specify/teams/state/results/request-123.json")
    )


def test_resolved_packetized_state_accepts_runtime_worker_result_task_id_alias(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "worker-results" / "T001.json").unlink()
    runtime_result = (
        tmp_path / ".specify" / "teams" / "state" / "results" / "request-alias.json"
    )
    runtime_result.parent.mkdir(parents=True)
    runtime_result.write_text(
        """
{
  "taskId": "T001",
  "status": "success",
  "changed_files": ["src/specify_cli/demo.py"],
  "validation_results": [{"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "PASS"}],
  "summary": "Updated demo implementation"
}
""".strip(),
        encoding="utf-8",
    )
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result=".specify/teams/state/results/request-alias.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=[".specify/teams/state/results/request-alias.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True


def test_resolved_packetized_state_rejects_runtime_worker_result_task_id_mismatch(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "worker-results" / "T001.json").unlink()
    runtime_result = (
        tmp_path / ".specify" / "teams" / "state" / "results" / "request-999.json"
    )
    runtime_result.parent.mkdir(parents=True)
    runtime_result.write_text(
        """
{
  "task_id": "T999",
  "status": "success",
  "changed_files": ["src/specify_cli/demo.py"],
  "validation_results": [{"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "PASS"}],
  "summary": "Wrong task result"
}
""".strip(),
        encoding="utf-8",
    )
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result=".specify/teams/state/results/request-999.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=[".specify/teams/state/results/request-999.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "worker result task_id mismatch" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


def test_resolved_packetized_state_rejects_runtime_worker_result_missing_task_id(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "worker-results" / "T001.json").unlink()
    runtime_result = (
        tmp_path / ".specify" / "teams" / "state" / "results" / "request-missing.json"
    )
    runtime_result.parent.mkdir(parents=True)
    runtime_result.write_text(
        """
{
  "status": "success",
  "changed_files": ["src/specify_cli/demo.py"],
  "validation_results": [{"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "PASS"}],
  "summary": "Missing task id"
}
""".strip(),
        encoding="utf-8",
    )
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result=".specify/teams/state/results/request-missing.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=[".specify/teams/state/results/request-missing.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "worker result missing task_id" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


@pytest.mark.parametrize(
    "worker_result_reference",
    [
        "../outside-worker-result.json",
        "/tmp/outside-worker-result.json",
        "C:/tmp/outside-worker-result.json",
        "\\\\server\\share\\outside-worker-result.json",
        "worker-results\\T001.json",
        "./worker-results/T001.json",
        ".specify/./teams/state/results/request-123.json",
    ],
)
def test_resolved_packetized_state_rejects_unsafe_ledger_worker_result_reference(
    tmp_path: Path,
    worker_result_reference: str,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result=worker_result_reference,
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=[worker_result_reference],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        f"unsafe worker_result {worker_result_reference}" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


def test_resolved_packetized_state_reports_missing_safe_ledger_worker_result_reference(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    write_task_ledger(
        feature_dir,
        [
            TaskLedgerEntry(
                task_id="T001",
                status="accepted",
                task_brief="implementation-review/task-briefs/T001.md",
                worker_result=".specify/teams/state/results/missing-request.json",
                review_package="implementation-review/review-packages/T001.md",
                task_review="implementation-review/task-reviews/T001.json",
                last_evidence=[".specify/teams/state/results/missing-request.json"],
            )
        ],
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any(
        "worker_result is missing: .specify/teams/state/results/missing-request.json"
        in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


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


def test_active_packetized_checked_task_without_review_ledger_reports_gap(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir, ledger=False, branch_review=False)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: executing",
                "feature: 001-demo",
                "resume_decision: continue",
                "---",
                "",
                "## Current Focus",
                "current_batch: implementation",
                "goal: continue implementation",
                "next_action: keep working",
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
                "- [X] T001 [US1] Update implementation in src/specify_cli/demo.py",
                "- [ ] T002 [US1] Continue implementation in src/specify_cli/followup.py",
            ]
        ),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is False
    assert any(
        "implementation-review/ledger.json" in gap for gap in payload["open_gaps"]
    )


def test_resolved_packetized_state_with_unchecked_extra_packet_task_fails(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "task-packets" / "T002.json").write_text(
        '{"task_id":"T002"}\n', encoding="utf-8"
    )
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


def test_resolved_packetized_state_allows_checked_legacy_task_without_ledger_entry(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [X] T001 [US1] Update implementation in src/specify_cli/demo.py",
                "- [X] T002 [US1] Legacy checked cleanup in docs/notes.md",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "worker-results" / "T002.json").write_text(
        """
{
  "task_id": "T002",
  "status": "success",
  "changed_files": ["docs/notes.md"],
  "validation_results": [{"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "PASS"}],
  "summary": "Completed legacy cleanup"
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert not any(
        "T002 is missing from implementation-review/ledger.json" in gap
        for gap in payload["open_gaps"]
    )


def test_checked_component_task_with_synthetic_only_consumer_evidence_is_gap(
    tmp_path: Path,
) -> None:
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
    assert any(
        "real-entrypoint consumer evidence" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


def test_explicit_real_entrypoint_requirement_is_enforced_without_consumer_keyword(
    tmp_path: Path,
) -> None:
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
    assert any(
        "real-entrypoint consumer evidence" in finding["missing_evidence"]
        for finding in payload["task_findings"]
    )


def test_implementation_summary_records_completed_work_changes_and_verification(
    tmp_path: Path,
) -> None:
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
    assert payload["report_path"].endswith(
        ".specify/features/001-demo/implementation-summary.md"
    )
    assert payload["completed_work"][0]["task_id"] == "T001"
    assert (
        payload["completed_work"][0]["summary"]
        == "Added the demo command and regression coverage"
    )
    assert "src/specify_cli/demo.py" in payload["changed_paths"]["from_worker_results"]
    assert (
        payload["verification_evidence"][0]["command"] == "pytest tests/test_demo.py -q"
    )
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


def test_implementation_summary_exposes_pending_ui_human_review(tmp_path: Path) -> None:
    project = tmp_path
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_basic_feature(feature_dir)
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "ui_verification": {
                    "applicable": True,
                    "visual_comparison": "needs-human-review",
                    "fidelity_status": "pending-human-review",
                    "human_review_ref": "evidence/ui-review.md",
                },
            }
        ),
        encoding="utf-8",
    )

    payload = build_implementation_summary(project, feature_dir)

    assert payload["status"] == "blocked"
    assert payload["human_needed_checks"] == [
        "T001: UI visual approval is pending; review target: evidence/ui-review.md"
    ]
    blocker = payload["blockers"][0]
    assert blocker["category"] == "human-review"
    assert blocker["human_action_required"] is True
    assert len(blocker["human_action_guide"]["steps"]) == 4
    assert blocker["resume"]["argv"][:3] == [
        "specify",
        "implement",
        "resume-audit",
    ]
    assert str(feature_dir) in blocker["resume"]["argv"]
    assert (
        "viewport/state"
        in " ".join(blocker["human_action_guide"]["evidence_to_return"]).lower()
    )
    report = (feature_dir / "implementation-summary.md").read_text(encoding="utf-8")
    assert "## Human Checks Needed" in report
    assert "evidence/ui-review.md" in report
    assert "Before you start" in report
    assert "If it fails" in report
    assert "Return to the agent" in report


def test_implementation_summary_renders_protected_ci_babysitter_guide(
    tmp_path: Path,
) -> None:
    project = tmp_path
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_basic_feature(feature_dir)
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "blockers": [
                    {
                        "classification": "external",
                        "owner": "maintainer",
                        "evidence": [
                            "protected pipeline is required for commit abc123"
                        ],
                        "exact_next_action": "Run the protected verify job for commit abc123",
                        "approval_question": "May the maintainer trigger the protected verify job?",
                        "unblock_criteria": "The verify job passes for commit abc123",
                        "implementation_can_continue": False,
                        "completion_impact": "mandatory_for_completion",
                    }
                ],
                "ui_verification": {"applicable": False},
            }
        ),
        encoding="utf-8",
    )

    payload = build_implementation_summary(project, feature_dir)

    blocker = payload["blockers"][0]
    guide = blocker["human_action_guide"]
    schema = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "workflow-blocker-schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(blocker)
    assert blocker["category"] == "external-system"
    assert blocker["human_action_required"] is True
    assert blocker["resume"]["argv"][:3] == [
        "specify",
        "implement",
        "resume-audit",
    ]
    assert str(feature_dir) in blocker["resume"]["argv"]
    assert guide["steps"][0]["command"] == (
        "git branch --show-current; git rev-parse HEAD; git status --short"
    )
    assert "Pipeline URL or ID" in guide["evidence_to_return"]
    report = (feature_dir / "implementation-summary.md").read_text(encoding="utf-8")
    for required in (
        "Confirm the exact revision",
        "Open the matching pipeline",
        "If it fails",
        "Pipeline URL or ID",
        "Resume:",
    ):
        assert required in report


def test_closeout_normalizes_malformed_task_lifecycle_blockers(tmp_path: Path) -> None:
    feature_dir = tmp_path / ".specify" / "features" / "001-demo"
    _write_basic_feature(feature_dir)
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "blockers": [
                    {
                        "classification": "technical",
                        "owner": "unexpected",
                        "evidence": ["owner field is corrupt"],
                        "exact_next_action": "Repair the lifecycle record",
                        "approval_question": None,
                        "unblock_criteria": "The lifecycle record validates",
                        "implementation_can_continue": False,
                        "completion_impact": "mandatory_for_completion",
                    },
                    {
                        "classification": "technical",
                        "owner": "agent",
                        "evidence": [],
                        "exact_next_action": "Repair the lifecycle record",
                        "approval_question": None,
                        "unblock_criteria": "The lifecycle record validates",
                        "implementation_can_continue": False,
                        "completion_impact": "mandatory_for_completion",
                    },
                ],
                "ui_verification": {"applicable": False},
            }
        ),
        encoding="utf-8",
    )
    blockers = implementation_closeout_blockers(
        feature_dir,
        resume_audit={
            "status": "fail",
            "trusted_terminal_state": False,
            "open_gaps": ["task lifecycle validation failed"],
        },
    )
    schema = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "workflow-blocker-schema.json"
        ).read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)

    assert len(blockers) == 3
    assert all(list(validator.iter_errors(blocker)) == [] for blocker in blockers)
    assert [blocker["code"] for blocker in blockers[:2]] == [
        "invalid-task-lifecycle-blocker",
        "invalid-task-lifecycle-blocker",
    ]
    assert all(blocker["owner"] == "agent" for blocker in blockers[:2])
    assert "invalid owner" in " ".join(blockers[0]["evidence"])
    assert "non-empty" in " ".join(blockers[1]["evidence"])


def test_implementation_helpers_reject_feature_paths_outside_project(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside-feature"
    outside.mkdir()

    with pytest.raises(ValueError, match="inside the current project"):
        audit_implement_resume(project, outside)
    with pytest.raises(ValueError, match="inside the current project"):
        build_implementation_summary(project, outside, write_report=False)


def test_implementation_summary_includes_packetized_review_artifacts(
    tmp_path: Path,
) -> None:
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
    assert (
        payload["completed_work"][0]["review_artifacts"]["task_review"]
        == payload["review_artifacts"]["task_reviews"]["T001"]
    )

    report = (feature_dir / "implementation-summary.md").read_text(encoding="utf-8")
    assert "## Review Artifacts" in report
    assert "implementation-review/ledger.json" in report
    assert "implementation-review/branch-review.md" in report
    assert "implementation-review/task-reviews/T001.json" in report
