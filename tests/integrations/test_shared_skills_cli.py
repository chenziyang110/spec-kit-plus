"""Project skill destinations through the public installation commands."""

from pathlib import Path

from typer.testing import CliRunner

import specify_cli as cli
from specify_cli.agents import CommandRegistrar
from specify_cli.extensions import ExtensionRegistry
from specify_cli.integrations.manifest import IntegrationManifest


runner = CliRunner()


def invoke(*args):
    result = runner.invoke(cli.app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def init_here(agent, *args):
    return invoke(
        "init", "--here", "--force", "--no-git", "--ignore-agent-tools",
        "--integration", agent, "--script", "ps", *args,
    )


def test_shared_default_switches_renderer_and_keeps_custom_skill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom = Path(".agents/skills/local-build/SKILL.md")
    custom.parent.mkdir(parents=True)
    custom.write_text("Local build notes", encoding="utf-8")

    output = init_here("agy")
    shared_do = Path(".agents/skills/sp-do/SKILL.md")
    assert shared_do.is_file()
    assert "/sp-plan" in shared_do.read_text(encoding="utf-8")
    assert ".agents/skills" in output

    invoke("integration", "switch", "codex")
    assert "$sp-plan" in shared_do.read_text(encoding="utf-8")
    assert not Path(".codex/skills").exists()
    assert IntegrationManifest.load("codex", tmp_path).skill_layout == "shared"
    assert custom.read_text(encoding="utf-8") == "Local build notes"

    invoke("integration", "uninstall")
    assert not shared_do.exists()
    assert custom.is_file()


def test_native_fallback_and_migration_preserve_registered_skill_ownership(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_here("claude")
    assert Path(".claude/skills/sp-do/SKILL.md").is_file()
    assert not Path(".agents/skills").exists()
    invoke("integration", "switch", "codex", "--skills-layout", "native")
    invoke(
        "init", "--here", "--force", "--no-git", "--ignore-agent-tools",
        "--integration", "codex", "--script", "ps", "--workflow-profile", "advanced",
    )
    native = Path(".codex/skills")
    shared = Path(".agents/skills")
    classic = "sp-do/SKILL.md"
    advanced = "spx-do/SKILL.md"
    original = {name: (native / name).read_bytes() for name in (classic, advanced)}

    registry = ExtensionRegistry(tmp_path / ".specify/extensions")
    registry.add("widget", {"registered_commands": {"codex": ["sp.widget.go"]}})
    blocked = runner.invoke(cli.app, ["integration", "migrate-skills"])
    assert blocked.exit_code == 1
    assert "Remove the extension 'widget'" in blocked.output
    assert (native / classic).exists()
    registry.remove("widget")

    invoke("integration", "migrate-skills")
    assert all((shared / name).read_bytes() == data for name, data in original.items())
    assert not (native / classic).exists()
    assert not (native / advanced).exists()
    assert cli._get_skills_dir(tmp_path, "codex") == tmp_path / shared
    assert "Project skills: .agents/skills" in invoke("integration", "list")

    invoke("integration", "migrate-skills", "--skills-layout", "native")
    assert all((native / name).read_bytes() == data for name, data in original.items())


def test_switch_reactivates_dormant_native_skills_before_migration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_install_shared_infra", lambda *_: None)
    codex = IntegrationManifest("codex", tmp_path)
    classic = codex.record_file(".codex/skills/sp-do/SKILL.md", "classic workflow")
    advanced = codex.record_file(".codex/skills/spx-do/SKILL.md", "advanced workflow")
    original_manifest = codex.save().read_bytes()
    gemini = IntegrationManifest("gemini", tmp_path)
    gemini_command = gemini.record_file(".gemini/commands/sp.do.toml", "gemini workflow")
    gemini.save()
    cli._write_integration_json(tmp_path, "gemini", "ps")
    cli.save_init_options(tmp_path, {
        "integration": "gemini",
        "script": "ps",
        "workflow_profiles_by_integration": {"codex": ["classic", "advanced"]},
    })

    assert "Reactivating integration" in invoke("integration", "switch", "codex")
    assert codex.manifest_path.read_bytes() == original_manifest
    assert classic.read_text(encoding="utf-8") == "classic workflow"
    assert advanced.read_text(encoding="utf-8") == "advanced workflow"
    assert not gemini_command.exists()
    metadata = cli._read_integration_json(tmp_path)
    assert metadata["integration"] == "codex"
    assert metadata["workflow_profiles"] == ["classic", "advanced"]

    invoke("integration", "migrate-skills")
    assert not classic.exists()
    assert not advanced.exists()
    assert (tmp_path / ".agents/skills/sp-do/SKILL.md").read_text(encoding="utf-8") == "classic workflow"
    assert (tmp_path / ".agents/skills/spx-do/SKILL.md").read_text(encoding="utf-8") == "advanced workflow"


def test_shared_command_registrar_preserves_unowned_skill(tmp_path):
    manifest = IntegrationManifest("codex", tmp_path)
    manifest.skill_layout = "shared"
    manifest.save()
    custom = tmp_path / ".agents/skills/sp-widget-go/SKILL.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("User content", encoding="utf-8")
    (tmp_path / "go.md").write_text("Extension content", encoding="utf-8")
    commands = [{"name": "sp.widget.go", "file": "go.md"}]

    registrar = CommandRegistrar()
    assert registrar.register_commands("codex", commands, "widget", tmp_path, tmp_path) == []
    assert not registrar.may_write_shared_skill(tmp_path, custom, owner="codex")
    assert custom.read_text(encoding="utf-8") == "User content"
