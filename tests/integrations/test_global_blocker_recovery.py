"""Exercise effective global recovery contracts, including installed sidecars.

Discover command coverage from the real catalogs rather than a four-name list.
These tests check prompt delivery and protected boundaries, not LLM behavior.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from specify_cli import _install_shared_infra
from specify_cli.integrations import get_integration
from specify_cli.integrations.base import IntegrationBase, SkillsIntegration
from specify_cli.integrations.manifest import IntegrationManifest

ROOT = Path(__file__).resolve().parents[2]


def _compact(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).lower()


@pytest.fixture(
    scope="module",
    params=[
        ("codex", "classic", "sh"),
        ("codex", "advanced", "sh"),
        ("claude", "classic", "sh"),
        ("claude", "advanced", "sh"),
        ("gemini", "classic", "sh"),
        ("codex", "classic", "ps"),
        ("codex", "advanced", "ps"),
    ],
    ids=lambda row: "-".join(row),
)
def installed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory):
    agent, profile, script_type = request.param
    project = tmp_path_factory.mktemp(f"global-recovery-{agent}-{profile}-{script_type}")
    integration = get_integration(agent)
    assert integration is not None
    assert _install_shared_infra(project, script_type) is True
    manifest = IntegrationManifest(agent, project)
    created = integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": profile},
        script_type=script_type,
    )
    return project, integration, manifest, created, profile, script_type


def _entrypoints(installed) -> tuple[list[Path], list[Path]]:
    project, integration, _, created, profile, _ = installed
    templates = integration.list_command_templates()
    assert templates
    if isinstance(integration, SkillsIntegration):
        root = integration.skills_dest(project)
        classic_templates = (
            [p for p in templates if p.stem in integration.ADVANCED_CLASSIC_COMPANION_COMMANDS]
            if profile == "advanced" else templates
        )
        expected_classic = {
            root / ("sp-teams" if p.stem == "team" else f"sp-{p.stem.replace('.', '-')}") / "SKILL.md"
            for p in classic_templates
        }
        # Integration-owned commands (for example Claude implement-teams) are
        # also part of the installed denominator, not accidental extra files.
        classic = sorted({p for p in created if p.name == "SKILL.md" and p.parent.name.startswith("sp-")})
        assert expected_classic <= set(classic)
        if profile == "advanced":
            assert set(classic) == expected_classic
        advanced_templates = integration.list_advanced_skill_templates() if profile == "advanced" else []
        advanced = [root / p.name / "SKILL.md" for p in advanced_templates]
        assert set(root.glob("sp-*/SKILL.md")) == set(classic)
        assert set(root.glob("spx-*/SKILL.md")) == set(advanced)
    else:
        assert profile == "classic"
        by_name = {p.name: p for p in created}
        classic = [by_name[integration.command_filename(p.stem)] for p in templates]
        advanced = []
    assert classic or advanced
    assert all(path.is_file() for path in classic + advanced)
    return classic, advanced


def test_every_installed_entrypoint_reaches_the_full_recovery_contract(installed) -> None:
    project, _, _, _, _, _ = installed
    classic, advanced = _entrypoints(installed)
    shared_policy = project / ".specify/templates/workflow-blocker-template.md"
    assert shared_policy.is_file()
    assert "## recovery decision (agent-only)" in _compact(shared_policy)
    assert (project / ".specify/templates/workflow-blocker-schema.json").is_file()
    for path in classic:
        content = _compact(path)
        assert content.count("## blocked exit contract") == 1, path
        assert "all `sp-*` workflows must recover before exiting" in content, path
        assert ".specify/templates/workflow-blocker-template.md" in content, path
        assert "resume the exact interrupted gate in the same invocation" in content, path
        assert "read-only and stage boundaries" in content, path
    for path in advanced:
        content = _compact(path)
        assert content.count("## blocked exit contract") == 1, path
        assert "references/blocker-resolution.md" in content, path
        exit_reference = path.parent / "references/blocker-resolution.md"
        recovery_reference = path.parent / "references/autonomous-blocker-recovery.md"
        assert "every `spx-*` workflow" in _compact(exit_reference), path
        assert "before deciding that a failure is terminal" in _compact(exit_reference), path
        assert "references/autonomous-blocker-recovery.md" in _compact(exit_reference), path
        assert "all `spx-*` workflows" in _compact(recovery_reference), path
        assert ".specify/templates/workflow-blocker-template.md" in _compact(recovery_reference), path
        assert "resume the exact interrupted gate" in _compact(recovery_reference), path
        assert "read-only and stage boundaries" in _compact(recovery_reference), path


def test_owned_missing_recovery_files_are_repaired_without_overwriting_user_edits(installed) -> None:
    project, integration, manifest, _, profile, script_type = installed
    if not isinstance(integration, SkillsIntegration):
        pytest.skip("Missing skill-file repair does not apply to TOML commands")
    root = integration.skills_dest(project)
    prefix = "spx" if profile == "advanced" else "sp"
    entry = root / f"{prefix}-plan/SKILL.md"
    user_file = root / f"{prefix}-ask/SKILL.md"
    assert entry.is_file() and user_file.is_file()
    expected = entry.read_bytes()
    original_user = user_file.read_bytes()
    user_bytes = original_user + b"\n<!-- user-owned recovery note -->\n"
    reference = root / "spx-plan/references/autonomous-blocker-recovery.md"
    expected_reference = reference.read_bytes() if profile == "advanced" else None
    try:
        user_file.write_bytes(user_bytes)
        entry.unlink()
        if profile == "advanced":
            reference.unlink()
            integration.repair_missing_advanced_skill_files(project, manifest, script_type=script_type)
            assert reference.read_bytes() == expected_reference
        else:
            integration.repair_missing_classic_skill_files(project, manifest, script_type=script_type)
        assert entry.read_bytes() == expected
        assert user_file.read_bytes() == user_bytes
    finally:
        user_file.write_bytes(original_user)


def test_every_classic_source_command_gets_the_global_gate() -> None:
    commands = sorted((ROOT / "templates/commands").glob("*.md"))
    assert commands
    for command in commands:
        rendered = IntegrationBase.render_template_content(
            command.read_text(encoding="utf-8"), template_path=command
        )
        assert "All `sp-*` workflows must recover before exiting" in rendered, command
        assert rendered.count("## Blocked Exit Contract") == 1, command
        assert "{{spec-kit-include:" not in rendered, command


def test_future_classic_commands_receive_recovery_without_an_allowlist(tmp_path: Path) -> None:
    commands = tmp_path / "templates/commands"
    common = tmp_path / "templates/command-partials/common"
    commands.mkdir(parents=True)
    common.mkdir(parents=True)
    (common / "blocker-resolution.md").write_bytes(
        (ROOT / "templates/command-partials/common/blocker-resolution.md").read_bytes()
    )
    source = commands / "future-workflow.md"
    raw = "---\ndescription: Future workflow\n---\n\nFuture body.\n"
    rendered = IntegrationBase.render_template_content(raw, template_path=source)
    assert rendered.count("## Blocked Exit Contract") == 1
    assert "All `sp-*` workflows must recover before exiting" in rendered
    assert rendered.index("## Blocked Exit Contract") < rendered.index("Future body.")
    assert IntegrationBase.render_template_content(rendered, template_path=source) == rendered


def test_future_advanced_skills_receive_the_global_exit_reference(tmp_path: Path) -> None:
    integration = get_integration("codex")
    assert isinstance(integration, SkillsIntegration)
    source = tmp_path / "templates/advanced-skills/spx-future-workflow/SKILL.md"
    raw = "---\nname: spx-future-workflow\ndescription: Future workflow\n---\n\nFuture body.\n"
    rendered = integration._render_advanced_skill_content(
        source_path=source,
        raw=raw,
        project_root=tmp_path,
        script_type="sh",
        arg_placeholder="$ARGUMENTS",
    )
    assert rendered.count("## Blocked Exit Contract") == 1
    assert "references/blocker-resolution.md" in rendered
    assert rendered.index("## Blocked Exit Contract") < rendered.index("Future body.")


def test_wheel_includes_every_recovery_policy_owner() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        force_include = tomllib.load(stream)["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["templates/command-partials"] == "specify_cli/core_pack/command-partials"
    assert force_include["templates/advanced-skills"] == "specify_cli/core_pack/advanced-skills"
    for name in ("workflow-blocker-template.md", "workflow-blocker-schema.json"):
        assert force_include[f"templates/{name}"] == f"specify_cli/core_pack/templates/{name}"
