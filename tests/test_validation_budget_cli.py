import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


runner = CliRunner()


def _run_in_project(project: Path, args: list[str]):
    previous = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(previous)


def _project_with_feature_epoch_policy(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / "specs" / "001-budget"
    feature.mkdir(parents=True)
    (project / ".specify").mkdir()
    (feature / "task-index.json").write_text(
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
                "tasks": [{"id": "T001"}],
            }
        ),
        encoding="utf-8",
    )
    return project, feature


def test_validation_epoch_cli_reserves_finishes_and_reports_shared_budget(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_feature_epoch_policy(tmp_path)
    relative_feature = feature.relative_to(project).as_posix()

    started = _run_in_project(
        project,
        [
            "implement",
            "validation-start",
            "--feature-dir",
            relative_feature,
            "--stage",
            "implement",
            "--purpose",
            "convergence",
            "--command",
            "pytest -q",
            "--task-id",
            "T001",
            "--format",
            "json",
        ],
    )
    assert started.exit_code == 0, started.output
    start_payload = json.loads(started.output)
    assert start_payload["run_id"] == "V1"
    assert len(start_payload["fingerprint"]) == 64
    assert start_payload["used_epochs"] == 1
    assert start_payload["remaining_epochs"] == 2

    finished = _run_in_project(
        project,
        [
            "implement",
            "validation-finish",
            "--feature-dir",
            relative_feature,
            "--run-id",
            "V1",
            "--status",
            "passed",
            "--evidence-ref",
            "implementation-review/validation-evidence/V1.txt",
            "--summary",
            "Shared convergence passed",
            "--format",
            "json",
        ],
    )
    assert finished.exit_code == 0, finished.output
    assert json.loads(finished.output)["status"] == "passed"

    reported = _run_in_project(
        project,
        [
            "implement",
            "validation-status",
            "--feature-dir",
            relative_feature,
            "--format",
            "json",
        ],
    )
    assert reported.exit_code == 0, reported.output
    payload = json.loads(reported.output)
    assert payload["used_epochs"] == 1
    assert payload["remaining_epochs"] == 2
    assert payload["runs"][0]["status"] == "passed"


def test_validation_epoch_cli_records_runner_interruption_and_reuses_gate(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_feature_epoch_policy(tmp_path)
    relative_feature = feature.relative_to(project).as_posix()
    common_start = [
        "implement",
        "validation-start",
        "--feature-dir",
        relative_feature,
        "--stage",
        "implement",
        "--purpose",
        "convergence",
        "--command",
        "pytest -q",
        "--task-id",
        "T001",
        "--fingerprint",
        "sha-a",
        "--format",
        "json",
    ]
    first = _run_in_project(project, common_start)
    assert first.exit_code == 0, first.output

    interrupted = _run_in_project(
        project,
        [
            "implement",
            "validation-finish",
            "--feature-dir",
            relative_feature,
            "--run-id",
            "V1",
            "--status",
            "interrupted",
            "--failure-kind",
            "runner_timeout",
            "--evidence-ref",
            "implementation-review/validation-evidence/V1-timeout.txt",
            "--summary",
            "Execution host stopped the command before a verdict.",
            "--format",
            "json",
        ],
    )
    assert interrupted.exit_code == 0, interrupted.output
    assert json.loads(interrupted.output)["status"] == "interrupted"

    retry = _run_in_project(project, common_start)
    assert retry.exit_code == 0, retry.output
    payload = json.loads(retry.output)
    assert payload["run_id"] == "V1"
    assert payload["attempt_id"] == "V1-A2"
    assert payload["used_epochs"] == 1
    assert payload["used_attempts"] == 2


def test_implement_deferral_cli_requires_exact_confirmation_digest(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_feature_epoch_policy(tmp_path)
    relative_feature = feature.relative_to(project).as_posix()
    task_index = json.loads(
        (feature / "task-index.json").read_text(encoding="utf-8")
    )
    task_index["acceptance_refs"] = ["FR-001"]
    (feature / "task-index.json").write_text(
        json.dumps(task_index), encoding="utf-8"
    )
    lifecycle_dir = feature / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "blockers": [
                    {
                        "classification": "external",
                        "owner": "user",
                        "evidence": "Device is unavailable.",
                        "exact_next_action": "Run the device check in Review.",
                        "approval_question": "Transfer this check to Review?",
                        "unblock_criteria": "Review records device evidence.",
                        "implementation_can_continue": True,
                        "completion_impact": "mandatory_for_completion",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal_path = project / "deferral-proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "blocker_refs": ["T001-B01"],
                "affected_task_ids": ["T001"],
                "affected_acceptance_refs": ["FR-001"],
                "deferred_validation_purposes": [],
                "exact_excluded_behavior": "Device evidence is unavailable.",
                "residual_risk": "Review may find device-specific drift.",
                "risk_severity": "medium",
                "claims_withheld": ["device verified"],
                "reopen_or_stop_condition": "Review must obtain device evidence.",
                "downstream_artifact": "implementation-handoff.json",
                "downstream_owner": "review",
                "defer_until": "review",
            }
        ),
        encoding="utf-8",
    )

    proposed = _run_in_project(
        project,
        [
            "implement",
            "deferral-propose",
            "--feature-dir",
            relative_feature,
            "--input",
            str(proposal_path),
            "--format",
            "json",
        ],
    )
    assert proposed.exit_code == 0, proposed.output
    proposal = json.loads(proposed.output)

    wrong_digest = _run_in_project(
        project,
        [
            "implement",
            "deferral-confirm",
            "--feature-dir",
            relative_feature,
            "--deferral-id",
            proposal["deferral_id"],
            "--proposal-sha256",
            "0" * 64,
            "--confirmation-source",
            "human-reply",
            "--statement",
            "同意移交到 Review，不算通过。",
            "--format",
            "json",
        ],
    )
    assert wrong_digest.exit_code == 10

    confirmed = _run_in_project(
        project,
        [
            "implement",
            "deferral-confirm",
            "--feature-dir",
            relative_feature,
            "--deferral-id",
            proposal["deferral_id"],
            "--proposal-sha256",
            proposal["proposal_sha256"],
            "--confirmation-source",
            "human-reply",
            "--statement",
            "同意移交到 Review，不算通过。",
            "--format",
            "json",
        ],
    )
    assert confirmed.exit_code == 0, confirmed.output
    assert json.loads(confirmed.output)["disposition"] == "transferred_to_review"
