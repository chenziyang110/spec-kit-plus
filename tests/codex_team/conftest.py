from pathlib import Path

import pytest


@pytest.fixture
def codex_team_project_root(tmp_path: Path) -> Path:
    project = tmp_path / "codex-team-project"
    project.mkdir()
    return project
