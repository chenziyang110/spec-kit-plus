from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PROFESSIONAL_FIELDS = {
    "surface_catalog",
    "scenario_matrix",
    "interaction_matrix",
    "editing_matrix",
    "data_state_matrix",
    "accessibility_matrix",
    "navigation_matrix",
    "content_matrix",
    "motion_contract",
    "usability_validation",
}

EDITING_CONTRACT_FIELDS = {
    "id",
    "surface",
    "input_methods",
    "composition_behavior",
    "paste_autofill_behavior",
    "selection_caret_behavior",
    "formatting_behavior",
    "validation_timing",
    "validation_feedback",
    "dirty_state_behavior",
    "persistence_behavior",
    "undo_redo_behavior",
    "conflict_behavior",
    "read_only_disabled_behavior",
    "submission_behavior",
    "decision_ids",
}

INTERACTION_CONTRACT_FIELDS = {
    "id",
    "surface",
    "input",
    "trigger",
    "event_sequence",
    "immediate_feedback",
    "focus_behavior",
    "repeat_behavior",
    "cancellation_behavior",
    "pending_behavior",
    "decision_ids",
}

COMPONENT_GOVERNANCE_FIELDS = {
    "variants",
    "content_constraints",
    "semantic_token_refs",
    "governance",
    "iconography",
}


def _json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _text(relative: str) -> str:
    return " ".join((ROOT / relative).read_text(encoding="utf-8").split())


def test_professional_ui_rows_are_frozen_in_preview_and_immutable_handoff() -> None:
    preview_schema = _json("templates/design-preview-manifest.schema.json")
    handoff_schema = _json("templates/design-handoff-schema.json")
    source_manifest = _json("src/specify_cli/design_preview_source/manifest.json")

    assert PROFESSIONAL_FIELDS <= set(
        preview_schema["$defs"]["handoff"]["required"]
    )
    assert PROFESSIONAL_FIELDS <= set(
        handoff_schema["properties"]["reproduction"]["required"]
    )
    assert PROFESSIONAL_FIELDS <= set(source_manifest["handoff"])


def test_surface_scenario_graph_is_bounded_referential_and_complete(
    tmp_path: Path,
) -> None:
    from specify_cli import design as design_module

    manifest_path = tmp_path / "round-20.manifest.json"
    design_module.scaffold_design_preview_manifest(
        manifest_path,
        profile_ids=["web", "mobile"],
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    handoff = manifest["handoff"]
    surfaces = handoff["surface_catalog"]
    scenarios = handoff["scenario_matrix"]

    surface_ids = {row["id"] for row in surfaces}
    assert len(surface_ids) == 2
    assert all(row["source_refs"] for row in surfaces)
    assert all(row["specimen_ids"] for row in surfaces)
    assert all(row["component_ids"] for row in surfaces)

    reference_fields = {
        "interaction_ids": "interaction_matrix",
        "editing_ids": "editing_matrix",
        "data_state_ids": "data_state_matrix",
        "accessibility_ids": "accessibility_matrix",
        "navigation_ids": "navigation_matrix",
        "content_ids": "content_matrix",
        "responsive_ids": "responsive_matrix",
        "motion_transition_ids": "motion_contract",
    }
    known_refs = {
        field: {
            row["id"]
            for row in (
                handoff[field]["transitions"]
                if field == "motion_contract"
                else handoff[field]
            )
        }
        for field in reference_fields.values()
    }
    covered = {field: set() for field in reference_fields}
    for scenario in scenarios:
        assert scenario["surface_id"] in surface_ids
        assert scenario["risk"] in {"low", "medium", "high"}
        assert scenario["required"] is True
        script = scenario["interaction_script"]
        assert script["preconditions"]
        assert all(
            not precondition.endswith("..")
            for precondition in script["preconditions"]
        )
        assert script["start_state_id"] in scenario["data_state_ids"]
        assert script["steps"]
        assert all(
            step["input"] and step["action"] and step["expected_feedback"]
            for step in script["steps"]
        )
        assert all(
            script[field]
            for field in (
                "focus_checkpoint",
                "announcement_checkpoint",
                "completion_checkpoint",
                "recovery_checkpoint",
            )
        )
        branch_conditions: set[str] = set()
        assert script["branches"]
        for branch in script["branches"]:
            assert branch["conditions"]
            assert not branch_conditions.intersection(branch["conditions"])
            branch_conditions.update(branch["conditions"])
            assert branch["expected_state_id"] in scenario["data_state_ids"]
            assert all(
                branch[field]
                for field in (
                    "setup",
                    "expected_feedback",
                    "focus_behavior",
                    "announcement",
                    "continuation",
                )
            )
        assert branch_conditions == {
            "success",
            "failure",
            "timeout",
            "cancel",
            "retry",
            "duplicate",
            "out_of_order",
        }
        referenced_decisions: set[str] = set()
        for ref_field, source_field in reference_fields.items():
            refs = set(scenario[ref_field])
            assert refs
            assert refs <= known_refs[source_field]
            covered[ref_field].update(refs)
            source_rows = (
                handoff[source_field]["transitions"]
                if source_field == "motion_contract"
                else handoff[source_field]
            )
            referenced_decisions.update(
                decision_id
                for row in source_rows
                if row["id"] in refs
                for decision_id in row["decision_ids"]
            )
        assert set(scenario["decision_ids"]) == referenced_decisions

    for ref_field, source_field in reference_fields.items():
        assert covered[ref_field] == known_refs[source_field]
    assert len(scenarios) <= sum(len(values) for values in known_refs.values())
    assert {row["id"] for row in surfaces + scenarios} <= set(
        design_module._design_handoff_contract_ids(manifest)
    )


def test_professional_ui_contract_survives_every_consumer_shape() -> None:
    consumers = (
        ("templates/spec-contract-template.json", "design_contract"),
        ("templates/plan-contract-template.json", "ui_design_contract"),
        ("templates/task-packet-template.json", "ui_contract"),
        (
            "templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json",
            "ui_contract",
        ),
    )
    for relative, key in consumers:
        assert PROFESSIONAL_FIELDS <= set(_json(relative)[key]), relative

    advanced_scenario = _json(
        "templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json"
    )["ui_contract"]["scenario_matrix"][0]
    assert advanced_scenario["interaction_script"]["start_state_id"]
    assert advanced_scenario["interaction_script"]["branches"]
    advanced_interaction = _json(
        "templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json"
    )["ui_contract"]["interaction_matrix"][0]
    assert set(advanced_interaction) == INTERACTION_CONTRACT_FIELDS

    preview_schema = _json("templates/design-preview-manifest.schema.json")
    handoff_schema = _json("templates/design-handoff-schema.json")
    for schema in (preview_schema, handoff_schema):
        required = set(schema["$defs"]["componentContract"]["required"])
        assert COMPONENT_GOVERNANCE_FIELDS <= required
        assert "surfaceContract" in schema["$defs"]
        assert "scenarioContract" in schema["$defs"]
        scenario_required = set(schema["$defs"]["scenarioContract"]["required"])
        assert "interaction_script" in scenario_required
        assert {
            "preconditions",
            "start_state_id",
            "steps",
            "branches",
            "focus_checkpoint",
            "announcement_checkpoint",
            "completion_checkpoint",
            "recovery_checkpoint",
        } <= set(schema["$defs"]["interactionScript"]["required"])
        assert {
            "conditions",
            "setup",
            "expected_state_id",
            "expected_feedback",
            "focus_behavior",
            "announcement",
            "continuation",
        } <= set(schema["$defs"]["interactionBranch"]["required"])
        editing = schema["$defs"]["editingContract"]
        assert editing["additionalProperties"] is False
        assert EDITING_CONTRACT_FIELDS == set(editing["required"])
        interaction = schema["$defs"]["interactionContract"]
        assert interaction["additionalProperties"] is False
        assert INTERACTION_CONTRACT_FIELDS == set(interaction["required"])


def test_style_authority_survives_every_ui_consumer_shape() -> None:
    style_fields = {
        "mode",
        "scope_level",
        "source_refs",
        "protected_surfaces",
        "allowed_style_delta_surfaces",
        "authorization_source",
    }
    consumers = (
        ("templates/spec-contract-template.json", "design_contract"),
        ("templates/plan-contract-template.json", "ui_design_contract"),
        ("templates/task-packet-template.json", "ui_contract"),
        (
            "templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json",
            "ui_contract",
        ),
    )

    for relative, key in consumers:
        authority = _json(relative)[key]["style_authority"]
        assert set(authority) == style_fields, relative

    for relative in (
        "templates/design-change-template.md",
        "templates/advanced-skills/spx-design/assets/design-change.md",
    ):
        content = _text(relative).lower()
        assert "style_authority:" in content
        assert "page-overhaul-authorized" in content
        assert "global-shell" in content
        assert "shared-components" in content


def test_accessibility_contract_is_specific_enough_for_wcag_and_native_equivalents() -> None:
    schema = _json("templates/design-preview-manifest.schema.json")
    required = set(schema["$defs"]["accessibilityContract"]["required"])
    assert {
        "id",
        "surface",
        "semantics",
        "reading_order",
        "focus_order",
        "keyboard",
        "announcements",
        "target_size",
        "contrast",
        "zoom_reflow",
        "alternatives",
        "decision_ids",
    } <= required


def test_interaction_contract_covers_the_complete_event_lifecycle() -> None:
    profiles = _json("templates/design-capability-profiles.json")["profiles"]
    source_fields = INTERACTION_CONTRACT_FIELDS - {"decision_ids"}
    active_profiles = [profile for profile in profiles if profile["preview_required"]]

    assert active_profiles
    for profile in active_profiles:
        rows = profile["interaction_matrix"]
        assert rows, profile["id"]
        for row in rows:
            assert set(row) == source_fields
            assert all(str(row[field]).strip() for field in source_fields)

    combined = " ".join(
        json.dumps(row, ensure_ascii=False).lower()
        for profile in active_profiles
        for row in profile["interaction_matrix"]
    )
    for marker in (
        "pointerdown",
        "pointercancel",
        "keydown",
        "immediate",
        "focus",
        "repeat",
        "cancel",
        "pending",
    ):
        assert marker in combined

    source_rows = _json("src/specify_cli/design_preview_source/manifest.json")[
        "handoff"
    ]["interaction_matrix"]
    assert source_rows
    for row in source_rows:
        assert set(row) == INTERACTION_CONTRACT_FIELDS
        assert all(
            str(row[field]).strip()
            for field in INTERACTION_CONTRACT_FIELDS - {"decision_ids"}
        )


def test_editing_contract_covers_the_complete_input_lifecycle() -> None:
    profiles = _json("templates/design-capability-profiles.json")["profiles"]
    source_fields = EDITING_CONTRACT_FIELDS - {"decision_ids"}
    active_profiles = [profile for profile in profiles if profile["preview_required"]]

    assert active_profiles
    for profile in active_profiles:
        rows = profile["editing_matrix"]
        assert rows, profile["id"]
        for row in rows:
            assert set(row) == source_fields
            assert row["input_methods"]
            assert all(
                str(row[field]).strip()
                for field in source_fields - {"id", "input_methods"}
            )

    combined = " ".join(
        json.dumps(row, ensure_ascii=False).lower()
        for profile in active_profiles
        for row in profile["editing_matrix"]
    )
    for marker in (
        "ime",
        "composition",
        "paste",
        "autofill",
        "caret",
        "validation",
        "dirty",
        "autosave",
        "undo",
        "conflict",
        "read-only",
        "disabled",
        "duplicate",
    ):
        assert marker in combined


def test_design_guidance_covers_professional_ui_lenses_without_duplicates() -> None:
    classic = _text("templates/design-change-template.md")
    advanced = _text(
        "templates/advanced-skills/spx-design/assets/design-change.md"
    )
    combined = " ".join(
        (
            classic,
            advanced,
            _text("templates/command-partials/design-intelligence/shared-foundation.md"),
            _text("templates/advanced-skills/_shared/ui-quality-gate.md"),
        )
    )

    for marker in (
        "accessibility_matrix",
        "editing_matrix",
        "navigation_matrix",
        "content_matrix",
        "motion_contract",
        "usability_validation",
        "WCAG 2.2 AA",
        "Name/Role/Value",
        "24x24",
        "44pt",
        "400%",
        "deep link",
        "right-to-left",
        "target-user",
        "composition",
        "autofill",
        "undo/redo",
        "dirty state",
        "edit conflict",
        "event_sequence",
        "immediate_feedback",
        "focus_behavior",
        "repeat_behavior",
        "cancellation_behavior",
        "pending_behavior",
    ):
        assert marker in combined

    assert classic.count("Add explicit rows for rapid/repeated activation") == 1
    assert classic.count("Stress long/localized content") == 1
