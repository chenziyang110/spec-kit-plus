"""Canonical orchestration models shared by dispatch selection and runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, cast

SubagentExecutionModel = Literal["subagents-first"]
DispatchShape = Literal["one-subagent", "parallel-subagents", "leader-inline-fallback"]
ExecutionSurface = Literal["native-subagents", "managed-team", "leader-inline"]
NativeWorkerSurface = Literal["unknown", "none", "native-cli", "spawn_agent"]
DelegationConfidence = Literal["low", "medium", "high"]
_CANONICAL_DISPATCH_SHAPES = frozenset(
    {"one-subagent", "parallel-subagents", "leader-inline-fallback"}
)
_ONE_SUBAGENT_ATTEMPT_COMMANDS = frozenset({"implement", "quick", "test-build"})


def utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class CapabilitySnapshot:
    """Captured integration/runtime capabilities used for subagent dispatch decisions."""

    integration_key: str
    native_subagents: bool = False
    managed_team_supported: bool = False
    structured_results: bool = False
    durable_coordination: bool = False
    native_worker_surface: NativeWorkerSurface = "unknown"
    delegation_confidence: DelegationConfidence = "low"
    model_family: str | None = None
    runtime_probe_succeeded: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionDecision:
    """Persisted decision that selects how a command should execute.

    The command remains leader-owned. ``dispatch_shape`` captures whether the
    next safe lane goes to one subagent, parallel subagents, or leader-inline
    fallback; ``execution_surface`` captures the runtime used for that shape.
    """

    command_name: str
    dispatch_shape: DispatchShape
    reason: str
    fallback_from: DispatchShape | None = None
    created_at: str = field(default_factory=utc_now)
    execution_surface: ExecutionSurface | None = None
    execution_model: SubagentExecutionModel = "subagents-first"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dispatch_shape",
            _normalize_dispatch_shape(self.dispatch_shape),
        )
        if self.fallback_from is not None:
            object.__setattr__(
                self,
                "fallback_from",
                _normalize_dispatch_shape(self.fallback_from),
            )
        if self.execution_surface is None:
            object.__setattr__(
                self,
                "execution_surface",
                _derive_execution_surface(self.dispatch_shape),
            )


@dataclass(slots=True)
class BatchExecutionPolicy:
    """Shared policy output describing how a batch should converge."""

    batch_classification: Literal["strict", "mixed_tolerance"]
    safe_preparation_allowed: bool = False
    reason: str = "full_success_required"
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class ReviewGatePolicy:
    """Shared policy output describing whether a batch needs extra review."""

    requires_review_gate: bool = False
    peer_review_lane_recommended: bool = False
    reason: str = "low_risk_batch"
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class PhaseExecutionState:
    """Persisted milestone-level view of a phase and its next ready work."""

    phase_number: float
    phase_name: str
    ready_batch_count: int = 0
    leader_mode: bool = True
    continue_milestone: bool = True
    current_batch_id: str | None = None
    blocking_reason: str | None = None
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class MilestoneExecutionDecision:
    """Scheduler output describing the next executable phase and milestone flow."""

    phase_number: float
    phase_name: str
    ready_batch_count: int
    leader_mode: bool = True
    continue_milestone: bool = True
    next_phase_number: float | None = None
    next_phase_name: str | None = None
    selected_batch_id: str | None = None
    reason: str = "roadmap-order"
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


utc_now_iso = utc_now


def should_attempt_one_subagent(command_name: str) -> bool:
    """Return whether one safe lane should prefer one subagent over leader-inline work."""

    return command_name.strip().lower() in _ONE_SUBAGENT_ATTEMPT_COMMANDS


def _normalize_dispatch_shape(dispatch_shape: str) -> DispatchShape:
    if dispatch_shape in _CANONICAL_DISPATCH_SHAPES:
        return cast(DispatchShape, dispatch_shape)
    raise ValueError(f"Unsupported dispatch shape: {dispatch_shape}")


def _derive_execution_surface(dispatch_shape: DispatchShape) -> ExecutionSurface:
    if dispatch_shape in {"one-subagent", "parallel-subagents"}:
        return "native-subagents"
    return "leader-inline"
