"""Tests for CodexIntegration."""

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
                ".specify/codex-team/README.md",
                ".specify/codex-team/runtime.json",
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
        assert (target / ".codex" / "skills" / "sp-team" / "SKILL.md").exists()
        assert (target / ".specify" / "codex-team" / "runtime.json").exists()
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

    assert templates == [commands_dir / "plan.md", commands_dir / "team.md"]


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
    assert ".specify/project-map/architecture.md" in content.lower()
    assert ".specify/project-map/workflows.md" in content.lower()
    assert ".specify/project-map/operations.md" in content.lower()
    assert "first-class implementation context" in content.lower()
    assert "user execution notes" in content.lower()
    assert "resume_decision" in content.lower()
    assert "you are the **leader**, not the concrete implementer" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "specify team" in content
    assert "single-agent" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "invoking runtime acts as the leader" in content
    assert "single-agent still means one delegated worker lane" in content
    assert "selects the next executable phase and ready batch" in content
    assert "run `/sp-map-codebase` before final completion reporting" in content.lower()
    assert "verification is truthfully green and no explicit blocker prevents completion" in content.lower()
    assert "including unresolved `open_gaps`" in content.lower()
    assert "shared implement template is the primary source of truth" in content
    assert "join point" in content.lower()
    assert "retry-pending" in content.lower() or "retry pending" in content.lower()
    assert "blocker" in content.lower()
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in content
    assert "`research_gap`" in content
    assert "`plan_gap`" in content
    assert "`spec_gap`" in content
    assert "delegated execution" in content.lower() or "delegates execution" in content.lower()
    assert "prefer `native-multi-agent`" in content
    assert "only fall back to `specify team`" in content.lower()
    assert "must not edit implementation files directly while worker delegation is active" in content.lower()


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
    for skill_name in ("sp-specify", "sp-plan", "sp-tasks", "sp-implement", "sp-map-codebase"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "single-agent" in content
        assert "native-multi-agent" in content
        assert "sidecar-runtime" in content
        assert "spawn_agent" in content
        assert "wait_agent" in content
        assert "project-handbook.md" in content
        assert ".specify/project-map/architecture.md" in content
        assert ".specify/project-map/workflows.md" in content

    shared_skills = ("sp-specify", "sp-plan", "sp-tasks")
    for skill_name in shared_skills:
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "specify team" not in content


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
    assert ".specify/project-map/architecture.md" in content
    assert 'choose_execution_strategy(command_name="map-codebase"' in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "complete-refresh" in content
    assert "do not create `.planning/codebase/`" in content


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

    assert "codex native multi-agent investigation" in content
    assert "project-handbook.md" in content
    assert ".specify/project-map/architecture.md" in content
    assert ".specify/project-map/workflows.md" in content
    assert ".specify/project-map/integrations.md" in content
    assert ".specify/project-map/testing.md" in content
    assert ".specify/project-map/operations.md" in content
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
    assert "suggested_evidence_lanes" in content
    assert "decisive control-plane signals" in content
    assert "scheduler-admission" in content
    assert "cache-snapshot" in content
    assert "ui-projection" in content
    assert "source-of-truth state" in content
    assert "queue contents" in content
    assert "must not update the debug file" in content
    assert "leader" in content
    assert "if the active session is `awaiting_human_verify`" in content
    assert "start a linked follow-up session" in content
    assert "record the parent/child relationship" in content
    assert "return to the parent session to finish the original human verification" in content
    assert "if automated verification or human verification fails repeatedly" in content
    assert ".planning/debug/[slug].research.md" in content
    assert "debug-local research checkpoint" in content
    assert "if a join-point `wait_agent` returns no completed agents" in content
    assert "continue the leader's local investigation path instead of issuing another blind wait" in content
    assert "send_input" in content
    assert "interrupt=true" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-codebase` before moving to `awaiting_human_verify` or `resolved`" in content
    assert "3-5 strongest facts" in content or "3 to 5 strongest facts" in content


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
    assert "specify team" in content
    assert "single-agent" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "single-agent still means one delegated worker lane" in content
    assert "dispatch exactly one delegated worker lane" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "do **not** perform broad repository analysis" in content
    assert "the next concrete action must be dispatch" in content
    assert "materially improve throughput" in content
    assert "local execution is the last fallback" in content
    assert "execution_fallback" in content
    assert "join point" in content
    assert "leader" in content
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
    assert "strategy: single-agent | native-multi-agent | sidecar-runtime" in content
    assert "summary pointer" in content
    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
