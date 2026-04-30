from dataclasses import fields
from datetime import datetime
from typing import get_args

from specify_cli.orchestration.models import (
    Batch,
    CapabilitySnapshot,
    DispatchShape,
    ExecutionSurface,
    ExecutionDecision,
    Lane,
    ReviewGatePolicy,
    Session,
    SubagentExecutionModel,
    should_attempt_one_subagent,
    utc_now,
)


def test_capability_snapshot_has_canonical_fields_and_defaults():
    snapshot = CapabilitySnapshot(integration_key="claude")
    field_names = [item.name for item in fields(CapabilitySnapshot)]

    assert snapshot.integration_key == "claude"
    assert snapshot.native_subagents is False
    assert snapshot.managed_team_supported is False
    assert snapshot.structured_results is False
    assert snapshot.durable_coordination is False
    assert snapshot.native_worker_surface == "unknown"
    assert snapshot.delegation_confidence == "low"
    assert snapshot.model_family is None
    assert snapshot.runtime_probe_succeeded is False
    assert snapshot.notes == []
    assert field_names == [
        "integration_key",
        "native_subagents",
        "managed_team_supported",
        "structured_results",
        "durable_coordination",
        "native_worker_surface",
        "delegation_confidence",
        "model_family",
        "runtime_probe_succeeded",
        "notes",
    ]


def test_execution_decision_has_canonical_fields_defaults_and_values():
    decision = ExecutionDecision(
        command_name="implement",
        dispatch_shape="one-subagent",
        reason="default",
    )
    field_names = [item.name for item in fields(ExecutionDecision)]

    assert decision.command_name == "implement"
    assert decision.dispatch_shape == "one-subagent"
    assert decision.reason == "default"
    assert decision.fallback_from is None
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagents-first"
    assert datetime.fromisoformat(decision.created_at).utcoffset().total_seconds() == 0
    assert field_names == [
        "command_name",
        "dispatch_shape",
        "reason",
        "fallback_from",
        "created_at",
        "execution_surface",
        "execution_model",
    ]


def test_utc_now_returns_parseable_utc_timestamp():
    stamp = utc_now()
    parsed = datetime.fromisoformat(stamp)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_session_batch_and_lane_have_utc_defaults():
    session = Session(session_id="session-1", integration_key="claude", command_name="implement")
    batch = Batch(batch_id="batch-1", session_id="session-1")
    lane = Lane(lane_id="lane-1", session_id="session-1", batch_id="batch-1")
    session_fields = [item.name for item in fields(Session)]

    assert session.status == "created"
    assert datetime.fromisoformat(session.created_at).utcoffset().total_seconds() == 0
    assert datetime.fromisoformat(batch.created_at).utcoffset().total_seconds() == 0
    assert datetime.fromisoformat(lane.created_at).utcoffset().total_seconds() == 0
    assert session_fields == [
        "session_id",
        "integration_key",
        "command_name",
        "status",
        "created_at",
    ]


def test_dispatch_shape_and_execution_surface_literals_are_canonical():
    assert get_args(SubagentExecutionModel) == ("subagents-first",)
    assert get_args(DispatchShape) == (
        "one-subagent",
        "parallel-subagents",
        "leader-inline-fallback",
    )
    assert get_args(ExecutionSurface) == (
        "native-subagents",
        "managed-team",
        "leader-inline",
    )


def test_execution_decision_derives_debug_inline_fallback_as_leader_inline():
    decision = ExecutionDecision(
        command_name="debug",
        dispatch_shape="leader-inline-fallback",
        reason="no-safe-batch",
    )

    assert decision.execution_surface == "leader-inline"
    assert decision.execution_model == "subagents-first"


def test_execution_decision_rejects_legacy_single_agent_alias() -> None:
    try:
        ExecutionDecision(
            command_name="debug",
            dispatch_shape="single-agent",  # type: ignore[arg-type]
            reason="legacy-persisted-state",
        )
    except ValueError as exc:
        assert "Unsupported dispatch shape" in str(exc)
    else:
        raise AssertionError("legacy dispatch shape should be rejected")


def test_execution_decision_can_record_managed_team_surface() -> None:
    decision = ExecutionDecision(
        command_name="debug",
        dispatch_shape="parallel-subagents",
        reason="native-unavailable",
        fallback_from="parallel-subagents",
        execution_surface="managed-team",
    )

    assert decision.dispatch_shape == "parallel-subagents"
    assert decision.fallback_from == "parallel-subagents"
    assert decision.execution_surface == "managed-team"


def test_one_subagent_attempt_default_is_command_specific():
    assert should_attempt_one_subagent("implement") is True
    assert should_attempt_one_subagent("quick") is True
    assert should_attempt_one_subagent("test-build") is True
    assert should_attempt_one_subagent("debug") is False
    assert should_attempt_one_subagent("tasks") is False
    assert should_attempt_one_subagent("specify") is False


def test_review_gate_policy_has_canonical_fields_and_defaults():
    policy = ReviewGatePolicy()
    field_names = [item.name for item in fields(ReviewGatePolicy)]

    assert policy.requires_review_gate is False
    assert policy.peer_review_lane_recommended is False
    assert policy.reason == "low_risk_batch"
    assert datetime.fromisoformat(policy.created_at).utcoffset().total_seconds() == 0
    assert field_names == [
        "requires_review_gate",
        "peer_review_lane_recommended",
        "reason",
        "created_at",
    ]
