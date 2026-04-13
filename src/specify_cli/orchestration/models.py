"""Canonical orchestration models shared by strategy selection and runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

ExecutionStrategy = Literal["single-agent", "native-multi-agent", "sidecar-runtime"]
# Backward-compatible alias for early Task 1 references.
Strategy = ExecutionStrategy


def utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class CapabilitySnapshot:
    """Captured integration/runtime capabilities used for execution strategy decisions."""

    integration_key: str
    native_multi_agent: bool = False
    sidecar_runtime_supported: bool = False
    structured_results: bool = False
    durable_coordination: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionDecision:
    """Persisted decision that selects how a command should execute."""

    command_name: str
    strategy: ExecutionStrategy
    reason: str
    fallback_from: ExecutionStrategy | None = None
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class Session:
    """Top-level orchestration session record."""

    session_id: str
    integration_key: str
    command_name: str
    status: str = "created"
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class Batch:
    """Group of lanes/tasks processed together within a session."""

    batch_id: str
    session_id: str
    status: str = "pending"
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class Lane:
    """Single execution lane within a batch."""

    lane_id: str
    session_id: str
    batch_id: str
    status: str = "pending"
    created_at: str = field(default_factory=utc_now)


# Backward-compatible alias for early Task 1 references.
utc_now_iso = utc_now
