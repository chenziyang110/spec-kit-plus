"""Design Evidence v1 schema and semantic validator tests."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.design_intelligence import (
    EVIDENCE_TYPE_INFERRED,
    EVIDENCE_TYPE_MEASURED,
    load_design_evidence_schema,
    normalize_evidence_type,
    validate_design_context,
    validate_design_evidence,
    validate_design_evidence_list,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    PROJECT_ROOT
    / "templates"
    / "design-intelligence"
    / "schema"
    / "design-evidence.schema.json"
)


def test_design_evidence_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["required"] == ["claim", "type"]
    assert "measured" in schema["properties"]["type"]["enum"]
    assert "inferred" in schema["properties"]["type"]["enum"]


def test_load_design_evidence_schema_matches_repo_file() -> None:
    assert load_design_evidence_schema() == json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )


def test_normalize_evidence_type_aliases() -> None:
    assert normalize_evidence_type("measured") == EVIDENCE_TYPE_MEASURED
    assert normalize_evidence_type("inferred") == EVIDENCE_TYPE_INFERRED
    assert normalize_evidence_type("evidence-backed-inference") == EVIDENCE_TYPE_INFERRED
    assert normalize_evidence_type("assumption") == "assumption"
    assert normalize_evidence_type("nope") is None


def test_validate_design_evidence_accepts_measured() -> None:
    result = validate_design_evidence(
        {
            "claim": "Primary is #0B5FFF",
            "type": "measured",
            "source": "devtools on /app",
            "confidence": 1.0,
        }
    )
    assert result.valid is True
    assert result.normalized_type == EVIDENCE_TYPE_MEASURED


def test_validate_design_evidence_rejects_inferred_without_source_or_gap() -> None:
    result = validate_design_evidence(
        {
            "claim": "Body font is Inter",
            "type": "inferred",
            "rationale": "looks like Inter",
        }
    )
    assert result.valid is False
    assert any("source" in error.message for error in result.errors)


def test_validate_design_evidence_rejects_non_measured_without_rationale() -> None:
    result = validate_design_evidence(
        {
            "claim": "Card radius is 12px",
            "type": "assumption",
            "source": "guess",
        }
    )
    assert result.valid is False
    assert any("rationale" in error.message for error in result.errors)


def test_validate_design_evidence_accepts_inferred_with_source_gap() -> None:
    result = validate_design_evidence(
        {
            "claim": "Body font is Inter",
            "type": "evidence-backed-inference",
            "source": None,
            "source_gap": "screenshot only; no CSS access",
            "rationale": "glyph similarity",
            "confidence": "low",
        }
    )
    assert result.valid is True
    assert result.normalized_type == EVIDENCE_TYPE_INFERRED


def test_validate_design_evidence_list_indexes_paths() -> None:
    result = validate_design_evidence_list(
        [
            {
                "claim": "ok",
                "type": "measured",
                "source": "css",
            },
            {
                "claim": "bad",
                "type": "inferred",
                "rationale": "pattern",
            },
        ]
    )
    assert result.valid is False
    assert any(error.path.startswith("$[1]") for error in result.errors)


def test_design_context_rejects_invalid_embedded_evidence() -> None:
    result = validate_design_context(
        {
            "version": "1.0",
            "intent": {"user_goal": "Ship calmer dashboard"},
            "evidence": [
                {
                    "claim": "Primary is blue",
                    "type": "inferred",
                    "rationale": "looks blue",
                }
            ],
        }
    )
    assert result.valid is False
    assert any("evidence" in error.path for error in result.errors)


def test_design_context_accepts_valid_embedded_evidence() -> None:
    result = validate_design_context(
        {
            "version": "1.0",
            "intent": {"user_goal": "Ship calmer dashboard"},
            "evidence": [
                {
                    "claim": "Primary is #0B5FFF",
                    "type": "measured",
                    "source": "token file",
                }
            ],
        }
    )
    assert result.valid is True
