"""Reconcile lane recovery state against durable truth surfaces."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from specify_cli.hooks.checkpoint_serializers import (
    serialize_implement_tracker,
    serialize_workflow_state,
)

from .lease import lane_lease_expired
from .models import LaneRecord
from .state_store import read_lane_lease, write_lane_recovery


def _persist_recovery_summary(project_root: Path, lane: LaneRecord, *, command_name: str) -> None:
    write_lane_recovery(
        project_root,
        lane.lane_id,
        {
            "command_name": command_name,
            "recovery_state": lane.recovery_state,
            "recovery_reason": lane.recovery_reason,
            "last_stable_checkpoint": lane.last_stable_checkpoint,
        },
    )


def reconcile_lane(project_root: Path, lane: LaneRecord, *, command_name: str) -> LaneRecord:
    """Classify whether a lane is resumable for the given command."""

    feature_dir = project_root / lane.feature_dir
    workflow_path = feature_dir / "workflow-state.md"
    tracker_path = feature_dir / "implement-tracker.md"

    updated = replace(lane)

    if command_name == "implement":
        if not workflow_path.exists() or not tracker_path.exists():
            updated.recovery_state = "blocked"
            updated.recovery_reason = "missing implement stage artifacts"
            _persist_recovery_summary(project_root, updated, command_name=command_name)
            return updated

        workflow = serialize_workflow_state(workflow_path)
        tracker = serialize_implement_tracker(tracker_path)
        lease = read_lane_lease(project_root, lane.lane_id)

        next_command = str(workflow.get("next_command") or "")
        tracker_status = str(tracker.get("status") or "")
        tracker_next_action = str(tracker.get("next_action") or "")

        if next_command != "/sp.implement" and tracker_status not in {"blocked", "resolved"}:
            updated.recovery_state = "uncertain"
            updated.recovery_reason = (
                f"next_command {next_command} conflicts with tracker status {tracker_status}"
            )
            _persist_recovery_summary(project_root, updated, command_name=command_name)
            return updated

        if lease is not None and lane_lease_expired(lease) and tracker_status not in {"blocked", "resolved"}:
            if not tracker_next_action:
                updated.recovery_state = "uncertain"
                updated.recovery_reason = "expired lease without reliable next action"
                _persist_recovery_summary(project_root, updated, command_name=command_name)
                return updated

        updated.recovery_state = "resumable"
        updated.last_stable_checkpoint = str(tracker.get("current_batch") or "implement-ready")
        updated.recovery_reason = ""
        _persist_recovery_summary(project_root, updated, command_name=command_name)
        return updated

    if not workflow_path.exists():
        updated.recovery_state = "blocked"
        updated.recovery_reason = "missing workflow-state.md"
        _persist_recovery_summary(project_root, updated, command_name=command_name)
        return updated

    workflow = serialize_workflow_state(workflow_path)
    next_command = str(workflow.get("next_command") or "")
    expected = f"/sp.{command_name}"
    if next_command and next_command != expected:
        updated.recovery_state = "uncertain"
        updated.recovery_reason = f"next_command {next_command} does not match {expected}"
        _persist_recovery_summary(project_root, updated, command_name=command_name)
        return updated

    updated.recovery_state = "resumable"
    updated.last_stable_checkpoint = str(workflow.get("next_action") or expected)
    updated.recovery_reason = ""
    _persist_recovery_summary(project_root, updated, command_name=command_name)
    return updated
