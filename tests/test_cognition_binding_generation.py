"""Binding gates must reach real installed mutation workflows in both profiles."""

from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_mutation_profiles_preserve_verification_binding(
    tmp_path: Path, integration_key: str, profile: str,
):
    integration = get_integration(integration_key)
    project = tmp_path / integration_key / profile
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project, manifest,
        parsed_options={"workflow_profile": profile}, script_type="ps",
    )
    skills = integration.skills_dest(project)
    prefix = "sp" if profile == "classic" else "spx"
    for command in ["fast", "debug", "implement", "quick", "review", "e2e", "do"]:
        owner = skills / f"{prefix}-{command}"
        assert (owner / "SKILL.md").is_file(), command
        effective = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(owner.rglob("*.md"))
        )
        assert "cognition.closeout.binding.v1" in effective, command
        assert "cognition closeout binding begin" in effective, command
        assert "before" in effective and "seal" in effective and "check" in effective
        assert "Legacy" in effective and "audit" in effective
        assert "{{specify-subcmd:" not in effective
        heading = (
            "### Inline Project Cognition Update"
            if profile == "classic"
            else "# Closeout after repository changes"
        )
        closeout = effective[effective.index(heading):]
        # The planner supplies begin inputs, so discovering them after verification
        # makes the installed procedure impossible to follow as written.
        assert closeout.index("cognition closeout-plan") < closeout.index(
            "cognition closeout binding begin"
        ), command
        instructions = " ".join(closeout.split())
        assert "For non-Do source changes, carry the current sealed binding" in (
            instructions
        ), command
        assert "Do calls the planner at knowledge closeout with its existing proof" in (
            instructions
        ), command
        assert "without repeating completed work" in instructions, command
        if command != "do":
            if profile == "advanced":
                local = " ".join(
                    (owner / "SKILL.md").read_text(encoding="utf-8").lower().split()
                )
                assert local.index("cognition closeout-plan") < local.index(
                    "begin the native work/source binding"
                    if command != "e2e"
                    else "begin the native current-work/source binding"
                ), command
            else:
                markers = {
                    "fast": "Before the final check of changed source",
                    "debug": "After the accepted repair edits and before final",
                    "implement": "After accepted source-changing joins and before",
                    "quick": "1. After accepted joins",
                    "review": "For source-changing Review repair joins",
                    "e2e": "After retained test-asset edits and accepted joins",
                }
                local = effective[effective.index(markers[command]):].split("\n\n", 1)[0]
                assert local.index("planner") < local.index("begin"), command
    if profile == "advanced":
        assert not (skills / "spec-kit-project-cognition-gate").exists()
