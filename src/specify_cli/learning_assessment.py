from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Iterable

from specify_cli.learning_policy import LearningPolicy, default_learning_policy


ASSESSMENT_VERSION = "v1"

LEARNING_VALUE_TIERS = {"high", "medium", "low"}
ASSESSMENT_DECISIONS = {
    "capture-safe",
    "capture-sanitized",
    "defer",
    "ignore",
}
VALUE_REASON_CODES = {
    "explicit_capture",
    "workflow_gap",
    "user_correction",
    "reusable_constraint",
    "near_miss",
    "repeated_occurrence",
    "tooling_trap",
    "recovery_path",
    "high_signal",
    "routine_outcome",
}
DECISION_REASONS = {
    "safe_content",
    "valuable_after_abstraction",
    "sensitive_without_reusable_abstraction",
    "routine_outcome",
}
ASSESSMENT_REDACTION_LABELS = {
    "credential",
    "email",
    "private_key",
    "machine_path",
    "personal_identifier",
    "business_identifier",
    "organization_sensitive",
}

_PHONE_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<phone>\+?[\d() .-]{7,25}\d)(?![A-Za-z0-9])"
)
_HYPHEN_PHONE_RE = re.compile(r"(?:\d{1,3}-)?\d{3}-\d{3}-\d{4}")
_HIGH_ENTROPY_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<token>[A-Za-z0-9!@#$%^&*_=+~.-]{20,})(?![A-Za-z0-9])"
)
_REDACTION_MARKERS: tuple[tuple[str, str], ...] = (
    ("[REDACTED_SECRET]", "credential"),
    ("[REDACTED_EMAIL]", "email"),
    ("[REDACTED_PRIVATE_KEY]", "private_key"),
    ("<USER_HOME>", "machine_path"),
    ("[REDACTED_PHONE]", "personal_identifier"),
    ("[REDACTED_BUSINESS_ID]", "business_identifier"),
    ("[REDACTED_ORG_TERM]", "organization_sensitive"),
)


@dataclass(frozen=True)
class LearningAssessment:
    learning_value_tier: str
    learning_value_reason_codes: tuple[str, ...]
    sensitivity: str
    sensitivity_risk_tier: str
    redaction_labels: tuple[str, ...]
    assessment_decision: str
    assessment_reason: str
    summary: str
    evidence: str
    recommended_action: str

    def flat_payload(self) -> dict[str, object]:
        return {
            "learning_value_tier": self.learning_value_tier,
            "learning_value_reason_codes": list(self.learning_value_reason_codes),
            "sensitivity_risk_tier": self.sensitivity_risk_tier,
            "assessment_decision": self.assessment_decision,
            "assessment_reason": self.assessment_reason,
        }

    def payload(self) -> dict[str, object]:
        return {
            "learning_value": {
                "tier": self.learning_value_tier,
                "reason_codes": list(self.learning_value_reason_codes),
            },
            "content_safety": {
                "sensitivity": self.sensitivity,
                "risk_tier": self.sensitivity_risk_tier,
                "redaction_labels": list(self.redaction_labels),
            },
            "decision": self.assessment_decision,
            "decision_reason": self.assessment_reason,
        }


BaseSanitizer = Callable[[str], tuple[str, list[str]]]


def _replace_high_entropy(match: re.Match[str]) -> str:
    token = match.group("token")
    categories = sum(
        (
            any(character.islower() for character in token),
            any(character.isupper() for character in token),
            any(character.isdigit() for character in token),
            any(not character.isalnum() and character not in "._-" for character in token),
        )
    )
    if categories < 3 or len(set(token)) < 10:
        return token
    return "[REDACTED_SECRET]"


def _replace_phone(match: re.Match[str]) -> str:
    candidate = match.group("phone")
    digit_count = sum(character.isdigit() for character in candidate)
    if not 7 <= digit_count <= 15:
        return candidate
    if any(character in candidate for character in "+() "):
        return "[REDACTED_PHONE]"
    if _HYPHEN_PHONE_RE.fullmatch(candidate):
        return "[REDACTED_PHONE]"
    return candidate


def _literal_value_pattern(prefix: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?i)(?<![A-Za-z0-9_]){re.escape(prefix)}[^\s\"',;}}\]]{{3,}}"
    )


def _sensitive_key_pattern(key: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?i)(?P<key>(?<![A-Za-z0-9_.-]){re.escape(key)}\s*[:=]\s*)(?P<quote>[\"']?)(?P<value>(?!\[REDACTED_)[^\"'\s,;}}]+)(?P=quote)"
    )


def _business_identifier_pattern(prefix: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?i)(?<![A-Za-z0-9_]){re.escape(prefix)}[A-Za-z0-9_-]{{3,}}(?![A-Za-z0-9_])"
    )


def sanitize_learning_text(
    value: str,
    *,
    policy: LearningPolicy | None = None,
    base_sanitizer: BaseSanitizer | None = None,
) -> tuple[str, list[str]]:
    """Apply bounded literal detectors plus built-ins without retaining detector values."""

    active_policy = policy or default_learning_policy()
    sanitized = str(value or "")
    labels: set[str] = {
        label for marker, label in _REDACTION_MARKERS if marker in sanitized
    }

    for term in active_policy.detectors.sensitive_terms:
        sanitized, count = re.subn(
            re.escape(term), "[REDACTED_ORG_TERM]", sanitized, flags=re.IGNORECASE
        )
        if count:
            labels.add("organization_sensitive")
    for key in active_policy.detectors.sensitive_key_names:
        sanitized, count = _sensitive_key_pattern(key).subn(
            lambda match: (
                f"{match.group('key')}{match.group('quote')}[REDACTED_SECRET]{match.group('quote')}"
            ),
            sanitized,
        )
        if count:
            labels.add("credential")
    for prefix in active_policy.detectors.secret_prefixes:
        sanitized, count = _literal_value_pattern(prefix).subn(
            "[REDACTED_SECRET]", sanitized
        )
        if count:
            labels.add("credential")
    for prefix in active_policy.detectors.business_id_prefixes:
        sanitized, count = _business_identifier_pattern(prefix).subn(
            "[REDACTED_BUSINESS_ID]", sanitized
        )
        if count:
            labels.add("business_identifier")

    if base_sanitizer is not None:
        sanitized, base_labels = base_sanitizer(sanitized)
        labels.update(base_labels)

    before_phone = sanitized
    sanitized = _PHONE_CANDIDATE_RE.sub(_replace_phone, sanitized)
    if sanitized != before_phone:
        labels.add("personal_identifier")
    before_entropy = sanitized
    sanitized = _HIGH_ENTROPY_TOKEN_RE.sub(_replace_high_entropy, sanitized)
    if sanitized != before_entropy:
        labels.add("credential")

    labels.update(
        label for marker, label in _REDACTION_MARKERS if marker in sanitized
    )
    return sanitized, sorted(labels & ASSESSMENT_REDACTION_LABELS)


def _canonical_signals(values: Iterable[str]) -> set[str]:
    return {
        re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
        for value in values
        if str(value or "").strip()
    }


def _learning_value(
    *,
    source: str,
    learning_type: str,
    signal_strength: str,
    occurrences: int,
    trigger_signals: Iterable[str],
) -> tuple[str, tuple[str, ...]]:
    source = str(source or "auto").strip().lower()
    learning_type = str(learning_type or "").strip().lower()
    signal_strength = str(signal_strength or "medium").strip().lower()
    signals = _canonical_signals(trigger_signals)
    type_reason = {
        "workflow_gap": "workflow_gap",
        "project_constraint": "reusable_constraint",
        "tooling_trap": "tooling_trap",
        "recovery_path": "recovery_path",
        "near_miss": "near_miss",
    }.get(learning_type)
    high_reasons: set[str] = set()
    if "user_correction" in signals:
        high_reasons.add("user_correction")
    if "near_miss" in signals or learning_type == "near_miss":
        high_reasons.add("near_miss")
    if "reusable_constraint" in signals:
        high_reasons.add("reusable_constraint")
    if max(0, int(occurrences)) >= 2:
        high_reasons.add("repeated_occurrence")
        if type_reason:
            high_reasons.add(type_reason)
    if source == "manual":
        reasons = {"explicit_capture", *high_reasons}
        if type_reason:
            reasons.add(type_reason)
        return "high", tuple(sorted(reasons))
    if high_reasons:
        return "high", tuple(sorted(high_reasons))
    if learning_type == "recovery_path" or "recovery_completed" in signals:
        return "medium", ("recovery_path",)
    if learning_type == "workflow_gap":
        return "medium", ("workflow_gap",)
    if learning_type == "project_constraint":
        return "medium", ("reusable_constraint",)
    if learning_type == "tooling_trap":
        return "medium", ("tooling_trap",)
    if signal_strength in {"medium", "high"}:
        return "medium", ("high_signal",)
    return "low", ("routine_outcome",)


def _risk_tier(labels: Iterable[str]) -> str:
    label_set = set(labels)
    if not label_set:
        return "none"
    if label_set & {"credential", "private_key", "organization_sensitive"}:
        return "high"
    return "moderate"


def _semantic_residue(value: str) -> tuple[set[str], int]:
    joined = str(value or "")
    for marker, _label in _REDACTION_MARKERS:
        joined = joined.replace(marker, " ")
    joined = re.sub(
        r"(?i)\b(?:secret|password|token|api[_-]?key|authorization|credential|email|phone|customer[_-]?id)\b",
        " ",
        joined,
    )
    words = {
        word.casefold()
        for word in re.findall(r"[^\W_]+", joined, flags=re.UNICODE)
        if len(word) >= 2
    }
    alphanumeric_count = sum(character.isalnum() for character in joined)
    return words, alphanumeric_count


def _has_reusable_semantics(
    summary: str, evidence: str, recommended_action: str
) -> bool:
    action_words, action_characters = _semantic_residue(recommended_action)
    if len(action_words) >= 3 or action_characters >= 6:
        return True
    words, characters = _semantic_residue(f"{summary} {evidence}")
    return len(words) >= 4 or characters >= 8


def assess_learning(
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
    base_sanitizer: BaseSanitizer | None = None,
) -> LearningAssessment:
    """Return a deterministic value/sensitivity assessment and sanitized content."""

    sanitized_fields = [
        sanitize_learning_text(
            value, policy=policy, base_sanitizer=base_sanitizer
        )
        for value in (summary, evidence, recommended_action)
    ]
    sanitized_summary, summary_labels = sanitized_fields[0]
    sanitized_evidence, evidence_labels = sanitized_fields[1]
    sanitized_action, action_labels = sanitized_fields[2]
    labels = tuple(sorted({*summary_labels, *evidence_labels, *action_labels}))
    value_tier, reason_codes = _learning_value(
        source=source,
        learning_type=learning_type,
        signal_strength=signal_strength,
        occurrences=occurrences,
        trigger_signals=trigger_signals,
    )
    sensitivity = "sanitized" if labels else "safe"
    risk_tier = _risk_tier(labels)
    if value_tier == "low":
        decision = "ignore"
        decision_reason = "routine_outcome"
    elif not labels:
        decision = "capture-safe"
        decision_reason = "safe_content"
    elif _has_reusable_semantics(
        sanitized_summary, sanitized_evidence, sanitized_action
    ):
        decision = "capture-sanitized"
        decision_reason = "valuable_after_abstraction"
    else:
        decision = "defer"
        decision_reason = "sensitive_without_reusable_abstraction"
    return LearningAssessment(
        learning_value_tier=value_tier,
        learning_value_reason_codes=reason_codes,
        sensitivity=sensitivity,
        sensitivity_risk_tier=risk_tier,
        redaction_labels=labels,
        assessment_decision=decision,
        assessment_reason=decision_reason,
        summary=sanitized_summary,
        evidence=sanitized_evidence,
        recommended_action=sanitized_action,
    )


def assessment_payload_from_flat(
    *,
    learning_value_tier: str,
    learning_value_reason_codes: Iterable[str],
    sensitivity: str,
    sensitivity_risk_tier: str,
    redaction_labels: Iterable[str],
    assessment_decision: str,
    assessment_reason: str,
) -> dict[str, object] | None:
    reasons = tuple(
        dict.fromkeys(
            reason
            for reason in learning_value_reason_codes
            if reason in VALUE_REASON_CODES
        )
    )
    labels = tuple(
        sorted(
            {
                label
                for label in redaction_labels
                if label in ASSESSMENT_REDACTION_LABELS
            }
        )
    )
    if (
        learning_value_tier not in LEARNING_VALUE_TIERS
        or not reasons
        or assessment_decision not in ASSESSMENT_DECISIONS
        or assessment_reason not in DECISION_REASONS
        or sensitivity not in {"safe", "sanitized"}
        or sensitivity_risk_tier not in {"none", "moderate", "high"}
    ):
        return None
    expected_reason = {
        "capture-safe": "safe_content",
        "capture-sanitized": "valuable_after_abstraction",
        "defer": "sensitive_without_reusable_abstraction",
        "ignore": "routine_outcome",
    }[assessment_decision]
    if assessment_reason != expected_reason:
        return None
    if assessment_decision == "capture-safe" and (
        sensitivity != "safe" or sensitivity_risk_tier != "none" or labels
    ):
        return None
    if assessment_decision in {"capture-sanitized", "defer"} and (
        sensitivity != "sanitized"
        or sensitivity_risk_tier not in {"moderate", "high"}
        or not labels
    ):
        return None
    if assessment_decision == "ignore" and learning_value_tier != "low":
        return None
    if assessment_decision != "ignore" and learning_value_tier == "low":
        return None
    return {
        "learning_value": {
            "tier": learning_value_tier,
            "reason_codes": list(reasons),
        },
        "content_safety": {
            "sensitivity": sensitivity,
            "risk_tier": sensitivity_risk_tier,
            "redaction_labels": list(labels),
        },
        "decision": assessment_decision,
        "decision_reason": assessment_reason,
    }
