"""Structured review findings and review-round records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Literal


ReviewSeverity = Literal["critical", "high", "medium", "low"]
ReviewCategory = Literal["simplify", "harden", "spec"]


@dataclass(slots=True)
class ReviewFinding:
    finding_id: str
    lane_id: str
    category: ReviewCategory
    severity: ReviewSeverity
    summary: str
    file_path: str
    line_number: int = 0
    recommendation: str = ""


@dataclass(slots=True)
class ReviewRoundRecord:
    review_id: str
    batch_id: str
    round_number: int
    status: str
    findings: list[ReviewFinding] = field(default_factory=list)


def _filter_dataclass_payload(cls: type, payload: dict[str, object]) -> dict[str, object]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in payload.items() if key in allowed}


def review_finding_payload(finding: ReviewFinding) -> dict[str, object]:
    return asdict(finding)


def review_round_payload(record: ReviewRoundRecord) -> dict[str, object]:
    return asdict(record)


def review_round_from_json(text: str) -> ReviewRoundRecord:
    payload = json.loads(text)
    findings = [
        ReviewFinding(**_filter_dataclass_payload(ReviewFinding, item))
        for item in payload.get("findings", [])
        if isinstance(item, dict)
    ]
    data = _filter_dataclass_payload(ReviewRoundRecord, payload)
    data["findings"] = findings
    return ReviewRoundRecord(**data)
