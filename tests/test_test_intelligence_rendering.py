from __future__ import annotations

from copy import deepcopy

import pytest

from specify_cli.test_intelligence import (
    TestIntelligenceValidationError,
    render_test_catalog_markdown,
    validate_test_intelligence_bundle,
)


def _bundle() -> tuple[dict[str, object], ...]:
    universe = {
        "version": 1,
        "artifact": "test-universe",
        "feature_ref": "features/042-test-intelligence",
        "capabilities": [
            {
                "capability_id": "CAP-001",
                "title": "Evidence-backed order approval",
                "requirement_refs": ["REQ-001"],
                "test_case_ids": ["TC-001"],
                "scenario_ids": ["SCN-001"],
            }
        ],
        "scenarios": [
            {
                "scenario_id": "SCN-001",
                "title": "Manager approves a queued order",
                "capability_refs": ["CAP-001"],
                "test_case_ids": ["TC-001"],
                "coverage_ref": "COV-001",
            }
        ],
        "test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Approval succeeds from the real entrypoint",
                "kind": "review",
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "data_refs": ["TD-001"],
                "coverage_refs": ["COV-001"],
            }
        ],
    }
    catalog = {
        "version": 1,
        "artifact": "test-catalog",
        "cases": [
            {
                "test_case_id": "TC-001",
                "title": "Approval succeeds from the real entrypoint",
                "objective": "Prove that a manager can approve one queued order.",
                "stage": "review",
                "priority": "p0",
                "requirement_refs": ["REQ-001"],
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "test_data_refs": ["TD-001"],
                "verification_method": "runtime-diagnostics",
                "preconditions": ["The approval queue contains TD-001."],
                "steps": ["Open the official approval entrypoint.", "Approve the order."],
                "pass_criteria": ["The order becomes approved exactly once."],
                "evidence_requirements": ["runtime_diagnostics"],
            }
        ],
    }
    data_manifest = {
        "version": 1,
        "artifact": "test-data-manifest",
        "datasets": [
            {
                "test_data_id": "TD-001",
                "name": "Approval queue synthetic seed",
                "kind": "synthetic",
                "sensitivity": "sanitized",
                "contains_pii": False,
                "source": "generated",
                "applicable_test_case_ids": ["TC-001"],
                "applicable_scenario_ids": ["SCN-001"],
                "hygiene": {
                    "classification_reason": "Synthetic queue records only",
                    "sanitization_status": "not_required",
                    "retention_policy": "ephemeral",
                },
            }
        ],
    }
    coverage = {
        "version": 1,
        "artifact": "coverage-matrix",
        "rows": [
            {
                "coverage_id": "COV-001",
                "requirement_ref": "REQ-001",
                "capability_ref": "CAP-001",
                "scenario_ref": "SCN-001",
                "test_case_ref": "TC-001",
                "test_data_refs": ["TD-001"],
                "evidence_refs": ["EVD-001"],
                "acceptance_refs": ["HA-001"],
                "status": "covered",
            }
        ],
    }
    return universe, catalog, data_manifest, coverage


def test_valid_bundle_has_bidirectional_traceability() -> None:
    universe, catalog, data_manifest, coverage = _bundle()

    validate_test_intelligence_bundle(
        universe=universe,
        catalog=catalog,
        data_manifest=data_manifest,
        coverage_matrix=coverage,
    )


def test_bundle_rejects_unknown_data_and_one_way_case_links() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    broken_catalog = deepcopy(catalog)
    broken_case = broken_catalog["cases"][0]
    assert isinstance(broken_case, dict)
    broken_case["test_data_refs"] = ["TD-404"]

    with pytest.raises(TestIntelligenceValidationError) as error:
        validate_test_intelligence_bundle(
            universe=universe,
            catalog=broken_catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
        )

    message = str(error.value)
    assert "TD-404" in message
    assert "test-data-manifest" in message


def test_catalog_markdown_is_deterministic_and_declares_json_authority() -> None:
    _, catalog, _, _ = _bundle()

    first = render_test_catalog_markdown(catalog)
    second = render_test_catalog_markdown(deepcopy(catalog))

    assert first == second
    assert first.startswith("# Test Catalog\n")
    assert "`test-catalog.json` is canonical" in first
    assert "## TC-001 — Approval succeeds from the real entrypoint" in first
    assert "### Preconditions" in first
    assert "### Steps" in first
    assert "### Pass Criteria" in first
    assert "`TD-001`" in first
