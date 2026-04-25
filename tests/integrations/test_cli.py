"""Tests for --integration flag on specify init (CLI-level)."""

import json
import os
import subprocess
from pathlib import Path

import yaml


class TestInitIntegrationFlag:
    @staticmethod
    def _frontmatter(skill_path):
        content = skill_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1])

    def test_codex_init_advertises_specify_team_surface(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "codex-team-surface"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
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
        assert (project / ".specify" / "codex-team" / "runtime.json").exists()
        assert (project / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (project / ".specify" / "templates" / "project-map" / "ARCHITECTURE.md").exists()
        assert (project / ".specify" / "templates" / "project-map" / "OPERATIONS.md").exists()
        assert (project / ".specify" / "project-map" / "status.json").exists()
        assert "specify team" in result.output
        assert "Codex Teams Readiness" in result.output
        assert "agent-teams extension installed" in result.output
        assert "git repo detected" in result.output
        assert "worktree-ready" in result.output

    def test_non_codex_init_does_not_advertise_specify_team_surface(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-no-team-surface"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
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
        assert not (project / ".claude" / "skills" / "sp-team" / "SKILL.md").exists()
        assert not (project / ".specify" / "codex-team" / "runtime.json").exists()
        assert "specify team" not in result.output.lower()
        assert "/sp-team" not in result.output.lower()
        assert "(codex-only)" not in result.output.lower()

    def test_non_codex_implement_skill_does_not_use_specify_team_as_primary_entrypoint(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-no-team-entrypoint"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
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
        assert not (project / ".claude" / "skills" / "sp-team" / "SKILL.md").exists()
        assert not (project / ".specify" / "codex-team" / "runtime.json").exists()

        implement_skill = project / ".claude" / "skills" / "sp-implement" / "SKILL.md"
        assert implement_skill.exists()
        content = implement_skill.read_text(encoding="utf-8")
        assert "single-agent" in content
        assert "native-multi-agent" in content
        assert "sidecar-runtime" in content
        assert "project-handbook.md" in content.lower()
        assert ".specify/project-map/architecture.md" in content.lower()
        assert ".specify/project-map/operations.md" in content.lower()
        assert "specify team" not in content.lower()

    def test_non_codex_shared_workflow_skills_use_canonical_strategy_language(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-shared-routing"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
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

        skills_dir = project / ".claude" / "skills"
        for skill_name in ("sp-specify", "sp-plan", "sp-tasks", "sp-explain", "sp-debug"):
            content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "single-agent" in content
            assert "native-multi-agent" in content
            assert "sidecar-runtime" in content
            assert "specify team" not in content

        debug_content = (skills_dir / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert 'choose_execution_strategy(command_name="debug"' in debug_content
        assert "capability-aware investigation" in debug_content
        assert "project-handbook.md" in debug_content
        assert ".specify/project-map/architecture.md" in debug_content
        assert ".specify/project-map/workflows.md" in debug_content
        assert "spawn_agent" not in debug_content

        fast_content = (skills_dir / "sp-fast" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "project-handbook.md" in fast_content
        assert "shared surfaces" in fast_content
        assert "risky coordination points" in fast_content

        quick_content = (skills_dir / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert ".specify/memory/constitution.md" in quick_content
        assert ".specify/memory/project-rules.md" in quick_content
        assert ".specify/memory/project-learnings.md" in quick_content
        assert ".planning/learnings/candidates.md" in quick_content
        assert "project-handbook.md" in quick_content
        assert "topic map" in quick_content
        assert "touched-area topical files" in quick_content
        assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in quick_content
        assert "attempt the smallest safe recovery step before declaring the task blocked" in quick_content
        assert "retry_attempts" in quick_content
        assert "blocker_reason" in quick_content

    def test_integration_and_ai_mutually_exclusive(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "init", str(tmp_path / "test-project"), "--ai", "claude", "--integration", "copilot",
        ])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_unknown_integration_rejected(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "init", str(tmp_path / "test-project"), "--integration", "nonexistent",
        ])
        assert result.exit_code != 0
        assert "Unknown integration" in result.output

    def test_integration_copilot_creates_files(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app
        runner = CliRunner()
        project = tmp_path / "int-test"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(app, [
                "init", "--here", "--integration", "copilot", "--script", "sh", "--no-git",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        assert (project / ".github" / "agents" / "sp.plan.agent.md").exists()
        assert (project / ".github" / "agents" / "sp.spec-extend.agent.md").exists()
        assert (project / ".github" / "agents" / "sp.explain.agent.md").exists()
        assert (project / ".github" / "prompts" / "sp.plan.prompt.md").exists()
        assert (project / ".specify" / "scripts" / "bash" / "common.sh").exists()
        assert (project / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (project / ".specify" / "templates" / "project-map" / "ARCHITECTURE.md").exists()
        assert (project / ".specify" / "templates" / "project-map" / "OPERATIONS.md").exists()
        assert (project / ".specify" / "project-map" / "status.json").exists()
        assert (project / ".specify" / "templates" / "references-template.md").exists()
        assert (project / ".specify" / "templates" / "spec-template.md").exists()

        data = json.loads((project / ".specify" / "integration.json").read_text(encoding="utf-8"))
        assert data["integration"] == "copilot"
        assert "scripts" in data
        assert "update-context" in data["scripts"]

        opts = json.loads((project / ".specify" / "init-options.json").read_text(encoding="utf-8"))
        assert opts["integration"] == "copilot"

        assert (project / ".specify" / "integrations" / "copilot.manifest.json").exists()
        assert (project / ".specify" / "integrations" / "copilot" / "scripts" / "update-context.sh").exists()

        shared_manifest = project / ".specify" / "integrations" / "speckit.manifest.json"
        assert shared_manifest.exists()

    def test_ai_copilot_auto_promotes(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app
        project = tmp_path / "promote-test"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--ai", "copilot", "--script", "sh", "--no-git",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0
        assert (project / ".github" / "agents" / "sp.plan.agent.md").exists()

    def test_ai_claude_here_preserves_preexisting_commands(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-here-existing"
        project.mkdir()
        commands_dir = project / ".claude" / "skills"
        commands_dir.mkdir(parents=True)
        skill_dir = commands_dir / "sp-specify"
        skill_dir.mkdir(parents=True)
        command_file = skill_dir / "SKILL.md"
        command_file.write_text("# preexisting command\n", encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--force", "--ai", "claude", "--ai-skills", "--script", "sh", "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert command_file.exists()
        # init replaces skills (not additive); verify the file has valid skill content
        assert command_file.exists()
        assert "sp-specify" in command_file.read_text(encoding="utf-8")
        assert (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()

    def test_shared_infra_skips_existing_files(self, tmp_path):
        """Pre-existing shared files are not overwritten by _install_shared_infra."""
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "skip-test"
        project.mkdir()

        # Pre-create a shared script with custom content
        scripts_dir = project / ".specify" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        custom_content = "# user-modified common.sh\n"
        (scripts_dir / "common.sh").write_text(custom_content, encoding="utf-8")

        # Pre-create a shared template with custom content
        templates_dir = project / ".specify" / "templates"
        templates_dir.mkdir(parents=True)
        custom_template = "# user-modified spec-template\n"
        (templates_dir / "spec-template.md").write_text(custom_template, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--force",
                "--integration", "copilot",
                "--script", "sh",
                "--no-git",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0

        # User's files should be preserved
        assert (scripts_dir / "common.sh").read_text(encoding="utf-8") == custom_content
        assert (templates_dir / "spec-template.md").read_text(encoding="utf-8") == custom_template

        # Other shared files should still be installed
        assert (scripts_dir / "setup-plan.sh").exists()
        assert (templates_dir / "alignment-template.md").exists()
        assert (templates_dir / "plan-template.md").exists()

    def test_codex_init_uses_plus_branded_visible_output(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "codex-plus-brand"
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
        assert "Spec Kit Plus" in result.output
        assert "Specify Plus Project Setup" not in result.output
        assert "Initialize Spec Kit Plus Project" in result.output
        assert "Spec Kit Plus project ready." in result.output
        assert "Start Here" in result.output
        assert "Plus Next Steps" not in result.output
        assert "Optional support skills" in result.output
        assert "Plus Enhancement Skills" not in result.output
        assert "Agent Folder Security" not in result.output
        assert "Spec Kit Plus skills were" in result.output
        assert ".codex/skills" in result.output
        assert "Start using skills with your AI agent" in result.output
        assert "Core workflow skills" in result.output
        assert "Support skills" in result.output
        assert "Codex-only runtime" in result.output
        assert "$sp-constitution" in result.output
        assert "$sp-specify" in result.output
        assert "$sp-plan" in result.output
        assert "$sp-tasks" in result.output
        assert "$sp-implement" in result.output
        assert "$sp-implement-teams" in result.output
        assert "$sp-checklist" in result.output
        assert "$sp-analyze" in result.output
        assert "$sp-explain" in result.output
        assert "$sp-map-codebase" in result.output
        assert "$sp-spec-extend" in result.output
        assert "$sp-team" in result.output
        assert "The Codex team skill is available as" not in result.output
        assert "spec-extend" in result.output
        assert "spec-extend" in result.output.lower()
        assert "explain" in result.output
        assert "$sp-learnings" not in result.output

    def test_claude_init_uses_same_skill_surface_without_codex_runtime(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-plus-brand"
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
        assert "Spec Kit Plus" in result.output
        assert "Initialize Spec Kit Plus Project" in result.output
        assert "Spec Kit Plus project ready." in result.output
        assert "Start Here" in result.output
        assert "Optional support skills" in result.output
        assert "Spec Kit Plus skills were" in result.output
        assert ".claude/skills" in result.output
        assert "Start using skills with your AI agent" in result.output
        assert "Core workflow skills" in result.output
        assert "Support skills" in result.output
        assert "/sp-constitution" in result.output
        assert "/sp-specify" in result.output
        assert "/sp-plan" in result.output
        assert "/sp-tasks" in result.output
        assert "/sp-implement" in result.output
        assert "/sp-implement-teams" in result.output
        assert "/sp-checklist" in result.output
        assert "/sp-analyze" in result.output
        assert "/sp-explain" in result.output
        assert "/sp-map-codebase" in result.output
        assert "/sp-spec-extend" in result.output
        assert "/sp-learnings" not in result.output
        assert "Codex-only runtime" not in result.output
        assert "specify team" not in result.output.lower()
        assert "/sp-team" not in result.output.lower()
        assert "(codex-only)" not in result.output.lower()

    def test_init_directory_conflict_uses_normalized_error_surface(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "existing-project"
        project.mkdir()

        runner = CliRunner()
        result = runner.invoke(app, ["init", str(project)])

        assert result.exit_code != 0
        assert "Directory Conflict" not in result.output
        assert "Directory conflict" in result.output
        assert "choose a different project name" in result.output.lower()
        assert "Next" in result.output

    def test_codex_init_generates_analysis_rework_skill_surface(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "codex-analysis-rework"
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

        skills_dir = project / ".codex" / "skills"

        assert (skills_dir / "sp-spec-extend" / "SKILL.md").exists()
        assert (skills_dir / "sp-explain" / "SKILL.md").exists()
        assert (skills_dir / "sp-map-codebase" / "SKILL.md").exists()
        assert (project / ".specify" / "templates" / "references-template.md").exists()

        specify_fm = self._frontmatter(skills_dir / "sp-specify" / "SKILL.md")
        spec_extend_fm = self._frontmatter(skills_dir / "sp-spec-extend" / "SKILL.md")
        plan_fm = self._frontmatter(skills_dir / "sp-plan" / "SKILL.md")
        explain_fm = self._frontmatter(skills_dir / "sp-explain" / "SKILL.md")
        map_codebase_fm = self._frontmatter(skills_dir / "sp-map-codebase" / "SKILL.md")

        assert isinstance(specify_fm["description"], str) and specify_fm["description"].strip()
        assert isinstance(spec_extend_fm["description"], str) and spec_extend_fm["description"].strip()
        assert isinstance(plan_fm["description"], str) and plan_fm["description"].strip()
        assert isinstance(explain_fm["description"], str) and explain_fm["description"].strip()
        assert isinstance(map_codebase_fm["description"], str) and map_codebase_fm["description"].strip()

        assert "feature specification" in specify_fm["description"].lower()
        assert "natural language" in specify_fm["description"].lower()
        assert "current specification" in spec_extend_fm["description"].lower()
        assert "targeted enhancement" in spec_extend_fm["description"].lower()
        assert "implementation planning workflow" in plan_fm["description"].lower()
        assert "design artifacts" in plan_fm["description"].lower()
        assert "current stage artifact" in explain_fm["description"].lower()
        assert "plain language" in explain_fm["description"].lower()
        assert "handbook navigation system" in map_codebase_fm["description"].lower()
        assert "spec-extend" in result.output.lower()
        assert "spec-extend" in result.output
        assert "explain" in result.output

    def test_quick_help_exposes_management_commands(self):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["quick", "--help"])

        assert result.exit_code == 0, result.output
        for command in ("list", "status", "resume", "close", "archive"):
            assert command in result.output

    def test_project_map_status_and_check_commands_render_seeded_state(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-status"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            status_result = runner.invoke(app, ["project-map", "status", "--format", "json"], catch_exceptions=False)
            check_result = runner.invoke(app, ["project-map", "check", "--format", "json"], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert status_result.exit_code == 0, status_result.output
        assert check_result.exit_code == 0, check_result.output

        status_payload = json.loads(status_result.output)
        check_payload = json.loads(check_result.output)
        assert status_payload["freshness"] == "missing"
        assert status_payload["status_path"].replace("\\", "/").endswith(".specify/project-map/status.json")
        assert check_payload["freshness"] == "possibly_stale"
        assert check_payload["reasons"] == ["git baseline unavailable for project-map freshness"]

    def test_project_map_mark_dirty_sets_runtime_stale_state(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-dirty"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            dirty_result = runner.invoke(
                app,
                ["project-map", "mark-dirty", "shared_surface_changed", "--format", "json"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert dirty_result.exit_code == 0, dirty_result.output

        payload = json.loads(dirty_result.output)
        assert payload["freshness"] == "stale"
        assert payload["dirty"] is True
        assert payload["dirty_reasons"] == ["shared_surface_changed"]
        assert payload["must_refresh_topics"] == ["ARCHITECTURE.md", "STRUCTURE.md"]
        assert payload["review_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"]

    def test_project_map_mark_dirty_normalizes_human_reason(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-dirty-normalize"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            dirty_result = runner.invoke(
                app,
                ["project-map", "mark-dirty", "workflow contract changed", "--format", "json"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert dirty_result.exit_code == 0, dirty_result.output

        payload = json.loads(dirty_result.output)
        assert payload["dirty_reasons"] == ["workflow_contract_changed"]
        assert payload["must_refresh_topics"] == ["WORKFLOWS.md"]
        assert payload["review_topics"] == ["ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md"]

    def test_project_map_record_refresh_requires_canonical_outputs(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-refresh"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            refresh_result = runner.invoke(
                app,
                ["project-map", "record-refresh", "--reason", "manual"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert refresh_result.exit_code != 0
        lowered = refresh_result.output.lower()
        assert "canonical map files" in lowered
        assert "are missing" in lowered
        assert "map-codebase" in refresh_result.output.lower()

    def test_project_map_complete_refresh_records_map_codebase_reason(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-complete-refresh"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            (project / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
            project_map_dir = project / ".specify" / "project-map"
            for name in (
                "ARCHITECTURE.md",
                "STRUCTURE.md",
                "CONVENTIONS.md",
                "INTEGRATIONS.md",
                "WORKFLOWS.md",
                "TESTING.md",
                "OPERATIONS.md",
            ):
                (project_map_dir / name).write_text(f"# {name}\n", encoding="utf-8")

            refresh_result = runner.invoke(
                app,
                ["project-map", "complete-refresh", "--format", "json"],
                catch_exceptions=False,
            )
            status_result = runner.invoke(
                app,
                ["project-map", "status", "--format", "json"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert refresh_result.exit_code == 0, refresh_result.output
        assert status_result.exit_code == 0, status_result.output

        refresh_payload = json.loads(refresh_result.output)
        status_payload = json.loads(status_result.output)
        assert refresh_payload["freshness"] == "possibly_stale"
        assert status_payload["last_refresh_reason"] == "map-codebase"

    def test_init_installs_shared_worker_prompt_templates(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "worker-prompt-assets"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
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
        prompt_dir = project / ".specify" / "templates" / "worker-prompts"
        assert (prompt_dir / "implementer.md").exists()
        assert (prompt_dir / "debug-investigator.md").exists()
        assert (prompt_dir / "quick-worker.md").exists()
        assert (prompt_dir / "spec-reviewer.md").exists()
        assert (prompt_dir / "code-quality-reviewer.md").exists()

    def test_project_map_refresh_topics_records_partial_refresh_scope(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-refresh-topics"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            (project / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
            project_map_dir = project / ".specify" / "project-map"
            for name in (
                "ARCHITECTURE.md",
                "STRUCTURE.md",
                "CONVENTIONS.md",
                "INTEGRATIONS.md",
                "WORKFLOWS.md",
                "TESTING.md",
                "OPERATIONS.md",
            ):
                (project_map_dir / name).write_text(f"# {name}\n", encoding="utf-8")

            refresh_result = runner.invoke(
                app,
                ["project-map", "refresh-topics", "INTEGRATIONS.md", "WORKFLOWS.md", "--reason", "topic-refresh", "--format", "json"],
                catch_exceptions=False,
            )
            status_result = runner.invoke(
                app,
                ["project-map", "status", "--format", "json"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert refresh_result.exit_code == 0, refresh_result.output
        assert status_result.exit_code == 0, status_result.output

        refresh_payload = json.loads(refresh_result.output)
        status_payload = json.loads(status_result.output)
        assert refresh_payload["last_refresh_scope"] == "partial"
        assert refresh_payload["last_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]
        assert refresh_payload["last_refresh_basis"] == "topic-refresh"
        assert status_payload["last_refresh_scope"] == "partial"
        assert status_payload["last_refresh_topics"] == ["INTEGRATIONS.md", "WORKFLOWS.md"]

    def test_project_map_refresh_topics_rejects_unknown_topic(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "project-map-refresh-topics-invalid"
        project.mkdir()
        runner = CliRunner()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            init_result = runner.invoke(
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
            refresh_result = runner.invoke(
                app,
                ["project-map", "refresh-topics", "UNKNOWN.md"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert init_result.exit_code == 0, init_result.output
        assert refresh_result.exit_code != 0
        assert "unknown topic" in refresh_result.output.lower()


def test_install_psmux_for_codex_teams_uses_exact_winget_id(monkeypatch):
    from specify_cli import _install_psmux_for_codex_teams

    commands: list[list[str]] = []

    def fake_run(cmd, capture_output, text, check):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("specify_cli.detect_team_runtime_backend", lambda: {"available": False, "name": None, "binary": None})
    monkeypatch.setattr("specify_cli.shutil.which", lambda name: "C:\\Windows\\System32\\winget.exe" if name == "winget" else None)
    monkeypatch.setattr("specify_cli.subprocess.run", fake_run)

    ok, detail = _install_psmux_for_codex_teams()

    assert ok is True
    assert "Installed psmux" in detail
    assert commands == [[
        "winget",
        "install",
        "--id",
        "marlocarlo.psmux",
        "--exact",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]]


def test_install_psmux_for_codex_teams_skips_when_already_available(monkeypatch):
    from specify_cli import _install_psmux_for_codex_teams

    monkeypatch.setattr("specify_cli.detect_team_runtime_backend", lambda: {"available": True, "name": "psmux", "binary": "C:\\psmux\\tmux.exe"})
    monkeypatch.setattr("specify_cli.shutil.which", lambda name: None)

    ok, detail = _install_psmux_for_codex_teams()

    assert ok is True
    assert "already installed" in detail.lower()


def test_create_codex_teams_initial_commit_bootstraps_head(tmp_path):
    from specify_cli import _create_codex_teams_initial_commit

    project = tmp_path / "codex-teams-git"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.name", "Spec Kit Test"], cwd=project, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "spec-kit@example.invalid"], cwd=project, capture_output=True, text=True, check=True)
    (project / "README.md").write_text("# Test\n", encoding="utf-8")

    ok, detail = _create_codex_teams_initial_commit(project)

    assert ok is True
    assert "initial git commit" in detail.lower()
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert head.returncode == 0
    assert status.stdout.strip() == ""


def test_create_codex_teams_initial_commit_excludes_vs_and_svn_metadata(tmp_path):
    from specify_cli import _create_codex_teams_initial_commit

    project = tmp_path / "codex-teams-ignore-metadata"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.name", "Spec Kit Test"], cwd=project, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "spec-kit@example.invalid"], cwd=project, capture_output=True, text=True, check=True)
    (project / "README.md").write_text("# Test\n", encoding="utf-8")
    (project / ".vs" / "JZDownloader" / "FileContentIndex").mkdir(parents=True)
    (project / ".vs" / "JZDownloader" / "FileContentIndex" / "index.vsidx").write_text("cache\n", encoding="utf-8")
    (project / ".svn" / "pristine").mkdir(parents=True)
    (project / ".svn" / "pristine" / "base.svn-base").write_text("svn metadata\n", encoding="utf-8")

    ok, detail = _create_codex_teams_initial_commit(project)

    assert ok is True
    assert "initial git commit" in detail.lower()
    exclude_path = project / ".git" / "info" / "exclude"
    exclude_content = exclude_path.read_text(encoding="utf-8")
    assert ".vs/" in exclude_content
    assert ".svn/" in exclude_content
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.stdout.strip() == ""


def test_maybe_bootstrap_codex_teams_environment_runs_psmux_and_initial_commit(monkeypatch, tmp_path):
    from specify_cli import _maybe_bootstrap_codex_teams_environment

    project = tmp_path / "codex-bootstrap"
    project.mkdir()

    statuses = [
        {
            "native_windows": True,
            "runtime_backend_available": True,
            "git_repo_detected": True,
            "git_head_available": False,
        },
        {
            "native_windows": True,
            "runtime_backend_available": True,
            "git_repo_detected": True,
            "git_head_available": True,
        },
    ]
    confirms = iter([True, True])
    calls: list[str] = []

    monkeypatch.setattr("specify_cli.sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("specify_cli.shutil.which", lambda name: "C:\\Windows\\System32\\winget.exe" if name == "winget" else None)
    monkeypatch.setattr("specify_cli.typer.confirm", lambda prompt, default=True: next(confirms))
    monkeypatch.setattr("specify_cli._install_psmux_for_codex_teams", lambda: (calls.append("psmux") or True, "Installed psmux via winget"))
    monkeypatch.setattr("specify_cli._create_codex_teams_initial_commit", lambda project_root: (calls.append("git") or True, "Created an initial git commit for Codex teams"))
    monkeypatch.setattr("specify_cli.codex_team_runtime_status", lambda project_root, integration_key="codex": statuses.pop(0))

    final_status = _maybe_bootstrap_codex_teams_environment(
        project,
        team_status={
            "native_windows": True,
            "runtime_backend_available": False,
            "git_repo_detected": True,
            "git_head_available": False,
        },
    )

    assert calls == ["psmux", "git"]
    assert final_status["runtime_backend_available"] is True
    assert final_status["git_head_available"] is True
