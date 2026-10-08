"""Standalone DO keeps one runtime contract across native installation surfaces."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.agents import CommandRegistrar
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import load_runtime_launcher, write_runtime_launcher_config


ROOT = Path(__file__).resolve().parents[2]
SKILLS = (
    "agy", "claude", "codex", "cursor-agent", "grok", "kimi", "trae", "vibe", "zcode",
)
MAP_COMPANIONS = {"sp-map-scan", "sp-map-build", "sp-map-update"}


def install(project: Path, key: str, profile: str, script_type: str):
    binary = project.parent / "runtime-source" / "specify-runtime"
    binary.parent.mkdir(exist_ok=True)
    binary.write_bytes(b"renderer fixture only\n")
    write_runtime_launcher_config(project, binary)
    integration = get_integration(key)
    manifest = IntegrationManifest(key, project)
    integration.setup(
        project, manifest,
        parsed_options={"workflow_profile": profile}, script_type=script_type,
    )
    return integration, manifest


def assert_do_runtime_binding(project: Path, content: str) -> None:
    launcher = load_runtime_launcher(project)
    assert launcher is not None
    assert f"{launcher.command} playbook find" in content
    assert f"{launcher.command} api show do.start" in content
    assert "{{specify-subcmd:" not in content
    assert "{{spec-kit-include:" not in content
    assert "{{project-cognition-workflow}}" not in content
    assert "specify specify-runtime do" not in content
    assert "specify specify-runtime playbook" not in content


@pytest.mark.parametrize("key", SKILLS)
@pytest.mark.parametrize("profile,prefix", [("classic", "sp"), ("advanced", "spx")])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_do_renders_for_every_skill_profile(key, profile, prefix, script_type, tmp_path):
    project = tmp_path / f"{key}-{profile}-{script_type}"
    integration, manifest = install(project, key, profile, script_type)
    skills_dir = integration.skills_dest(project)
    skill_dir = skills_dir / f"{prefix}-do"
    entry = skill_dir / "SKILL.md"
    content = entry.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(content.split("---", 2)[1])
    assert frontmatter["description"].startswith(CommandRegistrar.USER_INVOKED_DESCRIPTION_PREFIX)
    assert entry.relative_to(project).as_posix() in manifest.files
    assert_do_runtime_binding(project, content)
    assert "references/operation-contract.md" in content
    metadata = yaml.safe_load((skill_dir / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert metadata["policy"]["allow_implicit_invocation"] is False

    reference = skill_dir / "references/operation-contract.md"
    contract = reference.read_text(encoding="utf-8")
    assert reference.relative_to(project).as_posix() in manifest.files
    for required in ("DoSession", "do-record-input", "expected_revision", "source", "playbook"):
        assert required in contract
    assert f"integration key `{key}`" in contract
    assert "__AGENT__" not in content + contract
    if profile == "advanced":
        assert {p.parent.name for p in skills_dir.glob("sp-*/SKILL.md")} == MAP_COMPANIONS
        assert not (skills_dir / "spec-kit-project-cognition-gate").exists()
    else:
        for name in ("INDEX.md", "closeout.md", "source-mutation.md"):
            path = skill_dir / "references" / name
            assert path.is_file()
            assert path.relative_to(project).as_posix() in manifest.files
        assert not any(skills_dir.glob("spx-*/SKILL.md"))
    assert not (project / ".specify/do").exists()
    assert not (project / ".specify/playbooks").exists()


@pytest.mark.parametrize("key", ["qwen", "gemini", "forge", "copilot"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_do_command_rendering_keeps_triggered_sidecars(key, script_type, tmp_path):
    project = tmp_path / key
    integration, manifest = install(project, key, "classic", script_type)
    command = integration.commands_dest(project) / integration.command_filename("do")
    content = command.read_text(encoding="utf-8")
    if key == "gemini":
        content = tomllib.loads(content)["prompt"]
    assert_do_runtime_binding(project, content)
    assert "references/do/operation-contract.md" in content
    for name in ("INDEX.md", "operation-contract.md", "closeout.md", "source-mutation.md"):
        reference = command.parent / "references/do" / name
        assert reference.is_file()
        assert reference.relative_to(project).as_posix() in manifest.files
        assert "__AGENT__" not in reference.read_text(encoding="utf-8")
    contract = (command.parent / "references/do/operation-contract.md").read_text(encoding="utf-8")
    assert f"integration key `{key}`" in contract
    if key == "forge":
        assert "$ARGUMENTS" not in content
        assert "{{parameters}}" in content
    if key == "copilot":
        companion = project / ".github/prompts/sp.do.prompt.md"
        assert companion.relative_to(project).as_posix() in manifest.files
        assert "agent: sp.do" in companion.read_text(encoding="utf-8")


@pytest.mark.parametrize("profile,prefix", [("classic", "sp"), ("advanced", "spx")])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_do_repair_restores_missing_contract_without_rewriting_user_data(profile, prefix, script_type, tmp_path):
    project = tmp_path / f"repair-{profile}"
    integration, manifest = install(project, "codex", profile, script_type)
    skill_dir = integration.skills_dest(project) / f"{prefix}-do"
    entry = skill_dir / "SKILL.md"
    edited = entry.read_bytes() + b"\n<!-- user-owned operation note -->\n"
    entry.write_bytes(edited)
    reference = skill_dir / "references/operation-contract.md"
    original = reference.read_bytes()
    reference.unlink()
    user_files = {
        ".specify/do/sessions/user-session/session.json": b'{"user":"session"}\n',
        ".specify/playbooks/user-method/revisions/1.json": b'{"user":"method"}\n',
    }
    for relative, data in user_files.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    before = dict(manifest.files)
    restored = integration.repair_runtime_assets(project, manifest, script_type=script_type)
    assert reference in restored
    assert reference.read_bytes() == original
    assert entry.read_bytes() == edited
    assert manifest.files == before
    for relative, data in user_files.items():
        assert (project / relative).read_bytes() == data
        assert relative not in manifest.files


def run_init(profile: str, script_type: str):
    result = CliRunner().invoke(
        app,
        [
            "init", "--here", "--force", "--ai", "codex",
            "--workflow-profile", profile, "--script", script_type,
            "--no-git", "--ignore-agent-tools",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    return result


@pytest.mark.parametrize("profile,prefix", [("classic", "sp"), ("advanced", "spx")])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
@pytest.mark.usefixtures("unified_runtime_env")
def test_real_init_installs_do_and_shared_playbook_schemas(profile, prefix, script_type, tmp_path, monkeypatch):
    project = tmp_path / f"init-{profile}-{script_type}"
    project.mkdir()
    monkeypatch.chdir(project)
    result = run_init(profile, script_type)
    assert f"${prefix}-do" in result.output
    core = IntegrationManifest.load("speckit", project)
    for name in ("playbook-definition.schema.json", "playbook-update.schema.json"):
        relative = f".specify/templates/artifacts/{name}"
        assert (project / relative).read_bytes() == (ROOT / "templates/artifacts" / name).read_bytes()
        assert relative in core.files
    manifest = IntegrationManifest.load("codex", project)
    relative = f".codex/skills/{prefix}-do/SKILL.md"
    assert relative in manifest.files
    assert_do_runtime_binding(project, (project / relative).read_text(encoding="utf-8"))
    assert not (project / ".specify/do").exists()
    assert not (project / ".specify/playbooks").exists()


@pytest.mark.parametrize("first,second", [("classic", "advanced"), ("advanced", "classic")])
@pytest.mark.usefixtures("unified_runtime_env")
def test_real_init_additive_profiles_preserve_do_edits_and_local_methods(first, second, tmp_path, monkeypatch):
    project = tmp_path / "coexistence"
    project.mkdir()
    monkeypatch.chdir(project)
    run_init(first, "sh")
    name = "sp-do" if first == "classic" else "spx-do"
    entry = project / ".codex/skills" / name / "SKILL.md"
    reference = entry.parent / "references/operation-contract.md"
    preserved = {
        entry: entry.read_bytes() + b"\n<!-- user-owned operation note -->\n",
        reference: reference.read_bytes() + b"\nUser-owned recovery note.\n",
        project / ".specify/do/sessions/existing/session.json": b'{"keep":"session"}\n',
        project / ".specify/playbooks/existing/revisions/1.json": b'{"keep":"method"}\n',
    }
    for path, data in preserved.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    run_init(second, "sh")
    assert {path: path.read_bytes() for path in preserved} == preserved
    manifest = IntegrationManifest.load("codex", project)
    for name in ("sp-do", "spx-do"):
        assert f".codex/skills/{name}/SKILL.md" in manifest.files
    config = json.loads((project / ".specify/init-options.json").read_text(encoding="utf-8"))
    assert config["installed_workflow_profiles"] == [first, second]
    for manifest_key in ("codex", "speckit"):
        files = IntegrationManifest.load(manifest_key, project).files
        assert not any(p.startswith((".specify/do/", ".specify/playbooks/")) for p in files)
