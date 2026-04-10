from pathlib import Path

from specify_cli.codex_team.state_paths import (
    codex_team_state_root,
    dispatch_record_path,
    runtime_session_path,
)


def test_codex_team_state_root_is_under_specify_state(codex_team_project_root: Path):
    root = codex_team_state_root(codex_team_project_root)

    assert root == codex_team_project_root / ".specify" / "codex-team" / "state"


def test_runtime_session_path_uses_session_prefix(codex_team_project_root: Path):
    path = runtime_session_path(codex_team_project_root, "abc123")

    assert path == codex_team_project_root / ".specify" / "codex-team" / "state" / "session-abc123.json"


def test_dispatch_record_path_uses_dispatch_prefix(codex_team_project_root: Path):
    path = dispatch_record_path(codex_team_project_root, "req-7")

    assert path == codex_team_project_root / ".specify" / "codex-team" / "state" / "dispatch-req-7.json"
