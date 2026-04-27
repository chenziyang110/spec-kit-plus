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
        "Agent automation should prefer the optional `specify-teams-mcp` MCP facade when `specify-cli[mcp]` is installed and the facade is configured, "
        "using the CLI surface as parity fallback. "
        f"Launch the full-screen observer with `{TEAM_COMMAND_NAME} watch` when you need a live board over members and flow. "
        f"Submit structured worker results through `{TEAM_COMMAND_NAME} submit-result` or `{TEAM_COMMAND_NAME} api submit-result` when automation needs a stable result contract. "
        f"Generate canonical pending payloads with `{TEAM_COMMAND_NAME} result-template` and inspect the schema with `{TEAM_COMMAND_NAME} submit-result --print-schema`. "
        "The generated template is a placeholder only and must be replaced with a real success, blocked, or failed result before submission. "
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
