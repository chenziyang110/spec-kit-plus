from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


ARTIFACT_CONTRACTS: tuple[dict[str, object], ...] = (
    {
        "name": "test-universe",
        "schema": "templates/test-universe-schema.json",
        "template": "templates/artifacts/test-universe.md",
        "valid": {
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
                    "title": "Approval journey succeeds from the real entrypoint",
                    "kind": "review",
                    "capability_refs": ["CAP-001"],
                    "scenario_refs": ["SCN-001"],
                    "data_refs": ["TD-001"],
                    "coverage_refs": ["COV-001"],
                }
            ],
        },
        "invalid": {
            "version": 1,
            "artifact": "test-universe",
            "feature_ref": "features/042-test-intelligence",
            "capabilities": [
                {
                    "capability_id": "capability-1",
                    "title": "Bad ids and one-way links",
                    "requirement_refs": [],
                    "test_case_ids": ["TC-404"],
                    "scenario_ids": [],
                }
            ],
            "scenarios": [],
            "test_cases": [],
        },
    },
    {
        "name": "test-catalog",
        "schema": "templates/test-catalog-schema.json",
        "template": "templates/artifacts/test-catalog.md",
        "valid": {
            "version": 1,
            "artifact": "test-catalog",
            "cases": [
                {
                    "test_case_id": "TC-001",
                    "title": "Approval journey succeeds from the real entrypoint",
                    "stage": "review",
                    "priority": "p0",
                    "requirement_refs": ["REQ-001"],
                    "capability_refs": ["CAP-001"],
                    "scenario_refs": ["SCN-001"],
                    "test_data_refs": ["TD-001"],
                    "verification_method": "runtime-diagnostics",
                    "pass_criteria": [
                        "Real entrypoint becomes ready",
                        "User-visible approval confirmation is shown",
                    ],
                }
            ],
        },
        "invalid": {
            "version": 1,
            "artifact": "test-catalog",
            "cases": [
                {
                    "test_case_id": "001",
                    "title": "No traceability or stable ids",
                    "stage": "review",
                    "priority": "p0",
                    "requirement_refs": [],
                    "capability_refs": [],
                    "scenario_refs": [],
                    "test_data_refs": [],
                    "verification_method": "runtime-diagnostics",
                    "pass_criteria": [],
                }
            ],
        },
    },
    {
        "name": "test-data-manifest",
        "schema": "templates/test-data-manifest-schema.json",
        "template": "templates/artifacts/test-data-manifest.md",
        "valid": {
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
        },
        "invalid": {
            "version": 1,
            "artifact": "test-data-manifest",
            "datasets": [
                {
                    "test_data_id": "TD-001",
                    "name": "Unclassified customer export",
                    "kind": "fixture",
                    "contains_pii": True,
                    "source": "captured",
                    "applicable_test_case_ids": ["TC-001"],
                    "applicable_scenario_ids": ["SCN-001"],
                    "hygiene": {
                        "classification_reason": "",
                        "sanitization_status": "not_required",
                        "retention_policy": "forever",
                    },
                }
            ],
        },
    },
    {
        "name": "coverage-matrix",
        "schema": "templates/coverage-matrix-schema.json",
        "template": "templates/artifacts/coverage-matrix.md",
        "valid": {
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
        },
        "invalid": {
            "version": 1,
            "artifact": "coverage-matrix",
            "rows": [
                {
                    "coverage_id": "1",
                    "requirement_ref": "REQ-001",
                    "capability_ref": "CAP-001",
                    "scenario_ref": "SCN-001",
                    "test_case_ref": "TC-999",
                    "test_data_refs": [],
                    "evidence_refs": [],
                    "acceptance_refs": [],
                    "status": "covered",
                }
            ],
        },
    },
)


def _load_json(relative: str) -> dict[str, object]:
    path = ROOT / relative
    assert path.is_file(), f"missing required contract file: {relative}"
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(relative: str) -> Draft202012Validator:
    schema = _load_json(relative)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.mark.parametrize("artifact", ARTIFACT_CONTRACTS, ids=lambda item: str(item["name"]))
def test_test_intelligence_contract_files_exist(artifact: dict[str, object]) -> None:
    schema_path = ROOT / str(artifact["schema"])
    template_path = ROOT / str(artifact["template"])

    assert schema_path.is_file(), f"missing required schema: {artifact['schema']}"
    assert template_path.is_file(), f"missing required template: {artifact['template']}"


@pytest.mark.parametrize("artifact", ARTIFACT_CONTRACTS, ids=lambda item: str(item["name"]))
def test_test_intelligence_schema_accepts_minimal_valid_example(
    artifact: dict[str, object],
) -> None:
    validator = _validator(str(artifact["schema"]))
    validator.validate(artifact["valid"])


@pytest.mark.parametrize("artifact", ARTIFACT_CONTRACTS, ids=lambda item: str(item["name"]))
def test_test_intelligence_schema_rejects_core_invalid_example(
    artifact: dict[str, object],
) -> None:
    validator = _validator(str(artifact["schema"]))
    errors = sorted(
        validator.iter_errors(artifact["invalid"]),
        key=lambda item: [str(part) for part in item.path],
    )
    assert errors, f"{artifact['name']} invalid example unexpectedly passed"


@pytest.mark.parametrize("artifact", ARTIFACT_CONTRACTS, ids=lambda item: str(item["name"]))
def test_canonical_json_scaffold_is_schema_valid(
    artifact: dict[str, object],
) -> None:
    scaffold = _load_json(f"templates/artifacts/{artifact['name']}.json")
    _validator(str(artifact["schema"])).validate(scaffold)


def test_test_universe_schema_can_express_stable_ids_and_bidirectional_links() -> None:
    schema = _load_json("templates/test-universe-schema.json")
    text = json.dumps(schema).lower()

    assert "cap-001" not in text
    assert "capability_id" in text
    assert "scenario_id" in text
    assert "test_case_id" in text
    assert "requirement_refs" in text
    assert "scenario_refs" in text or "scenario_ids" in text
    assert "test_case_refs" in text or "test_case_ids" in text
    assert "pattern" in text
    assert "minitems" in text


def test_test_data_manifest_schema_can_express_data_hygiene_constraints() -> None:
    schema = _load_json("templates/test-data-manifest-schema.json")
    text = json.dumps(schema).lower()

    assert "sensitivity" in text
    assert "contains_pii" in text
    assert "sanitization_status" in text
    assert "classification_reason" in text
    assert "retention_policy" in text
    assert "sanitized" in text
    assert "restricted" in text or "internal" in text


def test_catalog_schema_accepts_repository_refs_and_ids_beyond_999() -> None:
    contract = next(item for item in ARTIFACT_CONTRACTS if item["name"] == "test-catalog")
    payload = deepcopy(contract["valid"])
    case = payload["cases"][0]
    case["test_case_id"] = "TC-1000"
    case["requirement_refs"] = ["spec-contract.json#/acceptance_criteria/0"]
    case["capability_refs"] = ["CAP-1000"]
    case["scenario_refs"] = ["SCN-1000"]
    case["test_data_refs"] = ["TD-1000"]

    _validator(str(contract["schema"])).validate(payload)


def test_data_manifest_schema_rejects_unsanitized_pii() -> None:
    contract = next(
        item for item in ARTIFACT_CONTRACTS if item["name"] == "test-data-manifest"
    )
    payload = deepcopy(contract["valid"])
    dataset = payload["datasets"][0]
    dataset["contains_pii"] = True
    dataset["sensitivity"] = "public"
    dataset["hygiene"]["sanitization_status"] = "not_required"

    errors = list(_validator(str(contract["schema"])).iter_errors(payload))
    assert errors, "unsafe unsanitized PII unexpectedly passed"


def test_data_manifest_schema_accepts_large_ids_and_restricted_pii() -> None:
    contract = next(
        item for item in ARTIFACT_CONTRACTS if item["name"] == "test-data-manifest"
    )
    payload = deepcopy(contract["valid"])
    dataset = payload["datasets"][0]
    dataset["test_data_id"] = "TD-1000"
    dataset["applicable_test_case_ids"] = ["TC-1000"]
    dataset["applicable_scenario_ids"] = ["SCN-1000"]
    dataset["contains_pii"] = True
    dataset["sensitivity"] = "restricted"
    dataset["hygiene"]["sanitization_status"] = "pending"

    _validator(str(contract["schema"])).validate(payload)


def test_data_sensitivity_rejects_workflow_state_labels() -> None:
    contract = next(
        item for item in ARTIFACT_CONTRACTS if item["name"] == "test-data-manifest"
    )
    payload = deepcopy(contract["valid"])
    payload["datasets"][0]["sensitivity"] = "pending"

    errors = list(_validator(str(contract["schema"])).iter_errors(payload))
    assert errors, "workflow state unexpectedly accepted as a sensitivity classification"


def test_coverage_gap_row_can_be_explicit_without_fabricated_evidence() -> None:
    contract = next(
        item for item in ARTIFACT_CONTRACTS if item["name"] == "coverage-matrix"
    )
    payload = deepcopy(contract["valid"])
    row = payload["rows"][0]
    row["status"] = "missing"
    row["evidence_refs"] = []
    row["acceptance_refs"] = []

    _validator(str(contract["schema"])).validate(payload)


@pytest.mark.parametrize("status", ["blocked", "deferred", "excluded", "not_applicable"])
def test_coverage_schema_accepts_explicit_noncoverage_dispositions(status: str) -> None:
    contract = next(
        item for item in ARTIFACT_CONTRACTS if item["name"] == "coverage-matrix"
    )
    payload = deepcopy(contract["valid"])
    row = payload["rows"][0]
    row["status"] = status
    row["evidence_refs"] = []
    row["acceptance_refs"] = []

    _validator(str(contract["schema"])).validate(payload)


def test_coverage_matrix_template_is_a_deterministic_view_not_the_source_of_truth() -> None:
    template = ROOT / "templates" / "artifacts" / "coverage-matrix.md"
    assert template.is_file(), "missing required template: templates/artifacts/coverage-matrix.md"
    content = template.read_text(encoding="utf-8").lower()

    assert "coverage matrix" in content
    assert "deterministic" in content or "source of truth" in content
    assert "cov-" in content or "coverage_id" in content
    assert "tc-" in content or "test_case" in content
    assert "td-" in content or "test_data" in content
