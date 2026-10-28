"""Indexed design accounting versus the original full-rescan joins.

Synthetic books test declared accounting, not real product or visual coverage.
"""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
import random

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("condition_index_fixtures", ROOT / "tests/test_e2e_conditions.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
e2e = fixtures.e2e
book = fixtures.book
detailed = fixtures.detailed


def rescanning_check(book, root):
    """Original check() joins, kept independent of the indexed join implementation."""
    operations, requirements, scenarios, obligations = e2e.structure(book, root)
    gaps = []
    for identity, operation in operations.items():
        related = [s for s in scenarios.values() if s["operation"] == identity]
        covered = {d for s in related for d in s["dimensions"]}
        for dimension, decision in operation["dimensions"].items():
            if decision["disposition"] == "applicable" and dimension not in covered:
                gaps.append({"kind": "dimension", "operation": identity, "dimension": dimension})
    mapped = {r for s in scenarios.values() for r in s["requirements"]}
    gaps.extend({"kind": "requirement", "id": r} for r in sorted(set(requirements) - mapped))
    for obligation in obligations:
        matches = [s["id"] for s in scenarios.values() if s["operation"] == obligation["operation"]
                   and any(p["event"] == obligation["event"] and p["checkpoint"] == obligation["checkpoint"]
                           for p in s["perturbations"])]
        obligation["scenario_ids"] = sorted(matches)
        if not matches:
            gaps.append({"kind": "timing", **obligation})
    gaps.extend({"kind": "discovery", **gap} for gap in book["discovery_gaps"])
    conditions, condition_gaps = e2e.condition_coverage(book, operations, scenarios)
    gaps.extend(condition_gaps)
    extra = {"condition_obligations": conditions} if book["schema_version"] == 2 else {}
    return {**extra, "schema_version": book["schema_version"],
            "claim": "scenario_design_ready" if not gaps else "design_incomplete",
            "book_sha256": e2e.sha(book), "scenario_count": len(scenarios),
            "timing_obligations": obligations, "gaps": gaps, "exclusions": book["exclusions"],
            "qualification": "Declared design accounting only: not executed tests, discovery completeness, semantic oracle correctness, visual acceptance, or release safety."}


def expanded(book, copies, seed=0, remove=True):
    """Reuse local timing IDs across operations to challenge accidental cross-credit."""
    rng = random.Random(seed)
    result = deepcopy(book)
    result["operations"], result["scenarios"] = [], []
    if book["schema_version"] == 2:
        result["conditions"] = []
    for i in range(copies):
        operation = deepcopy(book["operations"][0])
        op = operation["id"] = f"op-{i}-文"
        rng.shuffle(operation["checkpoints"])
        rng.shuffle(operation["events"])
        result["operations"].append(operation)
        for original in book.get("conditions", []):
            condition = deepcopy(original)
            condition["id"] = op + "/" + original["id"]
            condition["operation"] = op
            result["conditions"].append(condition)
        for original in book["scenarios"]:
            if remove and rng.randrange(4) == 0:
                continue
            row = deepcopy(original)
            row.update(id=op + "/" + original["id"], operation=op)
            for binding in row.get("condition_bindings", []):
                binding["condition"] = op + "/" + binding["condition"]
            result["scenarios"].append(row)
    rng.shuffle(result["operations"])
    rng.shuffle(result["scenarios"])
    if "conditions" in result:
        rng.shuffle(result["conditions"])
    if remove and seed % 3 == 0:
        result["discovery_gaps"] = [{"id": "unread", "description": "Synthetic undiscovered surface",
                                     "owner": "fixture", "next_action": "Keep the discovery gap"}]
    return result


@pytest.mark.parametrize("seed", range(64))
@pytest.mark.parametrize("version", [1, 2])
def test_exact_report_and_gap_order_match_rescanning(detailed, tmp_path, seed, version):
    source = deepcopy(detailed)
    if version == 1:
        source["schema_version"] = 1
        del source["conditions"]
        for row in source["scenarios"]:
            del row["condition_bindings"]
    model = expanded(source, 1 + seed % 7, seed)
    before = deepcopy(model)
    assert e2e.check(model, tmp_path) == rescanning_check(model, tmp_path)
    assert model == before


def test_same_event_ids_do_not_credit_another_operation(detailed, tmp_path):
    model = expanded(detailed, 2, remove=False)
    model["scenarios"] = [s for s in model["scenarios"]
                          if not (s["operation"] == "op-1-文" and s["perturbations"])]
    report = e2e.check(model, tmp_path)
    timing = report["timing_obligations"]
    assert len(timing) == 4
    assert all(row["scenario_ids"] for row in timing if row["operation"] == "op-0-文")
    assert all(not row["scenario_ids"] for row in timing if row["operation"] == "op-1-文")
    assert len([gap for gap in report["gaps"] if gap["kind"] == "timing"]) == 2


def test_unknown_event_at_known_other_operation_is_rejected(detailed, tmp_path):
    model = expanded(detailed, 2, remove=False)
    op = next(o for o in model["operations"] if o["id"] == "op-1-文")
    op["events"][0]["id"] = "different-event"
    with pytest.raises(e2e.ScenarioError, match="unknown/duplicate timing obligation"):
        e2e.check(model, tmp_path)


@pytest.mark.parametrize("count", [10, 100])
def test_timing_join_has_bounded_perturbation_traversals(book, tmp_path, count):
    op = book["operations"][0]
    template = deepcopy(book["scenarios"][1])
    op["events"] = [{"id": f"event-{i}", "change": "Synthetic change",
                     "checkpoints": ["dialog-open"]} for i in range(count)]
    book["scenarios"] = [book["scenarios"][0]]
    visits = Counter()
    class Counted(list):
        def __iter__(self):
            visits["iterations"] += 1
            return super().__iter__()
    for i in range(count):
        row = deepcopy(template)
        row["id"] = f"scenario-{i}"
        row["perturbations"] = Counted([dict(event=f"event-{i}", checkpoint="dialog-open", step_id="inject")])
        book["scenarios"].append(row)
    report = e2e.check(book, tmp_path)
    assert len(report["timing_obligations"]) == count
    assert all(len(row["scenario_ids"]) == 1 for row in report["timing_obligations"])
    # Structural validation, one indexed join and JSON hashing. No clock threshold.
    assert visits["iterations"] <= 4 * count


def test_empty_book_preserves_all_gaps(detailed, tmp_path):
    detailed["scenarios"] = []
    assert e2e.check(detailed, tmp_path) == rescanning_check(detailed, tmp_path)


def test_bound_timing_budget_still_refuses_expansion(book, tmp_path, monkeypatch):
    book["operations"][0]["events"] *= 2
    book["operations"][0]["events"][1] = dict(book["operations"][0]["events"][1], id="other")
    monkeypatch.setattr(e2e, "MAX_RECORDS", 3)
    with pytest.raises(e2e.ScenarioError, match="timing obligation budget"):
        e2e.check(book, tmp_path)


@pytest.mark.parametrize("status", ["passed", "failed", "blocked", "skipped", "not_run", "flaky", "absent"])
def test_audit_retains_exact_status_and_condition_denominators(detailed, tmp_path, monkeypatch, status):
    model = expanded(detailed, 3, 4, remove=False)
    trace = fixtures.legacy.trace_for(model, tmp_path)
    if status == "absent":
        trace["results"].pop()
    elif status == "flaky":
        trace["results"][-1]["attempts"].insert(0, {"status": "failed", "reason": "Synthetic first failure"})
    elif status != "passed":
        trace["results"][-1]["attempts"] = [{"status": status, "reason": "Synthetic outcome"}]
    actual = e2e.audit(model, trace, tmp_path)
    with monkeypatch.context() as context:
        context.setattr(e2e, "check", rescanning_check)
        expected = e2e.audit(model, trace, tmp_path)
    assert actual == expected
    assert sum(actual["statuses"].values()) == len(model["scenarios"])


@pytest.mark.parametrize("action", ["check", "audit"])
def test_benchmark_rejects_changed_or_nondeterministic_output(tmp_path, monkeypatch, action):
    from types import SimpleNamespace
    path = ROOT / "tools/workflow-quality/benchmark_e2e_scenarios.py"
    spec = importlib.util.spec_from_file_location("scenario_index_benchmark", path)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    calls = Counter()
    def wrong(*args):
        calls[action] += 1
        result = getattr(e2e, action)(*args)
        if calls[action] > 1:
            result["unexpected"] = True
        return result
    proxy = SimpleNamespace(check=e2e.check, audit=e2e.audit)
    setattr(proxy, action, wrong)
    monkeypatch.setattr(benchmark, "module", lambda path, name: e2e if name.endswith("baseline") else proxy)
    with pytest.raises(ValueError, match="changed output or input"):
        benchmark.benchmark(Path(e2e.__file__), Path(e2e.__file__), repeats=2)
