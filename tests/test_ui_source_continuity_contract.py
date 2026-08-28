"""Reference-grounded UI source continuity contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import specify_cli.design_intelligence as design_intelligence


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = (
    ROOT
    / "templates"
    / "design-intelligence"
    / "schema"
    / "ui-source-continuity.schema.json"
)


def _valid_contract() -> dict[str, object]:
    return {
        "schema": "spec-kit-ui-source-continuity-v1",
        "applicability": "required",
        "mode": "mixed",
        "reason": "Existing visual, runtime, and implementation sources govern the reconstruction.",
        "coverage": {
            "surface_ids": ["DH-SURFACE-DESKTOP-001"],
            "interaction_ids": ["DH-INT-DESKTOP-001"],
            "component_ids": ["DH-COMP-DESKTOP-001"],
        },
        "authority_refs": [
            "evidence/main-window.png",
            "src/legacy/main_window.cpp",
            "runtime://legacy/main-window",
        ],
        "surface_bindings": [
            {
                "id": "SC-SURFACE-001",
                "surface_id": "DH-SURFACE-DESKTOP-001",
                "source_refs": ["src/legacy/main_window.cpp"],
                "discovery": "measured",
                "disposition": "adapt",
                "rationale": "Preserve the primary workspace while adapting platform chrome.",
            }
        ],
        "action_bindings": [
            {
                "id": "SC-ACTION-001",
                "interaction_id": "DH-INT-DESKTOP-001",
                "source_refs": ["src/legacy/main_window.cpp#exportAction"],
                "user_promise": "Export the current document.",
                "business_outcome": "A user-selected file contains the current document.",
                "side_effects": ["write one file", "update recent export location"],
                "final_state": "The workspace remains usable and reports the exported path.",
                "verification": "Run the source and target click path with the same document.",
            }
        ],
        "asset_bindings": [
            {
                "id": "SC-ASSET-001",
                "component_id": "DH-COMP-DESKTOP-001",
                "semantic_role": "export action",
                "source_refs": ["assets/export.svg"],
                "target_strategy": "preserve",
                "target_ref": "src/assets/export.svg",
                "provenance": "project-owned",
                "fallback": "Visible Export label plus accessible name.",
                "placeholder_policy": "forbid-character-substitution",
            }
        ],
        "unresolved_gaps": [],
    }


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_ui_source_continuity_schema_and_validator_accept_complete_contract() -> None:
    assert SCHEMA.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "spec-kit-ui-source-continuity-v1"

    validate = getattr(
        design_intelligence,
        "validate_ui_source_continuity",
        None,
    )
    assert callable(validate)
    result = validate(_valid_contract(), require_ready=True)
    assert result.valid is True


def test_ui_source_continuity_rejects_missing_business_action_and_open_gaps() -> None:
    validate = getattr(
        design_intelligence,
        "validate_ui_source_continuity",
        None,
    )
    assert callable(validate)

    payload = _valid_contract()
    payload["action_bindings"] = []
    payload["unresolved_gaps"] = ["Secondary dialogs have not been explored."]
    result = validate(payload, require_ready=True)

    assert result.valid is False
    messages = "\n".join(error.message for error in result.errors)
    assert "action" in messages.lower()
    assert "unresolved" in messages.lower()


def test_ui_source_continuity_rejects_character_icon_substitution() -> None:
    validate = getattr(
        design_intelligence,
        "validate_ui_source_continuity",
        None,
    )
    assert callable(validate)

    payload = _valid_contract()
    asset = payload["asset_bindings"][0]
    assert isinstance(asset, dict)
    asset["placeholder_policy"] = "allow-character-substitution"
    asset["target_ref"] = "text:★"
    result = validate(payload, require_ready=True)

    assert result.valid is False
    assert any(
        "character" in error.message.lower() or "placeholder" in error.message.lower()
        for error in result.errors
    )


def test_ui_source_continuity_ready_requires_bidirectional_coverage() -> None:
    validate = getattr(
        design_intelligence,
        "validate_ui_source_continuity",
        None,
    )
    assert callable(validate)

    payload = _valid_contract()
    coverage = payload["coverage"]
    assert isinstance(coverage, dict)
    coverage["interaction_ids"] = [
        "DH-INT-DESKTOP-001",
        "DH-INT-DESKTOP-UNBOUND",
    ]
    result = validate(payload, require_ready=True)

    assert result.valid is False
    assert any(
        "coverage" in error.message.lower()
        and "interaction" in error.message.lower()
        for error in result.errors
    )


def test_ui_source_continuity_draft_and_not_applicable_lifecycle() -> None:
    validate = design_intelligence.validate_ui_source_continuity
    draft = _valid_contract()
    draft.update(
        {
            "applicability": "not-assessed",
            "mode": "none",
            "reason": None,
            "coverage": {
                "surface_ids": [],
                "interaction_ids": [],
                "component_ids": [],
            },
            "authority_refs": [],
            "surface_bindings": [],
            "action_bindings": [],
            "asset_bindings": [],
            "unresolved_gaps": [],
        }
    )
    draft_result = validate(draft)
    assert draft_result.ok is True
    assert validate(draft, require_ready=True).valid is False

    not_applicable = dict(draft)
    not_applicable.update(
        {
            "applicability": "not-applicable",
            "reason": "No prior UI or reference governs this greenfield scope.",
        }
    )
    assert validate(not_applicable, require_ready=True).valid is True

    not_applicable["mode"] = "mixed"
    not_applicable["reason"] = ""
    not_applicable["authority_refs"] = ["unexpected-source"]
    coverage = not_applicable["coverage"]
    assert isinstance(coverage, dict)
    coverage["surface_ids"] = ["unexpected-surface"]
    invalid = validate(not_applicable, require_ready=True)
    assert invalid.valid is False
    assert any("not-applicable" in error.message for error in invalid.errors)


def test_ui_source_continuity_rejects_duplicate_binding_ids_and_wrong_draft_mode() -> None:
    validate = design_intelligence.validate_ui_source_continuity
    payload = _valid_contract()
    action = payload["action_bindings"][0]
    surface = payload["surface_bindings"][0]
    assert isinstance(action, dict) and isinstance(surface, dict)
    action["id"] = surface["id"]
    duplicate = validate(payload, require_ready=True)
    assert any("duplicates" in error.message for error in duplicate.errors)

    payload = _valid_contract()
    payload["mode"] = "none"
    wrong_mode = validate(payload)
    assert any("source-backed mode" in error.message for error in wrong_mode.errors)


def test_ui_source_continuity_approved_text_symbol_requires_exact_exception_pair() -> None:
    validate = design_intelligence.validate_ui_source_continuity
    payload = _valid_contract()
    asset = payload["asset_bindings"][0]
    assert isinstance(asset, dict)
    asset.update(
        {
            "target_strategy": "approved-exception",
            "placeholder_policy": "approved-text-symbol",
            "target_ref": "text:→",
        }
    )
    assert validate(payload, require_ready=True).valid is True

    asset["target_strategy"] = "preserve"
    invalid_strategy = validate(payload, require_ready=True)
    assert any("approved-exception" in error.message for error in invalid_strategy.errors)

    asset["target_strategy"] = "approved-exception"
    asset["placeholder_policy"] = "forbid-character-substitution"
    invalid_policy = validate(payload, require_ready=True)
    assert any("approved-text-symbol" in error.message for error in invalid_policy.errors)

    asset["placeholder_policy"] = "approved-text-symbol"
    asset["target_ref"] = "src/assets/export.svg"
    invalid_target = validate(payload, require_ready=True)
    assert any("intentional character" in error.message for error in invalid_target.errors)


@pytest.mark.parametrize(
    "target_ref",
    ["unknown", "__ICON_TODO__", "emoji:★", "&#9733;", "U+2605", "★"],
)
def test_ui_source_continuity_rejects_placeholder_and_character_target_refs(
    target_ref: str,
) -> None:
    payload = _valid_contract()
    asset = payload["asset_bindings"][0]
    assert isinstance(asset, dict)
    asset["target_ref"] = target_ref
    result = design_intelligence.validate_ui_source_continuity(
        payload,
        require_ready=True,
    )
    assert result.valid is False
    assert any(
        "placeholder" in error.message.lower()
        or "character" in error.message.lower()
        for error in result.errors
    )


def test_ui_source_continuity_rejects_non_object_payload() -> None:
    result = design_intelligence.validate_ui_source_continuity([], require_ready=True)
    assert result.valid is False
    assert result.errors[0].path == "$"


def test_professional_router_selects_source_grounded_reconstruction_specialist() -> None:
    module_globals: dict[str, object] = {}
    exec(
        compile(
            _read("templates/ui-professional-skills/route.py"),
            "route.py",
            "exec",
        ),
        module_globals,
    )
    route = module_globals["route"]
    catalog = json.loads(_read("templates/ui-professional-skills/catalog.json"))

    payload = route(
        catalog,
        "根据截图、现有 HTML、可运行旧软件和源码重建桌面软件，"
        "必须挖掘按钮业务结果、深层界面和图标资源",
        style_authority="inherit-existing",
    )

    assert "specialist-source-grounded-reconstruction" in payload["selection"][
        "specialist_skill_ids"
    ]
    assert (
        "ui-professional-skills/specialists/source-grounded-reconstruction.md"
        in payload["load_refs"]
    )


def test_design_quick_worker_and_review_share_source_continuity_contract() -> None:
    surfaces = (
        "templates/command-partials/design/shell.md",
        "templates/advanced-skills/spx-design/SKILL.md",
        "templates/advanced-skills/_shared/ui-quality-gate.md",
        "templates/command-references/quick/packetized-work.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
        "templates/worker-prompts/quick-worker.md",
        "templates/command-references/review/system-scenario-contract.md",
    )
    for relative in surfaces:
        content = _read(relative).lower()
        for marker in (
            "source_continuity",
            "business_outcome",
            "asset_bindings",
            "unresolved_gaps",
            "forbid-character-substitution",
        ):
            assert marker in content, (relative, marker)


def test_design_and_quick_artifacts_persist_source_continuity() -> None:
    surfaces = (
        "templates/design-brief-template.md",
        "templates/design-change-template.md",
        "templates/advanced-skills/spx-design/assets/design-change.md",
        "templates/ui-brief-template.md",
        "templates/plan-contract-template.json",
        "templates/artifacts/quick-status.md",
        "templates/quick-confirmation-schema.json",
    )
    for relative in surfaces:
        content = _read(relative)
        assert "source_continuity" in content, relative


def test_spx_task_asset_uses_object_shaped_source_continuity_bindings() -> None:
    payload = json.loads(
        _read("templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json")
    )
    continuity = payload["ui_contract"]["source_continuity"]

    assert set(continuity["coverage"]) == {
        "surface_ids",
        "interaction_ids",
        "component_ids",
    }
    for field in ("surface_bindings", "action_bindings", "asset_bindings"):
        assert continuity[field]
        assert isinstance(continuity[field][0], dict), field


def test_source_continuity_lab_is_executable_across_formal_quick_and_review() -> None:
    surfaces = (
        "templates/command-references/implement/ui-design-intelligence.md",
        "templates/command-references/quick/packetized-work.md",
        "templates/command-references/review/system-scenario-contract.md",
        "templates/advanced-skills/spx-implement/SKILL.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
        "templates/advanced-skills/spx-review/SKILL.md",
        "templates/advanced-skills/_shared/ui-quality-gate.md",
        "templates/worker-prompts/implementer.md",
        "templates/worker-prompts/quick-worker.md",
    )
    for relative in surfaces:
        content = _read(relative)
        assert "source-continuity-manifest" in content, relative
        assert "source-continuity-adapter-catalog" in content, relative
        assert "source-continuity-adapter-bridge" in content, relative
        assert "source-continuity-adapter-probe" in content, relative
        assert "source-continuity-adapter-plan" in content, relative
        assert "source-continuity-adapter-execution" in content, relative
        assert "source-continuity-validate" in content, relative
        assert "source_continuity_lab_report_ref" in content, relative
        assert "source_continuity_adapter_plan_ref" in content, relative


def test_user_invoked_design_surfaces_own_source_continuity_without_passive_gate() -> None:
    assert not (
        ROOT / "templates" / "passive-skills" / "spec-kit-ui-design"
    ).exists()

    for relative in (
        "templates/ui-professional-skills/specialists/source-grounded-reconstruction.md",
        "templates/advanced-skills/_shared/ui-quality-gate.md",
    ):
        content = _read(relative)
        assert "source-continuity-adapter-catalog" in content, relative
        assert "source-continuity-adapter-bridge" in content, relative
        assert "source-continuity-adapter-probe" in content, relative
        assert "source-continuity-adapter-plan" in content, relative
        assert "source-continuity-adapter-execution" in content, relative
        assert "technology-neutral" in content, relative


def test_source_continuity_lifecycle_and_registry_fields_remain_bound() -> None:
    lifecycle = json.loads(_read("templates/task-lifecycle-template.json"))
    verification = lifecycle["ui_verification"]
    for field in (
        "source_continuity_lab_report_ref",
        "source_continuity_lab_report_sha256",
        "source_continuity_adapter_plan_ref",
        "source_continuity_adapter_plan_sha256",
        "source_continuity_adapter_execution_ref",
        "source_continuity_adapter_execution_sha256",
        "covered_source_continuity_surface_ids",
        "covered_source_continuity_interaction_ids",
        "covered_source_continuity_component_ids",
    ):
        assert field in verification

    registry = json.loads(_read("templates/workflow-artifact-registry.json"))
    lab = next(
        item for item in registry["artifacts"] if item["id"] == "source_continuity_lab"
    )
    assert "specify-runtime evidence source-continuity-manifest" in lab["owner_cli"]
    assert "specify-runtime evidence source-continuity-adapter-probe" in lab["owner_cli"]
    assert "specify-runtime evidence source-continuity-adapter-plan" in lab["owner_cli"]
    assert "specify-runtime evidence source-continuity-adapter-execution" in lab["owner_cli"]
    assert "specify-runtime evidence source-continuity-validate" in lab["owner_cli"]
