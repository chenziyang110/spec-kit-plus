import json
from pathlib import Path

from .template_utils import (
    assert_debug_checkpoint_card_shape,
    assert_quick_checkpoint_card_shape,
    assert_ui_confirmation_card_shape,
    read_template,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_classic_quick_and_debug_cards_confirm_human_decisions_not_agent_internals() -> None:
    quick = read_template("templates/command-partials/quick/checkpoint-card.md")
    debug_path = PROJECT_ROOT / "templates/command-partials/debug/checkpoint-card.md"

    assert debug_path.is_file()
    debug = read_template("templates/command-partials/debug/checkpoint-card.md")
    assert_quick_checkpoint_card_shape(quick)
    assert_debug_checkpoint_card_shape(debug)

    quick_lower = quick.lower()
    for agent_owned_row in (
        "| affected surfaces |",
        "| implementation plan |",
        "| next action |",
    ):
        assert agent_owned_row not in quick_lower
    assert "technical execution belongs to the agent" in quick_lower
    assert "for awareness, not as a request to approve technical details" in quick_lower

    debug_lower = debug.lower()
    for agent_owned_row in (
        "| candidate focus |",
        "| investigation plan |",
        "| first evidence action |",
        "| fix gate |",
        "| progress signal |",
    ):
        assert agent_owned_row not in debug_lower
    assert "technical hypotheses belong to the agent" in debug_lower
    assert "diagnose only" in debug_lower
    assert "diagnose and fix" in debug_lower
    assert "for awareness, not as a request to approve a hypothesis" in debug_lower


def test_classic_ui_card_is_independent_conditional_and_shares_one_confirmation() -> None:
    ui_path = PROJECT_ROOT / "templates/command-partials/common/ui-confirmation-card.md"

    assert ui_path.is_file()
    ui = read_template("templates/command-partials/common/ui-confirmation-card.md")
    assert_ui_confirmation_card_shape(ui)

    lowered = ui.lower()
    assert "user-visible screen" in lowered
    assert "does not require an external image" in lowered
    assert "quick uses this card for an implementation proposal" in lowered
    assert "debug uses this card for a target baseline" in lowered
    assert "must not pre-approve a speculative fix" in lowered
    assert "design_system.status: bootstrap" in lowered
    assert "do not render an incomplete ui confirmation" in lowered
    assert "inspectable visual artifact" in lowered
    assert "original references" in lowered
    assert "reference intent" in lowered
    assert "real content" in lowered

    for card in (
        read_template("templates/command-partials/quick/checkpoint-card.md"),
        read_template("templates/command-partials/debug/checkpoint-card.md"),
    ):
        card_lower = card.lower()
        main_heading = (
            card_lower.index("## quick checkpoint")
            if "## quick checkpoint" in card_lower
            else card_lower.index("## debug checkpoint")
        )
        assert main_heading < card_lower.index("## ui confirmation")
        assert card_lower.index("## ui confirmation") < card_lower.index(
            "reply with `confirm`/`确认`"
        )
        assert card_lower.count("reply with `confirm`/`确认`") == 1
        assert "revise: ui" in card_lower
        assert "revise: scope" in card_lower


def test_advanced_quick_and_debug_use_the_same_human_confirmation_contract() -> None:
    shared_path = PROJECT_ROOT / "templates/advanced-skills/_shared/human-confirmation.md"

    assert shared_path.is_file()
    shared = shared_path.read_text(encoding="utf-8")
    assert_quick_checkpoint_card_shape(shared)
    assert_debug_checkpoint_card_shape(shared)
    assert_ui_confirmation_card_shape(shared)

    for skill in ("spx-quick", "spx-debug"):
        body = _read(f"templates/advanced-skills/{skill}/SKILL.md").lower()
        assert "references/human-confirmation.md" in body

    surface_map = json.loads(_read("templates/advanced-skills/_shared/surface-map.json"))
    assert "_shared/human-confirmation.md" in surface_map["shared_references"]


def test_confirmation_and_ui_decisions_persist_and_reach_workers() -> None:
    state_sources = (
        "templates/artifacts/quick-status.md",
        "templates/debug.md",
        "templates/advanced-skills/spx-quick/assets/status.md",
        "templates/advanced-skills/spx-debug/assets/debug-session.md",
    )
    required_ui_fields = (
        "ui_confirmation",
        "confirmation_purpose",
        "user_and_primary_job",
        "design_basis_and_source_material",
        "target_experience",
        "structure_and_visible_change",
        "interaction_states_and_adaptation",
        "design_boundaries",
        "acceptance_evidence",
        "confirmation_digest",
    )
    for source in state_sources:
        content = _read(source).lower()
        for field in required_ui_fields:
            assert field in content, (source, field)

    quick_state = _read("templates/artifacts/quick-status.md").lower()
    assert "agent_execution_plan" in quick_state
    debug_state = _read("templates/debug.md").lower()
    assert "agent_investigation_plan" in debug_state

    quick_workers = "\n".join(
        _read(path).lower()
        for path in (
            "templates/worker-prompts/quick-worker.md",
            "templates/advanced-skills/spx-quick/references/worker-contract.md",
        )
    )
    assert "confirmed ui confirmation" in quick_workers
    assert "must not redesign" in quick_workers

    debug_workers = "\n".join(
        _read(path).lower()
        for path in (
            "templates/worker-prompts/debug-investigator.md",
            "templates/advanced-skills/spx-debug/references/investigator-worker.md",
        )
    )
    assert "confirmed ui target baseline" in debug_workers
    assert "must not propose a redesign" in debug_workers


def test_ui_only_reconfirmation_is_reason_first_and_delta_only() -> None:
    contracts = (
        _read("templates/command-references/quick/intake-and-checkpoint.md"),
        _read("templates/command-references/debug/intake-and-debug-checkpoint.md"),
        _read("templates/advanced-skills/spx-quick/references/task-contract.md"),
        _read("templates/advanced-skills/spx-debug/references/investigation-contract.md"),
    )

    for contract in contracts:
        lowered = contract.lower()
        assert "ui-only" in lowered
        assert "changed ui confirmation rows" in lowered
        assert "main checkpoint is unchanged" in lowered


def test_generated_quick_guidance_does_not_restore_the_legacy_approval_table() -> None:
    propagated_sources = (
        "src/specify_cli/integrations/base.py",
        "src/specify_cli/integrations/cursor_agent/__init__.py",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        "README.md",
        "templates/project-handbook-template.md",
    )

    combined = "\n".join(_read(path).lower() for path in propagated_sources)
    assert "| item | current understanding |" not in combined
    assert "request and outcome" in combined
    assert "user-visible result" in combined
    assert "reconfirmation trigger" in combined
    assert "ui confirmation" in combined
