"""Adversarial consistency tests; these are not actual Agent work observations."""
import copy
import importlib.util
import sys
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def fresh_dependency_check(project, case_id):
    script = "import importlib.util,json; from pathlib import Path; " + (
        f"s=importlib.util.spec_from_file_location('probe', {str(ROOT / 'tests/e2e_samples/cognition_loop_probe.py')!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        f"print(json.dumps(m.business_dependency_check(Path({str(project)!r}), {case_id!r})))")
    return subprocess.run([sys.executable, "-c", script], cwd=project, capture_output=True, timeout=30)


@pytest.mark.parametrize("helper,service,passes", [
    ("def fee(value):\n    return round(value, 2)\n", "from src.rounding import fee\ndef charge(amount, rate=0.1):\n    return fee(amount * rate)\n", True),
    ("def keep_precision(value, digits):\n    return round(value, digits)\n", "import src.rounding as r\ndef charge(amount, rate=0.1):\n    return r.keep_precision(amount * rate, 2)\n", True),
    ("raise RuntimeError('unused helper')\n", "# src.rounding\ndef charge(amount, rate=0.1):\n    return round(amount * rate, 2)\n", False),
    ("def fee(value):\n    return round(value, 2)\n", "from src.rounding import fee\ndef charge(amount, rate=0.1):\n    return round(amount * rate, 2)\n", False),
    ("def fee(value):\n    raise RuntimeError('crashing helper')\n", "from src.rounding import fee\ndef charge(amount, rate=0.1):\n    return fee(amount * rate)\n", False),
    ("def fee(value):\n    return 10\n", "from src.rounding import fee\ndef charge(amount, rate=0.1):\n    return fee(amount * rate)\n", False),
])
def test_rounding_dependency_requires_actual_calls_and_equivalent_behavior(tmp_path, helper, service, passes):
    _, probe = modules()
    project = tmp_path / "loop-fixture-rounding"
    probe.create_fixture(project)
    (project / "src/rounding.py").write_text(helper, encoding="utf-8")
    (project / "src/service.py").write_text(service, encoding="utf-8")
    result = fresh_dependency_check(project, "L10")
    assert (result.returncode == 0) is passes, result.stderr.decode(errors="replace")
    if passes:
        assert json.loads(result.stdout)["actual_dependency_calls"]


@pytest.mark.parametrize("guard,consumer_call,passes", [
    ("percent < 0 or percent > 100", "discount(amount, percent)", True),
    ("not 0 <= percent <= 100", "discount(amount, percent)", True),
    ("percent > 100", "discount(amount, percent)", False),
    ("percent < 0 or percent > 100", "75", False),
    ("percent <= 0 or percent >= 100", "discount(amount, percent)", False),
])
def test_discount_both_bounds_and_consumer_execute_component(tmp_path, guard, consumer_call, passes):
    _, probe = modules()
    project = tmp_path / "loop-fixture-discount"
    probe.create_fixture(project)
    (project / "src/discount.py").write_text(f"def discount(amount, percent):\n    if {guard}:\n        raise ValueError('range')\n    return amount * (1 - percent / 100)\n", encoding="utf-8")
    with (project / "src/consumer.py").open("a", encoding="utf-8") as stream:
        stream.write(f"\nfrom src.discount import discount\ndef discounted_invoice(amount, percent):\n    return {{'amount': {consumer_call}}}\n")
    result = fresh_dependency_check(project, "L04")
    assert (result.returncode == 0) is passes, result.stderr.decode(errors="replace")


@pytest.mark.parametrize("regression,expected", [
    ("with self.assertRaises(ValueError):\n            charge(-20)", True),
    ("self.assertRaises(ValueError, charge, -20)", True),
    ("raise RuntimeError('always fails')", False),
    ("charge(-20)\n        self.fail('ValueError not raised')", False),
    ("self.assertEqual(charge(-20), -2)", False),
    ("with self.assertRaises(ValueError):\n            charge(20)", False),
    ("with self.assertRaises(ValueError):\n            charge(-20)\n        self.fail('always fails after a correct rejection')", False),
])
def test_negative_regression_exact_actual_failure_cause(tmp_path, regression, expected):
    _, probe = modules()
    project = tmp_path / "loop-fixture-regression"
    probe.create_fixture(project)
    probe.write_new(project / "tests/e2e-harness.json", {"pattern": "test_negative_e2e.py", "test_id": "test_negative_e2e.NegativeE2E.test_negative_charge"})
    (project / "tests/test_negative_e2e.py").write_text("import unittest\nfrom src.service import charge\nclass NegativeE2E(unittest.TestCase):\n    def test_negative_charge(self):\n        " + regression + "\n", encoding="utf-8")
    result = probe.negative_regression_check(project)
    assert (result["status"] == "passed") is expected
    assert result["native_call"]["stdout"]
    assert result["native_call"]["stderr"]
    if expected:
        assert result["native_call"]["exit_code"] == 1
        assert result["regression"]["execution_prerequisite"] == "failed"
        assert result["regression"]["tests_run"] == 1
        assert "ValueError not raised" in result["native_call"]["stderr"]
        assert result["regression"]["test_events"][0]["traceback"]
        assert result["counterfactual_control_call"]["exit_code"] == 0
        assert result["counterfactual_control"]["test_events"][0]["status"] == "passed"


@pytest.mark.parametrize("source", [
    "raise RuntimeError('import failed')\n",
    "import unittest\nclass NegativeE2E(unittest.TestCase):\n    def setUp(self):\n        raise RuntimeError('setup failed')\n    def test_negative_charge(self):\n        pass\n",
    "# no tests\n",
    "syntax !!!\n",
    "import unittest\nfrom src.service import charge\nclass NegativeE2E(unittest.TestCase):\n    def setUp(self):\n        with self.assertRaises(ValueError):\n            charge(-20)\n    def test_negative_charge(self):\n        pass\n",
])
def test_negative_regression_rejects_import_setup_zero_tests_and_syntax(tmp_path, source):
    _, probe = modules()
    project = tmp_path / "loop-fixture-invalid-regression"
    probe.create_fixture(project)
    probe.write_new(project / "tests/e2e-harness.json", {"pattern": "test_negative_e2e.py", "test_id": "test_negative_e2e.NegativeE2E.test_negative_charge"})
    (project / "tests/test_negative_e2e.py").write_text(source, encoding="utf-8")
    result = probe.negative_regression_check(project)
    assert result["status"] == "failed"
    assert result["native_call"]["stdout"]
    assert result["native_call"]["stderr"]


def test_fixture_generator_and_git_blobs_preserve_all_ten_original_byte_facts(tmp_path):
    _, probe = modules()
    project = tmp_path / "loop-fixture-source-binding"
    probe.create_fixture(project)
    marker = probe.load(project / ".cognition-loop-fixture.json")
    before = {name: (project / name).read_bytes() for name in probe.FIXTURE_FILES}
    result = subprocess.run([sys.executable, "tools/generate.py"], cwd=project, capture_output=True, timeout=30)
    assert result.returncode == 0
    assert len(before) == len(marker["original_sources"]) == 10
    for name, original in before.items():
        assert (project / name).read_bytes() == original
        blob = subprocess.run(["git", "cat-file", "blob", f"HEAD:{name}"], cwd=project, capture_output=True, timeout=30)
        assert blob.returncode == 0 and blob.stdout == original
        assert marker["original_sources"][name] == {"sha256": probe.digest(project / name), "bytes": len(original)}
    assert (project / "src/generated.txt").read_bytes() == (project / "templates/service.txt").read_bytes()


def modules():
    directory = ROOT / "tools" / "workflow-quality"
    sys.path.insert(0, str(directory))
    import cognition_loop_eval as evaluation
    spec = importlib.util.spec_from_file_location("cognition_loop_probe_test", ROOT / "tests" / "e2e_samples" / "cognition_loop_probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return evaluation, probe


def create_json(module, path, value):
    module.write_new(path, value)
    return module.binding(path)


@pytest.fixture
def contract(tmp_path):
    m, probe = modules()
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    source = frozen / "service.py"
    source.write_text("def charge(value):\n    return value\n", encoding="utf-8")
    sources = tmp_path / "source-manifest.json"
    create_json(m, sources, [{"source_path": "src/service.py", **m.binding(source)}])
    tasks = tmp_path / "tasks.json"
    def fact_contract(case_id):
        return [{"id": f"{case_id}-{kind}", "kind": kind, "expected_state": "retired" if kind == "old_fact" else "accepted",
                 "criterion": f"Unit fixture source supports {kind}; independently inspect the fixture"} for kind in m.FACT_KINDS]
    create_json(m, tasks, {"schema": "cognition-loop-tasks.v1", "author": "test-task-author", "cases": [
        {**row, "request": "Verify fixture behavior and correctly update cognition", "business_acceptance": ["actual final behavior corresponds to task"], "owned_paths": ["src/service.py"], "fact_contract": fact_contract(row["id"])}
        for row in m.case_rows()]})
    gold = tmp_path / "gold.json"
    create_json(m, gold, {"schema": "cognition-loop-gold.v1", "status": "accepted", "reviewer": "test-independent-reviewer", "tasks_sha256": m.digest(tasks), "cases": [
        {"id": row["id"], "source_before": m.binding(sources), "source_expected": m.binding(sources), "facts": [
            {**fact, "evidence": [m.binding(source)]} for fact in fact_contract(row["id"])]}
        for row in m.case_rows()]})
    environment = tmp_path / "environment.json"
    create_json(m, environment, {key: "unit-test only; no real model telemetry" for key in ("platform", "python", "model", "permissions", "cold_warm_policy", "clock")})
    entry = tmp_path / "installed-entry.md"
    entry.write_text("Fixture-only installed entry\n", encoding="utf-8")
    surfaces = tmp_path / "surfaces.json"
    entries = [{"profile": profile, "command": command, "invocation": f"{profile}/{command}", "classification": "consume_only", "installed_entry": m.binding(entry), "triggered_contracts": [m.binding(entry)]}
               for profile in m.PROFILES for command in m.CLASSIC]
    entries.append({**entries[-1], "command": "map-rebuild"})
    create_json(m, surfaces, {"schema": "cognition-loop-surfaces.v1", "entries": entries, "classic_map_companions": [
        {"command": name, "classic": m.binding(entry), "advanced": m.binding(entry)} for name in ("map-scan", "map-build", "map-update")]})
    baseline = tmp_path / "baseline.json"
    create_json(m, baseline, {"schema": "cognition-loop-source-baseline.v1", "frozen_root": str(frozen), "files": [{"path": "service.py", "sha256": m.digest(source), "bytes": source.stat().st_size}]})
    accepted = tmp_path / "baseline-accepted.json"
    create_json(m, accepted, {"status": "accepted", "validator": "test-independent-reviewer", "manifest": m.binding(baseline)})
    runtime = tmp_path / "runtime.exe"
    runtime.write_bytes(b"unit-test runtime identity; never native evidence")
    plan_path = tmp_path / "plan.json"
    create_json(m, plan_path, m.freeze(tasks, gold, environment, surfaces, baseline, accepted, runtime))
    project = tmp_path / "loop-fixture-unit"
    (project / "src").mkdir(parents=True)
    (project / "src" / "service.py").write_bytes(source.read_bytes())
    create_json(m, project / ".cognition-loop-fixture.json", {"schema": probe.FIXTURE_SCHEMA, "root": str(project.resolve()), "nonce": "a" * 32})
    stdout = tmp_path / "stdout.raw"
    stdout.write_bytes(b'{"status":"ok"}\n')
    stderr = tmp_path / "stderr.raw"
    stderr.write_bytes(b"")
    packet_path = tmp_path / "packet.json"
    packet = {"schema": "cognition-loop-packet.v1", "slot": "classic/L03", "kind": "mechanism_replay", "phase": "before", "case_id": "L03", "project_root": str(project.resolve()), "runtime": m.binding(runtime), "source_before": m.binding(sources), "installed_entry": m.binding(entry), "plan_sha256": m.digest(plan_path), "owned_paths": ["src/service.py"], "producer_id": "test-producer"}
    create_json(m, packet_path, packet)
    decisions = [{"id": fact["id"], "state": fact["expected_state"], "evidence": [m.binding(source)]} for fact in fact_contract("L03")]
    decision_path = tmp_path / "decisions.json"
    create_json(m, decision_path, decisions)
    semantic = tmp_path / "semantic.json"
    create_json(m, semantic, {"status": "accepted", "validator": "test-semantic-reviewer", "gold_sha256": m.digest(gold), "case_id": "L03", "decisions_sha256": m.digest(decision_path), "source_after": m.binding(sources), "rows": [{"id": fact["id"], "status": "accepted", "criterion": fact["criterion"], "reason": "Unit fixture only; inspected source", "evidence": [m.binding(source)]} for fact in fact_contract("L03")]})
    consumer_decision = tmp_path / "consumer.json"
    record = {**{key: value for key, value in packet.items() if key != "schema"}, "schema": "cognition-loop-observation.v1", "packet": m.binding(packet_path), "run_id": "unit-test-record",
              "started_at_ns": 1_000_000, "ended_at_ns": 11_000_000, "total_ms": 10,
              "attempts": [{"id": "initial", "stage": "closeout", "result": "passed", "started_at_ns": 2_000_000, "ended_at_ns": 4_000_000,
                            "calls": [{"argv": [str(runtime), "cognition", "status"], "cwd": str(project.resolve()), "exit_code": 0, "started_at_ns": 2_000_000, "ended_at_ns": 4_000_000, "stdout": m.binding(stdout), "stderr": m.binding(stderr)}], "evidence": []}],
              "business_result": "passed", "source_after": m.binding(sources), "fact_decisions": decisions, "decisions_artifact": m.binding(decision_path), "semantic_review": m.binding(semantic),
              "consumer": {"total_ms": 3}, "closeout": {"scope_result": "scope_ready"}, "model_tokens": {"status": "unavailable"}}
    proof_fields = {key: record[key] for key in ("run_id", "slot", "phase", "case_id", "project_root", "plan_sha256", "installed_entry", "source_after")}
    proof_fields.update(profile="classic", business_acceptance=["actual final behavior corresponds to task"], native_owner="unit-only fixture verification", native_calls=record["attempts"][0]["calls"])
    proof = {**proof_fields, "schema": "cognition-loop-business-proof.v1", "criteria": [{"id": "B01", "criterion": "actual final behavior corresponds to task", "status": "passed", "reason": "unit fixture only", "evidence": [m.binding(stdout)]}]}
    business_ref = create_json(m, tmp_path / "business-proof.json", proof)
    record["business_verification"] = business_ref
    record["consumer"]["decision"] = create_json(m, consumer_decision, {"case_id": "L03", "source_after": m.binding(sources), "business_result": "passed", "old_fact_used": False, "verification": business_ref})
    record["closeout"]["evidence"] = create_json(m, tmp_path / "closeout-proof.json", {**proof_fields, "schema": "cognition-loop-closeout-proof.v1", "scope_result": "scope_ready", "scope_binding": {"project_root": record["project_root"], "owned_paths": record["owned_paths"], "source_after": record["source_after"]}, "native_result": m.binding(stdout)})
    return m, probe, plan_path, packet_path, record


def rebind_packet(m, path, record, tmp_path):
    packet = m.load(path)
    for key in ("slot", "kind", "phase", "case_id", "project_root", "runtime", "source_before", "installed_entry", "plan_sha256", "owned_paths", "producer_id"):
        packet[key] = record[key]
    changed = tmp_path / f"packet-{len(list(tmp_path.glob('packet-*.json')))}.json"
    create_json(m, changed, packet)
    record["packet"] = m.binding(changed)


def test_fixed_denominators_are_separate_and_missing_remains_open(contract):
    m, _, plan, _, record = contract
    result = m.evaluate(plan, [record])
    assert [(row["kind"], row["required"], row["observed"]) for row in result["matrices"]] == [
        ("mechanism_replay", 80, 1), ("actual_agent_work", 20, 0), ("learning_ablation", 18, 0)]
    assert len(result["matrices"][0]["unexecuted_slots"]) == 79
    assert result["installed_entry_coverage"] == {"classic": 29, "advanced": 30, "classic_map_companions": 3}
    assert result["status"] == "pending_complete_loop_evidence"


def test_runtime_ready_without_semantics_or_consumer_is_not_complete(contract):
    m, _, plan, _, record = contract
    record.pop("semantic_review")
    record.pop("consumer")
    row = m.evaluate(plan, [record])["observations"][0]
    assert row["loop_acceptance"] == "fail"
    assert not row["independent_semantic_acceptance"]
    assert not row["new_session_consumer_passed"]


@pytest.mark.parametrize("kind", ["actual_agent_work", "learning_ablation"])
def test_replay_cannot_impersonate_actual_actor(contract, tmp_path, kind):
    m, _, plan, packet, record = contract
    record["kind"] = kind
    record["slot"] = "classic/L03" if kind == "actual_agent_work" else "classic/empty/new_session_repeat"
    if kind == "learning_ablation":
        record["case_id"] = "L35"
    rebind_packet(m, packet, record, tmp_path)
    with pytest.raises(ValueError, match="actual work actor"):
        m.evaluate(plan, [record])


def test_native_byte_counts_do_not_supply_model_tokens(contract):
    m, _, plan, _, record = contract
    record["model_tokens"] = {"status": "native_telemetry", "input": 10, "output": 20, "evidence": record["attempts"][0]["calls"][0]["stdout"]}
    with pytest.raises(ValueError, match="cannot supply model tokens"):
        m.evaluate(plan, [record])


def test_failure_history_counts_and_original_clock_cannot_be_reset(contract):
    m, _, plan, _, record = contract
    record["attempts"].insert(0, {"id": "failed-original", "stage": "verification", "result": "failed", "started_at_ns": 1_000_000, "ended_at_ns": 2_000_000, "calls": [], "evidence": []})
    row = m.evaluate(plan, [record])["observations"][0]
    assert row["loop_acceptance"] == "pass"
    assert not row["first_attempt_success"]
    assert row["metrics"]["complete_total_ms"] == 10
    assert row["metrics"]["failed_or_blocked_attempts"] == 1
    record["total_ms"] = 9
    with pytest.raises(ValueError, match="omits failures"):
        m.evaluate(plan, [record])


def test_old_alias_false_acceptance_and_missing_retirement_have_own_counts(contract):
    m, _, plan, _, record = contract
    record.pop("semantic_review")
    record["fact_decisions"][-1]["state"] = "accepted"
    row = m.evaluate(plan, [record])["observations"][0]
    assert row["false_accepted_facts"] == ["L03-old_fact"]
    assert row["missed_invalidation"] == ["L03-old_fact"]
    assert row["loop_acceptance"] == "fail"


def test_duplicate_slots_and_fact_ids_cannot_inflate_coverage(contract):
    m, _, plan, _, record = contract
    with pytest.raises(ValueError, match="duplicate observation"):
        m.evaluate(plan, [record, copy.deepcopy(record)])
    record["fact_decisions"].append(copy.deepcopy(record["fact_decisions"][0]))
    with pytest.raises(ValueError, match="duplicate fact"):
        m.evaluate(plan, [record])


def test_source_receipt_cross_case_and_final_version_binding_refuse(contract, tmp_path):
    m, _, plan, _, record = contract
    original = m.load(Path(record["semantic_review"]["path"]))
    changed = tmp_path / "foreign-review.json"
    original["case_id"] = "L01"
    record["semantic_review"] = create_json(m, changed, original)
    with pytest.raises(ValueError, match="original case"):
        m.evaluate(plan, [record])


def test_semantic_reviewer_cannot_be_output_author(contract, tmp_path):
    m, _, plan, _, record = contract
    review = m.load(Path(record["semantic_review"]["path"]))
    review["validator"] = record["producer_id"]
    record["semantic_review"] = create_json(m, tmp_path / "self-review.json", review)
    with pytest.raises(ValueError, match="not separate"):
        m.evaluate(plan, [record])


def test_missing_independent_fact_row_refuses_even_aggregate_pass(contract, tmp_path):
    m, _, plan, _, record = contract
    review = m.load(Path(record["semantic_review"]["path"]))
    review["rows"].pop()
    record["semantic_review"] = create_json(m, tmp_path / "incomplete-review.json", review)
    with pytest.raises(ValueError, match="dropped original fact"):
        m.evaluate(plan, [record])


@pytest.mark.parametrize("mutation", ["drop", "rename", "kind", "duplicate_kind"])
def test_gold_cannot_shrink_or_replace_original_task_fact_contract(contract, mutation):
    m, _, plan, _, _ = contract
    frozen = m.load(plan)
    gold = m.load(Path(frozen["gold"]["path"]))
    facts = gold["cases"][0]["facts"]
    if mutation == "drop":
        facts.pop()
    elif mutation == "rename":
        facts[0]["id"] = "invented-fact"
    elif mutation == "kind":
        facts[0]["kind"] = "old_fact"
    else:
        facts[1]["kind"] = facts[0]["kind"]
    with pytest.raises(ValueError, match="original task fact denominator"):
        m.validate_gold(gold, Path(frozen["tasks"]["path"]))


@pytest.mark.parametrize("missing", ["criterion", "reason", "evidence"])
def test_semantic_acceptance_labels_without_inspectable_fact_proof_refuse(contract, tmp_path, missing):
    m, _, plan, _, record = contract
    review = m.load(Path(record["semantic_review"]["path"]))
    review["rows"][0].pop(missing)
    record["semantic_review"] = create_json(m, tmp_path / f"semantic-no-{missing}.json", review)
    with pytest.raises(ValueError, match="each semantic fact row"):
        m.evaluate(plan, [record])


@pytest.mark.parametrize("target", ["business", "consumer", "closeout"])
def test_random_hashed_artifact_cannot_prove_business_consumer_or_closeout(contract, tmp_path, target):
    m, _, plan, _, record = contract
    arbitrary = record["attempts"][0]["calls"][0]["stdout"]
    if target == "business":
        record["business_verification"] = arbitrary
    elif target == "closeout":
        record["closeout"]["evidence"] = arbitrary
    else:
        decision = m.load(Path(record["consumer"]["decision"]["path"]))
        decision["verification"] = arbitrary
        record["consumer"]["decision"] = create_json(m, tmp_path / "arbitrary-consumer.json", decision)
    with pytest.raises(ValueError, match="typed native evidence certificate"):
        m.evaluate(plan, [record])


@pytest.mark.parametrize("field", ["case_id", "source_after", "installed_entry", "profile", "business_acceptance"])
def test_business_proof_cannot_bind_foreign_case_source_entry_or_criteria(contract, tmp_path, field):
    m, _, plan, _, record = contract
    proof = m.load(Path(record["business_verification"]["path"]))
    proof[field] = "foreign"
    record["business_verification"] = create_json(m, tmp_path / f"foreign-{field}.json", proof)
    with pytest.raises(ValueError, match="foreign episode|changed original business"):
        m.evaluate(plan, [record])


def test_closeout_proof_cannot_invent_a_call_outside_original_attempt_trace(contract, tmp_path):
    m, _, plan, _, record = contract
    proof = m.load(Path(record["closeout"]["evidence"]["path"]))
    proof["native_calls"][0]["argv"].append("invented-owner")
    record["closeout"]["evidence"] = create_json(m, tmp_path / "foreign-call-closeout.json", proof)
    with pytest.raises(ValueError, match="absent from original episode trace"):
        m.evaluate(plan, [record])


def test_closeout_proof_cannot_use_foreign_scope(contract, tmp_path):
    m, _, plan, _, record = contract
    proof = m.load(Path(record["closeout"]["evidence"]["path"]))
    proof["scope_binding"]["owned_paths"] = ["foreign/component.py"]
    record["closeout"]["evidence"] = create_json(m, tmp_path / "foreign-scope-proof.json", proof)
    with pytest.raises(ValueError, match="exact scope"):
        m.evaluate(plan, [record])


def test_failed_endpoint_cannot_enter_acceleration_ratio_and_keeps_cost_denominator(contract, tmp_path):
    m, _, before, _, record = contract
    frozen = m.load(before)
    prerequisite_rows = []
    for index in range(8):
        acceptance = tmp_path / f"unit-prerequisite-acceptance-{index}.json"
        create_json(m, acceptance, {"status": "accepted", "validator": "unit-independent-reviewer", "item": f"R{index}", "accepted_outputs": [frozen["runtime"]]})
        prerequisite_rows.append({"id": f"R{index}", "author": "unit-author", "acceptance": m.binding(acceptance), "outputs": [frozen["runtime"]]})
    prerequisite = tmp_path / "unit-prerequisites.json"
    create_json(m, prerequisite, {"status": "accepted", "items": prerequisite_rows})
    budget = tmp_path / "unit-budget.json"
    create_json(m, budget, {"schema": "cognition-loop-budget.v1", "before_plan_sha256": m.digest(before), "status": "accepted", "profiles": {profile: {"max_median_total_ratio": 1.1} for profile in m.PROFILES}})
    after = tmp_path / "unit-after.json"
    create_json(m, after, m.freeze_after(before, Path(frozen["runtime"]["path"]), Path(frozen["surfaces"]["path"]), Path(record["source_before"]["path"]), prerequisite, budget))
    # Both intentionally failed, preserving full timing. Their small values
    # cannot be used to manufacture a speedup from incomplete work.
    before_record = copy.deepcopy(record)
    before_record.pop("semantic_review")
    before_record.pop("consumer")
    before_record.pop("closeout")
    before_record["business_result"] = "failed"
    after_record = copy.deepcopy(before_record)
    after_record.update(phase="after", plan_sha256=m.digest(after), run_id="unit-after-failed", ended_at_ns=6_000_000, total_ms=5)
    after_record["packet"] = create_json(m, tmp_path / "unit-after-packet.json", {**m.load(Path(record["packet"]["path"])), "phase": "after", "plan_sha256": m.digest(after)})
    result = m.compare(before, after, [before_record], [after_record])
    pair = next(row for row in result["pairs"] if row["kind"] == "mechanism_replay" and row["profile"] == "classic")
    assert pair["available_pairs"] == 1 and pair["required_pairs"] == 40
    assert pair["matched_successful_pairs"] == 0
    assert pair["median_complete_ratio"] is None and pair["budget_status"] == "pending"
    assert pair["ineligible_failed_pairs"] == ["classic/L03"]
    assert pair["all_observed_cost_before_ms"] == 10 and pair["all_observed_cost_after_ms"] == 5


def test_plan_surface_and_forty_case_denominator_cannot_shrink(contract, tmp_path):
    m, _, plan, _, record = contract
    value = m.load(plan)
    value["required_slots"]["actual_agent_work"].pop()
    altered = tmp_path / "short-plan.json"
    create_json(m, altered, value)
    with pytest.raises(ValueError, match="shrink"):
        m.evaluate(altered, [record])
    surfaces = m.load(Path(value["surfaces"]["path"]))
    surfaces["entries"].pop()
    with pytest.raises(ValueError, match="29 Classic"):
        m.validate_surfaces(surfaces)


def test_after_requires_all_accepted_prerequisites_and_predeclared_profile_budgets(contract, tmp_path):
    m, _, plan, _, _ = contract
    original = m.load(plan)
    prerequisite = tmp_path / "prerequisites.json"
    create_json(m, prerequisite, {"status": "accepted", "items": []})
    budget = tmp_path / "budget.json"
    create_json(m, budget, {"schema": "cognition-loop-budget.v1", "before_plan_sha256": m.digest(plan), "status": "accepted", "profiles": {}})
    with pytest.raises(ValueError, match="all eight"):
        m.freeze_after(plan, Path(original["runtime"]["path"]), Path(original["surfaces"]["path"]), Path(m.load(Path(original["gold"]["path"]))["cases"][0]["source_before"]["path"]), prerequisite, budget)


@pytest.mark.parametrize("path", ["../escape.py", "/outside.py", "C:/outside.py", "src\\service.py"])
def test_probe_does_not_route_edits_outside_fixture(contract, path):
    _, probe, _, _, record = contract
    with pytest.raises(ValueError, match="path must"):
        probe.inside(Path(record["project_root"]), path)


def test_probe_protects_existing_targets_and_runtime_owners(contract, tmp_path):
    m, probe, _, _, record = contract
    with pytest.raises(ValueError, match="new dedicated"):
        probe.create_fixture(Path(record["project_root"]))
    observation = tmp_path / "open.json"
    create_json(m, observation, record)
    record["owned_paths"].append(".specify/project-cognition/project-cognition.db")
    observation.write_text(__import__("json").dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="protected runtime"):
        probe.edit(observation, ".specify/project-cognition/project-cognition.db", "bad")


def test_probe_actual_work_and_build_run_in_new_fixture(tmp_path):
    m, probe = modules()
    project = tmp_path / "loop-fixture-real-code"
    probe.create_fixture(project)
    import subprocess
    for argv in ([sys.executable, "-m", "unittest", "discover", "-s", "tests"], [sys.executable, "build.py"]):
        result = subprocess.run(argv, cwd=project, capture_output=True, timeout=30, check=False)
        assert result.returncode == 0, result.stderr
    assert (project / "out" / "service.zip").is_file()
    first = probe.snapshot(project, list(probe.FIXTURE_FILES), tmp_path / "first")
    assert len(m.source_manifest(first, "real fixture")) == 10


def test_fixture_rename_requires_real_consumer_dependency_repair(tmp_path):
    _, probe = modules()
    project = tmp_path / "loop-fixture-real-rename"
    probe.create_fixture(project)
    import subprocess
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_service.py"]
    (project / "src/legacy.py").rename(project / "src/compat.py")
    failed = subprocess.run(command, cwd=project, capture_output=True, timeout=30, check=False)
    assert failed.returncode != 0 and b"src.legacy" in failed.stderr
    consumer = project / "src/consumer.py"
    consumer.write_text(consumer.read_text().replace("from src.legacy import", "from src.compat import"), encoding="utf-8")
    repaired = subprocess.run(command, cwd=project, capture_output=True, timeout=30, check=False)
    assert repaired.returncode == 0, repaired.stderr
    assert not (project / "src/legacy.py").exists()


def test_probe_submit_cannot_rewrite_original_clock_or_failure_history(contract, tmp_path):
    m, probe, _, _, record = contract
    observation = tmp_path / "open.json"
    create_json(m, observation, record)
    decision = tmp_path / "illegal-decision.json"
    create_json(m, decision, {"started_at_ns": record["ended_at_ns"], "attempts": []})
    with pytest.raises(ValueError, match="cannot overwrite"):
        probe.submit(observation, decision, tmp_path / "final.json")


def test_changed_artifact_and_exclusive_output_refuse(contract, tmp_path):
    m, _, plan, _, record = contract
    destination = tmp_path / "output.json"
    create_json(m, destination, {})
    with pytest.raises(FileExistsError):
        m.write_new(destination, {})
    Path(record["attempts"][0]["calls"][0]["stdout"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed evidence"):
        m.evaluate(plan, [record])


def test_new_consumer_must_be_fresh_native_actor(contract, tmp_path):
    m, _, plan, packet, record = contract
    record["kind"] = "actual_agent_work"
    rebind_packet(m, packet, record, tmp_path)
    actor = tmp_path / "actor.json"
    create_json(m, actor, {"task_id": "unit-test-actor", "turn_id": "unit-test-turn", "model": "unit-test-only", "origin": "native_collaboration"})
    record["actor"] = m.binding(actor)
    record["consumer"]["identity"] = m.binding(actor)
    with pytest.raises(ValueError, match="different native Agent"):
        m.evaluate(plan, [record])


def test_declared_native_telemetry_needs_its_actual_evidence(contract):
    m, _, plan, _, record = contract
    record["lock_wait"] = {"status": "estimated", "ms": 0}
    with pytest.raises(ValueError, match="cannot be inferred"):
        m.evaluate(plan, [record])


def test_instrumented_source_bytes_are_separate_from_unavailable_native_io(contract, tmp_path):
    m, _, plan, _, record = contract
    source = m.load(Path(record["source_before"]["path"]))[0]
    record["source_reads"] = [{"source_path": "src/service.py", "source_sha256": source["sha256"], "evidence": source}]
    record["source_edits"] = [create_json(m, tmp_path / "instrumented-edit.json", {"source_path": "src/service.py", "source_write_bytes": 19})]
    metrics = m.evaluate(plan, [record])["observations"][0]["metrics"]
    assert metrics["instrumented_source_read_bytes"] == source["bytes"]
    assert metrics["instrumented_source_write_bytes"] == 19
    assert metrics["io"] == {"status": "unavailable"}
    record["source_reads"][0]["source_path"] = ".specify/project-cognition/project-cognition.db"
    with pytest.raises(ValueError, match="source-read byte evidence"):
        m.evaluate(plan, [record])


def test_native_start_failure_preserves_original_episode_attempt(contract, tmp_path, monkeypatch):
    m, probe, _, packet_path, record = contract
    packet = m.load(packet_path)
    packet["allowed_commands"] = [{"executable": record["runtime"], "argv_prefix": []}]
    mutable_packet = tmp_path / "start-failure-packet.json"
    create_json(m, mutable_packet, packet)
    record["packet"] = m.binding(mutable_packet)
    observation = tmp_path / "start-failure-open.json"
    create_json(m, observation, record)
    original_start = record["started_at_ns"]
    def cannot_start(*args, **kwargs):
        raise PermissionError("actual injected unit-test process boundary failure")
    monkeypatch.setattr(probe.subprocess, "run", cannot_start)
    result = probe.call(observation, [record["runtime"]["path"]], "verification")
    saved = m.load(observation)
    assert result["result"] == "failed" and result["call"]["exit_code"] == -1
    assert saved["started_at_ns"] == original_start
    assert len(saved["attempts"]) == len(record["attempts"]) + 1
    assert b"PermissionError" in Path(result["call"]["stderr"]["path"]).read_bytes()


def test_source_edit_after_checkpoint_reopens_instead_of_reusing_review(contract, tmp_path):
    m, probe, _, _, record = contract
    # Start with an author-only trace; unit-test time provenance is irrelevant
    # here because this checks the recorder's version handoff refusal.
    record.pop("source_after")
    record.pop("semantic_review")
    record.pop("consumer")
    record.pop("decisions_artifact")
    observation = tmp_path / "open.json"
    create_json(m, observation, record)
    candidate = tmp_path / "candidate.json"
    create_json(m, candidate, {"business_result": "passed", "fact_decisions": record["fact_decisions"]})
    probe.checkpoint(observation, candidate)
    Path(record["project_root"], "src/service.py").write_text("changed after verification\n", encoding="utf-8")
    finish = tmp_path / "finish.json"
    create_json(m, finish, {})
    with pytest.raises(ValueError, match="reopen owning task"):
        probe.submit(observation, finish, tmp_path / "final.json")
    probe.checkpoint(observation, candidate)
    repaired = m.load(observation)
    assert len(repaired["candidate_history"]) == 1
    assert repaired["candidate_history"][0]["status"] == "superseded_pending_revalidation"
    assert repaired["started_at_ns"] == record["started_at_ns"]
    assert repaired["attempts"][:-1] == record["attempts"]
    assert repaired["attempts"][-1]["result"] == "failed"


def test_probe_source_reads_do_not_bypass_runtime_stores(contract, tmp_path):
    m, probe, _, packet, record = contract
    value = m.load(packet)
    value["read_paths"] = [".specify/project-cognition/status.json"]
    changed = tmp_path / "unsafe-read-packet.json"
    record["packet"] = create_json(m, changed, value)
    observation = tmp_path / "unsafe-open.json"
    create_json(m, observation, record)
    with pytest.raises(ValueError, match="protected runtime"):
        probe.read(observation, ".specify/project-cognition/status.json")
