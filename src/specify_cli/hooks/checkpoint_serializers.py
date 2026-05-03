"""Serialization helpers for workflow recovery checkpoints."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .types import QualityHookError


SECTION_RE = re.compile(r"(?ms)^##+\s+(?P<title>.+?)\n(?P<body>.*?)(?=^##+\s+|\Z)")
COMMAND_ALIASES = {
    "research": "deep-research",
}


def normalize_command_name(command_name: str) -> str:
    normalized = str(command_name or "").strip().lower()
    if not normalized:
        raise QualityHookError("command_name is required")
    if normalized.startswith("sp-"):
        normalized = normalized[3:]
    elif normalized.startswith("sp."):
        normalized = normalized[3:]
    elif normalized.startswith("/sp-"):
        normalized = normalized[4:]
    elif normalized.startswith("/sp."):
        normalized = normalized[4:]
    normalized = COMMAND_ALIASES.get(normalized, normalized)
    return normalized


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_wrappers(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    return cleaned


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    lines = text.splitlines()
    end_idx = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_idx = index
            break
    if end_idx is None:
        return {}, text
    frontmatter: dict[str, str] = {}
    for raw_line in lines[1:end_idx]:
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = _strip_wrappers(value)
    body = "\n".join(lines[end_idx + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return frontmatter, body


def section_body(text: str, title: str) -> str:
    target = title.strip().lower()
    for match in SECTION_RE.finditer(text):
        if match.group("title").strip().lower() == target:
            return match.group("body").strip()
    return ""


def extract_field(text: str, field_name: str) -> str:
    prefix = f"{field_name}:"
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped.lower().startswith(prefix.lower()):
            return _strip_wrappers(stripped[len(prefix) :].strip())
    return ""


def extract_first_nonempty_line(text: str) -> str:
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        return _strip_wrappers(stripped)
    return ""


def extract_bullets(text: str) -> list[str]:
    values: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            continue
        values.append(_strip_wrappers(stripped[2:].strip()))
    return values


def serialize_workflow_state(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    current_command = section_body(text, "Current Command")
    phase_mode = section_body(text, "Phase Mode")
    next_action = section_body(text, "Next Action")
    next_command = section_body(text, "Next Command")
    authoritative_files = section_body(text, "Authoritative Files")
    exit_criteria = section_body(text, "Exit Criteria")
    learning_signals = section_body(text, "Learning Signals")
    false_starts = section_body(text, "False Starts")
    hidden_dependencies = section_body(text, "Hidden Dependencies")
    reusable_constraints = section_body(text, "Reusable Constraints")

    return {
        "state_kind": "workflow-state",
        "path": str(path),
        "active_command": extract_field(current_command, "active_command"),
        "status": extract_field(current_command, "status"),
        "phase_mode": extract_field(phase_mode, "phase_mode"),
        "next_action": extract_first_nonempty_line(next_action),
        "next_command": extract_first_nonempty_line(next_command),
        "authoritative_files": extract_bullets(authoritative_files),
        "exit_criteria": extract_bullets(exit_criteria),
        "route_reason": extract_field(learning_signals, "route_reason"),
        "blocked_reason": extract_field(learning_signals, "blocked_reason"),
        "false_starts": extract_bullets(false_starts),
        "hidden_dependencies": extract_bullets(hidden_dependencies),
        "reusable_constraints": extract_bullets(reusable_constraints),
    }


def serialize_implement_tracker(path: Path) -> dict[str, Any]:
    frontmatter, body = parse_frontmatter(_read_text(path))
    current_focus = section_body(body, "Current Focus")
    execution_state = section_body(body, "Execution State")

    return {
        "state_kind": "implement-tracker",
        "path": str(path),
        "status": frontmatter.get("status", ""),
        "resume_decision": frontmatter.get("resume_decision", ""),
        "current_batch": extract_field(current_focus, "current_batch"),
        "goal": extract_field(current_focus, "goal"),
        "next_action": extract_field(current_focus, "next_action"),
        "retry_attempts": extract_field(execution_state, "retry_attempts"),
    }


def serialize_quick_status(path: Path) -> dict[str, Any]:
    frontmatter, body = parse_frontmatter(_read_text(path))
    current_focus = section_body(body, "Current Focus")
    execution = section_body(body, "Execution")
    summary_pointer = section_body(body, "Summary Pointer")

    return {
        "state_kind": "quick-status",
        "path": str(path),
        "status": frontmatter.get("status", ""),
        "strategy": frontmatter.get("strategy", ""),
        "active_lane": extract_field(execution, "active_lane"),
        "next_action": extract_field(current_focus, "next_action"),
        "resume_decision": extract_field(summary_pointer, "resume_decision"),
    }


def serialize_debug_session(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    current_focus = section_body(text, "Current Focus")
    observer_framing = section_body(text, "Observer Framing")
    return {
        "state_kind": "debug-session",
        "path": str(path),
        "next_action": extract_field(current_focus, "next_action") or extract_first_nonempty_line(current_focus),
        "observer_summary": extract_first_nonempty_line(observer_framing),
    }
