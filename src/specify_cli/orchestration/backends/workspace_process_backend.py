"""Direct subprocess launches in an explicitly selected project directory."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from .base import BackendDescriptor
from .environment import build_child_environment


class WorkspaceBindingError(ValueError):
    """Raised when the caller has not selected a usable project directory."""


@dataclass(slots=True, frozen=True)
class WorkspaceProcessHandle:
    """A direct child handle; process exit never implies workflow acceptance."""

    pid: int
    command: tuple[str, ...]
    cwd: Path
    _process: subprocess.Popen = field(repr=False, compare=False)

    def poll(self) -> int | None:
        return self._process.poll()

    def wait(self, timeout: float | None = None) -> int:
        return self._process.wait(timeout=timeout)

    def cancel(self) -> int:
        """Stop and reap this child, escalating if it does not exit promptly."""

        if self._process.poll() is None:
            self._process.terminate()
        try:
            return self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
            return self._process.wait(timeout=5)


class WorkspaceProcessBackend:
    """Launch directly after the caller's packet and execution/Board guards.

    The caller owns scope confirmation, leases, checkpoints, cancellation
    coordination, result acceptance and external-action authorization. This
    backend neither claims work nor turns a child exit into acceptance.
    It never discovers a parent Git root or manages repository state.
    """

    def describe(self) -> BackendDescriptor:
        return BackendDescriptor(
            name="workspace-process",
            available=True,
            interactive=False,
            binary=None,
            reason="direct project-scoped subprocess backend",
        )

    def launch(
        self,
        command: Sequence[str],
        *,
        project_root: Path,
        env: Mapping[str, str] | None = None,
    ) -> WorkspaceProcessHandle:
        argv = _validate_argv(command)
        root = _validate_project_root(project_root)
        process = subprocess.Popen(
            argv,
            cwd=root,
            env=build_child_environment(env),
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return WorkspaceProcessHandle(
            pid=process.pid,
            command=tuple(argv),
            cwd=root,
            _process=process,
        )


def _validate_argv(command: Sequence[str]) -> list[str]:
    if isinstance(command, (str, bytes)):
        raise TypeError("workspace process launch requires tokenized argv")
    argv = list(command)
    if not argv:
        raise TypeError("workspace process launch requires nonempty tokenized argv")
    if any(not isinstance(token, str) or token == "" or "\x00" in token for token in argv):
        raise TypeError("workspace process launch requires tokenized argv strings")
    return argv


def _validate_project_root(project_root: Path) -> Path:
    path = Path(project_root)
    if not path.is_absolute():
        raise WorkspaceBindingError(f"project_root must be absolute: {path}")
    if not path.is_dir():
        raise WorkspaceBindingError(f"project_root must exist and be a directory: {path}")
    return path.resolve(strict=True)
