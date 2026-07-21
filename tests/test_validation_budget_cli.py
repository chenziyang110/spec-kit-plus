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
