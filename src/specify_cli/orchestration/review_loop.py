"""Helpers for review-gated batch execution."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.codex_team.state_paths import batch_record_path, review_record_path
from specify_cli.codex_team.task_ops import get_task, mark_join_point
from specify_cli.execution.review_schema import ReviewFinding, ReviewRoundRecord, review_round_payload


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_review_lanes(batch_payload: dict[str, object], *, round_number: int) -> list[dict[str, object]]:
    if not batch_payload.get("review_required"):
        return []

    suffix = f"r{round_number}"
    reason = str(batch_payload.get("review_reason", "high_risk_batch"))
    batch_name = str(batch_payload.get("batch_name", batch_payload.get("batch_id", "batch")))
    return [
        {
            "lane_id": f"simplify-review-{suffix}",
            "category": "simplify",
            "reason": reason,
            "summary": f"Review {batch_name} for avoidable complexity",
        },
        {
            "lane_id": f"harden-review-{suffix}",
            "category": "harden",
            "reason": reason,
            "summary": f"Review {batch_name} for resilience and security gaps",
        },
        {
            "lane_id": f"spec-review-{suffix}",
            "category": "spec",
            "reason": reason,
            "summary": f"Review {batch_name} for contract and acceptance drift",
        },
    ]


def compile_review_fix_tasks(findings: list[ReviewFinding]) -> dict[str, object]:
    inline_findings = [finding for finding in findings if finding.severity == "low"]
    followup_findings = [finding for finding in findings if finding.severity != "low"]
    highest = min(
        (finding.severity for finding in findings),
        key=lambda item: _SEVERITY_ORDER[item],
        default="low",
    )
    return {
        "inline_findings": [
            {
                "finding_id": finding.finding_id,
                "severity": finding.severity,
                "summary": finding.summary,
                "file_path": finding.file_path,
                "recommendation": finding.recommendation,
            }
            for finding in inline_findings
        ],
        "followup_findings": [
            {
                "finding_id": finding.finding_id,
                "severity": finding.severity,
                "summary": finding.summary,
                "file_path": finding.file_path,
                "recommendation": finding.recommendation,
            }
            for finding in followup_findings
        ],
        "highest_severity": highest,
    }


def record_review_round(
    project_root: Path,
    *,
    batch_id: str,
    findings: list[ReviewFinding],
    round_number: int,
) -> dict[str, object]:
    batch_path = batch_record_path(project_root, batch_id)
    batch_payload = json.loads(batch_path.read_text(encoding="utf-8"))
    review_id = f"{batch_id}-round-{round_number}"
    review_status = "approved" if not findings else "fix_required"
    review_record = ReviewRoundRecord(
        review_id=review_id,
        batch_id=batch_id,
        round_number=round_number,
        status=review_status,
        findings=findings,
    )

    record_path = review_record_path(project_root, review_id)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(review_round_payload(review_record), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    batch_payload["review_round"] = round_number
    batch_payload["review_record_ids"] = list(batch_payload.get("review_record_ids", [])) + [review_id]
    batch_payload["review_status"] = review_status
    batch_payload["status"] = "completed" if review_status == "approved" else "review_fix_required"
    batch_path.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    join_point_name = str(batch_payload.get("join_point_name") or "")
    if join_point_name:
        join_status = "complete" if review_status == "approved" else "review_pending"
        for task_id in [str(item) for item in batch_payload.get("task_ids", [])]:
            task = get_task(project_root, task_id)
            mark_join_point(
                project_root,
                task_id=task_id,
                join_point_name=join_point_name,
                expected_version=task.version,
                status=join_status,
                details={
                    "batch_id": batch_id,
                    "batch_name": batch_payload.get("batch_name", ""),
                    "review_status": review_status,
                    "review_round": round_number,
                },
            )

    return {
        "review_id": review_id,
        "batch_id": batch_id,
        "round_number": round_number,
        "status": review_status,
        "fix_plan": compile_review_fix_tasks(findings),
    }
