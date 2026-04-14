"""Tests for orchestration strategy selection policy."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import (
    choose_execution_strategy,
    classify_batch_execution_policy,
)


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


def test_choose_execution_strategy_prefers_sidecar_for_codex_implement_when_available() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
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

    assert decision.strategy == "sidecar-runtime"
    assert decision.reason == "sidecar-preferred"
    assert decision.fallback_from == "native-multi-agent"


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
    assert decision.reason == "sidecar-preferred"
    assert decision.fallback_from is None


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


def test_choose_execution_strategy_keeps_non_implement_codex_commands_on_shared_policy() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
        },
    )

    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"


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


def test_classify_batch_execution_policy_marks_low_risk_preparation_as_mixed_tolerance() -> None:
    policy = classify_batch_execution_policy(
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
            "safe_preparation": True,
            "preparation_scope": "scaffolding",
        }
    )

    assert policy.batch_classification == "mixed_tolerance"
    assert policy.safe_preparation_allowed is True
    assert policy.reason == "low_risk_preparation"


def test_classify_batch_execution_policy_keeps_general_parallel_implementation_strict() -> None:
    policy = classify_batch_execution_policy(
        workload_shape={
            "parallel_batches": 2,
            "overlapping_write_sets": False,
            "safe_preparation": False,
        }
    )

    assert policy.batch_classification == "strict"
    assert policy.safe_preparation_allowed is False
    assert policy.reason == "full_success_required"
