"""Project skill layout ownership and rollback regressions."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.integrations import skill_layout
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.integrations.skill_layout import (
    migrate_skill_layout,
    preflight_skill_install,
)


@pytest.fixture
def installed_skills(tmp_path):
    manifest = IntegrationManifest("codex", tmp_path, version="0.8.7")
    source = tmp_path / ".codex/skills"
    target = tmp_path / ".agents/skills"
    contents = {
        "sp-plan/SKILL.md": b"classic\n",
        "sp-plan/references/rules.md": b"\x00classic-reference",
        "spx-plan/SKILL.md": b"advanced\n",
        "references/advanced.md": b"advanced-shared-reference",
    }
    for relative, content in contents.items():
        manifest.record_file((source / relative).relative_to(tmp_path), content)
    manifest.record_file(".codex/hooks.json", b"unrelated")
    manifest.save()
    return manifest, source, target, contents


def test_migration_moves_both_profiles_and_sidecars(installed_skills):
    manifest, source, target, contents = installed_skills
    root = manifest.project_root
    user_skill = source / "personal/SKILL.md"
    user_skill.parent.mkdir()
    user_skill.write_bytes(b"keep")
    created = migrate_skill_layout(root, manifest, source, target, layout="shared")

    assert set(created) == {target / path for path in contents}
    assert all((target / path).read_bytes() == data for path, data in contents.items())
    assert all(not (source / path).exists() for path in contents)
    assert user_skill.read_bytes() == b"keep"
    loaded = IntegrationManifest.load(manifest.key, root)
    assert loaded.skill_layout == "shared"
    assert loaded.version == manifest.version
    assert set(loaded.files) == {".codex/hooks.json"} | {
        (target / path).relative_to(root).as_posix() for path in contents
    }
    assert loaded.check_modified() == []
    assert migrate_skill_layout(root, loaded, source, target, layout="shared") == []


@pytest.mark.parametrize("location, reason", [("source", "modified"), ("target", "untracked")])
def test_migration_refuses_conflicting_sidecars(installed_skills, location, reason):
    manifest, source, target, contents = installed_skills
    path = (source if location == "source" else target) / "sp-plan/references/rules.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"user changes")
    before = manifest.manifest_path.read_bytes()
    with pytest.raises(ValueError, match=reason):
        migrate_skill_layout(manifest.project_root, manifest, source, target, layout="shared")
    assert path.read_bytes() == b"user changes"
    assert (source / "sp-plan/SKILL.md").read_bytes() == contents["sp-plan/SKILL.md"]
    assert not (target / "sp-plan/SKILL.md").exists()
    assert manifest.manifest_path.read_bytes() == before


def test_preflight_refuses_missing_peer_claim_but_allows_explicit_switch(tmp_path):
    peer = IntegrationManifest("peer", tmp_path)
    asset = peer.record_file(".agents/skills/sp-plan/references/rules.md", b"shared")
    peer.save()
    asset.unlink()
    target = tmp_path / ".agents/skills"
    manifest = IntegrationManifest("next", tmp_path)
    with pytest.raises(ValueError, match="another integration"):
        preflight_skill_install(tmp_path, manifest, target, ["sp-plan"])
    preflight_skill_install(tmp_path, manifest, target, ["sp-plan"], replacing_manifest=peer)
    asset.write_bytes(b"edited")
    with pytest.raises(ValueError, match="modified"):
        preflight_skill_install(tmp_path, manifest, target, ["sp-plan"], replacing_manifest=peer)


def test_preflight_refuses_hardlink_inside_skill(tmp_path):
    manifest = IntegrationManifest("codex", tmp_path)
    asset = manifest.record_file(".agents/skills/sp-plan/SKILL.md", b"skill")
    manifest.save()
    os.link(asset, tmp_path / "backup.md")
    with pytest.raises(ValueError, match="unlinked"):
        preflight_skill_install(tmp_path, manifest, tmp_path / ".agents/skills", ["sp-plan"])


def test_preflight_refuses_symlinked_skill_parent(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    alias = tmp_path / ".agents"
    try:
        alias.symlink_to(original, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    with pytest.raises(ValueError, match="symlink"):
        preflight_skill_install(
            tmp_path, IntegrationManifest("codex", tmp_path), alias / "skills", ["sp-plan"],
        )
    assert not list(original.iterdir())


@pytest.mark.parametrize("phase", ["remove", "publish_manifest"])
def test_migration_rolls_back_even_after_publication(installed_skills, monkeypatch, phase):
    manifest, source, target, contents = installed_skills
    original_manifest = manifest.manifest_path.read_bytes()
    if phase == "remove":
        real_unlink = Path.unlink

        def fail_unlink(path, *args, **kwargs):
            if path == source / "sp-plan/SKILL.md":
                raise OSError("injected failure")
            return real_unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", fail_unlink)
    else:
        real_save = manifest._save_locked

        def fail_save(*args):
            real_save(*args)
            raise OSError("injected failure")

        monkeypatch.setattr(manifest, "_save_locked", fail_save)

    with pytest.raises(OSError, match="injected failure"):
        migrate_skill_layout(manifest.project_root, manifest, source, target, layout="shared")
    assert manifest.skill_layout is None
    assert manifest.manifest_path.read_bytes() == original_manifest
    assert all((source / path).read_bytes() == data for path, data in contents.items())
    assert not target.exists()


def test_migration_preserves_concurrently_created_target(installed_skills, monkeypatch):
    manifest, source, target, contents = installed_skills
    publish = skill_layout._publish_exclusive
    raced = target / "sp-plan/SKILL.md"

    def create_then_publish(stage, destination):
        if destination == raced:
            destination.write_bytes(b"user-owned")
        return publish(stage, destination)

    monkeypatch.setattr(skill_layout, "_publish_exclusive", create_then_publish)
    with pytest.raises(FileExistsError):
        migrate_skill_layout(manifest.project_root, manifest, source, target, layout="shared")
    assert raced.read_bytes() == b"user-owned"
    assert all((source / path).read_bytes() == data for path, data in contents.items())
    assert not (target / "references/advanced.md").exists()
