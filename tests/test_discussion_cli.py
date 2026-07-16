import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from tests.conftest import strip_ansi
from tests.test_discussion_state_runtime import RUNTIME_PATH, _write_confirmed_handoff


runner = CliRunner()


def _load_discussion_runtime():
    import importlib.util

    spec = importlib.util.spec_from_file_location("discussion_state_runtime_for_cli_tests", RUNTIME_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def _create_ready_discussion(project: Path, slug: str) -> tuple[object, Path, str]:
    runtime = _load_discussion_runtime()
    initialized = runtime.initialize_discussion(project, slug, slug.replace("-", " ").title())
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    feature_dir = project / ".specify" / "features" / f"001-{initialized['slug']}"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "entry_source": "sp-discussion",
                "discussion_slug": initialized["slug"],
                "source_contract": json_path.relative_to(project).as_posix(),
                "review_digest": review_digest,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return runtime, feature_dir, initialized["slug"]


def test_discussion_init_and_resume_json_emit_compact_turn_packet(tmp_path: Path):
    project, _discussion_root = _setup_project(tmp_path)

    initialized = _invoke_in_project(
        project,
        ["discussion", "init", "Agent-friendly discussion", "--slug", "agent-discussion", "--json"],
    )
    resumed = _invoke_in_project(project, ["discussion", "resume", "agent-discussion", "--json"])

    assert initialized.exit_code == 0, initialized.stdout
    assert resumed.exit_code == 0, resumed.stdout
    init_payload = json.loads(initialized.stdout)
    resume_payload = json.loads(resumed.stdout)
    assert init_payload["slug"] == "agent-discussion"
    assert resume_payload["turn_packet"]["discussion_slug"] == "agent-discussion"
    assert resume_payload["turn_packet"]["persistence_mode"] == "frontstage-only"


def test_discussion_checkpoint_json_updates_dynamic_turn_context(tmp_path: Path):
    project, _discussion_root = _setup_project(tmp_path)
    _invoke_in_project(
        project,
        ["discussion", "init", "Checkpoint discussion", "--slug", "checkpoint-discussion"],
    )

    result = _invoke_in_project(
        project,
        [
            "discussion",
            "checkpoint",
            "checkpoint-discussion",
            "--summary",
            "Human frontstage is confirmed.",
            "--phase",
            "decide",
            "--decision",
            "Keep typed state backstage.",
            "--recommendation",
            "Use the shared runtime.",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["discussion"]["lifecycle_phase"] == "decide"
    assert payload["discussion"]["turn_packet"]["confirmed_decisions"] == [
        "Keep typed state backstage."
    ]


def test_discussion_write_handoff_writes_agent_only_contract(tmp_path: Path):
    project, _discussion_root = _setup_project(tmp_path)
    _invoke_in_project(
        project,
        ["discussion", "init", "Canonical handoff", "--slug", "canonical-handoff"],
    )
    payload = json.loads(
        (Path(__file__).resolve().parents[1] / "templates" / "discussion-handoff-template.json").read_text(
            encoding="utf-8"
        )
    )
    payload["discussion_slug"] = "canonical-handoff"
    payload["handoff_goal"] = "Generate one canonical requirement contract."
    payload["agent_requirement_contract"]["target_need"] = "A deterministic handoff contract."
    payload["must_preserve"] = [
        {
            "id": "MP-001",
            "type": "decision",
            "claim": "JSON remains canonical.",
            "source": "user confirmation",
            "downstream_requirement": "Preserve the agent-only JSON contract.",
            "blocking_level": "hard",
            "owner": "sp-discussion",
            "latest_resolve_phase": "review",
            "status": "confirmed",
        }
    ]
    input_path = project / "handoff-draft.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _invoke_in_project(
        project,
        [
            "discussion",
            "write-handoff",
            "canonical-handoff",
            "--input",
            str(input_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    written = json.loads(result.stdout)
    assert written["review_digest"]
    contract_path = Path(written["json_path"])
    assert contract_path.is_file()
    assert "markdown_path" not in written
    assert not contract_path.with_suffix(".md").exists()


def test_discussion_validate_and_mark_ready_json_use_runtime_gate(tmp_path: Path):
    project, _discussion_root = _setup_project(tmp_path)
    runtime = _load_discussion_runtime()
    initialized = runtime.initialize_discussion(project, "validated-handoff", "Validated handoff")
    _write_confirmed_handoff(runtime, project, initialized["slug"])

    validation = _invoke_in_project(
        project,
        ["discussion", "validate-handoff", initialized["slug"], "--json"],
    )
    ready = _invoke_in_project(project, ["discussion", "mark-ready", initialized["slug"], "--json"])

    assert validation.exit_code == 0, validation.stdout
    assert ready.exit_code == 0, ready.stdout
    assert json.loads(validation.stdout)["valid"] is True
    assert json.loads(ready.stdout)["discussion"]["status"] == "handoff-ready"


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


def test_discussion_list_json_preserves_cjk_paths_with_non_utf8_inherited_encoding(
    tmp_path: Path, monkeypatch
):
    project = tmp_path / "PI项目研究"
    project.mkdir()
    project, discussion_root = _setup_project(project)
    workspace = _write_discussion(
        discussion_root,
        "cjk-path",
        status="exploring",
        summary="CJK path encoding",
    )
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    monkeypatch.setenv("PYTHONIOENCODING", "gbk")

    result = _invoke_in_project(project, ["discussion", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    workspace_path = payload["discussions"][0]["workspace_path"]
    assert "\ufffd" not in workspace_path
    assert workspace_path == str(workspace.resolve())


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
    assert "only closed completed or abandoned discussions can be archived" in strip_ansi(result.stdout).lower()


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
    _runtime, feature_dir, slug = _create_ready_discussion(project, "workflow-template-management")

    consumed_result = _invoke_in_project(
        project,
        [
            "discussion",
            "mark-consumed",
            slug,
            "--feature-dir",
            feature_dir.relative_to(project).as_posix(),
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
    assert f"- consumed_by_feature_dir: {feature_dir.relative_to(project).as_posix()}" in state_text
    assert "- next_command: none" in state_text


def test_discussion_mark_consumed_can_archive_closed_session(tmp_path: Path):
    project, discussion_root = _setup_project(tmp_path)
    _runtime, feature_dir, slug = _create_ready_discussion(project, "workflow-template-management")

    result = _invoke_in_project(
        project,
        [
            "discussion",
            "mark-consumed",
            slug,
            "--feature-dir",
            feature_dir.relative_to(project).as_posix(),
            "--archive",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert not (discussion_root / "workflow-template-management").exists()
    assert (discussion_root / "archive" / "workflow-template-management" / "discussion-state.md").exists()


def test_discussion_list_is_read_only_when_index_is_missing(tmp_path: Path):
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
    assert not (discussion_root / "index.json").exists()
    assert "handoff-ready-demo" in result.stdout
    assert "archived-demo" in result.stdout
