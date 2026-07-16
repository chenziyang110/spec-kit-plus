"""Small cross-platform primitives for durable local state files."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import tempfile


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


@contextmanager
def interprocess_lock(path: Path) -> Iterator[None]:
    """Hold an OS-released exclusive lock for one local state transaction."""

    lock_path = _absolute_path_without_link_resolution(path)
    _reject_link_components(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _reject_link_components(lock_path)
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
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
    try:
        target_mode = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        target_mode = 0o644
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


__all__ = ["atomic_write_text", "interprocess_lock"]
