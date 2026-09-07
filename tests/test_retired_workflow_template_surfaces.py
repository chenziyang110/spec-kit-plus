import json
import re
from pathlib import Path

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RETIRED_CLASSIC_TEMPLATES = (
    PROJECT_ROOT / "templates" / "commands" / "prd.md",
    PROJECT_ROOT / "templates" / "commands" / "research.md",
)
RETIRED_SPX_SKILLS = (
    PROJECT_ROOT / "templates" / "advanced-skills" / "spx-prd",
    PROJECT_ROOT / "templates" / "advanced-skills" / "spx-research",
)


def test_retired_alias_workflow_templates_are_not_source_surfaces() -> None:
    for path in RETIRED_CLASSIC_TEMPLATES:
        assert not path.exists(), path
    for path in RETIRED_SPX_SKILLS:
        assert not path.exists(), path

    surface_map = json.loads(
        (
            PROJECT_ROOT
            / "templates"
            / "advanced-skills"
            / "_shared"
            / "surface-map.json"
        ).read_text(encoding="utf-8")
    )
    skills = surface_map["skills"]
    assert "spx-prd" not in skills
    assert "spx-research" not in skills
    assert "spx-prd-scan" in skills
    assert "spx-prd-build" in skills
    assert "spx-deep-research" in skills


def test_retired_alias_workflows_are_not_installed_for_new_skill_profiles(tmp_path) -> None:
    integration = get_integration("codex")

    classic_root = tmp_path / "classic"
    classic_manifest = IntegrationManifest("codex", classic_root)
    integration.setup(
        classic_root,
        classic_manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )
    classic_skills = integration.skills_dest(classic_root)
    assert not (classic_skills / "sp-prd" / "SKILL.md").exists()
    assert not (classic_skills / "sp-research" / "SKILL.md").exists()
    assert (classic_skills / "sp-prd-scan" / "SKILL.md").exists()
    assert (classic_skills / "sp-prd-build" / "SKILL.md").exists()
    assert (classic_skills / "sp-deep-research" / "SKILL.md").exists()

    advanced_root = tmp_path / "advanced"
    advanced_manifest = IntegrationManifest("codex", advanced_root)
    integration.setup(
        advanced_root,
        advanced_manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    advanced_skills = integration.skills_dest(advanced_root)
    assert not (advanced_skills / "spx-prd" / "SKILL.md").exists()
    assert not (advanced_skills / "spx-research" / "SKILL.md").exists()
    assert (advanced_skills / "spx-prd-scan" / "SKILL.md").exists()
    assert (advanced_skills / "spx-prd-build" / "SKILL.md").exists()
    assert (advanced_skills / "spx-deep-research" / "SKILL.md").exists()


def test_retired_alias_workflow_skills_are_pruned_only_when_unmodified(tmp_path) -> None:
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    skills = integration.skills_dest(tmp_path)

    manifest.record_file(
        (skills / "sp-prd" / "SKILL.md").relative_to(tmp_path),
        "---\nname: sp-prd\n---\nold generated prd alias\n",
    )
    manifest.record_file(
        (skills / "sp-prd" / "agents" / "openai.yaml").relative_to(tmp_path),
        "interface:\n  display_name: SP PRD\n",
    )
    modified_research = manifest.record_file(
        (skills / "sp-research" / "SKILL.md").relative_to(tmp_path),
        "---\nname: sp-research\n---\nold generated research alias\n",
    )
    modified_research.write_text(
        "---\nname: sp-research\n---\nuser customized research alias\n",
        encoding="utf-8",
    )

    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )

    assert not (skills / "sp-prd").exists()
    assert (skills / "sp-research" / "SKILL.md").exists()
    prd_skill_rel = (skills / "sp-prd" / "SKILL.md").relative_to(tmp_path).as_posix()
    prd_metadata_rel = (
        skills / "sp-prd" / "agents" / "openai.yaml"
    ).relative_to(tmp_path).as_posix()
    research_skill_rel = (
        skills / "sp-research" / "SKILL.md"
    ).relative_to(tmp_path).as_posix()
    assert prd_skill_rel not in manifest.files
    assert prd_metadata_rel not in manifest.files
    assert research_skill_rel in manifest.files


def test_retired_alias_command_files_are_pruned_only_when_unmodified(tmp_path) -> None:
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)
    commands = integration.commands_dest(tmp_path)

    manifest.record_file(
        (commands / "sp.prd.toml").relative_to(tmp_path),
        "prompt = \"old generated prd\"\n",
    )
    modified_research = manifest.record_file(
        (commands / "sp.research.toml").relative_to(tmp_path),
        "prompt = \"old generated research\"\n",
    )
    modified_research.write_text(
        "prompt = \"user customized research\"\n",
        encoding="utf-8",
    )

    integration.setup(tmp_path, manifest, script_type="sh")

    assert not (commands / "sp.prd.toml").exists()
    assert (commands / "sp.research.toml").exists()
    prd_command_rel = (commands / "sp.prd.toml").relative_to(tmp_path).as_posix()
    research_command_rel = (
        commands / "sp.research.toml"
    ).relative_to(tmp_path).as_posix()
    assert prd_command_rel not in manifest.files
    assert research_command_rel in manifest.files


def test_retired_advanced_alias_skills_are_pruned_only_when_unmodified(tmp_path) -> None:
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    skills = integration.skills_dest(tmp_path)

    manifest.record_file(
        (skills / "spx-prd" / "SKILL.md").relative_to(tmp_path),
        "---\nname: spx-prd\n---\nold generated advanced prd alias\n",
    )
    manifest.record_file(
        (skills / "spx-prd" / "agents" / "openai.yaml").relative_to(tmp_path),
        "interface:\n  display_name: SPX PRD\n",
    )
    modified_research = manifest.record_file(
        (skills / "spx-research" / "SKILL.md").relative_to(tmp_path),
        "---\nname: spx-research\n---\nold generated advanced research alias\n",
    )
    modified_research.write_text(
        "---\nname: spx-research\n---\nuser customized advanced research alias\n",
        encoding="utf-8",
    )

    integration.setup(
        tmp_path,
        manifest,
        # Retired surfaces are global cleanup, independent of which profile is
        # selected for this upgrade pass.
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )

    assert not (skills / "spx-prd").exists()
    assert (skills / "spx-research" / "SKILL.md").exists()
    prd_skill_rel = (skills / "spx-prd" / "SKILL.md").relative_to(tmp_path).as_posix()
    prd_metadata_rel = (
        skills / "spx-prd" / "agents" / "openai.yaml"
    ).relative_to(tmp_path).as_posix()
    research_skill_rel = (
        skills / "spx-research" / "SKILL.md"
    ).relative_to(tmp_path).as_posix()
    assert prd_skill_rel not in manifest.files
    assert prd_metadata_rel not in manifest.files
    assert research_skill_rel in manifest.files


def test_active_templates_do_not_point_users_to_retired_alias_workflows() -> None:
    active_sources = [
        PROJECT_ROOT / "templates" / "workflow-state-template.md",
        PROJECT_ROOT / "templates" / "advanced-skills" / "_shared" / "project-learning.md",
        PROJECT_ROOT / "templates" / "advanced-skills" / "spx-prd-scan" / "SKILL.md",
        PROJECT_ROOT / "templates" / "passive-skills" / "project-to-prd" / "SKILL.md",
        PROJECT_ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-learning"
        / "SKILL.md",
    ]
    for path in active_sources:
        content = path.read_text(encoding="utf-8")
        assert re.search(r"\bspx-prd(?!-scan|-build)\b", content) is None
        assert re.search(r"\bspx-research\b", content) is None
        assert re.search(r"\bsp-research\b", content) is None
        assert re.search(r"\bsp-prd(?!-scan|-build)\b", content) is None
