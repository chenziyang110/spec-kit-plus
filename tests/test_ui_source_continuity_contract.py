"""Reference-grounded UI source continuity contract tests."""

from __future__ import annotations

import json
from pathlib import Path

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

