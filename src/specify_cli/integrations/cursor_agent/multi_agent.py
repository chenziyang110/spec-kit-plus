"""Multi-agent adapter for the Cursor integration."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    build_capability_snapshot,
    supports_workflow_command,
)

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS


class CursorMultiAgentAdapter:
    """Describe Cursor's native ``Task`` subagent surface."""

    integration_key = "cursor-agent"

    def detect_capabilities(self):
        return build_capability_snapshot(
            integration_key=self.integration_key,
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="cursor-task",
            delegation_confidence="medium",
            model_family="cursor",
            notes=[
                "Cursor native delegation uses the session-visible Task schema; "
                "workers return terminal results directly or through background "
                "task completion.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
