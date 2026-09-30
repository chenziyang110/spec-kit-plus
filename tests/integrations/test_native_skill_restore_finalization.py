"""Missing skill repair must retain native metadata without adopting user files."""

import os
import subprocess
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.claude import ARGUMENT_HINTS
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.mark.parametrize("integration_key", ["claude", "grok", "vibe"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_missing_native_skill_restores_original_bytes_and_preserves_user_files(
    tmp_path, integration_key, script_type, profile
):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path, manifest,
        parsed_options={"workflow_profile": profile}, script_type=script_type,
    )
    skills_dir = integration.skills_dest(tmp_path)
    prefix = "sp" if profile == "classic" else "spx"
    missing = skills_dir / f"{prefix}-e2e/SKILL.md"
    installed_bytes = missing.read_bytes()
    metadata = integration._parse_skill_frontmatter(installed_bytes.decode("utf-8"))
    assert metadata["user-invocable"] is True
    if integration_key == "claude" and profile == "classic":
        assert metadata["argument-hint"] == ARGUMENT_HINTS["e2e"]

    # Establish the existing repair-owned hook/settings assets before checking
    # that restoring a missing skill does not change installation membership.
    integration.repair_runtime_assets(tmp_path, manifest, script_type=script_type)
    assert missing.read_bytes() == installed_bytes

    edited = skills_dir / f"{prefix}-quick/SKILL.md"
    edited_bytes = b"---\nname: user-quick\n---\nUser-owned guidance without generated addenda.\n"
    edited.write_bytes(edited_bytes)
    untracked = skills_dir / f"{prefix}-ask/SKILL.md"
    assert manifest.remove_file_if_unmodified(untracked.relative_to(tmp_path))
    untracked_bytes = b"---\nname: user-ask\n---\nUntracked user skill.\n"
    untracked.write_bytes(untracked_bytes)
    manifest.save()
    before = dict(manifest.files)
    missing.unlink()

    restored = integration.repair_runtime_assets(
        tmp_path, manifest, script_type=script_type
    )

    assert missing in restored
    assert missing.read_bytes() == installed_bytes
    assert edited.read_bytes() == edited_bytes
    assert untracked.read_bytes() == untracked_bytes
    assert set(manifest.files) == set(before)
    for path in (missing, edited):
        relative = path.relative_to(tmp_path).as_posix()
        assert manifest.files[relative] == before[relative]
    assert untracked.relative_to(tmp_path).as_posix() not in manifest.files


@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_claude_restores_native_runtime_contracts_exactly(tmp_path, script_type):
    integration = get_integration("claude")
    manifest = IntegrationManifest("claude", tmp_path)
    integration.setup(
        tmp_path, manifest,
        parsed_options={"workflow_profile": "classic"}, script_type=script_type,
    )
    skills_dir = integration.skills_dest(tmp_path)
    originals = {
        skills_dir / f"sp-{name}/SKILL.md": (skills_dir / f"sp-{name}/SKILL.md").read_bytes()
        for name in ("implement", "debug", "quick")
    }
    for path in originals:
        path.unlink()

    restored = integration.repair_missing_classic_skill_files(
        tmp_path, manifest, script_type=script_type
    )

    assert set(originals).issubset(restored)
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize("integration_key", ["claude", "grok", "vibe"])
def test_native_setup_accepts_relative_project_roots(tmp_path, monkeypatch, integration_key):
    monkeypatch.chdir(tmp_path)
    project = Path("relative-project")
    project.mkdir()
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, project)

    integration.setup(
        project, manifest,
        parsed_options={"workflow_profile": "classic"}, script_type="sh",
    )

    skill = integration.skills_dest(project) / "sp-e2e/SKILL.md"
    metadata = integration._parse_skill_frontmatter(skill.read_text(encoding="utf-8"))
    assert metadata["user-invocable"] is True
    if integration_key == "claude":
        assert metadata["argument-hint"] == ARGUMENT_HINTS["e2e"]


@pytest.mark.parametrize("integration_key", ["claude", "grok", "vibe"])
def test_native_finalizer_rejects_linked_ancestor_without_touching_user_target(
    tmp_path, integration_key
):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    skills_dir = integration.skills_dest(tmp_path)
    missing = skills_dir / "sp-e2e/SKILL.md"
    manifest.record_file(missing.relative_to(tmp_path), b"original\n")
    missing.unlink()
    missing.parent.rmdir()
    user_directory = tmp_path / "user-owned"
    user_directory.mkdir()
    target = user_directory / "SKILL.md"
    user_bytes = b"---\nname: user-skill\n---\nUser-owned content.\n"
    target.write_bytes(user_bytes)
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(missing.parent), str(user_directory)],
            check=True, capture_output=True,
        )
    else:
        missing.parent.symlink_to(user_directory, target_is_directory=True)
    before = dict(manifest.files)

    with pytest.raises(ValueError, match="symlink"):
        integration.finalize_native_skill_files(
            [missing], tmp_path, manifest, skills_dir
        )

    assert target.read_bytes() == user_bytes
    assert manifest.files == before
