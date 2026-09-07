"""Ordinary delegation must survive installation without activating a workflow."""

from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.mark.parametrize("integration_key", ["codex", "claude", "cursor-agent"])
def test_installed_passive_delegation_preserves_both_execution_contexts(
    tmp_path: Path, integration_key: str
) -> None:
    integration = get_integration(integration_key)
    assert integration is not None
    project = tmp_path / integration_key
    integration.setup(
        project,
        IntegrationManifest(integration_key, project),
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )

    for name in ("subagent-driven-development", "dispatching-parallel-agents"):
        skill = integration.skills_dest(project) / name / "SKILL.md"
        content = " ".join(skill.read_text(encoding="utf-8").lower().split())

        # Generic development and missing slicing must not demand a workflow.
        assert "do not require a workflow command merely to continue ordinary development" in content
        assert "if an executable task graph is missing" in content
        assert "in-session task list with dependencies, write scopes, acceptance, and verification" in content
        assert "no runtime receipt is required" in content
        assert "do not create or mutate canonical workflow artifacts for this ordinary path" in content
        assert "and stop" not in content
        assert "then stop" not in content

        # This must not become implicit entry or an escape from an active gate.
        assert "passive skill invocation must not enter any `sp-*` or `spx-*` workflow" in content
        assert "workflow files alone do not activate" in content
        assert "without requiring the user to repeat its command" in content
        assert "never relabel active workflow work as ordinary development to bypass a gate" in content
        assert "validated packets, result channels, and approval gates" in content
        assert "{{invoke:" not in content

        # Ordinary delegation still has real scope and verification obligations.
        assert "bounded assignment" in content
        assert "forbidden drift, acceptance, verification, and recovery/escalation conditions" in content
        assert "structured" in content and "result" in content
