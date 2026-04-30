"""Multi-agent adapter for Codex integration."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    build_capability_snapshot,
    supports_workflow_command,
)

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS | frozenset({"team"})


class CodexMultiAgentAdapter:
    """First-release Codex adapter skeleton for capability and command checks."""

    integration_key = "codex"

    def detect_capabilities(self):
        return build_capability_snapshot(
            integration_key=self.integration_key,
            native_subagents=True,
            managed_team_supported=True,
            structured_results=False,
            durable_coordination=True,
            native_worker_surface="spawn_agent",
            delegation_confidence="high",
            model_family="codex",
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
