"""Multi-agent adapter for MiMo Code."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    build_capability_snapshot,
    supports_workflow_command,
)

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS


class MimoMultiAgentAdapter:
    """Capability adapter for MiMo Code's built-in subagent surface."""

    integration_key = "mimo"

    def detect_capabilities(self):
        return build_capability_snapshot(
            integration_key=self.integration_key,
            native_subagents=True,
            managed_team_supported=False,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
            model_family="mimo",
            notes=[
                "MiMo Code includes General and Explore subagents, and custom commands can target agents or force subtask execution.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
