"""Runtime routing tests for the implement workflow."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_template() -> str:
    return (PROJECT_ROOT / "templates" / "commands" / "implement.md").read_text(encoding="utf-8")


def test_sp_implement_can_escalate_to_specify_team() -> None:
    content = _read_template().lower()

    assert "specify team" in content
    assert "auto-dispatch" in content
    assert "escalat" in content
    assert "runtime availability" in content


def test_sp_implement_preserves_join_point_semantics() -> None:
    content = _read_template().lower()

    assert "join-point semantics" in content


def test_sp_implement_distinguishes_execution_modes() -> None:
    content = _read_template().lower()

    assert "sequential execution" in content
    assert "native subagents" in content
    assert "durable team runtime" in content
