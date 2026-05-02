import json
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "compaction-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_quick_status(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260502-001"',
                'slug: "demo"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_compaction_build_writes_json_and_markdown(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.compaction.build",
        {"command_name": "quick", "workspace": str(workspace), "trigger": "before_stop"},
    )

    assert result.status == "ok"
    compaction_path = project / ".specify" / "runtime" / "compaction" / "quick-260502-001-demo" / "latest.json"
    markdown_path = compaction_path.with_suffix(".md")
    assert compaction_path.exists()
    assert markdown_path.exists()

    payload = json.loads(compaction_path.read_text(encoding="utf-8"))
    assert payload["identity"]["command_name"] == "quick"
    assert payload["phase_state"]["next_action"] == "integrate results"
    assert "resume_cue" in payload


def test_compaction_read_warns_when_artifact_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.compaction.read",
        {"command_name": "quick", "workspace": str(workspace)},
    )

    assert result.status == "warn"
    assert result.data["exists"] is False


def test_context_monitor_embeds_compaction_refresh_reason(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.context.monitor",
        {"command_name": "quick", "workspace": str(workspace), "trigger": "before_stop"},
    )

    assert result.status == "warn"
    assert result.data["compaction"]["should_refresh"] is True
    assert result.data["compaction"]["reason"] == "before_stop"
