"""Project-map related first-party workflow hooks."""

from __future__ import annotations

from pathlib import Path

from specify_cli.execution import worker_task_packet_from_json
from specify_cli.project_map_status import (
    complete_project_map_refresh,
    git_head_commit,
    has_git_repo,
    inspect_project_map_freshness,
    mark_project_map_dirty,
    project_map_status_path,
)

from .events import PROJECT_MAP_COMPLETE_REFRESH, PROJECT_MAP_MARK_DIRTY
from .types import HookResult, QualityHookError


STALE_BLOCK_COMMANDS = {"implement", "quick", "fast", "specify", "plan", "tasks"}


def project_map_freshness_result(project_root: Path, *, command_name: str) -> HookResult:
    normalized = command_name.strip().lower()
    freshness = inspect_project_map_freshness(project_root)
    state = str(freshness.get("freshness", "")).strip().lower()
    reasons = [str(item) for item in freshness.get("reasons", []) if str(item).strip()]

    if state == "fresh":
        return HookResult(
            event="project_map.refresh.validate",
            status="ok",
            severity="info",
            data={"freshness": freshness},
        )
    if state == "stale" and normalized in STALE_BLOCK_COMMANDS:
        return HookResult(
            event="project_map.refresh.validate",
            status="blocked",
            severity="critical",
            errors=reasons or ["project-map freshness is stale"],
            data={"freshness": freshness},
        )
    return HookResult(
        event="project_map.refresh.validate",
        status="warn",
        severity="warning",
        warnings=reasons or [f"project-map freshness is {state or 'unknown'}"],
        data={"freshness": freshness},
    )


def mark_dirty_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    """Record manual dirty fallback state when a complete refresh cannot finish now."""

    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise QualityHookError("reason is required for project_map.mark_dirty")
    scope_paths: list[str] | None = None
    packet_file = str(payload.get("packet_file") or "").strip()
    if packet_file:
        packet_path = Path(packet_file)
        if not packet_path.is_absolute():
            packet_path = (project_root / packet_path).resolve()
        if packet_path.exists():
            packet = worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))
            scope_paths = list(dict.fromkeys([*packet.scope.write_scope, *packet.scope.read_scope]))
    status = mark_project_map_dirty(
        project_root,
        reason,
        origin_command=str(payload.get("origin_command") or "").strip(),
        origin_feature_dir=str(payload.get("origin_feature_dir") or "").strip(),
        origin_lane_id=str(payload.get("origin_lane_id") or "").strip(),
        scope_paths=scope_paths,
    )
    return HookResult(
        event=PROJECT_MAP_MARK_DIRTY,
        status="ok",
        severity="info",
        writes={"status_path": str(project_map_status_path(project_root))},
        data={"project_map_status": status.to_dict()},
    )


def complete_refresh_hook(project_root: Path, _payload: dict[str, object]) -> HookResult:
    """Finalize a successful full refresh against the current git baseline."""

    if not has_git_repo(project_root) or not git_head_commit(project_root):
        return HookResult(
            event=PROJECT_MAP_COMPLETE_REFRESH,
            status="blocked",
            severity="critical",
            errors=["git baseline unavailable for project-map complete-refresh"],
        )
    status = complete_project_map_refresh(project_root)
    return HookResult(
        event=PROJECT_MAP_COMPLETE_REFRESH,
        status="ok",
        severity="info",
        writes={"status_path": str(project_map_status_path(project_root))},
        data={"project_map_status": status.to_dict()},
    )
