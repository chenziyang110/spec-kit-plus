from pathlib import Path

from specify_cli.implement_audit import audit_implement_resume
from specify_cli.execution.implementation_review import (
    TaskLedgerEntry,
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


def test_resolved_packetized_state_with_accepted_ledger_and_branch_review_passes(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_packetized_review_state(feature_dir)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True
    assert payload["recommended_tracker_status"] == "resolved"


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
