from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import specify_cli.test_intelligence as test_intelligence
from specify_cli.test_intelligence import (
    TestIntelligenceValidationError,
    render_test_catalog_markdown,
    render_test_data_manifest_markdown,
    render_test_universe_markdown,
    validate_test_intelligence_bundle,
)


def _bundle() -> tuple[dict[str, object], ...]:
    universe = {
        "version": 1,
        "artifact": "test-universe",
        "feature_ref": "features/042-test-intelligence",
        "obligations": [
            {
                "obligation_id": "TO-001",
                "title": "Manager approval is accepted exactly once",
                "source_refs": ["REQ-001"],
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "dimension": "functional",
                "risk_tier": "critical",
                "applicability": "applicable",
                "rationale": "Approval is inside the frozen feature scope.",
                "required_evidence_classes": ["system"],
                "test_case_ids": ["TC-001"],
                "gap_refs": [],
                "invalidation_triggers": ["Approval contract or entrypoint changes"],
            }
        ],
        "capabilities": [
            {
                "capability_id": "CAP-001",
                "title": "Evidence-backed order approval",
                "requirement_refs": ["REQ-001"],
                "obligation_ids": ["TO-001"],
                "test_case_ids": ["TC-001"],
                "scenario_ids": ["SCN-001"],
            }
        ],
        "scenarios": [
            {
                "scenario_id": "SCN-001",
                "title": "Manager approves a queued order",
                "capability_refs": ["CAP-001"],
                "obligation_refs": ["TO-001"],
                "test_case_ids": ["TC-001"],
                "coverage_ref": "COV-001",
            }
        ],
        "test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Approval succeeds from the real entrypoint",
                "kind": "review",
                "obligation_refs": ["TO-001"],
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
                "status": "approved",
                "stage": "review",
                "priority": "p0",
                "risk_tags": ["approval", "idempotency"],
                "requirement_refs": ["REQ-001"],
                "obligation_refs": ["TO-001"],
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "test_data_refs": ["TD-001"],
                "automation_target": "hybrid",
                "owner_stage": "review",
                "environment": ["isolated review runtime"],
                "entrypoint_refs": ["approval UI"],
                "verification_method": "runtime-diagnostics",
                "preconditions": ["The approval queue contains TD-001."],
                "roles_permissions": ["manager role"],
                "configuration": ["approval feature enabled"],
                "steps": ["Open the official approval entrypoint.", "Approve the order."],
                "expected_results": ["The queued order is visible.", "The order becomes approved exactly once."],
                "variants": {
                    "positive": "covered",
                    "negative": "deferred",
                    "boundary": "deferred",
                    "state": "covered",
                    "permission": "covered",
                    "concurrency": "deferred",
                    "timing": "not_applicable",
                    "recovery": "deferred",
                    "compatibility": "not_applicable",
                },
                "cleanup_reset": "Delete the synthetic order after review.",
                "idempotency": "Repeated approval is a no-op.",
                "side_effect_boundary": "Only the isolated synthetic order may change.",
                "pass_criteria": ["The order becomes approved exactly once."],
                "evidence_requirements": ["runtime_diagnostics"],
                "freshness_rule": "Evidence must match the current source fingerprint.",
                "invalidation_triggers": ["Approval contract, role, or entrypoint changes"],
                "flake_risks": [],
                "residual_risk": "Deferred variants remain tracked in test-gaps.json.",
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
                "disposition": "generate",
                "readiness": "recipe-ready",
                "provenance_refs": [],
                "format": "json",
                "schema_ref": "approval-order-schema.json",
                "volume": "one queued order",
                "relationships": ["order belongs to synthetic manager tenant"],
                "constraints": ["non-production identifiers only"],
                "license": "project-generated",
                "usage_limits": "isolated test environments only",
                "fixed_seed": "42",
                "distribution": "one deterministic happy-path record",
                "edge_partitions": ["queued state"],
                "checksum": "sha256 computed after generation",
                "allowed_usage": ["review", "automated test"],
                "environment_refs": ["isolated review runtime"],
                "snapshot_binding": "current source fingerprint",
                "refresh_policy": "regenerate when the order schema changes",
                "cleanup_reset": "delete the synthetic order after the run",
                "oracle_binding": "order status equals approved exactly once",
                "limitations": [],
                "residual_risk": "none",
                "generation_recipe": "Generate deterministic approval queue records with a fixed seed.",
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
                "obligation_ref": "TO-001",
                "capability_ref": "CAP-001",
                "scenario_ref": "SCN-001",
                "test_case_ref": "TC-001",
                "test_data_refs": ["TD-001"],
                "evidence_refs": ["EVD-001"],
                "acceptance_refs": ["HA-001"],
                "gap_refs": [],
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


def test_bundle_rejects_coverage_gap_not_linked_from_obligation() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    row = coverage["rows"][0]
    row["status"] = "partial"
    row["gap_refs"] = ["GAP-001"]
    row["evidence_refs"] = []
    row["acceptance_refs"] = []

    with pytest.raises(TestIntelligenceValidationError, match="gap_refs are not linked"):
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


def test_bundle_rejects_coverage_dataset_absent_from_its_case() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    universe["test_cases"][0]["data_refs"] = []
    catalog["cases"][0]["test_data_refs"] = []

    with pytest.raises(TestIntelligenceValidationError, match="absent from catalog case"):
        validate_test_intelligence_bundle(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
        )


def test_bundle_rejects_duplicate_stable_ids() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    duplicate = deepcopy(universe["capabilities"][0])
    universe["capabilities"].append(duplicate)

    with pytest.raises(TestIntelligenceValidationError, match="duplicate CAP-001"):
        validate_test_intelligence_bundle(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
        )


def test_bundle_rejects_one_way_capability_links() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    universe["capabilities"].append(
        {
            "capability_id": "CAP-002",
            "title": "Unacknowledged capability link",
            "requirement_refs": ["REQ-002"],
            "obligation_ids": ["TO-001"],
            "test_case_ids": ["TC-001"],
            "scenario_ids": ["SCN-001"],
        }
    )

    with pytest.raises(TestIntelligenceValidationError, match="reverse"):
        validate_test_intelligence_bundle(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
        )


def test_bundle_rejects_an_unaccounted_frozen_obligation() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    universe["obligations"][0]["test_case_ids"] = ["TC-999"]

    with pytest.raises(TestIntelligenceValidationError, match="TO-001"):
        validate_test_intelligence_bundle(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
        )


def test_bundle_rejects_coverage_requirement_drift() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    coverage["rows"][0]["requirement_ref"] = "REQ-999"

    with pytest.raises(TestIntelligenceValidationError, match="REQ-999"):
        validate_test_intelligence_bundle(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
        )


def test_scenario_can_trace_multiple_layered_cases_and_coverage_rows() -> None:
    universe, catalog, data_manifest, coverage = _bundle()

    second_universe_case = deepcopy(universe["test_cases"][0])
    second_universe_case["test_case_id"] = "TC-002"
    second_universe_case["title"] = "Approval contract is enforced at integration level"
    second_universe_case["kind"] = "integration"
    second_universe_case["coverage_refs"] = ["COV-002"]
    universe["test_cases"].append(second_universe_case)
    universe["obligations"][0]["test_case_ids"].append("TC-002")
    universe["capabilities"][0]["test_case_ids"].append("TC-002")
    scenario = universe["scenarios"][0]
    scenario["test_case_ids"].append("TC-002")
    scenario.pop("coverage_ref")
    scenario["coverage_refs"] = ["COV-001", "COV-002"]

    second_catalog_case = deepcopy(catalog["cases"][0])
    second_catalog_case["test_case_id"] = "TC-002"
    second_catalog_case["title"] = "Approval contract is enforced at integration level"
    second_catalog_case["stage"] = "integration"
    catalog["cases"].append(second_catalog_case)
    data_manifest["datasets"][0]["applicable_test_case_ids"].append("TC-002")

    second_coverage_row = deepcopy(coverage["rows"][0])
    second_coverage_row["coverage_id"] = "COV-002"
    second_coverage_row["test_case_ref"] = "TC-002"
    coverage["rows"].append(second_coverage_row)

    validate_test_intelligence_bundle(
        universe=universe,
        catalog=catalog,
        data_manifest=data_manifest,
        coverage_matrix=coverage,
    )


def test_bundle_allows_a_case_with_no_fabricated_test_data_dependency() -> None:
    universe, catalog, data_manifest, coverage = _bundle()
    universe["test_cases"][0]["data_refs"] = []
    catalog["cases"][0]["test_data_refs"] = []
    data_manifest["datasets"] = []
    coverage["rows"][0]["test_data_refs"] = []

    validate_test_intelligence_bundle(
        universe=universe,
        catalog=catalog,
        data_manifest=data_manifest,
        coverage_matrix=coverage,
    )


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
    assert "### Obligation Refs" in first
    assert "### Expected Results" in first
    assert "### Variant Dispositions" in first
    assert "### Lifecycle and Isolation" in first
    assert "`TD-001`" in first
    assert "1. Open the official approval entrypoint." in first
    assert "2. Approve the order." in first
    assert first.index("1. Open the official approval entrypoint.") < first.index(
        "2. Approve the order."
    )
    assert "- The order becomes approved exactly once." in first


def test_universe_markdown_renders_capability_scenario_and_case_details() -> None:
    universe, _, _, _ = _bundle()

    rendered = render_test_universe_markdown(universe)

    assert "## Capabilities" in rendered
    assert "## Obligations" in rendered
    assert "### TO-001 — Manager approval is accepted exactly once" in rendered
    assert "### CAP-001 — Evidence-backed order approval" in rendered
    assert "## Scenarios" in rendered
    assert "### SCN-001 — Manager approves a queued order" in rendered
    assert "## Test Cases" in rendered
    assert "### TC-001 — Approval succeeds from the real entrypoint" in rendered
    assert "- Kind: `review`" in rendered
    assert "`COV-001`" in rendered


def test_data_manifest_markdown_renders_material_provenance_and_reproducibility() -> None:
    _, _, data_manifest, _ = _bundle()

    rendered = render_test_data_manifest_markdown(data_manifest)

    assert "- Disposition: `generate`" in rendered
    assert "- License: project-generated" in rendered
    assert "- Fixed Seed: 42" in rendered
    assert "### Edge Partitions" in rendered
    assert "- queued state" in rendered
    assert "### Limitations" in rendered


def test_schema_candidates_include_the_wheel_core_pack_location() -> None:
    source, packaged = test_intelligence._schema_candidates(
        Path("test-universe-schema.json")
    )

    assert source.name == "test-universe-schema.json"
    assert packaged == (
        Path(test_intelligence.__file__).resolve().parent
        / "core_pack"
        / "templates"
        / "test-universe-schema.json"
    )
