from __future__ import annotations

import json
import os
from pathlib import Path

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from typer.testing import CliRunner

from specify_cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLASSIC_DESIGN = PROJECT_ROOT / "templates" / "commands" / "design.md"
CLASSIC_REFERENCES = PROJECT_ROOT / "templates" / "command-references" / "design"
ADVANCED_DESIGN = PROJECT_ROOT / "templates" / "advanced-skills" / "spx-design"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_router_contract(content: str, *, public_entry: str) -> None:
    lowered = content.lower()
    compact = " ".join(lowered.split())
    assert "single public entry point" in lowered
    assert "task_type: create | refine | audit" in content
    assert "input_strategy: context | synthesize" in content
    assert "synthesize is an input strategy, not a terminal task type" in compact
    assert "resume before reclassification" in lowered
    assert "approval, feedback, and continuation" in compact
    assert f"{public_entry}:create" in content
    assert f"{public_entry}:refine" in content
    assert f"{public_entry}:audit" in content
    assert "do not register or expose" in lowered


def _assert_consumer_contract(content: str) -> None:
    lowered = content.lower()
    compact = " ".join(lowered.split())
    assert "first formal consumer" in lowered
    assert "direct-delivery consumer" in lowered
    assert "sp-specify" in lowered or "spx-specify" in lowered
    assert "sp-quick" in lowered or "spx-quick" in lowered
    assert "sp-review" in lowered or "spx-review" in lowered
    assert "must not silently retarget" in lowered
    assert "exact current approval digests" in lowered
    assert "audit pass" in lowered
    assert "discussion" in lowered
    assert "not a formal design-contract consumer" in compact


def test_classic_design_uses_prompt_routing_and_explicit_consumers() -> None:
    command = _read(CLASSIC_DESIGN)
    router = _read(CLASSIC_REFERENCES / "task-router.md")
    consumers = _read(CLASSIC_REFERENCES / "consumer-contract.md")

    assert "references/task-router.md" in command
    assert "references/consumer-contract.md" in command
    _assert_router_contract(router, public_entry="sp-design")
    _assert_consumer_contract(consumers)


def test_advanced_design_preserves_the_same_routing_contract() -> None:
    skill = _read(ADVANCED_DESIGN / "SKILL.md")
    router = _read(ADVANCED_DESIGN / "references" / "task-router.md")
    consumers = _read(ADVANCED_DESIGN / "references" / "consumer-contract.md")

    assert "references/task-router.md" in skill
    assert "references/consumer-contract.md" in skill
    _assert_router_contract(router, public_entry="spx-design")
    _assert_consumer_contract(consumers)
    lowered_skill = skill.lower()
    assert "every project-wide `refine`" in lowered_skill
    assert "new immutable review round" in lowered_skill

    surface_map = json.loads(
        _read(ADVANCED_DESIGN.parent / "_shared" / "surface-map.json")
    )
    references = surface_map["skills"]["spx-design"]["references"]
    assert "spx-design/references/task-router.md" in references
    assert "spx-design/references/consumer-contract.md" in references


def test_quick_pins_the_approved_design_snapshot_for_direct_delivery() -> None:
    classic_quick = _read(
        PROJECT_ROOT
        / "templates"
        / "command-references"
        / "quick"
        / "packetized-work.md"
    )
    advanced_quick = _read(
        PROJECT_ROOT / "templates" / "advanced-skills" / "spx-quick" / "SKILL.md"
    )

    for content in (classic_quick, advanced_quick):
        assert "preview/manifest/handoff SHA-256" in content
        assert "DS-*" in content
        assert "DH-*" in content
        assert "must not silently adopt a later design approval" in content.lower()


def test_design_routing_is_documented_as_a_cross_profile_product_contract() -> None:
    for path in (
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "PROJECT-HANDBOOK.md",
        PROJECT_ROOT / "templates" / "project-handbook-template.md",
        PROJECT_ROOT / "AGENTS.md",
    ):
        content = _read(path).lower()
        assert "create/refine/audit" in content, path
        assert "synthesis" in content, path
        assert "sp-specify" in content, path
        assert "sp-quick" in content, path
        assert "silently" in content and "retarget" in content, path


def test_classic_passive_router_preserves_design_types_and_consumers() -> None:
    content = " ".join(
        _read(
            PROJECT_ROOT
            / "templates"
            / "passive-skills"
            / "spec-kit-workflow-routing"
            / "SKILL.md"
        )
        .lower()
        .split()
    )
    assert "one natural-language entrypoint" in content
    assert "create/refine/audit" in content
    assert "synthesis is an input strategy" in content
    assert "first formal consumer" in content
    assert "direct-delivery consumer" in content
    assert "must not silently retarget" in content


def test_design_brief_persists_the_prompt_route() -> None:
    content = _read(PROJECT_ROOT / "templates" / "design-brief-template.md")
    assert "task_type: null" in content
    assert "input_strategy: null" in content
    assert "route_reason: null" in content


def test_init_start_here_teaches_the_prompt_router_and_consumers() -> None:
    content = " ".join(
        _read(PROJECT_ROOT / "src" / "specify_cli" / "__init__.py").split()
    )
    assert '"design", "create, refine, or audit' in content
    assert "one prompt-routed design entry" in content
    assert "formal adoption through" in content
    assert "direct delivery through" in content


def test_classic_init_start_here_exposes_one_prompt_routed_design_skill(
    tmp_path: Path,
) -> None:
    project = tmp_path / "classic-design-start-here"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = CliRunner().invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "codex",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    output = " ".join(result.output.split())
    assert result.exit_code == 0, result.output
    assert "$sp-design" in output
    assert "one prompt-routed design entry" in output
    assert "$sp-specify" in output
    assert "$sp-quick" in output


def test_advanced_init_start_here_exposes_the_same_design_route(
    tmp_path: Path,
) -> None:
    project = tmp_path / "advanced-design-start-here"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = CliRunner().invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "codex",
                "--script",
                "sh",
                "--workflow-profile",
                "advanced",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    output = " ".join(result.output.split())
    assert result.exit_code == 0, result.output
    assert "$spx-design" in output
    assert "create, refine, or audit one prompt-routed design system" in output
    assert "formal adoption through spx-specify" in output
    assert "direct delivery through spx-quick" in output


def test_generated_codex_design_skill_keeps_one_public_entrypoint(
    tmp_path: Path,
) -> None:
    project = tmp_path / "codex-design-router"
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", project)
    integration.setup(project, manifest, script_type="sh")

    skills_dir = integration.skills_dest(project)
    design_dir = skills_dir / "sp-design"
    skill = _read(design_dir / "SKILL.md")
    router = _read(design_dir / "references" / "task-router.md")
    consumers = _read(design_dir / "references" / "consumer-contract.md")

    assert "references/task-router.md" in skill
    assert "references/consumer-contract.md" in skill
    _assert_router_contract(router, public_entry="sp-design")
    _assert_consumer_contract(consumers)
    assert not any(":" in path.name for path in skills_dir.iterdir())
