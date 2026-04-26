"""Routing tests for implement strategy selection."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import choose_execution_strategy


def test_implement_routes_to_single_agent_when_workload_is_unsafe() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": 3,
            "overlapping_write_sets": True,
        },
    )

    assert decision.command_name == "implement"
    assert decision.strategy == "single-lane"
    assert decision.reason == "no-safe-batch"


def test_implement_routes_codex_to_native_multi_agent_when_supported() -> None:
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

    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"
    assert decision.fallback_from is None


def test_implement_keeps_non_codex_integrations_on_native_when_supported() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
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


def test_implement_routes_to_sidecar_runtime_when_native_is_missing() -> None:
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
    assert decision.fallback_from is None


def test_implement_routes_to_single_agent_when_parallel_batch_count_is_zero() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
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

    assert decision.strategy == "single-lane"
    assert decision.reason == "no-safe-batch"


def test_implement_treats_boolean_parallel_batch_counts_as_unset() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_multi_agent=True,
        sidecar_runtime_supported=True,
    )

    decision = choose_execution_strategy(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "parallel_batches": False,
            "safe_parallel_batch": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.strategy == "native-multi-agent"
    assert decision.reason == "native-supported"
