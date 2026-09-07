from __future__ import annotations

import json
import os
from pathlib import Path

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from typer.testing import CliRunner

from specify_cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLASSIC_DESIGN = PROJECT_ROOT / "templates" / "commands" / "design.md"
CLASSIC_REFERENCES = PROJECT_ROOT / "templates" / "command-references" / "design"
ADVANCED_DESIGN = PROJECT_ROOT / "templates" / "advanced-skills" / "spx-design"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_router_contract(content: str, *, public_entry: str) -> None:
    lowered = content.lower()
    compact = " ".join(lowered.split())
    assert "single public entry point" in lowered
    assert "contract_action: create | refine | audit" in content
    assert "surface_posture: greenfield | inherit-existing | page-overhaul-authorized" in content
    assert "input_strategy: context | synthesize" in content
    assert "synthesize is an input strategy, not a terminal task type" in compact
    assert "resume before reclassification" in lowered
    assert "approval, feedback, and continuation" in compact
    assert f"{public_entry}:create" in content
    assert f"{public_entry}:refine" in content
    assert f"{public_entry}:audit" in content
    assert "do not register or expose" in lowered


def _assert_consumer_contract(content: str) -> None:
    lowered = content.lower()
    compact = " ".join(lowered.split())
    assert "design-first" in lowered
    assert "post-specify" in lowered
    assert "requirements owner" in lowered
    assert "second specify" in lowered
    assert "specify -> design -> plan" in lowered
    assert "direct-delivery consumer" in lowered
    assert "sp-specify" in lowered or "spx-specify" in lowered
    assert "sp-quick" in lowered or "spx-quick" in lowered
    assert "sp-review" in lowered or "spx-review" in lowered
    assert "must not silently retarget" in lowered
    assert "exact current approval digests" in lowered
    assert "audit pass" in lowered
    assert "discussion" in lowered
    assert "not a formal design-contract consumer" in compact


def _assert_terms_in_order(content: str, terms: list[str]) -> None:
    cursor = -1
    lowered = content.lower()
    for term in terms:
        next_cursor = lowered.find(term, cursor + 1)
        assert next_cursor != -1, f"missing ordered term: {term}"
        cursor = next_cursor


def test_classic_design_uses_prompt_routing_and_explicit_consumers() -> None:
    command = _read(CLASSIC_DESIGN)
    router = _read(CLASSIC_REFERENCES / "task-router.md")
    consumers = _read(CLASSIC_REFERENCES / "consumer-contract.md")

    assert "references/task-router.md" in command
    assert "references/consumer-contract.md" in command
    _assert_router_contract(router, public_entry="sp-design")
    _assert_consumer_contract(consumers)


def test_advanced_design_preserves_the_same_routing_contract() -> None:
    skill = _read(ADVANCED_DESIGN / "SKILL.md")
    router = _read(ADVANCED_DESIGN / "references" / "task-router.md")
    consumers = _read(ADVANCED_DESIGN / "references" / "consumer-contract.md")

    assert "references/task-router.md" in skill
    assert "references/consumer-contract.md" in skill
    _assert_router_contract(router, public_entry="spx-design")
    _assert_consumer_contract(consumers)
    lowered_skill = skill.lower()
    compact_skill = " ".join(lowered_skill.split())
    assert "every `refine` that changes approved design truth" in lowered_skill
    assert "create a new `ud-*` workspace" in compact_skill

    surface_map = json.loads(
        _read(ADVANCED_DESIGN.parent / "_shared" / "surface-map.json")
    )
    references = surface_map["skills"]["spx-design"]["references"]
    assert "spx-design/references/task-router.md" in references
    assert "spx-design/references/consumer-contract.md" in references
    assert surface_map["skills"]["spx-design"]["assets"] == [
        "spx-design/assets/design-change.md"
    ]
    optimization = surface_map["skills"]["spx-design"]["optimization"].lower()
    assert "change-scoped" in optimization
    assert "root design-system" not in optimization


def test_quick_pins_an_exact_registered_design_change_for_direct_delivery() -> None:
    classic_quick = _read(
        PROJECT_ROOT
        / "templates"
        / "command-references"
        / "quick"
        / "packetized-work.md"
    )
    advanced_quick = _read(
        PROJECT_ROOT / "templates" / "advanced-skills" / "spx-quick" / "SKILL.md"
    )

    for content in (classic_quick, advanced_quick):
        normalized = " ".join(content.lower().split())
        assert ".specify/design/index.json" in content
        assert "design_change_id" in content
        assert "design_change_ref" in content
        assert "design_change_sha256" in content
        assert "design_contract_ref" in content
        assert "never resolve" in normalized and "latest" in normalized
        assert "preview/manifest/handoff SHA-256" in content
        assert "DS-*" in content
        assert "DH-*" in content
        assert "must not silently adopt a later design approval" in content.lower()


def test_workflow_registry_models_change_scoped_design_artifacts_without_design_md() -> None:
    registry = json.loads(
        _read(PROJECT_ROOT / "templates" / "workflow-artifact-registry.json")
    )
    entries = {entry["id"]: entry for entry in registry["artifacts"]}

    assert ".specify/design/index.json" in entries["ui_design_change_index"][
        "path_patterns"
    ]
    change = entries["ui_design_change_contract"]
    assert ".specify/design/changes/*/design-change.md" in change["path_patterns"]
    assert ".specify/design/changes/*/design-contract.json" in change[
        "path_patterns"
    ]
    workspace = entries["ui_design_change_workspace"]
    assert ".specify/design/changes/*/brief.md" in workspace["path_patterns"]
    assert ".specify/design/changes/*/review.md" in workspace["path_patterns"]
    assert "legacy_project_design_contract" not in entries
    checkpoint = entries["ui_design_direction_checkpoint"]
    assert checkpoint["path_patterns"] == [
        ".specify/design/changes/*/previews/round-*.direction.json"
    ]
    assert checkpoint["owner_cli"] == [
        "specify-runtime design direction-confirm",
        "specify-runtime artifact show",
        "specify-runtime artifact list",
    ]
    assert "round-NN.direction.json" not in change["path_hints"]
    assert "specify-runtime artifact patch" not in checkpoint["owner_cli"]
    prompt = entries["ui_design_generation_prompt"]
    assert prompt["owner_cli"][0] == "specify-runtime design prompt"
    assert "specify-runtime artifact patch" not in prompt["owner_cli"]
    generation = entries["ui_design_generation_sidecar"]
    assert generation["owner_cli"][0] == "specify-runtime design prompt"
    assert "specify-runtime artifact patch" not in generation["owner_cli"]
    concept = entries["ui_design_concept_receipt"]
    assert concept["owner_cli"][0] == "specify-runtime design preview-lint"
    assert "specify-runtime artifact patch" not in concept["owner_cli"]
    index_patterns = entries["ui_design_change_index"]["safe_instruction_patterns"]
    for command in (
        "specify-runtime design iterate",
        "specify-runtime design resolve",
        "specify-runtime design diff",
        "specify-runtime design impact",
        "specify-runtime design adopt",
        "specify-runtime design adoption",
    ):
        assert command in index_patterns


def test_design_routing_is_documented_as_a_cross_profile_product_contract() -> None:
    for path in (
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "PROJECT-HANDBOOK.md",
        PROJECT_ROOT / "templates" / "project-handbook-template.md",
        PROJECT_ROOT / "AGENTS.md",
    ):
        content = _read(path).lower()
        assert "create/refine/audit" in content, path
        assert "synthesis" in content, path
        assert "sp-specify" in content, path
        assert "sp-quick" in content, path
        assert "silently" in content and "retarget" in content, path
        assert "specify-runtime design iterate" in content, path
        assert "specify-runtime design resolve" in content, path
        assert "specify-runtime design diff" in content, path
        assert "specify-runtime design impact" in content, path
        assert "specify-runtime design adopt" in content, path
        assert "specify-runtime design adoption" in content, path
        assert "superseded_scopes" in content, path
        assert "singular" in content, path
        assert "independently bound" in content, path
        assert "confirmation.json" in content, path
        assert "decision.ui_confirmation.design_binding" in content, path
        assert "ui_design_binding" in content, path
        assert "preserved_bindings" in content, path
        assert "invalidated_bindings" in content, path
        assert "reconcile_from" in content, path


def test_design_brief_persists_the_prompt_route() -> None:
    content = _read(PROJECT_ROOT / "templates" / "design-brief-template.md")
    assert "contract_action: null" in content
    assert "surface_posture: null" in content
    assert "input_strategy: null" in content
    assert "route_reason: null" in content
    assert "design_read: null" in content
    assert "dials:" in content
    assert "aesthetic_family: null" in content
    assert "foundation_strategy: null" in content
    assert "redesign_mode: null" in content
    assert "anti_slop_locks: []" in content
    assert "reference_board_intents: []" in content
    assert "style_authority:" in content
    assert "mode: unresolved" in content
    assert "source_refs: []" in content
    assert "protected_surfaces: []" in content
    assert "allowed_style_delta_surfaces: []" in content
    assert "authorization_source: null" in content
    assert "delivery_context:" in content
    assert "origin: standalone" in content
    assert "return_target: null" in content
    assert "## Taste Intake" in content


def test_design_brief_scaffold_agent_fill_required_includes_taste_fields() -> None:
    scaffold = _read(
        PROJECT_ROOT / "tools" / "specify-runtime" / "artifact_scaffold.go"
    )
    # Bound the design-brief kind block so we do not match unrelated kinds.
    start = scaffold.index('"design-brief"')
    end = scaffold.index('"design-review"', start)
    block = scaffold[start:end]
    for field in (
        "design_read",
        "dials",
        "aesthetic_family",
        "foundation_strategy",
        "anti_slop_locks",
        "reference_board_intents",
        "style_authority",
        "delivery_context",
    ):
        assert f'"{field}"' in block
    assert '"redesign_mode"' not in block


def test_design_surfaces_teach_taste_intake_iteration_and_redesign() -> None:
    classic_shell = _read(
        PROJECT_ROOT / "templates" / "command-partials" / "design" / "shell.md"
    )
    classic_router = _read(CLASSIC_REFERENCES / "task-router.md")
    advanced_skill = _read(ADVANCED_DESIGN / "SKILL.md")
    advanced_contract = _read(ADVANCED_DESIGN / "references" / "design-contract.md")
    advanced_router = _read(ADVANCED_DESIGN / "references" / "task-router.md")
    ui_gate = _read(
        PROJECT_ROOT
        / "templates"
        / "advanced-skills"
        / "_shared"
        / "ui-quality-gate.md"
    )
    frontend = _read(
        PROJECT_ROOT / "templates" / "passive-skills" / "frontend-design" / "SKILL.md"
    )
    anti_slop = _read(
        PROJECT_ROOT / "templates" / "design-library" / "anti-slop-policy.md"
    )

    for content in (
        classic_shell,
        classic_router,
        advanced_skill,
        advanced_contract,
        advanced_router,
    ):
        lowered = content.lower()
        assert "design_read" in lowered or "taste intake" in lowered
        assert "dials" in lowered or "variance" in lowered

    for router in (classic_router, advanced_router):
        lowered = router.lower()
        assert "single public entry" in lowered
        assert "do not register or expose" in lowered or "do not expose colon" in lowered
        assert "taste" in lowered

    assert "same direction" in classic_shell.lower()
    assert "new immutable round" in classic_shell.lower()
    assert "explicit approval" in classic_shell.lower()
    assert "preserve" in classic_shell.lower() and "overhaul" in classic_shell.lower()
    assert "mood" in classic_router.lower() and "color-only" in classic_router.lower()
    assert "landing" in anti_slop.lower()
    assert "product-workspace" in anti_slop.lower()
    assert "trust-public" in anti_slop.lower()
    assert "subordinate" in anti_slop.lower()
    assert "anti-slop" in ui_gate.lower() or "anti-slop" in frontend.lower()
    assert "design-library/anti-slop-policy.md" in frontend or "anti-slop-policy" in frontend

    for content in (
        classic_shell,
        classic_router,
        advanced_skill,
        advanced_contract,
        advanced_router,
        ui_gate,
    ):
        lowered = " ".join(content.lower().split())
        assert "style_authority" in lowered
        assert "inherit-existing" in lowered
        assert "page-overhaul-authorized" in lowered
        assert "global-shell" in lowered
        assert "shared-components" in lowered

    seeds = list((PROJECT_ROOT / "templates" / "design-library").glob("*.md"))
    seed_names = {path.name for path in seeds}
    assert "anti-slop-policy.md" in seed_names
    assert "marketing-editorial-asymmetric.md" in seed_names
    assert "soft-premium-calm.md" in seed_names
    assert "industrial-brutalist.md" in seed_names
    assert "minimal-product-linear.md" in seed_names
    for name in (
        "marketing-editorial-asymmetric.md",
        "soft-premium-calm.md",
        "industrial-brutalist.md",
        "minimal-product-linear.md",
    ):
        seed = _read(PROJECT_ROOT / "templates" / "design-library" / name)
        assert "Not approval truth" in seed or "not approval truth" in seed.lower()
        assert "seed_warning" in seed


def test_design_direction_flow_is_platform_neutral_and_single_concept() -> None:
    classic = "\n".join(
        [
            _read(CLASSIC_DESIGN),
            _read(CLASSIC_REFERENCES / "task-router.md"),
            _read(CLASSIC_REFERENCES / "discovery-dialogue.md"),
            _read(CLASSIC_REFERENCES / "image-generation-studio.md"),
            _read(CLASSIC_REFERENCES / "html-prototype-studio.md"),
            _read(CLASSIC_REFERENCES / "critique-loop.md"),
        ]
    )
    advanced = "\n".join(
        [
            _read(ADVANCED_DESIGN / "SKILL.md"),
            _read(ADVANCED_DESIGN / "references" / "task-router.md"),
            _read(ADVANCED_DESIGN / "references" / "studio-loop.md"),
            _read(ADVANCED_DESIGN / "references" / "image-round.md"),
            _read(ADVANCED_DESIGN / "references" / "html-round.md"),
            _read(ADVANCED_DESIGN / "references" / "design-contract.md"),
        ]
    )

    for content in (classic, advanced):
        compact = " ".join(content.lower().split())
        _assert_terms_in_order(
            compact,
            [
                "intake",
                "concept-calibration",
                "direction-confirmed",
                "contract-completion",
                "formal-approval",
                "register",
            ],
        )
        assert "platform-neutral" in compact or "platform independent" in compact
        assert "one current concept" in compact
        assert "2-3 textual choices" in compact
        assert "do not generate three full boards" in compact


def test_direction_confirmation_is_not_consumable_by_delivery_workflows() -> None:
    classic = "\n".join(
        [
            _read(CLASSIC_REFERENCES / "consumer-contract.md"),
            _read(CLASSIC_REFERENCES / "discovery-dialogue.md"),
            _read(CLASSIC_REFERENCES / "critique-loop.md"),
        ]
    )
    advanced = "\n".join(
        [
            _read(ADVANCED_DESIGN / "references" / "consumer-contract.md"),
            _read(ADVANCED_DESIGN / "references" / "studio-loop.md"),
            _read(ADVANCED_DESIGN / "references" / "design-contract.md"),
        ]
    )

    for content in (classic, advanced):
        compact = " ".join(content.lower().split())
        assert "direction-confirmed is non-consumable" in compact
        assert "plan and implement may consume only formal-approval plus register" in compact
        assert "direction-confirmed must not bind spec-contract.json" in compact
        assert "approve/register receipt" in compact


def test_post_specify_design_returns_to_plan_without_repeating_specify() -> None:
    classic = " ".join(
        _read(CLASSIC_REFERENCES / "consumer-contract.md").lower().split()
    )
    advanced = " ".join(
        _read(ADVANCED_DESIGN / "references" / "consumer-contract.md")
        .lower()
        .split()
    )
    plan_surfaces = (
        _read(PROJECT_ROOT / "templates" / "command-partials" / "plan" / "shell.md"),
        _read(
            PROJECT_ROOT
            / "templates"
            / "advanced-skills"
            / "spx-plan"
            / "references"
            / "planning-contract.md"
        ),
    )

    for content in (classic, advanced):
        assert "formal-post-specify" in content
        assert "specify -> design -> plan" in content
        assert "must not require a second specify" in content
        assert "requirements change" in content

    for content in plan_surfaces:
        lowered = " ".join(content.lower().split())
        assert "formal-post-specify" in lowered
        assert "specify-runtime design adoption" in lowered
        assert "source spec" in lowered


def test_specify_design_gate_is_an_external_user_invoked_stop_before_plan() -> None:
    classic = " ".join(
        _read(PROJECT_ROOT / "templates" / "command-partials" / "specify" / "shell.md")
        .lower()
        .split()
    )
    advanced = " ".join(
        _read(PROJECT_ROOT / "templates" / "advanced-skills" / "spx-specify" / "SKILL.md")
        .lower()
        .split()
    )

    for content in (classic, advanced):
        assert "design_gate" in content
        assert "/sp.design" in content
        assert "formal-post-specify" in content
        assert "return" in content and "plan" in content
        assert "do not invoke" in content


def test_plan_and_review_enforce_existing_ui_style_authority() -> None:
    surfaces = (
        _read(
            PROJECT_ROOT
            / "templates"
            / "command-references"
            / "plan"
            / "research-and-design-lanes.md"
        ),
        _read(
            PROJECT_ROOT
            / "templates"
            / "command-partials"
            / "review"
            / "shell.md"
        ),
        _read(
            PROJECT_ROOT
            / "templates"
            / "advanced-skills"
            / "spx-review"
            / "SKILL.md"
        ),
        _read(
            PROJECT_ROOT
            / "templates"
            / "advanced-skills"
            / "spx-review"
            / "references"
            / "review-contract.md"
        ),
    )

    for content in surfaces:
        lowered = " ".join(content.lower().split())
        assert "style_authority" in lowered
        assert "inherit-existing" in lowered
        assert "page-overhaul-authorized" in lowered
        assert "global-shell" in lowered
        assert "shared-components" in lowered


def test_init_start_here_teaches_the_prompt_router_and_consumers() -> None:
    content = " ".join(
        _read(PROJECT_ROOT / "src" / "specify_cli" / "__init__.py").split()
    )
    assert '"design", "create, refine, or audit' in content
    assert "one prompt-routed collaborative studio" in content
    assert "formal adoption through" in content
    assert "direct delivery through" in content


def test_classic_init_start_here_exposes_one_prompt_routed_design_skill(
    tmp_path: Path,
) -> None:
    project = tmp_path / "classic-design-start-here"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = CliRunner().invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "codex",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    output = " ".join(result.output.split())
    assert result.exit_code == 0, result.output
    assert "$sp-design" in output
    assert "one prompt-routed collaborative studio" in output
    assert "$sp-specify" in output
    assert "$sp-quick" in output


def test_advanced_init_start_here_exposes_the_same_design_route(
    tmp_path: Path,
) -> None:
    project = tmp_path / "advanced-design-start-here"
    project.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = CliRunner().invoke(
            app,
            [
                "init",
                "--here",
                "--ai",
                "codex",
                "--script",
                "sh",
                "--workflow-profile",
                "advanced",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    output = " ".join(result.output.split())
    assert result.exit_code == 0, result.output
    assert "$spx-design" in output
    assert "create, refine, or audit one prompt-routed design system" in output
    assert "formal adoption through spx-specify" in output
    assert "direct delivery through spx-quick" in output


def test_generated_codex_design_skill_keeps_one_public_entrypoint(
    tmp_path: Path,
) -> None:
    project = tmp_path / "codex-design-router"
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", project)
    integration.setup(project, manifest, script_type="sh")

    skills_dir = integration.skills_dest(project)
    design_dir = skills_dir / "sp-design"
    skill = _read(design_dir / "SKILL.md")
    router = _read(design_dir / "references" / "task-router.md")
    consumers = _read(design_dir / "references" / "consumer-contract.md")

    assert "references/task-router.md" in skill
    assert "references/consumer-contract.md" in skill
    _assert_router_contract(router, public_entry="sp-design")
    _assert_consumer_contract(consumers)
    assert not any(":" in path.name for path in skills_dir.iterdir())
