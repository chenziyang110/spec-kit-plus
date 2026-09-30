"""Runtime copies accept stable platform metadata and reject real changes."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli import specify_runtime as runtime


def _stat_with(metadata, **changes):
    fields = {
        name: getattr(metadata, name)
        for name in dir(metadata) if name.startswith("st_")
    }
    return SimpleNamespace(**(fields | changes))


def test_native_runtime_copy_accepts_previously_materialized_source(tmp_path):
    source, cached, pinned = (tmp_path / name for name in ("download", "cache", "pin"))
    source.write_bytes(b"native-runtime")

    runtime._atomic_link_or_copy(source, cached)
    runtime._atomic_link_or_copy(cached, pinned)

    assert pinned.read_bytes() == source.read_bytes()
    assert not os.path.samefile(source, cached)
    assert not os.path.samefile(cached, pinned)


@pytest.mark.parametrize("difference", ["ctime", "mode", "both"])
def test_runtime_copy_accepts_stable_api_specific_metadata(
    tmp_path, monkeypatch, difference,
):
    source, target = tmp_path / "runtime.exe", tmp_path / "target.exe"
    source.write_bytes(b"runtime")
    identity = source.lstat()
    real_fstat = os.fstat

    def by_descriptor(fd):
        metadata = real_fstat(fd)
        if not os.path.samestat(identity, metadata):
            return metadata
        changes = {}
        if difference in {"ctime", "both"}:
            changes["st_ctime_ns"] = metadata.st_ctime_ns + 1_000_000_000
        if difference in {"mode", "both"}:
            changes["st_mode"] = metadata.st_mode ^ 0o111
        return _stat_with(metadata, **changes)

    monkeypatch.setattr(os, "fstat", by_descriptor)
    runtime._atomic_link_or_copy(source, target)

    assert target.read_bytes() == source.read_bytes()
    assert not os.path.samefile(source, target)


@pytest.mark.parametrize("api", ["descriptor", "path"])
@pytest.mark.parametrize(
    "field", ["st_mode", "st_size", "st_mtime_ns", "st_ctime_ns", "st_ino"],
)
def test_runtime_copy_rejects_changed_snapshot_before_publication(
    tmp_path, monkeypatch, api, field,
):
    source, target = tmp_path / "runtime.exe", tmp_path / "target.exe"
    source.write_bytes(b"runtime")
    target.write_bytes(b"previous-runtime")
    identity = source.lstat()
    real_fstat, real_lstat = os.fstat, Path.lstat
    real_copy = runtime.shutil.copyfileobj
    copied = False

    def observe(metadata, observed_api):
        if copied and api == observed_api:
            value = getattr(metadata, field)
            value = value ^ 0o100 if field == "st_mode" else value + 1
            return _stat_with(metadata, **{field: value})
        return metadata

    def by_descriptor(fd):
        metadata = real_fstat(fd)
        return (
            observe(metadata, "descriptor")
            if os.path.samestat(identity, metadata) else metadata
        )

    def by_path(path, *args, **kwargs):
        metadata = real_lstat(path, *args, **kwargs)
        return observe(metadata, "path") if path == source else metadata

    def copy_then_change(*args, **kwargs):
        nonlocal copied
        real_copy(*args, **kwargs)
        copied = True

    monkeypatch.setattr(os, "fstat", by_descriptor)
    monkeypatch.setattr(Path, "lstat", by_path)
    monkeypatch.setattr(runtime.shutil, "copyfileobj", copy_then_change)

    with pytest.raises(runtime.SpecifyRuntimeError, match="source changed while copying"):
        runtime._atomic_link_or_copy(source, target)

    assert target.read_bytes() == b"previous-runtime"
    assert source.read_bytes() == b"runtime"
    assert not list(tmp_path.glob(".target.exe.*.candidate"))
