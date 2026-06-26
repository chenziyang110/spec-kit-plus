"""Tests for --integration flag on specify init (CLI-level)."""

import json
import os
import re
import subprocess

import yaml
from typer.testing import CliRunner

from specify_cli import app
from tests.conftest import strip_ansi


def test_top_level_cli_exposes_discussion_entrypoint():
    runner = CliRunner()
    root_help = runner.invoke(app, ["--help"], catch_exceptions=False)
    discussion_help = runner.invoke(app, ["discussion", "--help"], catch_exceptions=False)
    discussion_entrypoint = runner.invoke(app, ["discussion"], catch_exceptions=False)

    assert root_help.exit_code == 0, root_help.output
    assert discussion_help.exit_code == 0, discussion_help.output
    assert discussion_entrypoint.exit_code == 0, discussion_entrypoint.output
    discussion_output = re.sub(r"\s+", " ", strip_ansi(discussion_help.output).lower())
    assert "discussion" in root_help.output
    assert "resumable senior product-engineering" in discussion_output
    assert "discussion before formal specification" in discussion_output
    assert "workflow entrypoint and help surface" in strip_ansi(discussion_entrypoint.output).lower()


class TestInitIntegrationFlag:
    @staticmethod
    def _frontmatter(skill_path):
        content = skill_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1])

    def test_codex_init_advertises_sp_teams_surface(self, tmp_path):
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
        assert (project / ".codex" / "skills" / "sp-teams" / "SKILL.md").exists()
        assert (project / ".specify" / "teams" / "runtime.json").exists()
        assert (project / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (project / ".specify" / "project-cognition").is_dir()
        status = json.loads(
            (project / ".specify" / "project-cognition" / "status.json").read_text(
                encoding="utf-8"
            )
        )
        assert status["baseline_kind"] == "greenfield_empty"
        assert (project / ".specify" / "project-cognition" / "project-cognition.db").exists()
        assert not (project / ".specify" / "templates" / "project-map").exists()
        assert not (project / ".specify" / "project-map").exists()
        assert "sp-teams" in result.output
        assert "Codex Teams Readiness" in result.output
        assert "git repo detected" in result.output
        assert "worktree-ready" in result.output
        assert "integrate" in result.output.lower()

    def test_non_codex_init_does_not_advertise_sp_teams_surface(self, tmp_path):
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
        assert not (project / ".claude" / "skills" / "sp-teams" / "SKILL.md").exists()
        assert not (project / ".specify" / "teams" / "runtime.json").exists()
        assert "specify team" not in result.output.lower()
        assert "/sp-teams" not in result.output.lower()
        assert "(codex-only)" not in result.output.lower()
        assert "integrate" in result.output.lower()

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
        assert not (project / ".claude" / "skills" / "sp-teams" / "SKILL.md").exists()
        assert not (project / ".specify" / "teams" / "runtime.json").exists()

        implement_skill = project / ".claude" / "skills" / "sp-implement" / "SKILL.md"
        assert implement_skill.exists()
        content = implement_skill.read_text(encoding="utf-8")
        assert "execution_model: subagent-mandatory" in content
        assert "dispatch_shape: one-subagent | parallel-subagents" in content
        assert "execution_surface: native-subagents" in content
        assert "compass --intent implement" in content
        assert "lexicon -> semantic_intake -> query" in content
        assert "project-cognition query --query-plan" in content
        assert "--query-plan" in content
        assert "readiness" in content
        assert "task-local bundle" in content
        assert "minimal_live_reads" in content
        assert ".specify/project-cognition/slices/change.json" not in content.lower()
        assert "status and slice artifacts" not in content.lower()
        assert "build-handbook.md" not in content.lower()
        assert "build-workflow-contract" not in content.lower()
        assert "change-entrypoints" not in content.lower()
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
        assert (skills_dir / "sp-discussion" / "SKILL.md").exists()
        for skill_name in ("sp-explain",):
            content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "execution_model: subagent-mandatory" in content
            assert "dispatch_shape: one-subagent | parallel-subagents" in content
            assert "execution_surface: native-subagents" in content
            assert "specify team" not in content
        specify_content = (skills_dir / "sp-specify" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "choose_evidence_lane_dispatch" in specify_content
        assert "lane_mode: read-only-evidence" in specify_content
        assert "structured_result: evidence_packet" in specify_content
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in specify_content
        assert "execution_surface: leader-inline | native-subagents | none" in specify_content
        assert "specify team" not in specify_content
        for skill_name in ("sp-plan", "sp-tasks"):
            content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "execution_model: adaptive" in content
            assert "execution_mode: light | standard | heavy" in content
            assert "workflow_status: ready | blocked" in content
            assert "specify team" not in content

        debug_content = (skills_dir / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "execution_model: leader-inline | subagent-assisted | blocked" in debug_content
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in debug_content
        assert "execution_surface: leader-inline | native-subagents | none" in debug_content
        assert "small focused investigation" in debug_content
        assert "subagent-assisted" in debug_content
        assert 'choose_subagent_dispatch(command_name="debug"' in debug_content
        assert "capability-aware investigation" in debug_content
        assert "compass --intent debug" in debug_content
        assert "lexicon -> semantic_intake -> query" in debug_content
        assert "project-cognition query --query-plan" in debug_content
        assert "--query-plan" in debug_content
        assert "returned readiness" in debug_content
        assert "task-local bundle" in debug_content
        assert "minimal_live_reads" in debug_content
        assert ".specify/project-cognition/slices/debug.json" not in debug_content
        assert ".specify/project-cognition/graph/claims.json" not in debug_content
        assert ".specify/project-cognition/graph/conflicts.json" not in debug_content
        assert "debug-handbook.md" not in debug_content
        assert "debug-workflow-contract" not in debug_content
        assert "spawn_agent" not in debug_content

        fast_content = (skills_dir / "sp-fast" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "compass --intent implement" in fast_content
        assert "lexicon -> semantic_intake -> query" in fast_content
        assert "project-cognition query --query-plan" in fast_content
        assert "--query-plan" in fast_content
        assert "returned readiness" in fast_content
        assert "minimal_live_reads" in fast_content
        assert "minimal_live_reads" in fast_content
        assert ".specify/project-cognition/slices/change.json" not in fast_content
        assert "build-handbook.md" not in fast_content
        assert "shared surfaces" in fast_content
        assert "change-propagation hotspot" in fast_content

        quick_content = (skills_dir / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert ".specify/memory/constitution.md" in quick_content
        assert ".specify/memory/project-rules.md" in quick_content
        assert ".specify/memory/learnings/index.md" in quick_content
        assert "learning reflex" in quick_content
        assert "future senior engineer" in quick_content
        assert ".specify/memory/project-learnings.md" not in quick_content
        assert ".planning/learnings/candidates.md" not in quick_content
        assert "compass --intent implement" in quick_content
        assert "lexicon -> semantic_intake -> query" in quick_content
        assert "project-cognition query --query-plan" in quick_content
        assert "--query-plan" in quick_content
        assert "project cognition query" in quick_content
        assert "returned readiness" in quick_content
        assert "minimal_live_reads" in quick_content
        assert "minimal_live_reads" in quick_content
        assert "understanding checkpoint" in quick_content
        assert "understanding_confirmed" in quick_content
        assert "status and slice artifacts" not in quick_content
        assert ".specify/project-cognition/slices/change.json" not in quick_content
        assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in quick_content
        assert "attempt the smallest safe recovery step before declaring the task blocked" in quick_content
        assert "retry_attempts" in quick_content
        assert "blocker_reason" in quick_content

    def test_top_level_cli_exposes_graph_native_map_commands(self):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()

        root_help = runner.invoke(app, ["--help"], catch_exceptions=False)
        map_scan_help = runner.invoke(app, ["map-scan", "--help"], catch_exceptions=False)
        map_build_help = runner.invoke(app, ["map-build", "--help"], catch_exceptions=False)
        map_update_help = runner.invoke(app, ["map-update", "--help"], catch_exceptions=False)

        assert root_help.exit_code == 0, root_help.output
        assert map_scan_help.exit_code == 0, map_scan_help.output
        assert map_build_help.exit_code == 0, map_build_help.output
        assert map_update_help.exit_code == 0, map_update_help.output

        assert "map-scan" in root_help.output
        assert "map-build" in root_help.output
        assert "map-update" in root_help.output
        assert "graph-native cognition baseline" in map_scan_help.output.lower()
        assert "project cognition graph" in map_build_help.output.lower()
        assert "cognition baseline exists" in map_update_help.output.lower()
        assert "runtime incrementally" in map_update_help.output.lower()

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


def test_check_reports_missing_project_launcher_in_spec_kit_project(tmp_path, monkeypatch):
    runner = CliRunner()
    project = tmp_path / "project"
    project.mkdir()
    (project / ".specify").mkdir()
    (project / ".specify" / "config.json").write_text("{}", encoding="utf-8")

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["check"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0
    assert "project launcher" in result.output.lower()
    assert "compatibility mode" in result.output.lower()


def test_check_reports_project_runtime_compatibility_issues(tmp_path):
    runner = CliRunner()
    project = tmp_path / "project-compat"
    project.mkdir()
    (project / ".specify" / "scripts" / "powershell").mkdir(parents=True)
    (project / ".specify" / "config.json").write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "broken launcher",
                    "argv": ["definitely-missing-specify-command", "specify"],
                }
            }
        ),
        encoding="utf-8",
    )
    (project / ".specify" / "scripts" / "powershell" / "common.ps1").write_text(
        "function Get-FeaturePathsEnv { $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch }\n",
        encoding="utf-8",
    )
    (project / ".specify" / "scripts" / "bash").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "scripts" / "bash" / "common.sh").write_text(
        'get_feature_dir() { echo "$1/specs/$2"; }\n',
        encoding="utf-8",
    )
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'python "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py session-start',
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["check"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0
    output = " ".join(strip_ansi(result.output).lower().split())
    assert "project compatibility" in output
    assert "persisted project launcher is configured but unavailable" in output
    assert "generated powershell workflow scripts are stale" in output
    assert "generated shared workflow scripts still target legacy feature roots" in output
    assert "claude managed hook commands still use shell-parsed direct python" in output
    assert "shell-free node launcher" in output
    assert "managed native hook commands still invoke integration dispatch scripts through a direct python command" in output


def test_init_creates_project_cognition_greenfield_empty_runtime(tmp_path):
    project = tmp_path / "project-cognition-runtime-dir"
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
    finally:
        os.chdir(old_cwd)

    assert init_result.exit_code == 0, init_result.output
    assert (project / ".specify" / "project-cognition").is_dir()
    status = json.loads(
        (project / ".specify" / "project-cognition" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status["baseline_kind"] == "greenfield_empty"
    assert (project / ".specify" / "project-cognition" / "project-cognition.db").exists()
    assert not (project / ".specify" / "project-map" / "status.json").exists()
    assert not (project / ".specify" / "project-map" / "index" / "status.json").exists()


def test_python_cli_no_longer_exposes_project_cognition_runtime_namespaces():
    runner = CliRunner()

    assert runner.invoke(app, ["project-cognition", "--help"]).exit_code != 0
    assert runner.invoke(app, ["project-map", "--help"]).exit_code != 0
    assert runner.invoke(app, ["cognition", "--help"]).exit_code != 0


def test_init_installs_brainstorming_truth_templates(tmp_path):
    runner = CliRunner()
    project = tmp_path / "demo"
    result = runner.invoke(app, ["init", str(project), "--ai", "codex", "--ignore-agent-tools"])
    assert result.exit_code == 0, result.output
    templates_dir = project / ".specify" / "templates"
    assert (templates_dir / "brainstorming-facts-template.json").exists()
    assert (templates_dir / "brainstorming-route-template.json").exists()
    assert (templates_dir / "brainstorming-intent-template.json").exists()
    assert (templates_dir / "brainstorming-complexity-template.json").exists()
    assert (templates_dir / "brainstorming-handoff-specify-template.json").exists()
    assert (templates_dir / "brainstorming-stage-manifest-template.json").exists()
    assert (templates_dir / "brainstorming-domains-template.json").exists()
    assert (templates_dir / "brainstorming-evidence-index-template.json").exists()
    assert (templates_dir / "brainstorming-evidence-record-template.json").exists()


def test_check_reports_workflow_contract_drift(tmp_path):
    runner = CliRunner()
    project = tmp_path / "project-workflow-contract"
    project.mkdir()
    (project / ".specify" / "scripts" / "powershell").mkdir(parents=True)
    (project / ".specify" / "config.json").write_text("{}", encoding="utf-8")
    (project / ".specify" / "scripts" / "powershell" / "common.ps1").write_text(
        "function Find-FeatureDirByPrefix {}\nFind-FeatureDirByPrefix -RepoRoot $repoRoot -BranchName $currentBranch\n",
        encoding="utf-8",
    )
    (project / ".specify" / "templates" / "commands").mkdir(parents=True)
    (project / ".specify" / "templates" / "commands" / "analyze.md").write_text(
        "Run scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks\n",
        encoding="utf-8",
    )
    (project / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning").mkdir(parents=True)
    (project / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning" / "SKILL.md").write_text(
        "specify hook review-learning --command analyze --origin-artifact plan.md\n",
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["check"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    lowered = result.output.lower()
    assert "generated analyze workflow guidance is stale" in lowered
    assert "generated learning guidance still references unsupported" in lowered
    assert "helper command surface" in lowered
    assert "specify integration repair" in lowered


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
        assert (project / ".github" / "agents" / "sp.clarify.agent.md").exists()
        assert (project / ".github" / "agents" / "sp.explain.agent.md").exists()
        assert (project / ".github" / "prompts" / "sp.plan.prompt.md").exists()
        assert (project / ".specify" / "scripts" / "bash" / "common.sh").exists()
        assert (project / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (project / ".specify" / "project-cognition" / "status.json").exists()
        assert not (project / ".specify" / "templates" / "project-map").exists()
        assert not (project / ".specify" / "project-map").exists()
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

        # New shared templates should still be installed
        assert (templates_dir / "specify-draft-template.md").exists()

    def test_init_installs_specify_draft_template(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "draft-template-install"
        project.mkdir()
        scripts_dir = project / ".specify" / "scripts" / "bash"
        templates_dir = project / ".specify" / "templates"

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
        assert (project / ".specify" / "templates" / "specify-draft-template.md").exists()

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
        assert "Support and gate skills" in result.output
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
        assert "$sp-discussion" in result.output
        assert "$sp-plan" in result.output
        assert "$sp-tasks" in result.output
        assert "$sp-implement" in result.output
        assert "$sp-implement-teams" in result.output
        assert "$sp-checklist" in result.output
        assert "$sp-test" not in result.output
        assert "$sp-test-scan" not in result.output
        assert "$sp-test-build" not in result.output
        assert "$sp-analyze" in result.output
        assert "$sp-auto" in result.output
        assert "$sp-explain" in result.output
        assert "$sp-map-scan" in result.output
        assert "$sp-map-build" in result.output
        assert "$sp-map-codebase" not in result.output
        assert "$sp-clarify" in result.output
        assert "$sp-deep-research" in result.output
        assert "$sp-teams" in result.output
        assert "seeded default constitution" in result.output.lower()
        assert "project-specific changes" in result.output.lower()
        assert "required for existing code" in result.output
        assert "optional diagnostic / legacy revalidation" in result.output.lower()
        assert "The Codex team skill is available as" not in result.output
        assert "clarify" in result.output
        assert "clarify" in result.output.lower()
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
        assert "Support and gate skills" in result.output
        assert "Spec Kit Plus skills were" in result.output
        assert ".claude/skills" in result.output
        assert "Start using skills with your AI agent" in result.output
        assert "Core workflow skills" in result.output
        assert "Support skills" in result.output
        assert "/sp-constitution" in result.output
        assert "/sp-specify" in result.output
        assert "/sp-discussion" in result.output
        assert "/sp-plan" in result.output
        assert "/sp-tasks" in result.output
        assert "/sp-implement" in result.output
        assert "/sp-implement-teams" in result.output
        assert "/sp-checklist" in result.output
        assert "/sp-test" not in result.output
        assert "/sp-test-scan" not in result.output
        assert "/sp-test-build" not in result.output
        assert "/sp-analyze" in result.output
        assert "/sp-auto" in result.output
        assert "seeded default constitution" in result.output.lower()
        assert "project-specific changes" in result.output.lower()
        assert "/sp-explain" in result.output
        assert "/sp-map-scan" in result.output
        assert "/sp-map-build" in result.output
        assert "/sp-map-codebase" not in result.output
        assert "/sp-clarify" in result.output
        assert "/sp-deep-research" in result.output
        assert "required for existing code" in result.output
        assert "optional diagnostic / legacy revalidation" in result.output.lower()
        assert "/sp-learnings" not in result.output
        assert "Codex-only runtime" not in result.output
        assert "specify team" not in result.output.lower()
        assert "/sp-teams" not in result.output.lower()
        assert "(codex-only)" not in result.output.lower()

    def test_cursor_init_uses_skills_surface_and_new_directory(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "cursor-plus-brand"
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
                    "cursor-agent",
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
        assert "Spec Kit Plus skills were" in result.output
        assert ".cursor/skills" in result.output
        assert "Start using skills with your AI agent" in result.output
        assert "/sp-plan" in result.output
        assert "/sp.specify" not in result.output
        assert "Support and gate skills" in result.output
        assert "Support and gate commands" not in result.output

    def test_vibe_init_uses_skills_surface_and_new_directory(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "vibe-plus-brand"
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
                    "vibe",
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
        assert "Spec Kit Plus skills were" in result.output
        assert ".vibe/skills" in result.output
        assert "Start using skills with your AI agent" in result.output
        assert "/sp-plan" in result.output
        assert "/sp.specify" not in result.output
        assert "Support and gate skills" in result.output
        assert "Support and gate commands" not in result.output

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

        assert (skills_dir / "sp-discussion" / "SKILL.md").exists()
        assert (skills_dir / "sp-clarify" / "SKILL.md").exists()
        assert (skills_dir / "sp-deep-research" / "SKILL.md").exists()
        assert (skills_dir / "sp-explain" / "SKILL.md").exists()
        assert (skills_dir / "sp-map-scan" / "SKILL.md").exists()
        assert (skills_dir / "sp-map-build" / "SKILL.md").exists()
        assert not (project / ".specify" / "templates" / "project-map").exists()
        assert not (project / ".specify" / "project-map").exists()
        assert not (skills_dir / "sp-map-codebase" / "SKILL.md").exists()
        assert (project / ".specify" / "templates" / "references-template.md").exists()

        specify_fm = self._frontmatter(skills_dir / "sp-specify" / "SKILL.md")
        spec_extend_fm = self._frontmatter(skills_dir / "sp-clarify" / "SKILL.md")
        deep_research_fm = self._frontmatter(skills_dir / "sp-deep-research" / "SKILL.md")
        plan_fm = self._frontmatter(skills_dir / "sp-plan" / "SKILL.md")
        explain_fm = self._frontmatter(skills_dir / "sp-explain" / "SKILL.md")
        map_scan_fm = self._frontmatter(skills_dir / "sp-map-scan" / "SKILL.md")
        map_build_fm = self._frontmatter(skills_dir / "sp-map-build" / "SKILL.md")

        assert isinstance(specify_fm["description"], str) and specify_fm["description"].strip()
        assert isinstance(spec_extend_fm["description"], str) and spec_extend_fm["description"].strip()
        assert isinstance(deep_research_fm["description"], str) and deep_research_fm["description"].strip()
        assert isinstance(plan_fm["description"], str) and plan_fm["description"].strip()
        assert isinstance(explain_fm["description"], str) and explain_fm["description"].strip()
        assert isinstance(map_scan_fm["description"], str) and map_scan_fm["description"].strip()
        assert isinstance(map_build_fm["description"], str) and map_build_fm["description"].strip()

        assert specify_fm["description"].startswith("Use when")
        assert spec_extend_fm["description"].startswith("Use when")
        assert plan_fm["description"].startswith("Use when")
        assert explain_fm["description"].startswith("Use when")
        assert map_scan_fm["description"].startswith("Use when")
        assert map_build_fm["description"].startswith("Use when")
        assert "guided requirement discovery" in specify_fm["description"].lower()
        assert "planning-ready specification package" in specify_fm["description"].lower()
        assert "planning-critical gaps" in spec_extend_fm["description"].lower()
        assert "implementation planning" in plan_fm["description"].lower()
        assert "plain language" in explain_fm["description"].lower()
        assert "graph-native cognition baseline" in map_scan_fm["description"].lower()
        assert "compatibility/export" in map_scan_fm["description"].lower()
        assert "map-scan" in map_build_fm["description"].lower()
        assert "capability flow and lifecycle truth layer" in (project / "AGENTS.md").read_text(encoding="utf-8").lower()
        assert "clarify" in result.output.lower()
        assert "clarify" in result.output
        assert "explain" in result.output

    def test_quick_help_exposes_management_commands(self):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["quick", "--help"])

        assert result.exit_code == 0, result.output
        for command in ("list", "status", "resume", "close", "archive"):
            assert command in result.output

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

def test_install_psmux_for_codex_teams_uses_exact_winget_id(monkeypatch):
    from specify_cli import _install_psmux_for_codex_teams

    commands: list[list[str]] = []

    def fake_run(cmd, capture_output, text, check, **kwargs):
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


def test_root_level_feature_resolution_prefers_unique_resumable_lane(tmp_path):
    from specify_cli import _resolve_feature_dir_for_command
    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record

    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".specify").mkdir(exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-analyze`",
                "- status: `completed`",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: executing",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: execute batch",
                "next_action: collect worker result",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    resolved = _resolve_feature_dir_for_command(tmp_path, command_name="implement", feature_dir=None)

    assert resolved == (tmp_path / "specs" / "001-demo").resolve()


def test_root_level_feature_resolution_returns_none_for_ambiguous_lanes(tmp_path):
    from specify_cli import _resolve_feature_dir_for_command
    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record

    (tmp_path / ".specify").mkdir(exist_ok=True)
    for slug in ("001-alpha", "002-beta"):
        feature_dir = tmp_path / "specs" / slug
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-analyze`",
                    "- status: `completed`",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.implement`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (feature_dir / "implement-tracker.md").write_text(
            "\n".join(
                [
                    "---",
                    "status: executing",
                    f"feature: {slug}",
                    "resume_decision: resume-here",
                    "---",
                    "",
                    "## Current Focus",
                    "current_batch: batch-a",
                    "goal: execute batch",
                    "next_action: collect worker result",
                    "",
                    "## Execution State",
                    "retry_attempts: 0",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    lane_a = LaneRecord(
        lane_id="lane-001",
        feature_id="001-alpha",
        feature_dir="specs/001-alpha",
        branch_name="001-alpha",
        worktree_path=".specify/lanes/worktrees/lane-001",
        recovery_state="resumable",
        last_command="implement",
    )
    lane_b = LaneRecord(
        lane_id="lane-002",
        feature_id="002-beta",
        feature_dir="specs/002-beta",
        branch_name="002-beta",
        worktree_path=".specify/lanes/worktrees/lane-002",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane_a)
    write_lane_record(tmp_path, lane_b)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]})

    resolved = _resolve_feature_dir_for_command(tmp_path, command_name="implement", feature_dir=None)

    assert resolved is None


def test_root_level_feature_resolution_supports_legacy_spec_root_from_lane_record(tmp_path):
    from specify_cli import _resolve_feature_dir_for_command
    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record

    feature_dir = tmp_path / ".specify" / "specs" / "001-legacy"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".specify").mkdir(exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `completed`",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lane = LaneRecord(
        lane_id="lane-legacy",
        feature_id="001-legacy",
        feature_dir=".specify/specs/001-legacy",
        branch_name="001-legacy-hotfix",
        worktree_path=".specify/lanes/worktrees/lane-legacy",
        recovery_state="resumable",
        last_command="specify",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-legacy"}]})

    resolved = _resolve_feature_dir_for_command(tmp_path, command_name="plan", feature_dir=None)

    assert resolved == feature_dir.resolve()


def test_integrate_command_is_registered(tmp_path):
    runner = CliRunner()
    project = tmp_path / "integrate-command"
    project.mkdir()
    (project / ".specify").mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["integrate", "--help"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0
    assert "close out" in result.output.lower() or "closeout" in result.output.lower()


def test_integrate_discovery_reports_readiness_checks(tmp_path):
    runner = CliRunner()
    project = tmp_path / "integrate-discovery"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()

    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        verification_status="passed",
        last_command="implement",
    )
    write_lane_record(project, lane)
    write_lane_index(project, {"lanes": [{"lane_id": "lane-001"}]})
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: done",
                "next_action: none",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["integrate"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["mode"] == "discovery"
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["recommended_action"] in {"close", "fix-prechecks"}
    assert isinstance(candidate["checks"], list)
    assert candidate["checks"]


def test_integrate_discovery_includes_not_ready_lane_with_fix_prechecks_action(tmp_path):
    runner = CliRunner()
    project = tmp_path / "integrate-discovery-not-ready"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()

    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="blocked",
        verification_status="failed",
        last_command="implement",
    )
    write_lane_record(project, lane)
    write_lane_index(project, {"lanes": [{"lane_id": "lane-001"}]})
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: blocked",
                "feature: 001-demo",
                "resume_decision: blocked-waiting",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: blocked",
                "next_action: fix verification",
                "",
                "## Execution State",
                "retry_attempts: 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["integrate"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["ready"] is False
    assert candidate["recommended_action"] == "fix-prechecks"


def test_integrate_targeted_blocks_when_feature_dir_has_no_registered_lane(tmp_path):
    runner = CliRunner()
    project = tmp_path / "integrate-no-lane"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["integrate", "--feature-dir", str(feature_dir)],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["lane_id"] is None


def test_integrate_targeted_close_marks_ready_lane_completed(tmp_path):
    runner = CliRunner()
    project = tmp_path / "integrate-close"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-analyze`",
                "- status: `completed`",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: done",
                "next_action: none",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record, read_lane_record

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="completed",
        verification_status="passed",
        last_command="implement",
    )
    write_lane_record(project, lane)
    write_lane_index(project, {"lanes": [{"lane_id": "lane-001", "feature_dir": "specs/001-demo"}]})

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["integrate", "--feature-dir", str(feature_dir), "--close"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["closed"] is True
    updated = read_lane_record(project, "lane-001")
    assert updated is not None
    assert updated.last_command == "integrate"
    assert updated.lifecycle_state == "completed"


def test_lane_register_writes_lane_record_and_index(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-register"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "lane",
                "register",
                "--lane-id",
                "lane-001",
                "--feature-dir",
                str(feature_dir),
                "--branch",
                "001-demo",
                "--worktree",
                str(project / ".specify" / "lanes" / "worktrees" / "lane-001"),
                "--command",
                "specify",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["lane_id"] == "lane-001"
    assert payload["lifecycle_state"] == "specified"
    assert payload["recovery_state"] == "resumable"
    assert payload["materialize_status"] in {"skipped", "created", "existing"}
    assert (project / ".specify" / "lanes" / "lane-001" / "lane.json").exists()
    assert (project / ".specify" / "lanes" / "index.json").exists()


def test_lane_register_inferrs_completed_implement_lane_from_tracker(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-register-implement"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-implement`",
                "- status: `completed`",
                "",
                "## Next Action",
                "",
                "- done",
                "",
                "## Next Command",
                "",
                "- `/sp.integrate`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: done",
                "next_action: none",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "lane",
                "register",
                "--lane-id",
                "lane-001",
                "--feature-dir",
                str(feature_dir),
                "--branch",
                "001-demo",
                "--worktree",
                str(project / ".specify" / "lanes" / "worktrees" / "lane-001"),
                "--command",
                "implement",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["recovery_state"] == "completed"
    assert payload["verification_status"] == "passed"


def test_lane_materialize_worktree_command_creates_worktree_when_git_head_exists(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-materialize"
    project.mkdir()
    (project / ".specify" / "lanes" / "lane-001").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=project, check=True)
    (project / ".specify").mkdir(exist_ok=True)
    (project / ".specify" / "lanes" / "lane-001" / "lane.json").write_text(
        json.dumps(
            {
                "lane_id": "lane-001",
                "feature_id": "001-demo",
                "feature_dir": "specs/001-demo",
                "branch_name": "001-demo",
                "worktree_path": ".specify/lanes/worktrees/lane-001",
                "lifecycle_state": "specified",
                "recovery_state": "resumable",
                "last_command": "specify",
                "last_stable_checkpoint": "",
                "recovery_reason": "",
                "verification_status": "unknown",
                "created_at": "2026-05-02T00:00:00+00:00",
                "updated_at": "2026-05-02T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["lane", "materialize-worktree", "--lane-id", "lane-001"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] in {"created", "existing"}
    assert (project / ".specify" / "lanes" / "worktrees" / "lane-001").exists()


def test_lane_resolve_can_ensure_worktree_for_unique_lane(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-resolve-worktree"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=project, check=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-analyze`",
                "- status: `completed`",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: executing",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: execute batch",
                "next_action: collect worker result",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(project, lane)
    write_lane_index(project, {"lanes": [{"lane_id": "lane-001"}]})

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["lane", "resolve", "--command", "implement", "--ensure-worktree"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "resume"
    assert payload["worktree"]["status"] in {"created", "existing"}
    assert (project / ".specify" / "lanes" / "worktrees" / "lane-001").exists()


def test_lane_status_lists_registered_lanes(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-status"
    (project / ".specify" / "lanes" / "lane-001").mkdir(parents=True)
    (project / ".specify").mkdir(exist_ok=True)
    (project / ".specify" / "lanes" / "lane-001" / "lane.json").write_text(
        json.dumps(
            {
                "lane_id": "lane-001",
                "feature_id": "001-demo",
                "feature_dir": "specs/001-demo",
                "branch_name": "001-demo",
                "worktree_path": ".specify/lanes/worktrees/lane-001",
                "lifecycle_state": "implementing",
                "recovery_state": "resumable",
                "last_command": "implement",
                "last_stable_checkpoint": "batch-a",
                "recovery_reason": "",
                "verification_status": "unknown",
                "created_at": "2026-05-02T00:00:00+00:00",
                "updated_at": "2026-05-02T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, ["lane", "status"], catch_exceptions=False)
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["lane_count"] == 1
    assert payload["lanes"][0]["lane_id"] == "lane-001"
    assert payload["lanes"][0]["worktree_exists"] is False
    assert payload["lanes"][0]["verification_status"] == "unknown"
    assert payload["lanes"][0]["ready_for_integrate"] is False
    assert payload["lanes"][0]["suggested_next_command"] == "implement"
    assert payload["lanes"][0]["inferred_command"] == "implement"


def test_lane_resolve_returns_choose_for_ambiguous_candidates(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-resolve"
    (project / ".specify" / "lanes" / "lane-001").mkdir(parents=True)
    (project / ".specify" / "lanes" / "lane-002").mkdir(parents=True)
    (project / ".specify").mkdir(exist_ok=True)

    for lane_id, slug in (("lane-001", "001-alpha"), ("lane-002", "002-beta")):
        feature_dir = project / "specs" / slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-analyze`",
                    "- status: `completed`",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.implement`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (feature_dir / "implement-tracker.md").write_text(
            "\n".join(
                [
                    "---",
                    "status: executing",
                    f"feature: {slug}",
                    "resume_decision: resume-here",
                    "---",
                    "",
                    "## Current Focus",
                    "current_batch: batch-a",
                    "goal: execute batch",
                    "next_action: collect worker result",
                    "",
                    "## Execution State",
                    "retry_attempts: 0",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (project / ".specify" / "lanes" / lane_id / "lane.json").write_text(
            json.dumps(
                {
                    "lane_id": lane_id,
                    "feature_id": slug,
                    "feature_dir": f"specs/{slug}",
                    "branch_name": slug,
                    "worktree_path": f".specify/lanes/worktrees/{lane_id}",
                    "lifecycle_state": "implementing",
                    "recovery_state": "resumable",
                    "last_command": "implement",
                    "last_stable_checkpoint": "",
                    "recovery_reason": "",
                    "created_at": "2026-05-02T00:00:00+00:00",
                    "updated_at": "2026-05-02T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

    (project / ".specify" / "lanes" / "index.json").write_text(
        json.dumps({"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]}),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["lane", "resolve", "--command", "implement"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "choose"
    assert len(payload["candidates"]) == 2
    assert "verification_status" in payload["candidates"][0]
    assert "worktree_exists" in payload["candidates"][0]
    assert "inferred_command" in payload["candidates"][0]


def test_lane_resolve_explicit_feature_dir_can_ensure_worktree(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-resolve-explicit-worktree"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=project, check=True)

    (project / ".specify" / "lanes" / "lane-001").mkdir(parents=True)
    (project / ".specify" / "lanes" / "lane-001" / "lane.json").write_text(
        json.dumps(
            {
                "lane_id": "lane-001",
                "feature_id": "001-demo",
                "feature_dir": "specs/001-demo",
                "branch_name": "001-demo",
                "worktree_path": ".specify/lanes/worktrees/lane-001",
                "lifecycle_state": "specified",
                "recovery_state": "resumable",
                "last_command": "specify",
                "last_stable_checkpoint": "",
                "recovery_reason": "",
                "verification_status": "unknown",
                "created_at": "2026-05-02T00:00:00+00:00",
                "updated_at": "2026-05-02T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "lane",
                "resolve",
                "--command",
                "plan",
                "--feature-dir",
                str(feature_dir),
                "--ensure-worktree",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "resume"
    assert payload["selected_lane_id"] == "lane-001"
    assert payload["candidates"][0]["inferred_command"] == "specify"
    assert payload["worktree"]["status"] in {"created", "existing"}
    assert (project / ".specify" / "lanes" / "worktrees" / "lane-001").exists()


def test_lane_resolve_explicit_feature_dir_blocks_when_no_lane_matches(tmp_path):
    runner = CliRunner()
    project = tmp_path / "lane-resolve-no-lane"
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (project / ".specify").mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            ["lane", "resolve", "--command", "plan", "--feature-dir", str(feature_dir)],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "blocked"
    assert payload["reason"] == "feature-dir-has-no-registered-lane"


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
