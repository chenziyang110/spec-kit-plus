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
