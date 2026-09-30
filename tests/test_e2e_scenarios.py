"""Scenario-design and trace checks; all observations here are synthetic fixtures.

These tests exercise the checker, not a GUI, a visual model, or a user product.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/shared/e2e_scenarios.py"
SPEC = importlib.util.spec_from_file_location("e2e_scenarios", HELPER)
e2e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e2e)


def receipt(root, path, content):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


@pytest.fixture
def book(tmp_path):
    source = receipt(tmp_path, "fixture-contract.md", "Synthetic rename contract. Preserve unrelated files; read back outcomes.")
    applicable = {"happy_path", "external_mutation", "event_order", "persistence_consistency", "visual_interaction"}
    operation = {
        "id": "rename", "title": "Rename a test file", "entrypoint": "Fixture file manager > Rename",
        "source_refs": [source["path"]], "assumptions": ["the original object still exists"],
        "side_effects": True,
        "dimensions": {d: {"disposition": "applicable" if d in applicable else "not_applicable",
                           "reason": "Synthetic checker fixture; not a real product coverage decision.",
                           "source_refs": [source["path"]]} for d in e2e.DIMENSIONS},
        "checkpoints": [{"id": "dialog-open", "observation": "Rename dialog is visible"},
                        {"id": "before-confirm", "observation": "New name entered; confirm not activated"}],
        "events": [{"id": "deleted", "change": "Delete the original test file externally",
                    "checkpoints": ["dialog-open", "before-confirm"]}],
    }
    scenario = {
        "id": "rename-normal", "operation": "rename", "title": "Normal rename",
        "dimensions": ["happy_path", "persistence_consistency", "visual_interaction"],
        "requirements": ["R-identity"], "technique": ["state-transition"], "priority": "high",
        "preconditions": ["Create A.txt with known content in an isolated temporary directory"],
        "steps": [{"id": "open", "actor": "visual-model", "action": "Open rename dialog", "observe": "A.txt selected"},
                  {"id": "confirm", "actor": "visual-model", "action": "Enter B.txt and confirm", "observe": "Observe actual response"}],
        "perturbations": [],
        "oracles": [{"id": "ui", "channel": "visual", "assertion": "UI matches operation outcome", "check": "Inspect current screenshot"},
                    {"id": "storage", "channel": "filesystem", "assertion": "Original content and unrelated files preserved",
                     "check": "Read paths and content through an independent filesystem tool"}],
        "execution": "visual", "cleanup": ["Remove only the temporary fixture directory"],
        "safety": ["Never target user files"],
    }
    scenarios = [scenario]
    for checkpoint in operation["checkpoints"]:
        row = deepcopy(scenario)
        row["id"] = "rename-deleted-" + checkpoint["id"]
        row["title"] = "Original deleted at " + checkpoint["id"]
        row["dimensions"] = ["external_mutation", "event_order", "persistence_consistency", "visual_interaction"]
        row["technique"] = ["error-guessing", "state-transition", "event-sequence"]
        row["steps"].insert(1, {"id": "inject", "actor": "fixture", "action": "Delete A.txt at the selected checkpoint",
                                "observe": "Independently confirm A.txt is absent before continuing"})
        row["perturbations"] = [{"event": "deleted", "checkpoint": checkpoint["id"], "step_id": "inject"}]
        scenarios.append(row)
    return {"schema_version": 1, "scope": "Synthetic file rename checker fixture", "source_revision": "fixture-v1",
            "sources": [source], "requirements": [{"id": "R-identity", "source_ref": source["path"],
                                                    "assertion": "Do not mutate an unrelated object"}],
            "operations": [operation], "scenarios": scenarios, "discovery_gaps": [], "exclusions": []}


def trace_for(book, root):
    # Text marked as visual below is deliberately parser metadata, not a screenshot.
    # The checker binds declared kinds and hashes, not actual model perception.
    evidence = []
    for identity, kind in [("screen", "visual"), ("storage", "filesystem"), ("actions", "action_log")]:
        evidence.append({"id": identity, "kind": kind, "captured_at": "2026-09-29T01:00:30Z",
                         **receipt(root, f"test-results/{identity}.txt", f"SYNTHETIC {kind}; no GUI executed")})
    results = []
    for scenario in book["scenarios"]:
        results.append({"id": scenario["id"], "attempts": [{
            "status": "passed",
            "steps": [{"id": step["id"], "observation": "Synthetic step observation", "evidence_ids": ["actions"]}
                      for step in scenario["steps"]],
            "oracles": [{"id": oracle["id"], "outcome": "passed", "observation": "Synthetic oracle observation",
                         "evidence_ids": ["screen" if oracle["channel"] == "visual" else "storage"]}
                        for oracle in scenario["oracles"]],
            "cleanup": {"status": "passed", "observation": "Synthetic cleanup verified", "evidence_ids": ["storage"]},
        }]})
    return {"schema_version": 1, "book_sha256": e2e.sha(book), "source_revision": book["source_revision"],
            "run_id": "synthetic-checker-test", "target": "fixture-not-a-product",
            "executor": {"kind": "visual-model", "name": "synthetic-fixture-no-model-executed"},
            "started_at": "2026-09-29T01:00:00Z", "finished_at": "2026-09-29T01:01:00Z",
            "evidence": evidence, "results": results}


def test_valid_design_is_only_planning_not_execution(book, tmp_path):
    report = e2e.check(book, tmp_path)
    assert report["claim"] == "scenario_design_ready"
    assert report["scenario_count"] == 3
    assert len(report["timing_obligations"]) == 2
    assert "not executed tests" in report["qualification"]


def test_timing_expansion_preserves_each_checkpoint(book, tmp_path):
    report = e2e.check(book, tmp_path)
    assert {(o["event"], o["checkpoint"]) for o in report["timing_obligations"]} == {
        ("deleted", "dialog-open"), ("deleted", "before-confirm")}
    changed = deepcopy(book)
    changed["operations"][0]["events"][0]["checkpoints"].reverse()
    assert e2e.check(changed, tmp_path)["timing_obligations"] == report["timing_obligations"]


def test_same_event_at_one_time_does_not_cover_other_time(book, tmp_path):
    book["scenarios"].pop()
    report = e2e.check(book, tmp_path)
    assert report["claim"] == "design_incomplete"
    assert [g["checkpoint"] for g in report["gaps"] if g["kind"] == "timing"] == ["before-confirm"]


def test_renamed_event_is_not_covered_by_deleted_event(book, tmp_path):
    book["operations"][0]["events"].append({"id": "renamed", "change": "Another actor renames original",
                                          "checkpoints": ["dialog-open", "before-confirm"]})
    gaps = e2e.check(book, tmp_path)["gaps"]
    assert len([g for g in gaps if g["kind"] == "timing" and g["event"] == "renamed"]) == 2


def test_unreviewed_dimension_cannot_disappear(book, tmp_path):
    del book["operations"][0]["dimensions"]["input_boundaries"]
    with pytest.raises(e2e.ScenarioError, match="missing dimension"):
        e2e.check(book, tmp_path)


def test_applicable_dimension_needs_a_case(book, tmp_path):
    book["operations"][0]["dimensions"]["input_boundaries"]["disposition"] = "applicable"
    assert {"kind": "dimension", "operation": "rename", "dimension": "input_boundaries"} in e2e.check(book, tmp_path)["gaps"]


@pytest.mark.parametrize("field", ["reason", "source_refs"])
def test_not_applicable_needs_reason_and_bound_evidence(book, tmp_path, field):
    book["operations"][0]["dimensions"]["input_boundaries"][field] = "" if field == "reason" else []
    with pytest.raises(e2e.ScenarioError):
        e2e.check(book, tmp_path)


def test_unmapped_requirement_remains_a_gap(book, tmp_path):
    book["requirements"].append({"id": "R-extra", "source_ref": "fixture-contract.md", "assertion": "Not forgotten"})
    assert {"kind": "requirement", "id": "R-extra"} in e2e.check(book, tmp_path)["gaps"]


def test_side_effects_cannot_be_proven_with_screenshots_only(book, tmp_path):
    book["scenarios"][0]["oracles"] = book["scenarios"][0]["oracles"][:1]
    with pytest.raises(e2e.ScenarioError, match="independent readback"):
        e2e.check(book, tmp_path)


def test_visual_route_needs_a_visual_oracle(book, tmp_path):
    book["scenarios"][0]["oracles"] = book["scenarios"][0]["oracles"][1:]
    with pytest.raises(e2e.ScenarioError, match="visual oracle"):
        e2e.check(book, tmp_path)


@pytest.mark.parametrize("mutation", ["unknown_checkpoint", "missing_step", "duplicate", "not_applicable"])
def test_invalid_perturbation_is_rejected(book, tmp_path, mutation):
    row = book["scenarios"][1]
    if mutation == "unknown_checkpoint":
        row["perturbations"][0]["checkpoint"] = "imagined"
    elif mutation == "missing_step":
        row["perturbations"][0]["step_id"] = "missing"
    elif mutation == "duplicate":
        row["perturbations"].append(deepcopy(row["perturbations"][0]))
    else:
        book["operations"][0]["dimensions"]["external_mutation"]["disposition"] = "not_applicable"
    with pytest.raises(e2e.ScenarioError):
        e2e.check(book, tmp_path)


def test_empty_scenario_book_returns_design_gaps(book, tmp_path):
    book["scenarios"] = []
    assert e2e.check(book, tmp_path)["claim"] == "design_incomplete"


def test_discovery_gaps_and_exclusions_are_not_hidden(book, tmp_path):
    book["discovery_gaps"] = [{"id": "G1", "description": "Uninspected sync behavior", "owner": "agent", "next_action": "Inspect sync entrypoint"}]
    book["exclusions"] = [{"scope": "production", "reason": "isolated data only", "owner": "project-owner"}]
    report = e2e.check(book, tmp_path)
    assert report["claim"] == "design_incomplete"
    assert report["exclusions"] == book["exclusions"]
    assert any(g["kind"] == "discovery" for g in report["gaps"])


@pytest.mark.parametrize("field", ["operations", "requirements", "scenarios"])
def test_duplicate_ids_rejected(book, tmp_path, field):
    book[field].append(deepcopy(book[field][0]))
    with pytest.raises(e2e.ScenarioError, match="duplicate"):
        e2e.check(book, tmp_path)


@pytest.mark.parametrize("where", ["book", "operation", "scenario", "oracle", "step", "dimension"])
def test_unknown_fields_rejected(book, tmp_path, where):
    target = {"book": book, "operation": book["operations"][0], "scenario": book["scenarios"][0],
              "oracle": book["scenarios"][0]["oracles"][0], "step": book["scenarios"][0]["steps"][0],
              "dimension": book["operations"][0]["dimensions"]["happy_path"]}[where]
    target["typo"] = True
    with pytest.raises(e2e.ScenarioError, match="unknown fields"):
        e2e.check(book, tmp_path)


def test_changed_source_is_stale(book, tmp_path):
    (tmp_path / "fixture-contract.md").write_text("changed")
    with pytest.raises(e2e.ScenarioError, match="stale source"):
        e2e.check(book, tmp_path)


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:/file", "folder\\file", "./fixture-contract.md"])
def test_unsafe_or_noncanonical_paths_rejected(book, tmp_path, path):
    book["sources"][0]["path"] = path
    with pytest.raises(e2e.ScenarioError, match="unsafe"):
        e2e.check(book, tmp_path)


def test_symlink_escape_rejected(book, tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.write_text("outside")
    try:
        (tmp_path / "link").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    try:
        book["sources"][0]["path"] = "link"
        with pytest.raises(e2e.ScenarioError, match="escaping"):
            e2e.check(book, tmp_path)
    finally:
        outside.unlink()


def test_visual_trace_is_not_forced_into_pytest_or_playwright(book, tmp_path):
    report = e2e.audit(book, trace_for(book, tmp_path), tmp_path)
    assert report["claim"] == "evidence_complete_against_declared_scenarios"
    assert report["statuses"]["passed"] == 3
    assert "no attestation" in report["qualification"]


@pytest.mark.parametrize("status", ["failed", "blocked", "skipped", "not_run"])
def test_nonpass_never_closes_trace(book, tmp_path, status):
    trace = trace_for(book, tmp_path)
    trace["results"][0]["attempts"] = [{"status": status, "reason": "Concrete synthetic failure"}]
    report = e2e.audit(book, trace, tmp_path)
    assert report["claim"] == "incomplete"
    assert report["statuses"][status] == 1


def test_missing_scenario_result_is_not_run(book, tmp_path):
    trace = trace_for(book, tmp_path)
    trace["results"].pop()
    report = e2e.audit(book, trace, tmp_path)
    assert report["statuses"]["not_run"] == 1
    assert report["claim"] == "incomplete"


def test_failed_then_passed_is_flaky(book, tmp_path):
    trace = trace_for(book, tmp_path)
    trace["results"][0]["attempts"].insert(0, {"status": "failed", "reason": "Original failure retained"})
    report = e2e.audit(book, trace, tmp_path)
    assert report["statuses"]["flaky"] == 1
    assert report["claim"] == "incomplete"


@pytest.mark.parametrize("part", ["steps", "oracles"])
def test_pass_requires_all_step_and_oracle_observations(book, tmp_path, part):
    trace = trace_for(book, tmp_path)
    trace["results"][1]["attempts"][0][part].pop()
    with pytest.raises(e2e.ScenarioError, match="observations"):
        e2e.audit(book, trace, tmp_path)


def test_screenshot_cannot_substitute_for_filesystem_evidence(book, tmp_path):
    trace = trace_for(book, tmp_path)
    trace["results"][0]["attempts"][0]["oracles"][1]["evidence_ids"] = ["screen"]
    with pytest.raises(e2e.ScenarioError, match="matching evidence channel"):
        e2e.audit(book, trace, tmp_path)


@pytest.mark.parametrize("status", ["failed", "blocked", "skipped"])
def test_failed_cleanup_prevents_pass(book, tmp_path, status):
    trace = trace_for(book, tmp_path)
    trace["results"][0]["attempts"][0]["cleanup"]["status"] = status
    with pytest.raises(e2e.ScenarioError, match="cleanup"):
        e2e.audit(book, trace, tmp_path)


def test_unobserved_oracle_is_not_a_pass(book, tmp_path):
    trace = trace_for(book, tmp_path)
    trace["results"][0]["attempts"][0]["oracles"][0]["outcome"] = "unobserved"
    with pytest.raises(e2e.ScenarioError, match="unverified oracle"):
        e2e.audit(book, trace, tmp_path)


@pytest.mark.parametrize("part", ["book_sha256", "source_revision"])
def test_stale_trace_binding_rejected(book, tmp_path, part):
    trace = trace_for(book, tmp_path)
    trace[part] = "stale"
    with pytest.raises(e2e.ScenarioError, match="stale trace"):
        e2e.audit(book, trace, tmp_path)


def test_evidence_bytes_are_checked(book, tmp_path):
    trace = trace_for(book, tmp_path)
    (tmp_path / "test-results/screen.txt").write_text("tampered")
    with pytest.raises(e2e.ScenarioError, match="stale evidence"):
        e2e.audit(book, trace, tmp_path)


@pytest.mark.parametrize("timestamp", ["2020-01-01T00:00:00Z", "2030-01-01T00:00:00Z", "2026-09-29T01:00:30"])
def test_outdated_or_naive_capture_time_rejected(book, tmp_path, timestamp):
    trace = trace_for(book, tmp_path)
    trace["evidence"][0]["captured_at"] = timestamp
    with pytest.raises(e2e.ScenarioError):
        e2e.audit(book, trace, tmp_path)


def test_all_observed_passes_do_not_erase_discovery_gaps(book, tmp_path):
    book["discovery_gaps"] = [{"id": "G1", "description": "Uninspected native integration", "owner": "agent", "next_action": "Inspect it"}]
    assert e2e.audit(book, trace_for(book, tmp_path), tmp_path)["claim"] == "incomplete"


def test_duplicate_trace_result_is_not_a_retry(book, tmp_path):
    trace = trace_for(book, tmp_path)
    trace["results"].append(deepcopy(trace["results"][0]))
    with pytest.raises(e2e.ScenarioError, match="duplicate scenario"):
        e2e.audit(book, trace, tmp_path)


def test_duplicate_json_keys_are_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"scope":"one", "scope":"two"}')
    with pytest.raises(e2e.ScenarioError, match="duplicate JSON"):
        e2e.load(path)


def test_cli_design_and_trace_exit_codes(book, tmp_path):
    (tmp_path / "book.json").write_text(json.dumps(book))
    trace = trace_for(book, tmp_path)
    (tmp_path / "trace.json").write_text(json.dumps(trace))
    prefix = [sys.executable, str(HELPER)]
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    for mode in ("derive", "check", "audit"):
        argv = prefix + [mode, "book.json", "--root", str(tmp_path)]
        if mode == "audit":
            argv += ["--trace", "trace.json"]
        run = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout)["claim"] != "passed"
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")) == before
    book["scenarios"] = []
    (tmp_path / "book.json").write_text(json.dumps(book))
    assert subprocess.run(prefix + ["check", "book.json", "--root", str(tmp_path)], capture_output=True).returncode == 1
    assert subprocess.run(prefix + ["audit", "book.json", "--root", str(tmp_path), "--trace", "trace.json"], capture_output=True).returncode == 2


@pytest.mark.parametrize("args", [["check"], ["catalog", "unexpected.json"], ["audit", "book.json"], ["derive", "book.json", "--trace", "trace.json"]])
def test_cli_invalid_modes_fail_closed(args):
    assert subprocess.run([sys.executable, str(HELPER), *args], capture_output=True, timeout=10).returncode == 2


def test_published_schemas_match_valid_book_and_trace(book, tmp_path):
    from jsonschema import Draft202012Validator
    schemas = e2e.schemas()
    for kind, instance in [("book", book), ("trace", trace_for(book, tmp_path))]:
        Draft202012Validator.check_schema(schemas[kind])
        Draft202012Validator(schemas[kind]).validate(instance)
    assert set(schemas["book"]["properties"]) == set(book)
    assert set(schemas["book"]["properties"]["operations"]["items"]["properties"]) == set(book["operations"][0])


def test_schema_is_discoverable_without_a_project():
    result = subprocess.run([sys.executable, str(HELPER), "schema"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert set(json.loads(result.stdout)) == {"claim", "book", "trace"}


def test_one_mutation_step_cannot_cover_two_different_checkpoints(book, tmp_path):
    scenario = book["scenarios"][1]
    scenario["perturbations"].append({"event": "deleted", "checkpoint": "before-confirm", "step_id": "inject"})
    with pytest.raises(e2e.ScenarioError, match="own perturbation step"):
        e2e.check(book, tmp_path)


def test_observed_actions_must_preserve_planned_event_order(book, tmp_path):
    trace = trace_for(book, tmp_path)
    trace["results"][1]["attempts"][0]["steps"].reverse()
    with pytest.raises(e2e.ScenarioError, match="observed step order"):
        e2e.audit(book, trace, tmp_path)
