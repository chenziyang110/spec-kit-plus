"""Real client -> native pytest phases -> frozen-plan audit integration.

The disposable sample has its own 32-code-point policy. This tests Tk widget
interaction and independent file effects, not model perception or real init.
Missing Tk/display is a failure when SPECIFY_E2E_REQUIRE_DESKTOP=1.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPERS = ("e2e_coverage.py", "e2e_runner.py", "e2e_pytest_reporter.py")
# All 34 real-widget journeys can exceed a minute on an isolated native desktop.
# Keep the child budget finite and reserve another 30 seconds for its parent.
DESKTOP_RUN_TIMEOUT = 180

# These conditions come from the sample's explicit contract, not OS-wide rules.
INPUTS = [
    ("empty", "", "empty"), ("whitespace", "   ", "whitespace"),
    ("dot", ".", "reserved"), ("parent", "..", "reserved"),
    ("marker", ".spec-kit-e2e-sandbox", "reserved"),
    ("slash", "a/b", "disallowed"), ("backslash", "a\\b", "disallowed"),
    ("colon", "a:b", "disallowed"), ("wildcard", "a?b", "disallowed"),
    ("quote", 'a"b', "disallowed"), ("nul", "a\x00b", "disallowed"),
    ("newline", "a\nb", "disallowed"),
    ("ascii-over", "x" * 33, "exceeds"), ("unicode-over", "文" * 33, "exceeds"),
]

# This file is written as an ordinary child test, not as a fabricated report.
HARNESS = r'''"""Widget-driven sample obligations; no visual-model execution is claimed."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import pytest
import desktop_rename as sample

CASES = json.loads(Path("cases.json").read_text(encoding="utf-8"))


def click(app, control):
    app.root.update()
    control.event_generate("<Enter>")
    control.event_generate("<ButtonPress-1>", x=8, y=8)
    app.root.update()
    control.event_generate("<ButtonRelease-1>", x=8, y=8)
    app.root.update()


def enter(app, name):
    app.entry.delete(0, "end")
    app.entry.insert(0, name)
    app.root.update()
    assert app.name.get() == name, "The intended input did not reach the widget"


def readback(path):
    # Never use the product's Store.readback to validate the same implementation.
    return {p.name: p.read_bytes() for p in path.iterdir() if p.name != sample.MARKER}


def mutate(path, event):
    source = path / "A.txt"
    if event == "delete":
        source.unlink()
    elif event == "rename":
        source.rename(path / "external.txt")
    elif event == "replace":
        source.rename(path / "original-kept.txt")
        source.write_bytes(b"distinct replacement; preserve it")
    elif event == "modify":
        source.write_bytes(b"modified content; preserve it")
    else:
        raise AssertionError("Unknown external event")


@pytest.fixture
def client(tmp_path, request):
    sandbox = sample.create_sandbox(tmp_path / "sandbox")
    root = None
    errors = []
    try:
        # No import/display skip in the child: an unavailable client is not a pass.
        root = sample.tk.Tk()
        root.report_callback_exception = lambda kind, value, trace: errors.append(str(value))
        app = sample.RenameClient(root, sample.Store(sandbox))
        root.update()
        yield app
    finally:
        if root is not None:
            root.destroy()
        shutil.rmtree(sandbox)
        assert not sandbox.exists(), "Disposable client files were not cleaned up"
        print("DESKTOP_CLEANUP " + request.node.nodeid, flush=True)
        assert not errors, "Tk callback failure: " + repr(errors)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_client(case, client):
    assert sample.LIMIT == 32, "Update the source-grounded matrix when its contract changes"
    path = client.store.root
    before = readback(path)
    kind = case["kind"]
    if kind == "absent":
        mutate(path, "delete")
        before = readback(path)
        click(client, client.rename_button)
        assert client.dialog is None
        assert "no longer exists" in client.status.get()
    else:
        click(client, client.rename_button)
        assert client.dialog is not None and client.dialog.winfo_ismapped()
        name = case.get("name", "B.txt")
        if kind == "mutation" and case["checkpoint"] == "dialog-open":
            assert client.name.get() == "A.txt"
            mutate(path, case["event"])
            before = readback(path)
        enter(client, name)
        if kind == "mutation" and case["checkpoint"] == "before-confirm":
            mutate(path, case["event"])
            before = readback(path)
        if kind in {"conflict", "combined"}:
            (path / name).write_bytes(b"independent actor owns the target")
            if kind == "combined":
                mutate(path, case["event"])
            before = readback(path)
        if os.environ.get("SPECIFY_E2E_SAMPLE_UNEXPECTED_DELETE") == case["id"]:
            # Deliberate negative-control fault: not a claim of a product defect.
            mutate(path, "delete")
            assert not (path / "A.txt").exists()
            print("DESKTOP_NEGATIVE_CONTROL " + case["id"], flush=True)
        click(client, client.confirm_button)
        if kind in {"invalid", "mutation", "conflict", "combined", "recovery"}:
            assert client.dialog is not None
            assert case["error"] in client.error.get()
            assert "Not renamed:" in client.status.get()
            assert readback(path) == before
            click(client, client.cancel_button)
            assert client.dialog is None
            click(client, client.refresh_button)
            assert set(client.listbox.get(0, "end")) == set(before)
            if kind == "recovery":
                click(client, client.rename_button)
                enter(client, "B.txt")
                click(client, client.confirm_button)
                client.root.after_idle(client.confirm)  # A queued duplicate intent.
                client.root.update()
                assert client.dialog is None
                assert client.status.get() == "Renamed to B.txt"
                before = {"B.txt": sample.SENTINEL, "taken.txt": sample.OCCUPIED}
        elif kind == "same":
            assert client.dialog is None and client.status.get() == "Name unchanged"
        else:
            assert kind == "valid"
            assert client.dialog is None and client.status.get() == f"Renamed to {name}"
            before = {name: sample.SENTINEL, "taken.txt": sample.OCCUPIED}
            assert name in client.listbox.get(0, "end")
    assert readback(path) == before
    client.root.update()
    assert client.status_label.winfo_ismapped()
    assert client.status_label.winfo_height() > 1
    assert (client.status_label.winfo_rooty() + client.status_label.winfo_height()
            < client.root.winfo_rooty() + client.root.winfo_height())
    print("DESKTOP_OBSERVATION " + json.dumps({
        "id": case["id"], "kind": kind, "checkpoint": case.get("checkpoint"),
        "status": client.status.get(),
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in before.items()},
    }, ensure_ascii=True), flush=True)
'''


def definitions():
    cases = [dict(variant=v, kind="valid", name=n) for v, n in (
        ("normal", "B.txt"), ("unicode", "文档.txt"),
        ("below", "x" * 31), ("at", "x" * 32), ("unicode-at", "文" * 32),
    )]
    cases += [dict(variant=v, kind="invalid", name=n, error=e) for v, n, e in INPUTS]
    for checkpoint in ("dialog-open", "before-confirm"):
        for event in ("delete", "rename", "replace", "modify"):
            cases.append(dict(variant=f"{event}-{checkpoint}", kind="mutation",
                              event=event, checkpoint=checkpoint,
                              error="no longer exists" if event in {"delete", "rename"} else "changed"))
    cases += [dict(variant="conflict", kind="conflict", error="Destination already exists"),
              dict(variant="absent-before-entry", kind="absent"),
              dict(variant="recover-and-double-confirm", kind="recovery", name="x" * 33, error="exceeds"),
              dict(variant="same", kind="same", name="A.txt")]
    cases += [dict(variant="invalid-missing-conflicting", kind="combined", name="x" * 33,
                   event="delete", error="exceeds"),
              dict(variant="missing-conflicting", kind="combined", name="B.txt",
                   event="delete", error="no longer exists"),
              dict(variant="replaced-conflicting", kind="combined", name="B.txt",
                   event="replace", error="changed")]
    return cases


def file_record(project, name):
    return {"path": name, "sha256": hashlib.sha256((project / name).read_bytes()).hexdigest()}


def run(command, project, env):
    return subprocess.run(command, cwd=project, env=env, text=True, encoding="utf-8",
                          capture_output=True, timeout=DESKTOP_RUN_TIMEOUT + 30, check=False)


@pytest.fixture
def prepared_desktop(tmp_path):
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
    except (ImportError, RuntimeError) as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Required desktop unavailable: {exc}")
        pytest.skip(f"Optional desktop unavailable: {exc}")
    except tk.TclError as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Required desktop unavailable: {exc}")
        pytest.skip(f"Optional display unavailable: {exc}")
    project = tmp_path / "client with spaces"
    helpers = project / ".specify/scripts/shared"
    helpers.mkdir(parents=True)
    for name in HELPERS:
        shutil.copyfile(ROOT / "scripts/shared" / name, helpers / name)
    shutil.copyfile(ROOT / "tests/e2e_samples/desktop_rename.py", project / "desktop_rename.py")
    (project / "test_client.py").write_text(HARNESS, encoding="utf-8")
    source = file_record(project, "desktop_rename.py")
    definitions_by_variant = {row["variant"]: row for row in definitions()}
    assert len(definitions_by_variant) == 34
    # Every ordered event/checkpoint is a separate journey, not an unordered factor.
    model = {
        "schema_version": 1, "scope": "Disposable Tk sample: 34 declared client conditions",
        "source_revision": "desktop-sample-sha256:" + source["sha256"],
        "sources": [source], "exclusions": [], "requirements": [], "journeys": [],
    }
    for variant, row in definitions_by_variant.items():
        requirement = "R-" + variant
        model["requirements"].append({"id": requirement, "source": "desktop_rename.py",
                                      "assertion": f"Verify {variant} feedback, unchanged unrelated files, and cleanup"})
        steps = ["Open the real Tk sample with disposable files"]
        if row["kind"] == "absent":
            steps += ["Delete A.txt and independently prove absence",
                      "Activate Rename on the stale selection; no dialog may open"]
        else:
            steps.append("Open the rename dialog and prove it is visible")
            if row["kind"] == "mutation" and row["checkpoint"] == "dialog-open":
                steps.append(f"{row['event']} A.txt; independently prove the change before editing")
            steps.append("Enter the exact declared name and read the widget value back")
            if row["kind"] == "mutation" and row["checkpoint"] == "before-confirm":
                steps.append(f"{row['event']} A.txt; independently prove the change before confirming")
            if row["kind"] in {"conflict", "combined"}:
                steps.append("Create an independently owned destination")
            if row["kind"] == "combined":
                steps.append(f"{row['event']} A.txt and independently record both conflicting states")
            steps.append("Activate Confirm and verify the declared result")
            if row["kind"] in {"invalid", "mutation", "conflict", "combined", "recovery"}:
                steps.append("Cancel the rejected dialog and refresh; preserve unrelated objects")
            if row["kind"] == "recovery":
                steps += ["Reopen; enter B.txt and confirm successfully",
                          "Dispatch a queued duplicate confirmation; verify one durable effect"]
        steps += ["Check visible feedback and independently read file bytes", "Destroy the window and clean only its sandbox"]
        model["journeys"].append({"id": variant, "requirements": [requirement], "steps": steps,
                                   "factors": {"condition": [variant]}, "strength": "exhaustive",
                                   "exclude": [], "mandatory": []})
    manifest = project / "manifest.json"
    manifest.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    env = os.environ.copy()
    for key in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH", "SPECIFY_E2E_SAMPLE_UNEXPECTED_DELETE"):
        env.pop(key, None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    planner = run([sys.executable, str(helpers / "e2e_coverage.py"), "plan", str(manifest),
                   "--root", str(project)], project, env)
    assert planner.returncode == 0, planner.stderr
    plan = json.loads(planner.stdout)
    cases = [dict(definitions_by_variant[item["journey"]], id=item["id"]) for item in plan["cases"]]
    (project / "cases.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    bindings = {
        "schema_version": 1, "manifest_sha256": plan["manifest_sha256"],
        "test_sources": [file_record(project, n) for n in (
            "test_client.py", "cases.json", "desktop_rename.py",
            *(f".specify/scripts/shared/{name}" for name in HELPERS),
        )],
        "cases": [{"id": item["id"], "test_ref": "test_client.py",
                   "selector": f"test_client.py::test_client[{item['id']}]",
                   "asserted_requirements": item["requirements"]} for item in plan["cases"]],
    }
    (project / "bindings.json").write_text(json.dumps(bindings), encoding="utf-8")
    command = [sys.executable, str(helpers / "e2e_runner.py"), "manifest.json",
               "--bindings", "bindings.json", "--root", str(project), "--runner", "pytest",
               "--target", "disposable-tk-client", "--output-dir", "test-results/run",
               "--timeout", str(DESKTOP_RUN_TIMEOUT), "--", "test_client.py", "-q", "-s",
               "--basetemp", "test-results/fixture-store"]
    return project, env, command, cases


@pytest.mark.parametrize("mode", ["full", "filtered", "collect-only", "unexpected-delete"])
def test_real_desktop_native_execution_keeps_the_frozen_denominator(prepared_desktop, mode):
    project, env, command, cases = prepared_desktop
    if mode == "filtered":
        selected = next(c for c in cases if c["variant"] == "delete-before-confirm")
        command += ["-k", selected["id"]]
    elif mode == "collect-only":
        command += ["--collect-only"]
    elif mode == "unexpected-delete":
        selected = next(c for c in cases if c["variant"] == "normal")
        env["SPECIFY_E2E_SAMPLE_UNEXPECTED_DELETE"] = selected["id"]
    process = run(command, project, env)
    output = project / "test-results/run"
    log = (output / "runner.log").read_text(encoding="utf-8")
    assert process.returncode == (0 if mode == "full" else 1), process.stderr + "\n" + log
    report = json.loads(process.stdout)
    native = json.loads((output / "native-report.json").read_text(encoding="utf-8"))
    assert report["planned_cases"] == 34
    expected_passed = {"full": 34, "filtered": 1, "collect-only": 0, "unexpected-delete": 33}[mode]
    expected_failed = int(mode == "unexpected-delete")
    executed = expected_passed + expected_failed
    assert report["statuses"]["passed"] == expected_passed
    assert report["statuses"]["failed"] == expected_failed
    assert report["statuses"]["not_run"] == 34 - executed
    # Filter/collection-only children return 0, but the full-scope audit stays incomplete.
    assert report["runner_exit_code"] == expected_failed
    assert report["requirements"]["total"] == 34
    assert report["requirements"]["passed"] == expected_passed
    assert len(native["events"]) == executed * 3
    assert len(native["collected"]) == (1 if mode == "filtered" else 34)
    assert sum(line.startswith("DESKTOP_OBSERVATION ") for line in log.splitlines()) == expected_passed
    assert sum(line.lstrip(".F").startswith("DESKTOP_CLEANUP ") for line in log.splitlines()) == executed
    for gap in report["gaps"]:
        assert gap["status"] == ("failed" if expected_failed else "not_run")
    if expected_failed:
        assert report["gaps"] == [{"id": selected["id"], "journey": "normal", "status": "failed"}]
        assert "DESKTOP_NEGATIVE_CONTROL " + selected["id"] in log
    assert json.loads((output / "coverage.json").read_text(encoding="utf-8")) == report
    # All temporary client stores were explicitly removed by actual teardown.
    assert not list(project.glob("**/sandbox"))
