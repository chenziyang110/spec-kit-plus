from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_readme_describes_sp_implement_as_leader_subagent_runtime() -> None:
    content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "sp-implement" in content
    assert "leader" in content
    assert "dispatch" in content or "subagent" in content
    assert "join point" in content
    assert "blocker" in content
    assert "retry" in content


def test_readme_mentions_sp_teams_watch_surface() -> None:
    content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "sp-teams watch" in content
    assert "full-screen" in content
    assert "members and flow" in content
