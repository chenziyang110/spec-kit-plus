#!/usr/bin/env python
"""Thin Gemini CLI native hook adapter for spec-kit-plus.

This script is installed into ``.gemini/hooks/`` for project-local Gemini
integrations. It translates Gemini hook payloads into the shared
``specify hook ...`` command surface so workflow truth stays in the canonical
Python hook engine instead of being duplicated inside standalone scripts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


WORKFLOW_COMMAND_MAP = {
    "sp-specify": "specify",
    "sp-spec-extend": "spec-extend",
    "sp-plan": "plan",
    "sp-tasks": "tasks",
    "sp-analyze": "analyze",
    "sp-test": "test",
    "sp-implement": "implement",
    "sp-debug": "debug",
    "sp-quick": "quick",
    "sp-fast": "fast",
    "sp-map-codebase": "map-codebase",
    "sp-constitution": "constitution",
    "sp-checklist": "checklist",
}
ACTIVE_STATE_STATUSES = {"active", "started", "starting", "in_progress", "executing", "execution"}
TERMINAL_STATE_STATUSES = {"resolved", "completed", "done", "cancelled", "closed", "blocked", "failed"}
LEARNING_SIGNAL_FIELDS = {
    "retry_attempts": "--retry-attempts",
    "hypothesis_changes": "--hypothesis-changes",
    "validation_failures": "--validation-failures",
    "artifact_rewrites": "--artifact-rewrites",
    "command_failures": "--command-failures",
    "user_corrections": "--user-corrections",
    "route_changes": "--route-changes",
    "scope_changes": "--scope-changes",
}


def _read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _project_root(payload: dict[str, Any]) -> Path:
    env_root = str(os.environ.get("GEMINI_PROJECT_DIR") or "").strip()
    if env_root:
        return Path(env_root).resolve()

    raw_cwd = str(payload.get("cwd") or "").strip()
    if raw_cwd:
        return Path(raw_cwd).resolve()

    return Path(__file__).resolve().parents[2]


def _run_shared_hook(project_root: Path, args: list[str]) -> dict[str, Any] | None:
    commands: list[list[str]] = []
    if shutil.which("specify"):
        commands.append(["specify", "hook", *args])
    commands.append([sys.executable, "-m", "specify_cli", "hook", *args])
    if shutil.which("py"):
        commands.append(["py", "-m", "specify_cli", "hook", *args])

    seen: set[tuple[str, ...]] = set()
    for command in commands:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        try:
            result = subprocess.run(
                command,
                cwd=project_root,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
        except OSError:
            continue
        if result.returncode != 0:
            continue
        stdout = (result.stdout or "").strip()
        if not stdout:
            continue
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _shared_additional_context(shared_payload: dict[str, Any] | None) -> str:
    if not shared_payload:
        return ""
    warnings = [str(item) for item in shared_payload.get("warnings", []) if str(item).strip()]
    actions = [str(item) for item in shared_payload.get("actions", []) if str(item).strip()]
    return " ".join([*warnings, *actions]).strip()


def _shared_block_to_gemini(
    shared_payload: dict[str, Any] | None,
    *,
    system_message: str = "",
) -> dict[str, Any] | None:
    if not shared_payload:
        return None
    status = str(shared_payload.get("status") or "").strip().lower()
    if status != "blocked":
        return None
    errors = [str(item) for item in shared_payload.get("errors", []) if str(item).strip()]
    warnings = [str(item) for item in shared_payload.get("warnings", []) if str(item).strip()]
    actions = [str(item) for item in shared_payload.get("actions", []) if str(item).strip()]
    reason = errors[0] if errors else (warnings[0] if warnings else "shared quality hook blocked the action")
    extra = " ".join([system_message, *warnings, *actions]).strip()
    output = {
        "decision": "deny",
        "reason": reason,
    }
    if extra:
        output["systemMessage"] = extra
    return output


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_field(text: str, field_name: str) -> str:
    pattern = re.compile(
        rf"^\s*-\s*{re.escape(field_name)}:\s*(.+?)\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        value = value[1:-1].strip()
    return value


def _extract_frontmatter_field(text: str, field_name: str) -> str:
    if not text.startswith("---\n"):
        return ""
    lines = text.splitlines()
    end_idx = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_idx = index
            break
    if end_idx is None:
        return ""
    for raw_line in lines[1:end_idx]:
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        if key.strip() != field_name:
            continue
        cleaned = value.strip()
        if cleaned.startswith("`") and cleaned.endswith("`") and len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()
        return cleaned
    return ""


def _extract_int_field(text: str, field_name: str) -> int:
    value = _extract_field(text, field_name) or _extract_frontmatter_field(text, field_name)
    if not value:
        return 0
    try:
        return int(value.strip())
    except ValueError:
        return 0


def _extract_list_field(text: str, field_name: str) -> list[str]:
    value = _extract_field(text, field_name)
    if not value:
        return []
    if value in {"[]", "-", "none", "None"}:
        return []
    return [
        item.strip(" -`\"'")
        for item in re.split(r"\s*[;,]\s*", value)
        if item.strip(" -`\"'")
    ]


def _extract_section_items(text: str, section_name: str) -> list[str]:
    heading = re.compile(rf"^##+\s+{re.escape(section_name)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = heading.search(text)
    if not match:
        return []
    next_heading = re.search(r"^##+\s+", text[match.end():], re.MULTILINE)
    section = text[match.end(): match.end() + next_heading.start()] if next_heading else text[match.end():]
    items: list[str] = []
    for raw_line in section.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            continue
        item = stripped[2:].strip(" `\"'")
        if item:
            items.append(item)
    return items


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _candidate_sort_key(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _infer_active_context(project_root: Path) -> dict[str, str] | None:
    implement_candidates: list[tuple[float, dict[str, str]]] = []
    for tracker_path in project_root.glob("specs/*/implement-tracker.md"):
        text = _read_text(tracker_path)
        if not text:
            continue
        status = _extract_frontmatter_field(text, "status").lower()
        if not status or status in TERMINAL_STATE_STATUSES:
            continue
        implement_candidates.append(
            (
                _candidate_sort_key(tracker_path),
                {
                    "command_name": "implement",
                    "feature_dir": str(tracker_path.parent),
                    "state_file": str(tracker_path),
                },
            )
        )
    if implement_candidates:
        return max(implement_candidates, key=lambda item: item[0])[1]

    quick_candidates: list[tuple[float, dict[str, str]]] = []
    for status_path in project_root.glob(".planning/quick/*/STATUS.md"):
        text = _read_text(status_path)
        if not text:
            continue
        status = _extract_frontmatter_field(text, "status").lower()
        if not status or status in TERMINAL_STATE_STATUSES:
            continue
        quick_candidates.append(
            (
                _candidate_sort_key(status_path),
                {
                    "command_name": "quick",
                    "workspace": str(status_path.parent),
                    "state_file": str(status_path),
                },
            )
        )
    if quick_candidates:
        return max(quick_candidates, key=lambda item: item[0])[1]

    workflow_candidates: list[tuple[float, dict[str, str]]] = []
    for workflow_path in project_root.glob("specs/*/workflow-state.md"):
        text = _read_text(workflow_path)
        if not text:
            continue
        active_command = _extract_field(text, "active_command").lower()
        status = _extract_field(text, "status").lower()
        mapped = WORKFLOW_COMMAND_MAP.get(active_command)
        if not mapped or (status and status not in ACTIVE_STATE_STATUSES):
            continue
        workflow_candidates.append(
            (
                _candidate_sort_key(workflow_path),
                {
                    "command_name": mapped,
                    "feature_dir": str(workflow_path.parent),
                    "state_file": str(workflow_path),
                },
            )
        )
    if workflow_candidates:
        return max(workflow_candidates, key=lambda item: item[0])[1]

    return None


def _extract_prompt_text(payload: dict[str, Any]) -> str:
    llm_request = payload.get("llm_request") or payload.get("llmRequest")
    if isinstance(llm_request, dict):
        messages = llm_request.get("messages")
        if isinstance(messages, list):
            parts: list[str] = []
            for message in messages:
                if not isinstance(message, dict):
                    continue
                role = str(message.get("role") or "").strip().lower()
                if role and role != "user":
                    continue
                content = str(message.get("content") or "").strip()
                if content:
                    parts.append(content)
                message_parts = message.get("parts")
                if isinstance(message_parts, list):
                    for part in message_parts:
                        if not isinstance(part, dict):
                            continue
                        text = str(part.get("text") or "").strip()
                        if text:
                            parts.append(text)
            if parts:
                return " ".join(parts).strip()

    for key in ("prompt", "prompt_text", "user_prompt", "userPrompt", "text"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def _extract_tool_name(payload: dict[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("toolName") or "").strip()


def _extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    return tool_input if isinstance(tool_input, dict) else {}


def _extract_read_path(tool_input: dict[str, Any]) -> str:
    for key in ("file_path", "path"):
        value = str(tool_input.get(key) or "").strip()
        if value:
            return value
    return ""


def _extract_commit_message(command: str) -> str:
    if not re.search(r"(^|\s)git(\.exe)?\s+commit(\s|$)", command):
        return ""
    patterns = (
        r'-m\s+"([^"]+)"',
        r"-m\s+'([^']+)'",
    )
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1).strip()
    return ""


def _statusline_context(project_root: Path) -> str:
    context = _infer_active_context(project_root)
    if not context:
        return ""
    args = ["render-statusline", "--command", context["command_name"]]
    if "feature_dir" in context:
        args.extend(["--feature-dir", context["feature_dir"]])
    if "workspace" in context:
        args.extend(["--workspace", context["workspace"]])
    shared = _run_shared_hook(project_root, args)
    if not shared:
        return ""
    return str(shared.get("data", {}).get("statusline") or "").strip()


def _learning_signal_context(project_root: Path) -> str:
    context = _infer_active_context(project_root)
    if not context:
        return ""
    state_file = context.get("state_file", "")
    if not state_file:
        return ""
    text = _read_text(Path(state_file))
    if not text:
        return ""
    args = ["signal-learning", "--command", context["command_name"]]
    has_signal = False
    for field_name, option_name in LEARNING_SIGNAL_FIELDS.items():
        value = _extract_int_field(text, field_name)
        if value <= 0:
            continue
        args.extend([option_name, str(value)])
        has_signal = True

    false_starts = _dedupe(
        [
            *_extract_list_field(text, "false_start"),
            *_extract_list_field(text, "false_starts"),
            *_extract_section_items(text, "False Starts"),
            *_extract_section_items(text, "False Leads"),
        ]
    )
    for item in false_starts:
        args.extend(["--false-start", item])
        has_signal = True

    hidden_dependencies = _dedupe(
        [
            *_extract_list_field(text, "hidden_dependency"),
            *_extract_list_field(text, "hidden_dependencies"),
            *_extract_section_items(text, "Hidden Dependencies"),
            *_extract_section_items(text, "Hidden Dependency"),
        ]
    )
    for item in hidden_dependencies:
        args.extend(["--hidden-dependency", item])
        has_signal = True

    if not has_signal:
        return ""
    shared = _run_shared_hook(project_root, args)
    return _shared_additional_context(shared)


def _handle_session_start(project_root: Path, _payload: dict[str, Any]) -> dict[str, Any]:
    statusline = _statusline_context(project_root)
    return {"systemMessage": statusline} if statusline else {}


def _handle_before_agent(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    prompt = _extract_prompt_text(payload)
    statusline = _statusline_context(project_root)
    learning_signal = _learning_signal_context(project_root)
    advisory = " ".join([statusline, learning_signal]).strip()

    if prompt:
        shared = _run_shared_hook(project_root, ["validate-prompt", "--prompt-text", prompt])
        blocked = _shared_block_to_gemini(shared, system_message=advisory)
        if blocked:
            return blocked

    if advisory:
        return {
            "hookSpecificOutput": {
                "hookEventName": "BeforeAgent",
                "additionalContext": advisory,
            }
        }
    return {}


def _handle_before_tool(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    tool_name = _extract_tool_name(payload).lower()
    tool_input = _extract_tool_input(payload)

    if tool_name in {"read_file", "read", "read-file"}:
        target_path = _extract_read_path(tool_input)
        if not target_path:
            return {}
        shared = _run_shared_hook(project_root, ["validate-read-path", "--target-path", target_path])
        return _shared_block_to_gemini(shared) or {}

    if tool_name in {"run_shell_command", "bash", "run-shell-command"}:
        command = str(tool_input.get("command") or "").strip()
        if not command:
            return {}
        commit_message = _extract_commit_message(command)
        if not commit_message:
            return {}
        shared = _run_shared_hook(project_root, ["validate-commit", "--commit-message", commit_message])
        return _shared_block_to_gemini(shared) or {}

    return {}


def main() -> int:
    route = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = _read_stdin_payload()
    project_root = _project_root(payload)

    handlers = {
        "session-start": _handle_session_start,
        "before-agent": _handle_before_agent,
        "before-tool": _handle_before_tool,
    }
    handler = handlers.get(route)
    if not handler:
        return 0

    output = handler(project_root, payload)
    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
