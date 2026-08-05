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


def test_result_path_for_quick_workspace_uses_canonical_handoff_location(
    tmp_path: Path,
):
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
    assert (
        payload["path"]
        .replace("\\", "/")
        .endswith(".planning/quick/001-fix/worker-results/lane-a.json")
    )


def test_result_submit_normalizes_and_writes_quick_result(tmp_path: Path):
    project = _create_project(tmp_path, integration="cursor-agent")
    workspace = project / ".planning" / "quick" / "001-fix"
    workspace.mkdir(parents=True, exist_ok=True)
    result_json = json.dumps(
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
            "--result-json",
            result_json,
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    stored = json.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert stored["status"] == "success"
    assert stored["reported_status"] == "done_with_concerns"
    assert stored["concerns"] == ["follow-up cleanup remains"]


def test_result_submit_rejects_obsolete_ui_result_fields(tmp_path: Path) -> None:
    project = _create_project(tmp_path, integration="cursor-agent")
    workspace = project / ".planning" / "quick" / "001-fix"
    workspace.mkdir(parents=True, exist_ok=True)
    result_json = json.dumps(
        {
            "task_id": "lane-a",
            "status": "success",
            "uiEvidence": [{"kind": "visual_capture", "ref": "evidence/screen.png"}],
        }
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
            "--result-json",
            result_json,
        ],
    )

    assert result.exit_code != 0
    assert "uiEvidence" in result.output
    assert not (workspace / "worker-results" / "lane-a.json").exists()


def test_result_submit_rejects_codex_implement_and_explains_native_and_durable_routes(
    tmp_path: Path,
):
    project = _create_project(tmp_path, integration="codex")

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
            "--result-json",
            json.dumps({"task_id": "T001", "status": "success"}),
        ],
    )

    assert result.exit_code != 0
    normalized_output = " ".join(result.output.split())
    assert "implement result-merge" in normalized_output
    assert "sp-teams submit-result" in normalized_output


def test_result_submit_accepts_codex_stage_owned_plan_and_tasks_lanes(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path, integration="codex")
    feature_dir = project / ".specify" / "features" / "001-feature"
    feature_dir.mkdir(parents=True)

    for command_name, directory in (
        ("plan", "planning/handoffs"),
        ("tasks", "task-generation/handoffs"),
    ):
        result = _invoke_in_project(
            project,
            [
                "result",
                "submit",
                "--command",
                command_name,
                "--feature-dir",
                str(feature_dir),
                "--lane-id",
                "lane-a",
                "--result-json",
                json.dumps({"task_id": "lane-a", "status": "success"}),
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert (
            payload["path"]
            .replace("\\", "/")
            .endswith(f".specify/features/001-feature/{directory}/lane-a.json")
        )
        assert "sp-teams" not in result.output


def test_result_path_for_codex_requires_request_id_without_traceback(tmp_path: Path):
    project = _create_project(tmp_path, integration="codex")

    result = _invoke_in_project(
        project,
        [
            "result",
            "path",
            "--command",
            "implement",
            "--feature-dir",
            "specs/001-feature",
            "--task-id",
            "T001",
        ],
    )

    assert result.exit_code != 0
    assert "Codex result handoff paths are runtime-managed" in result.output
    assert "--request-id <id>" in result.output
    assert "Traceback" not in result.output


def test_result_path_for_codex_request_id_uses_runtime_managed_path(tmp_path: Path):
    project = _create_project(tmp_path, integration="codex")

    result = _invoke_in_project(
        project,
        [
            "result",
            "path",
            "--command",
            "implement",
            "--request-id",
            "req-t001",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["integration"] == "codex"
    assert (
        payload["path"]
        .replace("\\", "/")
        .endswith(".specify/teams/state/results/req-t001.json")
    )
