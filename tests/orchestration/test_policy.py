"""Tests for orchestration strategy selection policy."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import (
    choose_subagent_dispatch,
    classify_batch_execution_policy,
    classify_review_gate_policy,
)


def test_choose_subagent_dispatch_routes_one_ready_lane_to_one_native_subagent() -> None:
    snapshot = CapabilitySnapshot(integration_key="codex", native_subagents=True)

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


def test_choose_subagent_dispatch_routes_multiple_ready_lanes_to_parallel_native_subagents() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "plan"
    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "mandatory-parallel-subagents"
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"


def test_choose_subagent_dispatch_uses_one_subagent_for_ordinary_sp_commands() -> None:
    snapshot = CapabilitySnapshot(integration_key="claude", native_subagents=True)

    for command_name in (
        "specify",
        "tasks",
        "explain",
        "debug",
        "quick",
        "test-scan",
        "map-build",
    ):
        decision = choose_subagent_dispatch(
            command_name=command_name,
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


def test_classify_review_gate_policy_marks_high_risk_shared_surface_batches() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_shared_surface": True,
            "review_lane_available": True,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.peer_review_lane_recommended is True
    assert policy.reason == "shared_surface"


def test_classify_review_gate_policy_marks_boundary_batches_without_peer_lane() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_protocol_boundary": True,
            "review_lane_available": False,
        }
    )

    assert policy.requires_review_gate is True
    assert policy.peer_review_lane_recommended is False
    assert policy.reason == "boundary_contract"


def test_classify_review_gate_policy_skips_low_risk_batches() -> None:
    policy = classify_review_gate_policy(
        workload_shape={
            "touches_shared_surface": False,
            "touches_schema": False,
            "touches_protocol_boundary": False,
        }
    )

    assert policy.requires_review_gate is False
    assert policy.peer_review_lane_recommended is False
    assert policy.reason == "low_risk_batch"
