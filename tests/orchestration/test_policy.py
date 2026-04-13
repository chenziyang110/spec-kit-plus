"""Tests for orchestration strategy selection policy."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import choose_execution_strategy


def test_choose_execution_strategy_blocks_parallel_when_batch_is_not_safe() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 0,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "implement"
    assert decision.strategy == "single-agent"
    assert decision.reason == "no-safe-batch"


def test_choose_execution_strategy_prefers_native_multi_agent_when_available() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
        },
    )

    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"


def test_choose_execution_strategy_falls_back_to_sidecar_when_native_is_missing() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_multi_agent=False,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 1,
            "overlapping_write_sets": False,
        },
    )

    assert decision.strategy == "sidecar-runtime"
    assert decision.reason == "native-missing"


def test_choose_execution_strategy_uses_parallel_batches_even_with_safe_alias() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 0,
            "safe_parallel_batch": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.strategy == "single-agent"
    assert decision.reason == "no-safe-batch"


def test_choose_execution_strategy_treats_non_empty_overlap_collections_as_conflicts() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": {"src/specify_cli/__init__.py"},
        },
    )

    assert decision.strategy == "single-agent"
    assert decision.reason == "no-safe-batch"


def test_choose_execution_strategy_treats_empty_overlap_collections_as_no_conflict() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": [],
        },
    )

    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"


def test_choose_execution_strategy_treats_boolean_parallel_batches_as_unset() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": True,
            "safe_parallel_batch": False,
            "overlapping_write_sets": False,
        },
    )

    assert decision.strategy == "single-agent"
    assert decision.reason == "no-safe-batch"


def test_choose_execution_strategy_supports_specify_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "specify"
    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"


def test_choose_execution_strategy_supports_plan_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_multi_agent=False,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 1,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "plan"
    assert decision.strategy == "sidecar-runtime"
    assert decision.reason == "native-missing"


def test_choose_execution_strategy_supports_tasks_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "tasks"
    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"


def test_choose_execution_strategy_supports_explain_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="explain",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 0,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "explain"
    assert decision.strategy == "single-agent"
    assert decision.reason == "no-safe-batch"
