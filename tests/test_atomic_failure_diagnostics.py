"""Secondary stage-cleanup errors must not change write/retry/cancel semantics.

Use real files and publication owners. OS failures are controlled injections;
the final child sends itself an actual SIGINT before byte publication.
"""
from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from specify_cli import atomic_io
from specify_cli.integrations import manifest as manifest_module


WRITERS = ("text", "bytes", "text-private", "bytes-private")
PAYLOAD = "private payload 中文\r\n"  # Must never appear in cleanup diagnostics.


def publish(path: Path, writer: str) -> None:
    options = {"new_file_mode": 0o600} if writer.endswith("-private") else {}
    if writer.startswith("text"):
        atomic_io.atomic_write_text(path, PAYLOAD, **options)
    else:
        atomic_io.atomic_write_bytes(path, PAYLOAD.encode("utf-8"), **options)


def setup_target(root: Path, writer: str) -> Path:
    target = root / "state.json"
    # Exercise exclusive-creation mode as well as the existing-file staging path.
    if not writer.endswith("-private"):
        target.write_bytes(b"old valid state")
    return target


def assert_old_state(target: Path, writer: str) -> None:
    if writer.endswith("-private"):
        assert not target.exists()
    else:
        assert target.read_bytes() == b"old valid state"


def deny_stage_cleanup(monkeypatch):
    original = Path.unlink
    retained = []

    def fail(path, *args, **kwargs):
        if path.suffix == ".tmp":
            retained.append(path)
            raise PermissionError(errno.EACCES, "stage still in use", str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail)
    return retained


@pytest.mark.parametrize("writer", WRITERS)
@pytest.mark.parametrize("phase", ["flush", "replace"])
def test_original_io_error_errno_traceback_and_notes_survive(tmp_path, monkeypatch, writer, phase):
    target = setup_target(tmp_path, writer)
    code = errno.ENOSPC if phase == "flush" else errno.EXDEV
    original_error = OSError(code, "original publication error")
    original_error.add_note("caller context retained")
    cause = RuntimeError("underlying source cause")

    def fail(*args, **kwargs):
        raise original_error from cause

    with monkeypatch.context() as patch:
        retained = deny_stage_cleanup(patch)
        patch.setattr(atomic_io.os, "fsync" if phase == "flush" else "replace", fail)
        with pytest.raises(OSError) as raised:
            publish(target, writer)
    assert raised.value is original_error
    assert raised.value.errno == code
    assert raised.value.__cause__ is cause
    frames, traceback = [], raised.value.__traceback__
    while traceback is not None:
        frames.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "fail" in frames
    assert len(retained) == 1 and retained[0].is_file()
    notes = raised.value.__notes__
    assert notes[0] == "caller context retained" and len(notes) == 2
    assert "cleanup failed" in notes[1] and str(retained[0]) in notes[1]
    assert "stage still in use" in notes[1]
    assert PAYLOAD not in notes[1]
    assert_old_state(target, writer)
    # Resolving the fault permits a deliberate fresh call. Never sweep other
    # temporary files left by previous failed calls as part of a later write.
    publish(target, writer)
    assert target.read_bytes() == PAYLOAD.encode("utf-8")
    assert retained[0].exists()


@pytest.mark.parametrize("writer", ["text", "bytes"])
@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_cancellation_keeps_its_original_type_and_value(tmp_path, monkeypatch, writer, error_type):
    target = setup_target(tmp_path, writer)
    original_error = error_type(19)
    with monkeypatch.context() as patch:
        retained = deny_stage_cleanup(patch)

        def fail(*args, **kwargs):
            raise original_error

        patch.setattr(atomic_io.os, "replace", fail)
        with pytest.raises(error_type) as raised:
            publish(target, writer)
    assert raised.value is original_error and raised.value.args == (19,)
    assert len(raised.value.__notes__) == 1
    assert str(retained[0]) in raised.value.__notes__[0]
    assert_old_state(target, writer)


@pytest.mark.parametrize("writer", WRITERS)
def test_successful_cleanup_does_not_add_notes_or_leave_files(tmp_path, monkeypatch, writer):
    target = setup_target(tmp_path, writer)
    original_error = OSError(errno.ENOSPC, "original disk error")

    def fail(*args, **kwargs):
        raise original_error

    monkeypatch.setattr(atomic_io.os, "replace", fail)
    with pytest.raises(OSError) as raised:
        publish(target, writer)
    assert raised.value is original_error
    assert not hasattr(original_error, "__notes__")
    assert not list(tmp_path.glob("*.tmp"))
    assert_old_state(target, writer)


def test_already_removed_stage_does_not_mask_the_original_error(tmp_path, monkeypatch):
    target = setup_target(tmp_path, "bytes")
    original_error = OSError(errno.EIO, "publish failed")

    def fail(source, destination):
        Path(source).unlink()
        raise original_error

    monkeypatch.setattr(atomic_io.os, "replace", fail)
    with pytest.raises(OSError) as raised:
        publish(target, "bytes")
    assert raised.value is original_error and not hasattr(original_error, "__notes__")
    assert not list(tmp_path.glob("*.tmp"))
    assert_old_state(target, "bytes")


def test_no_stage_created_means_no_cleanup_attempt(tmp_path, monkeypatch):
    original_error = OSError(errno.ENOSPC, "cannot create stage")

    def fail(*args, **kwargs):
        raise original_error

    monkeypatch.setattr(atomic_io.tempfile, "NamedTemporaryFile", fail)
    retained = deny_stage_cleanup(monkeypatch)
    with pytest.raises(OSError) as raised:
        atomic_io.atomic_write_bytes(tmp_path / "state", b"value")
    assert raised.value is original_error and retained == []
    assert not hasattr(original_error, "__notes__")


@pytest.mark.parametrize("kind", ["disk-full", "interrupt", "exit"])
def test_record_file_does_not_retry_fatal_or_cancelled_write_after_cleanup_error(tmp_path, monkeypatch, kind):
    manifest = manifest_module.IntegrationManifest("claude", tmp_path)
    target = manifest.record_file("asset.txt", "current asset")
    manifest.save()
    before_json = manifest.manifest_path.read_bytes()
    before_records = manifest.files
    error = {"disk-full": OSError(errno.ENOSPC, "disk full"),
             "interrupt": KeyboardInterrupt(), "exit": SystemExit(9)}[kind]
    replace, calls, sleeps = atomic_io.os.replace, [], []

    def fail_first(source, destination):
        if Path(destination) == target:
            calls.append(str(source))
            if len(calls) == 1:
                raise error
        return replace(source, destination)

    with monkeypatch.context() as patch:
        retained = deny_stage_cleanup(patch)
        patch.setattr(atomic_io.os, "replace", fail_first)
        patch.setattr(manifest_module.time, "sleep", lambda seconds: sleeps.append(seconds))
        with pytest.raises(type(error)) as raised:
            manifest.record_file("asset.txt", "must not be published")
    assert raised.value is error
    assert len(calls) == 1 and sleeps == []
    assert len(retained) == 1 and retained[0].exists()
    assert target.read_bytes() == b"current asset"
    assert manifest.files == before_records
    assert manifest.manifest_path.read_bytes() == before_json
    # The caller still owns recovery; a later explicit call succeeds normally.
    manifest.record_file("asset.txt", "deliberately retried")
    manifest.save()
    assert manifest_module.IntegrationManifest.load("claude", tmp_path).check_modified() == []


def test_a_real_sigint_cannot_be_converted_into_a_successful_retry(tmp_path):
    script = tmp_path / "cancel_write.py"
    script.write_text('''import json, os, pathlib, signal, sys, types
pkg = types.ModuleType("specify_cli")
pkg.__path__ = [sys.argv[1]]
sys.modules["specify_cli"] = pkg
from specify_cli import atomic_io
from specify_cli.integrations.manifest import IntegrationManifest
root = pathlib.Path(sys.argv[2])
manifest = IntegrationManifest("claude", root)
target = manifest.record_file("asset.txt", "old")
manifest.save()
records = manifest.files
metadata = manifest.manifest_path.read_bytes()
replace = atomic_io.os.replace
unlink = pathlib.Path.unlink
calls = []
def interrupt(source, destination):
    if pathlib.Path(destination) == target:
        calls.append(1)
        if len(calls) == 1:
            os.kill(os.getpid(), signal.SIGINT)
    return replace(source, destination)
def deny_stage(path, *args, **kwargs):
    if path.suffix == ".tmp":
        raise PermissionError(13, "controlled cleanup failure", str(path))
    return unlink(path, *args, **kwargs)
atomic_io.os.replace = interrupt
pathlib.Path.unlink = deny_stage
cancelled = False
notes = []
try:
    manifest.record_file("asset.txt", "new")
except KeyboardInterrupt as error:
    cancelled = True
    notes = getattr(error, "__notes__", [])
finally:
    atomic_io.os.replace = replace
    pathlib.Path.unlink = unlink
print(json.dumps({"cancelled": cancelled, "attempts":len(calls),
                 "asset_preserved":target.read_bytes() == b"old",
                 "records_preserved":manifest.files == records,
                 "metadata_preserved":manifest.manifest_path.read_bytes() == metadata,
                 "cleanup_note":any("cleanup failed" in note for note in notes)}))
''', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(script), str(Path(atomic_io.__file__).parent),
         str(tmp_path / "project")], stdin=subprocess.DEVNULL, capture_output=True,
        text=True, encoding="utf-8", timeout=10, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "cancelled": True, "attempts": 1, "asset_preserved": True,
        "records_preserved": True, "metadata_preserved": True, "cleanup_note": True,
    }
