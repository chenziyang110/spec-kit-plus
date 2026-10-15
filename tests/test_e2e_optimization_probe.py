"""Cost probe regression: actual runtime persistence/refusal and durable oracle."""
import importlib.util
from pathlib import Path

import pytest


def load_probe():
    path = Path(__file__).parent / "e2e_samples/e2e_optimization_probe.py"
    spec = importlib.util.spec_from_file_location("e2e_optimization_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_keeps_every_scope_and_seven_stage_denominator():
    probe = load_probe()
    for size in (7, 70, 700):
        plan = probe.make_plan(size)
        assert len(plan["tasks"]) == size
        for scope in plan["scope"]:
            assert {t["stage"] for t in plan["tasks"] if scope["id"] in t["scope_ids"]} == set(range(1, 8))
    with pytest.raises(ValueError):
        probe.make_plan(8)


def test_actual_runtime_resume_refusal_drift_and_cli_oracle(built_unified_runtime, tmp_path):
    report = load_probe().runtime_probe(built_unified_runtime, tmp_path / "probe", (7,), repeats=1)
    assert {a["id"] for a in report["assertions"]} == {"resume-7", "single-input-drift"}
    assert all(a["passed"] for a in report["assertions"])
    refusals = [m for m in report["measurements"] if m["exit_code"] != 0]
    assert {m["action"] for m in refusals} == {"task-start", "task-submit", "status"}
    assert report["agent_tokens"]["status"] == "unavailable"
    assert all(Path(m["stdout_ref"]).is_file() for m in report["measurements"])
