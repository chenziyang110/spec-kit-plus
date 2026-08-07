"""Executable UI quality gate report + starter rules tests."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.design_intelligence import (
    GATE_REPORT_VERSION,
    load_ui_quality_gate_report_schema,
    run_ui_quality_gate_rules,
    validate_ui_quality_gate_report,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    PROJECT_ROOT
    / "templates"
    / "design-intelligence"
    / "schema"
    / "ui-quality-gate-report.schema.json"
)


def test_ui_quality_gate_report_schema_exists() -> None:
    assert SCHEMA_PATH.is_file()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["version"]["const"] == GATE_REPORT_VERSION
    assert load_ui_quality_gate_report_schema() == schema


def test_run_ui_quality_gate_rules_passes_clean_inputs() -> None:
    report = run_ui_quality_gate_rules(
        evidence=[
            {
                "claim": "Primary #0B5FFF",
                "type": "measured",
                "source": "css",
            }
        ],
        required_states=["default", "focus", "loading"],
        observed_states=["default", "focus", "loading", "error"],
        scope="feature-ui",
    )
    assert report.status == "pass"
    assert report.issues == ()
    assert validate_ui_quality_gate_report(report.as_dict()).valid is True


def test_run_ui_quality_gate_rules_flags_evidence_and_states() -> None:
    report = run_ui_quality_gate_rules(
        evidence=[
            {
                "claim": "Font is Inter",
                "type": "inferred",
                "rationale": "looks like Inter",
            }
        ],
        required_states=["empty", "error"],
        observed_states=["default"],
    )
    assert report.status == "fail"
    categories = {issue.category for issue in report.issues}
    assert "evidence" in categories
    assert "consistency" in categories
    assert validate_ui_quality_gate_report(report.as_dict()).valid is True


def test_run_ui_quality_gate_rules_not_run_without_inputs() -> None:
    report = run_ui_quality_gate_rules()
    assert report.status == "not-run"
