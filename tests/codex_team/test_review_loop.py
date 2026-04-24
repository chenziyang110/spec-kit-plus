import json
from pathlib import Path

from specify_cli.codex_team.state_paths import batch_record_path
from specify_cli.codex_team.task_ops import create_task, get_task
from specify_cli.codex_team.runtime_state import batch_record_payload
from specify_cli.execution.review_schema import ReviewFinding
from specify_cli.orchestration.review_loop import (
    build_review_lanes,
    compile_review_fix_tasks,
    record_review_round,
)


def test_build_review_lanes_returns_expected_audit_lanes_for_required_review() -> None:
    batch_payload = {
        "batch_id": "batch-1",
        "batch_name": "Parallel Batch 1.1",
        "review_required": True,
        "peer_review_lane_recommended": True,
        "review_reason": "schema_change+protocol_seam",
        "task_ids": ["T002", "T003"],
    }

    lanes = build_review_lanes(batch_payload, round_number=1)

    assert [lane["lane_id"] for lane in lanes] == [
        "simplify-review-r1",
        "harden-review-r1",
        "spec-review-r1",
    ]
    assert lanes[0]["reason"] == "schema_change+protocol_seam"


def test_compile_review_fix_tasks_splits_inline_low_severity_from_followup_work() -> None:
    findings = [
        ReviewFinding(
            finding_id="F-1",
            lane_id="simplify-review-r1",
            category="simplify",
            severity="low",
            summary="Remove dead branch",
            file_path="src/app.py",
            line_number=14,
            recommendation="Delete the unreachable branch",
        ),
        ReviewFinding(
            finding_id="F-2",
            lane_id="harden-review-r1",
            category="harden",
            severity="high",
            summary="Missing validation",
            file_path="src/api.py",
            line_number=21,
            recommendation="Validate external input before use",
        ),
    ]

    fix_plan = compile_review_fix_tasks(findings)

    assert [item["finding_id"] for item in fix_plan["inline_findings"]] == ["F-1"]
    assert [item["finding_id"] for item in fix_plan["followup_findings"]] == ["F-2"]
    assert fix_plan["highest_severity"] == "high"


def test_record_review_round_marks_batch_fix_required_and_join_points_review_pending(codex_team_project_root: Path) -> None:
    batch_path = batch_record_path(codex_team_project_root, "batch-1")
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        json.dumps(
            batch_record_payload(
                batch_id="batch-1",
                batch_name="Parallel Batch 1.1",
                session_id="default",
                feature_dir="specs/001-test-feature",
                task_ids=["T002", "T003"],
                request_ids=["req-1", "req-2"],
                join_point_name="Join Point 1.1",
                status="awaiting_review",
            )
            | {
                "review_required": True,
                "peer_review_lane_recommended": True,
                "review_reason": "schema_change",
                "review_status": "awaiting_review",
                "review_round": 0,
                "review_record_ids": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for task_id in ("T002", "T003"):
        create_task(
            codex_team_project_root,
            task_id=task_id,
            summary=f"{task_id} summary",
            metadata={
                "join_points": {
                    "Join Point 1.1": {
                        "status": "review_pending",
                        "details": {
                            "batch_id": "batch-1",
                            "batch_name": "Parallel Batch 1.1",
                        },
                    }
                }
            },
        )

    record = record_review_round(
        codex_team_project_root,
        batch_id="batch-1",
        findings=[
            ReviewFinding(
                finding_id="F-2",
                lane_id="harden-review-r1",
                category="harden",
                severity="high",
                summary="Missing validation",
                file_path="src/api.py",
                line_number=21,
                recommendation="Validate external input before use",
            )
        ],
        round_number=1,
    )

    updated_batch = json.loads(batch_path.read_text(encoding="utf-8"))
    assert record["status"] == "fix_required"
    assert updated_batch["review_status"] == "fix_required"
    assert updated_batch["review_round"] == 1
    assert updated_batch["status"] == "review_fix_required"
    task = get_task(codex_team_project_root, "T002")
    assert task.metadata["join_points"]["Join Point 1.1"]["status"] == "review_pending"
