from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_fast_template_exists_and_defines_scope_gate() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "fast.md").read_text(encoding="utf-8").lower()

    assert "read `project-handbook.md`" in content
    assert ".specify/project-map/status.json" in content
    assert "project-map freshness helper" in content
    assert "freshness is `missing` or `stale`" in content
    assert "freshness is `possibly_stale`" in content
    assert "shared surfaces" in content
    assert "risky coordination points" in content
    assert "change-propagation hotspots" in content
    assert "verification entry points" in content
    assert "known unknowns" in content
    assert "if `project-handbook.md` or `.specify/project-map/` is missing" in content
    assert "redirect to `/sp-quick` so the navigation system can be rebuilt safely" in content
    assert "execute a trivial task directly" in content
    assert "scope gate" in content
    assert "at most 3 files" in content or "no more than 3 files" in content
    assert "no new dependencies" in content
    assert "no architecture changes" in content or "no api changes" in content
    assert "use `/sp.quick`" in content or "use `/sp-quick`" in content or "use `/sp.quick`" in content
    assert "do the work directly" in content
    assert "verify" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-codebase` before the final report" in content
    assert "if that refresh would break the fast-path scope" in content
    assert "mark `.specify/project-map/status.json` dirty" in content


def test_fast_template_stays_lightweight() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "fast.md").read_text(encoding="utf-8").lower()

    assert "do not create spec.md" in content or "no spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "do not spawn" in content or "no subagents" in content


def test_fast_template_defines_explicit_upgrade_triggers() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "fast.md").read_text(encoding="utf-8").lower()

    assert "upgrade to `/sp-quick` immediately if" in content
    assert "more than 3 files" in content
    assert "shared surface" in content
    assert "change-propagation hotspot" in content
    assert "known unknowns" in content
    assert "needs research" in content or "research or clarification" in content
    assert "upgrade to `/sp-specify` immediately if" in content
    assert "new workflow" in content
    assert "compatibility" in content
    assert "acceptance criteria" in content
