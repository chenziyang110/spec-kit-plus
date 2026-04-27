"""Shared dispatcher for first-party workflow quality hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .artifact_validation import validate_artifacts_hook
from .checkpoint import checkpoint_hook
from .commit_validation import commit_validation_hook
from .context_monitor import context_monitor_hook
from .delegation import validate_join_hook, validate_packet_hook
from .events import (
    CANONICAL_HOOK_EVENTS,
    DELEGATION_JOIN_VALIDATE,
    DELEGATION_PACKET_VALIDATE,
    PROJECT_MAP_COMPLETE_REFRESH,
    PROJECT_MAP_MARK_DIRTY,
    WORKFLOW_ARTIFACTS_VALIDATE,
    WORKFLOW_CHECKPOINT,
    WORKFLOW_CONTEXT_MONITOR,
    WORKFLOW_PREFLIGHT,
    WORKFLOW_BOUNDARY_VALIDATE,
    WORKFLOW_COMMIT_VALIDATE,
    WORKFLOW_PHASE_BOUNDARY_VALIDATE,
    WORKFLOW_PROMPT_GUARD_VALIDATE,
    WORKFLOW_READ_GUARD_VALIDATE,
    WORKFLOW_SESSION_STATE_VALIDATE,
    WORKFLOW_STATE_VALIDATE,
    WORKFLOW_STATUSLINE_RENDER,
)
from .prompt_guard import prompt_guard_hook
from .preflight import workflow_preflight_hook
from .project_map import complete_refresh_hook, mark_dirty_hook
from .read_guard import read_guard_hook
from .session_state import session_state_hook
from .state_validation import validate_state_hook
from .statusline import statusline_hook
from .workflow_boundary import phase_boundary_hook, workflow_boundary_hook
from .types import HookResult, QualityHookError


HookFn = Callable[[Path, dict[str, object]], HookResult]


_HOOK_REGISTRY: dict[str, HookFn] = {
    WORKFLOW_PREFLIGHT: workflow_preflight_hook,
    WORKFLOW_STATE_VALIDATE: validate_state_hook,
    WORKFLOW_ARTIFACTS_VALIDATE: validate_artifacts_hook,
    WORKFLOW_CHECKPOINT: checkpoint_hook,
    WORKFLOW_CONTEXT_MONITOR: context_monitor_hook,
    WORKFLOW_SESSION_STATE_VALIDATE: session_state_hook,
    WORKFLOW_STATUSLINE_RENDER: statusline_hook,
    WORKFLOW_READ_GUARD_VALIDATE: read_guard_hook,
    WORKFLOW_PROMPT_GUARD_VALIDATE: prompt_guard_hook,
    WORKFLOW_BOUNDARY_VALIDATE: workflow_boundary_hook,
    WORKFLOW_PHASE_BOUNDARY_VALIDATE: phase_boundary_hook,
    WORKFLOW_COMMIT_VALIDATE: commit_validation_hook,
    DELEGATION_PACKET_VALIDATE: validate_packet_hook,
    DELEGATION_JOIN_VALIDATE: validate_join_hook,
    PROJECT_MAP_MARK_DIRTY: mark_dirty_hook,
    PROJECT_MAP_COMPLETE_REFRESH: complete_refresh_hook,
}


def run_quality_hook(
    project_root: Path,
    event_name: str,
    payload: dict[str, object] | None = None,
) -> HookResult:
    normalized = str(event_name or "").strip()
    if normalized not in CANONICAL_HOOK_EVENTS:
        raise QualityHookError(f"Unknown hook event: {normalized or '<empty>'}")
    if normalized not in _HOOK_REGISTRY:
        raise QualityHookError(f"Hook event is not implemented yet: {normalized}")
    return _HOOK_REGISTRY[normalized](project_root, payload or {})
