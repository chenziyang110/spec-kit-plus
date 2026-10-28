"""Debug approval is a concrete repair decision after evidence discovery.

These are rendered prompt and state contracts, not runtime consent enforcement.
"""

import re
import tomllib
from pathlib import Path

import pytest
import yaml

from specify_cli.integrations import get_integration
from specify_cli.integrations.base import SkillsIntegration, TomlIntegration
from specify_cli.integrations.manifest import IntegrationManifest

from .template_utils import assert_debug_checkpoint_card_shape, read_template


ROOT = Path(__file__).resolve().parents[1]
REPAIR_FIELDS = (
    "discovered_problem",
    "root_cause",
    "evidence_refs",
    "proposed_fix",
    "change_scope",
    "expected_outcome",
    "risks",
    "validation_plan",
)


def _compact(content: str) -> str:
    return " ".join(content.lower().replace("`", "").split())


def _installed_contract(integration, project: Path, profile: str, command_name: str = "debug") -> str:
    if isinstance(integration, SkillsIntegration):
        workflow = f"spx-{command_name}" if profile == "advanced" else f"sp-{command_name}"
        command = integration.skills_dest(project) / workflow / "SKILL.md"
        references = command.parent / "references"
        body = command.read_text(encoding="utf-8")
    else:
        command = integration.commands_dest(project) / integration.command_filename(command_name)
        references = command.parent / "references" / command_name
        body = command.read_text(encoding="utf-8")
        if isinstance(integration, TomlIntegration):
            body = tomllib.loads(body)["prompt"]
    assert command.is_file()
    if command_name == "debug":
        assert references.is_dir()
    sidecars = sorted(references.rglob("*.md"))
    if command_name == "debug":
        assert sidecars
    return "\n\n".join([body, *(path.read_text(encoding="utf-8") for path in sidecars)])


@pytest.mark.parametrize(
    ("integration_key", "profile"),
    (
        ("codex", "classic"),
        ("codex", "advanced"),
        ("claude", "classic"),
        ("claude", "advanced"),
        ("gemini", "classic"),
        ("opencode", "classic"),
    ),
)
def test_installed_debug_presents_findings_and_repair_before_mutation(
    tmp_path: Path, integration_key: str, profile: str
) -> None:
    integration = get_integration(integration_key)
    project = tmp_path / integration_key / profile
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile})

    contract = _installed_contract(integration, project, profile)
    assert_debug_checkpoint_card_shape(contract)
    compact = _compact(contract)
    for field in (*REPAIR_FIELDS, "confirmation_digest"):
        assert field in compact, (integration_key, profile, field)
    assert "evidence-backed-repair" in compact
    assert "diagnostic-enablement" in compact
    assert "understanding_confirmed: false" in compact
    assert (
        "before any repair write or fix-worker dispatch" in compact
        or "before user approval, no product or test changes, harness repair, persistent instrumentation, or fix-worker dispatch is allowed" in compact
    )
    for obsolete_gate in (
        "not a fix-plan approval",
        "blocks evidence investigation on resume",
        "wait for user confirmation before reproduction commands",
    ):
        assert obsolete_gate not in compact, (integration_key, profile, obsolete_gate)

    # The same generated contract still requires causal proof, RED, fresh
    # regression evidence, and final human verification after the repair.
    for invariant in (
        "root cause",
        "failing automated",
        "awaiting_human_verify",
        "human verification",
    ):
        assert invariant in compact, (integration_key, profile, invariant)
    assert "related risk" in compact or "related-risk" in compact
    _assert_auto_preserves_debug_human_consent(
        _installed_contract(integration, project, profile, "auto")
    )

    if profile == "classic" and isinstance(integration, SkillsIntegration):
        passive = integration.skills_dest(project) / "test-driven-development" / "SKILL.md"
        passive_contract = _compact(passive.read_text(encoding="utf-8"))
        debug_rule = next(
            line for line in passive_contract.split("- ") if "sp-debug" in line
        )
        assert "existing evidence first" in debug_rule
        assert "user confirmation before authoring tests" in debug_rule
        assert "prove red before changing production code" in debug_rule
        assert "diagnostic-enablement approval permits only" in debug_rule


def test_new_debug_state_starts_without_repair_authority_and_keeps_bound_fields() -> None:
    source = (ROOT / "templates/artifacts/debug-session.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(source.split("---", 2)[1])
    assert frontmatter["understanding_confirmed"] is False
    assert frontmatter["human_verification"] == "not_requested"
    section = re.search(
        r"^## Debug Understanding Checkpoint\s*\n(.*?)(?=^## |\Z)",
        source,
        re.MULTILINE | re.DOTALL,
    )
    assert section is not None
    checkpoint = yaml.safe_load(section.group(1))["checkpoint"]
    assert checkpoint["confirmation_purpose"] == "evidence-backed-repair"
    assert checkpoint["fix_authority"] == "diagnose only"
    assert not checkpoint["confirmation_digest"]
    assert set(REPAIR_FIELDS) <= checkpoint.keys()
    assert all(not checkpoint[field] for field in REPAIR_FIELDS)


def test_documented_debug_state_describes_the_same_repair_decision() -> None:
    source = (ROOT / "templates/debug.md").read_text(encoding="utf-8")
    source = source.split("```markdown", 1)[1].split("```", 1)[0]
    assert "## Debug Understanding Checkpoint" in source
    assert "confirmation_purpose: evidence-backed-repair | diagnostic-enablement" in source
    assert "true only after explicit approval of the current concrete" in source
    assert "not required for safe diagnosis" in source
    for field in (*REPAIR_FIELDS, "confirmation_digest"):
        assert re.search(rf"^  {field}:", source, re.MULTILINE), field


def test_debug_card_separates_proven_findings_from_reporter_corrections() -> None:
    contracts = (
        read_template("templates/command-partials/debug/checkpoint-card.md"),
        (ROOT / "templates/advanced-skills/_shared/human-confirmation.md").read_text(
            encoding="utf-8"
        ),
    )
    for contract in contracts:
        assert_debug_checkpoint_card_shape(contract)
        compact = _compact(contract)
        assert (
            "technical hypotheses belong to the agent" in compact
            or "user approves the bounded repair, not the technical hypothesis" in compact
        )
        assert "decisive evidence" in compact
        assert "expected outcome" in compact or "expected_outcome" in compact or "what the user should observe afterward" in compact
        assert "diagnose only" in compact
        assert "speculative" in compact
        assert "diagnostic" in compact


@pytest.mark.parametrize(
    "path",
    (
        "templates/command-references/debug/intake-and-debug-checkpoint.md",
        "templates/advanced-skills/spx-debug/references/investigation-contract.md",
    ),
)
def test_repair_approval_is_bound_on_resume_and_diagnostic_permission_is_separate(path: str) -> None:
    contract = _compact(read_template(path))
    assert "understanding_confirmed: false" in contract
    assert "understanding_confirmed: true" in contract
    for field in (*REPAIR_FIELDS, "confirmation_digest"):
        assert field in contract, (path, field)
    assert "canonical json" in contract or "canonical approved decision json" in contract
    assert "sorted keys" in contract or "sorted object keys" in contract
    assert "stable array order" in contract or "stable arrays" in contract
    assert "utf-8" in contract
    assert "exclude checkpoint/ui confirmation digests" in contract or (
        "exclude both checkpoint.confirmation_digest" in contract
        and "ui_confirmation.confirmation_digest self-fields" in contract
    )
    assert "legacy" in contract
    assert "matching digest" in contract
    assert "does not authorize repair" in contract or "is not repair authority" in contract
    assert "diagnostic-enablement" in contract
    assert "evidence-backed-repair" in contract
    assert "return to investigation" in contract or "return to diagnosis" in contract
    assert "debug checkpoint amendment" in contract
    assert "unchanged" in contract
    assert "safe bounded diagnosis may continue" in contract or "safe bounded diagnosis within the existing scope may continue" in contract


@pytest.mark.parametrize(
    "path",
    (
        "templates/command-partials/common/context-sufficiency-choice.md",
        "templates/advanced-skills/_shared/context-sufficiency-choice.md",
    ),
)
def test_context_direct_choice_itself_explains_and_approves_the_concrete_repair(path: str) -> None:
    contract = _compact(read_template(path))
    assert "discovered defect" in contract
    assert "decisive evidence" in contract
    assert "concrete proposed fix" in contract
    assert "affected change scope" in contract
    assert "expected result, risks" in contract
    assert "original-reproduction/regression verification" in contract
    assert "approves that exact bounded repair" in contract
    assert "not ask a redundant repair confirmation" in contract or "not add a redundant repair confirmation" in contract
    assert "generic fix request or an unexplained menu" in contract or (
        "generic request to fix nor a menu without these findings" in contract
    )


@pytest.mark.parametrize(
    "path",
    (
        "templates/worker-prompts/debug-investigator.md",
        "templates/advanced-skills/spx-debug/references/investigator-worker.md",
    ),
)
def test_unconfirmed_workers_only_collect_evidence_against_a_provisional_ui_target(path: str) -> None:
    contract = _compact(read_template(path))
    assert "read-only evidence workers may run during unconfirmed diagnosis" in contract
    assert "provisional existing/source-backed target before repair confirmation" in contract
    assert "confirmed ui repair target afterward" in contract
    assert "diagnostic-enablement authority" in contract
    assert "do not edit product or test files" in contract or "worker does not edit product or test files" in contract
    assert "must not propose a redesign" in contract


def _assert_auto_preserves_debug_human_consent(content: str) -> None:
    contract = _compact(content)
    assert "auto_default_recommendation cannot grant" in contract
    assert "diagnostic-enablement consent, select **direct fix (recommended)**" in contract
    assert "substitute for final human verification" in contract
    assert "exact human-approved decision content and its current binding" in contract
    assert "wait for a real human reply" in contract
    assert "wait for the user's result" in contract
    assert "safe bounded diagnosis remains available under debug's intake gates" in contract


@pytest.mark.parametrize("path", ("templates/commands/auto.md", "templates/advanced-skills/spx-auto/SKILL.md"))
def test_auto_recommendation_cannot_replace_debug_user_confirmation(path: str) -> None:
    _assert_auto_preserves_debug_human_consent(read_template(path))
