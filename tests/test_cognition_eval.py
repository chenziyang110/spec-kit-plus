import importlib.util
import json
import uuid
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "tools" / "workflow-quality" / "cognition_eval.py"
    spec = importlib.util.spec_from_file_location("cognition_eval", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def fixture_packet(tmp_path):
    m = module()
    frozen_root = tmp_path / "frozen"
    frozen_root.mkdir()
    original = frozen_root / "source.go"
    original.write_text("package fixture\n// live source basis\n", encoding="utf-8")
    original_negative = frozen_root / "negative.go"
    original_negative.write_text("package fixture\n// unrelated negative owner\n", encoding="utf-8")
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    source = project / "src" / "source.go"
    source.write_text("package fixture\n// live source basis\n", encoding="utf-8")
    negative = project / "src" / "negative.go"
    negative.write_bytes(original_negative.read_bytes())
    evidence = {**m.binding(original), "source_path": "src/source.go"}
    negative_evidence = {**m.binding(original_negative), "source_path": "src/negative.go"}
    tasks = tmp_path / "tasks.json"
    m.write_new(tasks, {"author": "task-author"})
    gold = tmp_path / "gold.json"
    m.write_new(gold, {"schema": "cognition-eval-gold.v1", "status": "accepted", "reviewer": "independent-reviewer", "tasks_sha256": m.digest(tasks), "tasks": [{"family": family, "owners": ["src/source.go"], "consumers": ["src/source.go"], "verification": ["src/source.go"], "negative_paths": ["src/negative.go"], "evidence": [evidence, negative_evidence]} for family in m.FAMILIES]})
    runtime = tmp_path / "runtime.exe"
    runtime.write_bytes(b"bound runtime")
    original_manifest = frozen_root / "manifest.json"
    m.write_new(original_manifest, [evidence, negative_evidence])
    manifest = project / "manifest.json"
    m.write_new(manifest, [{**m.binding(source), "source_path": "src/source.go"}, {**m.binding(negative), "source_path": "src/negative.go"}])
    environment = tmp_path / "environment.json"
    m.write_new(environment, {"platform": "test", "hardware": "test", "model": "inherited", "model_config": "inherited", "permissions": "fixture-only", "cold_warm_policy": "independent rounds, OS cache unchanged"})
    plan = tmp_path / "plan.json"
    m.write_new(plan, m.freeze(tasks, gold, environment, runtime, original_manifest))
    stdout, stderr = tmp_path / "stdout", tmp_path / "stderr"
    stdout.write_bytes(b'{"status":"ok"}')
    stderr.write_bytes(b"")
    record = {"schema": "cognition-eval-observation.v1", "kind": "native_runtime_replay", "phase": "before", "slot": "classic/locate/first/1", "run_id": "one-real-call", "project_root": str(project.resolve()), "plan_sha256": m.digest(plan), "gold_sha256": m.digest(gold), "environment_sha256": m.digest(environment), "runtime": m.binding(runtime), "source_manifest": m.binding(manifest), "semantic_contract": {"query": "locate fixture owner", "intent": "explain", "scope_id": "classic/locate/1", "required_facets": ["locate"], "negative_constraints": ["graph is advisory"]}, "permission_contract": {"allowed": ["read"], "forbidden": ["source mutation"]}, "condition_order": 1, "independent_round": 1, "source_change": None, "tool_calls": [{"argv": [str(runtime), "cognition", "compass"], "cwd": str(project), "exit_code": 0, "elapsed_ms": 1, "stdout": m.binding(stdout), "stderr": m.binding(stderr)}], "source_reads": [{"source_path": p, "mode": "full", "evidence": m.binding(target)} for p, target in (("src/source.go", source), ("src/negative.go", negative))], "decision": {"owners": ["src/source.go"], "consumers": ["src/source.go"], "verification": ["src/source.go"], "rejected_paths": ["src/negative.go"]}, "first_confirmed_owner_ms": 2, "total_ms": 3, "model_tokens": {"status": "unavailable"}}
    record["phase_source_manifest"] = m.binding(original_manifest)
    sync_packet(m, plan, record, tmp_path)
    return m, plan, record, source


def sync_packet(m, plan, record, tmp_path):
    packet_path = tmp_path / f"packet-{uuid.uuid4().hex}.json"
    fields = ("slot", "phase", "project_root", "runtime", "source_manifest", "phase_source_manifest", "source_change", "semantic_contract", "permission_contract", "plan_sha256", "environment_sha256", "gold_sha256")
    m.write_new(packet_path, {"schema": "cognition-eval-task-packet.v2", **{field: record[field] for field in fields}, "query": record["semantic_contract"]["query"], "intent": record["semantic_contract"]["intent"]})
    record["task_packet"] = m.binding(packet_path)


def test_missing_real_observations_remain_in_original_denominator(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    result = m.evaluate(plan, [record])
    native = result["matrices"][0]
    assert native["required"] == 120
    assert native["observed"] == 1
    assert len(native["unexecuted_slots"]) == 119
    assert native["per_profile"]["classic"]["required"] == 60
    assert native["per_profile"]["advanced"]["required"] == 60
    assert result["matrices"][1]["observed"] == 0
    assert result["status"] == "pending_actual_agent_evidence"
    assert result["paired"][0]["median_total_ms_after"] is None


def test_runtime_replay_cannot_claim_agent_or_token_credit(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    record["kind"] = "actual_agent_observation"
    with pytest.raises(ValueError, match="real task/turn/model"):
        m.evaluate(plan, [record])
    record["kind"] = "native_runtime_replay"
    record["model_tokens"] = {"status": "native_telemetry", "input": 10, "output": 20, "evidence": record["tool_calls"][0]["stdout"]}
    with pytest.raises(ValueError, match="replay cannot provide model tokens"):
        m.evaluate(plan, [record])


def test_duplicate_slots_and_run_ids_cannot_inflate_coverage(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    other = {**record, "run_id": "second-id"}
    with pytest.raises(ValueError, match="duplicate observation"):
        m.evaluate(plan, [record, other])
    other = {**record, "slot": "classic/locate/first/2", "independent_round": 2}
    sync_packet(m, plan, other, tmp_path)
    with pytest.raises(ValueError, match="duplicate observation"):
        m.evaluate(plan, [record, other])


def test_changed_source_or_trace_does_not_survive_digest_check(tmp_path):
    m, plan, record, source = fixture_packet(tmp_path)
    source.write_text("different live basis", encoding="utf-8")
    with pytest.raises(ValueError, match="changed evidence"):
        m.evaluate(plan, [record])


def test_aggregate_pass_does_not_replace_required_live_reads(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    record["source_reads"] = []
    record["passing"] = True
    row = m.evaluate(plan, [record])["observations"][0]
    assert row["fact_acceptance"] == "fail"
    assert row["required_live_read_gaps"] == ["src/negative.go", "src/source.go"]


def test_wrong_owner_and_missing_consumer_are_accounted_separately(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    record["decision"]["owners"] = ["src/negative.go"]
    record["decision"]["consumers"] = []
    row = m.evaluate(plan, [record])["observations"][0]
    assert row["wrong_owner_paths"] == ["src/negative.go"]
    assert row["missing"]["owners"] == ["src/source.go"]
    assert row["missing"]["consumers"] == ["src/source.go"]
    assert row["fact_acceptance"] == "fail"


def test_source_change_condition_cannot_be_laundered_as_repeat(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    record["slot"] = "classic/locate/source_changed/1"
    record["condition_order"] = 4
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="exact different content"):
        m.evaluate(plan, [record])
    record["source_change"] = {"before_sha256": "a" * 64, "after_sha256": "b" * 64}
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="source change original basis"):
        m.evaluate(plan, [record])
    record["slot"] = "classic/locate/repeat/1"
    record["condition_order"] = 2
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="silently change source"):
        m.evaluate(plan, [record])


def test_before_runtime_binding_cannot_be_changed(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    target = tmp_path / "other-runtime.exe"
    target.write_bytes(b"new runtime")
    record["runtime"] = m.binding(target)
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="changed baseline runtime"):
        m.evaluate(plan, [record])


def test_gold_requires_independent_source_bound_fact_owner(tmp_path):
    m, plan, _, _ = fixture_packet(tmp_path)
    packet = m.load(plan)
    gold_path = Path(packet["gold"]["path"])
    gold = m.load(gold_path)
    gold["reviewer"] = "task-author"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    with pytest.raises(ValueError, match="separate from task author"):
        m.validate_gold(gold, Path(packet["tasks"]["path"]))


def test_duplicate_json_and_nonfinite_numbers_rejected(tmp_path):
    m = module()
    path = tmp_path / "unsafe.json"
    path.write_text('{"kind":"native_runtime_replay","kind":"actual_agent_observation"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        m.load(path)
    path.write_text('{"time":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        m.load(path)


def test_output_is_exclusively_created(tmp_path):
    m = module()
    path = tmp_path / "existing.json"
    path.write_bytes(b"preserve original evidence")
    with pytest.raises(FileExistsError):
        m.write_new(path, {"passing": True})
    assert path.read_bytes() == b"preserve original evidence"


def test_plan_cannot_reduce_the_required_matrix(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    packet = m.load(plan)
    packet["required_slots"] = packet["required_slots"][:1]
    plan.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="original 120-row denominator"):
        m.evaluate(plan, [record])


def test_foreign_target_cannot_reuse_valid_source_manifest(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    foreign = tmp_path / "foreign-target"
    foreign.mkdir()
    record["project_root"] = str(foreign.resolve())
    with pytest.raises(ValueError, match="changed task packet project_root"):
        m.evaluate(plan, [record])
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="another target"):
        m.evaluate(plan, [record])


def test_invented_source_change_digests_do_not_match_unchanged_files(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    original = m.load(Path(record["phase_source_manifest"]["path"]))[0]
    current = m.load(Path(record["source_manifest"]["path"]))[0]
    record.update(slot="classic/locate/source_changed/1", condition_order=4, source_change={"path": "src/source.go", "before_sha256": "a" * 64, "after_sha256": "b" * 64, "before": {k: original[k] for k in ("path", "sha256", "bytes")}, "after": {k: current[k] for k in ("path", "sha256", "bytes")}})
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="does not match exact original/current"):
        m.evaluate(plan, [record])


def test_real_source_change_has_exact_original_and_current_content_bindings(tmp_path):
    m, plan, record, source = fixture_packet(tmp_path)
    original = m.load(Path(record["phase_source_manifest"]["path"]))[0]
    sources = m.load(Path(record["source_manifest"]["path"]))
    source.write_bytes(source.read_bytes() + b"// exact changed source\n")
    sources[0] = {**m.binding(source), "source_path": "src/source.go"}
    new_manifest = Path(record["project_root"]) / "changed-manifest.json"
    m.write_new(new_manifest, sources)
    record["source_manifest"] = m.binding(new_manifest)
    record["source_reads"][0]["evidence"] = m.binding(source)
    record.update(slot="classic/locate/source_changed/1", condition_order=4, source_change={"path": "src/source.go", "before_sha256": original["sha256"], "after_sha256": sources[0]["sha256"], "before": {k: original[k] for k in ("path", "sha256", "bytes")}, "after": m.binding(source)})
    sync_packet(m, plan, record, tmp_path)
    assert m.evaluate(plan, [record])["observations"][0]["fact_acceptance"] == "pass"
    record.update(slot="classic/locate/repeat/1", condition_order=2, source_change=None)
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="condition source changes differ"):
        m.evaluate(plan, [record])


@pytest.mark.parametrize("kind", ["actual_agent_observation", "native_runtime_replay"])
def test_original_decision_artifact_cannot_be_replaced_by_record_claim(tmp_path, kind):
    m, plan, record, _ = fixture_packet(tmp_path)
    decision = tmp_path / "original-decision.json"
    m.write_new(decision, {"owners": ["src/negative.go"], "consumers": [], "verification": [], "rejected_paths": []})
    record["kind"] = kind
    if kind == "actual_agent_observation":
        record["agent"] = {"task_id": "test-stub-not-actual-agent", "turn_id": "stub", "model_config": "test-only"}
        record["agent_decision_evidence"] = m.binding(decision)
    else:
        record["replay_decision_evidence"] = m.binding(decision)
    with pytest.raises(ValueError, match="decision differs"):
        m.evaluate(plan, [record])


def test_zero_call_reuse_cannot_prove_live_runtime_snapshot(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    previous = tmp_path / "previous.json"
    m.write_new(previous, record)
    record.update(slot="classic/locate/repeat/1", condition_order=2, tool_calls=[], reuse_intake=m.binding(previous))
    sync_packet(m, plan, record, tmp_path)
    with pytest.raises(ValueError, match="zero-call"):
        m.evaluate(plan, [record])


@pytest.mark.parametrize("field", ["project_root", "runtime", "environment_sha256", "gold_sha256", "phase", "semantic_contract", "permission_contract"])
def test_reuse_context_binds_target_runtime_scope_constraints_and_permissions(tmp_path, field):
    m, _, record, _ = fixture_packet(tmp_path)
    current = {**record, "slot": "classic/locate/repeat/1"}
    current[field] = "changed"
    with pytest.raises(ValueError, match=f"changed {field}"):
        m.validate_reuse_context(record, current)


def test_original_intake_requires_supported_snapshot_and_native_basis(tmp_path):
    m, _, record, _ = fixture_packet(tmp_path)
    current = {**record, "slot": "classic/locate/repeat/1"}
    with pytest.raises(ValueError, match="lacks same-generation snapshot"):
        m.validate_runtime_reuse(current, record)
    arbitrary = tmp_path / "empty-prior.json"
    m.write_new(arbitrary, {**current, "tool_calls": [], "reuse_intake": {"path": str(tmp_path / "missing.json"), "sha256": "a" * 64, "bytes": 1}})
    current["tool_calls"] = []
    current["reuse_intake"] = m.binding(arbitrary)
    with pytest.raises(ValueError, match="changed evidence"):
        m.original_compass(current)
    record["tool_calls"][0]["cwd"] = "foreign-native-target"
    with pytest.raises(ValueError, match="different runtime or target"):
        m.original_compass(record)


def test_owner_confirmation_cannot_move_between_episode_records(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    record["started_at_ns"] = 10
    event = {"run_id": record["run_id"], "slot": record["slot"], "task_packet": record["task_packet"], "started_at_ns": 10, "chosen_owner": "src/source.go", "elapsed_ms": 2, "source_read_evidence": record["source_reads"][0]["evidence"]}
    evidence = tmp_path / "confirmed-event.json"
    m.write_new(evidence, event)
    record["owner_confirmations"] = [{**event, "event_evidence": m.binding(evidence)}]
    assert m.evaluate(plan, [record])["observations"][0]["metrics"]["first_confirmed_owner_ms"] == 2
    record["run_id"] = "another-episode"
    with pytest.raises(ValueError, match="belongs to another episode"):
        m.evaluate(plan, [record])


@pytest.mark.parametrize("value", [None, "a" * 64, "SHA256:" + "a" * 64, "sha256:" + "A" * 64, "sha256:" + "a" * 63, "sha256:" + "a" * 65])
def test_navigation_digest_prefix_does_not_weaken_raw_artifact_hashes(value):
    m = module()
    with pytest.raises(ValueError):
        m.require_navigation_digest(value)
    assert m.require_navigation_digest("sha256:" + "a" * 64) == "sha256:" + "a" * 64
    with pytest.raises(ValueError):
        m.require_hash("sha256:" + "a" * 64, "artifact")


def guarded_record(m, record, tmp_path, *, readiness="query_ready", status="ok"):
    ref = {"id": "exp-unit-only", "active_generation_id": "GEN-unit-only", "query_fingerprint": "q-unit-only", "expansion_contract_version": 2, "navigation_digest": "sha256:" + "a" * 64}
    payload = {"expansion_ref": ref}
    stdout, stderr = tmp_path / f"guard-{uuid.uuid4().hex}.stdout", tmp_path / f"guard-{uuid.uuid4().hex}.stderr"
    m.write_new(stdout, {"status": "ok", "data": {k: v for k, v in ref.items() if k != "navigation_digest"} | {"status": status, "readiness": readiness, "epistemic_contract": {"contract_version": 1, "graph_role": "route_candidate_only", "fact_source_of_truth": "live_repository", "live_verification_required": True, "graph_only_claims_allowed": False, "unverified_claim_action": "withhold"}}})
    stderr.write_bytes(b"")
    guard = {"argv": [record["runtime"]["path"], "cognition", "expand", "--id", ref["id"], "--section", "related_paths", "--format", "json"], "cwd": record["project_root"], "exit_code": 0, "elapsed_ms": 1, "stdout": m.binding(stdout), "stderr": m.binding(stderr)}
    current = {**record, "slot": "classic/locate/repeat/1", "tool_calls": [guard], "reuse_runtime_guard": guard}
    return payload, current


@pytest.mark.parametrize("readiness", ["query_ready", "review"])
def test_snapshot_guard_accepts_actual_prefix_without_invented_echo(tmp_path, readiness):
    m, _, record, _ = fixture_packet(tmp_path)
    payload, current = guarded_record(m, record, tmp_path, readiness=readiness)
    assert "navigation_digest" not in m.runtime_payload(current["reuse_runtime_guard"])
    m.validate_runtime_guard(current, payload)


@pytest.mark.parametrize("field,value", [("status", "stale_expansion"), ("readiness", "blocked"), ("id", "foreign-expansion"), ("active_generation_id", "foreign-generation"), ("epistemic_contract", {"graph_only_claims_allowed": True})])
def test_outer_native_zero_does_not_prove_inner_snapshot_or_advisory_boundary(tmp_path, field, value):
    m, _, record, _ = fixture_packet(tmp_path)
    payload, current = guarded_record(m, record, tmp_path)
    guard = current["reuse_runtime_guard"]
    path = Path(guard["stdout"]["path"])
    actual = m.load(path)
    actual["data"][field] = value
    path.write_text(json.dumps(actual), encoding="utf-8")
    guard["stdout"] = m.binding(path)
    with pytest.raises(ValueError, match="runtime"):
        m.validate_runtime_guard(current, payload)


def after_plan_fixture(m, plan, record, tmp_path):
    original = m.load(plan)
    gold = m.load(Path(original["gold"]["path"]))
    gold.update(phase="after", before_gold=original["gold"], logical_role_mapping=[{"family": task["family"], "role": role, "before_paths": task[role], "after_paths": task[role], "criterion": "same logical task role, current physical evidence"} for task in gold["tasks"] for role in ("owners", "consumers", "verification", "negative_paths")])
    path = tmp_path / "after-gold.json"
    m.write_new(path, gold)
    after = tmp_path / "after-plan.json"
    m.write_new(after, m.freeze_after(plan, path, Path(record["runtime"]["path"]), Path(original["baseline_source_manifest"]["path"])))
    return after, gold


def test_after_phase_contract_cannot_rewrite_before_facts_or_reduce_role_denominator(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    frozen_bytes = plan.read_bytes()
    after, gold = after_plan_fixture(m, plan, record, tmp_path)
    assert plan.read_bytes() == frozen_bytes
    report = m.compare(plan, after, [record], [])
    assert report["required_actual_pairs"] == 120
    assert report["observed_actual_pairs"] == 0
    assert len(report["missing_after"]) == 120
    gold["logical_role_mapping"].pop()
    with pytest.raises(ValueError, match="twenty logical role"):
        m.validate_phase_mapping(m.load(Path(m.load(plan)["gold"]["path"])), gold)


def test_after_observation_cannot_use_before_plan_or_foreign_phase_runtime(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    after, _ = after_plan_fixture(m, plan, record, tmp_path)
    record.update(phase="after", plan_sha256=m.digest(after), gold_sha256=m.load(after)["gold"]["sha256"])
    sync_packet(m, after, record, tmp_path)
    assert m.evaluate(after, [record])["observations"][0]["phase"] == "after"
    record["phase"] = "before"
    with pytest.raises(ValueError, match="different phase plan"):
        m.evaluate(after, [record])


def test_comparison_refuses_forged_negative_acceptance_and_changed_model_environment(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    after, _ = after_plan_fixture(m, plan, record, tmp_path)
    sidecar = tmp_path / "negative.json"
    m.write_new(sidecar, {"schema": "cognition-eval-negative-acceptance.v1", "status": "accepted", "validator": "same-author", "author": "same-author", "after_plan_sha256": m.digest(after), "rows": []})
    with pytest.raises(ValueError, match="independent"):
        m.compare(plan, after, [], [], sidecar)
    changed = m.load(after)
    changed["environment"] = changed["gold"]
    after.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="paired environment"):
        m.compare(plan, after, [], [])


def test_graph_snapshot_reuse_does_not_prove_unchanged_learning(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    after, _ = after_plan_fixture(m, plan, record, tmp_path)
    record.update(phase="after", plan_sha256=m.digest(after), gold_sha256=m.load(after)["gold"]["sha256"])
    sync_packet(m, after, record, tmp_path)
    payload, current = guarded_record(m, record, tmp_path)
    compass_path = Path(record["tool_calls"][0]["stdout"]["path"])
    compass_path.write_text(json.dumps({"data": payload}), encoding="utf-8")
    record["tool_calls"][0]["stdout"] = m.binding(compass_path)
    prior_path = tmp_path / "prior-after.json"
    m.write_new(prior_path, record)
    current.update(condition_order=2, reuse_intake=m.binding(prior_path))
    sync_packet(m, after, current, tmp_path)
    with pytest.raises(ValueError, match="Learning applicability"):
        m.evaluate(after, [current])
    current["learning_reuse"] = {"outcome": "not_granted_refreshed"}
    learning = {**current["tool_calls"][0], "argv": [record["runtime"]["path"], "learning", "start", "--command", "sp-ask", "--context", "component=locate", "--format", "json"]}
    current["tool_calls"].append(learning)
    with pytest.raises(ValueError, match="Learning owner did not return"):
        m.evaluate(after, [current])
    learning_stdout = tmp_path / "learning-owner.stdout"
    m.write_new(learning_stdout, {"data": {"read_only": True, "schema_version": 1, "command": "sp-ask", "task_context": {"components": ["locate"]}}})
    learning["stdout"] = m.binding(learning_stdout)
    assert m.evaluate(after, [current])["observations"][0]["fact_acceptance"] == "pass"


def test_negative_receipt_keeps_all_five_independent_rows_explicit(tmp_path):
    m, plan, record, _ = fixture_packet(tmp_path)
    after, _ = after_plan_fixture(m, plan, record, tmp_path)
    receipt = {"schema": "cognition-eval-negative-acceptance.v1", "status": "accepted", "validator": "independent-unit-stub", "author": "unit-fixture-author", "after_plan_sha256": m.digest(after), "rows": [{"condition": condition, "status": "accepted", "evidence": [record["tool_calls"][0]["stdout"]]} for condition in m.NEGATIVES]}
    path = tmp_path / "negative-full.json"
    m.write_new(path, receipt)
    report = m.compare(plan, after, [], [], path)
    assert set(report["negative_conditions"]) == set(m.NEGATIVES)
    assert all(row["status"] == "accepted" for row in report["negative_conditions"].values())
    receipt["rows"].pop()
    bad = tmp_path / "negative-reduced.json"
    m.write_new(bad, receipt)
    with pytest.raises(ValueError, match="dropped an original"):
        m.compare(plan, after, [], [], bad)
