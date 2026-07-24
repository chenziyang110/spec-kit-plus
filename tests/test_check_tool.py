"""Tests for check_tool() — Claude Code CLI detection across install methods.

Covers issue https://github.com/github/spec-kit/issues/550:
  `specify check` reports "Claude Code CLI (not found)" even when claude is
  installed via npm-local (the default `claude` installer path).
"""

import os
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from specify_cli import app, check_tool, _command_path_candidates


class TestCheckToolClaude:
    """Claude CLI detection must work for all install methods."""

    def test_detected_via_migrate_installer_path(self, tmp_path):
        """claude migrate-installer puts binary at ~/.claude/local/claude."""
        fake_claude = tmp_path / "claude"
        fake_claude.touch()

        # Ensure npm-local path is missing so we only exercise migrate-installer path
        fake_missing = tmp_path / "nonexistent" / "claude"

        with patch("specify_cli.CLAUDE_LOCAL_PATH", fake_claude), \
             patch("specify_cli.CLAUDE_NPM_LOCAL_PATH", fake_missing), \
             patch("shutil.which", return_value=None):
            assert check_tool("claude") is True

    def test_detected_via_npm_local_path(self, tmp_path):
        """npm-local install puts binary at ~/.claude/local/node_modules/.bin/claude."""
        fake_npm_claude = tmp_path / "node_modules" / ".bin" / "claude"
        fake_npm_claude.parent.mkdir(parents=True)
        fake_npm_claude.touch()

        # Neither the migrate-installer path nor PATH has claude
        fake_migrate = tmp_path / "nonexistent" / "claude"

        with patch("specify_cli.CLAUDE_LOCAL_PATH", fake_migrate), \
             patch("specify_cli.CLAUDE_NPM_LOCAL_PATH", fake_npm_claude), \
             patch("shutil.which", return_value=None):
            assert check_tool("claude") is True

    def test_detected_via_path(self, tmp_path):
        """claude on PATH (global npm install) should still work."""
        fake_missing = tmp_path / "nonexistent" / "claude"

        with patch("specify_cli.CLAUDE_LOCAL_PATH", fake_missing), \
             patch("specify_cli.CLAUDE_NPM_LOCAL_PATH", fake_missing), \
             patch("shutil.which", return_value="/usr/local/bin/claude"):
            assert check_tool("claude") is True

    def test_not_found_when_nowhere(self, tmp_path):
        """Should return False when claude is genuinely not installed."""
        fake_missing = tmp_path / "nonexistent" / "claude"

        with patch("specify_cli.CLAUDE_LOCAL_PATH", fake_missing), \
             patch("specify_cli.CLAUDE_NPM_LOCAL_PATH", fake_missing), \
             patch("shutil.which", return_value=None):
            assert check_tool("claude") is False

    def test_tracker_updated_on_npm_local_detection(self, tmp_path):
        """StepTracker should be marked 'available' for npm-local installs."""
        fake_npm_claude = tmp_path / "node_modules" / ".bin" / "claude"
        fake_npm_claude.parent.mkdir(parents=True)
        fake_npm_claude.touch()

        fake_missing = tmp_path / "nonexistent" / "claude"
        tracker = MagicMock()

        with patch("specify_cli.CLAUDE_LOCAL_PATH", fake_missing), \
             patch("specify_cli.CLAUDE_NPM_LOCAL_PATH", fake_npm_claude), \
             patch("shutil.which", return_value=None):
            result = check_tool("claude", tracker=tracker)

        assert result is True
        tracker.complete.assert_called_once_with("claude", "available")


class TestCheckToolOther:
    """Non-Claude tools should be unaffected by the fix."""

    def test_git_detected_via_path(self):
        with patch("shutil.which", return_value="/usr/bin/git"):
            assert check_tool("git") is True

    def test_missing_tool(self):
        with patch("shutil.which", return_value=None):
            assert check_tool("nonexistent-tool") is False

    def test_kiro_fallback(self):
        """kiro-cli detection should try both kiro-cli and kiro."""
        def fake_which(name):
            return "/usr/bin/kiro" if name == "kiro" else None

        with patch("shutil.which", side_effect=fake_which):
            assert check_tool("kiro-cli") is True


class TestSpecifyPathDiagnostics:
    """Detect duplicate specify executables that can shadow newer installs."""

    def test_command_path_candidates_finds_duplicate_executables(self, tmp_path, monkeypatch):
        first = tmp_path / "conda" / "Scripts"
        second = tmp_path / "uv" / "bin"
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        executable_name = "specify.exe" if os.name == "nt" else "specify"
        (first / executable_name).write_text("", encoding="utf-8")
        (second / executable_name).write_text("", encoding="utf-8")

        monkeypatch.setenv("PATH", f"{first}{os.pathsep}{second}")
        monkeypatch.setenv("PATHEXT", ".EXE;.BAT;.CMD")

        candidates = _command_path_candidates("specify")

        assert candidates == [
            str((first / executable_name).resolve()),
            str((second / executable_name).resolve()),
        ]


class TestProjectCompatibilityCheck:
    def test_check_blocks_when_claude_personal_skill_shadows_project(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        project_skill = (
            project / ".claude" / "skills" / "sp-map-scan" / "SKILL.md"
        )
        project_skill.parent.mkdir(parents=True)
        project_skill.write_text("# Project map scan\n", encoding="utf-8")
        manifest = (
            project
            / ".specify"
            / "integrations"
            / "claude.manifest.json"
        )
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            """{
  "integration": "claude",
  "files": {
    ".claude/skills/sp-map-scan/SKILL.md": "test-digest"
  }
}
""",
            encoding="utf-8",
        )
        claude_config = tmp_path / "claude-config"
        personal_skill = (
            claude_config / "skills" / "sp-map-scan" / "SKILL.md"
        )
        personal_skill.parent.mkdir(parents=True)
        personal_skill.write_text("# Stale personal map scan\n", encoding="utf-8")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_config))
        monkeypatch.chdir(project)

        def available(tool, *, tracker=None):
            if tracker is not None:
                tracker.complete(tool, "available")
            return True

        with patch("specify_cli.check_tool", side_effect=available), patch(
            "specify_cli._command_path_candidates",
            return_value=[],
        ):
            result = CliRunner().invoke(app, ["check"], catch_exceptions=False)

        assert result.exit_code == 10, result.output
        assert "Claude personal skills shadow" in result.output
        assert "sp-map-scan" in result.output
        assert "project is not ready" in result.output.lower()
        assert "Specify CLI is ready to use!" not in result.output
