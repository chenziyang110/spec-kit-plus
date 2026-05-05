#!/usr/bin/env python3
"""Thin Claude Code native hook adapter for spec-kit-plus.

This script is installed into ``.claude/hooks/`` for project-local Claude
integrations. It translates Claude hook payloads into the shared
``specify hook ...`` command surface so workflow truth stays in the canonical
Python hook engine instead of being duplicated inside standalone scripts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


WORKFLOW_COMMAND_MAP = {
    "sp-specify": "specify",
    "sp-clarify": "clarify",
    "sp-deep-research": "deep-research",
    "sp-plan": "plan",
    "sp-tasks": "tasks",
    "sp-analyze": "analyze",
    "sp-test-scan": "test-scan",
    "sp-test-build": "test-build",
    "sp-implement": "implement",
    "sp-debug": "debug",
    "sp-quick": "quick",
    "sp-fast": "fast",
    "sp-map-scan": "map-scan",
    "sp-map-build": "map-build",
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
    env_root = str(os.environ.get("CLAUDE_PROJECT_DIR") or "").strip()
    if env_root:
        return Path(env_root).resolve()

    raw_cwd = str(payload.get("cwd") or "").strip()
    if raw_cwd:
        return Path(raw_cwd).resolve()

    return Path(__file__).resolve().parents[2]


def _argv_from_env(name: str) -> tuple[str, ...] | None:
    raw_json = os.environ.get(f"{name}_ARGV", "").strip()
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list) and parsed and all(isinstance(item, str) and item for item in parsed):
            return tuple(parsed)

    raw_command = os.environ.get(f"{name}_COMMAND", "").strip()
    if raw_command:
        try:
            parsed_command = shlex.split(raw_command, posix=os.name != "nt")
        except ValueError:
            parsed_command = []
        if parsed_command:
            return tuple(parsed_command)

    return None


def _argv_from_project_config(project_root: Path) -> tuple[str, ...] | None:
    config_path = project_root / ".specify" / "config.json"
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(loaded, dict):
        return None

    launcher = loaded.get("specify_launcher") or loaded.get("hook_launcher")
    if not isinstance(launcher, dict):
        return None
    argv = launcher.get("argv")
    if isinstance(argv, list) and argv and all(isinstance(item, str) and item for item in argv):
        return tuple(argv)
    return None


def _project_launcher_broken(project_root: Path) -> bool:
    launcher_argv = _argv_from_project_config(project_root)
    if not launcher_argv:
        return False
    first = launcher_argv[0]
    return shutil.which(first) is None and not Path(first).exists()


def _shared_hook_commands(project_root: Path, args: list[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    for launcher_argv in (
        _argv_from_env("SPECIFY_HOOK"),
        _argv_from_project_config(project_root),
    ):
        if launcher_argv:
            commands.append([*launcher_argv, "hook", *args])

    commands.append([sys.executable, "-m", "specify_cli", "hook", *args])
    if shutil.which("specify"):
        commands.append(["specify", "hook", *args])
    if shutil.which("py"):
        commands.append(["py", "-m", "specify_cli", "hook", *args])
    return commands


def _run_shared_hook(project_root: Path, args: list[str]) -> dict[str, Any] | None:
    if _project_launcher_broken(project_root):
        return {
            "status": "blocked",
            "errors": ["project launcher is configured but unavailable"],
            "warnings": [],
            "actions": [
                "repair `.specify/config.json`. If regeneration is required, use the `specify init --here --force` command surface from a trusted launcher source and supply the same integration-specific options that originally bootstrapped the project",
            ],
        }

    seen: set[tuple[str, ...]] = set()
    for command in _shared_hook_commands(project_root, args):
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


def _shared_to_claude_output(
    *,
    hook_event_name: str,
    shared_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not shared_payload:
        return None

    status = str(shared_payload.get("status") or "").strip().lower()
    errors = [str(item) for item in shared_payload.get("errors", []) if str(item).strip()]
    warnings = [str(item) for item in shared_payload.get("warnings", []) if str(item).strip()]
    actions = [str(item) for item in shared_payload.get("actions", []) if str(item).strip()]
    system_message = str(shared_payload.get("systemMessage") or shared_payload.get("system_message") or "").strip()
    advisory = " ".join([*warnings, *actions]).strip()

    if status in {"blocked", "repairable-block"}:
        reason = errors[0] if errors else (warnings[0] if warnings else "shared quality hook blocked the action")
        if hook_event_name == "PreToolUse":
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        if hook_event_name == "UserPromptSubmit":
            output = {"decision": "block", "reason": reason}
            if system_message:
                output["systemMessage"] = system_message
                return output
            if advisory and advisory != reason:
                output["systemMessage"] = advisory
            return output
        if hook_event_name == "PostToolUse":
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "additionalContext": " ".join([reason, advisory]).strip(),
                }
            }
        return {"decision": "block", "reason": reason}

    if status == "warn" and system_message and hook_event_name == "UserPromptSubmit":
        return {"systemMessage": system_message}

    if status == "warn" and advisory:
        if hook_event_name == "PreToolUse":
            return {"systemMessage": advisory}
        return {
            "hookSpecificOutput": {
                "hookEventName": hook_event_name,
                "additionalContext": advisory,
            }
        }

    return None


def _format_recovery_summary(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    phase_mode = str(summary.get("phase_mode") or "").strip()
    next_action = str(summary.get("next_action") or "").strip()
    next_command = str(summary.get("next_command") or "").strip()
    route_reason = str(summary.get("route_reason") or "").strip()
    if phase_mode:
        parts.append(f"Phase: {phase_mode}.")
    if next_action:
        parts.append(f"Next action: {next_action}.")
    if next_command:
        parts.append(f"Next command: {next_command}.")
    if route_reason:
        parts.append(f"Reason: {route_reason}.")
    return " ".join(parts)


def _artifact_resume_cue(artifact: dict[str, Any]) -> str:
    phase_state = artifact.get("phase_state", {})
    if not isinstance(phase_state, dict):
        phase_state = {}
    next_action = str(phase_state.get("next_action") or "").strip()
    if next_action:
        return f"Resume cue: {next_action}."
    resume_cue = artifact.get("resume_cue", [])
    if isinstance(resume_cue, list):
        for item in resume_cue:
            text = str(item or "").strip()
            if text:
                return text
    return ""


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
    candidates = (
        payload.get("prompt"),
        payload.get("prompt_text"),
        payload.get("user_prompt"),
        payload.get("text"),
    )
    for candidate in candidates:
        value = str(candidate or "").strip()
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


def _learning_signal_args(context: dict[str, str]) -> list[str] | None:
    state_file = context.get("state_file")
    if not state_file:
        return None
    text = _read_text(Path(state_file))
    if not text:
        return None

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

    return args if has_signal else None


def _learning_signal_context(project_root: Path, context: dict[str, str], hook_event_name: str) -> str:
    args = _learning_signal_args(context)
    if not args:
        return ""
    shared = _run_shared_hook(project_root, args)
    output = _shared_to_claude_output(hook_event_name=hook_event_name, shared_payload=shared)
    if not output:
        return ""
    return str(output.get("hookSpecificOutput", {}).get("additionalContext") or "").strip()


def _active_context_args(context: dict[str, str], *, include_command: bool = True) -> list[str]:
    args: list[str] = []
    if include_command:
        args.extend(["--command", context["command_name"]])
    if "feature_dir" in context:
        args.extend(["--feature-dir", context["feature_dir"]])
    if "workspace" in context:
        args.extend(["--workspace", context["workspace"]])
    if "session_file" in context:
        args.extend(["--session-file", context["session_file"]])
    return args


def _workflow_policy_output(
    project_root: Path,
    context: dict[str, str] | None,
    *,
    hook_event_name: str,
    trigger: str,
    requested_action: str = "",
) -> dict[str, Any] | None:
    if not context:
        return None
    args = ["workflow-policy", *_active_context_args(context), "--trigger", trigger]
    if requested_action:
        args.extend(["--requested-action", requested_action])
    shared = _run_shared_hook(project_root, args)
    return _shared_to_claude_output(hook_event_name=hook_event_name, shared_payload=shared)


def _compaction_resume_context(
    project_root: Path,
    context: dict[str, str] | None,
    *,
    build: bool,
    read_first: bool,
    trigger: str,
    prefer_summary: bool,
) -> str:
    if not context:
        return ""
    shared = None
    artifact: dict[str, Any] | Any = {}

    if read_first or not build:
        shared = _run_shared_hook(project_root, ["read-compaction", *_active_context_args(context)])
        artifact = shared.get("data", {}).get("artifact", {}) if shared else {}

    if build and (not shared or not isinstance(artifact, dict) or not artifact):
        args = ["build-compaction", *_active_context_args(context), "--trigger", trigger]
        shared = _run_shared_hook(project_root, args)
        artifact = shared.get("data", {}).get("artifact", {}) if shared else {}

    if not shared:
        return ""
    if not isinstance(artifact, dict) or not artifact:
        return ""
    if prefer_summary:
        recovery_summary = artifact.get("recovery_summary", {})
        if isinstance(recovery_summary, dict):
            formatted = _format_recovery_summary(recovery_summary)
            if formatted:
                return formatted
    return _artifact_resume_cue(artifact)


def _stop_system_message(message: str) -> dict[str, Any] | None:
    message = message.strip()
    if not message:
        return None
    return {"systemMessage": message}


def _handle_user_prompt_submit(project_root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    prompt = _extract_prompt_text(payload)
    if not prompt:
        return None
    context = _infer_active_context(project_root)
    shared = _run_shared_hook(project_root, ["validate-prompt", "--prompt-text", prompt])
    output = _shared_to_claude_output(hook_event_name="UserPromptSubmit", shared_payload=shared)
    if output:
        return output
    policy_output = _workflow_policy_output(
        project_root,
        context,
        hook_event_name="UserPromptSubmit",
        trigger="prompt",
    )
    if policy_output:
        return policy_output
    return None


def _handle_pre_tool_read(project_root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if _extract_tool_name(payload) != "Read":
        return None
    context = _infer_active_context(project_root)
    policy_output = _workflow_policy_output(
        project_root,
        context,
        hook_event_name="PreToolUse",
        trigger="pre_tool",
    )
    if policy_output and "hookSpecificOutput" in policy_output:
        hook_specific = policy_output.get("hookSpecificOutput", {})
        if isinstance(hook_specific, dict) and hook_specific.get("permissionDecision") == "deny":
            return policy_output
    target_path = _extract_read_path(_extract_tool_input(payload))
    if not target_path:
        return policy_output
    shared = _run_shared_hook(project_root, ["validate-read-path", "--target-path", target_path])
    output = _shared_to_claude_output(hook_event_name="PreToolUse", shared_payload=shared)
    return output or policy_output


def _handle_pre_tool_bash(project_root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if _extract_tool_name(payload) != "Bash":
        return None
    context = _infer_active_context(project_root)
    policy_output = _workflow_policy_output(
        project_root,
        context,
        hook_event_name="PreToolUse",
        trigger="pre_tool",
    )
    if policy_output and "hookSpecificOutput" in policy_output:
        hook_specific = policy_output.get("hookSpecificOutput", {})
        if isinstance(hook_specific, dict) and hook_specific.get("permissionDecision") == "deny":
            return policy_output
    command = str(_extract_tool_input(payload).get("command") or "").strip()
    if not command:
        return policy_output
    commit_message = _extract_commit_message(command)
    if not commit_message:
        return policy_output
    shared = _run_shared_hook(project_root, ["validate-commit", "--commit-message", commit_message])
    output = _shared_to_claude_output(hook_event_name="PreToolUse", shared_payload=shared)
    return output or policy_output


def _handle_session_start(project_root: Path, _payload: dict[str, Any]) -> dict[str, Any] | None:
    context = _infer_active_context(project_root)
    if not context:
        return None

    args = ["render-statusline", "--command", context["command_name"]]
    if "feature_dir" in context:
        args.extend(["--feature-dir", context["feature_dir"]])
    if "workspace" in context:
        args.extend(["--workspace", context["workspace"]])
    if "session_file" in context:
        args.extend(["--session-file", context["session_file"]])

    shared = _run_shared_hook(project_root, args)
    if not shared:
        return None
    statusline = str(shared.get("data", {}).get("statusline") or "").strip()
    resume_context = _compaction_resume_context(
        project_root,
        context,
        build=True,
        read_first=True,
        trigger="session_start",
        prefer_summary=True,
    )
    additional_context = " ".join(part for part in [statusline, resume_context] if part).strip()
    if not additional_context:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }


def _handle_post_tool_session_state(project_root: Path, _payload: dict[str, Any]) -> dict[str, Any] | None:
    context = _infer_active_context(project_root)
    if not context:
        return None
    advisory_parts: list[str] = []
    if context["command_name"] not in {"implement", "quick", "debug"}:
        signal_context = _learning_signal_context(project_root, context, "PostToolUse")
        if signal_context:
            advisory_parts.append(signal_context)
        if not advisory_parts:
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": " ".join(advisory_parts),
            }
        }

    args = ["validate-session-state", "--command", context["command_name"]]
    if "feature_dir" in context:
        args.extend(["--feature-dir", context["feature_dir"]])
    if "workspace" in context:
        args.extend(["--workspace", context["workspace"]])
    if "session_file" in context:
        args.extend(["--session-file", context["session_file"]])

    shared = _run_shared_hook(project_root, args)
    shared_output = _shared_to_claude_output(hook_event_name="PostToolUse", shared_payload=shared)
    if shared_output:
        # PostToolUse should stay advisory; never emit a permission decision here.
        hook_specific = shared_output.get("hookSpecificOutput", {})
        hook_specific.pop("permissionDecision", None)
        hook_specific.pop("permissionDecisionReason", None)
        additional_context = str(hook_specific.get("additionalContext") or "").strip()
        if additional_context:
            advisory_parts.append(additional_context)

    signal_context = _learning_signal_context(project_root, context, "PostToolUse")
    if signal_context:
        advisory_parts.append(signal_context)
    compaction_context = _compaction_resume_context(
        project_root,
        context,
        build=True,
        read_first=False,
        trigger="post_tool",
        prefer_summary=False,
    )
    if compaction_context:
        advisory_parts.append(compaction_context)
    if advisory_parts:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": " ".join(advisory_parts),
            }
        }
    return None


def _handle_stop_monitor(project_root: Path, _payload: dict[str, Any]) -> dict[str, Any] | None:
    context = _infer_active_context(project_root)
    if not context:
        return None

    args = ["monitor-context", "--command", context["command_name"], "--trigger", "before_stop"]
    if "feature_dir" in context:
        args.extend(["--feature-dir", context["feature_dir"]])
    if "workspace" in context:
        args.extend(["--workspace", context["workspace"]])
    if "session_file" in context:
        args.extend(["--session-file", context["session_file"]])

    shared = _run_shared_hook(project_root, args)
    if not shared:
        return None

    status = str(shared.get("status") or "").strip().lower()
    errors = [str(item) for item in shared.get("errors", []) if str(item).strip()]
    warnings = [str(item) for item in shared.get("warnings", []) if str(item).strip()]
    actions = [str(item) for item in shared.get("actions", []) if str(item).strip()]

    if status == "blocked":
        output = {
            "decision": "block",
            "reason": errors[0] if errors else "shared context monitor blocked stop until resume state is repaired",
        }
        extra = " ".join([*warnings, *actions]).strip()
        if extra:
            output["systemMessage"] = extra
        return output

    if status == "warn":
        extra = " ".join([*warnings, *actions]).strip()
        compaction_context = _compaction_resume_context(
            project_root,
            context,
            build=True,
            read_first=False,
            trigger="before_stop",
            prefer_summary=False,
        )
        if compaction_context:
            extra = f"{extra} {compaction_context}".strip()
        else:
            checkpoint = shared.get("data", {}).get("checkpoint", {})
            if isinstance(checkpoint, dict):
                next_action = str(checkpoint.get("next_action") or "").strip()
                if next_action:
                    extra = f"{extra} Resume cue: {next_action}.".strip()
        signal_context = _learning_signal_context(project_root, context, "Stop")
        if signal_context:
            extra = f"{extra} {signal_context}".strip()
        if extra:
            return _stop_system_message(extra)

    compaction_context = _compaction_resume_context(
        project_root,
        context,
        build=True,
        read_first=False,
        trigger="before_stop",
        prefer_summary=False,
    )
    if compaction_context:
        return _stop_system_message(compaction_context)
    signal_context = _learning_signal_context(project_root, context, "Stop")
    if signal_context:
        return _stop_system_message(signal_context)

    return None


def main() -> int:
    route = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = _read_stdin_payload()
    project_root = _project_root(payload)

    handlers = {
        "session-start": _handle_session_start,
        "user-prompt-submit": _handle_user_prompt_submit,
        "post-tool-session-state": _handle_post_tool_session_state,
        "stop-monitor": _handle_stop_monitor,
        "pre-tool-read": _handle_pre_tool_read,
        "pre-tool-bash": _handle_pre_tool_bash,
    }
    handler = handlers.get(route)
    if not handler:
        return 0

    output = handler(project_root, payload)
    if output:
        sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
