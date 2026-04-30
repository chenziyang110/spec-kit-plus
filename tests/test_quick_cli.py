import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.learnings import read_learning_entries


runner = CliRunner()


def _write_status(workspace: Path, frontmatter: dict[str, str], body: str) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f'{key}: "{value}"')
    lines.append("---")
    lines.append(body.strip())
    (workspace / "STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _setup_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    quick_root = project / ".planning" / "quick"
    quick_root.mkdir(parents=True, exist_ok=True)
    return project, quick_root


def _invoke_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def test_quick_list_defaults_to_unfinished_items(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)

    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "executing"},
        "## Next Action\n- Add helper script",
    )
    _write_status(
        quick_root / "260417-002-align-cursor-quick-docs",
        {"id": "260417-002", "title": "Align docs", "status": "resolved", "closed_at": "2026-04-17T10:00:00Z"},
        "## Next Action\n- Archive this task",
    )

    result = _invoke_in_project(project, ["quick", "list"])

    assert result.exit_code == 0, result.stdout
    assert "260417-001" in result.stdout
    assert "Fix quick index sync" in result.stdout
    assert "260417-002" not in result.stdout


def test_quick_status_reads_status_md_as_source_of_truth(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)

    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "blocked"},
        "## Current Focus\nInvestigate stale index\n\n## Next Action\n- Rebuild index from STATUS.md",
    )
    (quick_root / "index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {
                        "id": "260417-001",
                        "title": "STALE TITLE",
                        "status": "executing",
                        "next_action": "STALE ACTION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(project, ["quick", "status", "260417-001"])

    assert result.exit_code == 0, result.stdout
    assert "Fix quick index sync" in result.stdout
    assert "blocked" in result.stdout.lower()
    assert "rebuild index from status.md" in result.stdout.lower()
    assert "STALE TITLE" not in result.stdout


def test_quick_archive_rejects_active_task(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)
    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "executing"},
        "## Next Action\n- Finish implementation",
    )

    result = _invoke_in_project(project, ["quick", "archive", "260417-001"])

    assert result.exit_code == 1
    assert "only resolved or blocked quick tasks can be archived" in result.stdout.lower()


def test_quick_index_can_be_rebuilt_when_missing(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)
    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "executing"},
        "## Next Action\n- Add index rebuild",
    )
    index_path = quick_root / "index.json"
    assert not index_path.exists()

    result = _invoke_in_project(project, ["quick", "list"])

    assert result.exit_code == 0, result.stdout
    assert index_path.exists()
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert any(task["id"] == "260417-001" for task in index_payload["tasks"])


def test_quick_list_command_prints_unfinished_tasks(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)

    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "blocked"},
        "## Next Action\n- Retry helper integration",
    )
    _write_status(
        quick_root / "260417-002-align-cursor-quick-docs",
        {"id": "260417-002", "title": "Align docs", "status": "resolved", "closed_at": "2026-04-17T10:00:00Z"},
        "## Next Action\n- Archive",
    )

    result = _invoke_in_project(project, ["quick", "list"])

    assert result.exit_code == 0, result.stdout
    assert "260417-001" in result.stdout
    assert "retry helper integration" in result.stdout.lower()
    assert "260417-002" not in result.stdout


def test_quick_status_command_prints_current_focus_and_next_action(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)

    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "executing"},
        "## Current Focus\nKeep helper and CLI in sync\n\n## Next Action\n- Run targeted tests",
    )

    result = _invoke_in_project(project, ["quick", "status", "260417-001"])

    assert result.exit_code == 0, result.stdout
    assert "executing" in result.stdout.lower()
    assert "keep helper and cli in sync" in result.stdout.lower()
    assert "run targeted tests" in result.stdout.lower()


def test_quick_close_command_requires_resolved_or_blocked(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)
    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "executing"},
        "## Next Action\n- Close after validation",
    )

    result = _invoke_in_project(project, ["quick", "close", "260417-001", "--status", "executing"])

    assert result.exit_code == 1
    assert "--status must be 'resolved' or 'blocked'" in result.stdout.lower()


def test_quick_archive_command_rejects_active_tasks(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)
    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "planned"},
        "## Next Action\n- Implement helper",
    )

    result = _invoke_in_project(project, ["quick", "archive", "260417-001"])

    assert result.exit_code == 1
    assert "only resolved or blocked quick tasks can be archived" in result.stdout.lower()


def test_quick_close_auto_captures_learning_from_retry_and_validation_state(tmp_path: Path):
    project, quick_root = _setup_project(tmp_path)
    _write_status(
        quick_root / "260417-001-fix-quick-index-sync",
        {"id": "260417-001", "title": "Fix quick index sync", "status": "executing"},
        """
## Current Focus
goal: keep the quick index consistent
current_focus: validate the recovery result
next_action: close after validation

## Execution
active_lane: one-subagent
join_point:
files_or_surfaces: scripts/powershell/quick-state.ps1
execution_fallback: none
blockers: []
recovery_action: rerun index rebuild once state is refreshed
retry_attempts: 1
blocker_reason: stale quick index snapshot

## Validation
planned_checks:
  - pytest tests/test_quick_cli.py -q
completed_checks:
  - pytest tests/test_quick_cli.py -q

## Summary Pointer
summary_path: .planning/quick/260417-001-fix-quick-index-sync/SUMMARY.md
resume_decision: resolved
""",
    )

    result = _invoke_in_project(project, ["quick", "close", "260417-001", "--status", "resolved"])

    assert result.exit_code == 0, result.stdout
    _, entries = read_learning_entries(project / ".planning" / "learnings" / "candidates.md")
    summaries = [entry.summary for entry in entries]
    assert "Retry the smallest recorded recovery step and rerun scoped checks before resolving a quick task" in summaries
