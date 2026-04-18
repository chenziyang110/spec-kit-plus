from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def test_quickstart_teaches_specify_to_plan_mainline():
    quickstart = _read("docs/quickstart.md")

    assert "move directly from `/speckit.specify` to `/speckit.plan`" in quickstart
    assert "`/speckit.specify` to `/speckit.plan`" in quickstart or "`/speckit.specify` and `/speckit.plan`" in quickstart
    assert "`specify -> plan` as the default path" in quickstart


def test_quickstart_positions_spec_extend_correctly():
    quickstart = _read("docs/quickstart.md")
    lowered = quickstart.lower()

    assert "/speckit.spec-extend" in quickstart
    assert "optional enhancement path" in lowered or "needs deeper analysis before planning" in lowered


def test_guidance_docs_explain_skill_groups():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    assert "Core workflow skills" in readme
    assert "Support skills" in readme
    assert "Codex-only runtime" in readme
    assert "`spec-extend`" in readme
    assert "`checklist`" in readme
    assert "`analyze`" in readme
    assert "`explain`" in readme
    assert "`specify team`" in readme

    assert "Core workflow skills" in quickstart
    assert "Support skills" in quickstart
    assert "Codex-only runtime" in quickstart
    assert "/speckit.spec-extend" in quickstart
    assert "/speckit.checklist" in quickstart
    assert "/speckit.analyze" in quickstart


def test_guidance_docs_explain_handbook_navigation_system():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert "Generated projects include `PROJECT-HANDBOOK.md` as the root navigation artifact." in content
        assert "Deep project knowledge lives under `.specify/project-map/`." in content
        assert "Any code change that alters navigation meaning must update the handbook system." in content


def test_guidance_docs_explain_fast_quick_specify_routing():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "sp-fast" in content or "/speckit.fast" in content
        assert "sp-quick" in content or "/speckit.quick" in content
        assert "more than 3 files" in content
        assert "shared surface" in content
        assert "multiple independent capabilities" in content
        assert "compatibility" in content
        assert "acceptance criteria" in content


def test_guidance_docs_explain_resumable_quick_management():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert ".planning/quick/<id>-<slug>/" in content
        assert "index.json" in content
        assert "no arguments" in content or "with no arguments" in content
        assert "blocked" in content
        assert "specify quick list" in content
        assert "specify quick status" in content
        assert "specify quick close" in content
        assert "specify quick archive" in content


def test_repo_docs_share_same_workflow_guidance():
    readme = _read("README.md").lower()
    agents = _read("AGENTS.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    assert "specify -> plan" in readme
    assert "specify -> plan" in agents
    assert "specify -> plan" in quickstart


def test_agents_declares_native_delegation_defaults():
    agents = _read("AGENTS.md").lower()

    assert "native subagents or native delegation surface" in agents
    assert "for codex, that runtime surface is `specify team`" in agents
