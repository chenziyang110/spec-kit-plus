"""Design Intelligence horizontal layer across UI-bearing Spec workflow stages.

Proves shared contracts, stage hooks, and durable design-context surfaces without
introducing a new mainline command.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADVANCED = PROJECT_ROOT / "templates" / "advanced-skills"
CLASSIC_PARTIAL = (
    PROJECT_ROOT / "templates" / "command-partials" / "common" / "design-intelligence.md"
)
DI_PARTIALS_DIR = (
    PROJECT_ROOT / "templates" / "command-partials" / "design-intelligence"
)
UI_GATE = ADVANCED / "_shared" / "ui-quality-gate.md"
ANTI_SLOP = (
    PROJECT_ROOT / "templates" / "design-library" / "anti-slop-policy.md"
)
DI_SHARED_MARKERS = (
    "Design Intelligence Engine",
    "Design Evidence v1",
    "Evidence → System → Implementation",
    "DesignContext v1",
)

UI_STAGES_CLASSIC = (
    "discussion",
    "specify",
    "quick",
    "debug",
    "implement",
    "review",
)

UI_STAGES_SPX = (
    "spx-discussion",
    "spx-specify",
    "spx-quick",
    "spx-debug",
    "spx-implement",
    "spx-review",
)

FORBIDDEN_MAINLINE_COMMANDS = (
    "sp-design-intelligence",
    "spx-design-intelligence",
    "sp-taste",
    "spx-taste",
)


def _read(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def _rendered_command(name: str) -> str:
    parts = [read_template(f"templates/commands/{name}.md")]
    ref_dir = PROJECT_ROOT / "templates" / "command-references" / name
    if ref_dir.is_dir():
        for path in sorted(ref_dir.glob("*.md")):
            parts.append(read_template(path.relative_to(PROJECT_ROOT).as_posix()))
    partial = PROJECT_ROOT / "templates" / "command-partials" / name / "shell.md"
    if partial.is_file():
        parts.append(read_template(partial.relative_to(PROJECT_ROOT).as_posix()))
    return "\n".join(parts)


def test_no_new_mainline_design_intelligence_command() -> None:
    commands = list((PROJECT_ROOT / "templates" / "commands").glob("*.md"))
    names = {path.stem for path in commands}
    assert "design-intelligence" not in names
    assert "taste" not in names

    advanced_skills = {
        path.name
        for path in ADVANCED.iterdir()
        if path.is_dir() and path.name.startswith("spx-")
    }
    assert "spx-design-intelligence" not in advanced_skills
    assert "spx-taste" not in advanced_skills

    shared = CLASSIC_PARTIAL.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_MAINLINE_COMMANDS:
        assert forbidden not in shared or "No" in shared


def test_shared_design_intelligence_surface_exists() -> None:
    assert CLASSIC_PARTIAL.is_file()
    classic = read_template(
        "templates/command-partials/common/design-intelligence.md"
    )
    advanced = UI_GATE.read_text(encoding="utf-8")
    anti = ANTI_SLOP.read_text(encoding="utf-8")

    for content in (classic, advanced):
        lowered = content.lower()
        assert "design intelligence" in lowered
        assert "variance" in lowered and "motion" in lowered and "density" in lowered
        assert "anti-slop" in lowered or "anti_slop" in lowered
        assert "bootstrap" in lowered or "design approve" in lowered
        assert "design approve" in lowered or "approved" in lowered

    assert "subordinate" in anti.lower()
    assert "landing" in anti.lower()
    assert "product-workspace" in anti.lower()


def test_design_intelligence_partials_are_single_sourced() -> None:
    """Classic DI rule body lives under design-intelligence/; common is orchestrator."""

    expected = (
        "shared-foundation.md",
        "evidence-rules.md",
        "stage-hooks.md",
        "ui-quality-gate-pointer.md",
    )
    for name in expected:
        assert (DI_PARTIALS_DIR / name).is_file(), name

    orchestrator = CLASSIC_PARTIAL.read_text(encoding="utf-8")
    for name in expected:
        assert f"design-intelligence/{name}" in orchestrator.replace("\\", "/")

    # Shared markers appear once in the split sources (not duplicated across files).
    for marker in DI_SHARED_MARKERS:
        hits = [
            path.name
            for path in DI_PARTIALS_DIR.glob("*.md")
            if marker in path.read_text(encoding="utf-8")
        ]
        assert len(hits) == 1, f"{marker!r} should be single-sourced, found in {hits}"

    advanced = UI_GATE.read_text(encoding="utf-8")
    assert "install surface" in advanced.lower() or "not a second rule book" in advanced.lower()
    assert "design-evidence.schema.json" in advanced
    assert (PROJECT_ROOT / "templates/design-intelligence/CAPABILITY-MATRIX.md").is_file()
    assert (PROJECT_ROOT / "templates/design-intelligence/ARTIFACT-LIFECYCLE.md").is_file()


def test_classic_ui_stages_include_design_intelligence_partial() -> None:
    for stage in UI_STAGES_CLASSIC:
        shell = _read(f"templates/command-partials/{stage}/shell.md")
        assert "design-intelligence.md" in shell, stage


def test_advanced_ui_stages_reference_ui_quality_gate_with_stage_hooks() -> None:
    gate = UI_GATE.read_text(encoding="utf-8")
    gate_lower = gate.lower()
    assert "design discovery" in gate_lower or "design_context" in gate_lower
    assert "ui acceptance" in gate_lower or "ui requirements" in gate_lower
    assert "design-before-code" in gate_lower or "quick design loop" in gate_lower or "ui audit" in gate_lower
    assert "visual/layout" in gate_lower
    assert "taste/generic-look" in gate_lower or "taste" in gate_lower
    assert "ui implementation rules" in gate_lower or "implement" in gate_lower
    assert "measured" in gate_lower and "assumption" in gate_lower

    for skill in UI_STAGES_SPX:
        content = (ADVANCED / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "references/ui-quality-gate.md" in content, skill


def test_discussion_design_context_is_durable() -> None:
    state = _read("templates/discussion-state-template.md")
    handoff = json.loads(_read("templates/discussion-handoff-template.json"))
    discussion = _rendered_command("discussion")
    lowered = discussion.lower()

    assert "design_context" in state
    assert "feeling_tone" in state
    assert "variance" in state
    assert "anti_slop_locks" in state
    assert "sp_design_required" in state

    digest = handoff["discussion_decision_digest"]
    assert "design_context" in digest
    ctx = digest["design_context"]
    assert "ui_involved" in ctx
    assert "dials" in ctx
    assert set(ctx["dials"]) >= {"variance", "motion", "density"}

    assert "design discovery" in lowered
    assert "design_context" in discussion
    assert "design intelligence" in lowered


def test_specify_carries_ui_acceptance_and_design_dna() -> None:
    spec = _read("templates/spec-template.md")
    brief = _read("templates/ui-brief-template.md")
    specify = _rendered_command("specify")
    spx_ui = _read(
        "templates/advanced-skills/spx-specify/references/ui-and-handoffs.md"
    )

    assert "## UI Acceptance Criteria" in spec or "UI Acceptance Criteria" in spec
    assert "loading" in spec.lower() and "empty" in spec.lower() and "error" in spec.lower()
    assert "design dna" in spec.lower() or "personality" in spec.lower()
    assert "anti-slop" in spec.lower() or "generic dashboard" in spec.lower()

    assert "design dna" in brief.lower() or "personality" in brief.lower()
    assert "dials" in brief.lower()
    assert "anti-slop" in brief.lower()

    assert "ui acceptance" in specify.lower() or "design intelligence" in specify.lower()
    assert "design_context" in spx_ui or "UI Acceptance Criteria" in spx_ui


def test_quick_requires_design_before_code_loop() -> None:
    quick = _rendered_command("quick")
    packet = _read("templates/command-references/quick/packetized-work.md")
    spx = _read("templates/advanced-skills/spx-quick/SKILL.md")
    combined = "\n".join([quick, packet, spx]).lower()

    assert "design-before-code" in combined or "quick design loop" in combined
    assert "analyze current ui" in combined
    assert "identify" in combined and "issue" in combined
    assert "propose" in combined
    assert "visual" in combined and ("review" in combined or "check" in combined)
    assert "do not jump" in combined or "bare code edits" in combined


def test_debug_classifies_visual_ux_and_taste_issues() -> None:
    debug = _rendered_command("debug")
    repro = _read("templates/command-references/debug/reproduction-and-evidence.md")
    spx = _read("templates/advanced-skills/spx-debug/SKILL.md")
    combined = "\n".join([debug, repro, spx]).lower()

    assert "visual/layout" in combined
    assert "ux" in combined
    assert "taste" in combined or "generic-look" in combined
    assert "spacing" in combined or "alignment" in combined or "overflow" in combined
    assert "design-aware" in combined or "design intelligence" in combined


def test_implement_and_review_bind_design_system_and_anti_slop() -> None:
    implement = _rendered_command("implement")
    review = _rendered_command("review")
    spx_impl = _read("templates/advanced-skills/spx-implement/SKILL.md")
    spx_review = _read("templates/advanced-skills/spx-review/SKILL.md")
    combined = "\n".join([implement, review, spx_impl, spx_review]).lower()

    assert "design intelligence" in combined or "ui implementation rules" in combined
    assert "anti-slop" in combined or "anti_slop" in combined
    assert "design.md" in combined
    assert "visual hierarchy" in combined or "hierarchy" in combined
    assert "bootstrap" in combined
    assert "structure_snapshot" in combined
    assert "pending-human-review" in combined


def test_design_template_documents_personality_and_dials() -> None:
    design = _read("templates/design-template.md")
    lowered = design.lower()
    assert "design personality" in lowered or "design dna" in lowered
    assert "variance" in lowered and "motion" in lowered and "density" in lowered
    assert "anti-patterns" in lowered
    assert "bootstrap" in lowered


def test_passive_ui_skill_surfaces_design_intelligence() -> None:
    skill = _read("templates/passive-skills/spec-kit-ui-design/SKILL.md")
    lowered = skill.lower()
    assert "design intelligence" in lowered
    assert "design-before-code" in lowered or "quick" in lowered
    assert "visual/layout" in lowered or "taste" in lowered
    assert "design_context" in skill or "design context" in lowered


def test_approval_authority_not_bypassed() -> None:
    classic = read_template(
        "templates/command-partials/common/design-intelligence.md"
    )
    advanced = UI_GATE.read_text(encoding="utf-8")
    for content in (classic, advanced):
        lowered = content.lower()
        assert "approve" in lowered or "approval" in lowered
        # Must not invent parallel root product tree as required path
        assert (
            "root `.design/`" not in lowered
            or "no parallel" in lowered
            or "not a parallel" in lowered
            or "parallel root" in lowered and ("not" in lowered or "never" in lowered)
        )
    assert re.search(
        r"not a new|no `sp-design-intelligence`|not a new mainline",
        classic.lower(),
    )
    assert "bootstrap" in classic.lower() or "bootstrap" in advanced.lower()


def test_handoff_template_design_context_is_json_object() -> None:
    handoff = json.loads(_read("templates/discussion-handoff-template.json"))
    ctx = handoff["discussion_decision_digest"]["design_context"]
    assert isinstance(ctx, dict)
    assert ctx.get("ui_involved") is False
    assert ctx["dials"]["variance"] is None
    assert isinstance(ctx["reference_products"], list)
    assert isinstance(ctx["anti_slop_locks"], list)


def test_design_intelligence_engine_evidence_system_implementation() -> None:
    classic = read_template(
        "templates/command-partials/common/design-intelligence.md"
    )
    advanced = UI_GATE.read_text(encoding="utf-8")
    brief = _read("templates/design-brief-template.md")
    design_shell = _read("templates/command-partials/design/shell.md")
    spx_contract = _read(
        "templates/advanced-skills/spx-design/references/design-contract.md"
    )
    combined = "\n".join([classic, advanced, brief, design_shell, spx_contract]).lower()

    assert "design intelligence engine" in combined or "reverse engineering" in combined
    assert "evidence" in combined and "system" in combined and "implementation" in combined
    assert "measured" in combined
    assert "assumption" in combined
    assert "inferred" in combined or "evidence-backed-inference" in combined
    assert "ui system model" in combined or "ui system" in combined
    assert "tokens" in combined and "components" in combined and "states" in combined
    assert "pixel" in combined or "behavior layer" in combined or "engineering layer" in combined
    assert ".specify/design" in classic or "no parallel root" in classic.lower()
    assert "design evidence v1" in combined or "validate_design_evidence" in combined
    assert "## UI Evidence And System Model" in brief
    assert "ui evidence analysis" in design_shell.lower()
    assert "design-intelligence.md" in design_shell
    assert "source_gap" in classic or "source_gap" in brief


def test_specify_ui_requirements_and_quick_ui_audit() -> None:
    spec = _read("templates/spec-template.md")
    quick = _rendered_command("quick")
    packet = _read("templates/command-references/quick/packetized-work.md")
    combined_quick = "\n".join([quick, packet]).lower()

    assert "UI Requirements" in spec
    assert "layout pattern" in spec.lower() or "tokens" in spec.lower()
    assert "ui audit" in combined_quick
    assert "before → after" in combined_quick or "before->" in combined_quick or "before/after" in combined_quick or "before → after" in packet.lower() or "before → after" in combined_quick


def test_debug_ui_debug_mode_covers_interaction_states() -> None:
    debug = _rendered_command("debug")
    repro = _read("templates/command-references/debug/reproduction-and-evidence.md")
    combined = "\n".join([debug, repro]).lower()
    assert "ui debug mode" in combined or "visual debug" in combined
    assert "hover" in combined and "focus" in combined
    assert "loading" in combined and "error" in combined
