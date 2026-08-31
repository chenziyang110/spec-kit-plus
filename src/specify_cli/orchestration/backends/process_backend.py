"""Portable subprocess-based backend for orchestration runtime launches."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .base import BackendDescriptor
from .environment import build_child_environment


@dataclass(slots=True, frozen=True)
class ProcessHandle:
    """Launch metadata returned by :class:`ProcessBackend`."""

    pid: int
    command: Sequence[str] | str
    cwd: Path | str | None


class ProcessBackend:
    """Runtime backend that launches independent local subprocesses."""

    def describe(self) -> BackendDescriptor:
        return BackendDescriptor(
            name="process",
            available=True,
            interactive=False,
            binary=None,
            reason="portable subprocess backend",
        )

    def launch(
        self,
        command: Sequence[str] | str,
        cwd: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessHandle:
        process = subprocess.Popen(command, cwd=cwd, env=build_child_environment(env))
        return ProcessHandle(pid=process.pid, command=command, cwd=cwd)
