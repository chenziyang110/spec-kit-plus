"""Guidance routing tests for the Codex integration."""

from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _init_codex_project(tmp_path: Path) -> Path:
    runner = CliRunner()
    project = tmp_path / "codex-guidance"
    result = runner.invoke(
        app,
        [
            "init",
            str(project),
            "--ai",
            "codex",
            "--script",
            "sh",
            "--no-git",
            "--ignore-agent-tools",
        ],
    )
    assert result.exit_code == 0, result.output
    return project


def _read_sp_implement(project: Path) -> str:
    return (project / ".agents" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")


def test_codex_guidance_calls_out_routing_choices(tmp_path: Path) -> None:
    """Ensure the Codex guidance talks about solo, native, and team paths."""
    project = _init_codex_project(tmp_path)
    content = _read_sp_implement(project)
    lower = content.lower()

    assert "solo" in lower
    assert "native subagents" in lower
    assert "specify team" in content


def test_sp_implement_includes_runtime_escalation_language(tmp_path: Path) -> None:
    """The implementation skill should describe runtime-aware escalations."""
    project = _init_codex_project(tmp_path)
    content = _read_sp_implement(project)
    lower = content.lower()

    assert "runtime" in lower
    assert "escalat" in lower
    assert "auto-dispatch" in lower


def test_team_guidance_declares_codex_only_scope() -> None:
    """The team guidance template must remain scoped to Codex."""
    template = (PROJECT_ROOT / "templates" / "commands" / "team.md").read_text(encoding="utf-8")
    lower = template.lower()

    assert "codex-only" in lower
    assert "do not surface" in lower
