"""Quick adaptive execution evaluation utilities.

This module defines a small, offline evaluation contract. It does not run agents,
assign quality scores, or infer acceptance. A harness supplies observed run
records from an external evaluator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QuickEvalRecord:
    case_id: str
    mode: str  # worker-full, worker-compact, direct-full, direct-compact
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: int | None = None
    duration_ms: int | None = None
    accepted: bool | None = None
    human_intervention: bool | None = None
    notes: dict[str, Any] = field(default_factory=dict)


def summarize(records: list[QuickEvalRecord]) -> dict[str, Any]:
    """Aggregate observed metrics without inventing missing values."""
    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        group = groups.setdefault(record.mode, {"runs": 0, "accepted": 0, "unknown": 0})
        group["runs"] += 1
        if record.accepted is True:
            group["accepted"] += 1
        elif record.accepted is None:
            group["unknown"] += 1
    return {"groups": groups, "record_count": len(records)}
