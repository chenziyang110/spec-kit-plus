from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from tests.test_extension_skills import _body_without_frontmatter
from tests.template_utils import read_skill_with_references


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_repo_quick_skill_mirror_has_codex_subagent_dispatch_contract(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "codex-quick-mirror"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, result.output

    mirror_path = target / ".codex" / "skills" / "sp-quick" / "SKILL.md"
    body = _body_without_frontmatter(mirror_path).lower()
    full_body = read_skill_with_references(mirror_path).lower()

    assert ".planning/quick/<id>-<slug>/status.md" in body
    assert ".planning/quick/index.json" in full_body
    assert 'choose_subagent_dispatch(command_name="quick"' in full_body
    assert "read `.specify/memory/constitution.md` first" in body
    assert "understanding checkpoint" in body
    assert "understanding_confirmed: true" in body
    assert "dispatch_shape: one-subagent | parallel-subagents" in full_body
    assert "execution_surface: native-subagents" in full_body
    assert "one-subagent" in full_body
    assert "parallel-subagents" in full_body
    assert "native-subagents" in full_body
    assert "subagent-blocked" in full_body
    assert "constitution read is the first hard gate" in full_body
    assert "codex leader gate" in body
    assert "spawn_agent" in body
    assert "wait_agent" in body
    assert "close_agent" in body
    assert "managed team" in body
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in body
    assert (
        "the next concrete action must be dispatch" in full_body
        or "first actionable execution step after scope lock and understanding confirmation is to dispatch" in full_body
    )
    assert "materially improve throughput" in body
    assert "blocked_dispatch" in full_body
    assert "continue automatically until the quick task is complete or blocked" in body
    assert "if exactly one unfinished quick task exists" in full_body
    assert "if multiple unfinished quick tasks exist" in full_body
    assert "ask the user which quick task to continue" in full_body
