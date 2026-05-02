from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import (
    lane_index_path,
    lane_record_path,
    read_lane_index,
    read_lane_record,
    rebuild_lane_index,
    write_lane_index,
    write_lane_record,
    write_lane_recovery,
)


def test_lane_paths_live_under_specify_lanes(tmp_path: Path):
    assert lane_index_path(tmp_path) == tmp_path / ".specify" / "lanes" / "index.json"
    assert (
        lane_record_path(tmp_path, "lane-001")
        == tmp_path / ".specify" / "lanes" / "lane-001" / "lane.json"
    )


def test_write_and_read_lane_record_round_trip(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )

    write_lane_record(tmp_path, lane)
    loaded = read_lane_record(tmp_path, "lane-001")

    assert loaded is not None
    assert loaded.lane_id == "lane-001"
    assert loaded.recovery_state == "resumable"
    assert loaded.last_command == "implement"


def test_write_and_read_lane_index_round_trip(tmp_path: Path):
    payload = {
        "lanes": [
            {"lane_id": "lane-001", "feature_id": "001-demo", "last_command": "implement"}
        ]
    }

    write_lane_index(tmp_path, payload)
    assert read_lane_index(tmp_path) == payload


def test_rebuild_lane_index_uses_lane_records(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )

    write_lane_record(tmp_path, lane)
    write_lane_recovery(
        tmp_path,
        "lane-001",
        {
            "command_name": "implement",
            "recovery_state": "resumable",
            "recovery_reason": "",
            "last_stable_checkpoint": "batch-a",
        },
    )

    payload = rebuild_lane_index(tmp_path)

    assert payload == {
        "lanes": [
            {
                "lane_id": "lane-001",
                "feature_id": "001-demo",
                "feature_dir": "specs/001-demo",
                "last_command": "implement",
                "recovery_state": "resumable",
            }
        ]
    }
