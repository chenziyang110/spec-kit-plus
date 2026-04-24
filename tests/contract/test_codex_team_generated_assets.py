"""Contract tests for Codex team generated assets."""

import os

from typer.testing import CliRunner

from specify_cli import app


def test_codex_init_generates_team_assets(tmp_path):
    project = tmp_path / "fresh-codex-team"
    project.mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = CliRunner().invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "codex",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    assert (project / ".codex" / "skills" / "sp-team" / "SKILL.md").exists()
    assert (project / ".codex" / "skills" / "sp-implement-teams" / "SKILL.md").exists()
    assert (project / ".specify" / "codex-team" / "runtime.json").exists()
    assert (project / ".specify" / "codex-team" / "README.md").exists()


def test_non_codex_init_does_not_generate_codex_team_assets(tmp_path):
    project = tmp_path / "fresh-claude-no-codex-team"
    project.mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = CliRunner().invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "claude",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    assert not (project / ".claude" / "skills" / "sp-team" / "SKILL.md").exists()
    assert (project / ".claude" / "skills" / "sp-implement-teams" / "SKILL.md").exists()
    assert not (project / ".specify" / "codex-team" / "runtime.json").exists()
