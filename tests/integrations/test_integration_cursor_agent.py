"""Tests for CursorAgentIntegration."""

from .test_integration_base_markdown import MarkdownIntegrationTests


class TestCursorAgentIntegration(MarkdownIntegrationTests):
    KEY = "cursor-agent"
    FOLDER = ".cursor/"
    COMMANDS_SUBDIR = "commands"
    REGISTRAR_DIR = ".cursor/commands"
    CONTEXT_FILE = ".cursor/rules/specify-rules.mdc"


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

    skill_path = target / ".cursor" / "commands" / "sp.quick.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".specify/memory/constitution.md" in content
    assert "execution_model: subagent-mandatory" in content or "execution model: `subagents-first`" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "cursor leader gate" in content
    assert "cursor subagent execution" in content
    assert "dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis" in content
    assert "leader-inline-fallback" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "do **not** perform broad repository analysis" in content
    assert "use cursor's native subagent path for bounded lanes when available" in content
    assert "the next concrete action must be dispatch" in content
    assert "materially improve throughput" in content
    assert "managed-team" in content
    assert "leader-inline-fallback" in content
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


def test_cursor_runtime_commands_hard_gate_project_map_reads(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-project-map-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"

    for rel in (
        ".cursor/commands/sp.implement.md",
        ".cursor/commands/sp.debug.md",
        ".cursor/commands/sp.quick.md",
    ):
        content = (target / rel).read_text(encoding="utf-8").lower()
        assert "crucial first step" in content
        assert "project-handbook.md" in content
        assert "atlas.entry" in content
        assert "atlas.index.status" in content
        assert "atlas.index.atlas" in content
        assert "map-scan" in content
        assert "map-build" in content
