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
import time
from pathlib import Path
from typing import Any, Literal, NamedTuple


WORKFLOW_COMMAND_MAP = {
    "sp-specify": "specify",
    "sp-clarify": "clarify",
    "sp-deep-research": "deep-research",
    "sp-plan": "plan",
    "sp-tasks": "tasks",
    "sp-analyze": "analyze",
    "sp-implement": "implement",
    "sp-accept": "accept",
    "sp-debug": "debug",
    "sp-quick": "quick",
    "sp-fast": "fast",
    "sp-map-scan": "map-scan",
    "sp-map-build": "map-build",
    "sp-map-update": "map-update",
    "sp-constitution": "constitution",
    "sp-checklist": "checklist",
}
ACTIVE_STATE_STATUSES = {
    "active",
    "started",
    "starting",
    "in_progress",
    "executing",
    "execution",
}
TERMINAL_STATE_STATUSES = {
    "resolved",
    "complete",
    "completed",
    "done",
    "cancelled",
    "closed",
    "failed",
}
TERMINAL_STATE_PREFIXES = ("complete_with_", "completed_with_")
OPTIONAL_NEXT_ACTION_PREFIXES = (
    "optional follow-up",
    "optional followup",
    "optional:",
    "manual review if needed",
    "manual review if required",
)
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
SHARED_HOOK_TIMEOUT_SECONDS = 5.0
SHARED_HOOK_PAYLOAD_STATUSES = {"ok", "warn", "blocked", "repaired", "repairable-block"}
SHARED_HOOK_BLOCKING_PAYLOAD_STATUSES = {"blocked", "repairable-block"}
SharedHookClientStatus = Literal[
    "ok", "blocked", "unavailable", "timeout", "invalid-output"
]


class SharedHookResult(NamedTuple):
    status: SharedHookClientStatus
    payload: dict[str, Any] | None = None
    reason: str = ""
    attempted_plans: tuple[str, ...] = ()
    attempted_plan: str = ""
    stdout_preview: str = ""
    timeout_seconds: float | None = None


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
        if (
            isinstance(parsed, list)
            and parsed
            and all(isinstance(item, str) and item for item in parsed)
        ):
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
    if (
        isinstance(argv, list)
        and argv
        and all(isinstance(item, str) and item for item in argv)
    ):
        return tuple(argv)
    return None


def _project_launcher_broken(project_root: Path) -> bool:
    launcher_argv = _argv_from_project_config(project_root)
    if not launcher_argv:
        return False
    first = launcher_argv[0]
    return shutil.which(first) is None and not Path(first).exists()


def _source_tree_cli_command() -> list[str] | None:
    for parent in Path(__file__).resolve().parents:
        src_root = parent
        if (src_root / "specify_cli" / "__init__.py").exists():
            code = f"import sys; sys.path.insert(0, {str(src_root)!r}); from specify_cli import main; main()"
            return [sys.executable, "-c", code]
    return None


def _shared_hook_commands(project_root: Path, args: list[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    for launcher_argv in (
        _argv_from_env("SPECIFY_HOOK"),
        _argv_from_project_config(project_root),
    ):
        if launcher_argv:
            commands.append([*launcher_argv, "hook", *args])

    source_command = _source_tree_cli_command()
    if source_command:
        commands.append([*source_command, "hook", *args])
    commands.append([sys.executable, "-m", "specify_cli", "hook", *args])
    if shutil.which("specify"):
        commands.append(["specify", "hook", *args])
    if shutil.which("py"):
        commands.append(["py", "-m", "specify_cli", "hook", *args])
    return commands


def _project_launcher_block_payload() -> dict[str, Any]:
    return {
        "status": "blocked",
        "errors": ["project launcher is configured but unavailable"],
        "warnings": [],
        "actions": [
            "repair `.specify/config.json`. If regeneration is required, use the `specify init --here --force` command surface from a trusted launcher source and supply the same integration-specific options that originally bootstrapped the project",
        ],
    }


def _redacted_invocation_preview(command: list[str]) -> str:
    redacted: list[str] = []
    index = 0
    while index < len(command):
        item = str(command[index])
        if item == "--prompt-text":
            redacted.append(item)
            if index + 1 < len(command):
                redacted.append("[REDACTED_PROMPT]")
                index += 2
                continue
        elif item.startswith("--prompt-text="):
            redacted.append("--prompt-text=[REDACTED_PROMPT]")
            index += 1
            continue
        redacted.append(item)
        index += 1
    return " ".join(redacted)


def _sensitive_hook_values(args: list[str], stdin_text: str | None) -> list[str]:
    values: list[str] = []
    if stdin_text:
        values.append(stdin_text)
    index = 0
    while index < len(args):
        item = str(args[index])
        if item == "--prompt-text" and index + 1 < len(args):
            values.append(str(args[index + 1]))
            index += 2
            continue
        if item.startswith("--prompt-text="):
            values.append(item.split("=", 1)[1])
        index += 1
    return [value for value in values if value]


def _redact_sensitive_text(text: str, sensitive_values: list[str]) -> str:
    redacted = text
    for value in sorted(set(sensitive_values), key=len, reverse=True):
        if value:
            redacted = redacted.replace(value, "[REDACTED_PROMPT]")
    return redacted


def _stdout_preview(stdout: str, sensitive_values: list[str]) -> str:
    preview = stdout.strip().replace("\r\n", "\n")
    if len(preview) > 500:
        preview = f"{preview[:500]}..."
    return _redact_sensitive_text(preview, sensitive_values)


def _shared_result_status(payload: dict[str, Any]) -> SharedHookClientStatus | None:
    status = str(payload.get("status") or "").strip().lower()
    if status not in SHARED_HOOK_PAYLOAD_STATUSES:
        return None
    if status in SHARED_HOOK_BLOCKING_PAYLOAD_STATUSES:
        return "blocked"
    return "ok"


def _invoke_shared_hook(
    project_root: Path,
    args: list[str],
    *,
    stdin_text: str | None = None,
    timeout_seconds: float = SHARED_HOOK_TIMEOUT_SECONDS,
) -> SharedHookResult:
    if _project_launcher_broken(project_root):
        return SharedHookResult(
            status="blocked",
            payload=_project_launcher_block_payload(),
            reason="project launcher is configured but unavailable",
        )

    seen: set[tuple[str, ...]] = set()
    attempted_plans: list[str] = []
    invalid_result: SharedHookResult | None = None
    sensitive_values = _sensitive_hook_values(args, stdin_text)
    deadline = time.monotonic() + timeout_seconds
    for command in _shared_hook_commands(project_root, args):
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        attempted_plan = _redacted_invocation_preview(command)
        attempted_plans.append(attempted_plan)
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            return SharedHookResult(
                status="timeout",
                reason="shared hook event deadline was exhausted",
                attempted_plans=tuple(attempted_plans),
                attempted_plan=attempted_plan,
                timeout_seconds=timeout_seconds,
            )
        try:
            result = subprocess.run(
                command,
                cwd=project_root,
                input=stdin_text,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
                timeout=remaining_seconds,
            )
        except subprocess.TimeoutExpired:
            return SharedHookResult(
                status="timeout",
                reason="shared hook invocation timed out",
                attempted_plans=tuple(attempted_plans),
                attempted_plan=attempted_plan,
                timeout_seconds=timeout_seconds,
            )
        except OSError:
            continue
        # Shared hooks use 10 for a valid, resumable business blocker. Their
        # JSON payload is still authoritative and must reach the native hook.
        if result.returncode not in {0, 10}:
            continue
        stdout = (result.stdout or "").strip()
        if not stdout:
            continue
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            if invalid_result is None:
                invalid_result = SharedHookResult(
                    status="invalid-output",
                    reason="shared hook returned invalid JSON",
                    attempted_plans=tuple(attempted_plans),
                    attempted_plan=attempted_plan,
                    stdout_preview=_stdout_preview(stdout, sensitive_values),
                )
            continue
        if not isinstance(payload, dict):
            if invalid_result is None:
                invalid_result = SharedHookResult(
                    status="invalid-output",
                    reason="shared hook returned a non-object JSON payload",
                    attempted_plans=tuple(attempted_plans),
                    attempted_plan=attempted_plan,
                    stdout_preview=_stdout_preview(stdout, sensitive_values),
                )
            continue
        result_status = _shared_result_status(payload)
        if not result_status:
            if invalid_result is None:
                invalid_result = SharedHookResult(
                    status="invalid-output",
                    reason="shared hook returned an unknown status",
                    attempted_plans=tuple(attempted_plans),
                    attempted_plan=attempted_plan,
                    stdout_preview=_stdout_preview(stdout, sensitive_values),
                )
            continue
        if result.returncode == 10 and result_status != "blocked":
            if invalid_result is None:
                invalid_result = SharedHookResult(
                    status="invalid-output",
                    reason="shared hook exit 10 requires a blocking payload status",
                    attempted_plans=tuple(attempted_plans),
                    attempted_plan=attempted_plan,
                    stdout_preview=_stdout_preview(stdout, sensitive_values),
                )
            continue
        return SharedHookResult(
            status=result_status,
            payload=payload,
            attempted_plans=tuple(attempted_plans),
            attempted_plan=attempted_plan,
        )
    if invalid_result:
        return invalid_result._replace(attempted_plans=tuple(attempted_plans))
    return SharedHookResult(
        status="unavailable",
        reason="no shared hook invocation plan produced valid JSON output",
        attempted_plans=tuple(attempted_plans),
    )


def _run_shared_hook(
    project_root: Path,
    args: list[str],
    *,
    stdin_text: str | None = None,
    timeout_seconds: float = SHARED_HOOK_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    result = _invoke_shared_hook(
        project_root,
        args,
        stdin_text=stdin_text,
        timeout_seconds=timeout_seconds,
    )
    if result.status in {"ok", "blocked"}:
        return result.payload
    return None


def _shared_blocker_detail(shared_payload: dict[str, Any]) -> str:
    blockers = shared_payload.get("blockers")
    if (
        not isinstance(blockers, list)
        or not blockers
        or not isinstance(blockers[0], dict)
    ):
        return ""
    blocker = blockers[0]
    evidence = blocker.get("evidence")
    if isinstance(evidence, list):
        evidence_text = "; ".join(str(item) for item in evidence if str(item).strip())
    else:
        evidence_text = str(evidence or "").strip()
    resume = blocker.get("resume")
    resume_text = ""
    if isinstance(resume, dict):
        resume_text = str(
            resume.get("command") or resume.get("instruction") or ""
        ).strip()
    attempted = blocker.get("attempted_recovery")
    attempted_text = "none recorded"
    if isinstance(attempted, list) and attempted:
        attempted_text = (
            "; ".join(
                f"{item.get('action')} -> {item.get('result')}"
                for item in attempted
                if isinstance(item, dict)
            )
            or "none recorded"
        )
    affected = blocker.get("affected_scope")
    affected_text = (
        "; ".join(str(item) for item in affected if str(item).strip())
        if isinstance(affected, list)
        else str(affected or "").strip()
    )
    parts = [
        f"Workflow/stage: {blocker.get('workflow')} / {blocker.get('stage')}",
        f"Blocked: {blocker.get('summary')}",
        f"Category/owner: {blocker.get('category')} / {blocker.get('owner')}",
        f"Why: {blocker.get('details')}",
        f"Evidence: {evidence_text}" if evidence_text else "",
        f"Attempted recovery: {attempted_text}",
        f"Affected scope: {affected_text}" if affected_text else "",
        f"Next action: {blocker.get('exact_next_action')}",
        f"Unblock criteria: {blocker.get('unblock_criteria')}",
        f"Resume: {resume_text}" if resume_text else "",
    ]
    guide = blocker.get("human_action_guide")
    if blocker.get("human_action_required") is True and isinstance(guide, dict):
        step_text = "; ".join(
            f"{step.get('order')}. {step.get('title')}: {step.get('action')} "
            f"[expected: {step.get('expected_result')}; if failed: {step.get('if_failed')}]"
            for step in guide.get("steps") or []
            if isinstance(step, dict)
        )
        parts.extend(
            [
                f"Human goal: {guide.get('goal')}",
                f"Why human: {guide.get('why_human')}",
                f"Prerequisites: {'; '.join(str(item) for item in guide.get('prerequisites') or [])}",
                f"Safety: {'; '.join(str(item) for item in guide.get('safety_notes') or [])}",
                f"Steps: {step_text}" if step_text else "",
                f"Return: {'; '.join(str(item) for item in guide.get('evidence_to_return') or [])}",
                f"Human resume: {guide.get('resume_instruction')}",
            ]
        )
    return " | ".join(part for part in parts if part and not part.endswith(": None"))


def _shared_to_claude_output(
    *,
    hook_event_name: str,
    shared_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not shared_payload:
        return None

    status = str(shared_payload.get("status") or "").strip().lower()
    errors = [
        str(item) for item in shared_payload.get("errors", []) if str(item).strip()
    ]
    warnings = [
        str(item) for item in shared_payload.get("warnings", []) if str(item).strip()
    ]
    actions = [
        str(item) for item in shared_payload.get("actions", []) if str(item).strip()
    ]
    system_message = str(
        shared_payload.get("systemMessage")
        or shared_payload.get("system_message")
        or ""
    ).strip()
    advisory = " ".join([*warnings, *actions]).strip()
    autofix_command = str(
        ((shared_payload.get("data") or {}).get("autofix") or {}).get("command") or ""
    ).strip()
    blocker_detail = _shared_blocker_detail(shared_payload)

    if status == "repairable-block":
        reason = (
            errors[0]
            if errors
            else (
                warnings[0]
                if warnings
                else "shared quality hook requires repair before continuing"
            )
        )
        if hook_event_name == "UserPromptSubmit":
            output: dict[str, Any] = {}
            message = " ".join(
                part
                for part in [
                    system_message,
                    blocker_detail,
                    advisory,
                    autofix_command,
                    reason,
                ]
                if part
            ).strip()
            if message:
                output["systemMessage"] = message
            return output or None
        if hook_event_name == "PreToolUse":
            return None
        return None

    if status == "blocked":
        reason = (
            errors[0]
            if errors
            else (warnings[0] if warnings else "shared quality hook blocked the action")
        )
        detailed_reason = blocker_detail or reason
        if hook_event_name == "PreToolUse":
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": detailed_reason,
                }
            }
        if hook_event_name == "UserPromptSubmit":
            output = {"decision": "block", "reason": detailed_reason}
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
                    "additionalContext": " ".join([detailed_reason, advisory]).strip(),
                }
            }
        return {"decision": "block", "reason": detailed_reason}

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
    if next_action and not _is_optional_next_action(next_action):
        parts.append(f"Next action: {next_action}.")
    if next_command:
        parts.append(f"Next command: {next_command}.")
    if route_reason:
        parts.append(f"Reason: {route_reason}.")
    return " ".join(parts)


def _normalized_state(value: str) -> str:
    return re.sub(r"[\s-]+", "_", str(value or "").strip().lower())


def _is_terminal_state_status(value: str) -> bool:
    normalized = _normalized_state(value)
    return normalized in TERMINAL_STATE_STATUSES or normalized.startswith(
        TERMINAL_STATE_PREFIXES
    )


def _is_active_state_status(value: str) -> bool:
    return _normalized_state(value) in ACTIVE_STATE_STATUSES


def _is_optional_next_action(value: str) -> bool:
    normalized = " ".join(str(value or "").strip().lower().split()).rstrip(".")
    return normalized in {"", "none", "n/a", "no-op", "noop"} or normalized.startswith(
        OPTIONAL_NEXT_ACTION_PREFIXES
    )


def _artifact_resume_cue(artifact: dict[str, Any]) -> str:
    phase_state = artifact.get("phase_state", {})
    if not isinstance(phase_state, dict):
        phase_state = {}
    next_action = str(phase_state.get("next_action") or "").strip()
    if next_action and not _is_optional_next_action(next_action):
        return f"Resume cue: {next_action}."
    resume_cue = artifact.get("resume_cue", [])
    if isinstance(resume_cue, list):
        for item in resume_cue:
            text = str(item or "").strip()
            if text and not _is_optional_next_action(
                text.removeprefix("Resume cue:").strip()
            ):
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
    value = _extract_field(text, field_name) or _extract_frontmatter_field(
        text, field_name
    )
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
    heading = re.compile(
        rf"^##+\s+{re.escape(section_name)}\s*$", re.IGNORECASE | re.MULTILINE
    )
    match = heading.search(text)
    if not match:
        return []
    next_heading = re.search(r"^##+\s+", text[match.end() :], re.MULTILINE)
    section = (
        text[match.end() : match.end() + next_heading.start()]
        if next_heading
        else text[match.end() :]
    )
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


def _feature_root_candidates(project_root: Path) -> list[Path]:
    return [
        project_root / ".specify" / "features",
        project_root / "specs",
        project_root / ".specify" / "specs",
    ]


def _infer_active_context(project_root: Path) -> dict[str, str] | None:
    implement_candidates: list[tuple[float, dict[str, str]]] = []
    for root in _feature_root_candidates(project_root):
        if not root.is_dir():
            continue
        for tracker_path in root.glob("*/implement-tracker.md"):
            text = _read_text(tracker_path)
            if not text:
                continue
            status = _extract_frontmatter_field(text, "status").lower()
            if not status or _is_terminal_state_status(status):
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
        if not status or _is_terminal_state_status(status):
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
    for root in _feature_root_candidates(project_root):
        if not root.is_dir():
            continue
        for workflow_path in root.glob("*/workflow-state.md"):
            text = _read_text(workflow_path)
            if not text:
                continue
            active_command = _extract_field(text, "active_command").lower()
            status = _extract_field(text, "status").lower()
            mapped = WORKFLOW_COMMAND_MAP.get(active_command)
            if not mapped or (status and not _is_active_state_status(status)):
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


def _extract_write_path(tool_input: dict[str, Any]) -> str:
    for key in ("file_path", "path"):
        value = str(tool_input.get(key) or "").strip()
        if value:
            return value
    return ""


def _extract_commit_message(command: str) -> str:
    if not re.search(r"(^|\s)git(\.exe)?(?:\s+-c\s+\S+)*\s+commit(\s|$)", command):
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


def _is_repairable_block(shared_payload: dict[str, Any] | None) -> bool:
    return (
        str((shared_payload or {}).get("status") or "").strip().lower()
        == "repairable-block"
    )


def _normalized_path_for_compare(project_root: Path, raw_path: str) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return str(path.resolve()).replace("\\", "/").lower()


def _is_state_repair_path(
    project_root: Path, context: dict[str, str] | None, target_path: str
) -> bool:
    state_file = str((context or {}).get("state_file") or "").strip()
    if not state_file or not target_path:
        return False
    return _normalized_path_for_compare(
        project_root, target_path
    ) == _normalized_path_for_compare(project_root, state_file)


def _is_validate_state_autofix_command(command: str) -> bool:
    normalized = " ".join(command.lower().split())
    return (
        "specify hook validate-state" in normalized
        and "--autofix" in normalized
        and "--feature-dir" in normalized
    )


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

    trigger_signals = _dedupe(
        [
            *_extract_list_field(text, "trigger_signal"),
            *_extract_list_field(text, "trigger_signals"),
            *_extract_section_items(text, "Learning Triggers"),
        ]
    )
    for item in trigger_signals:
        args.extend(["--trigger-signal", item])
        has_signal = True

    return args if has_signal else None


def _learning_signal_context(
    project_root: Path, context: dict[str, str], hook_event_name: str
) -> str:
    args = _learning_signal_args(context)
    if not args:
        return ""
    shared = _run_shared_hook(project_root, args)
    output = _shared_to_claude_output(
        hook_event_name=hook_event_name, shared_payload=shared
    )
    if not output:
        return ""
    return str(
        output.get("hookSpecificOutput", {}).get("additionalContext") or ""
    ).strip()


def _active_context_args(
    context: dict[str, str], *, include_command: bool = True
) -> list[str]:
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
    return _shared_to_claude_output(
        hook_event_name=hook_event_name, shared_payload=shared
    )


def _workflow_policy_shared(
    project_root: Path,
    context: dict[str, str] | None,
    *,
    trigger: str,
    requested_action: str = "",
) -> dict[str, Any] | None:
    if not context:
        return None
    args = ["workflow-policy", *_active_context_args(context), "--trigger", trigger]
    if requested_action:
        args.extend(["--requested-action", requested_action])
    return _run_shared_hook(project_root, args)


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
        shared = _run_shared_hook(
            project_root, ["read-compaction", *_active_context_args(context)]
        )
        artifact = shared.get("data", {}).get("artifact", {}) if shared else {}

    if build and (not shared or not isinstance(artifact, dict) or not artifact):
        args = [
            "build-compaction",
            *_active_context_args(context),
            "--trigger",
            trigger,
        ]
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


def _handle_user_prompt_submit(
    project_root: Path, payload: dict[str, Any]
) -> dict[str, Any] | None:
    prompt = _extract_prompt_text(payload)
    if not prompt:
        return None
    context = _infer_active_context(project_root)
    shared = _run_shared_hook(
        project_root,
        ["validate-prompt", "--prompt-stdin"],
        stdin_text=prompt,
    )
    output = _shared_to_claude_output(
        hook_event_name="UserPromptSubmit", shared_payload=shared
    )
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


def _handle_pre_tool_read(
    project_root: Path, payload: dict[str, Any]
) -> dict[str, Any] | None:
    if _extract_tool_name(payload) != "Read":
        return None
    context = _infer_active_context(project_root)
    policy_shared = _workflow_policy_shared(project_root, context, trigger="pre_tool")
    policy_output = _shared_to_claude_output(
        hook_event_name="PreToolUse", shared_payload=policy_shared
    )
    target_path = _extract_read_path(_extract_tool_input(payload))
    if not target_path:
        return policy_output
    if _is_repairable_block(policy_shared) and not _is_state_repair_path(
        project_root, context, target_path
    ):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "workflow-state repair is required before reading other files",
            }
        }
    if policy_output and "hookSpecificOutput" in policy_output:
        hook_specific = policy_output.get("hookSpecificOutput", {})
        if (
            isinstance(hook_specific, dict)
            and hook_specific.get("permissionDecision") == "deny"
        ):
            return policy_output
    shared = _run_shared_hook(
        project_root, ["validate-read-path", "--target-path", target_path]
    )
    output = _shared_to_claude_output(
        hook_event_name="PreToolUse", shared_payload=shared
    )
    return output or policy_output


def _handle_pre_tool_write(
    project_root: Path, payload: dict[str, Any]
) -> dict[str, Any] | None:
    if _extract_tool_name(payload) not in {"Write", "Edit", "MultiEdit"}:
        return None
    context = _infer_active_context(project_root)
    policy_shared = _workflow_policy_shared(project_root, context, trigger="pre_tool")
    target_path = _extract_write_path(_extract_tool_input(payload))
    if not target_path:
        return None
    if _is_repairable_block(policy_shared):
        if _is_state_repair_path(project_root, context, target_path):
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "workflow-state repair is required before writing other files",
            }
        }
    return None


def _handle_pre_tool_bash(
    project_root: Path, payload: dict[str, Any]
) -> dict[str, Any] | None:
    if _extract_tool_name(payload) != "Bash":
        return None
    context = _infer_active_context(project_root)
    command = str(_extract_tool_input(payload).get("command") or "").strip()
    policy_shared = _workflow_policy_shared(project_root, context, trigger="pre_tool")
    policy_output = _shared_to_claude_output(
        hook_event_name="PreToolUse", shared_payload=policy_shared
    )
    if not command:
        return policy_output
    if _is_repairable_block(policy_shared) and not _is_validate_state_autofix_command(
        command
    ):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "workflow-state repair is required before running other shell commands",
            }
        }
    if policy_output and "hookSpecificOutput" in policy_output:
        hook_specific = policy_output.get("hookSpecificOutput", {})
        if (
            isinstance(hook_specific, dict)
            and hook_specific.get("permissionDecision") == "deny"
        ):
            return policy_output
    commit_message = _extract_commit_message(command)
    if not commit_message:
        return policy_output
    args = ["validate-commit", "--commit-message", commit_message]
    if (
        context
        and context.get("command_name") == "implement"
        and context.get("feature_dir")
    ):
        args.extend(["--feature-dir", context["feature_dir"]])
    intent_match = re.search(
        r"(?:^|\s)-c\s+specify\.commitIntent=(?P<intent>[^\s]+)",
        command,
        re.IGNORECASE,
    )
    if intent_match:
        args.extend(["--commit-intent", intent_match.group("intent")])
    shared = _run_shared_hook(project_root, args)
    output = _shared_to_claude_output(
        hook_event_name="PreToolUse", shared_payload=shared
    )
    return output or policy_output


def _handle_session_start(
    project_root: Path, _payload: dict[str, Any]
) -> dict[str, Any] | None:
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
    additional_context = " ".join(
        part for part in [statusline, resume_context] if part
    ).strip()
    if not additional_context:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }


def _handle_post_tool_session_state(
    project_root: Path, _payload: dict[str, Any]
) -> dict[str, Any] | None:
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
    shared_output = _shared_to_claude_output(
        hook_event_name="PostToolUse", shared_payload=shared
    )
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


def _handle_stop_monitor(
    project_root: Path, _payload: dict[str, Any]
) -> dict[str, Any] | None:
    context = _infer_active_context(project_root)
    if not context:
        return None

    args = [
        "monitor-context",
        "--command",
        context["command_name"],
        "--trigger",
        "before_stop",
    ]
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
            "reason": errors[0]
            if errors
            else "shared context monitor blocked stop until resume state is repaired",
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
                if next_action and not _is_optional_next_action(next_action):
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
        "pre-tool-write": _handle_pre_tool_write,
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
