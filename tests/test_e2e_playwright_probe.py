"""Real optional Node Playwright Test execution; no native parser fixtures."""
import importlib.util
from pathlib import Path

import pytest


def load_probe():
    path = Path(__file__).parent / "e2e_samples/e2e_playwright_probe.py"
    spec = importlib.util.spec_from_file_location("e2e_playwright_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_actual_playwright_success_failure_retry_empty_and_create_only(tmp_path):
    module = load_probe()
    env = module.environment()
    if env["missing"]:
        pytest.skip("Existing optional Node Playwright Test/Chromium unavailable: " + ", ".join(env["missing"]))
    result = module.probe(tmp_path / "browser-probe", env)
    rows = {row["route"]: row for row in result["routes"]}
    assert rows["success"]["statuses"]["passed"] == 1
    assert rows["failure"]["statuses"]["failed"] == 1
    assert rows["retry"]["statuses"]["flaky"] == 1
    assert rows["empty"]["claim"] != "complete_against_frozen_scope"
    assert rows["empty"]["durable_readbacks"] == []
    if rows["empty"]["statuses"] is not None:
        assert rows["empty"]["statuses"]["passed"] == 0 and rows["empty"]["statuses"]["not_run"] == 1
    else:
        assert rows["empty"]["command"]["exit_code"] == 2 and result["coverage_derived_for_every_route"] is False
        assert rows["empty"]["error"] == "Playwright report contains zero mapped tests"
    assert result["probe_completed"] is True and result["product_pass"] is False
    assert all(Path(row["command"]["stdout_ref"]).is_file() for row in rows.values())
    with pytest.raises(FileExistsError):
        module.probe(tmp_path / "browser-probe", env)
