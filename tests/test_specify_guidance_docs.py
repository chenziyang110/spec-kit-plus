from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def _section(content: str, start: str, end: str) -> str:
    start_index = content.index(start)
    end_index = content.index(end, start_index)
    return content[start_index:end_index]


def test_quickstart_teaches_specify_to_plan_mainline():
    quickstart = _read("docs/quickstart.md")

    assert "move directly from `specify` to `plan`" in quickstart
    assert "$sp-specify" in quickstart
    assert "$sp-prd" in quickstart
    assert "/skill:sp-plan" in quickstart
    assert "/sp.specify" in quickstart
    assert "/sp.prd" in quickstart
    assert "`specify -> plan` as the default path" in quickstart
    assert "`specify` -> `deep-research` -> `plan`" in quickstart


def test_quickstart_declares_integration_specific_invocation_syntax():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    assert "Invocation syntax depends on the integration:" in quickstart
    assert "$sp-specify" in quickstart
    assert "$sp-prd" in quickstart
    assert "/skill:sp-specify" in quickstart
    assert "/skill:sp-prd" in quickstart
    assert "/sp.specify" in quickstart
    assert "/sp.prd" in quickstart
    assert "Canonical workflow names are integration-neutral" in quickstart
    assert "Slash-dot command integrations" in readme
    assert "Slash-dot command integrations" in quickstart
    assert "Slash-dot command integrations" in installation
    assert "Markdown command integrations" not in readme
    assert "Markdown command integrations" not in quickstart
    assert "Markdown command integrations" not in installation

    for content in (readme, quickstart, installation):
        assert "`/sp-*` is not universal for skills-backed integrations" in content
        assert "canonical workflow names" in content.lower()
        assert "$sp-plan" in content
        assert "$sp-prd" in content
        assert "/skill:sp-plan" in content
        assert "/skill:sp-prd" in content
        assert "/sp.plan" in content
        assert "/sp.prd" in content


def test_upgrade_doc_mentions_project_launcher_binding():
    upgrade = _read("docs/upgrade.md")

    assert "specify_launcher" in upgrade
    assert "project launcher" in upgrade.lower()
    assert "runtime" in upgrade.lower()


def test_quickstart_positions_clarify_correctly():
    quickstart = _read("docs/quickstart.md")
    lowered = quickstart.lower()

    assert "/sp-clarify" in quickstart
    assert "repair lane" in lowered or "needs deeper analysis before planning" in lowered


def test_guidance_docs_explain_skill_groups():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    assert "Core workflow skills" in readme
    assert "Support skills" in readme
    assert "Codex-only runtime" in readme
    assert "`auto`" in readme
    assert "`clarify`" in readme
    assert "`deep-research`" in readme
    assert "`prd`" in readme
    assert "`checklist`" in readme
    assert "`analyze`" in readme
    assert "`debug`" in readme
    assert "`explain`" in readme
    assert "`map-scan`" in readme
    assert "`map-build`" in readme
    assert "`sp-teams`" in readme

    assert "Core workflow skills" in quickstart
    assert "Support skills" in quickstart
    assert "Codex-only runtime" in quickstart
    skill_map = _section(quickstart, "## Skill Map", "For Codex team-mode execution")
    assert "`constitution`, `specify`, `plan`, `tasks`, `implement`" in skill_map
    assert "`map-scan`, `map-build`, `test-scan`, `test-build`, `auto`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `clarify`, `deep-research` (`research` alias), `checklist`, `analyze`, `debug`, `explain`" in skill_map
    assert "/sp-" not in skill_map


def test_quickstart_skill_map_and_guidance_use_canonical_names_not_claude_syntax():
    quickstart = _read("docs/quickstart.md")

    skill_map = _section(quickstart, "## Skill Map", "For Codex team-mode execution")
    support_guidance = _section(quickstart, "Use support skills when they solve a specific gap:", "Passive project learning layer:")

    for section in (skill_map, support_guidance):
        assert "/sp-" not in section

    assert "`map-scan` followed by `map-build`" in support_guidance
    assert "`deep-research` when a planning-ready spec still needs feasibility evidence" in support_guidance
    assert "`prd-scan` followed by `prd-build` as the existing-project reverse PRD lane" in support_guidance
    assert "does not automatically hand off to `plan`" in support_guidance
    assert "`analyze` as the required gate before implementation once `tasks.md` exists" in support_guidance
    assert "`fast` is only for trivial local fixes" in support_guidance
    assert "the shared `specify`, `plan`, `tasks`, `implement`, and `debug` workflows" in support_guidance


def test_quickstart_taskify_walkthrough_frames_literal_sp_examples_as_claude_style():
    quickstart = _read("docs/quickstart.md")
    walkthrough = _section(quickstart, "## Detailed Example: Building Taskify", "## Key Principles")

    assert "The following Taskify snippets use Claude-style `/sp-*` invocation syntax." in walkthrough
    assert "translate each literal command through the invocation matrix above" in walkthrough
    assert "### Step 2: Define Requirements with `specify`" in walkthrough
    assert "Once `specify` reaches planning-ready alignment, move directly to `plan`." in walkthrough
    assert "using the `checklist` workflow" in walkthrough
    assert "using the `tasks` workflow" in walkthrough
    assert "using `analyze`" in walkthrough
    assert "If `analyze` finds issues" in walkthrough
    assert "Define Requirements with `/sp-specify`" not in walkthrough
    assert "Once `/sp-specify`" not in walkthrough
    assert "using the `/sp-" not in walkthrough
