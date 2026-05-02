import json

import pytest

from specify_cli.codex_team.state_paths import task_claim_path, task_record_path
from specify_cli.codex_team.task_ops import (
    ClaimConflictError,
    ClaimValidationError,
    TaskOpsError,
    TransitionError,
    claim_task,
    create_task,
    get_task,
    list_tasks,
    mark_join_point,
    record_task_approval,
    transition_task_status,
    update_task_metadata,
)


def test_create_task_persists_record(codex_team_project_root):
    record = create_task(codex_team_project_root, task_id="task-1", summary="initial work")

    assert record.task_id == "task-1"
    assert record.status == "pending"
    assert record.summary == "initial work"


def test_list_tasks_returns_all_created_entries(codex_team_project_root):
    create_task(codex_team_project_root, task_id="task-alpha")
    create_task(codex_team_project_root, task_id="task-beta")

    ids = {task.task_id for task in list_tasks(codex_team_project_root)}

    assert ids == {"task-alpha", "task-beta"}


def test_update_task_metadata_increments_version(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-2", summary="phase one")

    updated = update_task_metadata(
        codex_team_project_root,
        "task-2",
        summary="phase two",
        expected_version=created.version,
    )

    assert updated.version == created.version + 1
    assert updated.summary == "phase two"


def test_created_at_not_reset_on_metadata_updates(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-2a", summary="phase one")

    updated = update_task_metadata(
        codex_team_project_root,
        "task-2a",
        metadata={"phase": "two"},
        expected_version=created.version,
    )

    assert updated.created_at == created.created_at
    assert updated.updated_at != created.updated_at


def test_claim_task_records_token_and_worker(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-3")
    token = claim_task(
        codex_team_project_root,
        task_id="task-3",
        worker_id="worker-a",
        expected_version=created.version,
    )

    assert isinstance(token, str) and token

    record = get_task(codex_team_project_root, "task-3")
    claim_meta = record.metadata.get("current_claim")

    assert claim_meta["claim_id"] == token
    assert claim_meta["worker_id"] == "worker-a"


def test_claim_task_enforces_expected_version(codex_team_project_root):
    create_task(codex_team_project_root, task_id="task-4")

    with pytest.raises(TaskOpsError):
        claim_task(
            codex_team_project_root,
            task_id="task-4",
            worker_id="worker-b",
            expected_version=2,
        )


def test_claim_task_rejects_conflicts(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-5")
    claim_task(
        codex_team_project_root,
        task_id="task-5",
        worker_id="worker-a",
        expected_version=created.version,
    )

    with pytest.raises(ClaimConflictError):
        claim_task(
            codex_team_project_root,
            task_id="task-5",
            worker_id="worker-b",
            expected_version=created.version + 1,
        )


def test_status_transitions_follow_allowed_path(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-6")
    token = claim_task(
        codex_team_project_root,
        task_id="task-6",
        worker_id="worker-a",
        expected_version=created.version,
    )

    in_progress = transition_task_status(
        codex_team_project_root,
        task_id="task-6",
        new_status="in_progress",
        owner="worker-a",
        expected_version=created.version + 1,
        claim_token=token,
    )

    assert in_progress.status == "in_progress"

    completed = transition_task_status(
        codex_team_project_root,
        task_id="task-6",
        new_status="completed",
        owner="worker-a",
        expected_version=in_progress.version,
        claim_token=token,
    )

    assert completed.status == "completed"


def test_status_transition_invalid_sequence_is_rejected(codex_team_project_root):
    create_task(codex_team_project_root, task_id="task-7")

    with pytest.raises(TransitionError):
        transition_task_status(
            codex_team_project_root,
            task_id="task-7",
            new_status="completed",
            owner="worker-a",
            expected_version=1,
            claim_token="fake",
        )


def test_claim_token_mismatch_rejected(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-10")
    claim_task(
        codex_team_project_root,
        task_id="task-10",
        worker_id="worker-a",
        expected_version=created.version,
    )

    record = get_task(codex_team_project_root, "task-10")
    with pytest.raises(ClaimValidationError):
        transition_task_status(
            codex_team_project_root,
            task_id="task-10",
            new_status="in_progress",
            owner="worker-a",
            expected_version=record.version,
            claim_token="invalid",
        )


def test_claim_worker_mismatch_rejected(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-11")
    token = claim_task(
        codex_team_project_root,
        task_id="task-11",
        worker_id="worker-a",
        expected_version=created.version,
    )

    record = get_task(codex_team_project_root, "task-11")
    with pytest.raises(ClaimValidationError):
        transition_task_status(
            codex_team_project_root,
            task_id="task-11",
            new_status="in_progress",
            owner="worker-b",
            expected_version=record.version,
            claim_token=token,
        )


def _tamper_claim_file(project_root, claim_id, transform):
    path = task_claim_path(project_root, claim_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    transform(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_claim_validation_checks_canonical_claim_file(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-17")
    token = claim_task(
        codex_team_project_root,
        task_id="task-17",
        worker_id="worker-a",
        expected_version=created.version,
    )

    _tamper_claim_file(codex_team_project_root, token, lambda payload: payload.update({"worker_id": "intruder"}))
    record = get_task(codex_team_project_root, "task-17")
    with pytest.raises(ClaimValidationError):
        transition_task_status(
            codex_team_project_root,
            task_id="task-17",
            new_status="in_progress",
            owner="worker-a",
            expected_version=record.version,
            claim_token=token,
        )


def test_claim_validation_rejects_mismatched_task_id(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-18")
    token = claim_task(
        codex_team_project_root,
        task_id="task-18",
        worker_id="worker-a",
        expected_version=created.version,
    )

    _tamper_claim_file(codex_team_project_root, token, lambda payload: payload.update({"task_id": "task-wrong"}))
    record = get_task(codex_team_project_root, "task-18")
    with pytest.raises(ClaimValidationError):
        transition_task_status(
            codex_team_project_root,
            task_id="task-18",
            new_status="in_progress",
            owner="worker-a",
            expected_version=record.version,
            claim_token=token,
        )


def test_claim_validation_rejects_mismatched_claim_id(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-19")
    token = claim_task(
        codex_team_project_root,
        task_id="task-19",
        worker_id="worker-a",
        expected_version=created.version,
    )

    _tamper_claim_file(codex_team_project_root, token, lambda payload: payload.update({"claim_id": "wrong"}))
    record = get_task(codex_team_project_root, "task-19")
    with pytest.raises(ClaimValidationError):
        transition_task_status(
            codex_team_project_root,
            task_id="task-19",
            new_status="in_progress",
            owner="worker-a",
            expected_version=record.version,
            claim_token=token,
        )


def test_record_task_approvals_and_rejections(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-8")
    token = claim_task(
        codex_team_project_root,
        task_id="task-8",
        worker_id="worker-a",
        expected_version=created.version,
    )

    transition_task_status(
        codex_team_project_root,
        task_id="task-8",
        new_status="in_progress",
        owner="worker-a",
        expected_version=created.version + 1,
        claim_token=token,
    )

    approved = record_task_approval(
        codex_team_project_root,
        task_id="task-8",
        decision="approved",
        worker_id="worker-a",
        claim_token=token,
        expected_version=created.version + 2,
    )

    assert approved["decision"] == "approved"

    record = get_task(codex_team_project_root, "task-8")
    assert record.metadata["approvals"][-1]["decision"] == "approved"
    assert approved["claim_id"] == token
    assert approved["task_version"] == record.version - 1
    assert approved["claim_version"] == created.version
    assert approved["claim_worker_id"] == "worker-a"

    rejected = record_task_approval(
        codex_team_project_root,
        task_id="task-8",
        decision="rejected",
        worker_id="worker-a",
        claim_token=token,
        expected_version=record.version,
        reason="needs more info",
    )

    assert rejected["decision"] == "rejected"


def test_record_task_approval_uses_canonical_claim_data(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-16")
    token = claim_task(
        codex_team_project_root,
        task_id="task-16",
        worker_id="worker-a",
        expected_version=created.version,
    )

    path = task_record_path(codex_team_project_root, "task-16")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metadata"]["current_claim"]["worker_id"] = "tampered"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    record = get_task(codex_team_project_root, "task-16")
    entry = record_task_approval(
        codex_team_project_root,
        task_id="task-16",
        decision="approved",
        worker_id="worker-a",
        claim_token=token,
        expected_version=record.version,
    )

    assert entry["claim_worker_id"] == "worker-a"
    assert entry["claim_id"] == token
    claim_payload = json.loads(task_claim_path(codex_team_project_root, token).read_text(encoding="utf-8"))
    assert entry["claim_created_at"] == claim_payload["created_at"]
    assert record.metadata["current_claim"]["created_at"] == claim_payload["created_at"]


def test_join_point_entry_includes_provenance(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-12")
    token = claim_task(
        codex_team_project_root,
        task_id="task-12",
        worker_id="worker-a",
        expected_version=created.version,
    )

    in_progress = transition_task_status(
        codex_team_project_root,
        task_id="task-12",
        new_status="in_progress",
        owner="worker-a",
        expected_version=created.version + 1,
        claim_token=token,
    )

    entry = mark_join_point(
        codex_team_project_root,
        task_id="task-12",
        join_point_name="batch-sync",
        expected_version=in_progress.version,
        details={"batch": "alpha"},
    )

    assert entry["claim_id"] == token
    assert entry["claim_worker_id"] == "worker-a"
    assert entry["task_version"] == in_progress.version
    assert entry["details"] == {"batch": "alpha"}


def test_mark_join_point_records_marker(codex_team_project_root):
    create_task(codex_team_project_root, task_id="task-9")

    record = get_task(codex_team_project_root, "task-9")
    entry = mark_join_point(
        codex_team_project_root,
        task_id="task-9",
        join_point_name="batch-sync",
        status="complete",
        expected_version=record.version,
        details={"source": "test"},
    )

    assert entry["status"] == "complete"

    assert entry["details"] == {"source": "test"}

    record = get_task(codex_team_project_root, "task-9")
    assert record.metadata["join_points"]["batch-sync"]["status"] == "complete"


def test_mark_join_point_enforces_expected_version(codex_team_project_root):
    create_task(codex_team_project_root, task_id="task-13")
    record = get_task(codex_team_project_root, "task-13")

    with pytest.raises(TaskOpsError):
        mark_join_point(
            codex_team_project_root,
            task_id="task-13",
            join_point_name="batch-sync",
            status="complete",
            expected_version=record.version + 1,
        )


def test_terminal_transition_clears_claim_and_blocks_approvals(codex_team_project_root):
    created = create_task(codex_team_project_root, task_id="task-14")
    token = claim_task(
        codex_team_project_root,
        task_id="task-14",
        worker_id="worker-a",
        expected_version=created.version,
    )

    in_progress = transition_task_status(
        codex_team_project_root,
        task_id="task-14",
        new_status="in_progress",
        owner="worker-a",
        expected_version=created.version + 1,
        claim_token=token,
    )

    transition_task_status(
        codex_team_project_root,
        task_id="task-14",
        new_status="completed",
        owner="worker-a",
        expected_version=in_progress.version,
        claim_token=token,
    )

    record = get_task(codex_team_project_root, "task-14")
    assert record.metadata.get("current_claim") is None

    with pytest.raises(TaskOpsError):
        record_task_approval(
            codex_team_project_root,
            task_id="task-14",
            decision="approved",
            worker_id="worker-a",
            claim_token=token,
            expected_version=record.version,
        )
