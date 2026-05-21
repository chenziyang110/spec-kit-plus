"""Tests for VibeIntegration."""


def test_vibe_skills_init_installs_command_and_passive_skills(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "vibe-skills-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "vibe", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai vibe failed: {result.output}"
    assert (target / ".vibe" / "skills" / "sp-plan" / "SKILL.md").exists()
    assert (target / ".vibe" / "skills" / "dispatching-parallel-agents" / "SKILL.md").exists()
