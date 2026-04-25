from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_wheel_force_include_bundles_passive_skills() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/passive-skills" = "specify_cli/core_pack/passive-skills"' in pyproject


def test_wheel_force_include_bundles_workflow_state_template() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"templates/workflow-state-template.md" = '
        '"specify_cli/core_pack/templates/workflow-state-template.md"'
    ) in pyproject


def test_wheel_force_include_bundles_agent_teams_extension_assets() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    expected_entries = [
        '"extensions/agent-teams/extension.yml" = "specify_cli/core_pack/extensions/agent-teams/extension.yml"',
        '"extensions/agent-teams/commands" = "specify_cli/core_pack/extensions/agent-teams/commands"',
        '"extensions/agent-teams/scripts" = "specify_cli/core_pack/extensions/agent-teams/scripts"',
        '"extensions/agent-teams/engine/package.json" = "specify_cli/core_pack/extensions/agent-teams/engine/package.json"',
        '"extensions/agent-teams/engine/src" = "specify_cli/core_pack/extensions/agent-teams/engine/src"',
        '"extensions/agent-teams/engine/crates" = "specify_cli/core_pack/extensions/agent-teams/engine/crates"',
        '"extensions/agent-teams/engine/prompts" = "specify_cli/core_pack/extensions/agent-teams/engine/prompts"',
        '"extensions/agent-teams/engine/skills" = "specify_cli/core_pack/extensions/agent-teams/engine/skills"',
    ]

    for entry in expected_entries:
        assert entry in pyproject
