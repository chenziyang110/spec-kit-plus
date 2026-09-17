"""Regression tests for the real hyphenated-directory evaluation tools."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "workflow-quality"


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load_tool("quick_adaptive_eval")
runner = load_tool("quick_eval_runner")


def row(**changes):
    value = {"mode": "direct-compact"}
    value.update(changes)
    return value


def group(*records):
    return runner.summarize(records)["groups"]["direct-compact"]


@pytest.mark.parametrize("metric", contract.METRICS)
@pytest.mark.parametrize("value", [None, "missing"])
def test_unknown_metrics_are_not_zero(metric, value):
    record = row(**({} if value == "missing" else {metric: value}))
    result = group(record)["metrics"][metric]
    assert result == {"sum": None, "total": None, "mean": None,
                      "observed": 0, "unknown": 1, "coverage": 0.0}


@pytest.mark.parametrize("metric", contract.METRICS)
@pytest.mark.parametrize("value", [-1, True, False, 1.2, "3", [], {}])
def test_invalid_metrics_fail(metric, value):
    with pytest.raises(ValueError, match=metric):
        runner.summarize([row(**{metric: value})])


@pytest.mark.parametrize("name", ["accepted", "human_intervention"])
@pytest.mark.parametrize("value", ["true", 1, 0, [], {}])
def test_observations_require_real_booleans(name, value):
    with pytest.raises(ValueError, match=name):
        group(row(**{name: value}))


def test_unknown_acceptance_has_no_rate():
    result = group(row(accepted=None))
    assert result["accepted_rate"] is None
    assert result["acceptance_coverage"] == 0
    assert result["unknown_quality"] == 1
    assert result["tokens"] is None
    assert result["tokens_per_accepted_run"] is None


def test_known_denominator_and_failure_cost():
    rows = [row(accepted=True, input_tokens=10, output_tokens=5),
            row(accepted=False, input_tokens=20, output_tokens=5)]
    result = group(*rows)
    assert result["accepted_rate"] == 0.5
    assert result["tokens_per_accepted_run"] == 40
    result = group(*rows, row())
    assert result["accepted_rate"] == 0.5
    assert result["acceptance_coverage"] == 2 / 3
    assert result["tokens"] is None
    assert result["tokens_per_accepted_run"] is None
    assert result["metrics"]["tokens"]["sum"] == 40
    assert result["tokens_per_run"] == 20


def test_zero_is_an_observed_value():
    result = group(row(input_tokens=0, output_tokens=0, accepted=True))
    assert result["tokens"] == result["tokens_per_accepted_run"] == 0
    assert result["metrics"]["tokens"]["observed"] == 1


def test_dataclass_roundtrip_preserves_nulls():
    record = contract.QuickEvalRecord(case_id="Q001", mode="worker-full")
    assert contract.summarize([record]) == runner.summarize([asdict(record)])
    assert runner.summarize([asdict(record)])["groups"]["worker-full"]["tokens"] is None


def test_dataclass_uses_same_validation():
    with pytest.raises(ValueError, match="accepted"):
        contract.QuickEvalRecord(case_id="Q001", mode="worker-full", accepted="true")


def test_duplicate_run_rejected_across_modes():
    with pytest.raises(ValueError, match="duplicate run_id"):
        runner.summarize([row(run_id="r1"), row(run_id="r1", mode="worker-full")])


def test_legacy_identity_is_not_claimed_complete():
    result = runner.summarize([row()])
    assert result["identity"]["deduplication_complete"] is False
    assert result["rules"]["comparability_verified"] is False


@pytest.mark.parametrize("mode", [None, "bad", [], {}])
def test_invalid_mode(mode):
    with pytest.raises(ValueError, match="mode"):
        group(row(mode=mode))


def test_all_modes():
    assert set(runner.summarize([row(mode=m) for m in contract.MODES])["groups"]) == contract.MODES


def test_strict_identity():
    complete = row(**{name: f"value-{name}" for name in contract.IDENTITY_FIELDS})
    assert runner.summarize([complete], strict=True)["identity"]["deduplication_complete"]
    for name in contract.IDENTITY_FIELDS:
        incomplete = dict(complete)
        del incomplete[name]
        with pytest.raises(ValueError, match=name):
            runner.summarize([incomplete], strict=True)


@pytest.mark.parametrize("text", [
    '{"mode":"direct-compact","accepted":true,"accepted":false}\n',
    '{"mode":"direct-compact","input_tokens":NaN}\n',
    '[]\n', 'null\n', '{bad}\n',
])
def test_jsonl_diagnostics(tmp_path, text):
    source = tmp_path / "records.jsonl"
    source.write_text("\n" + text, encoding="utf-8")
    with pytest.raises(ValueError, match="records.jsonl:2"):
        runner.load_records(source)


def cli(source, output, *extra):
    return subprocess.run([sys.executable, str(TOOLS / "quick_eval_runner.py"),
                           str(source), "--output", str(output), *extra],
                          text=True, capture_output=True, timeout=15)


def test_real_cli_and_output_protection(tmp_path):
    source, output = tmp_path / "records.jsonl", tmp_path / "report.json"
    original = json.dumps(row(input_tokens=None, output_tokens=None)) + "\n"
    source.write_text(original, encoding="utf-8")
    first = cli(source, output)
    assert first.returncode == 0, first.stderr
    report = json.loads(output.read_text())
    assert report["schema"] == "quick-adaptive-eval-report-v2"
    assert report["groups"]["direct-compact"]["accepted_rate"] is None
    before = output.read_bytes()
    assert cli(source, output).returncode == 2
    assert output.read_bytes() == before
    assert cli(source, source).returncode == 2
    assert source.read_text() == original


@pytest.mark.parametrize("content", ["", "\n", "broken", '{"mode":"bad"}\n'])
def test_bad_cli_input_does_not_create_report(tmp_path, content):
    source, output = tmp_path / "records.jsonl", tmp_path / "report.json"
    source.write_text(content, encoding="utf-8")
    result = cli(source, output)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_strict_cli_rejects_unidentified_records(tmp_path):
    source, output = tmp_path / "records.jsonl", tmp_path / "report.json"
    source.write_text(json.dumps(row()) + "\n", encoding="utf-8")
    assert cli(source, output, "--strict").returncode == 2
    assert not output.exists()
