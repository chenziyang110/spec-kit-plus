"""Serialization helpers for workflow recovery checkpoints."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
import yaml

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


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
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
    frontmatter_text = "\n".join(lines[1:end_idx])
    try:
        loaded = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        loaded = {}
    frontmatter = loaded if isinstance(loaded, dict) else {}
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


def _frontmatter_string(frontmatter: dict[str, Any], key: str) -> str:
    value = frontmatter.get(key, "")
    if value is None:
        return ""
    if isinstance(value, str):
        return _strip_wrappers(value)
    return str(value).strip()


def _frontmatter_list(frontmatter: dict[str, Any], key: str) -> list[str]:
    value = frontmatter.get(key)
    if isinstance(value, list):
        return [_strip_wrappers(str(item)) for item in value if str(item).strip()]
    if isinstance(value, str):
        cleaned = _strip_wrappers(value)
        if not cleaned:
            return []
        return [cleaned]
    return []


def extract_nested_bullets_by_label(text: str, label: str) -> list[str]:
    target = f"{label}:"
    values: list[str] = []
    collecting = False
    child_indent: int | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        is_top_level_bullet = stripped.startswith("- ") and indent == 0
        if is_top_level_bullet:
            item = stripped[2:].strip()
            collecting = item.lower() == target.lower()
            child_indent = None
            continue
        if collecting and indent > 0 and stripped.startswith("- "):
            if child_indent is None:
                child_indent = indent
            if indent == child_indent:
                values.append(_strip_wrappers(stripped[2:].strip()))
    return values


def serialize_workflow_state(path: Path) -> dict[str, Any]:
    frontmatter, body = parse_frontmatter(_read_text(path))
    text = body
    current_command = section_body(text, "Current Command")
    phase_mode = section_body(text, "Phase Mode")
    fixed_lifecycle_state = section_body(text, "Fixed Lifecycle State")
    stage_state = section_body(text, "Stage State")
    lifecycle_state = fixed_lifecycle_state or stage_state
    analyze_gate = section_body(text, "Analyze Gate")
    scenario_profile = section_body(text, "Scenario Profile")
    profile_obligations = section_body(text, "Profile Obligations")
    next_action = section_body(text, "Next Action")
    next_command = section_body(text, "Next Command")
    allowed_artifact_writes = section_body(text, "Allowed Artifact Writes")
    forbidden_actions = section_body(text, "Forbidden Actions")
    authoritative_files = section_body(text, "Authoritative Files")
    lane_context = section_body(text, "Lane Context")
    resume_checklist = section_body(text, "Resume Checklist")
    exit_criteria = section_body(text, "Exit Criteria")
    learning_signals = section_body(text, "Learning Signals")
    learning_triggers = section_body(text, "Learning Triggers")
    false_starts = section_body(text, "False Starts")
    hidden_dependencies = section_body(text, "Hidden Dependencies")
    reusable_constraints = section_body(text, "Reusable Constraints")
    brainstorming_locks = section_body(text, "Brainstorming Locks")
    unknown_handling = section_body(text, "Unknown Handling")
    reopen_contract = section_body(text, "Reopen Contract")
    handoff_files = section_body(text, "Handoff Files")

    fixed_state_kind = bool(fixed_lifecycle_state)
    active_command = (
        extract_field(current_command, "active_command")
        or extract_field(fixed_lifecycle_state, "active_command")
        or _frontmatter_string(frontmatter, "active_command")
    )
    status = (
        extract_field(current_command, "status")
        or extract_field(fixed_lifecycle_state, "status")
        or _frontmatter_string(frontmatter, "status")
    )
    phase_mode_value = (
        extract_field(phase_mode, "phase_mode")
        or extract_field(fixed_lifecycle_state, "phase_mode")
        or _frontmatter_string(frontmatter, "phase_mode")
    )
    summary = (
        extract_field(phase_mode, "summary")
        or extract_field(fixed_lifecycle_state, "summary")
        or _frontmatter_string(frontmatter, "summary")
    )

    return {
        "state_kind": "workflow-state",
        "path": str(path),
        "active_command": active_command,
        "status": status,
        "phase_mode": phase_mode_value,
        "summary": summary,
        **(
            {}
            if fixed_state_kind
            else {
                "active_profile": extract_field(scenario_profile, "active_profile"),
                "routing_reason": extract_field(scenario_profile, "routing_reason"),
                "confidence_level": extract_field(scenario_profile, "confidence_level"),
                "required_sections": extract_nested_bullets_by_label(profile_obligations, "required_sections"),
                "activated_gates": extract_nested_bullets_by_label(profile_obligations, "activated_gates"),
                "task_shaping_rules": extract_nested_bullets_by_label(profile_obligations, "task_shaping_rules"),
                "required_evidence": extract_nested_bullets_by_label(profile_obligations, "required_evidence"),
                "transition_policy": extract_field(profile_obligations, "transition_policy"),
            }
        ),
        "current_stage": extract_field(lifecycle_state, "current_stage")
        or _frontmatter_string(frontmatter, "current_stage"),
        "current_domain": extract_field(lifecycle_state, "current_domain")
        or _frontmatter_string(frontmatter, "current_domain"),
        "next_action": extract_field(lifecycle_state, "next_action")
        or extract_first_nonempty_line(next_action)
        or _frontmatter_string(frontmatter, "next_action"),
        "blocker_reason": extract_field(lifecycle_state, "blocker_reason")
        or _frontmatter_string(frontmatter, "blocker_reason"),
        "approach_comparison_status": extract_field(lifecycle_state, "approach_comparison_status")
        or _frontmatter_string(frontmatter, "approach_comparison_status"),
        "section_approval_status": extract_field(lifecycle_state, "section_approval_status")
        or _frontmatter_string(frontmatter, "section_approval_status"),
        "final_handoff_decision": extract_field(lifecycle_state, "final_handoff_decision")
        or _frontmatter_string(frontmatter, "final_handoff_decision"),
        "gate_status": extract_field(analyze_gate, "gate_status"),
        "gate_cycle": extract_field(analyze_gate, "gate_cycle"),
        "highest_invalid_stage": extract_field(analyze_gate, "highest_invalid_stage"),
        "blocker_attribution_values": extract_field(analyze_gate, "blocker_attribution_values"),
        "facts_lock": extract_field(brainstorming_locks, "facts_lock"),
        "route_lock": extract_field(brainstorming_locks, "route_lock"),
        "intent_lock": extract_field(brainstorming_locks, "intent_lock"),
        "complexity_lock": extract_field(brainstorming_locks, "complexity_lock"),
        "hard_unknown_count": extract_field(unknown_handling, "hard_unknown_count"),
        "soft_unknown_count": extract_field(unknown_handling, "soft_unknown_count"),
        "next_unknown_to_resolve": extract_field(unknown_handling, "next_unknown_to_resolve"),
        "reopen_source": extract_field(reopen_contract, "reopen_source"),
        "reopen_target": extract_field(reopen_contract, "reopen_target"),
        "reopen_reason": extract_field(reopen_contract, "reopen_reason"),
        "handoff_to_specify": extract_field(handoff_files, "handoff_to_specify"),
        "handoff_to_plan": extract_field(handoff_files, "handoff_to_plan"),
        "handoff_to_tasks": extract_field(handoff_files, "handoff_to_tasks"),
        "handoff_to_implement": extract_field(handoff_files, "handoff_to_implement"),
        "next_command": extract_first_nonempty_line(next_command) or _frontmatter_string(frontmatter, "next_command"),
        "allowed_artifact_writes": extract_bullets(allowed_artifact_writes)
        or _frontmatter_list(frontmatter, "allowed_artifact_writes"),
        "forbidden_actions": extract_bullets(forbidden_actions) or _frontmatter_list(frontmatter, "forbidden_actions"),
        "authoritative_files": extract_bullets(authoritative_files)
        or _frontmatter_list(frontmatter, "authoritative_files"),
        "lane_id": extract_field(lane_context, "lane_id"),
        "branch_name": extract_field(lane_context, "branch_name"),
        "worktree_path": extract_field(lane_context, "worktree_path"),
        "recovery_state": extract_field(lane_context, "recovery_state"),
        "last_stable_checkpoint": extract_field(lane_context, "last_stable_checkpoint"),
        **(
            {}
            if fixed_state_kind
            else {
                "draft_file": extract_field(resume_checklist, "draft_file"),
                "coverage_mode": extract_field(resume_checklist, "coverage_mode"),
                "observer_status": extract_field(resume_checklist, "observer_status"),
                "last_observer_pass": extract_field(resume_checklist, "last_observer_pass"),
            }
        ),
        "exit_criteria": extract_bullets(exit_criteria),
        "route_reason": extract_field(learning_signals, "route_reason"),
        "blocked_reason": extract_field(learning_signals, "blocked_reason"),
        "trigger_signals": extract_bullets(learning_triggers),
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
