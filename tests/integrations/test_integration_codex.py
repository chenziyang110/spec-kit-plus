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
