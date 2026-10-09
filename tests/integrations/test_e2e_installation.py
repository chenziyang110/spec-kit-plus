"""E2E renderer contracts and separate real init/upgrade coverage.

Integration.setup renders native surfaces; only specify init installs shared
infrastructure. Keep the two boundaries separate and inspect their real manifests.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest

ROOT = Path(__file__).resolve().parents[2]
HELPERS = (
    "e2e_scenarios.py", "e2e_coverage.py", "e2e_runner.py", "e2e_pytest_reporter.py",
)
SKILLS = (
    "agy", "claude", "codex", "cursor-agent", "grok", "kimi", "trae", "vibe", "zcode",
)
MAP_COMPANIONS = {"sp-map-scan", "sp-map-build", "sp-map-update"}


def install(key: str, project: Path, profile: str, script_type: str):
    integration = get_integration(key)
    assert integration is not None
    manifest = IntegrationManifest(key, project)
    integration.setup(
        project, manifest,
        parsed_options={"workflow_profile": profile}, script_type=script_type,
    )
    return integration, manifest


def run_init(profile: str, script_type: str):
    # The caller changes cwd only to its pytest-owned disposable project.
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


def assert_helpers(project: Path) -> None:
    # Shared scripts belong to the core manifest, not the agent renderer manifest.
    core = IntegrationManifest.load("speckit", project)
    for name in HELPERS:
        relative = f".specify/scripts/shared/{name}"
        installed = project / relative
        assert installed.is_file(), f"E2E helper was not installed: {relative}"
        assert installed.read_bytes() == (ROOT / "scripts/shared" / name).read_bytes()
        assert relative in core.files
    process = subprocess.run(
        [sys.executable, str(project / ".specify/scripts/shared/e2e_scenarios.py"), "catalog"],
        cwd=project, text=True, capture_output=True, timeout=30, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert len(json.loads(process.stdout)["dimensions"]) >= 14
    for name in ("e2e_coverage.py", "e2e_runner.py"):
        process = subprocess.run(
            [sys.executable, str(project / ".specify/scripts/shared" / name), "--help"],
            cwd=project, text=True, capture_output=True, timeout=30, check=False,
        )
        assert process.returncode == 0, process.stderr


@pytest.mark.parametrize("key", SKILLS)
@pytest.mark.parametrize("profile,prefix", [("classic", "sp"), ("advanced", "spx")])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_e2e_renders_for_every_skill_profile(key, profile, prefix, script_type, tmp_path):
    project = tmp_path / f"{key}-{profile}-{script_type}"
    integration, manifest = install(key, project, profile, script_type)
    skill_dir = integration.skills_dest(project) / f"{prefix}-e2e"
    skill = skill_dir / "SKILL.md"
    assert skill.is_file()
    assert skill.relative_to(project).as_posix() in manifest.files
    text = skill.read_text(encoding="utf-8")
    assert "e2e_scenarios.py" in text
    assert "{{spec-kit-include:" not in text
    assert "{{project-cognition-workflow}}" not in text
    assert "{{specify-subcmd:" not in text
    assert "e2e.task-accept" in text and "e2e.review-submit" in text
    assert "e2e.scope-add" in text and "e2e.close" in text
    assert "--include-schema" in text
    metadata = yaml.safe_load((skill_dir / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert metadata["policy"]["allow_implicit_invocation"] is False
    if profile == "advanced":
        reference = skill_dir / "references/scenario-design.md"
        assert reference.is_file()
        assert reference.relative_to(project).as_posix() in manifest.files
        assert {p.parent.name for p in integration.skills_dest(project).glob("sp-*/SKILL.md")} == MAP_COMPANIONS
        assert not (integration.skills_dest(project) / "spec-kit-project-cognition-gate").exists()
    else:
        assert not any(integration.skills_dest(project).glob("spx-*/SKILL.md"))


@pytest.mark.parametrize("key,extension", [("qwen", "md"), ("gemini", "toml")])
def test_e2e_command_based_rendering(key, extension, tmp_path):
    project = tmp_path / key
    integration, manifest = install(key, project, "classic", "sh")
    command = integration.commands_dest(project) / f"sp.e2e.{extension}"
    assert command.is_file()
    assert command.relative_to(project).as_posix() in manifest.files
    text = command.read_text(encoding="utf-8")
    if extension == "toml":
        text = tomllib.loads(text)["prompt"]
    assert "e2e_scenarios.py" in text
    assert "{{spec-kit-include:" not in text
    assert "{{project-cognition-workflow}}" not in text
    assert "{{specify-subcmd:" not in text
    assert "e2e.task-accept" in text and "e2e.review-submit" in text
    assert "--include-schema" in text


@pytest.mark.parametrize("profile,prefix", [("classic", "sp"), ("advanced", "spx")])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
@pytest.mark.usefixtures("unified_runtime_env")
def test_real_init_installs_helpers_and_advertises_e2e(profile, prefix, script_type, tmp_path, monkeypatch):
    project = tmp_path / f"init-{profile}-{script_type}"
    project.mkdir()
    monkeypatch.chdir(project)
    result = run_init(profile, script_type)
    assert f"${prefix}-e2e" in result.output
    assert "scenario-first E2E" in result.output
    assert_helpers(project)
    manifest = IntegrationManifest.load("codex", project)
    assert f".codex/skills/{prefix}-e2e/SKILL.md" in manifest.files


@pytest.mark.parametrize("first,second", [("classic", "advanced"), ("advanced", "classic")])
@pytest.mark.usefixtures("unified_runtime_env")
def test_real_init_additive_profiles_preserve_user_edits(first, second, tmp_path, monkeypatch):
    project = tmp_path / "coexistence"
    project.mkdir()
    monkeypatch.chdir(project)
    run_init(first, "sh")
    assert_helpers(project)
    first_name = "sp-e2e" if first == "classic" else "spx-e2e"
    first_skill = project / ".codex/skills" / first_name / "SKILL.md"
    helper = project / ".specify/scripts/shared/e2e_scenarios.py"
    edited_skill = first_skill.read_bytes() + b"\n<!-- user-owned E2E note -->\n"
    edited_helper = helper.read_bytes() + b"\n# user-owned E2E note\n"
    first_skill.write_bytes(edited_skill)
    helper.write_bytes(edited_helper)
    run_init(second, "sh")
    assert first_skill.read_bytes() == edited_skill
    assert helper.read_bytes() == edited_helper
    manifest = IntegrationManifest.load("codex", project)
    core = IntegrationManifest.load("speckit", project)
    for name in ("sp-e2e", "spx-e2e"):
        relative = f".codex/skills/{name}/SKILL.md"
        assert (project / relative).is_file()
        assert relative in manifest.files
    assert ".specify/scripts/shared/e2e_scenarios.py" in core.check_modified()
