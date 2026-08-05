from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping
import yaml

from specify_cli.atomic_io import atomic_write_text, interprocess_lock
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.hooks.checkpoint_serializers import (
    parse_frontmatter,
    serialize_workflow_state,
)
from specify_cli.verification import summarize_validation_results
from specify_cli.learning_assessment import (
    ASSESSMENT_VERSION,
    ASSESSMENT_DECISIONS,
    LEARNING_VALUE_TIERS,
    VALUE_REASON_CODES,
    assess_learning,
    assessment_payload_from_flat,
    sanitize_learning_text,
)
from specify_cli.learning_policy import (
    LearningPolicy,
    default_learning_policy,
    learning_policy_digest,
    load_learning_policy,
)


LEARNING_TYPES = {
    "pitfall",
    "recovery_path",
    "user_preference",
    "workflow_gap",
    "project_constraint",
    "routing_mistake",
    "verification_gap",
    "state_surface_gap",
    "map_coverage_gap",
    "tooling_trap",
    "false_lead_pattern",
    "near_miss",
    "decision_debt",
}
LEARNING_STATUSES = {
    "candidate",
    "confirmed",
    "promoted-rule",
}
SIGNAL_STRENGTHS = {"low", "medium", "high"}
PROMOTION_TARGETS = {"learning", "rule"}
LEARNING_FACET_KEYS = (
    "components",
    "operation_owners",
    "consumer_owners",
    "outcomes",
    "states",
    "entrypoints",
    "validation_surfaces",
)
LEARNING_CONTEXT_KEY_MAP = {
    "component": "components",
    "operation_owner": "operation_owners",
    "consumer_owner": "consumer_owners",
    "outcome": "outcomes",
    "state": "states",
    "entrypoint": "entrypoints",
    "validation_surface": "validation_surfaces",
}
LEARNING_CONTEXT_ARG_KEYS = {
    value: key for key, value in LEARNING_CONTEXT_KEY_MAP.items()
}
SENSITIVITY_SAFE = "safe"
SENSITIVITY_SANITIZED = "sanitized"
SENSITIVITY_VALUES = {SENSITIVITY_SAFE, SENSITIVITY_SANITIZED}
CANONICAL_REDACTION_LABELS = {
    "credential",
    "email",
    "private_key",
    "machine_path",
    "personal_identifier",
    "business_identifier",
    "organization_sensitive",
}
MAX_LEARNING_CONTEXT_VALUES = 64
MAX_LEARNING_CONTEXT_VALUE_LENGTH = 256
MAP_WORKFLOW_COMMANDS = (
    "sp-map-scan",
    "sp-map-build",
    "sp-map-update",
    "sp-map-rebuild",
)
KNOWN_COMMANDS = (
    "sp-accept",
    "sp-analyze",
    "sp-ask",
    "sp-auto",
    "sp-checklist",
    "sp-clarify",
    "sp-constitution",
    "sp-debug",
    "sp-deep-research",
    "sp-design",
    "sp-discussion",
    "sp-explain",
    "sp-fast",
    "sp-implement",
    "sp-implement-teams",
    "sp-integrate",
    *MAP_WORKFLOW_COMMANDS,
    "sp-plan",
    "sp-prd",
    "sp-prd-build",
    "sp-prd-scan",
    "sp-quick",
    "sp-specify",
    "sp-tasks",
    "sp-taskstoissues",
    "sp-team",
)
COMMAND_ALIASES = {
    "sp-research": "sp-deep-research",
}

# Consumption is always read-only. Capture policy tells workflow prompts whether
# closeout may write a candidate directly, must defer capture to an owning
# workflow, or should skip learning entirely for a deliberately trivial path.
LEARNING_WORKFLOW_POLICIES = {command: "consume-capture" for command in KNOWN_COMMANDS}
LEARNING_WORKFLOW_POLICIES.update(
    {
        "sp-accept": "consume-only",
        "sp-analyze": "consume-only",
        "sp-ask": "consume-only",
        "sp-auto": "consume-only",
        "sp-constitution": "consume-only",
        "sp-explain": "consume-only",
        "sp-fast": "skip",
        "sp-implement-teams": "consume-only",
        "sp-taskstoissues": "consume-only",
        "sp-team": "consume-only",
    }
)

MACHINE_BEGIN = "<!-- SPECKIT_LEARNING_DATA_BEGIN -->"
MACHINE_END = "<!-- SPECKIT_LEARNING_DATA_END -->"

RULES_TEMPLATE_TEXT = (
    "# Project Rules\n\n"
    "Shared defaults that later `sp-xxx` workflows should follow across specification,\n"
    "planning, implementation, debugging, and quick-task execution.\n\n"
    "Promote only stable project rules through `specify-runtime learning promote --target rule`.\n"
    "Keep one-off observations as CLI-managed candidates until recurrence or explicit\n"
    "confirmation proves they belong in this shared rule layer.\n\n"
    "---\n"
)
CONFIRMED_LEARNINGS_TEMPLATE_TEXT = (
    "# Confirmed Project Learning\n\n"
    "Runtime-maintained confirmed Learning behind `specify-runtime learning start`, `list`,\n"
    "and `show`. Agents should use those CLI surfaces instead of parsing this file.\n\n"
    "---\n"
)
LEARNING_INDEX_TEMPLATE_TEXT = (
    "# Project Learning Index\n\n"
    "Runtime-maintained compact index behind `specify-runtime learning start` and\n"
    "`specify-runtime learning list`. Agents should use those CLI surfaces and expand one\n"
    "selected record with `specify-runtime learning show`; do not parse this file directly\n"
    "during normal workflow execution.\n\n"
    "---\n\n"
    f"{MACHINE_BEGIN}\n[]\n{MACHINE_END}\n\n"
    "## Managed Entries\n\n"
    "_No learning index entries recorded yet._\n"
)
CANDIDATES_TEMPLATE_TEXT = (
    "# Candidate Learnings\n\n"
    "Passive candidate learnings captured from `sp-xxx` workflows.\n\n"
    "---\n"
)
REVIEW_TEMPLATE_TEXT = (
    "# Learning Review\n\n"
    "Pending recurrence, confirmation, and promotion notes for passive project learning.\n\n"
    "---\n"
)


def _facet_match_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().replace("\\", "/")).casefold()


def _normalize_facet_values(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values: Iterable[Any] = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        return []
    by_token: dict[str, str] = {}
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            continue
        display = re.sub(r"\s+", " ", raw_value.strip().replace("\\", "/"))
        token = _facet_match_token(display)
        if token and token not in by_token:
            by_token[token] = display
    return [by_token[token] for token in sorted(by_token)]


def normalize_learning_facets(value: Any) -> dict[str, list[str]]:
    """Normalize optional sparse Learning facets without rejecting legacy rows."""

    if not isinstance(value, Mapping):
        return {}
    facets: dict[str, list[str]] = {}
    for key in LEARNING_FACET_KEYS:
        values = _normalize_facet_values(value.get(key))
        if values:
            facets[key] = values
    return facets


def _learning_facet_payload_warnings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Mapping):
        return ["facets must be an object; ignored optional facets"]
    warnings: list[str] = []
    for key, raw_values in value.items():
        if key not in LEARNING_FACET_KEYS:
            warnings.append(f"unknown optional facet '{key}' was ignored")
            continue
        values = [raw_values] if isinstance(raw_values, str) else raw_values
        if not isinstance(values, (list, tuple, set)) or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            warnings.append(f"malformed optional facet '{key}' was partially ignored")
    return warnings


def parse_learning_task_context(values: Iterable[str] | None) -> dict[str, list[str]]:
    """Parse repeatable ``--context key=value`` CLI values into canonical facets."""

    if not values:
        return {}
    parsed: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    count = 0
    for raw_item in values:
        item = str(raw_item or "").strip()
        if "=" not in item:
            raise ValueError("learning context must use key=value")
        raw_key, raw_value = item.split("=", 1)
        key = raw_key.strip().casefold().replace("-", "_")
        facet_key = LEARNING_CONTEXT_KEY_MAP.get(key)
        if facet_key is None:
            raise ValueError(f"unknown context facet '{raw_key.strip()}'")
        value = re.sub(r"\s+", " ", raw_value.strip().replace("\\", "/"))
        if not value:
            raise ValueError(f"context facet '{key}' requires a non-empty value")
        if len(value) > MAX_LEARNING_CONTEXT_VALUE_LENGTH:
            raise ValueError(
                f"context facet '{key}' exceeds {MAX_LEARNING_CONTEXT_VALUE_LENGTH} characters"
            )
        identity = (facet_key, _facet_match_token(value))
        if identity in seen:
            raise ValueError(f"duplicate context facet value '{key}={value}'")
        seen.add(identity)
        parsed.setdefault(facet_key, []).append(value)
        count += 1
        if count > MAX_LEARNING_CONTEXT_VALUES:
            raise ValueError(
                f"learning context accepts at most {MAX_LEARNING_CONTEXT_VALUES} values"
            )
    return normalize_learning_facets(parsed)


def _merge_learning_facets(
    current: Mapping[str, Iterable[str]] | None,
    incoming: Mapping[str, Iterable[str]] | None,
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    current_facets = normalize_learning_facets(current)
    incoming_facets = normalize_learning_facets(incoming)
    for key in LEARNING_FACET_KEYS:
        values = _normalize_facet_values(
            [*current_facets.get(key, []), *incoming_facets.get(key, [])]
        )
        if values:
            merged[key] = values
    return merged


def _sanitize_learning_facets(
    value: Mapping[str, Iterable[str]] | None,
    *,
    policy: LearningPolicy | None = None,
) -> dict[str, list[str]]:
    normalized = normalize_learning_facets(value)
    sanitized: dict[str, list[str]] = {}
    for key, values in normalized.items():
        sanitized_values, _labels = _sanitize_list_with_labels(values, policy=policy)
        if sanitized_values:
            sanitized[key] = sanitized_values
    return normalize_learning_facets(sanitized)


def _learning_context_argv(facets: Mapping[str, Iterable[str]]) -> list[str]:
    args: list[str] = []
    normalized = normalize_learning_facets(facets)
    for facet_key in LEARNING_FACET_KEYS:
        arg_key = LEARNING_CONTEXT_ARG_KEYS[facet_key]
        for value in normalized.get(facet_key, []):
            args.extend(["--context", f"{arg_key}={value}"])
    return args


def _redact_machine_path(match: re.Match[str]) -> str:
    path = match.group(0).replace("\\", "/")
    if path.endswith("/"):
        path = path[:-1]
    parts = path.split("/")
    if len(parts) > 1 and parts[1].casefold() == "root":
        if len(parts) <= 2:
            return "<USER_HOME>"
        return "<USER_HOME>/" + "/".join(parts[2:])
    if len(parts) <= 3:
        return "<USER_HOME>"
    return "<USER_HOME>/" + "/".join(parts[3:])


REDACTION_PATTERNS: tuple[tuple[str, re.Pattern[str], str | Any], ...] = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        "credential",
        re.compile(r"\b(?:https?://)[^\s/@:]+:[^\s/@]+@", re.IGNORECASE),
        lambda match: match.group(0).split("://", 1)[0] + "://[REDACTED_SECRET]@",
    ),
    (
        "credential",
        re.compile(
            r"\bAuthorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]+",
            re.IGNORECASE,
        ),
        "Authorization: [REDACTED_SECRET]",
    ),
    (
        "credential",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
        "[REDACTED_SECRET]",
    ),
    (
        "credential",
        re.compile(
            r"(?P<key>[\"']?(?:secret|password|token|api[_-]?key|authorization)[\"']?\s*[:=]\s*)(?P<quote>[\"']?)(?P<value>(?!\[REDACTED_)[^\"'\s,;}]+)(?P=quote)",
            re.IGNORECASE,
        ),
        lambda match: (
            f"{match.group('key')}{match.group('quote')}[REDACTED_SECRET]{match.group('quote')}"
        ),
    ),
    (
        "credential",
        re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b"),
        "[REDACTED_SECRET]",
    ),
    (
        "credential",
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
        "[REDACTED_SECRET]",
    ),
    (
        "credential",
        re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
        "[REDACTED_SECRET]",
    ),
    (
        "credential",
        re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "[REDACTED_SECRET]",
    ),
    (
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        "[REDACTED_EMAIL]",
    ),
    (
        "machine_path",
        re.compile(
            r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+(?:[\\/]+[^\s,;:]+)*|/(?:home|Users)/[^/\s]+(?:/[^\s,;:]+)*|/root(?:/[^\s,;:]+)+|/root(?=$|[\s,;:]))"
        ),
        _redact_machine_path,
    ),
)


def _sanitize_p0_agent_text(value: str) -> tuple[str, list[str]]:
    sanitized = str(value or "")
    labels: set[str] = set()
    if "[REDACTED_SECRET]" in sanitized:
        labels.add("credential")
    if "[REDACTED_EMAIL]" in sanitized:
        labels.add("email")
    if "[REDACTED_PRIVATE_KEY]" in sanitized:
        labels.add("private_key")
    if "<USER_HOME>" in sanitized:
        labels.add("machine_path")
    for label, pattern, replacement in REDACTION_PATTERNS:
        sanitized, count = pattern.subn(replacement, sanitized)
        if count:
            labels.add(label)
    return sanitized, sorted(labels)


def sanitize_agent_text(
    value: str, *, policy: LearningPolicy | None = None
) -> tuple[str, list[str]]:
    return sanitize_learning_text(
        value,
        policy=policy or default_learning_policy(),
        base_sanitizer=_sanitize_p0_agent_text,
    )


def assess_learning_candidate(
    *,
    source: str,
    learning_type: str,
    signal_strength: str,
    occurrences: int,
    summary: str,
    evidence: str,
    recommended_action: str,
    trigger_signals: Iterable[str] = (),
    policy: LearningPolicy | None = None,
):
    """Assess one Learning using the same deterministic Python compatibility rules."""

    return assess_learning(
        source=source,
        learning_type=learning_type,
        signal_strength=signal_strength,
        occurrences=occurrences,
        summary=summary,
        evidence=evidence,
        recommended_action=recommended_action,
        trigger_signals=trigger_signals,
        policy=policy or default_learning_policy(),
        base_sanitizer=_sanitize_p0_agent_text,
    )


def _sanitize_text(value: str) -> str:
    return sanitize_agent_text(value)[0]


def _sanitize_list(values: Iterable[str]) -> list[str]:
    return [
        sanitized
        for sanitized in (_sanitize_text(str(item).strip()) for item in values)
        if sanitized.strip()
    ]


def _sanitize_list_with_labels(
    values: Iterable[str], *, policy: LearningPolicy | None = None
) -> tuple[list[str], list[str]]:
    sanitized_values: list[str] = []
    label_groups: list[list[str]] = []
    for item in values:
        sanitized, labels = sanitize_agent_text(str(item).strip(), policy=policy)
        label_groups.append(labels)
        if sanitized.strip():
            sanitized_values.append(sanitized)
    return sanitized_values, _merge_redaction_labels(*label_groups)


def _merge_redaction_labels(*label_groups: Iterable[str]) -> list[str]:
    labels = {
        str(label).strip()
        for group in label_groups
        for label in group
        if str(label).strip() in CANONICAL_REDACTION_LABELS
    }
    return sorted(labels)


def _canonicalize_recurrence_key(
    value: str, *, policy: LearningPolicy | None = None
) -> tuple[str, list[str]]:
    active_policy = policy or default_learning_policy()
    sanitized, labels = sanitize_agent_text(
        str(value or "").strip().lower(), policy=active_policy
    )
    label_set = set(labels)
    for term in active_policy.detectors.sensitive_terms:
        slug = _slugify(term)
        sanitized, count = re.subn(
            rf"(?i)(?<![a-z0-9]){re.escape(slug)}(?![a-z0-9])",
            "[REDACTED_ORG_TERM]",
            sanitized,
        )
        if count:
            label_set.add("organization_sensitive")
    canonical = (
        sanitized.replace("[REDACTED_SECRET]", "redacted-secret")
        .replace("[REDACTED_EMAIL]", "redacted-email")
        .replace("[REDACTED_PRIVATE_KEY]", "redacted-private-key")
        .replace("[REDACTED_PHONE]", "redacted-phone")
        .replace("[REDACTED_BUSINESS_ID]", "redacted-business-id")
        .replace("[REDACTED_ORG_TERM]", "redacted-org-term")
        .replace("<USER_HOME>", "user-home")
        .replace("\\", "/")
    )
    canonical = re.sub(r"[^a-z0-9._/-]+", "-", canonical)
    canonical = canonical.replace("/", "-")
    canonical = re.sub(r"-+", "-", canonical).strip(".-")
    return canonical, sorted(label_set)


def _safe_index_timestamp(value: Any) -> tuple[str, list[str]]:
    sanitized, labels = sanitize_agent_text(str(value or "").strip())
    try:
        parsed = datetime.fromisoformat(sanitized.replace("Z", "+00:00"))
    except ValueError:
        return "1970-01-01T00:00:00Z", labels
    if parsed.tzinfo is None:
        return "1970-01-01T00:00:00Z", labels
    normalized = (
        parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return normalized, labels


def _safe_learning_index_id(value: Any) -> tuple[str, list[str]]:
    sanitized, labels = sanitize_agent_text(str(value or "").strip().lower())
    if not sanitized.startswith("learn-"):
        return "", labels
    suffix = sanitized.removeprefix("learn-")
    safe_suffix = _slugify(suffix)
    return f"learn-{safe_suffix}", labels


@dataclass(frozen=True)
class LearningPaths:
    constitution: Path
    project_rules: Path
    confirmed_learnings: Path
    learning_index: Path
    learning_detail_template: Path
    candidates: Path
    review: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "constitution": str(self.constitution),
            "project_rules": str(self.project_rules),
            "confirmed_learnings": str(self.confirmed_learnings),
            "learning_index": str(self.learning_index),
            "learning_detail_template": str(self.learning_detail_template),
            "candidates": str(self.candidates),
            "review": str(self.review),
        }


@dataclass
class LearningEntry:
    id: str
    summary: str
    learning_type: str
    source_command: str
    evidence: str
    recurrence_key: str
    default_scope: str
    applies_to: list[str]
    signal_strength: str
    status: str
    first_seen: str
    last_seen: str
    occurrence_count: int = 1
    pain_score: int = 0
    false_starts: list[str] = field(default_factory=list)
    rejected_paths: list[str] = field(default_factory=list)
    decisive_signal: str = ""
    root_cause_family: str = ""
    injection_targets: list[str] = field(default_factory=list)
    promotion_hint: str = ""
    problem: str = ""
    recommended_action: str = ""
    avoid: list[str] = field(default_factory=list)
    trigger_signals: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    facets: dict[str, list[str]] = field(default_factory=dict)
    sensitivity: str = SENSITIVITY_SAFE
    redaction_labels: list[str] = field(default_factory=list)
    learning_value_tier: str = ""
    learning_value_reason_codes: list[str] = field(default_factory=list)
    sensitivity_risk_tier: str = ""
    assessment_decision: str = ""
    assessment_reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        if not self.facets:
            payload.pop("facets", None)
        if not self.learning_value_tier:
            for key in (
                "learning_value_tier",
                "learning_value_reason_codes",
                "sensitivity_risk_tier",
                "assessment_decision",
                "assessment_reason",
            ):
                payload.pop(key, None)
        return payload

    def assessment_payload(self) -> dict[str, object] | None:
        return assessment_payload_from_flat(
            learning_value_tier=self.learning_value_tier,
            learning_value_reason_codes=self.learning_value_reason_codes,
            sensitivity=self.sensitivity,
            sensitivity_risk_tier=self.sensitivity_risk_tier,
            redaction_labels=self.redaction_labels,
            assessment_decision=self.assessment_decision,
            assessment_reason=self.assessment_reason,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LearningEntry":
        applies_to = payload.get("applies_to") or []
        if not isinstance(applies_to, list):
            applies_to = []
        sanitized_fields: dict[str, str] = {}
        label_groups: list[list[str]] = []
        for key in (
            "id",
            "summary",
            "learning_type",
            "evidence",
            "default_scope",
            "signal_strength",
            "status",
            "first_seen",
            "last_seen",
            "decisive_signal",
            "root_cause_family",
            "promotion_hint",
            "problem",
            "recommended_action",
        ):
            sanitized_fields[key], labels = sanitize_agent_text(str(payload.get(key) or ""))
            label_groups.append(labels)
        recurrence_key, recurrence_labels = _canonicalize_recurrence_key(
            str(payload.get("recurrence_key") or "")
        )
        label_groups.append(recurrence_labels)
        sanitized_lists: dict[str, list[str]] = {}
        for key in (
            "false_starts",
            "rejected_paths",
            "injection_targets",
            "avoid",
            "trigger_signals",
            "success_criteria",
            "exceptions",
        ):
            sanitized_lists[key] = []
            for item in _coerce_str_list(payload.get(key)):
                sanitized, labels = sanitize_agent_text(item)
                label_groups.append(labels)
                if sanitized.strip():
                    sanitized_lists[key].append(sanitized)
        facets = normalize_learning_facets(payload.get("facets"))
        sanitized_facets: dict[str, list[str]] = {}
        for key, values in facets.items():
            sanitized_facets[key] = []
            for item in values:
                sanitized, labels = sanitize_agent_text(item)
                label_groups.append(labels)
                if sanitized.strip():
                    sanitized_facets[key].append(sanitized)
        labels = _merge_redaction_labels(
            _coerce_str_list(payload.get("redaction_labels")), *label_groups
        )
        raw_sensitivity = str(payload.get("sensitivity") or "").strip().lower()
        sensitivity = (
            raw_sensitivity
            if raw_sensitivity in SENSITIVITY_VALUES and not labels
            else SENSITIVITY_SANITIZED
            if labels
            else SENSITIVITY_SAFE
        )
        learning_value_tier = str(
            payload.get("learning_value_tier") or ""
        ).strip().lower()
        learning_value_reason_codes = sorted(
            {
                value
                for value in _coerce_str_list(
                    payload.get("learning_value_reason_codes")
                )
                if value in VALUE_REASON_CODES
            }
        )
        sensitivity_risk_tier = str(
            payload.get("sensitivity_risk_tier") or ""
        ).strip().lower()
        assessment_decision = str(
            payload.get("assessment_decision") or ""
        ).strip().lower()
        assessment_reason = str(
            payload.get("assessment_reason") or ""
        ).strip().lower()
        if assessment_payload_from_flat(
            learning_value_tier=learning_value_tier,
            learning_value_reason_codes=learning_value_reason_codes,
            sensitivity=sensitivity,
            sensitivity_risk_tier=sensitivity_risk_tier,
            redaction_labels=labels,
            assessment_decision=assessment_decision,
            assessment_reason=assessment_reason,
        ) is None:
            learning_value_tier = ""
            learning_value_reason_codes = []
            sensitivity_risk_tier = ""
            assessment_decision = ""
            assessment_reason = ""
        return cls(
            id=sanitized_fields["id"],
            summary=sanitized_fields["summary"],
            learning_type=sanitized_fields["learning_type"],
            source_command=normalize_command_name(payload["source_command"]),
            evidence=sanitized_fields["evidence"],
            recurrence_key=recurrence_key,
            default_scope=sanitized_fields["default_scope"],
            applies_to=[normalize_command_name(item) for item in applies_to],
            signal_strength=sanitized_fields["signal_strength"],
            status=sanitized_fields["status"],
            first_seen=sanitized_fields["first_seen"],
            last_seen=sanitized_fields["last_seen"],
            occurrence_count=int(payload.get("occurrence_count", 1)),
            pain_score=_coerce_int(payload.get("pain_score")),
            false_starts=sanitized_lists["false_starts"],
            rejected_paths=sanitized_lists["rejected_paths"],
            decisive_signal=sanitized_fields["decisive_signal"],
            root_cause_family=sanitized_fields["root_cause_family"],
            injection_targets=sanitized_lists["injection_targets"],
            promotion_hint=sanitized_fields["promotion_hint"],
            problem=sanitized_fields["problem"],
            recommended_action=sanitized_fields["recommended_action"],
            avoid=sanitized_lists["avoid"],
            trigger_signals=sanitized_lists["trigger_signals"],
            success_criteria=sanitized_lists["success_criteria"],
            exceptions=sanitized_lists["exceptions"],
            facets=normalize_learning_facets(sanitized_facets),
            sensitivity=sensitivity,
            redaction_labels=labels,
            learning_value_tier=learning_value_tier,
            learning_value_reason_codes=learning_value_reason_codes,
            sensitivity_risk_tier=sensitivity_risk_tier,
            assessment_decision=assessment_decision,
            assessment_reason=assessment_reason,
        )


@dataclass
class LearningIndexEntry:
    id: str
    problem: str
    lesson: str
    learning_type: str
    source_command: str
    recurrence_key: str
    applies_to: list[str]
    trigger_signals: list[str]
    detail: str
    first_seen: str
    last_seen: str
    occurrence_count: int = 1
    signal_strength: str = "medium"
    facets: dict[str, list[str]] = field(default_factory=dict)
    sensitivity: str = SENSITIVITY_SAFE
    redaction_labels: list[str] = field(default_factory=list)
    learning_value_tier: str = ""
    learning_value_reason_codes: list[str] = field(default_factory=list)
    sensitivity_risk_tier: str = ""
    assessment_decision: str = ""
    assessment_reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        if not self.facets:
            payload.pop("facets", None)
        if not self.learning_value_tier:
            for key in (
                "learning_value_tier",
                "learning_value_reason_codes",
                "sensitivity_risk_tier",
                "assessment_decision",
                "assessment_reason",
            ):
                payload.pop(key, None)
        return payload

    def assessment_payload(self) -> dict[str, object] | None:
        return assessment_payload_from_flat(
            learning_value_tier=self.learning_value_tier,
            learning_value_reason_codes=self.learning_value_reason_codes,
            sensitivity=self.sensitivity,
            sensitivity_risk_tier=self.sensitivity_risk_tier,
            redaction_labels=self.redaction_labels,
            assessment_decision=self.assessment_decision,
            assessment_reason=self.assessment_reason,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LearningIndexEntry":
        required = {
            "id",
            "problem",
            "lesson",
            "learning_type",
            "source_command",
            "recurrence_key",
            "applies_to",
            "trigger_signals",
            "detail",
            "first_seen",
            "last_seen",
            "occurrence_count",
            "signal_strength",
        }
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(
                f"learning index entry is missing required fields: {', '.join(missing)}"
            )
        if not isinstance(payload["applies_to"], list):
            raise ValueError("learning index applies_to must be a list")
        if not isinstance(payload["trigger_signals"], list):
            raise ValueError("learning index trigger_signals must be a list")
        learning_type = normalize_learning_type(str(payload["learning_type"]))
        source_command = normalize_command_name(str(payload["source_command"]))
        recurrence_key, recurrence_labels = _canonicalize_recurrence_key(
            str(payload["recurrence_key"])
        )
        if not recurrence_key:
            raise ValueError("learning index recurrence_key is required")
        signal_strength = normalize_signal_strength(str(payload["signal_strength"]))
        problem, problem_labels = sanitize_agent_text(str(payload["problem"]).strip())
        lesson, lesson_labels = sanitize_agent_text(str(payload["lesson"]).strip())
        first_seen, first_seen_labels = _safe_index_timestamp(payload["first_seen"])
        last_seen, last_seen_labels = _safe_index_timestamp(payload["last_seen"])
        index_id, index_id_labels = _safe_learning_index_id(payload["id"])
        if not index_id.startswith("learn-"):
            raise ValueError("learning index id must start with 'learn-'")
        if not problem or not lesson or not first_seen or not last_seen:
            raise ValueError(
                "learning index problem, lesson, first_seen, and last_seen are required"
            )
        detail, detail_labels = sanitize_agent_text(str(payload["detail"]).strip())
        if not _is_valid_detail_ref(detail):
            detail = _detail_ref_for_index_id(index_id)
        applies_to = _coerce_str_list(payload["applies_to"])
        trigger_signals, trigger_labels = _sanitize_list_with_labels(
            _coerce_str_list(payload["trigger_signals"])
        )
        if not applies_to or not trigger_signals:
            raise ValueError(
                "learning index applies_to and trigger_signals must not be empty"
            )
        raw_facets = normalize_learning_facets(payload.get("facets"))
        sanitized_facets: dict[str, list[str]] = {}
        facet_label_groups: list[list[str]] = []
        for key, values in raw_facets.items():
            sanitized_values, facet_labels = _sanitize_list_with_labels(values)
            facet_label_groups.append(facet_labels)
            if sanitized_values:
                sanitized_facets[key] = sanitized_values
        redaction_labels = _merge_redaction_labels(
            _coerce_str_list(payload.get("redaction_labels")),
            recurrence_labels,
            index_id_labels,
            problem_labels,
            lesson_labels,
            first_seen_labels,
            last_seen_labels,
            detail_labels,
            trigger_labels,
            *facet_label_groups,
        )
        raw_sensitivity = str(payload.get("sensitivity") or "").strip().lower()
        sensitivity = (
            raw_sensitivity
            if raw_sensitivity in SENSITIVITY_VALUES and not redaction_labels
            else SENSITIVITY_SANITIZED
            if redaction_labels
            else SENSITIVITY_SAFE
        )
        occurrence_count = _coerce_int(payload["occurrence_count"])
        if occurrence_count < 1:
            raise ValueError("learning index occurrence_count must be at least 1")
        learning_value_tier = str(
            payload.get("learning_value_tier") or ""
        ).strip().lower()
        learning_value_reason_codes = sorted(
            {
                value
                for value in _coerce_str_list(
                    payload.get("learning_value_reason_codes")
                )
                if value in VALUE_REASON_CODES
            }
        )
        sensitivity_risk_tier = str(
            payload.get("sensitivity_risk_tier") or ""
        ).strip().lower()
        assessment_decision = str(
            payload.get("assessment_decision") or ""
        ).strip().lower()
        assessment_reason = str(
            payload.get("assessment_reason") or ""
        ).strip().lower()
        if assessment_payload_from_flat(
            learning_value_tier=learning_value_tier,
            learning_value_reason_codes=learning_value_reason_codes,
            sensitivity=sensitivity,
            sensitivity_risk_tier=sensitivity_risk_tier,
            redaction_labels=redaction_labels,
            assessment_decision=assessment_decision,
            assessment_reason=assessment_reason,
        ) is None:
            learning_value_tier = ""
            learning_value_reason_codes = []
            sensitivity_risk_tier = ""
            assessment_decision = ""
            assessment_reason = ""
        return cls(
            id=index_id,
            problem=problem,
            lesson=lesson,
            learning_type=learning_type,
            source_command=source_command,
            recurrence_key=recurrence_key,
            applies_to=[normalize_command_name(item) for item in applies_to],
            trigger_signals=trigger_signals,
            detail=detail,
            first_seen=first_seen,
            last_seen=last_seen,
            occurrence_count=occurrence_count,
            signal_strength=signal_strength,
            facets=normalize_learning_facets(sanitized_facets),
            sensitivity=sensitivity,
            redaction_labels=redaction_labels,
            learning_value_tier=learning_value_tier,
            learning_value_reason_codes=learning_value_reason_codes,
            sensitivity_risk_tier=sensitivity_risk_tier,
            assessment_decision=assessment_decision,
            assessment_reason=assessment_reason,
        )


@dataclass(frozen=True)
class AutoCaptureSuggestion:
    learning_type: str
    summary: str
    evidence: str
    recurrence_key: str
    signal_strength: str = "medium"
    applies_to: tuple[str, ...] | None = None
    problem: str = ""
    recommended_action: str = ""
    trigger_signals: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()


SEMANTIC_TRIGGER_GUIDANCE: dict[str, tuple[str, str, str, str]] = {
    "user_correction": (
        "user_preference",
        "Apply the corrected assumption, preference, or boundary before repeating the affected work.",
        "The next affected workflow reflects the correction without requiring the user to repeat it.",
        "Continuing from the superseded assumption.",
    ),
    "repeated_attempt": (
        "pitfall",
        "Reuse the proven recovery path and skip attempts already disproved by evidence.",
        "The next run reaches the verified path without replaying the same failed attempts.",
        "Repeating a failed attempt without new contradictory evidence.",
    ),
    "route_change": (
        "routing_mistake",
        "Resume from the recorded next command and route reason instead of inferring the route from chat history.",
        "The resumed workflow can explain and follow the selected route from durable state.",
        "Routing from chat memory alone.",
    ),
    "blocker_recovery": (
        "recovery_path",
        "Reuse the recorded recovery action and verify its unblock condition before resuming.",
        "The blocker is cleared by recorded evidence and the workflow resumes at the stated next action.",
        "Retrying unrelated technical actions while the unblock condition remains false.",
    ),
    "false_lead": (
        "false_lead_pattern",
        "Check the rejected path and its decisive evidence before reopening that hypothesis.",
        "The rejected path is skipped unless new evidence directly contradicts the prior decision.",
        "Repeating a disproved route or diagnosis without new evidence.",
    ),
    "decisive_signal": (
        "pitfall",
        "Look for the recorded decisive signal before widening investigation or implementation scope.",
        "The future decision cites the decisive signal and reaches the correct route earlier.",
        "Treating low-value surrounding symptoms as stronger than the decisive signal.",
    ),
    "hidden_dependency": (
        "project_constraint",
        "Resolve or honor the hidden dependency before changing the affected surface.",
        "Downstream work names the dependency and verifies its required precondition.",
        "Starting dependent work before the hidden precondition is satisfied.",
    ),
    "validation_gap": (
        "verification_gap",
        "Add or run the missing real acceptance check before making the affected completion claim.",
        "The completion claim is backed by the recorded verification surface and green evidence.",
        "Using source-only or indirect checks as proof of real behavior.",
    ),
    "tooling_trap": (
        "tooling_trap",
        "Verify the environment and tool boundary before diagnosing the same symptom as a product defect.",
        "The environment/tool cause is ruled in or out before production code changes.",
        "Changing product code before checking the recorded tooling condition.",
    ),
    "state_loss": (
        "state_surface_gap",
        "Persist the missing decision, evidence, and next action before handoff or compaction.",
        "A resumed run continues safely without reconstructing the lost state from chat.",
        "Stopping with required recovery context only in conversation history.",
    ),
    "cognition_gap": (
        "map_coverage_gap",
        "Use live evidence for the missing surface and refresh cognition coverage through the owning map workflow.",
        "The truth-owning surface is queryable and the active workflow no longer depends on a stale omission.",
        "Treating missing cognition coverage as evidence that the surface does not exist.",
    ),
    "reusable_constraint": (
        "project_constraint",
        "Apply the recorded constraint before planning or modifying the affected surface.",
        "Later work names and honors the constraint in its plan, task, or verification route.",
        "Rediscovering the constraint after implementation begins.",
    ),
    "near_miss": (
        "near_miss",
        "Preserve the guard or check that prevented the risky action and run it before similar work.",
        "The same risk is detected before any destructive or hard-to-reverse action.",
        "Relying on luck or operator memory to avoid the same risk.",
    ),
}


def _semantic_trigger_suggestions(
    *,
    command_name: str,
    feature_ref: str,
    trigger_signals: Iterable[str],
) -> list[AutoCaptureSuggestion]:
    suggestions: list[AutoCaptureSuggestion] = []
    for raw_signal in trigger_signals:
        signal = str(raw_signal).strip()
        if not signal:
            continue
        raw_kind, separator, raw_detail = signal.partition(":")
        kind = raw_kind.strip().lower().replace("-", "_").replace(" ", "_")
        detail = " ".join((raw_detail.strip() if separator else signal).split())
        sanitized_detail = _sanitize_text(detail)
        learning_type, action, success, avoid = SEMANTIC_TRIGGER_GUIDANCE.get(
            kind,
            (
                "pitfall",
                "Apply the recorded signal before repeating the affected work.",
                "The next affected workflow uses the signal and records confirming evidence.",
                "Ignoring an explicit reusable-learning signal.",
            ),
        )
        signal_label = kind.replace("_", " ")
        summary = f"{signal_label}: {sanitized_detail}"
        recurrence_suffix = hashlib.sha256(
            sanitized_detail.encode("utf-8")
        ).hexdigest()[:16]
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type=learning_type,
                summary=summary,
                recurrence_key=(
                    f"{command_name}.trigger.{kind}.digest-{recurrence_suffix}"
                ),
                evidence=_format_evidence(
                    "Observed explicit Learning trigger from workflow-state.md",
                    [
                        ("feature_dir", feature_ref),
                        ("command", command_name),
                        ("trigger_kind", kind),
                        ("trigger_detail", sanitized_detail),
                    ],
                ),
                problem=f"The recorded {signal_label} signal could be lost after handoff or compaction: {sanitized_detail}",
                recommended_action=action,
                trigger_signals=(kind,),
                success_criteria=(success,),
                avoid=(avoid,),
            )
        )
    return suggestions


def build_learning_paths(project_root: Path) -> LearningPaths:
    memory_dir = project_root / ".specify" / "memory"
    learning_memory_dir = memory_dir / "learnings"
    learning_dir = project_root / ".planning" / "learnings"
    return LearningPaths(
        constitution=memory_dir / "constitution.md",
        project_rules=memory_dir / "project-rules.md",
        confirmed_learnings=learning_memory_dir / "confirmed.md",
        learning_index=learning_memory_dir / "INDEX.md",
        learning_detail_template=project_root
        / ".specify"
        / "templates"
        / "project-learning-detail-template.md",
        candidates=learning_dir / "candidates.md",
        review=learning_dir / "review.md",
    )


def now_iso() -> str:
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def normalize_command_name(command_name: str) -> str:
    raw = str(command_name or "").strip().lower()
    if not raw:
        raise ValueError("command name is required")
    while raw.startswith("/"):
        raw = raw[1:]
    if not raw:
        raise ValueError("command name is required")
    if raw.startswith("spx-"):
        raw = f"sp-{raw[4:]}"
    elif raw.startswith("spx."):
        raw = f"sp-{raw[4:]}"
    if raw.startswith("sp-"):
        normalized = raw
    elif raw.startswith("sp."):
        normalized = f"sp-{raw[3:]}"
    else:
        normalized = f"sp-{raw}"
    if not re.fullmatch(r"sp-[a-z0-9][a-z0-9-]*", normalized):
        raise ValueError(f"invalid command name '{command_name}'")
    return COMMAND_ALIASES.get(normalized, normalized)


def _slugify(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return lowered or "learning"


def default_scope_for_type(learning_type: str) -> str:
    normalized = learning_type.strip().lower()
    if normalized in {"user_preference", "project_constraint"}:
        return "global"
    if normalized in {
        "workflow_gap",
        "routing_mistake",
        "state_surface_gap",
        "decision_debt",
    }:
        return "planning-heavy"
    if normalized in {"recovery_path", "verification_gap", "false_lead_pattern"}:
        return "execution-heavy"
    if normalized in {"map_coverage_gap", "tooling_trap", "near_miss"}:
        return "cross-workflow"
    return "implementation-heavy"


def default_applies_to_for_type(learning_type: str, source_command: str) -> list[str]:
    normalized_type = learning_type.strip().lower()
    normalized_source = normalize_command_name(source_command)
    if normalized_type in {"user_preference", "project_constraint"}:
        return list(KNOWN_COMMANDS)
    if normalized_type == "workflow_gap":
        return ["sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-quick"]
    if normalized_type == "routing_mistake":
        return [
            "sp-fast",
            "sp-quick",
            "sp-specify",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-debug",
        ]
    if normalized_type == "verification_gap":
        return ["sp-implement", "sp-accept", "sp-debug", "sp-quick", "sp-fast"]
    if normalized_type == "state_surface_gap":
        return [
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-accept",
            "sp-debug",
            "sp-quick",
            *MAP_WORKFLOW_COMMANDS,
        ]
    if normalized_type == "map_coverage_gap":
        return [
            *MAP_WORKFLOW_COMMANDS,
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-debug",
        ]
    if normalized_type == "tooling_trap":
        return ["sp-implement", "sp-debug", "sp-quick", *MAP_WORKFLOW_COMMANDS]
    if normalized_type == "false_lead_pattern":
        return ["sp-debug", "sp-implement", "sp-quick"]
    if normalized_type == "near_miss":
        return sorted({normalized_source, "sp-implement", "sp-debug", "sp-quick"})
    if normalized_type == "decision_debt":
        return [
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            *MAP_WORKFLOW_COMMANDS,
        ]
    if normalized_type == "recovery_path":
        return ["sp-implement", "sp-debug", "sp-quick"]
    if normalized_type == "pitfall":
        return sorted({normalized_source, "sp-implement", "sp-debug", "sp-quick"})
    return [normalized_source]


def normalize_learning_type(learning_type: str) -> str:
    normalized = learning_type.strip().lower()
    if normalized not in LEARNING_TYPES:
        raise ValueError(f"unsupported learning type '{learning_type}'")
    return normalized


def normalize_signal_strength(signal_strength: str) -> str:
    normalized = signal_strength.strip().lower()
    if normalized not in SIGNAL_STRENGTHS:
        raise ValueError(f"unsupported signal strength '{signal_strength}'")
    return normalized


def normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in LEARNING_STATUSES:
        raise ValueError(f"unsupported learning status '{status}'")
    return normalized


def derive_recurrence_key(learning_type: str, summary: str) -> str:
    return f"{normalize_learning_type(learning_type)}.{_slugify(summary)}"


def build_learning_id() -> str:
    return datetime.now(tz=UTC).strftime("LRN-%Y%m%d-%H%M%S-%f")


def build_learning_entry(
    *,
    command_name: str,
    learning_type: str,
    summary: str,
    evidence: str,
    recurrence_key: str | None = None,
    signal_strength: str = "medium",
    applies_to: Iterable[str] | None = None,
    default_scope: str | None = None,
    status: str = "candidate",
    pain_score: int | None = None,
    false_starts: Iterable[str] | None = None,
    rejected_paths: Iterable[str] | None = None,
    decisive_signal: str | None = None,
    root_cause_family: str | None = None,
    injection_targets: Iterable[str] | None = None,
    promotion_hint: str | None = None,
    problem: str | None = None,
    recommended_action: str | None = None,
    avoid: Iterable[str] | None = None,
    trigger_signals: Iterable[str] | None = None,
    success_criteria: Iterable[str] | None = None,
    exceptions: Iterable[str] | None = None,
    facets: Mapping[str, Iterable[str]] | None = None,
    assessment_source: str = "manual",
    assessment_occurrences: int = 1,
    policy: LearningPolicy | None = None,
) -> LearningEntry:
    active_policy = policy or default_learning_policy()
    assessment = assess_learning_candidate(
        source=assessment_source,
        learning_type=learning_type,
        signal_strength=signal_strength,
        occurrences=assessment_occurrences,
        summary=str(summary or "").strip(),
        evidence=str(evidence or "").strip(),
        recommended_action=str(recommended_action or "").strip(),
        trigger_signals=trigger_signals or (),
        policy=active_policy,
    )
    normalized_summary = assessment.summary
    normalized_evidence = assessment.evidence
    summary_labels = list(assessment.redaction_labels)
    evidence_labels = list(assessment.redaction_labels)
    if not normalized_summary:
        raise ValueError("learning summary is required")
    if not normalized_evidence:
        raise ValueError("learning evidence is required")
    normalized_command, command_labels = _safe_review_command_with_labels(
        command_name, active_policy
    )
    normalized_type = normalize_learning_type(learning_type)
    normalized_signal = normalize_signal_strength(signal_strength)
    normalized_status = normalize_status(status)
    applies_labels: list[str] = []
    if applies_to:
        normalized_applies = []
        for item in applies_to:
            safe_command, safe_command_labels = _safe_review_command_with_labels(
                item, active_policy
            )
            normalized_applies.append(safe_command)
            applies_labels.extend(safe_command_labels)
    else:
        normalized_applies = default_applies_to_for_type(
            normalized_type, normalized_command
        )
    raw_recurrence_key = (
        str(
            recurrence_key or derive_recurrence_key(normalized_type, normalized_summary)
        )
        .strip()
        .lower()
    )
    normalized_recurrence_key, recurrence_labels = _canonicalize_recurrence_key(
        raw_recurrence_key, policy=active_policy
    )
    if not normalized_recurrence_key:
        raise ValueError("learning recurrence_key is required")
    default_scope_value, default_scope_labels = sanitize_agent_text(
        (default_scope or default_scope_for_type(normalized_type)).strip().lower(),
        policy=active_policy,
    )
    false_start_values, false_start_labels = _sanitize_list_with_labels(
        (str(item).strip() for item in (false_starts or []) if str(item).strip()),
        policy=active_policy,
    )
    rejected_path_values, rejected_path_labels = _sanitize_list_with_labels(
        (str(item).strip() for item in (rejected_paths or []) if str(item).strip()),
        policy=active_policy,
    )
    decisive_signal_value, decisive_signal_labels = sanitize_agent_text(
        str(decisive_signal or "").strip(), policy=active_policy
    )
    root_cause_value, root_cause_labels = sanitize_agent_text(
        str(root_cause_family or "").strip(), policy=active_policy
    )
    injection_target_values, injection_target_labels = _sanitize_list_with_labels(
        (
            str(item).strip()
            for item in (injection_targets or [])
            if str(item).strip()
        ),
        policy=active_policy,
    )
    promotion_hint_value, promotion_hint_labels = sanitize_agent_text(
        str(promotion_hint or "").strip(), policy=active_policy
    )
    problem_value, problem_labels = sanitize_agent_text(
        str(problem or normalized_summary).strip(), policy=active_policy
    )
    action_value = assessment.recommended_action or normalized_summary
    action_value, action_labels = sanitize_agent_text(action_value, policy=active_policy)
    avoid_values, avoid_labels = _sanitize_list_with_labels(
        (str(item).strip() for item in (avoid or []) if str(item).strip()),
        policy=active_policy,
    )
    trigger_signal_values, trigger_signal_labels = _sanitize_list_with_labels(
        (
            str(item).strip()
            for item in (trigger_signals or [])
            if str(item).strip()
        ),
        policy=active_policy,
    )
    success_values, success_labels = _sanitize_list_with_labels(
        (
            str(item).strip()
            for item in (success_criteria or [])
            if str(item).strip()
        ),
        policy=active_policy,
    )
    exception_values, exception_labels = _sanitize_list_with_labels(
        (str(item).strip() for item in (exceptions or []) if str(item).strip()),
        policy=active_policy,
    )
    normalized_facets = normalize_learning_facets(facets)
    facet_labels: list[str] = []
    sanitized_facets: dict[str, list[str]] = {}
    for key, values in normalized_facets.items():
        for item in values:
            sanitized, labels = sanitize_agent_text(item, policy=active_policy)
            facet_labels.extend(labels)
            if sanitized.strip():
                sanitized_facets.setdefault(key, []).append(sanitized)
    redaction_labels = _merge_redaction_labels(
        summary_labels,
        evidence_labels,
        command_labels,
        applies_labels,
        recurrence_labels,
        default_scope_labels,
        false_start_labels,
        rejected_path_labels,
        decisive_signal_labels,
        root_cause_labels,
        injection_target_labels,
        promotion_hint_labels,
        problem_labels,
        action_labels,
        avoid_labels,
        trigger_signal_labels,
        success_labels,
        exception_labels,
        facet_labels,
    )
    assessment_decision = assessment.assessment_decision
    assessment_reason = assessment.assessment_reason
    sensitivity_risk_tier = _assessment_risk_tier(redaction_labels)
    if redaction_labels and assessment_decision == "capture-safe":
        assessment_decision = "capture-sanitized"
        assessment_reason = "valuable_after_abstraction"
    timestamp = now_iso()
    return LearningEntry(
        id=build_learning_id(),
        summary=normalized_summary,
        learning_type=normalized_type,
        source_command=normalized_command,
        evidence=normalized_evidence,
        recurrence_key=normalized_recurrence_key,
        default_scope=default_scope_value,
        applies_to=sorted(dict.fromkeys(normalized_applies)),
        signal_strength=normalized_signal,
        status=normalized_status,
        first_seen=timestamp,
        last_seen=timestamp,
        occurrence_count=1,
        pain_score=max(0, _coerce_int(pain_score)),
        false_starts=sorted(dict.fromkeys(false_start_values)),
        rejected_paths=sorted(dict.fromkeys(rejected_path_values)),
        decisive_signal=decisive_signal_value,
        root_cause_family=root_cause_value,
        injection_targets=sorted(
            dict.fromkeys(injection_target_values)
        ),
        promotion_hint=promotion_hint_value,
        problem=problem_value,
        recommended_action=action_value,
        avoid=sorted(dict.fromkeys(avoid_values)),
        trigger_signals=sorted(dict.fromkeys(trigger_signal_values)),
        success_criteria=sorted(dict.fromkeys(success_values)),
        exceptions=sorted(dict.fromkeys(exception_values)),
        facets=normalize_learning_facets(sanitized_facets),
        sensitivity=SENSITIVITY_SANITIZED if redaction_labels else SENSITIVITY_SAFE,
        redaction_labels=redaction_labels,
        learning_value_tier=assessment.learning_value_tier,
        learning_value_reason_codes=list(assessment.learning_value_reason_codes),
        sensitivity_risk_tier=sensitivity_risk_tier,
        assessment_decision=assessment_decision,
        assessment_reason=assessment_reason,
    )


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            return int(stripped)
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
        if item is None:
            continue
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                values.append(stripped)
            continue
        if isinstance(item, dict):
            dumped = yaml.safe_dump(item, sort_keys=False).strip()
            if dumped:
                values.append(dumped)
            continue
        dumped = str(item).strip()
        if dumped:
            values.append(dumped)
    return values


def _coerce_dict_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        return []
    values: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            values.append(item)
    return values


def _coerce_section_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, list):
        return {}
    merged: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        for key, nested in item.items():
            merged[str(key)] = nested
    return merged


def _coerce_grouped_mapping_list(value: Any, *, group_key: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    items: list[Any]
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict):
        items = [value]
    else:
        return []

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        grouped = item.get(group_key)
        mapping = _coerce_section_mapping(grouped)
        if mapping:
            results.append(mapping)
    return results


def _load_sectioned_markdown(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    frontmatter: dict[str, Any] = {}
    body = text
    parsed_frontmatter, parsed_body = parse_frontmatter(text)
    if parsed_frontmatter:
        frontmatter = dict(parsed_frontmatter)
        body = parsed_body

    sections: dict[str, Any] = {}
    current_section: str | None = None
    current_lines: list[str] = []
    for raw_line in body.splitlines():
        match = re.match(r"^##\s+(?P<title>.+?)\s*$", raw_line)
        if match:
            if current_section is not None:
                section_text = "\n".join(current_lines).strip()
                sections[current_section] = (
                    yaml.safe_load(section_text) if section_text else None
                )
            current_section = match.group("title").strip()
            current_lines = []
            continue
        if current_section is not None:
            current_lines.append(raw_line)
    if current_section is not None:
        section_text = "\n".join(current_lines).strip()
        sections[current_section] = (
            yaml.safe_load(section_text) if section_text else None
        )
    return frontmatter, sections


def _auto_capture_registry_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / "auto-capture.json"


def _project_root_from_learning_paths(paths: LearningPaths) -> Path:
    return paths.review.parent.parent.parent


def _load_auto_capture_registry(project_root: Path) -> dict[str, Any]:
    path = _auto_capture_registry_path(project_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_auto_capture_registry(project_root: Path, payload: dict[str, Any]) -> None:
    path = _auto_capture_registry_path(project_root)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _safe_registry_fingerprint(value: str) -> str:
    raw = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", raw):
        return raw
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_project_relative_ref(project_root: Path, path: Path) -> str:
    try:
        ref = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        ref = Path(path.name)
    return ref.as_posix()


def _safe_ref_from_registry_value(project_root: Path, value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    normalized_raw = raw.replace("\\", "/")
    looks_external_absolute = bool(
        re.match(r"^[A-Za-z]:/", normalized_raw)
        or normalized_raw.startswith("//")
        or normalized_raw.startswith("/")
    )
    candidate = Path(raw)
    if candidate.is_absolute():
        return _safe_project_relative_ref(project_root, candidate)
    sanitized = _sanitize_text(normalized_raw)
    if looks_external_absolute:
        if sanitized.startswith("<USER_HOME>/"):
            return sanitized
        return Path(sanitized).name
    candidate = project_root / sanitized
    try:
        return candidate.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return Path(sanitized).name


def _safe_registry_timestamp(value: Any) -> str:
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


def _auto_capture_supported_commands() -> set[str]:
    return {
        "sp-implement",
        "sp-quick",
        "sp-debug",
        *WORKFLOW_STATE_AUTO_CAPTURE_COMMANDS,
    }


def _normalize_auto_capture_registry(
    project_root: Path,
    registry: dict[str, Any],
    *,
    policy: LearningPolicy | None = None,
) -> tuple[dict[str, Any], bool]:
    normalized: dict[str, Any] = {}
    changed = False
    for raw_key, raw_record in registry.items():
        safe_key = _safe_registry_fingerprint(str(raw_key))
        if safe_key != raw_key:
            changed = True
        if not isinstance(raw_record, dict):
            changed = True
            continue
        source_ref = _safe_ref_from_registry_value(
            project_root, raw_record.get("source_ref") or raw_record.get("source_path")
        )
        recurrence_keys = []
        for raw_recurrence in _coerce_str_list(raw_record.get("recurrence_keys")):
            recurrence_key, _labels = _canonicalize_recurrence_key(
                raw_recurrence, policy=policy
            )
            if recurrence_key:
                recurrence_keys.append(recurrence_key)
        try:
            command = normalize_command_name(str(raw_record.get("command") or ""))
        except ValueError:
            changed = True
            continue
        if command not in _auto_capture_supported_commands():
            changed = True
            continue
        record = {
            "command": command,
            "source_ref": source_ref,
            "recurrence_keys": sorted(dict.fromkeys(recurrence_keys)),
            "captured_at": _safe_registry_timestamp(raw_record.get("captured_at")),
        }
        normalized[safe_key] = record
        if record != raw_record:
            changed = True
    return normalized, changed


_METRIC_TOTAL_KEYS = {
    "assessed",
    "captured",
    "candidate_captured",
    "confirmed",
    "promoted",
    "deferred",
    "ignored",
}
_METRIC_MAP_KEYS = {
    "decisions",
    "value_tiers",
    "risk_tiers",
    "reason_codes",
    "redaction_labels",
}
_PENDING_REVIEW_DECISIONS = {"deferred", "manual-capture-needed"}
_REVIEW_DECISIONS = {
    "none",
    "captured",
    "auto-captured",
    *_PENDING_REVIEW_DECISIONS,
}


def _learning_metrics_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / "metrics.json"


def _learning_review_state_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / "review-state.json"


def _legacy_signal_state_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / "signal-state.json"


def _empty_metric_bucket() -> dict[str, dict[str, int]]:
    return {
        "totals": {key: 0 for key in sorted(_METRIC_TOTAL_KEYS)},
        "decisions": {key: 0 for key in sorted(ASSESSMENT_DECISIONS)},
        "value_tiers": {key: 0 for key in sorted(LEARNING_VALUE_TIERS)},
        "risk_tiers": {key: 0 for key in ("high", "moderate", "none")},
        "reason_codes": {key: 0 for key in sorted(VALUE_REASON_CODES)},
        "redaction_labels": {
            key: 0 for key in sorted(CANONICAL_REDACTION_LABELS)
        },
    }


def _normalize_count_map(value: Any, *, allowed: set[str] | None = None) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        key = str(raw_key or "").strip()
        if not key or (allowed is not None and key not in allowed):
            continue
        count = _coerce_int(raw_count)
        if count >= 0:
            normalized[key] = count
    return normalized


def _normalize_metric_bucket(value: Any) -> dict[str, dict[str, int]]:
    bucket = _empty_metric_bucket()
    if not isinstance(value, Mapping):
        return bucket
    bucket["totals"].update(
        _normalize_count_map(value.get("totals"), allowed=_METRIC_TOTAL_KEYS)
    )
    allowed_by_key = {
        "decisions": ASSESSMENT_DECISIONS,
        "value_tiers": LEARNING_VALUE_TIERS,
        "risk_tiers": {"none", "moderate", "high"},
        "reason_codes": VALUE_REASON_CODES,
        "redaction_labels": CANONICAL_REDACTION_LABELS,
    }
    for key, allowed in allowed_by_key.items():
        bucket[key].update(_normalize_count_map(value.get(key), allowed=allowed))
    return bucket


def _load_learning_metrics(project_root: Path) -> dict[str, Any]:
    path = _learning_metrics_path(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        raw = {}
    by_command: dict[str, dict[str, dict[str, int]]] = {}
    raw_by_command = raw.get("by_command") if isinstance(raw, Mapping) else None
    if isinstance(raw_by_command, Mapping):
        for command, bucket in raw_by_command.items():
            try:
                normalized_command = normalize_command_name(str(command))
            except ValueError:
                continue
            if normalized_command in KNOWN_COMMANDS:
                by_command[normalized_command] = _normalize_metric_bucket(bucket)
    return {
        "schema_version": 1,
        "global": _normalize_metric_bucket(
            raw.get("global") if isinstance(raw, Mapping) else None
        ),
        "by_command": by_command,
    }


def _increment_metric(mapping: dict[str, int], key: str, amount: int = 1) -> None:
    mapping[key] = max(0, _coerce_int(mapping.get(key))) + amount


def _update_metric_bucket(
    bucket: dict[str, dict[str, int]],
    entry: LearningEntry,
    *,
    confirmed: bool = False,
) -> None:
    _increment_metric(bucket["totals"], "assessed")
    decision = entry.assessment_decision
    if decision in ASSESSMENT_DECISIONS:
        _increment_metric(bucket["decisions"], decision)
    if entry.learning_value_tier in LEARNING_VALUE_TIERS:
        _increment_metric(bucket["value_tiers"], entry.learning_value_tier)
    if entry.sensitivity_risk_tier in {"none", "moderate", "high"}:
        _increment_metric(bucket["risk_tiers"], entry.sensitivity_risk_tier)
    for reason in entry.learning_value_reason_codes:
        if reason in VALUE_REASON_CODES:
            _increment_metric(bucket["reason_codes"], reason)
    for label in entry.redaction_labels:
        if label in CANONICAL_REDACTION_LABELS:
            _increment_metric(bucket["redaction_labels"], label)
    if decision in {"capture-safe", "capture-sanitized"}:
        _increment_metric(bucket["totals"], "captured")
        _increment_metric(
            bucket["totals"], "confirmed" if confirmed else "candidate_captured"
        )
    elif decision == "defer":
        _increment_metric(bucket["totals"], "deferred")
    elif decision == "ignore":
        _increment_metric(bucket["totals"], "ignored")


def _record_learning_metric_unlocked(
    project_root: Path, entry: LearningEntry, *, confirmed: bool = False
) -> None:
    metrics = _load_learning_metrics(project_root)
    _update_metric_bucket(metrics["global"], entry, confirmed=confirmed)
    if entry.source_command in KNOWN_COMMANDS:
        command_bucket = metrics["by_command"].setdefault(
            entry.source_command, _empty_metric_bucket()
        )
        _update_metric_bucket(command_bucket, entry, confirmed=confirmed)
    path = _learning_metrics_path(project_root)
    atomic_write_text(path, json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")


def _record_promotion_metric_unlocked(
    project_root: Path, command_name: str, *, target: str
) -> None:
    metrics = _load_learning_metrics(project_root)
    total_key = "confirmed" if target == "learning" else "promoted"
    _increment_metric(metrics["global"]["totals"], total_key)
    if command_name in KNOWN_COMMANDS:
        bucket = metrics["by_command"].setdefault(
            command_name, _empty_metric_bucket()
        )
        _increment_metric(bucket["totals"], total_key)
    atomic_write_text(
        _learning_metrics_path(project_root),
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
    )


def _safe_review_time(value: Any, *, fallback: str = "") -> str:
    return _safe_registry_timestamp(value) or fallback


def _safe_review_command_with_labels(
    command_name: str, policy: LearningPolicy
) -> tuple[str, list[str]]:
    command = normalize_command_name(command_name)
    sanitized, labels = sanitize_agent_text(command, policy=policy)
    return ("sp-other" if labels or sanitized != command else command), labels


def _safe_review_command(command_name: str, policy: LearningPolicy) -> str:
    return _safe_review_command_with_labels(command_name, policy)[0]


def _normalize_review_item(
    raw: Any,
    *,
    policy: LearningPolicy,
    fallback_now: str,
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    try:
        command = _safe_review_command(str(raw.get("command") or ""), policy)
    except ValueError:
        return None
    decision = str(raw.get("decision") or "").strip().lower()
    if decision not in _PENDING_REVIEW_DECISIONS:
        return None
    rationale, _labels = sanitize_agent_text(
        str(raw.get("rationale") or "").strip(), policy=policy
    )
    if not rationale:
        return None
    recurrence_key, _recurrence_labels = _canonicalize_recurrence_key(
        str(raw.get("recurrence_key") or ""), policy=policy
    )
    created_at = _safe_review_time(raw.get("created_at"), fallback=fallback_now)
    updated_at = _safe_review_time(raw.get("updated_at"), fallback=created_at)
    default_review_after = (
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        + timedelta(days=policy.deferred_review_days)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    review_after = _safe_review_time(
        raw.get("review_after"), fallback=default_review_after
    )
    return {
        "command": command,
        "decision": decision,
        "rationale": rationale,
        "recurrence_key": recurrence_key,
        "created_at": created_at,
        "updated_at": updated_at,
        "review_after": review_after,
    }


def _read_legacy_review_items(
    project_root: Path, *, policy: LearningPolicy, fallback_now: str
) -> list[dict[str, Any]]:
    path = _legacy_signal_state_path(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, Mapping):
        return []
    items: list[dict[str, Any]] = []
    for raw_command, signal in raw.items():
        if not isinstance(signal, Mapping):
            continue
        review = signal.get("learning_review")
        if not isinstance(review, Mapping):
            continue
        item = _normalize_review_item(
            {
                "command": raw_command,
                "decision": review.get("decision"),
                "rationale": review.get("rationale"),
                "recurrence_key": review.get("recurrence_key"),
                "created_at": review.get("deferred_at")
                or signal.get("observed_at"),
                "updated_at": review.get("deferred_at")
                or signal.get("observed_at"),
                "review_after": review.get("review_after"),
            },
            policy=policy,
            fallback_now=fallback_now,
        )
        if item is not None:
            items.append(item)
    return items


def _load_review_items(
    project_root: Path,
    *,
    policy: LearningPolicy,
    include_legacy: bool,
    fallback_now: str | None = None,
) -> list[dict[str, Any]]:
    now = fallback_now or now_iso()
    path = _learning_review_state_path(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        raw = {}
    raw_items = raw.get("items") if isinstance(raw, Mapping) else []
    candidates = list(raw_items) if isinstance(raw_items, list) else []
    canonical_commands: set[str] = set()
    for raw_item in candidates:
        normalized = _normalize_review_item(
            raw_item, policy=policy, fallback_now=now
        )
        if normalized is not None:
            canonical_commands.add(normalized["command"])
    if include_legacy:
        candidates.extend(
            item
            for item in _read_legacy_review_items(
                project_root, policy=policy, fallback_now=now
            )
            if item["command"] not in canonical_commands
        )
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_item in candidates:
        item = _normalize_review_item(raw_item, policy=policy, fallback_now=now)
        if item is None:
            continue
        identity = (item["command"], item["recurrence_key"])
        current = by_identity.get(identity)
        if current is None or item["updated_at"] >= current["updated_at"]:
            by_identity[identity] = item
    return sorted(
        by_identity.values(),
        key=lambda item: (item["review_after"], item["command"], item["recurrence_key"]),
    )


def _write_review_items(project_root: Path, items: list[dict[str, Any]]) -> None:
    atomic_write_text(
        _learning_review_state_path(project_root),
        json.dumps(
            {"schema_version": 1, "items": items},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )


def _record_review_state_unlocked(
    project_root: Path,
    *,
    command_name: str,
    decision: str,
    rationale: str,
    trigger_signals: Iterable[str] = (),
    recurrence_key: str = "",
    policy: LearningPolicy,
    observed_at: str = "",
) -> dict[str, Any]:
    del trigger_signals  # canonical review-state intentionally retains no raw signals
    command = _safe_review_command(command_name, policy)
    safe_rationale, _labels = sanitize_agent_text(rationale, policy=policy)
    if decision not in _PENDING_REVIEW_DECISIONS:
        raise ValueError("only pending learning review decisions may be persisted")
    if not safe_rationale.strip():
        raise ValueError(f"learning review decision `{decision}` requires a rationale")
    safe_recurrence, _recurrence_labels = _canonicalize_recurrence_key(
        recurrence_key, policy=policy
    )
    now = _safe_review_time(observed_at, fallback=now_iso())
    items = _load_review_items(
        project_root, policy=policy, include_legacy=True, fallback_now=now
    )
    identity = (command, safe_recurrence)
    existing = next(
        (
            item
            for item in items
            if (item["command"], item["recurrence_key"]) == identity
        ),
        None,
    )
    created_at = existing["created_at"] if existing else now
    review_after = (
        datetime.fromisoformat(now.replace("Z", "+00:00"))
        + timedelta(days=policy.deferred_review_days)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    item = {
        "command": command,
        "decision": decision,
        "rationale": safe_rationale,
        "recurrence_key": safe_recurrence,
        "created_at": created_at,
        "updated_at": now,
        "review_after": review_after,
    }
    items = [
        candidate
        for candidate in items
        if (candidate["command"], candidate["recurrence_key"]) != identity
    ]
    items.append(item)
    items.sort(
        key=lambda candidate: (
            candidate["review_after"],
            candidate["command"],
            candidate["recurrence_key"],
        )
    )
    _write_review_items(project_root, items)
    _clear_legacy_review_for_command(project_root, command, policy=policy)
    return item


def _entry_seen_after(entry: LearningEntry, timestamp: str) -> bool:
    if not timestamp:
        return True
    try:
        return datetime.fromisoformat(entry.last_seen.replace("Z", "+00:00")) >= datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
    except ValueError:
        return False


_LEGACY_SIGNAL_FACTOR_KEYS = {
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


def _sanitize_legacy_trigger_signals(
    value: Any, *, policy: LearningPolicy
) -> tuple[list[str], list[str]]:
    signals: list[str] = []
    label_groups: list[list[str]] = []
    for item in _coerce_str_list(value):
        sanitized, labels = sanitize_agent_text(item, policy=policy)
        label_groups.append(labels)
        kind = sanitized.partition(":")[0].strip().lower()
        kind = re.sub(r"[^a-z0-9_]+", "_", kind.replace("-", " ")).strip("_")
        if kind:
            signals.append(kind)
    return sorted(dict.fromkeys(signals)), _merge_redaction_labels(*label_groups)


def _sanitize_legacy_signal_payload_for_write(
    command_name: str,
    payload: Mapping[str, Any],
    *,
    policy: LearningPolicy,
) -> dict[str, Any]:
    safe_command, command_labels = _safe_review_command_with_labels(
        command_name, policy
    )
    false_starts, false_start_labels = _sanitize_list_with_labels(
        _coerce_str_list(payload.get("false_starts")), policy=policy
    )
    hidden_dependencies, dependency_labels = _sanitize_list_with_labels(
        _coerce_str_list(payload.get("hidden_dependencies")), policy=policy
    )
    trigger_signals, trigger_labels = _sanitize_legacy_trigger_signals(
        payload.get("trigger_signals"), policy=policy
    )
    existing_safety = payload.get("content_safety")
    existing_labels = (
        _coerce_str_list(existing_safety.get("redaction_labels"))
        if isinstance(existing_safety, Mapping)
        else []
    )
    labels = _merge_redaction_labels(
        existing_labels,
        command_labels,
        false_start_labels,
        dependency_labels,
        trigger_labels,
    )
    sanitized: dict[str, Any] = {
        "command": safe_command,
        "pain_score": max(0, _coerce_int(payload.get("pain_score"))),
        "factors": (
            {
                str(key): max(0, _coerce_int(value))
                for key, value in payload.get("factors", {}).items()
                if str(key) in _LEGACY_SIGNAL_FACTOR_KEYS
            }
            if isinstance(payload.get("factors"), Mapping)
            else {}
        ),
        "false_starts": sorted(dict.fromkeys(false_starts)),
        "hidden_dependencies": sorted(dict.fromkeys(hidden_dependencies)),
        "trigger_signals": trigger_signals,
        "content_safety": {
            "sensitivity": "sanitized" if labels else "safe",
            "redaction_labels": labels,
        },
        "observed_at": _safe_review_time(payload.get("observed_at")),
    }
    if "last_observed_at" in payload:
        sanitized["last_observed_at"] = _safe_review_time(
            payload.get("last_observed_at")
        )
    review = payload.get("learning_review")
    if isinstance(review, Mapping):
        decision = str(review.get("decision") or "").strip().lower()
        rationale, rationale_labels = sanitize_agent_text(
            str(review.get("rationale") or "").strip(), policy=policy
        )
        if decision in _REVIEW_DECISIONS:
            labels = _merge_redaction_labels(labels, rationale_labels)
            sanitized["learning_review"] = {
                "decision": decision,
                "rationale": rationale,
                "deferred_at": _safe_review_time(review.get("deferred_at")),
            }
            sanitized["content_safety"] = {
                "sensitivity": "sanitized" if labels else "safe",
                "redaction_labels": labels,
            }
    return sanitized


def _clear_legacy_review_for_command(
    project_root: Path,
    command_name: str,
    *,
    policy: LearningPolicy,
) -> None:
    path = _legacy_signal_state_path(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(raw, dict):
        return
    sanitized_state: dict[str, dict[str, Any]] = {}
    target_command = _safe_review_command(command_name, policy)
    removed = False
    for key, raw_signal in raw.items():
        if not isinstance(key, str) or not isinstance(raw_signal, Mapping):
            continue
        try:
            safe_key_command = _safe_review_command(key, policy)
        except ValueError:
            continue
        signal = _sanitize_legacy_signal_payload_for_write(
            safe_key_command, raw_signal, policy=policy
        )
        if safe_key_command == target_command and "learning_review" in signal:
            signal.pop("learning_review", None)
            removed = True
        sanitized_state[safe_key_command.removeprefix("sp-")] = signal
    if not removed:
        return
    atomic_write_text(
        path, json.dumps(sanitized_state, ensure_ascii=False, indent=2) + "\n"
    )


def _clear_matching_review_state_unlocked(
    project_root: Path, entry: LearningEntry
) -> bool:
    policy = load_learning_policy(project_root, for_write=True).policy
    items = _load_review_items(project_root, policy=policy, include_legacy=True)
    removed_commands: set[str] = set()
    retained: list[dict[str, Any]] = []
    for item in items:
        command_matches = item["command"] in entry.applies_to or item[
            "command"
        ] == entry.source_command
        recurrence_matches = not item["recurrence_key"] or item[
            "recurrence_key"
        ] == entry.recurrence_key
        if (
            command_matches
            and recurrence_matches
            and _entry_seen_after(entry, item["created_at"])
        ):
            removed_commands.add(item["command"])
            continue
        retained.append(item)
    if len(retained) == len(items):
        return False
    _write_review_items(project_root, retained)
    for command in removed_commands:
        _clear_legacy_review_for_command(project_root, command, policy=policy)
    return True


def _detail_path_response(paths: LearningPaths, detail_path: Path) -> str:
    return _safe_project_relative_ref(_project_root_from_learning_paths(paths), detail_path)


def _ensure_project_contained_path(project_root: Path, path: Path, label: str) -> Path:
    resolved_project = project_root.resolve()
    candidate = path if path.is_absolute() else project_root / path
    resolved_path = candidate.resolve()
    try:
        resolved_path.relative_to(resolved_project)
    except ValueError as exc:
        raise ValueError(f"{label} must resolve inside the project root") from exc
    return resolved_path


def _snapshot_fingerprint(
    command_name: str,
    source_ref: str,
    suggestions: list[AutoCaptureSuggestion],
    *,
    policy: LearningPolicy | None = None,
) -> str:
    active_policy = policy or default_learning_policy()

    def semantic_digest(value: str) -> str:
        sanitized, _labels = sanitize_agent_text(value, policy=active_policy)
        return hashlib.sha256(sanitized.encode("utf-8")).hexdigest()[:16]

    normalized_payload = {
        "assessment_version": ASSESSMENT_VERSION,
        "policy_digest": learning_policy_digest(active_policy),
        "command": normalize_command_name(command_name),
        "source_ref": source_ref,
        "suggestions": [
            {
                "learning_type": item.learning_type,
                "recurrence_key": _canonicalize_recurrence_key(
                    item.recurrence_key, policy=active_policy
                )[0],
                "signal_strength": item.signal_strength,
                "summary_digest": semantic_digest(item.summary),
                "evidence_digest": semantic_digest(item.evidence),
            }
            for item in suggestions
        ],
    }
    payload = json.dumps(
        normalized_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _extract_payload_block(content: str) -> tuple[str, list[dict[str, Any]]]:
    if MACHINE_BEGIN not in content or MACHINE_END not in content:
        return content.rstrip(), []
    before, rest = content.split(MACHINE_BEGIN, 1)
    payload_text, _after = rest.split(MACHINE_END, 1)
    payload_text = payload_text.strip()
    if not payload_text:
        return before.rstrip(), []
    payload = json.loads(payload_text)
    if not isinstance(payload, list):
        raise ValueError("learning payload must be a list")
    return before.rstrip(), payload


def _render_entry_summary(entry: LearningEntry) -> str:
    applies = ", ".join(entry.applies_to)
    base = (
        f"### {entry.id} - {entry.summary}\n\n"
        f"- Status: `{entry.status}`\n"
        f"- Type: `{entry.learning_type}`\n"
        f"- Source Command: `{entry.source_command}`\n"
        f"- Recurrence Key: `{entry.recurrence_key}`\n"
        f"- Scope: `{entry.default_scope}`\n"
        f"- Applies To: {applies}\n"
        f"- Signal: `{entry.signal_strength}`\n"
        f"- Occurrence Count: {entry.occurrence_count}\n"
        f"- First Seen: `{entry.first_seen}`\n"
        f"- Last Seen: `{entry.last_seen}`\n\n"
        f"#### Evidence\n\n{entry.evidence}\n"
    )
    structured_lines: list[str] = []
    if entry.pain_score:
        structured_lines.append(f"- Pain Score: `{entry.pain_score}`")
    if entry.false_starts:
        structured_lines.append(f"- False Starts: {', '.join(entry.false_starts)}")
    if entry.rejected_paths:
        structured_lines.append(f"- Rejected Paths: {', '.join(entry.rejected_paths)}")
    if entry.decisive_signal:
        structured_lines.append(f"- Decisive Signal: {entry.decisive_signal}")
    if entry.root_cause_family:
        structured_lines.append(f"- Root Cause Family: `{entry.root_cause_family}`")
    if entry.injection_targets:
        structured_lines.append(
            f"- Injection Targets: {', '.join(entry.injection_targets)}"
        )
    if entry.promotion_hint:
        structured_lines.append(f"- Promotion Hint: {entry.promotion_hint}")
    for key, values in entry.facets.items():
        if values:
            structured_lines.append(f"- Facet {key}: {', '.join(values)}")
    if not structured_lines:
        return base
    return f"{base}\n#### Structured Learning\n\n" + "\n".join(structured_lines) + "\n"


def _render_learning_file(preamble: str, entries: list[LearningEntry]) -> str:
    payload = [entry.to_payload() for entry in entries]
    sections = [
        preamble.rstrip(),
        "",
        MACHINE_BEGIN,
        json.dumps(payload, ensure_ascii=False, indent=2),
        MACHINE_END,
        "",
        "## Managed Entries",
        "",
    ]
    if not entries:
        sections.append("_No entries recorded yet._")
    else:
        sections.append(
            "\n\n---\n\n".join(_render_entry_summary(entry) for entry in entries)
        )
    sections.append("")
    return "\n".join(sections)


def _learning_index_date_prefix(first_seen: str) -> str:
    prefix = str(first_seen or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", prefix):
        return prefix
    return "unknown-date"


def _learning_index_id(recurrence_key: str, first_seen: str) -> str:
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    return f"learn-{_learning_index_date_prefix(first_seen)}-{_slugify(recurrence_key)[:56]}-{recurrence_hash}"


def _detail_ref_for_index_id(index_id: str) -> str:
    return f"./{index_id}.md"


def _trigger_signals_from_entry(entry: LearningEntry) -> list[str]:
    signals = [entry.learning_type, entry.signal_strength]
    signals.extend(entry.trigger_signals)
    signals.extend(entry.false_starts)
    signals.extend(entry.rejected_paths)
    if entry.decisive_signal:
        signals.append(entry.decisive_signal)
    if entry.root_cause_family:
        signals.append(entry.root_cause_family)
    return sorted(dict.fromkeys(signal for signal in signals if str(signal).strip()))


def _index_entry_from_learning(entry: LearningEntry) -> LearningIndexEntry:
    index_id = _learning_index_id(entry.recurrence_key, entry.first_seen)
    return LearningIndexEntry(
        id=index_id,
        problem=entry.problem or entry.summary,
        lesson=(
            entry.recommended_action
            or (
                entry.evidence.splitlines()[0]
                if entry.evidence.strip()
                else entry.summary
            )
        ),
        learning_type=entry.learning_type,
        source_command=entry.source_command,
        recurrence_key=entry.recurrence_key,
        applies_to=entry.applies_to,
        trigger_signals=_trigger_signals_from_entry(entry),
        detail=_detail_ref_for_index_id(index_id),
        first_seen=entry.first_seen,
        last_seen=entry.last_seen,
        occurrence_count=entry.occurrence_count,
        signal_strength=entry.signal_strength,
        facets=entry.facets,
        sensitivity=entry.sensitivity,
        redaction_labels=entry.redaction_labels,
        learning_value_tier=entry.learning_value_tier,
        learning_value_reason_codes=entry.learning_value_reason_codes,
        sensitivity_risk_tier=entry.sensitivity_risk_tier,
        assessment_decision=entry.assessment_decision,
        assessment_reason=entry.assessment_reason,
    )


def _render_index_entry_summary(entry: LearningIndexEntry) -> str:
    applies = ", ".join(entry.applies_to)
    triggers = ", ".join(entry.trigger_signals)
    summary = (
        f"### {entry.id} - {entry.problem}\n\n"
        f"- Type: `{entry.learning_type}`\n"
        f"- Source Command: `{entry.source_command}`\n"
        f"- Recurrence Key: `{entry.recurrence_key}`\n"
        f"- Applies To: {applies}\n"
        f"- Trigger Signals: {triggers}\n"
        f"- Signal: `{entry.signal_strength}`\n"
        f"- Occurrence Count: {entry.occurrence_count}\n"
        f"- First Seen: `{entry.first_seen}`\n"
        f"- Last Seen: `{entry.last_seen}`\n"
        f"- Detail: `{entry.detail}`\n\n"
        f"#### Lesson\n\n{entry.lesson}\n"
    )
    if not entry.facets:
        return summary
    facet_lines = [
        f"- {key}: {', '.join(values)}"
        for key, values in entry.facets.items()
        if values
    ]
    return summary + "\n#### Facets\n\n" + "\n".join(facet_lines) + "\n"


def _empty_learning_index_diagnostics() -> dict[str, Any]:
    return {
        "skipped_malformed_entries": 0,
        "file_level_errors": 0,
        "details": [],
        "warnings": [],
    }


def _read_index_entries_with_diagnostics(
    path: Path,
    *,
    tolerate_file_errors: bool = True,
) -> tuple[str, list[LearningIndexEntry], dict[str, Any]]:
    diagnostics = _empty_learning_index_diagnostics()
    if not path.exists():
        return "", [], diagnostics

    try:
        preamble, payloads = _extract_payload_block(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        if not tolerate_file_errors:
            raise
        message = f"learning_index_parse_error:{type(exc).__name__}"
        diagnostics["file_level_errors"] = 1
        diagnostics["warnings"].append(message)
        diagnostics["details"].append(
            {
                "index": None,
                "action": "fallback_internal_store_catalog",
                "reason": str(exc),
            }
        )
        return "", [], diagnostics

    entries: list[LearningIndexEntry] = []
    for index, payload in enumerate(payloads):
        entry_id = payload.get("id") if isinstance(payload, dict) else None
        try:
            if not isinstance(payload, dict):
                raise ValueError("learning index entry is not an object")
            facet_warnings = _learning_facet_payload_warnings(payload.get("facets"))
            for warning in facet_warnings:
                diagnostics["warnings"].append(
                    f"learning_index_entry_{index}_facet_warning:{warning}"
                )
                diagnostics["details"].append(
                    {
                        "index": index,
                        "id": str(entry_id or ""),
                        "action": "ignored_optional_facet",
                        "reason": warning,
                    }
                )
            entry = LearningIndexEntry.from_payload(payload)
        except Exception as exc:  # noqa: BLE001 - diagnostics must report and continue after malformed current entries.
            diagnostics["skipped_malformed_entries"] += 1
            warning = f"learning_index_entry_{index}_skipped:{type(exc).__name__}"
            diagnostics["warnings"].append(warning)
            diagnostics["details"].append(
                {
                    "index": index,
                    "id": str(entry_id or ""),
                    "action": "skipped",
                    "reason": str(exc),
                }
            )
            continue

        entries.append(entry)

    return preamble, entries, diagnostics


def _read_index_entries(path: Path) -> tuple[str, list[LearningIndexEntry]]:
    preamble, entries, _diagnostics = _read_index_entries_with_diagnostics(
        path, tolerate_file_errors=False
    )
    return preamble, entries


def _render_learning_index_file(
    preamble: str, entries: list[LearningIndexEntry]
) -> str:
    payload = [entry.to_payload() for entry in entries]
    sections = [
        preamble.rstrip(),
        "",
        MACHINE_BEGIN,
        json.dumps(payload, ensure_ascii=False, indent=2),
        MACHINE_END,
        "",
        "## Managed Entries",
        "",
    ]
    if not entries:
        sections.append("_No learning index entries recorded yet._")
    else:
        sections.append(
            "\n\n---\n\n".join(_render_index_entry_summary(entry) for entry in entries)
        )
    sections.append("")
    return "\n".join(sections)


def _write_index_entries(
    path: Path, preamble: str, entries: list[LearningIndexEntry]
) -> None:
    atomic_write_text(path, _render_learning_index_file(preamble, entries))


def _read_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    if not path.exists():
        return "", []
    preamble, payloads = _extract_payload_block(path.read_text(encoding="utf-8"))
    return preamble, [LearningEntry.from_payload(payload) for payload in payloads]


def read_learning_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    return _read_entries(path)


def read_learning_index_entries(path: Path) -> tuple[str, list[LearningIndexEntry]]:
    return _read_index_entries(path)


def _write_entries(path: Path, preamble: str, entries: list[LearningEntry]) -> None:
    atomic_write_text(path, _render_learning_file(preamble, entries))


def _seed_from_template(
    destination: Path, template_path: Path, fallback_text: str
) -> bool:
    if destination.exists():
        return False
    if template_path.is_file():
        atomic_write_text(destination, template_path.read_text(encoding="utf-8"))
    else:
        atomic_write_text(destination, fallback_text)
    return True


def ensure_learning_memory_from_templates(
    project_root: Path,
    tracker: Any | None = None,
) -> LearningPaths:
    paths = build_learning_paths(project_root)
    templates_root = project_root / ".specify" / "templates"
    created: list[str] = []

    if _seed_from_template(
        paths.project_rules,
        templates_root / "project-rules-template.md",
        RULES_TEMPLATE_TEXT,
    ):
        created.append("project-rules.md")
    if _seed_from_template(
        paths.confirmed_learnings,
        templates_root / "project-confirmed-learnings-template.md",
        CONFIRMED_LEARNINGS_TEMPLATE_TEXT,
    ):
        created.append("learnings/confirmed.md")
    if _seed_from_template(
        paths.learning_index,
        templates_root / "project-learnings-index-template.md",
        LEARNING_INDEX_TEMPLATE_TEXT,
    ):
        created.append("learnings/INDEX.md")

    if tracker:
        tracker.add("learning-memory", "Project learning memory")
        if created:
            tracker.complete("learning-memory", ", ".join(created))
        else:
            tracker.skip("learning-memory", "existing files preserved")

    return paths


def ensure_learning_runtime_files(project_root: Path) -> LearningPaths:
    paths = build_learning_paths(project_root)
    _seed_from_template(paths.candidates, Path(""), CANDIDATES_TEMPLATE_TEXT)
    _seed_from_template(paths.review, Path(""), REVIEW_TEMPLATE_TEXT)
    return paths


def ensure_learning_files(
    project_root: Path,
    *,
    include_runtime: bool = True,
    tracker: Any | None = None,
) -> LearningPaths:
    with interprocess_lock(_learning_lock_path(project_root)):
        return _ensure_learning_files_unlocked(
            project_root,
            include_runtime=include_runtime,
            tracker=tracker,
        )


def _ensure_learning_files_unlocked(
    project_root: Path,
    *,
    include_runtime: bool = True,
    tracker: Any | None = None,
) -> LearningPaths:
    paths = ensure_learning_memory_from_templates(project_root, tracker=tracker)
    _migrate_legacy_confirmed_learnings_unlocked(project_root, paths)
    if include_runtime:
        ensure_learning_runtime_files(project_root)
    return paths


def _learning_lock_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / ".learning.lock"


def _merge_distinct_evidence(current: str, legacy: str) -> str:
    current = str(current or "").strip()
    legacy = str(legacy or "").strip()
    if not current:
        return legacy
    if not legacy or legacy in current:
        return current
    if current in legacy:
        return legacy
    return f"{current}\n\nLegacy store evidence:\n{legacy}"


def _merge_legacy_confirmed_entry(
    current: LearningEntry, legacy: LearningEntry
) -> LearningEntry:
    signal_rank = {"low": 0, "medium": 1, "high": 2}
    signal_strength = max(
        (current.signal_strength, legacy.signal_strength),
        key=lambda value: signal_rank.get(value, -1),
    )
    first_seen = min(
        (value for value in (current.first_seen, legacy.first_seen) if value),
        default=current.first_seen or legacy.first_seen,
    )
    last_seen = max(
        (value for value in (current.last_seen, legacy.last_seen) if value),
        default=current.last_seen or legacy.last_seen,
    )
    redaction_labels = _merge_redaction_labels(
        current.redaction_labels, legacy.redaction_labels
    )
    assessment_fields = _merge_assessment_fields(
        current, legacy, redaction_labels
    )

    return LearningEntry(
        id=current.id,
        summary=current.summary or legacy.summary,
        learning_type=current.learning_type or legacy.learning_type,
        source_command=current.source_command or legacy.source_command,
        evidence=_merge_distinct_evidence(current.evidence, legacy.evidence),
        recurrence_key=current.recurrence_key,
        default_scope=current.default_scope or legacy.default_scope,
        applies_to=sorted(dict.fromkeys([*current.applies_to, *legacy.applies_to])),
        signal_strength=signal_strength,
        status="confirmed",
        first_seen=first_seen,
        last_seen=last_seen,
        occurrence_count=max(current.occurrence_count, legacy.occurrence_count),
        pain_score=max(current.pain_score, legacy.pain_score),
        false_starts=sorted(
            dict.fromkeys([*current.false_starts, *legacy.false_starts])
        ),
        rejected_paths=sorted(
            dict.fromkeys([*current.rejected_paths, *legacy.rejected_paths])
        ),
        decisive_signal=current.decisive_signal or legacy.decisive_signal,
        root_cause_family=current.root_cause_family or legacy.root_cause_family,
        injection_targets=sorted(
            dict.fromkeys([*current.injection_targets, *legacy.injection_targets])
        ),
        promotion_hint=current.promotion_hint or legacy.promotion_hint,
        problem=current.problem or legacy.problem,
        recommended_action=current.recommended_action or legacy.recommended_action,
        avoid=sorted(dict.fromkeys([*current.avoid, *legacy.avoid])),
        trigger_signals=sorted(
            dict.fromkeys([*current.trigger_signals, *legacy.trigger_signals])
        ),
        success_criteria=sorted(
            dict.fromkeys([*current.success_criteria, *legacy.success_criteria])
        ),
        exceptions=sorted(dict.fromkeys([*current.exceptions, *legacy.exceptions])),
        facets=_merge_learning_facets(current.facets, legacy.facets),
        sensitivity=SENSITIVITY_SANITIZED
        if redaction_labels
        else current.sensitivity
        if current.sensitivity == SENSITIVITY_SANITIZED
        else legacy.sensitivity,
        redaction_labels=redaction_labels,
        **assessment_fields,
    )


def _migrate_legacy_confirmed_learnings_unlocked(
    project_root: Path, paths: LearningPaths
) -> None:
    """Merge the pre-index Learning store while the caller holds the runtime lock."""

    legacy_path = project_root / ".specify" / "memory" / "project-learnings.md"
    if not legacy_path.is_file():
        return

    _legacy_preamble, legacy_entries = _read_entries(legacy_path)
    if not legacy_entries:
        return

    preamble, confirmed_entries = _read_entries(paths.confirmed_learnings)
    confirmed_by_key = {
        entry.recurrence_key: index for index, entry in enumerate(confirmed_entries)
    }
    migrated_entries: list[LearningEntry] = []
    changed = False

    for legacy_entry in legacy_entries:
        legacy_entry.recurrence_key = legacy_entry.recurrence_key.strip().lower()
        legacy_entry.status = "confirmed"
        existing_index = confirmed_by_key.get(legacy_entry.recurrence_key)
        if existing_index is None:
            confirmed_by_key[legacy_entry.recurrence_key] = len(confirmed_entries)
            confirmed_entries.append(legacy_entry)
            stored = legacy_entry
            changed = True
        else:
            existing = confirmed_entries[existing_index]
            stored = _merge_legacy_confirmed_entry(existing, legacy_entry)
            if stored.to_payload() != existing.to_payload():
                confirmed_entries[existing_index] = stored
                changed = True
        migrated_entries.append(stored)

    if changed:
        _write_entries(
            paths.confirmed_learnings,
            preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
            confirmed_entries,
        )

    for entry in migrated_entries:
        _sync_learning_index_detail(paths, entry)


def _merge_assessment_fields(
    primary: LearningEntry | LearningIndexEntry,
    secondary: LearningEntry | LearningIndexEntry,
    redaction_labels: list[str],
) -> dict[str, Any]:
    tier = primary.learning_value_tier or secondary.learning_value_tier
    reasons = (
        primary.learning_value_reason_codes or secondary.learning_value_reason_codes
    )
    decision = primary.assessment_decision or secondary.assessment_decision
    decision_reason = primary.assessment_reason or secondary.assessment_reason
    if not tier or not reasons or not decision or not decision_reason:
        return {
            "learning_value_tier": "",
            "learning_value_reason_codes": [],
            "sensitivity_risk_tier": "",
            "assessment_decision": "",
            "assessment_reason": "",
        }
    risk_tier = _assessment_risk_tier(redaction_labels)
    if redaction_labels and decision == "capture-safe":
        decision = "capture-sanitized"
        decision_reason = "valuable_after_abstraction"
    elif not redaction_labels and decision == "capture-sanitized":
        decision = "capture-safe"
        decision_reason = "safe_content"
    return {
        "learning_value_tier": tier,
        "learning_value_reason_codes": list(reasons),
        "sensitivity_risk_tier": risk_tier,
        "assessment_decision": decision,
        "assessment_reason": decision_reason,
    }


def _scrub_learning_entry_for_policy(
    entry: LearningEntry, policy: LearningPolicy
) -> LearningEntry:
    payload = entry.to_payload()
    labels = set(entry.redaction_labels)
    safe_source_command, source_command_labels = _safe_review_command_with_labels(
        entry.source_command, policy
    )
    payload["source_command"] = safe_source_command
    labels.update(source_command_labels)
    safe_applies_to: list[str] = []
    for command in entry.applies_to:
        safe_command, command_labels = _safe_review_command_with_labels(
            command, policy
        )
        safe_applies_to.append(safe_command)
        labels.update(command_labels)
    payload["applies_to"] = safe_applies_to
    for key in (
        "summary",
        "evidence",
        "default_scope",
        "decisive_signal",
        "root_cause_family",
        "promotion_hint",
        "problem",
        "recommended_action",
    ):
        safe, field_labels = sanitize_agent_text(str(payload.get(key) or ""), policy=policy)
        payload[key] = safe
        labels.update(field_labels)
    for key in (
        "false_starts",
        "rejected_paths",
        "injection_targets",
        "avoid",
        "trigger_signals",
        "success_criteria",
        "exceptions",
    ):
        safe_values, field_labels = _sanitize_list_with_labels(
            _coerce_str_list(payload.get(key)), policy=policy
        )
        payload[key] = safe_values
        labels.update(field_labels)
    payload["facets"] = _sanitize_learning_facets(
        normalize_learning_facets(payload.get("facets")), policy=policy
    )
    safe_recurrence, recurrence_labels = _canonicalize_recurrence_key(
        entry.recurrence_key, policy=policy
    )
    payload["recurrence_key"] = safe_recurrence
    labels.update(recurrence_labels)
    payload["redaction_labels"] = sorted(labels)
    payload["sensitivity"] = "sanitized" if labels else "safe"
    if payload.get("learning_value_tier"):
        payload["sensitivity_risk_tier"] = _assessment_risk_tier(labels)
        if labels and payload.get("assessment_decision") == "capture-safe":
            payload["assessment_decision"] = "capture-sanitized"
            payload["assessment_reason"] = "valuable_after_abstraction"
    return LearningEntry.from_payload(payload)


def _scrub_learning_index_for_policy(
    entry: LearningIndexEntry, policy: LearningPolicy
) -> LearningIndexEntry:
    payload = entry.to_payload()
    labels = set(entry.redaction_labels)
    safe_source_command, source_command_labels = _safe_review_command_with_labels(
        entry.source_command, policy
    )
    payload["source_command"] = safe_source_command
    labels.update(source_command_labels)
    safe_applies_to: list[str] = []
    for command in entry.applies_to:
        safe_command, command_labels = _safe_review_command_with_labels(
            command, policy
        )
        safe_applies_to.append(safe_command)
        labels.update(command_labels)
    payload["applies_to"] = safe_applies_to
    for key in ("id", "problem", "lesson", "detail"):
        safe, field_labels = sanitize_agent_text(str(payload.get(key) or ""), policy=policy)
        payload[key] = safe
        labels.update(field_labels)
    safe_signals, signal_labels = _sanitize_list_with_labels(
        entry.trigger_signals, policy=policy
    )
    payload["trigger_signals"] = safe_signals
    labels.update(signal_labels)
    payload["facets"] = _sanitize_learning_facets(entry.facets, policy=policy)
    safe_recurrence, recurrence_labels = _canonicalize_recurrence_key(
        entry.recurrence_key, policy=policy
    )
    payload["recurrence_key"] = safe_recurrence
    labels.update(recurrence_labels)
    payload["redaction_labels"] = sorted(labels)
    payload["sensitivity"] = "sanitized" if labels else "safe"
    if payload.get("learning_value_tier"):
        payload["sensitivity_risk_tier"] = _assessment_risk_tier(labels)
        if labels and payload.get("assessment_decision") == "capture-safe":
            payload["assessment_decision"] = "capture-sanitized"
            payload["assessment_reason"] = "valuable_after_abstraction"
    return LearningIndexEntry.from_payload(payload)


def _merge_entry(
    existing: LearningEntry, new_entry: LearningEntry, *, status: str | None = None
) -> LearningEntry:
    merged_applies = sorted(
        dict.fromkeys([*existing.applies_to, *new_entry.applies_to])
    )
    merged_false_starts = sorted(
        dict.fromkeys([*existing.false_starts, *new_entry.false_starts])
    )
    merged_rejected_paths = sorted(
        dict.fromkeys([*existing.rejected_paths, *new_entry.rejected_paths])
    )
    merged_injection_targets = sorted(
        dict.fromkeys([*existing.injection_targets, *new_entry.injection_targets])
    )
    merged_avoid = sorted(dict.fromkeys([*existing.avoid, *new_entry.avoid]))
    merged_trigger_signals = sorted(
        dict.fromkeys([*existing.trigger_signals, *new_entry.trigger_signals])
    )
    merged_success_criteria = sorted(
        dict.fromkeys([*existing.success_criteria, *new_entry.success_criteria])
    )
    merged_exceptions = sorted(
        dict.fromkeys([*existing.exceptions, *new_entry.exceptions])
    )
    merged_status = status or existing.status
    merged_signal = (
        "high"
        if "high" in {existing.signal_strength, new_entry.signal_strength}
        else "medium"
        if "medium" in {existing.signal_strength, new_entry.signal_strength}
        else "low"
    )
    redaction_labels = _merge_redaction_labels(
        existing.redaction_labels, new_entry.redaction_labels
    )
    assessment_fields = _merge_assessment_fields(
        new_entry, existing, redaction_labels
    )
    return LearningEntry(
        id=existing.id,
        summary=new_entry.summary or existing.summary,
        learning_type=existing.learning_type,
        source_command=new_entry.source_command or existing.source_command,
        evidence=new_entry.evidence or existing.evidence,
        recurrence_key=existing.recurrence_key,
        default_scope=new_entry.default_scope or existing.default_scope,
        applies_to=merged_applies,
        signal_strength=merged_signal,
        status=merged_status,
        first_seen=existing.first_seen,
        last_seen=new_entry.last_seen,
        occurrence_count=existing.occurrence_count + 1,
        pain_score=max(existing.pain_score, new_entry.pain_score),
        false_starts=merged_false_starts,
        rejected_paths=merged_rejected_paths,
        decisive_signal=new_entry.decisive_signal or existing.decisive_signal,
        root_cause_family=new_entry.root_cause_family or existing.root_cause_family,
        injection_targets=merged_injection_targets,
        promotion_hint=new_entry.promotion_hint or existing.promotion_hint,
        problem=new_entry.problem or existing.problem,
        recommended_action=new_entry.recommended_action or existing.recommended_action,
        avoid=merged_avoid,
        trigger_signals=merged_trigger_signals,
        success_criteria=merged_success_criteria,
        exceptions=merged_exceptions,
        facets=_merge_learning_facets(existing.facets, new_entry.facets),
        sensitivity=SENSITIVITY_SANITIZED
        if redaction_labels
        else existing.sensitivity
        if existing.sensitivity == SENSITIVITY_SANITIZED
        else new_entry.sensitivity,
        redaction_labels=redaction_labels,
        **assessment_fields,
    )


def _upsert_entry(
    entries: list[LearningEntry], new_entry: LearningEntry, *, status: str | None = None
) -> tuple[list[LearningEntry], LearningEntry]:
    updated = list(entries)
    for index, existing in enumerate(updated):
        if existing.recurrence_key == new_entry.recurrence_key:
            merged = _merge_entry(existing, new_entry, status=status)
            updated[index] = merged
            return updated, merged
    if status:
        new_entry.status = status
    updated.append(new_entry)
    return updated, new_entry


def _merge_index_entry(
    existing: LearningIndexEntry, new_entry: LearningIndexEntry
) -> LearningIndexEntry:
    redaction_labels = _merge_redaction_labels(
        existing.redaction_labels, new_entry.redaction_labels
    )
    assessment_fields = _merge_assessment_fields(
        new_entry, existing, redaction_labels
    )
    return LearningIndexEntry(
        id=existing.id,
        problem=new_entry.problem or existing.problem,
        lesson=new_entry.lesson or existing.lesson,
        learning_type=existing.learning_type,
        source_command=new_entry.source_command or existing.source_command,
        recurrence_key=existing.recurrence_key,
        applies_to=sorted(dict.fromkeys([*existing.applies_to, *new_entry.applies_to])),
        trigger_signals=sorted(
            dict.fromkeys([*existing.trigger_signals, *new_entry.trigger_signals])
        ),
        detail=existing.detail,
        first_seen=existing.first_seen,
        last_seen=new_entry.last_seen,
        occurrence_count=new_entry.occurrence_count,
        signal_strength="high"
        if "high" in {existing.signal_strength, new_entry.signal_strength}
        else "medium"
        if "medium" in {existing.signal_strength, new_entry.signal_strength}
        else "low",
        facets=_merge_learning_facets(existing.facets, new_entry.facets),
        sensitivity=SENSITIVITY_SANITIZED
        if redaction_labels
        else existing.sensitivity
        if existing.sensitivity == SENSITIVITY_SANITIZED
        else new_entry.sensitivity,
        redaction_labels=redaction_labels,
        **assessment_fields,
    )


def _upsert_index_entry(
    entries: list[LearningIndexEntry], new_entry: LearningIndexEntry
) -> tuple[list[LearningIndexEntry], LearningIndexEntry]:
    updated = list(entries)
    for index, existing in enumerate(updated):
        if existing.recurrence_key == new_entry.recurrence_key:
            merged = _merge_index_entry(existing, new_entry)
            updated[index] = merged
            return updated, merged
    updated.append(new_entry)
    return updated, new_entry


def _render_learning_detail(
    entry: LearningEntry, index_entry: LearningIndexEntry
) -> str:
    payload = [entry.to_payload()]
    false_starts = (
        "\n".join(f"- {item}" for item in entry.false_starts)
        or "_No false starts recorded._"
    )
    rejected_paths = (
        "\n".join(f"- {item}" for item in entry.rejected_paths)
        or "_No rejected paths recorded._"
    )
    avoid = (
        "\n".join(f"- {item}" for item in entry.avoid)
        or "_No explicit avoid list recorded._"
    )
    success = (
        "\n".join(f"- {item}" for item in entry.success_criteria)
        or "_No explicit success criteria recorded._"
    )
    exceptions = (
        "\n".join(f"- {item}" for item in entry.exceptions)
        or "_No exceptions recorded._"
    )
    triggers = (
        "\n".join(f"- {item}" for item in index_entry.trigger_signals)
        or "_No trigger signals recorded._"
    )
    facets = (
        "\n".join(
            f"- {key}: {', '.join(values)}"
            for key, values in entry.facets.items()
            if values
        )
        or "_No structured facets recorded._"
    )
    return "\n".join(
        [
            f"# {index_entry.problem}",
            "",
            MACHINE_BEGIN,
            json.dumps(payload, ensure_ascii=False, indent=2),
            MACHINE_END,
            "",
            "## Problem",
            "",
            index_entry.problem,
            "",
            "## Lesson",
            "",
            index_entry.lesson,
            "",
            "## Recommended Action",
            "",
            entry.recommended_action or index_entry.lesson,
            "",
            "## When To Apply",
            "",
            ", ".join(index_entry.applies_to),
            "",
            "## Trigger Signals",
            "",
            triggers,
            "",
            "## Structured Facets",
            "",
            facets,
            "",
            "## Evidence",
            "",
            entry.evidence,
            "",
            "## Prevention Or Recovery",
            "",
            f"Decisive signal: {entry.decisive_signal or 'not recorded'}",
            "",
            "False starts:",
            false_starts,
            "",
            "Rejected paths:",
            rejected_paths,
            "",
            "Avoid:",
            avoid,
            "",
            "## Success Criteria",
            "",
            success,
            "",
            "## Exceptions",
            "",
            exceptions,
            "",
        ]
    )


def _is_valid_detail_ref(detail_ref: str) -> bool:
    detail_ref = str(detail_ref)
    if not detail_ref.startswith("./"):
        return False
    detail_name = detail_ref.removeprefix("./")
    return bool(re.fullmatch(r"learn-[A-Za-z0-9][A-Za-z0-9._-]*\.md", detail_name))


def _detail_path_for_ref(learning_dir: Path, detail_ref: str) -> Path:
    return learning_dir / str(detail_ref).removeprefix("./")


def _detail_ref_resolves_inside(learning_dir: Path, detail_ref: str) -> bool:
    return (
        _detail_path_for_ref(learning_dir, detail_ref)
        .resolve()
        .is_relative_to(learning_dir.resolve())
    )


def _normalized_detail_path_key(learning_dir: Path, detail_ref: str) -> str:
    return str(_detail_path_for_ref(learning_dir, detail_ref).resolve()).casefold()


def _repair_detail_ref_from_learning(
    learning_dir: Path, entry: LearningEntry, index_entry: LearningIndexEntry
) -> None:
    if _is_valid_detail_ref(index_entry.detail) and _detail_ref_resolves_inside(
        learning_dir, index_entry.detail
    ):
        return
    index_entry.id = _learning_index_id(entry.recurrence_key, entry.first_seen)
    index_entry.detail = _detail_ref_for_index_id(index_entry.id)
    if not _is_valid_detail_ref(index_entry.detail) or not _detail_ref_resolves_inside(
        learning_dir, index_entry.detail
    ):
        raise ValueError("learning detail path escapes learning memory directory")


def _write_learning_detail(
    paths: LearningPaths, entry: LearningEntry, index_entry: LearningIndexEntry
) -> Path:
    learning_dir = paths.learning_index.parent
    _repair_detail_ref_from_learning(learning_dir, entry, index_entry)
    detail_path = _detail_path_for_ref(learning_dir, index_entry.detail)
    atomic_write_text(detail_path, _render_learning_detail(entry, index_entry))
    return detail_path


def _detail_ref_used_by_other(
    entries: list[LearningIndexEntry],
    detail_ref: str,
    recurrence_key: str,
    learning_dir: Path,
) -> bool:
    detail_key = _normalized_detail_path_key(learning_dir, detail_ref)
    return any(
        entry.recurrence_key != recurrence_key
        and _normalized_detail_path_key(learning_dir, entry.detail) == detail_key
        for entry in entries
    )


def _unused_detail_ref(
    entries: list[LearningIndexEntry],
    recurrence_key: str,
    first_seen: str,
    learning_dir: Path,
) -> tuple[str, str]:
    base_id = _learning_index_id(recurrence_key, first_seen)
    candidate_id = base_id
    candidate_detail = _detail_ref_for_index_id(candidate_id)
    suffix = 2
    while _detail_ref_used_by_other(
        entries, candidate_detail, recurrence_key, learning_dir
    ):
        candidate_id = f"{base_id}-{suffix}"
        candidate_detail = _detail_ref_for_index_id(candidate_id)
        suffix += 1
    return candidate_id, candidate_detail


def _sync_learning_index_detail(
    paths: LearningPaths,
    stored: LearningEntry,
    *,
    policy: LearningPolicy | None = None,
) -> tuple[LearningIndexEntry, Path]:
    active_policy = policy or default_learning_policy()
    stored = _scrub_learning_entry_for_policy(stored, active_policy)
    index_preamble, index_entries = _read_index_entries(paths.learning_index)
    index_entries = [
        _scrub_learning_index_for_policy(item, active_policy)
        for item in index_entries
    ]
    index_entries, stored_index = _upsert_index_entry(
        index_entries, _index_entry_from_learning(stored)
    )
    learning_dir = paths.learning_index.parent
    _repair_detail_ref_from_learning(learning_dir, stored, stored_index)
    if _detail_ref_used_by_other(
        index_entries, stored_index.detail, stored_index.recurrence_key, learning_dir
    ):
        stored_index.id, stored_index.detail = _unused_detail_ref(
            index_entries,
            stored.recurrence_key,
            stored.first_seen,
            learning_dir,
        )
        if not _is_valid_detail_ref(
            stored_index.detail
        ) or not _detail_ref_resolves_inside(learning_dir, stored_index.detail):
            raise ValueError("learning detail path escapes learning memory directory")
    if _detail_ref_used_by_other(
        index_entries, stored_index.detail, stored_index.recurrence_key, learning_dir
    ):
        raise ValueError(
            "learning detail ref is already used by another recurrence key"
        )
    detail_path = _write_learning_detail(paths, stored, stored_index)
    _write_index_entries(
        paths.learning_index,
        index_preamble or LEARNING_INDEX_TEMPLATE_TEXT.rstrip(),
        index_entries,
    )
    return stored_index, detail_path


def _remove_by_recurrence(
    entries: list[LearningEntry], recurrence_key: str
) -> list[LearningEntry]:
    return [entry for entry in entries if entry.recurrence_key != recurrence_key]


def _append_review_note(
    path: Path, note: str, *, policy: LearningPolicy | None = None
) -> None:
    timestamp = now_iso()
    if not path.exists():
        atomic_write_text(path, REVIEW_TEMPLATE_TEXT)
    content = path.read_text(encoding="utf-8").rstrip()
    if policy is not None:
        content = sanitize_agent_text(content, policy=policy)[0]
        note = sanitize_agent_text(note, policy=policy)[0]
    content += f"\n- `{timestamp}` {note}\n"
    atomic_write_text(path, content + "\n")


def _format_evidence(title: str, items: list[tuple[str, Any]]) -> str:
    lines = [title]
    for key, value in items:
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            joined = ", ".join(str(item) for item in value if str(item).strip())
            if not joined:
                continue
            lines.append(f"- {key}: {joined}")
            continue
        dumped = str(value).strip()
        if dumped:
            lines.append(f"- {key}: {dumped}")
    return "\n".join(lines)


def _suggest_implement_auto_capture(
    feature_dir: Path,
    *,
    feature_ref: str,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
    tracker_path = feature_dir / "implement-tracker.md"
    if not tracker_path.exists():
        return tracker_path, []

    frontmatter, sections = _load_sectioned_markdown(tracker_path)
    status = str(frontmatter.get("status", "")).strip().lower()
    current_focus = sections.get("Current Focus") or {}
    execution_state = sections.get("Execution State") or {}
    validation = sections.get("Validation") or {}
    blockers = _coerce_dict_list(sections.get("Blockers"))
    open_gaps = _coerce_dict_list(sections.get("Open Gaps"))
    retry_attempts = _coerce_int(execution_state.get("retry_attempts"))
    failed_tasks = _coerce_str_list(execution_state.get("failed_tasks"))
    completed_checks = _coerce_str_list(validation.get("completed_checks"))
    planned_checks = _coerce_str_list(validation.get("planned_checks"))
    current_batch = str(current_focus.get("current_batch", "")).strip()
    goal = str(current_focus.get("goal", "")).strip()

    suggestions: list[AutoCaptureSuggestion] = []
    if status == "resolved" and retry_attempts >= 1 and completed_checks:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="recovery_path",
                summary="Rerun planned validation after implementation recovery before resolving the feature",
                recurrence_key="implement.rerun-validation-after-recovery-before-resolve",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_ref),
                        ("tracker_status", status),
                        ("retry_attempts", retry_attempts),
                        ("current_batch", current_batch),
                        ("goal", goal),
                        ("failed_tasks", failed_tasks),
                        ("completed_checks", completed_checks),
                    ],
                ),
                problem="Implementation recovery can be marked resolved before the planned validation is rerun.",
                recommended_action="Rerun the planned validation after recovery and record green evidence before resolving the feature.",
                trigger_signals=(
                    "implementation retry completed",
                    "recovery before terminal resolution",
                ),
                success_criteria=(
                    "all planned post-recovery checks are recorded green",
                ),
                avoid=("resolving from the code change alone",),
            )
        )
    if (
        retry_attempts >= 1
        and failed_tasks
        and (completed_checks or planned_checks or blockers)
    ):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="pitfall",
                summary="Failed implementation tasks should keep execution in recovery until validation turns green",
                recurrence_key="implement.failed-tasks-keep-recovery-active-until-validation",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_ref),
                        ("tracker_status", status),
                        ("retry_attempts", retry_attempts),
                        ("current_batch", current_batch),
                        ("failed_tasks", failed_tasks),
                        ("planned_checks", planned_checks),
                        ("completed_checks", completed_checks),
                        (
                            "blockers",
                            [
                                item.get("recovery_action", "")
                                for item in blockers
                                if item.get("recovery_action")
                            ],
                        ),
                    ],
                ),
                problem="A failed task can be treated as finished while its recovery validation is still incomplete.",
                recommended_action="Keep execution in recovery, clear the failed task, and rerun its planned checks before continuing.",
                trigger_signals=(
                    "failed task after retry",
                    "validation incomplete after task failure",
                ),
                success_criteria=(
                    "failed tasks are cleared and their planned checks are green",
                ),
                avoid=(
                    "continuing later batches while failed-task validation is unresolved",
                ),
            )
        )
    gap_types = [
        str(item.get("type", "")).strip()
        for item in open_gaps
        if str(item.get("type", "")).strip()
    ]
    planning_gap_types = [
        value
        for value in gap_types
        if value in {"plan_gap", "research_gap", "spec_gap"}
    ]
    if planning_gap_types:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Execution blockers that change task shape must feed back into planning artifacts before implementation resumes",
                recurrence_key="implement.execution-blockers-feed-back-into-planning",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_ref),
                        ("tracker_status", status),
                        ("current_batch", current_batch),
                        ("open_gap_types", planning_gap_types),
                        (
                            "open_gap_summaries",
                            [
                                str(item.get("summary", "")).strip()
                                for item in open_gaps
                                if str(item.get("summary", "")).strip()
                            ],
                        ),
                        (
                            "open_gap_next_actions",
                            [
                                str(item.get("next_action", "")).strip()
                                for item in open_gaps
                                if str(item.get("next_action", "")).strip()
                            ],
                        ),
                    ],
                ),
                problem="An execution blocker can change task shape while implementation continues against stale planning artifacts.",
                recommended_action="Reopen the highest invalid planning stage, update the affected artifacts, then resume implementation.",
                trigger_signals=(
                    "plan gap during implementation",
                    "research gap during implementation",
                    "spec gap during implementation",
                ),
                success_criteria=(
                    "the corrected planning artifacts and tasks reflect the blocker-driven shape change",
                ),
                avoid=(
                    "patching a planning-shape change only inside the current implementation task",
                ),
            )
        )
    blocker_types = [
        str(item.get("type", "")).strip()
        for item in blockers
        if str(item.get("type", "")).strip()
    ]
    if any(value in {"external", "human-action"} for value in blocker_types):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="External or human-action blockers should be treated as explicit implementation constraints instead of repeated technical retries",
                recurrence_key="implement.external-or-human-blockers-are-project-constraints",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_ref),
                        ("tracker_status", status),
                        ("blocker_types", blocker_types),
                        (
                            "blocker_evidence",
                            [
                                str(item.get("evidence", "")).strip()
                                for item in blockers
                                if str(item.get("evidence", "")).strip()
                            ],
                        ),
                        (
                            "recovery_actions",
                            [
                                str(item.get("recovery_action", "")).strip()
                                for item in blockers
                                if str(item.get("recovery_action", "")).strip()
                            ],
                        ),
                    ],
                ),
                problem="A human or external precondition cannot be cleared by repeating technical implementation attempts.",
                recommended_action="Record the owner, exact human steps, unblock condition, and required evidence; stop technical retries until it is satisfied.",
                trigger_signals=("external blocker", "human-action blocker"),
                success_criteria=(
                    "the precondition has explicit completion evidence before implementation resumes",
                ),
                avoid=(
                    "repeating technical retries while the external precondition remains false",
                ),
            )
        )
    return tracker_path, suggestions


def _suggest_quick_auto_capture(
    workspace: Path,
    *,
    workspace_ref: str,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
    status_path = workspace / "STATUS.md"
    if not status_path.exists():
        return status_path, []

    frontmatter, sections = _load_sectioned_markdown(status_path)
    status = str(frontmatter.get("status", "")).strip().lower()
    current_focus = sections.get("Current Focus") or {}
    execution = sections.get("Execution") or {}
    validation = sections.get("Validation") or {}
    retry_attempts = _coerce_int(execution.get("retry_attempts"))
    blocker_reason = str(execution.get("blocker_reason", "")).strip()
    recovery_action = str(execution.get("recovery_action", "")).strip()
    execution_fallback = str(execution.get("execution_fallback", "")).strip()
    completed_checks = _coerce_str_list(validation.get("completed_checks"))
    goal = str(current_focus.get("goal", "")).strip()
    next_action = str(current_focus.get("next_action", "")).strip()

    suggestions: list[AutoCaptureSuggestion] = []
    if (
        status == "resolved"
        and retry_attempts >= 1
        and (completed_checks or blocker_reason or recovery_action)
    ):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="recovery_path",
                summary="Retry the smallest recorded recovery step and rerun scoped checks before resolving a quick task",
                recurrence_key="quick.retry-recovery-step-before-resolve",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from quick STATUS.md",
                    [
                        ("workspace", workspace_ref),
                        ("status", status),
                        ("retry_attempts", retry_attempts),
                        ("goal", goal),
                        ("next_action", next_action),
                        ("blocker_reason", blocker_reason),
                        ("recovery_action", recovery_action),
                        ("completed_checks", completed_checks),
                    ],
                ),
                problem="A quick task can be marked resolved before the recovery step and scoped checks prove the fix.",
                recommended_action="Run the smallest recorded recovery action, then rerun the scoped checks before resolving.",
                trigger_signals=(
                    "quick task recovered after retry",
                    "quick blocker cleared",
                ),
                success_criteria=(
                    "the recorded recovery action is followed by green scoped checks",
                ),
                avoid=("resolving immediately after the retry without validation",),
            )
        )
    if execution_fallback and execution_fallback.lower() != "none":
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="Leader-inline quick-task fallback should preserve the runtime unavailability reason as a reusable execution constraint",
                recurrence_key="quick.leader-inline-fallback-preserves-runtime-unavailability-reason",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from quick STATUS.md",
                    [
                        ("workspace", workspace_ref),
                        ("status", status),
                        ("goal", goal),
                        ("execution_fallback", execution_fallback),
                        ("blocker_reason", blocker_reason),
                        ("recovery_action", recovery_action),
                    ],
                ),
                problem="An inline fallback can hide a reusable runtime limitation and cause future dispatch attempts to repeat the same failure.",
                recommended_action="Check the recorded runtime limitation before dispatch and reuse the approved fallback only while it still applies.",
                trigger_signals=(
                    "leader-inline fallback used",
                    "agent runtime unavailable",
                ),
                success_criteria=(
                    "future routing checks runtime readiness before selecting the fallback",
                ),
                avoid=(
                    "retrying unavailable execution infrastructure without a state change",
                ),
            )
        )
    return status_path, suggestions


WORKFLOW_STATE_AUTO_CAPTURE_COMMANDS = {
    "sp-constitution",
    "sp-specify",
    "sp-clarify",
    "sp-deep-research",
    "sp-plan",
    "sp-checklist",
    "sp-tasks",
    "sp-analyze",
    "sp-accept",
    "sp-prd-scan",
    "sp-prd-build",
    *MAP_WORKFLOW_COMMANDS,
}


def _suggest_workflow_state_auto_capture(
    feature_dir: Path,
    *,
    command_name: str,
    feature_ref: str,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
    state_path = feature_dir / "workflow-state.md"
    if not state_path.exists():
        return state_path, []

    checkpoint = serialize_workflow_state(state_path)
    next_command = str(checkpoint.get("next_command") or "").strip()
    next_action = str(checkpoint.get("next_action") or "").strip()
    route_reason = str(checkpoint.get("route_reason") or "").strip()
    blocked_reason = str(checkpoint.get("blocked_reason") or "").strip()
    if route_reason.casefold() in {
        "none",
        "n/a",
        "not-applicable",
    } or route_reason.startswith("["):
        route_reason = ""
    if blocked_reason.casefold() in {
        "none",
        "n/a",
        "not-applicable",
    } or blocked_reason.startswith("["):
        blocked_reason = ""
    false_starts = _coerce_str_list(checkpoint.get("false_starts"))
    hidden_dependencies = _coerce_str_list(checkpoint.get("hidden_dependencies"))
    reusable_constraints = _coerce_str_list(checkpoint.get("reusable_constraints"))
    trigger_signals = _coerce_str_list(checkpoint.get("trigger_signals"))
    status = str(checkpoint.get("status") or "").strip()
    phase_mode = str(checkpoint.get("phase_mode") or "").strip()

    suggestions: list[AutoCaptureSuggestion] = []
    if next_command and route_reason:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Workflow-state handoff should preserve the exact re-entry reason so later stages do not rediscover why routing changed",
                recurrence_key=f"{command_name}.workflow-state-preserves-reentry-reason",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_ref),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("next_command", next_command),
                        ("next_action", next_action),
                        ("route_reason", route_reason),
                        ("blocked_reason", blocked_reason),
                    ],
                ),
                problem="A changed workflow route can lose its exact re-entry reason between stages or after resume.",
                recommended_action="Preserve the next command, next action, and exact route reason before handoff.",
                trigger_signals=(
                    "next command changed",
                    "route reason recorded",
                    "workflow re-entry",
                ),
                success_criteria=(
                    "the resumed workflow can explain and follow the route without chat history",
                ),
                avoid=("routing from chat memory alone",),
            )
        )
    if blocked_reason and not (next_command and route_reason):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Blocked workflow-state closeout should preserve the blocker as a reusable learning signal",
                recurrence_key=f"{command_name}.workflow-state-preserves-blocked-reason",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_ref),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("blocked_reason", blocked_reason),
                        ("next_command", next_command),
                        ("next_action", next_action),
                    ],
                ),
                problem="A blocked terminal state can lose the blocker detail needed for safe recovery.",
                recommended_action="Preserve the blocker, owner, next action, and unblock condition before stopping.",
                trigger_signals=("workflow blocked", "blocked_reason present"),
                success_criteria=(
                    "resume can continue from the recorded unblock condition",
                ),
                avoid=("reporting blocked without a durable reason",),
            )
        )
    if false_starts:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="false_lead_pattern",
                summary="Workflow-state should preserve false starts so later runs do not repeat the same route or diagnosis loop",
                recurrence_key=f"{command_name}.workflow-state-preserves-false-starts",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_ref),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("false_starts", false_starts),
                        ("next_command", next_command),
                        ("next_action", next_action),
                    ],
                ),
                problem="A later run can repeat a route or diagnosis already disproved by evidence.",
                recommended_action="Check recorded false starts before repeating a route or hypothesis.",
                trigger_signals=(
                    "false start recorded",
                    "hypothesis changed",
                    "route rejected",
                ),
                success_criteria=(
                    "the rejected path is not retried without new contradictory evidence",
                ),
                avoid=("replaying a false start without new evidence",),
            )
        )
    if hidden_dependencies or reusable_constraints:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="Dependencies and reusable constraints discovered in workflow-state should be promoted into shared memory before later work resumes",
                recurrence_key=f"{command_name}.workflow-state-promotes-discovered-constraints",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_ref),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("hidden_dependencies", hidden_dependencies),
                        ("reusable_constraints", reusable_constraints),
                        ("next_command", next_command),
                    ],
                ),
                problem="A hidden dependency or reusable constraint can disappear when it remains only in workflow-local state.",
                recommended_action="Apply the recorded dependency or constraint before planning or changing the affected surface.",
                trigger_signals=(
                    "hidden dependency",
                    "reusable constraint",
                    "cross-workflow dependency",
                ),
                success_criteria=(
                    "downstream work names and honors the dependency or constraint",
                ),
                avoid=("rediscovering the constraint after implementation starts",),
            )
        )
    suggestions.extend(
        _semantic_trigger_suggestions(
            command_name=command_name,
            feature_ref=feature_ref,
            trigger_signals=trigger_signals,
        )
    )
    return state_path, suggestions


def _suggest_debug_auto_capture(
    session_file: Path,
    *,
    session_ref: str,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
    if not session_file.exists():
        return session_file, []

    state = MarkdownPersistenceHandler(session_file.parent).load(session_file)
    validation_summary = summarize_validation_results(
        state.resolution.validation_results
    )
    validation_commands = [item.command for item in state.resolution.validation_results]
    suggestions: list[AutoCaptureSuggestion] = []

    if (
        state.status.value == "resolved"
        and state.resolution.fail_count >= 1
        and validation_summary.failed == 0
        and validation_summary.passed >= 1
    ):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="recovery_path",
                summary="Return to investigation with new evidence after failed verification instead of stacking debug fixes",
                recurrence_key="debug.return-to-investigation-after-failed-verification",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from resolved debug session",
                    [
                        ("session_file", session_ref),
                        ("trigger", state.trigger),
                        ("fail_count", state.resolution.fail_count),
                        ("fix", state.resolution.fix or ""),
                        (
                            "failure_mechanism",
                            state.resolution.root_cause.failure_mechanism
                            if state.resolution.root_cause
                            else "",
                        ),
                        ("validation_commands", validation_commands),
                        (
                            "loop_restoration_proof",
                            state.resolution.loop_restoration_proof,
                        ),
                    ],
                ),
                problem="A failed verification can lead to stacked fixes without returning to the evidence and root-cause model.",
                recommended_action="Return to investigation with the failed check as new evidence, update the hypothesis, then apply one justified fix.",
                trigger_signals=(
                    "debug verification failed before eventual resolution",
                ),
                success_criteria=(
                    "the final fix restores the loop and all recorded validation commands pass",
                ),
                avoid=("stacking another fix without updating the investigation",),
            )
        )
    if state.resolution.fail_count >= 2:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Repeated failed verification should trigger a research checkpoint before another debug fix loop",
                recurrence_key="debug.research-checkpoint-after-repeated-verification-failure",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from resolved debug session",
                    [
                        ("session_file", session_ref),
                        ("trigger", state.trigger),
                        ("fail_count", state.resolution.fail_count),
                        ("validation_commands", validation_commands),
                        (
                            "root_cause_summary",
                            state.resolution.root_cause.summary
                            if state.resolution.root_cause
                            else "",
                        ),
                    ],
                ),
                problem="Repeated failed verification indicates the current debug model or capability evidence is insufficient.",
                recommended_action="Pause the fix loop, open a focused research checkpoint, and return with evidence that changes the hypothesis or implementation chain.",
                trigger_signals=("two or more debug verification failures",),
                success_criteria=(
                    "new evidence resolves the uncertainty before another production fix is attempted",
                ),
                avoid=("repeating the same debug-fix loop with unchanged evidence",),
            )
        )
    if (
        state.status.value == "resolved"
        and state.resolution.fix_scope == "surface-only"
        and state.resolution.rejected_surface_fixes
    ):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="pitfall",
                summary="Surface-only debug fixes are insufficient without loop-restoration proof",
                recurrence_key="debug.surface-only-fixes-need-loop-restoration-proof",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from resolved debug session",
                    [
                        ("session_file", session_ref),
                        ("trigger", state.trigger),
                        (
                            "rejected_surface_fixes",
                            state.resolution.rejected_surface_fixes,
                        ),
                        (
                            "loop_restoration_proof",
                            state.resolution.loop_restoration_proof,
                        ),
                    ],
                ),
                problem="A surface-only fix can suppress the symptom while leaving the broken causal loop unchanged.",
                recommended_action="Reject the surface patch unless loop-restoration proof shows the underlying behavior is restored.",
                trigger_signals=(
                    "surface-only debug fix",
                    "rejected surface fixes present",
                ),
                success_criteria=(
                    "loop-restoration proof and targeted validation demonstrate the causal behavior is fixed",
                ),
                avoid=("accepting symptom disappearance as root-cause resolution",),
            )
        )
    return session_file, suggestions


def is_relevant_to_command(entry: LearningEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to


def is_index_relevant_to_command(entry: LearningIndexEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to


def is_highest_signal(entry: LearningEntry) -> bool:
    return entry.signal_strength == "high" or entry.occurrence_count >= 2


def learning_workflow_policy(command_name: str) -> str:
    """Return the explicit Learning consumption/capture policy for a workflow."""

    normalized = normalize_command_name(command_name)
    return LEARNING_WORKFLOW_POLICIES.get(normalized, "consume-capture")


def _read_entries_if_present(path: Path) -> list[LearningEntry]:
    if not path.is_file():
        return []
    try:
        return _read_entries(path)[1]
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return []


def _learning_catalog(
    project_root: Path,
    *,
    policy: LearningPolicy | None = None,
) -> tuple[
    LearningPaths,
    list[tuple[LearningIndexEntry, LearningEntry | None, str]],
    dict[str, Any],
]:
    """Merge internal Learning stores into one deterministic consumer catalog."""

    active_policy = policy or load_learning_policy(
        project_root, for_write=False
    ).policy
    paths = build_learning_paths(project_root)
    source_layers: list[tuple[str, list[LearningEntry]]] = [
        (
            "candidate",
            [
                _scrub_learning_entry_for_policy(entry, active_policy)
                for entry in _read_entries_if_present(paths.candidates)
            ],
        ),
        (
            "confirmed-learning",
            [
                _scrub_learning_entry_for_policy(entry, active_policy)
                for entry in _read_entries_if_present(paths.confirmed_learnings)
            ],
        ),
        (
            "project-rule",
            [
                _scrub_learning_entry_for_policy(entry, active_policy)
                for entry in _read_entries_if_present(paths.project_rules)
            ],
        ),
    ]
    source_by_key: dict[str, tuple[LearningEntry, str]] = {}
    for layer, entries in source_layers:
        for entry in entries:
            source_by_key[entry.recurrence_key] = (entry, layer)

    if paths.learning_index.is_file():
        _preamble, index_entries, diagnostics = _read_index_entries_with_diagnostics(
            paths.learning_index
        )
    else:
        index_entries = []
        diagnostics = _empty_learning_index_diagnostics()
        diagnostics["warnings"].append(
            "Learning index is missing; run `specify learning ensure` before capture."
        )
    index_entries = [
        _scrub_learning_index_for_policy(entry, active_policy)
        for entry in index_entries
    ]

    catalog: list[tuple[LearningIndexEntry, LearningEntry | None, str]] = []
    seen: set[str] = set()
    for index_entry in index_entries:
        source = source_by_key.get(index_entry.recurrence_key)
        entry, layer = source if source else (None, "index-only")
        catalog.append((index_entry, entry, layer))
        seen.add(index_entry.recurrence_key)

    for recurrence_key, (entry, layer) in source_by_key.items():
        if recurrence_key in seen:
            continue
        catalog.append((_index_entry_from_learning(entry), entry, layer))

    catalog.sort(
        key=lambda item: (
            -item[0].occurrence_count,
            {"high": 0, "medium": 1, "low": 2}.get(item[0].signal_strength, 3),
            item[0].recurrence_key,
        )
    )
    return paths, catalog, diagnostics


def _learning_context_match(
    index_entry: LearningIndexEntry,
    task_context: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    normalized_context = normalize_learning_facets(task_context)
    normalized_facets = normalize_learning_facets(index_entry.facets)
    matched_facets: dict[str, list[str]] = {}
    legacy_signal_tokens = {
        _facet_match_token(signal): signal
        for signal in index_entry.trigger_signals
        if _facet_match_token(signal)
    }
    for facet_key, query_values in normalized_context.items():
        query_tokens = {_facet_match_token(value) for value in query_values}
        stored_values = normalized_facets.get(facet_key, [])
        stored_by_token = {_facet_match_token(value): value for value in stored_values}
        matches = [
            stored_by_token[token]
            for token in sorted(query_tokens & set(stored_by_token))
        ]
        if (
            not matches
            and not stored_values
            and facet_key in {"operation_owners", "components"}
        ):
            matches = [
                legacy_signal_tokens[token]
                for token in sorted(query_tokens & set(legacy_signal_tokens))
            ]
        if matches:
            matched_facets[facet_key] = matches

    matched_values = sum(len(values) for values in matched_facets.values())
    return {
        "matched_facets": matched_facets,
        "matched_dimensions": len(matched_facets),
        "matched_values": matched_values,
        "exact_operation_owner": bool(matched_facets.get("operation_owners")),
    }


def _context_allows_cross_command(match: Mapping[str, Any]) -> bool:
    return (
        bool(match.get("exact_operation_owner"))
        or int(match.get("matched_dimensions") or 0) >= 2
    )


def _assessment_risk_tier(labels: Iterable[str]) -> str:
    label_set = set(labels)
    if not label_set:
        return "none"
    if label_set & {"credential", "private_key", "organization_sensitive"}:
        return "high"
    return "moderate"


def _sanitize_card_for_policy(
    card: dict[str, Any], policy: LearningPolicy
) -> dict[str, Any]:
    sanitized = dict(card)
    labels = set(_coerce_str_list(card.get("redaction_labels")))
    safe_ref, ref_labels = _canonicalize_recurrence_key(
        str(card.get("ref") or ""), policy=policy
    )
    labels.update(ref_labels)
    sanitized["ref"] = safe_ref
    show_argv = sanitized.get("show_argv")
    if isinstance(show_argv, list):
        safe_argv = list(show_argv)
        if "--ref" in safe_argv:
            ref_index = safe_argv.index("--ref") + 1
            if ref_index < len(safe_argv):
                safe_argv[ref_index] = safe_ref
        sanitized["show_argv"] = safe_argv
    for key in ("summary", "action", "why_relevant"):
        if isinstance(sanitized.get(key), str):
            sanitized[key], field_labels = sanitize_agent_text(
                sanitized[key], policy=policy
            )
            labels.update(field_labels)
    trigger_signals = sanitized.get("trigger_signals")
    if isinstance(trigger_signals, list):
        safe_signals, signal_labels = _sanitize_list_with_labels(
            trigger_signals, policy=policy
        )
        sanitized["trigger_signals"] = safe_signals
        labels.update(signal_labels)
    context_match = sanitized.get("context_match")
    if isinstance(context_match, dict):
        context_copy = dict(context_match)
        facets = context_copy.get("matched_facets")
        if isinstance(facets, Mapping):
            context_copy["matched_facets"] = _sanitize_learning_facets(
                facets, policy=policy
            )
        sanitized["context_match"] = context_copy
    sanitized["redaction_labels"] = sorted(labels)
    sanitized["sensitivity"] = "sanitized" if labels else "safe"
    if isinstance(sanitized.get("applies_to"), list):
        sanitized["applies_to"] = [
            _safe_review_command(command, policy)
            for command in sanitized["applies_to"]
        ]
    assessment = sanitized.get("assessment")
    if isinstance(assessment, dict):
        assessment_copy = dict(assessment)
        content_safety = dict(assessment_copy.get("content_safety") or {})
        content_safety.update(
            {
                "sensitivity": "sanitized" if labels else "safe",
                "risk_tier": _assessment_risk_tier(labels),
                "redaction_labels": sorted(labels),
            }
        )
        assessment_copy["content_safety"] = content_safety
        if labels and assessment_copy.get("decision") == "capture-safe":
            assessment_copy["decision"] = "capture-sanitized"
            assessment_copy["decision_reason"] = "valuable_after_abstraction"
        sanitized["assessment"] = assessment_copy
    return sanitized


def _sanitize_detail_for_policy(
    payload: dict[str, Any], policy: LearningPolicy
) -> dict[str, Any]:
    labels = set(
        _coerce_str_list((payload.get("content_safety") or {}).get("redaction_labels"))
        if isinstance(payload.get("content_safety"), dict)
        else []
    )

    def sanitize_value(value: Any) -> Any:
        if isinstance(value, str):
            safe, field_labels = sanitize_agent_text(value, policy=policy)
            labels.update(field_labels)
            return safe
        if isinstance(value, list):
            return [sanitize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: sanitize_value(item) for key, item in value.items()}
        return value

    sanitized = dict(payload)
    for key in ("ref", "id"):
        if isinstance(sanitized.get(key), str):
            safe_key, key_labels = _canonicalize_recurrence_key(
                sanitized[key], policy=policy
            )
            sanitized[key] = safe_key
            labels.update(key_labels)
    if isinstance(sanitized.get("summary"), str):
        sanitized["summary"] = sanitize_value(sanitized["summary"])
    for section in ("guidance", "evidence"):
        if isinstance(sanitized.get(section), dict):
            sanitized[section] = sanitize_value(sanitized[section])
    applicability = sanitized.get("applicability")
    if isinstance(applicability, dict):
        applicability_copy = dict(applicability)
        if isinstance(applicability_copy.get("commands"), list):
            applicability_copy["commands"] = [
                _safe_review_command(command, policy)
                for command in applicability_copy["commands"]
            ]
        for key in ("trigger_signals", "scope", "facets"):
            if key in applicability_copy:
                applicability_copy[key] = sanitize_value(applicability_copy[key])
        sanitized["applicability"] = applicability_copy
    lifecycle = sanitized.get("lifecycle")
    if isinstance(lifecycle, dict):
        lifecycle_copy = dict(lifecycle)
        for key in ("injection_targets", "promotion_hint"):
            if key in lifecycle_copy:
                lifecycle_copy[key] = sanitize_value(lifecycle_copy[key])
        sanitized["lifecycle"] = lifecycle_copy
    provenance = sanitized.get("provenance")
    if isinstance(provenance, dict):
        provenance_copy = dict(provenance)
        if isinstance(provenance_copy.get("source_command"), str):
            provenance_copy["source_command"] = _safe_review_command(
                provenance_copy["source_command"], policy
            )
        sanitized["provenance"] = provenance_copy
    if isinstance(sanitized.get("detail_path"), str):
        sanitized["detail_path"] = sanitize_value(sanitized["detail_path"])
    content_safety = dict(sanitized.get("content_safety") or {})
    content_safety.update(
        {
            "sensitivity": "sanitized" if labels else "safe",
            "redaction_labels": sorted(labels),
        }
    )
    sanitized["content_safety"] = content_safety
    assessment = sanitized.get("assessment")
    if isinstance(assessment, dict):
        assessment_copy = dict(assessment)
        assessment_copy["content_safety"] = {
            **content_safety,
            "risk_tier": _assessment_risk_tier(labels),
        }
        if labels and assessment_copy.get("decision") == "capture-safe":
            assessment_copy["decision"] = "capture-sanitized"
            assessment_copy["decision_reason"] = "valuable_after_abstraction"
        sanitized["assessment"] = assessment_copy
    return sanitized


def _learning_summary_card(
    index_entry: LearningIndexEntry,
    entry: LearningEntry | None,
    source_layer: str,
    *,
    command_name: str | None,
    context_match: Mapping[str, Any] | None = None,
    cross_command: bool = False,
) -> dict[str, Any]:
    status = entry.status if entry else "indexed"
    summary = entry.summary if entry else index_entry.problem
    action = (
        entry.recommended_action
        if entry and entry.recommended_action
        else index_entry.lesson
    )
    redaction_labels = (
        entry.redaction_labels if entry else index_entry.redaction_labels
    )
    sensitivity = (
        SENSITIVITY_SANITIZED
        if redaction_labels
        else entry.sensitivity
        if entry
        else index_entry.sensitivity
    )
    card: dict[str, Any] = {
        "ref": index_entry.recurrence_key,
        "summary": summary,
        "action": action,
        "type": index_entry.learning_type,
        "status": status,
        "signal": index_entry.signal_strength,
        "occurrences": index_entry.occurrence_count,
        "applies_to": index_entry.applies_to,
        "trigger_signals": index_entry.trigger_signals,
        "source_layer": source_layer,
        "sensitivity": sensitivity,
        "redaction_labels": redaction_labels,
        "show_argv": [
            "specify",
            "learning",
            "show",
            "--ref",
            index_entry.recurrence_key,
            "--format",
            "json",
        ],
    }
    assessment = (
        entry.assessment_payload() if entry else index_entry.assessment_payload()
    )
    if assessment is not None:
        card["assessment"] = assessment
    if context_match and int(context_match.get("matched_dimensions") or 0) > 0:
        rendered_matches = ", ".join(
            f"{key}={value}"
            for key, values in context_match.get("matched_facets", {}).items()
            for value in values
        )
        card["context_match"] = {
            "matched_facets": dict(context_match.get("matched_facets", {})),
            "matched_dimensions": int(context_match.get("matched_dimensions") or 0),
            "matched_values": int(context_match.get("matched_values") or 0),
            "exact_operation_owner": bool(context_match.get("exact_operation_owner")),
            "cross_command": cross_command,
        }
        card["why_relevant"] = f"task context matched {rendered_matches}" + (
            " across command applicability" if cross_command else ""
        )
    elif command_name:
        card["why_relevant"] = f"applies to {command_name}"
    return card


def list_learning_summaries(
    project_root: Path,
    *,
    command_name: str | None = None,
    learning_type: str | None = None,
    status: str | None = None,
    query: str | None = None,
    task_context: Mapping[str, Iterable[str]] | None = None,
    cursor: int = 0,
    limit: int = 50,
    include_all: bool = False,
) -> dict[str, Any]:
    """Return compact Learning cards; detail expansion is owned by ``show``."""

    policy_result = load_learning_policy(project_root, for_write=False)
    policy = policy_result.policy
    normalized_command = (
        _safe_review_command(command_name, policy) if command_name else None
    )
    normalized_type = normalize_learning_type(learning_type) if learning_type else None
    normalized_status = status.strip().lower() if status else None
    if normalized_status and normalized_status not in {*LEARNING_STATUSES, "indexed"}:
        raise ValueError(f"unsupported learning status '{status}'")
    normalized_query = query.strip().casefold() if query else ""
    normalized_context = normalize_learning_facets(task_context)
    safe_query = (
        sanitize_agent_text(query.strip(), policy=policy)[0] if query else ""
    )
    safe_context = _sanitize_learning_facets(normalized_context, policy=policy)
    cursor = max(0, int(cursor))
    if include_all:
        limit = 0
    elif limit < 1:
        raise ValueError("limit must be at least 1 unless --all is used")
    else:
        limit = min(int(limit), 200)

    _paths, catalog, diagnostics = _learning_catalog(project_root, policy=policy)
    ranked_cards: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
    for catalog_index, (index_entry, entry, source_layer) in enumerate(catalog):
        command_match = bool(
            normalized_command
            and is_index_relevant_to_command(index_entry, normalized_command)
        )
        context_match = _learning_context_match(index_entry, normalized_context)
        cross_command = False
        if normalized_command and not command_match:
            if not normalized_context or not _context_allows_cross_command(
                context_match
            ):
                continue
            cross_command = True
        elif not normalized_command and normalized_context:
            if int(context_match.get("matched_dimensions") or 0) == 0:
                continue
        if normalized_type and index_entry.learning_type != normalized_type:
            continue
        entry_status = entry.status if entry else "indexed"
        if normalized_status and entry_status != normalized_status:
            continue
        searchable = " ".join(
            [
                index_entry.recurrence_key,
                index_entry.problem,
                index_entry.lesson,
                index_entry.learning_type,
                *index_entry.trigger_signals,
                *index_entry.applies_to,
                *(value for values in index_entry.facets.values() for value in values),
            ]
        ).casefold()
        if normalized_query and normalized_query not in searchable:
            continue
        card = _learning_summary_card(
            index_entry,
            entry,
            source_layer,
            command_name=normalized_command,
            context_match=context_match if normalized_context else None,
            cross_command=cross_command,
        )
        rank = (
            -int(bool(context_match.get("exact_operation_owner"))),
            -int(context_match.get("matched_dimensions") or 0),
            -int(context_match.get("matched_values") or 0),
            catalog_index,
        )
        ranked_cards.append((rank, card))

    if normalized_context:
        ranked_cards.sort(key=lambda item: item[0])
    cards = [
        _sanitize_card_for_policy(card, policy) for _rank, card in ranked_cards
    ]

    total = len(cards)
    page = cards[cursor:] if include_all else cards[cursor : cursor + limit]
    next_cursor = None if cursor + len(page) >= total else cursor + len(page)
    next_argv: list[str] | None = None
    if next_cursor is not None:
        next_argv = ["specify", "learning", "list"]
        if normalized_command:
            next_argv.extend(["--command", normalized_command])
        if normalized_type:
            next_argv.extend(["--type", normalized_type])
        if normalized_status:
            next_argv.extend(["--status", normalized_status])
        if query:
            next_argv.extend(["--query", safe_query])
        next_argv.extend(_learning_context_argv(safe_context))
        next_argv.extend(
            ["--cursor", str(next_cursor), "--limit", str(limit), "--format", "json"]
        )
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/summaryList",
        "command": normalized_command,
        "policy": learning_workflow_policy(normalized_command)
        if normalized_command
        else None,
        "filters": {
            "type": normalized_type,
            "status": normalized_status,
            "query": safe_query or None,
        },
        "pagination": {
            "cursor": cursor,
            "limit": None if include_all else limit,
            "returned": len(page),
            "total": total,
            "next_cursor": next_cursor,
            "next_argv": next_argv,
        },
        "items": page,
        "warnings": [
            *list(diagnostics.get("warnings", [])),
            *policy_result.warnings,
        ],
    }
    if safe_context:
        payload["task_context"] = safe_context
    from .launcher import bind_project_launcher_payload

    return bind_project_launcher_payload(payload, project_root)


def show_learning_detail(project_root: Path, *, learning_ref: str) -> dict[str, Any]:
    """Expand exactly one Learning into an agent-oriented detail record."""

    policy_result = load_learning_policy(project_root, for_write=False)
    policy = policy_result.policy
    requested_raw = learning_ref.strip()
    requested, _request_labels = _canonicalize_recurrence_key(
        requested_raw, policy=policy
    )
    requested = requested or requested_raw
    if not requested:
        raise ValueError("learning ref is required")
    paths, catalog, diagnostics = _learning_catalog(project_root, policy=policy)
    match = next(
        (
            item
            for item in catalog
            if requested
            in {
                item[0].id,
                item[0].recurrence_key,
                _canonicalize_recurrence_key(item[0].id, policy=policy)[0],
                _canonicalize_recurrence_key(
                    item[0].recurrence_key, policy=policy
                )[0],
            }
        ),
        None,
    )
    if match is None:
        raise ValueError(f"learning '{requested}' not found")
    index_entry, entry, source_layer = match

    detail_path: Path | None = None
    if _is_valid_detail_ref(index_entry.detail) and _detail_ref_resolves_inside(
        paths.learning_index.parent, index_entry.detail
    ):
        candidate_path = _detail_path_for_ref(
            paths.learning_index.parent, index_entry.detail
        )
        if candidate_path.is_file():
            detail_path = candidate_path
            detail_entries = [
                _scrub_learning_entry_for_policy(item, policy)
                for item in _read_entries_if_present(candidate_path)
            ]
            detail_entry = next(
                (
                    item
                    for item in detail_entries
                    if item.recurrence_key == index_entry.recurrence_key
                ),
                None,
            )
            if detail_entry is not None:
                entry = detail_entry

    problem = entry.problem if entry and entry.problem else index_entry.problem
    action = (
        entry.recommended_action
        if entry and entry.recommended_action
        else index_entry.lesson
    )
    applicability = {
        "commands": index_entry.applies_to,
        "trigger_signals": index_entry.trigger_signals,
        "scope": entry.default_scope if entry else "",
    }
    detail_facets = entry.facets if entry and entry.facets else index_entry.facets
    if detail_facets:
        applicability["facets"] = detail_facets
    redaction_labels = (
        entry.redaction_labels if entry else index_entry.redaction_labels
    )
    sensitivity = (
        SENSITIVITY_SANITIZED
        if redaction_labels
        else entry.sensitivity
        if entry
        else index_entry.sensitivity
    )
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/detailRecord",
        "ref": index_entry.recurrence_key,
        "id": index_entry.id,
        "summary": entry.summary if entry else index_entry.problem,
        "type": index_entry.learning_type,
        "status": entry.status if entry else "indexed",
        "guidance": {
            "problem": problem,
            "action": action,
            "avoid": entry.avoid if entry else [],
            "success_criteria": entry.success_criteria if entry else [],
            "exceptions": entry.exceptions if entry else [],
        },
        "applicability": applicability,
        "evidence": {
            "observation": entry.evidence if entry else index_entry.lesson,
            "decisive_signal": entry.decisive_signal if entry else "",
            "false_starts": entry.false_starts if entry else [],
            "rejected_paths": entry.rejected_paths if entry else [],
            "root_cause_family": entry.root_cause_family if entry else "",
        },
        "provenance": {
            "source_command": index_entry.source_command,
            "first_seen": index_entry.first_seen,
            "last_seen": index_entry.last_seen,
            "occurrences": index_entry.occurrence_count,
            "source_layer": source_layer,
        },
        "lifecycle": {
            "signal": index_entry.signal_strength,
            "pain_score": entry.pain_score if entry else 0,
            "injection_targets": entry.injection_targets if entry else [],
            "promotion_hint": entry.promotion_hint if entry else "",
        },
        "content_safety": {
            "sensitivity": sensitivity,
            "redaction_labels": redaction_labels,
        },
        "detail_path": (
            _safe_project_relative_ref(project_root, detail_path)
            if detail_path
            else None
        ),
        "warnings": [
            *list(diagnostics.get("warnings", [])),
            *policy_result.warnings,
        ],
    }
    assessment = entry.assessment_payload() if entry else index_entry.assessment_payload()
    if assessment is not None:
        payload["assessment"] = assessment
    return _sanitize_detail_for_policy(payload, policy)


def start_learning_session(
    project_root: Path,
    *,
    command_name: str,
    task_context: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Return the compact, read-only Learning intake for one workflow."""

    paths = build_learning_paths(project_root)
    policy = load_learning_policy(project_root, for_write=False).policy
    normalized_command = _safe_review_command(command_name, policy)
    catalog = list_learning_summaries(
        project_root,
        command_name=normalized_command,
        task_context=task_context,
        include_all=True,
    )
    ranked_items = list(catalog["items"])
    stable_items = [
        item for item in ranked_items if item.get("source_layer") != "candidate"
    ]
    candidate_items = [
        item for item in ranked_items if item.get("source_layer") == "candidate"
    ]
    candidate_sources = {
        _canonicalize_recurrence_key(entry.recurrence_key, policy=policy)[
            0
        ]: _safe_review_command(entry.source_command, policy)
        for entry in _read_entries_if_present(paths.candidates)
    }

    def intake_rank(item: Mapping[str, Any]) -> tuple[int, int, int, int, int, str]:
        context_match = item.get("context_match")
        context = context_match if isinstance(context_match, Mapping) else {}
        assessment = item.get("assessment")
        value = assessment.get("learning_value") if isinstance(assessment, Mapping) else {}
        tier = value.get("tier") if isinstance(value, Mapping) else ""
        value_rank = {"high": 0, "medium": 1, "low": 2}.get(str(tier), 3)
        signal_rank = {"high": 0, "medium": 1, "low": 2}.get(
            str(item.get("signal") or ""), 3
        )
        return (
            -int(bool(context.get("exact_operation_owner"))),
            -int(context.get("matched_dimensions") or 0),
            -int(context.get("matched_values") or 0),
            value_rank,
            signal_rank - int(item.get("occurrences") or 0),
            str(item.get("ref") or ""),
        )

    stable_items.sort(key=intake_rank)
    candidate_items.sort(key=intake_rank)

    def select_diverse_candidates(
        items: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        selected_refs: set[str] = set()
        type_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}

        def try_select(*, enforce_source: bool, enforce_family: bool) -> None:
            for item in items:
                if len(selected) >= limit:
                    return
                ref = str(item.get("ref") or "")
                if ref in selected_refs:
                    continue
                learning_type = str(item.get("type") or "")
                source = candidate_sources.get(ref, "")
                suffix = ref.split(".", 1)[-1]
                family = f"{learning_type}:{suffix.split('-', 1)[0]}"
                if type_counts.get(learning_type, 0) >= 2:
                    continue
                if enforce_source and source_counts.get(source, 0) >= 2:
                    continue
                if enforce_family and family_counts.get(family, 0) >= 2:
                    continue
                selected.append(item)
                selected_refs.add(ref)
                type_counts[learning_type] = type_counts.get(learning_type, 0) + 1
                source_counts[source] = source_counts.get(source, 0) + 1
                family_counts[family] = family_counts.get(family, 0) + 1

        try_select(enforce_source=True, enforce_family=True)
        try_select(enforce_source=False, enforce_family=True)
        if len(selected) < limit:
            for item in items:
                ref = str(item.get("ref") or "")
                if ref not in selected_refs:
                    selected.append(item)
                    selected_refs.add(ref)
                    if len(selected) >= limit:
                        break
        return selected

    selected_stable = stable_items[:15]
    selected_candidates = select_diverse_candidates(candidate_items, 5)
    stable_gap = 15 - len(selected_stable)
    candidate_gap = 5 - len(selected_candidates)
    if stable_gap > 0:
        selected_candidates = select_diverse_candidates(candidate_items, 5 + stable_gap)
    if candidate_gap > 0:
        selected_stable.extend(stable_items[15 : 15 + candidate_gap])
    selected_items = [*selected_stable, *selected_candidates][:20]
    pagination = dict(catalog["pagination"])
    next_argv = None
    if len(ranked_items) > len(selected_items):
        safe_context = _sanitize_learning_facets(task_context, policy=policy)
        next_argv = [
            "specify",
            "learning",
            "list",
            "--command",
            normalized_command,
            "--cursor",
            "0",
            "--limit",
            "50",
            "--format",
            "json",
        ]
        next_argv.extend(_learning_context_argv(safe_context))
    pagination.update(
        {
            "cursor": 0,
            "limit": 20,
            "returned": len(selected_items),
            "total": len(ranked_items),
            "next_cursor": 0 if next_argv else None,
            "next_argv": next_argv,
        }
    )
    candidates = [
        entry
        for entry in (
            _scrub_learning_entry_for_policy(item, policy)
            for item in _read_entries_if_present(paths.candidates)
        )
        if is_relevant_to_command(entry, normalized_command)
    ]
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/startSummary",
        "command": normalized_command,
        "policy": learning_workflow_policy(normalized_command),
        "read_only": True,
        "items": selected_items,
        "pagination": pagination,
        "promotion_ready": [
            {
                "ref": _canonicalize_recurrence_key(
                    entry.recurrence_key, policy=policy
                )[0],
                "summary": sanitize_agent_text(entry.summary, policy=policy)[0],
                "occurrences": entry.occurrence_count,
            }
            for entry in candidates
            if entry.occurrence_count >= 2
        ],
        "needs_confirmation": [
            {
                "ref": _canonicalize_recurrence_key(
                    entry.recurrence_key, policy=policy
                )[0],
                "summary": sanitize_agent_text(entry.summary, policy=policy)[0],
                "signal": entry.signal_strength,
            }
            for entry in candidates
            if is_highest_signal(entry)
        ],
        "warnings": catalog["warnings"],
    }
    if catalog.get("task_context"):
        payload["task_context"] = catalog["task_context"]
    return payload


def capture_learning(
    project_root: Path,
    *,
    command_name: str,
    learning_type: str,
    summary: str,
    evidence: str,
    recurrence_key: str | None = None,
    signal_strength: str = "medium",
    applies_to: Iterable[str] | None = None,
    default_scope: str | None = None,
    confirm: bool = False,
    pain_score: int | None = None,
    false_starts: Iterable[str] | None = None,
    rejected_paths: Iterable[str] | None = None,
    decisive_signal: str | None = None,
    root_cause_family: str | None = None,
    injection_targets: Iterable[str] | None = None,
    promotion_hint: str | None = None,
    problem: str | None = None,
    recommended_action: str | None = None,
    avoid: Iterable[str] | None = None,
    trigger_signals: Iterable[str] | None = None,
    success_criteria: Iterable[str] | None = None,
    exceptions: Iterable[str] | None = None,
    facets: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    policy = load_learning_policy(project_root, for_write=True).policy
    normalized_type = normalize_learning_type(learning_type)
    safe_summary, _summary_labels = sanitize_agent_text(summary, policy=policy)
    normalized_recurrence, _recurrence_labels = _canonicalize_recurrence_key(
        recurrence_key or derive_recurrence_key(normalized_type, safe_summary),
        policy=policy,
    )
    with interprocess_lock(_learning_lock_path(project_root)):
        paths = _ensure_learning_files_unlocked(project_root)
        occurrences = _existing_occurrence_count(paths, normalized_recurrence) + 1
        entry = build_learning_entry(
            command_name=command_name,
            learning_type=normalized_type,
            summary=summary,
            evidence=evidence,
            recurrence_key=normalized_recurrence,
            signal_strength=signal_strength,
            applies_to=applies_to,
            default_scope=default_scope,
            status="confirmed" if confirm else "candidate",
            pain_score=pain_score,
            false_starts=false_starts,
            rejected_paths=rejected_paths,
            decisive_signal=decisive_signal,
            root_cause_family=root_cause_family,
            injection_targets=injection_targets,
            promotion_hint=promotion_hint,
            problem=problem,
            recommended_action=recommended_action,
            avoid=avoid,
            trigger_signals=trigger_signals,
            success_criteria=success_criteria,
            exceptions=exceptions,
            facets=facets,
            assessment_source="manual",
            assessment_occurrences=occurrences,
            policy=policy,
        )
        entry = _scrub_learning_entry_for_policy(entry, policy)
        if entry.assessment_decision == "defer":
            _record_review_state_unlocked(
                project_root,
                command_name=entry.source_command,
                decision="deferred",
                rationale=entry.assessment_reason,
                trigger_signals=entry.trigger_signals,
                recurrence_key=entry.recurrence_key,
                policy=policy,
            )
            _record_learning_metric_unlocked(project_root, entry)
            return {
                "status": "deferred",
                "entry": entry.to_payload(),
                "assessment": entry.assessment_payload(),
                "needs_confirmation": False,
            }
        stored = _store_learning_entry(
            paths, entry, confirm=confirm, policy=policy
        )
        _record_learning_metric_unlocked(project_root, entry, confirmed=confirm)
        _clear_matching_review_state_unlocked(project_root, entry)
        stored["assessment"] = entry.assessment_payload()
        return stored


def _existing_occurrence_count(paths: LearningPaths, recurrence_key: str) -> int:
    return max(
        (
            entry.occurrence_count
            for path in (
                paths.candidates,
                paths.confirmed_learnings,
                paths.project_rules,
            )
            for entry in _read_entries_if_present(path)
            if entry.recurrence_key == recurrence_key
        ),
        default=0,
    )


def _store_learning_entry(
    paths: LearningPaths,
    entry: LearningEntry,
    *,
    confirm: bool,
    policy: LearningPolicy | None = None,
) -> dict[str, Any]:
    active_policy = policy or default_learning_policy()
    entry = _scrub_learning_entry_for_policy(entry, active_policy)
    if confirm:
        preamble, learning_entries = _read_entries(paths.confirmed_learnings)
        learning_entries = [
            _scrub_learning_entry_for_policy(item, active_policy)
            for item in learning_entries
        ]
        learning_entries, stored = _upsert_entry(
            learning_entries, entry, status="confirmed"
        )
        _write_entries(
            paths.confirmed_learnings,
            preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
            learning_entries,
        )
        candidate_preamble, candidate_entries = _read_entries(paths.candidates)
        candidate_entries = [
            _scrub_learning_entry_for_policy(item, active_policy)
            for item in candidate_entries
        ]
        candidate_entries = _remove_by_recurrence(
            candidate_entries, stored.recurrence_key
        )
        _write_entries(
            paths.candidates,
            candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
            candidate_entries,
        )
        _append_review_note(
            paths.review,
            f"confirmed `{stored.recurrence_key}` from `{stored.source_command}`",
            policy=active_policy,
        )
        stored_index, detail_path = _sync_learning_index_detail(
            paths, stored, policy=active_policy
        )
        return {
            "status": "confirmed",
            "entry": stored.to_payload(),
            "index_entry": stored_index.to_payload(),
            "detail_path": _detail_path_response(paths, detail_path),
            "needs_confirmation": False,
        }

    preamble, candidate_entries = _read_entries(paths.candidates)
    candidate_entries = [
        _scrub_learning_entry_for_policy(item, active_policy)
        for item in candidate_entries
    ]
    candidate_entries, stored = _upsert_entry(
        candidate_entries, entry, status="candidate"
    )
    _write_entries(
        paths.candidates,
        preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
        candidate_entries,
    )
    _append_review_note(
        paths.review,
        f"captured candidate `{stored.recurrence_key}` from `{stored.source_command}`",
        policy=active_policy,
    )
    stored_index, detail_path = _sync_learning_index_detail(
        paths, stored, policy=active_policy
    )
    return {
        "status": "candidate",
        "entry": stored.to_payload(),
        "index_entry": stored_index.to_payload(),
        "detail_path": _detail_path_response(paths, detail_path),
        "needs_confirmation": is_highest_signal(stored),
    }


def capture_auto_learning(
    project_root: Path,
    *,
    command_name: str,
    feature_dir: Path | None = None,
    workspace: Path | None = None,
    session_file: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy_result = load_learning_policy(project_root, for_write=True)
    policy = policy_result.policy
    normalized_command = normalize_command_name(command_name)
    if normalized_command == "sp-implement":
        if feature_dir is None:
            raise ValueError("feature_dir is required for implement auto-capture")
        feature_dir = _ensure_project_contained_path(
            project_root, feature_dir, "feature_dir"
        )
        source_path, suggestions = _suggest_implement_auto_capture(
            feature_dir,
            feature_ref=_safe_project_relative_ref(project_root, feature_dir),
        )
    elif normalized_command == "sp-quick":
        if workspace is None:
            raise ValueError("workspace is required for quick auto-capture")
        workspace = _ensure_project_contained_path(project_root, workspace, "workspace")
        source_path, suggestions = _suggest_quick_auto_capture(
            workspace,
            workspace_ref=_safe_project_relative_ref(project_root, workspace),
        )
    elif normalized_command in WORKFLOW_STATE_AUTO_CAPTURE_COMMANDS:
        if feature_dir is None:
            raise ValueError("feature_dir is required for workflow-state auto-capture")
        feature_dir = _ensure_project_contained_path(
            project_root, feature_dir, "feature_dir"
        )
        source_path, suggestions = _suggest_workflow_state_auto_capture(
            feature_dir,
            command_name=normalized_command,
            feature_ref=_safe_project_relative_ref(project_root, feature_dir),
        )
    elif normalized_command == "sp-debug":
        if session_file is None:
            raise ValueError("session_file is required for debug auto-capture")
        session_file = _ensure_project_contained_path(
            project_root, session_file, "session_file"
        )
        source_path, suggestions = _suggest_debug_auto_capture(
            session_file,
            session_ref=_safe_project_relative_ref(project_root, session_file),
        )
    else:
        raise ValueError(f"auto-capture is unsupported for '{command_name}'")

    safe_source_path = sanitize_agent_text(
        _safe_project_relative_ref(project_root, source_path), policy=policy
    )[0]
    if not suggestions:
        if dry_run:
            return {
                "status": "dry-run",
                "dry_run": True,
                "command": normalized_command,
                "source_path": safe_source_path,
                "assessed": [],
                "captured": [],
                "warnings": list(policy_result.warnings),
            }
        return {
            "status": "no-op",
            "command": normalized_command,
            "source_path": safe_source_path,
            "captured": [],
            "reason": "no high-signal auto-capture patterns matched the current state",
        }

    fingerprint = _snapshot_fingerprint(
        normalized_command, safe_source_path, suggestions, policy=policy
    )

    def assess_suggestions(paths: LearningPaths) -> tuple[list[LearningEntry], list[dict[str, Any]]]:
        entries: list[LearningEntry] = []
        assessed: list[dict[str, Any]] = []
        for suggestion in suggestions:
            recurrence_key, _labels = _canonicalize_recurrence_key(
                suggestion.recurrence_key, policy=policy
            )
            occurrences = _existing_occurrence_count(paths, recurrence_key) + 1
            entry = build_learning_entry(
                command_name=normalized_command,
                learning_type=suggestion.learning_type,
                summary=suggestion.summary,
                evidence=suggestion.evidence,
                recurrence_key=recurrence_key,
                signal_strength=suggestion.signal_strength,
                applies_to=suggestion.applies_to,
                status="candidate",
                problem=suggestion.problem or None,
                recommended_action=suggestion.recommended_action or None,
                trigger_signals=suggestion.trigger_signals,
                success_criteria=suggestion.success_criteria,
                avoid=suggestion.avoid,
                exceptions=suggestion.exceptions,
                assessment_source="auto",
                assessment_occurrences=occurrences,
                policy=policy,
            )
            entry = _scrub_learning_entry_for_policy(entry, policy)
            entries.append(entry)
            assessed.append(
                {
                    "type": entry.learning_type,
                    "summary": entry.summary,
                    "action": entry.recommended_action,
                    "recurrence_key": entry.recurrence_key,
                    "assessment": entry.assessment_payload(),
                }
            )
        return entries, assessed

    if dry_run:
        paths = build_learning_paths(project_root)
        _entries, assessed = assess_suggestions(paths)
        return {
            "status": "dry-run",
            "dry_run": True,
            "command": normalized_command,
            "source_path": safe_source_path,
            "assessed": assessed,
            "captured": [],
            "fingerprint": fingerprint,
            "warnings": list(policy_result.warnings),
        }

    with interprocess_lock(_learning_lock_path(project_root)):
        paths = _ensure_learning_files_unlocked(project_root)
        registry = _load_auto_capture_registry(project_root)
        registry, registry_changed = _normalize_auto_capture_registry(
            project_root, registry, policy=policy
        )
        if registry_changed:
            _write_auto_capture_registry(project_root, registry)
        if fingerprint in registry:
            return {
                "status": "duplicate-snapshot",
                "command": normalized_command,
                "source_path": safe_source_path,
                "captured": [],
                "reason": "this workflow state snapshot was already auto-captured",
                "fingerprint": fingerprint,
            }

        entries, assessed = assess_suggestions(paths)
        captured: list[dict[str, Any]] = []
        for entry in entries:
            _record_learning_metric_unlocked(project_root, entry)
            if entry.assessment_decision in {"capture-safe", "capture-sanitized"}:
                captured.append(
                    _store_learning_entry(
                        paths, entry, confirm=False, policy=policy
                    )
                )
                _clear_matching_review_state_unlocked(project_root, entry)
            elif entry.assessment_decision == "defer":
                _record_review_state_unlocked(
                    project_root,
                    command_name=entry.source_command,
                    decision="deferred",
                    rationale=entry.assessment_reason,
                    trigger_signals=entry.trigger_signals,
                    recurrence_key=entry.recurrence_key,
                    policy=policy,
                )

        registry[fingerprint] = {
            "command": normalized_command,
            "source_ref": safe_source_path,
            "recurrence_keys": [entry.recurrence_key for entry in entries],
            "captured_at": now_iso(),
        }
        _write_auto_capture_registry(project_root, registry)
        _append_review_note(
            paths.review,
            f"auto-captured {len(captured)} learning candidate(s) from `{normalized_command}` using `{safe_source_path}`",
            policy=policy,
        )
        return {
            "status": "captured"
            if captured
            else "deferred"
            if any(entry.assessment_decision == "defer" for entry in entries)
            else "no-op",
            "command": normalized_command,
            "source_path": safe_source_path,
            "captured": captured,
            "assessed": assessed,
            "fingerprint": fingerprint,
            "warnings": list(policy_result.warnings),
        }


def promote_learning(
    project_root: Path,
    *,
    recurrence_key: str,
    target: str,
) -> dict[str, Any]:
    policy = load_learning_policy(project_root, for_write=True).policy
    normalized_target = target.strip().lower()
    if normalized_target not in PROMOTION_TARGETS:
        raise ValueError(f"unsupported promotion target '{target}'")
    normalized_recurrence_key, _labels = _canonicalize_recurrence_key(
        str(recurrence_key or ""), policy=policy
    )
    if not normalized_recurrence_key:
        raise ValueError("learning recurrence_key is required")

    with interprocess_lock(_learning_lock_path(project_root)):
        paths = _ensure_learning_files_unlocked(project_root)
        result = _promote_learning_locked(
            paths,
            recurrence_key=normalized_recurrence_key,
            normalized_target=normalized_target,
            policy=policy,
        )
        promoted_entry = LearningEntry.from_payload(result["entry"])
        _clear_matching_review_state_unlocked(project_root, promoted_entry)
        _record_promotion_metric_unlocked(
            project_root,
            promoted_entry.source_command,
            target=normalized_target,
        )
        return result


def _promote_learning_locked(
    paths: LearningPaths,
    *,
    recurrence_key: str,
    normalized_target: str,
    policy: LearningPolicy | None = None,
) -> dict[str, Any]:
    active_policy = policy or default_learning_policy()
    candidate_preamble, candidate_entries = _read_entries(paths.candidates)
    learning_preamble, learning_entries = _read_entries(paths.confirmed_learnings)
    rule_preamble, rule_entries = _read_entries(paths.project_rules)
    candidate_entries = [
        _scrub_learning_entry_for_policy(item, active_policy)
        for item in candidate_entries
    ]
    learning_entries = [
        _scrub_learning_entry_for_policy(item, active_policy)
        for item in learning_entries
    ]
    rule_entries = [
        _scrub_learning_entry_for_policy(item, active_policy)
        for item in rule_entries
    ]

    source_entry = next(
        (
            entry
            for entry in candidate_entries
            if entry.recurrence_key == recurrence_key
        ),
        None,
    )
    source_layer = "candidates"
    if source_entry is None:
        source_entry = next(
            (
                entry
                for entry in learning_entries
                if entry.recurrence_key == recurrence_key
            ),
            None,
        )
        source_layer = "confirmed_learnings"
    if source_entry is None:
        source_entry = next(
            (entry for entry in rule_entries if entry.recurrence_key == recurrence_key),
            None,
        )
        source_layer = "project_rules"
    if source_entry is None:
        raise ValueError(f"learning '{recurrence_key}' not found")
    if normalized_target == "rule" and source_layer == "candidates":
        raise ValueError(
            "candidate learning must be confirmed before promotion to project rule"
        )
    source_entry.last_seen = now_iso()

    if normalized_target == "learning":
        source_entry.status = "confirmed"
        learning_entries, stored = _upsert_entry(
            learning_entries, source_entry, status="confirmed"
        )
        candidate_entries = _remove_by_recurrence(candidate_entries, recurrence_key)
        _write_entries(
            paths.confirmed_learnings,
            learning_preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
            learning_entries,
        )
        _write_entries(
            paths.candidates,
            candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
            candidate_entries,
        )
        _append_review_note(
            paths.review,
            f"promoted `{recurrence_key}` to project learnings from `{source_layer}`",
            policy=active_policy,
        )
        stored_index, detail_path = _sync_learning_index_detail(
            paths, stored, policy=active_policy
        )
        return {
            "status": "confirmed",
            "entry": stored.to_payload(),
            "index_entry": stored_index.to_payload(),
            "detail_path": _detail_path_response(paths, detail_path),
        }

    source_entry.status = "promoted-rule"
    rule_entries, stored = _upsert_entry(
        rule_entries, source_entry, status="promoted-rule"
    )
    candidate_entries = _remove_by_recurrence(candidate_entries, recurrence_key)
    learning_entries = _remove_by_recurrence(learning_entries, recurrence_key)
    _write_entries(
        paths.project_rules, rule_preamble or RULES_TEMPLATE_TEXT.rstrip(), rule_entries
    )
    _write_entries(
        paths.confirmed_learnings,
        learning_preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
        learning_entries,
    )
    _write_entries(
        paths.candidates,
        candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
        candidate_entries,
    )
    _append_review_note(
        paths.review,
        f"promoted `{recurrence_key}` to project rules from `{source_layer}`",
        policy=active_policy,
    )
    stored_index, detail_path = _sync_learning_index_detail(
        paths, stored, policy=active_policy
    )
    return {
        "status": "promoted-rule",
        "entry": stored.to_payload(),
        "index_entry": stored_index.to_payload(),
        "detail_path": _detail_path_response(paths, detail_path),
    }


def _entry_counts(project_root: Path) -> dict[str, int]:
    paths = build_learning_paths(project_root)
    _, candidate_entries = (
        _read_entries(paths.candidates) if paths.candidates.exists() else ("", [])
    )
    _, learning_entries = (
        _read_entries(paths.confirmed_learnings)
        if paths.confirmed_learnings.exists()
        else ("", [])
    )
    _, rule_entries = (
        _read_entries(paths.project_rules) if paths.project_rules.exists() else ("", [])
    )
    return {
        "candidates": len(candidate_entries),
        "confirmed_learnings": len(learning_entries),
        "project_rules": len(rule_entries),
    }


def learning_review_status(
    project_root: Path,
    *,
    command_name: str | None = None,
    current_time: datetime | None = None,
) -> dict[str, Any]:
    """Return the durable pending-review queue without mutating or aging storage."""

    policy_result = load_learning_policy(project_root, for_write=False)
    normalized_command = (
        _safe_review_command(command_name, policy_result.policy)
        if command_name
        else None
    )
    now = (current_time or datetime.now(tz=UTC)).astimezone(UTC)
    now_text = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    items = _load_review_items(
        project_root,
        policy=policy_result.policy,
        include_legacy=True,
        fallback_now=now_text,
    )
    if normalized_command:
        items = [item for item in items if item["command"] == normalized_command]
    age_buckets = {
        "not_due": 0,
        "due_0_7_days": 0,
        "due_8_30_days": 0,
        "due_over_30_days": 0,
    }
    overdue = 0
    for item in items:
        review_after = datetime.fromisoformat(
            item["review_after"].replace("Z", "+00:00")
        )
        due = now >= review_after
        if not due:
            age_buckets["not_due"] += 1
        else:
            overdue += 1
            due_days = max(0, int((now - review_after).total_seconds() // 86400))
            if due_days <= 7:
                age_buckets["due_0_7_days"] += 1
            elif due_days <= 30:
                age_buckets["due_8_30_days"] += 1
            else:
                age_buckets["due_over_30_days"] += 1
    return {
        "schema_version": 1,
        "read_only": True,
        "command": normalized_command,
        "pending": len(items),
        "overdue": overdue,
        "age_buckets": age_buckets,
        "warnings": list(policy_result.warnings),
    }


def _durable_learning_entries(project_root: Path) -> list[LearningEntry]:
    paths = build_learning_paths(project_root)
    return [
        entry
        for path in (
            paths.candidates,
            paths.confirmed_learnings,
            paths.project_rules,
        )
        for entry in _read_entries_if_present(path)
    ]


def review_learning(
    project_root: Path,
    *,
    command_name: str,
    decision: str,
    rationale: str = "",
    recurrence_key: str = "",
) -> dict[str, Any]:
    """Persist or close one explicit Learning review decision."""

    policy = load_learning_policy(project_root, for_write=True).policy
    command = _safe_review_command(command_name, policy)
    normalized_decision = str(decision or "").strip().lower()
    if normalized_decision not in _REVIEW_DECISIONS:
        raise ValueError("unsupported Project Learning review decision")
    safe_rationale, _labels = sanitize_agent_text(rationale, policy=policy)
    if normalized_decision in _PENDING_REVIEW_DECISIONS and not safe_rationale:
        raise ValueError(
            f"learning review decision `{normalized_decision}` requires a rationale"
        )
    safe_recurrence, _recurrence_labels = _canonicalize_recurrence_key(
        recurrence_key, policy=policy
    )
    with interprocess_lock(_learning_lock_path(project_root)):
        pending = _load_review_items(
            project_root, policy=policy, include_legacy=True
        )
        command_pending = [item for item in pending if item["command"] == command]
        if normalized_decision == "none":
            if command_pending:
                raise ValueError(
                    "pending Project Learning review cannot be closed with decision `none`"
                )
            return {
                "status": "ok",
                "command": command,
                "decision": normalized_decision,
                "rationale": safe_rationale,
            }
        if normalized_decision in _PENDING_REVIEW_DECISIONS:
            item = _record_review_state_unlocked(
                project_root,
                command_name=command,
                decision=normalized_decision,
                rationale=safe_rationale,
                recurrence_key=safe_recurrence,
                policy=policy,
            )
            return {"status": "pending", "item": item}

        scrubbed_durable_entries = [
            _scrub_learning_entry_for_policy(entry, policy)
            for entry in _durable_learning_entries(project_root)
        ]
        durable_entries = [
            entry
            for entry in scrubbed_durable_entries
            if entry.source_command == command or command in entry.applies_to
        ]

        def fresh_entry_for(recurrence: str) -> LearningEntry | None:
            relevant_pending = [
                item
                for item in command_pending
                if not item["recurrence_key"]
                or item["recurrence_key"] == recurrence
            ]
            return next(
                (
                    entry
                    for entry in durable_entries
                    if (not recurrence or entry.recurrence_key == recurrence)
                    and (
                        not relevant_pending
                        or all(
                            _entry_seen_after(entry, item["created_at"])
                            for item in relevant_pending
                        )
                    )
                ),
                None,
            )

        matching_entries: list[LearningEntry]
        if safe_recurrence:
            matching = fresh_entry_for(safe_recurrence)
            matching_entries = [matching] if matching is not None else []
        else:
            pending_recurrences = sorted(
                {
                    item["recurrence_key"]
                    for item in command_pending
                    if item["recurrence_key"]
                }
            )
            if pending_recurrences:
                matching_entries = []
                for pending_recurrence in pending_recurrences:
                    matching = fresh_entry_for(pending_recurrence)
                    if matching is None:
                        matching_entries = []
                        break
                    matching_entries.append(matching)
            else:
                matching = fresh_entry_for("")
                matching_entries = [matching] if matching is not None else []

        if not matching_entries:
            raise ValueError(
                "no matching durable Learning capture was found for this review"
            )
        for matching_entry in matching_entries:
            _clear_matching_review_state_unlocked(project_root, matching_entry)
        response: dict[str, Any] = {
            "status": "captured",
            "command": command,
            "decision": normalized_decision,
            "recurrence_key": matching_entries[0].recurrence_key,
        }
        if len(matching_entries) > 1:
            response["recurrence_keys"] = [
                entry.recurrence_key for entry in matching_entries
            ]
        return response


def learning_metrics_payload(
    project_root: Path, *, command_name: str | None = None
) -> dict[str, Any]:
    """Return aggregate-only assessment metrics; never expose refs or source text."""

    policy_result = load_learning_policy(project_root, for_write=False)
    normalized_command = (
        _safe_review_command(command_name, policy_result.policy)
        if command_name
        else None
    )
    metrics = _load_learning_metrics(project_root)
    bucket = (
        metrics["by_command"].get(normalized_command, _empty_metric_bucket())
        if normalized_command
        else metrics["global"]
    )
    review_status = learning_review_status(
        project_root, command_name=normalized_command
    )
    captured_count = bucket["totals"]["captured"]
    confirmed_count = bucket["totals"]["confirmed"]
    confirmation_rate = (
        min(1.0, confirmed_count / captured_count) if captured_count else 0.0
    )
    return {
        "schema_version": 1,
        "read_only": True,
        "command": normalized_command,
        "metrics": bucket,
        "derived": {"confirmation_rate": confirmation_rate},
        "age_buckets": review_status["age_buckets"],
        "warnings": list(
            dict.fromkeys([*policy_result.warnings, *review_status["warnings"]])
        ),
    }


def learning_status_payload(
    project_root: Path,
    *,
    include_runtime: bool = True,
    command_name: str | None = None,
) -> dict[str, Any]:
    paths = build_learning_paths(project_root)
    payload: dict[str, Any] = {
        "paths": paths.to_dict(),
        "exists": {
            "constitution": paths.constitution.exists(),
            "project_rules": paths.project_rules.exists(),
            "confirmed_learnings": paths.confirmed_learnings.exists(),
            "learning_index": paths.learning_index.exists(),
        },
        "counts": _entry_counts(project_root),
    }
    if include_runtime:
        payload["exists"].update(
            {
                "candidates": paths.candidates.exists(),
                "review": paths.review.exists(),
            }
        )
        payload["review_status"] = learning_review_status(
            project_root, command_name=command_name
        )
        payload["metrics"] = learning_metrics_payload(
            project_root, command_name=command_name
        )
    return payload
