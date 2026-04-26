"""Tests for ClaudeIntegration."""

import json
import os
from unittest.mock import patch
from pathlib import Path

import yaml

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import IntegrationBase
from specify_cli.integrations.claude import ARGUMENT_HINTS
from specify_cli.integrations.manifest import IntegrationManifest

SPEC_KIT_BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"


class TestClaudeIntegration:
    def test_registered(self):
        assert "claude" in INTEGRATION_REGISTRY
        assert get_integration("claude") is not None

    def test_is_base_integration(self):
        assert isinstance(get_integration("claude"), IntegrationBase)

    def test_config_uses_skills(self):
        integration = get_integration("claude")
        assert integration.config["folder"] == ".claude/"
        assert integration.config["commands_subdir"] == "skills"

    def test_registrar_config_uses_skill_layout(self):
        integration = get_integration("claude")
        assert integration.registrar_config["dir"] == ".claude/skills"
        assert integration.registrar_config["format"] == "markdown"
        assert integration.registrar_config["args"] == "$ARGUMENTS"
        assert integration.registrar_config["extension"] == "/SKILL.md"

    def test_context_file(self):
        integration = get_integration("claude")
        assert integration.context_file == "CLAUDE.md"

    def test_setup_creates_skill_files(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        skill_files = [path for path in created if path.name == "SKILL.md"]
        assert skill_files

        skills_dir = tmp_path / ".claude" / "skills"
        assert skills_dir.is_dir()

        plan_skill = skills_dir / "sp-plan" / "SKILL.md"
        assert plan_skill.exists()

        content = plan_skill.read_text(encoding="utf-8")
        assert "{SCRIPT}" not in content
        assert "{ARGS}" not in content
        assert "__AGENT__" not in content

        parts = content.split("---", 2)
        parsed = yaml.safe_load(parts[1])
        assert parsed["name"] == "sp-plan"
        assert parsed["user-invocable"] is True
        assert parsed["disable-model-invocation"] is True
        assert parsed["metadata"]["source"] == "templates/commands/plan.md"
        assert (skills_dir / "sp-implement-teams" / "SKILL.md").exists()

    def test_setup_keeps_passive_skills_model_invokable(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        passive_skill = tmp_path / ".claude" / "skills" / "spec-kit-workflow-routing" / "SKILL.md"
        assert passive_skill.exists()

        content = passive_skill.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        parsed = yaml.safe_load(parts[1])

        assert parsed["name"] == "spec-kit-workflow-routing"
        assert "user-invocable" not in parsed
        assert "disable-model-invocation" not in parsed
        assert parsed["metadata"]["source"] == "templates/passive-skills/spec-kit-workflow-routing/SKILL.md"

    def test_setup_installs_update_context_scripts(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        scripts_dir = tmp_path / ".specify" / "integrations" / "claude" / "scripts"
        assert scripts_dir.is_dir()
        assert (scripts_dir / "update-context.sh").exists()
        assert (scripts_dir / "update-context.ps1").exists()

        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".specify/integrations/claude/scripts/update-context.sh" in tracked
        assert ".specify/integrations/claude/scripts/update-context.ps1" in tracked

    def test_ai_flag_auto_promotes_and_enables_skills(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-promote"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
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
        assert (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (project / ".claude" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()
        assert (project / ".claude" / "skills" / "spec-kit-project-map-gate" / "SKILL.md").exists()
        assert not (project / ".claude" / "commands").exists()

        init_options = json.loads(
            (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
        )
        assert init_options["ai"] == "claude"
        assert init_options["ai_skills"] is True
        assert init_options["integration"] == "claude"

    def test_init_bootstraps_context_file(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-context"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
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
        assert (project / "CLAUDE.md").is_file()

    def test_init_bootstrapped_context_file_contains_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-context-guidance"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
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
        content = (project / "CLAUDE.md").read_text(encoding="utf-8")
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

        project = tmp_path / "claude-context-existing"
        project.mkdir()
        claude_file = project / "CLAUDE.md"
        initial = "# User CLAUDE\n\nCustom note.\n"
        claude_file.write_text(initial, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--force",
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
        content = claude_file.read_text(encoding="utf-8")
        assert content.startswith(initial)
        assert SPEC_KIT_BLOCK_START in content
        assert "PROJECT-HANDBOOK.md" in content
        assert ".specify/project-map/" in content
        assert "## Workflow Routing" in content
        assert "## Artifact Priority" in content
        assert "## Map Maintenance" in content

    def test_integration_flag_creates_skill_files(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-integration"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--integration",
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
        assert (project / ".claude" / "skills" / "sp-specify" / "SKILL.md").exists()
        assert (project / ".specify" / "integrations" / "claude.manifest.json").exists()

    def test_interactive_claude_selection_uses_integration_path(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-interactive"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            with patch("specify_cli.select_with_arrows", return_value="claude"):
                result = runner.invoke(
                    app,
                    [
                        "init",
                        "--here",
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
        assert (project / ".specify" / "integration.json").exists()
        assert (project / ".specify" / "integrations" / "claude.manifest.json").exists()

        skill_file = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        assert skill_file.exists()
        skill_content = skill_file.read_text(encoding="utf-8")
        assert "user-invocable: true" in skill_content
        assert "disable-model-invocation: true" in skill_content

        init_options = json.loads(
            (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
        )
        assert init_options["ai"] == "claude"
        assert init_options["ai_skills"] is True
        assert init_options["integration"] == "claude"

    def test_claude_init_remains_usable_when_converter_fails(self, tmp_path):
        """Claude init should succeed even without install_ai_skills."""
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "fail-proj"

        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "claude", "--script", "sh", "--no-git", "--ignore-agent-tools"],
        )

        assert result.exit_code == 0
        assert (target / ".claude" / "skills" / "sp-specify" / "SKILL.md").exists()

    def test_claude_hooks_render_skill_invocation(self, tmp_path):
        from specify_cli.extensions import HookExecutor

        project = tmp_path / "claude-hooks"
        project.mkdir()
        init_options = project / ".specify" / "init-options.json"
        init_options.parent.mkdir(parents=True, exist_ok=True)
        init_options.write_text(json.dumps({"ai": "claude", "ai_skills": True}))

        hook_executor = HookExecutor(project)
        message = hook_executor.format_hook_message(
            "before_plan",
            [
                {
                    "extension": "test-ext",
                    "command": "sp.plan",
                    "optional": False,
                }
            ],
        )

        assert "Executing: `/sp-plan`" in message
        assert "EXECUTE_COMMAND: sp.plan" in message
        assert "EXECUTE_COMMAND_INVOCATION: /sp-plan" in message

    def test_claude_preset_creates_new_skill_without_commands_dir(self, tmp_path):
        from specify_cli import save_init_options
        from specify_cli.presets import PresetManager

        project = tmp_path / "claude-preset-skill"
        project.mkdir()
        save_init_options(project, {"ai": "claude", "ai_skills": True, "script": "sh"})

        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        preset_dir = tmp_path / "claude-skill-command"
        preset_dir.mkdir()
        (preset_dir / "commands").mkdir()
        (preset_dir / "commands" / "sp.research.md").write_text(
            "---\n"
            "description: Research workflow\n"
            "---\n\n"
            "preset:claude-skill-command\n"
        )
        manifest_data = {
            "schema_version": "1.0",
            "preset": {
                "id": "claude-skill-command",
                "name": "Claude Skill Command",
                "version": "1.0.0",
                "description": "Test",
            },
            "requires": {"speckit_version": ">=0.1.0"},
            "provides": {
                "templates": [
                    {
                        "type": "command",
                        "name": "sp.research",
                        "file": "commands/sp.research.md",
                    }
                ]
            },
        }
        with open(preset_dir / "preset.yml", "w") as f:
            yaml.dump(manifest_data, f)

        manager = PresetManager(project)
        manager.install_from_directory(preset_dir, "0.1.5")

        skill_file = skills_dir / "sp-research" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "preset:claude-skill-command" in content
        assert "name: sp-research" in content
        assert "user-invocable: true" in content
        assert "disable-model-invocation: true" in content

        metadata = manager.registry.get("claude-skill-command")
        assert "sp-research" in metadata.get("registered_skills", [])


class TestClaudeArgumentHints:
    """Verify that argument-hint frontmatter is injected for Claude skills."""

    @staticmethod
    def _explicit_skill_files(created):
        return [
            f
            for f in created
            if f.name == "SKILL.md" and f.parent.name.startswith("sp-")
        ]

    def test_all_skills_have_hints(self, tmp_path):
        """Every explicit Claude workflow skill must contain an argument-hint line."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        assert len(skill_files) > 0
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            assert "argument-hint:" in content, (
                f"{f.parent.name}/SKILL.md is missing argument-hint frontmatter"
            )

    def test_hints_match_expected_values(self, tmp_path):
        """Each skill's argument-hint must match the expected text."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        for f in skill_files:
            stem = f.parent.name
            if stem.startswith("sp-"):
                stem = stem[len("sp-"):]
            expected_hint = ARGUMENT_HINTS.get(stem)
            assert expected_hint is not None, (
                f"No expected hint defined for skill '{stem}'"
            )
            content = f.read_text(encoding="utf-8")
            assert f'argument-hint: "{expected_hint}"' in content, (
                f"{f.parent.name}/SKILL.md: expected hint '{expected_hint}' not found"
            )

    def test_hint_is_inside_frontmatter(self, tmp_path):
        """argument-hint must appear between the --- delimiters, not in the body."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            assert len(parts) >= 3, f"No frontmatter in {f.parent.name}/SKILL.md"
            frontmatter = parts[1]
            body = parts[2]
            assert "argument-hint:" in frontmatter, (
                f"{f.parent.name}/SKILL.md: argument-hint not in frontmatter section"
            )
            assert "argument-hint:" not in body, (
                f"{f.parent.name}/SKILL.md: argument-hint leaked into body"
            )

    def test_hint_appears_after_description(self, tmp_path):
        """argument-hint must immediately follow the description line."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            found_description = False
            for idx, line in enumerate(lines):
                if line.startswith("description:"):
                    found_description = True
                    assert idx + 1 < len(lines), (
                        f"{f.parent.name}/SKILL.md: description is last line"
                    )
                    assert lines[idx + 1].startswith("argument-hint:"), (
                        f"{f.parent.name}/SKILL.md: argument-hint does not follow description"
                    )
                    break
            assert found_description, (
                f"{f.parent.name}/SKILL.md: no description: line found in output"
            )

    def test_inject_argument_hint_only_in_frontmatter(self):
        """inject_argument_hint must not modify description: lines in the body."""
        from specify_cli.integrations.claude import ClaudeIntegration

        content = (
            "---\n"
            "description: My command\n"
            "---\n"
            "\n"
            "description: this is body text\n"
        )
        result = ClaudeIntegration.inject_argument_hint(content, "Test hint")
        lines = result.splitlines()
        hint_count = sum(1 for ln in lines if ln.startswith("argument-hint:"))
        assert hint_count == 1, (
            f"Expected exactly 1 argument-hint line, found {hint_count}"
        )

    def test_inject_argument_hint_skips_if_already_present(self):
        """inject_argument_hint must not duplicate if argument-hint already exists."""
        from specify_cli.integrations.claude import ClaudeIntegration

        content = (
            "---\n"
            "description: My command\n"
            'argument-hint: "Existing hint"\n'
            "---\n"
            "\n"
            "Body text\n"
        )
        result = ClaudeIntegration.inject_argument_hint(content, "New hint")
        assert result == content, "Content should be unchanged when hint already exists"
        lines = result.splitlines()
        hint_count = sum(1 for ln in lines if ln.startswith("argument-hint:"))
        assert hint_count == 1


def test_claude_generated_runtime_facing_skills_include_native_delegation_contract(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-delegation-contract"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    skills_dir = target / ".claude" / "skills"
    for skill_name in ("sp-implement", "sp-debug", "sp-quick"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "delegation surface contract" in content
        assert "native dispatch surface" in content
        assert "result contract" in content
        assert "result handoff path" in content
        assert "wait for every delegated lane's structured handoff" in content
        assert "do not treat an idle child as done work" in content
        assert "do not interrupt or shut down delegated work before the handoff has been written" in content
        assert "done_with_concerns" in content
        assert "needs_context" in content
        assert "workertaskresult" in content
        assert "spawn_agent" not in content
        assert "specify team" not in content
    implement_content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()
    debug_content = (skills_dir / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
    quick_content = (skills_dir / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "feature_dir/worker-results/<task-id>.json" in implement_content
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in debug_content
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in quick_content


def test_claude_generated_implement_skill_includes_shared_leader_gate(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-implement-leader-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    content = (target / ".claude" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "## claude dispatch-first gate" in content
    assert "attempt delegated execution before leader-local implementation" in content
    assert "treat `single-agent` as one delegated child-worker lane" in content
    assert "if multiple safe worker lanes exist for the current batch, dispatch them in parallel" in content
    assert "do not begin concrete implementation on the leader path while an untried delegated path is available" in content
    assert "only fall back to leader-local execution after recording a concrete fallback reason" in content
    assert "/sp-implement-teams" in content
    assert "## claude code leader gate".lower() in content
    assert "you are the **leader**, not the concrete implementer" in content
    assert "autonomous blocker recovery" in content
    assert "missed_agent_dispatch" in content
    assert "current runtime's native worker lanes" in content
    assert "current integration's coordinated runtime surface" in content


def test_claude_generated_sp_implement_description_prefers_worker_dispatch(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-implement-description"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    content = (target / ".claude" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")
    parts = content.split("---", 2)
    parsed = yaml.safe_load(parts[1])

    assert parsed["description"] == (
        "Execute the implementation plan by dispatching tasks to worker agents and integrating their results"
    )


def test_claude_generated_sp_implement_teams_skill_uses_agent_teams_surface(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-implement-teams"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    skill_path = target / ".claude" / "skills" / "sp-implement-teams" / "SKILL.md"
    assert skill_path.exists()

    content = skill_path.read_text(encoding="utf-8")
    lower = content.lower()
    assert "claude code agent teams" in lower
    assert "teamcreate" in lower
    assert "taskcreate" in lower
    assert "taskupdate" in lower
    assert "sendmessage" in lower
    assert "tasklist" in lower
    assert "taskget" in lower
    assert "teamdelete" in lower
    assert "~/.claude/teams/" in content
    assert "~/.claude/tasks/" in content
    assert "claude_code_experimental_agent_teams=1" in lower
    assert "if the agent teams surface is unavailable" in lower
    assert "first `teamcreate` / agent teams call fails as though the feature is disabled" in lower
    assert "explicitly remind the user to enable `claude_code_experimental_agent_teams`" in lower
    assert "hard prerequisite for `/sp-implement-teams`" in lower
    assert "resolve the current session model before teammate creation" in lower
    assert "inspect the environment variable `anthropic_model`" in lower
    assert "do not fallback to `claude_model`, `~/.claude/settings.json`, or any other local file" in lower
    assert "resolved `anthropic_model` string" in lower
    assert "cannot be resolved unambiguously" in lower
    assert "routing alias" in lower
    assert "for example `anthropic_model=group`" in lower
    assert "does not prove the active session model" in lower
    assert "ask the user for an explicit teammate model" in lower
    assert "create or update local `.claude/agents/<team-name>-<role>.md` files" in lower
    assert 'write the resolved current-session model into the teammate frontmatter as `model: "<resolved-current-model>"`' in lower
    assert "update its `model` field for the current run" in lower
    assert ".claude/agents/*.md" in content
    assert "generated teammate definition name" in lower
    assert "inspect `~/.claude/teams/{team-name}/config.json` after teammate creation" in lower
    assert "recorded `model`" in content
    assert "if the runtime cannot use the generated custom teammate definition" in lower
    assert "`model not found`" in content
    assert "enters `idle` without consuming its first probe message" in lower
    assert "treat startup as failed rather than successful" in lower
    assert "minimal readiness probe message before task assignment" in lower
    assert "shared contract with `/sp-implement`" in lower
    assert "canonical implementation workflow" in lower
    assert "implement-tracker.md" in lower
    assert "workertaskpacket" in lower
    assert "single-agent" in lower
    assert "native-multi-agent" in lower
    assert "sidecar-runtime" in lower
    assert "join point" in lower
    assert "worker-results" in lower
    assert "worker result contract" in lower
    assert "result file handoff path" in lower
    assert "feature_dir/worker-results/<task-id>.json" in lower
    assert "specify team" not in lower
    assert "sp.agent-teams.run" not in lower
    assert "specify extension add agent-teams" not in lower
    assert "tmux" not in lower


def test_claude_implement_teams_template_keeps_only_backend_specific_guidance():
    template = Path(
        "src/specify_cli/integrations/claude/templates/implement-teams.md"
    ).read_text(encoding="utf-8")
    lower = template.lower()

    assert "## Shared Contract With `/sp-implement`" not in template
    assert ".claude/agents/<team-name>-<role>.md" in template
    assert 'model: "<resolved-current-model>"' in template
    assert "claude_code_experimental_agent_teams" in lower
    assert "for example `anthropic_model=group`" in lower
    assert "hard prerequisite" in lower
    assert "config.json" in template
    assert "idle" in lower


def test_claude_generated_skills_preserve_agent_required_marker_lines(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-agent-marker"
    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, result.output

    for skill_name in ("sp-fast", "sp-quick", "sp-map-codebase", "sp-implement", "sp-specify", "sp-plan", "sp-tasks", "sp-debug"):
        content = (target / ".claude" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[AGENT]" in content


def test_claude_question_driven_skills_prefer_ask_user_question_with_fallback(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    for skill_name in ("sp-specify", "sp-spec-extend", "sp-checklist", "sp-quick"):
        content = (target / ".claude" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "AskUserQuestion" in content
        assert "`question`" in content
        assert "`header`" in content
        assert "`multiSelect`" in content
        assert "fallback-only guidance" in lower
        assert "must use it" in lower
        assert "do not render the textual fallback block" in lower
        assert "do not self-authorize textual fallback" in lower
        assert "active question exactly once" in lower
        assert (
            "fall back to the" in lower
            or "plain-text confirmation question" in lower
            or "textual question format" in lower
            or "plain-text clarification" in lower
        )

    specify_content = (target / ".claude" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")
    assert "If the runtime's native structured question tool is available for the current turn, you must use it." in specify_content
    assert "Treat the shared open question block structure below as fallback-only text format guidance" in specify_content
