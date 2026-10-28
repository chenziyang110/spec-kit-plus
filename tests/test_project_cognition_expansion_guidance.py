"""Exercise expansion commands from installed workflow prompts against the CLI."""

import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import write_runtime_launcher_config
from specify_cli.specify_runtime import project_runtime_launcher_arg


ROOT = Path(__file__).resolve().parents[1]


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def _expansion_commands(content: str) -> list[list[str]]:
    commands = [
        command
        for command in re.findall(r"`([^`\r\n]*\bcognition expand [^`\r\n]+)`", content)
        if command.startswith(f"{project_runtime_launcher_arg()} cognition expand ")
        and ("--id " in command or "--ref " in command)
    ]
    assert commands, "installed cognition guidance has no executable expansion example"
    replacements = {
        "<id>": "exp-guidance-no-existing-bundle",
        "<expansion-ref>": "exp-guidance-no-existing-bundle",
        "<section>": "related_paths",
    }
    return [
        [
            replacements.get(token.strip("'\""), token.strip("'\""))
            for token in shlex.split(command, posix=os.name != "nt")
        ]
        for command in commands
    ]


def test_advanced_expansion_guidance_binds_runtime_reference_fields() -> None:
    content = (
        ROOT / "templates/advanced-skills/_shared/project-cognition.md"
    ).read_text(encoding="utf-8")

    assert "expansion_ref.id" in content
    assert "expansion_ref.available_sections" in content
    assert "cognition expand --ref" not in content
    assert (
        "only when coverage or contradictory live evidence requires more map detail"
        in content
    )


@pytest.mark.parametrize("profile", ["classic", "advanced"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_installed_expansion_commands_reach_runtime_diagnostics(
    tmp_path: Path,
    built_unified_runtime: Path,
    profile: str,
    script_type: str,
    record_property,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    write_runtime_launcher_config(project, built_unified_runtime)
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": profile},
        script_type=script_type,
    )
    skills = integration.skills_dest(project)
    if profile == "advanced":
        references = sorted(skills.glob("spx-*/references/project-cognition.md"))
        assert len(references) == 30
        references.append(skills / "references/project-cognition.md")
    else:
        references = [skills / "sp-quick/SKILL.md"]

    commands: set[tuple[str, ...]] = set()
    for reference in references:
        content = reference.read_text(encoding="utf-8")
        assert "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE" not in content
        for argv in _expansion_commands(content):
            assert "--ref" not in argv, reference
            assert "--id" in argv and "--section" in argv, reference
            assert not any("<" in value or ">" in value for value in argv)
            commands.add(tuple(argv))

    record_property("rendered_reference_count", len(references))
    record_property(
        "runtime_sha256", hashlib.sha256(built_unified_runtime.read_bytes()).hexdigest()
    )
    before = _file_hashes(project)
    observations = []
    for command in sorted(commands):
        # Windows CreateProcess does not resolve argv[0] against subprocess cwd.
        # Resolve the installed prompt's launcher, preserving every runtime arg.
        launcher = (project / command[0]).resolve(strict=True)
        assert launcher.is_relative_to(project.resolve())
        assert launcher.is_file()
        assert (
            hashlib.sha256(launcher.read_bytes()).digest()
            == hashlib.sha256(built_unified_runtime.read_bytes()).digest()
        )
        result = subprocess.run(
            (str(launcher), *command[1:]),
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert "flag provided but not defined" not in result.stderr, result.stderr
        assert result.returncode in (0, 10), (result.returncode, result.stderr)
        payload = json.loads(result.stdout)["data"]
        assert payload["status"] == "missing_expansion", payload
        assert payload["id"] == "exp-guidance-no-existing-bundle"
        assert payload["recommended_next_action"] == "rerun_project_cognition_compass"
        assert payload["epistemic_contract"]["graph_only_claims_allowed"] is False
        assert payload["epistemic_contract"]["live_verification_required"] is True
        observations.append(
            {
                "argv": [str(launcher), *command[1:]],
                "native_exit": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    assert _file_hashes(project) == before
    record_property("native_observations", json.dumps(observations))
    record_property("unchanged_fixture_files", len(before))
