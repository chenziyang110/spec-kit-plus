"""Tests for CodexIntegration."""

from .test_integration_base_skills import SkillsIntegrationTests


class TestCodexIntegration(SkillsIntegrationTests):
    KEY = "codex"
    FOLDER = ".agents/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".agents/skills"
    CONTEXT_FILE = "AGENTS.md"

    def _expected_files(self, script_variant: str) -> list[str]:
        files = super()._expected_files(script_variant)
        files.extend(
            [
                ".codex/config.toml",
                ".specify/config.json",
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


def test_codex_generated_sp_implement_includes_strategy_contract_and_team_surface(tmp_path):
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

    assert "specify team" in content
    assert "single-agent" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "invoking runtime acts as the leader" in content
    assert "single-agent still means one delegated worker lane" in content
    assert "selects the next executable phase and ready batch" in content
    assert "shared implement template is the primary source of truth" in content
    assert "join point" in content.lower()
    assert "retry-pending" in content.lower() or "retry pending" in content.lower()
    assert "blocker" in content.lower()
    assert "delegated execution" in content.lower() or "delegates execution" in content.lower()
    assert "prefer `sidecar-runtime`" in content
    assert "ask the user whether codex should continue via native subagents" in content.lower()


def test_codex_generated_shared_workflow_skills_stay_runtime_neutral(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-shared-routing"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".agents" / "skills"
    for skill_name in ("sp-specify", "sp-plan", "sp-tasks", "sp-explain"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "single-agent" in content
        assert "native-multi-agent" in content
        assert "sidecar-runtime" in content
        assert "specify team" not in content
