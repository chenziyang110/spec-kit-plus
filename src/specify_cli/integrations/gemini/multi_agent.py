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
            native_multi_agent=False,
            sidecar_runtime_supported=False,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="none",
            delegation_confidence="low",
            model_family="gemini",
            notes=[
                "No native subagent surface is available in Gemini today; keep execution leader-led unless a future runtime probe proves otherwise.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
