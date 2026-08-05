from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import unicodedata
from typing import Any, Mapping


MAX_DETECTOR_ITEMS = 64
MAX_DETECTOR_ITEM_LENGTH = 128
DEFAULT_DEFERRED_REVIEW_DAYS = 7
MIN_DEFERRED_REVIEW_DAYS = 1
MAX_DEFERRED_REVIEW_DAYS = 365

_PROJECT_LEARNING_KEYS = {"detectors", "deferred_review_days"}
_DETECTOR_KEYS = {
    "secret_prefixes",
    "sensitive_key_names",
    "business_id_prefixes",
    "sensitive_terms",
}


class LearningPolicyError(ValueError):
    """Raised when Project Learning policy is unsafe or malformed."""


@dataclass(frozen=True)
class LearningDetectors:
    secret_prefixes: tuple[str, ...] = ()
    sensitive_key_names: tuple[str, ...] = ()
    business_id_prefixes: tuple[str, ...] = ()
    sensitive_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearningPolicy:
    detectors: LearningDetectors = field(default_factory=LearningDetectors)
    deferred_review_days: int = DEFAULT_DEFERRED_REVIEW_DAYS


@dataclass(frozen=True)
class LearningPolicyResult:
    policy: LearningPolicy
    warnings: tuple[str, ...] = ()
    valid: bool = True


def default_learning_policy() -> LearningPolicy:
    return LearningPolicy()


def _normalize_detector_values(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Return the canonical, order-independent detector execution order."""

    deduplicated: dict[str, str] = {}
    for value in values:
        identity = value.casefold()
        current = deduplicated.get(identity)
        if current is None or value < current:
            deduplicated[identity] = value
    return tuple(
        sorted(
            deduplicated.values(),
            key=lambda value: (-len(value), value.casefold(), value),
        )
    )


def learning_policy_digest(policy: LearningPolicy) -> str:
    payload = {
        "detectors": {
            "secret_prefixes": list(
                _normalize_detector_values(policy.detectors.secret_prefixes)
            ),
            "sensitive_key_names": list(
                _normalize_detector_values(policy.detectors.sensitive_key_names)
            ),
            "business_id_prefixes": list(
                _normalize_detector_values(policy.detectors.business_id_prefixes)
            ),
            "sensitive_terms": list(
                _normalize_detector_values(policy.detectors.sensitive_terms)
            ),
        },
        "deferred_review_days": policy.deferred_review_days,
    }
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_detector_list(name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LearningPolicyError(f"project_learning.detectors.{name} must be a list")
    if len(value) > MAX_DETECTOR_ITEMS:
        raise LearningPolicyError(
            f"project_learning.detectors.{name} accepts at most {MAX_DETECTOR_ITEMS} items"
        )
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise LearningPolicyError(
                f"project_learning.detectors.{name} items must be strings"
            )
        stripped = item.strip()
        if not stripped or len(stripped) > MAX_DETECTOR_ITEM_LENGTH:
            raise LearningPolicyError(
                f"project_learning.detectors.{name} items must contain 1..{MAX_DETECTOR_ITEM_LENGTH} characters"
            )
        if any(unicodedata.category(character) == "Cc" for character in stripped):
            raise LearningPolicyError(
                f"project_learning.detectors.{name} items must not contain control characters"
            )
        normalized.append(stripped)
    return _normalize_detector_values(normalized)


def parse_learning_policy(value: Mapping[str, Any] | None) -> LearningPolicy:
    if value is None:
        return default_learning_policy()
    if not isinstance(value, Mapping):
        raise LearningPolicyError("project_learning must be an object")
    unknown = set(value) - _PROJECT_LEARNING_KEYS
    if unknown:
        raise LearningPolicyError("project_learning contains unsupported fields")

    raw_detectors = value.get("detectors", {})
    if not isinstance(raw_detectors, Mapping):
        raise LearningPolicyError("project_learning.detectors must be an object")
    unknown_detectors = set(raw_detectors) - _DETECTOR_KEYS
    if unknown_detectors:
        raise LearningPolicyError(
            "project_learning.detectors contains unsupported fields"
        )
    detectors = LearningDetectors(
        secret_prefixes=_validate_detector_list(
            "secret_prefixes", raw_detectors.get("secret_prefixes", [])
        ),
        sensitive_key_names=_validate_detector_list(
            "sensitive_key_names", raw_detectors.get("sensitive_key_names", [])
        ),
        business_id_prefixes=_validate_detector_list(
            "business_id_prefixes", raw_detectors.get("business_id_prefixes", [])
        ),
        sensitive_terms=_validate_detector_list(
            "sensitive_terms", raw_detectors.get("sensitive_terms", [])
        ),
    )

    deferred_review_days = value.get(
        "deferred_review_days", DEFAULT_DEFERRED_REVIEW_DAYS
    )
    if isinstance(deferred_review_days, bool) or not isinstance(
        deferred_review_days, int
    ):
        raise LearningPolicyError(
            "project_learning.deferred_review_days must be an integer"
        )
    if not MIN_DEFERRED_REVIEW_DAYS <= deferred_review_days <= MAX_DEFERRED_REVIEW_DAYS:
        raise LearningPolicyError(
            f"project_learning.deferred_review_days must be between {MIN_DEFERRED_REVIEW_DAYS} and {MAX_DEFERRED_REVIEW_DAYS}"
        )
    return LearningPolicy(
        detectors=detectors,
        deferred_review_days=deferred_review_days,
    )


def load_learning_policy(
    project_root: Path,
    *,
    for_write: bool = False,
) -> LearningPolicyResult:
    """Load a bounded literal-only policy, failing closed for write operations."""

    path = project_root / ".specify" / "config.json"
    if not path.is_file():
        return LearningPolicyResult(default_learning_policy())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise LearningPolicyError("project configuration must be an object")
        policy = (
            parse_learning_policy(payload["project_learning"])
            if "project_learning" in payload
            else default_learning_policy()
        )
        if "project_learning" in payload and payload["project_learning"] is None:
            raise LearningPolicyError("project_learning must be an object")
    except (OSError, json.JSONDecodeError, LearningPolicyError) as exc:
        if for_write:
            raise LearningPolicyError(
                "Project Learning policy is invalid; write was rejected"
            ) from exc
        return LearningPolicyResult(
            default_learning_policy(),
            warnings=("project_learning_policy_invalid:using_builtin_policy",),
            valid=False,
        )
    return LearningPolicyResult(policy)
