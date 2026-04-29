from pathlib import Path


def test_readme_describes_codex_only_first_release_scope():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "sp-teams" in readme
    assert "Codex-only" in readme or "Codex only" in readme
    assert "optional upgrade" in readme or "optional, non-blocking" in readme
    assert "single-lane" in readme
    assert "native-multi-agent" in readme
    assert "sidecar-runtime" in readme
    assert "specify-teams-mcp" in readme
