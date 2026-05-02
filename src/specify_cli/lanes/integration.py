"""Lane closeout helpers for sp-integrate."""

from __future__ import annotations

from pathlib import Path

from .models import LaneRecord
from .state_store import read_lane_index, read_lane_record, write_lane_record


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
            lane.lifecycle_state == "implementing" and lane.recovery_state == "completed"
        ):
            candidates.append(lane)
    return candidates


def mark_lane_integrated(project_root: Path, lane: LaneRecord) -> LaneRecord:
    """Mark a lane completed after closeout."""

    lane.lifecycle_state = "completed"
    lane.recovery_state = "completed"
    lane.last_command = "integrate"
    write_lane_record(project_root, lane)
    return lane
