"""Advanced support-file repair must preserve the installed profile contract."""

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


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
