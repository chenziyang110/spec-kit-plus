"""Tests for ``specify integration`` subcommand (list, install, uninstall, switch)."""

import json
import os

import pytest
from typer.testing import CliRunner

import specify_cli as cli_module
from specify_cli import app
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import (
    SPECIFY_RUNTIME_UNAVAILABLE_MARKER,
    SPECIFY_PROJECT_LAUNCHER_POSIX,
    SPECIFY_PROJECT_LAUNCHER_WINDOWS,
    SpecifyLauncherSpec,
    render_claude_hook_launcher,
    resolve_specify_launcher_spec,
)


runner = CliRunner()


def _init_project(tmp_path, integration="copilot"):
    """Helper: init a spec-kit project with the given integration."""
    project = tmp_path / "proj"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, [
            "init", "--here",
            "--integration", integration,
            "--script", "sh",
            "--no-git",
            "--ignore-agent-tools",
        ], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)
    assert result.exit_code == 0, f"init failed: {result.output}"
    return project


def _expected_claude_hook(route: str) -> dict[str, object]:
    return render_claude_hook_launcher(route)


# ── list ─────────────────────────────────────────────────────────────


class TestIntegrationList:
    def test_list_requires_speckit_project(self, tmp_path):
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["integration", "list"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Not a Spec Kit Plus project" in result.output
        assert "Run this command from a Spec Kit Plus project root" in result.output

    def test_list_shows_installed(self, tmp_path):
        project = _init_project(tmp_path, "copilot")
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "list"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "copilot" in result.output
        assert "installed" in result.output

    def test_list_shows_available_integrations(self, tmp_path):
        project = _init_project(tmp_path, "copilot")
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "list"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        # Should show multiple integrations
        assert "claude" in result.output
        assert "gemini" in result.output


# ── install ──────────────────────────────────────────────────────────


class TestIntegrationInstall:
    def test_install_requires_speckit_project(self, tmp_path):
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["integration", "install", "claude"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Not a Spec Kit Plus project" in result.output
        assert "Run this command from a Spec Kit Plus project root" in result.output

    def test_install_unknown_integration(self, tmp_path):
        project = _init_project(tmp_path)
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "install", "nonexistent"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Unknown integration" in result.output

    def test_install_already_installed(self, tmp_path):
        project = _init_project(tmp_path, "copilot")
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "install", "copilot"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "already installed" in result.output
        assert "uninstall" in result.output

    def test_install_different_when_one_exists(self, tmp_path):
        project = _init_project(tmp_path, "copilot")
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "install", "claude"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "already installed" in result.output
        assert "uninstall" in result.output

    def test_install_into_bare_project(self, tmp_path):
        """Install into a project with .specify/ but no integration."""
        project = tmp_path / "bare"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "install", "claude",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, result.output
        assert "installed successfully" in result.output

        # integration.json written
        data = json.loads((project / ".specify" / "integration.json").read_text(encoding="utf-8"))
        assert data["integration"] == "claude"

        # Manifest created
        assert (project / ".specify" / "integrations" / "claude.manifest.json").exists()

        # Claude uses skills directory (not commands)
        assert (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (project / ".claude" / "skills" / "sp-prd" / "SKILL.md").exists()

    def test_install_codex_into_bare_project_creates_team_assets(self, tmp_path):
        """Installing codex into a bare project should create codex team assets only there."""
        project = tmp_path / "bare-codex"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "install", "codex",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, result.output
        assert (project / ".codex" / "skills" / "sp-teams" / "SKILL.md").exists()
        assert (project / ".specify" / "teams" / "runtime.json").exists()

    def test_install_bare_project_gets_shared_infra(self, tmp_path):
        """Installing into a bare project should create shared scripts and templates."""
        project = tmp_path / "bare"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "install", "claude",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, result.output

        # Shared infrastructure should be present
        assert (project / ".specify" / "scripts").is_dir()
        assert (project / ".specify" / "templates").is_dir()


# ── uninstall ────────────────────────────────────────────────────────


class TestIntegrationUninstall:
    def test_uninstall_requires_speckit_project(self, tmp_path):
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["integration", "uninstall"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Not a Spec Kit Plus project" in result.output
        assert "Run this command from a Spec Kit Plus project root" in result.output

    def test_uninstall_no_integration(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "No integration" in result.output

    def test_uninstall_removes_files(self, tmp_path):
        project = _init_project(tmp_path, "claude")
        # Claude uses skills directory
        assert (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (project / ".specify" / "integrations" / "claude.manifest.json").exists()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall"], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "uninstalled" in result.output

        # Command files removed
        assert not (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()

        # Manifest removed
        assert not (project / ".specify" / "integrations" / "claude.manifest.json").exists()

        # integration.json removed
        assert not (project / ".specify" / "integration.json").exists()

    def test_uninstall_preserves_modified_files(self, tmp_path):
        """Full lifecycle: install → modify → uninstall → modified file kept."""
        project = _init_project(tmp_path, "claude")
        plan_file = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        assert plan_file.exists()

        # Modify a file
        plan_file.write_text("# My custom plan command\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall"], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "preserved" in result.output

        # Modified file kept
        assert plan_file.exists()
        assert plan_file.read_text(encoding="utf-8") == "# My custom plan command\n"

    def test_uninstall_wrong_key(self, tmp_path):
        project = _init_project(tmp_path, "copilot")
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall", "claude"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "not the currently installed" in result.output

    def test_uninstall_preserves_shared_infra(self, tmp_path):
        """Shared scripts and templates are not removed by integration uninstall."""
        project = _init_project(tmp_path, "claude")
        shared_script = project / ".specify" / "scripts" / "bash" / "common.sh"
        assert shared_script.exists()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall"], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0

        # Shared infrastructure preserved
        assert shared_script.exists()
        assert (project / ".specify" / "templates").is_dir()

    def test_uninstall_claude_removes_install_owned_settings_and_hook_assets(self, tmp_path):
        project = _init_project(tmp_path, "claude")
        settings_path = project / ".claude" / "settings.json"
        hook_script = project / ".claude" / "hooks" / "claude-hook-dispatch.py"

        assert settings_path.exists()
        assert hook_script.exists()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall"], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert not settings_path.exists()
        assert not hook_script.exists()

    def test_uninstall_claude_preserves_user_settings_and_strips_managed_hooks(self, tmp_path):
        project = _init_project(tmp_path, "claude")
        settings_path = project / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings["custom.setting"] = True
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall"], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert settings_path.exists()
        remaining = json.loads(settings_path.read_text(encoding="utf-8"))
        assert remaining["custom.setting"] is True
        remaining_commands = [
            hook["command"]
            for entries in remaining.get("hooks", {}).values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
        assert not any("claude-hook-dispatch.py" in command for command in remaining_commands)


# ── switch ───────────────────────────────────────────────────────────


class TestIntegrationSwitch:
    def test_switch_requires_speckit_project(self, tmp_path):
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["integration", "switch", "claude"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Not a Spec Kit Plus project" in result.output
        assert "Run this command from a Spec Kit Plus project root" in result.output

    def test_switch_unknown_target(self, tmp_path):
        project = _init_project(tmp_path)
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "switch", "nonexistent"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Unknown integration" in result.output

    def test_switch_same_noop(self, tmp_path):
        project = _init_project(tmp_path, "copilot")
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "switch", "copilot"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "already installed" in result.output

    def test_switch_between_integrations(self, tmp_path):
        project = _init_project(tmp_path, "claude")
        # Verify claude files exist (claude uses skills)
        assert (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "switch", "copilot",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, result.output
        assert "Switched to" in result.output

        # Old claude files removed
        assert not (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()

        # New copilot files created
        assert (project / ".github" / "agents" / "sp.plan.agent.md").exists()

        # integration.json updated
        data = json.loads((project / ".specify" / "integration.json").read_text(encoding="utf-8"))
        assert data["integration"] == "copilot"

    def test_switch_preserves_shared_infra(self, tmp_path):
        """Switching preserves shared scripts, templates, and memory."""
        project = _init_project(tmp_path, "claude")
        shared_script = project / ".specify" / "scripts" / "bash" / "common.sh"
        assert shared_script.exists()
        shared_content = shared_script.read_text(encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "switch", "copilot",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0

        # Shared infra untouched
        assert shared_script.exists()
        assert shared_script.read_text(encoding="utf-8") == shared_content

    def test_switch_from_claude_preserves_user_settings_while_removing_managed_hooks(self, tmp_path):
        project = _init_project(tmp_path, "claude")
        settings_path = project / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings["custom.setting"] = True
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "switch", "copilot", "--script", "sh"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert settings_path.exists()
        remaining = json.loads(settings_path.read_text(encoding="utf-8"))
        assert remaining["custom.setting"] is True
        remaining_commands = [
            hook["command"]
            for entries in remaining.get("hooks", {}).values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
        assert not any("claude-hook-dispatch.py" in command for command in remaining_commands)
        assert (project / ".github" / "agents" / "sp.plan.agent.md").exists()

    def test_switch_from_nothing(self, tmp_path):
        """Switch when no integration is installed should just install the target."""
        project = tmp_path / "bare"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "switch", "claude",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert "Switched to" in result.output

        data = json.loads((project / ".specify" / "integration.json").read_text(encoding="utf-8"))
        assert data["integration"] == "claude"


class TestIntegrationRepair:
    def test_repair_runtime_assets_preserves_modified_integration_script(
        self,
        tmp_path,
    ):
        project = tmp_path / "project"
        integration = get_integration("claude")
        assert integration is not None
        manifest = IntegrationManifest("claude", project)
        installed = integration.install_scripts(project, manifest)
        assert installed
        target = installed[0]
        original = "# USER INTEGRATION SCRIPT\n"
        target.write_text(original, encoding="utf-8")

        repaired = integration.repair_runtime_assets(
            project,
            manifest,
            script_type="ps",
        )

        relative = target.relative_to(project).as_posix()
        assert target not in repaired
        assert target.read_text(encoding="utf-8") == original
        assert relative in integration._last_repair_skipped_modified

    @pytest.mark.parametrize(
        ("integration", "hook_readme"),
        (
            ("claude", ".claude/hooks/README.md"),
            ("gemini", ".gemini/hooks/README.md"),
        ),
    )
    def test_repair_preserves_modified_hook_and_shared_launcher_assets(
        self,
        tmp_path,
        integration,
        hook_readme,
    ):
        project = _init_project(tmp_path, integration)
        readme = project / hook_readme
        shared_launcher = project / ".specify" / "bin" / "specify-hook.py"
        readme_sentinel = "# USER HOOK README SENTINEL\n"
        launcher_sentinel = "# USER SHARED LAUNCHER SENTINEL\n"
        readme.write_text(readme_sentinel, encoding="utf-8")
        shared_launcher.write_text(launcher_sentinel, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "sh"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 10, result.output
        assert "PARTIAL" in result.output
        assert hook_readme in result.output
        assert ".specify/bin/specify-hook.py" in result.output
        assert readme.read_text(encoding="utf-8") == readme_sentinel
        assert shared_launcher.read_text(encoding="utf-8") == launcher_sentinel

    @pytest.mark.parametrize(
        "runtime_call",
        (
            f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:specify-runtime cognition compass",
            "`specify-runtime cognition compass --intent plan --format json`",
        ),
    )
    def test_repair_reports_modified_cognition_runtime_call_as_partial_candidate(
        self,
        tmp_path,
        runtime_call,
    ):
        project = tmp_path / "project"
        integration = get_integration("claude")
        assert integration is not None
        manifest = IntegrationManifest("claude", project)
        target = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            f"Run {runtime_call}.\n",
            encoding="utf-8",
        )
        manifest.record_existing(target.relative_to(project))
        original = target.read_text(encoding="utf-8") + "User-owned note.\n"
        target.write_text(original, encoding="utf-8")

        integration.repair_runtime_assets(project, manifest, script_type="ps")

        relative = target.relative_to(project).as_posix()
        assert target.read_text(encoding="utf-8") == original
        assert relative in integration._last_repair_skipped_modified
        assert relative in integration._last_repair_unresolved_cognition_markers

    @pytest.mark.parametrize("namespace", ("workflow", "artifact", "cognition"))
    def test_repair_rebinds_unmodified_bare_specify_runtime_call(
        self,
        tmp_path,
        namespace,
    ):
        project = tmp_path / "project"
        integration = get_integration("claude")
        assert integration is not None
        manifest = IntegrationManifest("claude", project)
        binary = project / "runtime" / "specify-runtime.exe"
        binary.parent.mkdir(parents=True)
        binary.write_text("runtime", encoding="utf-8")
        config = project / ".specify" / "config.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {
                    "runtime_launcher": {
                        "command": str(binary),
                        "argv": [str(binary)],
                    }
                }
            ),
            encoding="utf-8",
        )
        target = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            f"Run `specify-runtime {namespace} status --format json`.\n",
            encoding="utf-8",
        )
        manifest.record_existing(target.relative_to(project))

        repaired = integration.repair_runtime_assets(
            project,
            manifest,
            script_type="ps",
        )

        content = target.read_text(encoding="utf-8")
        assert target in repaired
        assert str(binary) in content
        assert f"`specify-runtime {namespace} status" not in content
        assert target.relative_to(project).as_posix() not in (
            integration._last_repair_skipped_modified
        )

    def test_repair_converts_wrapper_conflict_to_typed_partial_report(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        (project / ".specify").mkdir(parents=True)

        def fail_launcher(*args, **kwargs):
            raise RuntimeError("project launcher conflict: preserved wrapper")

        monkeypatch.setattr(
            "specify_cli.launcher.write_project_specify_launcher_config",
            fail_launcher,
        )
        monkeypatch.setattr(
            "specify_cli.launcher.load_runtime_launcher",
            lambda project_root: object(),
        )
        monkeypatch.setattr(
            "specify_cli.launcher.runtime_launcher_is_compatible",
            lambda project_root, launcher: True,
        )
        monkeypatch.setattr(cli_module, "_install_shared_infra", lambda *args, **kwargs: True)

        report = cli_module._repair_active_integration_runtime_assets(
            project,
            script_type="ps",
        )

        wrapper = (
            SPECIFY_PROJECT_LAUNCHER_WINDOWS
            if os.name == "nt"
            else SPECIFY_PROJECT_LAUNCHER_POSIX
        )
        assert wrapper in report.skipped_modified
        assert any(
            issue["code"] == "project-launcher-wrapper-conflict"
            for issue in report.remaining_issues
        )

    def test_repair_diagnostics_fall_back_to_unresolved_cognition_marker_scan(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        (project / ".specify").mkdir(parents=True)
        generated = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        generated.parent.mkdir(parents=True)
        generated.write_text(
            f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:specify-runtime cognition compass\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "specify_cli.launcher.write_project_specify_launcher_config",
            lambda project_root: None,
        )
        monkeypatch.setattr(
            "specify_cli.launcher.load_runtime_launcher",
            lambda project_root: object(),
        )
        monkeypatch.setattr(
            "specify_cli.launcher.runtime_launcher_is_compatible",
            lambda project_root, launcher: True,
        )
        monkeypatch.setattr(cli_module, "_install_shared_infra", lambda *args, **kwargs: True)

        report = cli_module._repair_active_integration_runtime_assets(
            project,
            script_type="ps",
        )

        assert any(
            issue["code"] == "unrebound-specify-runtime-launcher"
            and ".claude/skills/sp-plan/SKILL.md" in issue["summary"]
            for issue in report.remaining_issues
        )

    def test_repair_keeps_claude_personal_skill_shadow_as_remaining_issue(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        (project / ".specify").mkdir(parents=True)
        collision = {
            "code": "claude-personal-skills-shadow-project",
            "severity": "repairable-block",
            "summary": "Claude personal skills shadow project skills: sp-map-scan.",
            "repair": "Move the personal skill outside Claude's skills directory.",
        }
        monkeypatch.setattr(
            "specify_cli.launcher.write_project_specify_launcher_config",
            lambda project_root: None,
        )
        monkeypatch.setattr(
            "specify_cli.launcher.load_runtime_launcher",
            lambda project_root: object(),
        )
        monkeypatch.setattr(
            "specify_cli.launcher.runtime_launcher_is_compatible",
            lambda project_root, launcher: True,
        )
        monkeypatch.setattr(
            "specify_cli.launcher.diagnose_project_runtime_compatibility",
            lambda project_root: [collision],
        )
        monkeypatch.setattr(
            cli_module,
            "_install_shared_infra",
            lambda *args, **kwargs: True,
        )

        report = cli_module._repair_active_integration_runtime_assets(
            project,
            script_type="ps",
        )

        assert report.remaining_issues == (collision,)

    def test_repair_rechecks_runtime_when_binding_drifted(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        (project / ".specify").mkdir(parents=True)
        forced: list[bool] = []
        runtime_binary = project / "runtime" / (
            "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
        )
        runtime_binary.parent.mkdir(parents=True)
        runtime_binary.write_text("runtime", encoding="utf-8")

        monkeypatch.setattr(
            "specify_cli.launcher.write_project_specify_launcher_config",
            lambda project_root: None,
        )
        monkeypatch.setattr(
            "specify_cli.launcher.load_runtime_launcher",
            lambda project_root: object(),
        )
        monkeypatch.setattr(
            "specify_cli.launcher.runtime_launcher_is_compatible",
            lambda project_root, launcher: False,
        )
        monkeypatch.setattr(
            "specify_cli.specify_runtime.ensure_binary",
            lambda force=False: forced.append(force) or runtime_binary,
        )
        monkeypatch.setattr(
            "specify_cli.specify_runtime.write_project_launcher_config",
            lambda project_root, binary: project_root / ".specify" / "config.json",
        )
        monkeypatch.setattr(
            cli_module,
            "_install_shared_infra",
            lambda *args, **kwargs: True,
        )

        cli_module._repair_active_integration_runtime_assets(
            project,
            script_type="ps",
        )

        assert forced == [False]

    def test_partial_repair_tutorial_uses_external_runtime_for_wrapper_recovery(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        (project / ".specify").mkdir(parents=True)
        wrapper = (
            SPECIFY_PROJECT_LAUNCHER_WINDOWS
            if os.name == "nt"
            else SPECIFY_PROJECT_LAUNCHER_POSIX
        )
        report = cli_module.IntegrationRepairReport(
            active_key="claude",
            tracked_files=1,
            skipped_modified=(wrapper,),
            remaining_issues=(
                {
                    "code": "project-launcher-wrapper-conflict",
                    "summary": "wrapper preserved",
                    "repair": "use external runtime",
                },
            ),
        )
        monkeypatch.setattr(
            cli_module,
            "_repair_active_integration_runtime_assets",
            lambda project_root, script_type: report,
        )
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        external = resolve_specify_launcher_spec().command
        assert result.exit_code == 10, result.output
        normalized_output = " ".join(result.output.split())
        assert f"{external} --runtime-id" in normalized_output
        assert f"{external} integration repair --script ps" in normalized_output
        assert "copy the exact `specify_launcher.command`" not in result.output
        assert wrapper in result.output

    def test_partial_repair_prints_safe_claude_shadow_recovery(
        self,
        tmp_path,
        monkeypatch,
    ):
        project = tmp_path / "project"
        (project / ".specify").mkdir(parents=True)
        repair_text = (
            "Back up and move the matching personal skill directory outside "
            "Claude's `skills` directory, fully restart Claude Code, then rerun "
            "`specify check`."
        )
        report = cli_module.IntegrationRepairReport(
            active_key="claude",
            tracked_files=1,
            remaining_issues=(
                {
                    "code": "claude-personal-skills-shadow-project",
                    "severity": "repairable-block",
                    "summary": "Claude personal skills shadow project skills.",
                    "repair": repair_text,
                },
            ),
        )
        monkeypatch.setattr(
            cli_module,
            "_repair_active_integration_runtime_assets",
            lambda project_root, script_type: report,
        )
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 10, result.output
        assert repair_text in " ".join(result.output.split())
        assert "never include tokens or secrets" not in result.output

    def test_repair_upgrades_direct_claude_hook_commands_to_shared_launcher(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        settings_path = project / ".claude" / "settings.json"
        settings_payload = json.loads(settings_path.read_text(encoding="utf-8"))
        for entries in settings_payload.get("hooks", {}).values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                        command = hook["command"]
                        if ".specify/bin/specify-hook" in command:
                            hook["command"] = command.replace(
                                '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd claude',
                                'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py',
                            )
                            hook["command"] = hook["command"].replace(
                                '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook claude',
                                'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py',
                            )
        settings_path.write_text(json.dumps(settings_payload, indent=2) + "\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        repaired_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        hooks = [
            hook
            for entries in repaired_settings["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]
        assert _expected_claude_hook("session-start") in hooks
        assert not any(
            isinstance(hook.get("command"), str) and "claude-hook-dispatch.py" in hook["command"]
            for hook in hooks
        )

    def test_repair_refreshes_missing_project_launcher_and_stale_claude_hook_commands(self, tmp_path, monkeypatch):
        project = _init_project(tmp_path, "claude")

        config_path = project / ".specify" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_payload = {}
        config_path.write_text(json.dumps(config_payload, indent=2) + "\n", encoding="utf-8")

        launcher = SpecifyLauncherSpec(
            command="uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa specify",
            argv=(
                "uvx",
                "--from",
                "git+https://github.com/chenziyang110/spec-kit-plus.git@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "specify",
            ),
        )
        monkeypatch.setattr("specify_cli.launcher.resolve_specify_launcher_spec", lambda: launcher)

        settings_path = project / ".claude" / "settings.json"
        settings_payload = json.loads(settings_path.read_text(encoding="utf-8"))
        for entries in settings_payload.get("hooks", {}).values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                        hook["command"] = hook["command"].replace(
                            '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook',
                            '"$env:CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd',
                        )
        settings_path.write_text(json.dumps(settings_payload, indent=2) + "\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert "repaired runtime-managed surfaces" in result.output.lower()

        repaired_config = json.loads(config_path.read_text(encoding="utf-8"))
        assert isinstance(repaired_config.get("specify_launcher"), dict)
        assert repaired_config["specify_launcher"]["argv"] == list(launcher.argv)

        repaired_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        hooks = [
            hook
            for entries in repaired_settings["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        ]
        assert hooks
        assert _expected_claude_hook("session-start") in hooks
        assert all(
            isinstance(hook.get("command"), str)
            and hook["command"].startswith('node -e "')
            and '" specify-hook claude ' in hook["command"]
            and "specify-hook.mjs" in hook["command"]
            for hook in hooks
        )
        assert all("args" not in hook for hook in hooks)
        assert all("specify-hook.cmd" not in json.dumps(hook) for hook in hooks)
        assert all("$CLAUDE_PROJECT_DIR" not in json.dumps(hook) for hook in hooks)
        assert all("$env:CLAUDE_PROJECT_DIR" not in json.dumps(hook) for hook in hooks)

    def test_repair_preserves_user_modified_shared_powershell_script(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        common_path = project / ".specify" / "scripts" / "powershell" / "common.ps1"
        common_path.parent.mkdir(parents=True, exist_ok=True)
        original = "function Get-FeaturePathsEnv { $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch }\n"
        common_path.write_text(original, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 10, result.output
        assert "PARTIAL" in result.output
        assert ".specify/scripts/powershell/common.ps1" in result.output
        repaired = common_path.read_text(encoding="utf-8")
        assert repaired == original

    def test_repair_preserves_user_modified_skill_content(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        skill_path = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        original = "# custom user skill content\n"
        skill_path.write_text(original, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert skill_path.read_text(encoding="utf-8") == original

    def test_repair_restores_missing_manifest_owned_reference_sidecar(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        reference = (
            project
            / ".claude"
            / "skills"
            / "sp-plan"
            / "references"
            / "INDEX.md"
        )
        assert reference.exists()
        reference.unlink()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "sh"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert reference.exists()
        assert "Plan Reference Index" in reference.read_text(encoding="utf-8")

    def test_repair_preserves_user_modified_reference_sidecar(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        reference = (
            project
            / ".claude"
            / "skills"
            / "sp-plan"
            / "references"
            / "INDEX.md"
        )
        original = "# user-modified reference index\n"
        reference.write_text(original, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "sh"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert reference.read_text(encoding="utf-8") == original

    def test_repair_codex_removes_misplaced_claude_hook_artifacts(self, tmp_path):
        project = _init_project(tmp_path, "codex")

        hooks_path = project / ".codex" / "hooks.json"
        hooks_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PostToolUse": [
                            {
                                "matcher": "Bash|Edit|Write|MultiEdit|Task",
                                "hooks": [
                                    _expected_claude_hook("post-tool-session-state")
                                ],
                            }
                        ]
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        hooks_dir = project / ".codex" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "claude-hook-dispatch.py").write_text("print('stale')\n", encoding="utf-8")
        (hooks_dir / "README.md").write_text("# Claude Hook Assets\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "ps"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert not hooks_path.exists()
        assert not hooks_dir.exists()
        assert (project / ".codex" / "skills" / "sp-teams" / "SKILL.md").exists()


# ── Full lifecycle ───────────────────────────────────────────────────


class TestIntegrationLifecycle:
    def test_install_modify_uninstall_preserves_modified(self, tmp_path):
        """Full lifecycle: install → modify file → uninstall → verify modified file kept."""
        project = tmp_path / "lifecycle"
        project.mkdir()
        (project / ".specify").mkdir()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)

            # Install
            result = runner.invoke(app, [
                "integration", "install", "claude",
                "--script", "sh",
            ], catch_exceptions=False)
            assert result.exit_code == 0
            assert "installed successfully" in result.output

            # Claude uses skills directory
            plan_file = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
            assert plan_file.exists()

            # Modify one file
            plan_file.write_text("# user customization\n", encoding="utf-8")

            # Uninstall
            result = runner.invoke(app, ["integration", "uninstall"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "preserved" in result.output

            # Modified file kept
            assert plan_file.exists()
            assert plan_file.read_text(encoding="utf-8") == "# user customization\n"
        finally:
            os.chdir(old_cwd)


# ── Edge-case fixes ─────────────────────────────────────────────────


class TestScriptTypeValidation:
    def test_invalid_script_type_rejected(self, tmp_path):
        """--script with an invalid value should fail with a clear error."""
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "install", "claude",
                "--script", "bash",
            ])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code != 0
        assert "Invalid script type" in result.output

    def test_valid_script_types_accepted(self, tmp_path):
        """Both 'sh' and 'ps' should be accepted."""
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".specify").mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "integration", "install", "claude",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0


class TestParseIntegrationOptionsEqualsForm:
    def test_equals_form_parsed(self):
        """--commands-dir=./x should be parsed the same as --commands-dir ./x."""
        from specify_cli import _parse_integration_options
        from specify_cli.integrations import get_integration

        integration = get_integration("generic")
        assert integration is not None

        result_space = _parse_integration_options(integration, "--commands-dir ./mydir")
        result_equals = _parse_integration_options(integration, "--commands-dir=./mydir")
        assert result_space is not None
        assert result_equals is not None
        assert result_space["commands_dir"] == "./mydir"
        assert result_equals["commands_dir"] == "./mydir"


class TestUninstallNoManifestClearsInitOptions:
    def test_init_options_cleared_on_no_manifest_uninstall(self, tmp_path):
        """When no manifest exists, uninstall should still clear init-options.json."""
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".specify").mkdir()

        # Write integration.json and init-options.json without a manifest
        int_json = project / ".specify" / "integration.json"
        int_json.write_text(json.dumps({"integration": "claude"}), encoding="utf-8")

        opts_json = project / ".specify" / "init-options.json"
        opts_json.write_text(json.dumps({
            "integration": "claude",
            "ai": "claude",
            "ai_skills": True,
            "script": "sh",
        }), encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, ["integration", "uninstall", "claude"])
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0

        # init-options.json should have integration keys cleared
        opts = json.loads(opts_json.read_text(encoding="utf-8"))
        assert "integration" not in opts
        assert "ai" not in opts
        assert "ai_skills" not in opts
        # Non-integration keys preserved
        assert opts.get("script") == "sh"


class TestSwitchClearsMetadataAfterTeardown:
    def test_metadata_cleared_between_phases(self, tmp_path):
        """After a successful switch, metadata should reference the new integration."""
        project = _init_project(tmp_path, "claude")

        # Verify initial state
        int_json = project / ".specify" / "integration.json"
        assert json.loads(int_json.read_text(encoding="utf-8"))["integration"] == "claude"

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            # Switch to copilot — should succeed and update metadata
            result = runner.invoke(app, [
                "integration", "switch", "copilot",
                "--script", "sh",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0

        # integration.json should reference copilot, not claude
        data = json.loads(int_json.read_text(encoding="utf-8"))
        assert data["integration"] == "copilot"

        # init-options.json should reference copilot
        opts_json = project / ".specify" / "init-options.json"
        opts = json.loads(opts_json.read_text(encoding="utf-8"))
        assert opts.get("ai") == "copilot"
