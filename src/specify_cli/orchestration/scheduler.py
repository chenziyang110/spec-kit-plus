"""Roadmap-aware milestone scheduling helpers for leader-only execution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re

from .models import MilestoneExecutionDecision, PhaseExecutionState, utc_now

_PHASE_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _coerce_phase_number(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean phase numbers are not supported")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = _PHASE_NUMBER_RE.search(value.strip())
        if match:
            return float(match.group(1))
    raise ValueError(f"Unsupported phase number: {value!r}")


def _coerce_phase_state(candidate: PhaseExecutionState | Mapping[str, object]) -> PhaseExecutionState:
    if isinstance(candidate, PhaseExecutionState):
        return candidate

    return PhaseExecutionState(
        phase_number=_coerce_phase_number(candidate["phase_number"]),
        phase_name=str(candidate["phase_name"]),
        ready_batch_count=int(candidate.get("ready_batch_count", 0)),
        leader_mode=bool(candidate.get("leader_mode", True)),
        continue_milestone=bool(candidate.get("continue_milestone", True)),
        current_batch_id=(
            str(candidate["current_batch_id"]) if candidate.get("current_batch_id") is not None else None
        ),
        blocking_reason=(
            str(candidate["blocking_reason"]) if candidate.get("blocking_reason") is not None else None
        ),
        created_at=str(candidate.get("created_at")) if candidate.get("created_at") else utc_now(),
    )


def _ordered_phases(
    phases: Iterable[PhaseExecutionState | Mapping[str, object]],
) -> list[PhaseExecutionState]:
    return sorted(
        (_coerce_phase_state(phase) for phase in phases),
        key=lambda phase: phase.phase_number,
    )


def select_next_phase(
    phases: Iterable[PhaseExecutionState | Mapping[str, object]],
    *,
    current_phase_number: float | int | str | None = None,
) -> PhaseExecutionState | None:
    """Select the next executable phase, preserving numeric roadmap order."""

    ordered = _ordered_phases(phases)
    current_number = _coerce_phase_number(current_phase_number) if current_phase_number is not None else None

    for phase in ordered:
        if phase.ready_batch_count <= 0 or phase.blocking_reason:
            continue
        if current_number is not None and phase.phase_number < current_number:
            continue
        return phase

    return None


def build_milestone_execution_decision(
    phases: Iterable[PhaseExecutionState | Mapping[str, object]],
    *,
    current_phase_number: float | int | str | None = None,
) -> MilestoneExecutionDecision | None:
    """Build a scheduler decision for the next ready batch and milestone continuation."""

    ordered = _ordered_phases(phases)
    selected_phase = select_next_phase(ordered, current_phase_number=current_phase_number)
    if selected_phase is None:
        return None

    next_ready_phase = None
    for phase in ordered:
        if phase.phase_number <= selected_phase.phase_number:
            continue
        if phase.ready_batch_count <= 0 or phase.blocking_reason:
            continue
        next_ready_phase = phase
        break

    # Continue automatically while the current phase still has queued work or a later
    # roadmap-ordered phase is already executable.
    continue_milestone = selected_phase.ready_batch_count > 1 or next_ready_phase is not None

    return MilestoneExecutionDecision(
        phase_number=selected_phase.phase_number,
        phase_name=selected_phase.phase_name,
        ready_batch_count=selected_phase.ready_batch_count,
        leader_mode=selected_phase.leader_mode,
        continue_milestone=continue_milestone,
        next_phase_number=next_ready_phase.phase_number if next_ready_phase else None,
        next_phase_name=next_ready_phase.phase_name if next_ready_phase else None,
        selected_batch_id=selected_phase.current_batch_id,
        reason="roadmap-order",
    )


__all__ = ["build_milestone_execution_decision", "select_next_phase"]
