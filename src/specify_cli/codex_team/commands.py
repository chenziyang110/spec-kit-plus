"""User-facing Codex team command helpers."""

from __future__ import annotations

from pathlib import Path

TEAM_COMMAND_NAME = "specify team"
TEAM_SKILL_NAME = "sp-team"

__all__ = [
    "TEAM_COMMAND_NAME",
    "TEAM_SKILL_NAME",
    "runtime_state_summary",
    "team_availability_message",
    "team_help_text",
]


def team_help_text() -> str:
    """Return the official product surface for the Codex team runtime."""
    return (
        f"Use `{TEAM_COMMAND_NAME}` for the Codex-only team/runtime surface. "
        "`omx` and `$team` are not the official product surface. "
        "Existing Codex project upgrades remain optional support, not a first-release requirement."
    )


def team_availability_message(integration_key: str | None) -> str:
    """Describe whether the team surface is available for the integration."""
    if integration_key == "codex":
        return (
            "Codex team runtime is available. "
            f"Use `{TEAM_COMMAND_NAME}` inside a supported tmux-compatible environment."
        )
    return (
        "Codex team runtime is only available for Codex integration projects."
    )


def runtime_state_summary(project_root: Path) -> str:
    """Return a short summary of where Codex team runtime state is stored."""
    from .state_paths import codex_team_state_root

    state_root = codex_team_state_root(project_root)
    return (
        f"Codex team runtime state is stored in {state_root}. "
        "This state includes worker outcomes, join points, retry-pending work, and blockers."
    )
