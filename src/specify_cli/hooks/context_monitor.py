"""Context pressure monitoring hooks for proactive recovery checkpointing."""

from __future__ import annotations

from pathlib import Path

from .checkpoint import checkpoint_hook
from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_CONTEXT_MONITOR
from .types import HookResult


STRUCTURAL_CHECKPOINT_TRIGGERS = {
    "before_join_point",
    "before_delegation",
    "before_stop",
    "before_long_validation",
    "after_artifact_synthesis",
}
DEFAULT_WARNING_THRESHOLD = 80


def context_monitor_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    trigger = str(payload.get("trigger") or "").strip().lower()
    raw_usage = payload.get("context_usage_percent")
    usage = _normalize_percent(raw_usage)

    structural_trigger = trigger in STRUCTURAL_CHECKPOINT_TRIGGERS
    threshold_trigger = usage is not None and usage >= DEFAULT_WARNING_THRESHOLD
    should_checkpoint = structural_trigger or threshold_trigger

    reasons: list[str] = []
    if structural_trigger:
        reasons.append(f"structural trigger: {trigger}")
    if threshold_trigger and usage is not None:
        reasons.append(f"context usage at {usage}%")

    if not should_checkpoint:
        return HookResult(
            event=WORKFLOW_CONTEXT_MONITOR,
            status="ok",
            severity="info",
            data={
                "should_checkpoint": False,
                "command_name": command_name,
                "trigger": trigger or "turn-progress",
                "context_usage_percent": usage,
                "reasons": [],
            },
        )

    checkpoint = checkpoint_hook(project_root, payload)
    if checkpoint.status == "blocked":
        return HookResult(
            event=WORKFLOW_CONTEXT_MONITOR,
            status="blocked",
            severity="critical",
            errors=list(checkpoint.errors),
            data={
                "should_checkpoint": True,
                "command_name": command_name,
                "trigger": trigger or "turn-progress",
                "context_usage_percent": usage,
                "reasons": reasons,
            },
        )

    return HookResult(
        event=WORKFLOW_CONTEXT_MONITOR,
        status="warn",
        severity="warning",
        warnings=["checkpoint recommended before further work continues"],
        data={
            "should_checkpoint": True,
            "command_name": command_name,
            "trigger": trigger or "turn-progress",
            "context_usage_percent": usage,
            "reasons": reasons,
            "checkpoint": checkpoint.data["checkpoint"],
        },
    )


def _normalize_percent(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return 0
    if parsed > 100:
        return 100
    return parsed

