"""Multi-agent adapter for the Grok Build integration."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    build_capability_snapshot,
    supports_workflow_command,
)

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS | frozenset(
    {
        "discussion",
        "prd-scan",
        "prd-build",
        "quick",
        "accept",
        "auto",
        "design",
    }
)


class GrokMultiAgentAdapter:
    """Describe Grok Build's native ``spawn_subagent`` surface."""

    integration_key = "grok"

    def detect_capabilities(self):
        return build_capability_snapshot(
            integration_key=self.integration_key,
            native_subagents=True,
            managed_team_supported=False,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="spawn_subagent",
            delegation_confidence="high",
            model_family="grok",
            notes=[
                "Grok Build native delegation uses `spawn_subagent` with "
                "`get_command_or_subagent_output` join and "
                "`kill_command_or_subagent` cancel.",
                "Workers return structured evidence for the Leader; stage-owned "
                "artifacts stay on leased specify-runtime writes.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
