from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_root_agents_documents_lane_first_recovery_rules() -> None:
    content = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "specify --help" in content
    assert "generated create-feature script" in lowered
    assert "do not invent" in lowered
    assert "specify create-feature" in lowered
    assert "## Lane Recovery Rules" in content
    assert "lane-first, not branch-first" in lowered
    assert "explicit `feature_dir`" in content
    assert "materialized worktree" in lowered
    assert "/sp.plan" in content
    assert ".specify/features/<feature>/" in content


def test_root_claude_context_documents_lane_first_recovery_rules() -> None:
    content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "AGENTS.md" in content
    assert "specify --help" in content
    assert "generated create-feature script" in lowered
    assert "do not invent" in lowered
    assert "specify create-feature" in lowered
    assert "## Lane Recovery Rules" in content
    assert "lane-first, not branch-first" in lowered
    assert "explicit `feature_dir`" in content
    assert "/sp.plan" in content
    assert ".specify/features/<feature>/" in content
