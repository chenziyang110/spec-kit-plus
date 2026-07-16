"""Helpers for recognizing misplaced first-party native hook artifacts."""

from __future__ import annotations

from typing import Any


def is_claude_managed_hook(hook: Any) -> bool:
    """Return True when *hook* invokes the first-party Claude hook route."""

    if not isinstance(hook, dict):
        return False

    command = str(hook.get("command") or "")
    if "claude-hook-dispatch.py" in command:
        return True
    if "specify-hook" in command and " claude " in f" {command} ":
        return True

    args = hook.get("args")
    if not isinstance(args, list):
        return False

    normalized_args = [str(arg) for arg in args]
    joined_args = " ".join(normalized_args)
    return "specify-hook" in joined_args and " claude " in f" {joined_args} "


def strip_claude_managed_hook_entries(payload: Any) -> tuple[Any, bool]:
    """Remove Claude managed hook entries from a native hook settings payload."""

    if not isinstance(payload, dict):
        return payload, False

    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return payload, False

    changed = False
    next_hooks: dict[str, Any] = {}

    for event_name, entries in hooks.items():
        if not isinstance(entries, list):
            next_hooks[event_name] = entries
            continue

        next_entries: list[Any] = []
        for entry in entries:
            if not isinstance(entry, dict):
                next_entries.append(entry)
                continue

            hook_items = entry.get("hooks")
            if not isinstance(hook_items, list):
                next_entries.append(entry)
                continue

            kept_hooks = []
            removed_managed_hook = False
            for hook in hook_items:
                if is_claude_managed_hook(hook):
                    changed = True
                    removed_managed_hook = True
                else:
                    kept_hooks.append(hook)

            if not removed_managed_hook:
                next_entries.append(entry)
            elif kept_hooks:
                next_entry = dict(entry)
                next_entry["hooks"] = kept_hooks
                next_entries.append(next_entry)
            else:
                changed = True

        if next_entries:
            next_hooks[event_name] = next_entries
        elif event_name in hooks:
            changed = True

    if not changed:
        return payload, False

    next_payload = dict(payload)
    if next_hooks:
        next_payload["hooks"] = next_hooks
    else:
        next_payload.pop("hooks", None)
    return next_payload, True


def contains_claude_managed_hook_entries(payload: Any) -> bool:
    """Return True when a native hook settings payload contains Claude routes."""

    _, changed = strip_claude_managed_hook_entries(payload)
    return changed
