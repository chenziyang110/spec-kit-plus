from __future__ import annotations

import json
from pathlib import Path

from specify_cli.design import (
    _direction_visual_fingerprint,
    _load_design_diagnostic_contract,
    _load_visual_fingerprint_rule,
    _visual_fingerprints_comparable,
    enrich_design_diagnostics,
    lint_design_preview_file,
)
from tests.test_design_preview import (
    _candidate_preview,
    _preview_manifest,
    _replace_preview_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_visual_fingerprint_rule_is_versioned_v1() -> None:
    rule = _load_visual_fingerprint_rule()
    assert rule["version"] == "1"
    assert rule["dimensions"] == [
        "typography",
        "geometry",
        "density",
        "elevation",
        "motion",
        "modes",
    ]
    spec = (
        REPO_ROOT / "templates" / "design-library" / "visual-fingerprint-spec.md"
    ).read_text(encoding="utf-8")
    assert 'version: "1"' in spec
    assert "Comparable" in spec or "comparable" in spec


def test_direction_visual_fingerprint_includes_version_and_dimensions() -> None:
    fingerprint = _direction_visual_fingerprint(
        {
            "typography": {"display": "A", "body": "B", "heading_tracking": "0"},
            "geometry": {"radius_control": "4px", "radius_surface": "8px"},
            "density": {"space_unit": "4px", "label": "compact", "scale": 1},
            "elevation": {"surface": "none", "control": "none"},
            "motion": {
                "duration_fast": "100ms",
                "duration_base": "200ms",
                "duration_slow": "400ms",
                "easing_standard": "ease",
                "easing_emphasized": "ease",
                "distance_enter": "8px",
                "stagger": "10ms",
                "reduced_motion": "opacity only",
            },
            "modes": {"light": {"canvas": "#fff"}, "dark": {}, "high-contrast": {}},
        }
    )
    assert fingerprint["version"] == "1"
    assert fingerprint["dimensions"][0] == "typography"
    assert len(fingerprint["hash"]) == 64
    same = _direction_visual_fingerprint(
        {
            "typography": {"display": "A", "body": "B", "heading_tracking": "0"},
            "geometry": {"radius_control": "4px", "radius_surface": "8px"},
            "density": {"space_unit": "4px", "label": "compact", "scale": 1},
            "elevation": {"surface": "none", "control": "none"},
            "motion": {
                "duration_fast": "100ms",
                "duration_base": "200ms",
                "duration_slow": "400ms",
                "easing_standard": "ease",
                "easing_emphasized": "ease",
                "distance_enter": "8px",
                "stagger": "10ms",
                "reduced_motion": "opacity only",
            },
            "modes": {"light": {"canvas": "#fff"}, "dark": {}, "high-contrast": {}},
            "signature_element": "ignored for fingerprint",
        }
    )
    assert _visual_fingerprints_comparable(fingerprint, same)
    assert fingerprint["hash"] == same["hash"]


def test_visual_fingerprints_not_comparable_across_versions() -> None:
    left = {"version": "1", "dimensions": ["typography"], "hash": "a" * 64}
    right = {"version": "2", "dimensions": ["typography"], "hash": "a" * 64}
    assert not _visual_fingerprints_comparable(left, right)


def test_diagnostic_contract_maps_quality_and_semantic_codes() -> None:
    contract = _load_design_diagnostic_contract()
    codes = contract["codes"]
    assert codes["preview-manifest-schema-error"]["layer"] == "structural"
    assert codes["preview-scaffold-taste-reason"]["layer"] == "semantic"
    assert codes["preview-undifferentiated-direction-visuals"]["layer"] == "quality"
    assert any(
        "metadata" in item.lower() or "token" in item.lower()
        for item in codes["preview-undifferentiated-direction-visuals"]["agent_action"]
    )


def test_lint_enriches_identical_visual_failure_with_recovery(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    first = directions[0]
    assert isinstance(first, dict)
    shared = {
        key: first[key]
        for key in (
            "typography",
            "geometry",
            "density",
            "elevation",
            "motion",
            "modes",
        )
    }
    for direction in directions:
        assert isinstance(direction, dict)
        direction.update(shared)
    preview = tmp_path / "same-visuals.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")
    match = next(
        item
        for item in diagnostics
        if item.code == "preview-undifferentiated-direction-visuals"
    )
    assert match.layer == "quality"
    assert match.recovery
    assert match.agent_action
    assert match.why
    assert any("metadata" in item.lower() or "token" in item.lower() for item in match.agent_action)


def test_enrich_design_diagnostics_applies_default_for_unknown_code() -> None:
    from specify_cli.design import DesignDiagnostic

    enriched = enrich_design_diagnostics(
        [DesignDiagnostic("unknown-code-xyz", "boom", "path")]
    )[0]
    assert enriched.layer == "structural"
    assert enriched.recovery
    assert enriched.agent_action


def test_packaging_includes_diagnostic_and_fingerprint_contracts() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (
        '"templates/design-diagnostic-contract.json" = '
        '"specify_cli/core_pack/templates/design-diagnostic-contract.json"'
    ) in pyproject
    assert (
        '"templates/visual-fingerprint-rule.json" = '
        '"specify_cli/core_pack/templates/visual-fingerprint-rule.json"'
    ) in pyproject
    assert (REPO_ROOT / "templates" / "design-diagnostic-contract.json").is_file()
    assert (REPO_ROOT / "templates" / "visual-fingerprint-rule.json").is_file()
    assert (
        REPO_ROOT / "templates" / "design-library" / "visual-fingerprint-spec.md"
    ).is_file()
