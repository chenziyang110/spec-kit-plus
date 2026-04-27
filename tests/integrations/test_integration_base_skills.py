"""Reusable test mixin for standard SkillsIntegration subclasses.

Each per-agent test file sets ``KEY``, ``FOLDER``, ``COMMANDS_SUBDIR``,
``REGISTRAR_DIR``, and ``CONTEXT_FILE``, then inherits all verification
logic from ``SkillsIntegrationTests``.

Mirrors ``MarkdownIntegrationTests`` / ``TomlIntegrationTests`` closely,
adapted for the ``sp-<name>/SKILL.md`` skills layout.
"""

import os

import yaml

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import SkillsIntegration
from specify_cli.integrations.manifest import IntegrationManifest

SPEC_KIT_BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"


class SkillsIntegrationTests:
    """Mixin — set class-level constants and inherit these tests.

    Required class attrs on subclass::

        KEY: str              — integration registry key
        FOLDER: str           — e.g. ".agents/"
        COMMANDS_SUBDIR: str  — e.g. "skills"
        REGISTRAR_DIR: str    — e.g. ".agents/skills"
        CONTEXT_FILE: str     — e.g. "AGENTS.md"
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

    def test_is_skills_integration(self):
        assert isinstance(get_integration(self.KEY), SkillsIntegration)

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
        assert i.registrar_config["extension"] == "/SKILL.md"

    def test_context_file(self):
        i = get_integration(self.KEY)
        assert i.context_file == self.CONTEXT_FILE

    # -- Setup / teardown -------------------------------------------------

    def test_setup_creates_files(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        assert len(created) > 0
        skills_dir = i.skills_dest(tmp_path).resolve()
        expected_skill_dirs = {
            *(f"sp-{command}" for command in self._skill_commands()),
            *self._passive_skill_names(),
        }
        generated_files = [f for f in created if "scripts" not in f.parts]
        skill_manifests = [f for f in generated_files if f.name == "SKILL.md"]

        assert skill_manifests, "No generated SKILL.md files were created"
        for f in generated_files:
            assert f.exists()
            rel = f.resolve().relative_to(skills_dir)
            assert rel.parts[0] in expected_skill_dirs
        for f in skill_manifests:
            assert f.parent.name in expected_skill_dirs

    def test_setup_writes_to_correct_directory(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        expected_dir = i.skills_dest(tmp_path)
        assert expected_dir.exists(), f"Expected directory {expected_dir} was not created"
        expected_skill_dirs = {
            *(f"sp-{command}" for command in self._skill_commands()),
            *self._passive_skill_names(),
        }
        generated_files = [f for f in created if "scripts" not in f.parts]
        skill_manifests = [f for f in generated_files if f.name == "SKILL.md"]
        assert len(skill_manifests) > 0, "No skill files were created"
        for f in generated_files:
            rel = f.resolve().relative_to(expected_dir.resolve())
            assert rel.parts[0] in expected_skill_dirs, f"{f} is not under {expected_dir}"

    def test_skill_directory_structure(self, tmp_path):
        """Commands and passive skills produce their expected skill directories."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]

        expected_commands = set(self._skill_commands())
        expected_passive_skills = set(self._passive_skill_names())

        # Derive command names from the skill directory names
        actual_commands = set()
        actual_passive_skills = set()
        for f in skill_files:
            skill_dir_name = f.parent.name
            if skill_dir_name.startswith("sp-"):
                actual_commands.add(skill_dir_name.removeprefix("sp-"))
            else:
                actual_passive_skills.add(skill_dir_name)

        assert actual_commands == expected_commands
        assert actual_passive_skills == expected_passive_skills

    def test_passive_skills_use_distinct_non_sp_namespace(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        passive_skill_files = [
            f for f in created if f.name == "SKILL.md" and not f.parent.name.startswith("sp-")
        ]

        assert passive_skill_files, "Expected at least one passive skill to be generated"
        for skill_file in passive_skill_files:
            content = skill_file.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            assert fm["name"] == skill_file.parent.name
            assert not fm["name"].startswith("sp-")
            assert fm["metadata"]["source"].startswith("templates/passive-skills/")

    def test_skill_frontmatter_structure(self, tmp_path):
        """SKILL.md must have name, description, compatibility, metadata."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]

        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            assert content.startswith("---\n"), f"{f} missing frontmatter"
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            assert "name" in fm, f"{f} frontmatter missing 'name'"
            assert "description" in fm, f"{f} frontmatter missing 'description'"
            assert "compatibility" in fm, f"{f} frontmatter missing 'compatibility'"
            assert "metadata" in fm, f"{f} frontmatter missing 'metadata'"
            assert fm["metadata"]["author"] == "github-spec-kit"
            assert "source" in fm["metadata"]

    def test_skill_uses_template_descriptions(self, tmp_path):
        """SKILL.md should use the original template description for ZIP parity."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]

        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            # Description must be a non-empty string (from the template)
            assert isinstance(fm["description"], str)
            assert len(fm["description"]) > 0, f"{f} has empty description"

    def test_templates_are_processed(self, tmp_path):
        """Skill body must have placeholders replaced, not raw templates."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]
        assert len(skill_files) > 0
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            assert "{SCRIPT}" not in content, f"{f.name} has unprocessed {{SCRIPT}}"
            assert "__AGENT__" not in content, f"{f.name} has unprocessed __AGENT__"
            assert "{ARGS}" not in content, f"{f.name} has unprocessed {{ARGS}}"

    def test_skill_body_has_content(self, tmp_path):
        """Each SKILL.md body should contain template content after the frontmatter."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            # Body is everything after the second ---
            parts = content.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""
            assert len(body) > 0, f"{f} has empty body"

    def test_implement_skill_has_shared_leader_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        implement_path = i.skills_dest(tmp_path) / "sp-implement" / "SKILL.md"
        content = implement_path.read_text(encoding="utf-8")
        lowered = content.lower()
        agent_name = i.config["name"].replace(" CLI", "")

        assert f"## {agent_name} Leader Gate" in content
        assert "you are the **leader**, not the concrete implementer" in lowered
        assert "autonomous blocker recovery" in lowered
        assert "missed_agent_dispatch" in lowered
        assert "`single-lane` names the topology for one safe execution lane" in content
        assert "does not, by itself, decide whether the leader or a delegated worker executes that lane" in content
        assert "current runtime's native worker lanes" in lowered
        assert "current integration's coordinated runtime surface" in lowered
        assert "dispatch only from validated `workertaskpacket`" in lowered
        assert "must not edit implementation files directly while worker delegation is active" in lowered

    def test_runtime_skills_have_shared_delegation_and_result_contracts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        for name in ("implement", "debug", "quick"):
            content = (i.skills_dest(tmp_path) / f"sp-{name}" / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "delegation surface contract" in content
            assert "native dispatch surface" in content
            assert "sidecar fallback" in content
            assert "worker result contract" in content
            assert "result handoff path" in content
            assert "reported_status" in content
            assert "needs_context" in content

    def test_debug_and_quick_skills_have_shared_leader_and_routing_sections(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "")

        debug_content = (i.skills_dest(tmp_path) / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
        quick_content = (i.skills_dest(tmp_path) / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()

        assert f"## {agent_name} Leader Gate".lower() in debug_content
        assert "you are the **leader**, not a freeform debugger" in debug_content
        assert "investigation routing contract" in debug_content
        assert "single-lane" in debug_content
        assert "native-multi-agent" in debug_content
        assert "sidecar-runtime" in debug_content

        assert f"## {agent_name} Leader Gate".lower() in quick_content
        assert "you are the **leader**, not the concrete implementer" in quick_content
        assert "quick execution routing" in quick_content
        assert "single-lane" in quick_content
        assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in quick_content
        assert "sidecar-runtime" in quick_content

    def test_question_driven_skills_define_native_tool_preference_with_fallback(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "").lower()

        for name in ("specify", "spec-extend", "checklist", "quick", "debug"):
            content = (i.skills_dest(tmp_path) / f"sp-{name}" / "SKILL.md").read_text(encoding="utf-8").lower()
            assert f"## {agent_name} structured question preference" in content
            assert "native structured question tool" in content
            assert "fallback-only guidance" in content
            assert "must use it" in content
            assert "do not render the textual fallback block" in content
            assert "do not self-authorize textual fallback" in content
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

    def test_pre_existing_skills_not_removed(self, tmp_path):
        """Pre-existing non-speckit skills should be left untouched."""
        i = get_integration(self.KEY)
        skills_dir = i.skills_dest(tmp_path)
        foreign_dir = skills_dir / "other-tool"
        foreign_dir.mkdir(parents=True)
        (foreign_dir / "SKILL.md").write_text("# Foreign skill\n")

        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        assert (foreign_dir / "SKILL.md").exists(), "Foreign skill was removed"

    # -- Scripts ----------------------------------------------------------

    def test_setup_installs_update_context_scripts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
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
        skills_dir = i.skills_dest(project)
        assert skills_dir.is_dir(), f"--ai {self.KEY} did not create skills directory"
        for skill_name in self._passive_skill_names():
            assert (skills_dir / skill_name / "SKILL.md").exists(), (
                f"--ai {self.KEY} did not install passive skill {skill_name}"
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
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        assert (project / self.CONTEXT_FILE).is_file(), (
            f"--ai {self.KEY} did not create context file {self.CONTEXT_FILE}"
        )

    def test_init_bootstrapped_context_file_contains_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"context-guidance-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        content = (project / self.CONTEXT_FILE).read_text(encoding="utf-8")
        assert "## Active Technologies" in content
        assert SPEC_KIT_BLOCK_START in content
        assert "[AGENT]" in content
        assert "specify -> plan" in content
        assert "PROJECT-HANDBOOK.md" in content
        assert ".specify/project-map/" in content
        assert ".specify/memory/project-rules.md" in content
        assert "## Workflow Routing" in content
        assert "sp-fast" in content
        assert "sp-quick" in content
        assert "sp-specify" in content
        assert "sp-debug" in content
        assert "sp-test" in content
        assert "## Artifact Priority" in content
        assert "workflow-state.md" in content
        assert "alignment.md" in content
        assert "context.md" in content
        assert "plan.md" in content
        assert "tasks.md" in content
        assert ".specify/testing/TESTING_CONTRACT.md" in content
        assert ".specify/project-map/status.json" in content
        assert "## Map Maintenance" in content
        assert "refresh `PROJECT-HANDBOOK.md`" in content
        assert "mark `.specify/project-map/status.json` dirty" in content

    def test_init_augments_existing_context_file_with_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"context-existing-{self.KEY}"
        project.mkdir()
        context_path = project / self.CONTEXT_FILE
        context_path.parent.mkdir(parents=True, exist_ok=True)
        initial = "# User Context\n\nKeep this line.\n"
        context_path.write_text(initial, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        content = context_path.read_text(encoding="utf-8")
        assert content.startswith(initial)
        assert SPEC_KIT_BLOCK_START in content
        assert "PROJECT-HANDBOOK.md" in content
        assert ".specify/project-map/" in content
        assert "## Workflow Routing" in content
        assert "## Artifact Priority" in content
        assert "## Map Maintenance" in content

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
        skills_dir = i.skills_dest(project)
        assert skills_dir.is_dir(), f"Skills directory {skills_dir} not created"
        for skill_name in self._passive_skill_names():
            assert (skills_dir / skill_name / "SKILL.md").exists(), (
                f"--integration {self.KEY} did not install passive skill {skill_name}"
            )

    # -- IntegrationOption ------------------------------------------------

    def test_options_include_skills_flag(self):
        i = get_integration(self.KEY)
        opts = i.options()
        skills_opts = [o for o in opts if o.name == "--skills"]
        assert len(skills_opts) == 1
        assert skills_opts[0].is_flag is True

    # -- Complete file inventory ------------------------------------------

    def _skill_commands(self) -> list[str]:
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
            if path.is_file()
            and path.name != "vscode-settings.json"
        )

    def _passive_skill_names(self) -> list[str]:
        i = get_integration(self.KEY)
        passive_dir = i.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []

        return sorted(
            path.name
            for path in passive_dir.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )

    def _passive_skill_files(self) -> list[str]:
        i = get_integration(self.KEY)
        passive_dir = i.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []

        return sorted(
            path.relative_to(passive_dir).as_posix()
            for path in passive_dir.rglob("*")
            if path.is_file()
        )

    def _expected_files(self, script_variant: str) -> list[str]:
        """Build the full expected file list for a given script variant."""
        i = get_integration(self.KEY)
        skills_prefix = i.config["folder"].rstrip("/") + "/" + i.config.get("commands_subdir", "skills")

        files = []
        # Skill files
        for cmd in self._skill_commands():
            files.append(f"{skills_prefix}/sp-{cmd}/SKILL.md")
        for relative_file in self._passive_skill_files():
            files.append(f"{skills_prefix}/{relative_file}")
        files.append(self.CONTEXT_FILE)
        # Integration metadata
        files += [
            ".specify/init-options.json",
            ".specify/integration.json",
            f".specify/integrations/{self.KEY}.manifest.json",
            f".specify/integrations/{self.KEY}/scripts/update-context.ps1",
            f".specify/integrations/{self.KEY}/scripts/update-context.sh",
            ".specify/integrations/speckit.manifest.json",
            ".specify/memory/constitution.md",
            ".specify/memory/project-learnings.md",
            ".specify/memory/project-rules.md",
            ".specify/project-map/status.json",
        ]
        # Script variant
        if script_variant == "sh":
            files += [
                ".specify/scripts/bash/check-prerequisites.sh",
                ".specify/scripts/bash/common.sh",
                ".specify/scripts/bash/create-new-feature.sh",
                ".specify/scripts/bash/project-map-freshness.sh",
                ".specify/scripts/bash/quick-state.sh",
                ".specify/scripts/bash/sync-ecc-to-codex.sh",
                ".specify/scripts/bash/setup-plan.sh",
                ".specify/scripts/bash/update-agent-context.sh",
            ]
        else:
            files += [
                ".specify/scripts/powershell/check-prerequisites.ps1",
                ".specify/scripts/powershell/common.ps1",
                ".specify/scripts/powershell/create-new-feature.ps1",
                ".specify/scripts/powershell/project-map-freshness.ps1",
                ".specify/scripts/powershell/quick-state.ps1",
                ".specify/scripts/powershell/sync-ecc-to-codex.ps1",
                ".specify/scripts/powershell/setup-plan.ps1",
                ".specify/scripts/powershell/update-agent-context.ps1",
            ]
        # Templates
        files += [f".specify/templates/{name}" for name in self._template_files()]
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
                "init", "--here", "--integration", self.KEY,
                "--script", "sh", "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        actual = sorted(
            p.relative_to(project).as_posix()
            for p in project.rglob("*") if p.is_file()
        )
        expected = self._expected_files("sh")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
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
                "init", "--here", "--integration", self.KEY,
                "--script", "ps", "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        actual = sorted(
            p.relative_to(project).as_posix()
            for p in project.rglob("*") if p.is_file()
        )
        expected = self._expected_files("ps")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )
