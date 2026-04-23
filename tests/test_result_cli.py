import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


def _create_project(tmp_path: Path, *, integration: str) -> Path:
    project = tmp_path / f"{integration}-result-cli"
    project.mkdir()
    specify_dir = project / ".specify"
    specify_dir.mkdir()
    (specify_dir / "integration.json").write_text(
        json.dumps({"integration": integration}),
        encoding="utf-8",
    )
    return project


def _invoke_in_project(project: Path, args: list[str]):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)
    return result


def test_result_path_for_quick_workspace_uses_canonical_handoff_location(tmp_path: Path):
    project = _create_project(tmp_path, integration="claude")
    workspace = project / ".planning" / "quick" / "001-fix"
    workspace.mkdir(parents=True, exist_ok=True)

    result = _invoke_in_project(
        project,
        [
            "result",
            "path",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--lane-id",
            "lane-a",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["command"] == "quick"
    assert payload["integration"] == "claude"
    assert payload["path"].replace("\\", "/").endswith(".planning/quick/001-fix/worker-results/lane-a.json")


def test_result_submit_normalizes_and_writes_quick_result(tmp_path: Path):
    project = _create_project(tmp_path, integration="cursor-agent")
    workspace = project / ".planning" / "quick" / "001-fix"
    workspace.mkdir(parents=True, exist_ok=True)
    result_file = project / "worker-result.json"
    result_file.write_text(
        json.dumps(
            {
                "taskId": "T201",
                "status": "DONE_WITH_CONCERNS",
                "files_changed": ["src/feature.py"],
                "message": "done with concerns",
                "issues": ["follow-up cleanup remains"],
                "validationResults": [
                    {"command": "pytest -q", "status": "passed", "output": "1 passed"}
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
            "--workspace",
            str(workspace),
            "--lane-id",
            "lane-a",
            "--result-file",
            str(result_file),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    stored = json.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert stored["status"] == "success"
    assert stored["reported_status"] == "done_with_concerns"
    assert stored["concerns"] == ["follow-up cleanup remains"]


def test_result_submit_rejects_codex_projects_and_redirects_to_team_surface(tmp_path: Path):
    project = _create_project(tmp_path, integration="codex")
    result_file = project / "worker-result.json"
    result_file.write_text(
        json.dumps({"task_id": "T001", "status": "success"}, ensure_ascii=False),
        encoding="utf-8",
    )

    result = _invoke_in_project(
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
        ],
    )

    assert result.exit_code != 0
    assert "specify team submit-result" in result.output
