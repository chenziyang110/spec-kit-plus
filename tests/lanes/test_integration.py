from pathlib import Path

from specify_cli.lanes.integration import assess_integration_readiness, collect_integration_candidates, mark_lane_integrated
from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


def test_collect_integration_candidates_returns_completed_or_ready_lanes(tmp_path: Path):
    ready_lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        verification_status="passed",
        last_command="implement",
    )
    blocked_lane = LaneRecord(
        lane_id="lane-002",
        feature_id="002-demo",
        feature_dir="specs/002-demo",
        branch_name="002-demo",
        worktree_path=".specify/lanes/worktrees/lane-002",
        lifecycle_state="implementing",
        recovery_state="blocked",
        last_command="implement",
    )
    write_lane_record(tmp_path, ready_lane)
    write_lane_record(tmp_path, blocked_lane)
    write_lane_index(
        tmp_path,
        {"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]},
    )

    candidates = collect_integration_candidates(tmp_path)

    assert [candidate.feature_id for candidate in candidates] == ["001-demo"]


def test_assess_integration_readiness_reports_failed_checks(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="blocked",
        verification_status="failed",
        last_command="implement",
    )

    readiness = assess_integration_readiness(tmp_path, lane)

    assert readiness.ready is False
    assert any(check["name"] == "verification-passed" and check["status"] == "fail" for check in readiness.checks)


def test_mark_lane_integrated_marks_completed_and_preserves_lane_id(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="integrating",
        recovery_state="resumable",
        verification_status="passed",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane)

    updated = mark_lane_integrated(tmp_path, lane)

    assert updated.lane_id == "lane-001"
    assert updated.lifecycle_state == "completed"
    assert updated.recovery_state == "completed"
    assert updated.last_command == "integrate"
