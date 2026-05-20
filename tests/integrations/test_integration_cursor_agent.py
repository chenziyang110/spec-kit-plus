"""Tests for CursorAgentIntegration."""

from .test_integration_base_skills import SkillsIntegrationTests


class TestCursorAgentIntegration(SkillsIntegrationTests):
    KEY = "cursor-agent"
    FOLDER = ".cursor/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".cursor/skills"
    CONTEXT_FILE = ".cursor/rules/specify-rules.mdc"


def test_cursor_skills_init_installs_command_and_passive_skills(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-skills-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"
    assert (target / ".cursor" / "skills" / "sp-plan" / "SKILL.md").exists()
    assert (target / ".cursor" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()


def test_cursor_generated_sp_quick_prefers_subagent_execution(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-quick-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"

    skill_path = target / ".cursor" / "skills" / "sp-quick" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".specify/memory/constitution.md" in content
    assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "cursor leader gate" in content
    assert "cursor subagent execution" in content
    assert "dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis" in content
    assert "subagent-blocked" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "do **not** perform broad repository analysis" in content
    assert "use cursor's native subagent path for bounded lanes when available" in content
    assert "the next concrete action must be dispatch" in content
    assert "materially improve throughput" in content
    assert "managed-team" in content
    assert "subagent-blocked" in content
    assert "use cursor's native subagent path" in content
    assert "status.md" in content
    assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in content
    assert "attempt the smallest safe recovery step before declaring the task blocked" in content
    assert "retry_attempts" in content
    assert "blocker_reason" in content
    assert "subagent dispatch contract" in content
    assert "subagent result contract" in content
    assert "result handoff path" in content
    assert "done_with_concerns" in content
    assert "needs_context" in content
    assert "workertaskresult" in content
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in content


def test_cursor_runtime_skills_hard_gate_project_cognition_reads(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-project-cognition-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"

    for rel in (
        ".cursor/skills/sp-implement/SKILL.md",
        ".cursor/skills/sp-debug/SKILL.md",
        ".cursor/skills/sp-quick/SKILL.md",
    ):
        content = (target / rel).read_text(encoding="utf-8").lower()
        assert "crucial first step" in content
        assert "map-scan" in content
        assert "map-build" in content
        assert (
            "use map-update for ordinary existing-baseline gaps. use map-scan -> map-build "
            "only for missing or unusable baseline, schema failure, zero active-generation "
            "path_index rows, explicit_rebuild_requested, or baseline_identity_invalid"
        ) in content
        for stale_phrase in (
            "path-index-" + "incomplete",
            "unadoptable " + "coverage gaps",
            "blocked by " + "unadoptable",
            "unadoptable " + "path-index gaps",
        ):
            assert stale_phrase not in content
        if "sp-debug" in rel:
            assert "project-cognition query --intent debug" in content
            assert "debug session state" in content
            assert "debug-handbook.md" not in content
            assert "debug-workflow-contract" not in content
        else:
            assert "project-cognition query --intent implement" in content
            assert "task-local bundle" in content
            assert "minimal_live_reads" in content
            assert "build-handbook.md" not in content
            assert "build-workflow-contract" not in content
