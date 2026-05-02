"""Lease helpers for lane write coordination."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import LaneLease


def lane_lease_expired(lease: LaneLease, *, now: datetime | None = None) -> bool:
    """Return whether a lane lease has expired."""

    current = now or datetime.now(timezone.utc)
    return datetime.fromisoformat(lease.renew_until) <= current


def validate_lane_write_lease(
    lease: LaneLease | None,
    *,
    requester_session_id: str,
    now: datetime | None = None,
) -> str:
    """Return the write availability for a requester."""

    if lease is None:
        return "available"
    if lease.session_id == requester_session_id:
        return "owned"
    if lane_lease_expired(lease, now=now):
        return "expired"
    return "blocked"
