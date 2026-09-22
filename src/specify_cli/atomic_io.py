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
import uuid
from typing import BinaryIO, Callable, TypeVar


_StagingResult = TypeVar("_StagingResult")


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
def interprocess_lock(path: Path, *, timeout: float = 120.0) -> Iterator[None]:
    """Hold an OS-released exclusive lock with a bounded acquisition wait.

    ``timeout`` is a finite, nonnegative number of seconds; zero attempts once.
    The default matches the existing Windows wait budget on every platform.
    This bounds contention polling, not filesystem open/fsync or the protected
    operation. A timeout closes the waiting descriptor, never removes the lock
    file, terminates its owner, or enters the protected operation without a lock.
    """

    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("lock timeout must be a finite nonnegative number")
    try:
        timeout = float(timeout)
    except OverflowError as exc:
        raise ValueError("lock timeout must be a finite nonnegative number") from exc
    if not 0.0 <= timeout < float("inf"):
        raise ValueError("lock timeout must be a finite nonnegative number")

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

            retryable = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}
        else:
            import fcntl

            retryable = {errno.EACCES, errno.EAGAIN, errno.EINTR}

        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in retryable:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"timed out waiting for local state lock: {lock_path}"
                    ) from exc
                time.sleep(min(0.025, remaining))
                # An overscheduled sleep must not authorize a late acquisition.
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"timed out waiting for local state lock: {lock_path}"
                    ) from exc
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


def _create_state_stage(
    target: Path, create: Callable[[str], _StagingResult],
) -> _StagingResult:
    """Create same-directory staging, shortening only an overlong temp name.

    A valid destination leaf can exceed the filesystem limit once a random
    suffix is appended. Keep ordinary staging names unchanged; retry exclusive
    creation once with a fixed short prefix only for ENAMETOOLONG. The factory
    must only allocate staging, never write content or publish the destination.
    Collisions, access errors and later failures are not retried by this helper.
    A long directory path can still fail: this does not enable long-path support.
    """

    try:
        return create(f"{target.name}.")
    except OSError as exc:
        if exc.errno != errno.ENAMETOOLONG:
            raise
    # The failed creation owns no file. Recheck before the bounded fallback;
    # never let a concurrent parent redirect turn it into an external write.
    _reject_link_components(target)
    _regular_state_stat(target, missing_ok=True)
    return create(".specify-")


def atomic_write_text(
    path: Path, content: str, *, encoding: str = "utf-8",
    new_file_mode: int | None = None,
) -> None:
    """Flush and atomically replace text, optionally respecting creation umask.

    Existing callers retain their original text-writing and permission behavior.
    The opt-in mode uses the byte publisher's exclusive, OS-masked staging path;
    existing destination modes are preserved. Never read or change process umask.
    """

    if new_file_mode is not None:
        atomic_write_bytes(path, content.encode(encoding), new_file_mode=new_file_mode)
        return

    target = _absolute_path_without_link_resolution(path)
    _reject_link_components(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_link_components(target)
    metadata = _regular_state_stat(target, missing_ok=True)
    target_mode = stat.S_IMODE(metadata.st_mode) if metadata is not None else 0o644
    temp_path: Path | None = None
    try:
        with _create_state_stage(
            target,
            lambda prefix: tempfile.NamedTemporaryFile(
                mode="w", encoding=encoding, newline="\n", dir=target.parent,
                prefix=prefix, suffix=".tmp", delete=False,
            ),
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
    except BaseException as error:
        # Cleanup is best-effort after a failed publication. In particular, a
        # watcher/permission error must not turn ENOSPC or cancellation into a
        # retryable write failure. Keep the original exception and its traceback.
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                error.add_note(
                    f"Temporary state file cleanup failed: {temp_path}: {cleanup_error}"
                )
        raise


def atomic_write_bytes(
    path: Path, content: bytes, *, new_file_mode: int | None = None,
) -> None:
    """Flush and replace bytes without newline conversion.

    Existing modes and the default 0644 creation policy are unchanged. Supplying
    new_file_mode requests OS/umask-filtered creation permissions only for a new
    destination, without reading or changing the process-global umask.
    """

    if new_file_mode is not None and (
        type(new_file_mode) is not int or not 0 <= new_file_mode <= 0o777
    ):
        raise ValueError("new_file_mode must contain only permission bits")

    target = _absolute_path_without_link_resolution(path)
    _reject_link_components(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_link_components(target)
    metadata = _regular_state_stat(target, missing_ok=True)
    target_mode = stat.S_IMODE(metadata.st_mode) if metadata is not None else (
        0o644 if new_file_mode is None else None
    )
    temp_path: Path | None = None
    try:
        if target_mode is None:
            # Exclusive creation applies umask on the staging inode. A collision
            # fails without deleting that other file; never truncate a candidate.
            def create_exclusive(prefix: str) -> tuple[int, Path]:
                candidate = target.with_name(f"{prefix}{uuid.uuid4().hex}.tmp")
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
                return os.open(candidate, flags, new_file_mode), candidate

            fd, temp_path = _create_state_stage(target, create_exclusive)
            try:
                handle = os.fdopen(fd, "wb")
            except BaseException:
                os.close(fd)
                raise
        else:
            handle = _create_state_stage(
                target,
                lambda prefix: tempfile.NamedTemporaryFile(
                    mode="wb", dir=target.parent, prefix=prefix,
                    suffix=".tmp", delete=False,
                ),
            )
            temp_path = Path(handle.name)
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if target_mode is not None:
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
    except BaseException as error:
        # Cleanup is best-effort after a failed publication. In particular, a
        # watcher/permission error must not turn ENOSPC or cancellation into a
        # retryable write failure. Keep the original exception and its traceback.
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                error.add_note(
                    f"Temporary state file cleanup failed: {temp_path}: {cleanup_error}"
                )
        raise


__all__ = [
    "atomic_write_bytes",
    "atomic_write_text",
    "interprocess_lock",
    "read_local_state_bytes",
    "read_local_state_text",
    "safe_local_state_path",
]
