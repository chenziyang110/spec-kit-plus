from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PROFESSIONAL_UI_FIELDS = {
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


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _ui_contract_fields(relative: str, key: str) -> set[str]:
    payload = json.loads(_read(relative))
    contract = payload[key]
    assert isinstance(contract, dict)
    return set(contract)


def _read_generated_skill(skill_path: Path) -> str:
    parts = [skill_path.read_text(encoding="utf-8")]
    references = skill_path.parent / "references"
    if references.is_dir():
        parts.extend(
            path.read_text(encoding="utf-8")
            for path in sorted(references.glob("**/*.md"))
        )
    return "\n\n".join(parts)


def _joined(*relative_paths: str) -> str:
    return "\n".join(_read(path) for path in relative_paths)


def test_ui_contract_carries_interaction_and_data_scenarios_to_worker_packets() -> None:
    expected = {
        "surface_catalog",
        "scenario_matrix",
        "interaction_matrix",
        "editing_matrix",
        "data_state_matrix",
    }

    assert expected <= _ui_contract_fields(
        "templates/spec-contract-template.json", "design_contract"
    )
    assert expected <= _ui_contract_fields(
        "templates/plan-contract-template.json", "ui_design_contract"
    )
    assert expected <= _ui_contract_fields(
        "templates/task-packet-template.json", "ui_contract"
    )

    advanced_entry = json.loads(
        _read("templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json")
    )
    assert expected <= set(advanced_entry["ui_contract"])


def test_design_handoff_models_input_data_and_continuous_resize_behavior() -> None:
    schema = json.loads(_read("templates/design-handoff-schema.json"))
    component = schema["$defs"]["componentContract"]
    responsive = schema["$defs"]["responsiveContract"]

    assert {"interaction_modes", "data_scenarios"} <= set(component["required"])
    assert {"stretch_behavior", "overflow_behavior"} <= set(
        responsive["required"]
    )

    for relative in (
        "templates/design-change-template.md",
        "templates/advanced-skills/spx-design/assets/design-change.md",
    ):
        content = " ".join(_read(relative).split())
        for marker in (
            "interaction_matrix",
            "editing_matrix",
            "data_state_matrix",
            "mouse",
            "keyboard",
            "empty",
            "populated",
            "stretch",
            "overflow",
            "duplicate submission",
            "async completion order",
            "session expiry",
            "text zoom",
            "event_sequence",
            "immediate_feedback",
            "focus_behavior",
            "repeat_behavior",
            "cancellation_behavior",
            "pending_behavior",
        ):
            assert marker in content, f"{relative} must preserve {marker}"


def test_classic_and_advanced_ui_workflows_use_one_scenario_vocabulary() -> None:
    classic = "\n".join(
        _read(relative)
        for relative in (
            "templates/command-partials/design-intelligence/shared-foundation.md",
            "templates/command-partials/design-intelligence/stage-hooks.md",
            "templates/command-partials/design/shell.md",
            "templates/command-partials/specify/shell.md",
            "templates/command-partials/plan/shell.md",
            "templates/command-partials/tasks/shell.md",
            "templates/command-partials/implement/shell.md",
            "templates/command-partials/review/shell.md",
            "templates/command-partials/quick/shell.md",
            "templates/command-partials/debug/shell.md",
        )
    )
    advanced = "\n".join(
        _read(relative)
        for relative in (
            "templates/advanced-skills/_shared/ui-quality-gate.md",
            "templates/advanced-skills/spx-design/references/design-contract.md",
            "templates/advanced-skills/spx-specify/references/ui-and-handoffs.md",
            "templates/advanced-skills/spx-plan/references/planning-contract.md",
            "templates/advanced-skills/spx-tasks/references/task-graph-contract.md",
            "templates/advanced-skills/spx-implement/SKILL.md",
            "templates/advanced-skills/spx-review/references/review-contract.md",
            "templates/advanced-skills/spx-quick/references/worker-contract.md",
            "templates/advanced-skills/spx-debug/SKILL.md",
        )
    )

    for content in (classic, advanced):
        for marker in (
            "interaction_matrix",
            "editing_matrix",
            "data_state_matrix",
            "interaction_script",
            "editing_ids",
            "preconditions",
            "start_state_id",
            "branches",
            "expected_state_id",
            "focus_checkpoint",
            "announcement_checkpoint",
            "completion_checkpoint",
            "recovery_checkpoint",
            "pointer",
            "keyboard",
            "partial",
            "permission",
            "offline",
            "stretch_behavior",
            "overflow_behavior",
            "retry",
            "undo",
            "composition_behavior",
            "paste_autofill_behavior",
            "selection_caret_behavior",
            "validation_timing",
            "dirty_state_behavior",
            "undo_redo_behavior",
            "conflict_behavior",
            "read_only_disabled_behavior",
            "submission_behavior",
            "event_sequence",
            "immediate_feedback",
            "focus_behavior",
            "repeat_behavior",
            "cancellation_behavior",
            "pending_behavior",
        ):
            assert marker in content


def test_codex_rendered_profiles_preserve_the_interaction_scenario_contract(
    tmp_path: Path,
) -> None:
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest

    integration = get_integration("codex")
    assert integration is not None

    for profile, prefix in (("classic", "sp-"), ("advanced", "spx-")):
        project = tmp_path / profile
        manifest = IntegrationManifest("codex", project)
        integration.setup(
            project,
            manifest,
            parsed_options={"workflow_profile": profile},
            script_type="sh",
        )
        rendered = "\n".join(
            _read_generated_skill(
                project / ".codex" / "skills" / f"{prefix}{workflow}" / "SKILL.md"
            )
            for workflow in (
                "design",
                "specify",
                "plan",
                "tasks",
                "implement",
                "review",
                "quick",
                "debug",
            )
        )

        for marker in (
            "interaction_matrix",
            "editing_matrix",
            "data_state_matrix",
            "pointer",
            "keyboard",
            "empty",
            "populated",
            "stretch_behavior",
            "overflow_behavior",
            "duplicate submission",
            "async completion order",
            "session expiry",
            "text zoom",
            "event_sequence",
            "immediate_feedback",
            "focus_behavior",
            "repeat_behavior",
            "cancellation_behavior",
            "pending_behavior",
        ):
            assert marker in rendered, f"{profile} rendering lost {marker}"


def test_design_artifacts_define_a_professional_ui_contract() -> None:
    for relative in (
        "templates/design-change-template.md",
        "templates/advanced-skills/spx-design/assets/design-change.md",
        "templates/ui-brief-template.md",
        "templates/design-brief-template.md",
    ):
        content = _read(relative)
        for field in PROFESSIONAL_UI_FIELDS:
            assert field in content, f"{relative} must preserve {field}"

    canonical = " ".join(
        _joined(
            "templates/command-partials/design-intelligence/shared-foundation.md",
            "templates/advanced-skills/_shared/ui-quality-gate.md",
        ).split()
    ).lower()
    for marker in (
        "wcag 2.2 aa",
        "name/role/value",
        "reading order",
        "focus order",
        "keyboard alternative",
        "drag alternative",
        "dynamic status",
        "24×24 css px",
        "44pt",
        "4.5:1",
        "3:1",
        "400%",
        "forced colors",
        "deep link",
        "interruption recovery",
        "destructive action",
        "privacy",
        "rtl",
        "time zone",
        "semantic token",
        "iconography",
        "deprecation",
        "duration",
        "easing",
        "reduced-motion alternative",
        "perceived-performance threshold",
        "target user",
        "critical task",
        "success criteria",
        "human review",
        "automated tests and screenshots",
    ):
        assert marker in canonical, f"professional UI guidance lost {marker}"


def test_professional_ui_contract_survives_every_classic_and_advanced_stage() -> None:
    classic_stages = {
        "design": (
            "templates/command-partials/design/shell.md",
            "templates/command-partials/design-intelligence/shared-foundation.md",
        ),
        "specify": ("templates/command-partials/specify/shell.md",),
        "plan": (
            "templates/command-partials/plan/shell.md",
            "templates/command-references/plan/plan-contract-fields.md",
        ),
        "tasks": (
            "templates/commands/tasks.md",
            "templates/command-references/tasks/must-preserve-ledger.md",
        ),
        "test-design": (
            "templates/command-references/test-design/test-design-contract.md",
        ),
        "implement": (
            "templates/commands/implement.md",
            "templates/command-references/implement/join-point-review.md",
        ),
        "review": (
            "templates/command-partials/review/shell.md",
            "templates/command-references/review/repair-and-revalidation.md",
        ),
        "accept": ("templates/command-partials/accept/shell.md",),
        "quick": ("templates/command-partials/quick/shell.md",),
        "debug": ("templates/command-partials/debug/shell.md",),
        "analyze": ("templates/command-partials/analyze/shell.md",),
        "checklist": ("templates/command-partials/checklist/shell.md",),
    }
    advanced_stages = {
        "design": (
            "templates/advanced-skills/spx-design/references/design-contract.md",
            "templates/advanced-skills/spx-design/assets/design-change.md",
        ),
        "specify": (
            "templates/advanced-skills/spx-specify/references/ui-and-handoffs.md",
        ),
        "plan": (
            "templates/advanced-skills/spx-plan/references/planning-contract.md",
        ),
        "tasks": (
            "templates/advanced-skills/spx-tasks/references/task-graph-contract.md",
            "templates/advanced-skills/spx-tasks/assets/ui-task.md",
        ),
        "test-design": (
            "templates/advanced-skills/spx-test-design/references/test-design-contract.md",
        ),
        "implement": ("templates/advanced-skills/spx-implement/SKILL.md",),
        "review": (
            "templates/advanced-skills/spx-review/references/review-contract.md",
        ),
        "accept": (
            "templates/advanced-skills/spx-accept/references/acceptance-contract.md",
        ),
        "quick": (
            "templates/advanced-skills/spx-quick/references/worker-contract.md",
        ),
        "debug": ("templates/advanced-skills/spx-debug/SKILL.md",),
        "analyze": (
            "templates/advanced-skills/spx-analyze/references/analysis-gate.md",
        ),
        "checklist": (
            "templates/advanced-skills/spx-checklist/references/checklist-contract.md",
        ),
    }

    for profile, stages in (("classic", classic_stages), ("advanced", advanced_stages)):
        for stage, paths in stages.items():
            content = _joined(*paths)
            for field in PROFESSIONAL_UI_FIELDS:
                assert field in content, f"{profile} {stage} lost {field}"
            assert "risk-based" in content or "risk based" in content, (
                f"{profile} {stage} must retain risk-bounded coverage"
            )
            assert "Cartesian" in content, (
                f"{profile} {stage} must prohibit combinatorial explosion"
            )


def test_design_change_templates_do_not_duplicate_scenario_guidance() -> None:
    for relative in (
        "templates/design-change-template.md",
        "templates/advanced-skills/spx-design/assets/design-change.md",
    ):
        content = _read(relative)
        assert content.count("rapid/repeated activation") == 1
        assert content.count("Stress long/localized content") == 1
