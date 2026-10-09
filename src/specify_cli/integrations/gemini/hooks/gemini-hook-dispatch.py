#!/usr/bin/env python3
"""Thin Gemini CLI native hook adapter for spec-kit-plus.

This script is installed into ``.gemini/hooks/`` for project-local Gemini
integrations. Runtime-owned validation hooks are routed to the project-pinned
``specify-runtime`` binary. Hooks not yet owned by that binary continue through
the human/bootstrap ``specify`` launcher during the migration window.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import shlex
from contextvars import ContextVar
from functools import wraps
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Literal, NamedTuple


WORKFLOW_COMMAND_MAP = {
    "sp-specify": "specify",
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
RUNTIME_OWNED_HOOK_SUBCOMMANDS = frozenset(
    {"validate-artifacts", "validate-commit", "validate-state"}
)
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
    env_root = str(os.environ.get("GEMINI_PROJECT_DIR") or "").strip()
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


def _launcher_argv_from_project_config(
    project_root: Path, *keys: str
) -> tuple[str, ...] | None:
    config_path = project_root / ".specify" / "config.json"
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(loaded, dict):
        return None

    launcher = next(
        (loaded.get(key) for key in keys if isinstance(loaded.get(key), dict)),
        None,
    )
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


def _argv_from_project_config(project_root: Path) -> tuple[str, ...] | None:
    return _launcher_argv_from_project_config(
        project_root, "specify_launcher", "hook_launcher"
    )


def _runtime_argv_from_project_config(project_root: Path) -> tuple[str, ...] | None:
    return _launcher_argv_from_project_config(project_root, "runtime_launcher")


_EXPLICIT_WORKFLOW: ContextVar[str | None] = ContextVar("explicit_workflow", default=None)
_EXPLICIT_DO_SESSION: ContextVar[str | None] = ContextVar("explicit_do_session", default=None)


def _current_user_prompt(payload: dict[str, Any]) -> str:
    prompt = ""
    for key in ("prompt", "prompt_text", "user_prompt", "userPrompt", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            prompt = value.strip()
            break
    if not prompt:
        request = payload.get("llm_request") or payload.get("llmRequest") or {}
        messages = request.get("messages", []) if isinstance(request, dict) else []
        for message in reversed(messages if isinstance(messages, list) else []):
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            parts = message.get("parts", [])
            content = message.get("content")
            if isinstance(content, str):
                prompt = content.strip()
            elif isinstance(parts, list):
                prompt = " ".join(
                    part["text"]
                    for part in parts
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                ).strip()
            break
    return prompt


def _explicit_workflow_command(payload: dict[str, Any]) -> str | None:
    """Use only an explicit invocation in the current native user payload."""
    match = re.match(
        r"^(?:use\s+)?(?:/skill:|[$/])spx?[-.]([a-z][a-z0-9-]*)(?=$|\s)",
        _current_user_prompt(payload),
        re.IGNORECASE,
    )
    return match.group(1).lower() if match else None


def _explicit_do_session(payload: dict[str, Any]) -> str | None:
    match = re.match(
        r"^(?:use\s+)?(?:/skill:|[$/])spx?[-.]do\s+resume(?=$|\s)(.*)$",
        _current_user_prompt(payload), re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    arguments = match.group(1).split()
    # An explicitly malformed resume must never adopt another active owner.
    session_id = arguments[0] if arguments else ""
    return session_id if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", session_id) else ""


def _with_explicit_workflow_context(handler):
    @wraps(handler)
    def wrapped(project_root: Path, payload: dict[str, Any]):
        token = _EXPLICIT_WORKFLOW.set(_explicit_workflow_command(payload))
        session_token = _EXPLICIT_DO_SESSION.set(_explicit_do_session(payload))
        try:
            return handler(project_root, payload)
        finally:
            _EXPLICIT_DO_SESSION.reset(session_token)
            _EXPLICIT_WORKFLOW.reset(token)
    return wrapped


def _do_runtime_payload(project_root: Path, *args: str) -> dict[str, Any] | None:
    """Read standalone DO state through the pinned Go runtime, never Python."""
    launcher = _runtime_argv_from_project_config(project_root)
    if not launcher or not args or args[0] not in {"show", "validate"}:
        return None
    capability = f"do.{args[0]}"
    deadline = time.monotonic() + SHARED_HOOK_TIMEOUT_SECONDS
    try:
        ensured = subprocess.run(
            [*launcher, "api", "ensure", "--capabilities", capability, "--format", "json"],
            cwd=project_root, text=True, encoding="utf-8", errors="replace",
            capture_output=True, check=False, timeout=SHARED_HOOK_TIMEOUT_SECONDS,
        )
        discovery = json.loads(ensured.stdout or "")
        data = discovery.get("data") if isinstance(discovery, dict) else None
        if not (
            ensured.returncode == 0 and isinstance(discovery, dict)
            and discovery.get("status") == "ok" and isinstance(data, dict)
            and data.get("requested") == [capability]
            and data.get("present") == [capability] and data.get("missing") == []
        ):
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        result = subprocess.run(
            [*launcher, "do", *args, "--format", "json"],
            cwd=project_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=min(SHARED_HOOK_TIMEOUT_SECONDS, remaining),
        )
        if result.returncode not in {0, 10}:
            return None
        payload = json.loads(result.stdout or "")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _active_do_context(project_root: Path) -> dict[str, str] | None:
    selected_id = _EXPLICIT_DO_SESSION.get()
    if selected_id is not None:
        unavailable = {"command_name": "do", "unavailable": "true"}
        if not selected_id:
            return {**unavailable, "invalid_resume": "true"}
        unavailable["session_id"] = selected_id
        payload = _do_runtime_payload(project_root, "show", selected_id)
        data = payload.get("data") if payload else None
        if not payload or payload.get("status") != "ok" or not _do_selected_session_matches(data):
            return unavailable
        # Keep an explicitly selected terminal session bound through its stop gate.
        return {"command_name": "do", "session_id": selected_id}
    if not (project_root / ".specify" / "do").is_dir():
        return None
    payload = _do_runtime_payload(project_root, "show", "--active", "--adapter-id", "gemini")
    data = payload.get("data", {}) if payload else {}
    if not isinstance(data, dict):
        return {"command_name": "do", "unavailable": "true"}
    if data.get("ambiguous") is True:
        return {"command_name": "do", "ambiguous": "true"}
    if not payload or payload.get("status") != "ok":
        return {"command_name": "do", "unavailable": "true"}
    if data.get("active") is False:
        return None
    if data.get("active") is not True:
        return {"command_name": "do", "unavailable": "true"}
    session = data.get("session", {})
    session_id = data.get("session_id") or (
        session.get("id") if isinstance(session, dict) else None
    )
    if not isinstance(session_id, str) or not session_id.strip():
        return {"command_name": "do", "unavailable": "true"}
    return {"command_name": "do", "session_id": session_id}


def _do_selected_session_matches(data: Any) -> bool:
    selected_id = _EXPLICIT_DO_SESSION.get()
    if selected_id is None:
        return True
    session = data.get("session") if isinstance(data, dict) else None
    return (
        bool(selected_id) and isinstance(session, dict) and session.get("id") == selected_id
        and ("session_id" not in data or data["session_id"] == selected_id)
    )


def _do_resume_context(context: dict[str, str]) -> str:
    if context.get("invalid_resume") == "true":
        return "An explicit Do resume requires a valid exact session ID; use `/sp-do resume <id>` and do not select another active session."
    if context.get("ambiguous") == "true":
        return "Multiple active DoSessions require an explicit session ID; do not choose the latest session or switch workflows."
    if context.get("unavailable") == "true":
        lookup = f"do show {context['session_id']}" if context.get("session_id") else "do show --active --adapter-id gemini"
        return (
            "DoSession ownership could not be read from the pinned runtime. "
            f"Restore that runtime and use it for `{lookup}`; "
            "do not treat the failed lookup as no active session or claim completion."
        )
    session_id = context["session_id"]
    return (
        f"Selected DoSession {session_id}. Use the project-pinned runtime for `do show {session_id}` "
        f"and `do resume {session_id}` for the exact pending action. "
        "Preserve observed attempts and reconcile uncertain external effects before retrying. "
        "Completion requires fresh do validation and a terminal execution/knowledge receipt."
    )


def _do_validation_context(project_root: Path, context: dict[str, str]) -> str:
    if context.get("ambiguous") == "true" or context.get("unavailable") == "true":
        return _do_resume_context(context)
    payload = _do_runtime_payload(project_root, "validate", context["session_id"])
    data = payload.get("data", {}) if payload else {}
    validation = data.get("validation", {}) if isinstance(data, dict) else {}
    if not payload or payload.get("status") not in {"ok", "blocked"} or not isinstance(validation, dict) or not validation or not _do_selected_session_matches(data):
        return _do_resume_context(context) + " The current DO validation could not be read; do not claim completion."
    session = data.get("session", {})
    blocker = session.get("blocker") if isinstance(session, dict) else None
    if data.get("can_stop") is True and data.get("terminal") is False and isinstance(blocker, dict) and blocker.get("owner") in {"human", "external"}:
        return _do_resume_context(context) + " A recorded external blocker permits a blocked exit; report its next action and resume point without claiming completion."
    terminal = payload.get("status") == "ok" and data.get("terminal") is True and validation.get("status") == "passed"
    state = "terminal and freshly validated" if terminal else "not yet terminal; continue the runtime's pending action"
    return _do_resume_context(context) + f" Validation: {state}."


def _runtime_owned_hook(args: list[str]) -> bool:
    return bool(args) and args[0] in RUNTIME_OWNED_HOOK_SUBCOMMANDS


def _project_launcher_broken(project_root: Path, args: list[str]) -> bool:
    launcher_argv = (
        _runtime_argv_from_project_config(project_root)
        if _runtime_owned_hook(args)
        else _argv_from_project_config(project_root)
    )
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
    if _runtime_owned_hook(args):
        runtime_argv = _runtime_argv_from_project_config(project_root)
        return [[*runtime_argv, "hook", *args]] if runtime_argv else []

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
    if _project_launcher_broken(project_root, args):
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


def _shared_additional_context(shared_payload: dict[str, Any] | None) -> str:
    if not shared_payload:
        return ""
    warnings = [
        str(item) for item in shared_payload.get("warnings", []) if str(item).strip()
    ]
    actions = [
        str(item) for item in shared_payload.get("actions", []) if str(item).strip()
    ]
    return " ".join([*warnings, *actions]).strip()


def _shared_blocker_detail(shared_payload: dict[str, Any]) -> str:
    blockers = shared_payload.get("blockers")
    if (
        not isinstance(blockers, list)
        or not blockers
        or not isinstance(blockers[0], dict)
    ):
        return ""
    blocker = blockers[0]
    workflow = str(blocker.get("workflow") or "").strip()
    stage = str(blocker.get("stage") or "").strip()
    summary = str(blocker.get("summary") or "").strip()
    category = str(blocker.get("category") or "").strip()
    owner = str(blocker.get("owner") or "").strip()
    cause = str(blocker.get("details") or blocker.get("cause") or "").strip()
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
    attempted_text = "none recorded" if "attempted_recovery" in blocker else ""
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
        f"Workflow/stage: {workflow or '-'} / {stage or '-'}"
        if workflow or stage
        else "",
        f"Blocked: {summary}" if summary else "",
        f"Category/owner: {category or '-'} / {owner or '-'}"
        if category or owner
        else "",
        f"Why: {cause}" if cause else "",
        f"Evidence: {evidence_text}" if evidence_text else "",
        f"Attempted recovery: {attempted_text}" if attempted_text else "",
        f"Affected scope: {affected_text}" if affected_text else "",
        f"Next action: {blocker.get('exact_next_action')}"
        if blocker.get("exact_next_action")
        else "",
        f"Unblock criteria: {blocker.get('unblock_criteria')}"
        if blocker.get("unblock_criteria")
        else "",
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
    return " | ".join(part for part in parts if part)


def _shared_block_to_gemini(
    shared_payload: dict[str, Any] | None,
    *,
    system_message: str = "",
) -> dict[str, Any] | None:
    if not shared_payload:
        return None
    status = str(shared_payload.get("status") or "").strip().lower()
    if status == "repairable-block":
        autofix_command = str(
            ((shared_payload.get("data") or {}).get("autofix") or {}).get("command")
            or ""
        ).strip()
        extra = _shared_additional_context(shared_payload)
        blocker_detail = _shared_blocker_detail(shared_payload)
        message = " ".join(
            part
            for part in [system_message, blocker_detail, extra, autofix_command]
            if part
        ).strip()
        if message:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "BeforeAgent",
                    "additionalContext": message,
                }
            }
        return {}
    if status != "blocked":
        return None
    errors = [
        str(item) for item in shared_payload.get("errors", []) if str(item).strip()
    ]
    warnings = [
        str(item) for item in shared_payload.get("warnings", []) if str(item).strip()
    ]
    actions = [
        str(item) for item in shared_payload.get("actions", []) if str(item).strip()
    ]
    reason = (
        errors[0]
        if errors
        else (warnings[0] if warnings else "shared quality hook blocked the action")
    )
    blocker_detail = _shared_blocker_detail(shared_payload)
    detailed_reason = blocker_detail or reason
    extra = " ".join([system_message, *warnings, *actions]).strip()
    output = {
        "decision": "deny",
        "reason": detailed_reason,
    }
    if extra:
        output["systemMessage"] = extra
    return output


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
        "specify-runtime hook validate-state" in normalized
        and "--autofix" in normalized
        and "--feature-dir" in normalized
    )


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
    # DO has no feature state: its only owner is the adapter-filtered runtime lookup.
    explicit = _EXPLICIT_WORKFLOW.get()
    if explicit is not None:
        if explicit == "do":
            return _active_do_context(project_root)
        return _infer_legacy_active_context(project_root, command_name=explicit)
    do_context = _active_do_context(project_root)
    if do_context:
        return do_context
    return _infer_legacy_active_context(project_root)


def _infer_legacy_active_context(project_root: Path, command_name: str | None = None) -> dict[str, str] | None:
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
    if implement_candidates and command_name in {None, "implement"}:
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
    if quick_candidates and command_name in {None, "quick"}:
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
            if not mapped or command_name not in {None, mapped} or (status and not _is_active_state_status(status)):
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


def _active_context_args(context: dict[str, str]) -> list[str]:
    args = ["--command", context["command_name"]]
    if "feature_dir" in context:
        args.extend(["--feature-dir", context["feature_dir"]])
    if "workspace" in context:
        args.extend(["--workspace", context["workspace"]])
    if "session_file" in context:
        args.extend(["--session-file", context["session_file"]])
    return args


def _compaction_resume_context(
    project_root: Path,
    *,
    build: bool,
    trigger: str,
) -> str:
    context = _infer_active_context(project_root)
    if not context:
        return ""
    if context.get("command_name") == "do":
        return _do_resume_context(context)
    shared = _run_shared_hook(
        project_root, ["read-compaction", *_active_context_args(context)]
    )
    artifact = shared.get("data", {}).get("artifact", {}) if shared else {}
    if build and (not shared or not isinstance(artifact, dict) or not artifact):
        shared = _run_shared_hook(
            project_root,
            ["build-compaction", *_active_context_args(context), "--trigger", trigger],
        )
    if not shared:
        return ""
    artifact = shared.get("data", {}).get("artifact", {})
    if not isinstance(artifact, dict):
        return ""
    recovery_summary = artifact.get("recovery_summary", {})
    if isinstance(recovery_summary, dict):
        formatted = _format_recovery_summary(recovery_summary)
        if formatted:
            return formatted
    phase_state = artifact.get("phase_state", {})
    if isinstance(phase_state, dict):
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


def _workflow_policy_block(
    project_root: Path, *, trigger: str, requested_action: str = ""
) -> dict[str, Any] | None:
    if not requested_action:
        return None
    context = _infer_active_context(project_root)
    if not context or context.get("command_name") == "do":
        return None
    args = ["workflow-policy", *_active_context_args(context), "--trigger", trigger]
    if requested_action:
        args.extend(["--requested-action", requested_action])
    shared = _run_shared_hook(project_root, args)
    if not shared:
        return None
    status = str(shared.get("status") or "").strip().lower()
    policy = shared.get("data", {}).get("policy", {})
    if (
        status == "warn"
        and isinstance(policy, dict)
        and policy.get("classification") == "redirect"
    ):
        recovery_summary = policy.get("recovery_summary", {})
        message = (
            _format_recovery_summary(recovery_summary)
            if isinstance(recovery_summary, dict)
            else ""
        )
        warnings = [
            str(item) for item in shared.get("warnings", []) if str(item).strip()
        ]
        reason = (
            warnings[0]
            if warnings
            else "requested action conflicts with the active workflow phase"
        )
        output = {"decision": "deny", "reason": reason}
        if message:
            output["systemMessage"] = message
        return output
    if status not in {"blocked", "repairable-block"}:
        return None
    return _shared_block_to_gemini(shared)


def _workflow_policy_shared(
    project_root: Path,
    *,
    trigger: str,
    context: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    context = context or _infer_active_context(project_root)
    if not context or context.get("command_name") == "do":
        return None
    args = ["workflow-policy", *_active_context_args(context), "--trigger", trigger]
    return _run_shared_hook(project_root, args)


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

    if not has_signal:
        return ""
    shared = _run_shared_hook(project_root, args)
    return _shared_additional_context(shared)


@_with_explicit_workflow_context
def _handle_session_start(
    project_root: Path, _payload: dict[str, Any]
) -> dict[str, Any]:
    context = _infer_active_context(project_root)
    if context and context.get("command_name") == "do":
        resume = _do_resume_context(context)
        return {
            "systemMessage": resume,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": resume},
        }
    statusline = _statusline_context(project_root)
    resume_context = _compaction_resume_context(
        project_root, build=True, trigger="session_start"
    )
    message = " ".join(part for part in [statusline, resume_context] if part).strip()
    return {"systemMessage": message} if message else {}


@_with_explicit_workflow_context
def _handle_before_agent(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    prompt = _extract_prompt_text(payload)
    context = _infer_active_context(project_root)
    if context and context.get("command_name") == "do":
        advisory = _do_validation_context(project_root, context)
        if prompt:
            shared = _run_shared_hook(
                project_root, ["validate-prompt", "--prompt-stdin"], stdin_text=prompt
            )
            blocked = _shared_block_to_gemini(shared, system_message=advisory)
            if blocked:
                return blocked
        return {
            "hookSpecificOutput": {
                "hookEventName": "BeforeAgent", "additionalContext": advisory
            }
        }
    statusline = _statusline_context(project_root)
    resume_context = _compaction_resume_context(
        project_root, build=False, trigger="prompt"
    )
    learning_signal = _learning_signal_context(project_root)
    advisory = " ".join([statusline, resume_context, learning_signal]).strip()

    if prompt:
        shared = _run_shared_hook(
            project_root,
            ["validate-prompt", "--prompt-stdin"],
            stdin_text=prompt,
        )
        blocked = _shared_block_to_gemini(shared, system_message=advisory)
        if blocked:
            return blocked
        policy_shared = _workflow_policy_shared(project_root, trigger="prompt")
        repairable = _shared_block_to_gemini(policy_shared, system_message=advisory)
        if repairable:
            return repairable
        normalized_prompt = prompt.lower()
        requested_action = ""
        if (
            "implement directly" in normalized_prompt
            or "jump to implement" in normalized_prompt
        ):
            requested_action = "jump_to_implement"
        elif (
            "start editing code" in normalized_prompt
            or "start implementation" in normalized_prompt
        ):
            requested_action = "start_editing_code"
        policy_block = _workflow_policy_block(
            project_root, trigger="prompt", requested_action=requested_action
        )
        if policy_block:
            if advisory and not policy_block.get("systemMessage"):
                policy_block["systemMessage"] = advisory
            return policy_block

    if advisory:
        return {
            "hookSpecificOutput": {
                "hookEventName": "BeforeAgent",
                "additionalContext": advisory,
            }
        }
    return {}


@_with_explicit_workflow_context
def _handle_before_tool(project_root: Path, payload: dict[str, Any], *, owner_paths: set[str] | None = None) -> dict[str, Any]:
    tool_name = _extract_tool_name(payload).lower()
    tool_input = _extract_tool_input(payload)
    context = _infer_active_context(project_root)
    policy_shared = _workflow_policy_shared(
        project_root, trigger="pre_tool", context=context
    )

    if tool_name in {"read_file", "read", "read-file"}:
        target_path = _extract_read_path(tool_input)
        if not target_path:
            return {}
        if _is_repairable_block(policy_shared) and _is_state_repair_path(
            project_root, context, target_path
        ):
            return {}
        if _is_repairable_block(policy_shared):
            return {
                "decision": "deny",
                "reason": "workflow-state repair is required before reading other files",
            }
        shared = _run_shared_hook(
            project_root, ["validate-read-path", "--target-path", target_path]
        )
        return _shared_block_to_gemini(shared) or {}

    if tool_name in {"run_shell_command", "bash", "run-shell-command"}:
        command = str(tool_input.get("command") or "").strip()
        if not command:
            return {}
        if _is_repairable_block(policy_shared) and _is_validate_state_autofix_command(
            command
        ):
            return {}
        if _is_repairable_block(policy_shared):
            return {
                "decision": "deny",
                "reason": "workflow-state repair is required before running other shell commands",
            }
        commit_message = _extract_commit_message(command)
        if not commit_message:
            return {}
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
        return _shared_block_to_gemini(shared) or {}

    if tool_name in {
        "write_file",
        "write",
        "edit_file",
        "edit",
        "multi_edit",
        "multiedit",
    }:
        target_path = _extract_read_path(tool_input)
        if _is_repairable_block(policy_shared) and _is_state_repair_path(
            project_root, context, target_path
        ):
            if owner_paths is not None:
                owner_paths.add(target_path)
            return {}
        if _is_repairable_block(policy_shared):
            return {
                "decision": "deny",
                "reason": "workflow-state repair is required before writing other files",
            }

    return {}


@_with_explicit_workflow_context
def _handle_after_agent(project_root: Path, _payload: dict[str, Any]) -> dict[str, Any]:
    context = _infer_active_context(project_root)
    if not context or context.get("command_name") != "do":
        return {}
    if context.get("ambiguous") == "true" or context.get("unavailable") == "true":
        return {"decision": "deny", "reason": _do_resume_context(context)}
    session_id = context["session_id"]
    shown = _do_runtime_payload(project_root, "show", session_id)
    shown_data = shown.get("data") if shown else None
    if not shown or shown.get("status") != "ok" or not isinstance(shown_data, dict) or not _do_selected_session_matches(shown_data):
        return {"decision": "deny", "reason": _do_resume_context(context) + " Restore the pinned runtime before ending this operation."}
    session = shown_data.get("session", {})
    blocker = session.get("blocker") if isinstance(session, dict) else None
    if (
        shown_data.get("can_stop") is True and shown_data.get("terminal") is False
        and isinstance(blocker, dict) and blocker.get("owner") in {"human", "external"}
    ):
        return {}
    payload = _do_runtime_payload(project_root, "validate", session_id)
    data = payload.get("data") if payload else None
    validation = data.get("validation") if isinstance(data, dict) else None
    if (
        payload and payload.get("status") == "ok" and isinstance(data, dict)
        and data.get("terminal") is True and isinstance(validation, dict)
        and _do_selected_session_matches(data)
        and validation.get("status") == "passed"
    ):
        return {}
    return {
        "decision": "deny",
        "reason": f"DoSession {session_id} has no fresh terminal execution and knowledge receipt. "
        "Inspect do show/validate and complete only its pending recovery or closeout action.",
    }


def main() -> int:
    route = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = _read_stdin_payload()
    project_root = _project_root(payload)

    handlers = {
        "session-start": _handle_session_start,
        "before-agent": _handle_before_agent,
        "before-tool": _handle_before_tool,
        "after-agent": _handle_after_agent,
    }
    handler = handlers.get(route)
    if not handler:
        return 0

    owner_paths: set[str] = set()
    output = (
        handler(project_root, payload, owner_paths=owner_paths)
        if route == "before-tool"
        else handler(project_root, payload)
    )
    if route in {"before-tool", "after-agent"} and output.get("decision") not in {"deny", "block"} and output.get("continue") is not False:
        phase = "finish" if route == "after-agent" else "before"
        asset = _run_asset_guard(project_root, payload, phase, owner_paths=owner_paths)
        if asset.get("status") == "blocked":
            output.update({"decision": "deny", "reason": str(asset.get("message") or "Asset check failed.")})
        elif asset.get("status") == "unavailable":
            output["systemMessage"] = " ".join(part for part in [output.get("systemMessage", ""), str(asset.get("message") or "Asset verification is unavailable; do not claim it passed.")] if part)
    sys.stdout.write(json.dumps(output))
    return 0


def _run_asset_guard(project_root: Path, payload: dict[str, Any], phase: str, *, owner_paths: set[str] | None = None) -> dict[str, Any]:
    tool_name = _extract_tool_name(payload).lower()
    if phase == "before" and tool_name not in {"write", "edit", "multiedit", "write_file", "edit_file", "multi_edit", "replace", "bash", "powershell", "run_shell_command", "run-shell-command"}:
        return {}
    candidates = [project_root / ".specify/bin/specify-asset-guard.py"]
    candidates.extend(parent / "shared_hooks/specify-asset-guard.py" for parent in Path(__file__).resolve().parents)
    helper_path = next((path for path in candidates if path.is_file()), None)
    if helper_path is None:
        if phase == "finish":
            return {}
        return {"status": "unavailable", "message": "Asset verification is unavailable: the project hook helper is missing. Repair the integration; do not claim this check passed."}
    try:
        spec = importlib.util.spec_from_file_location("spec_kit_asset_guard", helper_path)
        if spec is None or spec.loader is None:
            raise ValueError("asset helper cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode
        if phase == "finish":
            return module.finish_turn(project_root, payload, "gemini")
        return module.before_tool(project_root, payload, "gemini", owner_paths=owner_paths)
    except (OSError, ValueError, AttributeError, TypeError, ImportError, SyntaxError) as exc:
        return {"status": "unavailable", "message": f"Asset verification is unavailable: {' '.join(str(exc).split())[:200]}. Do not claim this check passed."}


if __name__ == "__main__":
    raise SystemExit(main())
