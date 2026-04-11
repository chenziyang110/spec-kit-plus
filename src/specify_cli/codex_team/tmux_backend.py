"""Tmux-compatible worker backend planning helpers for the Codex team runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from specify_cli.codex_team import runtime_bridge

_BACKEND_INSTALL_INSTRUCTIONS: dict[str, str] = {
    "tmux": (
        "Install tmux with your package manager (Homebrew, apt, choco, etc.) "
        "or build from https://github.com/tmux/tmux."
    ),
    "psmux": "Install psmux with: winget install psmux",
}


class RuntimeEnvironmentError(RuntimeError):
    """Raised when the worker backend cannot be used in the current environment."""


@dataclass(slots=True, frozen=True)
class TeamRuntimeBackend:
    name: str | None
    binary: str | None
    available: bool
    description: str
    install_instructions: str | None


@dataclass(slots=True)
class WorkerPaneSpec:
    backend: str | None
    binary: str | None
    session: str
    worker_id: str
    pane_title: str
    launch_command: str
    worktree: str
    env: dict[str, str]


def detect_team_runtime_backend() -> TeamRuntimeBackend:
    backend_payload = runtime_bridge.detect_team_runtime_backend()
    name = backend_payload["name"]
    description = "tmux-compatible backend" if name else "tmux"
    install_instructions = _BACKEND_INSTALL_INSTRUCTIONS.get(name, _BACKEND_INSTALL_INSTRUCTIONS["tmux"])

    return TeamRuntimeBackend(
        name=name,
        binary=backend_payload["binary"],
        available=backend_payload["available"],
        description=description,
        install_instructions=install_instructions,
    )


def ensure_tmux_available() -> TeamRuntimeBackend:
    backend = detect_team_runtime_backend()
    if backend.available:
        return backend
    runtime_bridge.ensure_tmux_available()
    return backend


def plan_worker_launch(
    backend: TeamRuntimeBackend,
    *,
    session_id: str,
    worker_id: str,
    launch_command: str,
    worktree: Path | str,
    env: Mapping[str, str] | None = None,
) -> WorkerPaneSpec:
    if not backend.available:
        raise RuntimeEnvironmentError("No supported backend is available for worker launch.")

    session_name = f"codex-team-{session_id}"
    pane_title = f"worker-{worker_id}"
    resolved_worktree = str(Path(worktree))
    merged_env: dict[str, str] = {
        "WORKTREE_PATH": resolved_worktree,
        "WORKER_ID": worker_id,
        "SESSION_ID": session_id,
    }
    if env:
        merged_env.update(env)

    return WorkerPaneSpec(
        backend=backend.name,
        binary=backend.binary,
        session=session_name,
        worker_id=worker_id,
        pane_title=pane_title,
        launch_command=launch_command,
        worktree=resolved_worktree,
        env=merged_env,
    )


__all__ = [
    "RuntimeEnvironmentError",
    "TeamRuntimeBackend",
    "WorkerPaneSpec",
    "detect_team_runtime_backend",
    "ensure_tmux_available",
    "plan_worker_launch",
]
