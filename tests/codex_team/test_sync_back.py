from pathlib import Path

import pytest


def _seed_worker_file(project_root: Path, *, session_id: str = "default", worker_id: str = "worker-a") -> Path:
    worktree_root = project_root / ".specify" / "codex-team" / "worktrees" / session_id / worker_id
    file_path = worktree_root / "src" / "app.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("print('from worker')\n", encoding="utf-8")
    return file_path


def test_collect_sync_back_candidates_returns_worker_relative_paths(codex_team_project_root: Path):
    from specify_cli.codex_team.sync_back import collect_sync_back_candidates

    source = _seed_worker_file(codex_team_project_root)

    candidates = collect_sync_back_candidates(codex_team_project_root, session_id="default")

    assert len(candidates) == 1
    assert candidates[0]["source_path"] == str(source)
    assert candidates[0]["target_path"] == str(codex_team_project_root / "src" / "app.py")
    assert candidates[0]["relative_path"] == "src/app.py"


def test_apply_sync_back_refuses_dirty_workspace_without_override(monkeypatch, codex_team_project_root: Path):
    from specify_cli.codex_team.sync_back import apply_sync_back

    _seed_worker_file(codex_team_project_root)
    monkeypatch.setattr("specify_cli.codex_team.sync_back.workspace_has_uncommitted_changes", lambda project_root: True)

    with pytest.raises(RuntimeError, match="dirty"):
        apply_sync_back(codex_team_project_root, session_id="default", allow_dirty=False)


def test_apply_sync_back_copies_worker_files_back_to_main_workspace(monkeypatch, codex_team_project_root: Path):
    from specify_cli.codex_team.sync_back import apply_sync_back

    _seed_worker_file(codex_team_project_root)
    monkeypatch.setattr("specify_cli.codex_team.sync_back.workspace_has_uncommitted_changes", lambda project_root: False)

    result = apply_sync_back(codex_team_project_root, session_id="default", allow_dirty=False)

    target = codex_team_project_root / "src" / "app.py"
    assert result["copied_count"] == 1
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "print('from worker')\n"
