"""Exact planner compatibility, bounded-work and fresh-evidence regressions.

The reference is the pre-optimization full-rescan selector, not another agent's
acceptance. Generated matrices exercise the declared combination model only.
"""
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/shared/e2e_coverage.py"
spec = importlib.util.spec_from_file_location("e2e_coverage_planner_tests", HELPER)
e2e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e2e)


def source(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def model_for(seed=0):
    rng = random.Random(seed)
    journeys = []
    for number in range(1 + seed % 3):
        width = rng.randint(1, 5)
        factors = {f"factor-{i}": [f"value-{j}" for j in range(rng.randint(1, 3))]
                   for i in range(width)}
        keys = sorted(factors)
        rows = [dict(zip(keys, values)) for values in itertools.product(*(factors[k] for k in keys))]
        excluded = []
        if len(rows) > 2:
            banned = rng.choice(rows)
            remaining = [row for row in rows if row != banned]
            if all({row[k] for row in remaining} == set(factors[k]) for k in keys):
                excluded = [{"when": banned, "reason": "synthetic infeasible fixture"}]
                rows = remaining
        mandatory = []
        for _ in range(seed % 7):
            row = rng.choice(rows)
            subset = rng.sample(keys, rng.randint(1, width))
            mandatory.append({k: row[k] for k in subset})
        if mandatory and seed % 2:
            mandatory.append(deepcopy(mandatory[0]))
        journeys.append({"id": f"journey-{number}", "requirements": ["R1"],
                         "steps": ["enter", "act", "observe"], "factors": factors,
                         "strength": "exhaustive" if seed % 11 == 0 else rng.randint(1, width),
                         "exclude": excluded, "mandatory": mandatory})
    return {"schema_version": 1, "scope": "synthetic planner contract",
            "source_revision": "fixture", "sources": [{"path": "source.txt", "sha256": "0" * 64}],
            "requirements": [{"id": "R1", "source": "source.txt", "assertion": "fixture assertion"}],
            "journeys": journeys, "exclusions": []}


def reference_plan(model, max_cases=1000):
    """Freeze the old selector and its lexicographic mandatory-first scoring."""
    cases, summaries = [], []
    for identity, data in e2e.prepare(model).items():
        uncovered = set(data["universe"])
        mandatory = list(data["mandatory"])
        chosen = []
        if data["strength"] == len(data["candidates"][0]):
            chosen = list(range(len(data["candidates"])))
            uncovered.clear()
            mandatory.clear()
        while uncovered or mandatory:
            scores = [(sum(all(row[k] == v for k, v in item.items()) for item in mandatory),
                       len(data["tuples"][i] & uncovered)) for i, row in enumerate(data["candidates"])]
            best = max(range(len(scores)), key=lambda i: scores[i])
            assert scores[best] != (0, 0)
            row = data["candidates"][best]
            chosen.append(best)
            uncovered.difference_update(data["tuples"][best])
            mandatory = [item for item in mandatory if not all(row[k] == v for k, v in item.items())]
        if len(cases) + len(chosen) > max_cases:
            raise e2e.CoverageError(f"case budget {max_cases} exceeded; raise the budget or explicitly revise scope/strength")
        for index in chosen:
            row = data["candidates"][index]
            payload = json.dumps({"journey": identity, "parameters": row}, sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":"))
            cases.append({"id": "E2E-" + hashlib.sha256(payload.encode()).hexdigest()[:24],
                          "journey": identity, "parameters": row, "requirements": data["requirements"]})
        summaries.append({"journey": identity, "strength": data["strength"],
                          "feasible_combinations": len(data["candidates"]),
                          "required_interactions": len(data["universe"]), "planned_cases": len(chosen),
                          "mandatory_combinations": len(data["mandatory"])})
    payload = json.dumps(model, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {"schema_version": 1, "manifest_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "claim": "planned_only", "cases": cases, "journeys": summaries,
            "exclusions": model.get("exclusions", [])}


def assert_full_denominator(model, planned):
    """Enumerate feasibility/tuples without the production prepare/interactions."""
    for journey in model["journeys"]:
        keys = sorted(journey["factors"])
        feasible = [dict(zip(keys, values)) for values in itertools.product(
            *(journey["factors"][key] for key in keys))]
        feasible = [row for row in feasible if not any(
            all(row[k] == v for k, v in item["when"].items()) for item in journey["exclude"])]
        selected = [case["parameters"] for case in planned["cases"] if case["journey"] == journey["id"]]
        strength = journey["strength"]
        if strength == "exhaustive":
            strength = len(keys)
        def tuples(rows):
            return {tuple((k, row[k]) for k in subset) for row in rows
                    for subset in itertools.combinations(keys, strength)}
        assert tuples(selected) == tuples(feasible)
        assert len({tuple(sorted(row.items())) for row in selected}) == len(selected)
        assert all(row in feasible for row in selected)
        assert all(any(all(row[k] == v for k, v in partial.items()) for row in selected)
                   for partial in journey["mandatory"])


@pytest.mark.parametrize("seed", range(128))
def test_generated_models_preserve_exact_legacy_plan_and_feasible_coverage(seed):
    model = model_for(seed)
    original = deepcopy(model)
    expected = reference_plan(model)
    assert e2e.plan(model) == expected
    assert e2e.plan(model, max_cases=len(expected["cases"])) == expected
    assert_full_denominator(model, expected)
    assert model == original
    if len(expected["cases"]) > 1:
        with pytest.raises(e2e.CoverageError, match="case budget"):
            e2e.plan(model, max_cases=len(expected["cases"]) - 1)


def results_for(model, root):
    tests = source(root, "test.txt", "synthetic assertion fixture; no product execution")
    evidence = source(root, "run.json", '{"fixture": true}')
    return {"schema_version": 1, "manifest_sha256": e2e.digest(model),
            "source_revision": model["source_revision"], "run_id": "synthetic-audit-fixture",
            "target": "fixture", "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:01:00Z", "command": ["fixture"], "exit_code": 0,
            "test_sources": [tests], "evidence": [evidence],
            "cases": [{"id": case["id"], "status": "passed", "test_ref": tests["path"],
                       "asserted_requirements": case["requirements"], "evidence": [evidence]}
                      for case in reference_plan(model)["cases"]]}


@pytest.fixture
def bound_model(tmp_path):
    model = model_for(7)
    model["sources"] = [source(tmp_path, "source.txt", "source revision one")]
    return model


def test_audit_prepares_once_and_accepts_historical_case_bindings(bound_model, tmp_path, monkeypatch):
    results = results_for(bound_model, tmp_path)
    original = e2e.prepare
    calls = []
    def counted(model, root=None):
        calls.append(root)
        return original(model, root)
    monkeypatch.setattr(e2e, "prepare", counted)
    report = e2e.audit(bound_model, results, tmp_path)
    assert calls == [tmp_path]
    assert report["claim"] == "complete_against_frozen_scope"
    assert not report["gaps"]
    assert all(not row["missing_interactions"] and not row["missing_mandatory"] for row in report["journeys"])


@pytest.mark.parametrize("path", ["source.txt", "test.txt", "run.json"])
def test_audit_rechecks_bytes_on_every_invocation(bound_model, tmp_path, path):
    results = results_for(bound_model, tmp_path)
    assert e2e.audit(bound_model, results, tmp_path)["claim"] == "complete_against_frozen_scope"
    (tmp_path / path).write_text("changed after accepted fixture audit", encoding="utf-8")
    with pytest.raises(e2e.CoverageError, match="stale or changed"):
        e2e.audit(bound_model, results, tmp_path)


@pytest.mark.parametrize("status", ["failed", "skipped", "blocked", "not_run", "flaky", "missing"])
def test_historical_bindings_keep_every_nonpass_visible(bound_model, tmp_path, status):
    results = results_for(bound_model, tmp_path)
    identity = results["cases"][0]["id"]
    if status == "missing":
        results["cases"].pop(0)
        status = "not_run"
    else:
        results["cases"][0]["status"] = status
    report = e2e.audit(bound_model, results, tmp_path)
    assert report["claim"] == "incomplete"
    assert report["statuses"][status] == 1
    assert any(row["id"] == identity and row["status"] == status for row in report["gaps"])
    assert sum(report["statuses"].values()) == len(reference_plan(bound_model)["cases"])


@pytest.mark.parametrize("mode", ["plan", "audit"])
@pytest.mark.parametrize("budget", [0, -1, True, 1.5, "1", None])
def test_budget_validation_still_precedes_model_validation(mode, budget, tmp_path):
    with pytest.raises(e2e.CoverageError, match="max_cases must be positive"):
        if mode == "plan":
            e2e.plan({}, tmp_path, budget)
        else:
            e2e.audit({}, {}, tmp_path, budget)


def test_indexed_selector_does_not_mutate_prepared_inputs():
    model = model_for(19)
    prepared = e2e.prepare(model)
    original = deepcopy(prepared)
    first = e2e._plan_prepared(model, prepared, 1000)
    assert e2e._plan_prepared(model, prepared, 1000) == first
    assert prepared == original


def test_mandatory_matching_is_per_selected_row_not_per_candidate_round(monkeypatch):
    model = model_for()
    journey = model["journeys"][0]
    journey.update(factors={f"f{i}": ["0", "1", "2"] for i in range(6)}, strength=2,
                   exclude=[], mandatory=[{"f0": "2"}, {"f0": "2", "f1": "1"}] * 4)
    prepared = e2e.prepare(model)
    original = e2e.matches
    calls = 0
    def counted(row, partial):
        nonlocal calls
        calls += 1
        return original(row, partial)
    monkeypatch.setattr(e2e, "matches", counted)
    planned = e2e._plan_prepared(model, prepared, 1000)
    assert calls <= len(planned["cases"]) * len(journey["mandatory"])
    assert len(planned["cases"]) < len(prepared[journey["id"]]["candidates"])


def test_unicode_overlapping_duplicate_mandatory_and_tie_order():
    model = model_for()
    model["journeys"] = [{"id": "unicode", "requirements": ["R1"], "steps": ["act", "observe"],
                          "factors": {"角色": ["管理员", "访客"], "a": ["[a]", "z"]}, "strength": 1,
                          "exclude": [], "mandatory": [{"角色": "访客"}, {"角色": "访客"},
                                                       {"角色": "访客", "a": "z"}]}]
    planned = e2e.plan(model)
    assert planned == reference_plan(model)
    assert planned["cases"][0]["parameters"] == {"a": "z", "角色": "访客"}


@pytest.mark.parametrize("limit,field,value", [("MAX_CANDIDATES", "candidates exceed", 1),
                                               ("MAX_TOTAL_CANDIDATES", "total candidate budget", 1),
                                               ("MAX_INTERACTIONS", "interaction budget", 1)])
def test_preparation_budgets_still_fail_closed(monkeypatch, limit, field, value):
    model = model_for(5)
    monkeypatch.setattr(e2e, limit, value)
    with pytest.raises(e2e.CoverageError, match=field):
        e2e.plan(model)


def test_process_hash_seeds_do_not_change_plan(bound_model, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(bound_model), encoding="utf-8")
    outputs = []
    for seed in ("0", "1", "8675309", "random"):
        proc = subprocess.run([sys.executable, str(HELPER), "plan", str(manifest), "--root", str(tmp_path)],
                              env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, text=True,
                              timeout=30, check=False)
        assert proc.returncode == 0, proc.stderr
        outputs.append(proc.stdout)
    assert all(output == outputs[0] for output in outputs)
    assert json.loads(outputs[0]) == reference_plan(bound_model)


def test_cli_budget_refusal_has_no_partial_plan(bound_model, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(bound_model), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(HELPER), "plan", str(manifest), "--root", str(tmp_path),
                           "--max-cases", "1"], capture_output=True, text=True, timeout=30, check=False)
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert json.loads(proc.stderr)["claim"] == "invalid"
    assert "case budget" in json.loads(proc.stderr)["error"]


@pytest.mark.parametrize("disposition", ["plan", "passed", "missing", "stale", "no-results"])
def test_in_process_cli_preserves_all_exit_claims(bound_model, tmp_path, capsys, disposition):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(bound_model), encoding="utf-8")
    argv = ["plan" if disposition == "plan" else "audit", str(manifest), "--root", str(tmp_path)]
    expected_exit, expected_claim = 0, "planned_only"
    if disposition != "plan":
        results = results_for(bound_model, tmp_path)
        expected_claim = "complete_against_frozen_scope"
        if disposition == "missing":
            results["cases"] = []
            expected_exit, expected_claim = 1, "incomplete"
        elif disposition == "stale":
            (tmp_path / "source.txt").write_text("stale", encoding="utf-8")
            expected_exit, expected_claim = 2, "invalid"
        elif disposition == "no-results":
            expected_exit, expected_claim = 2, "invalid"
        result_path = tmp_path / "result.json"
        result_path.write_text(json.dumps(results), encoding="utf-8")
        if disposition != "no-results":
            argv += ["--results", str(result_path)]
    assert e2e.main(argv) == expected_exit
    captured = capsys.readouterr()
    payload = captured.err if expected_exit == 2 else captured.out
    assert json.loads(payload)["claim"] == expected_claim
    assert (captured.out if expected_exit == 2 else captured.err) == ""


def test_benchmark_checks_every_output_and_alternates_order(monkeypatch):
    benchmark_path = ROOT / "tools/workflow-quality/benchmark_e2e_coverage.py"
    spec = importlib.util.spec_from_file_location("benchmark_e2e_test", benchmark_path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    clock = iter(range(12))
    monkeypatch.setattr(benchmark, "time", SimpleNamespace(perf_counter=lambda: next(clock)))
    calls = []
    def run(name):
        calls.append(name)
        return {"fixed": [1, 2, 3]}
    report = benchmark.compare_calls(lambda: run("baseline"), lambda: run("candidate"), 3)
    assert calls == ["baseline", "candidate", "baseline", "candidate", "candidate", "baseline", "baseline", "candidate"]
    assert report["outputs_equal"] is True
    assert report["speedup"] == 1
    assert report["samples_seconds"] == {"baseline": [1, 1, 1], "candidate": [1, 1, 1]}
    with pytest.raises(ValueError, match="output mismatch"):
        benchmark.compare_calls(lambda: 1, lambda: 2, 1)
    changing = iter([1, 2])
    clock = iter(range(4))
    with pytest.raises(ValueError, match="nondeterministic"):
        benchmark.compare_calls(lambda: 1, lambda: next(changing), 1)


@pytest.mark.parametrize("cardinalities,strength", [((100, 100), 1), ((10, 10, 10, 10), 2), ((3, 3, 3, 3, 3, 3), 3)])
def test_large_bounded_matrices_preserve_exact_plan(cardinalities, strength):
    model = model_for()
    journey = model["journeys"][0]
    journey.update(factors={f"f{i}": [str(value) for value in range(size)]
                            for i, size in enumerate(cardinalities)},
                   strength=strength, exclude=[], mandatory=[])
    planned = e2e.plan(model)
    assert planned == reference_plan(model)
    assert_full_denominator(model, planned)
