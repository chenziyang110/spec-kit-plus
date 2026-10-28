"""Exercise the optimized protocol with actual packages and Chinese parameters."""
import importlib.util
import json
from pathlib import Path


def test_real_parameter_reuse_incremental_and_fast_closeout(built_unified_runtime, tmp_path):
    sample = Path(__file__).parent / "e2e_samples/do_optimization_probe.py"
    spec = importlib.util.spec_from_file_location("do_optimization_probe", sample)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.probe(built_unified_runtime, tmp_path / "project")
    assert result["status"] == "passed"
    assert [r["revision"] for r in result["rounds"]] == [1, 1, 1]
    assert len({r["instance_digest"] for r in result["rounds"]}) == 3
    assert len({r["method_digest"] for r in result["rounds"]}) == 1
    assert result["rounds"][0]["retained_attempts"] == 3
    assert result["closeout_public_calls"]["complete"] == 1
    assert result["incremental_required_actions"]["verified_retention"] == 1
    assert result["closeout_public_calls"]["legacy_finish_update_finish"] == 5
    assert result["closeout_owner_calls"]["legacy_finish_update_finish"] == 3
    assert result["incremental_required_actions"]["full_replan"] == 4
    assert result["baseline"]["revision"] == 1
    assert result["native_observations"] == 19
    assert result["runtime_execution_verified"] is False
    print(json.dumps({"rounds": [{key: row[key] for key in ("revision", "public_runtime_calls", "native_observations", "retained_attempts", "adapter_episode_ms")} for row in result["rounds"]],
                      "baseline": {key: result["baseline"][key] for key in ("revision", "public_runtime_calls", "native_observations", "adapter_episode_ms")},
                      "closeout_public_calls": result["closeout_public_calls"], "incremental_required_actions": result["incremental_required_actions"]}))
