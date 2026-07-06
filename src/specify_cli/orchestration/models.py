"""Canonical orchestration models shared by dispatch selection and runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, cast, get_args

ExecutionModel = Literal["subagent-mandatory", "adaptive"]
SubagentExecutionModel = ExecutionModel
WorkflowStatus = Literal["ready", "blocked"]
ExecutionMode = Literal["light", "standard", "heavy"]
DispatchShape = Literal[
    "one-subagent",
    "parallel-subagents",
    "leader-inline",
    "leader-inline-fallback",
    "subagent-blocked",
]
ExecutionSurface = Literal["native-subagents", "leader-inline", "none"]
NativeWorkerSurface = Literal["unknown", "none", "native-cli", "spawn_agent"]
DelegationConfidence = Literal["low", "medium", "high"]
EvidenceLaneMode = Literal["read-only-evidence", "ui-reference-artifact"]
READ_ONLY_EVIDENCE_ALLOWED_OPERATIONS: tuple[str, ...] = (
    "file-read",
    "rg",
    "project-cognition",
    "memory-read",
    "state-read",
    "docs-read",
    "template-read",
)
READ_ONLY_EVIDENCE_FORBIDDEN_OPERATIONS: tuple[str, ...] = (
    "file-write",
    "state-write",
    "handoff-write",
    "tests",
    "builds",
    "package-managers",
    "project-cli",
    "app-server",
)
UI_REFERENCE_ALLOWED_OPERATIONS: tuple[str, ...] = (
    "file-read",
    "rg",
    "project-cognition",
    "memory-read",
    "state-read",
    "docs-read",
    "template-read",
    "reference-input-read",
    "ui-reference-notes-write",
    "ui-brief-write",
    "ui-target-html-write",
)
UI_REFERENCE_FORBIDDEN_OPERATIONS: tuple[str, ...] = (
    "source-code-write",
    "test-write",
    "app-style-write",
    "component-implementation-write",
    "broad-state-write",
    "handoff-readiness-write",
    "tests",
    "builds",
    "package-managers",
    "project-cli",
    "app-server",
)
_CANONICAL_DISPATCH_SHAPES = frozenset(
    {
        "one-subagent",
        "parallel-subagents",
        "leader-inline",
        "leader-inline-fallback",
        "subagent-blocked",
    }
)
_CANONICAL_EXECUTION_SURFACES = frozenset(get_args(ExecutionSurface))
_CANONICAL_EXECUTION_MODELS = frozenset(get_args(ExecutionModel))
_CANONICAL_WORKFLOW_STATUSES = frozenset(get_args(WorkflowStatus))
_CANONICAL_EXECUTION_MODES = frozenset(get_args(ExecutionMode))
_ORDINARY_SP_COMMANDS = frozenset(
    {
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
        "map-update",
        "plan",
        "quick",
        "research",
        "specify",
        "tasks",
        "taskstoissues",
    }
)


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
    """Persisted decision selecting a workflow dispatch shape."""

    command_name: str
    dispatch_shape: DispatchShape
    reason: str
    fallback_from: DispatchShape | None = None
    created_at: str = field(default_factory=utc_now)
    execution_surface: ExecutionSurface | None = None
    execution_model: ExecutionModel = "subagent-mandatory"
    workflow_status: WorkflowStatus = "ready"
    execution_mode: ExecutionMode | None = None
    capability_degraded: bool = False
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dispatch_shape",
            _normalize_dispatch_shape(self.dispatch_shape),
        )
        if self.fallback_from is not None:
            object.__setattr__(self, "fallback_from", _normalize_dispatch_shape(self.fallback_from))
        if self.execution_surface is None:
            object.__setattr__(self, "execution_surface", _derive_execution_surface(self.dispatch_shape))
        else:
            object.__setattr__(
                self,
                "execution_surface",
                _normalize_execution_surface(self.execution_surface),
            )
        object.__setattr__(
            self,
            "execution_model",
            _normalize_execution_model(self.execution_model),
        )
        object.__setattr__(
            self,
            "workflow_status",
            _normalize_workflow_status(self.workflow_status),
        )
        if self.execution_mode is not None:
            object.__setattr__(
                self,
                "execution_mode",
                _normalize_execution_mode(self.execution_mode),
            )
        if self.execution_surface != _derive_execution_surface(self.dispatch_shape):
            raise ValueError("execution_surface must match dispatch_shape")
        if self.blocked_reason is not None:
            object.__setattr__(self, "blocked_reason", self.blocked_reason.strip())
        if self.workflow_status == "blocked" and not self.blocked_reason:
            raise ValueError("blocked ExecutionDecision requires blocked_reason")
        if self.workflow_status == "blocked" and self.dispatch_shape != "subagent-blocked":
            raise ValueError("blocked workflow_status requires subagent-blocked dispatch")
        if self.dispatch_shape == "subagent-blocked" and self.workflow_status != "blocked":
            raise ValueError("subagent-blocked dispatch requires blocked workflow_status")
        if self.dispatch_shape == "subagent-blocked" and not self.blocked_reason:
            raise ValueError("subagent-blocked dispatch requires blocked_reason")


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
class EvidenceLaneDecision:
    """Dispatch decision for optional read-only evidence lanes."""

    command_name: str
    dispatch_shape: DispatchShape
    reason: str
    created_at: str = field(default_factory=utc_now)
    execution_surface: ExecutionSurface | None = None
    workflow_status: WorkflowStatus = "ready"
    blocked_reason: str | None = None
    capability_degraded: bool = False
    lane_mode: EvidenceLaneMode = "read-only-evidence"
    structured_result: str = "evidence_packet"
    allowed_operations: tuple[str, ...] = READ_ONLY_EVIDENCE_ALLOWED_OPERATIONS
    forbidden_operations: tuple[str, ...] = READ_ONLY_EVIDENCE_FORBIDDEN_OPERATIONS

    def __post_init__(self) -> None:
        if self.lane_mode == "ui-reference-artifact":
            if self.structured_result == "evidence_packet":
                object.__setattr__(self, "structured_result", "ui_reference_artifacts")
            if self.allowed_operations == READ_ONLY_EVIDENCE_ALLOWED_OPERATIONS:
                object.__setattr__(self, "allowed_operations", UI_REFERENCE_ALLOWED_OPERATIONS)
            if self.forbidden_operations == READ_ONLY_EVIDENCE_FORBIDDEN_OPERATIONS:
                object.__setattr__(self, "forbidden_operations", UI_REFERENCE_FORBIDDEN_OPERATIONS)
        object.__setattr__(
            self,
            "dispatch_shape",
            _normalize_dispatch_shape(self.dispatch_shape),
        )
        if self.execution_surface is None:
            object.__setattr__(self, "execution_surface", _derive_execution_surface(self.dispatch_shape))
        else:
            object.__setattr__(
                self,
                "execution_surface",
                _normalize_execution_surface(self.execution_surface),
            )
        object.__setattr__(
            self,
            "workflow_status",
            _normalize_workflow_status(self.workflow_status),
        )
        if self.execution_surface != _derive_execution_surface(self.dispatch_shape):
            raise ValueError("execution_surface must match dispatch_shape")
        if self.blocked_reason is not None:
            object.__setattr__(self, "blocked_reason", self.blocked_reason.strip())
        if self.workflow_status == "blocked" and not self.blocked_reason:
            raise ValueError("blocked EvidenceLaneDecision requires blocked_reason")
        if self.workflow_status == "blocked" and self.dispatch_shape != "subagent-blocked":
            raise ValueError("blocked workflow_status requires subagent-blocked dispatch")
        if self.dispatch_shape == "subagent-blocked" and self.workflow_status != "blocked":
            raise ValueError("subagent-blocked dispatch requires blocked workflow_status")
        if self.dispatch_shape == "subagent-blocked" and not self.blocked_reason:
            raise ValueError("subagent-blocked dispatch requires blocked_reason")


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
    """Return whether an ordinary sp-* command should dispatch one subagent for one ready lane."""

    return command_name.strip().lower() in _ORDINARY_SP_COMMANDS


def _normalize_dispatch_shape(dispatch_shape: str) -> DispatchShape:
    if dispatch_shape in _CANONICAL_DISPATCH_SHAPES:
        return cast(DispatchShape, dispatch_shape)
    raise ValueError(f"Unsupported dispatch shape: {dispatch_shape}")


def _normalize_execution_surface(execution_surface: str) -> ExecutionSurface:
    if execution_surface in _CANONICAL_EXECUTION_SURFACES:
        return cast(ExecutionSurface, execution_surface)
    raise ValueError(f"Unsupported execution surface: {execution_surface}")


def _normalize_execution_model(execution_model: str) -> ExecutionModel:
    if execution_model in _CANONICAL_EXECUTION_MODELS:
        return cast(ExecutionModel, execution_model)
    raise ValueError(f"Unsupported execution model: {execution_model}")


def _normalize_workflow_status(workflow_status: str) -> WorkflowStatus:
    if workflow_status in _CANONICAL_WORKFLOW_STATUSES:
        return cast(WorkflowStatus, workflow_status)
    raise ValueError(f"Unsupported workflow status: {workflow_status}")


def _normalize_execution_mode(execution_mode: str) -> ExecutionMode:
    if execution_mode in _CANONICAL_EXECUTION_MODES:
        return cast(ExecutionMode, execution_mode)
    raise ValueError(f"Unsupported execution mode: {execution_mode}")


def _derive_execution_surface(dispatch_shape: DispatchShape) -> ExecutionSurface:
    normalized = _normalize_dispatch_shape(dispatch_shape)
    if normalized in {"one-subagent", "parallel-subagents"}:
        return "native-subagents"
    if normalized in {"leader-inline", "leader-inline-fallback"}:
        return "leader-inline"
    return "none"
