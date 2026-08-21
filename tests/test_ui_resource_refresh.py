from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ui-resource-refresh"
REFRESH = ROOT / "templates" / "ui-professional-skills" / "refresh.py"


def _load_refresh_module():
    assert REFRESH.is_file(), f"missing expected refresh entrypoint: {REFRESH}"
    spec = importlib.util.spec_from_file_location("ui_resource_refresh", REFRESH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "field_name, expected",
    [
        ("selected_only", ["material-ui", "ag-grid", "tiptap"]),
        ("offline_default", True),
        (
            "allowed_source_kinds",
            {"agent-skill", "mcp", "llms-txt", "markdown"},
        ),
    ],
)
def test_refresh_entrypoint_contract_is_present(field_name, expected) -> None:
    module = _load_refresh_module()
    assert hasattr(module, field_name), f"missing contract field: {field_name}"
    assert getattr(module, field_name) == expected


def test_refresh_normalizes_text_before_hashing() -> None:
    module = _load_refresh_module()
    text_a = "  Hello\nworld  "
    text_b = "hello world"
    assert module.normalized_hash(text_a) == module.normalized_hash(text_b)


def test_refresh_rejects_non_official_or_unauthorized_sources() -> None:
    module = _load_refresh_module()
    snapshot = FIXTURES / "selected-snapshot.json"
    report = module.run_refresh(
        snapshot_path=snapshot,
        baseline_path=None,
        offline=True,
    )
    assert report["run_mode"] == "read_only"
    assert report["status"] == "complete"
    assert report["network_policy"] == "blocked_by_default"
    assert report["writes"] == "none"
    assert report["install_or_upgrade"] == "unauthorized"
    assert all(item["source_kind"] in {"agent-skill", "mcp", "llms-txt", "markdown"} for item in report["items"])


def test_refresh_selected_only_and_output_order_are_stable() -> None:
    module = _load_refresh_module()
    snapshot = FIXTURES / "selected-snapshot.json"
    report_a = module.run_refresh(snapshot_path=snapshot, baseline_path=None, offline=True)
    report_b = module.run_refresh(snapshot_path=snapshot, baseline_path=None, offline=True)
    assert [item["resource_id"] for item in report_a["items"]] == ["material-ui", "ag-grid", "tiptap"]
    assert report_a["items"] == report_b["items"]


def test_refresh_reports_content_version_license_and_missing_drift() -> None:
    module = _load_refresh_module()
    snapshot = FIXTURES / "selected-snapshot.json"
    baseline = FIXTURES / "baseline.json"
    report = module.run_refresh(snapshot_path=snapshot, baseline_path=baseline, offline=True)
    drift_codes = {item["drift"]["status"] for item in report["items"]}
    assert {"content_changed", "version_changed", "license_changed", "missing", "blocked", "unknown"} & drift_codes


def test_refresh_forbids_install_and_upgrade_side_effects() -> None:
    module = _load_refresh_module()
    assert getattr(module, "INSTALL_POLICY", None) == "unauthorized"
    assert getattr(module, "UPGRADE_POLICY", None) == "unauthorized"
    assert getattr(module, "NETWORK_POLICY", None) == "blocked_by_default"
