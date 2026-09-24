"""Release errors must not replace the failure from protected work.

Use real POSIX locks/descriptors, injecting only the explicit unlock failure.
Closing the descriptor must still release the OS lock; never unlink its path.
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
from specify_cli.integrations.manifest import IntegrationManifest

pytestmark = pytest.mark.skipif(os.name == "nt", reason="real POSIX lock release regression")


def failed_unlock(monkeypatch):
    import fcntl

    original = fcntl.flock
    descriptors = []
    cleanup = PermissionError(errno.EACCES, "controlled unlock failure")

    def flock(fd, operation):
        if operation == fcntl.LOCK_UN:
            descriptors.append(fd)
            raise cleanup
        return original(fd, operation)

    monkeypatch.setattr(fcntl, "flock", flock)
    return descriptors, cleanup


def assert_closed_and_reusable(path: Path, descriptors: list[int]) -> None:
    assert len(descriptors) == 1
    with pytest.raises(OSError) as raised:
        os.fstat(descriptors[0])
    assert raised.value.errno == errno.EBADF
    # A new real acquisition proves the failed explicit unlock did not leak
    # the OS lock. The original coordination inode must remain in place.
    before = path.stat()
    with atomic_io.interprocess_lock(path, timeout=0):
        assert os.path.samestat(before, path.stat())


@pytest.mark.parametrize("kind", ["disk-full", "value", "interrupt", "exit"])
def test_protected_failure_keeps_identity_cause_traceback_and_notes(tmp_path, monkeypatch, kind):
    path = tmp_path / "lock 中文"
    path.write_bytes(b"retained lock contents")
    before = path.stat()
    primary = {
        "disk-full": OSError(errno.ENOSPC, "original disk full"),
        "value": ValueError("original validation failure"),
        "interrupt": KeyboardInterrupt(),
        "exit": SystemExit(17),
    }[kind]
    cause = RuntimeError("original cause")
    primary.add_note("caller note")

    def protected_work():
        raise primary from cause

    with monkeypatch.context() as patch:
        descriptors, _ = failed_unlock(patch)
        with pytest.raises(type(primary)) as raised:
            with atomic_io.interprocess_lock(path):
                protected_work()
    assert raised.value is primary
    assert raised.value.__cause__ is cause
    assert primary.__notes__[0] == "caller note"
    assert len(primary.__notes__) == 2
    assert "Lock release failed" in primary.__notes__[1]
    assert str(path) in primary.__notes__[1]
    frames, tb = [], primary.__traceback__
    while tb is not None:
        frames.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    assert "protected_work" in frames
    assert os.path.samestat(before, path.stat())
    assert path.read_bytes() == b"retained lock contents"
    assert_closed_and_reusable(path, descriptors)


def test_release_failure_without_primary_failure_still_raises(tmp_path, monkeypatch):
    path = tmp_path / "state.lock"
    with monkeypatch.context() as patch:
        descriptors, cleanup = failed_unlock(patch)
        with pytest.raises(PermissionError) as raised:
            with atomic_io.interprocess_lock(path):
                pass
    assert raised.value is cleanup
    assert not hasattr(cleanup, "__notes__")
    assert_closed_and_reusable(path, descriptors)


def test_normal_release_does_not_add_failure_notes(tmp_path):
    path = tmp_path / "state.lock"
    primary = RuntimeError("work failed")
    with pytest.raises(RuntimeError) as raised:
        with atomic_io.interprocess_lock(path):
            raise primary
    assert raised.value is primary
    assert not hasattr(primary, "__notes__")
    with atomic_io.interprocess_lock(path, timeout=0):
        pass


def test_post_acquisition_guard_failure_is_not_masked(tmp_path, monkeypatch):
    import fcntl

    path = tmp_path / "state.lock"
    primary = ValueError("changed lock observation")
    original_stat = atomic_io._regular_state_stat
    original_flock = fcntl.flock
    acquired = False
    descriptors = []

    def flock(fd, operation):
        nonlocal acquired
        if operation == fcntl.LOCK_UN:
            descriptors.append(fd)
            raise OSError(errno.EIO, "unlock also failed")
        original_flock(fd, operation)
        acquired = True

    def stat_after_acquisition(target, **kwargs):
        if acquired and target == path:
            raise primary
        return original_stat(target, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(fcntl, "flock", flock)
        patch.setattr(atomic_io, "_regular_state_stat", stat_after_acquisition)
        with pytest.raises(ValueError) as raised:
            with atomic_io.interprocess_lock(path):
                pytest.fail("failed guard entered protected work")
    assert raised.value is primary
    assert "unlock also failed" in primary.__notes__[0]
    assert_closed_and_reusable(path, descriptors)


@pytest.mark.parametrize("action", ["save", "record"])
def test_manifest_io_error_is_preserved_with_state_intact(tmp_path, monkeypatch, action):
    manifest = IntegrationManifest("test", tmp_path)
    asset = manifest.record_file("asset.txt", "old")
    manifest.save()
    metadata = manifest.manifest_path.read_bytes()
    records = manifest.files
    primary = OSError(errno.ENOSPC, "original publication failure")
    manifest.version = "pending change"

    def fail_replace(*args, **kwargs):
        raise primary

    with monkeypatch.context() as patch:
        descriptors, _ = failed_unlock(patch)
        patch.setattr(atomic_io.os, "replace", fail_replace)
        with pytest.raises(OSError) as raised:
            if action == "save":
                manifest.save()
            else:
                manifest.record_file("asset.txt", "new")
    assert raised.value is primary
    assert raised.value.errno == errno.ENOSPC
    assert manifest.manifest_path.read_bytes() == metadata
    assert manifest.files == records
    assert asset.read_bytes() == b"old"
    lock = tmp_path / ".specify/runtime/manifest-test.lock"
    assert_closed_and_reusable(lock, descriptors)
    manifest.save()
    assert IntegrationManifest.load("test", tmp_path).version == "pending change"


def test_actual_sigint_survives_unlock_error_in_child(tmp_path):
    script = r'''import fcntl, importlib.util, json, os, pathlib, signal, sys
spec = importlib.util.spec_from_file_location("state_io", sys.argv[1])
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
path = pathlib.Path(sys.argv[2])
original = fcntl.flock
def flock(fd, operation):
    if operation == fcntl.LOCK_UN:
        raise OSError(5, "controlled unlock failure")
    return original(fd, operation)
fcntl.flock = flock
cancelled = False
noted = False
try:
    with owner.interprocess_lock(path):
        os.kill(os.getpid(), signal.SIGINT)
except KeyboardInterrupt as error:
    cancelled = True
    noted = any("Lock release failed" in note for note in error.__notes__)
finally:
    fcntl.flock = original
with owner.interprocess_lock(path, timeout=0):
    released = True
print(json.dumps({"cancelled": cancelled, "noted": noted, "released": released}))
'''
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script, atomic_io.__file__,
         str(tmp_path / "signal.lock")], stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=5, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"cancelled": True, "noted": True, "released": True}
