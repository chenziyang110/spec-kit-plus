import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "result-control-plane"
    project.mkdir()
    (project / ".specify").mkdir()
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "cursor-agent"}), encoding="utf-8"
    )
    (project / "specs" / "001-feature").mkdir(parents=True)
    return project


def _invoke(project: Path, args: list[str]):
    runner = CliRunner()
    previous = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(previous)


def test_result_submit_accepts_inline_json_without_agent_authored_temp_file(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    raw = json.dumps(
        {
            "task_id": "T001",
            "status": "success",
            "changed_files": ["src/feature.py"],
            "validation_results": [
                {"command": "python -m compileall src", "status": "passed"}
            ],
            "summary": "Implemented feature",
        }
    )

    result = _invoke(
        project,
        [
            "result",
            "submit",
            "--command",
            "implement",
            "--feature-dir",
            "specs/001-feature",
            "--task-id",
            "T001",
            "--result-json",
            raw,
        ],
    )

    assert result.exit_code == 0, result.output
    receipt = json.loads(result.output)
    assert receipt["worker_status"] == "success"
    assert "payload" not in receipt
    assert len(result.output.encode("utf-8")) < 4096
    stored = json.loads(
        (project / "specs" / "001-feature" / "worker-results" / "T001.json").read_text(
            encoding="utf-8"
        )
    )
    assert stored["status"] == "success"


def test_result_submit_rejects_agent_authored_result_files(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result_file = project / "result.json"
    result_file.write_text('{"task_id":"T001","status":"success"}', encoding="utf-8")

    result = _invoke(
        project,
        [
            "result",
            "submit",
            "--command",
            "implement",
            "--feature-dir",
            "specs/001-feature",
            "--task-id",
            "T001",
            "--result-file",
            str(result_file),
            "--result-json",
            '{"task_id":"T001","status":"success"}',
        ],
    )

    assert result.exit_code != 0
    help_result = _invoke(project, ["result", "submit", "--help"])
    assert help_result.exit_code == 0
    assert "--result-json" in help_result.output
    assert "--result-file" not in help_result.output
    assert not (
        project / "specs" / "001-feature" / "worker-results" / "T001.json"
    ).exists()
