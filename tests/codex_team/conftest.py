from pathlib import Path
import json

import pytest


@pytest.fixture
def codex_team_project_root(tmp_path: Path) -> Path:
    project = tmp_path / "codex-team-project"
    project.mkdir()
    project_map_dir = project / ".specify" / "project-map"
    project_map_dir.mkdir(parents=True, exist_ok=True)
    (project_map_dir / "status.json").write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": "",
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "",
                "freshness": "missing",
                "last_refresh_reason": "seeded-test",
                "dirty": False,
                "dirty_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    return project
