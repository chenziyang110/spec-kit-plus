"""Tests for orchestration strategy selection policy."""

from specify_cli.orchestration.models import CapabilitySnapshot
from specify_cli.orchestration.policy import (
    choose_subagent_dispatch,
    classify_batch_execution_policy,
    classify_review_gate_policy,
)


def test_choose_subagent_dispatch_blocks_delegation_when_batch_is_not_safe() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
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

    assert decision.command_name == "implement"
    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "no-safe-delegated-lane"
    assert decision.fallback_from == "one-subagent"
    assert decision.execution_surface == "leader-inline"
    assert decision.execution_model == "subagents-first"


def test_choose_subagent_dispatch_prefers_parallel_native_subagents_when_available() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
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
    assert decision.execution_surface == "native-subagents"


def test_choose_subagent_dispatch_prefers_native_for_codex_implement_when_available() -> None:
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
    assert decision.execution_surface == "native-subagents"


def test_choose_subagent_dispatch_falls_back_for_sp_implement_when_native_is_missing() -> None:
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


def test_choose_subagent_dispatch_uses_managed_team_for_non_implement_low_confidence() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
        delegation_confidence="low",
        runtime_probe_succeeded=True,
    )

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "managed-team-supported"
    assert decision.fallback_from == "parallel-subagents"
    assert decision.execution_surface == "managed-team"


def test_choose_subagent_dispatch_falls_back_when_native_confidence_is_low_and_no_managed_team() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=False,
        delegation_confidence="low",
        runtime_probe_succeeded=True,
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

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "low-delegation-confidence"
    assert decision.fallback_from == "parallel-subagents"
    assert decision.execution_surface == "leader-inline"


def test_choose_subagent_dispatch_uses_safe_subagent_lanes_over_legacy_safe_alias() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 0,
            "safe_parallel_batch": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "no-safe-delegated-lane"
    assert decision.execution_surface == "leader-inline"


def test_choose_subagent_dispatch_treats_non_empty_overlap_collections_as_conflicts() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": {"src/specify_cli/__init__.py"},
        },
    )

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "unsafe-write-sets"
    assert decision.fallback_from == "parallel-subagents"
    assert decision.execution_surface == "leader-inline"


def test_choose_subagent_dispatch_treats_empty_overlap_collections_as_no_conflict() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": [],
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "safe-parallel-subagents"
    assert decision.execution_surface == "native-subagents"


def test_choose_subagent_dispatch_treats_boolean_lane_counts_as_unset() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": True,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "no-safe-delegated-lane"
    assert decision.execution_surface == "leader-inline"


def test_choose_subagent_dispatch_supports_specify_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="specify",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "specify"
    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "safe-parallel-subagents"
    assert decision.execution_surface == "native-subagents"


def test_choose_subagent_dispatch_supports_plan_managed_team_when_native_missing() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=False,
        managed_team_supported=True,
    )

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
    assert decision.reason == "managed-team-supported"
    assert decision.fallback_from == "parallel-subagents"
    assert decision.execution_surface == "managed-team"


def test_choose_subagent_dispatch_keeps_non_implement_codex_commands_on_shared_policy() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="plan",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "safe-parallel-subagents"
    assert decision.execution_surface == "native-subagents"


def test_choose_subagent_dispatch_supports_tasks_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="tasks",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 2,
            "packet_ready": True,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "tasks"
    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.reason == "safe-parallel-subagents"
    assert decision.execution_surface == "native-subagents"


def test_choose_subagent_dispatch_supports_explain_command_name() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="claude",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="explain",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 0,
            "overlapping_write_sets": False,
        },
    )

    assert decision.command_name == "explain"
    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "no-safe-delegated-lane"
    assert decision.fallback_from is None
    assert decision.execution_surface == "leader-inline"


def test_choose_subagent_dispatch_requires_packet_for_one_subagent_commands() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
        managed_team_supported=True,
    )

    decision = choose_subagent_dispatch(
        command_name="implement",
        snapshot=snapshot,
        workload_shape={
            "safe_subagent_lanes": 1,
            "packet_ready": False,
            "overlapping_write_sets": False,
        },
    )

    assert decision.dispatch_shape == "leader-inline-fallback"
    assert decision.reason == "packet-not-ready"
    assert decision.fallback_from == "one-subagent"
    assert decision.execution_surface == "leader-inline"


def test_choose_subagent_dispatch_routes_one_safe_lane_to_one_native_subagent() -> None:
    snapshot = CapabilitySnapshot(
        integration_key="codex",
        native_subagents=True,
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

    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "safe-one-subagent"
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
