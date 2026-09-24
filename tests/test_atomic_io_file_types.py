"""Real special-file and descriptor regressions for the shared state I/O owner."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from specify_cli import atomic_io


_OPERATIONS = ("read-bytes", "read-text", "lock", "write-bytes", "write-text")


def operate(path: Path, operation: str):
    if operation == "read-bytes":
        return atomic_io.read_local_state_bytes(path)
    if operation == "read-text":
        return atomic_io.read_local_state_text(path)
    if operation == "write-bytes":
        return atomic_io.atomic_write_bytes(path, b"replacement\r\n\x00")
    if operation == "write-text":
        return atomic_io.atomic_write_text(path, "replacement 中文\n")
    with atomic_io.interprocess_lock(path):
        return "entered"


def fifo(path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("this host has no POSIX FIFO support")
    os.mkfifo(path)


def isolated_call(tmp_path: Path, path: Path, operation: str):
    # A separate process bounds regression hangs without leaving blocked threads.
    # It loads the complete atomic_io owner, not the heavy CLI initializer.
    script = tmp_path / "call.py"
    script.write_text('''import importlib.util, json, pathlib, sys
spec = importlib.util.spec_from_file_location("state_io", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
path, op = pathlib.Path(sys.argv[2]), sys.argv[3]
try:
    if op == "read-bytes": module.read_local_state_bytes(path)
    elif op == "read-text": module.read_local_state_text(path)
    elif op == "lock":
        with module.interprocess_lock(path): pass
    else: raise AssertionError(op)
except ValueError:
    print(json.dumps({"rejected": True}))
else:
    print(json.dumps({"rejected": False}))
''', encoding="utf-8")
    try:
        return subprocess.run(
            [sys.executable, "-I", "-S", str(script), atomic_io.__file__, str(path), operation],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("state I/O blocked on a FIFO instead of rejecting its file type")


@pytest.mark.parametrize("operation", ["read-bytes", "read-text", "lock"])
def test_fifo_is_rejected_without_waiting_for_a_peer(tmp_path, operation):
    path = tmp_path / "state.pipe"
    fifo(path)
    before = path.lstat()
    result = isolated_call(tmp_path, path, operation)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"rejected": True}
    assert stat.S_ISFIFO(path.lstat().st_mode)
    assert os.path.samestat(before, path.lstat())


@pytest.mark.parametrize("operation", ["write-bytes", "write-text"])
@pytest.mark.parametrize("kind", ["fifo", "socket"])
def test_atomic_write_does_not_replace_ipc_endpoints(
    tmp_path, operation, kind, create_filesystem_socket,
):
    path = tmp_path / "state"
    if kind == "fifo":
        fifo(path)
    else:
        create_filesystem_socket(path)
    before = path.lstat()
    with pytest.raises(ValueError, match="regular"):
        operate(path, operation)
    assert os.path.samestat(before, path.lstat())
    assert path.lstat().st_mode == before.st_mode
    assert not list(tmp_path.glob("state.*.tmp"))


@pytest.mark.parametrize("operation", _OPERATIONS)
def test_directory_is_not_a_state_file(tmp_path, operation):
    path = tmp_path / "state"
    path.mkdir()
    retained = path / "keep"
    retained.write_bytes(b"untouched")
    with pytest.raises(ValueError, match="regular"):
        operate(path, operation)
    assert retained.read_bytes() == b"untouched"
    assert not list(tmp_path.glob("state.*.tmp"))


@pytest.mark.parametrize("operation", _OPERATIONS)
def test_linked_final_path_remains_rejected(tmp_path, operation):
    victim = tmp_path / "victim"
    victim.write_bytes(b"untouched")
    alias = tmp_path / "state"
    try:
        alias.symlink_to(victim)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ValueError):
        operate(alias, operation)
    assert victim.read_bytes() == b"untouched"


def test_shared_lock_inode_cannot_initialize_an_external_file(tmp_path):
    victim = tmp_path / "empty-user-file"
    victim.touch()
    lock = tmp_path / "state.lock"
    try:
        os.link(victim, lock)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")
    before = victim.stat()
    with pytest.raises(ValueError, match="link"):
        with atomic_io.interprocess_lock(lock):
            pytest.fail("a multiply linked lock must not enter the protected operation")
    assert victim.read_bytes() == b""
    assert victim.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("operation", ["read-bytes", "lock"])
@pytest.mark.parametrize("replacement", ["regular", "fifo"])
def test_descriptor_is_checked_after_the_open_race(tmp_path, monkeypatch, operation, replacement):
    if replacement == "fifo" and not hasattr(os, "mkfifo"):
        pytest.skip("this host has no POSIX FIFO support")
    path = tmp_path / "state"
    path.write_bytes(b"original")
    original_open = atomic_io.os.open
    opened = []

    def replace_at_open(name, flags, *args, **kwargs):
        if Path(name) == path:
            path.rename(tmp_path / "original-kept")
            if replacement == "fifo":
                # A swapped FIFO must not block before fstat gets a chance to run.
                assert flags & os.O_NONBLOCK
                os.mkfifo(path)
            else:
                path.write_bytes(b"different inode")
            fd = original_open(name, flags, *args, **kwargs)
            opened.append(fd)
            return fd
        return original_open(name, flags, *args, **kwargs)

    monkeypatch.setattr(atomic_io.os, "open", replace_at_open)
    with pytest.raises(ValueError, match="regular|changed"):
        operate(path, operation)
    assert len(opened) == 1
    with pytest.raises(OSError):
        os.fstat(opened[0])
    assert (tmp_path / "original-kept").read_bytes() == b"original"


@pytest.mark.parametrize("operation", ["write-bytes", "write-text"])
def test_destination_type_is_rechecked_before_publication(tmp_path, monkeypatch, operation):
    path = tmp_path / "state"
    path.write_bytes(b"old")
    if not hasattr(os, "mkfifo"):
        pytest.skip("this host has no POSIX FIFO support")
    original_chmod = atomic_io.os.chmod
    swapped = []

    def replace_before_publication(name, mode, *args, **kwargs):
        result = original_chmod(name, mode, *args, **kwargs)
        if Path(name).suffix == ".tmp":
            path.unlink()
            os.mkfifo(path)
            swapped.append(path.lstat())
        return result

    monkeypatch.setattr(atomic_io.os, "chmod", replace_before_publication)
    with pytest.raises(ValueError, match="regular"):
        operate(path, operation)
    assert len(swapped) == 1 and os.path.samestat(swapped[0], path.lstat())
    assert stat.S_ISFIFO(path.lstat().st_mode)
    assert not list(tmp_path.glob("state.*.tmp"))


@pytest.mark.parametrize("operation", ["read-bytes", "lock"])
def test_descriptor_closes_when_fdopen_fails(tmp_path, monkeypatch, operation):
    path = tmp_path / "state"
    path.write_bytes(b"old")
    descriptors = []

    def fail(fd, *args, **kwargs):
        descriptors.append(fd)
        raise OSError("controlled fdopen failure")

    monkeypatch.setattr(atomic_io.os, "fdopen", fail)
    with pytest.raises(OSError, match="fdopen"):
        operate(path, operation)
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.fstat(descriptors[0])
    assert path.read_bytes() == b"old"


def test_regular_files_keep_bytes_encoding_and_missing_semantics(tmp_path):
    path = tmp_path / "nested" / "state"
    with pytest.raises(FileNotFoundError):
        atomic_io.read_local_state_bytes(path)
    assert not path.parent.exists()
    raw = b"first\r\n\x00\xfflast\n"
    atomic_io.atomic_write_bytes(path, raw)
    assert atomic_io.read_local_state_bytes(path) == raw
    atomic_io.atomic_write_text(path, "中文😀\n")
    assert atomic_io.read_local_state_text(path) == "中文😀\n"
    atomic_io.atomic_write_text(path, "café", encoding="utf-16")
    assert atomic_io.read_local_state_text(path, encoding="utf-16") == "café"


@pytest.mark.parametrize("operation", ["write-bytes", "write-text"])
def test_regular_file_replacement_still_detaches_backups(tmp_path, operation):
    path = tmp_path / "state"
    path.write_bytes(b"old")
    backup = tmp_path / "backup"
    try:
        os.link(path, backup)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")
    before = backup.stat()
    operate(path, operation)
    assert not os.path.samefile(path, backup)
    assert backup.read_bytes() == b"old"
    assert backup.stat().st_mtime_ns == before.st_mtime_ns
    assert stat.S_IMODE(path.stat().st_mode) == stat.S_IMODE(before.st_mode)


def test_lock_keeps_its_inode_and_releases_on_body_error(tmp_path):
    path = tmp_path / "nested/state.lock"
    with pytest.raises(RuntimeError, match="body"):
        with atomic_io.interprocess_lock(path):
            observed = path.stat()
            raise RuntimeError("controlled body failure")
    with atomic_io.interprocess_lock(path):
        assert os.path.samestat(observed, path.stat())
    assert path.read_bytes() == b"\0"


@pytest.mark.parametrize("metadata_kind", ["binding", "dispatch"])
def test_launcher_metadata_fifo_returns_unavailable(tmp_path, metadata_kind):
    from specify_cli import launcher

    root = tmp_path / "bindings"
    binding_id = "a" * 32
    metadata = (root / binding_id / "binding.json" if metadata_kind == "binding"
                else root / "dispatch.json")
    metadata.parent.mkdir(parents=True)
    fifo(metadata)
    script = tmp_path / "metadata.py"
    script.write_text('''import json, os, pathlib, sys, types
# Load real owners but not the heavyweight CLI initializer in this bounded child.
pkg = types.ModuleType("specify_cli")
pkg.__path__ = [sys.argv[1]]
sys.modules["specify_cli"] = pkg
from specify_cli import launcher
os.environ[launcher.SPECIFY_LOCAL_BINDING_ENV] = sys.argv[2]
value = (launcher._read_project_launcher_binding("a" * 32) if sys.argv[3] == "binding"
         else launcher._read_project_launcher_dispatch())
print(json.dumps({"unavailable": value is None}))
''', encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(script), str(Path(launcher.__file__).parent),
             str(root), metadata_kind],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("launcher metadata lookup blocked on a FIFO")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"unavailable": True}
    assert stat.S_ISFIFO(metadata.lstat().st_mode)


@pytest.mark.skipif(os.name == "nt", reason="real POSIX flock wait/inode replacement fixture")
def test_waiter_does_not_enter_after_lock_path_is_replaced(tmp_path):
    import fcntl
    import time

    lock = tmp_path / "state.lock"
    lock.write_bytes(b"\0")
    ready = tmp_path / "waiting"
    script = tmp_path / "waiter.py"
    script.write_text('''import fcntl, importlib.util, json, pathlib, sys
spec = importlib.util.spec_from_file_location("state_io", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
lock, ready = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
original = fcntl.flock
def observed(fd, operation):
    if operation & fcntl.LOCK_EX: ready.touch()
    return original(fd, operation)
fcntl.flock = observed
try:
    with module.interprocess_lock(lock):
        print(json.dumps({"entered": True}))
except ValueError:
    print(json.dumps({"entered": False}))
''', encoding="utf-8")
    with lock.open("r+b") as holder:
        fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
        child = subprocess.Popen(
            [sys.executable, "-I", "-S", str(script), atomic_io.__file__, str(lock), str(ready)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            deadline = time.monotonic() + 5
            while not ready.exists():
                assert child.poll() is None, "waiter terminated before reaching flock"
                assert time.monotonic() < deadline, "waiter did not reach flock"
                time.sleep(0.01)
            # The child has opened the old inode; retain it for comparison.
            old = tmp_path / "old-lock"
            lock.rename(old)
            lock.write_bytes(b"replacement lock")
            fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
            stdout, stderr = child.communicate(timeout=5)
            assert child.returncode == 0, stderr
            assert json.loads(stdout) == {"entered": False}
            assert lock.read_bytes() == b"replacement lock"
            assert old.read_bytes() == b"\0"
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)


def test_lock_link_created_during_open_is_rejected_before_initialization(tmp_path, monkeypatch):
    path = tmp_path / "state.lock"
    path.touch()
    other = tmp_path / "external"
    original_open = os.open

    def add_link(name, flags, *args, **kwargs):
        fd = original_open(name, flags, *args, **kwargs)
        if Path(name) == path:
            try:
                os.link(path, other)
            except (OSError, NotImplementedError) as exc:
                os.close(fd)
                pytest.skip(f"hardlinks unavailable: {exc}")
        return fd

    monkeypatch.setattr(atomic_io.os, "open", add_link)
    with pytest.raises(ValueError, match="link"):
        with atomic_io.interprocess_lock(path):
            pytest.fail("a shared lock descriptor cannot be initialized")
    assert other.read_bytes() == path.read_bytes() == b""


@pytest.mark.parametrize("operation", ["read-bytes", "lock"])
def test_descriptor_closes_when_fstat_fails(tmp_path, monkeypatch, operation):
    path = tmp_path / "state"
    path.write_bytes(b"old")
    original_fstat = os.fstat
    descriptors = []

    def fail(fd):
        descriptors.append(fd)
        raise OSError("controlled fstat failure")

    monkeypatch.setattr(atomic_io.os, "fstat", fail)
    with pytest.raises(OSError, match="fstat"):
        operate(path, operation)
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        original_fstat(descriptors[0])
    assert path.read_bytes() == b"old"


@pytest.mark.parametrize("operation", ["write-bytes", "write-text"])
def test_flush_failure_keeps_regular_destination(tmp_path, monkeypatch, operation):
    path = tmp_path / "state"
    path.write_bytes(b"working old state")

    def fail(fd):
        raise OSError("controlled flush failure")

    monkeypatch.setattr(atomic_io.os, "fsync", fail)
    with pytest.raises(OSError, match="flush"):
        operate(path, operation)
    assert path.read_bytes() == b"working old state"
    assert not list(tmp_path.glob("state.*.tmp"))
