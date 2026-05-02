"""Durable storage for concurrent workflow lanes."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from specify_cli.orchestration.state_store import read_json, write_json

from .models import LaneLease, LaneRecord


def lanes_root(project_root: Path) -> Path:
    """Return the root directory for lane state."""

    return project_root / ".specify" / "lanes"


def lane_index_path(project_root: Path) -> Path:
    """Return the lane index path."""

    return lanes_root(project_root) / "index.json"


def lane_dir(project_root: Path, lane_id: str) -> Path:
    """Return the directory that owns one lane's durable files."""

    return lanes_root(project_root) / lane_id


def lane_record_path(project_root: Path, lane_id: str) -> Path:
    """Return the path for a lane record."""

    return lane_dir(project_root, lane_id) / "lane.json"


def lane_events_path(project_root: Path, lane_id: str) -> Path:
    """Return the append-only event log path for a lane."""

    return lane_dir(project_root, lane_id) / "events.ndjson"


def lane_lease_path(project_root: Path, lane_id: str) -> Path:
    """Return the write-lease path for a lane."""

    return lane_dir(project_root, lane_id) / "lease.json"


def lane_recovery_path(project_root: Path, lane_id: str) -> Path:
    """Return the reconcile summary path for a lane."""

    return lane_dir(project_root, lane_id) / "recovery.json"


def write_lane_index(project_root: Path, payload: dict[str, object]) -> Path:
    """Persist the rebuildable lane index."""

    return write_json(lane_index_path(project_root), payload)


def read_lane_index(project_root: Path) -> dict[str, object] | None:
    """Read the rebuildable lane index when present."""

    payload = read_json(lane_index_path(project_root))
    if payload is None:
        return None
    return payload


def write_lane_record(project_root: Path, lane: LaneRecord) -> Path:
    """Persist one lane record."""

    return write_json(lane_record_path(project_root, lane.lane_id), asdict(lane))


def read_lane_record(project_root: Path, lane_id: str) -> LaneRecord | None:
    """Read one lane record when present."""

    payload = read_json(lane_record_path(project_root, lane_id))
    if payload is None:
        return None
    return LaneRecord(**payload)


def iter_lane_records(project_root: Path) -> list[LaneRecord]:
    """Read every lane record under the lanes root."""

    root = lanes_root(project_root)
    records: list[LaneRecord] = []
    if not root.exists():
        return records
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        record = read_lane_record(project_root, child.name)
        if record is not None:
            records.append(record)
    return records


def write_lane_lease(project_root: Path, lease: LaneLease) -> Path:
    """Persist a lane write lease."""

    return write_json(lane_lease_path(project_root, lease.lane_id), asdict(lease))


def read_lane_lease(project_root: Path, lane_id: str) -> LaneLease | None:
    """Read a lane write lease."""

    payload = read_json(lane_lease_path(project_root, lane_id))
    if payload is None:
        return None
    return LaneLease(**payload)


def write_lane_recovery(project_root: Path, lane_id: str, payload: dict[str, object]) -> Path:
    """Persist the latest reconcile summary for a lane."""

    return write_json(lane_recovery_path(project_root, lane_id), payload)


def read_lane_recovery(project_root: Path, lane_id: str) -> dict[str, object] | None:
    """Read the latest reconcile summary for a lane."""

    payload = read_json(lane_recovery_path(project_root, lane_id))
    if payload is None:
        return None
    return payload


def append_lane_event(project_root: Path, lane_id: str, payload: dict[str, object]) -> Path:
    """Append one NDJSON event to the lane event log."""

    path = lane_events_path(project_root, lane_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return path


def rebuild_lane_index(project_root: Path) -> dict[str, object]:
    """Rebuild the lane index from durable lane records."""

    payload: dict[str, object] = {
        "lanes": [
            {
                "lane_id": record.lane_id,
                "feature_id": record.feature_id,
                "feature_dir": record.feature_dir,
                "last_command": record.last_command,
                "recovery_state": record.recovery_state,
            }
            for record in iter_lane_records(project_root)
        ]
    }
    write_lane_index(project_root, payload)
    return payload
