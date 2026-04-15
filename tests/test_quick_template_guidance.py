from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_template_exists_and_defines_lightweight_tracked_flow() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "ad-hoc task" in content or "small, ad-hoc task" in content
    assert "lightweight" in content
    assert ".planning/quick/" in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "skip the full" in content and "specify" in content
    assert "summary.md" in content or "summary artifact" in content


def test_quick_template_preserves_quality_guardrails() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "scope gate" in content
    assert "small but non-trivial" in content or "not for trivial work" in content
    assert "redirect to `/sp-fast`" in content or "use `/sp-fast`" in content
    assert "redirect to `/sp-specify`" in content or "use `/sp-specify`" in content
    assert "validate" in content
    assert "verify" in content
