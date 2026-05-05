import json
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook
from specify_cli.project_map_status import write_project_map_status, ProjectMapStatus


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-project-map-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_mark_dirty_hook_normalizes_reason(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "project_map.mark_dirty",
        {
            "reason": "workflow contract changed",
            "origin_command": "implement",
            "origin_feature_dir": "specs/001-demo",
            "origin_lane_id": "lane-001",
        },
    )

    assert result.status == "ok"
    payload = json.loads((project / ".specify" / "project-map" / "status.json").read_text(encoding="utf-8"))
    assert payload["dirty_reasons"] == ["workflow_contract_changed"]
    assert payload["dirty_origin_command"] == "implement"
    assert payload["dirty_origin_feature_dir"] == "specs/001-demo"
    assert payload["dirty_origin_lane_id"] == "lane-001"


def test_complete_refresh_hook_requires_git_baseline(tmp_path: Path):
    project = _create_project(tmp_path)
    write_project_map_status(
        project,
        ProjectMapStatus(
            last_mapped_commit="",
            last_mapped_at="2026-04-27T00:00:00Z",
            last_mapped_branch="feature/demo",
            freshness="stale",
            dirty=True,
            dirty_reasons=["shared_surface_changed"],
        ),
    )

    result = run_quality_hook(
        project,
        "project_map.complete_refresh",
        {},
    )

    assert result.status == "blocked"
    assert any("git" in message.lower() for message in result.errors)
