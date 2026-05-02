from dataclasses import asdict

from specify_cli.lanes.models import LaneLease, LaneRecord


def test_lane_record_defaults_to_draft_and_blocked_safe_values():
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-parallel-lane",
        feature_dir="specs/001-parallel-lane",
        branch_name="001-parallel-lane",
        worktree_path=".specify/lanes/worktrees/lane-001",
    )

    payload = asdict(lane)

    assert lane.lifecycle_state == "draft"
    assert lane.recovery_state == "blocked"
    assert lane.last_command == ""
    assert payload["lane_id"] == "lane-001"
    assert payload["feature_id"] == "001-parallel-lane"


def test_lane_lease_tracks_owner_and_expiry_fields():
    lease = LaneLease(
        lane_id="lane-001",
        session_id="sess-1",
        owner_command="implement",
        acquired_at="2026-05-02T00:00:00+00:00",
        renew_until="2026-05-02T00:05:00+00:00",
        repo_root="F:/github/spec-kit-plus",
        runtime_token="tok-1",
    )

    assert lease.owner_command == "implement"
    assert lease.session_id == "sess-1"
    assert lease.runtime_token == "tok-1"
