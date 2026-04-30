"""Routing tests for implement strategy selection."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import choose_subagent_dispatch


def test_implement_routes_to_leader_inline_fallback_when_workload_is_unsafe() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 3,
            "packet_ready": True,
            "overlapping_write_sets": True,
        },
    )

    assert decision.command_name == "implement"
    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "unsafe-write-sets"


def test_implement_routes_codex_to_parallel_native_subagents_when_supported() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
        managed_team_supported=True,
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
    assert decision.reason == "safe-parallel-subagents"
    assert decision.fallback_from is None


def test_implement_keeps_non_codex_integrations_on_native_subagents_when_supported() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_subagents=True,
        managed_team_supported=True,
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
    assert decision.reason == "safe-parallel-subagents"


def test_implement_uses_leader_inline_fallback_when_native_is_missing() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=False,
        managed_team_supported=True,
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

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "runtime-no-subagents"
    assert decision.fallback_from == "one-subagent"
    assert decision.execution_surface == "leader-inline"


def test_implement_routes_to_leader_inline_when_safe_lane_count_is_zero() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 0,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "no-safe-delegated-lane"


def test_implement_treats_boolean_safe_lane_counts_as_unset() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="gemini",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": False,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "no-safe-delegated-lane"
