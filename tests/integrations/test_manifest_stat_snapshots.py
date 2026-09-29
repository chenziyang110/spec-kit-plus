"""Manifest hashing must compare metadata from the same stat API.

Windows can expose different ctime values (and filename-derived executable
bits) through fstat and lstat for the same unchanged file. Simulate that on
any CI host, while retaining coverage of actual mutations and replacements.
"""

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.integrations import manifest as manifest_module


CONTENT = b"alpha\r\nbeta\r\n"
READERS = ("sha256", "raw", "eol")


def _stat_view(metadata, **overrides):
    fields = {
        name: getattr(metadata, name)
        for name in dir(metadata)
        if name.startswith("st_")
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _read(reader, path):
    if reader == "sha256":
        return manifest_module._sha256(path)
    expected = CONTENT if reader == "raw" else CONTENT.replace(b"\r\n", b"\n")
    return manifest_module._matches_recorded_hash(
        path, hashlib.sha256(expected).hexdigest(),
    )


def _divergent_fstat(monkeypatch, field):
    real_fstat = os.fstat

    def fstat(fd):
        metadata = real_fstat(fd)
        overrides = {}
        if field in ("ctime", "both"):
            overrides["st_ctime_ns"] = metadata.st_ctime_ns + 10_000_000_000
        if field in ("mode", "both"):
            overrides["st_mode"] = metadata.st_mode ^ 0o111
        return _stat_view(metadata, **overrides)

    monkeypatch.setattr(os, "fstat", fstat)


def _after_read(monkeypatch, callback):
    """Run a deterministic mutation after a bounded read, not on a timer."""
    real_open = manifest_module._open_regular_state_file

    @contextmanager
    def observed_open(path):
        with real_open(path) as handle:
            class Reader:
                pass_number = 1

                def fileno(self):
                    return handle.fileno()

                def read(self, size):
                    assert 0 < size <= 65536
                    chunk = handle.read(size)
                    if chunk:
                        callback(self.pass_number)
                    return chunk

                def seek(self, offset):
                    self.pass_number += 1
                    return handle.seek(offset)

            yield Reader()

    monkeypatch.setattr(manifest_module, "_open_regular_state_file", observed_open)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("field", ("ctime", "mode", "both"))
def test_unchanged_file_accepts_distinct_stat_api_metadata(
    tmp_path, monkeypatch, reader, field,
):
    target = tmp_path / ".gitignore"
    target.write_bytes(CONTENT)
    _divergent_fstat(monkeypatch, field)

    result = _read(reader, target)

    assert result == (hashlib.sha256(CONTENT).hexdigest() if reader == "sha256" else True)
    assert target.read_bytes() == CONTENT


@pytest.mark.parametrize("filename", (".gitignore", "tool.exe", "tool.cmd"))
@pytest.mark.parametrize("content", (b"", b"\x00\xff\r\n", CONTENT))
def test_native_stat_hashes_regular_files(tmp_path, filename, content):
    target = tmp_path / filename
    target.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()

    assert manifest_module._sha256(target) == expected
    assert manifest_module._matches_recorded_hash(target, expected)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("api", ("fstat", "lstat"))
@pytest.mark.parametrize("field", ("st_ctime_ns", "st_mtime_ns", "st_size", "st_mode", "st_ino"))
def test_same_api_changes_are_still_rejected(
    tmp_path, monkeypatch, reader, api, field,
):
    target = tmp_path / ".gitignore"
    target.write_bytes(CONTENT)
    changed = False

    def mark_changed(_pass_number):
        nonlocal changed
        changed = True

    def observe(metadata):
        if not changed:
            return metadata
        value = getattr(metadata, field)
        return _stat_view(metadata, **{field: value ^ 0o200 if field == "st_mode" else value + 1})

    if api == "fstat":
        real_fstat = os.fstat
        monkeypatch.setattr(os, "fstat", lambda fd: observe(real_fstat(fd)))
    else:
        real_lstat = Path.lstat

        def lstat(path, *args, **kwargs):
            metadata = real_lstat(path, *args, **kwargs)
            return observe(metadata) if path == target else metadata

        monkeypatch.setattr(Path, "lstat", lstat)
    _after_read(monkeypatch, mark_changed)

    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read(reader, target)
    assert target.read_bytes() == CONTENT


@pytest.mark.parametrize("api", ("fstat", "lstat"))
def test_second_eol_pass_rechecks_both_original_snapshots(tmp_path, monkeypatch, api):
    target = tmp_path / ".gitignore"
    target.write_bytes(CONTENT)
    changed = False

    def mark_changed(pass_number):
        nonlocal changed
        changed = pass_number == 2

    def observe(metadata):
        if changed:
            return _stat_view(metadata, st_ctime_ns=metadata.st_ctime_ns + 1)
        return metadata

    if api == "fstat":
        real_fstat = os.fstat
        monkeypatch.setattr(os, "fstat", lambda fd: observe(real_fstat(fd)))
    else:
        real_lstat = Path.lstat

        def lstat(path, *args, **kwargs):
            metadata = real_lstat(path, *args, **kwargs)
            return observe(metadata) if path == target else metadata

        monkeypatch.setattr(Path, "lstat", lstat)
    _after_read(monkeypatch, mark_changed)

    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read("eol", target)
    assert changed


@pytest.mark.parametrize("reader", READERS)
def test_path_baseline_must_identify_open_descriptor(tmp_path, monkeypatch, reader):
    target = tmp_path / ".gitignore"
    target.write_bytes(CONTENT)
    real_open = manifest_module._open_regular_state_file
    real_lstat = Path.lstat
    opened = False

    def lstat(path, *args, **kwargs):
        metadata = real_lstat(path, *args, **kwargs)
        if path == target and opened:
            return _stat_view(metadata, st_ino=metadata.st_ino + 1)
        return metadata

    @contextmanager
    def replaced_open(path):
        nonlocal opened
        with real_open(path) as handle:
            opened = True
            yield handle

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(manifest_module, "_open_regular_state_file", replaced_open)

    with pytest.raises(ValueError, match="Manifest file changed while hashing"):
        _read(reader, target)


@pytest.mark.parametrize("field", ("ctime", "mode", "both"))
def test_codex_record_save_reload_and_cleanup_with_distinct_stat_views(
    tmp_path, monkeypatch, field,
):
    relative = ".codex/skills/code-review-skill/.gitignore"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(CONTENT)
    _divergent_fstat(monkeypatch, field)
    manifest = manifest_module.IntegrationManifest("codex", tmp_path)

    manifest.record_existing(relative)
    manifest.save()
    loaded = manifest_module.IntegrationManifest.load("codex", tmp_path)

    assert loaded.files == {relative: hashlib.sha256(CONTENT).hexdigest()}
    assert loaded.check_modified() == []
    assert loaded.remove_file_if_unmodified(relative)
    assert not target.exists()


def test_user_modified_asset_is_preserved_with_distinct_stat_views(tmp_path, monkeypatch):
    _divergent_fstat(monkeypatch, "both")
    manifest = manifest_module.IntegrationManifest("codex", tmp_path)
    target = manifest.record_file("user.md", CONTENT)
    manifest.save()
    target.write_bytes(b"user changes\n")

    assert manifest.check_modified() == ["user.md"]
    assert not manifest.remove_file_if_unmodified("user.md")
    assert target.read_bytes() == b"user changes\n"
