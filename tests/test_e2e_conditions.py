"""Condition-level accounting regressions; all traces are synthetic, not GUI proof."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("e2e_legacy_condition_fixtures", ROOT / "tests/test_e2e_scenarios.py")
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
e2e = legacy.e2e
book = legacy.book


@pytest.fixture
def detailed(book):
    book["schema_version"] = 2
    book["conditions"] = []
    for dimension, oracle in (("happy_path", "ui"), ("persistence_consistency", "storage"), ("visual_interaction", "ui")):
        assertion = next(o["assertion"] for o in book["scenarios"][0]["oracles"] if o["id"] == oracle)
        book["conditions"].append({
            "id": "C-" + dimension, "operation": "rename", "dimension": dimension,
            "kind": "example", "title": "Synthetic " + dimension,
            "source_refs": ["fixture-contract.md"], "requirements": ["R-identity"],
            "variants": [{"id": "main", "input": "Synthetic fixture stimulus", "expected": assertion}],
        })
    for scenario in book["scenarios"]:
        scenario["condition_bindings"] = [
            {"condition": "C-" + dimension, "variant": "main", "step_ids": ["confirm"],
             "oracle_ids": ["storage" if dimension == "persistence_consistency" else "ui"]}
            for dimension in scenario["dimensions"] if dimension not in {"external_mutation", "event_order"}
        ]
    book["operations"][0]["dimensions"]["input_boundaries"]["disposition"] = "applicable"
    book["conditions"].append({
        "id": "C-length", "operation": "rename", "dimension": "input_boundaries", "kind": "boundary",
        "title": "Synthetic maximum filename length, not a platform rule",
        "source_refs": ["fixture-contract.md"], "requirements": ["R-identity"],
        "boundary": {"limit": 32, "unit": "Unicode code points",
                     "expectations": {"below": "Accept a 31-point name", "at": "Accept a 32-point name",
                                      "above": "Reject a 33-point name without changing files"}},
    })
    for variant, length in (("below", 31), ("at", 32), ("above", 33)):
        scenario = deepcopy(book["scenarios"][0])
        scenario.update(id="length-" + variant, title="Synthetic " + variant, dimensions=["input_boundaries"])
        scenario["steps"][-1]["action"] = f"Enter a name of {length} Unicode code points; confirm"
        scenario["oracles"][0]["assertion"] = book["conditions"][-1]["boundary"]["expectations"][variant]
        scenario["condition_bindings"] = [{"condition": "C-length", "variant": variant,
                                           "step_ids": ["confirm"], "oracle_ids": ["ui"]}]
        book["scenarios"].append(scenario)
    return book


def test_all_boundary_points_are_derived(detailed, tmp_path):
    report = e2e.check(detailed, tmp_path)
    assert report["claim"] == "scenario_design_ready"
    assert len(report["condition_obligations"]) == 6
    points = {r["variant"]: r["input"] for r in report["condition_obligations"] if r["condition"] == "C-length"}
    assert points == {"below": "31 Unicode code points", "at": "32 Unicode code points", "above": "33 Unicode code points"}
    assert len(report["timing_obligations"]) == 2


def test_missing_at_boundary_is_not_hidden_by_dimension_tags(detailed, tmp_path):
    detailed["scenarios"] = [s for s in detailed["scenarios"] if s["id"] != "length-at"]
    result = e2e.check(detailed, tmp_path)
    assert result["claim"] == "design_incomplete"
    assert not any(g["kind"] == "dimension" for g in result["gaps"])
    assert [(g["condition"], g["variant"]) for g in result["gaps"] if g["kind"] == "condition"] == [("C-length", "at")]


def test_dimension_label_cannot_replace_condition_ledger(detailed, tmp_path):
    detailed["conditions"] = []
    for scenario in detailed["scenarios"]:
        scenario["condition_bindings"] = []
    report = e2e.check(detailed, tmp_path)
    assert report["claim"] == "design_incomplete"
    assert any(g["kind"] == "condition_family" for g in report["gaps"])
    assert any(g["kind"] == "unbound_scenario_dimension" for g in report["gaps"])


def test_ids_stable_under_reordering_but_content_hash_changes(detailed, tmp_path):
    original = e2e.check(detailed, tmp_path)
    detailed["conditions"].reverse()
    detailed["scenarios"].reverse()
    changed = e2e.check(detailed, tmp_path)
    assert changed["condition_obligations"] == original["condition_obligations"]
    assert changed["book_sha256"] != original["book_sha256"]


@pytest.mark.parametrize("kind", ["partition", "state", "rule", "sequence", "example"])
def test_explicit_variant_families_keep_every_member(detailed, tmp_path, kind):
    condition = detailed["conditions"][-1]
    condition.pop("boundary")
    condition["kind"] = kind
    condition["variants"] = [{"id": "one", "input": "First class/state/rule", "expected": "Expected outcome"},
                             {"id": "two", "input": "Second class/state/rule", "expected": "Different outcome"}]
    for scenario in detailed["scenarios"][-3:]:
        scenario["condition_bindings"] = []
    report = e2e.check(detailed, tmp_path)
    assert {g["variant"] for g in report["gaps"] if g["kind"] == "condition"} == {"one", "two"}


@pytest.mark.parametrize("value", [True, 32.0, "32", None, 10**12 + 1, -(10**12) - 1])
def test_boundary_limit_is_a_bounded_discrete_integer(detailed, tmp_path, value):
    detailed["conditions"][-1]["boundary"]["limit"] = value
    with pytest.raises(e2e.ScenarioError, match="boundary.limit"):
        e2e.check(detailed, tmp_path)


@pytest.mark.parametrize("field", ["unit", "expectations", "limit"])
def test_boundary_requires_unit_and_authoritative_oracles(detailed, tmp_path, field):
    del detailed["conditions"][-1]["boundary"][field]
    with pytest.raises(e2e.ScenarioError):
        e2e.check(detailed, tmp_path)


def test_boundary_cannot_omit_an_expected_outcome(detailed, tmp_path):
    del detailed["conditions"][-1]["boundary"]["expectations"]["above"]
    with pytest.raises(e2e.ScenarioError, match="boundary.above"):
        e2e.check(detailed, tmp_path)


def test_boundary_cannot_supply_a_sampled_variant_list(detailed, tmp_path):
    detailed["conditions"][-1]["variants"] = []
    with pytest.raises(e2e.ScenarioError, match="derived"):
        e2e.check(detailed, tmp_path)


@pytest.mark.parametrize("field,value", [("operation", "unknown"), ("dimension", "permissions"),
                                        ("kind", "imagined"), ("source_refs", ["unbound.md"]),
                                        ("requirements", ["R-unknown"]), ("title", " ")])
def test_conditions_require_bound_valid_semantics(detailed, tmp_path, field, value):
    detailed["conditions"][-1][field] = value
    with pytest.raises(e2e.ScenarioError):
        e2e.check(detailed, tmp_path)


@pytest.mark.parametrize("location", ["condition", "boundary", "expectations", "variant", "binding"])
def test_condition_shapes_reject_unknown_fields(detailed, tmp_path, location):
    targets = {"condition": detailed["conditions"][0], "boundary": detailed["conditions"][-1]["boundary"],
               "expectations": detailed["conditions"][-1]["boundary"]["expectations"],
               "variant": detailed["conditions"][0]["variants"][0],
               "binding": detailed["scenarios"][0]["condition_bindings"][0]}
    targets[location]["typo"] = "not silently ignored"
    with pytest.raises(e2e.ScenarioError, match="unknown fields"):
        e2e.check(detailed, tmp_path)


def test_duplicate_condition_and_variant_ids_rejected(detailed, tmp_path):
    changed = deepcopy(detailed)
    changed["conditions"].append(deepcopy(changed["conditions"][0]))
    with pytest.raises(e2e.ScenarioError, match="duplicate"):
        e2e.check(changed, tmp_path)
    detailed["conditions"][0]["variants"] *= 2
    with pytest.raises(e2e.ScenarioError, match="duplicate"):
        e2e.check(detailed, tmp_path)


@pytest.mark.parametrize("field,value", [("condition", "missing"), ("variant", "missing"),
                                        ("step_ids", []), ("step_ids", ["missing"]),
                                        ("step_ids", ["confirm", "open"]), ("oracle_ids", ["missing"])])
def test_bindings_require_real_steps_and_oracles(detailed, tmp_path, field, value):
    detailed["scenarios"][-1]["condition_bindings"][0][field] = value
    with pytest.raises(e2e.ScenarioError):
        e2e.check(detailed, tmp_path)


def test_generic_oracle_cannot_cover_specific_outcome(detailed, tmp_path):
    detailed["scenarios"][-1]["oracles"][0]["assertion"] = "The screen looks fine"
    with pytest.raises(e2e.ScenarioError, match="exact bound oracle"):
        e2e.check(detailed, tmp_path)


def test_same_stimulus_cannot_credit_two_boundary_points(detailed, tmp_path):
    scenario = detailed["scenarios"][-3]
    extra = deepcopy(scenario["oracles"][0])
    extra.update(id="at-oracle", assertion="Accept a 32-point name")
    scenario["oracles"].append(extra)
    scenario["condition_bindings"].append({"condition": "C-length", "variant": "at",
                                          "step_ids": ["confirm"], "oracle_ids": ["at-oracle"]})
    with pytest.raises(e2e.ScenarioError, match="distinct steps and oracles"):
        e2e.check(detailed, tmp_path)


def test_distinct_variant_steps_in_one_long_scenario_are_allowed(detailed, tmp_path):
    below, at = detailed["scenarios"][-3:-1]
    step = deepcopy(at["steps"][-1])
    step["id"] = "at-confirm"
    below["steps"].append(step)
    oracle = deepcopy(at["oracles"][0])
    oracle["id"] = "at-ui"
    below["oracles"].append(oracle)
    below["condition_bindings"].append({"condition": "C-length", "variant": "at",
                                       "step_ids": ["at-confirm"], "oracle_ids": ["at-ui"]})
    detailed["scenarios"].remove(at)
    assert e2e.check(detailed, tmp_path)["claim"] == "scenario_design_ready"


def test_one_scenario_cannot_claim_a_different_operations_condition(detailed, tmp_path):
    extra = deepcopy(detailed["operations"][0])
    extra["id"] = "other"
    detailed["operations"].append(extra)
    detailed["conditions"][-1]["operation"] = "other"
    with pytest.raises(e2e.ScenarioError, match="cross-operation"):
        e2e.check(detailed, tmp_path)


def test_condition_requirement_must_reach_scenario(detailed, tmp_path):
    detailed["requirements"].append({"id": "R-extra", "source_ref": "fixture-contract.md", "assertion": "Extra obligation"})
    detailed["conditions"][-1]["requirements"].append("R-extra")
    with pytest.raises(e2e.ScenarioError, match="requirements missing"):
        e2e.check(detailed, tmp_path)


def test_new_condition_does_not_reuse_old_trace(detailed, tmp_path):
    trace = legacy.trace_for(detailed, tmp_path)
    detailed["conditions"][-1]["title"] = "A new frozen interpretation"
    with pytest.raises(e2e.ScenarioError, match="stale trace"):
        e2e.audit(detailed, trace, tmp_path)


@pytest.mark.parametrize("status", ["failed", "blocked", "skipped", "not_run", "flaky", "missing"])
def test_execution_denominator_keeps_each_unverified_condition(detailed, tmp_path, status):
    trace = legacy.trace_for(detailed, tmp_path)
    row = next(r for r in trace["results"] if r["id"] == "length-at")
    if status == "missing":
        trace["results"].remove(row)
    elif status == "flaky":
        row["attempts"].insert(0, {"status": "failed", "reason": "Synthetic first failure"})
    else:
        row["attempts"] = [{"status": status, "reason": "Synthetic unverified outcome"}]
    report = e2e.audit(detailed, trace, tmp_path)
    assert report["claim"] == "incomplete"
    assert report["condition_coverage"]["total"] == 6
    assert report["condition_coverage"]["passed"] == 5
    assert [(r["condition"], r["variant"]) for r in report["condition_coverage"]["missing"]] == [("C-length", "at")]


def test_timing_execution_is_reported_independently(detailed, tmp_path):
    trace = legacy.trace_for(detailed, tmp_path)
    trace["results"] = [r for r in trace["results"] if r["id"] != "rename-deleted-before-confirm"]
    report = e2e.audit(detailed, trace, tmp_path)
    assert report["condition_coverage"]["passed"] == 6
    assert report["timing_coverage"]["passed"] == 1
    assert report["timing_coverage"]["missing"][0]["checkpoint"] == "before-confirm"
    assert report["claim"] == "incomplete"


def test_schemas_cover_both_versions_without_changing_legacy_defaults(detailed, tmp_path):
    schema = e2e.schemas(2)
    for key, value in (("book", detailed), ("trace", legacy.trace_for(detailed, tmp_path))):
        Draft202012Validator.check_schema(schema[key])
        Draft202012Validator(schema[key]).validate(value)
    assert e2e.schemas()["book"]["properties"]["schema_version"]["const"] == 1
    assert schema["trace"]["properties"]["schema_version"]["const"] == 1


def test_legacy_version_cannot_smuggle_condition_fields(detailed, tmp_path):
    detailed["schema_version"] = 1
    with pytest.raises(e2e.ScenarioError, match="unknown fields"):
        e2e.check(detailed, tmp_path)


def test_check_does_not_mutate_the_book(detailed, tmp_path):
    original = deepcopy(detailed)
    e2e.check(detailed, tmp_path)
    assert detailed == original


def test_expansion_fails_instead_of_silently_sampling(detailed, tmp_path, monkeypatch):
    monkeypatch.setattr(e2e, "MAX_RECORDS", 4)
    # Check the bounded expansion directly; base structure independently caps arrays.
    with pytest.raises(e2e.ScenarioError, match="condition obligation budget"):
        e2e.condition_coverage(detailed, {o["id"]: o for o in detailed["operations"]}, {})


@pytest.mark.parametrize("mode", ["check", "derive", "audit"])
def test_cli_require_v2_preserves_legacy_data(detailed, tmp_path, mode):
    path = tmp_path / "book.json"
    path.write_text(json.dumps(detailed), encoding="utf-8")
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(legacy.trace_for(detailed, tmp_path)), encoding="utf-8")
    argv = [sys.executable, str(legacy.HELPER), mode, "book.json", "--root", str(tmp_path), "--require-v2"]
    if mode == "audit":
        argv += ["--trace", "trace.json"]
    run = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    detailed["schema_version"] = 1
    del detailed["conditions"]
    for scenario in detailed["scenarios"]:
        del scenario["condition_bindings"]
    old = json.dumps(detailed)
    path.write_text(old, encoding="utf-8")
    run = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    assert run.returncode == 2
    assert "requires schema_version 2" in run.stderr
    assert path.read_text(encoding="utf-8") == old


@pytest.mark.parametrize("argv", [["catalog", "--require-v2"], ["catalog", "--schema-version", "2"],
                                  ["schema", "--schema-version", "3"], ["schema", "--require-v2"]])
def test_irrelevant_flags_are_not_silently_ignored(argv):
    result = subprocess.run([sys.executable, str(legacy.HELPER), *argv], capture_output=True, timeout=10)
    assert result.returncode == 2


@pytest.mark.parametrize("directory", ["plain", "project with spaces"])
def test_copied_installed_helper_executes_v2_without_source_tree_imports(detailed, tmp_path, directory):
    import shutil
    target = tmp_path / directory / ".specify/scripts/shared/e2e_scenarios.py"
    target.parent.mkdir(parents=True)
    shutil.copyfile(legacy.HELPER, target)
    (tmp_path / "book.json").write_text(json.dumps(detailed), encoding="utf-8")
    command = [sys.executable, str(target)]
    for args in (["schema", "--schema-version", "2"], ["check", "book.json", "--root", str(tmp_path), "--require-v2"]):
        run = subprocess.run(command + args, cwd=target.parent, capture_output=True, text=True, timeout=10)
        assert run.returncode == 0, run.stderr
        result = json.loads(run.stdout)
        if args[0] == "schema":
            assert result["book"]["properties"]["schema_version"]["const"] == 2
        else:
            assert len(result["condition_obligations"]) == 6


@pytest.mark.parametrize("path", ["templates/commands/e2e.md", "templates/advanced-skills/spx-e2e/SKILL.md"])
def test_both_workflow_sources_require_condition_gates(path):
    content = (ROOT / path).read_text(encoding="utf-8")
    assert "schema --schema-version 2" in content
    for line in content.splitlines():
        if any("e2e_scenarios.py " + mode in line for mode in ("derive", "check", "audit")):
            assert "--require-v2" in line, line
    for token in ("condition_bindings", "step_ids", "oracle_ids", "condition_coverage", "timing_coverage"):
        assert token in content
    assert "not_run" in content and "flaky" in content
    assert "review -> accept" in content
