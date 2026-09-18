"""Actual-file tests for runtime cache/project isolation, not release validation."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import shutil
import stat
import subprocess

import pytest


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    module = importlib.import_module("specify_cli.specify_runtime")
    monkeypatch.setenv(module.RUNTIME_CACHE_ENV, str(tmp_path / "cache"))
    return module


def source_file(tmp_path, content=b"original-runtime"):
    path = tmp_path / "download" / "runtime"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o600)
    return path


def assert_independent(*paths):
    for index, path in enumerate(paths):
        assert path.stat().st_nlink == 1
        for other in paths[index + 1:]:
            assert not os.path.samefile(path, other)


def link(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Hardlink creation is unavailable: {exc}")


def test_project_mutation_cannot_change_source_cache_or_other_project(runtime, tmp_path):
    source = source_file(tmp_path)
    digest = runtime._sha256_file(source)
    a = runtime.materialize_project_runtime_entrypoint(tmp_path / "a", source)
    b = runtime.materialize_project_runtime_entrypoint(tmp_path / "b", source)
    cached = runtime.content_addressed_runtime_path(digest)
    a.write_bytes(b"edited-project-a")
    assert source.read_bytes() == cached.read_bytes() == b.read_bytes() == b"original-runtime"
    assert_independent(source, cached, a, b)


def test_in_place_source_replacement_cannot_change_existing_pins(runtime, tmp_path):
    source = source_file(tmp_path)
    digest = runtime._sha256_file(source)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    source.write_bytes(b"new-download")
    assert pinned.read_bytes() == b"original-runtime"
    assert runtime.content_addressed_runtime_path(digest).read_bytes() == b"original-runtime"


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permission semantics")
def test_materialization_does_not_chmod_source(runtime, tmp_path):
    source = source_file(tmp_path)
    before = stat.S_IMODE(source.stat().st_mode)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    assert stat.S_IMODE(source.stat().st_mode) == before == 0o600
    assert pinned.stat().st_mode & stat.S_IXUSR


def test_legacy_hardlinks_detach_on_normal_materialization(runtime, tmp_path):
    source = source_file(tmp_path)
    digest = runtime._sha256_file(source)
    cached = runtime.content_addressed_runtime_path(digest)
    a = runtime.project_runtime_entrypoint_path(tmp_path / "a")
    b = runtime.project_runtime_entrypoint_path(tmp_path / "b")
    for destination in (cached, a, b):
        link(source, destination)
    old_b = b.stat()
    runtime.materialize_project_runtime_entrypoint(tmp_path / "a", source)
    assert cached.stat().st_nlink == a.stat().st_nlink == 1
    # No scanning, replacing or touching unrelated projects during A's repair.
    assert os.path.samefile(source, b)
    assert b.stat().st_ino == old_b.st_ino and b.stat().st_mtime_ns == old_b.st_mtime_ns
    runtime.materialize_project_runtime_entrypoint(tmp_path / "b", source)
    assert_independent(source, cached, a, b)
    a.write_bytes(b"only-a")
    assert source.read_bytes() == cached.read_bytes() == b.read_bytes() == b"original-runtime"


def test_valid_independent_materialization_is_idempotent(runtime, tmp_path, monkeypatch):
    source = source_file(tmp_path)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    cached = runtime.content_addressed_runtime_path(runtime._sha256_file(source))
    before = [(p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes()) for p in (cached, pinned)]
    def unexpected(*args, **kwargs):
        raise AssertionError("valid independent pins should not be recopied")
    monkeypatch.setattr(runtime, "_atomic_link_or_copy", unexpected)
    assert runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source) == pinned
    assert [(p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes()) for p in (cached, pinned)] == before


def test_upgrade_one_project_preserves_another_version(runtime, tmp_path):
    source = source_file(tmp_path)
    a = runtime.materialize_project_runtime_entrypoint(tmp_path / "a", source)
    b = runtime.materialize_project_runtime_entrypoint(tmp_path / "b", source)
    new_source = tmp_path / "second-download"
    new_source.write_bytes(b"new-version")
    runtime.materialize_project_runtime_entrypoint(tmp_path / "a", new_source)
    assert a.read_bytes() == b"new-version"
    assert b.read_bytes() == source.read_bytes() == b"original-runtime"


def test_corrupt_cache_does_not_change_pins_and_is_repaired(runtime, tmp_path):
    source = source_file(tmp_path)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    cached = runtime.content_addressed_runtime_path(runtime._sha256_file(source))
    cached.write_bytes(b"damaged-cache")
    assert pinned.read_bytes() == source.read_bytes() == b"original-runtime"
    runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    assert cached.read_bytes() == b"original-runtime"
    assert_independent(source, cached, pinned)


def test_candidate_corruption_is_rejected_before_replacement(runtime, tmp_path, monkeypatch):
    source = source_file(tmp_path)
    target = tmp_path / "target"
    target.write_bytes(b"working-old-runtime")
    copy = runtime.shutil.copyfileobj
    def corrupt(src, dst, *args, **kwargs):
        copy(src, dst, *args, **kwargs)
        dst.write(b"unexpected-trailer")
    monkeypatch.setattr(runtime.shutil, "copyfileobj", corrupt)
    with pytest.raises(runtime.SpecifyRuntimeError, match="integrity|changed"):
        runtime._atomic_link_or_copy(source, target)
    assert target.read_bytes() == b"working-old-runtime"
    assert not list(tmp_path.glob(".target.*.candidate"))


@pytest.mark.parametrize("stage", ["copy", "fsync", "chmod", "replace"])
def test_candidate_failure_preserves_previous_destination(runtime, tmp_path, monkeypatch, stage):
    if stage == "chmod" and os.name == "nt":
        pytest.skip("Windows mode changes differ")
    source = source_file(tmp_path)
    target = tmp_path / "target"
    target.write_bytes(b"working-old-runtime")
    if stage == "copy":
        def fail(src, dst, *args, **kwargs):
            dst.write(b"partial")
            raise OSError("injected copy failure")
        monkeypatch.setattr(runtime.shutil, "copyfileobj", fail)
    else:
        def fail(*args, **kwargs):
            raise OSError("injected candidate failure")
        monkeypatch.setattr(runtime.os, stage, fail)
    with pytest.raises(OSError):
        runtime._atomic_link_or_copy(source, target)
    assert target.read_bytes() == b"working-old-runtime"
    assert source.read_bytes() == b"original-runtime"
    assert not list(tmp_path.glob(".target.*.candidate"))


def test_expected_digest_mismatch_never_replaces_destination(runtime, tmp_path):
    source = source_file(tmp_path)
    target = tmp_path / "target"
    target.write_bytes(b"working-old-runtime")
    with pytest.raises(runtime.SpecifyRuntimeError, match="integrity|changed"):
        runtime._atomic_link_or_copy(source, target, expected_sha256="a" * 64)
    assert target.read_bytes() == b"working-old-runtime"
    assert not list(tmp_path.glob(".target.*.candidate"))


def test_source_change_during_copy_blocks_publication(runtime, tmp_path, monkeypatch):
    source = source_file(tmp_path)
    target = tmp_path / "target"
    target.write_bytes(b"working-old-runtime")
    copy = runtime.shutil.copyfileobj
    def mutate(src, dst, *args, **kwargs):
        copy(src, dst, *args, **kwargs)
        source.write_bytes(b"changed-download")
    monkeypatch.setattr(runtime.shutil, "copyfileobj", mutate)
    with pytest.raises(runtime.SpecifyRuntimeError, match="integrity|changed"):
        runtime._atomic_link_or_copy(source, target)
    assert target.read_bytes() == b"working-old-runtime"
    assert not list(tmp_path.glob(".target.*.candidate"))


def test_same_path_copy_can_detach_old_shared_inode(runtime, tmp_path):
    source = source_file(tmp_path)
    other = tmp_path / "old-project"
    link(source, other)
    runtime._atomic_link_or_copy(source, source)
    assert source.read_bytes() == other.read_bytes() == b"original-runtime"
    assert_independent(source, other)


def test_cache_itself_can_be_materialization_source(runtime, tmp_path):
    source = source_file(tmp_path)
    cached = runtime.content_addressed_runtime_path(runtime._sha256_file(source))
    link(source, cached)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", cached)
    assert_independent(source, cached, pinned)
    pinned.write_bytes(b"only-project")
    assert cached.read_bytes() == source.read_bytes() == b"original-runtime"


@pytest.mark.parametrize("kind", ["cache", "project-bin", "destination"])
def test_symlink_destination_or_ancestor_cannot_redirect_copy(runtime, tmp_path, kind):
    source = source_file(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "target"
    target.write_bytes(b"untouched")
    alias = tmp_path / "alias"
    if kind == "cache":
        alias = runtime.cache_dir()
    elif kind == "project-bin":
        alias = tmp_path / "project/.specify/bin"
        alias.parent.mkdir(parents=True)
    try:
        alias.symlink_to(target if kind == "destination" else outside, target_is_directory=kind != "destination")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")
    with pytest.raises((ValueError, runtime.SpecifyRuntimeError)):
        if kind == "destination":
            runtime._atomic_link_or_copy(source, alias)
        else:
            runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    assert target.read_bytes() == b"untouched"
    assert sorted(p.name for p in outside.iterdir()) == ["target"]


def test_rejects_nonregular_or_link_source(runtime, tmp_path):
    source = source_file(tmp_path)
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source.parent)
    alias = tmp_path / "source-link"
    try:
        alias.symlink_to(source)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")
    with pytest.raises(runtime.SpecifyRuntimeError, match="symbolic link"):
        runtime.materialize_project_runtime_entrypoint(tmp_path / "project", alias)


def test_preserves_user_gitignore_and_unrelated_files(runtime, tmp_path):
    source = source_file(tmp_path)
    project = tmp_path / "project"
    binary_dir = project / ".specify/bin"
    binary_dir.mkdir(parents=True)
    ignore = binary_dir / ".gitignore"
    ignore.write_text("# user entry\ncustom-helper\n", encoding="utf-8")
    unrelated = project / "keep.txt"
    unrelated.write_text("do not change", encoding="utf-8")
    runtime.materialize_project_runtime_entrypoint(project, source)
    runtime.materialize_project_runtime_entrypoint(project, source)
    lines = ignore.read_text().splitlines()
    assert lines[:2] == ["# user entry", "custom-helper"]
    assert lines.count("specify-runtime") == lines.count("specify-runtime.exe") == 1
    assert unrelated.read_text() == "do not change"
    assert (project / ".specify/runtime/.gitignore").read_text().splitlines() == ["*", "!.gitignore"]


@pytest.mark.skipif(not shutil.which("go"), reason="Local Go required for native executable fixture")
def test_relocated_real_executable_runs_without_shared_files(runtime, tmp_path):
    # Build a tiny native executable, not a pretend spec-kit-plus release.
    source = tmp_path / "download" / ("fixture.exe" if os.name == "nt" else "fixture")
    source.parent.mkdir()
    program = tmp_path / "fixture.go"
    program.write_text('package main\nimport "fmt"\nfunc main() { fmt.Println("isolated-executable-ok") }\n')
    env = os.environ.copy()
    env.update(GOWORK="off", GOTOOLCHAIN="local", GOPROXY="off", GOFLAGS="")
    build = subprocess.run(["go", "build", "-o", str(source), str(program)],
                           env=env, capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, build.stderr
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    completed = subprocess.run([str(pinned)], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "isolated-executable-ok"
    assert_independent(source, pinned, runtime.content_addressed_runtime_path(runtime._sha256_file(source)))


@pytest.mark.skipif(os.name == "nt", reason="POSIX privileged mode bits")
def test_candidate_does_not_inherit_privileged_mode_bits(runtime, tmp_path):
    source = source_file(tmp_path)
    source.chmod(0o6755)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    assert stat.S_IMODE(source.stat().st_mode) == 0o6755
    assert not pinned.stat().st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX)
    assert os.access(pinned, os.X_OK)


def test_project_copy_failure_keeps_existing_pin(runtime, tmp_path, monkeypatch):
    source = source_file(tmp_path)
    project = tmp_path / "project"
    pinned = runtime.materialize_project_runtime_entrypoint(project, source)
    new_source = tmp_path / "new-runtime"
    new_source.write_bytes(b"new-version")
    original_copy = runtime._atomic_link_or_copy
    def fail_project_copy(src, dst, **kwargs):
        if dst == pinned:
            raise OSError("injected project copy failure")
        return original_copy(src, dst, **kwargs)
    monkeypatch.setattr(runtime, "_atomic_link_or_copy", fail_project_copy)
    with pytest.raises(OSError, match="project copy"):
        runtime.materialize_project_runtime_entrypoint(project, new_source)
    assert pinned.read_bytes() == b"original-runtime"
    # A valid independent cache entry may exist; this is not a cross-file rollback.
    assert runtime.content_addressed_runtime_path(runtime._sha256_file(new_source)).read_bytes() == b"new-version"


def test_new_materialization_never_attempts_hardlink(runtime, tmp_path, monkeypatch):
    source = source_file(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime materialization must not use hardlinks")
    monkeypatch.setattr(runtime.os, "link", forbidden)
    pinned = runtime.materialize_project_runtime_entrypoint(tmp_path / "project", source)
    assert pinned.read_bytes() == source.read_bytes()
    assert_independent(source, pinned)
