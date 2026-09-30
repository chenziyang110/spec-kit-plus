"""Advanced file repair must preserve the installed profile contract."""

import json
import os
import subprocess

import pytest
from typer.testing import CliRunner

from specify_cli import app, load_init_options
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import (
    diagnose_project_runtime_compatibility,
    load_runtime_launcher,
    rebind_unbound_unified_runtime_calls,
    write_runtime_launcher_config,
)


@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_advanced_entrypoint_binds_appended_artifact_boundary(tmp_path, script_type):
    binary = tmp_path / "source" / (
        "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
    )
    binary.parent.mkdir()
    binary.write_bytes(b"runtime fixture")
    write_runtime_launcher_config(tmp_path, binary)
    launcher = load_runtime_launcher(tmp_path)
    assert launcher is not None
    integration = get_integration("codex")
    source = integration.shared_advanced_skills_dir() / "spx-e2e/SKILL.md"

    rendered = integration._render_advanced_skill_content(
        source_path=source,
        raw=source.read_text(encoding="utf-8"),
        project_root=tmp_path,
        script_type=script_type,
        arg_placeholder="$ARGUMENTS",
    )

    _, body = integration._split_frontmatter(rendered)
    assert integration._parse_skill_frontmatter(rendered)["name"] == "spx-e2e"
    _, bare_count = rebind_unbound_unified_runtime_calls(body, launcher.command)
    assert bare_count == 0
    for operation in ("show", "prepare", "submit"):
        assert f"`{launcher.command} artifact {operation}`" in body


@pytest.mark.parametrize("prefix", ["sp", "spx"])
def test_missing_skill_repair_rejects_redirected_directory(tmp_path, prefix):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    relative = f".codex/skills/{prefix}-e2e/SKILL.md"
    skill = manifest.record_file(relative, b"original managed skill\n")
    skill.unlink()
    skill.parent.rmdir()
    user_directory = tmp_path / "untracked-user-folder"
    user_directory.mkdir()
    sentinel = user_directory / "user-note.txt"
    sentinel.write_bytes(b"user-owned note\n")
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(skill.parent), str(user_directory)],
            check=True,
            capture_output=True,
        )
    else:
        skill.parent.symlink_to(user_directory, target_is_directory=True)
    before = dict(manifest.files)

    with pytest.raises(ValueError, match="symlink"):
        integration.repair_runtime_assets(
            tmp_path, manifest, script_type="sh"
        )

    assert not (user_directory / "SKILL.md").exists()
    assert sentinel.read_bytes() == b"user-owned note\n"
    assert manifest.files == before


@pytest.mark.parametrize("integration_key", ["codex", "cursor-agent"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_missing_classic_skills_restore_native_rendering_without_touching_user_files(
    tmp_path, integration_key, script_type
):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path, manifest,
        parsed_options={"workflow_profile": "classic"}, script_type=script_type,
    )
    skills_dir = integration.skills_dest(tmp_path)
    missing = [skills_dir / name / "SKILL.md" for name in ("sp-e2e", "sp-plan")]
    installed_bytes = {path: path.read_bytes() for path in missing}
    edited = skills_dir / "sp-quick/SKILL.md"
    edited_bytes = b"# User-owned quick workflow\n"
    edited.write_bytes(edited_bytes)
    untracked = skills_dir / "sp-ask/SKILL.md"
    assert manifest.remove_file_if_unmodified(untracked.relative_to(tmp_path))
    tracked_before = dict(manifest.files)
    for path in missing:
        path.unlink()

    restored = integration.repair_missing_classic_skill_files(
        tmp_path, manifest, script_type=script_type
    )

    assert set(restored) == set(missing)
    assert {path: path.read_bytes() for path in missing} == installed_bytes
    assert edited.read_bytes() == edited_bytes
    assert not untracked.exists()
    assert manifest.files == tracked_before
    assert manifest.check_modified() == [edited.relative_to(tmp_path).as_posix()]
    assert integration.repair_missing_classic_skill_files(
        tmp_path, manifest, script_type=script_type
    ) == []


@pytest.mark.parametrize("integration_key", ["codex", "cursor-agent"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_missing_advanced_skill_restores_installed_bytes_and_support_files(
    tmp_path, integration_key, script_type
):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type=script_type,
    )
    skill_dir = integration.skills_dest(tmp_path) / "spx-e2e"
    missing = [skill_dir / "SKILL.md", skill_dir / "references/scenario-design.md"]
    original = {path: path.read_bytes() for path in missing}
    tracked_before = dict(manifest.files)
    for path in missing:
        path.unlink()
    manifest.save()
    manifest = IntegrationManifest.load(integration_key, tmp_path)

    restored = integration.repair_missing_advanced_skill_files(
        tmp_path, manifest, script_type=script_type
    )

    assert {path: path.read_bytes() for path in missing if path.exists()} == original
    assert set(missing).issubset(restored)
    assert manifest.files == tracked_before
    assert manifest.check_modified() == []
    assert integration.repair_missing_advanced_skill_files(
        tmp_path, manifest, script_type=script_type
    ) == []


def test_advanced_repair_preserves_modified_skills_and_does_not_claim_untracked_skills(
    tmp_path,
):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    skills_dir = integration.skills_dest(tmp_path)
    modified = skills_dir / "spx-e2e/SKILL.md"
    edited = modified.read_bytes() + b"\n<!-- user-owned E2E note -->\n"
    modified.write_bytes(edited)
    untracked = skills_dir / "spx-ask/SKILL.md"
    assert manifest.remove_file_if_unmodified(untracked.relative_to(tmp_path))
    before = dict(manifest.files)

    restored = integration.repair_missing_advanced_skill_files(
        tmp_path, manifest, script_type="sh"
    )

    assert restored == []
    assert modified.read_bytes() == edited
    assert not untracked.exists()
    assert manifest.files == before
    assert manifest.check_modified() == [modified.relative_to(tmp_path).as_posix()]


@pytest.mark.parametrize("integration_key", ["codex", "cursor-agent"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_missing_advanced_references_restore_the_installed_bytes(
    tmp_path, integration_key, script_type
):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type=script_type,
    )
    skills_dir = integration.skills_dest(tmp_path)
    references = [
        skills_dir / "spx-implement" / "references" / "native-subagents.md",
        skills_dir / "spx-ask" / "references" / "native-subagents.md",
        skills_dir / "references" / "project-cognition.md",
    ]
    original = {path: path.read_bytes() for path in references}
    for path in references:
        path.unlink()
    manifest.save()
    manifest = IntegrationManifest.load(integration_key, tmp_path)

    restored = integration.repair_missing_advanced_skill_files(
        tmp_path, manifest, script_type=script_type
    )

    assert {path: path.read_bytes() for path in references if path.exists()} == original
    assert set(references).issubset(restored)
    assert manifest.check_modified() == []


def test_advanced_repair_preserves_modified_and_untracked_references(tmp_path):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    skills_dir = integration.skills_dest(tmp_path)
    modified = skills_dir / "spx-implement" / "references" / "native-subagents.md"
    modified.write_text("User-owned delegation instructions.\n", encoding="utf-8")
    untracked = skills_dir / "references" / "project-cognition.md"
    untracked.unlink()
    assert manifest.remove_file_if_unmodified(untracked.relative_to(tmp_path))
    before = manifest.files

    restored = integration.repair_missing_advanced_skill_files(
        tmp_path, manifest, script_type="sh"
    )

    assert restored == []
    assert modified.read_text(encoding="utf-8") == "User-owned delegation instructions.\n"
    assert not untracked.exists()
    assert manifest.files == before
    assert manifest.check_modified() == [modified.relative_to(tmp_path).as_posix()]


def test_classic_only_repair_does_not_install_advanced_files(tmp_path):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(
        tmp_path,
        manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )
    before = manifest.files

    restored = integration.repair_missing_advanced_skill_files(
        tmp_path, manifest, script_type="sh"
    )

    assert restored == []
    assert manifest.files == before
    assert not list(integration.skills_dest(tmp_path).glob("spx-*"))
    assert not (integration.skills_dest(tmp_path) / "references").exists()


@pytest.mark.parametrize(
    "first,second,script_type",
    [("classic", "advanced", "sh"), ("advanced", "classic", "ps")],
)
@pytest.mark.usefixtures("unified_runtime_env")
def test_real_repair_restores_missing_advanced_skill_after_additive_init(
    tmp_path, monkeypatch, first, second, script_type
):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    runner = CliRunner()

    def init(profile):
        result = runner.invoke(
            app,
            [
                "init", "--here", "--force", "--ai", "codex",
                "--workflow-profile", profile, "--script", script_type,
                "--no-git", "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

    def repair(expected_exit):
        result = runner.invoke(
            app,
            ["integration", "repair", "--script", script_type],
            catch_exceptions=False,
        )
        assert result.exit_code == expected_exit, result.output
        assert "Remaining diagnostics" not in result.output, result.output
        assert diagnose_project_runtime_compatibility(project) == []
        return result

    init(first)
    assert diagnose_project_runtime_compatibility(project) == []
    edited_skill_name = "sp-e2e" if first == "classic" else "spx-e2e"
    edited_skill = project / ".codex/skills" / edited_skill_name / "SKILL.md"
    helper = project / ".specify/scripts/shared/e2e_scenarios.py"
    edited_skill_bytes = edited_skill.read_bytes() + b"\n<!-- user-owned note -->\n"
    edited_helper_bytes = helper.read_bytes() + b"\n# user-owned note\n"
    edited_skill.write_bytes(edited_skill_bytes)
    helper.write_bytes(edited_helper_bytes)
    init(second)
    assert edited_skill.read_bytes() == edited_skill_bytes
    assert helper.read_bytes() == edited_helper_bytes

    assert diagnose_project_runtime_compatibility(project) == []
    missing_skill_name = "sp-e2e" if second == "classic" else "spx-e2e"
    missing = project / ".codex/skills" / missing_skill_name / "SKILL.md"
    installed_bytes = missing.read_bytes()
    manifests_before = {
        key: dict(IntegrationManifest.load(key, project).files)
        for key in ("codex", "speckit")
    }
    missing.unlink()

    result = repair(10)
    assert "PARTIAL" in result.output
    assert helper.relative_to(project).as_posix() in result.output
    assert missing.is_file(), result.output
    assert missing.read_bytes() == installed_bytes
    assert edited_skill.read_bytes() == edited_skill_bytes
    assert helper.read_bytes() == edited_helper_bytes
    # Repair may rebind runtime calls in other unmodified tracked skills.
    # It must retain both profiles and the ownership digests of user edits.
    for key, before in manifests_before.items():
        assert set(IntegrationManifest.load(key, project).files) == set(before)
    manifest = IntegrationManifest.load("codex", project)
    for path in (missing, edited_skill):
        relative = path.relative_to(project).as_posix()
        assert manifest.files[relative] == manifests_before["codex"][relative]
    assert manifest.check_modified() == [edited_skill.relative_to(project).as_posix()]
    core = IntegrationManifest.load("speckit", project)
    helper_relative = helper.relative_to(project).as_posix()
    assert core.files[helper_relative] == manifests_before["speckit"][helper_relative]
    assert core.check_modified() == [helper.relative_to(project).as_posix()]
    for name in ("sp-e2e", "spx-e2e"):
        assert f".codex/skills/{name}/SKILL.md" in manifest.files
    metadata = json.loads((project / ".specify/integration.json").read_text("utf-8"))
    assert set(metadata["workflow_profiles"]) == {"classic", "advanced"}
    assert set(load_init_options(project)["installed_workflow_profiles"]) == {
        "classic", "advanced"
    }
