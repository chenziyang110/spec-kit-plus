"""Tests for ZcodeIntegration."""


def test_zcode_skills_init_installs_command_and_passive_skills(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "zcode-skills-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "zcode", "--no-git", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai zcode failed: {result.output}"
    assert "Spec Kit Plus skills were" in result.output
    assert ".zcode/skills" in result.output
    assert "Start using skills with your AI agent" in result.output
    assert "$sp-plan" in result.output
    assert "/sp.specify" not in result.output
    assert "Support and gate skills" in result.output
    assert "Support and gate commands" not in result.output
    assert (target / ".zcode" / "skills" / "sp-plan" / "SKILL.md").exists()
    assert (target / ".zcode" / "skills" / "dispatching-parallel-agents" / "SKILL.md").exists()
    assert not (target / ".agents" / "skills" / "sp-plan" / "SKILL.md").exists()
