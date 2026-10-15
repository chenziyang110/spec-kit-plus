"""Real Playwright Test -> existing native runner -> coverage auditor probe.

No parser reports are manufactured. Each route freezes a new one-case book and
uses an actual Chromium page plus independently read durable JSON bytes. The
failure and retry routes deliberately inject a wrong side effect after a success
label, demonstrating that the oracle catches it and history remains nonpassing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[2]
HELPERS = REPO / "scripts/shared"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_coverage(path: Path | None = None):
    spec = importlib.util.spec_from_file_location("playwright_probe_coverage", path or HELPERS / "e2e_coverage.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def environment(node: Path | None = None, package: Path | None = None, chromium: Path | None = None) -> dict:
    runtime_root = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    node = node or Path(os.environ.get("SPECIFY_E2E_PLAYWRIGHT_NODE", str(runtime_root / "bin/node.exe")))
    package = package or Path(os.environ.get("SPECIFY_E2E_PLAYWRIGHT_PACKAGE", str(runtime_root / "node_modules/playwright")))
    chromium = chromium or Path(os.environ.get("SPECIFY_E2E_CHROMIUM", str(Path.home() / "AppData/Local/ms-playwright/chromium-1161/chrome-win/chrome.exe")))
    missing = [str(p) for p in (node, package / "cli.js", package / "test.js", chromium) if not p.is_file()]
    return {"node": str(node.resolve()), "package": str(package.resolve()), "chromium": str(chromium.resolve()), "missing": missing}


APP = r'''const http = require('node:http');
const fs = require('node:fs');
const html = '<!doctype html><html><meta charset="utf-8"><title>Disposable save</title><label>Value <input aria-label="Value"></label><button>Save</button><output>Ready</output><script>document.querySelector("button").onclick=async()=>{const r=await fetch("/save",{method:"POST",body:document.querySelector("input").value});document.querySelector("output").textContent=r.ok?"Saved":"Failed"}</script></html>';
exports.start = async function (statePath, wrongSideEffect) {
  fs.writeFileSync(statePath, JSON.stringify({value:'initial'}));
  const server = http.createServer((req,res)=>{
    if (req.method === 'GET') { res.writeHead(200, {'Content-Type':'text/html; charset=utf-8'});res.end(html);return; }
    let body='';req.on('data',chunk=>body+=chunk);req.on('end',()=>{
      const value=wrongSideEffect?'wrong-side-effect':body;
      fs.writeFileSync(statePath+'.tmp',JSON.stringify({value}));fs.renameSync(statePath+'.tmp',statePath);
      res.writeHead(200);res.end('saved');
    });
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  return {url:'http://127.0.0.1:'+server.address().port+'/',close:()=>new Promise(resolve=>server.close(resolve))};
};
'''


def fixture(root: Path, route: str, env: dict, coverage=None) -> tuple[dict, dict]:
    root.mkdir(parents=True, exist_ok=False)
    coverage = coverage or load_coverage()
    (root / "app.cjs").write_text(APP, encoding="utf-8")
    (root / "request.txt").write_text("Save the entered value unchanged. A Saved label alone is insufficient; independently read persisted bytes.\n", encoding="utf-8")
    model = {"schema_version": 1, "scope": f"Disposable real browser save, {route} route", "source_revision": "fixture-sha256:" + sha(root / "app.cjs"),
             "sources": [{"path": name, "sha256": sha(root / name)} for name in ("app.cjs", "request.txt")], "exclusions": [],
             "requirements": [{"id": "save-persists-input", "source": "request.txt", "assertion": "Persisted value exactly equals the entered value; success labels cannot substitute"}],
             "journeys": [{"id": "save", "requirements": ["save-persists-input"], "steps": ["enter value", "click Save", "read persisted bytes independently"],
                           "factors": {"value": ["requested-value"]}, "strength": "exhaustive"}]}
    plan = coverage.plan(model, root)
    identity = plan["cases"][0]["id"]
    selector = f"save durable value {identity}"
    module_path = (Path(env["package"]) / "test.js").as_posix()
    config = "const { defineConfig } = require(" + json.dumps(module_path) + ");\nmodule.exports=defineConfig({testDir:'.',testMatch:'save.spec.cjs',workers:1,retries:" + ("1" if route == "retry" else "0") + ",timeout:10000,projects:[{name:'chromium',use:{browserName:'chromium',headless:true,launchOptions:{executablePath:" + json.dumps(Path(env["chromium"]).as_posix()) + "}}}],outputDir:'test-results/artifacts'});\n"
    (root / "playwright.config.cjs").write_text(config, encoding="utf-8")
    test = "const {test,expect}=require(" + json.dumps(module_path) + ");\n" + r'''const fs=require('node:fs');const path=require('node:path');const app=require('./app.cjs');
test(SELECTOR,async({page},info)=>{
  const state=path.join(__dirname,'test-results','durable-'+process.env.SPECIFY_E2E_RUN_ID+'-'+info.retry+'.json');
  fs.mkdirSync(path.dirname(state),{recursive:true});
  const fault=ROUTE==='failure'||(ROUTE==='retry'&&info.retry===0);
  const server=await app.start(state,fault);
  try {
    await page.goto(server.url);
    await page.getByLabel('Value',{exact:true}).fill('requested-value');
    await page.getByRole('button',{name:'Save',exact:true}).click();
    await expect(page.locator('output')).toHaveText('Saved');
    const actual=JSON.parse(fs.readFileSync(state,'utf8'));
    console.log('INDEPENDENT_READBACK '+JSON.stringify({retry:info.retry,expected:'requested-value',actual:actual.value,state}));
    await info.attach('durable-readback',{body:Buffer.from(JSON.stringify(actual)),contentType:'application/json'});
    await page.screenshot({path:path.join(__dirname,'test-results','capture-'+process.env.SPECIFY_E2E_RUN_ID+'-'+info.retry+'.png')});
    expect(actual.value,'Independent durable side effect must equal entered value').toBe('requested-value');
  } finally { await server.close(); }
});
'''
    test = test.replace("SELECTOR", json.dumps(selector)).replace("ROUTE", json.dumps(route))
    (root / "save.spec.cjs").write_text(test, encoding="utf-8")
    bindings = {"schema_version": 1, "manifest_sha256": plan["manifest_sha256"],
                "test_sources": [{"path": name, "sha256": sha(root / name)} for name in ("save.spec.cjs", "playwright.config.cjs")],
                "cases": [{"id": identity, "test_ref": "save.spec.cjs", "selector": selector, "project": "chromium", "asserted_requirements": ["save-persists-input"]}]}
    write(root / "manifest.json", model)
    write(root / "bindings.json", bindings)
    write(root / "book.json", plan)
    return model, plan


def recorded(argv: list[str], cwd: Path, target: Path, label: str) -> tuple[subprocess.CompletedProcess, dict]:
    started = datetime.now(timezone.utc).isoformat()
    timer = time.perf_counter()
    actual = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=90)
    stdout, stderr = target / f"{label}.stdout", target / f"{label}.stderr"
    stdout.write_bytes(actual.stdout)
    stderr.write_bytes(actual.stderr)
    row = {"argv": argv, "cwd": str(cwd), "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
           "exit_code": actual.returncode, "elapsed_ms": (time.perf_counter() - timer) * 1000,
           "stdout_bytes": len(actual.stdout), "stderr_bytes": len(actual.stderr),
           "stdout_ref": str(stdout), "stdout_sha256": sha(stdout), "stderr_ref": str(stderr), "stderr_sha256": sha(stderr)}
    write(target / f"{label}-command.json", row)
    return actual, row


def probe(output: Path, env: dict) -> dict:
    if env["missing"]:
        raise FileNotFoundError("Existing runtime unavailable: " + ", ".join(env["missing"]))
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), output / "probe-source.py")
    # Freeze byte-equivalent existing helpers for reproducibility while other
    # workers edit source owners. Their source and copied hashes both bind.
    frozen_helpers = output / "helpers"
    frozen_helpers.mkdir()
    helper_inputs = []
    for name in ("e2e_runner.py", "e2e_coverage.py"):
        source, target = HELPERS / name, frozen_helpers / name
        shutil.copyfile(source, target)
        helper_inputs.append({"source": str(source), "source_sha256": sha(source), "frozen": str(target), "frozen_sha256": sha(target)})
    version, version_command = recorded([env["node"], str(Path(env["package"]) / "cli.js"), "--version"], REPO, output, "playwright-version")
    if version.returncode:
        raise RuntimeError(version.stderr.decode("utf-8", "replace"))
    coverage = load_coverage(frozen_helpers / "e2e_coverage.py")
    rows = []
    for route in ("success", "failure", "retry", "empty"):
        root = output / route
        model, plan = fixture(root, route, env, coverage)
        native_argv = [env["node"], str(Path(env["package"]) / "cli.js"), "test", "--config", "playwright.config.cjs"]
        if route == "empty":
            native_argv += ["--grep", "nothing-matches-this-deliberate-empty-selection", "--pass-with-no-tests"]
        argv = [sys.executable, str(frozen_helpers / "e2e_runner.py"), "manifest.json", "--bindings", "bindings.json", "--root", str(root),
                "--runner", "playwright", "--target", "disposable-local-chromium", "--output-dir", "test-results/run", "--timeout", "60", "--", *native_argv]
        actual, command = recorded(argv, root, root, "wrapper")
        run = root / "test-results/run"
        native = json.loads((run / "native-report.json").read_text(encoding="utf-8"))
        assert native["errors"] == [], "Browser runner global errors cannot satisfy a route"
        suites = list(native["suites"])
        attempts = []
        while suites:
            suite = suites.pop()
            suites.extend(suite.get("suites", []))
            for native_spec in suite.get("specs", []):
                for native_test in native_spec["tests"]:
                    attempts.extend({"retry": a["retry"], "status": a["status"], "has_error": bool(a.get("error") or a.get("errors"))} for a in native_test["results"])
        assert [(a["retry"], a["status"]) for a in attempts] == {
            "success": [(0, "passed")], "failure": [(0, "failed")],
            "retry": [(0, "failed"), (1, "passed")], "empty": []}[route]
        coverage_report = run / "coverage.json"
        row = {"route": route, "command": command, "case_count": len(plan["cases"]), "manifest_sha256": plan["manifest_sha256"],
               "native_report_sha256": sha(run / "native-report.json"), "native_stats": native["stats"], "native_attempts": attempts,
               "durable_readbacks": [{"path": str(p), "sha256": sha(p), "value": json.loads(p.read_text())["value"]} for p in sorted((root / "test-results").glob("durable-*.json"))]}
        if coverage_report.exists():
            report = json.loads(coverage_report.read_text(encoding="utf-8"))
            results = json.loads((run / "results.json").read_text(encoding="utf-8"))
            # Independent stateless audit re-reads the frozen book and exact
            # native evidence. It does not replace the native execution report.
            assert coverage.audit(model, results, root) == report
            audit_argv = [sys.executable, str(frozen_helpers / "e2e_coverage.py"), "audit", "manifest.json", "--root", str(root), "--results", "test-results/run/results.json"]
            audited, audit_command = recorded(audit_argv, root, root, "auditor")
            row.update(claim=report["claim"], statuses=report["statuses"], runner_exit_code=report["runner_exit_code"], auditor_command=audit_command,
                       gaps=report["gaps"])
            expected = {"success": (0, "passed"), "failure": (1, "failed"), "retry": (1, "flaky"), "empty": (1, "not_run")}[route]
            assert actual.returncode == expected[0] and audited.returncode == expected[0]
            assert report["statuses"][expected[1]] == 1
            assert (report["claim"] == "complete_against_frozen_scope") == (route == "success")
        else:
            error = json.loads((run / "error.json").read_text(encoding="utf-8"))
            assert route == "empty" and actual.returncode == 2 and error["claim"] == "invalid"
            assert error["exit_code"] == 0 and error["error"] == "Playwright report contains zero mapped tests"
            row.update(claim=error["claim"], error=error["error"], statuses=None,
                       gap="Current Playwright empty-selection adapter rejects before deriving not_run coverage; frozen full plan and raw empty report retained")
        assert len(row["durable_readbacks"]) == {"success": 1, "failure": 1, "retry": 2, "empty": 0}[route]
        expected_values = {"success": ["requested-value"], "failure": ["wrong-side-effect"], "retry": ["wrong-side-effect", "requested-value"], "empty": []}[route]
        assert [entry["value"] for entry in row["durable_readbacks"]] == expected_values
        rows.append(row)
    result = {"schema_version": 1, "item": "V1-real-playwright", "status": "submitted_for_independent_validation",
              "environment": {**env, "python": sys.version, "platform": platform.platform(), "playwright_version": version.stdout.decode().strip()},
              "helper_inputs": helper_inputs, "routes": rows, "probe_sha256": sha(Path(__file__)),
              "node_sha256": sha(Path(env["node"])), "chromium_sha256": sha(Path(env["chromium"])),
              "playwright_package_sha256": sha(Path(env["package"]) / "package.json"),
              "probe_completed": True, "product_pass": False,
              "coverage_derived_for_every_route": all(row["claim"] != "invalid" for row in rows),
              "gaps": [row["gap"] for row in rows if "gap" in row] + ["Captured pixels and browser automation are not a completed model visual assessment", "No release or cloud/platform-wide claim"]}
    write(output / "result.json", result)
    paths = [p for p in output.rglob("*") if p.is_file()]
    write(output / "output-manifest.json", {"files": [{"path": p.relative_to(output).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(paths)]})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args()
    result = probe(args.output.resolve(), environment(args.node, args.package, args.chromium))
    print(json.dumps({"result": str(args.output.resolve() / "result.json"), "probe_completed": result["probe_completed"],
                      "coverage_derived_for_every_route": result["coverage_derived_for_every_route"],
                      "routes": [{key: row[key] for key in ("route", "claim", "statuses")} for row in result["routes"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
