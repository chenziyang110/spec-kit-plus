"""Learning hooks that turn passive self-learning into workflow gates."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from specify_cli.learning_policy import LearningPolicy, LearningPolicyError, load_learning_policy

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
RECENT_SIGNAL_MAX_AGE_SECONDS = 6 * 60 * 60
CANONICAL_REDACTION_LABELS = {
    "credential",
    "email",
    "private_key",
    "machine_path",
    "personal_identifier",
    "business_identifier",
    "organization_sensitive",
}
PAIN_FACTOR_KEYS = {
    "retry_attempts",
    "hypothesis_changes",
    "validation_failures",
    "artifact_rewrites",
    "command_failures",
    "user_corrections",
    "route_changes",
    "scope_changes",
    "false_starts",
    "hidden_dependencies",
    "trigger_signals",
}


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


def _canonical_trigger_signal(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    kind = raw.partition(":")[0]
    return kind.strip().lower().replace("-", "_").replace(" ", "_")


def _canonical_trigger_signals(value: Any) -> list[str]:
    return sorted(
        dict.fromkeys(
            signal
            for signal in (
                _canonical_trigger_signal(item) for item in _coerce_str_list(value)
            )
            if signal
        )
    )


def _sanitize_signal_list(
    value: Any, *, policy: LearningPolicy | None = None
) -> tuple[list[str], list[str]]:
    from specify_cli.learnings import sanitize_agent_text

    sanitized_values: list[str] = []
    labels: set[str] = set()
    for item in _coerce_str_list(value):
        sanitized, item_labels = sanitize_agent_text(item, policy=policy)
        if sanitized.strip():
            sanitized_values.append(sanitized)
        labels.update(item_labels)
    return sanitized_values, sorted(labels)


def _sanitize_signal_text(
    value: Any, *, policy: LearningPolicy | None = None
) -> tuple[str, list[str]]:
    from specify_cli.learnings import sanitize_agent_text

    return sanitize_agent_text(str(value or "").strip(), policy=policy)


def _content_safety(labels: list[str]) -> dict[str, object]:
    canonical_labels = sorted(
        {
            str(label).strip()
            for label in labels
            if str(label).strip() in CANONICAL_REDACTION_LABELS
        }
    )
    return {
        "sensitivity": "sanitized" if canonical_labels else "safe",
        "redaction_labels": canonical_labels,
    }


def _safe_iso_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return (
        parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _is_valid_signal_command_key(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", value))


def _pending_review(payload: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    review = payload.get("learning_review")
    if not isinstance(review, dict):
        return None
    decision = str(review.get("decision") or "").strip().lower()
    rationale = str(review.get("rationale") or "").strip()
    if decision in {"deferred", "manual-capture-needed"} and rationale:
        return review
    return None


def _merge_pending_signal(
    existing: dict[str, object], incoming: dict[str, object]
) -> dict[str, object]:
    existing_safety = existing.get("content_safety")
    incoming_safety = incoming.get("content_safety")
    labels = sorted(
        {
            *_coerce_str_list(
                existing_safety.get("redaction_labels")
                if isinstance(existing_safety, dict)
                else None
            ),
            *_coerce_str_list(
                incoming_safety.get("redaction_labels")
                if isinstance(incoming_safety, dict)
                else None
            ),
        }
    )
    return {
        "command": existing.get("command") or incoming.get("command"),
        "pain_score": max(
            _coerce_int(existing.get("pain_score")),
            _coerce_int(incoming.get("pain_score")),
        ),
        "factors": dict(incoming.get("factors") or existing.get("factors") or {}),
        "false_starts": sorted(
            dict.fromkeys(
                [
                    *_coerce_str_list(existing.get("false_starts")),
                    *_coerce_str_list(incoming.get("false_starts")),
                ]
            )
        ),
        "hidden_dependencies": sorted(
            dict.fromkeys(
                [
                    *_coerce_str_list(existing.get("hidden_dependencies")),
                    *_coerce_str_list(incoming.get("hidden_dependencies")),
                ]
            )
        ),
        "trigger_signals": sorted(
            dict.fromkeys(
                [
                    *_canonical_trigger_signals(existing.get("trigger_signals")),
                    *_canonical_trigger_signals(incoming.get("trigger_signals")),
                ]
            )
        ),
        "content_safety": _content_safety(labels),
        "observed_at": str(existing.get("observed_at") or incoming.get("observed_at")),
        "last_observed_at": str(incoming.get("observed_at") or _now_iso()),
        "learning_review": existing.get("learning_review"),
    }


def _now_iso() -> str:
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _signal_state_path(project_root: Path) -> Path:
    return project_root / ".planning" / "learnings" / "signal-state.json"


def _sanitize_signal_payload(
    command_name: str,
    payload: dict[str, object],
    *,
    policy: LearningPolicy | None = None,
) -> dict[str, object]:
    false_starts, false_start_labels = _sanitize_signal_list(
        payload.get("false_starts"), policy=policy
    )
    hidden_dependencies, dependency_labels = _sanitize_signal_list(
        payload.get("hidden_dependencies"), policy=policy
    )
    existing_safety = payload.get("content_safety")
    existing_labels = (
        _coerce_str_list(existing_safety.get("redaction_labels"))
        if isinstance(existing_safety, dict)
        else []
    )
    labels = sorted({*false_start_labels, *dependency_labels, *existing_labels})
    sanitized: dict[str, object] = {
        "command": f"sp-{command_name}",
        "pain_score": _coerce_int(payload.get("pain_score")),
        "factors": (
            {
                str(key): _coerce_int(value)
                for key, value in (payload.get("factors") or {}).items()
                if str(key) in PAIN_FACTOR_KEYS
            }
            if isinstance(payload.get("factors"), dict)
            else {}
        ),
        "false_starts": false_starts,
        "hidden_dependencies": hidden_dependencies,
        "trigger_signals": _canonical_trigger_signals(payload.get("trigger_signals")),
        "content_safety": _content_safety(labels),
        "observed_at": _safe_iso_timestamp(payload.get("observed_at")),
    }
    review = payload.get("learning_review")
    if isinstance(review, dict):
        rationale, rationale_labels = _sanitize_signal_text(
            review.get("rationale"), policy=policy
        )
        labels = sorted({*labels, *rationale_labels})
        decision = str(review.get("decision") or "").strip().lower()
        if decision in LEARNING_REVIEW_DECISIONS:
            sanitized["learning_review"] = {
                "decision": decision,
                "rationale": rationale,
                "deferred_at": _safe_iso_timestamp(review.get("deferred_at")),
            }
            sanitized["content_safety"] = _content_safety(labels)
    return sanitized


def _load_signal_state(
    project_root: Path, *, policy: LearningPolicy | None = None
) -> dict[str, dict[str, object]]:
    path = _signal_state_path(project_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    state: dict[str, dict[str, object]] = {}
    changed = False
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            changed = True
            continue
        try:
            command_name = normalize_command_name(key)
        except QualityHookError:
            changed = True
            continue
        if not _is_valid_signal_command_key(command_name):
            changed = True
            continue
        sanitized = _sanitize_signal_payload(command_name, value, policy=policy)
        state[command_name] = sanitized
        if command_name != key or sanitized != value:
            changed = True
    if changed:
        _write_signal_state(project_root, state)
    return state


def _write_signal_state(
    project_root: Path, state: dict[str, dict[str, object]]
) -> None:
    path = _signal_state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _record_recent_signal(
    project_root: Path,
    *,
    command_name: str,
    payload: dict[str, object],
    policy: LearningPolicy | None = None,
) -> None:
    state = _load_signal_state(project_root, policy=policy)
    state[command_name] = payload
    _write_signal_state(project_root, state)


def _clear_recent_signal(
    project_root: Path, *, command_name: str, policy: LearningPolicy | None = None
) -> None:
    state = _load_signal_state(project_root, policy=policy)
    if command_name not in state:
        return
    del state[command_name]
    _write_signal_state(project_root, state)


def _recent_signal_for_command(
    project_root: Path,
    *,
    command_name: str,
    policy: LearningPolicy | None = None,
) -> dict[str, object] | None:
    state = _load_signal_state(project_root, policy=policy)
    payload = state.get(command_name)
    if not isinstance(payload, dict):
        return None
    observed_at = str(payload.get("observed_at") or "").strip()
    if not observed_at:
        return payload
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return payload
    age_seconds = (datetime.now(tz=UTC) - observed).total_seconds()
    review = payload.get("learning_review")
    if isinstance(review, dict):
        decision = str(review.get("decision") or "").strip().lower()
        rationale = str(review.get("rationale") or "").strip()
        if decision in {"deferred", "manual-capture-needed"} and rationale:
            return payload
    if age_seconds <= RECENT_SIGNAL_MAX_AGE_SECONDS:
        return payload
    del state[command_name]
    _write_signal_state(project_root, state)
    return None


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
        "hidden_dependencies": len(
            _coerce_str_list(payload.get("hidden_dependencies"))
        ),
        # An explicit semantic trigger is already a review-worthy event. The
        # numeric counters above still catch accumulated friction when no
        # workflow state has classified the signal yet.
        "trigger_signals": len(_coerce_str_list(payload.get("trigger_signals")))
        * PAIN_THRESHOLD,
    }
    return sum(factors.values()), factors


def derive_injection_targets(command_name: str, learning_type: str) -> list[str]:
    from specify_cli.learnings import normalize_learning_type

    command = _sp_command(command_name)
    normalized_type = normalize_learning_type(learning_type)
    targets_by_type = {
        "routing_mistake": [
            "spec-kit-workflow-routing",
            "sp-fast",
            "sp-quick",
            "sp-specify",
        ],
        "verification_gap": [
            "sp-implement",
            "sp-accept",
            "sp-debug",
            "sp-quick",
        ],
        "state_surface_gap": [
            "workflow-state.md",
            "implement-tracker.md",
            "STATUS.md",
            "sp-implement",
            "sp-accept",
            "sp-quick",
        ],
        "map_coverage_gap": [
            "sp-map-scan",
            "sp-map-build",
            "PROJECT-HANDBOOK.md",
            ".specify/project-map/",
        ],
        "tooling_trap": ["sp-debug", "sp-implement", "sp-map-scan", "sp-map-build"],
        "false_lead_pattern": ["sp-debug", "sp-implement"],
        "near_miss": ["sp-implement", "sp-debug", "project-rules"],
        "decision_debt": [
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            "ADR",
        ],
        "workflow_gap": ["sp-specify", "sp-deep-research", "sp-plan", "sp-tasks"],
        "project_constraint": ["project-rules", "confirmed-learning", command],
        "recovery_path": ["sp-debug", "sp-implement", "sp-quick"],
        "pitfall": ["sp-debug", "sp-implement", "sp-quick"],
        "user_preference": ["project-rules", "AGENTS.md", command],
    }
    return sorted(dict.fromkeys([command, *targets_by_type.get(normalized_type, [])]))


def learning_signal_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    score, factors = _pain_score(payload)
    try:
        policy_result = load_learning_policy(
            project_root, for_write=score >= PAIN_THRESHOLD
        )
    except LearningPolicyError as exc:
        raise QualityHookError(
            "Project Learning policy is invalid; signal write was rejected"
        ) from exc
    policy = policy_result.policy
    false_starts, false_start_labels = _sanitize_signal_list(
        payload.get("false_starts"), policy=policy
    )
    hidden_dependencies, dependency_labels = _sanitize_signal_list(
        payload.get("hidden_dependencies"), policy=policy
    )
    redaction_labels = sorted({*false_start_labels, *dependency_labels})
    trigger_signals = _canonical_trigger_signals(payload.get("trigger_signals"))
    data = {
        "command": f"sp-{command_name}",
        "pain_score": score,
        "factors": factors,
        "threshold": PAIN_THRESHOLD,
        "false_starts": false_starts,
        "hidden_dependencies": hidden_dependencies,
        "trigger_signals": trigger_signals,
        "content_safety": _content_safety(redaction_labels),
    }
    if score < PAIN_THRESHOLD:
        return HookResult(
            event=WORKFLOW_LEARNING_SIGNAL,
            status="ok",
            severity="info",
            warnings=list(policy_result.warnings),
            data=data,
        )
    signal_payload = {
        "command": f"sp-{command_name}",
        "pain_score": score,
        "factors": factors,
        "false_starts": false_starts,
        "hidden_dependencies": hidden_dependencies,
        "trigger_signals": trigger_signals,
        "content_safety": _content_safety(redaction_labels),
        "observed_at": _now_iso(),
    }
    existing_signal = _recent_signal_for_command(
        project_root, command_name=command_name, policy=policy
    )
    if _pending_review(existing_signal):
        signal_payload = _merge_pending_signal(existing_signal, signal_payload)
    _record_recent_signal(
        project_root,
        command_name=command_name,
        payload=signal_payload,
        policy=policy,
    )
    return HookResult(
        event=WORKFLOW_LEARNING_SIGNAL,
        status="warn",
        severity="warning",
        actions=[
            f"before terminal reporting, record a learning review decision for `sp-{command_name}`: `none`, `captured`, or `deferred`",
            "if the signal would change a future Agent's action, capture it through `specify-runtime learning capture-auto` or `specify-runtime learning capture`; do not edit Learning storage directly",
        ],
        warnings=[
            f"learning pain score {score} crossed threshold {PAIN_THRESHOLD}; this workflow has reusable-learning signal"
        ],
        data=data,
    )


def _entry_seen_after_signal(entry_last_seen: str, observed_at: str) -> bool:
    if not observed_at:
        return True
    try:
        entry_seen = datetime.fromisoformat(entry_last_seen.replace("Z", "+00:00"))
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return entry_seen >= observed


def _has_matching_durable_capture(
    project_root: Path,
    *,
    command_name: str,
    recent_signal: dict[str, object],
) -> bool:
    from specify_cli.learnings import (
        build_learning_paths,
        is_relevant_to_command,
        read_learning_entries,
    )

    paths = build_learning_paths(project_root)
    entries = []
    for path in (paths.candidates, paths.confirmed_learnings, paths.project_rules):
        if path.exists():
            entries.extend(read_learning_entries(path)[1])
    observed_at = str(recent_signal.get("observed_at") or "").strip()
    required_signals = set(_canonical_trigger_signals(recent_signal.get("trigger_signals")))
    for entry in entries:
        if not is_relevant_to_command(entry, f"sp-{command_name}"):
            continue
        if not _entry_seen_after_signal(entry.last_seen, observed_at):
            continue
        entry_signals = set(_canonical_trigger_signals(entry.trigger_signals))
        if required_signals and not required_signals.intersection(entry_signals):
            continue
        return True
    return False


def learning_review_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    from specify_cli.learnings import learning_review_status, review_learning

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

    try:
        policy = load_learning_policy(_project_root, for_write=True).policy
    except LearningPolicyError as exc:
        raise QualityHookError(
            "Project Learning policy is invalid; review write was rejected"
        ) from exc

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
                f"record a learning review decision for `sp-{command_name}` with status `{terminal_status}` before terminal reporting",
                "when no reusable learning exists, record decision `none`",
                "when this run exposed reusable friction, capture it through `specify-runtime learning capture-auto` or `specify-runtime learning capture`; do not edit Learning storage directly",
            ],
            data={"command": f"sp-{command_name}", "terminal_status": terminal_status},
        )

    decision = str(raw_review.get("decision") or "").strip().lower()
    if decision not in LEARNING_REVIEW_DECISIONS:
        safe_decision, decision_labels = _sanitize_signal_text(
            raw_review.get("decision"), policy=policy
        )
        return HookResult(
            event=WORKFLOW_LEARNING_REVIEW,
            status="blocked",
            severity="critical",
            errors=[
                "learning review decision must be one of: "
                + ", ".join(sorted(LEARNING_REVIEW_DECISIONS))
            ],
            data={
                "command": f"sp-{command_name}",
                "terminal_status": terminal_status,
                "review": {"decision": safe_decision, "rationale": ""},
                "content_safety": _content_safety(decision_labels),
            },
        )
    rationale, rationale_labels = _sanitize_signal_text(
        raw_review.get("rationale"), policy=policy
    )
    safe_review = {"decision": decision, "rationale": rationale}
    if decision in {"deferred", "manual-capture-needed"} and not rationale:
        return HookResult(
            event=WORKFLOW_LEARNING_REVIEW,
            status="blocked",
            severity="critical",
            errors=[f"learning review decision `{decision}` requires a rationale"],
            data={
                "command": f"sp-{command_name}",
                "terminal_status": terminal_status,
                "review": safe_review,
                "content_safety": _content_safety(rationale_labels),
            },
        )
    if decision == "none":
        recent_signal = _recent_signal_for_command(
            _project_root, command_name=command_name, policy=policy
        )
        if recent_signal is not None:
            return HookResult(
                event=WORKFLOW_LEARNING_REVIEW,
                status="blocked",
                severity="critical",
                errors=[
                    "recent friction signal indicates reusable learning value; `decision=none` is not allowed until the learning is captured or explicitly deferred"
                ],
                actions=[
                    "preserve the reusable lesson through `specify-runtime learning capture-auto` or `specify-runtime learning capture`; do not edit Learning storage directly",
                    f"or record a deferred learning review for `sp-{command_name}` with status `{terminal_status}` and rationale `capture deferred` when capture must wait",
                ],
                data={
                    "command": f"sp-{command_name}",
                    "terminal_status": terminal_status,
                    "review": safe_review,
                    "recent_signal": recent_signal,
                    "content_safety": _content_safety(rationale_labels),
                },
            )

    recent_signal = _recent_signal_for_command(
        _project_root, command_name=command_name, policy=policy
    )
    if decision == "none":
        try:
            review_learning(
                _project_root,
                command_name=command_name,
                decision=decision,
                rationale=rationale,
            )
        except ValueError:
            return HookResult(
                event=WORKFLOW_LEARNING_REVIEW,
                status="blocked",
                severity="critical",
                errors=[
                    "pending Project Learning review cannot be closed with decision `none`"
                ],
                data={
                    "command": f"sp-{command_name}",
                    "terminal_status": terminal_status,
                    "review": safe_review,
                    "content_safety": _content_safety(rationale_labels),
                },
            )
    if decision in {"deferred", "manual-capture-needed"}:
        try:
            review_learning(
                _project_root,
                command_name=command_name,
                decision=decision,
                rationale=rationale,
                recurrence_key=str(raw_review.get("recurrence_key") or ""),
            )
        except ValueError:
            return HookResult(
                event=WORKFLOW_LEARNING_REVIEW,
                status="blocked",
                severity="critical",
                errors=["Project Learning review could not be persisted safely"],
                data={
                    "command": f"sp-{command_name}",
                    "terminal_status": terminal_status,
                    "review": safe_review,
                    "content_safety": _content_safety(rationale_labels),
                },
            )
    elif decision in {"captured", "auto-captured"}:
        capture_signal = recent_signal or {
            "observed_at": "",
            "trigger_signals": [],
        }
        if not _has_matching_durable_capture(
            _project_root, command_name=command_name, recent_signal=capture_signal
        ):
            return HookResult(
                event=WORKFLOW_LEARNING_REVIEW,
                status="blocked",
                severity="critical",
                errors=[
                    "learning review claimed capture, but no matching durable candidate, confirmed learning, or project rule was found after the recent signal"
                ],
                actions=[
                    "capture the matching reusable lesson through `specify-runtime learning capture-auto` or `specify-runtime learning capture` before terminal closeout",
                    f"then record a captured learning review for `sp-{command_name}`",
                ],
                data={
                    "command": f"sp-{command_name}",
                    "terminal_status": terminal_status,
                    "review": safe_review,
                    "recent_signal": capture_signal,
                    "content_safety": _content_safety(rationale_labels),
                },
            )
        review_status = learning_review_status(
            _project_root, command_name=command_name
        )
        if review_status["pending"]:
            try:
                review_learning(
                    _project_root,
                    command_name=command_name,
                    decision=decision,
                    rationale=rationale,
                    recurrence_key=str(raw_review.get("recurrence_key") or ""),
                )
            except ValueError:
                return HookResult(
                    event=WORKFLOW_LEARNING_REVIEW,
                    status="blocked",
                    severity="critical",
                    errors=[
                        "captured Project Learning did not match the pending review"
                    ],
                    data={
                        "command": f"sp-{command_name}",
                        "terminal_status": terminal_status,
                        "review": safe_review,
                        "content_safety": _content_safety(rationale_labels),
                    },
                )
        _clear_recent_signal(
            _project_root, command_name=command_name, policy=policy
        )

    return HookResult(
        event=WORKFLOW_LEARNING_REVIEW,
        status="ok",
        severity="info",
        data={
            "command": f"sp-{command_name}",
            "terminal_status": terminal_status,
            "review": safe_review,
            "content_safety": _content_safety(rationale_labels),
        },
    )


def learning_inject_hook(_project_root: Path, payload: dict[str, object]) -> HookResult:
    from specify_cli.learnings import normalize_learning_type

    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    learning_type = normalize_learning_type(str(payload.get("learning_type") or ""))
    policy_result = load_learning_policy(_project_root, for_write=False)
    summary, summary_labels = _sanitize_signal_text(
        payload.get("summary"), policy=policy_result.policy
    )
    targets = derive_injection_targets(command_name, learning_type)
    return HookResult(
        event=WORKFLOW_LEARNING_INJECT,
        status="ok",
        severity="info",
        warnings=list(policy_result.warnings),
        actions=[f"route future prevention through: {', '.join(targets)}"],
        data={
            "command": f"sp-{command_name}",
            "learning_type": learning_type,
            "summary": summary,
            "injection_targets": targets,
            "content_safety": _content_safety(summary_labels),
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

    try:
        capture_payload = capture_learning(
            project_root,
            command_name=command_name,
            learning_type=learning_type,
            summary=summary,
            evidence=evidence,
            recurrence_key=str(payload.get("recurrence_key") or "").strip()
            or None,
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
            problem=str(payload.get("problem") or "").strip() or None,
            recommended_action=str(payload.get("recommended_action") or "").strip()
            or None,
            avoid=_coerce_str_list(payload.get("avoid")),
            trigger_signals=_coerce_str_list(payload.get("trigger_signals")),
            success_criteria=_coerce_str_list(payload.get("success_criteria")),
            exceptions=_coerce_str_list(payload.get("exceptions")),
        )
    except LearningPolicyError as exc:
        raise QualityHookError(
            "Project Learning policy is invalid; capture was rejected"
        ) from exc
    if capture_payload["status"] == "deferred":
        return HookResult(
            event=WORKFLOW_LEARNING_CAPTURE,
            status="warn",
            severity="warning",
            actions=[
                "review the deferred Learning after a safe reusable abstraction is available"
            ],
            writes={"learning_review": ".planning/learnings/review-state.json"},
            data={
                "capture": capture_payload,
                "injection_targets": capture_payload["entry"][
                    "injection_targets"
                ],
            },
        )
    return HookResult(
        event=WORKFLOW_LEARNING_CAPTURE,
        status="repaired",
        severity="info",
        actions=[
            f"captured learning candidate `{capture_payload['entry']['recurrence_key']}`"
        ],
        writes={"learning_candidates": ".planning/learnings/candidates.md"},
        data={
            "capture": capture_payload,
            "injection_targets": capture_payload["entry"]["injection_targets"],
        },
    )
