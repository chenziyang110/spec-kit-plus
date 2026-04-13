"""Portable subprocess-based backend for orchestration runtime launches."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .base import BackendDescriptor


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
        merged_env: dict[str, str] | None = None
        if env is not None:
            merged_env = os.environ.copy()
            merged_env.update(env)

        process = subprocess.Popen(command, cwd=cwd, env=merged_env)
        return ProcessHandle(pid=process.pid, command=command, cwd=cwd)
