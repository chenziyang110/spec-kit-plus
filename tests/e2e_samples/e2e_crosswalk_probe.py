"""Fresh bounded browser/native crosswalk probe; not model visual assessment.

Builds ordinary scenario/risk/bundle/crosswalk assets before invoking the existing
native runner. Observations derive from actual Playwright attempts and independent
durable bytes. Failed retries and empty selections keep their original reports.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[2]
TARGET = "disposable-local-chromium"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def ref(root, name):
    return {"path": name, "sha256": sha(root / name)}


def freeze(root, route, model, plan, assets, scenarios):
    dimensions = ["happy_path", "persistence_consistency"]
    contract = (root / "request.txt").read_text(encoding="utf-8").strip()
    expected = {"happy_path": "Native browser assertion observes Saved after clicking Save",
                "persistence_consistency": "Independent durable JSON value equals requested-value"}
    conditions = [{"id": "C-" + d, "operation": "save", "dimension": d, "kind": "example", "title": d,
        "source_refs": ["request.txt"], "requirements": ["save-persists-input"],
        "variants": [{"id": "main", "input": "Enter requested-value and Save", "expected": expected[d]}]} for d in dimensions]
    card = {"id": "save-durable", "operation": "save", "title": "Save and independently read durable bytes",
        "dimensions": dimensions, "requirements": ["save-persists-input"], "technique": ["state-transition"], "priority": "high",
        "preconditions": ["Own disposable application, browser process, and state directory"],
        "steps": [{"id": "save", "actor": "runner", "action": "Execute actual browser fill/click/assert and independent filesystem readback",
                   "observe": "Preserve every native attempt and readback, including wrong side effects"}], "perturbations": [],
        "oracles": [{"id": "ui", "channel": "cli", "assertion": expected["happy_path"],
                     "check": "Native assertion must reach subsequent INDEPENDENT_READBACK; this is browser automation, not model vision"},
                    {"id": "effect", "channel": "filesystem", "assertion": expected["persistence_consistency"],
                     "check": "Read original durable JSON bytes independently after the native attempt"}],
        "execution": "runner", "cleanup": ["Native server closes in finally and runner process exits; retain own evidence directory"],
        "safety": ["Headless browser, loopback server and disposable data only"],
        "condition_bindings": [{"condition": "C-" + d, "variant": "main", "step_ids": ["save"],
                                "oracle_ids": ["ui" if d == "happy_path" else "effect"]} for d in dimensions]}
    book = {"schema_version": 2, "scope": "One explicitly bounded browser save fixture, " + route,
        "source_revision": model["source_revision"], "sources": model["sources"],
        "requirements": [{"id": "save-persists-input", "source_ref": "request.txt", "assertion": contract}],
        "operations": [{"id": "save", "title": "Save", "entrypoint": "Disposable local save page", "source_refs": ["app.cjs", "request.txt"],
            "assumptions": ["Own headless Chromium and loopback server"], "side_effects": True,
            "dimensions": {d: {"disposition": "applicable" if d in dimensions else "not_applicable",
                "reason": "This explicit fixture request tests saved-label versus durable effect; other dimensions are outside this bounded probe",
                "source_refs": ["request.txt"]} for d in scenarios.DIMENSIONS}, "checkpoints": [], "events": []}],
        "scenarios": [card], "conditions": conditions, "discovery_gaps": [], "exclusions": []}
    write(root, "scenario-book.json", book)
    risk = {"schema_version": 1, "scope": contract, "risks": [{"id": "false-success", "operation": "save",
        "requirements": ["save-persists-input"], "source_refs": ["request.txt"], "rationale": "Saved label can conceal corrupt durable data",
        "interactions": [{"id": "ui-effect", "conditions": [{"condition": c["id"], "variant": "main"} for c in conditions],
                          "timing": [], "bindings": [{"scenario": "save-durable", "step_ids": ["save"], "oracle_ids": ["ui", "effect"]}]}]}],
        "gaps": [], "exclusions": []}
    write(root, "risk-intent.json", risk)
    write(root, "strength.json", assets.strength_prepare("risk-intent.json", "scenario-book.json", root))
    parent = {"schema_version": 1, "scope": contract, "request_sources": [ref(root, "request.txt")],
        "obligations": [{"id": "save", "kind": "operation", "description": contract, "source_refs": ["request.txt"], "depends_on": []}],
        "gaps": [], "exclusions": []}
    write(root, "parent.json", parent)
    intent = {"schema_version": 1, "books": [{"id": "save", "path": "scenario-book.json", "scope_bindings": [{
        "scope_id": "save", "operation_ids": ["save"], "scenario_ids": ["save-durable"]}], "depends_on": [], "fixtures": [],
        "target": {"id": TARGET, "bindings": [ref(root, p) for p in ("app.cjs", "save.spec.cjs", "playwright.config.cjs")]},
        "strength_refs": [ref(root, "strength.json")]}]}
    write(root, "bundle-intent.json", intent)
    bundle = assets.bundle_prepare("bundle-intent.json", "parent.json", root)
    write(root, "bundle.json", bundle)
    bundle_sha = sha(root / "bundle.json")
    design = scenarios.check(book, root)
    obligations = [{"book_id": "save", "kind": "scenario", "id": "save-durable"}] + [
        {"book_id": "save", "kind": "condition", "id": c["id"]} for c in design["condition_obligations"]]
    mapping = {"schema_version": 1, "native_lanes": [{"id": "browser", "root": ".", "manifest": ref(root, "manifest.json"),
        "bindings": ref(root, "bindings.json"), "runner": "playwright", "target": TARGET, "book_ids": ["save"]}],
        "mappings": [{"id": "save-native", "rationale": "The native case executes this complete scenario and both Saved-label and independent durable-value conditions",
            "scenario_refs": [{"book_id": "save", "scenario_id": "save-durable", "step_ids": ["save"], "oracle_ids": ["ui", "effect"]}],
            "obligations": obligations, "native_cases": [{"lane_id": "browser", "case_id": c["id"], "journey": c["journey"],
                "parameters": c["parameters"]} for c in plan["cases"]], "requirement_links": [{"book_id": "save",
                "requirement_id": "save-persists-input", "lane_id": "browser", "native_requirement_id": "save-persists-input"}]}]}
    write(root, "crosswalk-intent.json", mapping)
    crosswalk = assets.crosswalk_prepare("crosswalk-intent.json", "bundle.json", bundle_sha, root)
    write(root, "crosswalk.json", crosswalk)
    run_id = "fresh-s2-" + route
    write(root, "scenario-execution-binding.json", {"schema_version": 1, "bundle_file_sha256": bundle_sha,
        "book_binding_sha256": bundle["books"][0]["binding_sha256"], "book_id": "save", "run_id": run_id, "target": TARGET})
    write(root, "crosswalk-execution-binding.json", {"schema_version": 1, "crosswalk_file_sha256": sha(root / "crosswalk.json"),
        "book_id": "save", "run_id": run_id, "target": TARGET})
    return book, bundle, run_id


def run_probe(output):
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, output / "probe-source.py")
    helpers = output / "helpers"
    helpers.mkdir()
    for name in ("e2e_assets.py", "e2e_scenarios.py", "e2e_runner.py", "e2e_coverage.py"):
        shutil.copyfile(REPO / "scripts/shared" / name, helpers / name)
    sys.path.insert(0, str(helpers))
    import e2e_assets as assets
    import e2e_scenarios as scenarios
    import e2e_coverage as coverage
    native = module("crosswalk_real_native", REPO / "tests/e2e_samples/e2e_playwright_probe.py")
    env = native.environment()
    assert not env["missing"], env
    rows = []
    for route in ("success", "failure", "retry", "empty"):
        root = output / route
        model, plan = native.fixture(root, route, env, coverage)
        book, bundle, run_id = freeze(root, route, model, plan, assets, scenarios)
        started = now()
        native_argv = [env["node"], str(Path(env["package"]) / "cli.js"), "test", "--config", "playwright.config.cjs"]
        if route == "empty":
            native_argv += ["--grep", "deliberate-empty-selection", "--pass-with-no-tests"]
        argv = [sys.executable, str(helpers / "e2e_runner.py"), "manifest.json", "--bindings", "bindings.json", "--root", str(root),
            "--runner", "playwright", "--target", TARGET, "--output-dir", "test-results/run", "--timeout", "60", "--", *native_argv]
        proc, command = native.recorded(argv, root, root, "native")
        report = assets.load(root, "test-results/run/native-report.json")
        attempts, suites = [], list(report["suites"])
        while suites:
            suite = suites.pop()
            suites.extend(suite.get("suites", []))
            for spec in suite.get("specs", []):
                for test in spec["tests"]:
                    attempts.extend(test["results"])
        assert [a["status"] for a in attempts] == {"success": ["passed"], "failure": ["failed"], "retry": ["failed", "passed"], "empty": []}[route]
        assert proc.returncode == {"success": 0, "failure": 1, "retry": 1, "empty": 2}[route]
        evidence = []

        def add(identity, kind, name):
            evidence.append({"id": identity, "kind": kind, "captured_at": now(), **ref(root, name)})

        add("bundle-execution-binding", "log", "scenario-execution-binding.json")
        add("crosswalk-execution-binding", "log", "crosswalk-execution-binding.json")
        add("action", "action_log", "native-command.json")
        add("native-report", "log", "test-results/run/native-report.json")
        results_path = "test-results/run/results.json" if (root / "test-results/run/results.json").exists() else None
        execution_path = "test-results/run/execution.json" if results_path else "test-results/run/error.json"
        add("native-execution", "log", execution_path)
        if results_path:
            add("native-results", "log", results_path)
        trace_attempts, readbacks = [], []
        for attempt in attempts:
            number = attempt["retry"]
            readback_lines = [s["text"].strip().split("INDEPENDENT_READBACK ", 1)[1] for s in attempt["stdout"] if "INDEPENDENT_READBACK " in s.get("text", "")]
            assert len(readback_lines) == 1
            observed = json.loads(readback_lines[0])
            path = Path(observed["state"])
            assert path.resolve().is_relative_to(root.resolve())
            durable = json.loads(path.read_text(encoding="utf-8"))
            assert durable["value"] == observed["actual"]
            effect = durable["value"] == "requested-value"
            readbacks.append({"retry": number, "actual": durable["value"], "path": path.relative_to(root).as_posix(), "sha256": sha(path)})
            name = "observations/attempt-" + str(number) + ".json"
            write(root, name, {"native_attempt": attempt, "readback": observed, "actual_durable": durable,
                "qualification": "Reached readback only after actual Saved assertion; parent independently reread these same durable bytes"})
            add("ui-" + str(number), "cli", name)
            add("effect-" + str(number), "filesystem", path.relative_to(root).as_posix())
            current = {"status": "passed" if effect and attempt["status"] == "passed" else "failed",
                "steps": [{"id": "save", "observation": "Actual browser attempt " + str(number), "evidence_ids": ["action"]}],
                "oracles": [{"id": "ui", "outcome": "passed", "observation": "Native Saved assertion reached subsequent independent readback", "evidence_ids": ["ui-" + str(number)]},
                    {"id": "effect", "outcome": "passed" if effect else "failed", "observation": json.dumps(durable), "evidence_ids": ["effect-" + str(number)]}],
                "cleanup": {"status": "passed", "observation": "Native finally closed own server and process exited; own evidence retained", "evidence_ids": ["action"]}}
            if current["status"] != "passed":
                current["reason"] = "Real independent durable value was " + durable["value"]
            trace_attempts.append(current)
        if not attempts:
            trace_attempts = [{"status": "not_run", "reason": "Actual native empty selection; original raw report and owner error retained"}]
        trace = {"schema_version": 1, "book_sha256": scenarios.sha(book), "source_revision": book["source_revision"], "run_id": run_id,
            "target": TARGET, "executor": {"kind": "runner", "name": "Actual Playwright automation and independent Python file readback; no model vision"},
            "started_at": started, "finished_at": now(), "evidence": evidence, "results": [{"id": "save-durable", "attempts": trace_attempts}]}
        write(root, "scenario-trace.json", trace)
        original = scenarios.audit(book, trace, root)
        write(root, "scenario-audit.json", original)
        write(root, "scenario-index.json", {"schema_version": 1, "bundle_file_sha256": sha(root / "bundle.json"), "runs": [{"book_id": "save",
            "bundle_file_sha256": sha(root / "bundle.json"), "book_binding_sha256": bundle["books"][0]["binding_sha256"],
            "trace": ref(root, "scenario-trace.json"), "execution_binding": ref(root, "scenario-execution-binding.json")} ]})
        write(root, "native-index.json", {"schema_version": 1, "crosswalk_file_sha256": sha(root / "crosswalk.json"), "runs": [{"lane_id": "browser",
            "results": ref(root, results_path) if results_path else None, "native_report": ref(root, "test-results/run/native-report.json"), "execution": ref(root, execution_path)}]})
        audit_argv = [sys.executable, "-E", "-s", str(helpers / "e2e_assets.py"), "crosswalk-audit", "crosswalk.json",
            "--expected-crosswalk-sha256", sha(root / "crosswalk.json"), "--expected-bundle-sha256", sha(root / "bundle.json"),
            "--scenario-runs", "scenario-index.json", "--native-runs", "native-index.json", "--root", str(root)]
        audit, audit_command = native.recorded(audit_argv, root, root, "crosswalk-audit")
        cross = json.loads(audit.stdout)
        assert audit.returncode == (0 if route == "success" else 1), cross
        assert len(cross["denominator"]["obligations"]) == 3
        rows.append({"route": route, "native_command": command, "audit_command": audit_command, "claim": cross["claim"],
            "scenario_statuses": original["statuses"], "native_attempt_statuses": [a["status"] for a in attempts], "readbacks": readbacks,
            "obligation_count": 3, "native_case_count": 1, "execution_gaps": cross["execution_gaps"]})
    result = {"schema_version": 1, "claim": "fresh_crosswalk_controls_observed", "routes": rows,
        "helper_inputs": [ref(output, "helpers/" + p.name) for p in helpers.iterdir() if p.is_file()],
        "environment": {**env, "python": sys.version}, "product_pass": False,
        "qualification": "Four separate bounded one-case books; real headless browser and independent durable readback. No model vision, product acceptance, authenticated time/agent identity or release claim."}
    write(output, "result.json", result)
    write(output, "output-manifest.json", {"files": [{"path": p.relative_to(output).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size}
        for p in sorted(output.rglob("*")) if p.is_file()]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    value = run_probe(args.output.resolve())
    print(json.dumps({"claim": value["claim"], "routes": [{"route": r["route"], "claim": r["claim"]} for r in value["routes"]]}))
