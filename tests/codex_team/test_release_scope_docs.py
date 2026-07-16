from pathlib import Path


def test_readme_describes_codex_only_first_release_scope():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "sp-teams" in readme
    assert "Codex-only" in readme or "Codex only" in readme
    assert "optional upgrade" in readme or "optional, non-blocking" in readme
    assert "execution_model: adaptive" in readme
    assert "leader-direct" in readme
    assert "one-subagent" in readme
    assert "parallel-subagents" in readme
    assert "just in time" in readme
    assert "managed-team" in readme
    assert "specify-teams-mcp" in readme
