"""Exercise hook publication with real files and the production manifest owner.

Packaged payloads are small byte fixtures; full integration initialization and
native Windows execution are separate acceptance gates.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys

import pytest

from specify_cli import atomic_io, launcher
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.fixture
def layout(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    assets = root / "assets 中文"
    assets.mkdir()
    project = root / "project with spaces"
    monkeypatch.setattr(launcher, "_hook_launcher_assets_dir", lambda: assets)
    return assets, project


def asset(assets: Path, name: str = "specify-hook.py", data: bytes = b"new hook\r\n\x00\xff") -> Path:
    path = assets / name
    path.write_bytes(data)
    path.chmod(0o640)
    os.utime(path, ns=(1_700_000_000_000_000_000, 1_700_000_000_123_456_789))
    return path


def installed(project: Path, name: str = "specify-hook.py", data: bytes = b"working old hook") -> Path:
    path = project / ".specify" / "bin" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def identity(path: Path):
    info = path.stat()
    return path.read_bytes(), stat.S_IMODE(info.st_mode), info.st_mtime_ns


def link(source: Path, target: Path, *, hard: bool = False, directory: bool = False):
    try:
        if hard:
            os.link(source, target)
        else:
            target.symlink_to(source, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"link fixture unavailable: {exc}")


@pytest.mark.parametrize("name", ["specify-hook", "specify-hook.py", "specify-hook.cmd", "specify-hook.mjs"])
def test_install_detaches_external_hardlink_without_changing_backup(layout, name):
    assets, project = layout
    source = asset(assets, name)
    target = installed(project, name)
    backup = project.parent / "external-backup"
    link(target, backup, hard=True)
    before = identity(backup)
    manifest = IntegrationManifest("claude", project)
    created = launcher.install_shared_hook_launcher_assets(project, manifest=manifest)
    assert created == [target]
    assert not os.path.samefile(target, backup)
    assert identity(backup) == before
    assert target.read_bytes() == source.read_bytes()
    assert manifest.files == {target.relative_to(project).as_posix(): hashlib.sha256(target.read_bytes()).hexdigest()}


@pytest.mark.parametrize("dangling", [False, True])
def test_install_refuses_destination_symlink_without_touching_target(layout, dangling):
    assets, project = layout
    asset(assets)
    target = installed(project)
    target.unlink()
    victim = project.parent / "external-user-file"
    if not dangling:
        victim.write_bytes(b"user bytes")
    link(victim, target)
    manifest = IntegrationManifest("gemini", project)
    with pytest.raises(ValueError):
        launcher.install_shared_hook_launcher_assets(project, manifest=manifest)
    assert target.is_symlink()
    assert manifest.files == {}
    if dangling:
        assert not victim.exists()
    else:
        assert victim.read_bytes() == b"user bytes"


@pytest.mark.parametrize("relative", [".specify", ".specify/bin"])
def test_install_refuses_parent_link_before_mkdir_or_manifest_scan(layout, relative, monkeypatch):
    assets, project = layout
    asset(assets)
    outside = project.parent / "external-directory"
    outside.mkdir()
    alias = project / relative
    alias.parent.mkdir(parents=True, exist_ok=True)
    link(outside, alias, directory=True)
    manifest = IntegrationManifest("claude", project)

    def forbidden():
        pytest.fail("an unsafe destination must be rejected before manifest reads")

    monkeypatch.setattr(manifest, "check_modified", forbidden)
    with pytest.raises(ValueError, match="symlink"):
        launcher.install_shared_hook_launcher_assets(project, manifest=manifest, preserve_modified=True)
    assert list(outside.iterdir()) == []
    assert alias.is_symlink()


def test_destination_directory_is_not_interpreted_as_a_copy_folder(layout):
    assets, project = layout
    asset(assets)
    target = project / ".specify/bin/specify-hook.py"
    target.mkdir(parents=True)
    sentinel = target / "keep.txt"
    sentinel.write_bytes(b"user data")
    with pytest.raises(ValueError, match="regular"):
        launcher.install_shared_hook_launcher_assets(project)
    assert list(target.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"user data"


@pytest.mark.parametrize("kind", ["file", "dangling", "root"])
def test_packaged_source_links_are_not_followed(layout, monkeypatch, kind):
    assets, project = layout
    outside = project.parent / "outside-assets"
    outside.mkdir()
    victim = asset(outside)
    if kind == "root":
        alias = project.parent / "assets-alias"
        link(outside, alias, directory=True)
        monkeypatch.setattr(launcher, "_hook_launcher_assets_dir", lambda: alias)
    else:
        if kind == "dangling":
            victim.unlink()
        link(victim, assets / victim.name)
    with pytest.raises(ValueError, match="symlink"):
        launcher.install_shared_hook_launcher_assets(project)
    assert not (project / ".specify/bin/specify-hook.py").exists()
    if kind != "dangling":
        assert victim.read_bytes() == b"new hook\r\n\x00\xff"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO fixture")
def test_packaged_fifo_is_rejected_instead_of_silently_omitted(layout):
    assets, project = layout
    source = assets / "specify-hook.py"
    os.mkfifo(source)
    with pytest.raises(ValueError, match="regular"):
        launcher.install_shared_hook_launcher_assets(project)
    assert stat.S_ISFIFO(source.lstat().st_mode)
    assert not (project / ".specify/bin/specify-hook.py").exists()


@pytest.mark.parametrize("kind", ["modified", "untracked", "no-manifest", "symlink", "directory"])
def test_preserve_mode_does_not_adopt_or_rewrite_user_assets(layout, kind):
    assets, project = layout
    asset(assets)
    target = installed(project)
    manifest = IntegrationManifest("claude", project)
    relative = target.relative_to(project).as_posix()
    if kind not in {"untracked", "no-manifest"}:
        manifest.record_existing(relative)
    expected_manifest = manifest.files
    if kind == "modified":
        target.write_bytes(b"my custom hook")
    elif kind == "symlink":
        victim = project.parent / "user-hook"
        victim.write_bytes(b"my linked hook")
        target.unlink()
        link(victim, target)
    elif kind == "directory":
        target.unlink()
        target.mkdir()
    before = target.lstat()
    contents = None if kind == "directory" else target.read_bytes()
    skipped = []
    result = launcher.install_shared_hook_launcher_assets(
        project, manifest=None if kind == "no-manifest" else manifest,
        preserve_modified=True, skipped_modified=skipped,
    )
    assert result == [] and skipped == [relative]
    assert manifest.files == expected_manifest
    assert os.path.samestat(before, target.lstat())
    assert before.st_mode == target.lstat().st_mode
    assert contents is None or target.read_bytes() == contents


@pytest.mark.parametrize("key", ["claude", "gemini"])
def test_unmodified_tracked_hook_is_updated_and_manifest_roundtrips(layout, key):
    assets, project = layout
    source = asset(assets)
    target = installed(project)
    manifest = IntegrationManifest(key, project)
    relative = target.relative_to(project).as_posix()
    manifest.record_existing(relative)
    skipped = []
    assert launcher.install_shared_hook_launcher_assets(
        project, manifest=manifest, preserve_modified=True, skipped_modified=skipped,
    ) == [target]
    assert skipped == []
    assert target.read_bytes() == source.read_bytes()
    assert manifest.check_modified() == []
    manifest.save()
    assert IntegrationManifest.load(key, project).files == manifest.files


def test_payloads_metadata_and_node_selection_stay_compatible(layout):
    assets, project = layout
    names = ["specify-hook", "specify-hook.cmd", "specify-hook.mjs", "specify-hook.py"]
    sources = {name: asset(assets, name) for name in names}
    (assets / "not-an-asset-directory").mkdir()
    manifest = IntegrationManifest("gemini", project)
    created = launcher.install_shared_hook_launcher_assets(project, manifest=manifest, include_node=False)
    assert [p.name for p in created] == [name for name in names if name != "specify-hook.mjs"]
    assert not (project / ".specify/bin/specify-hook.mjs").exists()
    for path in created:
        source = sources[path.name]
        assert path.read_bytes() == source.read_bytes()
        assert path.stat().st_mtime_ns == source.stat().st_mtime_ns
        if os.name != "nt":
            mode = stat.S_IMODE(source.stat().st_mode) | (0o111 if path.name == "specify-hook" else 0)
            assert stat.S_IMODE(path.stat().st_mode) == mode
    assert len(manifest.files) == 3


def test_excluded_node_asset_is_neither_read_nor_overwritten(layout):
    assets, project = layout
    excluded = assets / launcher.HOOK_LAUNCHER_NODE
    link(assets / "absent-node-target", excluded)
    target = installed(project, launcher.HOOK_LAUNCHER_NODE, b"custom node hook")
    before = identity(target)
    assert launcher.install_shared_hook_launcher_assets(project, include_node=False) == []
    assert identity(target) == before


def test_absent_assets_remains_a_noop(layout, monkeypatch):
    _, project = layout
    monkeypatch.setattr(launcher, "_hook_launcher_assets_dir", lambda: None)
    assert launcher.install_shared_hook_launcher_assets(project) == []
    assert not project.exists()


@pytest.mark.parametrize("failure", ["read", "flush", "replace"])
def test_prepublication_failure_preserves_working_hook_and_manifest(layout, monkeypatch, failure):
    assets, project = layout
    asset(assets)
    target = installed(project)
    manifest = IntegrationManifest("claude", project)
    relative = target.relative_to(project).as_posix()
    manifest.record_existing(relative)
    before, recorded = identity(target), manifest.files

    def fail(*args, **kwargs):
        raise OSError("controlled " + failure + " failure")

    if failure == "read":
        monkeypatch.setattr(launcher, "read_local_state_bytes", fail)
    else:
        monkeypatch.setattr(atomic_io.os, "fsync" if failure == "flush" else "replace", fail)
    with pytest.raises(OSError, match="controlled"):
        launcher.install_shared_hook_launcher_assets(project, manifest=manifest)
    assert identity(target) == before
    assert manifest.files == recorded
    assert not list(target.parent.glob("*.tmp"))


def test_live_path_is_unchanged_until_atomic_publication(layout, monkeypatch):
    assets, project = layout
    source = asset(assets)
    target = installed(project)
    before = target.read_bytes()
    replace = os.replace
    observations = []

    def observe(candidate, destination):
        if Path(destination) == target:
            assert target.read_bytes() == before
            assert Path(candidate).read_bytes() == source.read_bytes()
            assert not os.path.samefile(candidate, target)
            observations.append(True)
        return replace(candidate, destination)

    monkeypatch.setattr(atomic_io.os, "replace", observe)
    launcher.install_shared_hook_launcher_assets(project)
    assert observations == [True]
    assert target.read_bytes() == source.read_bytes()


def test_late_metadata_failure_is_reported_without_claiming_rollback(layout, monkeypatch):
    assets, project = layout
    source = asset(assets)
    target = installed(project)
    manifest = IntegrationManifest("claude", project)
    manifest.record_existing(target.relative_to(project))
    recorded = manifest.files

    def fail(*args, **kwargs):
        raise OSError("controlled metadata failure")

    monkeypatch.setattr(launcher.shutil, "copystat", fail)
    with pytest.raises(OSError, match="metadata"):
        launcher.install_shared_hook_launcher_assets(project, manifest=manifest)
    assert target.read_bytes() == source.read_bytes()
    assert manifest.files == recorded
    assert manifest.check_modified() == [target.relative_to(project).as_posix()]


@pytest.mark.parametrize("integration", ["claude", "gemini"])
@pytest.mark.parametrize("transport", [
    "python", "node",
    pytest.param("shell", marks=pytest.mark.skipif(os.name == "nt", reason="POSIX shell launcher")),
])
@pytest.mark.parametrize("exit_code", [0, 7])
def test_actual_installed_hook_chain_preserves_io_and_exit(tmp_path, monkeypatch, integration, transport, exit_code):
    # Install the real packaged scripts. Only the final integration dispatcher
    # is an instrumented leaf, so no real agent CLI or workflow state is touched.
    root = tmp_path.resolve() / "project 中文 with spaces"
    assets = launcher._hook_launcher_assets_dir()
    assert assets is not None
    manifest = IntegrationManifest(integration, root)
    created = launcher.install_shared_hook_launcher_assets(root, manifest=manifest)
    assert {p.name for p in created} == {
        "specify-hook", "specify-hook.cmd", "specify-hook.mjs", "specify-hook.py",
    }
    for path in created:
        assert path.read_bytes() == (assets / path.name).read_bytes()
    dispatcher = root / f".{integration}/hooks/{integration}-hook-dispatch.py"
    dispatcher.parent.mkdir(parents=True)
    dispatcher.write_text(
        "import json, os, sys\n"
        "print(json.dumps({'argv':sys.argv[1:],'cwd':os.getcwd(),'input':sys.stdin.read()}))\n"
        "raise SystemExit(int(os.environ['SPECIFY_TEST_HOOK_EXIT']))\n",
        encoding="utf-8",
    )
    for name in ("CLAUDE_PROJECT_DIR", "GEMINI_PROJECT_DIR", "SPECIFY_PROJECT_DIR",
                 "SPECIFY_HOOK_RUNTIME_ARGV", "SPECIFY_HOOK_RUNTIME_COMMAND"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SPECIFY_TEST_HOOK_EXIT", str(exit_code))
    monkeypatch.setenv("PYTHONUTF8", "1")
    if transport == "node":
        node = shutil.which("node")
        if node is None:
            pytest.skip("Node is required for the real Node launcher test")
        monkeypatch.setenv("SPECIFY_HOOK_RUNTIME_ARGV", json.dumps([sys.executable]))
        argv = [node, str(root / ".specify/bin/specify-hook.mjs")]
    elif transport == "shell":
        # A project venv entry avoids shell-command parsing of the interpreter.
        interpreter = root / ".venv/bin/python"
        interpreter.parent.mkdir(parents=True)
        link(Path(sys.executable), interpreter)
        argv = [str(root / ".specify/bin/specify-hook")]
    else:
        argv = [sys.executable, str(root / ".specify/bin/specify-hook.py")]
    nested = root / "nested"
    nested.mkdir()
    route, payload = "route 中文;$()", '{"note":"保持原样 😀"}\n'
    result = subprocess.run(
        [*argv, integration, route], cwd=nested, input=payload,
        capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
    )
    assert result.returncode == exit_code, result.stderr
    assert json.loads(result.stdout) == {"argv": [route], "cwd": str(root), "input": payload}
    assert result.stderr == ""
    assert manifest.check_modified() == []
