"""Tests for CodexIntegration."""

from .test_integration_base_skills import SkillsIntegrationTests


class TestCodexIntegration(SkillsIntegrationTests):
    KEY = "codex"
    FOLDER = ".agents/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".agents/skills"
    CONTEXT_FILE = "AGENTS.md"
    _SKILL_COMMANDS = SkillsIntegrationTests._SKILL_COMMANDS + ["team"]

    def _expected_files(self, script_variant: str) -> list[str]:
        files = super()._expected_files(script_variant)
        files.extend(
            [
                ".specify/codex-team/README.md",
                ".specify/codex-team/runtime.json",
            ]
        )
        return sorted(files)


class TestCodexAutoPromote:
    """--ai codex auto-promotes to integration path."""

    def test_ai_codex_without_ai_skills_auto_promotes(self, tmp_path):
        """--ai codex should work the same as --integration codex."""
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "test-proj"
        result = runner.invoke(app, ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"])

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"
        assert (target / ".agents" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (target / ".agents" / "skills" / "sp-team" / "SKILL.md").exists()
        assert (target / ".specify" / "codex-team" / "runtime.json").exists()


def test_codex_team_template_comes_from_shared_commands_dir(monkeypatch, tmp_path):
    """Codex must discover team.md from the packaged shared commands directory."""
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.base import IntegrationBase

    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "plan.md").write_text("---\ndescription: plan\n---\nbody\n", encoding="utf-8")
    (commands_dir / "team.md").write_text("---\ndescription: team\n---\nbody\n", encoding="utf-8")

    monkeypatch.setattr(IntegrationBase, "shared_commands_dir", lambda self: commands_dir)

    templates = CodexIntegration().list_command_templates()

    assert templates == [commands_dir / "plan.md", commands_dir / "team.md"]


def test_codex_generated_sp_implement_includes_auto_parallel_team_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-auto-parallel"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".agents" / "skills" / "sp-implement" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "native subagents" in content.lower()
    assert "specify team" in content
    assert "execution strategy" in content.lower()
