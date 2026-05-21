from dataclasses import fields
from datetime import datetime
from typing import get_args

from specify_cli.orchestration.models import (
    Batch,
    CapabilitySnapshot,
    DispatchShape,
    ExecutionSurface,
    ExecutionDecision,
    ExecutionModel,
    Lane,
    ReviewGatePolicy,
    Session,
    WorkflowStatus,
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
    assert decision.created_at
    assert decision.execution_surface == "native-subagents"
    assert decision.execution_model == "subagent-mandatory"
    assert decision.workflow_status == "ready"
    assert decision.execution_mode is None
    assert decision.capability_degraded is False
    assert decision.blocked_reason is None
    assert datetime.fromisoformat(decision.created_at).utcoffset().total_seconds() == 0
    assert field_names == [
        "command_name",
        "dispatch_shape",
        "reason",
        "fallback_from",
        "created_at",
        "execution_surface",
        "execution_model",
        "workflow_status",
        "execution_mode",
        "capability_degraded",
        "blocked_reason",
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
    assert get_args(ExecutionModel) == ("subagent-mandatory", "adaptive")
    assert get_args(WorkflowStatus) == ("ready", "blocked")
    assert get_args(DispatchShape) == (
        "one-subagent",
        "parallel-subagents",
        "leader-inline",
        "leader-inline-fallback",
        "subagent-blocked",
    )
    assert get_args(ExecutionSurface) == (
        "native-subagents",
        "leader-inline",
        "none",
    )


def test_execution_decision_preserves_blocked_adaptive_state():
    decision = ExecutionDecision(
        command_name="tasks",
        dispatch_shape="subagent-blocked",
        reason="heavy-native-unavailable",
        execution_model="adaptive",
        workflow_status="blocked",
        execution_mode="heavy",
        execution_surface="none",
        blocked_reason="native subagents unavailable for heavy task generation",
    )

    assert decision.execution_model == "adaptive"
    assert decision.workflow_status == "blocked"
    assert decision.execution_mode == "heavy"
    assert decision.dispatch_shape == "subagent-blocked"
    assert decision.execution_surface == "none"
    assert decision.blocked_reason == "native subagents unavailable for heavy task generation"


def test_execution_decision_derives_none_surface_for_blocked_dispatch():
    decision = ExecutionDecision(
        command_name="tasks",
        dispatch_shape="subagent-blocked",
        reason="heavy-native-unavailable",
        workflow_status="blocked",
        blocked_reason="native subagents unavailable for heavy task generation",
    )

    assert decision.execution_surface == "none"


def test_execution_decision_trims_blocked_reason():
    decision = ExecutionDecision(
        command_name="tasks",
        dispatch_shape="subagent-blocked",
        reason="heavy-native-unavailable",
        workflow_status="blocked",
        blocked_reason="  native subagents unavailable  ",
    )

    assert decision.blocked_reason == "native subagents unavailable"


def test_execution_decision_rejects_blocked_dispatch_with_default_ready_status():
    try:
        ExecutionDecision(
            command_name="tasks",
            dispatch_shape="subagent-blocked",
            reason="heavy-native-unavailable",
            blocked_reason="native subagents unavailable for heavy task generation",
        )
    except ValueError as exc:
        assert "subagent-blocked dispatch requires blocked workflow_status" in str(exc)
    else:
        raise AssertionError("subagent-blocked dispatch should require blocked workflow_status")


def test_execution_decision_rejects_blocked_dispatch_with_non_none_surface():
    try:
        ExecutionDecision(
            command_name="tasks",
            dispatch_shape="subagent-blocked",
            reason="heavy-native-unavailable",
            workflow_status="blocked",
            execution_surface="native-subagents",
            blocked_reason="native subagents unavailable for heavy task generation",
        )
    except ValueError as exc:
        assert "execution_surface must match dispatch_shape" in str(exc)
    else:
        raise AssertionError("subagent-blocked dispatch should require none execution_surface")


def test_execution_decision_rejects_blocked_status_without_blocked_reason():
    try:
        ExecutionDecision(
            command_name="tasks",
            dispatch_shape="subagent-blocked",
            reason="heavy-native-unavailable",
            workflow_status="blocked",
        )
    except ValueError as exc:
        assert "blocked ExecutionDecision requires blocked_reason" in str(exc)
    else:
        raise AssertionError("blocked workflow status should require blocked_reason")


def test_execution_decision_rejects_whitespace_only_blocked_reason():
    try:
        ExecutionDecision(
            command_name="tasks",
            dispatch_shape="subagent-blocked",
            reason="heavy-native-unavailable",
            workflow_status="blocked",
            blocked_reason="   ",
        )
    except ValueError as exc:
        assert "blocked ExecutionDecision requires blocked_reason" in str(exc)
    else:
        raise AssertionError("whitespace-only blocked_reason should be rejected")


def test_execution_decision_rejects_blocked_status_with_one_subagent_dispatch():
    try:
        ExecutionDecision(
            command_name="tasks",
            dispatch_shape="one-subagent",
            reason="blocked-native",
            workflow_status="blocked",
            blocked_reason="native subagents unavailable",
        )
    except ValueError as exc:
        assert "blocked workflow_status requires subagent-blocked dispatch" in str(exc)
    else:
        raise AssertionError("blocked workflow status should require subagent-blocked dispatch")


def test_execution_decision_rejects_blocked_status_with_leader_inline_dispatch():
    try:
        ExecutionDecision(
            command_name="tasks",
            dispatch_shape="leader-inline",
            reason="blocked-inline",
            workflow_status="blocked",
            blocked_reason="native subagents unavailable",
        )
    except ValueError as exc:
        assert "blocked workflow_status requires subagent-blocked dispatch" in str(exc)
    else:
        raise AssertionError("blocked workflow status should require subagent-blocked dispatch")


def test_execution_decision_rejects_invalid_execution_surface():
    try:
        ExecutionDecision(
            command_name="implement",
            dispatch_shape="one-subagent",
            reason="invalid-surface",
            execution_surface="inline",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "Unsupported execution surface" in str(exc)
    else:
        raise AssertionError("invalid execution surface should be rejected")


def test_execution_decision_rejects_execution_surface_mismatch():
    try:
        ExecutionDecision(
            command_name="implement",
            dispatch_shape="one-subagent",
            reason="mismatched-surface",
            execution_surface="leader-inline",
        )
    except ValueError as exc:
        assert "execution_surface must match dispatch_shape" in str(exc)
    else:
        raise AssertionError("execution surface mismatch should be rejected")


def test_execution_decision_rejects_invalid_execution_model():
    try:
        ExecutionDecision(
            command_name="implement",
            dispatch_shape="one-subagent",
            reason="invalid-model",
            execution_model="leader-only",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "Unsupported execution model" in str(exc)
    else:
        raise AssertionError("invalid execution model should be rejected")


def test_execution_decision_rejects_invalid_workflow_status():
    try:
        ExecutionDecision(
            command_name="implement",
            dispatch_shape="one-subagent",
            reason="invalid-status",
            workflow_status="waiting",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "Unsupported workflow status" in str(exc)
    else:
        raise AssertionError("invalid workflow status should be rejected")


def test_execution_decision_rejects_invalid_execution_mode():
    try:
        ExecutionDecision(
            command_name="implement",
            dispatch_shape="one-subagent",
            reason="invalid-mode",
            execution_mode="tiny",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "Unsupported execution mode" in str(exc)
    else:
        raise AssertionError("invalid execution mode should be rejected")


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


def test_one_subagent_attempt_default_applies_to_ordinary_sp_commands():
    for command_name in (
        "analyze",
        "auto",
        "checklist",
        "clarify",
        "constitution",
        "debug",
        "deep-research",
        "explain",
        "fast",
        "implement",
        "map-build",
        "map-scan",
        "plan",
        "quick",
        "research",
        "specify",
        "tasks",
        "taskstoissues",
    ):
        assert should_attempt_one_subagent(command_name) is True


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
