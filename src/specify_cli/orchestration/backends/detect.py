"""Discovery helpers for orchestration runtime backends."""

from __future__ import annotations

import shutil

from .base import BackendDescriptor
from .process_backend import ProcessBackend


def _binary_descriptor(name: str) -> BackendDescriptor:
    binary = shutil.which(name)
    if binary:
        return BackendDescriptor(
            name=name,
            available=True,
            interactive=True,
            binary=binary,
            reason=f"{name} detected on PATH",
        )

    return BackendDescriptor(
        name=name,
        available=False,
        interactive=True,
        binary=None,
        reason=f"{name} not found on PATH",
    )


def detect_available_backends() -> dict[str, BackendDescriptor]:
    """Return descriptor entries for interactive and portable backends."""

    return {
        "tmux": _binary_descriptor("tmux"),
        "psmux": _binary_descriptor("psmux"),
        "process": ProcessBackend().describe(),
    }
