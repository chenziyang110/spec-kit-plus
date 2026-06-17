import json
from pathlib import Path

from specify_cli.execution.implementation_review import (
    ImplementationRepairOperation,
    ImplementationRepairRecord,
    ImplementationReviewFinding,
    ImplementationReviewRecord,
    next_append_task_id,
    snapshot_artifacts,
    validate_workflow_state_review_update,
    write_repair_record,
    write_review_record,
)


def test_write_review_record_appends_feature_dir_ndjson(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    finding = ImplementationReviewFinding(
        finding_id="IR-001",
        finding_type="missing_validation",
        severity="medium",
        summary="Real entrypoint validation is missing",
        affected_artifacts=["tasks.md"],
        task_ids=["T004"],
        repairable_at_task_layer=True,
        recommendation="Insert a real-entrypoint validation task",
    )
    record = ImplementationReviewRecord(
        review_id="pre-implement-r1",
        scope="pre-implement",
        trigger="before_first_task",
        decision="repair-and-continue",
        reviewed_tasks=["T001", "T002", "T003", "T004"],
        remaining_tasks=["T001", "T002", "T003", "T004"],
        findings=[finding],
        next_action="repair task-layer validation coverage",
    )

    path = write_review_record(feature_dir, record)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert path == feature_dir / "implementation-review" / "reviews.ndjson"
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["review_id"] == "pre-implement-r1"
    assert payload["findings"][0]["finding_type"] == "missing_validation"


def test_write_repair_record_appends_feature_dir_ndjson(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    record = ImplementationRepairRecord(
        repair_id="repair-pre-implement-r1",
        source_review_id="pre-implement-r1",
        changed_artifacts=["tasks.md", "task-packets/T081.json"],
        operations=[
            ImplementationRepairOperation(
                operation="insert_task",
                task_id="T081",
                details={"repair_for": "T004", "reason": "missing real-entrypoint validation"},
            )
        ],
        completed_tasks_preserved=True,
        next_batch="T001-T005",
    )

    path = write_repair_record(feature_dir, record)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert path == feature_dir / "implementation-review" / "repairs.ndjson"
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["repair_id"] == "repair-pre-implement-r1"
    assert payload["operations"][0]["task_id"] == "T081"


def test_snapshot_artifacts_copies_existing_task_layer_files(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (feature_dir / "handoff-to-implement.json").write_text('{"status": "ready"}\n', encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# State\n", encoding="utf-8")
    (feature_dir / "task-packets").mkdir()
    (feature_dir / "task-packets" / "T001.json").write_text('{"task_id": "T001"}\n', encoding="utf-8")

    snapshots = snapshot_artifacts(
        feature_dir,
        review_id="pre-implement-r1",
        relative_paths=[
            "tasks.md",
            "handoff-to-implement.json",
            "workflow-state.md",
            "task-packets/T001.json",
            "missing.json",
        ],
    )

    assert snapshots == [
        "implementation-review/snapshots/tasks.before-pre-implement-r1.md",
        "implementation-review/snapshots/handoff-to-implement.before-pre-implement-r1.json",
        "implementation-review/snapshots/workflow-state.before-pre-implement-r1.md",
        "implementation-review/snapshots/task-packets__T001.before-pre-implement-r1.json",
    ]
    for rel_path in snapshots:
        assert (feature_dir / rel_path).exists()


def test_snapshot_artifacts_rejects_out_of_feature_and_unapproved_paths(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    outside = tmp_path / "specs" / "plan.md"
    outside.write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "task-packets").mkdir()
    (feature_dir / "task-packets" / "T001.txt").write_text("not json\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    snapshots = snapshot_artifacts(
        feature_dir,
        review_id="pre-implement-r1",
        relative_paths=[
            "../plan.md",
            str(outside),
            "spec.md",
            "task-packets/T001.txt",
            "tasks.md",
        ],
    )

    assert snapshots == ["implementation-review/snapshots/tasks.before-pre-implement-r1.md"]


def test_next_append_task_id_preserves_numeric_width() -> None:
    assert next_append_task_id([]) == "T001"
    assert next_append_task_id(["T001", "T080"]) == "T081"
    assert next_append_task_id(["T009", "T099"]) == "T100"
    assert next_append_task_id(["T0009"]) == "T0010"


def test_validate_workflow_state_review_update_allows_only_review_fields() -> None:
    before = {
        "active_profile": "Reference-Implementation",
        "required_evidence": ["reference source evidence"],
        "final_handoff_decision": "/sp.implement",
        "gate_status": "cleared",
        "next_action": "begin implementation",
        "next_command": "/sp.implement",
    }
    allowed_after = before | {
        "next_action": "run pre-implement review",
        "next_command": "/sp.debug",
        "review_gate": {"status": "blocked"},
        "review_window_policy": {"max_completed_tasks_before_review": 5},
    }

    assert validate_workflow_state_review_update(before, allowed_after) == []

    blocked_after = allowed_after | {
        "required_evidence": [],
        "final_handoff_decision": "/sp.tasks",
        "gate_status": "blocked",
    }

    errors = validate_workflow_state_review_update(before, blocked_after)

    assert "required_evidence is protected for embedded review" in errors
    assert "final_handoff_decision is protected for embedded review" in errors
    assert "gate_status is protected for embedded review" in errors


def test_validate_workflow_state_review_update_rejects_public_or_unknown_review_routes() -> None:
    before = {
        "next_command": "/sp.implement",
    }

    assert validate_workflow_state_review_update(before, {"next_command": "/sp.review"}) == [
        "next_command has invalid embedded review route: /sp.review"
    ]
    assert validate_workflow_state_review_update(before, {"next_command": "sp-review"}) == [
        "next_command has invalid embedded review route: sp-review"
    ]
    assert validate_workflow_state_review_update(before, {"next_command": "/sp.tasks"}) == []
