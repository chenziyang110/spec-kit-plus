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
                "Grok Build native delegation is the three-tool surface: "
                "`spawn_subagent` (dispatch; background defaults true), "
                "`get_command_or_subagent_output` (join via task_ids/timeout_ms), "
                "and `kill_command_or_subagent` (cancel unfinished work only).",
                "Built-in subagent_type map: explore=read-only repo sweep; "
                "plan=read-only planning/architecture; general-purpose=bounded "
                "implementation/fix/validation. Prefer capability_mode "
                "read-only for evidence and worktree isolation only when "
                "independent source edits must not collide.",
                "Workers return structured evidence for the Leader; stage-owned "
                "artifacts stay on leased specify-runtime writes. The Rhai "
                "`workflow` orchestrator is optional multi-agent automation, "
                "not sp-teams and not the default sp-* lane path.",
            ],
        )

    def supports_command(self, command_name: str) -> bool:
        return supports_workflow_command(command_name, SUPPORTED_COMMANDS)
