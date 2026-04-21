"""Shared backend contracts for orchestration runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence


Command = Sequence[str] | str
WorkingDirectory = Path | str | None
Environment = Mapping[str, str] | None


@dataclass(slots=True, frozen=True)
class BackendDescriptor:
    """Runtime capability metadata for a backend."""

    name: str
    available: bool
    interactive: bool
    binary: str | None = None
    reason: str = ""


class RuntimeBackend(Protocol):
    """Protocol implemented by all runtime backend adapters."""

    def describe(self) -> BackendDescriptor:
        """Return availability and capability details for this backend."""

    def launch(self, command: Command, cwd: WorkingDirectory = None, env: Environment = None) -> object:
        """Launch a command and return backend-specific runtime metadata."""
