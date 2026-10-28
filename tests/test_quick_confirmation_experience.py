"""Quick explains a concrete change before asking for mutation approval.

These are prompt/rendering contracts and schema compatibility checks. They do
not claim to simulate an agent or replace the runtime's native execution gates.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import load_runtime_launcher, write_runtime_launcher_config

from .template_utils import (
    assert_quick_checkpoint_card_shape,
    read_command_with_references,
    read_template,
)


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_EXPLANATION_FIELDS = (
    "current_state_evidence", "recommended_approach",
    "assumptions_and_risks", "completion_evidence",
)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _assert_new_evidence_survives_runtime_staging(contract: str) -> None:
    normalized = _normalized(contract)
    for required in (
        "confirmation.decision.current_state_evidence", "views.decision",
        "incompatible", "pinned compatible runtime", "re-stage", "legacy",
    ):
        assert required in normalized
    assert "do not ask for approval" in normalized or "before asking for approval" in normalized
    assert "backfill" in normalized


def _assert_delta_evidence_preserves_binding_without_replaying_unchanged_basis(contract: str) -> None:
    normalized = _normalized(contract)
    assert "newly gathered raw request" in normalized
    start = normalized.index("for material amendments, retain supplied")
    end = normalized.index("otherwise omit the unchanged basis from the delta view", start)
    delta = normalized[start:end]
    assert "`current_state_evidence` in the returned typed decision and its digest" in delta
    assert (
        "show that basis in the human delta view only when `current_state_evidence` "
        "is named in `source.changed_decision_fields`"
    ) in delta


def _profile_contract(profile: str) -> str:
    if profile == "classic":
        return read_command_with_references("quick")
    paths = [ROOT / "templates/advanced-skills/spx-quick/SKILL.md"]
    paths.extend(sorted((ROOT / "templates/advanced-skills/spx-quick/references").glob("*.md")))
    paths.append(ROOT / "templates/advanced-skills/_shared/human-confirmation.md")
    return "\n\n".join(path.read_text(encoding="utf-8") for path in paths)


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_quick_intake_allows_bounded_evidence_before_mutation_approval(profile: str) -> None:
    contract = _normalized(_profile_contract(profile))
    for required in ("bounded", "existing", "read-only", "evidence", "safe", "before"):
        assert required in contract
    for protected_field in PROTECTED_EXPLANATION_FIELDS:
        assert protected_field in contract
    assert "read-only evidence" in contract
    assert "checkpoint-confirm" in contract


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_quick_confirmation_owns_mutation_not_safe_discovery(profile: str) -> None:
    contract = _normalized(_profile_contract(profile))
    assert "production" in contract
    assert "harness" in contract
    assert "instrumentation" in contract
    assert any(marker in contract for marker in (
        "implementation dispatch", "implementation delegation",
        "dispatch an implementation packet",
    ))
    assert "checkpoint-confirm" in contract
    assert "inherited" in contract
    assert "hand-patched" in contract or "hand-patch" in contract
    assert "start execution only after a leased `specify-runtime artifact patch` sets `understanding_confirmed: true`" not in contract
    assert "until the checkpoint is confirmed, you must not proceed to code edits, broad repository analysis, delegation, validation commands" not in contract


@pytest.mark.parametrize("path", [
    "templates/command-partials/quick/checkpoint-card.md",
    "templates/advanced-skills/_shared/human-confirmation.md",
])
def test_quick_human_card_shows_basis_change_impact_and_completion(path: str) -> None:
    contract = read_template(path)
    assert_quick_checkpoint_card_shape(contract)
    start = contract.index("## 请确认本次修改")
    end = contract.index("回复：", start)
    card = contract[start:end]
    sections = ("### 当前情况与依据", "### 你会看到", "### 交付与验收", "### 方案与完成标准")
    offsets = [card.index(section) for section in sections]
    assert offsets == sorted(offsets)
    for marker in ("推荐路径", "假设或风险", "完成证据"):
        assert marker in card
    normalized = _normalized(contract)
    assert "do not invent" in normalized
    assert "new" in normalized and ("greenfield" in normalized or "implementation" in normalized)
    for field in PROTECTED_EXPLANATION_FIELDS:
        assert field in normalized


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_quick_reuses_exact_approval_and_limits_reconfirmation_to_decision_delta(profile: str) -> None:
    contract = _normalized(_profile_contract(profile))
    for required in ("inherited", "--delivery-only", "changed_decision_fields", "semantic delta"):
        assert required in contract
    assert "current_state_evidence" in contract
    assert "do not reopen confirmation" in contract
    assert "only the changed rows or decisions" in contract
    assert "do not repeat the full initial quick checkpoint" in contract


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_quick_rejects_new_proposals_whose_old_runtime_drops_the_evidence_basis(profile: str) -> None:
    _assert_new_evidence_survives_runtime_staging(_profile_contract(profile))


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_quick_delta_keeps_evidence_bound_but_displays_only_selected_changed_basis(profile: str) -> None:
    paths = (
        (
            "templates/command-partials/quick/checkpoint-card.md",
            "templates/command-references/quick/intake-and-checkpoint.md",
        ) if profile == "classic" else (
            "templates/advanced-skills/_shared/human-confirmation.md",
            "templates/advanced-skills/spx-quick/references/task-contract.md",
        )
    )
    for path in paths:
        _assert_delta_evidence_preserves_binding_without_replaying_unchanged_basis(read_template(path))


def test_current_state_evidence_schema_does_not_break_legacy_confirmations() -> None:
    schema = json.loads((ROOT / "templates/quick-confirmation-schema.json").read_text(encoding="utf-8"))
    decision = schema["properties"]["decision"]
    field = decision["properties"]["current_state_evidence"]
    assert field["type"] == "array"
    assert field["items"]["type"] == "string"
    assert "current_state_evidence" not in decision["required"]
    assert schema["title"] == "quick-confirmation-v1"


@pytest.mark.parametrize("path", [
    "templates/command-partials/common/context-sufficiency-choice.md",
    "templates/advanced-skills/_shared/context-sufficiency-choice.md",
])
def test_quick_context_direct_choice_approves_one_explained_concrete_proposal(path: str) -> None:
    contract = _normalized(read_template(path))
    start = contract.index("for quick,")
    quick = contract[start:contract.index("for debug,", start)]
    for required in (
        "current findings", "evidence basis", "concrete proposed change",
        "reason", "affected behavior", "expected result", "risks", "verification",
        "direct change (recommended)", "approves that exact bounded proposal once",
        "do not add a redundant implementation confirmation",
    ):
        assert required in quick


@pytest.mark.parametrize("path", [
    "templates/commands/auto.md",
    "templates/advanced-skills/spx-auto/SKILL.md",
])
def test_auto_quick_continuation_preserves_real_human_consent(path: str) -> None:
    contract = _normalized(read_template(path))
    quick_start = contract.index("quick concrete-change consent") if "quick concrete-change consent" in contract else contract.index("for quick,")
    quick = contract[quick_start:contract.index("debug", quick_start)]
    for required in (
        "cannot confirm", "direct change (recommended)", "ui direction",
        "required human acceptance", "human-approved decision", "inherited binding",
        "safe bounded read-only evidence", "current findings", "concrete change",
        "impact, risks and verification", "wait for the real human reply",
        "material decision deltas", "execution-only rearranges",
    ):
        assert required in quick


@pytest.mark.parametrize("key,profile,script_type", [
    ("codex", "classic", "ps"),
    ("codex", "advanced", "sh"),
    ("claude", "classic", "sh"),
    ("claude", "advanced", "ps"),
    ("gemini", "classic", "ps"),
    ("opencode", "classic", "sh"),
])
def test_quick_confirmation_experience_survives_real_native_rendering(
    key: str, profile: str, script_type: str, tmp_path: Path,
) -> None:
    project = tmp_path / f"{key}-{profile}"
    # Installation is real; this fixture is deliberately not an executable
    # runtime and does not claim to execute checkpoint or consent routes.
    runtime = tmp_path / "runtime-source" / "specify-runtime.exe"
    runtime.parent.mkdir()
    runtime.write_bytes(b"render fixture only\n")
    write_runtime_launcher_config(project, runtime)
    integration = get_integration(key)
    manifest = IntegrationManifest(key, project)
    integration.setup(
        project, manifest,
        parsed_options={"workflow_profile": profile}, script_type=script_type,
    )
    if key in ("codex", "claude"):
        prefix = "spx" if profile == "advanced" else "sp"
        skill_dir = integration.skills_dest(project) / f"{prefix}-quick"
        entry = skill_dir / "SKILL.md"
        references = skill_dir / "references"
    else:
        entry = integration.commands_dest(project) / integration.command_filename("quick")
        references = entry.parent / "references/quick"
    entry_body = entry.read_text(encoding="utf-8")
    if key == "gemini":
        entry_body = tomllib.loads(entry_body)["prompt"]
    reference_paths = sorted(references.rglob("*.md"))
    assert reference_paths
    for path in (entry, *reference_paths):
        assert path.relative_to(project).as_posix() in manifest.files
    contract = entry_body + "\n" + "\n".join(path.read_text(encoding="utf-8") for path in reference_paths)
    normalized = _normalized(contract)
    assert_quick_checkpoint_card_shape(contract)
    _assert_new_evidence_survives_runtime_staging(contract)
    _assert_delta_evidence_preserves_binding_without_replaying_unchanged_basis(contract)
    for field in PROTECTED_EXPLANATION_FIELDS:
        assert field in normalized
    assert "read-only evidence" in normalized
    assert "hand-patched" in normalized or "hand-patch" in normalized
    launcher = load_runtime_launcher(project)
    assert launcher is not None
    assert f"{launcher.command} quick checkpoint-confirm" in contract
    for unresolved in ("{{spec-kit-include:", "{{specify-subcmd:", "__AGENT__"):
        assert unresolved not in contract
    assert "start execution only after a leased `specify-runtime artifact patch` sets `understanding_confirmed: true`" not in normalized
