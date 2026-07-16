"""Evidence helpers shared by delegated result validation and closeout audits."""

from __future__ import annotations

import re
from typing import Any


REAL_ENTRYPOINT_REQUIRED_FIELDS = (
    "entrypoint",
    "producer",
    "transformer",
    "consumer",
    "validation",
)
REAL_ENTRYPOINT_BOUNDARY_FIELDS = (
    "boundary_or_executor",
    "boundary",
    "executor",
)
PLACEHOLDER_VALUES = {
    "todo",
    "tbd",
    "na",
    "n_a",
    "none",
    "null",
    "unknown",
    "placeholder",
    "replace_me",
}


def normalize_evidence_label(value: str) -> str:
    """Normalize evidence labels so prompt wording can use spaces or hyphens."""

    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def has_any_evidence(value: object) -> bool:
    return isinstance(value, list) and any(bool(item) for item in value)


def has_real_entrypoint_consumer_evidence(value: object) -> bool:
    """Return true when consumer evidence proves a real user/runtime entry path."""

    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            continue
        kind = normalize_evidence_label(str(item.get("kind", "")))
        if kind != "real_entrypoint":
            continue
        if not all(_has_value(item, field) for field in REAL_ENTRYPOINT_REQUIRED_FIELDS):
            continue
        if not any(_has_value(item, field) for field in REAL_ENTRYPOINT_BOUNDARY_FIELDS):
            continue
        return True
    return False


def _has_value(item: dict[Any, Any], field: str) -> bool:
    value = item.get(field)
    if not isinstance(value, str):
        return False
    if not value.strip():
        return False
    return normalize_evidence_label(value) not in PLACEHOLDER_VALUES
