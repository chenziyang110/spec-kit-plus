"""Multi-agent adapter for Gemini integration."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    build_capability_snapshot,
    supports_workflow_command,
)

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS


class GeminiMultiAgentAdapter:
    """First-release Gemini adapter skeleton for capability and command checks."""

    integration_key = "gemini"

    def detect_capabilities(self):
        return build_capability_snapshot(
            integration_key=self.integration_key,
            native_subagents=True,
            managed_team_supported=False,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
            model_family="gemini",
            notes=[
                "Gemini CLI supports native subagent dispatch through @generalist or a named @agent when the active runtime exposes that surface.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
