"""Tests for GrokIntegration."""


def test_grok_skills_init_installs_command_and_passive_skills(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "grok-skills-runtime"

    result = runner.invoke(
        app,
        [
            "init",
            str(target),
            "--ai",
            "grok",
            "--no-git",
            "--ignore-agent-tools",
            "--script",
            "sh",
        ],
    )

    assert result.exit_code == 0, f"init --ai grok failed: {result.output}"
    plan_skill = target / ".grok" / "skills" / "sp-plan" / "SKILL.md"
    assert plan_skill.exists()
    assert (target / ".grok" / "skills" / "dispatching-parallel-agents" / "SKILL.md").exists()
    content = plan_skill.read_text(encoding="utf-8")
    assert "user-invocable: true" in content
    assert "/sp-plan" in content or "sp-plan" in content


def test_grok_invoke_placeholder_projects_slash_skill_surface():
    from specify_cli.integrations.base import IntegrationBase

    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "grok",
        "sh",
    )

    assert rendered.endswith("Run /sp-plan next.")
