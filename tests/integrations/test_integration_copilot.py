"""Tests for CopilotIntegration."""

import json
import os

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


class TestCopilotIntegration:
    @staticmethod
    def _command_stems() -> list[str]:
        copilot = get_integration("copilot")
        return [template.stem for template in copilot.list_command_templates()]

    @staticmethod
    def _template_files() -> list[str]:
        copilot = get_integration("copilot")
        templates_dir = copilot.shared_templates_dir()
        if not templates_dir or not templates_dir.is_dir():
            return []

        return sorted(
            path.relative_to(templates_dir).as_posix()
            for path in templates_dir.rglob("*")
            if path.is_file() and path.name != "vscode-settings.json"
        )

    @classmethod
    def _expected_inventory(cls, script_variant: str) -> list[str]:
        copilot = get_integration("copilot")
        expected = []

        for stem in cls._command_stems():
            expected.append(f".github/agents/sp.{stem}.agent.md")
            expected.append(f".github/prompts/sp.{stem}.prompt.md")

        if copilot.context_file:
            expected.append(copilot.context_file)

        expected.extend(
            [
                ".vscode/settings.json",
                ".specify/integration.json",
                ".specify/init-options.json",
                ".specify/integrations/copilot.manifest.json",
                ".specify/integrations/speckit.manifest.json",
                ".specify/integrations/copilot/scripts/update-context.ps1",
                ".specify/integrations/copilot/scripts/update-context.sh",
                ".specify/memory/constitution.md",
                ".specify/memory/project-learnings.md",
                ".specify/memory/project-rules.md",
                ".specify/project-map/index/status.json",
            ]
        )

        if script_variant == "sh":
            expected.extend(
                [
                    ".specify/scripts/bash/check-prerequisites.sh",
                    ".specify/scripts/bash/common.sh",
                    ".specify/scripts/bash/create-new-feature.sh",
                    ".specify/scripts/bash/project-map-freshness.sh",
                    ".specify/scripts/bash/quick-state.sh",
                    ".specify/scripts/bash/setup-plan.sh",
                    ".specify/scripts/bash/update-agent-context.sh",
                ]
            )
        else:
            expected.extend(
                [
                    ".specify/scripts/powershell/check-prerequisites.ps1",
                    ".specify/scripts/powershell/common.ps1",
                    ".specify/scripts/powershell/create-new-feature.ps1",
                    ".specify/scripts/powershell/project-map-freshness.ps1",
                    ".specify/scripts/powershell/quick-state.ps1",
                    ".specify/scripts/powershell/setup-plan.ps1",
                    ".specify/scripts/powershell/update-agent-context.ps1",
                ]
            )

        expected.extend(f".specify/templates/{name}" for name in cls._template_files())
        return sorted(expected)

    def test_copilot_key_and_config(self):
        copilot = get_integration("copilot")
        assert copilot is not None
        assert copilot.key == "copilot"
        assert copilot.config["folder"] == ".github/"
        assert copilot.config["commands_subdir"] == "agents"
        assert copilot.registrar_config["extension"] == ".agent.md"
        assert copilot.context_file == ".github/copilot-instructions.md"

    def test_command_filename_agent_md(self):
        copilot = get_integration("copilot")
        assert copilot.command_filename("plan") == "sp.plan.agent.md"

    def test_setup_creates_agent_md_files(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.setup(tmp_path, m)
        assert len(created) > 0
        agent_files = [f for f in created if ".agent." in f.name]
        assert len(agent_files) > 0
        for f in agent_files:
            assert f.parent == tmp_path / ".github" / "agents"
            assert f.name.endswith(".agent.md")

    def test_setup_creates_companion_prompts(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.setup(tmp_path, m)
        prompt_files = [f for f in created if f.parent.name == "prompts"]
        assert len(prompt_files) > 0
        for f in prompt_files:
            assert f.name.endswith(".prompt.md")
            content = f.read_text(encoding="utf-8")
            assert content.startswith("---\nagent: sp.")

    def test_agent_and_prompt_counts_match(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.setup(tmp_path, m)
        agents = [f for f in created if ".agent.md" in f.name]
        prompts = [f for f in created if ".prompt.md" in f.name]
        assert len(agents) == len(prompts)

    def test_setup_creates_vscode_settings_new(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        assert copilot._vscode_settings_path() is not None
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.setup(tmp_path, m)
        settings = tmp_path / ".vscode" / "settings.json"
        assert settings.exists()
        assert settings in created
        assert any("settings.json" in k for k in m.files)

    def test_setup_merges_existing_vscode_settings(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir(parents=True)
        existing = {"editor.fontSize": 14, "custom.setting": True}
        (vscode_dir / "settings.json").write_text(json.dumps(existing, indent=4), encoding="utf-8")
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.setup(tmp_path, m)
        settings = tmp_path / ".vscode" / "settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        assert data["editor.fontSize"] == 14
        assert data["custom.setting"] is True
        assert settings not in created
        assert not any("settings.json" in k for k in m.files)

    def test_all_created_files_tracked_in_manifest(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.setup(tmp_path, m)
        for f in created:
            rel = f.resolve().relative_to(tmp_path.resolve()).as_posix()
            assert rel in m.files, f"Created file {rel} not tracked in manifest"

    def test_install_uninstall_roundtrip(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.install(tmp_path, m)
        assert len(created) > 0
        m.save()
        for f in created:
            assert f.exists()
        removed, skipped = copilot.uninstall(tmp_path, m)
        assert len(removed) == len(created)
        assert skipped == []

    def test_modified_file_survives_uninstall(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        created = copilot.install(tmp_path, m)
        m.save()
        modified_file = created[0]
        modified_file.write_text("user modified this", encoding="utf-8")
        removed, skipped = copilot.uninstall(tmp_path, m)
        assert modified_file.exists()
        assert modified_file in skipped

    def test_directory_structure(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        copilot.setup(tmp_path, m)
        agents_dir = tmp_path / ".github" / "agents"
        assert agents_dir.is_dir()
        agent_files = sorted(agents_dir.glob("sp.*.agent.md"))
        expected_commands = set(self._command_stems())
        assert len(agent_files) == len(expected_commands)
        actual_commands = {f.name.removeprefix("sp.").removesuffix(".agent.md") for f in agent_files}
        assert actual_commands == expected_commands

    def test_templates_are_processed(self, tmp_path):
        from specify_cli.integrations.copilot import CopilotIntegration
        copilot = CopilotIntegration()
        m = IntegrationManifest("copilot", tmp_path)
        copilot.setup(tmp_path, m)
        agents_dir = tmp_path / ".github" / "agents"
        for agent_file in agents_dir.glob("sp.*.agent.md"):
            content = agent_file.read_text(encoding="utf-8")
            assert "{SCRIPT}" not in content, f"{agent_file.name} has unprocessed {{SCRIPT}}"
            assert "__AGENT__" not in content, f"{agent_file.name} has unprocessed __AGENT__"
            assert "{ARGS}" not in content, f"{agent_file.name} has unprocessed {{ARGS}}"
            assert "\nscripts:\n" not in content
            assert "\nagent_scripts:\n" not in content

    def test_runtime_commands_hard_gate_project_map_reads(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "copilot-project-map-gate"

        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "copilot", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai copilot failed: {result.output}"

        for rel in (
            ".github/agents/sp.implement.agent.md",
            ".github/agents/sp.debug.agent.md",
            ".github/agents/sp.quick.agent.md",
        ):
            content = (target / rel).read_text(encoding="utf-8").lower()
            assert "crucial first step" in content
            assert "project-handbook.md" in content
            assert ".specify/project-map/*.md" in content
            assert "/sp-map-codebase" in content

    def test_complete_file_inventory_sh(self, tmp_path):
        """Every file produced by specify init --integration copilot --script sh."""
        from typer.testing import CliRunner
        from specify_cli import app
        project = tmp_path / "inventory-sh"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--integration", "copilot", "--script", "sh", "--no-git",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        actual = sorted(p.relative_to(project).as_posix() for p in project.rglob("*") if p.is_file())
        expected = self._expected_inventory("sh")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )

    def test_complete_file_inventory_ps(self, tmp_path):
        """Every file produced by specify init --integration copilot --script ps."""
        from typer.testing import CliRunner
        from specify_cli import app
        project = tmp_path / "inventory-ps"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--integration", "copilot", "--script", "ps", "--no-git",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        actual = sorted(p.relative_to(project).as_posix() for p in project.rglob("*") if p.is_file())
        expected = self._expected_inventory("ps")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )
