"""Shared commit validation hook."""

from __future__ import annotations

from pathlib import Path
import re

from .checkpoint_serializers import serialize_implement_tracker
from .events import WORKFLOW_COMMIT_VALIDATE
from .types import HookResult, QualityHookError


COMMIT_MESSAGE_RE = re.compile(r"^(feat|fix|docs|refactor|test|chore)(\([^)]+\))?:\s+\S", re.IGNORECASE)
TERMINAL_TRACKER_STATUSES = {"resolved"}


def commit_validation_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    commit_message = str(payload.get("commit_message") or "").strip()
    if not commit_message:
        raise QualityHookError("commit_message is required")

    errors: list[str] = []
    if not COMMIT_MESSAGE_RE.match(commit_message):
        errors.append("commit message must follow conventional commit format")

    raw_feature_dir = str(payload.get("feature_dir") or "").strip()
    if raw_feature_dir:
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()
        tracker_path = feature_dir / "implement-tracker.md"
        if tracker_path.exists():
            tracker = serialize_implement_tracker(tracker_path)
            tracker_status = str(tracker.get("status") or "").strip().lower()
            if tracker_status and tracker_status not in TERMINAL_TRACKER_STATUSES:
                errors.append(f"implement-tracker is still {tracker_status}; commit should not finalize this workflow yet")

    if errors:
        return HookResult(
            event=WORKFLOW_COMMIT_VALIDATE,
            status="blocked",
            severity="critical",
            errors=errors,
        )

    return HookResult(
        event=WORKFLOW_COMMIT_VALIDATE,
        status="ok",
        severity="info",
        data={"commit_message": commit_message},
    )

