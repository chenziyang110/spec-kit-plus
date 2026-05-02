"""Lane models for concurrent feature workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


LaneLifecycleState = Literal[
    "draft",
    "specified",
    "planned",
    "tasked",
    "implementing",
    "integrating",
    "completed",
    "abandoned",
]

LaneRecoveryState = Literal[
    "resumable",
    "uncertain",
    "blocked",
    "completed",
]


def utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class LaneRecord:
    """Durable lane record for one isolated feature workflow."""

    lane_id: str
    feature_id: str
    feature_dir: str
    branch_name: str
    worktree_path: str
    lifecycle_state: LaneLifecycleState = "draft"
    recovery_state: LaneRecoveryState = "blocked"
    last_command: str = ""
    last_stable_checkpoint: str = ""
    recovery_reason: str = ""
    verification_status: Literal["unknown", "passed", "failed"] = "unknown"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class LaneLease:
    """Single-writer lease for foreground lane mutations."""

    lane_id: str
    session_id: str
    owner_command: str
    acquired_at: str
    renew_until: str
    repo_root: str
    runtime_token: str = ""


@dataclass(slots=True)
class LaneResolutionCandidate:
    """Candidate lane returned during command-scoped resume resolution."""

    lane_id: str
    feature_id: str
    feature_dir: str
    last_command: str
    recovery_state: LaneRecoveryState
    last_stable_checkpoint: str
    recovery_reason: str = ""


@dataclass(slots=True)
class LaneResolutionResult:
    """Result of command-scoped lane resolution."""

    mode: Literal["resume", "choose", "start", "blocked"]
    selected_lane_id: str = ""
    reason: str = ""
    candidates: list[LaneResolutionCandidate] = field(default_factory=list)
