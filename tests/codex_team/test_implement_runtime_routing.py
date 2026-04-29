"""Runtime routing tests for the implement workflow."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_template() -> str:
    return (PROJECT_ROOT / "templates" / "commands" / "implement.md").read_text(encoding="utf-8")


def _step_6_block() -> str:
    content = _read_template().lower()
    start = content.find("6. select an execution strategy for each ready batch before writing code:")
    assert start != -1
    end = content.find("\n7. execute implementation following the task plan:", start)
    assert end != -1
    return content[start:end]


def test_sp_implement_documents_canonical_decision_order() -> None:
    content = _step_6_block()

    no_safe_batch = content.find("parallel_batches <= 0")
    native_supported = content.find("native_multi_agent")
    native_missing = content.find("native-missing")
    fallback = content.find("fallback")

    assert no_safe_batch != -1
    assert native_supported != -1
    assert native_missing != -1
    assert fallback != -1
    assert no_safe_batch < native_supported < native_missing < fallback


def test_sp_implement_preserves_join_point_semantics() -> None:
    content = _read_template().lower()

    assert "join-point semantics" in content
    assert "implement-tracker.md" in content
    assert "execution-state source of truth" in content
    assert "user execution notes" in content
    assert "first-class implementation context" in content
    assert "resume_decision" in content


def test_sp_implement_distinguishes_execution_modes() -> None:
    content = _step_6_block()

    assert "single-lane" in content
    assert "native-multi-agent" in content
    assert "decision order" in content
    assert "specify team" not in content
    assert "auto-dispatch" not in content


def test_sp_implement_positions_the_runtime_as_leader_only() -> None:
    content = _read_template().lower()

    assert "invoking runtime acts as the leader" in content
    assert "dispatches work instead of performing concrete implementation directly" in content
    assert "`single-lane` names the topology for one safe execution lane" in content
    assert "does not, by itself, decide whether the leader or a delegated worker executes that lane" in content


def test_sp_implement_documents_milestone_next_step_selection() -> None:
    content = _read_template().lower()

    assert "selects the next executable phase and ready batch" in content
    assert "continues automatically until the milestone is complete or blocked" in content
    assert "do not stop after a single completed batch" in content
    assert "shared implement template is the primary source of truth" in content
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in _read_template()
    assert "`plan_gap`" in _read_template()
    assert "`spec_gap`" in _read_template()
