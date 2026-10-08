"""Validate method reuse against real local packaging commands and the Go CLI."""

import importlib.util
from pathlib import Path


def test_native_operation_first_reuse_and_verified_improvement(built_unified_runtime, tmp_path):
    sample = Path(__file__).parent / "e2e_samples" / "do_operation_probe.py"
    spec = importlib.util.spec_from_file_location("do_operation_probe", sample)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.probe(built_unified_runtime, tmp_path / "project")
    assert result["status"] == "passed"
    assert result["native_observations"] == 9
    assert [item["revision"] for item in result["rounds"]] == [1, 1, 2]
    assert result["runtime_execution_verified"] is False
