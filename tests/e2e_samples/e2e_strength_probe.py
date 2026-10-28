#!/usr/bin/env python3
"""Real Tk/filesystem strength controls in newly created disposable copies.

This opt-in probe requires a working native display (use an isolated desktop or
Xvfb). It never claims model vision. Deliberately incorrect copies must fail;
that is probe evidence, never product E2E success. All 22 book cases remain in
each trace denominator, including unselected cases. No repository source is
modified and no previous run is overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "tests/e2e_samples/desktop_scenario_trace.py"
SAMPLE = ROOT / "tests/e2e_samples/desktop_rename.py"
HELPER = ROOT / "scripts/shared/e2e_assets.py"
BOUNDARIES = ("length-below", "length-at", "length-above")


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_command(output, label, argv, expected_exit):
    commands = output / "commands"
    commands.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.run(argv, cwd=output, env=environment, capture_output=True, timeout=60, check=False)
    for suffix, content in (("stdout", process.stdout), ("stderr", process.stderr)):
        with (commands / f"{label}.{suffix}").open("xb") as handle:
            handle.write(content)
    write(commands / f"{label}.json", {"argv": argv, "cwd": str(output), "exit_code": process.returncode,
          "expected_exit": expected_exit, "stdout_sha256": hashlib.sha256(process.stdout).hexdigest(),
          "stderr_sha256": hashlib.sha256(process.stderr).hexdigest()})
    need(process.returncode == expected_exit,
         f"{label}: exit {process.returncode}, expected {expected_exit}; inspect retained commands")
    return json.loads(process.stdout)


def intent_for(book, unicode_matrix):
    interactions = []
    if unicode_matrix:
        for point, identity in zip(("below", "at", "above"), BOUNDARIES, strict=True):
            interactions.append({"id": point, "conditions": [
                {"condition": "name-length", "variant": point},
                {"condition": "input-repertoire", "variant": point}], "timing": [],
                "bindings": [{"scenario": identity, "step_ids": ["open", "enter", "confirm"],
                              "oracle_ids": ["feedback", "files"]}]})
    else:
        interactions = [{"id": "ui-and-storage", "conditions": [
            {"condition": "happy_path", "variant": "normal"},
            {"condition": "persistence_consistency", "variant": "normal"}], "timing": [],
            "bindings": [{"scenario": "normal", "step_ids": ["open", "enter", "confirm"],
                          "oracle_ids": ["feedback", "files"]}]}]
    return {"schema_version": 1, "scope": "Explicit sample negative control; no product acceptance",
            "risks": [{"id": "unicode-boundary" if unicode_matrix else "false-success",
                       "operation": "rename", "requirements": ["R-rename", "R-repertoire"] if unicode_matrix else ["R-rename"],
                       "source_refs": [s["path"] for s in book["sources"]],
                       "rationale": "Different Unicode repertoires at the same code-point boundary expose byte/code-unit confusion"
                       if unicode_matrix else "A success label can mask a missing durable rename; independently read the filesystem",
                       "interactions": interactions}], "gaps": [], "exclusions": []}


def run_matrix(base, name, *, mutant=None, glyph=None, selected=None, expected_strength_exit=0, strength=True):
    source_root = base / (name + "-sources")
    source_root.mkdir()
    driver = load_module("strength_driver_" + name.replace("-", "_"), DRIVER)
    originals = {**driver.INPUTS, "e2e_assets.py": HELPER, "strength_probe.py": Path(__file__)}
    inputs = {}
    for key, source in originals.items():
        target = source_root / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        inputs[key] = target
    control = source_root / "strength-control.json"
    write(control, {"expected_unit": "Unicode code points", "glyph": glyph,
                    "mutant": mutant, "negative_control_only": mutant is not None,
                    "contract": "Sample names have at most 32 Unicode code points; truthful success requires the original identity at the new path"})
    inputs["strength_control.json"] = control
    if mutant:
        sample_path = inputs["sample.py"]
        content = sample_path.read_text(encoding="utf-8")
        if mutant in {"utf8-bytes", "utf16-code-units"}:
            needle = "if len(name) > LIMIT:"
            expression = 'len(name.encode("utf-8"))' if mutant == "utf8-bytes" else 'len(name.encode("utf-16-le")) // 2'
            replacement = f"if {expression} > LIMIT:"
        else:
            need(mutant == "rename-noop", "unknown negative control")
            needle = "        source, target = self.root / selection.name, self.root / name"
            replacement = '        return f"Renamed to {name}"  # Explicit disposable false-success control\n' + needle
        need(content.count(needle) == 1, "Sample owner changed; inspect before applying a control")
        sample_path.write_text(content.replace(needle, replacement), encoding="utf-8")
    driver.ROOT, driver.INPUTS = source_root, inputs
    original_catalogue, original_book, original_execute = driver.catalogue, driver.build_book, driver.execute_case

    def catalogue():
        cases = original_catalogue()
        if glyph:
            for case in cases:
                if "boundary" in case:
                    case["name"] = glyph * {"below": 31, "at": 32, "above": 33}[case["boundary"]]
                    if case.get("success"):
                        case["message"] = "Renamed to " + case["name"]
        return cases

    def build_book(output, helper):
        book = original_book(output, helper)
        if glyph:
            book["requirements"].append({"id": "R-repertoire", "source_ref": "inputs/strength_control.json",
                                         "assertion": "The selected repertoire obeys the same 32-code-point boundary"})
            cases = {c["id"]: c for c in catalogue()}
            book["conditions"].append({"id": "input-repertoire", "operation": "rename", "dimension": "input_partitions",
                "kind": "partition", "title": "Unicode repertoire at the boundary", "source_refs": ["inputs/strength_control.json"],
                "requirements": ["R-rename", "R-repertoire"], "variants": [
                    {"id": point, "input": repr(cases[identity]["name"]), "expected": cases[identity]["message"]}
                    for point, identity in zip(("below", "at", "above"), BOUNDARIES, strict=True)]})
            for card in book["scenarios"]:
                if card["id"] in BOUNDARIES:
                    card["requirements"].append("R-repertoire")
                    card["dimensions"].append("input_partitions")
                    card["condition_bindings"].append({"condition": "input-repertoire", "variant": cases[card["id"]]["boundary"],
                        "step_ids": ["enter", "confirm"], "oracle_ids": ["feedback", "files"]})
        return book

    prepared = False

    def execute_case(case, card, output, *args, **kwargs):
        nonlocal prepared
        if strength and not prepared:
            book = json.loads((output / "book.json").read_text(encoding="utf-8"))
            write(output / "risk-intent.json", intent_for(book, bool(glyph)))
            asset = run_command(output, "strength-prepare", [sys.executable, "-X", "utf8", "-E", "-s", str(output / "inputs/e2e_assets.py"),
                "strength-prepare", "risk-intent.json", "--book", "book.json"], 0)
            write(output / "strength.json", asset)
            prepared = True
        return original_execute(case, card, output, *args, **kwargs)

    driver.catalogue, driver.build_book, driver.execute_case = catalogue, build_book, execute_case
    output = base / name
    report = driver.run(output, selected)
    if strength:
        need(prepared, "No execution began; no frozen strength asset was prepared")
        strength_report = run_command(output, "strength-audit", [sys.executable, "-X", "utf8", "-E", "-s", str(output / "inputs/e2e_assets.py"),
            "strength-audit", "strength.json", "--trace", "trace.json"], expected_strength_exit)
        write(output / "strength-audit.json", strength_report)
    need(not list(output.glob("*/sandbox")), "A disposable sandbox was not cleaned")
    return output, report


def run(output, controls):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    originals = {str(path): sha(path) for path in (DRIVER, SAMPLE, HELPER, Path(__file__))}
    results = []
    for mutant, glyph in (("utf8-bytes", "文"), ("utf16-code-units", "🧪")):
        if mutant not in controls:
            continue
        _, baseline = run_matrix(output, mutant + "-original-catalogue", mutant=mutant, strength=False)
        need(baseline["statuses"]["passed"] == 22 and baseline["claim"] == "evidence_complete_against_declared_scenarios",
             "Wrong-unit baseline did not reproduce the documented 22-case detection gap")
        failed_path, failed = run_matrix(output, mutant + "-interaction", mutant=mutant, glyph=glyph,
                                        selected=list(BOUNDARIES), expected_strength_exit=1)
        need(failed["statuses"]["failed"] == 2 and failed["statuses"]["passed"] == 1 and failed["statuses"]["not_run"] == 19,
             "Unicode interaction failed to preserve the expected failure/denominator")
        trace = json.loads((failed_path / "trace.json").read_text(encoding="utf-8"))
        attempts = {r["id"]: r["attempts"][0] for r in trace["results"]}
        for identity in BOUNDARIES[:2]:
            need("Name exceeds 32 Unicode code points" in attempts[identity]["reason"], "Different failure cannot prove wrong-unit detection")
        repaired_path, repaired = run_matrix(output, mutant + "-corrected", glyph=glyph)
        need(repaired["statuses"]["passed"] == 22 and repaired["claim"] == "evidence_complete_against_declared_scenarios",
             "Corrected source did not establish fresh full-book evidence")
        results.append({"control": mutant, "original_catalogue": baseline["statuses"], "interaction": failed["statuses"],
                        "corrected": repaired["statuses"], "failure_trace": str(failed_path.relative_to(output) / "trace.json"),
                        "fresh_corrected_trace": str(repaired_path.relative_to(output) / "trace.json")})
    if "rename-noop" in controls:
        failed_path, failed = run_matrix(output, "rename-noop", mutant="rename-noop", selected=["normal"], expected_strength_exit=1)
        need(failed["statuses"]["failed"] == 1 and failed["statuses"]["not_run"] == 21, "False-success denominator changed")
        trace = json.loads((failed_path / "trace.json").read_text(encoding="utf-8"))
        attempt = trace["results"][0]["attempts"][0]
        need(attempt["reason"] == "Independent file readback differs from the planned outcome", "False-success effect oracle did not catch the control")
        need(any(o["id"] == "feedback" and o["outcome"] == "passed" for o in attempt["oracles"]), "UI did not actually report success")
        need(any(e["kind"] == "filesystem" for e in trace["evidence"]), "Independent filesystem evidence missing")
        repaired_path, repaired = run_matrix(output, "rename-noop-corrected")
        need(repaired["statuses"]["passed"] == 22, "Corrected rename lacks fresh full-book evidence")
        results.append({"control": "rename-noop", "interaction": failed["statuses"], "ui_success_observed": True,
                        "effect_mismatch_observed": True, "corrected": repaired["statuses"],
                        "failure_trace": str(failed_path.relative_to(output) / "trace.json"),
                        "fresh_corrected_trace": str(repaired_path.relative_to(output) / "trace.json")})
    need(all(sha(Path(path)) == digest for path, digest in originals.items()), "Repository source changed during probe")
    report = {"claim": "declared_negative_controls_observed", "controls": results, "source_hashes": originals,
              "environment": {"os": platform.platform(), "python": platform.python_version(), "interpreter": sys.executable},
              "qualification": "Real native Tk widget and independent filesystem observations, not model perception. Incorrect-version failures stay failed; corrected versions have new books/traces. No full-product or mutation-score claim."}
    write(output / "result.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--control", action="append", choices=("utf8-bytes", "utf16-code-units", "rename-noop"))
    args = parser.parse_args(argv)
    try:
        report = run(args.output, args.control or ["utf8-bytes", "utf16-code-units", "rename-noop"])
    except (OSError, ValueError, RuntimeError, ImportError, subprocess.SubprocessError) as exc:
        print(json.dumps({"claim": "probe_incomplete", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
