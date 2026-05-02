"""Resolve the active lane for root-level resumable commands."""

from __future__ import annotations

from pathlib import Path

from specify_cli.hooks.checkpoint_serializers import (
    normalize_command_name,
    serialize_implement_tracker,
    serialize_workflow_state,
)

from .models import LaneResolutionCandidate, LaneResolutionResult
from .reconcile import reconcile_lane
from .state_store import read_lane_index, read_lane_record, rebuild_lane_index


def _candidate_lane_ids(project_root: Path) -> list[str]:
    index = read_lane_index(project_root)
    if index is None:
        index = rebuild_lane_index(project_root)
    lanes = index.get("lanes", [])
    if not isinstance(lanes, list):
        return []
    lane_ids: list[str] = []
    for item in lanes:
        if isinstance(item, dict) and item.get("lane_id"):
            lane_ids.append(str(item["lane_id"]))
    return lane_ids


def _inferred_command_name(project_root: Path, lane) -> str:
    feature_dir = project_root / lane.feature_dir
    tracker_path = feature_dir / "implement-tracker.md"
    workflow_path = feature_dir / "workflow-state.md"

    if tracker_path.exists():
        tracker = serialize_implement_tracker(tracker_path)
        tracker_status = str(tracker.get("status") or "")
        if tracker_status in {"gathering", "executing", "recovering", "replanning", "validating", "blocked", "resolved"}:
            return "implement"

    if workflow_path.exists():
        workflow = serialize_workflow_state(workflow_path)
        next_command = str(workflow.get("next_command") or "")
        if next_command:
            return normalize_command_name(next_command)

    lane_command = (lane.last_command or "").strip().lower()
    return lane_command or "specify"


def resolve_lane_for_command(project_root: Path, *, command_name: str) -> LaneResolutionResult:
    """Resolve the correct lane for a resumable command."""

    normalized_command = command_name.strip().lower()
    candidates: list[LaneResolutionCandidate] = []

    for lane_id in _candidate_lane_ids(project_root):
        lane = read_lane_record(project_root, lane_id)
        if lane is None:
            continue
        inferred_command = _inferred_command_name(project_root, lane)
        if normalized_command != "auto" and inferred_command != normalized_command:
            continue

        reconcile_command = inferred_command if normalized_command == "auto" else normalized_command
        reconciled = reconcile_lane(project_root, lane, command_name=reconcile_command)
        candidates.append(
            LaneResolutionCandidate(
                lane_id=reconciled.lane_id,
                feature_id=reconciled.feature_id,
                feature_dir=reconciled.feature_dir,
                last_command=reconcile_command,
                recovery_state=reconciled.recovery_state,
                last_stable_checkpoint=reconciled.last_stable_checkpoint,
                recovery_reason=reconciled.recovery_reason,
            )
        )

    resumable = [candidate for candidate in candidates if candidate.recovery_state == "resumable"]
    uncertain = [candidate for candidate in candidates if candidate.recovery_state == "uncertain"]

    if len(resumable) == 1 and not uncertain:
        return LaneResolutionResult(
            mode="resume",
            selected_lane_id=resumable[0].lane_id,
            reason="unique-safe-candidate",
            candidates=candidates,
        )
    if resumable or uncertain:
        return LaneResolutionResult(
            mode="choose",
            reason="ambiguous-or-uncertain",
            candidates=candidates,
        )
    return LaneResolutionResult(mode="start", reason="no-resumable-candidate", candidates=candidates)
