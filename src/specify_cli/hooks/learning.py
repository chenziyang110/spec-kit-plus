"""Learning hooks that turn passive self-learning into workflow gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .checkpoint_serializers import normalize_command_name
from .events import (
    WORKFLOW_LEARNING_CAPTURE,
    WORKFLOW_LEARNING_INJECT,
    WORKFLOW_LEARNING_REVIEW,
    WORKFLOW_LEARNING_SIGNAL,
)
from .types import HookResult, QualityHookError


TERMINAL_STATUSES = {
    "resolved",
    "blocked",
    "complete",
    "completed",
    "closeout",
    "handoff",
    "awaiting-human",
    "awaiting-human-verify",
    "awaiting_human",
    "awaiting_human_verify",
    "complete-refresh",
}

LEARNING_REVIEW_DECISIONS = {
    "none",
    "captured",
    "deferred",
    "auto-captured",
    "manual-capture-needed",
}

PAIN_THRESHOLD = 5


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, list):
        return []
    values: list[str] = []
    for item in value:
        stripped = str(item).strip()
        if stripped:
            values.append(stripped)
    return values


def _sp_command(command_name: str) -> str:
    return f"sp-{normalize_command_name(command_name)}"


def _pain_score(payload: dict[str, object]) -> tuple[int, dict[str, int]]:
    factors = {
        "retry_attempts": _coerce_int(payload.get("retry_attempts")) * 2,
        "hypothesis_changes": _coerce_int(payload.get("hypothesis_changes")) * 2,
        "validation_failures": _coerce_int(payload.get("validation_failures")),
        "artifact_rewrites": _coerce_int(payload.get("artifact_rewrites")),
        "command_failures": _coerce_int(payload.get("command_failures")),
        "user_corrections": _coerce_int(payload.get("user_corrections")) * 2,
        "route_changes": _coerce_int(payload.get("route_changes")) * 2,
        "scope_changes": _coerce_int(payload.get("scope_changes")),
        "false_starts": len(_coerce_str_list(payload.get("false_starts"))),
        "hidden_dependencies": len(_coerce_str_list(payload.get("hidden_dependencies"))),
    }
    return sum(factors.values()), factors


def derive_injection_targets(command_name: str, learning_type: str) -> list[str]:
    from specify_cli.learnings import normalize_learning_type

    command = _sp_command(command_name)
    normalized_type = normalize_learning_type(learning_type)
    targets_by_type = {
        "routing_mistake": ["spec-kit-workflow-routing", "sp-fast", "sp-quick", "sp-specify"],
        "verification_gap": ["sp-test", "sp-implement", "sp-debug", ".specify/testing/TESTING_CONTRACT.md"],
        "state_surface_gap": ["workflow-state.md", "implement-tracker.md", "STATUS.md", "sp-implement", "sp-quick"],
        "map_coverage_gap": ["sp-map-codebase", "PROJECT-HANDBOOK.md", ".specify/project-map/"],
        "tooling_trap": ["sp-debug", "sp-implement", "sp-map-codebase"],
        "false_lead_pattern": ["sp-debug", "sp-implement"],
        "near_miss": ["sp-implement", "sp-debug", "project-rules"],
        "decision_debt": ["sp-specify", "sp-plan", "sp-tasks", "ADR"],
        "workflow_gap": ["sp-specify", "sp-plan", "sp-tasks"],
        "project_constraint": ["project-rules", "project-learnings", command],
        "recovery_path": ["sp-debug", "sp-implement", "sp-quick"],
        "pitfall": ["sp-debug", "sp-implement", "sp-quick"],
        "user_preference": ["project-rules", "AGENTS.md", command],
    }
    return sorted(dict.fromkeys([command, *targets_by_type.get(normalized_type, [])]))


def learning_signal_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    score, factors = _pain_score(payload)
    data = {
        "command": f"sp-{command_name}",
        "pain_score": score,
        "factors": factors,
        "threshold": PAIN_THRESHOLD,
        "false_starts": _coerce_str_list(payload.get("false_starts")),
    }
    if score < PAIN_THRESHOLD:
        return HookResult(
            event=WORKFLOW_LEARNING_SIGNAL,
            status="ok",
            severity="info",
            data=data,
        )
    return HookResult(
        event=WORKFLOW_LEARNING_SIGNAL,
        status="warn",
        severity="warning",
        actions=[
            f"run `specify hook review-learning --command {command_name} --terminal-status resolved` before terminal closeout",
            "capture a candidate learning if the friction exposed a reusable pitfall, workflow gap, hidden constraint, or tooling trap",
        ],
        warnings=[
            f"learning pain score {score} crossed threshold {PAIN_THRESHOLD}; this workflow has reusable-learning signal"
        ],
        data=data,
    )


def learning_review_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    terminal_status = str(payload.get("terminal_status") or "").strip().lower()
    if not terminal_status:
        raise QualityHookError("terminal_status is required")
    if terminal_status not in TERMINAL_STATUSES:
        return HookResult(
            event=WORKFLOW_LEARNING_REVIEW,
            status="ok",
            severity="info",
            data={
                "command": f"sp-{command_name}",
                "terminal_status": terminal_status,
                "review": {"decision": "not-terminal"},
            },
        )

    raw_review = payload.get("learning_review")
    if not isinstance(raw_review, dict):
        return HookResult(
            event=WORKFLOW_LEARNING_REVIEW,
            status="blocked",
            severity="critical",
            errors=[
                "learning review is required before terminal workflow closeout; provide a review decision or capture a candidate learning"
            ],
            actions=[
                f"run `specify hook review-learning --command {command_name} --terminal-status {terminal_status} --decision none --rationale \"...\"` when no reusable learning exists",
                f"run `specify hook capture-learning --command {command_name} ...` when this run exposed reusable friction",
            ],
            data={"command": f"sp-{command_name}", "terminal_status": terminal_status},
        )

    decision = str(raw_review.get("decision") or "").strip().lower()
    if decision not in LEARNING_REVIEW_DECISIONS:
        return HookResult(
            event=WORKFLOW_LEARNING_REVIEW,
            status="blocked",
            severity="critical",
            errors=["learning review decision must be one of: " + ", ".join(sorted(LEARNING_REVIEW_DECISIONS))],
            data={"command": f"sp-{command_name}", "terminal_status": terminal_status, "review": raw_review},
        )
    rationale = str(raw_review.get("rationale") or "").strip()
    if decision == "none" and not rationale:
        return HookResult(
            event=WORKFLOW_LEARNING_REVIEW,
            status="blocked",
            severity="critical",
            errors=["learning review decision `none` requires a rationale"],
            data={"command": f"sp-{command_name}", "terminal_status": terminal_status, "review": raw_review},
        )

    return HookResult(
        event=WORKFLOW_LEARNING_REVIEW,
        status="ok",
        severity="info",
        data={
            "command": f"sp-{command_name}",
            "terminal_status": terminal_status,
            "review": {"decision": decision, "rationale": rationale},
        },
    )


def learning_inject_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    from specify_cli.learnings import normalize_learning_type

    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    learning_type = normalize_learning_type(str(payload.get("learning_type") or ""))
    targets = derive_injection_targets(command_name, learning_type)
    return HookResult(
        event=WORKFLOW_LEARNING_INJECT,
        status="ok",
        severity="info",
        actions=[f"route future prevention through: {', '.join(targets)}"],
        data={
            "command": f"sp-{command_name}",
            "learning_type": learning_type,
            "summary": str(payload.get("summary") or "").strip(),
            "injection_targets": targets,
        },
    )


def learning_capture_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    from specify_cli.learnings import capture_learning, normalize_learning_type

    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    learning_type = normalize_learning_type(str(payload.get("learning_type") or ""))
    summary = str(payload.get("summary") or "").strip()
    evidence = str(payload.get("evidence") or "").strip()
    if not summary:
        raise QualityHookError("summary is required")
    if not evidence:
        raise QualityHookError("evidence is required")

    pain_score = _coerce_int(payload.get("pain_score"))
    injection_targets = _coerce_str_list(payload.get("injection_targets"))
    if not injection_targets:
        injection_targets = derive_injection_targets(command_name, learning_type)

    capture_payload = capture_learning(
        project_root,
        command_name=command_name,
        learning_type=learning_type,
        summary=summary,
        evidence=evidence,
        recurrence_key=str(payload.get("recurrence_key") or "").strip() or None,
        signal_strength=str(payload.get("signal_strength") or "medium"),
        applies_to=_coerce_str_list(payload.get("applies_to")) or None,
        default_scope=str(payload.get("default_scope") or "").strip() or None,
        confirm=bool(payload.get("confirm") or False),
        pain_score=pain_score,
        false_starts=_coerce_str_list(payload.get("false_starts")),
        rejected_paths=_coerce_str_list(payload.get("rejected_paths")),
        decisive_signal=str(payload.get("decisive_signal") or "").strip(),
        root_cause_family=str(payload.get("root_cause_family") or "").strip(),
        injection_targets=injection_targets,
        promotion_hint=str(payload.get("promotion_hint") or "").strip(),
    )
    return HookResult(
        event=WORKFLOW_LEARNING_CAPTURE,
        status="repaired",
        severity="info",
        actions=[f"captured learning candidate `{capture_payload['entry']['recurrence_key']}`"],
        writes={"learning_candidates": ".planning/learnings/candidates.md"},
        data={"capture": capture_payload, "injection_targets": injection_targets},
    )
