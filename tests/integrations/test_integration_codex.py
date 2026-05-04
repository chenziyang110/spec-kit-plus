"""Tests for CodexIntegration."""

from pathlib import Path

from .test_integration_base_skills import SkillsIntegrationTests


def _assert_stable_subagent_contract(content: str) -> None:
    lower = content.lower()

    assert "1% chance" in lower
    assert "before any response or action" in lower
    assert "native subagents" in lower
    assert "validated `workertaskpacket`" in lower
    assert "structured handoff" in lower
    assert "`sp-teams` only" in lower


class TestCodexIntegration(SkillsIntegrationTests):
    KEY = "codex"
    FOLDER = ".codex/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".codex/skills"
    CONTEXT_FILE = "AGENTS.md"

    def _expected_files(self, script_variant: str) -> list[str]:
        files = super()._expected_files(script_variant)
        files.extend(
            [
                ".codex/config.toml",
                ".specify/config.json",
                ".specify/teams/README.md",
                ".specify/teams/runtime.json",
            ]
        )
        return sorted(files)


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
        assert (target / ".codex" / "skills" / "spec-kit-project-map-gate" / "SKILL.md").exists()
        assert (target / ".specify" / "teams" / "runtime.json").exists()
        assert (target / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (target / ".specify" / "templates" / "project-map" / "ARCHITECTURE.md").exists()
        assert (target / ".specify" / "templates" / "project-map" / "OPERATIONS.md").exists()
        assert (target / ".specify" / "project-map" / "status.json").exists()

        _assert_stable_subagent_contract((target / "AGENTS.md").read_text(encoding="utf-8"))


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

    assert "1% chance" in routing
    assert "before any response or action" in routing
    assert "clarifying question" in routing
    assert "file read" in routing
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

    assert "learning start --command constitution --format json" in constitution_content
    assert "validate-state --command implement" in implement_content
    assert "validate-session-state --command implement" in implement_content
    assert "{{specify-subcmd:" not in constitution_content
    assert "{{specify-subcmd:" not in implement_content


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
    assert "project-handbook.md" in content.lower()
    assert ".specify/project-map/root/architecture.md" in content.lower()
    assert ".specify/project-map/root/workflows.md" in content.lower()
    assert ".specify/project-map/root/operations.md" in content.lower()
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
    assert "run `/sp-map-scan` followed by `/sp-map-build` before final completion reporting" in content.lower()
    assert "verification is truthfully green and no explicit blocker prevents completion" in content.lower()
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
    for skill_name in ("sp-specify", "sp-plan", "sp-test-scan", "sp-test-build", "sp-tasks"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
        assert "dispatch_shape: one-subagent | parallel-subagents" in content
        assert "execution_surface: native-subagents" in content
        assert "spawn_agent" in content
        assert "wait_agent" in content
        assert "project-handbook.md" in content
        assert ".specify/project-map/root/architecture.md" in content
        assert ".specify/project-map/root/workflows.md" in content
        assert ".specify/memory/project-rules.md" in content
        assert ".specify/memory/project-learnings.md" in content
        assert ".planning/learnings/candidates.md" in content

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

    test_scan_content = (skills_dir / "sp-test-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "testscanpacket" in test_scan_content
    assert "read-only scout work" in test_scan_content
    assert "spawn_agent" in test_scan_content
    assert "wait_agent" in test_scan_content
    assert "test_build_plan.json" in test_scan_content

    test_build_content = (skills_dir / "sp-test-build" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "testbuildpacket" in test_build_content
    assert "manually execute the canonical test commands" in test_build_content
    assert "most recent manual validation run" in test_build_content
    assert "run coverage after the first meaningful test pass" in test_build_content
    assert "iterate on uncovered critical paths" in test_build_content
    assert "spawn_agent" in test_build_content
    assert "wait_agent" in test_build_content

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
    assert ".specify/memory/project-learnings.md" in constitution_content
    assert ".planning/learnings/candidates.md" in constitution_content
    assert "learning start --command constitution --format json" in constitution_content
    assert "project-handbook.md" in constitution_content
    assert ".specify/project-map/index/status.json" in constitution_content
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
    assert "[agent]" not in fast_content
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
    assert "architecture invariants, boundary ownership, forbidden implementation drift" in plan_content
    assert "Promote framework and boundary rules from \"technical background\" into explicit implementation constraints" in plan_content
    assert "Dispatch Compilation Hints" in plan_content

    tasks_content = (skills_dir / "sp-tasks" / "SKILL.md").read_text(encoding="utf-8")
    assert "Extract `Locked Planning Decisions`, `Implementation Constitution`" in tasks_content
    assert "implementation-guardrails phase before setup" in tasks_content
    assert "locked planning decision or implementation constitution rule" in tasks_content
    assert "Task Guardrail Index" in tasks_content

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
    assert "This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`." in analyze_content
    assert "workflow-state.md" in analyze_content
    assert "analysis-only" in analyze_content.lower()
    assert "`next_command: /sp.implement`" in analyze_content
    assert "If the highest-impact issue lives in `spec.md` or `context.md`" in analyze_content
    assert "has already started or finished" in analyze_content


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
    assert not (target / ".codex" / "skills" / "sp-map-codebase" / "SKILL.md").exists()

    assert ".specify/project-map/map-scan.md" in scan_content
    assert ".specify/project-map/coverage-ledger.md" in scan_content
    assert ".specify/project-map/coverage-ledger.json" in scan_content
    assert ".specify/project-map/scan-packets/<lane-id>.md" in scan_content
    assert ".specify/project-map/map-state.md" in scan_content
    assert "mapscanpacket" in scan_content
    assert 'choose_subagent_dispatch(command_name="map-scan"' in scan_content
    assert "rg --files" in scan_content
    assert "git-tracked files" in scan_content
    assert "reverse coverage" in scan_content
    assert "spawn_agent" in scan_content
    assert "wait_agent" in scan_content
    assert "close_agent" in scan_content
    assert "do not create `.planning/codebase/`" in scan_content

    assert "project-handbook.md" in build_content
    assert ".specify/project-map/index/atlas-index.json" in build_content
    assert ".specify/project-map/root/architecture.md" in build_content
    assert ".specify/project-map/modules/<module-id>/overview.md" in build_content
    assert 'choose_subagent_dispatch(command_name="map-build"' in build_content
    assert "route back to `/sp-map-scan`" in build_content
    assert "mapbuildpacket" in build_content
    assert ".specify/project-map/worker-results/<packet-id>.json" in build_content
    assert "spawn_agent" in build_content
    assert "wait_agent" in build_content
    assert "close_agent" in build_content
    assert "complete-refresh" in build_content
    assert "root and module document detail rules" in build_content
    assert "root docs carry cross-module truth; module docs carry module-local truth" in build_content
    assert "`project-handbook.md` must stay concise and index-first" in build_content
    assert "minimum verification" in build_content
    assert "confidence" in build_content


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
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "codex subagent evidence collection" in content
    assert "project-handbook.md" in content
    assert ".specify/project-map/root/architecture.md" in content
    assert ".specify/project-map/root/workflows.md" in content
    assert ".specify/project-map/root/integrations.md" in content
    assert ".specify/project-map/root/testing.md" in content
    assert ".specify/project-map/root/operations.md" in content
    assert "observer framing" in content
    assert "compressed observer framing" in content
    assert "full observer framing" in content
    assert "same_issue" in content
    assert "derived_issue" in content
    assert "unrelated_issue" in content
    assert "contrarian candidate" in content
    assert "the think subagent must not read source files" in content
    assert "the think subagent must not inspect logs" in content
    assert "primary suspected loop" in content
    assert "alternative cause candidates" in content
    assert "transition memo" in content
    assert "if the handbook navigation system is missing" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before root-cause analysis continues" in content
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
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "project-handbook.md" in content
    assert "shared surfaces" in content
    assert "project-map hard gate" in content
    assert "≤3 files touched" in content or "at most 3 files" in content or "no more than 3 files" in content
    assert "no dependency changes" in content
    assert "the leader performs the change directly" in content or "leader-direct" in content
    assert "verify" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before the final report" in content
    assert "if that refresh would break the fast-path scope" in content
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
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "project-handbook.md" in content
    assert "atlas.entry" in content
    assert "at least one relevant module overview document" in content
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
    assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "dispatch to one subagent with a task contract" in content or "one-subagent" in content
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "crucial first step" in content
    assert "the next concrete action must be dispatch" in content or "once the first lane is chosen" in content
    assert "materially improve throughput" in content
    assert "leader-inline-fallback" in content
    assert "join point" in content
    assert "leader" in content
    assert "wait for every subagent's structured handoff" in content
    assert "do not treat an idle subagent as done work" in content
    assert ".planning/quick/<id>-<slug>/" in content
    assert ".planning/quick/index.json" in content
    assert "status.md" in content
    assert "current focus" in content
    assert "next action" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before marking the quick task `resolved`" in content
    assert "resume" in content
    assert "resolved/" in content
    assert "status.md template" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "summary pointer" in content
    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
