"""Behavioral regression tests for the shared, dependency-free E2E helper."""
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "shared" / "e2e_coverage.py"
spec = importlib.util.spec_from_file_location("e2e_coverage", HELPER)
e2e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e2e)


def receipt(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def model(tmp_path):
    source = receipt(tmp_path, "app.txt", "revision-one")
    return {
        "schema_version": 1, "scope": "checkout", "source_revision": "fixture-revision",
        "sources": [source], "exclusions": [{"scope": "live bank", "reason": "sandbox only"}],
        "requirements": [{"id": "R1", "source": "app.txt", "assertion": "persist exactly one order"}],
        "journeys": [{
            "id": "checkout", "requirements": ["R1"],
            "steps": ["open checkout", "submit", "reload and verify persisted outcome"],
            "factors": {"role": ["member", "admin"], "browser": ["chromium", "firefox"],
                        "data": ["empty", "normal", "boundary"]},
            "strength": 2, "exclude": [], "mandatory": [],
        }],
    }


def result_for(model, root):
    plan = e2e.plan(model, root)
    tests = receipt(root, "tests/checkout.spec.ts", "// test-asset fixture, not a browser run")
    evidence = receipt(root, "results/run.json", "{\"fixture\": true}")
    return {
        "schema_version": 1, "manifest_sha256": plan["manifest_sha256"],
        "source_revision": model["source_revision"], "run_id": "unit-test-fixture",
        "target": "fixture", "started_at": "2026-09-29T00:00:00Z",
        "finished_at": "2026-09-29T00:01:00Z", "command": ["fixture", "--project", "one", "--project", "two"],
        "exit_code": 0, "test_sources": [tests], "evidence": [evidence],
        "cases": [{"id": case["id"], "status": "passed", "test_ref": tests["path"],
                   "asserted_requirements": case["requirements"], "evidence": [evidence]}
                  for case in plan["cases"]],
    }


def independently_observed_pairs(rows):
    pairs = set()
    for row in rows:
        for a, b in itertools.combinations(sorted(row), 2):
            pairs.add(((a, row[a]), (b, row[b])))
    return pairs


def test_pairwise_covers_actual_feasible_universe(model, tmp_path):
    plan = e2e.plan(model, tmp_path)
    factors = model["journeys"][0]["factors"]
    keys = sorted(factors)
    exhaustive = [dict(zip(keys, values)) for values in itertools.product(*(factors[k] for k in keys))]
    assert independently_observed_pairs([case["parameters"] for case in plan["cases"]]) == independently_observed_pairs(exhaustive)
    assert len(plan["cases"]) < len(exhaustive)
    assert plan["claim"] == "planned_only"


def test_constraints_and_mandatory_three_way(model, tmp_path):
    journey = model["journeys"][0]
    journey["exclude"] = [{"when": {"role": "admin", "data": "empty"}, "reason": "unreachable fixture"}]
    required = {"role": "member", "browser": "firefox", "data": "boundary"}
    journey["mandatory"] = [required]
    plan = e2e.plan(model, tmp_path)
    rows = [case["parameters"] for case in plan["cases"]]
    assert required in rows
    assert not any(row["role"] == "admin" and row["data"] == "empty" for row in rows)
    factors = journey["factors"]
    keys = sorted(factors)
    feasible = [dict(zip(keys, values)) for values in itertools.product(*(factors[k] for k in keys))]
    feasible = [row for row in feasible if not (row["role"] == "admin" and row["data"] == "empty")]
    assert independently_observed_pairs(rows) == independently_observed_pairs(feasible)


@pytest.mark.parametrize("strength", [3, "exhaustive"])
def test_higher_order_and_exhaustive(model, tmp_path, strength):
    model["journeys"][0]["strength"] = strength
    assert len(e2e.plan(model, tmp_path)["cases"]) == 12


def test_single_factor(model, tmp_path):
    model["journeys"][0]["factors"] = {"role": ["member", "admin"]}
    model["journeys"][0].pop("strength")
    assert len(e2e.plan(model, tmp_path)["cases"]) == 2


def test_deterministic_across_input_order(model, tmp_path):
    before = e2e.plan(model, tmp_path)
    modified = deepcopy(model)
    factors = modified["journeys"][0]["factors"]
    modified["journeys"][0]["factors"] = {key: list(reversed(values)) for key, values in reversed(list(factors.items()))}
    assert before["cases"] == e2e.plan(modified, tmp_path)["cases"]


@pytest.mark.parametrize("bad_strength", [0, 4, True, "pairwise", -1])
def test_invalid_strength(model, tmp_path, bad_strength):
    model["journeys"][0]["strength"] = bad_strength
    with pytest.raises(e2e.CoverageError, match="strength"):
        e2e.plan(model, tmp_path)


def test_unmapped_requirement(model, tmp_path):
    model["requirements"].append({"id": "R2", "source": "app.txt", "assertion": "not forgotten"})
    with pytest.raises(e2e.CoverageError, match="unmapped requirements"):
        e2e.plan(model, tmp_path)


@pytest.mark.parametrize("field", ["requirements", "journeys"])
def test_duplicate_identity_rejected(model, tmp_path, field):
    model[field].append(deepcopy(model[field][0]))
    with pytest.raises(e2e.CoverageError, match="duplicate id"):
        e2e.plan(model, tmp_path)


def test_unknown_requirement_rejected(model, tmp_path):
    model["journeys"][0]["requirements"] = ["UNKNOWN"]
    with pytest.raises(e2e.CoverageError, match="unknown requirement"):
        e2e.plan(model, tmp_path)


def test_infeasible_mandatory_rejected(model, tmp_path):
    journey = model["journeys"][0]
    journey["exclude"] = [{"when": {"role": "admin", "data": "empty"}, "reason": "impossible"}]
    journey["mandatory"] = [{"role": "admin", "data": "empty"}]
    with pytest.raises(e2e.CoverageError, match="infeasible mandatory"):
        e2e.plan(model, tmp_path)


def test_dead_factor_value_rejected(model, tmp_path):
    model["journeys"][0]["exclude"] = [{"when": {"role": "admin"}, "reason": "would hide a whole role"}]
    with pytest.raises(e2e.CoverageError, match="unreachable"):
        e2e.plan(model, tmp_path)


def test_no_silent_sampling_on_budget(model, tmp_path):
    with pytest.raises(e2e.CoverageError, match="case budget"):
        e2e.plan(model, tmp_path, max_cases=1)
    model["journeys"][0]["factors"] = {str(i): ["a", "b"] for i in range(14)}
    with pytest.raises(e2e.CoverageError, match="candidates exceed"):
        e2e.plan(model, tmp_path)


def test_empty_model_and_zero_test_results_not_green(model, tmp_path):
    with pytest.raises(e2e.CoverageError):
        e2e.plan({}, tmp_path)
    results = result_for(model, tmp_path)
    results["cases"] = []
    report = e2e.audit(model, results, tmp_path)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["not_run"] == report["planned_cases"]
    assert report["requirements"]["missing"] == ["R1"]


def test_complete_fixture_and_exclusions_reported(model, tmp_path):
    report = e2e.audit(model, result_for(model, tmp_path), tmp_path)
    assert report["claim"] == "complete_against_frozen_scope"
    assert report["exclusions"] == model["exclusions"]
    assert all(not journey["missing_interactions"] for journey in report["journeys"])


@pytest.mark.parametrize("status", ["failed", "skipped", "blocked", "not_run", "flaky"])
def test_nonpass_never_closes_run(model, tmp_path, status):
    results = result_for(model, tmp_path)
    results["cases"][0]["status"] = status
    report = e2e.audit(model, results, tmp_path)
    assert report["claim"] == "incomplete"
    assert report["statuses"][status] == 1


def test_missing_case_is_not_run(model, tmp_path):
    results = result_for(model, tmp_path)
    results["cases"].pop()
    report = e2e.audit(model, results, tmp_path)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["not_run"] == 1


def test_failing_runner_not_overridden_by_case_statuses(model, tmp_path):
    results = result_for(model, tmp_path)
    results["exit_code"] = 1
    assert e2e.audit(model, results, tmp_path)["claim"] == "incomplete"


@pytest.mark.parametrize("field", ["manifest_sha256", "source_revision"])
def test_stale_run_binding(model, tmp_path, field):
    results = result_for(model, tmp_path)
    results[field] = "stale"
    with pytest.raises(e2e.CoverageError, match="stale"):
        e2e.audit(model, results, tmp_path)


@pytest.mark.parametrize("path", ["app.txt", "tests/checkout.spec.ts", "results/run.json"])
def test_changed_source_test_or_evidence_rejected(model, tmp_path, path):
    results = result_for(model, tmp_path)
    (tmp_path / path).write_text("changed", encoding="utf-8")
    with pytest.raises(e2e.CoverageError, match="stale or changed"):
        e2e.audit(model, results, tmp_path)


@pytest.mark.parametrize("change", ["duplicate", "unknown", "missing_assertion", "missing_evidence", "unbound_test", "unknown_status"])
def test_bad_result_rejected(model, tmp_path, change):
    results = result_for(model, tmp_path)
    row = results["cases"][0]
    if change == "duplicate":
        results["cases"].append(deepcopy(row))
    elif change == "unknown":
        row["id"] = "unknown"
    elif change == "missing_assertion":
        row["asserted_requirements"] = []
    elif change == "missing_evidence":
        row["evidence"] = []
    elif change == "unbound_test":
        row["test_ref"] = "other.ts"
    else:
        row["status"] = "pass"
    with pytest.raises(e2e.CoverageError):
        e2e.audit(model, results, tmp_path)


def test_evidence_cannot_escape_root(model, tmp_path):
    results = result_for(model, tmp_path)
    results["evidence"][0]["path"] = "../outside.txt"
    with pytest.raises(e2e.CoverageError, match="unsafe path"):
        e2e.audit(model, results, tmp_path)


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
    with pytest.raises(e2e.CoverageError, match="duplicate JSON key"):
        e2e.load(path)


def test_cli_end_to_end_exit_codes(model, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(model), encoding="utf-8")
    prefix = [sys.executable, str(HELPER)]
    run = subprocess.run(prefix + ["plan", str(manifest), "--root", str(tmp_path)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["claim"] == "planned_only"
    results = result_for(model, tmp_path)
    result_path = tmp_path / "results.json"
    argv = prefix + ["audit", str(manifest), "--root", str(tmp_path), "--results", str(result_path)]
    result_path.write_text(json.dumps(results), encoding="utf-8")
    run = subprocess.run(argv, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    results["cases"].pop()
    result_path.write_text(json.dumps(results), encoding="utf-8")
    assert subprocess.run(argv, capture_output=True).returncode == 1
    (tmp_path / "app.txt").write_text("stale", encoding="utf-8")
    run = subprocess.run(argv, capture_output=True, text=True)
    assert run.returncode == 2
    assert not run.stdout
    assert json.loads(run.stderr)["claim"] == "invalid"


def test_repeated_steps_are_valid_for_duplicate_submission_journey(model, tmp_path):
    model["journeys"][0]["steps"] = ["open", "submit", "submit", "verify one persisted order"]
    assert e2e.plan(model, tmp_path)["cases"]


def test_missing_mandatory_combo_reported_separately(model, tmp_path):
    required = {"role": "member", "browser": "firefox", "data": "boundary"}
    model["journeys"][0]["mandatory"] = [required]
    planned = e2e.plan(model, tmp_path)
    results = result_for(model, tmp_path)
    identity = next(case["id"] for case in planned["cases"] if case["parameters"] == required)
    next(row for row in results["cases"] if row["id"] == identity)["status"] = "blocked"
    report = e2e.audit(model, results, tmp_path)
    assert report["journeys"][0]["missing_mandatory"] == [required]
    assert report["claim"] == "incomplete"


@pytest.mark.parametrize("where", ["manifest", "journey", "requirement", "constraint", "source", "results", "case"])
def test_unknown_fields_rejected_instead_of_silently_ignored(model, tmp_path, where):
    results = result_for(model, tmp_path)
    target = model
    if where == "journey":
        target = model["journeys"][0]
    elif where == "requirement":
        target = model["requirements"][0]
    elif where == "constraint":
        model["journeys"][0]["exclude"] = [{"when": {"role": "admin", "data": "empty"}, "reason": "fixture"}]
        target = model["journeys"][0]["exclude"][0]
    elif where == "source":
        target = model["sources"][0]
    elif where == "results":
        target = results
    elif where == "case":
        target = results["cases"][0]
    target["misspelled_field"] = "must not silently use defaults"
    with pytest.raises(e2e.CoverageError, match="unknown fields"):
        if where in {"results", "case"}:
            e2e.audit(model, results, tmp_path)
        else:
            e2e.plan(model, tmp_path)


@pytest.mark.parametrize("finished", ["yesterday", "2026-09-28T00:00:00Z", "2026-09-29T00:01:00"])
def test_invalid_or_reversed_run_timestamps(model, tmp_path, finished):
    results = result_for(model, tmp_path)
    results["finished_at"] = finished
    with pytest.raises(e2e.CoverageError):
        e2e.audit(model, results, tmp_path)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_json_numbers_rejected(tmp_path, constant):
    path = tmp_path / "bad.json"
    path.write_text('{"value":' + constant + '}', encoding="utf-8")
    with pytest.raises(e2e.CoverageError, match="invalid JSON constant"):
        e2e.load(path)


def test_symlink_evidence_cannot_escape_project(model, tmp_path):
    results = result_for(model, tmp_path)
    outside = tmp_path.parent / (tmp_path.name + "-external.txt")
    outside.write_text("external evidence", encoding="utf-8")
    link = tmp_path / "outside-link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks is not permitted on this platform")
    results["evidence"] = [{"path": "outside-link", "sha256": hashlib.sha256(outside.read_bytes()).hexdigest()}]
    with pytest.raises(e2e.CoverageError, match="escapes root"):
        e2e.audit(model, results, tmp_path)
