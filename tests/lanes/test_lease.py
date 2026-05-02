from datetime import datetime, timedelta, timezone

from specify_cli.lanes.lease import lane_lease_expired, validate_lane_write_lease
from specify_cli.lanes.models import LaneLease


def test_lane_lease_expired_returns_true_when_renew_until_is_past():
    lease = LaneLease(
        lane_id="lane-001",
        session_id="sess-1",
        owner_command="implement",
        acquired_at="2026-05-02T00:00:00+00:00",
        renew_until=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        repo_root="F:/github/spec-kit-plus",
        runtime_token="tok-1",
    )

    assert lane_lease_expired(lease) is True


def test_validate_lane_write_lease_blocks_second_active_writer():
    lease = LaneLease(
        lane_id="lane-001",
        session_id="sess-1",
        owner_command="implement",
        acquired_at="2026-05-02T00:00:00+00:00",
        renew_until=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        repo_root="F:/github/spec-kit-plus",
        runtime_token="tok-1",
    )

    status = validate_lane_write_lease(lease, requester_session_id="sess-2")

    assert status == "blocked"
