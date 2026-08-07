"""DesignContext v1 schema and structural validator tests."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.design_intelligence import (
    DESIGN_CONTEXT_VERSION,
    load_design_context_schema,
    validate_design_context,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    PROJECT_ROOT
    / "templates"
    / "design-intelligence"
    / "schema"
    / "design-context.schema.json"
)


def test_design_context_schema_file_exists_and_declares_v1() -> None:
    assert SCHEMA_PATH.is_file()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["required"] == ["version", "intent"]
    assert schema["properties"]["version"]["const"] == "1.0"
    assert "user_goal" in schema["properties"]["intent"]["required"]


def test_load_design_context_schema_matches_repo_file() -> None:
    loaded = load_design_context_schema()
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert loaded == on_disk
    assert DESIGN_CONTEXT_VERSION == "1.0"


def test_validate_design_context_rejects_empty_object() -> None:
    result = validate_design_context({})
    assert result.valid is False
    assert result.ok is False
    paths = {error.path for error in result.errors}
    assert "$.version" in paths or any("version" in e.message for e in result.errors)
    assert "$.intent" in paths or any("intent" in e.message for e in result.errors)


def test_validate_design_context_rejects_non_object() -> None:
    result = validate_design_context([])
    assert result.valid is False
    assert result.errors[0].path == "$"


def test_validate_design_context_accepts_minimal_payload() -> None:
    result = validate_design_context(
        {
            "version": "1.0",
            "intent": {"user_goal": "Ship a calmer ops dashboard"},
        }
    )
    assert result.valid is True
    assert result.errors == ()


def test_validate_design_context_accepts_full_v1_shape() -> None:
    result = validate_design_context(
        {
            "version": "1.0",
            "intent": {
                "user_goal": "Redesign agent dashboard",
                "product_context": "B2B AI ops product",
            },
            "design_language": {
                "tone": "professional calm",
                "density": 7,
                "motion": 2,
                "variance": 4,
                "visual_direction": "dense workbench, not marketing hero",
            },
            "system": {
                "tokens": {"color.primary": "#0B5FFF"},
                "components": ["Button", "Table"],
                "constraints": ["no generic three-card hero"],
            },
            "references": [
                {"source": "docs/refs/dashboard.png", "type": "screenshot"},
            ],
            "decisions": [
                {"rationale": "Prefer hierarchy over equal-weight cards"},
            ],
        }
    )
    assert result.valid is True


def test_validate_design_context_rejects_bad_version_and_dial_range() -> None:
    result = validate_design_context(
        {
            "version": "2.0",
            "intent": {"user_goal": "x"},
            "design_language": {"density": 99},
        }
    )
    assert result.valid is False
    messages = " ".join(error.message for error in result.errors)
    assert "1.0" in messages or "version" in messages.lower()
