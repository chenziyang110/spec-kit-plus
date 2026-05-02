"""Lane closeout helpers for sp-integrate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import LaneRecord
from .reconcile import reconcile_lane
from .state_store import (
    append_lane_event,
    read_lane_index,
    read_lane_record,
    rebuild_lane_index,
    write_lane_record,
)


def collect_integration_candidates(project_root: Path) -> list[LaneRecord]:
    """Return lanes that are ready to close out through sp-integrate."""

    payload = read_lane_index(project_root) or {}
    candidates: list[LaneRecord] = []
    for item in payload.get("lanes", []):
        if not isinstance(item, dict) or not item.get("lane_id"):
            continue
        lane = read_lane_record(project_root, str(item["lane_id"]))
        if lane is None:
            continue
        if lane.recovery_state == "completed" or (
            lane.lifecycle_state == "implementing" and lane.verification_status == "passed"
        ):
            candidates.append(lane)
    return candidates


@dataclass(slots=True)
class IntegrationReadiness:
    """Structured readiness report for one lane closeout candidate."""

    lane: LaneRecord
    ready: bool
    checks: list[dict[str, str]]


def assess_integration_readiness(project_root: Path, lane: LaneRecord) -> IntegrationReadiness:
    """Evaluate whether one lane is ready for closeout."""

    reconciled = reconcile_lane(project_root, lane, command_name=lane.last_command or "implement")
    checks: list[dict[str, str]] = []
    feature_dir = project_root / reconciled.feature_dir

    branch_status = "pass" if reconciled.branch_name.strip() else "fail"
    checks.append(
        {
            "name": "branch-bound",
            "status": branch_status,
            "detail": reconciled.branch_name or "missing branch name",
        }
    )

    feature_dir_status = "pass" if feature_dir.exists() else "fail"
    checks.append(
        {
            "name": "feature-dir-exists",
            "status": feature_dir_status,
            "detail": str(feature_dir),
        }
    )

    implementation_complete = False
    if reconciled.last_command == "integrate":
        implementation_complete = reconciled.recovery_state == "completed"
    elif reconciled.last_command == "implement":
        from specify_cli.hooks.checkpoint_serializers import serialize_implement_tracker

        tracker_path = feature_dir / "implement-tracker.md"
        if tracker_path.exists():
            tracker = serialize_implement_tracker(tracker_path)
            implementation_complete = str(tracker.get("status") or "") == "resolved"
        else:
            implementation_complete = reconciled.recovery_state == "completed"
    else:
        implementation_complete = reconciled.recovery_state == "completed"

    recovery_status = "pass" if implementation_complete else "fail"
    checks.append(
        {
            "name": "implementation-complete",
            "status": recovery_status,
            "detail": reconciled.recovery_state if reconciled.last_command != "implement" else "resolved-tracker-required",
        }
    )

    verification_status = "pass" if reconciled.verification_status == "passed" else "fail"
    checks.append(
        {
            "name": "verification-passed",
            "status": verification_status,
            "detail": reconciled.verification_status,
        }
    )

    ready = all(check["status"] == "pass" for check in checks)
    return IntegrationReadiness(lane=reconciled, ready=ready, checks=checks)


def mark_lane_integrated(project_root: Path, lane: LaneRecord) -> LaneRecord:
    """Mark a lane completed after closeout."""

    lane.lifecycle_state = "completed"
    lane.recovery_state = "completed"
    lane.last_command = "integrate"
    write_lane_record(project_root, lane)
    append_lane_event(
        project_root,
        lane.lane_id,
        {
            "event": "lane_integrated",
            "lane_id": lane.lane_id,
            "feature_id": lane.feature_id,
            "feature_dir": lane.feature_dir,
        },
    )
    rebuild_lane_index(project_root)
    return lane
