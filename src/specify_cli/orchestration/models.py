"""Canonical orchestration models shared by strategy selection and runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, cast

ExecutionStrategy = Literal["single-lane", "native-multi-agent", "sidecar-runtime"]
LaneTopology = Literal["single-lane", "multi-lane"]
ExecutionSurface = Literal["native-delegation", "sidecar-runtime", "leader-local"]
# Backward-compatible alias for early Task 1 references.
Strategy = ExecutionStrategy
NativeWorkerSurface = Literal["unknown", "none", "native-cli", "spawn_agent"]
DelegationConfidence = Literal["low", "medium", "high"]
_CANONICAL_EXECUTION_STRATEGIES = frozenset(
    {"single-lane", "native-multi-agent", "sidecar-runtime"}
)
_SINGLE_LANE_LABEL_COMMANDS = frozenset(
    {
        "debug",
        "explain",
        "implement",
        "map-codebase",
        "plan",
        "quick",
        "specify",
        "tasks",
        "test",
    }
)


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
    native_worker_surface: NativeWorkerSurface = "unknown"
    delegation_confidence: DelegationConfidence = "low"
    model_family: str | None = None
    runtime_probe_succeeded: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionDecision:
    """Persisted decision that selects how a command should execute.

    `strategy` names the lane topology and routing class. It does not, by
    itself, guarantee whether concrete work stays on the leader path or is
    delegated; that is captured separately by `execution_surface`.
    """

    command_name: str
    strategy: ExecutionStrategy
    reason: str
    fallback_from: ExecutionStrategy | None = None
    created_at: str = field(default_factory=utc_now)
    lane_topology: LaneTopology | None = None
    execution_surface: ExecutionSurface | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strategy",
            _normalize_execution_strategy(self.strategy),
        )
        if self.fallback_from is not None:
            object.__setattr__(
                self,
                "fallback_from",
                _normalize_execution_strategy(self.fallback_from),
            )
        if self.lane_topology is None:
            object.__setattr__(
                self,
                "lane_topology",
                _derive_lane_topology(self.command_name, self.strategy),
            )
        if self.execution_surface is None:
            object.__setattr__(
                self,
                "execution_surface",
                _derive_execution_surface(self.command_name, self.strategy),
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


# Backward-compatible alias for early Task 1 references.
utc_now_iso = utc_now


def prefers_single_lane_label(command_name: str) -> bool:
    """Return whether the command should prefer the user-visible `single-lane` label."""

    return command_name in _SINGLE_LANE_LABEL_COMMANDS


def single_worker_delegation_default(command_name: str) -> bool:
    """Return whether a single worker lane should still prefer delegated execution."""

    return command_name in {"implement", "quick"}


def _normalize_execution_strategy(strategy: str) -> ExecutionStrategy:
    if strategy == "single-agent":
        return "single-lane"
    if strategy in _CANONICAL_EXECUTION_STRATEGIES:
        return cast(ExecutionStrategy, strategy)
    raise ValueError(f"Unsupported execution strategy: {strategy}")


def _derive_lane_topology(command_name: str, strategy: ExecutionStrategy) -> LaneTopology:
    if strategy == "native-multi-agent":
        return "multi-lane"
    if strategy == "sidecar-runtime":
        return "multi-lane"
    return "single-lane"


def _derive_execution_surface(command_name: str, strategy: ExecutionStrategy) -> ExecutionSurface:
    if strategy == "sidecar-runtime":
        return "sidecar-runtime"
    if strategy == "native-multi-agent":
        return "native-delegation"
    if strategy == "single-lane":
        if single_worker_delegation_default(command_name):
            return "native-delegation"
        return "leader-local"
    return "leader-local"
