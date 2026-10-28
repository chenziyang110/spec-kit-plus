"""Repeatable E2E cost probe using an explicitly selected runtime and real clients.

Runtime protocol measurements are separate from application execution. Recorded
identity strings exercise guards; this adapter does not impersonate independent
agents or claim model perception/token measurements. Outputs are disposable.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Recorder:
    def __init__(self, root: Path):
        self.root = root
        self.calls: list[dict] = []
        root.mkdir(parents=True, exist_ok=True)

    def run(self, argv: list[str], cwd: Path, *, label: str, timeout: int = 60) -> tuple[subprocess.CompletedProcess, dict]:
        started = time.perf_counter()
        result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout)
        stem = f"{len(self.calls):04d}-{label}"
        stdout, stderr = self.root / f"{stem}.stdout", self.root / f"{stem}.stderr"
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        row = {"label": label, "argv": argv, "cwd": str(cwd), "exit_code": result.returncode,
               "elapsed_ms": (time.perf_counter() - started) * 1000,
               "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr),
               "stdout_ref": str(stdout), "stderr_ref": str(stderr),
               "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr)}
        self.calls.append(row)
        write_json(self.root / "commands.json", self.calls)
        return result, row


def make_plan(task_count: int) -> dict:
    """Seven stages for every frozen scope, including all unexecuted rows."""
    if task_count < 7 or task_count % 7:
        raise ValueError("task_count must be a positive multiple of seven")
    scope = [{"id": f"scope-{lane:03d}", "target": "cli", "operation": "save"}
             for lane in range(task_count // 7)]
    tasks = [{"id": f"T{lane:03d}-{stage}", "stage": stage, "scope_ids": [item["id"]],
              "inputs": ["request.txt"], "outputs": [f"tests/e2e/t{lane:03d}-{stage}.txt"],
              "acceptance": [{"id": "readback", "criterion": "Independent durable readback equals the requested value"}]}
             for lane, item in enumerate(scope) for stage in range(1, 8)]
    return {"mode": "execution", "scope": scope, "tasks": tasks}


def runtime_probe(runtime: Path, output: Path, sizes=(7, 70, 700), repeats: int = 3) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(output / "commands")
    measurements, assertions = [], []
    for count in sizes:
        project = output / f"tasks-{count}"
        project.mkdir()
        (project / "request.txt").write_text("Save requested-value and independently read it back.\n", encoding="utf-8")
        plan = make_plan(count)
        write_json(project / "plan.json", plan)
        revision = 1

        def call(action: str, *args: str, payload: dict | None = None, flag="--input-json", expected=0, label=None) -> dict:
            nonlocal revision
            argv = [str(runtime), "e2e", action, "--run-id", "probe", "--project-root", str(project), "--format", "json"]
            if action not in {"init", "status"}:
                argv += ["--expected-revision", str(revision)]
            argv += list(args)
            if payload is not None:
                path = project / f"input-{len(recorder.calls):04d}.json"
                write_json(path, payload)
                argv += [flag, "@" + str(path)]
            result, row = recorder.run(argv, project, label=label or f"{count}-{action}")
            envelope = json.loads(result.stdout)
            if (result.returncode == 0) != (expected == 0):
                raise AssertionError({"expected_success": expected == 0, "command": row, "envelope": envelope})
            data = envelope.get("data", {})
            revision = data.get("revision", revision)
            measurements.append({**row, "task_count": count, "action": action, "status": envelope["status"]})
            return envelope

        call("init", "--leader-id", "probe-leader", payload=plan)
        for iteration in range(repeats):
            status = call("status", label=f"{count}-pending-status-{iteration}")
            assert len(status["data"]["tasks"]) == count
        started = call("task-start", "--task-id", "T000-1", "--worker-id", "probe-worker")["data"]
        # A fresh process resumes the already persisted attempt. This is a
        # command-boundary interruption, not an unobserved crash during commit.
        resumed = call("status", label=f"{count}-interrupted-resume")["data"]
        task = next(t for t in resumed["tasks"] if t["id"] == "T000-1")
        assert task["packet"]["sha256"] == started["packet_sha256"] and task["attempt"] == 1
        assert task["status"] == "running" and resumed["product_pass"] is False
        call("task-start", "--task-id", "T000-1", "--worker-id", "probe-worker", expected=1)
        assertions.append({"id": f"resume-{count}", "passed": True, "packet_sha256": started["packet_sha256"],
                           "attempt": task["attempt"], "kind": "command-boundary persistence"})
        if count != sizes[0]:
            continue
        # Submit one actual CLI save/readback report, then replay the durable
        # oracle for the review. Remaining six stages stay visibly unexecuted.
        native = cli_rounds(project / "native", recorder)
        output_ref = project / "tests/e2e/t000-1.txt"
        output_ref.parent.mkdir(parents=True)
        write_json(output_ref, native)
        evidence = "tests/e2e/native-evidence.json"
        write_json(project / evidence, native)
        submission = copy.deepcopy(started["submission_template"])
        submission["outcome"] = "pass"
        submission["worker_result"] = {"task_id": "T000-1", "packet_id": started["packet_sha256"],
                                       "status": "success", "summary": "Actual CLI save and independent SQLite readback matched"}
        for check in submission["checks"]:
            check.update(status="passed", expected="requested-value", actual="requested-value",
                         reproduction="Run fixture CLI save, then query its SQLite database independently",
                         preconditions="Fresh disposable SQLite database; fixture hashes recorded", evidence_refs=[evidence])
        invalid = copy.deepcopy(submission)
        invalid["checks"] = []
        call("task-submit", "--task-id", "T000-1", "--worker-id", "probe-worker", payload=invalid, flag="--result-json", expected=1)
        call("task-submit", "--task-id", "T000-1", "--worker-id", "probe-worker", payload=submission, flag="--result-json")
        review = call("review-start", "--task-id", "T000-1", "--validator-id", "probe-validator")["data"]["review_template"]
        for check in review["checks"]:
            check.update(status="passed", method="replayed", expected="changed-value", actual=read_db(project / "native/data.sqlite"),
                         reproduction="Separate sqlite3 SELECT of persisted fixture row",
                         preconditions="Same isolated database after recorded CLI executions", evidence_refs=[evidence])
        assert all(c["actual"] == c["expected"] for c in review["checks"])
        call("review-submit", "--task-id", "T000-1", "--validator-id", "probe-validator", payload=review, flag="--result-json")
        accepted = call("task-accept", "--task-id", "T000-1", "--leader-id", "probe-leader")["data"]
        assert next(t for t in accepted["tasks"] if t["id"] == "T000-1")["status"] == "accepted"
        assert accepted["product_pass"] is False
        for iteration in range(repeats):
            call("status", label=f"{count}-accepted-status-{iteration}")
        (project / "request.txt").write_text("Changed one source input; fresh evidence is required.\n", encoding="utf-8")
        drift = call("status", expected=1, label=f"{count}-single-input-drift")["data"]
        assert "T000-1" in drift["stale_task_ids"] and drift["state_mutated"] is False and drift["product_pass"] is False
        assertions.append({"id": "single-input-drift", "passed": True, "stale_task_ids": drift["stale_task_ids"]})
    report = {"schema_version": 1, "runtime": str(runtime), "runtime_sha256": digest(runtime),
              "environment": {"platform": platform.platform(), "python": sys.version, "executable": sys.executable},
              "measurements": measurements, "assertions": assertions,
              "agent_tokens": {"status": "unavailable", "reason": "No model usage telemetry exposed to the probe"},
              "gaps": ["Only stage 1 has a protocol submission; remaining stage denominator is preserved",
                       "Recorded identities test runtime consistency, not independent agent semantic acceptance",
                       "Interruption measured at completed command boundary; mid-transaction crash not measured"]}
    write_json(output / "runtime-report.json", report)
    return report


CLI_SOURCE = '''import argparse,json,sqlite3
p=argparse.ArgumentParser();p.add_argument('value');p.add_argument('--fail-before-save',action='store_true');a=p.parse_args()
if a.fail_before_save: raise SystemExit(23)
with sqlite3.connect('data.sqlite') as c:
 c.execute('create table if not exists saved (id integer primary key, value text not null)')
 c.execute('insert or replace into saved values (1,?)',(a.value,))
print(json.dumps({'display':'Saved','value':a.value}))
'''


def read_db(path: Path) -> str:
    with sqlite3.connect(path) as conn:
        return conn.execute("select value from saved where id=1").fetchone()[0]


def cli_rounds(project: Path, recorder: Recorder) -> dict:
    project.mkdir(parents=True, exist_ok=False)
    app = project / "save.py"
    app.write_text(CLI_SOURCE, encoding="utf-8")
    rounds = []
    for label, value in [("cold", "requested-value"), ("repeat", "requested-value"), ("single-input-change", "changed-value")]:
        completed, measurement = recorder.run([sys.executable, str(app), value], project, label="cli-" + label)
        assert completed.returncode == 0 and read_db(project / "data.sqlite") == value
        rounds.append({**measurement, "expected": value, "actual": read_db(project / "data.sqlite"), "passed": True})
    failed, measurement = recorder.run([sys.executable, str(app), "recovered-value", "--fail-before-save"], project, label="cli-interrupted")
    assert failed.returncode == 23 and read_db(project / "data.sqlite") == "changed-value"
    recovered, recovery = recorder.run([sys.executable, str(app), "changed-value"], project, label="cli-resumed")
    assert recovered.returncode == 0 and read_db(project / "data.sqlite") == "changed-value"
    return {"surface": "cli", "fixture_sha256": digest(app), "rounds": rounds,
            "interruption": {"failure": measurement, "recovery": recovery, "passed": True},
            "oracle": "Independent sqlite3 query, not CLI display"}


WEB_HTML = b'''<!doctype html><html><meta charset="utf-8"><title>E2E disposable save fixture</title>
<label>Value <input id="value" aria-label="Value"></label><button id="save">Save</button><output id="status">Ready</output>
<script>document.querySelector('#save').onclick=async()=>{const r=await fetch('/save',{method:'POST',body:document.querySelector('#value').value});document.querySelector('#status').textContent=r.ok?'Saved':'Failed';};</script></html>'''


def web_rounds(output: Path) -> dict:
    """Actual Chromium, local HTTP server and an independent durable oracle."""
    from playwright.sync_api import sync_playwright
    output.mkdir(parents=True, exist_ok=False)
    db = output / "data.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("create table saved (id integer primary key, value text not null)")
        conn.execute("insert into saved values (1,'initial')")
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML)

        def do_POST(self):
            value = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
            with sqlite3.connect(db) as conn:
                conn.execute("update saved set value=? where id=1", (value,))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"saved")

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    rounds = []
    screenshots = []
    try:
        with sync_playwright() as pw:
            started = time.perf_counter()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            startup_ms = (time.perf_counter() - started) * 1000
            for label, value in [("cold", "requested-value"), ("repeat", "requested-value"), ("single-input-change", "changed-value")]:
                started = time.perf_counter()
                page.goto(url)
                page.get_by_label("Value").fill(value)
                page.get_by_role("button", name="Save", exact=True).click()
                page.locator("#status").get_by_text("Saved", exact=True).wait_for()
                actual = read_db(db)
                assert actual == value
                capture = output / f"{label}.png"
                page.screenshot(path=str(capture))
                screenshots.append({"path": str(capture), "sha256": digest(capture)})
                rounds.append({"label": label, "elapsed_ms": (time.perf_counter() - started) * 1000,
                               "browser_actions": 4, "independent_reads": 1, "expected": value, "actual": actual, "passed": True})
            page.goto(url)
            page.get_by_label("Value").fill("interrupted-value")
            page.close()  # Client process/page boundary before the save operation.
            assert read_db(db) == "changed-value"
            started = time.perf_counter()
            page = browser.new_page()
            page.goto(url)
            page.get_by_label("Value").fill("recovered-value")
            page.get_by_role("button", name="Save", exact=True).click()
            page.locator("#status").get_by_text("Saved", exact=True).wait_for()
            assert read_db(db) == "recovered-value"
            rounds.append({"label": "interruption-recovery", "elapsed_ms": (time.perf_counter() - started) * 1000,
                           "browser_actions": 5, "independent_reads": 2, "expected": "recovered-value", "actual": read_db(db), "passed": True,
                           "interruption_point": "Filled input, closed page before Save; prior persisted value survived"})
            result = {"surface": "web", "driver": "Actual Python Playwright Chromium", "browser_version": browser.version,
                      "startup_ms": startup_ms, "url": url, "fixture_sha256": hashlib.sha256(WEB_HTML).hexdigest(),
                      "rounds": rounds, "screenshots": screenshots, "oracle": "Direct SQLite read independent of DOM success label",
                      "gaps": ["Python browser driver does not establish optional Playwright Test adapter behavior",
                               "Screenshots are captured; model visual assessment is separately pending"]}
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    write_json(output / "surface-report.json", result)
    return result


def desktop_rounds(output: Path) -> dict:
    """Real Tk event loop and filesystem; widget driving is not model vision."""
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name("desktop_rename.py")
    spec = importlib.util.spec_from_file_location("optimization_desktop_sample", source)
    assert spec and spec.loader
    sample = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = sample
    spec.loader.exec_module(sample)
    root = None
    actions = 0

    def client(sandbox: Path):
        nonlocal root
        root = sample.tk.Tk()
        root.withdraw()
        app = sample.RenameClient(root, sample.Store(sandbox))
        # Exercise real native widgets while keeping the user's foreground
        # clear. Alpha-zero rendering is explicitly not visual evidence.
        root.attributes("-alpha", 0.0)
        root.deiconify()
        root.update()
        return app

    def click(app, widget):
        nonlocal actions
        widget.event_generate("<Enter>")
        widget.event_generate("<ButtonPress-1>", x=8, y=8)
        app.root.update()
        widget.event_generate("<ButtonRelease-1>", x=8, y=8)
        app.root.update()
        actions += 1

    def enter(app, value):
        nonlocal actions
        app.entry.delete(0, "end")
        app.entry.insert(0, value)
        app.root.update()
        actions += 1

    def select(app, name):
        nonlocal actions
        names = app.listbox.get(0, "end")
        app.listbox.selection_clear(0, "end")
        app.listbox.selection_set(names.index(name))
        app.listbox.event_generate("<<ListboxSelect>>")
        app.root.update()
        actions += 1

    def oracle(sandbox):
        return {p.name: p.read_bytes().hex() for p in sandbox.iterdir() if p.name != sample.MARKER}

    rounds = []
    try:
        started = time.perf_counter()
        sandbox = sample.create_sandbox(output / "sandbox")
        app = client(sandbox)
        startup_ms = (time.perf_counter() - started) * 1000
        current_name = "A.txt"
        for label, value in [("cold", "B.txt"), ("repeat", "C.txt"), ("single-input-change", "文档.txt")]:
            started, before_actions = time.perf_counter(), actions
            select(app, current_name)
            click(app, app.rename_button)
            enter(app, value)
            click(app, app.confirm_button)
            assert app.status.get() == f"Renamed to {value}"
            assert oracle(sandbox) == {value: sample.SENTINEL.hex(), "taken.txt": sample.OCCUPIED.hex()}
            rounds.append({"label": label, "elapsed_ms": (time.perf_counter() - started) * 1000, "widget_actions": actions - before_actions,
                           "independent_reads": 1, "expected_name": value, "actual": oracle(sandbox), "passed": True})
            current_name = value
        select(app, current_name)
        click(app, app.rename_button)
        enter(app, "not-saved.txt")
        app.cancel()
        root.destroy()
        root = None
        assert oracle(sandbox) == {"文档.txt": sample.SENTINEL.hex(), "taken.txt": sample.OCCUPIED.hex()}
        started, before_actions = time.perf_counter(), actions
        app = client(sandbox)
        select(app, "文档.txt")
        click(app, app.rename_button)
        enter(app, "recovered.txt")
        click(app, app.confirm_button)
        assert oracle(sandbox) == {"recovered.txt": sample.SENTINEL.hex(), "taken.txt": sample.OCCUPIED.hex()}
        rounds.append({"label": "interruption-recovery", "elapsed_ms": (time.perf_counter() - started) * 1000,
                       "widget_actions": actions - before_actions, "independent_reads": 2, "actual": oracle(sandbox), "passed": True,
                       "interruption_point": "Closed root with unconfirmed dialog; reopened client against same sandbox"})
        result = {"surface": "desktop", "driver": "Native Windows Tk event_generate, alpha-zero window",
                  "tk_version": sample.tk.TkVersion, "fixture_sha256": digest(source), "startup_ms": startup_ms,
                  "rounds": rounds, "oracle": "Independent filesystem names and exact bytes, not status label",
                  "gaps": ["Widget actions and invisible rendering do not establish visual-model observation or OS-level input automation",
                           "No screenshot/visual assessment; native CUA control unavailable in this session"]}
    finally:
        if root is not None:
            root.destroy()
    write_json(output / "surface-report.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sizes", default="7,70,700")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--surface", choices=["runtime", "web", "desktop"], default="runtime")
    args = parser.parse_args()
    if args.surface != "runtime":
        result = (web_rounds if args.surface == "web" else desktop_rounds)(args.output.resolve())
        print(json.dumps(result, ensure_ascii=False))
        return
    if args.runtime is None:
        parser.error("--runtime is required for runtime measurement")
    report = runtime_probe(args.runtime.resolve(), args.output.resolve(), tuple(map(int, args.sizes.split(","))), args.repeats)
    print(json.dumps({"report": str(args.output.resolve() / "runtime-report.json"), "runtime_sha256": report["runtime_sha256"],
                      "runtime_calls": len(report["measurements"]), "assertions": report["assertions"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
