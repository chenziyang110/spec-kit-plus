"""Validated, offline Quick evaluation records and coverage-aware aggregation.

Missing observations remain unknown. This module does not execute agents,
validate acceptance evidence, or infer quality from cost measurements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

MODES = frozenset({"worker-full", "worker-compact", "direct-full", "direct-compact"})
METRICS = ("input_tokens", "output_tokens", "tool_calls", "duration_ms")
IDENTITY_FIELDS = ("run_id", "case_id", "source_revision", "model", "environment")


@dataclass(frozen=True)
class QuickEvalRecord:
    case_id: str
    mode: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: int | None = None
    duration_ms: int | None = None
    accepted: bool | None = None
    human_intervention: bool | None = None
    notes: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    source_revision: str | None = None
    model: str | None = None
    environment: str | None = None

    def __post_init__(self) -> None:
        validate_record(asdict(self))


def validate_record(record: Mapping[str, Any], *, strict: bool = False) -> dict[str, Any]:
    """Validate observations, preserving absent and explicit-null values.

    Legacy records without identity fields can be inspected, but are marked
    incomplete. Strict input requires identifiers for auditable comparisons.
    """
    if not isinstance(record, Mapping):
        raise ValueError("record must be an object")
    value = dict(record)
    mode = value.get("mode")
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError(f"unsupported mode: {mode!r}")
    for name in METRICS:
        item = value.get(name)
        if item is not None and (type(item) is not int or item < 0):
            raise ValueError(f"{name} must be a non-negative integer or null")
    for name in ("accepted", "human_intervention"):
        item = value.get(name)
        if item is not None and type(item) is not bool:
            raise ValueError(f"{name} must be a boolean or null")
    for name in IDENTITY_FIELDS:
        item = value.get(name)
        if item is not None and (not isinstance(item, str) or not item.strip()):
            raise ValueError(f"{name} must be a non-empty string or null")
        if strict and item is None:
            raise ValueError(f"strict records require {name}")
    if "notes" in value and not isinstance(value["notes"], dict):
        raise ValueError("notes must be an object")
    return value


def _metric(values: list[int | None]) -> dict[str, Any]:
    observed = [value for value in values if value is not None]
    count = len(observed)
    total = len(values)
    return {
        "sum": sum(observed) if count else None,
        "total": sum(observed) if total and count == total else None,
        "mean": sum(observed) / count if count else None,
        "observed": count,
        "unknown": total - count,
        "coverage": count / total if total else None,
    }


def summarize(
    records: Iterable[Mapping[str, Any] | QuickEvalRecord], *, strict: bool = False
) -> dict[str, Any]:
    """Summarize observed results; never fill missing metrics with zero.

    A known-outcome acceptance rate is not a claim of experimental comparability.
    Runs with identifiers are deduplicated across the entire input, not per mode.
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    unidentified = 0
    identity_incomplete = 0
    count = 0
    for index, record in enumerate(records, 1):
        try:
            item = validate_record(
                asdict(record) if isinstance(record, QuickEvalRecord) else record,
                strict=strict,
            )
        except ValueError as exc:
            raise ValueError(f"record {index}: {exc}") from exc
        run_id = item.get("run_id")
        if run_id is None:
            unidentified += 1
        elif run_id in seen:
            raise ValueError(f"record {index}: duplicate run_id: {run_id!r}")
        else:
            seen.add(run_id)
        identity_incomplete += any(item.get(name) is None for name in IDENTITY_FIELDS)
        buckets.setdefault(item["mode"], []).append(item)
        count += 1

    groups: dict[str, Any] = {}
    for mode in sorted(buckets):
        rows = buckets[mode]
        runs = len(rows)
        accepted = sum(row.get("accepted") is True for row in rows)
        rejected = sum(row.get("accepted") is False for row in rows)
        known = accepted + rejected
        metrics = {name: _metric([row.get(name) for row in rows]) for name in METRICS}
        metrics["tokens"] = _metric([
            row["input_tokens"] + row["output_tokens"]
            if row.get("input_tokens") is not None and row.get("output_tokens") is not None
            else None
            for row in rows
        ])
        intervention_known = sum(row.get("human_intervention") is not None for row in rows)
        all_tokens = metrics["tokens"]["total"]
        groups[mode] = {
            "runs": runs,
            "accepted": accepted,
            "rejected": rejected,
            "unknown_quality": runs - known,
            "unknown": runs - known,
            "accepted_rate": accepted / known if known else None,
            "acceptance_coverage": known / runs,
            "human_intervention": sum(row.get("human_intervention") is True for row in rows),
            "unknown_human_intervention": runs - intervention_known,
            "human_intervention_coverage": intervention_known / runs,
            "metrics": metrics,
            # Compatibility names now mean complete totals, never partial sums.
            "tokens": all_tokens,
            "duration_ms": metrics["duration_ms"]["total"],
            "tokens_per_run": metrics["tokens"]["mean"],
            # Includes measured failed attempts. Unknown outcomes/cost block it.
            "tokens_per_accepted_run": (
                all_tokens / accepted
                if all_tokens is not None and accepted and known == runs else None
            ),
        }
    return {
        "schema": "quick-adaptive-eval-report-v2",
        "record_count": count,
        "groups": groups,
        "identity": {
            "runs_without_id": unidentified,
            "incomplete_runs": identity_incomplete,
            "deduplication_complete": count > 0 and unidentified == 0,
        },
        "rules": {
            "quality_from_tokens": False,
            "missing_acceptance_is_unknown": True,
            "missing_metrics_are_unknown": True,
            "acceptance_denominator": "known_outcomes",
            "comparability_verified": False,
            "acceptance_evidence_verified": False,
        },
    }
