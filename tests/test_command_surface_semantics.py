from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.agents import CommandRegistrar
from specify_cli.integrations.base import IntegrationBase


def test_init_generated_codex_skill_includes_invocation_note_and_projected_handoff(tmp_path: Path):
    runner = CliRunner()
    target = tmp_path / "codex-projection"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0
    content = (target / ".codex" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")

    assert "## Invocation Syntax" in content
    assert "`$sp-plan`-style syntax" in content
    assert "- **Default handoff**: $sp-plan" in content
    assert "`next_command: /sp.plan`" in content

    passive = (target / ".codex" / "skills" / "python-testing" / "SKILL.md").read_text(encoding="utf-8")
    assert "## Invocation Syntax" not in passive


def test_apply_skill_invocation_conventions_projects_user_facing_examples_by_agent():
    body = (
        "- Run /sp-plan next.\n"
        "- State token remains `next_command: /sp.plan`.\n"
    )

    codex = CommandRegistrar.apply_skill_invocation_conventions("codex", body)
    kimi = CommandRegistrar.apply_skill_invocation_conventions("kimi", body)
    claude = CommandRegistrar.apply_skill_invocation_conventions("claude", body)

    assert "## Invocation Syntax" in codex
    assert "## Invocation Syntax" in kimi
    assert "## Invocation Syntax" in claude
    assert "canonical workflow-state identifiers and handoff values" in codex
    assert "canonical workflow-state identifiers and handoff values" in kimi
    assert "canonical workflow-state identifiers and handoff values" in claude
    assert "do not rewrite them to this integration's invocation syntax" in codex
    assert "do not rewrite them to this integration's invocation syntax" in kimi
    assert "do not rewrite them to this integration's invocation syntax" in claude
    assert "- Run $sp-plan next." in codex
    assert "- Run /skill:sp-plan next." in kimi
    assert "- Run /sp-plan next." in claude
    assert "`next_command: /sp.plan`" in codex
    assert "`next_command: /sp.plan`" in kimi
    assert "`next_command: /sp.plan`" in claude


def test_apply_skill_invocation_conventions_preserves_hyphenated_canonical_state_tokens():
    body = (
        "- **Default handoff**: /sp-test-scan\n"
        "- State token remains `next_command: /sp-test-scan`.\n"
    )

    codex = CommandRegistrar.apply_skill_invocation_conventions("codex", body)

    assert "- **Default handoff**: $sp-test-scan" in codex
    assert "`next_command: /sp-test-scan`" in codex


def test_apply_skill_invocation_conventions_supports_agy_surface():
    body = "- Run /sp-plan next.\n"

    agy = CommandRegistrar.apply_skill_invocation_conventions("agy", body)

    assert "## Invocation Syntax" in agy
    assert "- Run $sp-plan next." in agy


def test_invoke_placeholder_projects_codex_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "codex",
        "sh",
    )

    assert rendered.endswith("Run $sp-plan next.")


def test_invoke_placeholder_projects_kimi_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:test-scan}} next.",
        "kimi",
        "sh",
    )

    assert rendered.endswith("Run /skill:sp-test-scan next.")


def test_invoke_placeholder_projects_markdown_command_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:tasks}} next.",
        "opencode",
        "sh",
    )

    assert rendered.endswith("Run /sp.tasks next.")


def test_invoke_placeholder_does_not_rewrite_canonical_tokens():
    rendered = CommandRegistrar.render_invocation_placeholders(
        "codex",
        "Run {{invoke:plan}} next; keep `/sp.plan` and `/sp-test-scan` unchanged.",
    )

    assert "Run $sp-plan next" in rendered
    assert "`/sp.plan`" in rendered
    assert "`/sp-test-scan`" in rendered
