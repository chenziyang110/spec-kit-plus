import json
from pathlib import Path

from specify_cli.lanes.integration import assess_integration_readiness, collect_integration_candidates, mark_lane_integrated
from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


def test_collect_integration_candidates_returns_completed_or_ready_lanes(tmp_path: Path):
    ready_lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        verification_status="passed",
        last_command="implement",
    )
    blocked_lane = LaneRecord(
        lane_id="lane-002",
        feature_id="002-demo",
        feature_dir="specs/002-demo",
        branch_name="002-demo",
        worktree_path=".specify/lanes/worktrees/lane-002",
        lifecycle_state="implementing",
        recovery_state="blocked",
        last_command="implement",
    )
    write_lane_record(tmp_path, ready_lane)
    write_lane_record(tmp_path, blocked_lane)
    write_lane_index(
        tmp_path,
        {"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]},
    )

    candidates = collect_integration_candidates(tmp_path)

    assert [candidate.feature_id for candidate in candidates] == ["001-demo", "002-demo"]


def test_assess_integration_readiness_reports_failed_checks(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="blocked",
        verification_status="failed",
        last_command="implement",
    )

    readiness = assess_integration_readiness(tmp_path, lane)

    assert readiness.ready is False
    assert any(check["name"] == "verification-passed" and check["status"] == "fail" for check in readiness.checks)


def test_mark_lane_integrated_marks_completed_and_preserves_lane_id(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="integrating",
        recovery_state="resumable",
        verification_status="passed",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane)

    updated = mark_lane_integrated(tmp_path, lane)

    assert updated.lane_id == "lane-001"
    assert updated.lifecycle_state == "completed"
    assert updated.recovery_state == "completed"
    assert updated.last_command == "integrate"


def test_assess_integration_readiness_requires_integrated_ui_evidence(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-ui"
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    evidence_dir = feature_dir / "evidence"
    lifecycle_dir.mkdir(parents=True)
    evidence_dir.mkdir()
    for name in ("a11y.json", "screen.png", "console.txt"):
        (evidence_dir / name).write_text("evidence\n", encoding="utf-8")
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "contract_version": 2,
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    lifecycle = {
        "task_id": "T001",
        "status": "accepted",
        "changed_paths": ["src/ui/settings.tsx"],
        "validation": [{"command": "npm test -- settings-ui", "status": "passed"}],
        "review": None,
        "blockers": [],
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "task",
            "integration_base_ref": None,
            "evidence": [
                {"kind": "accessibility_snapshot", "ref": "evidence/a11y.json"},
                {"kind": "screenshot", "ref": "evidence/screen.png"},
                {"kind": "console_runtime", "ref": "evidence/console.txt"},
            ],
            "contract_check": "passed",
            "runtime_evidence": "passed",
            "visual_comparison": "passed",
            "fidelity_status": "passed",
        },
    }
    lifecycle_path = lifecycle_dir / "T001.json"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: resolved\n---\n\nnext_action: integrate\n",
        encoding="utf-8",
    )
    lane = LaneRecord(
        lane_id="lane-ui",
        feature_id="001-ui",
        feature_dir="specs/001-ui",
        branch_name="001-ui",
        worktree_path=".specify/lanes/worktrees/lane-ui",
        lifecycle_state="implementing",
        recovery_state="completed",
        verification_status="passed",
        last_command="implement",
    )

    readiness = assess_integration_readiness(tmp_path, lane)
    assert readiness.ready is False
    assert any(
        check["name"] == "integrated-ui-evidence" and check["status"] == "fail"
        for check in readiness.checks
    )

    lifecycle["ui_verification"]["evidence_scope"] = "integrated"
    lifecycle["ui_verification"]["integration_base_ref"] = "main@abc123"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    assert assess_integration_readiness(tmp_path, lane).ready is True

    lifecycle["status"] = "pending"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    pending = assess_integration_readiness(tmp_path, lane)
    assert pending.ready is False
    assert any(
        check["name"] == "integrated-ui-evidence"
        and "status must be accepted" in check["detail"]
        for check in pending.checks
    )

    lifecycle["status"] = "accepted"
    lifecycle["validation"] = []
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    missing_validation = assess_integration_readiness(tmp_path, lane)
    assert missing_validation.ready is False
    assert any(
        check["name"] == "integrated-ui-evidence"
        and "validation must be a non-empty list" in check["detail"]
        for check in missing_validation.checks
    )
