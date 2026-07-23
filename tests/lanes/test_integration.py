import hashlib
import json
from pathlib import Path

from specify_cli.lanes.integration import assess_integration_readiness, collect_integration_candidates, mark_lane_integrated
from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


def _current_ui_task() -> dict[str, object]:
    return {
        "id": "T001",
        "ui_contract": {
            "ui_work_type": "feature-extension",
            "surface_type": "product-workspace",
            "platforms": ["web"],
            "subject": "settings",
            "audience": "account owners",
            "single_job": "update account settings",
            "visual_thesis": "clear grouped settings",
            "content_thesis": "real settings labels and values",
            "interaction_thesis": "edit then save with explicit feedback",
            "signature_element": "persistent save state",
            "approved_visual_ref": "DESIGN.md#settings",
            "approved_preview_sha256": "",
            "approved_manifest_sha256": "",
            "design_decision_ids": ["DS-COMP-001", "DS-RESP-001"],
            "design_sources": ["DESIGN.md", "ui-brief.md"],
            "reference_notes": "Preserve the approved hierarchy.",
            "visual_target": "Match the approved settings direction.",
            "reference_intents": [],
            "real_content_plan": [
                {"source_ref": "src/data/settings.ts", "usage": "field labels"}
            ],
            "image_plan": [],
            "color_modes": ["light", "dark"],
            "component_contracts": [
                {
                    "component": "settings form",
                    "decision_ids": ["DS-COMP-001"],
                    "required_states": ["loading", "error", "saved"],
                }
            ],
            "responsive_matrix": [
                {"viewport": "390", "adaptation": "stack settings sections"}
            ],
            "motion_contract": {
                "purpose": "show save feedback",
                "reduced_motion": "instant state change",
            },
            "visual_acceptance_matrix": [
                {"viewport": "390", "state": "saved", "evidence": "visual_capture"}
            ],
            "comparison_tolerance": "no unapproved structural drift",
            "accepted_deviations": [],
            "fidelity_level": "high",
            "must_preserve": ["settings hierarchy"],
            "may_adapt": ["spacing within tokens"],
            "must_not": ["replace real labels with placeholders"],
            "required_states": ["loading", "error", "saved"],
            "required_evidence": [
                "structure_snapshot",
                "visual_capture",
                "runtime_diagnostics",
                "visual_comparison_or_human_review",
            ],
        },
    }


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
    comparison_content = json.dumps(
        {
                "schema": "spec-kit-visual-comparison-v1",
                "task_id": "T001",
                "entry_point": "/settings",
                "approved": {
                    "visual_ref": "DESIGN.md#settings",
                    "preview_sha256": "",
                    "manifest_sha256": "",
                    "direction_id": "settings",
                    "decision_ids": ["DS-COMP-001", "DS-RESP-001"],
                },
                "implementation": {
                    "revision": "main@abc123",
                    "capture_refs": ["evidence/screen.png"],
                    "structure_snapshot_refs": ["evidence/a11y.json"],
                    "runtime_diagnostic_refs": ["evidence/console.txt"],
                },
                "matrix": [
                    {
                        "viewport": "390",
                        "color_mode": "light",
                        "motion_mode": "reduced",
                        "state": "saved",
                        "approved_target": "DESIGN.md#settings",
                        "implementation_capture_ref": "evidence/screen.png",
                        "covered_decision_ids": [
                            "DS-COMP-001",
                            "DS-RESP-001",
                        ],
                        "structural_differences": [],
                        "visual_differences": [],
                        "result": "passed",
                    }
                ],
                "comparison_tolerance": "no unapproved structural drift",
                "accepted_deviations": [],
                "decision_coverage": [],
                "verdict": "passed",
                "reviewer": "agent",
        }
    )
    (evidence_dir / "comparison.json").write_text(
        comparison_content,
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [_current_ui_task()],
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
                {"kind": "structure_snapshot", "ref": "evidence/a11y.json"},
                {"kind": "visual_capture", "ref": "evidence/screen.png"},
                {"kind": "runtime_diagnostics", "ref": "evidence/console.txt"},
            ],
            "contract_check": "passed",
            "runtime_evidence": "passed",
            "visual_comparison": "passed",
            "fidelity_status": "passed",
            "approved_visual_ref": "DESIGN.md#settings",
            "approved_preview_sha256": "",
            "approved_manifest_sha256": "",
            "comparison_report_ref": "evidence/comparison.json",
            "comparison_report_sha256": hashlib.sha256(
                comparison_content.encode("utf-8")
            ).hexdigest(),
            "implementation_capture_refs": ["evidence/screen.png"],
            "covered_decision_ids": ["DS-COMP-001", "DS-RESP-001"],
            "structural_differences": [],
            "visual_differences": [],
            "comparison_tolerance": "no unapproved structural drift",
            "accepted_deviations": [],
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

    comparison_sha = lifecycle["ui_verification"]["comparison_report_sha256"]
    lifecycle["ui_verification"]["comparison_report_sha256"] = "0" * 64
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    tampered_comparison = assess_integration_readiness(tmp_path, lane)
    assert tampered_comparison.ready is False
    assert any(
        "comparison_report_sha256" in check["detail"]
        for check in tampered_comparison.checks
    )
    lifecycle["ui_verification"]["comparison_report_sha256"] = comparison_sha

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


def test_assess_integration_readiness_rejects_obsolete_ui_task_contract(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_fidelity_requirements": {"level": "high"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
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
        check["name"] == "current-ui-contract"
        and "ui_fidelity_requirements" in check["detail"]
        for check in readiness.checks
    )


def test_assess_integration_readiness_rejects_partial_current_ui_contract(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {"subject": "settings"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
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
        check["name"] == "valid-ui-contract"
        and "missing current fields" in check["detail"]
        for check in readiness.checks
    )
