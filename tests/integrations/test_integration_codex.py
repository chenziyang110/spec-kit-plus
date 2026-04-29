"""Tests for CodexIntegration."""

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from .test_integration_base_skills import SkillsIntegrationTests


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
    assert "single-lane" in lower
    assert "native-multi-agent" in lower
    assert "sidecar-runtime" in lower
    assert "join point" in lower
    assert "worker result contract" in lower
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
    auto_parallel_idx = content.find("## Codex Auto-Parallel Execution")

    assert leader_gate_idx != -1
    assert outline_idx != -1
    assert auto_parallel_idx != -1
    assert leader_gate_idx < outline_idx < auto_parallel_idx
    assert "feature_dir/implement-tracker.md" in content.lower()
    assert "execution-state source of truth" in content.lower()
    assert "project-handbook.md" in content.lower()
    assert ".specify/project-map/root/architecture.md" in content.lower()
    assert ".specify/project-map/root/workflows.md" in content.lower()
    assert ".specify/project-map/root/operations.md" in content.lower()
    assert "first-class implementation context" in content.lower()
    assert "user execution notes" in content.lower()
    assert "resume_decision" in content.lower()
    assert "you are the **leader**, not the concrete implementer" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "single-lane" in content
    assert "native-multi-agent" in content
    assert "invoking runtime acts as the leader" in content
    assert "`single-lane` names the topology for one safe execution lane" in content
    assert "does not, by itself, decide whether the leader or a delegated worker executes that lane" in content
    assert "selects the next executable phase and ready batch" in content
    assert "run `/sp-map-codebase` before final completion reporting" in content.lower()
    assert "verification is truthfully green and no explicit blocker prevents completion" in content.lower()
    assert "including unresolved `open_gaps`" in content.lower()
    assert "shared implement template is the primary source of truth" in content
    assert "join point" in content.lower()
    assert "retry-pending" in content.lower() or "retry pending" in content.lower()
    assert "blocker" in content.lower()
    assert "once a `single-lane` batch clears the delegation-readiness bar" in content.lower()
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in content
    assert "`research_gap`" in content
    assert "`plan_gap`" in content
    assert "`spec_gap`" in content
    assert "delegated execution" in content.lower() or "delegates execution" in content.lower()
    assert "prefer `native-multi-agent`" in content
    assert "sp-teams" not in content.lower()
    assert "sidecar-runtime" not in content.lower()
    assert "must not edit implementation files directly while worker delegation is active" in content.lower()
    assert "wait for every delegated lane's structured handoff" in content.lower()
    assert "do not treat an idle child as done work" in content.lower()


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
    for skill_name in ("sp-specify", "sp-plan", "sp-test", "sp-tasks"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "single-lane" in content
        assert "native-multi-agent" in content
        assert "sidecar-runtime" in content
        assert "spawn_agent" in content
        assert "wait_agent" in content
        assert "project-handbook.md" in content
        assert ".specify/project-map/root/architecture.md" in content
        assert ".specify/project-map/root/workflows.md" in content
        assert ".specify/memory/project-rules.md" in content
        assert ".specify/memory/project-learnings.md" in content
        assert ".planning/learnings/candidates.md" in content

    implement_content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "single-lane" in implement_content
    assert "native-multi-agent" in implement_content
    assert "spawn_agent" in implement_content
    assert "wait_agent" in implement_content
    assert "close_agent" in implement_content
    assert "sidecar-runtime" not in implement_content
    assert "sp-teams" not in implement_content

    shared_skills = ("sp-specify", "sp-plan", "sp-tasks")
    for skill_name in shared_skills:
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "specify team" not in content
        assert "workflow-state.md" in content
        assert "workflow_state_file" in content
        assert "re-read `workflow_state_file`" in content or "re-read `workflow-state-file`" in content

    test_content = (skills_dir / "sp-test" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "specify team" not in test_content
    assert "testing-state.md" in test_content
    assert "testing_state_file" in test_content or "testing-state-file" in test_content
    assert "manually execute the canonical test commands" in test_content
    assert "most recent manual validation run" in test_content
    assert "run coverage after the first meaningful test pass" in test_content
    assert "iterate on uncovered critical paths" in test_content

    constitution_content = (skills_dir / "sp-constitution" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert ".specify/memory/project-rules.md" in constitution_content
    assert ".specify/memory/project-learnings.md" in constitution_content
    assert ".planning/learnings/candidates.md" in constitution_content
    assert "specify learning start --command constitution --format json" in constitution_content
    assert "project-handbook.md" in constitution_content
    assert ".specify/project-map/index/status.json" in constitution_content
    assert "/sp-map-codebase" in constitution_content
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

    for skill_name in ("sp-fast", "sp-quick", "sp-map-codebase", "sp-implement", "sp-specify", "sp-plan", "sp-tasks", "sp-debug"):
        content = (target / ".codex" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[AGENT]" in content


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
    assert "compile and validate the packet before any delegated work begins" in implement_content
    assert "validated `WorkerTaskPacket`" in implement_content
    assert "must not dispatch from raw task text alone" in implement_content.lower()

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
    assert "If analysis runs after `/sp-implement` has already started or finished" in analyze_content


def test_codex_generated_sp_map_codebase_includes_native_mapping_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-map-codebase"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-map-codebase" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert "project-handbook.md" in content
    assert ".specify/project-map/index/atlas-index.json" in content
    assert ".specify/project-map/root/architecture.md" in content
    assert ".specify/project-map/modules/<module-id>/overview.md" in content
    assert 'choose_execution_strategy(command_name="map-codebase"' in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "complete-refresh" in content
    assert "do not create `.planning/codebase/`" in content
    assert "layering exists so map consumers can read detail on demand" in content
    assert "do not treat layering as permission to discard technical detail" in content
    assert "external or exported api contracts" in content
    assert "`project-handbook.md` must stay concise and index-first" in content
    assert "macro scan and architecture identification" in content
    assert "directory structure deep analysis" in content
    assert "dependency relationships and module analysis" in content
    assert "core code element review" in content
    assert "data flow and api surface mapping" in content
    assert "patterns and conventions synthesis" in content
    assert "the generated navigation system should collectively cover the equivalent of these seven technical-document chapters" in content
    assert "for each high-value capability, core module, or critical workflow, emit at least one capability card" in content
    assert "truth lives" in content
    assert "extend here" in content
    assert "minimum verification" in content
    assert "failure modes" in content
    assert "confidence" in content
    assert "verified, inferred, or unknown-stale" in content


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
    assert "codex native multi-agent investigation" in content
    assert "project-handbook.md" in content
    assert ".specify/project-map/root/architecture.md" in content
    assert ".specify/project-map/root/workflows.md" in content
    assert ".specify/project-map/root/integrations.md" in content
    assert ".specify/project-map/root/testing.md" in content
    assert ".specify/project-map/root/operations.md" in content
    assert "observer framing" in content
    assert "compressed observer framing" in content
    assert "full observer framing" in content
    assert "do not read source files" in content
    assert "do not inspect logs" in content
    assert "primary suspected loop" in content
    assert "alternative cause candidates" in content
    assert "transition memo" in content
    assert "if the handbook navigation system is missing" in content
    assert "run `/sp-map-codebase` before root-cause analysis continues" in content
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
    assert "wait for every delegated lane's structured handoff" in content
    assert "do not treat an idle child as done work" in content


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
    assert "risky coordination points" in content
    assert "if `project-handbook.md` or `.specify/project-map/` is missing" in content
    assert "redirect to `/sp-quick` so the navigation system can be rebuilt safely" in content
    assert "at most 3 files" in content or "no more than 3 files" in content
    assert "no new dependencies" in content
    assert "do the work directly" in content
    assert "verify" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-codebase` before the final report" in content
    assert "if that refresh would break the fast-path scope" in content
    assert "do not create spec.md" in content or "no spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "do not spawn" in content or "no subagents" in content


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
    assert "topic map" in content
    assert "touched-area topical files" in content
    assert "if `project-handbook.md` or the required `.specify/project-map/` files are missing" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "lightweight" in content
    assert "summary.md" in content or "summary artifact" in content
    assert "codex leader gate" in content
    assert "codex native multi-agent execution" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "sp-teams" in content
    assert "single-lane" in content
    assert "single-lane" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "`single-lane` names the topology for one safe execution lane" in content
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "crucial first step" in content
    assert "the next concrete action must be dispatch" in content or "once the first lane is chosen" in content
    assert "materially improve throughput" in content
    assert "local execution is the last fallback" in content
    assert "execution_fallback" in content
    assert "join point" in content
    assert "leader" in content
    assert "wait for every delegated lane's structured handoff" in content
    assert "do not treat an idle child as done work" in content
    assert ".planning/quick/<id>-<slug>/" in content
    assert ".planning/quick/index.json" in content
    assert "status.md" in content
    assert "current focus" in content
    assert "next action" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-codebase` before marking the quick task `resolved`" in content
    assert "resume" in content
    assert "resolved/" in content
    assert "status.md template" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "strategy: single-lane | native-multi-agent | sidecar-runtime" in content
    assert "summary pointer" in content
    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
