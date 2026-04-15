from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_fast_template_exists_and_defines_scope_gate() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "fast.md").read_text(encoding="utf-8").lower()

    assert "execute a trivial task directly" in content
    assert "scope gate" in content
    assert "at most 3 files" in content or "no more than 3 files" in content
    assert "no new dependencies" in content
    assert "no architecture changes" in content or "no api changes" in content
    assert "use `/sp.quick`" in content or "use `/sp-quick`" in content or "use `/sp.quick`" in content
    assert "do the work directly" in content
    assert "verify" in content


def test_fast_template_stays_lightweight() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "fast.md").read_text(encoding="utf-8").lower()

    assert "do not create spec.md" in content or "no spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "do not spawn" in content or "no subagents" in content
