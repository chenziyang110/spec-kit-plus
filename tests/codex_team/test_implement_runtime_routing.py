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
    native_missing = content.find("sidecar_runtime_supported")
    fallback = content.find("fallback")

    assert no_safe_batch != -1
    assert native_supported != -1
    assert native_missing != -1
    assert fallback != -1
    assert no_safe_batch < native_supported < native_missing < fallback


def test_sp_implement_preserves_join_point_semantics() -> None:
    content = _read_template().lower()

    assert "join-point semantics" in content


def test_sp_implement_distinguishes_execution_modes() -> None:
    content = _step_6_block()

    assert "single-agent" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "decision order" in content
    assert "specify team" not in content
    assert "auto-dispatch" not in content
