"""Multi-agent adapter for Copilot integration."""

from __future__ import annotations

from specify_cli.orchestration.adapters import (
    FIRST_RELEASE_WORKFLOW_COMMANDS,
    supports_workflow_command,
)
from specify_cli.orchestration.models import CapabilitySnapshot

SUPPORTED_COMMANDS = FIRST_RELEASE_WORKFLOW_COMMANDS


class CopilotMultiAgentAdapter:
    """First-release Copilot adapter skeleton for capability and command checks."""

    integration_key = "copilot"

    def detect_capabilities(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key=self.integration_key,
            native_multi_agent=False,
            sidecar_runtime_supported=True,
            structured_results=False,
            durable_coordination=False,
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
