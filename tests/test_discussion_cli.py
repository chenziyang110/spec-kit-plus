import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from tests.conftest import strip_ansi


runner = CliRunner()


def _setup_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path
    discussion_root = project / ".specify" / "discussions"
    discussion_root.mkdir(parents=True, exist_ok=True)
    return project, discussion_root


def _write_discussion(
    discussion_root: Path,
    slug: str,
    *,
    status: str,
    summary: str,
    updated_at: str = "2026-06-10T00:00:00Z",
    next_command: str = "none",
    archived: bool = False,
) -> Path:
    workspace = discussion_root / ("archive" if archived else "") / slug
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "discussion-state.md").write_text(
        "\n".join(
            [
                f"# Discussion State: {slug}",
                "",
                "## Current Command",
                "",
                "- active_command: sp-discussion",
                "- state_surface: discussion-state",
                f"- status: {status}",
                f"- slug: {slug}",
                f"- updated_at: {updated_at}",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: discussion-only",
                f"- summary: {summary}",
                "",
                "## Session Routing",
                "",
                "- current_stage: handoff-ready",
                f"- current_topic: {summary}",
                "",
                "## Handoff",
                "",
                "- handoff_to_specify: handoff-to-specify.md",
                "- handoff_to_specify_json: handoff-to-specify.json",
                "- quality_gate_status: user_confirmed",
                "- handoff_requested_by_user: true",
                f"- next_command: {next_command}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return workspace


def _invoke_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def test_discussion_list_defaults_to_unclosed_discussions(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _write_discussion(
        discussion_root,
        "settings-provider-import-export",
        status="handoff-ready",
        summary="Settings provider import/export",
        next_command="sp-specify",
    )
    _write_discussion(
        discussion_root,
        "completed-workflow-cleanup",
        status="completed",
        summary="Completed workflow cleanup",
    )
    _write_discussion(
        discussion_root,
        "archived-cleanup",
        status="completed",
        summary="Archived cleanup",
        archived=True,
    )

    result = _invoke_in_project(project, ["discussion", "list"])

    assert result.exit_code == 0, result.stdout
    assert "settings-provider-import-export" in result.stdout
    assert "settings provider import/export" in result.stdout.lower()
    assert "completed-workflow-cleanup" not in result.stdout
    assert "archived-cleanup" not in result.stdout


def test_discussion_archive_rejects_handoff_ready_until_closed(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _write_discussion(
        discussion_root,
        "workflow-template-management",
        status="handoff-ready",
        summary="Workflow template management",
    )

    result = _invoke_in_project(project, ["discussion", "archive", "workflow-template-management"])

    assert result.exit_code == 1
    assert "only completed or abandoned discussions can be archived" in strip_ansi(result.stdout).lower()


def test_discussion_close_then_archive_removes_session_from_default_list(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _write_discussion(
        discussion_root,
        "workflow-template-management",
        status="handoff-ready",
        summary="Workflow template management",
    )

    close_result = _invoke_in_project(
        project,
        ["discussion", "close", "workflow-template-management", "--status", "completed"],
    )
    archive_result = _invoke_in_project(project, ["discussion", "archive", "workflow-template-management"])
    list_result = _invoke_in_project(project, ["discussion", "list"])

    assert close_result.exit_code == 0, close_result.stdout
    assert archive_result.exit_code == 0, archive_result.stdout
    assert list_result.exit_code == 0, list_result.stdout
    assert "workflow-template-management" not in list_result.stdout
    assert (discussion_root / "archive" / "workflow-template-management" / "discussion-state.md").exists()


def test_discussion_mark_consumed_closes_handoff_ready_session(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _write_discussion(
        discussion_root,
        "workflow-template-management",
        status="handoff-ready",
        summary="Workflow template management",
        next_command="sp-specify",
    )

    consumed_result = _invoke_in_project(
        project,
        [
            "discussion",
            "mark-consumed",
            "workflow-template-management",
            "--feature-dir",
            ".specify/features/009-workflow-template-management",
        ],
    )
    list_result = _invoke_in_project(project, ["discussion", "list"])
    status_result = _invoke_in_project(project, ["discussion", "status", "workflow-template-management"])

    assert consumed_result.exit_code == 0, consumed_result.stdout
    assert "marked discussion workflow-template-management consumed" in strip_ansi(consumed_result.stdout).lower()
    assert list_result.exit_code == 0, list_result.stdout
    assert "workflow-template-management" not in list_result.stdout
    assert status_result.exit_code == 0, status_result.stdout
    state_text = (discussion_root / "workflow-template-management" / "discussion-state.md").read_text(
        encoding="utf-8"
    )
    assert "- status: completed" in state_text
    assert "- handoff_consumption_status: consumed" in state_text
    assert "- consumed_by_feature_dir: .specify/features/009-workflow-template-management" in state_text
    assert "- next_command: none" in state_text


def test_discussion_mark_consumed_can_archive_closed_session(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _write_discussion(
        discussion_root,
        "workflow-template-management",
        status="handoff-ready",
        summary="Workflow template management",
        next_command="sp-specify",
    )

    result = _invoke_in_project(
        project,
        [
            "discussion",
            "mark-consumed",
            "workflow-template-management",
            "--feature-dir",
            ".specify/features/009-workflow-template-management",
            "--archive",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert not (discussion_root / "workflow-template-management").exists()
    assert (discussion_root / "archive" / "workflow-template-management" / "discussion-state.md").exists()


def test_discussion_list_rebuilds_index_with_archive_state(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _write_discussion(
        discussion_root,
        "handoff-ready-demo",
        status="handoff-ready",
        summary="Handoff-ready demo",
    )
    _write_discussion(
        discussion_root,
        "archived-demo",
        status="completed",
        summary="Archived demo",
        archived=True,
    )

    result = _invoke_in_project(project, ["discussion", "list", "--all"])

    assert result.exit_code == 0, result.stdout
    index_payload = json.loads((discussion_root / "index.json").read_text(encoding="utf-8"))
    indexed = {item["slug"]: item for item in index_payload["discussions"]}
    assert indexed["handoff-ready-demo"]["archived"] is False
    assert indexed["archived-demo"]["archived"] is True
