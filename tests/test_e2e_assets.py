"""Ordinary E2E asset refusal/recovery checks; fixture traces are synthetic.

Real desktop controls are produced separately by e2e_strength_probe.py; these
fixtures do not establish UI execution, model perception or semantic discovery.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "scripts/shared"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


scenario = module("e2e_scenarios", SHARED / "e2e_scenarios.py")
assets = module("e2e_assets", SHARED / "e2e_assets.py")
fixtures = module("e2e_asset_condition_fixtures", ROOT / "tests/test_e2e_conditions.py")
book = fixtures.book
detailed = fixtures.detailed


def write(root, name, value):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def prepared(detailed, tmp_path):
    intent = {"schema_version": 1, "scope": "Synthetic UI/effect interaction, not discovery proof",
              "risks": [{"id": "RISK-effect", "operation": "rename", "requirements": ["R-identity"],
                         "source_refs": ["fixture-contract.md"],
                         "rationale": "UI success can hide a missing durable rename",
                         "interactions": [{"id": "ui-effect", "conditions": [
                             {"condition": "C-happy_path", "variant": "main"},
                             {"condition": "C-persistence_consistency", "variant": "main"}],
                             "timing": [], "bindings": [{"scenario": "rename-normal", "step_ids": ["open", "confirm"],
                                                          "oracle_ids": ["ui", "storage"]}]}]}],
              "gaps": [], "exclusions": []}
    write(tmp_path, "book.json", detailed)
    write(tmp_path, "risk-intent.json", intent)
    asset = assets.strength_prepare("risk-intent.json", "book.json", tmp_path)
    write(tmp_path, "strength.json", asset)
    return detailed, intent, asset


def test_preparation_is_read_only_and_full_intent_bound(prepared, tmp_path):
    _, intent, asset = prepared
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    report = assets.strength_audit("strength.json", tmp_path)
    assert report["claim"] == "declared_strength_checked"
    assert report["execution"] == "unrequested"
    assert asset["intent"] == intent
    assert asset["intent_sha256"] == scenario.sha(intent)
    assert report["denominator"]["risk_ids"] == ["RISK-effect"]
    assert "semantic sufficiency" in report["qualification"]
    assert "scenario_audit" not in report
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}


def test_schema_validates_real_prepared_outputs(prepared):
    _, intent, asset = prepared
    schemas = assets.strength_schemas()
    for name, value in (("intent", intent), ("asset", asset)):
        Draft202012Validator.check_schema(schemas[name])
        Draft202012Validator(schemas[name]).validate(value)


@pytest.mark.parametrize("change,error", [
    (lambda i: i.update(schema_version=True), "version"),
    (lambda i: i.update(extra=True), "fields"),
    (lambda i: i["risks"][0].update(rationale=" "), "nonempty"),
    (lambda i: i["risks"][0].update(operation="unknown"), "operation"),
    (lambda i: i["risks"].append(deepcopy(i["risks"][0])), "duplicate ID"),
    (lambda i: i["risks"][0].update(requirements=["unknown"]), "reference"),
    (lambda i: i["risks"][0]["interactions"][0]["conditions"][0].update(variant="unknown"), "variant"),
    (lambda i: i["risks"][0]["interactions"][0]["conditions"].pop(), "two conditions"),
    (lambda i: i["risks"][0]["interactions"][0]["bindings"][0].update(scenario="length-below"), "interaction"),
    (lambda i: i["risks"][0]["interactions"][0]["bindings"][0].update(step_ids=["confirm", "open"]), "order"),
    (lambda i: i["risks"][0]["interactions"][0]["bindings"][0].update(step_ids=["open"]), "stimulus"),
    (lambda i: i["risks"][0]["interactions"][0]["bindings"][0].update(oracle_ids=["ui"]), "oracle"),
    (lambda i: i["risks"][0]["interactions"][0]["bindings"].append(deepcopy(i["risks"][0]["interactions"][0]["bindings"][0])), "duplicate"),
])
def test_invalid_risk_semantics_refused(prepared, tmp_path, change, error):
    _, intent, _ = prepared
    change(intent)
    write(tmp_path, "risk-intent.json", intent)
    with pytest.raises(assets.AssetError, match=error):
        assets.strength_prepare("risk-intent.json", "book.json", tmp_path)


def test_selected_risk_oracles_must_include_independent_effect(prepared, tmp_path):
    _, intent, _ = prepared
    interaction = intent["risks"][0]["interactions"][0]
    interaction["conditions"][1]["condition"] = "C-visual_interaction"
    interaction["bindings"][0]["oracle_ids"] = ["ui"]
    write(tmp_path, "risk-intent.json", intent)
    with pytest.raises(assets.AssetError, match="independent effect"):
        assets.strength_prepare("risk-intent.json", "book.json", tmp_path)


def test_requirement_source_cannot_be_replaced_with_arbitrary_book_source(prepared, tmp_path):
    detailed, intent, _ = prepared
    (tmp_path / "other.txt").write_text("Not the requirement authority", encoding="utf-8")
    detailed["sources"].append({"path": "other.txt", "sha256": scenario.file_hash(tmp_path, "other.txt")})
    intent["risks"][0]["source_refs"] = ["other.txt"]
    write(tmp_path, "book.json", detailed)
    write(tmp_path, "risk-intent.json", intent)
    with pytest.raises(assets.AssetError, match="requirement sources"):
        assets.strength_prepare("risk-intent.json", "book.json", tmp_path)


def test_event_checkpoint_pair_requires_exact_stimulus(prepared, tmp_path):
    _, intent, _ = prepared
    interaction = intent["risks"][0]["interactions"][0]
    interaction["conditions"] = []
    interaction["timing"] = [{"event": "deleted", "checkpoint": "before-confirm"}]
    interaction["bindings"] = [{"scenario": "rename-deleted-before-confirm", "step_ids": ["open", "inject", "confirm"],
                                 "oracle_ids": ["ui", "storage"]}]
    write(tmp_path, "risk-intent.json", intent)
    assert assets.strength_prepare("risk-intent.json", "book.json", tmp_path)["claim"] == "declared_strength_ready"
    interaction["bindings"][0]["step_ids"].remove("inject")
    write(tmp_path, "risk-intent.json", intent)
    with pytest.raises(assets.AssetError, match="timing stimulus"):
        assets.strength_prepare("risk-intent.json", "book.json", tmp_path)


def test_unbound_and_unknown_work_remain_in_denominator(prepared, tmp_path):
    _, intent, _ = prepared
    intent["risks"][0]["interactions"][0]["bindings"] = []
    intent["gaps"] = [{"id": "G1", "reason": "Input unit unknown", "owner": "reviewer", "next_action": "Inspect contract"}]
    intent["exclusions"] = [{"id": "EX1", "reason": "Different explicit platform scope", "source_refs": ["fixture-contract.md"]}]
    write(tmp_path, "risk-intent.json", intent)
    asset = assets.strength_prepare("risk-intent.json", "book.json", tmp_path)
    assert asset["claim"] == "strength_incomplete"
    assert {r["kind"] for r in asset["gaps"]} == {"unbound_interaction", "declared"}
    assert asset["denominator"]["gap_ids"] == ["G1"]
    assert asset["denominator"]["exclusion_ids"] == ["EX1"]


@pytest.mark.parametrize("target", ["book", "intent", "asset", "source"])
def test_drift_or_denominator_shrink_invalidates_frozen_asset(prepared, tmp_path, target):
    detailed, intent, asset = prepared
    if target == "book":
        detailed["scope"] += " changed"
        write(tmp_path, "book.json", detailed)
    elif target == "intent":
        intent["risks"][0]["interactions"][0]["bindings"] = []
        write(tmp_path, "risk-intent.json", intent)
    elif target == "asset":
        asset["denominator"]["risk_ids"] = []
        write(tmp_path, "strength.json", asset)
    else:
        (tmp_path / "fixture-contract.md").write_text("changed", encoding="utf-8")
    with pytest.raises((assets.AssetError, scenario.ScenarioError), match="stale|changed"):
        assets.strength_audit("strength.json", tmp_path)


def test_changed_intent_requires_new_asset_before_valid_resume(prepared, tmp_path):
    _, intent, old = prepared
    old_bytes = (tmp_path / "strength.json").read_bytes()
    intent["risks"][0]["rationale"] += "; reviewed source uncertainty"
    write(tmp_path, "risk-intent.json", intent)
    with pytest.raises(assets.AssetError, match="stale/changed"):
        assets.strength_audit("strength.json", tmp_path)
    new = assets.strength_prepare("risk-intent.json", "book.json", tmp_path)
    write(tmp_path, "strength-v2.json", new)
    assert new["intent_sha256"] != old["intent_sha256"]
    assert assets.strength_audit("strength-v2.json", tmp_path)["claim"] == "declared_strength_checked"
    assert (tmp_path / "strength.json").read_bytes() == old_bytes


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_frozen_asset_cannot_change_json_types_with_python_equality(prepared, tmp_path, version):
    _, _, asset = prepared
    asset["schema_version"] = version
    write(tmp_path, "strength.json", asset)
    with pytest.raises(assets.AssetError, match="stale/changed"):
        assets.strength_audit("strength.json", tmp_path)


@pytest.mark.parametrize("status", ["failed", "blocked", "skipped", "not_run", "missing", "flaky"])
def test_original_audit_nonpass_cannot_be_hidden_by_other_risk_passes(prepared, tmp_path, status):
    detailed, _, _ = prepared
    trace = fixtures.legacy.trace_for(detailed, tmp_path)
    # Outside the selected risk: full-book execution must still retain it.
    attempt = {"status": "failed" if status == "flaky" else status, "reason": "Synthetic negative observation"}
    if status == "missing":
        trace["results"].pop()
    elif status == "flaky":
        trace["results"][-1]["attempts"].insert(0, attempt)
    else:
        trace["results"][-1]["attempts"] = [attempt]
    write(tmp_path, "trace.json", trace)
    report = assets.strength_audit("strength.json", tmp_path, "trace.json")
    assert report["claim"] == "strength_incomplete"
    assert report["scenario_audit"]["execution_gaps"][-1]["status"] == ("not_run" if status == "missing" else status)
    assert report["risk_observations"][0]["scenarios"][0]["status"] == "passed"


def test_trace_binding_and_raw_evidence_remain_authoritative(prepared, tmp_path):
    detailed, _, _ = prepared
    trace = fixtures.legacy.trace_for(detailed, tmp_path)
    write(tmp_path, "trace.json", trace)
    report = assets.strength_audit("strength.json", tmp_path, "trace.json")
    assert report["claim"] == "declared_strength_checked"
    assert report["scenario_audit"]["statuses"]["passed"] == len(detailed["scenarios"])
    (tmp_path / trace["evidence"][0]["path"]).write_text("changed evidence", encoding="utf-8")
    with pytest.raises(scenario.ScenarioError, match="stale evidence"):
        assets.strength_audit("strength.json", tmp_path, "trace.json")


@pytest.mark.parametrize("path", ["../book.json", "/book.json", "F:/book.json", "a\\book.json", "./book.json", "a//book.json"])
def test_noncanonical_paths_rejected(prepared, tmp_path, path):
    with pytest.raises(assets.AssetError, match="unsafe"):
        assets.strength_prepare("risk-intent.json", path, tmp_path)


@pytest.mark.parametrize("data", ['{"schema_version":1,"schema_version":1}', '{"value":NaN}', '[]'])
def test_ambiguous_json_refused(tmp_path, data):
    (tmp_path / "input.json").write_text(data, encoding="utf-8")
    with pytest.raises(assets.AssetError):
        assets.load(tmp_path, "input.json")


def test_size_and_total_binding_budgets_refuse(prepared, tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "MAX_BYTES", 20)
    with pytest.raises(assets.AssetError, match="budget"):
        assets.load(tmp_path, "book.json")
    monkeypatch.setattr(assets, "MAX_BYTES", 4 * 1024 * 1024)
    monkeypatch.setattr(assets, "MAX_ROWS", 1)
    with pytest.raises(assets.AssetError, match="bounded|budget"):
        assets.strength_prepare("risk-intent.json", "book.json", tmp_path)


def test_standalone_copy_cli_refusal_and_valid_resume(prepared, tmp_path):
    prepared[1]["risks"][0]["rationale"] += "; Unicode \u6587 and \U0001f9ea must round-trip through Windows pipes"
    write(tmp_path, "risk-intent.json", prepared[1])
    install = tmp_path / "installed scripts with spaces"
    install.mkdir()
    for name in ("e2e_assets.py", "e2e_scenarios.py"):
        shutil.copyfile(SHARED / name, install / name)
    script = install / "e2e_assets.py"

    def run(*arguments):
        return subprocess.run([sys.executable, "-E", "-s", str(script), *arguments],
                              cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", check=False)

    assert run("--help").returncode == 0
    assert run("schema", "strength").returncode == 0
    result = run("strength-prepare", "risk-intent.json", "--book", "book.json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["intent"] == prepared[1]
    write(tmp_path, "copied-strength.json", json.loads(result.stdout))
    assert run("strength-audit", "copied-strength.json").returncode == 0
    detailed, _, _ = prepared
    trace = fixtures.legacy.trace_for(detailed, tmp_path)
    trace["results"] = []
    write(tmp_path, "empty-trace.json", trace)
    failed = run("strength-audit", "copied-strength.json", "--trace", "empty-trace.json")
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["scenario_audit"]["statuses"]["not_run"] == len(detailed["scenarios"])
    write(tmp_path, "fresh-trace.json", fixtures.legacy.trace_for(detailed, tmp_path))
    assert run("strength-audit", "copied-strength.json", "--trace", "fresh-trace.json").returncode == 0
    assert run("strength-audit", "copied-strength.json", "--book", "book.json").returncode == 2


def binding(root, path):
    return {"path": path, "sha256": assets.digest_file(root, path)}


@pytest.fixture
def bundled(prepared, tmp_path):
    """Three synthetic independent operations plus one shared consumer: FOUR books."""
    detailed, risk, _ = prepared
    for name, content in (("request.txt", "Complete request: alpha, beta, gamma and their shared journey"),
                          ("build.txt", "Shared executable build bytes v1"), ("fixture.txt", "Shared fixture bytes v1")):
        (tmp_path / name).write_text(content, encoding="utf-8")
    identities = ["alpha", "beta", "gamma", "journey"]
    parent = {"schema_version": 1, "scope": "Complete four-book synthetic parent request", "request_sources": [binding(tmp_path, "request.txt")],
              "obligations": [{"id": name, "kind": "cross_feature" if name == "journey" else "operation",
                               "description": "Original " + name, "source_refs": ["request.txt"],
                               "depends_on": identities[:3] if name == "journey" else []} for name in identities],
              "gaps": [], "exclusions": []}
    intent = {"schema_version": 1, "books": []}
    for name in identities:
        source = name + ".txt"
        (tmp_path / source).write_text("Independent source " + name, encoding="utf-8")
        current = deepcopy(detailed)
        current["sources"].append(binding(tmp_path, source))
        if name == "journey":
            current["operations"][0]["dimensions"]["cross_feature"]["disposition"] = "applicable"
            condition = deepcopy(current["conditions"][0])
            condition.update(id="C-cross", dimension="cross_feature")
            condition["variants"][0]["expected"] = current["scenarios"][0]["oracles"][1]["assertion"]
            current["conditions"].append(condition)
            for card in current["scenarios"]:
                card["dimensions"].append("cross_feature")
                card["condition_bindings"].append({"condition": "C-cross", "variant": "main", "step_ids": ["confirm"], "oracle_ids": ["storage"]})
        write(tmp_path, name + "-book.json", current)
        write(tmp_path, name + "-risk.json", risk)
        strength = assets.strength_prepare(name + "-risk.json", name + "-book.json", tmp_path)
        write(tmp_path, name + "-strength.json", strength)
        intent["books"].append({"id": name, "path": name + "-book.json",
                                "scope_bindings": [{"scope_id": name, "operation_ids": ["rename"],
                                                    "scenario_ids": [s["id"] for s in current["scenarios"]]}],
                                "depends_on": identities[:3] if name == "journey" else [],
                                "fixtures": [binding(tmp_path, "fixture.txt")],
                                "target": {"id": "fixture-not-a-product", "bindings": [binding(tmp_path, "build.txt")]},
                                "strength_refs": [binding(tmp_path, name + "-strength.json")]})
    write(tmp_path, "parent.json", parent)
    write(tmp_path, "bundle-intent.json", intent)
    frozen = assets.bundle_prepare("bundle-intent.json", "parent.json", tmp_path)
    write(tmp_path, "bundle.json", frozen)
    digest = assets.digest_file(tmp_path, "bundle.json")
    runs = {"schema_version": 1, "bundle_file_sha256": digest, "runs": []}
    for entry in frozen["books"]:
        name = entry["id"]
        trace = fixtures.legacy.trace_for(assets.load(tmp_path, entry["book"]["path"]), tmp_path)
        trace["run_id"] = "original-" + name
        receipt = {"schema_version": 1, "bundle_file_sha256": digest, "book_binding_sha256": entry["binding_sha256"],
                   "book_id": name, "run_id": trace["run_id"], "target": trace["target"]}
        write(tmp_path, name + "-execution-binding.json", receipt)
        receipt_ref = binding(tmp_path, name + "-execution-binding.json")
        trace["evidence"].append({"id": "bundle-execution-binding", "kind": "log", "captured_at": trace["started_at"], **receipt_ref})
        write(tmp_path, name + "-trace.json", trace)
        runs["runs"].append({"book_id": name, "bundle_file_sha256": digest, "book_binding_sha256": entry["binding_sha256"],
                             "trace": binding(tmp_path, name + "-trace.json"), "execution_binding": receipt_ref})
    write(tmp_path, "runs.json", runs)
    return parent, intent, frozen, digest, runs


def impact(root, bundled, runs="runs.json"):
    return assets.bundle_impact("bundle.json", bundled[3], root, runs)


def refreeze_bundle(root, bundled):
    write(root, "parent.json", bundled[0])
    write(root, "bundle-intent.json", bundled[1])
    value = assets.bundle_prepare("bundle-intent.json", "parent.json", root)
    write(root, "new-bundle.json", value)
    return value, assets.digest_file(root, "new-bundle.json")


def test_bundle_schemas_freeze_complete_parent_and_preserve_original_runs(bundled, tmp_path):
    parent, intent, frozen, digest, runs = bundled
    schemas = assets.bundle_schemas()
    for key, value in (("parent", parent), ("intent", intent), ("asset", frozen), ("runs", runs)):
        Draft202012Validator.check_schema(schemas[key])
        Draft202012Validator(schemas[key]).validate(value)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    report = impact(tmp_path, bundled)
    assert report["claim"] == "bundle_preparation_reusable"
    assert report["denominator"]["book_ids"] == ["alpha", "beta", "gamma", "journey"]
    assert {e["original_run_id"] for e in report["preserved_old_run_evidence"]} == {"original-" + b for b in report["denominator"]["book_ids"]}
    assert {e["claim"] for e in report["preserved_old_run_evidence"]} == {"preserve_old_run_evidence"}
    assert "never a new-run pass" in report["qualification"]
    assert digest != scenario.sha(frozen)  # CLI pin is the FILE bytes, not canonical book JSON.
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert impact(tmp_path, bundled, None)["execution"] == "unrequested"


@pytest.mark.parametrize("target", ["book", "source", "fixture", "target"])
def test_actual_input_bytes_invalidate_exact_books_and_transitive_consumers(bundled, tmp_path, target):
    if target == "book":
        value = assets.load(tmp_path, "alpha-book.json")
        value["scope"] += " changed"
        write(tmp_path, "alpha-book.json", value)
    else:
        path = {"source": "alpha.txt", "fixture": "fixture.txt", "target": "build.txt"}[target]
        (tmp_path / path).write_text("CHANGED bytes; labels/revision are unchanged", encoding="utf-8")
    report = impact(tmp_path, bundled)
    expected = {"alpha", "journey"} if target in {"book", "source"} else {"alpha", "beta", "gamma", "journey"}
    assert set(report["affected_books"]) == expected
    assert {r["book_id"] for r in report["preserved_old_run_evidence"]} == set(bundled[2]["denominator"]["book_ids"]) - expected
    assert len(report["denominator"]["scope_ids"]) == 4
    assert {r["book_id"] for r in report["run_gaps"]} == expected
    assert sum(len(r["scenario_ids"]) for r in report["scenario_denominator"]) == 24


def test_shared_source_path_directly_invalidates_all_actual_readers(bundled, tmp_path):
    (tmp_path / "fixture-contract.md").write_text("Changed shared requirement/source bytes", encoding="utf-8")
    assert impact(tmp_path, bundled)["directly_changed_books"] == ["alpha", "beta", "gamma", "journey"]


@pytest.mark.parametrize("change,error", [
    (lambda p, i: i["books"][-1].update(depends_on=["alpha", "beta"]), "missing book dependency"),
    (lambda p, i: i["books"][0].update(depends_on=["unknown"]), "unknown reference"),
    (lambda p, i: i["books"][0].update(depends_on=["journey"]), "cyclic"),
    (lambda p, i: i["books"][0].update(depends_on=["alpha"]), "self dependency"),
    (lambda p, i: i["books"][0]["scope_bindings"][0]["scenario_ids"].pop(), "every book scenario"),
    (lambda p, i: i["books"][0]["scope_bindings"][0].update(operation_ids=["missing"]), "unknown reference"),
    (lambda p, i: i["books"][0].update(strength_refs=[]), "bounded array"),
    (lambda p, i: i["books"][0]["target"].update(bindings=[]), "bounded array"),
    (lambda p, i: i["books"][1].update(path=i["books"][0]["path"]), "duplicate book path"),
    (lambda p, i: p["obligations"][-1].update(depends_on=["alpha"]), "at least two"),
    (lambda p, i: p["obligations"][0].update(depends_on=["journey"]), "cyclic"),
    (lambda p, i: p.update(schema_version=True), "version"),
])
def test_bundle_rejects_scope_dependency_and_binding_omissions(bundled, tmp_path, change, error):
    change(bundled[0], bundled[1])
    with pytest.raises(assets.AssetError, match=error):
        refreeze_bundle(tmp_path, bundled)


def test_parent_gaps_exclusions_and_unmapped_required_scope_cannot_disappear(bundled, tmp_path):
    parent = bundled[0]
    parent["obligations"].append({"id": "required-extra", "kind": "operation", "description": "Still required, unmapped",
                                   "source_refs": ["request.txt"], "depends_on": []})
    parent["gaps"] = [{"id": "unknown-input", "reason": "Unknown", "owner": "reviewer", "next_action": "Inspect"}]
    parent["exclusions"] = [{"id": "mobile", "reason": "Explicit desktop-only scope", "source_refs": ["request.txt"]}]
    value, digest = refreeze_bundle(tmp_path, bundled)
    report = assets.bundle_impact("new-bundle.json", digest, tmp_path)
    assert value["claim"] == "bundle_incomplete"
    assert {g["kind"] for g in value["gaps"]} == {"parent_gap", "unmapped_scope"}
    assert report["denominator"]["scope_ids"] == ["alpha", "beta", "gamma", "journey", "required-extra"]
    assert report["parent_gaps"] == parent["gaps"] and report["exclusions"] == parent["exclusions"]


def test_incomplete_q1_risk_remains_explicit_after_bundle_freeze(bundled, tmp_path):
    risk = assets.load(tmp_path, "alpha-risk.json")
    risk["risks"][0]["interactions"][0]["bindings"] = []
    write(tmp_path, "alpha-risk.json", risk)
    strength = assets.strength_prepare("alpha-risk.json", "alpha-book.json", tmp_path)
    write(tmp_path, "alpha-strength.json", strength)
    bundled[1]["books"][0]["strength_refs"] = [binding(tmp_path, "alpha-strength.json")]
    value, digest = refreeze_bundle(tmp_path, bundled)
    report = assets.bundle_impact("new-bundle.json", digest, tmp_path)
    assert report["claim"] == "bundle_impact_detected"
    assert value["gaps"][0]["kind"] == "strength_gap"
    assert strength["denominator"]["interactions"] == [{"risk": "RISK-effect", "interaction": "ui-effect"}]


@pytest.mark.parametrize("part", ["parent", "intent", "request", "bundle"])
def test_changed_authoritative_scope_or_bundle_pin_refused(bundled, tmp_path, part):
    filename = {"parent": "parent.json", "intent": "bundle-intent.json", "request": "request.txt", "bundle": "bundle.json"}[part]
    with (tmp_path / filename).open("a", encoding="utf-8") as stream:
        stream.write("\n ")
    with pytest.raises(assets.AssetError, match="changed|SHA-256|stale"):
        impact(tmp_path, bundled)


def test_new_parent_cannot_refreeze_then_adopt_old_run_index(bundled, tmp_path):
    bundled[0]["scope"] += " amended request"
    _, digest = refreeze_bundle(tmp_path, bundled)
    with pytest.raises(assets.AssetError, match="rebound"):
        assets.bundle_impact("new-bundle.json", digest, tmp_path, "runs.json")


def test_relabelled_index_cannot_adopt_old_execution_receipts_for_new_parent(bundled, tmp_path):
    bundled[0]["scope"] += " changed parent, same four books"
    frozen, digest = refreeze_bundle(tmp_path, bundled)
    runs = bundled[4]
    runs["bundle_file_sha256"] = digest
    for row, book in zip(runs["runs"], frozen["books"]):
        row.update(bundle_file_sha256=digest, book_binding_sha256=book["binding_sha256"])
    write(tmp_path, "relabelled-runs.json", runs)
    result = assets.bundle_impact("new-bundle.json", digest, tmp_path, "relabelled-runs.json")
    assert result["preserved_old_run_evidence"] == []
    assert len(result["run_gaps"]) == 4
    assert all("execution binding differs" in row["detail"] for row in result["run_gaps"])


@pytest.mark.parametrize("mutation", ["edit-original", "alternate-path", "duplicate", "unknown-id", "target"])
def test_run_receipt_must_match_unique_original_trace_evidence(bundled, tmp_path, mutation):
    trace = assets.load(tmp_path, "alpha-trace.json")
    runs = bundled[4]
    receipt = assets.load(tmp_path, "alpha-execution-binding.json")
    if mutation == "edit-original":
        receipt["run_id"] = "different-run"
        write(tmp_path, "alpha-execution-binding.json", receipt)
        runs["runs"][0]["execution_binding"] = binding(tmp_path, "alpha-execution-binding.json")
    elif mutation in {"alternate-path", "duplicate"}:
        write(tmp_path, "alternate-binding.json", receipt)
        runs["runs"][0]["execution_binding"] = binding(tmp_path, "alternate-binding.json")
        if mutation == "duplicate":
            trace["evidence"].append({"id": "other-binding", "kind": "log", "captured_at": trace["started_at"],
                                      **binding(tmp_path, "alternate-binding.json")})
    elif mutation == "unknown-id":
        trace["evidence"][-1]["id"] = "unknown-binding-id"
    else:
        trace["target"] = "different-build-label"
    write(tmp_path, "alpha-trace.json", trace)
    runs["runs"][0]["trace"] = binding(tmp_path, "alpha-trace.json")
    write(tmp_path, "runs.json", runs)
    result = impact(tmp_path, bundled)
    assert {r["book_id"] for r in result["run_gaps"]} == {"alpha"}
    assert "alpha" not in {r["book_id"] for r in result["preserved_old_run_evidence"]}


def test_input_book_dependency_cannot_be_hidden_by_scope_names(bundled, tmp_path):
    bundled[1]["books"][1]["fixtures"].append(binding(tmp_path, "alpha-book.json"))
    with pytest.raises(assets.AssetError, match="producer-book input dependency"):
        refreeze_bundle(tmp_path, bundled)


def test_refrozen_bundle_needs_fresh_receipts_and_fresh_trace_bytes(bundled, tmp_path):
    bundled[0]["scope"] += " reviewed parent revision"
    frozen, digest = refreeze_bundle(tmp_path, bundled)
    runs = {"schema_version": 1, "bundle_file_sha256": digest, "runs": []}
    for entry in frozen["books"]:
        name = entry["id"]
        trace = fixtures.legacy.trace_for(assets.load(tmp_path, entry["book"]["path"]), tmp_path)
        trace["run_id"] = "new-synthetic-run-" + name
        receipt = {"schema_version": 1, "bundle_file_sha256": digest, "book_binding_sha256": entry["binding_sha256"],
                   "book_id": name, "run_id": trace["run_id"], "target": trace["target"]}
        write(tmp_path, "fresh-" + name + "-receipt.json", receipt)
        ref = binding(tmp_path, "fresh-" + name + "-receipt.json")
        trace["evidence"].append({"id": "bundle-execution-binding", "kind": "log", "captured_at": trace["started_at"], **ref})
        write(tmp_path, "fresh-" + name + "-trace.json", trace)
        runs["runs"].append({"book_id": name, "bundle_file_sha256": digest, "book_binding_sha256": entry["binding_sha256"],
                             "trace": binding(tmp_path, "fresh-" + name + "-trace.json"), "execution_binding": ref})
    write(tmp_path, "fresh-runs.json", runs)
    result = assets.bundle_impact("new-bundle.json", digest, tmp_path, "fresh-runs.json")
    assert result["claim"] == "bundle_preparation_reusable"
    assert all(e["original_run_id"].startswith("new-synthetic-run-") for e in result["preserved_old_run_evidence"])
    assert all((tmp_path / (b + "-trace.json")).is_file() for b in result["denominator"]["book_ids"])


def test_failed_scope_cannot_be_split_out_of_bundle(bundled, tmp_path):
    bundled[1]["books"].pop(0)
    bundled[1]["books"][-1]["depends_on"].remove("alpha")
    frozen, digest = refreeze_bundle(tmp_path, bundled)
    assert frozen["claim"] == "bundle_incomplete"
    assert {"kind": "unmapped_scope", "scope_id": "alpha"} in frozen["gaps"]
    assert "alpha" in frozen["denominator"]["scope_ids"]
    with pytest.raises(assets.AssetError, match="rebound"):
        assets.bundle_impact("new-bundle.json", digest, tmp_path, "runs.json")


@pytest.mark.parametrize("status", ["failed", "blocked", "skipped", "not_run", "missing", "flaky"])
def test_unaffected_original_trace_is_reaudited_and_nonpass_kept(bundled, tmp_path, status):
    trace = assets.load(tmp_path, "beta-trace.json")
    if status == "missing":
        trace["results"].pop()
    elif status == "flaky":
        trace["results"][-1]["attempts"].insert(0, {"status": "failed", "reason": "First attempt failed"})
    else:
        trace["results"][-1]["attempts"] = [{"status": status, "reason": "Actual nonpass retained"}]
    write(tmp_path, "beta-trace.json", trace)
    bundled[4]["runs"][1]["trace"] = binding(tmp_path, "beta-trace.json")
    write(tmp_path, "runs.json", bundled[4])
    result = impact(tmp_path, bundled)
    assert result["affected_books"] == []
    assert result["run_gaps"][0]["book_id"] == "beta"
    assert result["run_gaps"][0]["original_scenario_audit"]["execution_gaps"][-1]["status"] == ("not_run" if status == "missing" else status)
    assert {r["book_id"] for r in result["preserved_old_run_evidence"]} == {"alpha", "gamma", "journey"}


@pytest.mark.parametrize("change,kind", [
    (lambda runs: runs["runs"].append({**runs["runs"][0], "book_id": "unknown"}), "unknown_book"),
    (lambda runs: runs["runs"].append(deepcopy(runs["runs"][0])), "conflicting_runs"),
    (lambda runs: runs["runs"].pop(0), "missing_run"),
    (lambda runs: runs["runs"][0].update(book_binding_sha256="0" * 64), "stale_run_binding"),
    (lambda runs: runs["runs"][0].update(bundle_file_sha256="0" * 64), "stale_run_binding"),
    (lambda runs: runs["runs"][0]["trace"].update(sha256="0" * 64), "unverified_run"),
])
def test_bad_run_references_are_explicit_gaps(bundled, tmp_path, change, kind):
    change(bundled[4])
    write(tmp_path, "runs.json", bundled[4])
    report = impact(tmp_path, bundled)
    assert report["claim"] == "bundle_impact_detected"
    assert kind in {g["kind"] for g in report["run_gaps"]}
    assert len(report["denominator"]["book_ids"]) == 4


def test_prior_pass_with_tampered_evidence_is_not_preserved(bundled, tmp_path):
    (tmp_path / "test-results/storage.txt").write_text("Evidence changed", encoding="utf-8")
    result = impact(tmp_path, bundled)
    assert result["preserved_old_run_evidence"] == []
    assert len(result["run_gaps"]) == 4


def test_changed_whole_book_cannot_accept_old_trace_after_new_freeze(bundled, tmp_path):
    value = assets.load(tmp_path, "alpha-book.json")
    value["scope"] += " honest new book"
    write(tmp_path, "alpha-book.json", value)
    write(tmp_path, "alpha-strength.json", assets.strength_prepare("alpha-risk.json", "alpha-book.json", tmp_path))
    bundled[1]["books"][0]["strength_refs"] = [binding(tmp_path, "alpha-strength.json")]
    frozen, digest = refreeze_bundle(tmp_path, bundled)
    # Even rewriting all index metadata cannot transplant the actual old trace.
    bundled[4]["bundle_file_sha256"] = digest
    for row, book in zip(bundled[4]["runs"], frozen["books"]):
        row.update(bundle_file_sha256=digest, book_binding_sha256=book["binding_sha256"])
    write(tmp_path, "rewritten-runs.json", bundled[4])
    result = assets.bundle_impact("new-bundle.json", digest, tmp_path, "rewritten-runs.json")
    assert {g["book_id"] for g in result["run_gaps"]} == {"alpha", "beta", "gamma", "journey"}
    assert "stale trace binding" in result["run_gaps"][0]["detail"]


def test_bundle_budget_refused_before_graph_expansion(bundled, tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "MAX_BUNDLE_BOOKS", 3)
    with pytest.raises(assets.AssetError, match="budget"):
        assets.bundle_prepare("bundle-intent.json", "parent.json", tmp_path)


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(schema_version=True),
    lambda r: r["runs"][0].update(book_binding_sha256=False),
    lambda r: r["runs"][0].update(extra="unknown field"),
    lambda r: r["runs"][0]["execution_binding"].update(path="../receipt.json"),
    lambda r: r["runs"][0]["trace"].update(path="./trace.json"),
])
def test_run_index_json_shape_and_paths_are_strict(bundled, tmp_path, mutation):
    mutation(bundled[4])
    write(tmp_path, "runs.json", bundled[4])
    with pytest.raises(assets.AssetError):
        impact(tmp_path, bundled)


def test_bundle_installed_cli_requires_external_pin_and_supports_fresh_resume(bundled, tmp_path):
    install = tmp_path / "installed"
    install.mkdir()
    for name in ("e2e_assets.py", "e2e_scenarios.py"):
        shutil.copyfile(SHARED / name, install / name)

    def run(*args):
        return subprocess.run([sys.executable, "-E", "-s", str(install / "e2e_assets.py"), *args],
                              cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", check=False)

    assert run("schema", "bundle").returncode == 0
    assert run("bundle-prepare", "bundle-intent.json", "--parent", "parent.json").returncode == 0
    assert run("bundle-impact", "bundle.json").returncode == 2
    args = ("bundle-impact", "bundle.json", "--expected-bundle-sha256", bundled[3], "--runs", "runs.json")
    assert run(*args).returncode == 0
    original = (tmp_path / "alpha.txt").read_bytes()
    (tmp_path / "alpha.txt").write_bytes(b"Changed source bytes")
    result = run(*args)
    assert result.returncode == 1
    assert json.loads(result.stdout)["affected_books"] == ["alpha", "journey"]
    (tmp_path / "alpha.txt").write_bytes(original)
    assert run(*args).returncode == 0


@pytest.fixture
def crossed(prepared, tmp_path):
    """Synthetic two-case native lane mapped to six complete scenario cards."""
    native = module("e2e_coverage", SHARED / "e2e_coverage.py")
    module("e2e_runner", SHARED / "e2e_runner.py")
    detailed = prepared[0]
    (tmp_path / "native_test.py").write_text("# Synthetic checker fixture, not executed native tests\n", encoding="utf-8")
    (tmp_path / "native-build.txt").write_text("Frozen synthetic target build", encoding="utf-8")
    parent = {"schema_version": 1, "scope": "Complete synthetic rename parent", "request_sources": [binding(tmp_path, "fixture-contract.md")],
              "obligations": [{"id": "rename", "kind": "operation", "description": "Complete rename fixture scope",
                               "source_refs": ["fixture-contract.md"], "depends_on": []}], "gaps": [], "exclusions": []}
    bundle_intent = {"schema_version": 1, "books": [{"id": "rename", "path": "book.json", "scope_bindings": [{
        "scope_id": "rename", "operation_ids": ["rename"], "scenario_ids": [s["id"] for s in detailed["scenarios"]]}],
        "depends_on": [], "fixtures": [], "target": {"id": "fixture-not-a-product", "bindings": [
            binding(tmp_path, "native-build.txt"), binding(tmp_path, "native_test.py")]}, "strength_refs": [binding(tmp_path, "strength.json")]}]}
    write(tmp_path, "cross-parent.json", parent)
    write(tmp_path, "cross-bundle-intent.json", bundle_intent)
    bundle = assets.bundle_prepare("cross-bundle-intent.json", "cross-parent.json", tmp_path)
    write(tmp_path, "cross-bundle.json", bundle)
    bundle_sha = assets.digest_file(tmp_path, "cross-bundle.json")
    model = {"schema_version": 1, "scope": "Synthetic native rename cases", "source_revision": "synthetic-v1",
        "sources": [binding(tmp_path, "fixture-contract.md")], "exclusions": [],
        "requirements": [{"id": "native-R", "source": "fixture-contract.md", "assertion": "Preserve exact durable file effect"}],
        "journeys": [{"id": "rename-native", "requirements": ["native-R"], "steps": ["Exercise rename and read files"],
                      "factors": {"input": ["one", "two"]}, "strength": "exhaustive"}]}
    plan = native.plan(model, tmp_path)
    native_bindings = {"schema_version": 1, "manifest_sha256": plan["manifest_sha256"],
        "test_sources": [binding(tmp_path, "native_test.py")], "cases": [{"id": c["id"], "test_ref": "native_test.py",
            "selector": "native_test.py::test_rename[" + c["id"] + "]", "asserted_requirements": c["requirements"]} for c in plan["cases"]]}
    write(tmp_path, "native-manifest.json", model)
    write(tmp_path, "native-bindings.json", native_bindings)
    design = scenario.check(detailed, tmp_path)
    obligations = [{"book_id": "rename", "kind": "scenario", "id": c["id"]} for c in detailed["scenarios"]]
    for kind, key in (("condition", "condition_obligations"), ("timing", "timing_obligations")):
        obligations.extend({"book_id": "rename", "kind": kind, "id": c["id"]} for c in design[key])
    intent = {"schema_version": 1, "native_lanes": [{"id": "native", "root": ".", "manifest": binding(tmp_path, "native-manifest.json"),
        "bindings": binding(tmp_path, "native-bindings.json"), "runner": "pytest", "target": "fixture-not-a-product", "book_ids": ["rename"]}],
        "mappings": [{"id": "many-to-many", "rationale": "Synthetic contract: both native inputs exercise every declared scenario obligation; semantic adequacy is independently reviewed",
            "scenario_refs": [{"book_id": "rename", "scenario_id": c["id"], "step_ids": [s["id"] for s in c["steps"]],
                               "oracle_ids": [o["id"] for o in c["oracles"]]} for c in detailed["scenarios"]],
            "obligations": obligations, "native_cases": [{"lane_id": "native", "case_id": c["id"], "journey": c["journey"], "parameters": c["parameters"]} for c in plan["cases"]],
            "requirement_links": [{"book_id": "rename", "requirement_id": "R-identity", "lane_id": "native", "native_requirement_id": "native-R"}]}]}
    write(tmp_path, "crosswalk-intent.json", intent)
    asset = assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", bundle_sha, tmp_path)
    write(tmp_path, "crosswalk.json", asset)
    cross_sha = assets.digest_file(tmp_path, "crosswalk.json")
    raw_native = {"schema_version": 1, "runner": "pytest", "run_id": "synthetic-native-run", "exit_code": 0, "errors": [],
        "collected": [c["selector"] for c in native_bindings["cases"]], "events": [{"nodeid": c["selector"], "file": "native_test.py",
            "phase": p, "outcome": "passed", "wasxfail": False} for c in native_bindings["cases"] for p in ("setup", "call", "teardown")]}
    write(tmp_path, "native-report.json", raw_native)
    execution = {"schema_version": 1, "run_id": raw_native["run_id"], "runner": "pytest", "command": ["synthetic-fixture"],
        "target": "fixture-not-a-product", "started_at": "2026-09-29T01:00:00Z", "finished_at": "2026-09-29T01:01:00Z",
        "manifest_sha256": plan["manifest_sha256"], "bindings_sha256": native.digest(native_bindings), "exit_code": 0,
        "native_report": binding(tmp_path, "native-report.json")}
    write(tmp_path, "native-execution.json", execution)
    evidence = [binding(tmp_path, p) for p in ("native-report.json", "native-execution.json")]
    results = {"schema_version": 1, "manifest_sha256": plan["manifest_sha256"], "source_revision": model["source_revision"],
        **{k: execution[k] for k in ("run_id", "target", "started_at", "finished_at", "command", "exit_code")},
        "test_sources": native_bindings["test_sources"], "evidence": evidence,
        "cases": [{"id": c["id"], "status": "passed", "test_ref": "native_test.py", "asserted_requirements": c["requirements"], "evidence": evidence} for c in plan["cases"]]}
    write(tmp_path, "native-results.json", results)
    trace = fixtures.legacy.trace_for(detailed, tmp_path)
    receipt = {"schema_version": 1, "bundle_file_sha256": bundle_sha, "book_binding_sha256": bundle["books"][0]["binding_sha256"],
               "book_id": "rename", "run_id": trace["run_id"], "target": trace["target"]}
    cross_receipt = {"schema_version": 1, "crosswalk_file_sha256": cross_sha, "book_id": "rename", "run_id": trace["run_id"], "target": trace["target"]}
    write(tmp_path, "scenario-execution.json", receipt)
    write(tmp_path, "crosswalk-execution.json", cross_receipt)
    for identity, path in (("bundle-execution-binding", "scenario-execution.json"), ("crosswalk-execution-binding", "crosswalk-execution.json"),
                           ("native-report", "native-report.json"), ("native-results", "native-results.json"), ("native-execution", "native-execution.json")):
        trace["evidence"].append({"id": identity, "kind": "log", "captured_at": trace["started_at"], **binding(tmp_path, path)})
    write(tmp_path, "cross-scenario-trace.json", trace)
    scenario_index = {"schema_version": 1, "bundle_file_sha256": bundle_sha, "runs": [{"book_id": "rename", "bundle_file_sha256": bundle_sha,
        "book_binding_sha256": bundle["books"][0]["binding_sha256"], "trace": binding(tmp_path, "cross-scenario-trace.json"),
        "execution_binding": binding(tmp_path, "scenario-execution.json")}]}
    native_index = {"schema_version": 1, "crosswalk_file_sha256": cross_sha, "runs": [{"lane_id": "native",
        "results": binding(tmp_path, "native-results.json"), "native_report": binding(tmp_path, "native-report.json"), "execution": binding(tmp_path, "native-execution.json")}]}
    write(tmp_path, "scenario-index.json", scenario_index)
    write(tmp_path, "native-index.json", native_index)
    return {"intent": intent, "asset": asset, "bundle": bundle, "bundle_sha": bundle_sha, "cross_sha": cross_sha,
            "model": model, "plan": plan, "bindings": native_bindings}


def cross_audit(root, crossed):
    return assets.crosswalk_audit("crosswalk.json", crossed["cross_sha"], crossed["bundle_sha"], "scenario-index.json", "native-index.json", root)


def refresh_cross_evidence(root):
    """Resign only synthetic negative-test artifacts; never used for real history."""
    execution = assets.load(root, "native-execution.json")
    execution["native_report"] = binding(root, "native-report.json")
    write(root, "native-execution.json", execution)
    results = assets.load(root, "native-results.json")
    evidence = [binding(root, p) for p in ("native-report.json", "native-execution.json")]
    results["evidence"] = evidence
    for case in results["cases"]:
        case["evidence"] = evidence
    write(root, "native-results.json", results)
    trace = assets.load(root, "cross-scenario-trace.json")
    for item in trace["evidence"]:
        item.update(binding(root, item["path"]))
    write(root, "cross-scenario-trace.json", trace)
    index = assets.load(root, "scenario-index.json")
    index["runs"][0]["trace"] = binding(root, "cross-scenario-trace.json")
    write(root, "scenario-index.json", index)
    index = assets.load(root, "native-index.json")
    for key in ("results", "native_report", "execution"):
        if index["runs"][0][key] is not None:
            index["runs"][0][key] = binding(root, index["runs"][0][key]["path"])
    write(root, "native-index.json", index)


def test_crosswalk_many_to_many_keeps_both_original_auditors(crossed, tmp_path):
    schemas = assets.crosswalk_schemas()
    for name, value in (("intent", crossed["intent"]), ("asset", crossed["asset"]), ("native_runs", assets.load(tmp_path, "native-index.json")),
                        ("execution_binding", assets.load(tmp_path, "crosswalk-execution.json"))):
        Draft202012Validator.check_schema(schemas[name])
        Draft202012Validator(schemas[name]).validate(value)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = cross_audit(tmp_path, crossed)
    assert result["claim"] == "crosswalk_accounting_complete"
    assert result["denominator"]["edge_count"] == len(result["denominator"]["obligations"]) * 2
    assert result["native_audits"][0]["native_audit"]["statuses"]["passed"] == 2
    assert result["bundle_audit"]["preserved_old_run_evidence"][0]["scenario_audit"]["statuses"]["passed"] == 6
    assert "new-run pass" in result["qualification"]
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_disjoint_many_to_many_mapping_rows_do_not_duplicate_credit(crossed, tmp_path):
    first = crossed["intent"]["mappings"][0]
    second = deepcopy(first)
    second["id"] = "second-native-input"
    second["native_cases"] = [first["native_cases"].pop()]
    crossed["intent"]["mappings"].append(second)
    write(tmp_path, "crosswalk-intent.json", crossed["intent"])
    fresh = assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)
    assert fresh["claim"] == "crosswalk_mapping_ready"
    assert fresh["denominator"]["edge_count"] == crossed["asset"]["denominator"]["edge_count"]


@pytest.mark.parametrize("change,error", [
    (lambda i: i["mappings"][0].update(rationale=""), "rationale"),
    (lambda i: i["mappings"][0]["obligations"][0].update(id="unknown"), "obligation ref"),
    (lambda i: i["mappings"][0]["native_cases"][0].update(case_id="unknown"), "unknown native case"),
    (lambda i: i["mappings"][0]["native_cases"][0].update(parameters={"input": "wrong"}), "combination"),
    (lambda i: i["mappings"][0]["scenario_refs"][0]["step_ids"].pop(), "complete ordered"),
    (lambda i: i["mappings"][0]["scenario_refs"][0]["oracle_ids"].pop(), "all scenario oracles"),
    (lambda i: i["mappings"][0].update(requirement_links=[]), "bounded array"),
    (lambda i: i["mappings"][0]["requirement_links"][0].update(native_requirement_id="other"), "requirement link"),
    (lambda i: i["mappings"].append({**deepcopy(i["mappings"][0]), "id": "duplicate-credit"}), "duplicate crosswalk credit"),
    (lambda i: i["native_lanes"].append({**deepcopy(i["native_lanes"][0]), "id": "duplicate-lane"}), "duplicate native selector"),
    (lambda i: i["native_lanes"][0].update(target="unbound-target"), "target differs"),
    (lambda i: i["native_lanes"][0].update(root="../outside"), "unsafe"),
    (lambda i: i.update(schema_version=True), "version"),
])
def test_crosswalk_unknown_conflicting_and_duplicate_links_refused(crossed, tmp_path, change, error):
    change(crossed["intent"])
    write(tmp_path, "crosswalk-intent.json", crossed["intent"])
    with pytest.raises(assets.AssetError, match=error):
        assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)


def test_missing_crosswalk_mapping_retains_complete_scope(crossed, tmp_path):
    crossed["intent"]["mappings"] = []
    write(tmp_path, "crosswalk-intent.json", crossed["intent"])
    fresh = assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)
    assert fresh["claim"] == "crosswalk_incomplete"
    assert len(fresh["denominator"]["obligations"]) == 14
    assert len(fresh["gaps"]) == 16
    assert {g["kind"] for g in fresh["gaps"]} == {"unmapped_obligation", "unmapped_native_case"}


@pytest.mark.parametrize("status", ["failed", "skipped", "not_run", "flaky"])
def test_native_nonpass_never_hidden_by_all_passing_scenarios(crossed, tmp_path, status):
    native = assets.load(tmp_path, "native-report.json")
    values = assets.load(tmp_path, "native-results.json")
    selector = native["collected"][0]
    if status == "not_run":
        native["collected"].remove(selector)
        native["events"] = [e for e in native["events"] if e["nodeid"] != selector]
        values["cases"].pop(0)
    elif status == "flaky":
        first = deepcopy(native["events"][1])
        first["outcome"] = "failed"
        native["events"].insert(0, first)
        values["cases"][0]["status"] = "flaky"
    else:
        native["events"][1]["outcome"] = status
        values["cases"][0]["status"] = status
    write(tmp_path, "native-report.json", native)
    write(tmp_path, "native-results.json", values)
    refresh_cross_evidence(tmp_path)
    result = cross_audit(tmp_path, crossed)
    assert result["claim"] == "crosswalk_incomplete"
    assert result["bundle_audit"]["preserved_old_run_evidence"][0]["scenario_audit"]["statuses"]["passed"] == 6
    assert result["native_audits"][0]["native_audit"]["statuses"][status] == 1
    assert result["native_audits"][0]["reconciliation"] == "original_native_adapter_matched"


def test_normalized_native_pass_cannot_hide_failed_raw_attempt(crossed, tmp_path):
    raw = assets.load(tmp_path, "native-report.json")
    raw["events"][1]["outcome"] = "failed"
    write(tmp_path, "native-report.json", raw)
    refresh_cross_evidence(tmp_path)
    result = cross_audit(tmp_path, crossed)
    assert result["claim"] == "crosswalk_incomplete"
    assert result["native_audits"][0]["native_audit"]["claim"] == "complete_against_frozen_scope"
    assert "raw outcomes conflict" in result["execution_gaps"][0]["detail"]


@pytest.mark.parametrize("kind", ["missing", "duplicate", "unknown", "no-results"])
def test_native_run_index_gaps_never_drop_denominator(crossed, tmp_path, kind):
    index = assets.load(tmp_path, "native-index.json")
    if kind == "missing":
        index["runs"] = []
    elif kind == "duplicate":
        index["runs"].append(deepcopy(index["runs"][0]))
    elif kind == "unknown":
        index["runs"].append({**deepcopy(index["runs"][0]), "lane_id": "unknown"})
    else:
        index["runs"][0]["results"] = None
    write(tmp_path, "native-index.json", index)
    result = cross_audit(tmp_path, crossed)
    assert result["claim"] == "crosswalk_incomplete"
    assert len(result["denominator"]["native_cases"][0]["cases"]) == 2
    assert len(result["denominator"]["obligations"]) == 14


@pytest.mark.parametrize("kind", ["missing", "wrong-digest", "duplicate", "missing-native"])
def test_old_scenario_trace_cannot_be_relabelled_into_crosswalk(crossed, tmp_path, kind):
    trace = assets.load(tmp_path, "cross-scenario-trace.json")
    if kind == "missing":
        trace["evidence"] = [e for e in trace["evidence"] if e["id"] != "crosswalk-execution-binding"]
    elif kind == "wrong-digest":
        value = assets.load(tmp_path, "crosswalk-execution.json")
        value["crosswalk_file_sha256"] = "0" * 64
        write(tmp_path, "crosswalk-execution.json", value)
    elif kind == "duplicate":
        write(tmp_path, "other-crosswalk-receipt.json", assets.load(tmp_path, "crosswalk-execution.json"))
        trace["evidence"].append({"id": "extra-binding", "kind": "log", "captured_at": trace["started_at"], **binding(tmp_path, "other-crosswalk-receipt.json")})
    else:
        trace["evidence"] = [e for e in trace["evidence"] if e["id"] != "native-report"]
    write(tmp_path, "cross-scenario-trace.json", trace)
    refresh_cross_evidence(tmp_path)
    result = cross_audit(tmp_path, crossed)
    assert result["claim"] == "crosswalk_incomplete"
    assert result["execution_gaps"]


def test_native_inputs_must_already_be_in_s1_scope(crossed, tmp_path):
    (tmp_path / "unbound-native-source.txt").write_text("Unbound source", encoding="utf-8")
    model = crossed["model"]
    model["sources"].append(binding(tmp_path, "unbound-native-source.txt"))
    write(tmp_path, "native-manifest.json", model)
    cross_bindings = crossed["bindings"]
    cross_bindings["manifest_sha256"] = scenario.sha(model)
    write(tmp_path, "native-bindings.json", cross_bindings)
    lane = crossed["intent"]["native_lanes"][0]
    lane.update(manifest=binding(tmp_path, "native-manifest.json"), bindings=binding(tmp_path, "native-bindings.json"))
    write(tmp_path, "crosswalk-intent.json", crossed["intent"])
    with pytest.raises(assets.AssetError, match="already be bound"):
        assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)


def test_crosswalk_standalone_cli_and_expected_digest_refusals(crossed, tmp_path):
    install = tmp_path / "copied-helpers"
    install.mkdir()
    for name in ("e2e_assets.py", "e2e_scenarios.py", "e2e_coverage.py", "e2e_runner.py"):
        shutil.copyfile(SHARED / name, install / name)
    def run(*args):
        return subprocess.run([sys.executable, "-E", "-s", str(install / "e2e_assets.py"), *args],
                              cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", check=False)
    assert run("schema", "crosswalk").returncode == 0
    assert run("crosswalk-prepare", "crosswalk-intent.json", "--bundle", "cross-bundle.json", "--expected-bundle-sha256", crossed["bundle_sha"]).returncode == 0
    arguments = ["crosswalk-audit", "crosswalk.json", "--expected-crosswalk-sha256", crossed["cross_sha"],
                 "--expected-bundle-sha256", crossed["bundle_sha"], "--scenario-runs", "scenario-index.json", "--native-runs", "native-index.json"]
    assert run(*arguments).returncode == 0
    arguments[3] = "0" * 64
    assert run(*arguments).returncode == 2


@pytest.mark.parametrize("path", ["native_test.py", "native-build.txt", "native-manifest.json", "native-bindings.json", "crosswalk-intent.json"])
def test_crosswalk_changed_inputs_refused_and_exact_restore_reuses_original_evidence(crossed, tmp_path, path):
    before = (tmp_path / path).read_bytes()
    (tmp_path / path).write_bytes(before + b"\n ")
    with pytest.raises(assets.AssetError):
        cross_audit(tmp_path, crossed)
    (tmp_path / path).write_bytes(before)
    restored = cross_audit(tmp_path, crossed)
    assert restored["claim"] == "crosswalk_accounting_complete"
    assert restored["bundle_audit"]["preserved_old_run_evidence"][0]["original_run_id"] == "synthetic-checker-test"


@pytest.mark.parametrize("field,value", [("schema_version", True), ("schema_version", 2), ("extra", "unknown")])
def test_native_index_strict_shape(crossed, tmp_path, field, value):
    index = assets.load(tmp_path, "native-index.json")
    index[field] = value
    write(tmp_path, "native-index.json", index)
    with pytest.raises(assets.AssetError):
        cross_audit(tmp_path, crossed)


@pytest.mark.parametrize("change", [
    lambda report: report["collected"].append("native_test.py::undeclared"),
    lambda report: report["events"].insert(0, {**deepcopy(report["events"][1]), "outcome": "failed"}),
    lambda report: report.update(collected=[], events=[]),
])
def test_unknown_retry_or_empty_raw_native_report_cannot_use_normalized_pass(crossed, tmp_path, change):
    raw = assets.load(tmp_path, "native-report.json")
    change(raw)
    write(tmp_path, "native-report.json", raw)
    refresh_cross_evidence(tmp_path)
    report = cross_audit(tmp_path, crossed)
    assert report["claim"] == "crosswalk_incomplete"
    assert report["execution_gaps"]
    assert report["native_audits"][0]["native_audit"]["claim"] == "complete_against_frozen_scope"


def test_changed_crosswalk_cannot_relabel_old_index_or_edit_original_receipt(crossed, tmp_path):
    intent = crossed["intent"]
    intent["mappings"][0]["rationale"] += "; changed reviewed mapping intent"
    write(tmp_path, "crosswalk-intent.json", intent)
    replacement = assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)
    write(tmp_path, "crosswalk.json", replacement)
    crossed["cross_sha"] = assets.digest_file(tmp_path, "crosswalk.json")
    index = assets.load(tmp_path, "native-index.json")
    index["crosswalk_file_sha256"] = crossed["cross_sha"]
    write(tmp_path, "native-index.json", index)
    assert cross_audit(tmp_path, crossed)["claim"] == "crosswalk_incomplete"
    receipt = assets.load(tmp_path, "crosswalk-execution.json")
    receipt["crosswalk_file_sha256"] = crossed["cross_sha"]
    write(tmp_path, "crosswalk-execution.json", receipt)
    report = cross_audit(tmp_path, crossed)
    assert report["claim"] == "crosswalk_incomplete"
    assert report["bundle_audit"]["run_gaps"]  # Original trace still pins the original receipt bytes.


def test_crosswalk_edge_budget_before_completion(crossed, tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "MAX_ROWS", 20)
    with pytest.raises(assets.AssetError, match="edge budget"):
        assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)


def test_crosswalk_total_native_case_budget_includes_unmapped_lanes(crossed, tmp_path, monkeypatch):
    intent = crossed["intent"]
    for number in range(10):
        bindings = deepcopy(crossed["bindings"])
        for case in bindings["cases"]:
            case["selector"] = "native_test.py::test_other_" + str(number) + "[" + case["id"] + "]"
        name = "bindings-" + str(number) + ".json"
        write(tmp_path, name, bindings)
        intent["native_lanes"].append({**deepcopy(intent["native_lanes"][0]), "id": "other-" + str(number), "bindings": binding(tmp_path, name)})
    write(tmp_path, "crosswalk-intent.json", intent)
    monkeypatch.setattr(assets, "MAX_ROWS", 20)
    with pytest.raises(assets.AssetError, match="total native case budget"):
        assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)


def test_each_many_to_many_edge_requires_its_own_requirement_link(crossed, tmp_path):
    # Every requirement is linked somewhere, but the Cartesian many-to-many
    # row includes ungrounded identity-to-boundary and boundary-to-identity edges.
    book = assets.load(tmp_path, "book.json")
    book["requirements"].append({"id": "R-second", "source_ref": "fixture-contract.md", "assertion": "Separate boundary obligation"})
    book["conditions"][-1]["requirements"] = ["R-second"]
    for card in book["scenarios"][-3:]:
        card["requirements"] = ["R-second"]
    write(tmp_path, "book.json", book)
    write(tmp_path, "strength.json", assets.strength_prepare("risk-intent.json", "book.json", tmp_path))
    bundle_intent = assets.load(tmp_path, "cross-bundle-intent.json")
    bundle_intent["books"][0]["strength_refs"] = [binding(tmp_path, "strength.json")]
    write(tmp_path, "cross-bundle-intent.json", bundle_intent)
    write(tmp_path, "cross-bundle.json", assets.bundle_prepare("cross-bundle-intent.json", "cross-parent.json", tmp_path))
    crossed["bundle_sha"] = assets.digest_file(tmp_path, "cross-bundle.json")
    model = crossed["model"]
    model["requirements"].append({"id": "native-second", "source": "fixture-contract.md", "assertion": "Separate obligation"})
    model["journeys"][0]["factors"] = {"input": ["one"]}
    model["journeys"].append({**deepcopy(model["journeys"][0]), "id": "boundary", "requirements": ["native-second"]})
    write(tmp_path, "native-manifest.json", model)
    native, _ = assets.native_modules()
    plan = native.plan(model, tmp_path)
    bindings = crossed["bindings"]
    bindings["manifest_sha256"] = native.digest(model)
    bindings["cases"] = [{"id": c["id"], "test_ref": "native_test.py", "selector": "native_test.py::test_rename[" + c["id"] + "]",
                          "asserted_requirements": c["requirements"]} for c in plan["cases"]]
    write(tmp_path, "native-bindings.json", bindings)
    intent = crossed["intent"]
    lane = intent["native_lanes"][0]
    lane.update(manifest=binding(tmp_path, "native-manifest.json"), bindings=binding(tmp_path, "native-bindings.json"))
    intent["mappings"][0]["native_cases"] = [{"lane_id": "native", "case_id": c["id"], "journey": c["journey"], "parameters": c["parameters"]} for c in plan["cases"]]
    intent["mappings"][0]["requirement_links"].append({"book_id": "rename", "requirement_id": "R-second", "lane_id": "native", "native_requirement_id": "native-second"})
    write(tmp_path, "crosswalk-intent.json", intent)
    with pytest.raises(assets.AssetError, match="edge has no exact requirement link"):
        assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)


@pytest.fixture
def playwright_crossed(crossed, tmp_path):
    """Only synthetic parser/receipt fixture; real browser probe is separate."""
    native, _ = assets.native_modules()
    binding_value = crossed["bindings"]
    for case in binding_value["cases"]:
        case.update(selector="synthetic " + case["id"], project="chromium")
    write(tmp_path, "native-bindings.json", binding_value)
    lane = crossed["intent"]["native_lanes"][0]
    lane.update(runner="playwright", bindings=binding(tmp_path, "native-bindings.json"))
    write(tmp_path, "crosswalk-intent.json", crossed["intent"])
    value = assets.crosswalk_prepare("crosswalk-intent.json", "cross-bundle.json", crossed["bundle_sha"], tmp_path)
    write(tmp_path, "crosswalk.json", value)
    crossed["cross_sha"] = assets.digest_file(tmp_path, "crosswalk.json")
    receipt = assets.load(tmp_path, "crosswalk-execution.json")
    receipt["crosswalk_file_sha256"] = crossed["cross_sha"]
    write(tmp_path, "crosswalk-execution.json", receipt)
    index = assets.load(tmp_path, "native-index.json")
    index["crosswalk_file_sha256"] = crossed["cross_sha"]
    write(tmp_path, "native-index.json", index)
    report = {"errors": [], "config": {"rootDir": str(tmp_path)}, "stats": {"startTime": "2026-09-29T01:00:10Z", "duration": 10},
        "suites": [{"suites": [], "specs": [{"file": "native_test.py", "title": case["selector"], "tests": [{
            "projectName": "chromium", "expectedStatus": "passed", "status": "expected", "results": [{"retry": 0, "status": "passed"}]}]}
            for case in binding_value["cases"]]}]}
    write(tmp_path, "native-report.json", report)
    execution = assets.load(tmp_path, "native-execution.json")
    execution.update(runner="playwright", bindings_sha256=native.digest(binding_value))
    write(tmp_path, "native-execution.json", execution)
    refresh_cross_evidence(tmp_path)
    assert cross_audit(tmp_path, crossed)["claim"] == "crosswalk_accounting_complete"
    return crossed


@pytest.mark.parametrize("change,detail", [
    (lambda r: r["stats"].update(startTime="2026-09-28T01:00:10Z"), "stale"),
    (lambda r: r["stats"].update(startTime="2026-09-30T01:00:10Z"), "future"),
    (lambda r: r["stats"].update(startTime="2026-09-29T01:00:10"), "timezone"),
    (lambda r: r["stats"].update(duration=100000), "duration"),
    (lambda r: r["stats"].update(duration=True), "duration"),
    (lambda r: r.pop("stats"), "timestamps"),
    (lambda r: r["suites"][0]["specs"][0]["tests"][0]["results"].insert(0, {"retry": 0, "status": "failed"}), "raw outcomes conflict"),
])
def test_playwright_old_time_or_retry_cannot_hide_behind_matching_pass_metadata(playwright_crossed, tmp_path, change, detail):
    raw = assets.load(tmp_path, "native-report.json")
    change(raw)
    write(tmp_path, "native-report.json", raw)
    refresh_cross_evidence(tmp_path)
    report = cross_audit(tmp_path, playwright_crossed)
    assert report["claim"] == "crosswalk_incomplete"
    assert detail in report["execution_gaps"][0]["detail"]
    assert report["native_audits"][0]["native_audit"]["claim"] == "complete_against_frozen_scope"
