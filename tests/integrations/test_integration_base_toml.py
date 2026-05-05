"""Reusable test mixin for standard TomlIntegration subclasses.

Each per-agent test file sets ``KEY``, ``FOLDER``, ``COMMANDS_SUBDIR``,
``REGISTRAR_DIR``, and ``CONTEXT_FILE``, then inherits all verification
logic from ``TomlIntegrationTests``.

Mirrors ``MarkdownIntegrationTests`` closely — same test structure,
adapted for TOML output format.
"""

import os
import re
import tomllib

import pytest

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import TomlIntegration
from specify_cli.integrations.manifest import IntegrationManifest

SPEC_KIT_BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"
SHARED_PRD_HELPER = ".specify/scripts/shared/prd-state.py"


def _assert_downstream_testing_control_plane(command_content: str) -> None:
    command_lower = command_content.lower()

    assert "preserve each lane's canonical `validation_command`" in command_lower
    assert "`validation_command` remains the lane acceptance command" in command_lower
    assert "do not replace it with a command-tier map" in command_lower
    assert "lane's `focused` command should mirror the canonical `validation_command`" in command_lower
    assert "focused` command should mirror the canonical `validation_command`" in command_lower
    assert "unless the build plan records an explicit exception" in command_lower

    assert "validation_command` remains the lane acceptance command" in command_lower
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in command_lower
    assert "including when each tier should be run" in command_lower
    assert re.search(
        r"command-tier expectations for `fast smoke`, `focused`, and `full`,"
        r" including when each tier should be run.*coverage commands.*ci commands",
        command_lower,
        re.S,
    )
    assert "successful manual validation evidence" in command_lower
    assert re.search(
        r"`full`[^.\n]*(broader regression|final verification|final or regression-sensitive)",
        command_lower,
    )
    for forbidden_full_acceptance in (
        "`full` remains the lane acceptance command",
        "`full` is the lane acceptance command",
        "`full` command is the lane acceptance command",
    ):
        assert forbidden_full_acceptance not in command_lower
    assert "ci/presubmit gate policy" in command_lower

    assert "covered-module rules" in command_lower
    assert "mandatory testing rules for future work" in command_lower
    assert "coverage baseline and threshold policy" in command_lower
    assert "covered-module status values and the minimum evidence required" in command_lower


class TomlIntegrationTests:
    """Mixin — set class-level constants and inherit these tests.

    Required class attrs on subclass::

        KEY: str              — integration registry key
        FOLDER: str           — e.g. ".gemini/"
        COMMANDS_SUBDIR: str  — e.g. "commands"
        REGISTRAR_DIR: str    — e.g. ".gemini/commands"
        CONTEXT_FILE: str     — e.g. "GEMINI.md"
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

    def test_is_toml_integration(self):
        assert isinstance(get_integration(self.KEY), TomlIntegration)

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
        assert i.registrar_config["format"] == "toml"
        assert i.registrar_config["args"] == "{{args}}"
        assert i.registrar_config["extension"] == ".toml"

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
            assert f.name.endswith(".toml")

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
        """Command files must have placeholders replaced and be valid TOML."""
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

    def test_feature_creation_surfaces_use_explicit_helper_paths_without_fake_cli(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        surfaces = [i.commands_dest(tmp_path) / i.command_filename("specify")]

        context_path = tmp_path / self.CONTEXT_FILE
        if context_path.exists():
            surfaces.append(context_path)

        routing_toml = i.commands_dest(tmp_path) / i.command_filename("spec-kit-workflow-routing")
        if routing_toml.exists():
            surfaces.append(routing_toml)

        for path in surfaces:
            content = path.read_text(encoding="utf-8").lower()
            assert ".specify/scripts/bash/create-new-feature.sh" in content, f"{path} missing bash helper path"
            assert ".specify/scripts/powershell/create-new-feature.ps1" in content, f"{path} missing powershell helper path"
            assert "run `specify create-feature`" not in content, f"{path} teaches fake runnable create-feature command"
            assert "use `specify create-feature`" not in content, f"{path} teaches fake runnable create-feature command"

    def test_toml_has_description(self, tmp_path):
        """Every TOML command file should have a description key."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        cmd_files = [f for f in created if "scripts" not in f.parts]
        for f in cmd_files:
            content = f.read_text(encoding="utf-8")
            assert 'description = "' in content, f"{f.name} missing description key"

    def test_toml_has_prompt(self, tmp_path):
        """Every TOML command file should have a prompt key."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        cmd_files = [f for f in created if "scripts" not in f.parts]
        for f in cmd_files:
            content = f.read_text(encoding="utf-8")
            assert "prompt = " in content, f"{f.name} missing prompt key"

    def test_toml_uses_correct_arg_placeholder(self, tmp_path):
        """TOML commands must use {{args}} (from {ARGS} replacement)."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        cmd_files = [f for f in created if "scripts" not in f.parts]
        # At least one file should contain {{args}} from the {ARGS} placeholder
        has_args = any("{{args}}" in f.read_text(encoding="utf-8") for f in cmd_files)
        assert has_args, "No TOML command file contains {{args}} placeholder"

    def test_research_alias_command_routes_to_deep_research(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        alias_path = i.commands_dest(tmp_path) / i.command_filename("research")
        assert alias_path.exists()
        content = alias_path.read_text(encoding="utf-8")
        parsed = tomllib.loads(content)
        prompt = parsed["prompt"]
        lowered = prompt.lower()

        assert "compatibility alias" in lowered
        assert "sp-deep-research" in prompt
        assert "active_command: sp-deep-research" in prompt
        assert "active_command: sp-research" not in prompt

    def test_integrate_command_is_generated(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        integrate_path = i.commands_dest(tmp_path) / i.command_filename("integrate")
        assert integrate_path.exists()
        content = integrate_path.read_text(encoding="utf-8").lower()
        assert "closeout" in content or "close out" in content
        assert "do not fold this workflow into `sp-implement`" in content

    def test_runtime_commands_hard_gate_project_map_reads(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        runtime_files = {
            f"sp.{stem}.toml"
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
            assert "atlas.entry" in content
            assert "atlas.index.status" in content
            assert "atlas.index.atlas" in content
            assert "map-scan" in content
            assert "map-build" in content

    def test_map_scan_build_commands_require_native_explorer_lanes_when_selected(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        commands_dir = i.commands_dest(tmp_path)
        assert not (commands_dir / "sp.map-codebase.toml").exists()

        scan_content = (commands_dir / "sp.map-scan.toml").read_text(encoding="utf-8").lower()
        build_content = (commands_dir / "sp.map-build.toml").read_text(encoding="utf-8").lower()
        assert "choose_subagent_dispatch(command_name=" in scan_content
        assert "map-scan" in scan_content
        assert "choose_subagent_dispatch(command_name=" in build_content
        assert "map-build" in build_content
        assert "execution_model: subagent-mandatory" in scan_content or "execution model: `subagents-first`" in scan_content
        assert "execution_model: subagent-mandatory" in build_content or "execution model: `subagents-first`" in build_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in scan_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in build_content
        assert "execution_surface: native-subagents" in scan_content
        assert "execution_surface: native-subagents" in build_content
        assert "coverage-ledger" in scan_content
        assert "map-state.md" in scan_content
        assert "mapscanpacket" in scan_content
        assert "mapbuildpacket" in build_content
        assert "worker-results" in build_content
        assert "route back to `/sp-map-scan`" in build_content

    def test_test_build_command_surfaces_downstream_testing_control_plane(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        command_content = (i.commands_dest(tmp_path) / "sp.test-build.toml").read_text(encoding="utf-8")
        _assert_downstream_testing_control_plane(command_content)

    def test_implement_command_has_shared_leader_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        implement_path = i.commands_dest(tmp_path) / "sp.implement.toml"
        content = implement_path.read_text(encoding="utf-8")
        lowered = content.lower()
        agent_name = i.config["name"].replace(" CLI", "")

        assert f"## {agent_name} Leader Gate" in content or "## Orchestration Model" in content
        assert "you are the **leader**, not the concrete implementer" in lowered or "leader and orchestrator" in lowered
        assert "autonomous blocker recovery" in lowered
        assert "Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready" in content
        assert "dispatch `parallel-subagents` when multiple validated packets have isolated write sets" in content
        assert "delegation surface contract" in lowered
        assert "leader-inline-fallback" in lowered
        assert "dispatch only from validated `workertaskpacket`" in lowered
        assert "must not edit implementation files directly while subagent execution is active" in lowered

    def test_runtime_commands_have_shared_subagent_dispatch_and_result_contracts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        for name in ("implement", "debug", "quick"):
            content = (i.commands_dest(tmp_path) / f"sp.{name}.toml").read_text(encoding="utf-8").lower()
            assert "subagent dispatch contract" in content
            assert "subagent dispatch" in content
            assert "fallback path" in content
            assert "subagent result contract" in content
            assert "result handoff path" in content
            assert "reported_status" in content
            assert "needs_context" in content

    def test_debug_and_quick_commands_have_shared_leader_and_routing_sections(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "")

        debug_content = (i.commands_dest(tmp_path) / "sp.debug.toml").read_text(encoding="utf-8").lower()
        quick_content = (i.commands_dest(tmp_path) / "sp.quick.toml").read_text(encoding="utf-8").lower()

        assert f"## {agent_name} Leader Gate".lower() in debug_content
        assert "you are the **leader**, not a freeform debugger" in debug_content
        assert "investigation routing contract" in debug_content
        assert "execution_model: subagent-mandatory" in debug_content or "execution model: `subagents-first`" in debug_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in debug_content
        assert "execution_surface: native-subagents" in debug_content or "execution surface: `native-subagents`" in debug_content

        assert f"## {agent_name} Leader Gate".lower() in quick_content
        assert "you are the **leader**, not the concrete implementer" in quick_content
        assert "quick execution routing" in quick_content
        assert "execution_model: subagent-mandatory" in quick_content or "execution model: `subagents-first`" in quick_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in quick_content
        assert "execution_surface: native-subagents" in quick_content
        assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in quick_content

    def test_question_driven_commands_define_native_tool_preference_with_fallback(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "").lower()

        for name in ("specify", "clarify", "deep-research", "checklist", "quick", "debug"):
            content = (i.commands_dest(tmp_path) / f"sp.{name}.toml").read_text(encoding="utf-8").lower()
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
                or "research-track decision" in content
            )
            assert "active question exactly once" in content

    @pytest.mark.parametrize(
        ("frontmatter", "expected"),
        [
            (
                "---\ndescription: |\n  First line\n  Second line\n---\nBody\n",
                "First line\nSecond line\n",
            ),
            (
                "---\ndescription: >\n  First line\n  Second line\n---\nBody\n",
                "First line Second line\n",
            ),
            (
                "---\ndescription: |-\n  First line\n  Second line\n---\nBody\n",
                "First line\nSecond line",
            ),
            (
                "---\ndescription: >-\n  First line\n  Second line\n---\nBody\n",
                "First line Second line",
            ),
        ],
    )
    def test_toml_extract_description_supports_block_scalars(self, frontmatter, expected):
        assert TomlIntegration._extract_description(frontmatter) == expected

    def test_split_frontmatter_ignores_indented_delimiters(self):
        content = (
            "---\n"
            "description: |\n"
            "  line one\n"
            "  ---\n"
            "  line two\n"
            "---\n"
            "Body\n"
        )

        frontmatter, body = TomlIntegration._split_frontmatter(content)

        assert "line two" in frontmatter
        assert body == "Body\n"

    def test_toml_prompt_excludes_frontmatter(self, tmp_path, monkeypatch):
        i = get_integration(self.KEY)
        template = tmp_path / "sample.md"
        template.write_text(
            "---\n"
            "description: Summary line one\n"
            "scripts:\n"
            "  sh: scripts/bash/example.sh\n"
            "---\n"
            "Body line one\n"
            "Body line two\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(i, "list_command_templates", lambda: [template])

        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        cmd_files = [f for f in created if "scripts" not in f.parts]
        assert len(cmd_files) == 1

        generated = cmd_files[0].read_text(encoding="utf-8")
        parsed = tomllib.loads(generated)

        assert parsed["description"] == "Summary line one"
        assert parsed["prompt"] == "Body line one\nBody line two"
        assert "description:" not in parsed["prompt"]
        assert "scripts:" not in parsed["prompt"]
        assert "---" not in parsed["prompt"]

    def test_toml_is_valid(self, tmp_path):
        """Every generated TOML file must parse without errors."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        cmd_files = [f for f in created if "scripts" not in f.parts]
        for f in cmd_files:
            raw = f.read_bytes()
            try:
                parsed = tomllib.loads(raw.decode("utf-8"))
            except Exception as exc:
                raise AssertionError(f"{f.name} is not valid TOML: {exc}") from exc
            assert "prompt" in parsed, f"{f.name} parsed TOML has no 'prompt' key"

    def test_multiline_prompt_closes_on_own_line_when_body_ends_with_quote(self, tmp_path):
        i = get_integration(self.KEY)
        template = tmp_path / "sample.md"
        template.write_text(
            "---\n"
            "description: Summary line one\n"
            "---\n"
            "Body line one\n"
            'Body ends with "\n',
            encoding="utf-8",
        )
        original_templates = i.list_command_templates
        try:
            i.list_command_templates = lambda: [template]
            m = IntegrationManifest(self.KEY, tmp_path)
            created = i.setup(tmp_path, m)
        finally:
            i.list_command_templates = original_templates

        cmd_files = [f for f in created if "scripts" not in f.parts]
        assert len(cmd_files) == 1

        generated = cmd_files[0].read_text(encoding="utf-8")
        parsed = tomllib.loads(generated)

        assert parsed["prompt"] == 'Body line one\nBody ends with "'
        assert 'Body ends with """"' not in generated
        assert generated.splitlines()[-1] == '"""'

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
        commands = sorted(cmd_dir.glob("sp.*.toml"))
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

        # Command files (.toml)
        for stem in self._command_stems():
            files.append(f"{cmd_dir}/sp.{stem}.toml")

        # Integration scripts
        files.append(f".specify/integrations/{self.KEY}/scripts/update-context.ps1")
        files.append(f".specify/integrations/{self.KEY}/scripts/update-context.sh")
        files.append(self.CONTEXT_FILE)

        # Framework files
        files.append(".specify/integration.json")
        files.append(".specify/init-options.json")
        files.append(f".specify/integrations/{self.KEY}.manifest.json")
        files.append(".specify/integrations/speckit.manifest.json")

        if script_variant == "sh":
            for name in ["check-prerequisites.sh", "common.sh", "create-new-feature.sh",
                         "prd-state.sh", "project-map-freshness.sh", "quick-state.sh", "setup-plan.sh", "sync-ecc-to-codex.sh", "update-agent-context.sh"]:
                files.append(f".specify/scripts/bash/{name}")
        else:
            for name in ["check-prerequisites.ps1", "common.ps1", "create-new-feature.ps1",
                         "prd-state.ps1", "project-map-freshness.ps1", "quick-state.ps1", "setup-plan.ps1", "sync-ecc-to-codex.ps1", "update-agent-context.ps1"]:
                files.append(f".specify/scripts/powershell/{name}")
        files.append(SHARED_PRD_HELPER)

        for name in self._template_files():
            files.append(f".specify/templates/{name}")

        files.append(".specify/memory/constitution.md")
        files.append(".specify/memory/project-learnings.md")
        files.append(".specify/memory/project-rules.md")
        files.append(".specify/project-map/status.json")
        files.append(".specify/project-map/index/status.json")
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
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh",
                "--no-git", "--ignore-agent-tools",
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
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh",
                "--no-git", "--ignore-agent-tools",
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
        assert "sp-deep-research" in content
        assert "sp-debug" in content
        assert "sp-test-scan" in content
        assert "sp-test-build" in content
        assert "## Artifact Priority" in content
        assert "workflow-state.md" in content
        assert "alignment.md" in content
        assert "context.md" in content
        assert "deep-research.md" in content
        assert "plan.md" in content
        assert "tasks.md" in content
        assert ".specify/testing/TESTING_CONTRACT.md" in content
        assert ".specify/project-map/index/status.json" in content
        assert "## Map Maintenance" in content
        assert "refresh `PROJECT-HANDBOOK.md`" in content
        assert "git-baseline freshness" in content.lower()
        assert "complete-refresh" in content
        assert "manual override/fallback" in content.lower()

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
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh",
                "--no-git", "--ignore-agent-tools",
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
