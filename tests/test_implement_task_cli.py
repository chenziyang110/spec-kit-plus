import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


def _feature(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / "specs" / "001-cli-state"
    feature.mkdir(parents=True)
    (project / ".specify" / "memory").mkdir(parents=True)
    (project / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- Keep state deterministic.\n", encoding="utf-8"
    )
    (project / "src").mkdir()
    (project / "src" / "contract.py").write_text("# contract\n", encoding="utf-8")
    (feature / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "source_revision": 3,
                "validation_policy": {
                    "mode": "feature_epochs",
                    "max_epochs": 3,
                    "budget_scope": "implement-review",
                    "budget_ref": "implementation-review/validation-runs.json",
                    "heavy_gate_owner": "leader",
                },
                "tasks": [
                    {
                        "id": "T001",
                        "objective": "Implement the CLI-owned task",
                        "expected_write_scope": ["src/task.py"],
                        "read_scope": ["src/contract.py"],
                        "required_refs": ["src/contract.py"],
                        "verification": ["python -m compileall src"],
                        "acceptance": ["The task is implemented"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Implement the CLI-owned task\n", encoding="utf-8"
    )
    return project, feature


def _invoke(project: Path, args: list[str]):
    runner = CliRunner()
    previous = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(previous)


def test_implement_cli_owns_packet_result_and_task_transitions(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)

    next_result = _invoke(
        project,
        ["implement", "task-next", "--feature-dir", str(feature), "--format", "json"],
    )
    assert next_result.exit_code == 0, next_result.output
    assert json.loads(next_result.output)["task"]["task_id"] == "T001"

    packet = _invoke(
        project,
        [
            "implement",
            "packet-compile",
            "--feature-dir",
            str(feature),
            "--task-id",
            "T001",
            "--format",
            "json",
        ],
    )
    assert packet.exit_code == 0, packet.output
    assert "data" not in json.loads(packet.output)

    started = _invoke(
        project,
        [
            "implement",
            "task-start",
            "--feature-dir",
            str(feature),
            "--task-id",
            "T001",
            "--execution-mode",
            "delegated",
            "--format",
            "json",
        ],
    )
    assert started.exit_code == 0, started.output
    assert json.loads(started.output)["task_status"] == "in_progress"

    unmanaged_result = project / "result.json"
    unmanaged_result.write_text(
        '{"task_id":"T001","status":"success"}', encoding="utf-8"
    )
    rejected_file = _invoke(
        project,
        [
            "implement",
            "result-merge",
            "--feature-dir",
            str(feature),
            "--task-id",
            "T001",
            "--result-file",
            str(unmanaged_result),
            "--format",
            "json",
        ],
    )
    assert rejected_file.exit_code != 0
    assert "CLI-owned canonical worker-result" in rejected_file.output

    raw_result = json.dumps(
        {
            "task_id": "T001",
            "status": "success",
            "changed_files": ["src/task.py"],
            "validation_results": [
                {"command": "python -m compileall src", "status": "passed"}
            ],
            "summary": "Implemented task",
        }
    )
    merged = _invoke(
        project,
        [
            "implement",
            "result-merge",
            "--feature-dir",
            str(feature),
            "--task-id",
            "T001",
            "--result-json",
            raw_result,
            "--format",
            "json",
        ],
    )
    assert merged.exit_code == 0, merged.output
    assert json.loads(merged.output)["worker_status"] == "success"

    accepted = _invoke(
        project,
        [
            "implement",
            "task-accept",
            "--feature-dir",
            str(feature),
            "--task-id",
            "T001",
            "--format",
            "json",
        ],
    )
    assert accepted.exit_code == 0, accepted.output
    payload = json.loads(accepted.output)
    assert payload["task_status"] == "accepted"
    assert payload["next_task_id"] is None
    assert "- [x] T001" in (feature / "tasks.md").read_text(encoding="utf-8")
