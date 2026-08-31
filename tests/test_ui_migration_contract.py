"""Regression cases for stateful, asset-backed native UI migrations."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from specify_cli.design_intelligence.source_continuity import (
    validate_ui_source_continuity,
)
from specify_cli.execution.ui_validation import _source_continuity_lab_semantic_errors
from specify_cli.design_intelligence.ui_migration import (
    migration_component_binding_errors,
    migration_observation_errors,
)


FIXTURES = Path(__file__).parent / "fixtures" / "source-continuity-lab"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_migration_contract_accepts_exact_state_asset_and_native_requirements() -> None:
    result = validate_ui_source_continuity(
        _fixture("migration-contract.json"), require_ready=True
    )
    assert result.valid, [error.message for error in result.errors]


def test_native_observation_does_not_require_an_unpromised_state_change(
    tmp_path: Path,
) -> None:
    contract = _fixture("migration-contract.json")
    contract["action_bindings"][0]["native_operation"]["effect_requirement"] = (
        "observation"
    )
    contract["action_bindings"][0]["side_effects"] = []
    contract["action_bindings"][0]["native_operation"]["expected_effect"] = (
        "Read the current native window position."
    )
    report = _fixture("migration-observation.json")
    native = report["action_results"][0]["native_operation"]
    native["after"] = copy.deepcopy(native["before"])
    report["action_results"][0]["observed_side_effects"] = []
    assert validate_ui_source_continuity(contract, require_ready=True).valid
    errors = _source_continuity_lab_semantic_errors(
        tmp_path, report, contract, None, "a" * 64
    )
    assert not any(
        error.startswith("native-operation-effect-mismatch") for error in errors
    ), errors


@pytest.mark.parametrize("shrink_source_inventory", [False, True])
def test_asset_state_denominator_cannot_shrink_with_its_result(
    shrink_source_inventory: bool,
) -> None:
    contract = _fixture("migration-contract.json")
    report = _fixture("migration-observation.json")
    variants = contract["asset_bindings"][0]["state_variants"]
    variants["required_states"].remove("disabled")
    variants["variants"].pop()
    if shrink_source_inventory:
        contract["asset_bindings"][0]["source_refs"].pop()
    report["asset_results"][0]["state_variants"].pop()
    assert not validate_ui_source_continuity(contract, require_ready=True).valid
    components = [
        {
            "id": "DH-COMP-001",
            "anatomy": ["indicator", "label"],
            "required_states": ["normal", "hover", "pressed", "disabled"],
        }
    ]
    assert migration_component_binding_errors(contract, components)
    assert migration_observation_errors(contract, report)


def test_native_state_change_cannot_be_downgraded_to_observation() -> None:
    contract = _fixture("migration-contract.json")
    contract["action_bindings"][0]["native_operation"]["effect_requirement"] = (
        "observation"
    )
    assert not validate_ui_source_continuity(contract, require_ready=True).valid
    assert any(
        error.startswith("native-operation-mode-mismatch")
        for error in migration_observation_errors(
            contract, _fixture("migration-observation.json")
        )
    )


@pytest.mark.parametrize(
    "after",
    [
        {"x": 100.0, "y": 100.0},
        {"x": 100, "y": 100, "timestamp": 2},
        {"x": 110},
    ],
)
def test_native_effect_compares_declared_fields_with_numeric_semantics(
    after: dict,
) -> None:
    contract = _fixture("migration-contract.json")
    contract["action_bindings"][0]["native_operation"]["effect_fields"] = ["x", "y"]
    report = _fixture("migration-observation.json")
    native = report["action_results"][0]["native_operation"]
    native["before"] = {"x": 100, "y": 100}
    if "timestamp" in after:
        native["before"]["timestamp"] = 1
    native["after"] = after
    assert any(
        error.startswith("native-operation-effect-mismatch")
        for error in migration_observation_errors(contract, report)
    )


def test_migration_schema_definitions_match_design_and_quick() -> None:
    root = Path(__file__).parents[1]
    canonical = json.loads(
        (
            root
            / "templates/design-intelligence/schema/ui-source-continuity.schema.json"
        ).read_text(encoding="utf-8")
    )
    handoff = json.loads(
        (root / "templates/design-handoff-schema.json").read_text(encoding="utf-8")
    )
    quick = json.loads(
        (root / "templates/quick-confirmation-schema.json").read_text(encoding="utf-8")
    )
    for name, definition in canonical["$defs"].items():
        if name.startswith("migration"):
            assert handoff["$defs"][name] == definition
            assert quick["$defs"][name] == definition
    contract = _fixture("migration-contract.json")
    for schema in (
        {"$defs": handoff["$defs"], "$ref": "#/$defs/sourceContinuity"},
        {
            "$defs": quick["$defs"],
            **quick["properties"]["decision"]["properties"]["ui_confirmation"][
                "properties"
            ]["source_continuity"],
        },
    ):
        Draft202012Validator(schema).validate(contract)


@pytest.mark.parametrize(
    "damage",
    ["missing-state", "missing-label", "wrong-size", "character", "missing-permission"],
)
def test_migration_contract_rejects_incomplete_or_contradictory_requirements(
    damage: str,
) -> None:
    contract = _fixture("migration-contract.json")
    if damage == "missing-state":
        contract["asset_bindings"][0]["state_variants"]["variants"].pop()
    elif damage == "missing-label":
        contract["surface_bindings"][0]["component_states"][0]["states"][-1][
            "visuals"
        ].pop()
    elif damage == "wrong-size":
        contract["asset_bindings"][0]["state_variants"]["variants"][-1][
            "target_size"
        ] = [24, 24]
    elif damage == "character":
        contract["asset_bindings"][0]["state_variants"]["variants"][-1][
            "target_ref"
        ] = "text:↻"
    else:
        contract["action_bindings"][0]["native_operation"]["permission_refs"] = []
    result = validate_ui_source_continuity(contract, require_ready=True)
    assert not result.valid


@pytest.mark.parametrize(
    ("damage", "expected"),
    [
        ("active-disabled-label", "component-state-visual-mismatch"),
        ("enabled-disabled-control", "component-state-behavior-mismatch"),
        ("missing-state", "asset-state-coverage-mismatch"),
        ("wrong-size", "asset-state-size-mismatch"),
        ("character", "asset-state-character-substitution"),
        ("missing-permission", "native-operation-permission-mismatch"),
        ("stationary-window", "native-operation-effect-mismatch"),
        ("screenshot-only-native", "native-operation-evidence-kind-mismatch"),
        ("malformed-state", "component-state-coverage-mismatch"),
        ("malformed-visual-list", "component-state-visual-coverage-mismatch"),
        ("boolean-size", "asset-state-size-mismatch"),
    ],
)
def test_migration_review_rejects_false_positive_ui_evidence(
    tmp_path: Path, damage: str, expected: str
) -> None:
    contract = _fixture("migration-contract.json")
    report = _fixture("migration-observation.json")
    disabled = report["surface_results"][0]["component_states"][-1]
    asset = report["asset_results"][0]
    native = report["action_results"][0]["native_operation"]
    if damage == "active-disabled-label":
        disabled["visuals"][-1]["matches"] = False
        disabled["visuals"][-1]["observation"] = (
            "The disabled label still uses the enabled treatment."
        )
    elif damage == "enabled-disabled-control":
        disabled["behavior_matches"] = False
    elif damage == "missing-state":
        asset["state_variants"].pop()
    elif damage == "wrong-size":
        asset["state_variants"][-1]["target_size"] = [24, 24]
    elif damage == "character":
        asset["state_variants"][-1]["character_substitution"] = True
    elif damage == "missing-permission":
        native["verified_permission_refs"] = []
    elif damage == "stationary-window":
        native["after"] = copy.deepcopy(native["before"])
    elif damage == "screenshot-only-native":
        native["effect_evidence_ref"] = "evidence://target/visual_capture"
    elif damage == "malformed-state":
        disabled["state"] = {"name": "disabled"}
    elif damage == "malformed-visual-list":
        disabled["visuals"].append("not an observation")
    else:
        asset["state_variants"][-1]["target_size"] = [True, 26]
    errors = _source_continuity_lab_semantic_errors(
        tmp_path, report, contract, None, "a" * 64
    )
    assert any(error.startswith(expected) for error in errors), errors
