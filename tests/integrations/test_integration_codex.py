"""Tests for CodexIntegration."""

import json
from pathlib import Path

from .test_integration_base_skills import (
    _assert_compact_managed_context,
    _extract_generated_cognition_policy,
)

STALE_COGNITION_ADDENDUM_PHRASES = (
    "for blocked, stale, missing, or incomplete references",
    "{{invoke:map-scan}} -> {{invoke:map-build}} or "
    + "{{invoke:map-update}} as "
    + "appropriate",
    "status and slice artifacts",
    "status and debug-oriented slice artifacts",
    "required project cognition status and slice artifacts",
    "graph-native runtime coverage",
    "map " + "repair",
    "first-baseline " + "map " + "repair",
    "user explicitly requested " + "map " + "repair",
    "reported map-maintenance action as follow-up " + "unless",
    "when the user wants " + "map " + "repair",
    "missing or " + "stale",
    "follow-up map maintenance when " + "useful",
    "recommend sp-map-update or " + "sp-map-scan -> sp-map-build",
    "recommend map-update or " + "map-scan -> map-build",
    "user wants " + "repair",
    "the user wants " + "repair",
    "path-index-" + "incomplete",
    "path-index " + "incomplete",
    "unadoptable " + "coverage gaps",
)


def _assert_stable_subagent_contract(content: str) -> None:
    lower = content.lower()

    assert "native subagents" in lower
    assert "validated `workertaskpacket`" in lower
    assert "structured handoff" in lower
    assert "`sp-teams` only" in lower


def test_codex_integration_metadata():
    from specify_cli.integrations import get_integration

    integration = get_integration("codex")

    assert integration is not None
    assert integration.config["folder"] == ".codex/"
    assert integration.config["commands_subdir"] == "skills"
    assert integration.context_file == "AGENTS.md"


def test_codex_install_inventory_tracks_core_skills_and_team_assets(tmp_path):
    from specify_cli.codex_team import install_codex_team_assets
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest

    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)

    integration.setup(tmp_path, manifest)
    install_codex_team_assets(tmp_path, manifest, integration_key="codex")

    expected_owned_paths = (
        ".codex/config.toml",
        ".codex/skills/sp-plan/SKILL.md",
        ".codex/skills/sp-implement/SKILL.md",
        ".codex/skills/sp-teams/SKILL.md",
        ".specify/config.json",
        ".specify/teams/README.md",
        ".specify/teams/runtime.json",
    )

    for rel_path in expected_owned_paths:
        assert (tmp_path / rel_path).exists()
        assert rel_path in manifest.files


def test_codex_uninstall_removes_team_assets_and_restores_existing_configs(tmp_path):
    from specify_cli.codex_team import install_codex_team_assets
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest

    existing_specify_config = '{"custom": true}\n'
    existing_codex_config = 'model = "gpt-test"\n'
    (tmp_path / ".specify").mkdir()
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".specify" / "config.json").write_text(existing_specify_config, encoding="utf-8")
    (tmp_path / ".codex" / "config.toml").write_text(existing_codex_config, encoding="utf-8")

    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(tmp_path, manifest)
    install_codex_team_assets(tmp_path, manifest, integration_key="codex")

    removed, skipped = integration.uninstall(tmp_path, manifest)

    removed_rel = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in removed}
    assert ".specify/teams/runtime.json" in removed_rel
    assert ".specify/teams/README.md" in removed_rel
    assert ".specify/teams/install-state.json" in removed_rel
    assert skipped == []
    assert (tmp_path / ".specify" / "config.json").read_text(encoding="utf-8") == existing_specify_config
    assert (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8") == existing_codex_config


class TestCodexIntegration:
    KEY = "codex"
    CONTEXT_FILE = "AGENTS.md"

    def test_init_bootstrapped_context_file_contains_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app
        import os

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
        _assert_compact_managed_context(content)

    def test_codex_generated_skills_do_not_include_obsolete_cognition_addenda(self, tmp_path):
        from specify_cli.integrations import get_integration
        from specify_cli.integrations.manifest import IntegrationManifest

        integration = get_integration(self.KEY)
        manifest = IntegrationManifest(self.KEY, tmp_path)
        integration.setup(tmp_path, manifest)

        skills_dir = tmp_path / ".codex" / "skills"
        generated = "\n".join(path.read_text(encoding="utf-8").lower() for path in skills_dir.glob("**/SKILL.md"))
        cognition_policy = "\n".join(
            _extract_generated_cognition_policy(path.read_text(encoding="utf-8"))
            for path in skills_dir.glob("**/SKILL.md")
        )

        assert "project-cognition query" in generated
        assert "minimal_live_reads" in generated
        for phrase in STALE_COGNITION_ADDENDUM_PHRASES:
            assert phrase not in cognition_policy


class TestCodexAutoPromote:
    """--ai codex auto-promotes to integration path."""

    def test_ai_codex_without_ai_skills_auto_promotes(self, tmp_path):
        """--ai codex should work the same as --integration codex."""
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "test-proj"
        result = runner.invoke(app, ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"])

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"
        assert (target / ".codex" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (target / ".codex" / "skills" / "sp-teams" / "SKILL.md").exists()
        assert (target / ".codex" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()
        assert (target / ".codex" / "skills" / "spec-kit-project-cognition-gate" / "SKILL.md").exists()
        assert not (target / ".codex" / "skills" / "spec-kit-project-map-gate").exists()
        assert (target / ".specify" / "teams" / "runtime.json").exists()
        assert (target / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (target / ".specify" / "project-cognition").is_dir()
        assert not (target / ".specify" / "project-cognition" / "status.json").exists()
        assert not (target / ".specify" / "templates" / "project-map").exists()
        assert not (target / ".specify" / "project-map").exists()
        cognition_helper = target / ".specify" / "scripts" / "bash" / "project-cognition-freshness.sh"
        assert cognition_helper.exists()
        cognition_helper_text = cognition_helper.read_text(encoding="utf-8")
        assert ".specify/project-map" not in cognition_helper_text
        assert "project-map-freshness" not in cognition_helper_text
        assert "project-cognition" in cognition_helper_text
        assert not (target / ".specify" / "scripts" / "bash" / "project-map-freshness.sh").exists()

        _assert_compact_managed_context((target / "AGENTS.md").read_text(encoding="utf-8"))
        _assert_stable_subagent_contract(
            (target / ".codex" / "skills" / "subagent-driven-development" / "SKILL.md").read_text(
                encoding="utf-8"
            )
        )

    def test_codex_init_installs_lightweight_discussion_recovery_contract(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "codex-discussion-recovery"
        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

        skill_content = (target / ".codex" / "skills" / "sp-discussion" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        command_template = (target / ".specify" / "templates" / "commands" / "discussion.md").read_text(
            encoding="utf-8"
        )
        state_template = (target / ".specify" / "templates" / "discussion-state-template.md").read_text(
            encoding="utf-8"
        )
        handoff_template = json.loads(
            (target / ".specify" / "templates" / "brainstorming-handoff-specify-template.json").read_text(
                encoding="utf-8"
            )
        )
        generated_discussion = "\n".join([skill_content, command_template])
        generated_lower = generated_discussion.lower()

        assert "Turn Classifier" in generated_discussion
        assert "Question Evidence Gate" in generated_discussion
        assert "Cognition Advisory, Code Authority" in generated_discussion
        assert "project-cognition lexicon --intent discussion" in generated_discussion
        assert "project-cognition query --intent discussion" in generated_discussion
        assert "project-cognition query --intent plan" not in generated_discussion
        assert "ordinary turns append" in generated_lower
        assert "semantic checkpoints" in generated_lower
        assert "draft handoff package can be produced" in generated_lower
        assert "complete handoff package can be produced" not in generated_lower
        assert "confirmed unified handoff pair" not in generated_lower

        assert "latest_event_checkpoint:" in state_template
        assert "latest_cognition_readiness:" in state_template
        assert "handoff-to-specify.md draft after explicit user request and boundary lock" in state_template

        source_contract = handoff_template["source_evidence_contract"]
        assert source_contract["required_fields"] == [
            "source_type",
            "evidence_status",
            "source",
            "claim",
        ]
        assert "project_cognition_route" in source_contract["optional_fields"]
        assert "live_code_evidence" in source_contract["optional_fields"]
        assert source_contract["authority_rule"] == (
            "Project cognition navigates; live repository evidence proves current behavior."
        )


def test_codex_team_template_comes_from_shared_commands_dir(monkeypatch, tmp_path):
    """Codex must discover team.md from the packaged shared commands directory."""
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.base import IntegrationBase

    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "plan.md").write_text("---\ndescription: plan\n---\nbody\n", encoding="utf-8")
    (commands_dir / "team.md").write_text("---\ndescription: team\n---\nbody\n", encoding="utf-8")

    monkeypatch.setattr(IntegrationBase, "shared_commands_dir", lambda self: commands_dir)

    templates = CodexIntegration().list_command_templates()

    assert commands_dir / "plan.md" in templates
    assert commands_dir / "team.md" in templates


def test_codex_generated_sp_implement_teams_skill_exists_and_is_codex_only(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-implement-teams"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-implement-teams" / "SKILL.md"
    assert skill_path.exists()

    content = skill_path.read_text(encoding="utf-8")
    lower = content.lower()
    assert "codex-only" in lower
    assert "psmux" in lower
    assert "native windows" in lower
    assert "sp-teams" in lower
    assert "sp.agent-teams.run" not in lower
    assert "primary product surface" in lower or "primary surface" in lower
    assert "specify extension add agent-teams" not in lower
    assert "shared contract with `sp-implement`" in lower
    assert "canonical implementation workflow" in lower
    assert "implement-tracker.md" in lower
    assert "execution-state source of truth" in lower
    assert "workertaskpacket" in lower
    assert "sp-teams doctor" in lower
    assert "sp-teams live-probe" in lower
    assert "execution_model" in lower
    assert "dispatch_shape" in lower
    assert "execution_surface" in lower
    assert "join point" in lower
    assert "subagent result contract" in lower
    assert "result file handoff path" in lower
    assert ".specify/teams/state/results/<request-id>.json" in lower
    assert "core implementation complete" in lower
    assert "ready for integration testing" in lower
    assert "overall feature completion" in lower
    assert "e2e" in lower
    assert "polish" in lower
    assert "explicit execution packet shape" in lower or "explicit execution packet" in lower
    assert "write set and shared surfaces" in lower
    assert "explicit verification command or acceptance check" in lower
    assert "completion-handoff protocol" in lower
    assert "platform guardrails" in lower
    assert "status flip alone" in lower
    assert "validation target" in lower
    assert "stale lane" in lower
    assert "if the current feature already has an active runtime session, resume or reuse it" in lower
    assert "do not create a second runtime team for the same feature" in lower
    assert "after each completed join point or ready batch, re-read the tracker and task state" in lower
    assert "select the next ready batch and continue automatically" in lower
    assert "stop only when no ready work remains, a real blocker stops progress, or an explicit human gate is reached" in lower
    assert "planned validation tasks are still ready work" in lower
    assert "do not stop to ask whether validation should start" in lower
    assert "check-prerequisites.sh --json --require-tasks --include-tasks" in lower
    assert "parse `feature_dir` and `available_docs` list" in lower
    assert "all paths must be absolute" in lower


def test_codex_generated_passive_subagent_skills_include_stable_dispatch_contract(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-passive-dispatch"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".codex" / "skills"
    routing = (skills_dir / "spec-kit-workflow-routing" / "SKILL.md").read_text(encoding="utf-8").lower()
    subagent = (skills_dir / "subagent-driven-development" / "SKILL.md").read_text(encoding="utf-8").lower()
    parallel = (skills_dir / "dispatching-parallel-agents" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "do not auto-enter an `sp-*` workflow unless the user invokes it" in routing
    assert "you may recommend a" in routing
    assert "natural-language tasks" in routing
    assert "always-on" in routing
    assert "project cognition and project memory" in routing
    assert "red flags" in routing

    assert "native subagents" in subagent
    assert "validated `workertaskpacket`" in subagent
    assert "must not dispatch from raw task text" in subagent
    assert "spec compliance review" in subagent
    assert "code quality review" in subagent
    assert "`sp-teams` only" in subagent

    assert "2+ independent lanes" in parallel
    assert "current runtime" in parallel
    assert "native subagents" in parallel
    assert "write-set" in parallel
    assert "structured handoff" in parallel
    assert "separate terminal" in parallel
    assert "advise the user to run multiple parallel instances" not in parallel


def test_codex_generated_skills_render_launcher_backed_runtime_commands(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-launcher-render"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    constitution_content = (target / ".codex" / "skills" / "sp-constitution" / "SKILL.md").read_text(encoding="utf-8")
    implement_content = (target / ".codex" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")
    quick_content = (target / ".codex" / "skills" / "sp-quick" / "SKILL.md").read_text(encoding="utf-8")

    assert "learning start --command constitution --format json" in constitution_content
    assert "{{specify-subcmd:" not in constitution_content

    for content in (implement_content, quick_content):
        assert "WorkerTaskPacket" in content
        assert "structured handoff" in content.lower()
        assert "{{specify-subcmd:hook" not in content

    assert "{{specify-subcmd:" not in implement_content
    assert "{{specify-subcmd:" not in quick_content

    routine_hook_guidance = (
        "hook validate-state --command implement",
        "hook validate-session-state --command implement",
        "hook validate-packet --packet-file",
        "hook validate-state --command quick",
        "hook validate-session-state --command quick",
        "hook monitor-context --command quick",
        "hook checkpoint --command quick",
    )
    for fragment in routine_hook_guidance:
        assert fragment not in implement_content
        assert fragment not in quick_content


def test_codex_implement_teams_template_keeps_only_backend_specific_guidance():
    template = Path("templates/commands/implement-teams.md").read_text(encoding="utf-8")

    assert "## Shared Contract With `sp-implement`" not in template
    assert "scripts:" in template
    assert "--require-tasks --include-tasks" in template
    assert "Run `{SCRIPT}` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS` list." in template
    assert "sp-teams doctor" in template
    assert "sp-teams live-probe" in template
    assert "validation target" in template.lower()
    assert "stale lane" in template.lower()


def test_codex_generated_sp_implement_includes_native_spawn_agent_routing(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-auto-parallel"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-implement" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    leader_gate_idx = content.find("## Codex Leader Gate")
    outline_idx = content.find("## Outline")
    auto_parallel_idx = content.find("## Codex Subagents-First Execution")

    assert leader_gate_idx != -1 or "## Orchestration Model" in content
    assert outline_idx != -1
    assert auto_parallel_idx == -1 or leader_gate_idx < outline_idx < auto_parallel_idx
    assert "feature_dir/implement-tracker.md" in content.lower()
    assert "execution-state source of truth" in content.lower()
    assert "lexicon --intent implement" in content.lower()
    assert "query --intent implement" in content.lower()
    assert "--query-plan" in content.lower()
    assert "minimal_live_reads" in content.lower()
    assert "build-handbook.md" not in content.lower()
    assert "build-workflow-contract" not in content.lower()
    assert "product-and-capability-map" not in content.lower()
    assert "change-entrypoints" not in content.lower()
    assert "first-class implementation context" in content.lower()
    assert "user execution notes" in content.lower()
    assert "resume_decision" in content.lower()
    assert "leader and orchestrator" in content.lower()
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "invoking runtime acts as the leader" in content
    assert "Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready" in content
    assert "dispatch `parallel-subagents` when multiple validated packets have isolated write sets" in content
    assert "selects the next executable phase and ready batch" in content
    assert "map-update" in content.lower()
    assert "completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs" in content.lower()
    assert "project cognition can support route selection but cannot be the sole evidence for completion" in content.lower()
    assert "including unresolved `open_gaps`" in content.lower()
    assert "shared implement template is the primary source of truth" in content
    assert "join point" in content.lower()
    assert "retry-pending" in content.lower() or "retry pending" in content.lower()
    assert "blocker" in content.lower()
    assert "once one safe lane clears the subagent-readiness bar" in content.lower()
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in content
    assert "`research_gap`" in content
    assert "`plan_gap`" in content
    assert "`spec_gap`" in content
    assert "subagent execution" in content.lower()
    assert "prefer `execution_surface: native-subagents`" in content or "spawn_agent" in content
    assert "sp-teams" not in content.lower()
    assert "must not edit implementation files directly while subagent execution is active" in content.lower()
    assert "wait for every subagent's structured handoff" in content.lower()
    assert "do not treat an idle subagent as done work" in content.lower()
    assert "Mark `subagent-blocked` and stop if any dispatch-blocking runtime condition is present" in content
    assert "Do not use leader-inline execution as a fallback for any dispatch-blocking condition." in content
    assert "A lane is dispatch-ready only if its validated `WorkerTaskPacket` includes" in content
    assert "If any required packet field is missing, do not dispatch and do not execute inline." in content
    assert "The only legal action is to repair the packet or stop as `subagent-blocked`." in content
    assert "Dispatch failure is not permission to continue locally." in content
    assert "Do not persist native subagent dispatch failures" in content
    assert "without writing a durable fallback decision to `implement-tracker.md`" in content
    assert "Dispatch Fallback" not in content
    assert "actual_surface: leader-inline" not in content
    assert "max_parallel_subagents = 4" in content
    assert "implement-slot-1" in content
    assert "current selected wave" in content
    assert "at most four validated isolated lanes" in content
    assert "more than four dispatch-ready isolated lanes" in content
    assert "execute multiple waves" in content
    assert "launch all selected lanes in the current `parallel-subagents` wave before waiting" in content
    assert "whole ready parallel batch" in content
    assert "current batch, `wait_agent` to join them" not in content


def test_codex_generated_shared_workflow_skills_include_native_spawn_agent_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-shared-routing"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".codex" / "skills"
    for skill_name in ("sp-specify",):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
        assert "dispatch_shape: one-subagent | parallel-subagents" in content
        assert "execution_surface: native-subagents" in content
        assert "spawn_agent" in content
        assert "wait_agent" in content
        assert ".specify/project-cognition/" in content
        assert ".specify/memory/project-rules.md" in content
        assert ".specify/memory/learnings/index.md" in content
        assert "future senior engineer" in content
        assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
        assert "if collaboration is justified" not in content
        assert "would benefit from them" not in content
        assert "make the next path explicit" not in content
    for skill_name in ("sp-plan", "sp-tasks"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "execution_model: adaptive" in content
        assert "execution_mode: light | standard | heavy" in content
        assert "workflow_status: ready | blocked" in content
        assert "execution_surface: leader-inline | native-subagents | none" in content
        assert "codex adaptive dispatch" in content
        assert "apply the adaptive dispatch decision recorded by `choose_subagent_dispatch`" in content
        assert "capability_degraded: true" in content
        assert "dispatch_shape: subagent-blocked" in content
        assert "execution_surface: none" in content
        assert "subagents-first dispatch model" not in content
        assert "leader-inline-fallback" not in content
        assert "execution model: `subagents-first`" not in content
        assert ".specify/project-cognition/" in content
        assert ".specify/memory/project-rules.md" in content
        assert ".specify/memory/learnings/index.md" in content
        assert "future senior engineer" in content
        assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
        assert "if collaboration is justified" not in content
        assert "would benefit from them" not in content
        assert "make the next path explicit" not in content

    implement_content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "execution_model: subagent-mandatory" in implement_content or "execution model: `subagents-first`" in implement_content
    assert "dispatch_shape: one-subagent | parallel-subagents" in implement_content
    assert "execution_surface: native-subagents" in implement_content
    assert "spawn_agent" in implement_content
    assert "wait_agent" in implement_content
    assert "close_agent" in implement_content
    assert "sp-teams" not in implement_content

    shared_skills = ("sp-specify", "sp-plan", "sp-tasks")
    for skill_name in shared_skills:
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "specify team" not in content
        assert "workflow-state.md" in content
        assert "workflow_state_file" in content
        assert "re-read `workflow_state_file`" in content or "re-read `workflow-state-file`" in content

    assert not (skills_dir / "sp-test-scan" / "SKILL.md").exists()
    assert not (skills_dir / "sp-test-build" / "SKILL.md").exists()

    prd_content = (skills_dir / "sp-prd" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "deprecated compatibility entrypoint" in prd_content
    assert "sp-prd-scan -> sp-prd-build" in prd_content
    assert "do not describe `sp-prd` as the preferred workflow" in prd_content

    prd_scan_content = (skills_dir / "sp-prd-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "current repository reality" in prd_scan_content
    assert ".specify/prd-runs/<run-id>/" in prd_scan_content
    assert "capability triage" in prd_scan_content
    assert "critical depth gate" in prd_scan_content
    assert "reconstruction-grade scan package" in prd_scan_content
    assert "evidence label gate" in prd_scan_content

    prd_build_content = (skills_dir / "sp-prd-build" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "reverse coverage validation" in prd_build_content
    assert "no new facts gate" in prd_build_content

    constitution_content = (skills_dir / "sp-constitution" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert ".specify/memory/project-rules.md" in constitution_content
    assert ".specify/memory/learnings/index.md" in constitution_content
    assert "future senior engineer" in constitution_content
    assert ".planning/learnings/candidates.md" not in constitution_content or "compatibility" in constitution_content
    assert "learning start --command constitution --format json" in constitution_content
    assert ".specify/project-cognition/status.json" in constitution_content
    assert "build-handbook.md" not in constitution_content
    assert ".specify/project-map/index/status.json" not in constitution_content
    assert "/sp-map-scan" in constitution_content
    assert "/sp-map-build" in constitution_content
    assert "workflow-state.md" in constitution_content
    assert "/sp-plan" in constitution_content
    assert "/sp-tasks" in constitution_content
    assert "/sp-analyze" in constitution_content


def test_codex_question_driven_skills_prefer_request_user_input_with_fallback(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    for skill_name in ("sp-specify", "sp-clarify", "sp-checklist", "sp-quick"):
        content = (target / ".codex" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "request_user_input" in content
        assert "if the current codex runtime exposes it" in lower
        assert "must use it" in lower
        assert "do not render the textual fallback block" in lower
        assert "do not self-authorize textual fallback" in lower
        assert "recommended option first" in lower
        assert "fall back immediately" in lower or "fall back to the" in lower

    quick_content = (target / ".codex" / "skills" / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "--discuss" in quick_content
    assert "multiple unfinished quick tasks exist" in quick_content


def test_codex_generated_skills_preserve_agent_required_marker_lines(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-agent-marker"
    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, result.output

    for skill_name in ("sp-quick", "sp-map-scan", "sp-map-build", "sp-implement", "sp-specify", "sp-prd", "sp-plan", "sp-tasks", "sp-debug"):
        content = (target / ".codex" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[agent]" in content.lower()

    fast_content = (target / ".codex" / "skills" / "sp-fast" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "[agent]" in fast_content
    assert "leader-direct" in fast_content


def test_codex_generated_plan_tasks_implement_skills_preserve_boundary_guardrails(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-boundary-guardrails"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".codex" / "skills"

    plan_content = (skills_dir / "sp-plan" / "SKILL.md").read_text(encoding="utf-8")
    assert "Add `Implementation Constitution`" in plan_content
    assert "`Implementation Constitution` MUST be added if any one of the following conditions is true" in plan_content
    assert "architecture invariants, boundary ownership, forbidden implementation drift" in plan_content
    assert "Promote framework and boundary rules from \"technical background\" into explicit implementation constraints" in plan_content
    assert "Dispatch Compilation Hints" in plan_content
    assert "planning/handoffs/<lane-id>.json" in plan_content
    assert "planning/evidence-index.json" in plan_content
    assert "planning/checkpoints.ndjson" in plan_content
    assert "planning evidence paths when delegated lanes were used" in plan_content
    assert "delegated_planning_lanes: none" in plan_content
    assert "Consume `planning/evidence-index.json` before final synthesis" in plan_content
    assert "Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results" in plan_content
    assert "heuristics" not in plan_content.lower()

    clarify_content = (skills_dir / "sp-clarify" / "SKILL.md").read_text(encoding="utf-8")
    assert "clarification/handoffs/<lane-id>.json" in clarify_content
    assert "clarification/evidence-index.json" in clarify_content
    assert "clarification/checkpoints.ndjson" in clarify_content
    assert "consume `clarification/evidence-index.json` before final artifact updates" in clarify_content.lower()
    assert "do not update `spec.md`, `alignment.md`, `context.md`, or `references.md` from chat-only lane results" in clarify_content.lower()

    tasks_content = (skills_dir / "sp-tasks" / "SKILL.md").read_text(encoding="utf-8")
    assert "Extract `Locked Planning Decisions`, `Implementation Constitution`" in tasks_content
    assert "implementation-guardrails phase before setup" in tasks_content
    assert "locked planning decision or implementation constitution rule" in tasks_content
    assert "Task Guardrail Index" in tasks_content
    assert "task-generation/handoffs/<lane-id>.json" in tasks_content
    assert "task-generation/evidence-index.json" in tasks_content
    assert "task-generation/checkpoints.ndjson" in tasks_content
    assert "task-generation evidence paths when delegated lanes were used" in tasks_content
    assert "delegated_task_generation_lanes: none" in tasks_content
    assert "Consume `task-generation/evidence-index.json` before final task synthesis" in tasks_content
    assert "planning/evidence-index.json and accepted planning/handoffs/*.json" in tasks_content
    assert "Do not synthesize `tasks.md` from chat-only delegated lane results" in tasks_content

    implement_content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")
    assert "Extract `Implementation Constitution` from `plan.md`" in implement_content
    assert "What framework or boundary pattern owns the touched surface?" in implement_content
    assert "Which files define the existing pattern that must be preserved?" in implement_content
    assert "What implementation drift is forbidden for this batch?" in implement_content
    assert "Boundary-pattern preservation" in implement_content
    assert "compile and validate the packet before any subagent work begins" in implement_content
    assert "validated `WorkerTaskPacket`" in implement_content
    assert "dispatch only from validated `workertaskpacket`" in implement_content.lower() or "raw task text alone" in implement_content.lower()

    analyze_content = (skills_dir / "sp-analyze" / "SKILL.md").read_text(encoding="utf-8")
    assert "Boundary Guardrail Gaps" in analyze_content
    assert "BG1" in analyze_content
    assert "BG2" in analyze_content
    assert "BG3" in analyze_content
    assert "DP1" in analyze_content
    assert "DP2" in analyze_content
    assert "DP3" in analyze_content
    assert "Boundary Guardrail Table" in analyze_content
    assert "Closed-loop requirement" in analyze_content
    assert "Recommended Re-entry" in analyze_content
    assert "Blocker Bundle" in analyze_content
    assert "fingerprint-first" in analyze_content.lower()
    assert "missed_by_previous_analyze" in analyze_content
    assert "No more than one task-layer remediation cycle is expected" in analyze_content
    assert "This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`." in analyze_content
    assert "workflow-state.md" in analyze_content
    assert "analysis-only" in analyze_content.lower()
    assert "`next_command: /sp.implement`" in analyze_content
    assert "If the highest invalid stage is `clarify`" in analyze_content
    assert "planning/evidence-index.json" in analyze_content
    assert "task-generation/evidence-index.json" in analyze_content
    assert "accepted planning handoff with no downstream consumer" in analyze_content.lower()
    assert "accepted task-generation handoff with no downstream consumer" in analyze_content.lower()
    assert "non-destructive cross-artifact consistency and boundary-guardrail analysis" in analyze_content.lower()
    assert "re-entry chain" in analyze_content.lower()


def test_codex_generated_sp_map_scan_build_include_native_mapping_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-map-scan-build"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    scan_content = (target / ".codex" / "skills" / "sp-map-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
    build_content = (target / ".codex" / "skills" / "sp-map-build" / "SKILL.md").read_text(encoding="utf-8").lower()
    update_content = (target / ".codex" / "skills" / "sp-map-update" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert not (target / ".codex" / "skills" / "sp-map-codebase" / "SKILL.md").exists()

    assert ".specify/project-cognition/" in scan_content
    assert ".specify/project-cognition/evidence/" in scan_content
    assert ".specify/project-cognition/provisional/nodes.json" in scan_content
    assert ".specify/project-cognition/provisional/edges.json" in scan_content
    assert ".specify/project-cognition/provisional/observations.json" in scan_content
    assert ".specify/project-cognition/coverage.json" in scan_content
    assert 'choose_subagent_dispatch(command_name="map-scan"' in scan_content
    assert "evidence" in scan_content
    assert "coverage" in scan_content
    assert "spawn_agent" in scan_content
    assert "wait_agent" in scan_content
    assert "close_agent" in scan_content
    assert "provisional" in scan_content

    assert ".specify/project-cognition/project-cognition.db" in build_content
    assert "lexicon --intent implement" in build_content
    assert "query --intent implement" in build_content
    assert "--query-plan" in build_content
    assert 'choose_subagent_dispatch(command_name="map-build"' in build_content
    assert "raw graph json artifacts or slices as runtime truth" in build_content
    assert "spawn_agent" in build_content
    assert "wait_agent" in build_content
    assert "close_agent" in build_content
    assert "project cognition" in build_content
    assert "confidence" in build_content
    assert "conflict" in build_content

    assert "sp-map-update" in update_content
    assert "project-cognition" in update_content
    assert "spawn_agent" in update_content
    assert "wait_agent" in update_content
    assert "diff impact closure" in update_content
    assert "affected claim refresh" in update_content
    assert "user supplement normalization" in update_content
    assert "conflict reconciliation" in update_content
    assert "prefer the smallest executable update lane set" in update_content
    assert "user-supplied scope remains authoritative unless repository evidence disproves it" in update_content
    assert "do not turn a one-slice or metadata-only refresh into scan-style parallel exploration" in update_content
    assert "leader-inline-fallback for a one-lane update is preferred over forcing extra subagents" in update_content


def test_codex_generated_sp_debug_includes_leader_led_native_investigation_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-debug-routing"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-debug" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/learnings/index.md" in content
    assert "future senior engineer" in content
    assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
    assert "codex subagent evidence collection" in content
    assert "lexicon --intent debug" in content
    assert "query --intent debug" in content
    assert "--query-plan" in content
    assert "minimal_live_reads" in content
    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "small focused investigation" in content
    assert "subagent-assisted" in content
    assert "execution_surface: none" in content
    assert "debug-handbook.md" not in content
    assert "debug-workflow-contract" not in content
    assert "symptom-to-surface-routing" not in content
    assert "system-topology-for-debug" not in content
    assert "observer framing" in content
    assert "map-backed minimum intake" in content
    assert "deep debug intake dispatch" in content
    assert "stage 1a: causal map" in content
    assert "same_issue" in content
    assert "derived_issue" in content
    assert "unrelated_issue" in content
    assert "contrarian candidate" in content
    assert "the think subagent must not read source files" in content
    assert "the think subagent must not inspect logs" in content
    assert "primary suspected loop" in content
    assert "alternative cause candidates" in content
    assert "transition memo" in content
    assert "if cognition freshness is `missing`, continue with live repository evidence" in content
    assert "recommend `$sp-map-scan`, then `$sp-map-build` as follow-up map maintenance" in content
    assert "if cognition freshness is `stale`, treat map output as advisory" in content
    assert "truth-owning layers" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "investigating" in content
    assert "debug file" in content
    assert "evidence-gathering" in content or "evidence gathering" in content
    assert "diagnostic_profile" in content
    assert "scheduler-admission" in content or "evidence-gathering" in content
    assert "must not update the debug file" in content
    assert "wait for every subagent's structured handoff" in content
    assert "do not treat an idle subagent as done work" in content
    assert "candidate queue" in content
    assert "root-cause mode" in content


def test_codex_generated_specify_skill_mentions_source_sweep_and_reopen(tmp_path):
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    target = tmp_path / "codex-specify"
    integration = CodexIntegration()
    manifest = IntegrationManifest("codex", target)
    integration.setup(target, manifest)
    content = (target / ".codex" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "source_signal_disposition" in content
    assert "source_files_read" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
    assert "reopen" in content
    assert "brainstorming kernel" not in content
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content


def test_codex_generated_sp_specify_uses_simplified_flow_wording(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-specify-brainstorming"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    content = (target / ".codex" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "two or three approaches" in lowered or "2-3 approaches" in lowered
    assert "semantic term" in lowered
    assert "source_signal_disposition" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
    assert "reopen" in lowered
    assert "brainstorming kernel" not in lowered
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content
    assert "task classification" not in lowered
    assert "active_profile" not in content
    assert "coverage_mode" not in content
    assert "observer gate" not in lowered
    assert "leader-inline-fallback" not in lowered


def test_codex_generated_implement_skill_mentions_optimization_scope_and_reopen(tmp_path):
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    target = tmp_path / "codex-implement"
    integration = CodexIntegration()
    manifest = IntegrationManifest("codex", target)
    integration.setup(target, manifest)
    content = (target / ".codex" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "allowed optimization scope" in content
    assert "must-preserve invariants" in content
    assert "reopen" in content


def test_codex_debug_skill_prefers_request_user_input_with_fallback(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-debug-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    content = (target / ".codex" / "skills" / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "request_user_input" in content
    assert "native structured question tool" in content
    assert "missing-information question" in content or "plain-text clarification" in content


def test_codex_generated_sp_fast_stays_inline_and_lightweight(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-fast-task"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-fast" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert "scope gate" in content
    assert "skip all learning hooks" in content
    assert "do not read constitution, project-rules, or project-learnings" in content
    assert "leave `.specify/memory/learnings/index.md`" in content
    assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
    assert "lexicon --intent implement" in content
    assert "query --intent implement" in content
    assert "--query-plan" in content
    assert "minimal_live_reads" in content
    assert "build-handbook.md" not in content
    assert "shared surfaces" in content
    assert "cognition gate" in content
    assert "≤3 files touched" in content or "at most 3 files" in content or "no more than 3 files" in content
    assert "no dependency changes" in content
    assert "the leader performs the change directly" in content or "leader-direct" in content
    assert "verify" in content
    assert "completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs" in content
    assert "project cognition can support route selection but cannot be the sole evidence for completion" in content
    assert "map-update" in content
    assert "do not call `project-cognition mark-dirty`" in content
    assert "do not create spec.md" in content or "no spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "leader-direct" in content or "the leader performs the change directly" in content


def test_codex_generated_sp_quick_supports_lightweight_tracked_execution(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-quick-task"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-quick" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".planning/quick/" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/learnings/index.md" in content
    assert "future senior engineer" in content
    assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
    assert "lexicon --intent implement" in content
    assert "query --intent implement" in content
    assert "--query-plan" in content
    assert "minimal_live_reads" in content
    assert "build-handbook.md" not in content
    assert "build-workflow-contract" not in content
    assert "product-and-capability-map" not in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "lightweight" in content
    assert "summary.md" in content or "summary artifact" in content
    assert "codex leader gate" in content
    assert "codex quick-task subagent execution" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "managed-team" in content
    assert "understanding checkpoint" in content
    assert "understanding_confirmed: true" in content
    assert "problem understood" in content
    assert "planned outcome" in content
    assert "scope boundary" in content
    assert "execution approach" in content
    assert "confirmed_validation" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "dispatch to one subagent with a task contract" in content or "one-subagent" in content
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "advisory first pass" in content
    assert "the next concrete action must be dispatch" in content or "once the first lane is chosen" in content
    assert "materially improve throughput" in content
    assert "subagent-blocked" in content
    assert "join point" in content
    assert "leader" in content
    assert "wait for every subagent's structured handoff" in content
    assert "do not treat an idle subagent as done work" in content
    assert ".planning/quick/<id>-<slug>/" in content
    assert ".planning/quick/index.json" in content
    assert "status.md" in content
    assert "current focus" in content
    assert "next action" in content
    assert "completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs" in content
    assert "project cognition can support route selection but cannot be the sole evidence for completion" in content
    assert "map-update" in content
    assert "resume" in content
    assert "resolved/" in content
    assert "status.md template" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "summary pointer" in content
    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
