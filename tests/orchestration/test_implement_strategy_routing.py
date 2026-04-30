"""Routing tests for implement strategy selection."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import choose_subagent_dispatch


def test_implement_routes_one_ready_lane_to_one_native_subagent() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_subagents=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "implement"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "mandatory-one-subagent"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"


def test_implement_routes_codex_to_parallel_native_subagents_when_supported() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "mandatory-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"


def test_implement_keeps_non_codex_integrations_on_native_subagents_when_supported() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_subagents=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "mandatory-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"


def test_implement_uses_one_subagent_for_single_lane_across_integrations() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "mandatory-one-subagent"
    assert decision.execution_surface == "native-subagents"


def test_implement_uses_parallel_subagents_for_multiple_lanes_across_integrations() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 3,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "mandatory-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
