"""Length-unit × input-repertoire regressions using the existing real Tk driver.

Keep the original 22-case catalogue intact. Separate source-bound books vary
only its boundary inputs. Wrong-unit mutants exist only in disposable copies;
they demonstrate a detection gap, not defects in the unmodified application.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/e2e_samples/desktop_scenario_trace.py"
SPEC = importlib.util.spec_from_file_location("desktop_length_unit_driver", DRIVER)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)
CATALOGUE = driver.catalogue
BOUNDARIES = ["length-below", "length-at", "length-above"]


@pytest.fixture(scope="module")
def display():
    try:
        import tkinter as tk
    except ImportError as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Required Tk unavailable: {exc}")
        pytest.skip(f"Optional Tk unavailable: {exc}")
    try:
        window = tk.Tk()
        window.destroy()
    except tk.TclError as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Required Tk display unavailable: {exc}")
        pytest.skip(f"Optional Tk display unavailable: {exc}")


def isolated_inputs(tmp_path, monkeypatch, *, glyph, wrong_unit=None):
    """Bind the actual selected sample, driver, helper and extension into evidence."""
    source_root = tmp_path / "isolated sources"
    inputs = {}
    for name, original in driver.INPUTS.items():
        target = source_root / original.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        inputs[name] = target
    extension = source_root / "tests/test_e2e_desktop_length_units.py"
    shutil.copyfile(Path(__file__), extension)
    inputs["length_units_test.py"] = extension
    control = source_root / "length-unit-control.json"
    control.write_text(json.dumps({"glyph": glyph, "expected_unit": "Unicode code points",
        "wrong_unit": wrong_unit, "negative_control_only": wrong_unit is not None,
        "boundaries": [31, 32, 33]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inputs["length_unit_control.json"] = control
    if wrong_unit is not None:
        sample = inputs["sample.py"]
        original = sample.read_text(encoding="utf-8")
        needle = "if len(name) > LIMIT:"
        assert original.count(needle) == 1, "Review the sample's changed length owner before mutating it"
        expression = {"utf8-bytes": 'len(name.encode("utf-8"))',
                      "utf16-code-units": 'len(name.encode("utf-16-le")) // 2'}[wrong_unit]
        sample.write_text(original.replace(needle, f"if {expression} > LIMIT:"), encoding="utf-8")
    monkeypatch.setattr(driver, "ROOT", source_root)
    monkeypatch.setattr(driver, "INPUTS", inputs)


def boundary_catalogue(glyph):
    rows = CATALOGUE()
    assert len(rows) == 22
    assert len(glyph) == 1
    for case in rows:
        if "boundary" in case:
            quantity = {"below": 31, "at": 32, "above": 33}[case["boundary"]]
            case["name"] = glyph * quantity
            assert len(case["name"]) == quantity
            if case.get("success"):
                case["message"] = "Renamed to " + case["name"]
    return rows


def trace(output):
    return json.loads((output / "trace.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("glyph", ["文", "🧪"], ids=["han", "non-bmp"])
def test_multibyte_boundaries_preserve_the_sample_code_point_contract(display, tmp_path, monkeypatch, glyph):
    isolated_inputs(tmp_path, monkeypatch, glyph=glyph)
    monkeypatch.setattr(driver, "catalogue", lambda: boundary_catalogue(glyph))
    output = tmp_path / "full unicode matrix"
    report = driver.run(output)
    assert report["claim"] == "evidence_complete_against_declared_scenarios", report["execution_gaps"]
    assert report["statuses"]["passed"] == 22
    assert report["condition_coverage"] == {"total": 88, "passed": 88, "missing": []}
    assert report["timing_coverage"] == {"total": 8, "passed": 8, "missing": []}
    observations = {r["id"]: r["attempts"][0] for r in trace(output)["results"]}
    for identity, quantity in zip(BOUNDARIES, [31, 32, 33], strict=True):
        attempt = observations[identity]
        entered = next(s for s in attempt["steps"] if s["id"] == "enter")
        assert json.loads(entered["observation"])["entry"] == glyph * quantity
        assert attempt["cleanup"]["status"] == "passed"
    assert not list(output.glob("*/sandbox"))


@pytest.mark.parametrize("wrong_unit,glyph", [("utf8-bytes", "文"), ("utf16-code-units", "🧪")])
def test_wrong_unit_survives_separate_smokes_but_not_unicode_boundary_interaction(display, tmp_path, monkeypatch, wrong_unit, glyph):
    isolated_inputs(tmp_path, monkeypatch, glyph=glyph, wrong_unit=wrong_unit)
    # Real execution, not manufactured outcomes: ASCII boundaries and the short
    # Unicode example alone do not detect either deliberately wrong unit.
    baseline_output = tmp_path / "mutant original catalogue"
    baseline = driver.run(baseline_output)
    assert baseline["claim"] == "evidence_complete_against_declared_scenarios"
    assert baseline["statuses"]["passed"] == 22
    monkeypatch.setattr(driver, "catalogue", lambda: boundary_catalogue(glyph))
    output = tmp_path / "mutant unicode boundaries"
    report = driver.run(output, BOUNDARIES)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["failed"] == 2
    assert report["statuses"]["passed"] == 1
    assert report["statuses"]["not_run"] == 19
    assert report["condition_coverage"]["passed"] == 4
    assert report["timing_coverage"]["passed"] == 0
    results = {r["id"]: r["attempts"][0] for r in trace(output)["results"]}
    for identity in ("length-below", "length-at"):
        assert results[identity]["status"] == "failed"
        assert "Name exceeds 32 Unicode code points" in results[identity]["reason"]
        assert results[identity]["cleanup"]["status"] == "passed"
    assert not list(output.glob("*/sandbox"))
    # Different frozen books are not interchangeable evidence, even though the
    # case IDs remain stable and both use the same disposable mutant source.
    assert trace(output)["book_sha256"] != trace(baseline_output)["book_sha256"]
