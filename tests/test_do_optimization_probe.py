"""Exercise the optimized protocol with actual packages and Chinese parameters."""
import importlib.util
import json
from pathlib import Path

import pytest


def _load_probe():
    sample = Path(__file__).parent / "e2e_samples/do_optimization_probe.py"
    spec = importlib.util.spec_from_file_location("do_optimization_probe", sample)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_parameter_reuse_incremental_and_fast_closeout(built_unified_runtime, tmp_path):
    module = _load_probe()
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


@pytest.mark.parametrize("source_write", [False, True])
def test_workspace_timings_and_exact_source_packet(built_unified_runtime, tmp_path, source_write):
    result = _load_probe().workspace_probe(built_unified_runtime, tmp_path / "project", source_write=source_write,
                                           timings=True, tracked_files=64, output_mib=2)
    assert result["validation_status"] == ("blocked" if source_write else "passed")
    start = result["cli"]["start"]["runtime"]
    assert start["phases"]["workspace_status"]["calls"] == 1
    assert start["phases"]["work_write_lock"]["calls"] >= 1
    assert start["counts"]["baseline_path_digests"] >= 64
    assert result["cli"]["replan"]["runtime"]["phases"]["workspace_status"]["calls"] == 2
    validation = result["cli"]["validate"]["runtime"]
    assert validation["phases"]["workspace_status"]["calls"] == 2
    assert validation["counts"]["artifact_hashes"] == 1
    assert validation["counts"]["artifact_bytes"] == 2 * 1024 * 1024
