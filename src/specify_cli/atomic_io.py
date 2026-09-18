"""Small cross-platform primitives for durable local state files."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat
import tempfile
import time
from typing import BinaryIO


def _absolute_path_without_link_resolution(path: Path) -> Path:
    """Return an absolute lexical path without following filesystem links."""

    return Path(os.path.abspath(os.fspath(path)))


def _reject_link_components(path: Path) -> None:
    """Reject existing symlink or junction components before local state I/O."""

    parts = path.parts
    if not parts:
        return
    current = Path(parts[0])
    for part in parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        is_junction = getattr(current, "is_junction", None)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        is_reparse_point = bool(
            getattr(metadata, "st_file_attributes", 0) & reparse_flag
        )
        if (
            stat.S_ISLNK(metadata.st_mode)
            or (callable(is_junction) and bool(is_junction()))
            or is_reparse_point
        ):
            raise ValueError(f"refusing local state I/O through symlink: {current}")


def safe_local_state_path(path: Path, *, root: Path | None = None) -> Path:
    """Return a contained absolute path after rejecting links and junctions."""

    target = _absolute_path_without_link_resolution(path)
    if root is not None:
        boundary = _absolute_path_without_link_resolution(root)
        try:
            target.relative_to(boundary)
        except ValueError as exc:
            raise ValueError(
                f"refusing local state I/O outside root: {target}"
            ) from exc
    _reject_link_components(target)
    return target


def _regular_state_stat(
    path: Path, *, missing_ok: bool = False, for_lock: bool = False,
) -> os.stat_result | None:
    """Inspect a file, not an IPC endpoint or device, without following links."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        raise
    _check_regular_state_stat(path, metadata, for_lock=for_lock)
    return metadata


def _check_regular_state_stat(
    path: Path, metadata: os.stat_result, *, for_lock: bool = False,
) -> None:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & reparse_flag
    ):
        raise ValueError(f"local state requires a regular non-link file: {path}")
    if for_lock and metadata.st_nlink != 1:
        # Initializing a shared empty inode would modify somebody else's file.
        raise ValueError(f"local state lock must not have multiple hardlinks: {path}")


@contextmanager
def _open_regular_state_file(
    path: Path, *, for_lock: bool = False,
) -> Iterator[BinaryIO]:
    """Check both pathname and opened descriptor before reading or initializing.

    Nonblocking open prevents a swapped POSIX FIFO from waiting for a peer.
    NOFOLLOW protects the final component where available. These observations
    do not make ancestor changes or later file mutations into a transaction.
    """

    before = _regular_state_stat(path, missing_ok=for_lock, for_lock=for_lock)
    flags = (os.O_RDWR | os.O_CREAT | os.O_APPEND) if for_lock else os.O_RDONLY
    for name in ("O_BINARY", "O_NONBLOCK", "O_NOFOLLOW", "O_NOCTTY"):
        flags |= getattr(os, name, 0)
    fd = os.open(path, flags, 0o666)
    try:
        opened = os.fstat(fd)
        _check_regular_state_stat(path, opened, for_lock=for_lock)
        _reject_link_components(path)
        current = _regular_state_stat(path, for_lock=for_lock)
        if (
            (before is not None and not os.path.samestat(before, opened))
            or not os.path.samestat(opened, current)
        ):
            raise ValueError(f"local state file changed while opening: {path}")
        # Keep raw-descriptor ownership even when wrapping or validation fails.
        with os.fdopen(fd, "a+b" if for_lock else "rb", closefd=False) as handle:
            yield handle
    finally:
        os.close(fd)


def read_local_state_bytes(path: Path, *, root: Path | None = None) -> bytes:
    """Read a regular local state file through a lexical, non-link path."""

    target = safe_local_state_path(path, root=root)
    with _open_regular_state_file(target) as handle:
        return handle.read()


def read_local_state_text(
    path: Path,
    *,
    root: Path | None = None,
    encoding: str = "utf-8",
) -> str:
    """Read text local state only through a lexical, non-link path."""

    return read_local_state_bytes(path, root=root).decode(encoding)


@contextmanager
def interprocess_lock(path: Path) -> Iterator[None]:
    """Hold an OS-released exclusive lock for one local state transaction."""

    lock_path = _absolute_path_without_link_resolution(path)
    _reject_link_components(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _reject_link_components(lock_path)
    with _open_regular_state_file(lock_path, for_lock=True) as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            deadline = time.monotonic() + 120.0
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in {
                        errno.EACCES,
                        errno.EAGAIN,
                        errno.EDEADLK,
                    }:
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            f"timed out waiting for local state lock: {lock_path}"
                        ) from exc
                    time.sleep(0.025)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            # A waiter may have acquired an old inode after the lock path was
            # replaced. Do not enter the transaction under that obsolete lock.
            _reject_link_components(lock_path)
            current = _regular_state_stat(lock_path, for_lock=True)
            if not os.path.samestat(os.fstat(handle.fileno()), current):
                raise ValueError(f"local state lock changed while waiting: {lock_path}")
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Flush and atomically replace a text file in its destination directory."""

    target = _absolute_path_without_link_resolution(path)
    _reject_link_components(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_link_components(target)
    metadata = _regular_state_stat(target, missing_ok=True)
    target_mode = stat.S_IMODE(metadata.st_mode) if metadata is not None else 0o644
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline="\n",
            dir=target.parent,
            prefix=f"{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, target_mode)
        _reject_link_components(target)
        _regular_state_stat(target, missing_ok=True)
        os.replace(temp_path, target)
        temp_path = None
        if os.name != "nt":
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Flush and atomically replace a binary file without newline conversion."""

    target = _absolute_path_without_link_resolution(path)
    _reject_link_components(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_link_components(target)
    metadata = _regular_state_stat(target, missing_ok=True)
    target_mode = stat.S_IMODE(metadata.st_mode) if metadata is not None else 0o644
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f"{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, target_mode)
        _reject_link_components(target)
        _regular_state_stat(target, missing_ok=True)
        os.replace(temp_path, target)
        temp_path = None
        if os.name != "nt":
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


__all__ = [
    "atomic_write_bytes",
    "atomic_write_text",
    "interprocess_lock",
    "read_local_state_bytes",
    "read_local_state_text",
    "safe_local_state_path",
]
