"""Tests for GeminiIntegration."""

from typer.testing import CliRunner

from specify_cli import app

from .test_integration_base_toml import TomlIntegrationTests


class TestGeminiIntegration(TomlIntegrationTests):
    KEY = "gemini"
    FOLDER = ".gemini/"
    COMMANDS_SUBDIR = "commands"
    REGISTRAR_DIR = ".gemini/commands"
    CONTEXT_FILE = "GEMINI.md"


def test_gemini_runtime_commands_hard_gate_project_map_reads(tmp_path):
    runner = CliRunner()
    target = tmp_path / "gemini-project-map-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "gemini", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai gemini failed: {result.output}"

    for rel in (
        ".gemini/commands/sp.implement.toml",
        ".gemini/commands/sp.debug.toml",
        ".gemini/commands/sp.quick.toml",
    ):
        content = (target / rel).read_text(encoding="utf-8").lower()
        assert "crucial first step" in content
        assert "project-handbook.md" in content
        assert ".specify/project-map/*.md" in content
        assert "/sp-map-codebase" in content
