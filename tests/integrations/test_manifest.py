"""Tests for IntegrationManifest — record, hash, save, load, uninstall, modified detection."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from specify_cli.integrations.manifest import IntegrationManifest, _sha256


class TestManifestRecordFile:
    def test_record_file_writes_and_hashes(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        content = "hello world"
        abs_path = m.record_file("a/b.txt", content)
        assert abs_path == tmp_path / "a" / "b.txt"
        assert abs_path.read_text(encoding="utf-8") == content
        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        assert m.files["a/b.txt"] == expected_hash

    def test_record_file_bytes(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        data = b"\x00\x01\x02"
        abs_path = m.record_file("bin.dat", data)
        assert abs_path.read_bytes() == data
        assert m.files["bin.dat"] == hashlib.sha256(data).hexdigest()

    def test_record_existing(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("content", encoding="utf-8")
        m = IntegrationManifest("test", tmp_path)
        m.record_existing("existing.txt")
        assert m.files["existing.txt"] == _sha256(f)


class TestManifestPathTraversal:
    def test_write_operations_reject_paths_outside_project(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        with pytest.raises(ValueError, match="outside"):
            m.record_file("../escape.txt", "bad")
        absolute_path = Path("C:/tmp/escape.txt") if os.name == "nt" else Path("/tmp/escape.txt")
        with pytest.raises(ValueError, match="Absolute paths|outside"):
            m.record_file(absolute_path, "bad")
        escape = tmp_path.parent / "escape.txt"
        escape.write_text("evil", encoding="utf-8")
        try:
            with pytest.raises(ValueError, match="outside"):
                m.record_existing("../escape.txt")
        finally:
            escape.unlink(missing_ok=True)

    def test_uninstall_skips_traversal_paths(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("safe.txt", "good")
        m._files["../outside.txt"] = "fakehash"
        m.save()
        removed, skipped = m.uninstall()
        assert len(removed) == 1
        assert removed[0].name == "safe.txt"


class TestManifestCheckModified:
    def test_check_modified_reports_only_changed_existing_files(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "original")
        assert m.check_modified() == []

        (tmp_path / "f.txt").write_text("changed", encoding="utf-8")
        assert m.check_modified() == ["f.txt"]

        (tmp_path / "f.txt").unlink()
        assert m.check_modified() == []

    def test_symlink_treated_as_modified(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "original")
        target = tmp_path / "target.txt"
        target.write_text("target", encoding="utf-8")
        (tmp_path / "f.txt").unlink()
        if not _can_create_symlink(tmp_path):
            pytest.skip("symlink creation not permitted in this environment")
        (tmp_path / "f.txt").symlink_to(target)
        assert m.check_modified() == ["f.txt"]


class TestManifestRemoveFileIfUnmodified:
    def test_preserves_symlink_to_another_tracked_file(self, tmp_path, monkeypatch):
        manifest = IntegrationManifest("test", tmp_path)
        current = manifest.record_file("skills/current.md", "current content")
        stale = manifest.record_file("skills/stale.md", "stale content")
        real_resolve = Path.resolve
        real_is_symlink = Path.is_symlink

        def resolve_symlink(path, *args, **kwargs):
            if path == stale:
                return current
            return real_resolve(path, *args, **kwargs)

        def identify_symlink(path):
            return path == stale or real_is_symlink(path)

        monkeypatch.setattr(Path, "resolve", resolve_symlink)
        monkeypatch.setattr(Path, "is_symlink", identify_symlink)

        removed = manifest.remove_file_if_unmodified("skills/stale.md")

        assert removed is False
        assert stale.is_symlink()
        assert stale.read_text(encoding="utf-8") == "stale content"
        assert current.read_text(encoding="utf-8") == "current content"
        assert "skills/current.md" in manifest.files
        assert "skills/stale.md" in manifest.files

    def test_preserves_file_beneath_symlinked_parent(self, tmp_path, monkeypatch):
        manifest = IntegrationManifest("test", tmp_path)
        target = manifest.record_file("real/current.md", "current content")
        linked_parent = tmp_path / "alias"
        stale = manifest.record_file("alias/stale.md", "stale content")
        real_resolve = Path.resolve
        real_is_symlink = Path.is_symlink

        def resolve_symlink(path, *args, **kwargs):
            if path == stale:
                return target
            return real_resolve(path, *args, **kwargs)

        def identify_symlink(path):
            return path == linked_parent or real_is_symlink(path)

        monkeypatch.setattr(Path, "resolve", resolve_symlink)
        monkeypatch.setattr(Path, "is_symlink", identify_symlink)

        removed = manifest.remove_file_if_unmodified("alias/stale.md")

        assert removed is False
        assert stale.read_text(encoding="utf-8") == "stale content"
        assert target.read_text(encoding="utf-8") == "current content"
        assert "real/current.md" in manifest.files
        assert "alias/stale.md" in manifest.files

    def test_preserves_file_beneath_junction_parent(self, tmp_path, monkeypatch):
        manifest = IntegrationManifest("test", tmp_path)
        stale = manifest.record_file("alias/stale.md", "stale content")
        junction_parent = tmp_path / "alias"
        real_is_junction = getattr(Path, "is_junction", None)

        def identify_junction(path):
            if path == junction_parent:
                return True
            return bool(real_is_junction and real_is_junction(path))

        monkeypatch.setattr(Path, "is_junction", identify_junction, raising=False)

        removed = manifest.remove_file_if_unmodified("alias/stale.md")

        assert removed is False
        assert stale.read_text(encoding="utf-8") == "stale content"
        assert "alias/stale.md" in manifest.files

    @pytest.mark.skipif(os.name != "nt", reason="drive-relative paths are Windows-only")
    def test_rejects_drive_relative_manifest_path(self, tmp_path):
        manifest = IntegrationManifest("test", tmp_path)
        manifest._files["C:escape.txt"] = "0" * 64

        with pytest.raises(ValueError, match="Unsafe manifest path"):
            manifest.remove_file_if_unmodified("C:escape.txt")

    def test_preserves_symlink_whose_target_is_outside_project(
        self, tmp_path, monkeypatch
    ):
        manifest = IntegrationManifest("test", tmp_path)
        stale = manifest.record_file("skills/stale.md", "stale content")
        outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
        outside.write_text("outside content", encoding="utf-8")
        real_resolve = Path.resolve
        real_is_symlink = Path.is_symlink

        def resolve_symlink(path, *args, **kwargs):
            if path == stale:
                return outside
            return real_resolve(path, *args, **kwargs)

        def identify_symlink(path):
            return path == stale or real_is_symlink(path)

        monkeypatch.setattr(Path, "resolve", resolve_symlink)
        monkeypatch.setattr(Path, "is_symlink", identify_symlink)
        try:
            removed = manifest.remove_file_if_unmodified("skills/stale.md")

            assert removed is False
            assert stale.is_symlink()
            assert stale.read_text(encoding="utf-8") == "stale content"
            assert outside.read_text(encoding="utf-8") == "outside content"
            assert "skills/stale.md" in manifest.files
        finally:
            outside.unlink(missing_ok=True)


class TestManifestUninstall:
    def test_removes_unmodified(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("d/f.txt", "content")
        m.save()
        removed, skipped = m.uninstall()
        assert len(removed) == 1
        assert not (tmp_path / "d" / "f.txt").exists()
        assert not (tmp_path / "d").exists()
        assert skipped == []

    def test_skips_modified(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "original")
        m.save()
        (tmp_path / "f.txt").write_text("modified", encoding="utf-8")
        removed, skipped = m.uninstall()
        assert removed == []
        assert len(skipped) == 1
        assert (tmp_path / "f.txt").exists()

    def test_force_removes_modified(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "original")
        m.save()
        (tmp_path / "f.txt").write_text("modified", encoding="utf-8")
        removed, skipped = m.uninstall(force=True)
        assert len(removed) == 1
        assert skipped == []

    def test_already_deleted_file(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "content")
        m.save()
        (tmp_path / "f.txt").unlink()
        removed, skipped = m.uninstall()
        assert removed == []
        assert skipped == []

    def test_removes_manifest_file(self, tmp_path):
        m = IntegrationManifest("test", tmp_path, version="1.0")
        m.record_file("f.txt", "content")
        m.save()
        assert m.manifest_path.exists()
        m.uninstall()
        assert not m.manifest_path.exists()

    def test_cleans_empty_parent_dirs(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("a/b/c/f.txt", "content")
        m.save()
        m.uninstall()
        assert not (tmp_path / "a").exists()

    def test_preserves_nonempty_parent_dirs(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("a/b/tracked.txt", "content")
        (tmp_path / "a" / "b" / "other.txt").write_text("keep", encoding="utf-8")
        m.save()
        m.uninstall()
        assert not (tmp_path / "a" / "b" / "tracked.txt").exists()
        assert (tmp_path / "a" / "b" / "other.txt").exists()

    def test_symlink_skipped_without_force(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "original")
        m.save()
        target = tmp_path / "target.txt"
        target.write_text("target", encoding="utf-8")
        (tmp_path / "f.txt").unlink()
        if not _can_create_symlink(tmp_path):
            pytest.skip("symlink creation not permitted in this environment")
        (tmp_path / "f.txt").symlink_to(target)
        removed, skipped = m.uninstall()
        assert removed == []
        assert len(skipped) == 1

    def test_symlink_removed_with_force(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "original")
        m.save()
        target = tmp_path / "target.txt"
        target.write_text("target", encoding="utf-8")
        (tmp_path / "f.txt").unlink()
        if not _can_create_symlink(tmp_path):
            pytest.skip("symlink creation not permitted in this environment")
        (tmp_path / "f.txt").symlink_to(target)
        removed, skipped = m.uninstall(force=True)
        assert len(removed) == 1
        assert target.exists()


def _can_create_symlink(tmp_path) -> bool:
    probe_target = tmp_path / "symlink-target.txt"
    probe_link = tmp_path / "symlink-probe.txt"
    probe_target.write_text("probe", encoding="utf-8")
    try:
        probe_link.symlink_to(probe_target)
        return True
    except OSError:
        return False
    finally:
        probe_link.unlink(missing_ok=True)
        probe_target.unlink(missing_ok=True)


class TestManifestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        m = IntegrationManifest("myagent", tmp_path, version="2.0.1")
        m.record_file("dir/file.md", "# Hello")
        m.save()
        loaded = IntegrationManifest.load("myagent", tmp_path)
        assert loaded.key == "myagent"
        assert loaded.version == "2.0.1"
        assert loaded.files == m.files

    def test_manifest_path(self, tmp_path):
        m = IntegrationManifest("copilot", tmp_path)
        assert m.manifest_path == tmp_path / ".specify" / "integrations" / "copilot.manifest.json"

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            IntegrationManifest.load("nonexistent", tmp_path)

    def test_save_creates_directories(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "content")
        path = m.save()
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["integration"] == "test"

    def test_save_preserves_installed_at(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        m.record_file("f.txt", "content")
        m.save()
        first_ts = m._installed_at
        m.save()
        assert m._installed_at == first_ts


class TestManifestLoadValidation:
    def test_load_rejects_invalid_manifest_shapes(self, tmp_path):
        path = tmp_path / ".specify" / "integrations" / "bad.manifest.json"
        path.parent.mkdir(parents=True)
        cases = [
            ('"just a string"', "JSON object"),
            (json.dumps({"files": ["not", "a", "dict"]}), "mapping"),
            (json.dumps({"files": {"a.txt": 123}}), "mapping"),
        ]

        for content, error_match in cases:
            path.write_text(content, encoding="utf-8")
            with pytest.raises(ValueError, match=error_match):
                IntegrationManifest.load("bad", tmp_path)

    def test_load_invalid_json_raises(self, tmp_path):
        path = tmp_path / ".specify" / "integrations" / "bad.manifest.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            IntegrationManifest.load("bad", tmp_path)
