from dataclasses import fields
from datetime import datetime
from typing import get_args

from specify_cli.orchestration.models import (
    Batch,
    CapabilitySnapshot,
    ExecutionStrategy,
    ExecutionDecision,
    Lane,
    Session,
    utc_now,
)


def test_capability_snapshot_has_canonical_fields_and_defaults():
    snapshot = CapabilitySnapshot(integration_key="claude")
    field_names = [item.name for item in fields(CapabilitySnapshot)]

    assert snapshot.integration_key == "claude"
    assert snapshot.native_multi_agent is False
    assert snapshot.sidecar_runtime_supported is False
    assert snapshot.structured_results is False
    assert snapshot.durable_coordination is False
    assert snapshot.notes == []
    assert field_names == [
        "integration_key",
        "native_multi_agent",
        "sidecar_runtime_supported",
        "structured_results",
        "durable_coordination",
        "notes",
    ]


def test_execution_decision_has_canonical_fields_defaults_and_values():
    decision = ExecutionDecision(
        command_name="implement",
        strategy="single-agent",
        reason="default",
    )
    field_names = [item.name for item in fields(ExecutionDecision)]

    assert decision.command_name == "implement"
    assert decision.strategy == "single-agent"
    assert decision.reason == "default"
    assert decision.fallback_from is None
    assert datetime.fromisoformat(decision.created_at).utcoffset().total_seconds() == 0
    assert field_names == [
        "command_name",
        "strategy",
        "reason",
        "fallback_from",
        "created_at",
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


def test_execution_strategy_literal_values_are_canonical():
    assert get_args(ExecutionStrategy) == (
        "single-agent",
        "native-multi-agent",
        "sidecar-runtime",
    )
