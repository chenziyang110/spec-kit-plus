"""Keep manifest hashing portable without weakening change detection."""

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.integrations import manifest as manifest_module
from specify_cli.integrations.manifest import IntegrationManifest


CONTENT = b"first line\r\nsecond line\r\n"


def _stat_with(metadata, **changes):
    fields = {
        name: getattr(metadata, name)
        for name in dir(metadata) if name.startswith("st_")
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


def _different_value(metadata, field):
    value = getattr(metadata, field)
    return value ^ 0o100 if field == "st_mode" else value + 1


def _read_digest(path, reader):
    if reader == "hash":
        return manifest_module._sha256(path)
    expected = CONTENT if reader == "raw" else CONTENT.replace(b"\r\n", b"\n")
    return manifest_module._matches_recorded_hash(
        path, hashlib.sha256(expected).hexdigest(),
    )


def _hook_read(monkeypatch, callback, *, on_rewind=False):
    real_open = manifest_module._open_regular_state_file

    @contextmanager
    def hooked_open(path):
        with real_open(path) as handle:
            class Reader:
                fired = False

                def fileno(self):
                    return handle.fileno()

                def read(self, size):
                    data = handle.read(size)
                    if data and not self.fired and not on_rewind:
                        self.fired = True
                        callback()
                    return data

                def seek(self, *args):
                    position = handle.seek(*args)
                    if on_rewind and not self.fired:
                        self.fired = True
                        callback()
                    return position

            yield Reader()

    monkeypatch.setattr(manifest_module, "_open_regular_state_file", hooked_open)


@pytest.fixture(params=["ctime", "mode", "both"])
def differing_stat_sources(request, monkeypatch):
    """Model Windows' stable fstat/lstat differences on every CI platform."""
    real_fstat = os.fstat

    def by_descriptor(fd):
        metadata = real_fstat(fd)
        changes = {}
        if request.param in {"ctime", "both"}:
            # fstat can expose change time while lstat exposes creation time.
            changes["st_ctime_ns"] = metadata.st_ctime_ns + 1_000_000_000
        if request.param in {"mode", "both"}:
            # Path-based Windows stat can infer execute bits from a filename.
            changes["st_mode"] = metadata.st_mode ^ 0o111
        return _stat_with(metadata, **changes)

    monkeypatch.setattr(os, "fstat", by_descriptor)


@pytest.mark.parametrize("reader", ["hash", "raw", "eol"])
def test_stable_file_accepts_different_stat_sources(
    tmp_path, differing_stat_sources, reader,
):
    path = tmp_path / ".gitignore"
    path.write_bytes(CONTENT)
    result = _read_digest(path, reader)
    assert result == (hashlib.sha256(CONTENT).hexdigest() if reader == "hash" else True)


@pytest.mark.parametrize("filename", [".gitignore", "tool.exe", "tool.cmd"])
@pytest.mark.parametrize("content", [b"", b"\x00\xff\r\n", CONTENT])
def test_native_stat_hashes_regular_files(tmp_path, filename, content):
    path = tmp_path / filename
    path.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()

    assert manifest_module._sha256(path) == expected
    assert manifest_module._matches_recorded_hash(path, expected)


def test_codex_manifest_lifecycle_with_different_stat_sources(
    tmp_path, differing_stat_sources,
):
    """Exercise adoption, saved revisions, EOL matching, repair and cleanup."""
    relative = ".codex/skills/code-review-skill/.gitignore"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(CONTENT)
    manifest = IntegrationManifest("codex", tmp_path)
    manifest.record_existing(relative)
    assert manifest.files[relative] == hashlib.sha256(CONTENT).hexdigest()
    manifest.save()
    manifest.save()

    loaded = IntegrationManifest.load("codex", tmp_path)
    assert loaded.check_modified() == []
    path.write_bytes(CONTENT.replace(b"\r\n", b"\n"))
    assert loaded.check_modified() == []
    assert loaded.remove_file_if_unmodified(relative)
    loaded.save()

    loaded.record_file(relative, CONTENT)
    loaded.save()
    removed, skipped = loaded.uninstall()
    assert removed == [path]
    assert skipped == []
    assert not path.exists()
    assert not loaded.manifest_path.exists()


@pytest.mark.parametrize("differing_stat_sources", ["both"], indirect=True)
def test_user_modified_asset_is_preserved_with_different_stat_sources(
    tmp_path, differing_stat_sources,
):
    manifest = IntegrationManifest("codex", tmp_path)
    path = manifest.record_file("user.md", CONTENT)
    manifest.save()
    path.write_bytes(b"user changes\n")

    assert manifest.check_modified() == ["user.md"]
    assert not manifest.remove_file_if_unmodified("user.md")
    assert path.read_bytes() == b"user changes\n"


@pytest.mark.parametrize("reader", ["hash", "raw", "eol"])
@pytest.mark.parametrize("source", ["descriptor", "path"])
@pytest.mark.parametrize(
    "field", ["st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"],
)
def test_rejects_changes_in_each_observation(tmp_path, monkeypatch, reader, source, field):
    path = tmp_path / "asset.md"
    path.write_bytes(CONTENT)
    changed = False

    def after_read():
        nonlocal changed
        changed = True

    _hook_read(monkeypatch, after_read)
    if source == "descriptor":
        real_fstat = os.fstat

        def observe(fd):
            metadata = real_fstat(fd)
            return _stat_with(metadata, **{field: _different_value(metadata, field)}) if changed else metadata

        monkeypatch.setattr(os, "fstat", observe)
    else:
        real_lstat = Path.lstat

        def observe(target, *args, **kwargs):
            metadata = real_lstat(target, *args, **kwargs)
            if changed and target == path:
                return _stat_with(metadata, **{field: _different_value(metadata, field)})
            return metadata

        monkeypatch.setattr(Path, "lstat", observe)

    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read_digest(path, reader)
    assert changed
    assert path.read_bytes() == CONTENT


@pytest.mark.parametrize("reader", ["hash", "raw", "eol"])
def test_rejects_path_replaced_before_hash_baseline(tmp_path, monkeypatch, reader):
    """Separate metadata baselines must still refer to the same opened file."""
    path = tmp_path / "asset.md"
    path.write_bytes(CONTENT)
    real_open = manifest_module._open_regular_state_file
    real_lstat = Path.lstat

    def replaced_stat(target, *args, **kwargs):
        metadata = real_lstat(target, *args, **kwargs)
        if target == path:
            return _stat_with(metadata, st_ino=metadata.st_ino + 1)
        return metadata

    @contextmanager
    def swapped_open(target):
        with real_open(target) as handle:
            monkeypatch.setattr(Path, "lstat", replaced_stat)
            yield handle

    monkeypatch.setattr(manifest_module, "_open_regular_state_file", swapped_open)
    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read_digest(path, reader)


@pytest.mark.parametrize("reader", ["hash", "raw", "eol"])
def test_rejects_real_in_place_write(tmp_path, monkeypatch, reader):
    path = tmp_path / "asset.md"
    path.write_bytes(CONTENT)
    metadata = path.stat()
    changed = CONTENT.replace(b"first", b"other")

    def write_during_read():
        path.write_bytes(changed)
        os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000_000))

    _hook_read(monkeypatch, write_during_read)
    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read_digest(path, reader)
    assert path.read_bytes() == changed


@pytest.mark.parametrize("source", ["descriptor", "path"])
def test_eol_pass_rechecks_original_ctime(tmp_path, monkeypatch, source):
    path = tmp_path / "asset.md"
    path.write_bytes(CONTENT)
    rewound = False

    def after_rewind():
        nonlocal rewound
        rewound = True

    def changed_metadata(metadata):
        if rewound:
            return _stat_with(metadata, st_ctime_ns=metadata.st_ctime_ns + 1)
        return metadata

    if source == "descriptor":
        real_fstat = os.fstat
        monkeypatch.setattr(os, "fstat", lambda fd: changed_metadata(real_fstat(fd)))
    else:
        real_lstat = Path.lstat

        def observe(target, *args, **kwargs):
            metadata = real_lstat(target, *args, **kwargs)
            return changed_metadata(metadata) if target == path else metadata

        monkeypatch.setattr(Path, "lstat", observe)

    _hook_read(monkeypatch, after_rewind, on_rewind=True)
    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read_digest(path, "eol")
    assert rewound
