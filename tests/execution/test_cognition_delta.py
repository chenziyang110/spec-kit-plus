"""Exercise retained observations across normalization and native Python owners."""

import hashlib
import json
from pathlib import Path

import pytest

from specify_cli.execution.cognition_delta import DELTA_SCHEMA, decode_result_json
from specify_cli.execution.result_normalizer import normalize_worker_task_result_payload
from specify_cli.execution.result_schema import worker_task_result_from_json, worker_task_result_payload
from specify_cli.execution.submission_history import bind_result_acceptance, read_result_owner, retained_submission_paths
from specify_cli.execution.result_handoff import write_normalized_result_handoff
from specify_cli.execution.task_runtime import TaskRuntimeError, accept_task, record_task_result, start_task
from tests.execution.test_task_runtime import _write_feature


def _delta(paths=None):
    return {
        "schema": DELTA_SCHEMA, "version": 1,
        "identity": {"task_id": "T001", "attempt_id": "worker-observation"},
        "changed_paths": paths or ["src/task_1.py"],
        "behavior_surfaces": [{"claim_ref": "charge", "before": {"value": 0}, "after": {"value": 1}}],
        "owner_surfaces": [{"owner": "src/task_1.py"}],
        "consumer_surfaces": ["src/consumer.py"], "interfaces": [{"name": "charge", "arity": 1}],
        "generated_surfaces": [{"source": "templates/input.md", "target": "docs/output.md"}],
        "generated_surface_notes": ["Generated through the existing renderer"],
        "state_contracts": [{"owner": "charge", "states": ["ready", "blocked"]}],
        "verification_evidence": [{"ref": "tests/test_charge.py", "observed": {"passed": True, "count": 2}}],
        "evidence_refs": ["tests/test_charge.py"], "invalidated_claim_refs": ["old-charge"],
        "known_unknowns": [{"owner": "consumer", "reason": "awaiting integrated check"}],
        "confidence_notes": [{"scope": "local", "score": 0.8}],
        "recovery": {"state": "candidate", "actions": [{"kind": "recheck", "refs": ["charge"]}]},
    }


def test_lossless_typed_delta_survives_candidate_and_canonical_read():
    delta = _delta(["src/old.py", "src/new.py"])
    delta["path_changes"] = [{"kind": "renamed", "old_path": "src/old.py", "new_path": "src/new.py"}]
    result = normalize_worker_task_result_payload({"task_id": "T001", "status": "failed", "cognition_delta": delta})
    payload = worker_task_result_payload(result)
    restored = worker_task_result_from_json(json.dumps(payload))
    assert restored.cognition_delta == delta
    assert restored.changed_files == ["src/old.py", "src/new.py"]
    assert isinstance(restored.cognition_delta["verification_evidence"][0]["observed"], dict)


@pytest.mark.parametrize("alias", ["changed_files", "changedFiles", "files_changed", "changed_paths", "changedPaths"])
def test_legacy_semantics_migrate_without_stringifying(alias):
    evidence = [{"ref": "tests/a.py", "observed": {"count": 3, "passed": True}}]
    result = normalize_worker_task_result_payload({
        "task_id": "T001", "status": "blocked", alias: ["src/a.py"],
        "behavior_surfaces": [{"owner": "a", "effect": {"mode": "changed"}}],
        "verification": evidence, "known_unknowns": ["missing consumer proof"],
    })
    assert result.changed_files == ["src/a.py"]
    assert result.cognition_delta["verification_evidence"] == evidence
    assert result.cognition_delta["path_changes"] == [{"kind": "unknown", "path": "src/a.py"}]


@pytest.mark.parametrize("extra", [
    {"changed_files": ["src/other.py"]},
    {"behavior_surfaces": ["contradicts typed value"]},
    {"verification": ["contradicts nested evidence"]},
    {"submission_history": []}, {"cognition_result_binding": {}},
    {"taskId": "T002"}, {"packet_id": "packet-a", "packetId": "packet-b"},
])
def test_conflicting_or_runtime_owned_candidate_fields_refuse(extra):
    with pytest.raises(ValueError):
        normalize_worker_task_result_payload({"task_id": "T001", "status": "success", "cognition_delta": _delta(), **extra})


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"schema": "different"},
    {"identity": {"task_id": "T002"}}, {"accepted": True},
    {"confidence_notes": [float("nan")]}, {"known_unknowns": {"reason": "not array"}},
    {"path_changes": [{"kind": "renamed", "old_path": "src/task_1.py", "new_path": "src/missing.py"}]},
    {"path_changes": [{"kind": "renamed", "old_path": "src/task_1.py", "new_path": "src/task_1.py"}]},
])
def test_unsupported_delta_shapes_refuse(change):
    with pytest.raises(ValueError):
        normalize_worker_task_result_payload({"task_id": "T001", "status": "success", "cognition_delta": {**_delta(), **change}})


def test_alias_equivalence_does_not_discard_ordered_semantic_values():
    result = normalize_worker_task_result_payload({"task_id": "T001", "status": "success", "changedFiles": ["./src/a.py", "src/b.py"], "changed_paths": ["src/b.py", "src/a.py"]})
    assert result.changed_files == ["src/a.py", "src/b.py"]
    with pytest.raises(ValueError, match="duplicate"):
        decode_result_json('{"changed_paths": [], "changed_paths": ["src/a.py"]}')
    with pytest.raises(ValueError, match="finite"):
        decode_result_json('{"confidence_notes": [NaN]}')
    with pytest.raises(ValueError, match="finite"):
        decode_result_json('{"evidence": {"observed": 1e400}}')
    assert decode_result_json('{"observed": 9007199254740993123456789}')["observed"] == 9007199254740993123456789


@pytest.mark.parametrize("path", [".", "./.", "src/a\nb.py", "src/a\rb.py"])
def test_delta_paths_reject_project_root_and_embedded_newlines(path):
    with pytest.raises(ValueError, match="project-relative"):
        normalize_worker_task_result_payload({
            "task_id": "T001", "status": "success", "changed_paths": [path],
        })


def _success(delta):
    return {"task_id": "T001", "status": "success", "cognition_delta": delta,
            "validation_results": [{"command": "pytest tests/test_task_1.py -q", "status": "passed"}]}


def test_native_task_retry_rejection_acceptance_retains_exact_all_events(tmp_path):
    project, feature = _write_feature(tmp_path, task_count=1)
    start_task(project, feature, "T001", execution_mode="leader-direct")
    record_task_result(project, feature, "T001", {"task_id": "T001", "status": "failed", "changed_paths": ["src/retained.py"], "behavior_surfaces": ["retained partial effect"]})
    lifecycle_path = feature / "implementation-review/tasks/T001.json"
    blocked_before = lifecycle_path.read_bytes()
    rejected = _success(_delta())
    rejected["changed_paths"] = ["src/rejected.py"]
    with pytest.raises(TaskRuntimeError, match="conflicts"):
        record_task_result(project, feature, "T001", rejected)
    assert lifecycle_path.read_bytes() == blocked_before
    stored_path = feature / "worker-results/T001.json"
    mid = json.loads(stored_path.read_text())
    assert mid["status"] == "failed"
    assert json.loads(mid["submission_history"][1]["result_json"])["changed_paths"] == ["src/rejected.py"]
    record_task_result(project, feature, "T001", _success(_delta()))
    accept_task(project, feature, "T001")
    final = read_result_owner(stored_path.read_bytes())
    assert [row["status"] for row in final["submission_history"]] == ["failed", "rejected", "success"]
    assert final["cognition_result_binding"]["acceptance_state"] == "accepted"
    assert final["cognition_result_binding"]["sequence"] == 3
    assert final["cognition_result_binding"]["result_ref"] == stored_path.relative_to(project).as_posix()
    assert final["cognition_result_binding"]["acceptance_ref"] == lifecycle_path.relative_to(project).as_posix()
    assert json.loads(lifecycle_path.read_text())["result_ref"] == stored_path.relative_to(feature).as_posix()
    assert set(json.loads(lifecycle_path.read_text())["changed_paths"]) == {
        "src/retained.py", "src/rejected.py", "src/task_1.py",
    }
    assert final["cognition_delta"] == {**_delta(), "path_changes": [{"kind": "unknown", "path": "src/task_1.py"}]}
    for row in final["submission_history"]:
        assert hashlib.sha256(row["result_json"].encode()).hexdigest() == row["result_sha256"]
        assert "submission_history" not in json.loads(row["result_json"])
    tampered = dict(final, summary="different actual result")
    with pytest.raises(ValueError, match="exact current"):
        bind_result_acceptance(tampered, acceptance_ref="tasks/T001.json", acceptance_revision=999)


def test_native_result_channel_retains_prior_legacy_and_rejected_input(tmp_path):
    workspace = tmp_path / ".planning/quick/001-fix"
    target = workspace / "worker-results/lane-a.json"
    target.parent.mkdir(parents=True)
    legacy = {"task_id": "lane-a", "status": "failed", "changed_files": ["src/old.py"], "behavior_surfaces": [{"partial": True}]}
    target.write_text(json.dumps(legacy))
    kwargs = dict(command_name="quick", integration_key="cursor-agent", quick_workspace=workspace, lane_id="lane-a")
    raw = '{"task_id":"lane-a","status":"success","changed_paths":["src/rejected.py"],"changed_files":["src/other.py"]}'
    with pytest.raises(ValueError, match="conflicting"):
        write_normalized_result_handoff(tmp_path, raw_result=raw, **kwargs)
    assert json.loads(target.read_text())["status"] == "failed"
    write_normalized_result_handoff(tmp_path, raw_result={"task_id": "lane-a", "status": "success", "changed_paths": ["src/new.py"], "owner_surfaces": [{"owner": "new"}]}, **kwargs)
    stored = read_result_owner(target.read_bytes())
    assert [row["status"] for row in stored["submission_history"]] == ["failed", "rejected", "success"]
    assert stored["submission_history"][1]["result_json"] == raw
    assert stored["cognition_result_binding"]["acceptance_state"] == "submitted"
    assert json.loads(stored["submission_history"][0]["result_json"]) == legacy
    paths, unknown = retained_submission_paths(stored)
    assert set(paths) == {"src/old.py", "src/rejected.py", "src/other.py", "src/new.py"}
    assert unknown == []


def test_malformed_rejected_input_remains_explicit_source_accounting_obligation(tmp_path):
    workspace = tmp_path / ".planning/quick/001-fix"
    with pytest.raises(ValueError):
        write_normalized_result_handoff(
            tmp_path, command_name="quick", integration_key="cursor-agent",
            quick_workspace=workspace, lane_id="lane-a", raw_result='{"changed_paths":',
        )
    stored = read_result_owner((workspace / "worker-results/lane-a.json").read_bytes())
    paths, unknown = retained_submission_paths(stored)
    assert paths == [] and unknown == [1]
    assert stored["submission_history"][0]["result_json"] == '{"changed_paths":'


@pytest.mark.parametrize("has_previous", [False, True])
def test_obsolete_ui_with_retained_edits_stays_rejected_and_accounted(tmp_path, has_previous):
    workspace = tmp_path / ".planning/quick/001-fix"
    target = workspace / "worker-results/lane-a.json"
    previous = {"task_id": "lane-a", "status": "blocked", "changed_files": ["src/old.py"]}
    if has_previous:
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(previous))
    raw = {"task_id": "lane-a", "status": "success", "uiEvidence": [], "changed_paths": ["src/retained.py"]}
    with pytest.raises(ValueError, match="obsolete UI"):
        write_normalized_result_handoff(tmp_path, command_name="quick", integration_key="cursor-agent", quick_workspace=workspace, lane_id="lane-a", raw_result=raw)
    stored = read_result_owner(target.read_bytes())
    assert stored["status"] == ("blocked" if has_previous else "pending")
    assert stored["submission_history"][-1]["status"] == "rejected"
    assert "src/retained.py" in retained_submission_paths(stored)[0]
    assert "cognition_result_binding" not in stored


def test_native_submission_compare_and_swap_preserves_concurrent_writer(tmp_path, monkeypatch):
    from specify_cli.execution import task_runtime

    project, feature = _write_feature(tmp_path, task_count=1)
    start_task(project, feature, "T001", execution_mode="leader-direct")
    path = feature / "worker-results/T001.json"
    original = task_runtime.apply_workflow_transaction
    concurrent = b'{"task_id":"T001","status":"failed","summary":"another writer"}'

    def race(*args, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(concurrent)
        return original(*args, **kwargs)

    monkeypatch.setattr(task_runtime, "apply_workflow_transaction", race)
    with pytest.raises(TaskRuntimeError, match="changed|precondition|conflict"):
        record_task_result(project, feature, "T001", _success(_delta()))
    assert path.read_bytes() == concurrent
    assert json.loads((feature / "implementation-review/tasks/T001.json").read_text())["status"] == "in_progress"


def test_generic_handoff_cannot_replace_implemented_submission_at_acceptance(tmp_path):
    project, feature = _write_feature(tmp_path, task_count=1)
    start_task(project, feature, "T001", execution_mode="leader-direct")
    record_task_result(project, feature, "T001", _success(_delta()))
    lifecycle_path = feature / "implementation-review/tasks/T001.json"
    lifecycle_before = lifecycle_path.read_bytes()
    replacement = _success(_delta())
    replacement["summary"] = "another submission outside the task lifecycle"
    write_normalized_result_handoff(
        project, command_name="implement", integration_key="cursor-agent",
        feature_dir=feature, task_id="T001", raw_result=replacement,
    )
    result_path = feature / "worker-results/T001.json"
    result_before = result_path.read_bytes()
    with pytest.raises(TaskRuntimeError, match="lifecycle submission"):
        accept_task(project, feature, "T001")
    assert lifecycle_path.read_bytes() == lifecycle_before
    assert result_path.read_bytes() == result_before
    assert json.loads(result_before)["cognition_result_binding"]["acceptance_state"] == "submitted"
