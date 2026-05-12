from pathlib import Path

from specify_cli.implement_audit import audit_implement_resume


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
