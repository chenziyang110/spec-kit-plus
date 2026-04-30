"""Multi-agent adapter for Claude integration."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    build_capability_snapshot,
    supports_workflow_command,
)

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS


class ClaudeMultiAgentAdapter:
    """First-release Claude adapter skeleton for capability and command checks."""

    integration_key = "claude"

    def detect_capabilities(self):
        return build_capability_snapshot(
            integration_key=self.integration_key,
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
            model_family="claude",
            notes=[
                "Native delegation depends on the current Claude tool surface and model support; fall back cleanly when the runtime does not expose subagents.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
