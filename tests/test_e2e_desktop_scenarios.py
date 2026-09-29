"""Real widget/filesystem -> v2 scenario trace integration, not model perception.

The selected 22-case regression scope remains explicit. Negative controls use
real executions; deliberate audit tampering is separate checker validation.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/e2e_samples/desktop_scenario_trace.py"
SPEC = importlib.util.spec_from_file_location("desktop_trace_tests", DRIVER)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


@pytest.fixture(scope="module")
def display():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
    except (ImportError, RuntimeError) as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Required Tk display unavailable: {exc}")
        pytest.skip(f"Tk unavailable: {exc}")
    except tk.TclError as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Required Tk display unavailable: {exc}")
        pytest.skip(f"Display unavailable: {exc}")


@pytest.fixture(scope="module")
def completed(display, tmp_path_factory):
    output = tmp_path_factory.mktemp("desktop-v2") / "full"
    report = driver.run(output)
    return output, report


def payload(output):
    return [json.loads((output / (name + ".json")).read_text(encoding="utf-8")) for name in ("book", "trace")]


def test_real_v2_trace_covers_declared_conditions_and_timing(completed):
    output, report = completed
    book, trace = payload(output)
    helper = driver.load_module(output / "inputs/e2e_scenarios.py", "audit")
    assert report["claim"] == "evidence_complete_against_declared_scenarios"
    assert report["statuses"]["passed"] == 22
    assert sum(report["statuses"].values()) == 22
    assert report["condition_coverage"] == {"total": 88, "passed": 88, "missing": []}
    assert report["timing_coverage"] == {"total": 8, "passed": 8, "missing": []}
    assert trace["executor"]["kind"] == "runner"
    assert trace["evidence"] and not any(e["kind"] == "visual" for e in trace["evidence"])
    assert not list(output.glob("*/sandbox"))
    assert {e["scope"] for e in report["exclusions"]} >= {"permissions", "visual acceptance", "environment_compatibility"}
    for kind, value in (("book", book), ("trace", trace)):
        Draft202012Validator(helper.schemas(2)[kind]).validate(value)
    # The standalone command used by both workflow profiles consumes the real trace.
    process = subprocess.run([sys.executable, str(output / "inputs/e2e_scenarios.py"), "audit", "book.json",
                              "--require-v2", "--root", str(output), "--trace", "trace.json"],
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == report


def test_real_mutations_are_observed_at_distinct_checkpoints(completed):
    output, _ = completed
    book, trace = payload(output)
    evidence = {e["id"]: e for e in trace["evidence"]}
    results = {r["id"]: r for r in trace["results"]}
    for event in ("deleted", "renamed", "replaced", "modified"):
        for checkpoint in ("dialog-open", "before-confirm"):
            scenario_id = f"{event}-{checkpoint}"
            observation = next(s for s in results[scenario_id]["attempts"][0]["steps"] if s["id"] == "mutate")
            fs = next(evidence[e] for e in observation["evidence_ids"] if evidence[e]["kind"] == "filesystem")
            actual = json.loads((output / fs["path"]).read_text())
            assert actual["checkpoint"] == checkpoint
            assert "A.txt" in actual["before"]
            assert ("A.txt" in actual["after"]) == (event in {"replaced", "modified"})
            if event == "replaced":
                assert actual["before"]["A.txt"]["sha256"] == actual["after"]["A.txt"]["sha256"]
                assert actual["before"]["A.txt"]["identity"] != actual["after"]["A.txt"]["identity"]
                assert actual["before"]["A.txt"]["identity"] == actual["after"]["original.txt"]["identity"]
            action = next(evidence[e] for e in observation["evidence_ids"] if evidence[e]["kind"] == "action_log")
            action = json.loads((output / action["path"]).read_text())
            assert action["before"]["entry"] == ("A.txt" if checkpoint == "dialog-open" else "B.txt")
            assert action["before"]["dialog"] is True


def test_removed_exact_boundary_case_remains_a_design_gap(completed):
    output, _ = completed
    book, _ = payload(output)
    book["scenarios"] = [s for s in book["scenarios"] if s["id"] != "length-at"]
    helper = driver.load_module(output / "inputs/e2e_scenarios.py", "audit")
    report = helper.check(book, output)
    assert report["claim"] == "design_incomplete"
    assert any(g["kind"] == "condition" and g["condition"] == "name-length" and g["variant"] == "at" for g in report["gaps"])


def test_filtering_keeps_all_unexecuted_scenarios(display, tmp_path):
    output = tmp_path / "filtered"
    report = driver.run(output, ["deleted-before-confirm"])
    assert report["claim"] == "incomplete"
    assert report["statuses"]["passed"] == 1
    assert report["statuses"]["not_run"] == 21
    assert report["condition_coverage"]["passed"] == 4
    assert report["timing_coverage"]["passed"] == 1
    assert len(payload(output)[0]["scenarios"]) == 22


def test_plan_only_does_not_execute_or_create_passing_observations(tmp_path):
    output = tmp_path / "plan-only"
    report = driver.run(output, plan_only=True)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["not_run"] == 22
    assert report["condition_coverage"]["passed"] == 0
    assert payload(output)[1]["evidence"] == []
    assert json.loads((output / "design.json").read_text())["claim"] == "scenario_design_ready"


def test_actual_failure_and_retry_remain_flaky(display, tmp_path):
    output = tmp_path / "retry"
    report = driver.run(output, ["normal"], fault=True, retry=True)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["flaky"] == 1
    assert report["statuses"]["passed"] == 0
    assert report["condition_coverage"]["passed"] == 0
    book, trace = payload(output)
    attempts = trace["results"][0]["attempts"]
    assert [a["status"] for a in attempts] == ["failed", "passed"]
    assert "Original file no longer exists" in attempts[0]["reason"]
    assert all(a["cleanup"]["status"] == "passed" for a in attempts)
    assert not list(output.glob("*/sandbox"))
    helper = driver.load_module(output / "inputs/e2e_scenarios.py", "audit")
    Draft202012Validator(helper.schemas(2)["trace"]).validate(trace)


def test_full_run_does_not_hide_an_actual_failed_case(display, tmp_path):
    report = driver.run(tmp_path / "fault", fault=True)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["passed"] == 21
    assert report["statuses"]["failed"] == 1
    assert {r["id"] for r in report["execution_gaps"]} == {"normal"}


@pytest.mark.parametrize("mutation", ["source", "evidence", "step-order", "oracle-channel", "book-binding"])
def test_real_trace_rejects_stale_or_incomplete_evidence(completed, tmp_path, mutation):
    source, _ = completed
    output = tmp_path / "audit-copy"
    shutil.copytree(source, output)
    book, trace = payload(output)
    helper = driver.load_module(output / "inputs/e2e_scenarios.py", "audit")
    if mutation == "source":
        (output / "inputs/sample.py").write_text("changed source")
    elif mutation == "evidence":
        (output / trace["evidence"][0]["path"]).write_text("changed observation")
    elif mutation == "step-order":
        trace["results"][0]["attempts"][0]["steps"].reverse()
    elif mutation == "oracle-channel":
        fs = next(e for e in trace["evidence"] if e["kind"] == "filesystem")
        fs["kind"] = "visual"
    else:
        book["scenarios"][0]["title"] += " changed after execution"
    with pytest.raises(helper.ScenarioError):
        helper.audit(book, trace, output)


def test_cleanup_failure_cannot_be_credited(display, tmp_path, monkeypatch):
    output = tmp_path / "cleanup"
    def deny_cleanup(path):
        raise PermissionError("controlled cleanup denial")
    with monkeypatch.context() as patch:
        patch.setattr(driver.shutil, "rmtree", deny_cleanup)
        report = driver.run(output, ["normal"])
    assert report["statuses"]["failed"] == 1
    assert report["condition_coverage"]["passed"] == 0
    attempt = payload(output)[1]["results"][0]["attempts"][0]
    assert attempt["cleanup"]["status"] == "failed"
    assert (output / "normal-attempt-1/sandbox").is_dir()
    shutil.rmtree(output / "normal-attempt-1/sandbox")


def test_missing_capability_preserves_blocked_denominator(tmp_path, monkeypatch):
    original = driver.load_module
    def unavailable(path, prefix):
        if prefix == "desktop_sample":
            raise ImportError("controlled missing Tk capability")
        return original(path, prefix)
    monkeypatch.setattr(driver, "load_module", unavailable)
    report = driver.run(tmp_path / "blocked")
    assert report["claim"] == "incomplete"
    assert report["statuses"]["blocked"] == 22
    assert report["condition_coverage"]["passed"] == 0


@pytest.mark.parametrize("selected", [["unknown"], ["normal", "normal"]])
def test_invalid_selection_cannot_create_partial_output(tmp_path, selected):
    output = tmp_path / "invalid"
    with pytest.raises(RuntimeError, match="selection"):
        driver.run(output, selected)
    assert not output.exists()


def test_existing_output_is_never_overwritten(tmp_path):
    sentinel = tmp_path / "previous.json"
    sentinel.write_text("retain this previous evidence")
    with pytest.raises(FileExistsError):
        driver.run(tmp_path)
    assert sentinel.read_text() == "retain this previous evidence"
    assert not (tmp_path / "book.json").exists()


def test_plan_only_cli_works_without_a_display(tmp_path):
    output = tmp_path / "CLI plan with spaces"
    env = os.environ.copy()
    env["DISPLAY"] = "invalid-display"
    process = subprocess.run([sys.executable, "-I", str(DRIVER), "--output", str(output), "--plan-only"],
                             env=env, capture_output=True, text=True, timeout=30)
    assert process.returncode == 1, process.stderr
    assert json.loads(process.stdout)["statuses"]["not_run"] == 22
    assert payload(output)[1]["results"] == []


def test_filtered_cli_preserves_incomplete_exit_status(display, tmp_path):
    output = tmp_path / "CLI filtered with spaces"
    process = subprocess.run([sys.executable, "-I", str(DRIVER), "--output", str(output),
                              "--case", "deleted-before-confirm"], capture_output=True, text=True, timeout=30)
    assert process.returncode == 1, process.stderr
    report = json.loads(process.stdout)
    assert report["statuses"]["passed"] == 1
    assert report["statuses"]["not_run"] == 21
