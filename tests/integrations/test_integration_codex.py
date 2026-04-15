"""Tests for CodexIntegration."""

from .test_integration_base_skills import SkillsIntegrationTests


class TestCodexIntegration(SkillsIntegrationTests):
    KEY = "codex"
    FOLDER = ".agents/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".agents/skills"
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
        assert (target / ".agents" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (target / ".agents" / "skills" / "sp-team" / "SKILL.md").exists()
        assert (target / ".specify" / "codex-team" / "runtime.json").exists()


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

    skill_path = target / ".agents" / "skills" / "sp-implement" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    leader_gate_idx = content.find("## Codex Leader Gate")
    outline_idx = content.find("## Outline")
    auto_parallel_idx = content.find("## Codex Auto-Parallel Execution")

    assert leader_gate_idx != -1
    assert outline_idx != -1
    assert auto_parallel_idx != -1
    assert leader_gate_idx < outline_idx < auto_parallel_idx
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
    assert "shared implement template is the primary source of truth" in content
    assert "join point" in content.lower()
    assert "retry-pending" in content.lower() or "retry pending" in content.lower()
    assert "blocker" in content.lower()
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

    skills_dir = target / ".agents" / "skills"
    for skill_name in ("sp-specify", "sp-plan", "sp-tasks", "sp-implement"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "single-agent" in content
        assert "native-multi-agent" in content
        assert "sidecar-runtime" in content
        assert "spawn_agent" in content
        assert "wait_agent" in content

    shared_skills = ("sp-specify", "sp-plan", "sp-tasks")
    for skill_name in shared_skills:
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "specify team" not in content


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

    skill_path = target / ".agents" / "skills" / "sp-debug" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert "codex native multi-agent investigation" in content
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

    skill_path = target / ".agents" / "skills" / "sp-fast" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert "scope gate" in content
    assert "at most 3 files" in content or "no more than 3 files" in content
    assert "no new dependencies" in content
    assert "do the work directly" in content
    assert "verify" in content
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

    skill_path = target / ".agents" / "skills" / "sp-quick" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".planning/quick/" in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "lightweight" in content
    assert "summary.md" in content or "summary artifact" in content
