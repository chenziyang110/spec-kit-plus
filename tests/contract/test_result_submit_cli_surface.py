"""Contract tests for the generic delegated-result CLI surface."""

from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "result-submit-cli"
    project.mkdir()
    specify_dir = project / ".specify"
    specify_dir.mkdir()
    (specify_dir / "integration.json").write_text(
        json.dumps({"integration": "claude"}),
        encoding="utf-8",
    )
    return project


def _invoke_in_project(project: Path, args: list[str]):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args)
    finally:
        os.chdir(old_cwd)
    return result


def test_result_submit_rejects_pending_placeholder_payload(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    result_file = project / "pending-result.json"
    result_file.write_text(
        json.dumps(
            {
                "task_id": "lane-a",
                "status": "pending",
                "validation_results": [
                    {
                        "command": "pytest -q",
                        "status": "skipped",
                        "output": "NOT RUN - replace with actual command output after execution",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "result",
            "submit",
            "--command",
            "quick",
            "--result-file",
            str(result_file),
            "--workspace",
            ".planning/quick/001-fix",
            "--lane-id",
            "lane-a",
        ],
    )

    assert result.exit_code != 0
    lowered = result.output.lower()
    assert "pending result templates cannot be written" in lowered
    assert "real success, blocked, or failed result" in lowered
