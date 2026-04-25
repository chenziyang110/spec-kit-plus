"""Reusable test mixin for standard MarkdownIntegration subclasses.

Each per-agent test file sets ``KEY``, ``FOLDER``, ``COMMANDS_SUBDIR``,
``REGISTRAR_DIR``, and ``CONTEXT_FILE``, then inherits all verification
logic from ``MarkdownIntegrationTests``.
"""

import os

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import MarkdownIntegration
from specify_cli.integrations.manifest import IntegrationManifest


class MarkdownIntegrationTests:
    """Mixin — set class-level constants and inherit these tests.

    Required class attrs on subclass::

        KEY: str              — integration registry key
        FOLDER: str           — e.g. ".claude/"
        COMMANDS_SUBDIR: str  — e.g. "commands"
        REGISTRAR_DIR: str    — e.g. ".claude/commands"
        CONTEXT_FILE: str     — e.g. "CLAUDE.md"
    """

    KEY: str
    FOLDER: str
    COMMANDS_SUBDIR: str
    REGISTRAR_DIR: str
    CONTEXT_FILE: str

    # -- Registration -----------------------------------------------------

    def test_registered(self):
        assert self.KEY in INTEGRATION_REGISTRY
        assert get_integration(self.KEY) is not None

    def test_is_markdown_integration(self):
        assert isinstance(get_integration(self.KEY), MarkdownIntegration)

    # -- Config -----------------------------------------------------------

    def test_config_folder(self):
        i = get_integration(self.KEY)
        assert i.config["folder"] == self.FOLDER

    def test_config_commands_subdir(self):
        i = get_integration(self.KEY)
        assert i.config["commands_subdir"] == self.COMMANDS_SUBDIR

    def test_registrar_config(self):
        i = get_integration(self.KEY)
        assert i.registrar_config["dir"] == self.REGISTRAR_DIR
        assert i.registrar_config["format"] == "markdown"
        assert i.registrar_config["args"] == "$ARGUMENTS"
        assert i.registrar_config["extension"] == ".md"

    def test_context_file(self):
        i = get_integration(self.KEY)
        assert i.context_file == self.CONTEXT_FILE

    # -- Setup / teardown -------------------------------------------------

    def test_setup_creates_files(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        assert len(created) > 0
        cmd_files = [f for f in created if "scripts" not in f.parts]
        for f in cmd_files:
            assert f.exists()
            assert f.name.startswith("sp.")
            assert f.name.endswith(".md")

    def test_setup_writes_to_correct_directory(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        expected_dir = i.commands_dest(tmp_path)
        assert expected_dir.exists(), f"Expected directory {expected_dir} was not created"
        cmd_files = [f for f in created if "scripts" not in f.parts]
        assert len(cmd_files) > 0, "No command files were created"
        for f in cmd_files:
            assert f.resolve().parent == expected_dir.resolve(), (
                f"{f} is not under {expected_dir}"
            )

    def test_templates_are_processed(self, tmp_path):
        """Command files must have placeholders replaced, not raw templates."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        cmd_files = [f for f in created if "scripts" not in f.parts]
        assert len(cmd_files) > 0
        for f in cmd_files:
            content = f.read_text(encoding="utf-8")
            assert "{SCRIPT}" not in content, f"{f.name} has unprocessed {{SCRIPT}}"
            assert "__AGENT__" not in content, f"{f.name} has unprocessed __AGENT__"
            assert "{ARGS}" not in content, f"{f.name} has unprocessed {{ARGS}}"
            assert "\nscripts:\n" not in content, f"{f.name} has unstripped scripts: block"
            assert "\nagent_scripts:\n" not in content, f"{f.name} has unstripped agent_scripts: block"

    def test_runtime_commands_hard_gate_project_map_reads(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        runtime_files = {
            f"sp.{stem}.md"
            for stem in ("implement", "debug", "quick")
        }
        cmd_files = [
            f for f in created
            if f.name in runtime_files and "scripts" not in f.parts
        ]
        assert len(cmd_files) == 3
        for f in cmd_files:
            content = f.read_text(encoding="utf-8").lower()
            assert "crucial first step" in content
            assert "project-handbook.md" in content
            assert ".specify/project-map/*.md" in content
            assert "/sp-map-codebase" in content

    def test_implement_command_has_shared_leader_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        implement_path = i.commands_dest(tmp_path) / "sp.implement.md"
        content = implement_path.read_text(encoding="utf-8")
        lowered = content.lower()
        agent_name = i.config["name"].replace(" CLI", "")

        assert f"## {agent_name} Leader Gate" in content
        assert "you are the **leader**, not the concrete implementer" in lowered
        assert "autonomous blocker recovery" in lowered
        assert "missed_agent_dispatch" in lowered
        assert "single-agent` still means one delegated worker lane" in content
        assert "current runtime's native worker lanes" in lowered
        assert "current integration's coordinated runtime surface" in lowered
        assert "dispatch only from validated `workertaskpacket`" in lowered
        assert "must not edit implementation files directly while worker delegation is active" in lowered

    def test_runtime_commands_have_shared_delegation_and_result_contracts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        for name in ("implement", "debug", "quick"):
            content = (i.commands_dest(tmp_path) / f"sp.{name}.md").read_text(encoding="utf-8").lower()
            assert "delegation surface contract" in content
            assert "native dispatch surface" in content
            assert "sidecar fallback" in content
            assert "worker result contract" in content
            assert "result handoff path" in content
            assert "reported_status" in content
            assert "needs_context" in content

    def test_debug_and_quick_commands_have_shared_leader_and_routing_sections(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "")

        debug_content = (i.commands_dest(tmp_path) / "sp.debug.md").read_text(encoding="utf-8").lower()
        quick_content = (i.commands_dest(tmp_path) / "sp.quick.md").read_text(encoding="utf-8").lower()

        assert f"## {agent_name} Leader Gate".lower() in debug_content
        assert "you are the **leader**, not a freeform debugger" in debug_content
        assert "investigation routing contract" in debug_content
        assert "single-agent" in debug_content
        assert "native-multi-agent" in debug_content
        assert "sidecar-runtime" in debug_content

        assert f"## {agent_name} Leader Gate".lower() in quick_content
        assert "you are the **leader**, not the concrete implementer" in quick_content
        assert "quick execution routing" in quick_content
        assert "dispatch exactly one delegated worker lane" in quick_content
        assert "sidecar-runtime" in quick_content

    def test_question_driven_commands_define_native_tool_preference_with_fallback(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "").lower()

        for name in ("specify", "spec-extend", "checklist", "quick", "debug"):
            content = (i.commands_dest(tmp_path) / f"sp.{name}.md").read_text(encoding="utf-8").lower()
            assert f"## {agent_name} structured question preference" in content
            assert "native structured question tool" in content
            assert "fallback-only guidance" in content
            assert (
                "template's existing textual question format" in content
                or "existing plain-text" in content
                or "shared open question block structure" in content
                or "plain-text confirmation question" in content
                or "textual question format" in content
                or "plain-text clarification" in content
                or "missing-information question" in content
            )
            assert "active question exactly once" in content

    def test_all_files_tracked_in_manifest(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        for f in created:
            rel = f.resolve().relative_to(tmp_path.resolve()).as_posix()
            assert rel in m.files, f"{rel} not tracked in manifest"

    def test_install_uninstall_roundtrip(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.install(tmp_path, m)
        assert len(created) > 0
        m.save()
        for f in created:
            assert f.exists()
        removed, skipped = i.uninstall(tmp_path, m)
        assert len(removed) == len(created)
        assert skipped == []

    def test_modified_file_survives_uninstall(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.install(tmp_path, m)
        m.save()
        modified_file = created[0]
        modified_file.write_text("user modified this", encoding="utf-8")
        removed, skipped = i.uninstall(tmp_path, m)
        assert modified_file.exists()
        assert modified_file in skipped

    # -- Scripts ----------------------------------------------------------

    def test_setup_installs_update_context_scripts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        scripts_dir = tmp_path / ".specify" / "integrations" / self.KEY / "scripts"
        assert scripts_dir.is_dir(), f"Scripts directory not created for {self.KEY}"
        assert (scripts_dir / "update-context.sh").exists()
        assert (scripts_dir / "update-context.ps1").exists()

    def test_scripts_tracked_in_manifest(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        script_rels = [k for k in m.files if "update-context" in k]
        assert len(script_rels) >= 2

    def test_sh_script_is_executable(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        sh = tmp_path / ".specify" / "integrations" / self.KEY / "scripts" / "update-context.sh"
        assert os.access(sh, os.X_OK)

    # -- CLI auto-promote -------------------------------------------------

    def test_ai_flag_auto_promotes(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"promote-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--ai", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        i = get_integration(self.KEY)
        cmd_dir = i.commands_dest(project)
        assert cmd_dir.is_dir(), f"--ai {self.KEY} did not create commands directory"

    def test_integration_flag_creates_files(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"int-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--integration", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init --integration {self.KEY} failed: {result.output}"
        i = get_integration(self.KEY)
        cmd_dir = i.commands_dest(project)
        assert cmd_dir.is_dir(), f"Commands directory {cmd_dir} not created"
        commands = sorted(cmd_dir.glob("sp.*"))
        assert len(commands) > 0, f"No command files in {cmd_dir}"

    # -- Complete file inventory ------------------------------------------

    def _command_stems(self) -> list[str]:
        i = get_integration(self.KEY)
        return [template.stem for template in i.list_command_templates()]

    def _template_files(self) -> list[str]:
        i = get_integration(self.KEY)
        templates_dir = i.shared_templates_dir()
        if not templates_dir or not templates_dir.is_dir():
            return []

        return sorted(
            path.relative_to(templates_dir).as_posix()
            for path in templates_dir.rglob("*")
            if path.is_file() and path.name != "vscode-settings.json"
        )

    def _expected_files(self, script_variant: str) -> list[str]:
        """Build the expected file list for this integration + script variant."""
        i = get_integration(self.KEY)
        cmd_dir = i.registrar_config["dir"]
        files = []

        # Command files
        for stem in self._command_stems():
            files.append(f"{cmd_dir}/sp.{stem}.md")

        # Integration scripts
        files.append(f".specify/integrations/{self.KEY}/scripts/update-context.ps1")
        files.append(f".specify/integrations/{self.KEY}/scripts/update-context.sh")
        files.append(self.CONTEXT_FILE)

        # Framework files
        files.append(f".specify/integration.json")
        files.append(f".specify/init-options.json")
        files.append(f".specify/integrations/{self.KEY}.manifest.json")
        files.append(f".specify/integrations/speckit.manifest.json")

        if script_variant == "sh":
            for name in ["check-prerequisites.sh", "common.sh", "create-new-feature.sh",
                         "project-map-freshness.sh", "quick-state.sh", "setup-plan.sh", "update-agent-context.sh"]:
                files.append(f".specify/scripts/bash/{name}")
        else:
            for name in ["check-prerequisites.ps1", "common.ps1", "create-new-feature.ps1",
                         "project-map-freshness.ps1", "quick-state.ps1", "setup-plan.ps1", "update-agent-context.ps1"]:
                files.append(f".specify/scripts/powershell/{name}")

        for name in self._template_files():
            files.append(f".specify/templates/{name}")

        files.append(".specify/memory/constitution.md")
        files.append(".specify/memory/project-learnings.md")
        files.append(".specify/memory/project-rules.md")
        files.append(".specify/project-map/status.json")
        return sorted(files)

    def test_complete_file_inventory_sh(self, tmp_path):
        """Every file produced by specify init --integration <key> --script sh."""
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"inventory-sh-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--integration", self.KEY, "--script", "sh",
                "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        actual = sorted(p.relative_to(project).as_posix()
                        for p in project.rglob("*") if p.is_file())
        expected = self._expected_files("sh")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )

    def test_init_bootstraps_context_file(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"context-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--ai", self.KEY, "--script", "sh",
                "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        assert (project / self.CONTEXT_FILE).is_file(), (
            f"--ai {self.KEY} did not create context file {self.CONTEXT_FILE}"
        )

    def test_complete_file_inventory_ps(self, tmp_path):
        """Every file produced by specify init --integration <key> --script ps."""
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"inventory-ps-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--integration", self.KEY, "--script", "ps",
                "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        actual = sorted(p.relative_to(project).as_posix()
                        for p in project.rglob("*") if p.is_file())
        expected = self._expected_files("ps")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )
