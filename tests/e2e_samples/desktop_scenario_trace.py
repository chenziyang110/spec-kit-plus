#!/usr/bin/env python3
"""Exercise a bounded desktop regression book through the real v2 trace audit.

This is an opt-in sample, not a new runner or installed workflow dependency.
The catalogue is deliberately authored; neither a model nor this code discovers
an exhaustive test universe. Tk/widget observations are labelled accessibility,
not visual-model evidence. Only newly created disposable directories are used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    "sample.py": ROOT / "tests/e2e_samples/desktop_rename.py",
    "trace_driver.py": Path(__file__),
    "e2e_scenarios.py": ROOT / "scripts/shared/e2e_scenarios.py",
}
# This independent expectation is the documented sample contract, not an OS rule.
ORIGINAL = b"original file: preserve these bytes\n"
OCCUPIED = b"existing destination: never overwrite\n"
# Same bytes, different inode: replacement is not merely a content-change case.
REPLACEMENT = ORIGINAL
MODIFIED = b"external modification\n"
UNTOUCHED = "Unrelated taken.txt retains its original bytes"
REFRESHED = "Refreshed list equals independently read file names"
VISIBLE = "Feedback control is mapped within the client window"


def need(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def load_module(path: Path, prefix: str):
    name = prefix + "_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    need(spec is not None and spec.loader is not None, f"Cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def catalogue() -> list[dict]:
    """Concrete expected outcomes are authored independently of app results."""
    def case(identity, name, message, dimension, **extra):
        return dict(id=identity, name=name, message=message, dimension=dimension, **extra)

    rows = [
        case("normal", "B.txt", "Renamed to B.txt", "happy_path", success=True),
        case("unicode", "文件.txt", "Renamed to 文件.txt", "input_partitions", success=True),
        case("empty", "", "Name must not be empty or whitespace", "input_partitions"),
        case("whitespace", "   ", "Name must not be empty or whitespace", "input_partitions"),
        case("invalid-character", "bad/name", "Name contains a disallowed character", "input_partitions"),
        case("length-below", "a" * 31, "Renamed to " + "a" * 31, "input_boundaries", success=True, boundary="below"),
        case("length-at", "a" * 32, "Renamed to " + "a" * 32, "input_boundaries", success=True, boundary="at"),
        case("length-above", "a" * 33, "Name exceeds 32 Unicode code points", "input_boundaries", boundary="above"),
        case("occupied-target", "taken.txt", "Destination already exists", "conflict_concurrency"),
        case("same-name", "A.txt", "Name unchanged", "repeat_cancel_retry", success=True),
        case("cancel-reopen", "B.txt", "Renamed to B.txt", "repeat_cancel_retry", success=True, reopen=True),
    ]
    for event in ("deleted", "renamed", "replaced", "modified"):
        message = ("Original file no longer exists" if event in {"deleted", "renamed"}
                   else "Original file changed or was replaced")
        for checkpoint in ("dialog-open", "before-confirm"):
            rows.append(case(f"{event}-{checkpoint}", "B.txt", message,
                             "object_lifecycle", event=event, checkpoint=checkpoint))
    rows += [
        case("invalid-missing-occupied", "a" * 33, "Name exceeds 32 Unicode code points",
             "conflict_concurrency", event="deleted", checkpoint="before-confirm", occupy=True),
        case("missing-occupied", "taken.txt", "Original file no longer exists",
             "conflict_concurrency", event="deleted", checkpoint="before-confirm"),
        case("replaced-occupied", "taken.txt", "Original file changed or was replaced",
             "conflict_concurrency", event="replaced", checkpoint="before-confirm"),
    ]
    return rows


def build_book(root: Path, helper) -> dict:
    """Freeze a selected regression scope; exclusions never masquerade as tests."""
    sources = [{"path": "inputs/" + name, "sha256": helper.file_hash(root, "inputs/" + name)}
               for name in sorted(INPUTS)]
    source_refs = [row["path"] for row in sources]
    cases = catalogue()
    applicable = {c["dimension"] for c in cases} | {
        "external_mutation", "event_order", "persistence_consistency", "visual_interaction", "cross_feature"}
    reasons = {
        "permissions": "Fixed writable owner-owned local fixture; OS permission changes and authorization are outside this selected regression scope.",
        "interruption_recovery": "Only observable pre-confirmation checkpoints are selected; crash/syscall durability is outside the sample contract.",
        "environment_compatibility": "One current host is tested; other OS/filesystem/device configurations are separately excluded, not certified compatible.",
    }
    operation = {
        "id": "rename", "title": "Selected pre-confirmation desktop rename regressions",
        "entrypoint": "RenameClient > select A.txt > Rename selected file",
        "source_refs": source_refs, "side_effects": True,
        "assumptions": ["Selection still identifies the same existing file", "Name is accepted by the sample's 32-code-point policy", "Destination is not occupied"],
        "dimensions": {d: {"disposition": "applicable" if d in applicable else "not_applicable",
                            "reason": "Explicit cases in this selected sample scope" if d in applicable else reasons[d],
                            "source_refs": source_refs} for d in helper.DIMENSIONS},
        "checkpoints": [{"id": "dialog-open", "observation": "Dialog mapped; input still A.txt"},
                        {"id": "before-confirm", "observation": "Exact new input read from widget; confirm not activated"}],
        "events": [{"id": e, "change": f"Original file externally {e}; independently read the resulting files",
                    "checkpoints": ["dialog-open", "before-confirm"]}
                   for e in ("deleted", "renamed", "replaced", "modified")],
    }
    conditions, scenarios = [], []
    for dimension in sorted(applicable - {"external_mutation", "event_order", "input_boundaries"}):
        selected = cases if dimension in {"persistence_consistency", "visual_interaction", "cross_feature"} else [c for c in cases if c["dimension"] == dimension]
        expected = {"persistence_consistency": UNTOUCHED, "visual_interaction": VISIBLE, "cross_feature": REFRESHED}
        conditions.append({"id": dimension, "operation": "rename", "dimension": dimension,
                           "kind": {"conflict_concurrency": "rule", "input_partitions": "partition", "object_lifecycle": "state", "repeat_cancel_retry": "sequence", "cross_feature": "sequence"}.get(dimension, "example"),
                           "title": "Selected " + dimension, "source_refs": source_refs, "requirements": ["R-rename"],
                           "variants": [{"id": c["id"], "input": json.dumps({k: v for k, v in c.items() if k != "message"}, ensure_ascii=False),
                                         "expected": expected.get(dimension, c["message"])} for c in selected]})
    conditions.append({"id": "name-length", "operation": "rename", "dimension": "input_boundaries",
                       "kind": "boundary", "title": "Sample-only 32-code-point name boundary", "source_refs": source_refs,
                       "requirements": ["R-rename"], "boundary": {"limit": 32, "unit": "Unicode code points",
                       "expectations": {c["boundary"]: c["message"] for c in cases if "boundary" in c}}})
    for c in cases:
        steps = [{"id": "open", "actor": "runner", "action": "Select A.txt and activate Rename", "observe": "Mapped dialog and selected name A.txt"},
                 {"id": "enter", "actor": "runner", "action": "Enter the exact name " + repr(c["name"]), "observe": "Read back the actual entry value"},
                 {"id": "confirm", "actor": "runner", "action": "Activate Confirm rename", "observe": "Read feedback and independent file state"},
                 {"id": "refresh", "actor": "runner", "action": "Cancel any remaining dialog, then Refresh", "observe": "List agrees with independent file names"}]
        if c.get("reopen"):
            steps.insert(1, {"id": "reopen", "actor": "runner", "action": "Enter discarded.txt, Cancel, then reopen Rename", "observe": "No rename occurred; new dialog contains A.txt"})
        perturbations = []
        if c.get("event"):
            index = next(i for i, s in enumerate(steps) if s["id"] == ("enter" if c["checkpoint"] == "dialog-open" else "confirm"))
            steps.insert(index, {"id": "mutate", "actor": "fixture", "action": f"Apply {c['event']} at {c['checkpoint']}" + (" and occupy the requested destination" if c.get("occupy") else ""),
                                 "observe": "Check checkpoint entry value and independent filesystem before and after mutation"})
            perturbations = [{"event": c["event"], "checkpoint": c["checkpoint"], "step_id": "mutate"}]
        oracles = [{"id": "feedback", "channel": "accessibility", "assertion": c["message"], "check": "Compare actual widget feedback text; not pixel perception"},
                   {"id": "files", "channel": "filesystem", "assertion": UNTOUCHED, "check": "Compare full independent file byte map, including source identity and destination"},
                   {"id": "visible", "channel": "accessibility", "assertion": VISIBLE, "check": "Mapped status control geometry lies within the real window"},
                   {"id": "list", "channel": "accessibility", "assertion": REFRESHED, "check": "Compare refreshed list with independent filesystem names"}]
        bindings = [{"condition": d, "variant": c["id"], "step_ids": ["confirm" if d != "cross_feature" else "refresh"], "oracle_ids": [o]}
                    for d, o in (("persistence_consistency", "files"), ("visual_interaction", "visible"), ("cross_feature", "list"))]
        bindings.append({"condition": "name-length" if "boundary" in c else c["dimension"],
                         "variant": c.get("boundary", c["id"]),
                         "step_ids": [s["id"] for s in steps if s["id"] != "refresh"], "oracle_ids": ["feedback", "files"]})
        dimensions = [c["dimension"], "persistence_consistency", "visual_interaction", "cross_feature"]
        if perturbations:
            dimensions += ["external_mutation", "event_order"]
        scenarios.append({"id": c["id"], "operation": "rename", "title": c["id"], "dimensions": dimensions,
                          "requirements": ["R-rename"], "technique": [{"input_boundaries": "boundary-value", "input_partitions": "equivalence-partition", "object_lifecycle": "event-sequence", "conflict_concurrency": "decision-rule", "repeat_cancel_retry": "state-transition"}.get(c["dimension"], "happy-path")],
                          "priority": "high", "preconditions": ["Fresh marked local sandbox; A.txt and taken.txt have independently known bytes"],
                          "steps": steps, "perturbations": perturbations, "oracles": oracles, "execution": "runner",
                          "condition_bindings": bindings, "cleanup": ["Destroy the Tk window and remove only this attempt's newly created sandbox"],
                          "safety": ["No user files, no network, no production directories; no guessed sleeps"]})
    return {"schema_version": 2, "scope": "22 explicitly selected desktop rename regressions, not full-product coverage or visual acceptance",
            "source_revision": "snapshot-sha256:" + helper.sha(sources), "sources": sources,
            "requirements": [{"id": "R-rename", "source_ref": "inputs/sample.py", "assertion": "Sample naming and identity contract; preserve unrelated data and truthful feedback"}],
            "operations": [operation], "conditions": conditions, "scenarios": scenarios, "discovery_gaps": [],
            "exclusions": [{"scope": scope, "reason": reason, "owner": "sample-regression"} for scope, reason in {
                **reasons, "visual acceptance": "Widget values/geometry do not prove pixels, aesthetics, IME or model perception; independent visual execution remains required.",
                "unselected input/recovery families": "This is a fixed regression subset, not all illegal characters, undo, all concurrency orderings or every possible rename interaction."}.items()]}


def read_files(workspace: Path) -> dict[str, bytes]:
    """Independent of Store.readback(); include every non-marker fixture file."""
    return {p.name: p.read_bytes() for p in workspace.iterdir() if p.name != ".spec-kit-e2e-sandbox"}


def mutate(workspace: Path, case: dict) -> None:
    source = workspace / "A.txt"
    event = case["event"]
    if event == "deleted":
        source.unlink()
    elif event == "renamed":
        source.rename(workspace / "elsewhere.txt")
    elif event == "replaced":
        source.rename(workspace / "original.txt")
        source.write_bytes(REPLACEMENT)
    else:
        source.write_bytes(MODIFIED)
    if case.get("occupy"):
        (workspace / case["name"]).write_bytes(OCCUPIED)


def expected_files(case: dict) -> dict[str, bytes]:
    result = {"A.txt": ORIGINAL, "taken.txt": OCCUPIED}
    event = case.get("event")
    if event in {"deleted", "renamed"}:
        del result["A.txt"]
        if event == "renamed":
            result["elsewhere.txt"] = ORIGINAL
    elif event == "replaced":
        result.update({"A.txt": REPLACEMENT, "original.txt": ORIGINAL})
    elif event == "modified":
        result["A.txt"] = MODIFIED
    if case.get("occupy"):
        result[case["name"]] = OCCUPIED
    if case.get("success"):
        result[case["name"]] = result.pop("A.txt")
    return result


def execute_case(case: dict, scenario: dict, root: Path, attempt_number: int, evidence: list, helper, sample, *, fault=False) -> dict:
    """Observe first, compare second, append pass only after cleanup succeeds."""
    directory = root / f"{case['id']}-attempt-{attempt_number}"
    directory.mkdir()
    workspace = directory / "sandbox"
    attempt = {"status": "failed", "steps": [], "oracles": []}
    window = app = None
    callback_errors = []

    def capture(kind: str, value: dict) -> str:
        identity = f"e{len(evidence) + 1:05d}"
        path = directory / (identity + ".json")
        write(path, value)
        relative = path.relative_to(root).as_posix()
        evidence.append({"id": identity, "kind": kind, "path": relative,
                         "sha256": helper.file_hash(root, relative), "captured_at": now()})
        return identity

    def state() -> dict:
        files = read_files(workspace)
        return {"dialog": app.dialog is not None, "entry": app.entry.get() if app.dialog is not None else None,
                "status": app.status.get(), "error": app.error.get() if app.dialog is not None else None,
                "list": list(app.listbox.get(0, "end")),
                "files": {n: {"hex": b.hex(), "sha256": hashlib.sha256(b).hexdigest(),
                              "identity": [(workspace / n).stat().st_dev, (workspace / n).stat().st_ino]}
                          for n, b in sorted(files.items())}}

    try:
        import tkinter as tk
        sample.create_sandbox(workspace)
        need(read_files(workspace) == {"A.txt": ORIGINAL, "taken.txt": OCCUPIED}, "Fixture content differs from the independent sample contract")
        original_identity = ((workspace / "A.txt").stat().st_dev, (workspace / "A.txt").stat().st_ino)
        unrelated_identity = ((workspace / "taken.txt").stat().st_dev, (workspace / "taken.txt").stat().st_ino)
        try:
            window = tk.Tk()
        except tk.TclError as exc:
            attempt.update(status="blocked", reason="Tk display unavailable: " + str(exc))
            return attempt
        window.report_callback_exception = lambda *args: callback_errors.append(str(args[1]))
        app = sample.RenameClient(window, sample.Store(workspace))
        window.update()
        for step in scenario["steps"]:
            identity = step["id"]
            before = state()
            if identity == "open":
                app.rename_button.invoke()
            elif identity == "reopen":
                app.entry.delete(0, "end")
                app.entry.insert(0, "discarded.txt")
                app.cancel_button.invoke()
                app.rename_button.invoke()
            elif identity == "enter":
                app.entry.delete(0, "end")
                app.entry.insert(0, case["name"])
            elif identity == "mutate":
                required_value = "A.txt" if case["checkpoint"] == "dialog-open" else case["name"]
                need(app.dialog is not None and app.entry.get() == required_value, "Mutation checkpoint was not reached")
                mutate(workspace, case)
            elif identity == "confirm":
                if fault:
                    (workspace / "A.txt").unlink()  # Explicit negative control, never a passing scenario.
                app.confirm_button.invoke()
            elif identity == "refresh":
                if app.dialog is not None:
                    app.cancel_button.invoke()
                app.refresh_button.invoke()
            window.update()
            observed = state()
            ev = capture("action_log", {"step": identity, "before": before, "after": observed, "negative_control": bool(fault and identity == "confirm")})
            evidence_ids = [ev]
            if identity == "mutate":
                evidence_ids.append(capture("filesystem", {"checkpoint": case["checkpoint"], "before": before["files"], "after": observed["files"]}))
            attempt["steps"].append({"id": identity, "observation": json.dumps(observed, ensure_ascii=False), "evidence_ids": evidence_ids})
            if identity == "mutate":
                need(read_files(workspace) == expected_files(case), "External mutation was not independently observed")
                if case["event"] == "replaced":
                    need(before["files"]["A.txt"]["identity"] != observed["files"]["A.txt"]["identity"], "Replacement did not create a distinct object")
                    need(before["files"]["A.txt"]["identity"] == observed["files"]["original.txt"]["identity"], "Original identity was not preserved for inspection")
            need(not callback_errors, "Tk callback failed: " + repr(callback_errors))
            if identity in {"open", "reopen"}:
                need(app.dialog is not None and app.dialog.winfo_ismapped() and app.entry.get() == "A.txt", "Dialog was not opened/reset")
                need(read_files(workspace) == {"A.txt": ORIGINAL, "taken.txt": OCCUPIED}, "Cancel/open unexpectedly changed files")
            if identity == "enter":
                need(app.entry.get() == case["name"], "Actual input differs from the planned name")
            if identity == "confirm":
                actual = app.status.get() if app.dialog is None else app.error.get()
                ui = capture("accessibility", {"feedback": actual, "dialog_open": app.dialog is not None,
                                               "expected_feedback": case["message"]})
                need(actual == case["message"] and (app.dialog is None) == bool(case.get("success")), "Unexpected feedback/dialog state: " + actual)
                attempt["oracles"].append({"id": "feedback", "outcome": "passed", "observation": actual, "evidence_ids": [ui]})
                files = read_files(workspace)
                fs = capture("filesystem", {"files": observed["files"], "original_identity": original_identity, "unrelated_identity": unrelated_identity})
                need(files == expected_files(case), "Independent file readback differs from the planned outcome")
                need(tuple(observed["files"]["taken.txt"]["identity"]) == unrelated_identity, "Unrelated object identity changed")
                if case.get("success"):
                    need(tuple(observed["files"][case["name"]]["identity"]) == original_identity, "Rename did not preserve the selected object identity")
                attempt["oracles"].append({"id": "files", "outcome": "passed", "observation": json.dumps({n: b.hex() for n, b in files.items()}), "evidence_ids": [fs]})
                label = app.status_label
                bounds = {"mapped": bool(label.winfo_ismapped()), "x": label.winfo_rootx() - window.winfo_rootx(),
                          "y": label.winfo_rooty() - window.winfo_rooty(), "w": label.winfo_width(), "h": label.winfo_height(),
                          "window_w": window.winfo_width(), "window_h": window.winfo_height()}
                visible = capture("accessibility", bounds)
                need(bounds["mapped"] and min(bounds["x"], bounds["y"]) >= 0 and bounds["x"] + bounds["w"] <= bounds["window_w"] and bounds["y"] + bounds["h"] <= bounds["window_h"], "Status feedback is clipped")
                attempt["oracles"].append({"id": "visible", "outcome": "passed", "observation": json.dumps(bounds), "evidence_ids": [visible]})
            if identity == "refresh":
                actual = list(app.listbox.get(0, "end"))
                ev = capture("accessibility", {"list": actual})
                need(actual == sorted(read_files(workspace)), "Refreshed list disagrees with independent file names")
                attempt["oracles"].append({"id": "list", "outcome": "passed", "observation": json.dumps(actual, ensure_ascii=False), "evidence_ids": [ev]})
        attempt["status"] = "passed"
    except Exception as exc:
        # Preserve unexpected Tcl/callback/driver failures as evidence too.
        attempt.update(status="blocked" if isinstance(exc, ImportError) else "failed", reason=str(exc))
    finally:
        cleanup_errors = []
        if window is not None:
            try:
                window.destroy()
            except Exception as exc:
                cleanup_errors.append(str(exc))
        try:
            if workspace.exists():
                shutil.rmtree(workspace)
            need(not workspace.exists(), "Sandbox cleanup incomplete")
        except (OSError, RuntimeError) as exc:
            cleanup_errors.append(str(exc))
        cleanup_errors += callback_errors
        value = {"sandbox_absent": not workspace.exists(), "window_created": window is not None, "no_remaining_window": not cleanup_errors,
                 "errors": cleanup_errors}
        ev = capture("filesystem", value)
        attempt["cleanup"] = {"status": "failed" if cleanup_errors else "passed", "observation": json.dumps(value), "evidence_ids": [ev]}
        if cleanup_errors:
            attempt.update(status="failed", reason="Cleanup/callback failed: " + repr(cleanup_errors))
        if attempt["status"] != "passed":
            for key in ("steps", "oracles"):
                if not attempt[key]:
                    del attempt[key]
    return attempt


def run(output: Path, selected: list[str] | None = None, *, fault: bool = False, retry: bool = False, plan_only: bool = False) -> dict:
    output = output.resolve()
    names = {c["id"] for c in catalogue()}
    need(selected is None or (len(set(selected)) == len(selected) and set(selected) <= names), "Unknown or duplicate case selection")
    need(not retry or fault, "Retry control requires the explicit fault control")
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "inputs"
    inputs.mkdir()
    for name, source in INPUTS.items():
        shutil.copyfile(source, inputs / name)
    helper = load_module(inputs / "e2e_scenarios.py", "scenario_audit")
    book = build_book(output, helper)
    write(output / "book.json", book)
    write(output / "inputs.json", {"source_revision": book["source_revision"],
          "files": [{"snapshot": "inputs/" + name, "repository_path": source.relative_to(ROOT).as_posix(),
                     "sha256": helper.file_hash(output, "inputs/" + name)} for name, source in INPUTS.items()]})
    design = helper.check(book, output)
    write(output / "design.json", design)
    need(design["claim"] == "scenario_design_ready", "Invalid sample design: " + repr(design["gaps"]))
    trace = {"schema_version": 1, "book_sha256": helper.sha(book), "source_revision": book["source_revision"],
             "run_id": uuid.uuid4().hex, "target": f"Tk sample; {platform.system()}; Python {platform.python_version()}",
             "executor": {"kind": "runner", "name": "Tk widget driver; no visual-model perception"},
             "started_at": now(), "finished_at": "", "evidence": [], "results": []}
    chosen = names if selected is None else set(selected)
    if not plan_only:
        try:
            sample = load_module(inputs / "sample.py", "desktop_sample")
        except ImportError as exc:
            sample = None
            import_error = "Sample capability unavailable: " + str(exc)
        for c, scenario in zip(catalogue(), book["scenarios"], strict=True):
            if c["id"] not in chosen:
                continue
            if sample is None:
                trace["results"].append({"id": c["id"], "attempts": [{"status": "blocked", "reason": import_error}]})
                continue
            injected = fault and c["id"] == "normal"
            attempts = [execute_case(c, scenario, output, 1, trace["evidence"], helper, sample, fault=injected)]
            if retry and injected:
                attempts.append(execute_case(c, scenario, output, 2, trace["evidence"], helper, sample))
            trace["results"].append({"id": c["id"], "attempts": attempts})
    trace["finished_at"] = now()
    write(output / "trace.json", trace)
    report = helper.audit(book, trace, output)
    write(output / "audit.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="NEW disposable evidence directory")
    parser.add_argument("--case", action="append", dest="selected", help="Execute only this case but preserve the full book")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run(args.output, args.selected, plan_only=args.plan_only)
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["claim"] == "evidence_complete_against_declared_scenarios" else 1


if __name__ == "__main__":
    raise SystemExit(main())
