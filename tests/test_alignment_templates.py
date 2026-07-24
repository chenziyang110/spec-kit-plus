import json
import re
from pathlib import Path
from typing import get_args

from specify_cli.execution.implementation_review import (
    TaskReviewRecord,
    task_review_acceptance_errors,
)
from specify_cli.execution.packet_schema import UIFidelityLevel

import yaml
import pytest

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_TUI_TEMPLATE_PATHS = (
    "templates/commands/specify.md",
    "templates/commands/clarify.md",
    "templates/commands/explain.md",
)
ASCII_CARD_HEADER_RE = re.compile(r"(?m)^\s*\+--")
ASCII_CARD_LINE_RE = re.compile(r"(?m)^\s*\| .+\|\s*$")
ASCII_CARD_FOOTER_RE = re.compile(r"(?m)^\s*\+-{10,}\+?\s*$")
MIGRATED_COMMAND_REFERENCE_WORKFLOWS = (
    "analyze",
    "checklist",
    "clarify",
    "deep-research",
    "design",
    "discussion",
    "fast",
    "implement",
    "implement-teams",
    "map-build",
    "map-scan",
    "map-update",
    "plan",
    "prd-scan",
    "quick",
    "specify",
    "tasks",
    "debug",
)


def _workflow_reference_surface(workflow: str) -> str:
    root = PROJECT_ROOT / "templates" / "command-references" / workflow
    parts = [
        (PROJECT_ROOT / "templates" / "commands" / f"{workflow}.md").read_text(
            encoding="utf-8"
        ),
        read_template(f"templates/commands/{workflow}.md"),
    ]
    if root.is_dir():
        for ref_path in sorted(root.glob("*.md")):
            rel_path = ref_path.relative_to(PROJECT_ROOT).as_posix()
            raw_reference = ref_path.read_text(encoding="utf-8")
            rendered_reference = read_template(rel_path)
            parts.append(raw_reference)
            if rendered_reference != raw_reference:
                parts.append(rendered_reference)
    parts.append(f"## End {workflow.title()} Reference Surface\n")
    return "\n\n".join(parts)


def _read(path: str) -> str:
    for workflow in MIGRATED_COMMAND_REFERENCE_WORKFLOWS:
        if path == f"templates/commands/{workflow}.md":
            return _workflow_reference_surface(workflow)
    return read_template(path)


def _read_project_file(path: str) -> str:
    for workflow in MIGRATED_COMMAND_REFERENCE_WORKFLOWS:
        if path == f"templates/commands/{workflow}.md":
            return _workflow_reference_surface(workflow)
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _design_system_from_front_matter(content: str) -> dict:
    assert content.startswith("---\n")
    front_matter = content.split("---", 2)[1]
    parsed = yaml.safe_load(front_matter)
    assert isinstance(parsed, dict)
    design_system = parsed.get("design_system")
    assert isinstance(design_system, dict)
    return design_system


@pytest.mark.parametrize("workflow", MIGRATED_COMMAND_REFERENCE_WORKFLOWS)
def test_command_reference_files_are_reachable_and_have_required_headers(workflow):
    root = PROJECT_ROOT / "templates" / "command-references" / workflow
    command = (PROJECT_ROOT / "templates" / "commands" / f"{workflow}.md").read_text(
        encoding="utf-8"
    )
    index = (root / "INDEX.md").read_text(encoding="utf-8")
    assert "references/INDEX.md" in command

    for path in sorted(root.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        if path.name == "INDEX.md":
            assert "Trigger:" in content, path
            continue
        if path.name != "INDEX.md":
            assert content.startswith("Trigger:"), path
        assert "Trigger:" in content, path
        assert "Purpose:" in content, path
        assert "Preserved Contract:" in content, path
        if path.name != "INDEX.md":
            assert path.name in index, path


@pytest.mark.parametrize("workflow", MIGRATED_COMMAND_REFERENCE_WORKFLOWS)
def test_command_reference_coverage_ledgers_target_existing_text(workflow):
    ledger = json.loads(
        (
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "command-reference-coverage"
            / f"{workflow}.json"
        ).read_text(encoding="utf-8")
    )
    for entry in ledger["entries"]:
        target = PROJECT_ROOT / entry["target"]
        assert target.exists(), entry
        assert entry["source_excerpt"] in target.read_text(encoding="utf-8"), entry


def test_design_template_declares_v1_schema_and_required_guidance() -> None:
    content = _read("templates/design-template.md")
    design_system = _design_system_from_front_matter(content)

    assert "design_system:" in content
    assert "schema: spec-kit-design-v1" in content
    assert design_system["schema"] == "spec-kit-design-v1"
    assert design_system["status"] == "bootstrap"
    assert design_system["approval"]["status"] == "unapproved"
    assert design_system["approval"]["visual_refs"] == []
    assert set(design_system["product_context"]) == {
        "subject",
        "audience",
        "single_job",
    }
    assert set(design_system["direction_contract"]) == {
        "visual_thesis",
        "content_thesis",
        "interaction_thesis",
        "signature_element",
        "safe_system_choices",
        "creative_risks",
    }
    assert set((design_system.get("tokens") or {})) >= {
        "color",
        "spacing",
        "radius",
        "typography",
        "motion",
    }
    assert all(not entries for entries in design_system["tokens"].values())
    assert design_system.get("components") == {}
    assert "tokens:" in content
    assert "components:" in content
    assert "accessibility:" in content
    assert "## Anti-Patterns" in content
    assert "## UI QA Checklist" in content
    for generic_anchor in ("#2563eb", 'value: "8px"', 'value: "14px"', "system-ui"):
        assert generic_anchor not in content


def test_design_library_contains_owned_second_created_presets() -> None:
    presets = [
        "workbench-precision",
        "developer-tool-sharp",
        "data-dense-ops",
        "consumer-mobile-polished",
    ]

    for preset in presets:
        content = _read(f"templates/design-library/{preset}.md")
        lowered = content.lower()
        design_system = _design_system_from_front_matter(content)

        assert "schema: spec-kit-design-v1" in content
        assert design_system["schema"] == "spec-kit-design-v1"
        assert set((design_system.get("tokens") or {})) >= {"color", "spacing", "radius", "typography"}
        assert set((design_system.get("components") or {})) >= {"button", "input", "card"}
        assert "spec kit plus owned" in lowered
        assert "second-created" in lowered
        assert "do not copy external brand expression" in lowered


def test_discussion_carries_ui_design_intent_to_handoff() -> None:
    content = _read("templates/commands/discussion.md")

    assert "experience_commitments" in content
    assert "design_system_requirements" in content
    assert "design_system_status" in content
    assert "design_risk_level" in content
    assert "sp-design" in content


def test_specify_reads_design_md_for_ui_features() -> None:
    content = _read("templates/commands/specify.md")

    assert "DESIGN.md" in content
    assert "Experience Requirements" in content
    assert "design-system readiness" in content
    assert "design_system_status" in content
    assert "strong blocker" in content.lower()
    assert "soft risk" in content.lower()


def test_discussion_design_carry_forward_artifacts_are_modeled() -> None:
    command = _read("templates/commands/discussion.md")
    state = _read("templates/discussion-state-template.md")
    handoff = _read("templates/discussion-handoff-template.json")

    for field in (
        "experience_commitments",
        "design_system_requirements",
        "design_system_status",
        "design_risk_level",
    ):
        assert field in command
        assert field in state
        assert field in handoff


def test_specify_design_readiness_has_alignment_and_context_slots() -> None:
    command = _read("templates/commands/specify.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")

    assert "design-system readiness" in command
    assert "design_system_status" in alignment
    assert "design_risk_level" in alignment
    assert "Design System Readiness" in alignment
    assert "Design References and Gaps" in context
    assert "design_system_requirements" in context
    assert "design references" in context.lower()


def test_specify_ui_reference_input_uses_writable_subagent_lane() -> None:
    command = _read("templates/commands/specify.md")
    shell = _read("templates/command-partials/specify/shell.md")
    combined = f"{command}\n{shell}"

    assert "UI Reference Input" in combined
    assert "choose_ui_reference_lane_dispatch" in combined
    assert "follow the decision from `choose_ui_reference_lane_dispatch`" in combined
    assert "gated `leader-inline` fallback with explicit user approval recorded" in combined
    assert "lane_mode: ui-reference-artifact" in combined
    assert "ui-reference-notes.md" in combined
    assert "ui-brief.md" in combined
    assert "ui-target.html" in combined
    assert "approximate" in combined
    assert "matching-language" in combined
    assert "Reference-Implementation" in combined
    assert "Fidelity Requirements" in combined
    assert "read-only evidence lane" in combined
    assert "must not directly parse" in combined.lower()
    assert "safe lane" in combined.lower()
    assert "contract-ready" in combined.lower() or "contract ready" in combined.lower()
    assert "fidelity criteria" in combined.lower()
    assert "verification entry points" in combined.lower()
    assert "accepted deviations" in combined.lower()


def test_feature_ui_brief_artifacts_are_carried_by_spec_package_templates() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    state = _read("templates/workflow-state-template.md")
    required_evidence_line = next(
        line for line in state.splitlines() if line.startswith("- required_evidence:")
    )

    assert "UI Reference Processing" in spec
    assert "ui-reference-notes.md" in spec
    assert "ui-brief.md" in spec
    assert "Fidelity Requirements" in spec
    assert "Reference Object" in spec
    assert "Required Fidelity" in spec
    assert "Reference Behavior Inventory" in spec
    assert "UI Brief Carry-Forward" in alignment
    assert "ui_reference_processing_status" in alignment
    assert "UI Reference Inputs" in context
    assert "ui_reference_lane_mode" in state
    assert "ui_fidelity_mode" in state
    assert "reference source evidence" in state
    assert "fidelity criteria" in state
    assert "verification entry points" in state
    assert "difference inventory" in state
    assert "accepted deviations" in state
    assert "reference source evidence" in required_evidence_line
    assert "fidelity criteria" in required_evidence_line
    assert "verification entry points" in required_evidence_line
    assert "difference inventory" in required_evidence_line
    assert "accepted deviations" in required_evidence_line
    assert "ui_fidelity_criteria" not in required_evidence_line
    assert "real_entrypoint_ui_evidence" not in required_evidence_line
    assert "visual_comparison_or_human_review" not in required_evidence_line
    assert "deviation_log" not in required_evidence_line
    assert "visual-comparison-or-human-review" in state
    assert "ui_fidelity_criteria" not in state
    assert "real_entrypoint_ui_evidence" not in state
    assert "deviation_log" not in state


def test_plan_tasks_implement_preserve_design_quality_chain() -> None:
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")

    assert "Design System Adoption" in plan
    assert "token strategy" in plan.lower()
    assert "Design Quality Coverage" in tasks
    assert "required states" in tasks.lower()
    assert "DESIGN.md" in implement
    assert "Playwright screenshots" in implement
    assert "representative output" in implement
    assert "tests passed" in implement
    assert "sp-design" in implement


def test_plan_tasks_implement_carry_feature_ui_brief_contract() -> None:
    plan_template = _read("templates/plan-template.md")
    plan_command = _read("templates/commands/plan.md")
    tasks_template = _read("templates/tasks-template.md")
    tasks_command = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")
    worker_prompt = _read("templates/worker-prompts/implementer.md")
    tasks_template_lower = tasks_template.lower()
    tasks_command_lower = tasks_command.lower()

    assert "Feature UI Brief Adoption" in plan_template
    assert "ui-brief.md" in plan_command
    assert "Reference-Implementation" in plan_command
    assert "visual_comparison_or_human_review" in plan_command
    assert "UI Implementation Contract" in tasks_template
    assert "ui_contract" in tasks_template
    assert "shorthand aliases" not in tasks_template_lower
    assert "structure_snapshot" in tasks_template_lower
    assert "visual_capture" in tasks_template_lower
    assert "runtime_diagnostics" in tasks_template_lower
    assert "fidelity_level" in tasks_command
    assert "required_evidence" in tasks_command
    assert "reference-fidelity item" in tasks_command_lower
    assert "real-entrypoint proof" in tasks_command_lower
    assert "difference inventory" in tasks_command_lower
    assert "accepted deviations" in tasks_command_lower
    assert "ui_verification" in implement
    assert "pending-human-review" in implement
    assert "ui_contract" in worker_prompt
    assert "ui_evidence" in worker_prompt


def test_classic_fast_and_quick_cannot_bypass_ui_quality_gate() -> None:
    fast = _read("templates/commands/fast.md")
    quick = _read("templates/commands/quick.md")
    combined = f"{fast}\n{quick}"

    assert "UI Fast Gate" in fast
    assert "design_system.status: bootstrap" in fast
    assert "representative screenshot or platform" in fast
    assert "UI handling applies even without an image" in quick
    assert "capture" in quick
    assert "repair" in quick
    assert "visual/interaction acceptance" in combined


def _launcher_query(intent: str) -> str:
    return f'{{{{specify-subcmd:specify-runtime cognition query --intent {intent} --query-plan "<query_plan_json>" --format json}}}}'


def _launcher_compass(intent: str) -> str:
    return f'{{{{specify-subcmd:specify-runtime cognition compass --intent {intent} --query="$ARGUMENTS" --format json}}}}'


INLINE_CLOSEOUT_SURFACES = (
    "templates/command-partials/common/inline-project-cognition-update.md",
)


STALE_DIRECT_CLOSEOUT_COMMANDS = (
    'specify-runtime cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json',
    'specify-runtime cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json',
    'specify-runtime cognition delta append --session "$DELTA_SESSION_ID"',
)


def test_inline_project_cognition_update_uses_shared_partial() -> None:
    shared = _read("templates/command-partials/common/inline-project-cognition-update.md")
    required_planner_terms = (
        "specify-runtime cognition closeout-plan --workflow",
        "--delta-session",
        "update_mode=delta_session",
        "update_mode=payload_file",
        "unknown_path_dispositions",
        "agent_disposition",
        "blocking_known_unknown",
        "update_argv",
        "delta_append_draft.argv_prefix",
        "display-only `update_command`",
        "display-only `delta_append_command`",
        "partial_refresh_reasons",
        "adopted_paths",
        "review_paths",
        "missing_passing_verification_result",
    )
    for term in required_planner_terms:
        assert term in shared, f"inline closeout partial missing {term}"

    assert "ignored_paths" not in shared
    assert "finalizer_policy" not in shared
    assert "fields listed in `required_agent_fields`" in shared
    assert "If a field appears in `required_agent_fields`, provide live-evidence-backed content for it." in shared
    assert "Fields not listed by `required_agent_fields`, such as `known_unknowns` and `boundary`" in shared
    assert "`known_unknowns`, `confidence_notes`, `user_decisions`, and `boundary` are populated only" not in shared
    assert "populated only when live evidence supports them" in shared
    assert "Use `known_unknowns` only for blockers that make the cognition update unsafe to trust" in shared
    assert "record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as a blocking `known_unknowns` item" in shared
    assert "result_state" in shared
    assert "recorded" in shared
    assert "verification_evidence" in shared
    assert "generated_surface_notes" in shared
    assert "`agent_disposition=adoptable` is an agent accounting decision" in shared
    assert "do not route that to `sp-map-update`" in shared
    assert "Never run the `complete-refresh` or `clear-dirty` helper after `result_state=partial_refresh`" in shared

    for path in (
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ):
        content = _read(path)
        assert "rendered planner-first closeout command" in content, path
        assert "registry-owned literal `sp-*` workflow ID" in content, path
        assert "$ACTIVE_WORKFLOW" not in content, path
        for term in required_planner_terms[2:]:
            assert term in content, f"{path} missing {term}"
        assert "fields listed in `required_agent_fields`" in content, path
        assert "populated only when evidence supports them" in content, path
        assert "Use `known_unknowns` only for blockers that make the cognition update unsafe to trust" in content, path
        assert "`agent_disposition=adoptable` is an agent accounting decision" in content, path
        assert "partial_refresh_reasons" in content, path
        assert "missing_passing_verification_result" in content, path

    for path in (
        "templates/worker-prompts/implementer.md",
        "templates/worker-prompts/quick-worker.md",
        "templates/worker-prompts/debug-investigator.md",
        "templates/worker-prompts/debug-thinker.md",
    ):
        content = _read(path)
        assert "Use `known_unknowns` only for blockers that make the update unsafe to trust" in content, path
        assert "excluded unrelated dirty workspace paths in `confidence_notes`" in content, path

    common_partials = [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/command-partials/common/navigation-check.md",
    ]
    for path in common_partials:
        content = _read_project_file(path)
        assert "{{spec-kit-include: inline-project-cognition-update.md}}" not in content, path
        assert "specify-runtime cognition update --changed-path" not in content, path

    commands = [
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/implement-teams.md",
        "templates/commands/integrate.md",
        "templates/commands/review.md",
    ]
    for path in commands:
        assert "specify-runtime cognition closeout-plan --workflow" in _read(path), path

    map_update = (
        PROJECT_ROOT / "templates" / "commands" / "map-update.md"
    ).read_text(encoding="utf-8")
    assert map_update.count("specify-runtime cognition closeout-plan --workflow sp-map-update") == 1


def test_ask_command_contract_is_read_only_evidence_backed_project_qa() -> None:
    command = _read("templates/commands/ask.md")
    shell = _read("templates/command-partials/ask/shell.md")
    combined = "\n".join([command, shell])
    lowered = combined.lower()

    assert "# sp-ask" in command
    assert "Evidence-Backed Project Q&A" in shell
    assert "read-only answer with conclusion, evidence, uncertainty, and next step" in command
    assert "no project files, state, or handoff artifacts are written" in command
    assert "do not invoke it automatically" in command
    assert _launcher_compass("ask") in shell
    assert _launcher_query("ask") in shell
    assert "specify-runtime cognition query --intent ask --query-plan-file <path> --format json" in shell
    assert "specify-runtime cognition lexicon --intent ask --mode catalog --format json" in shell
    assert "only after you build a semantic intake or query plan" in shell
    assert "compass output or live evidence is ambiguous or has incomplete coverage" in shell
    assert "stale or localization-sensitive results are examples" in shell.lower()
    assert "live evidence is authoritative" in lowered
    assert "classify the question before answering" in lowered
    _assert_read_only_evidence_lane_contract(combined, "ask")
    assert "read-only evidence lanes are optional" in lowered
    for classifier in (
        "`fact`",
        "`how_to`",
        "`why`",
        "`difference`",
        "`impact`",
        "`status`",
        "`recommendation`",
        "`concept`",
        "`history`",
        "`boundary`",
    ):
        assert classifier in combined
    for forbidden in (
        "Do not edit source files",
        "Do not create `.specify/ask/`",
        "Do not write handoff files",
        "Do not run tests",
        "Do not run builds",
        "Do not run package managers",
        "Do not launch apps or servers",
        "Do not execute project CLI commands",
        "Do not invoke another `sp-*` workflow automatically",
    ):
        assert forbidden in shell
    assert "commits that are already available locally" not in lowered
    assert "git log" not in lowered
    assert "git show" not in lowered
    assert "commit history" not in lowered
    assert (
        "`history`: explain prior decisions from project files, templates, docs, generated state, "
        "memory, or project cognition."
    ) in shell


def test_design_workflow_is_not_an_implementation_workflow() -> None:
    content = _read("templates/commands/design.md") + "\n" + _read("templates/command-partials/design/shell.md")
    lowered = content.lower()

    assert "active_command: sp-design" in content
    assert "phase_mode: design-only" in content
    assert "allowed writes" in lowered
    assert "forbidden writes" in lowered
    assert "source code" in lowered
    assert "css or theme implementation files" in lowered
    assert "ask the user to approve a direction" in lowered
    assert "{{specify-subcmd:specify-runtime design lint" in lowered
    assert "write the project's own `design.md`" in lowered


def test_discussion_and_specify_share_read_only_evidence_lane_contract() -> None:
    partial = _read("templates/command-partials/common/read-only-evidence-lanes.md")
    discussion_shell = _read("templates/command-partials/discussion/shell.md")
    discussion = "\n".join([
        _read("templates/commands/discussion.md"),
        discussion_shell,
    ])
    specify = _read("templates/commands/specify.md")
    specify_raw = _read_project_file("templates/commands/specify.md")

    _assert_read_only_evidence_lane_contract(partial, "<workflow>")
    _assert_read_only_evidence_lane_contract(discussion, "discussion")
    _assert_read_only_evidence_lane_contract(specify, "specify")
    assert "{{spec-kit-include: ../command-partials/common/read-only-evidence-lanes.md}}" in specify_raw
    assert "{{spec-kit-include: ../common/read-only-evidence-lanes.md}}" in _read_project_file(
        "templates/command-partials/discussion/shell.md"
    )
    assert "{{spec-kit-include: ../common/read-only-evidence-lanes.md}}" in _read_project_file(
        "templates/command-partials/ask/shell.md"
    )
    assert "leader owns product judgment" in discussion.lower()
    assert "never for source edits or artifact writes" in specify.lower()


def test_workflow_routing_recommends_ask_before_discussion_for_read_only_questions() -> None:
    routing = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = routing.lower()

    assert "Use `sp-ask` before `sp-discussion`" in routing
    assert "{{invoke:ask}}" in routing
    assert "read-only project" in lowered
    assert "evidence from live files, templates, docs, generated" in routing
    assert "memory, or project cognition" in routing
    assert "does not write state, create" in routing
    assert "handoffs, run tests, run builds, or edit files" in routing


def test_project_cognition_gate_has_ask_specific_read_only_navigation() -> None:
    gate = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md")
    lowered = gate.lower()

    assert "For `sp-ask`" in gate
    assert 'specify-runtime cognition compass --intent ask --query="$ARGUMENTS" --format json' in gate
    assert "specify-runtime cognition query --intent ask" in gate
    assert "semantic\n  intake or query plan" in gate
    assert "compass output or live evidence is ambiguous" in gate
    assert "or has incomplete coverage" in gate
    assert "Stale or localization-sensitive cases are examples" in gate
    assert "still require that ambiguity or incomplete-coverage reason" in gate
    assert "live evidence" in lowered and "authoritative" in lowered
    assert "read-only" in lowered
    for forbidden in (
        "do not run tests",
        "run builds",
        "execute project CLI commands",
        "write files",
        "create handoffs",
        "create ask\n  state",
    ):
        assert forbidden in gate


def test_source_changing_sp_workflows_include_inline_cognition_closeout_contract() -> None:
    commands = [
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/implement-teams.md",
        "templates/commands/integrate.md",
        "templates/commands/review.md",
    ]
    for path in commands:
        content = _read(path)
        assert "specify-runtime cognition closeout-plan --workflow" in content, path
        assert "$ACTIVE_WORKFLOW" not in content, path

    shared = _read("templates/command-partials/common/inline-project-cognition-update.md")
    for term in (
        "specify-runtime cognition closeout-plan --workflow",
        "--delta-session",
        "update_mode=delta_session",
        "update_mode=payload_file",
        "unknown_path_dispositions",
        "agent_disposition",
        "blocking_known_unknown",
        "update_argv",
        "delta_append_draft.argv_prefix",
        "display-only `update_command`",
        "display-only `delta_append_command`",
    ):
        assert term in shared, f"inline closeout partial missing {term}"


def test_inline_cognition_payload_schema_names_match_worker_handoffs_and_runtime_aliases() -> None:
    shared = _read("templates/command-partials/common/inline-project-cognition-update.md")
    required_payload_fields = (
        "changed_paths",
        "behavior_surfaces",
        "generated_surfaces",
        "state_contracts",
        "verification",
        "verification_evidence",
        "known_unknowns",
        "confidence_notes",
    )
    for field in required_payload_fields:
        assert field in shared, f"inline closeout partial missing {field}"

    for field in (
        "unknown_path_dispositions",
        "agent_disposition",
        "blocking_known_unknown",
        "update_argv",
        "delta_append_draft.argv_prefix",
        "display-only `update_command`",
        "display-only `delta_append_command`",
    ):
        assert field in shared, f"inline closeout partial missing {field}"

    for path in (
        "templates/worker-prompts/quick-worker.md",
        "templates/worker-prompts/implementer.md",
        "templates/worker-prompts/debug-investigator.md",
        "templates/worker-prompts/debug-thinker.md",
    ):
        content = _read(path)
        assert "verification" in content, f"{path} missing canonical worker verification field"
        assert "generated_surfaces" in content, f"{path} missing canonical generated_surfaces field"


def test_inline_cognition_closeout_dispositions_and_no_stale_direct_commands() -> None:
    for path in INLINE_CLOSEOUT_SURFACES:
        content = _read(path)
        lowered = content.lower()
        for token in (
            "adoptable",
            "review_only",
            "ignored",
            "blocking_known_unknown",
        ):
            assert token in content, f"{path} missing disposition token {token}"

        assert "verified `adoptable` paths do not become blocking `known_unknowns`" in lowered or (
            "verified adoptable paths do not become blocking `known_unknowns`" in lowered
        ), f"{path} missing non-blocking adoptable rule"

        for stale_command in STALE_DIRECT_CLOSEOUT_COMMANDS:
            assert stale_command not in content, f"{path} reintroduced stale direct closeout command"


def test_worker_prompts_report_inline_update_payload_evidence() -> None:
    required_fields = (
        "changed_paths",
        "behavior_surfaces",
        "generated_surfaces",
        "state_contracts",
        "verification",
        "known_unknowns",
        "confidence_notes",
    )
    for path in (
        "templates/worker-prompts/quick-worker.md",
        "templates/worker-prompts/implementer.md",
        "templates/worker-prompts/debug-investigator.md",
        "templates/worker-prompts/debug-thinker.md",
    ):
        content = _read(path)
        for field in required_fields:
            assert field in content, f"{path} missing {field}"


def _assert_agent_assisted_cognition_gate(content: str, intent: str) -> None:
    assert _launcher_compass(intent) in content
    assert "specify-runtime cognition query" in content
    assert "--query-plan" in content
    assert (
        "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in content
        or "In that escalation" in content
    )
    assert "minimal_live_reads" in content
    assert "first_pass_paths" in content
    assert "coverage_diagnostics" in content
    assert "lexicon -> semantic_intake -> query" in content
    assert "query_plan" in content
    assert "semantic_intake" in content
    assert "facet coverage" in content
    assert "covered_facets" in content
    assert "missing_facets" in content
    assert "match_sources" in content


def _assert_learning_index_detail_model(content: str) -> None:
    assert "learning start --command" in content
    assert "detail-level summary" in content
    assert "show_argv" in content or "learning show" in content
    lowered = content.lower()
    assert ".specify/memory/learnings/index.md" not in lowered
    assert ".specify/memory/project-learnings.md" not in lowered
    assert ".planning/learnings/candidates.md" not in lowered
    assert "returns no candidates" not in lowered
    assert "auto-capture learning candidates" not in lowered
    assert "keep lower-signal items as candidates" not in lowered


def _extract_step_6_strategy_block(content: str) -> str:
    lowered = content.lower()
    start = lowered.find("6. select subagent dispatch for each ready batch before writing code:")
    assert start != -1
    end = lowered.find("\n7. execute implementation following the task plan:", start)
    assert end != -1
    return lowered[start:end]


def _extract_outline_step_block(content: str, step_prefix: str, next_step_prefix: str) -> str:
    start = content.find(step_prefix)
    assert start != -1
    end = content.find(next_step_prefix, start)
    assert end != -1
    return content[start:end]


def _assert_contains_any(text: str, *needles: str) -> None:
    assert any(needle in text for needle in needles), f"Expected one of: {needles}"


MAP_UPDATE_FIRST_POLICY = (
    "use map-update for ordinary existing-baseline gaps. use map-scan -> map-build "
    "only for brownfield first/missing/unusable baseline, schema failure, schema v1 or old "
    "broad-schema rebuild-required readiness, zero active-generation path_index rows outside "
    "greenfield_empty, missing or invalid alias_index, explicit_rebuild_requested, or "
    "baseline_identity_invalid"
)

STALE_MAP_MAINTENANCE_POLICY_PHRASES = (
    "for blocked, stale, missing, or incomplete references",
    "path-index-" + "incomplete",
    "unadoptable " + "coverage gaps",
    "blocked by " + "unadoptable",
    "unadoptable " + "path-index gaps",
    "map " + "repair",
    "first-baseline " + "map " + "repair",
    "user explicitly requested " + "map " + "repair",
    "reported map-maintenance action as follow-up " + "unless",
    "when the user wants " + "map " + "repair",
    "missing or " + "stale",
    "follow-up map maintenance when " + "useful",
    "recommend sp-map-update or " + "sp-map-scan -> sp-map-build",
    "recommend map-update or " + "map-scan -> map-build",
    "user wants " + "repair",
    "the user wants " + "repair",
    "path-index-" + "incomplete",
    "path-index " + "incomplete",
    "unadoptable " + "coverage gaps",
    "{{invoke:map-scan}} -> {{invoke:map-build}} or "
    + "{{invoke:map-update}} as "
    + "appropriate",
)


def _normalize_policy_text(text: str) -> str:
    return " ".join(text.lower().replace("`", "").split())


def _assert_no_stale_map_policy_phrases(content: str, label: str) -> None:
    normalized = _normalize_policy_text(content)
    for phrase in STALE_MAP_MAINTENANCE_POLICY_PHRASES:
        assert phrase not in normalized, f"{label} contains stale phrase: {phrase}"


TASK7_GREENFIELD_POLICY_PHRASE = (
    "do not recommend map-scan -> map-build solely because the graph has no paths"
)

TASK7_BROWNFIELD_REBUILD_PHRASE = (
    "brownfield first/missing/unusable baseline, schema failure, schema v1 or old "
    "broad-schema rebuild-required readiness, zero active-generation path_index rows outside "
    "greenfield_empty, missing or invalid alias_index, explicit_rebuild_requested, or "
    "baseline_identity_invalid"
)

TASK7_GREENFIELD_POLICY_SURFACES = {
    "base integration": "src/specify_cli/integrations/base.py",
    "cursor-agent integration": "src/specify_cli/integrations/cursor_agent/__init__.py",
    "context loading gradient": "templates/command-partials/common/context-loading-gradient.md",
    "planning context loading gradient": "templates/command-partials/common/planning-context-loading-gradient.md",
    "navigation check": "templates/command-partials/common/navigation-check.md",
    "senior consequence gate": "templates/command-partials/common/senior-consequence-analysis-gate.md",
    "project cognition gate": "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    "workflow routing": "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
}

TASK7_MAP_POLICY_LABELS = {
    "base integration",
    "cursor-agent integration",
    "context loading gradient",
    "planning context loading gradient",
    "navigation check",
    "senior consequence gate",
    "project cognition gate",
    "workflow routing",
}

LEGACY_MAP_POLICY_ALLOWLIST = {
    "README",
    "quickstart",
    "project handbook",
    "project handbook template",
    "constitution template",
    "constitution product profile",
    "constitution shell",
    "constitution command",
}


def _assert_task7_greenfield_policy_surface(content: str, label: str) -> None:
    lowered = content.lower()
    normalized = _normalize_policy_text(content)

    assert "baseline_kind=greenfield_empty" in normalized, label
    assert TASK7_GREENFIELD_POLICY_PHRASE in lowered, label
    assert "brownfield first/missing/unusable baseline" in normalized, label
    assert "outside greenfield_empty" in normalized, label
    assert TASK7_BROWNFIELD_REBUILD_PHRASE in normalized, label

    for stale_branch in (
        "`greenfield_empty` ->",
        "if readiness is `greenfield_empty`",
        "`greenfield_empty` continues",
        "if cognition freshness is `greenfield_empty`",
        "freshness is `greenfield_empty`",
    ):
        assert stale_branch not in lowered, f"{label} treats baseline_kind as readiness/freshness"


def _assert_task7_brownfield_rebuild_policy(content: str, label: str) -> None:
    normalized = _normalize_policy_text(content)
    assert "brownfield first/missing/unusable baseline" in normalized, label
    assert "outside greenfield_empty" in normalized, label
    assert TASK7_BROWNFIELD_REBUILD_PHRASE in normalized, label


def _extract_matching_lines(content: str, *needles: str, context: int = 0) -> str:
    lines = content.splitlines()
    selected: set[int] = set()
    lowered_needles = tuple(needle.lower() for needle in needles)
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(needle in lowered for needle in lowered_needles):
            start = max(0, index - context)
            end = min(len(lines), index + context + 1)
            selected.update(range(start, end))
    return "\n".join(lines[index] for index in sorted(selected))


def _extract_section(content: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^{re.escape(heading)}\s*$.*?(?=^##\s+|\Z)",
    )
    match = pattern.search(content)
    assert match is not None, heading
    return match.group(0)


def _extract_markdown_heading_section(content: str, heading: str) -> str:
    level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(
        rf"(?ms)^{re.escape(heading)}\s*$.*?(?=^#{{1,{level}}}\s+|\Z)",
    )
    match = pattern.search(content)
    assert match is not None, heading
    return match.group(0)


def _assert_map_update_first_policy(content: str) -> None:
    normalized = _normalize_policy_text(content)
    assert "map-update" in normalized
    assert "ordinary existing-baseline gaps" in normalized
    assert (
        "use map-scan -> map-build only" in normalized
        or "recommend map-scan followed by map-build only" in normalized
        or "use /sp-map-scan -> /sp-map-build only" in normalized
        or "use /sp-map-scan followed by /sp-map-build only" in normalized
    )
    assert (
        "brownfield first/missing/unusable baseline" in normalized
        or "first/missing/unusable baseline" in normalized
        or "first baseline" in normalized
    )
    for condition in (
        "schema failure",
        "zero active-generation path_index rows",
        "explicit_rebuild_requested",
        "baseline_identity_invalid",
    ):
        assert condition in normalized


def _assert_subagent_dispatch_contract(text: str, command_name: str) -> None:
    assert f'choose_subagent_dispatch(command_name="{command_name}"' in text
    lowered = text.lower()
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "subagent-blocked" in lowered
    assert "native-subagents" in lowered


def _assert_read_only_evidence_lane_contract(text: str, command_name: str) -> None:
    assert f'choose_evidence_lane_dispatch(command_name="{command_name}"' in text
    lowered = text.lower()
    assert "lane_mode: read-only-evidence" in lowered
    assert "structured_result: evidence_packet" in lowered
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in lowered
    assert "execution_surface: leader-inline | native-subagents | none" in lowered
    assert "file reads" in lowered
    assert "project cognition" in lowered
    assert "forbidden delegated operations" in lowered
    assert "file writes" in lowered
    assert "project cli commands" in lowered
    assert "parent workflow owns judgment" in lowered


def _assert_adaptive_plan_tasks_contract(text: str, command_name: str) -> None:
    assert f'choose_subagent_dispatch(command_name="{command_name}"' in text
    lowered = text.lower()
    assert "execution_model: adaptive" in lowered
    assert "execution_mode: light | standard | heavy" in lowered
    assert "workflow_status: ready | blocked" in lowered
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in lowered
    assert "execution_surface: leader-inline | native-subagents | none" in lowered
    assert "capability_degraded: false | true" in lowered
    assert "blocked_reason: required when blocked" in lowered
    assert "managed-team fallback is not part" in lowered
    assert "execution_model: subagent-mandatory" not in lowered


def _assert_complexity_based_debug_contract(text: str) -> None:
    lowered = text.lower()
    assert 'choose_subagent_dispatch(command_name="debug"' in text
    assert "execution_model: leader-inline | subagent-assisted | blocked" in lowered
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in lowered
    assert "execution_surface: leader-inline | native-subagents | none" in lowered
    assert "subagent-blocked" in lowered
    assert "execution_surface: none" in lowered
    assert "execution_model: subagent-mandatory" not in lowered


def _assert_default_handoff_contract(content: str, expected_fragment: str) -> None:
    match = re.search(r"(?m)^  default_handoff: (?P<value>.+)$", content)
    assert match is not None
    handoff = match.group("value")
    assert expected_fragment in handoff
    assert "{{invoke:" not in handoff


def _assert_reference_evidence_contract(text: str) -> None:
    lowered = text.lower()
    assert "active_profile" in text
    assert "required_evidence" in text
    assert "Reference-Implementation" in text
    assert "reference source evidence" in lowered
    assert "fidelity criteria" in lowered
    assert "difference inventory" in lowered
    assert "accepted deviations" in lowered
    assert "verification entry points" in lowered


def _assert_must_preserve_ledger_contract(content: str) -> None:
    lowered = content.lower()
    assert "must-preserve ledger" in lowered
    assert "mp-*" in lowered or "mp-###" in lowered
    assert "coverage_status" in content
    assert "planning_gate_status" in content
    assert "hard_unknown_count" in content
    assert "open_conflict_count" in content
    assert "conflict blocker" in lowered or ("block" in lowered and "conflict" in lowered)


def _assert_senior_consequence_gate_contract(content: str) -> None:
    lowered = content.lower()
    assert "senior consequence analysis gate" in lowered
    assert "project cognition first" in lowered
    assert "senior consequence analysis second" in lowered
    assert "affected object map" in lowered
    assert "state-behavior matrix" in lowered
    assert "dependency impact table" in lowered
    assert "recovery and validation contract" in lowered
    assert "coverage gaps" in lowered
    assert "lifecycle operations" in lowered
    assert "running" in lowered
    assert "destructive" in lowered
    assert "shared state" in lowered
    assert "downstream consumers" in lowered
    assert "stand-down reason" in lowered


def _assert_consequence_json_contract(content: str) -> None:
    assert '"consequence_gate"' in content
    assert '"consequence_analysis"' in content
    assert '"consequence_obligations"' in content
    assert '"affected_object_map"' in content
    assert '"state_behavior_matrix"' in content
    assert '"dependency_impact"' in content
    assert '"recovery_and_validation"' in content
    assert '"coverage_gaps"' in content
    assert '"stop_and_reopen_conditions"' in content


def _extract_bash_managed_block(script: str) -> str:
    match = re.search(
        r"render_speckit_managed_block\(\)\s*\{\s*cat <<'EOF'\n(?P<block>.*?)\nEOF",
        script,
        flags=re.S,
    )
    assert match is not None
    return match.group("block")


def _extract_powershell_managed_block(script: str) -> str:
    match = re.search(
        r"function Get-SpecKitManagedBlock\b.*?@\(\s*(?P<body>.*?)\s*\)\s*-join \$Newline",
        script,
        flags=re.S,
    )
    assert match is not None
    lines = re.findall(r"'((?:''|[^'])*)'", match.group("body"))
    assert lines
    return "\n".join(line.replace("''", "'") for line in lines)


def _assert_managed_block_v2_contract(block: str) -> None:
    lowered = block.lower()

    assert "## Spec Kit Plus Managed Rules" in block
    assert "## Always-On Context" in block
    assert "project cognition and project learning are always available" in lowered
    assert "even without an active `sp-*` workflow" in lowered
    assert "when existing-system truth matters" in lowered
    assert "before broad source inspection" in lowered
    assert "narrow live reads" in lowered
    assert "learning start --command <workflow> --format json" in block
    assert "show_argv" in block
    assert ".specify/memory/learnings/INDEX.md" not in block

    assert "## Workflow Recommendations" in block
    assert "do not auto-enter an `sp-*` workflow" in lowered
    assert "unless the user invokes it" in lowered
    assert "recommend `sp-discussion`" in lowered
    assert "`sp-specify` for formal alignment" in lowered
    assert "`sp-deep-research` for feasibility proof" in lowered
    assert "`sp-debug` for root-cause diagnosis" in lowered

    assert "## Command Surface Rules" in block
    assert "{{specify-cli}} --help" in block
    assert "specify create-feature" in block
    assert ".specify/scripts/bash/create-new-feature.sh" in block
    assert ".specify/scripts/powershell/create-new-feature.ps1" in block

    assert "## Durable State" in block
    assert "prefer durable workflow state and explicit feature paths" in lowered
    assert "over branch name or chat memory" in lowered
    assert "frontstage-only deferred persistence" in lowered
    assert "do not write discussion files, counters, dirty markers, receipts, or status summaries for every user reply" in lowered
    assert "semantic checkpoints, user-triggered checkpoints/saves, compaction risk, or lifecycle transitions" in lowered
    assert "suggest `checkpoint, continue`" in lowered
    assert "prompt does not write files by itself" in lowered
    assert "project cognition freshness truthful" in lowered
    assert "store reusable lessons through project learning" in lowered

    assert "## Workflow Activation Discipline" not in block
    assert "1% chance" not in block
    assert "route before any response or action" not in lowered
    assert "## Workflow Routing" not in block
    assert "## Artifact Priority" not in block
    assert "## Brownfield Context Gate" not in block
    assert "## Project Cognition Usage" not in block
    assert "## Map Maintenance" not in block
    assert "## Delegated Execution Defaults" not in block
    assert "sp-fast" not in lowered
    assert "sp-quick" not in lowered
    assert "sp-test-scan" not in lowered
    assert "sp-test-build" not in lowered

    assert "possibly_stale" not in lowered
    assert "must_refresh_topics" not in lowered
    assert "review_topics" not in lowered
    assert "## Spec Quality Gate (`spec-lint`)" not in block

    repo_docs = "\n".join(
        [
            _read("README.md").lower(),
            _read("PROJECT-HANDBOOK.md").lower(),
            _read("templates/project-handbook-template.md").lower(),
        ]
    )
    assert "recorded refresh and ready refresh" in repo_docs
    assert "support drift" in repo_docs


def test_core_sp_templates_use_cli_progressive_learning_without_hook_gates():
    learning_layer = _read("templates/command-partials/common/learning-layer.md")
    assert "learning start --command <classic-command-name> --format json" in learning_layer
    assert "learning list --command <classic-command-name>" in learning_layer
    assert "show_argv" in learning_layer
    assert "only agent-facing Learning read surface" in learning_layer
    assert "learning capture-auto" in learning_layer
    assert ".specify/memory/learnings/INDEX.md" not in learning_layer

    command_templates = (
        "templates/commands/specify.md",
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/analyze.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/map-scan.md",
        "templates/commands/map-build.md",
    )

    for template_path in command_templates:
        content = _read(template_path)
        assert "{{specify-subcmd:hook signal-learning" not in content, (
            f"{template_path} should use direct passive learning, not signal-learning hooks"
        )
        assert "{{specify-subcmd:hook review-learning" not in content, (
            f"{template_path} should use direct passive learning, not review-learning hooks"
        )
        assert "{{specify-subcmd:hook capture-learning" not in content, (
            f"{template_path} should use direct passive learning, not capture-learning hooks"
        )
        assert "{{specify-subcmd:hook inject-learning" not in content, (
            f"{template_path} should use direct passive learning, not inject-learning hooks"
        )
        assert "learning start --command " in content
        assert "--format json" in content
        assert "--detail-level" not in content
        assert "show_argv" in content
        assert ".specify/memory/learnings/INDEX.md" not in content

    quick_content = _read("templates/commands/quick.md")
    assert "learning start --command <classic-command-name> --format json" in quick_content
    assert "{{specify-subcmd:hook review-learning --command quick" not in quick_content
    assert "{{specify-subcmd:hook capture-learning" not in quick_content
    assert ".specify/memory/learnings/INDEX.md" not in quick_content
    assert "show_argv" in quick_content

    fast_content = _read("templates/commands/fast.md")
    assert "Do not run Learning intake" in fast_content
    assert "Learning storage" in fast_content
    assert "{{specify-subcmd:learning capture --command fast ...}}" not in fast_content


def test_owned_workflow_templates_use_cli_learning_reflex() -> None:
    owned_workflow_templates = (
        "templates/commands/specify.md",
        "templates/commands/clarify.md",
        "templates/commands/constitution.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/analyze.md",
        "templates/commands/checklist.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/quick.md",
        "templates/commands/map-scan.md",
        "templates/commands/map-build.md",
    )

    for template_path in owned_workflow_templates:
        content = _read(template_path)
        assert ".specify/memory/constitution.md" in content
        assert "learning start" in content
        assert "show_argv" in content or "selected matching Learning" in content
        assert ".specify/memory/learnings/INDEX.md" not in content


def test_task3_owned_contract_handoffs_keep_canonical_tokens_without_invocation_placeholders() -> None:
    task3_owned_handoffs = {
        "templates/commands/analyze.md": [
            "/sp.clarify",
            "/sp.deep-research",
            "/sp.plan",
            "/sp.tasks",
            "/sp.debug",
            "/sp.implement",
        ],
        "templates/commands/auto.md": ["`next_command`", "/sp-auto"],
        "templates/commands/plan.md": ["/sp.tasks", "/sp.checklist"],
        "templates/commands/quick.md": ["/sp.specify"],
        "templates/commands/specify.md": ["/sp.plan", "/sp.clarify", "/sp.deep-research"],
        "templates/commands/tasks.md": ["/sp.analyze", "/sp.implement"],
    }

    assert len(task3_owned_handoffs) == 6

    for template_path, expected_fragments in task3_owned_handoffs.items():
        content = _read(template_path)
        for expected_fragment in expected_fragments:
            _assert_default_handoff_contract(content, expected_fragment)


def test_plan_tasks_frontmatter_outputs_are_conditional_for_adaptive_modes() -> None:
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")

    assert (
        "primary_outputs: 'Canonical agent-only `plan-contract.json` plus project-facing "
        "`plan.md`; `research.md`, `quickstart.md`, `data-model.md`, and `contracts/` only "
        "when their triggers are present; planning lane records only when delegated lanes are "
        "used. `workflow-state.md` remains resume state rather than phase handoff truth.'"
    ) in plan
    assert (
        "primary_outputs: '`FEATURE_DIR/task-index.json` as the canonical task graph for "
        "standard/heavy or any UI-bearing work plus rendered `tasks.md`; light non-UI "
        "leader-direct work may use only `tasks.md`. `handoff-to-tasks.json` is a compact agent "
        "transition when compatibility requires it. Worker packets are compiled just in time by "
        "`sp-implement`; task-generation lane records exist only when lanes were actually delegated.'"
    ) in tasks


def test_project_learning_skill_documents_direct_learning_helpers_not_hook_gates():
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md")

    assert "Consume With Progressive Disclosure" in content
    assert "learning start" in content
    assert "learning list" in content
    assert "learning show" in content or "show_argv" in content
    assert "learning capture-auto" in content
    assert "{{specify-subcmd:hook signal-learning" not in content
    assert "{{specify-subcmd:hook review-learning" not in content
    assert "{{specify-subcmd:hook capture-learning" not in content
    assert "{{specify-subcmd:hook inject-learning" not in content
    assert "tooling_trap" in content
    assert "map_coverage_gap" in content
    assert "Do not promote during a read command" in content


def _assert_discussion_advisor_upgrade_contract(content: str) -> None:
    lowered = content.lower()

    assert "Truth Pass" in content
    assert "truth pass" in lowered
    assert "verified_project_facts" in content
    assert "open_assumptions" in content
    assert "evidence_checked" in content
    assert "advice_confidence" in content
    assert "Boss-Friendly Advisor Response" in content
    assert "judgment" in lowered
    assert "evidence" in lowered
    assert "risk" in lowered
    assert "recommendation" in lowered
    assert "next discussion" in lowered
    assert "Discussion Compass" in content
    assert "discussion_compass_status" in content
    assert "current_decision_frame" in content
    assert "confirmed_decisions" in content
    assert "changed_recommendations" in content
    assert "next_discussion_paths" in content
    assert "Anti-Toothpaste Protocol" in content
    assert "show the map" in lowered
    assert "ask only when user judgment is genuinely required" in lowered
    assert "do not recommend implementation work before the relevant truth pass" in lowered


def test_discussion_command_contract_is_pre_spec_and_resumable() -> None:
    content = _read_project_file("templates/commands/discussion.md")
    lowered = content.lower()

    assert "sp-discussion" in content
    assert "senior technical expert" in lowered
    assert "senior product manager" in lowered
    assert "senior ui and interaction designer" in lowered
    assert "15 years" in content
    assert "ui-interaction-discussion" in content
    assert "ascii sketches" in lowered
    assert ".specify/discussions/<slug>/" in content
    assert "discussion-state.json" in content
    assert "discussion-state.md" in content
    assert "discussion-log.jsonl" in content
    assert "requirements.md" in content
    assert "technical-options.md" in content
    assert "project-context.md" in content
    assert "open-questions.md" in content
    assert "handoff-to-specify.json" in content
    assert "active | blocked | handoff-ready | completed | abandoned" in content
    assert "multiple incomplete discussions" in lowered
    assert "updated_at" in content
    assert "do not create feature branches" in lowered
    assert "do not edit source code" in lowered
    assert "do not edit source code or tests" in lowered
    assert "do not automatically invoke or route" in lowered
    assert "explicit user" in lowered
    assert "{{spec-kit-include: ../command-partials/discussion/shell.md}}" in content
    _assert_discussion_advisor_upgrade_contract(content)


def test_discussion_command_locks_context_boundary_before_technicalization() -> None:
    content = _read_project_file("templates/commands/discussion.md")
    lowered = content.lower()

    assert "senior product manager" in lowered
    assert "senior technical expert" in lowered
    assert "context-grounding" in content
    assert "technical-options" in content
    assert "handoff assessment" in content.lower()
    assert "context_boundary" in content
    assert "implementation_target" in content
    assert "quality_gate" in content
    assert "continue-discussion" in content
    assert "split-plan.md" not in content


def test_discussion_staged_cognition_gate_and_technical_options_contract() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "product framing may begin before project cognition" in lowered
    assert "forbidden before the cognition gate" in lowered
    assert ".specify/project-cognition/status.json" in content
    assert "specify-runtime cognition compass --intent discussion" in content
    assert "specify-runtime cognition query --query-plan" in content
    assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in content
    assert "specify-runtime cognition query --intent plan" not in content
    assert "Question Evidence Gate" in content
    assert "Turn Classifier" in content
    assert "Cognition Advisory, Code Authority" in content
    assert "runtime truth" not in lowered
    assert "live repository" in lowered
    assert "readiness=blocked" in content
    assert ".specify/project-cognition/slices/change.json" not in content
    assert "clearly greenfield" in lowered
    assert "source-code reads" in lowered
    assert "technical options board" in lowered
    assert "user-intent-aligned path" in lowered
    assert "architecture-correct path" in lowered
    assert "expansion-ready path" in lowered
    assert "minimal viable path" not in lowered
    assert "scope reduction requires user confirmation" in lowered
    assert "2-3" in content


def test_discussion_requires_truth_pass_before_project_specific_advice() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "## Truth Pass" in content
    assert "current project behavior" in lowered
    assert "existing capability reuse" in lowered
    assert "cross-cli propagation" in lowered
    assert "compatibility, lifecycle, state, security, or downstream workflow risk" in lowered
    assert "before the truth pass completes" in lowered
    assert "must not name affected files, modules, apis, tests, or implementation paths as facts" in lowered
    assert "project cognition remains advisory navigation" in lowered
    assert "live repository evidence proves current project behavior" in lowered


def test_discussion_uses_boss_friendly_advisor_response_and_compass() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "## Boss-Friendly Advisor Response" in content
    assert "the first sentence should be understandable to a non-technical owner" in lowered
    assert "use the unified frontstage reply contract instead of fixed visible headings" in lowered
    assert "put the decision-level meaning or recommended direction first" in lowered
    assert "ground the reason in verified project truth" in lowered
    assert "mention risk or trade-off only when it changes the decision" in lowered
    assert "state the default next move and the override path" in lowered
    assert "do not expose a canned response format to the user" in lowered
    assert "judgment:" not in lowered
    assert "## Discussion Compass" in content
    assert "what are we solving now" in lowered
    assert "what has been confirmed" in lowered
    assert "what changed from earlier thinking" in lowered
    assert "what remains undecided" in lowered
    assert "what is the current recommended direction" in lowered
    assert "where we are" in lowered


def test_discussion_anti_toothpaste_protocol_maps_adjacent_decisions() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "## Anti-Toothpaste Protocol" in content
    assert "literal issue the user raised" in lowered
    assert "deeper decision or risk behind it" in lowered
    assert "adjacent product, technical, workflow, or verification implications" in lowered
    assert "which items can be discussed together" in lowered
    assert "which item requires a clear user decision" in lowered
    assert "recommended order for the next discussion steps" in lowered
    assert 'the rule is not "ask many questions."' in lowered
    assert "show the map" in lowered
    assert "ask only when user judgment is genuinely required" in lowered


def test_discussion_reply_contract_is_adaptive_and_high_throughput() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    combined = "\n".join([content, shell, state])
    lowered = combined.lower()

    assert "## Adaptive Reply Contract" in content
    assert "frontstage_reply_contract: unified" in state
    assert "reply_shape_id" not in combined
    assert "fixed response format contract" not in lowered
    assert "use the section labels in the listed order" not in lowered
    assert "do not choose among named answer templates" in lowered
    assert "fixed cards" in lowered
    assert "agent controls heading names" in lowered
    assert "no visible section title is mandatory" in lowered
    assert "high-throughput collaborative brief" in lowered
    assert "frontstage / backstage separation" in lowered
    assert "visible conversation" in lowered
    assert "state accounting backstage" in lowered
    assert "continue by default" in lowered
    assert "do not ask for continuation" in lowered
    assert "do not persist every turn" in lowered
    assert "checkpoint persistence" in lowered
    assert "surface file paths and state updates only" in lowered
    assert "recommendation-first is not questionless" in lowered
    assert "ask only when user judgment is genuinely required" in lowered

    required_lifecycle_coverage = (
        "context intake covers",
        "product framing covers",
        "context grounding covers",
        "technical options compare",
        "readiness summary covers",
        "ui interaction discussion covers",
        "pre-handoff readiness covers",
        "draft handoff review covers",
        "handoff-ready closeout covers",
        "blocked or evidence-conflict replies",
    )
    for item in required_lifecycle_coverage:
        assert item in lowered

    for state_term in (
        "lifecycle_phase",
        "explore | ground | decide | prepare | review | ready | consumed | closed",
        "DiscussionTurnPacket",
    ):
        assert state_term in state

    required_visible_parts = (
        "recommended direction",
        "plain-language reason",
        "usable draft",
        "default next step",
        "override path",
        "frontstage reply gate",
        "Next-Step Content Rule",
        "status receipt",
        "readiness checklist",
        "default next action",
        "first-pass content",
        "handoff assessment preview",
        "decision requested",
        "recommended route",
        "scope to approve",
        "Excluded Scope",
        "readiness checks",
        "allowed approval",
        "handoff-ready closeout",
        "target boundary",
        "must-preserve coverage",
        "quality gate state",
        "downstream consumption path",
    )
    for visible_part in required_visible_parts:
        assert visible_part.lower() in lowered

    assert "do not close with only file paths, status counters, or a next command" in lowered
    assert "keep ready-summary quality checks internal" in lowered
    assert "discussion responsibility boundary" in lowered
    assert "does not own implementation planning" in lowered
    assert "do not split the work into p0/p1/p2" in lowered
    assert "migration phases" in lowered
    assert "task packets" in lowered
    assert "those belong to `sp-plan`, `sp-tasks`, or `sp-implement`" in lowered
    assert "no parallel old-backend operation" in lowered
    assert "no old-stack cutover fallback" in lowered
    assert "no alternate product path" in lowered
    assert "do not convert that rejection into a new discussion question" in lowered
    assert "database snapshots" in lowered
    assert "data-safety mechanisms" in lowered
    assert "downstream planning and implementation safety constraints" in lowered
    assert "handoff request-changes repair" in lowered
    assert "blocked_by_handoff_integrity" in lowered
    assert "the repair belongs to `sp-discussion`" in lowered
    assert "update canonical `handoff-to-specify.json`" in lowered
    assert "consumers block instead of patching upstream truth" in lowered
    assert "source_contract" in content
    assert "field-level validation errors" in content
    assert "review_digest" in content
    assert "source_files_read" not in content
    assert "planning_gate_status" in content
    assert "coverage_status" in content
    assert "soft unknowns that remain open must be carried forward explicitly" in lowered


def test_discussion_default_next_step_must_include_concrete_content() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    combined = "\n".join([content, shell])
    lowered = combined.lower()

    assert "next-step content rule" in lowered
    assert "do not end with only a promise to do the next step" in lowered
    assert "include the first-pass content in the same visible reply" in lowered
    assert "not just a future action sentence" in lowered
    assert "field-by-field review" in lowered
    assert "responsibility audit table" in lowered
    assert "keep / merge / downgrade / delete / defer" in lowered
    assert "product framing" in lowered
    assert "technical options" in lowered
    assert "readiness checklist" in lowered
    assert "handoff assessment" in lowered
    assert "blocked only when" in lowered
    assert "concrete content for the recommended next step" in shell.lower()


def test_discussion_handoff_assessment_preview_precedes_artifact_writes() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    combined = "\n".join([content, shell, state])
    lowered = combined.lower()

    assert "`prepare`" in content
    assert "prepare | review" in state
    assert "pre-handoff readiness" in lowered
    assert "without creating a separate assessment artifact" in lowered
    assert "likely verdict" in lowered
    assert "proposed handoff goal" in lowered
    assert "recommended consumer" in lowered
    assert "package scope" in lowered
    assert "excluded scope" in lowered
    assert "readiness checks" in lowered
    assert "blocking readiness checklist" in lowered
    assert "do not close with only a next-step label" in lowered
    assert "updated-artifact lists" in lowered
    assert "separate assessment" in lowered


def test_discussion_does_not_route_to_specify_before_ready_handoff_pair() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    routing = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    review = _read("templates/passive-skills/spec-kit-discussion-handoff-review/SKILL.md")
    combined = "\n".join([content, shell, routing, review])
    lowered = combined.lower()

    assert "pre-ready handoff next-step guard" in lowered
    assert "keep the visible next step inside `sp-discussion`: handoff assessment, draft handoff review, or handoff repair" in lowered
    assert "do not tell the user their next sentence should be `sp-specify`" in lowered
    assert "do not tell the user their next sentence can be `sp-specify`" in lowered
    assert "do not tell them to run or enter `sp-specify`" in lowered
    assert "before `handoff-ready`, do not describe the next consumption path as a user-invoked `sp-specify` command" in lowered
    assert "`specification-input.md`, `discussion-state.md`, and other discussion source files are not fallback handoffs" in lowered
    assert "specification-input.md` is not a substitute handoff" in lowered
    assert "the next action is `sp-discussion` handoff creation, review, or repair" in lowered
    assert "ready json contract exists" in lowered


def test_discussion_handoff_prompt_uses_executable_digest_bound_transition() -> None:
    classic = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    advanced = _read("templates/advanced-skills/spx-discussion/SKILL.md")
    closeout = _read("templates/command-references/discussion/quality-and-closeout.md")
    combined = "\n".join([classic, shell, advanced, closeout]).lower()

    assert "validate-handoff <slug> --mode draft --json" in combined
    assert "confirm-handoff <slug> --digest <review-digest> --json" in combined
    assert "mark-ready <slug> --json" in combined
    assert "a contextual confirmation such as `yes`, `ok`, or `可以`" in combined
    assert "before every final response that names `sp-specify`" in combined
    assert "do not treat an already-active discussion as a new automatic workflow entry" in combined
    assert "ready-for-contract" in combined
    assert "decide `ready-for-handoff`" not in combined


def test_managed_context_preserves_active_discussion_across_follow_up_turns() -> None:
    source = _read("src/specify_cli/__init__.py")
    bash = _read("scripts/bash/update-agent-context.sh")
    powershell = _read("scripts/powershell/update-agent-context.ps1")
    routing = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    combined = "\n".join([source, bash, powershell, routing]).lower()

    assert "continuing an already-invoked incomplete workflow is not auto-entry" in combined
    assert "before recommending `sp-specify`" in combined
    assert "not `handoff-ready`" in combined
    assert "resume `sp-discussion`" in combined


def test_discussion_readiness_summary_does_not_plan_execution_phases() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    combined = "\n".join([content, shell, state])
    lowered = combined.lower()

    assert "readiness summary" in content
    assert "readiness summary" in shell
    assert "lifecycle_phase" in state
    assert "direction is locked" in lowered
    assert "why the topic is not yet ready for handoff or downstream execution" in lowered
    assert "blocked decisions" in lowered
    assert "evidence gaps" in lowered
    assert "planning inputs to preserve" in lowered
    assert "does not create p0/p1/p2 sequences" in lowered
    assert "migration phases" in lowered
    assert "task packets" in lowered
    assert "do not ask the user to say next" in lowered
    assert "safe default discussion action" in lowered
    assert "state receipt" in lowered
    assert "status receipt" in lowered
    assert "file paths, status fields, oq ids, persistence notes, or updated-artifact lists" in lowered


def test_discussion_handoff_user_review_uses_draft_review_card() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    review = _read("templates/passive-skills/spec-kit-discussion-handoff-review/SKILL.md")
    combined = "\n".join([content, shell, state, review])
    lowered = combined.lower()

    assert "`review`" in content
    assert "review | ready" in state
    for required_content in (
        "decision requested",
        "recommended route",
        "scope to approve",
        "excluded scope",
        "readiness checks",
        "package paths",
        "approval/change-request responses",
    ):
        assert required_content in lowered
    assert "agent chooses visible labels" in lowered
    assert "do not present draft handoff review as a path receipt" in lowered
    assert "do not lead with artifact-write narration" in lowered
    assert "unrelated prompt" in lowered
    assert "is not approval" in lowered
    assert "do not use mandatory visible headings or fixed card labels" in lowered
    assert "draft handoff review card" not in lowered


def test_discussion_handoff_review_passive_skill_sets_review_standard() -> None:
    content = _read("templates/passive-skills/spec-kit-discussion-handoff-review/SKILL.md")
    lowered = content.lower()

    assert "name: spec-kit-discussion-handoff-review" in content
    assert "handoff-to-specify.json" in content
    assert "the only handoff authority" in lowered
    assert "do not require, generate, or compare a markdown companion" in lowered
    assert "named source-evidence ref" in lowered
    assert "do not sweep them by default" in lowered
    assert "approve" in content
    assert "request-changes" in content
    assert "blocked" in content
    assert "goal and in/out/deferred scope" in lowered
    assert "context boundary and implementation target" in lowered
    assert "review criteria" in lowered
    assert "agent chooses the visible headings and layout" in lowered
    assert "no fixed review card" in lowered
    assert "confirmation of an older digest" in lowered
    assert "minimum-sufficient rule" in lowered


def test_discussion_separates_human_frontstage_from_agent_backstage() -> None:
    command = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    review = _read("templates/passive-skills/spec-kit-discussion-handoff-review/SKILL.md")
    combined = "\n".join([command, shell, review])
    lowered = combined.lower()

    assert "human frontstage" in lowered
    assert "agent backstage" in lowered
    assert "written from the human's point of view" in lowered
    assert "discussionturnpacket" in lowered
    assert "do not expose typed state" in lowered
    assert "fixed visible review headings" not in lowered


def test_discussion_offers_optional_ui_interaction_stage_for_ui_requirements() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    content_lower = content.lower()
    shell_lower = shell.lower()
    state_lower = state.lower()
    ui_match = re.search(
        r"## optional ui and interaction discussion(?P<section>.*?)(?=\n## )",
        content_lower,
        re.S,
    )
    assert ui_match is not None
    ui_section = ui_match.group("section")

    assert "ui_discussion_status" in content
    assert "after functional discussion is stable" in content_lower
    assert "no explicit handoff request is active" in content_lower
    assert "assess handoff readiness first" in content_lower
    assert "only when no explicit handoff request is active" in content_lower
    assert "assess handoff readiness first" in content.split("`ui-interaction-discussion`", 1)[1].lower()
    assert "optional ui and interaction discussion" in content_lower
    assert "ui decisions block readiness" in content_lower
    assert ui_section.index("assess handoff readiness first") < ui_section.index("reopen ui")
    assert "ui_discussion_status: offered | accepted | completed | skipped | deferred" in content
    assert "senior ui and interaction designer" in content_lower
    assert "15 years" in content
    assert "ascii sketches" in content_lower
    assert "markdown is the primary carrier" in content_lower
    assert "json" in content_lower
    assert "ui_sketches_present" in content
    assert "ui_sketch_summary" in content
    assert "ui_sketch_reference" in content
    assert "not a blocking gate" in content_lower or "not a blocker" in content_lower

    assert "after functional discussion is stable" in shell_lower
    assert "no explicit handoff request is active" in shell_lower
    assert "optional ui and interaction discussion" in shell_lower
    assert "handoff assessment first" in shell_lower
    assert "ui decisions block readiness" in shell_lower
    assert "ui_discussion_status" in shell
    assert "preserve" in shell_lower
    assert "not a mandatory handoff gate" in shell_lower
    assert "ui_sketches_present" in shell
    assert "ui_sketch_summary" in shell
    assert "ui_sketch_reference" in shell_lower

    assert "current_stage:" in state
    assert "orthogonal" in state
    assert "ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred" in state
    assert "feature workflow" not in state_lower


def test_discussion_uses_lightweight_events_and_semantic_checkpoints() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    combined = "\n".join([content, shell, state])
    lowered = combined.lower()

    assert "Lightweight Recovery Log" in content
    assert "Semantic Checkpoints" in content
    assert "ordinary turns do not write local files by default" in lowered
    assert "persistence mode" in lowered
    assert "`frontstage-only`" in combined
    assert "`durable-checkpoint`" in combined
    assert "`evidence-handoff`" in combined
    assert "`lifecycle-transition`" in combined
    assert "treat an existing discussion package as a recovery surface, not a reason to write more often" in lowered
    assert "plain confirmations such as" in lowered
    assert "a user reply is not itself a save trigger" in lowered
    assert "hidden counters" in lowered
    assert "per-user-reply or per-tool-use discussion writes" in lowered
    assert "status summaries" in lowered
    assert "deferred persistence" in lowered
    assert "compaction preserve" in lowered
    assert "user-triggered checkpoint/save" in lowered
    assert "checkpoint, continue" in lowered
    assert "same visible reply" in lowered or "same reply" in lowered
    assert "evidence-handoff: delegated or source-grounded evidence must be consumed by later synthesis" in lowered
    assert (
        "save_trigger_policy: semantic-checkpoint | user-triggered-checkpoint-or-save | "
        "evidence-handoff | compaction-risk | durable-lifecycle-transition"
    ) in combined
    assert "semantic checkpoint is a durable meaning change" in lowered
    assert "turn count alone is never a save trigger" in lowered
    assert "pending_context_summary" in combined
    assert "ordinary_turn_persistence_mode" in combined
    assert "checkpoint_value_policy" in combined
    assert "checkpoint_continue_policy" in combined
    assert "do not maintain a hidden turn counter" in lowered
    assert "suppress local writes until save trigger" in lowered
    assert "hooks may remind on resume or compaction" in lowered
    assert "pending truth-pass state" in lowered
    assert "persist it to `discussion-state.md` only at semantic checkpoints or save triggers" in lowered
    assert "persist them to `open-questions.md` only when they materially change" in lowered
    assert "compaction_preserve_items" in combined
    assert "checkpoint triggers" in lowered
    assert "do not refresh all files" in lowered
    assert "requirements.md only when product requirements have changed enough to matter" in combined
    assert "technical-options.md only when options are introduced, revised, selected, or rejected" in combined
    assert (
        "project-context.md only when source-grounding evidence, truth-pass evidence, assumptions, "
        "advice confidence, or cognition coverage changes"
    ) in combined
    assert "open-questions.md only when blocking or soft unknowns materially change" in combined


def test_primary_workflows_include_senior_consequence_analysis_gate() -> None:
    for rel_path in (
        "templates/commands/discussion.md",
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/debug.md",
    ):
        _assert_senior_consequence_gate_contract(_read(rel_path))


def test_adjacent_workflows_preserve_consequence_obligations() -> None:
    for rel_path in (
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/analyze.md",
        "templates/commands/implement.md",
    ):
        content = _read(rel_path)
        lowered = content.lower()
        assert "consequence obligation" in lowered
        assert "ca-###" in lowered or "ca-*" in lowered
        assert "stop-and-reopen" in lowered
        assert "must not drop" in lowered or "cannot drop" in lowered


def test_discussion_shell_partial_summarizes_boundary_and_single_handoff_contract() -> None:
    content = _read("templates/command-partials/discussion/shell.md")
    lowered = content.lower()

    assert "adaptive question pack" in lowered
    assert "primary question" in lowered
    assert "same-topic follow-ups" in lowered
    assert "recommended option" in lowered
    assert "handoff-to-specify.json" in content
    assert "agent-only" in lowered
    assert "handoffs/<candidate_id>" not in content
    assert "split-plan.md" not in content
    assert "truth pass" in lowered
    assert "high-throughput collaborative brief" in lowered
    assert "frontstage / backstage separation" in lowered
    assert "discussion compass" in lowered
    assert "anti-toothpaste" in lowered
    assert "verified_project_facts" in content
    assert "open_assumptions" in content
    assert "evidence_checked" in content
    assert "advice_confidence" in content


def test_discussion_state_template_is_independent_from_feature_workflow_state() -> None:
    content = _read("templates/discussion-state-template.md")
    workflow_state = _read("templates/workflow-state-template.md")
    hook_state = _read_project_file("src/specify_cli/hooks/state_validation.py")
    start = hook_state.index("EXPECTED_WORKFLOW_STATE = {")
    end = hook_state.index("}\n\n\ndef validate_state_hook", start) + 1
    expected_workflow_state = hook_state[start:end]

    assert "state_surface: discussion-state" in content
    assert "active_command: sp-discussion" in content
    assert "phase_mode: discussion-only" in content
    assert "status: active | blocked | handoff-ready | completed | abandoned" in content
    assert "lifecycle_phase: explore | ground | decide | prepare | review | ready | consumed | closed" in content
    assert "orthogonal" in content
    assert "ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred" in content
    assert "updated_at:" in content
    assert "question_pack_mode: single-question | adaptive-pack | none" in content
    assert "primary_question:" in content
    assert "optional_followups:" in content
    assert "recommendation_required_for_choices: true" in content
    assert "truth_pass_status: not-needed | needed | in-progress | complete | blocked" in content
    assert "verified_project_facts:" in content
    assert "open_assumptions:" in content
    assert "evidence_checked:" in content
    assert "advice_confidence: high | medium | low | blocked | none" in content
    assert "discussion_compass_status: current | stale | missing" in content
    assert "current_decision_frame:" in content
    assert "confirmed_decisions:" in content
    assert "changed_recommendations:" in content
    assert "next_discussion_paths:" in content
    assert "## Allowed Artifact Writes" in content
    assert "discussion-state.json" in content
    assert "discussion-state.md" in content
    assert "handoff-to-specify.md" not in content
    assert "handoff_contract" in content
    assert "consumer_eligibility" in content
    assert "recommended_consumer" in content
    assert "quick_task_candidate" not in content
    assert "## Context Boundary" in content
    assert "context_boundary_status: not-started | needs-user-input | locked | blocked" in content
    assert "current_project_root:" in content
    assert "current_project_roles:" in content
    assert "target_project_root:" in content
    assert "target_project_roles:" in content
    assert "reference_sources:" in content
    assert "external_systems:" in content
    assert "boundary_blockers:" in content
    assert "## Handoff Review" in content
    assert "handoff_review_status: not-started | draft | self-reviewed | user-confirmed | blocked" in content
    assert "handoff_user_confirmed_at:" in content
    assert "handoff_blocker_reason:" in content
    assert "handoff_consumption_status: not_consumed | consumed" in content
    assert "consumed_at:" in content
    assert "consumed_by_feature_dir:" in content
    assert "handoff-to-specify.json draft after explicit user request and boundary lock" in content
    assert "mark handoff-ready only after self-review pass and user confirmation" in content
    assert "latest_event_checkpoint:" in content
    assert "last_compaction_checkpoint:" in content
    assert "latest_cognition_readiness:" in content
    assert "handoffs/*.md" not in content
    assert "handoffs/*.json" not in content
    assert "split_plan_status" not in content
    assert "active_candidate" not in content
    assert "sp-discussion" not in workflow_state
    assert '"discussion"' not in expected_workflow_state
    assert "sp-discussion" not in expected_workflow_state


def test_specify_consumes_confirmed_unified_discussion_handoff_without_repair() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "Resolve discussion handoff intake before feature creation" in content
    assert "canonical agent-only `handoff-to-specify.json`" in content
    assert "With no arguments and exactly one unconsumed `status: handoff-ready`" in content
    assert "If multiple unconsumed `handoff-ready` discussions exist" in content
    assert "SOURCE_CONTRACT" in content
    assert "SOURCE_DISCUSSION_SLUG" in content
    assert "SOURCE_HANDOFF_MD" not in content
    assert "SOURCE_HANDOFF_JSON" not in content
    assert "entry_source: sp-discussion" in content
    assert "discussion_requirement_contract" in content
    assert "consumer_eligibility" in content
    assert "sp-specify" in content
    assert "status: handoff-ready" in content
    assert "review_digest" in content
    assert "quality_gate.status: user_confirmed" in content
    assert "planning_gate_status: ready" in content
    assert "zero hard unknowns and open conflicts" in lowered
    assert "blocked_by_handoff_integrity" in content
    assert "do not require a markdown companion" in lowered
    assert "blocked_by_handoff_integrity" in lowered
    assert "not the path or slug" in lowered
    assert "Derive the feature description" in content
    assert "coverage_status" in content
    assert "planning_gate_status" in content
    assert "hard_unknown_count" in content
    assert "open_conflict_count" in content
    assert "Read supporting discussion files only through a named evidence reference" in content
    assert "specification-input.md" in content
    assert "do not reconstruct the contract from `specification-input.md`" in lowered
    assert "do not use `specification-input.md`, `discussion-state.md`, or other discussion source files as a substitute" in lowered
    assert "compile mode" in lowered
    assert "semantic_delta" in content
    assert "Do not repeat user review" in content
    assert "spec-contract.json" in content
    assert "pointer-only transition" in content
    assert "source_contract" in content
    assert "mark the source discussion consumed" in lowered


def test_quick_consumes_unified_discussion_handoff_through_checkpoint() -> None:
    content = _read("templates/commands/quick.md")
    lowered = content.lower()

    assert "resolve discussion handoff intake before quick-task execution" in lowered
    assert "discussion_requirement_contract" in content
    assert "consumer_eligibility" in content
    assert "sp-quick" in content
    assert "planning constraints" in lowered
    assert "review_digest" in content
    assert "quick_task_candidate" not in content
    assert "source_discussion_slug" in content
    assert "source refs actually read" in lowered
    assert "must_preserve" in content
    assert "reopen conditions" in lowered
    assert "bind `understanding_confirmed` to the confirmed `review_digest`" in lowered
    assert "do not repeat user confirmation" in lowered
    assert "do not require or search for a markdown companion or a quick-specific handoff" in lowered


def test_specify_preserves_discussion_decision_digest_not_only_handoff_files() -> None:
    content = _read("templates/commands/specify.md")

    assert "discussion_decision_digest" in content
    assert "decision_digest_ref" in content
    assert "locked direction" in content
    assert "rejected alternatives" in content
    assert "accepted tradeoffs" in content
    assert "experience commitments" in content
    assert "must_not_dilute" in content


def test_discussion_handoff_is_agent_facing_requirement_contract() -> None:
    content = _read("templates/commands/discussion.md")
    handoff_json = _read("templates/discussion-handoff-template.json")
    combined = "\n".join([content, handoff_json])
    lowered = combined.lower()

    assert "discussion_requirement_contract" in combined
    assert "Agent-Facing Requirement Contract" in content
    assert "target need" in lowered
    assert "constraints" in lowered
    assert "success criteria" in lowered
    assert "design direction" in lowered
    assert "optimal solution approach" in lowered
    assert "do not describe current execution or implementation progress" in lowered
    assert '"consumer_eligibility"' in handoff_json
    assert '"sp-specify"' in handoff_json
    assert '"sp-quick"' in handoff_json
    assert '"recommended_consumer"' in handoff_json
    assert '"planning_constraints"' in handoff_json
    assert '"quick_task_candidate"' not in handoff_json
    assert "do not write a" in lowered and "consumer-specific copy" in lowered
    assert "review_criteria_carried_forward" in content
    assert "technical-options.md" in content
    assert "ui_discussion" in content
    assert "ui_sketch_reference" in content
    assert "review criteria" in lowered
    assert "selected direction" in lowered
    assert "rejected_alternatives" in combined
    assert "accepted_tradeoffs" in combined
    assert "review criteria" in lowered
    assert "must_not_dilute" in content


def test_discussion_handoff_requires_must_preserve_ledger_contract() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    _assert_must_preserve_ledger_contract(content)
    assert "handoff-to-specify.json" in content
    assert "Human Confirmation" in content
    assert "review_digest" in content
    assert "source_contract" in content
    assert "Do not ask for a bare yes/no confirmation without review criteria" in content
    assert "agent-only" in lowered and "json" in lowered
    assert "id" in lowered
    assert "claim" in lowered
    assert "source" in lowered
    assert "downstream_requirement" in content
    assert "owner" in lowered
    assert "latest_resolve_phase" in content
    assert "stop_and_reopen_condition" in content
    assert "may not silently omit" in lowered


def test_discussion_handoff_exports_decision_digest_for_specify() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "discussion_decision_digest" in content
    assert "locked_direction" in content
    assert "rejected_alternatives" in content
    assert "accepted_tradeoffs" in content
    assert "experience_commitments" in content
    assert "review_criteria_carried_forward" in content
    assert "must_not_dilute" in content
    assert "technical-options.md" in content
    assert "review criteria" in lowered
    assert "must not rediscover or flatten" in lowered


def test_specify_discussion_handoff_has_coverage_and_planning_gate_split() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    _assert_must_preserve_ledger_contract(content)
    assert "entry_source: sp-discussion" in content
    assert "blocked_by_handoff_integrity" in content
    assert "complete coverage and ready planning gate" in lowered
    assert "zero hard unknowns and open conflicts" in lowered


def test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "sp-discussion" in content
    assert "rough idea" in lowered
    assert "not-yet-ready" in lowered
    assert "pre-spec" in lowered or "before formal specification" in lowered
    assert "explicit handoff" in lowered
    assert "{{invoke:discussion}}" in content
    assert "{{invoke:specify}}" in content
    assert "senior product-engineering advisor" in lowered
    assert "high-throughput senior product-engineering advisor" in lowered
    assert "visible conversation" in lowered
    assert "frontstage / backstage separation" in lowered
    assert "state accounting backstage" in lowered
    assert "checkpoint persistence" in lowered
    assert "does not persist every turn" in lowered
    assert "continues by default" in lowered
    assert "does not ask for continuation" in lowered
    assert "truth pass" in lowered
    assert "discussion compass" in lowered
    assert "proactive implication mapping" in lowered
    assert "json path or discussion slug" in lowered
    assert "exactly one unconsumed `handoff-ready` discussion" in content
    assert "before feature creation" in lowered


def test_project_cognition_gate_has_staged_discussion_gate() -> None:
    content = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md")
    lowered = content.lower()

    assert "sp-discussion" in content
    assert "product framing" in lowered
    assert "before the cognition gate" in lowered
    assert "technical options" in lowered
    assert "default project cognition intake" in lowered
    assert "minimal_live_reads" in lowered
    assert "specify-runtime cognition compass --intent discussion" in content
    assert "specify-runtime cognition query --intent discussion" in content
    assert "specify-runtime cognition compass --intent plan" not in content
    assert "specify-runtime cognition query --intent plan" not in content
    assert "use `--intent plan` from `sp-discussion`" in content
    assert "truth pass" in lowered
    assert "verified_project_facts" in content
    assert "open_assumptions" in content
    assert "evidence_checked" in content
    assert "advice_confidence" in content


def test_project_cognition_gate_reference_refresh_uses_closed_conditions() -> None:
    content = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md")
    normalized = _normalize_policy_text(content)

    assert "for blocked, stale, or incomplete references" in normalized
    assert "fall back to minimal live reads" in normalized
    assert "map-update" in normalized
    assert "localized stale coverage" in normalized
    assert "weak reference coverage" in normalized
    assert "external/manual changed-path map maintenance" in normalized
    assert "ordinary existing-baseline gaps after a usable reference baseline" in normalized
    assert "baseline_kind=greenfield_empty" in normalized
    assert "do not recommend map-scan -> map-build solely because the graph has no paths" in normalized
    assert "for brownfield missing or unusable reference baselines" in normalized
    assert "map-scan -> map-build" in normalized
    assert "reference project only for brownfield first/missing/unusable baseline" in normalized
    for condition in (
        "schema failure",
        "zero active-generation path_index rows",
        "explicit_rebuild_requested",
        "baseline_identity_invalid",
    ):
        assert condition in normalized

    assert "ordinary changed-path maintenance" not in normalized

    for phrase in STALE_MAP_MAINTENANCE_POLICY_PHRASES:
        assert phrase not in normalized

    reference_block = normalized[
        normalized.index("cross-project reference directories"):
        normalized.index("command surface discipline")
    ]
    assert "as " + "appropriate" not in reference_block


def test_task7_greenfield_guidance_surfaces_lock_policy() -> None:
    for label, path in TASK7_GREENFIELD_POLICY_SURFACES.items():
        content = _read_project_file(path) if path.startswith("src/") else _read(path)
        _assert_task7_greenfield_policy_surface(content, label)


def test_greenfield_empty_guidance_is_not_in_freshness_sections() -> None:
    for path in (
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
    ):
        content = _read(path)
        freshness = _extract_markdown_heading_section(content, "### Freshness")
        greenfield = _extract_markdown_heading_section(content, "### Greenfield Empty Baseline")

        assert "greenfield" not in freshness.lower(), path
        assert "baseline_kind=greenfield_empty" in _normalize_policy_text(greenfield), path
        assert TASK7_GREENFIELD_POLICY_PHRASE in greenfield.lower(), path


def _legacy_specify_alignment_first_contract():
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    _assert_agent_assisted_cognition_gate(content, "plan")
    assert "minimal_live_reads" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content
    assert "minimal compatibility handoff" in lowered
    assert "support-only project-map artifacts" not in lowered
    assert "WORKFLOW_STATE_FILE" in content
    assert "workflow-state.md" in content
    assert "Read `templates/workflow-state-template.md`." in content
    assert "Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known." in content
    assert "stage-state source of truth" in lowered
    assert "phase_mode: planning-only" in content
    assert "forbidden_actions" in content
    assert "Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`." in content
    assert "When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding." in content
    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:specify-runtime learning start --command specify --format json}}" in content
    assert "Required options: `--command`, `--type`, `--summary`, `--evidence`" in content
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-map/index/status.json" not in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "Treat `PROJECT-HANDBOOK.md` as the root navigation artifact" not in content
    assert "Use `Topic Map` to choose the smallest relevant topical documents" not in content
    assert "artifact-only `sp-specify` work" in lowered
    assert "record a planning advisory" in lowered
    assert ".specify/testing/" not in lowered
    assert "project cognition freshness helper" in lowered
    assert "freshness is `missing`" in lowered
    assert "freshness is `stale`" in lowered
    assert "freshness is `support_drift`" in lowered
    assert "freshness is `partial_refresh`" in lowered
    assert "recommended_next_action" in lowered
    assert "freshness is `possibly_stale`" in lowered
    assert "must_refresh_topics" in lowered
    assert "review_topics" in lowered
    assert "task-relevant coverage is insufficient" in lowered
    assert "coverage is insufficient when the touched area is named only vaguely" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "coverage-model check" in lowered
    assert "owning surfaces and truth locations" in lowered
    assert "consumer or adjacent surfaces likely to be affected" in lowered
    assert "change-propagation hotspots" in lowered
    assert "verification entry points" in lowered
    assert "known unknowns or stale evidence boundaries" in lowered

    assert "alignment.md" in content
    assert "aligned: ready for plan" in lowered
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "user's current language" in lowered
    assert "Business Goals" in content
    assert "Users & Roles" in content
    assert "Technical Constraints / Assumptions" in content
    assert "Outstanding Questions" in content
    assert "Default to concise clarification turns" in content
    assert "Do not restate the full current understanding after every answer" in content
    assert "Save the full synthesis for the alignment-ready turn" in content
    assert "Treat the shared open question block structure below as fallback-only text format guidance" in content
    assert "before generating any clarification question, confirmation, or bounded selection, apply the `sp-auto` recommended default continuation" in lowered
    assert "if that gate does not auto-resolve the question, check whether a native structured question tool is available" in lowered
    assert "when using a native structured question tool, map the same stage header plus topic label into the native header or title field" in lowered
    assert "if a native structured question tool is available, you must use it" in lowered
    assert "do not render the textual fallback block when the native tool is available" in lowered
    assert "do not self-authorize textual fallback because the question seems simple" in lowered
    assert "only fall back after the native tool is unavailable or the tool call fails" in lowered
    assert re.search(r"open (question )?blocks?", lowered)
    _assert_contains_any(lowered, "stage header", "stage title")
    _assert_contains_any(lowered, "question header", "question title")
    _assert_contains_any(lowered, "prompt", "question stem")
    _assert_contains_any(lowered, "recommendation", "recommended item", "[ recommended ]")
    _assert_contains_any(lowered, "reply instruction", "reply guidance", "response instruction")
    assert "example" in lowered
    assert "options" in lowered
    assert "question-card format" not in lowered
    assert "boxed card" not in lowered
    assert "Do not repeat the same question" in content
    assert "If the runtime exposes separate progress/commentary and final reply channels" in content
    assert "The user should see the current clarification question exactly once." in content
    assert "Use this open question block structure in the user's current language when rendering the textual fallback block" in content
    assert "Ask at most one unanswered high-impact question per message" in content
    assert "each clarification turn should contain at most one short checkpoint" in content
    assert "decompose" in lowered
    assert "proposed capability split" in lowered
    assert "default to one spec with capability decomposition when the work still belongs to one coherent feature boundary" in lowered
    assert "help the user decompose it into bounded capabilities inside the same spec first" in lowered
    assert "only escalate to separate specs or clearly phased releases when one spec would no longer be coherent to plan or test" in lowered
    assert "if the request contains 2 or more distinct deliverables, enhancements, or behavior changes that would independently change implementation or validation shape" in lowered
    assert "present the capability split before asking any detailed clarification question about one capability" in lowered
    assert "do not jump straight into a detailed gray-area question while multiple sibling capabilities are still unsplit or unprioritized" in lowered
    assert "confirm which capability should be clarified first while keeping the work in the current spec unless the user explicitly wants separate specs or phased release planning" in content
    assert "Do not spend one clarification pass collecting requirements for multiple independent capabilities." in content
    assert "If the request is already one bounded capability, say so briefly and continue inside the current spec." in content
    assert "confirmed product scope" in lowered
    assert "user-confirmed delivery sequence" in lowered
    assert "scope reduction requires user confirmation" in lowered
    assert "first-release scope" not in lowered
    assert "mvp scope" not in lowered
    assert 'choose_evidence_lane_dispatch(command_name="specify"' in content
    assert "lane_mode: read-only-evidence" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "native-subagents" in lowered
    assert "never for source edits or artifact writes" in lowered
    assert "targeted repository evidence" in lowered
    assert "user-supplied references, examples, or linked material" in lowered
    assert "high-impact ambiguity scan" in lowered
    assert "decompose it into capabilities" in lowered
    assert "Review the written `spec.md`, `alignment.md`, and `context.md`" in content
    assert "specify team" not in lowered
    assert "the starting point, not the finished requirement package" in lowered
    assert "analyze the whole feature first" in lowered
    assert "planning-ready requirement package" in lowered
    assert "Identify 3-5 planning-relevant gray areas" in content
    assert "impacted surfaces and change-propagation expectations" in content
    assert "major affected surfaces" in content
    assert "impacted surfaces and change-propagation expectations" in content
    assert "verification entry points and minimum evidence expectations" in content
    assert "known unknowns or stale evidence boundaries that could change planning safety" in content
    assert "planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria" in content
    assert "No alternative next command is valid for the current state." in content
    assert "report the single valid next path for the current state" in content
    assert "Do not emit a second alternative next command." in content
    assert "Do not present multiple downstream command options" in content
    assert "ask exactly one unresolved high-impact question per turn" in lowered
    assert "grouped questions are allowed only when the current domain is already narrowed to a local low-risk scope" in lowered
    assert "do not ask a second high-impact question before the first one is closed" in lowered
    assert "ask at most three questions in a batch" not in lowered
    assert "Make the next question build directly on the user's most recent answer" in content
    assert "rather than resetting to generic prompts" in content
    assert "vague, shallow, or contradictory" in content
    assert "targeted narrowing question, example, or recommendation" in content
    assert "Do not accept long but still ambiguous answers as sufficient." in content
    assert "Do not turn this into a freeform brainstorming workflow." in content
    assert "guided requirement discovery" in lowered
    assert "recommendation and example scaffolding" in lowered
    assert "a read-only reviewer lane MUST run before handoff" in content
    assert "a reviewer lane MUST NOT be added" in content
    assert "Review routing is condition-triggered, not preference-triggered." in content
    assert "workload justified it" not in lowered
    assert "make the next path explicit" not in lowered
    assert "current-understanding summary" in lowered
    assert "misunderstanding-correction gate" in lowered
    assert "confirm or correct the current understanding before the final handoff decision is locked." in content
    assert "Identify 3-5 planning-relevant gray areas" in content
    assert "Derive gray areas from the combination of user intent, the project cognition runtime, and targeted repository evidence" in content
    assert 'Do not use generic labels like "UX", "behavior", or "data handling"' in content
    assert "Each gray area should be captured internally with:" in content
    assert "why the decision changes implementation or test shape" in content
    assert "switch into decision-fork mode" in lowered
    assert "present 2-3 concrete options" in lowered
    assert "requirement-shaping decision" in lowered
    assert "behavior, boundary, compatibility, or acceptance proof" in lowered
    assert "do not use this mode for implementation architecture brainstorming" in lowered
    assert "desired happy-path behavior" in content
    assert "edge case or failure-path behavior" in content
    assert "compatibility, migration, or neighboring-workflow impact" in content
    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "two or three approaches" in lowered or "2-3 approaches" in lowered
    assert "semantic term" in lowered
    assert "user review" in lowered
    assert "spec-contract.json" in content
    assert "semantic_delta" in content
    assert "source_files_read" in content
    assert "discussion-log.jsonl" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
    assert "checklists/requirements.md" in content
    assert "brainstorming/handoff-to-specify.json" in content
    assert "fixed heavy discovery lifecycle" not in lowered
    assert "always execute these ten canonical `sp-specify` stages in order" not in lowered
    assert "release-decision" not in content
    assert "final-handoff-decision" not in content
    assert "intent-analyst" not in content
    assert "adversarial-reviewer" not in content
    assert "completeness-auditor" not in content
    assert "## Scenario Profile Routing" not in content
    assert "active_profile" not in content
    assert "coverage_mode" not in content
    assert "Task Classification" not in content


def test_docs_document_runtime_atlas_refresh_scope_and_workbench_boundaries() -> None:
    readme = _read_project_file("README.md")
    handbook = _read_project_file("PROJECT-HANDBOOK.md")
    readme_lowered = readme.lower()
    handbook_lowered = handbook.lower()

    assert ".specify/project-cognition/status.json" in readme_lowered
    assert "map-update" in readme_lowered
    assert "map-scan" in readme_lowered
    assert "map-build" in readme_lowered

    for lowered in (readme_lowered, handbook_lowered):
        assert "advisory project cognition index" in lowered
        assert "advisory navigation inputs" in lowered
        assert "map points, code proves" in lowered

    assert "templates/project-map/**` is retained only for legacy compatibility review" in handbook_lowered
    assert "`debug-handbook.md` - compatibility/export debug view" in handbook_lowered
    assert "`build-handbook.md` - compatibility/export build/change view" in handbook_lowered


def test_docs_explain_agent_normalization_as_agent_semantic_not_cli_tool_routing() -> None:
    required_paths = (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    )

    for path in required_paths:
        content = _read_project_file(path).lower()
        assert "agent_normalization" in content, path
        excerpt = _extract_matching_lines(content, "agent_normalization", context=3)
        assert "agent" in excerpt and "semantic" in excerpt, path
        assert "cli" in excerpt and "tool" in excerpt, path
        assert "not a route decision" in excerpt, path


def test_map_update_first_policy_is_locked_across_owned_surfaces() -> None:
    strict_surfaces = {
        "project cognition gate": _extract_matching_lines(
            _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md"),
            "use `map-update`",
            "for blocked, stale",
            "for brownfield missing or unusable reference baselines",
            context=4,
        ),
        "workflow routing": _extract_matching_lines(
            _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md"),
            "use `sp-map-update`",
            "use `sp-map-scan`",
            "only for brownfield",
            context=6,
        ),
        "README": _extract_matching_lines(
            _read_project_file("README.md"),
            "use `map-update`",
            "if the reference is blocked",
            "ordinary `sp-*` workflows",
            context=4,
        ),
        "quickstart": _extract_matching_lines(
            _read_project_file("docs/quickstart.md"),
            "use `map-update`",
            "ordinary workflows should report changed paths",
            context=4,
        ),
        "project handbook": _extract_matching_lines(
            _read_project_file("PROJECT-HANDBOOK.md"),
            "use `map-update`",
            context=3,
        ),
        "project handbook template": _extract_matching_lines(
            _read("templates/project-handbook-template.md"),
            "use `map-update`",
            context=3,
        ),
        "constitution template": _extract_matching_lines(
            _read("templates/constitution-template.md"),
            "ordinary existing-baseline gaps",
            context=4,
        ),
        "constitution product profile": _extract_matching_lines(
            _read("templates/constitution/profiles/product.yml"),
            "ordinary existing-baseline gaps",
            context=4,
        ),
        "base integration": "\n".join(
            [
                _extract_matching_lines(
                    _read_project_file("src/specify_cli/integrations/base.py"),
                    "map-update",
                    "map-scan",
                    "needs_rebuild",
                    "blocked",
                    context=3,
                ),
            ]
        ),
        "cursor-agent integration": _extract_matching_lines(
            _read_project_file("src/specify_cli/integrations/cursor_agent/__init__.py"),
            "map-update",
            "map-scan",
            context=3,
        ),
    }
    partial_surfaces = {
        "constitution shell": _read("templates/command-partials/constitution/shell.md"),
        "senior consequence gate": _read("templates/command-partials/common/senior-consequence-analysis-gate.md"),
        "context loading gradient": _read("templates/command-partials/common/context-loading-gradient.md"),
        "planning context loading gradient": _read("templates/command-partials/common/planning-context-loading-gradient.md"),
        "navigation check": _read("templates/command-partials/common/navigation-check.md"),
        "constitution command": _read("templates/commands/constitution.md"),
    }

    for label, content in strict_surfaces.items():
        try:
            _assert_map_update_first_policy(content)
            if label in TASK7_MAP_POLICY_LABELS:
                _assert_task7_brownfield_rebuild_policy(content, label)
            else:
                assert label in LEGACY_MAP_POLICY_ALLOWLIST, label
            _assert_no_stale_map_policy_phrases(content, label)
        except AssertionError as exc:
            raise AssertionError(f"{label} does not preserve map-update-first policy") from exc

    for label, content in partial_surfaces.items():
        normalized = _normalize_policy_text(content)
        assert "map-update" in normalized, label
        assert "ordinary existing-baseline" in normalized or "needs_update" in normalized, label
        if label in TASK7_MAP_POLICY_LABELS:
            _assert_task7_brownfield_rebuild_policy(content, label)
        else:
            assert label in LEGACY_MAP_POLICY_ALLOWLIST, label
            assert (
                "brownfield first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows outside greenfield_empty, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid" in normalized
                or "first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid" in normalized
            ), label
        _assert_no_stale_map_policy_phrases(content, label)


def test_templates_lock_cross_project_cognition_reference_rules() -> None:
    managed_block = _extract_bash_managed_block(_read("scripts/bash/update-agent-context.sh"))
    routing_skill = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md")
    plan_shell = _read("templates/command-partials/plan/shell.md")
    map_scan_shell = _read("templates/command-partials/map-scan/shell.md")

    combined = "\n".join([routing_skill, plan_shell, map_scan_shell])
    lowered = combined.lower()

    assert "## Always-On Context" in managed_block
    assert "project cognition query" in lowered
    assert "task-local project" in lowered
    assert "cross-project reference directories" in lowered
    assert "advisory navigation" in lowered
    assert "coverage metadata" in lowered
    assert "minimal live reads" in lowered
    assert "live repository files" in lowered
    assert "live evidence proves technical claims" in lowered
    assert "readiness is interpreted as advisory navigation" in lowered
    assert "ordinary first-read runtime contract" not in lowered
    assert "project-map" in lowered
    assert "project-map as primary truth" not in lowered
    assert "project-map primary truth" not in lowered


def _legacy_core_planning_templates_use_logical_atlas_references() -> None:
    legacy_rel_paths = [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]
    for rel_path in legacy_rel_paths:
        content = _read(rel_path)
        lowered = content.lower()
        _assert_agent_assisted_cognition_gate(content, "plan")
        assert "specify-runtime cognition query" in lowered
        assert "minimal_live_reads" in lowered
        assert "build-handbook.md" not in lowered
        assert "build-workflow-contract" not in lowered
        assert "product-and-capability-map" not in lowered
        assert "atlas.entry" not in lowered

    implement = _read("templates/commands/implement.md").lower()
    assert "specify-runtime cognition compass --intent implement" in implement
    assert "specify-runtime cognition query --query-plan" in implement
    assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in implement
    assert "query-plan" in implement
    assert "minimal_live_reads" in implement
    assert "build-handbook.md" not in implement
    assert "build-workflow-contract" not in implement
    assert "product-and-capability-map" not in implement
    assert "atlas.entry" not in implement


def test_project_map_root_templates_document_scenario_profile_contracts() -> None:
    workflows = _read("templates/project-map/root/WORKFLOWS.md").lower()
    testing = _read("templates/project-map/root/TESTING.md").lower()

    assert "scenario profile" in workflows
    assert "standard delivery" in workflows
    assert "reference-implementation" in workflows
    assert "profile routing" in workflows
    assert "sp-specify -> sp-plan -> sp-tasks -> sp-implement -> sp-review -> sp-accept" in workflows

    assert "profile-matched evidence" in testing
    assert "reference fidelity" in testing
    assert "standard delivery" in testing
    assert "reference-implementation" in testing


def test_constitution_template_uses_current_shared_context_and_reentry_contract() -> None:
    content = _read("templates/commands/constitution.md")
    shell = _read("templates/command-partials/constitution/shell.md")
    combined = f"{content}\n{shell}"
    lowered = content.lower()
    shell_lowered = shell.lower()

    assert "consume-only Learning CLI intake" in content
    assert "learning start --command constitution --format json" in content
    assert ".specify/memory/learnings/INDEX.md" not in content
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-map/index/status.json" not in content
    assert "`/sp-map-scan` followed by `/sp-map-build`" in content
    assert "workflow-state.md" in content
    assert "/sp-plan" in content
    assert "/sp-tasks" in content
    assert "/sp-analyze" in content
    assert "active_command: sp-constitution" in lowered
    assert "phase_mode: planning-only" in lowered
    assert "{{specify-subcmd:hook" not in lowered
    assert "this workflow writes only `.specify/memory/constitution.md`" in lowered
    assert "do not modify templates, command files, docs, project rules, learning files" in lowered
    assert "`feature_dir/workflow-state.md` as read-only context" in lowered
    assert "do not update or create" in lowered
    assert "pending follow-up" in lowered
    assert "highest affected downstream stage" in lowered
    assert "do not always hand off directly to `/sp-specify`" in lowered
    assert "any active `spec.md`, `plan.md`, `tasks.md`" in content
    assert "`workflow-state.md` package" in content
    assert "project rules or learnings that conflict with the amended constitution" in lowered
    assert "as pending follow-up work" in lowered
    assert "project cognition runtime truth" in lowered
    assert "mark the related project cognition compatibility/export surface for refresh" in lowered
    assert "ordinary existing-baseline" in lowered
    assert "first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`" in lowered
    assert "rewrite only `.specify/memory/constitution.md`" in shell_lowered
    assert "report pending alignment instead" in shell_lowered
    assert "not as permission to edit additional files" in shell_lowered
    for forbidden in (
        "the constitution must stay synchronized with dependent templates",
        "propagate any downstream template",
        "keep dependent templates, guidance, and lower-order project memory aligned",
        "reopen the highest affected downstream stage",
        "without updating them or flagging them",
    ):
        assert forbidden not in combined.lower()


def test_primary_tui_templates_avoid_closed_ascii_card_examples():
    for template_path in PRIMARY_TUI_TEMPLATE_PATHS:
        content = _read(template_path)

        assert not ASCII_CARD_HEADER_RE.search(content), (
            f"{template_path} still defines an ASCII card header"
        )
        assert not ASCII_CARD_LINE_RE.search(content), (
            f"{template_path} still defines right-side pipe framing"
        )
        assert not ASCII_CARD_FOOTER_RE.search(content), (
            f"{template_path} still defines an ASCII box closure"
        )


def test_generated_workflow_templates_use_launcher_backed_cognition_helpers() -> None:
    command_dir = PROJECT_ROOT / "templates" / "commands"
    offenders: list[str] = []
    for path in command_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        for bare in (
            "specify specify-runtime cognition query",
            "specify specify-runtime cognition complete-refresh",
            "specify specify-runtime cognition mark-dirty",
            "specify project-map complete-refresh",
            "specify project-map mark-dirty",
        ):
            if bare in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {bare}")
    assert offenders == []


def _legacy_plan_template_requires_alignment_report_before_planning():
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    _assert_agent_assisted_cognition_gate(content, "plan")
    assert "minimal_live_reads" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content
    assert "workflow-state.md" in content
    assert "WORKFLOW_STATE_FILE" in content
    assert "Read `templates/workflow-state-template.md`" in content
    assert "Create or resume `WORKFLOW_STATE_FILE` before substantial planning analysis." in content
    assert "phase_mode: design-only" in content
    assert "Do not implement code, edit source files, edit tests, or treat planning as implicit permission to start execution." in content
    assert "When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding." in content
    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:specify-runtime learning start --command plan --format json}}" in content
    assert "Required options: `--command`, `--type`, `--summary`, `--evidence`" in content
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-map/index/status.json" not in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "artifact-only `sp-plan` work" in lowered
    assert "record a planning advisory" in lowered
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert "alignment.md" in content
    assert ".specify/memory/constitution.md" in content
    assert "Missing alignment report" in content
    assert "Missing context artifact" in content
    assert "Force proceed with known risks" in content
    assert "Input Risks From Alignment" in content
    assert "user's current language" in lowered
    assert "Locked Decisions For Planning" in content
    assert "Outstanding Questions" in content
    assert "Planning Gate Recommendation" in content
    assert "Read `FEATURE_DIR/context.md`" in content
    assert "Read `templates/research-template.md`" in content
    assert "Treat `context.md` as the primary implementation-context artifact" in content
    assert "planning-critical unresolved items remain" in content
    assert "locked planning decisions from `alignment.md`, `context.md`, `spec.md`, and `deep-research.md`" in content
    assert "silently omitted from the generated plan artifacts" in content
    assert "`Implementation Constitution` MUST be added if any one of the following conditions is true" in content
    assert "established framework-owned boundary or adapter pattern" in content
    assert "native bridge, plugin surface, protocol seam, generated API surface" in content
    assert "generic implementation drift would violate" in lowered
    assert "canonical boundary files or examples" in content
    assert "split the work only into the supported plan lanes" in lowered
    assert "If the workload is lightweight safe, use `execution_mode: light`" in content
    assert "dispatch `one-subagent` for exactly one validated isolated planning lane" in content
    assert "or `parallel-subagents` for two or more isolated planning lanes" in content
    assert "If the workload is standard, native subagents are unavailable" in content
    assert "record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`" in content
    assert "Managed-team fallback is not part of adaptive plan/tasks dispatch." in content
    assert "if collaboration is justified" not in lowered
    assert "heuristics is true" not in lowered
    assert "## Scenario Profile Inputs" in content
    assert "Read `FEATURE_DIR/workflow-state.md` if present" in content
    assert "active_profile" in content
    assert "transition_policy" in content
    assert "Profile-Driven Implementation Constraints" in content
    assert "Reference-Implementation" in content
    assert "do not perform a second informal task classification pass" in lowered
    assert "stop and tell the operator to repair or re-run upstream scenario profile routing state before planning" in lowered
    assert "do not silently reinterpret unsupported profiles as a new planning mode" in lowered
    assert "do not use it as a substitute for a supported `active_profile`" in lowered
    _assert_adaptive_plan_tasks_contract(content, "plan")
    assert "research" in lowered
    assert "data model" in lowered
    assert "contracts" in lowered
    assert "quickstart and validation scenarios" in lowered
    assert "before final constitution and risk re-check" in lowered
    assert "before writing the consolidated implementation plan" in lowered
    assert "high-risk architectural choice -> stack/pattern/pitfall task" in content
    assert "external tool, runtime, or service dependency -> availability and fallback task" in content
    assert "Prefer official documentation, standards, and primary sources" in content
    assert "Source confidence (`verified`, `cited`, or `assumed`)" in content
    assert "`Don't hand-roll` guidance" in content
    assert "Common pitfalls, failure modes, and anti-patterns" in content
    assert "Assumptions log" in content
    assert "Validation notes" in content
    assert "Environment or dependency notes" in content
    assert "Do not present unverified claims as settled facts." in content
    assert "Prefer prescriptive recommendations over broad option dumps" in content
    assert "What does the planner need to know to produce a high-quality implementation plan" in content
    assert "Use `templates/research-template.md` as the default structure for `research.md`" in content
    assert "recommended follow-up quality check: `{{invoke:checklist}}`" in content
    assert "cognition follow-up" in lowered
    assert "artifact-only planning work" in lowered
    assert "actual source/runtime changes" in lowered
    assert "specify team" not in lowered
    assert "specify -> clarify -> plan" not in lowered


def test_plan_template_uses_adaptive_execution_modes() -> None:
    content = _read("templates/commands/plan.md")

    _assert_adaptive_plan_tasks_contract(content, "plan")
    assert "`light`: leader-inline synthesis" in content
    assert "`standard`: delegate only isolated" in content
    assert "`heavy`: use validated writable lanes" in content


def test_plan_template_records_planning_evidence_paths() -> None:
    content = _read("templates/commands/plan.md")

    assert "lane-manifest.json" in content
    assert "each lane writes one agent-only result" in content.lower()
    assert "do not require separate evidence-index and checkpoint logs" in content.lower()


def test_plan_template_requires_writable_delegated_planning_lanes() -> None:
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    assert "artifact-writing delegated planning lanes must be dispatched" in lowered
    assert "writable, execution-capable native subagent" in lowered
    assert "do not dispatch a read-only explorer, reviewer, or diagnostic lane" in lowered
    assert "allowed write scope must include the exact expected handoff path" in lowered
    assert "planning/handoffs/<lane-id>.json" in content
    assert "re-dispatch with a writable lane" in lowered


def test_adaptive_execution_partial_requires_writable_artifact_handoff_lanes() -> None:
    content = _read("templates/command-partials/common/adaptive-execution.md")
    lowered = content.lower()

    assert "artifact-writing delegated lanes must use writable" in lowered
    assert "execution-capable native subagents" in lowered
    assert "read-only explorer, reviewer, or diagnostic lane" in lowered
    assert "must include the exact expected handoff path" in lowered
    assert "re-dispatch with a writable lane" in lowered


def test_research_template_exists_and_captures_research_quality_contract():
    content = _read("templates/research-template.md")

    assert "# Research:" in content
    assert "## Summary" in content
    assert "## Decisions" in content
    assert "**Recommendation**" in content
    assert "**Rationale**" in content
    assert "**Alternatives Considered**" in content
    assert "**Source Confidence**" in content
    assert "## Standard Stack" in content
    assert "## Don't Hand-Roll" in content
    assert "## Common Pitfalls" in content
    assert "## Assumptions Log" in content
    assert "## Validation Notes" in content
    assert "## Environment / Dependency Notes" in content
    assert "## Sources" in content


def test_plan_template_carries_locked_decisions_into_plan_artifact():
    content = _read("templates/plan-template.md")
    lowered = content.lower()

    assert "## Locked Planning Decisions" in content
    assert "## Alignment Inputs" in content
    assert "### Canonical References" in content
    assert "### Input Risks From Alignment" in content
    assert "## Research Inputs" in content
    assert "## Implementation Constitution" in content
    assert "### Architecture Invariants" in content
    assert "### Boundary Ownership" in content
    assert "### Forbidden Implementation Drift" in content
    assert "### Required Implementation References" in content
    assert "### Review Focus" in content
    assert "### Standard Stack" in content
    assert "### Don't Hand-Roll" in content
    assert "### Common Pitfalls" in content
    assert "### Assumptions To Validate" in content
    assert "### Environment / Dependency Notes" in content
    assert "## Dispatch Compilation Hints" in content
    assert "### Boundary Owner" in content
    assert "### Required Packet References" in content
    assert "### Packet Validation Gates" in content
    assert "### Task-Level Quality Floor" in content
    assert "## Decision Preservation Check" in content
    assert "## Research Adoption Check" in content
    assert "cannot be silently dropped" in lowered
    assert "where it appears in the plan" in lowered
    assert "execution-rule surface" in lowered
    assert "constraint explicit" in lowered
    assert "consumed research.md" in lowered
    assert "background reading" in lowered


def _legacy_tasks_template_documents_shared_routing_before_decomposition():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    _assert_agent_assisted_cognition_gate(content, "plan")
    assert "minimal_live_reads" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content
    assert "PRODUCT-AND-CAPABILITY-MAP" not in content
    assert "WORKFLOW-SEQUENCES" not in content
    assert "MODULE-COLLABORATION" not in content
    assert "CHANGE-PROPAGATION-RISKS" not in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert "workflow-state.md" in content
    assert "WORKFLOW_STATE_FILE" in content
    assert "Read `templates/workflow-state-template.md`" in content
    assert "Create or resume `WORKFLOW_STATE_FILE` before substantial task-generation analysis." in content
    assert "phase_mode: task-generation-only" in content
    assert "Do not implement code, edit source files, edit tests, or treat task generation as permission to start execution." in content
    assert "When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding." in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "continue with live repository evidence when workflow policy allows degraded advisory navigation" in content.lower()
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert ".specify/memory/constitution.md" in content
    _assert_adaptive_plan_tasks_contract(content, "tasks")
    assert "story and phase decomposition" in lowered
    assert "dependency graph analysis" in lowered
    assert "write-set and parallel-safety analysis" in lowered
    assert "plan.md (tech stack, libraries, structure), spec.md (user stories with priorities), context.md (implementation context)" in content
    assert "alignment.md (locked decisions, outstanding questions, planning gate context)" in content
    assert "Scenario profile inputs" in content
    assert "same profile contract or active profile" in lowered
    assert "persisted first-release profile contract" in lowered
    assert "unsupported `active_profile`" in lowered
    assert "stops before decomposition" in lowered
    assert "repair/re-run upstream routing state" in lowered
    assert "preserve it only as context while shaping tasks" not in lowered
    assert "fidelity checkpoints" in lowered
    assert "before implementation batches that can materially change the reference-preserved surface" in lowered
    assert "after implementation batches that materially change" not in lowered
    assert "deviation review" in lowered
    assert "required evidence" in lowered
    assert "split work only into the supported task-generation lanes" in lowered
    assert "If the task-generation workload is lightweight safe, use `execution_mode: light`" in content
    assert "dispatch `one-subagent` for exactly one validated isolated lane" in content
    assert "or `parallel-subagents` for two or more isolated lanes" in content
    assert "If the workload is standard, native subagents are unavailable" in content
    assert "record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`" in content
    assert "Managed-team fallback is not part of adaptive plan/tasks dispatch." in content
    assert "If any design artifact required by the current scope is missing, stop and route back to `{{invoke:plan}}`." in content
    assert "Only optional artifacts may be absent without blocking task generation." in content
    assert "would benefit from them" not in lowered
    assert "Locked Planning Decisions" in content
    assert "Decision Preservation Check" in content
    assert "quickstart.md exists: extract validation scenarios" in lowered
    assert "validate decision preservation" in lowered
    assert "instead of silently dropping it" in lowered
    assert "top-level tasks should usually fit one bounded implementation slice" in lowered
    assert "roughly 10-20 minutes" in lowered
    assert "subagent can still execute the task internally through smaller 2-5 minute atomic steps" in lowered
    assert "stop decomposition once the current executable window is atomic" in lowered
    assert "leave later execution phases at the coarser story or phase level" in lowered
    assert "refinement inside the current confirmed delivery" in lowered
    assert "not delivery deferral or future work" in lowered
    assert "grouped parallelism is the default" in lowered
    assert "parallel-eligible" in lowered
    assert "batch range labels such as `t012-t021` are summaries, not executable lane identities" in lowered
    assert "lane-level execution unit" in lowered
    assert "pipeline is preferred when outputs flow linearly from one bounded lane to the next" in lowered
    assert "every pipeline stage still needs an explicit checkpoint" in lowered
    assert "classify_review_gate_policy(workload_shape)" in content
    assert "high-risk review checkpoint" in lowered
    assert "peer-review lane is available" in lowered
    assert "Planning inputs section" in content
    assert "before writing `tasks.md`" in content
    assert "before emitting canonical parallel batches and join points" in lowered
    assert "cognition follow-up" in lowered
    assert "artifact-only task generation" in lowered
    assert "actual source/runtime changes" in lowered
    assert "specify team" not in lowered


def test_tasks_template_uses_adaptive_execution_modes() -> None:
    content = _read("templates/commands/tasks.md")

    _assert_adaptive_plan_tasks_contract(content, "tasks")
    assert "`light`, `standard`, or `heavy`" in content
    assert "delegate only isolated decomposition lanes" in content
    assert "benefit exceeds handoff cost" in content


def _legacy_implement_template_wave_budget_contract():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "max_parallel_subagents = 4" in content
    assert "implement-slot-1" in content
    assert "implement-slot-4" in content
    assert "current selected wave" in lowered
    assert "at most four validated isolated lanes" in lowered
    assert "more than four dispatch-ready isolated lanes" in lowered
    assert "execute multiple waves" in lowered
    assert "launch all selected lanes in the current `parallel-subagents` wave before waiting" in lowered
    assert "whole ready parallel batch" in lowered
    assert "implement t012-t021 migrations" in lowered


def test_tasks_and_implement_templates_keep_task_review_and_handoff_system_review() -> None:
    tasks = _read("templates/commands/tasks.md")
    task_template = _read("templates/tasks-template.md")
    implement = _read("templates/commands/implement.md")
    workflow_state = _read("templates/workflow-state-template.md")
    combined = "\n".join([tasks, task_template, implement, workflow_state])
    lowered = combined.lower()

    assert "embedded implement review" in lowered
    assert "event-triggered review" in lowered
    assert "review_trigger" in combined
    assert "task lifecycle record" in lowered
    assert "task-briefs" not in combined
    assert "review-packages" not in combined
    assert "implementation-review/ledger.json" not in combined
    assert "sp-review" in combined
    assert "mandatory" in lowered


def test_implement_template_preserves_workflow_state_review_allowlist() -> None:
    implement = _read("templates/commands/implement.md")
    lowered = implement.lower()

    assert "task lifecycle record" in lowered
    assert "required refs" in lowered
    assert "event-triggered review" in lowered
    assert "must not rewrite upstream truth" in lowered
    assert "review trigger and verdict" in lowered
    assert "do not create separate task briefs, review packages, or a duplicate task ledger" in lowered


def _legacy_implement_uses_single_task_reviewer_by_default() -> None:
    content = _read("templates/commands/implement.md")

    assert ".specify/templates/worker-prompts/implementer.md" in content
    assert ".specify/templates/worker-prompts/task-reviewer.md" in content
    assert "ordinary post-task review" in content
    assert "task lifecycle record" in content
    assert "Do not create separate task briefs" in content
    assert "review packages" in content
    assert "duplicate task ledger" in content
    assert "broad diff review only when a review trigger fired" in content
    assert "pair post-implementation reviews with `.specify/templates/worker-prompts/spec-reviewer.md`" not in content


def test_task_reviewer_prompt_defines_dual_verdict_schema() -> None:
    content = _read("templates/worker-prompts/task-reviewer.md")

    assert "spec_verdict" in content
    assert "quality_verdict" in content
    assert "ui_fidelity_result" in content
    assert "final_assessment" in content
    assert "accepted_residual_risks" in content
    assert "follow_up_work" in content
    assert "controller_checks" in content
    assert "findings" in content
    assert '"plan_mandated_defects": []' in content
    assert "`category=plan_mandated_defect`" in content
    assert "Use the same finding object fields for both `findings` and `plan_mandated_defects`" in content
    assert "`plan_mandated_defects` is a separate finding source list" in content
    assert "`finding_source`: `findings`, `plan_mandated_defects`" in content
    assert "Dispositions that refer to `plan_mandated_defects`" in content
    assert "finding_source=plan_mandated_defects" in content
    assert "finding_source=findings" in content
    assert "canonical worker result path named by the lifecycle record" in content
    assert "FEATURE_DIR/worker-results/<task-id>.json" in content
    assert ".specify/teams/state/results/<request-id>.json" in content
    assert "Inline Project Cognition Handoff" not in content
    assert "changed_paths" not in content


def test_task_reviewer_first_json_example_is_runtime_parseable() -> None:
    content = _read("templates/worker-prompts/task-reviewer.md")
    match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
    assert match is not None

    example = match.group(1)
    assert " | " not in example
    payload = json.loads(example)
    record = TaskReviewRecord(**payload)

    assert record.spec_verdict == "pass"
    assert record.quality_verdict == "pass"
    assert record.ui_fidelity_result == "not_applicable"
    assert record.final_assessment == "accepted"
    assert task_review_acceptance_errors(record) == []


def test_legacy_split_reviewer_helper_snippets_are_not_default_task_review_path() -> None:
    spec_helper = _read("templates/passive-skills/subagent-driven-development/spec-reviewer-prompt.md")
    quality_helper = _read(
        "templates/passive-skills/subagent-driven-development/code-quality-reviewer-prompt.md"
    )

    for content in (spec_helper, quality_helper):
        assert "Legacy compatibility/helper snippet" in content
        assert "Ordinary `sp-implement` task review uses" in content
        assert ".specify/templates/worker-prompts/task-reviewer.md" in content
        assert "spec_verdict" in content
        assert "quality_verdict" in content

    assert "Only dispatch after spec compliance review passes" not in quality_helper


def test_plan_tasks_and_workflow_state_carry_compact_review_contract() -> None:
    combined = "\n".join(
        [
            _read("templates/commands/plan.md"),
            _read("templates/commands/tasks.md"),
            _read("templates/tasks-template.md"),
            _read("templates/workflow-state-template.md"),
            _read("templates/plan-contract-template.json"),
        ]
    )

    assert "Global Constraints" in combined
    assert "Task Interface Map" in combined
    assert "Review-Risk Notes" in combined
    assert "UI Implementation Contract Coverage" in combined
    assert "controller checks" in combined.lower()
    assert "current_task_lifecycle_ref" in combined
    assert "review_trigger" in combined
    assert "task-briefs" not in combined
    assert "review-packages" not in combined


def test_tasks_template_requires_stable_task_identity_for_embedded_repair() -> None:
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "task identity" in lowered
    assert "completed task ids are immutable" in lowered
    assert "append-only" in lowered
    assert "repair_for" in content
    assert "task-index.json" in content
    assert "lifecycle records" in content.lower()
    assert "worker-result" in lowered


def test_explain_template_documents_conservative_routing_contract():
    content = _read("templates/commands/explain.md")
    lowered = content.lower()

    assert ".specify/memory/constitution.md" in content
    _assert_subagent_dispatch_contract(content, "explain")
    assert "leader may render the explanation directly" in lowered
    assert "primary artifact reading" in lowered
    assert "supporting artifact cross-check" in lowered
    assert "before rendering the final explanation" in lowered
    assert "project cognition, touched-area state, or brownfield runtime truth" in lowered
    assert ".specify/project-cognition/status.json" in content
    assert "smallest matching slice" in lowered
    assert "handbook artifacts only when the user explicitly requests the compatibility/export surfaces themselves" in lowered
    assert "explain the architecture, cognition, or compatibility/export atlas artifact directly instead of forcing a planning-stage fallback" in lowered
    assert "verified facts, inferred relationships, important unknowns, and the next relevant cognition slice or export view" in lowered
    assert "specify team" not in lowered


def test_analyze_template_expands_to_context_and_locked_decision_drift():
    content = _read("templates/commands/analyze.md")
    lowered = content.lower()

    assert "description: Use when tasks.md exists and you need a non-destructive cross-artifact consistency and boundary-guardrail analysis before or during execution." in content
    assert "## Workflow Contract Summary" in content
    assert "This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`." in content
    assert "this command may update `workflow-state.md` to record the cleared or blocked gate result" in lowered
    assert "before, during, or after implementation revalidation" in lowered
    assert "workflow-state.md" in content
    assert "analysis-only" in lowered
    assert "`next_command: /sp.implement`" in content
    assert "when no upstream remediation is required" in lowered
    assert "`next_command: /sp.plan`" in content or "`next_command: /sp.tasks`" in content
    _assert_agent_assisted_cognition_gate(content, "implement")
    assert "minimal_live_reads" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content
    assert "PRODUCT-AND-CAPABILITY-MAP" not in content
    assert "CHANGE-ENTRYPOINTS" not in content
    assert "IMPLEMENTATION-PLAYBOOKS" not in content
    assert "CHANGE-PROPAGATION-RISKS" not in content
    assert "VERIFICATION-ROUTES" not in content
    assert "build-handbook.md" not in lowered
    assert ".specify/project-map/index/status.json" not in content
    assert "atlas.entry" not in lowered
    assert "follow-up `{{invoke:map-update}}` is useful for external map maintenance" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "spec-contract.json" in content
    assert "plan-contract.json" in content
    assert "task-index.json" in content
    assert ".specify/memory/constitution.md" in content
    assert "Consume the `specify-runtime cognition query` bundle." in content
    assert "choose the cognition intent" in lowered
    assert "--intent plan" in content
    assert "--intent implement" in content
    assert "selected_concepts" in content
    assert "rejected_concepts" in content
    assert "route_pack" in content
    assert "minimal_live_reads" in content
    assert "Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`" not in content
    assert "**From conditional context view when referenced:**" in content
    assert "Locked Decisions" in content
    assert "Locked Planning Decisions" in content
    assert "Implementation Constitution" in content
    assert "Locked decision inventory" in content
    assert "Boundary-sensitivity inventory" in content
    assert "#### F. Locked Decision Drift" in content
    assert "#### H. Boundary Guardrail Gaps" in content
    assert "boundary-sensitive implementation area" in lowered
    assert "BG1" in content
    assert "BG2" in content
    assert "BG3" in content
    assert "established framework-owned boundary or adapter pattern" in lowered
    assert "native bridge, plugin surface, protocol seam, generated api surface" in lowered
    assert "implementation guardrail tasks in `tasks.md` with no matching constitution rule in `plan.md`" in content
    assert "execution guidance fails to force pre-dispatch boundary confirmation" in content
    assert "missing `Implementation Constitution`" in content
    assert "silently weakened, deferred, or renamed" in lowered
    assert "locked decision silently dropped between artifacts" in lowered
    assert "**Locked Decision Preservation Table:**" in content
    assert "**Boundary Guardrail Table:**" in content
    assert "Signal Code" in content
    assert "| ID | Signal Code | Category | Severity | Location(s) | Summary | Recommendation |" in content
    assert "| BG1-001 | BG1 | Boundary Guardrail Gap | HIGH |" in content
    assert "| BG2-001 | BG2 | Boundary Guardrail Gap | HIGH |" in content
    assert "| BG3-001 | BG3 | Boundary Guardrail Gap | HIGH |" in content
    assert "| DP1-001 | DP1 | Dispatch Packet Gap | HIGH |" in content
    assert "| DP2-001 | DP2 | Dispatch Packet Gap | HIGH |" in content
    assert "| DP3-001 | DP3 | Dispatch Result Gap | HIGH |" in content
    assert "stable fingerprint-first finding ID" in content
    assert "keeps BG/DP values as signal codes where applicable" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content
    assert "Boundary Signal" in content
    assert "Seen In Plan Constitution?" in content
    assert "Boundary Guardrail Gap Count" in content
    assert "output exactly one `Recommended Next Command`" in content
    assert "Do not output multiple alternative next commands" in content
    assert "Closed-loop requirement" in content
    assert "complete blocker bundle" in lowered
    assert "Blocker Bundle" in content
    assert "selected/rejected concepts" in lowered
    assert "`route_pack`" in content
    assert "include every unique actionable finding" in content
    assert "`Blocker Bundle` and `workflow-state.md` MUST enumerate every blocking finding" in content
    assert "Do not hide blocking findings inside grouped summaries" in content
    assert "complete the full detection matrix before selecting the single `recommended next command`" in lowered
    assert "Stable Finding Identity" in content
    assert "fingerprint-first" in lowered
    assert "reuse the prior ID" in content
    assert "Allocate a new ID only for a genuinely new fingerprint" in content
    assert "Revalidation Attribution" in content
    assert "missed_by_previous_analyze" in content
    assert "introduced_by_remediation" in content
    assert "upstream_artifact_changed" in content
    assert "detector_scope_changed" in content
    assert "Persist attribution per new blocking finding in the `Analyze Gate` `blocker_bundle`" in content
    assert "No more than one task-layer remediation cycle is expected" in content
    assert "Do not treat repeated task/analyze loops as normal workflow" in content
    assert "Recommended Next Command" in content
    assert "### 9. Define Workflow Re-entry" in content
    assert "Recommended Re-entry" in content
    assert "If the highest invalid stage is `clarify`" in content
    assert "If the highest invalid stage is `plan`" in content
    assert "If the highest invalid stage is `tasks`" in content
    assert "If the constitution itself must change" in content
    assert "`next_command: /sp.constitution`" in content
    assert "Analyze Gate" in content
    assert "gate_status" in content
    assert "gate_cycle" in content
    assert "highest_invalid_stage" in content
    assert "blocker_bundle" in content
    assert "`blocker_bundle: [finding ID | invalid stage | status | attribution | compact summary | remediation requirement]`" in content
    assert "artifact_fingerprint_basis" in content
    assert "record its attribution on that `blocker_bundle` row" in content
    assert "If the remaining issue is execution-only, the re-entry chain MUST begin at `{{invoke:implement}}` or `{{invoke:debug}}`." in content
    assert "exact workflow re-entry path" in content


def test_analyze_template_separates_canonical_state_token_from_manual_invocation_guidance():
    content = _read("templates/commands/analyze.md")

    assert "Preserve canonical `/sp.implement` only in workflow-state fields." in content
    assert "When recommending manual implementation resumption to the user, tell them to run `{{invoke:implement}}`." in content
    assert "tell the user to run `{{invoke:implement}}` while preserving canonical `/sp.implement`" not in content
    assert "tell them to run `{{invoke:implement}}` while preserving canonical `/sp.implement`" not in content


def test_workflow_state_template_supports_analyze_gate_without_fixed_heavy_labels():
    content = _read("templates/workflow-state-template.md")
    lowered = content.lower()

    assert "## Review State" in content
    assert "last_user_reviewed_artifact_state" in content
    assert "canonical_contract_ref" in content
    assert "canonical_contract_revision" in content
    assert "semantic_delta" in content
    for stage in (
        "context-intake",
        "clarification",
        "approach-comparison",
        "section-approval",
        "artifact-writing",
        "artifact-review",
        "user-review",
    ):
        assert stage in content
    assert "fixed lifecycle state" not in lowered
    assert "release-decision" not in content
    assert "## Legacy Fixed-Heavy Compatibility Labels" not in content
    assert "final-handoff-decision" not in content
    assert "/sp.plan" in content
    assert "/sp.clarify" in content
    assert "/sp.deep-research" in content
    assert "## Analyze Gate" in content
    assert "gate_status" in content
    assert "gate_cycle" in content
    assert "highest_invalid_stage" in content
    assert "blocker_bundle" in content
    assert "[finding-id | invalid-stage | open | attribution | compact summary | remediation requirement]" in content
    assert "blocker_attribution_values" in content
    assert "artifact_fingerprint_basis" in content
    assert "missed_by_previous_analyze" in content
    assert "introduced_by_remediation" in content
    assert "upstream_artifact_changed" in content
    assert "detector_scope_changed" in content
    assert "new_finding_attribution" not in content
    assert "/sp.constitution" not in content


def test_workflow_state_template_includes_lane_context():
    content = _read("templates/workflow-state-template.md")

    assert "## Stage State" in content
    assert "current_stage:" in content
    assert "current_domain:" in content
    assert "next_action:" in content
    assert "blocker_reason:" in content
    assert "final_handoff_decision:" in content
    assert "## Lane Context" not in content


def test_workflow_state_template_includes_semantic_audit_state_contract():
    content = _read("templates/workflow-state-template.md")

    assert "## Semantic Audit State" in content
    assert "semantic_audit_status:" in content
    assert "semantic_audit_input_path:" in content
    assert "semantic_audit_output_path:" in content
    assert "semantic_audit_resume_status:" in content
    assert "semantic_audit_resume_validation:" in content
    assert "semantic_audit_route_fingerprint:" in content
    assert "semantic_audit_generated_resume_smoke:" in content
    assert "semantic_audit_stale_reasons:" in content
    assert "active-claim-changed" in content
    assert "active_claim_type:" in content
    assert "claim_readiness_status:" in content
    assert "claim_authorization_refs:" in content
    assert "claim_verification_refs:" in content
    assert "selected_candidate_ids:" in content
    assert "<WORKFLOW_STATE_DIR>/semantic-audit-input.json" in content
    assert "<WORKFLOW_STATE_DIR>/semantic-audit-output.json" in content


def test_debug_template_reads_constitution_and_feature_context_before_fixing() -> None:
    content = _read("templates/commands/debug.md")

    assert "### Required Context Inputs" in content
    assert ".specify/memory/constitution.md" in content
    assert "learning start --command <classic-command-name> --format json" in content
    assert ".specify/memory/learnings/INDEX.md" not in content
    assert "spec.md`, `plan.md`, and `tasks.md`" in content
    assert "`context.md` exists for the active feature" in content


def test_debug_templates_lock_map_backed_intake_contract() -> None:
    debug_command_content = _read("templates/commands/debug.md")
    debug_command = debug_command_content.lower()
    debug_thinker = _read("templates/worker-prompts/debug-thinker.md").lower()
    debug_contract_planner = _read("templates/worker-prompts/debug-contract-planner.md").lower()

    _assert_complexity_based_debug_contract(debug_command_content)
    assert "map-backed minimum intake" in debug_command
    assert "deep intake is fallback, not the default" in debug_command
    assert "stage 1a: causal map" in debug_command
    assert "stage 1b: investigation contract + log investigation plan" in debug_command
    assert "log investigation plan" in debug_command
    assert "logs are a first-class evidence source" in debug_command
    assert "existing logs" in debug_command
    assert "cannot directly enter fixing" in debug_command or "cannot enter fixing" in debug_command
    assert "optional expanded observer" not in debug_command
    assert "recommend enabling expanded observer" not in debug_command

    assert "causal-map-only" in debug_thinker
    assert "causal_map:" in debug_thinker
    assert "dimension_scan" in debug_thinker
    assert "candidate_board" in debug_thinker
    assert "project cognition" in debug_thinker
    assert "### project map" not in debug_thinker
    assert "light_scores" in debug_thinker
    assert "likelihood" in debug_thinker
    assert "impact_radius" in debug_thinker
    assert "falsifiability" in debug_thinker
    assert "log_observability" in debug_thinker
    assert "log_investigation_plan:" not in debug_thinker
    assert "expanded_observer:" not in debug_thinker
    assert "observer_mode:" not in debug_thinker

    assert "top-level log investigation plan" in debug_contract_planner
    assert "log_investigation_plan" in debug_contract_planner
    assert "top_candidate_summary:" in debug_contract_planner
    assert "expanded_observer" not in debug_contract_planner


def test_new_analysis_workflow_command_templates_exist():
    command_dir = PROJECT_ROOT / "templates" / "commands"
    template_stems = {path.stem for path in command_dir.glob("*.md")}

    assert "map-scan" in template_stems
    assert "map-build" in template_stems
    assert "map-codebase" not in template_stems
    assert "clarify" in template_stems
    assert "deep-research" in template_stems
    assert "explain" in template_stems
    assert "prd" in template_stems
    assert "spec-extend" not in template_stems


def test_deep_research_template_defines_feasibility_gate_contract():
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "sp-deep-research" in content
    assert "phase_mode: research-only" in content
    assert "deep-research.md" in content
    assert "research-spikes/" in content
    assert "Multi-Agent Research Orchestration" in content
    _assert_subagent_dispatch_contract(content, "deep-research")
    assert "dispatch shape" in lowered
    assert "Research Orchestration" in content
    assert "before writing `Planning Handoff`" in content
    assert "Traceability and Evidence Quality Contract" in content
    assert "CAP-001" in content
    assert "TRK-001" in content
    assert "EVD-001" in content
    assert "SPK-001" in content
    assert "PH-001" in content
    assert "Evidence Quality Rubric" in content
    assert "Planning Traceability Index" in content
    assert "what this does not prove" in lowered
    assert "evidence packet" in lowered
    assert "Research Agent Findings" in content
    assert "capability feasibility matrix" in lowered
    assert "implementation chain evidence" in content.lower()
    assert "Synthesis Decisions" in content
    assert "Planning Handoff" in content
    assert "constraints `/sp.plan` must preserve" in content
    assert "disposable demo" in lowered
    assert "do not edit production code" in lowered
    assert "skip deep research" in lowered
    assert "minor adjustment to existing behavior" in lowered
    assert "next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`" in content


def test_specify_template_keeps_canonical_state_tokens_but_not_universal_user_invocation():
    content = _read("templates/commands/specify.md")

    assert "Choose exactly one next command" in content
    assert "/sp.plan" in content
    assert "/sp.clarify" in content
    assert "/sp.deep-research" in content
    assert "Default handoff: /sp-plan" not in content
    assert "Default handoff: /sp.plan" not in content
    assert "/sp.plan" in content
    assert "brainstorming/handoff-to-specify.json" in content
    assert "source_signal_disposition" not in content
    assert "spec-contract.json" in content
    assert "semantic_delta" in content


def test_auto_template_requires_reconcile_before_resume():
    content = _read("templates/commands/auto.md").lower()

    assert "lane registry" in content
    assert "reconcile" in content
    assert "unique safe candidate" in content or "exactly one unique safe candidate" in content
    assert "do not guess" in content
    assert "never auto-resume an `uncertain` lane" in content
    assert "materialized worktree" in content


def test_plan_tasks_and_implement_templates_prefer_lane_resolution_when_feature_dir_is_not_explicit():
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")
    deep_research = _read("templates/commands/deep-research.md")
    clarify = _read("templates/commands/clarify.md")
    explain = _read("templates/commands/explain.md")

    assert "{{specify-subcmd:specify-runtime lane resolve --command plan --ensure-worktree}}" in plan
    assert "{{specify-subcmd:specify-runtime lane resolve --command tasks --ensure-worktree}}" in tasks
    assert "{{specify-subcmd:specify-runtime lane resolve --command implement --ensure-worktree}}" in implement
    assert "{{specify-subcmd:specify-runtime lane resolve --command deep-research --ensure-worktree}}" in deep_research
    assert "{{specify-subcmd:specify-runtime lane resolve --command clarify --ensure-worktree}}" in clarify
    assert "{{specify-subcmd:specify-runtime lane resolve --command explain --ensure-worktree}}" in explain
    assert "materialized worktree" in plan.lower()
    assert "materialized worktree" in tasks.lower()
    assert "materialized worktree" in implement.lower()
    assert "uncertain" in implement.lower()


def test_analyze_template_requires_lane_resolution_before_branch_guessing() -> None:
    content = _read("templates/commands/analyze.md")
    lowered = content.lower()

    assert "{{specify-subcmd:specify-runtime lane resolve --command analyze --ensure-worktree}}" in content
    assert "if `feature_dir` is not already explicit" in lowered
    assert "before guessing from branch-only context" in lowered
    assert "when lane resolution returns a materialized lane worktree" in lowered
    assert "must not switch branches" in lowered
    assert 'implicitly check out a "correct" feature branch' in lowered
    assert "mutate git state" in lowered


def test_specify_and_plan_templates_route_feasibility_gaps_through_deep_research():
    specify = _read("templates/commands/specify.md")
    plan = _read("templates/commands/plan.md")
    specify_lowered = specify.lower()

    assert "/sp.deep-research" in specify
    assert "/sp.plan" in specify
    assert "/sp.clarify" in specify
    assert "recommend exactly one next command" in specify_lowered
    assert "user review" in specify_lowered
    assert "planning-critical" in specify_lowered
    assert "release-decision" not in specify
    assert "final-handoff-decision" not in specify
    assert "deep-research `PH-###` traceability" in plan
    assert "Deep-research `PH-###` items remain direct evidence refs" in plan
    assert "route to deep research" in plan.lower()


def test_map_workflow_templates_define_graph_native_lifecycle() -> None:
    map_update_path = PROJECT_ROOT / "templates/commands/map-update.md"
    assert map_update_path.exists(), "map-update command template must exist for graph-native lifecycle maintenance"
    content = "\n".join(
        (
            _read("templates/commands/map-scan.md"),
            _read("templates/commands/map-build.md"),
            _read("templates/commands/map-update.md"),
        )
    )

    assert "map-update" in content
    assert "graph-native" in content.lower()
    assert "project-cognition" in content
    assert 'choose_subagent_dispatch(command_name="map-scan"' in content
    assert 'choose_subagent_dispatch(command_name="map-build"' in content
    assert "mandatory subagent lanes are read-only verification lanes only" in content.lower()
    assert "do not dispatch model-authored graph construction lanes" in content.lower()
    assert "build or refresh `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`" not in content
    assert "runtime handbook output contract" not in content.lower()


def test_spec_extend_template_positions_itself_as_planning_gap_rescue_lane():
    content = _read("templates/commands/clarify.md")
    lowered = content.lower()

    assert "closing planning-critical gaps" in lowered
    assert "`FEATURE_DIR/context.md` if present" in content
    assert "The subagent updates `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md` as needed." in content
    assert "Existing Code Insights" in content
    assert "unresolved gray areas that still change plan structure" in lowered
    assert "missing locked decisions, canonical references, or deferred-scope notes" in lowered
    assert "whether the spec package is now ready for `/sp.plan`, still needs more clarification, or needs `/sp.deep-research` feasibility proof first" in content
    assert "whether another `/sp.specify` or `/sp.clarify` pass is still justified before planning" in content
    assert "avoid implying an automatic handoff to `/sp.plan`" in lowered
    assert "default rescue lane" in lowered
    assert "recommend another clarification pass instead of implying that `/sp.plan` is now safe" in content
    assert "cognition follow-up" in lowered
    assert "artifact-only clarification work" in lowered
    assert "actual source/runtime changes" in lowered


def test_spec_template_defines_scope_boundaries_without_open_clarification_examples():
    content = _read("templates/spec-template.md")
    lowered = content.lower()

    assert "## Confirmed Scope" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content
    assert "### Deferred Or Future Scope" in content
    assert "### Boundary Constraints" in content
    assert "## Acceptance Proof" in content
    assert "## Decision Capture" in content
    assert "### Locked Decisions" in content
    assert "### User-Confirmed Deferrals" in content
    assert "### Canonical References" in content
    assert "[NEEDS CLARIFICATION:" not in content
    assert "confirmed product outcome" in lowered
    assert "confirmed scope" in lowered
    assert "coherent first release" not in lowered
    assert "viable mvp" not in lowered


def test_shared_artifact_templates_include_profile_fidelity_overlays():
    spec_content = _read("templates/spec-template.md")
    assert "Confirmed Scope" in spec_content
    assert "Acceptance Proof" in spec_content
    assert "## Fidelity Requirements" in spec_content
    assert "### Reference Object" in spec_content
    assert "### Required Fidelity" in spec_content
    assert "### Reference Behavior Inventory" in spec_content

    alignment_lowered = _read("templates/alignment-template.md").lower()
    assert "specification alignment report" in alignment_lowered
    assert "semantic term decisions" in alignment_lowered
    assert "upstream intent disposition" in alignment_lowered
    assert "out-of-scope conflicts" in alignment_lowered


def test_reference_fidelity_templates_propagate_behavior_inventory() -> None:
    spec_content = _read("templates/spec-template.md")
    plan_content = _read("templates/plan-template.md")
    tasks_content = _read("templates/tasks-template.md")
    analyze_content = _read("templates/commands/analyze.md")
    specify_content = _read("templates/commands/specify.md")
    plan_command = _read("templates/commands/plan.md")
    tasks_command = _read("templates/commands/tasks.md")

    assert "Reference Behavior Inventory" in spec_content
    assert "Reference Fidelity Inputs" in plan_content
    assert "Behavior-Level Fidelity Inventory" in plan_content
    assert "Reference Fidelity Mapping" in tasks_content
    assert "Reference Behavior Preservation Table" in analyze_content
    assert "reference behavior inventory" in analyze_content.lower()
    assert "Reference-Implementation" in specify_content
    assert "fidelity evidence" in specify_content.lower()
    assert "Reference Fidelity Inputs" in plan_command
    assert "reference-fidelity item" in tasks_command.lower()

    context_lowered = _read("templates/context-template.md").lower()
    assert "planning context" in context_lowered
    assert "integration boundaries" in context_lowered
    assert "change propagation matrix" in context_lowered


def test_context_template_exists_and_captures_planning_context():
    content = _read("templates/context-template.md")

    assert "# Planning Context:" in content
    assert "## Relevant Repository Context" in content
    assert "## Existing Patterns And Reuse Notes" in content
    assert "## Integration Boundaries" in content
    assert "## Product Boundary Constraints" in content
    assert "## Change Propagation Matrix" in content
    assert "## Locked Decisions Carry-Forward" in content
    assert "## Canonical References" in content
    assert "## Outstanding Questions" in content
    assert "## Deferred / Future Ideas" in content
    assert "# Feature Context:" not in content


def test_workflow_state_template_exists_and_captures_simplified_review_contract():
    content = _read("templates/workflow-state-template.md")

    assert "# Workflow State:" in content
    assert "## Current Command" in content
    assert "active_command:" in content
    assert "status:" in content
    assert "## Phase Mode" in content
    assert "phase_mode:" in content
    assert "summary:" in content
    assert "current_stage:" in content
    assert "## Review State" in content
    assert "last_user_reviewed_artifact_state" in content
    assert "canonical_contract_ref" in content
    assert "canonical_contract_revision" in content
    assert "semantic_delta" in content
    for stage in (
        "context-intake",
        "clarification",
        "approach-comparison",
        "section-approval",
        "artifact-writing",
        "artifact-review",
        "user-review",
    ):
        assert stage in content
    assert "## Fixed Lifecycle State" not in content
    assert "release-decision" not in content
    assert "## Legacy Fixed-Heavy Compatibility Labels" not in content
    assert "final-handoff-decision" not in content
    assert "goal-and-users" not in content
    assert "acceptance-and-completeness-gap-closure" not in content
    assert "/sp.plan" in content
    assert "/sp.clarify" in content
    assert "/sp.deep-research" in content


def test_workflow_state_template_documents_recovery_sections() -> None:
    content = _read("templates/workflow-state-template.md")

    assert "## Current Command" in content
    assert "## Phase Mode" in content
    assert "## Stage State" in content
    assert "blocker_reason: [None | Why progress is blocked]" in content
    assert (
        "approach_comparison_status: [not-needed | pending | awaiting-user-confirmation | "
        "selected | auto-accepted-recommended]"
        in content
    )
    assert (
        "section_approval_status: [not-needed | pending | awaiting-user-confirmation | "
        "approved | auto-approved-recommended]"
        in content
    )
    assert "final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]" in content
    assert "Re-read this file first after compaction or session recovery." not in content


def test_auto_template_routes_from_existing_state_surfaces():
    content = _read("templates/commands/auto.md")
    lowered = content.lower()

    assert "recommended next spec kit plus workflow step" in lowered
    assert "launcher/router" in lowered or "routing entrypoint" in lowered or "resume entrypoint" in lowered
    assert "workflow-state.md" in content
    assert "implement-tracker.md" in content
    assert "testing-state.md" not in content
    assert "status.md" in lowered
    assert "debug" in lowered
    assert "discussion-state.json" in content
    assert "handoff_consumption_status" in content
    assert "mark-consumed" in lowered
    assert "next_command" in content
    assert "do not rewrite the underlying workflow state to `/sp.auto`" in lowered
    assert "obey the recorded upstream gate" in lowered or "must obey the recorded upstream gate" in lowered
    assert "if state is missing, stale, conflicting, or cannot identify one safe next step" in lowered
    assert "stop in read-only diagnosis" in lowered or "diagnostic mode" in lowered
    assert "read-only diagnostic plus a self-unblock recommendation" in lowered
    assert "future `sp-auto` run continue automatically" in lowered
    assert "read `.specify/templates/commands/<target>.md`" in lowered or "follow the routed command's shared contract" in lowered
    assert "/sp.plan" in content
    assert "/sp.tasks" in content
    assert "/sp.analyze" in content
    assert "/sp.implement" in content
    assert "/sp.debug" in content
    assert "/sp.quick" in content
    assert "/sp.fast" in content


def test_auto_template_auto_accepts_single_safe_recommended_option() -> None:
    content = _read("templates/commands/auto.md")
    lowered = content.lower()

    assert "auto_default_recommendation" in content
    assert "single explicitly recommended option" in lowered
    assert "must auto-resolve" in lowered
    assert "question or confirmation" in lowered
    assert "record the recommended option as accepted by `sp-auto`" in lowered
    assert "do not invoke a structured question tool" in lowered
    assert "do not stop only to ask the user to reply `1`, `2`, or `3`" in lowered
    assert "scope reduction" in lowered
    assert "out-of-scope conflict" in lowered
    assert "unresolved planning-critical ambiguity" in lowered
    assert "write a self-unblock recommendation" in lowered
    assert "do not wait silently for user input" in lowered


def test_specify_template_honors_sp_auto_recommended_choice_resume() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "auto_default_recommendation" in content
    assert "before every bounded question, approach comparison, or section approval gate" in lowered
    assert "approach_comparison_status: auto-accepted-recommended" in content
    assert "section_approval_status: auto-approved-recommended" in content
    assert "self-unblock recommendation" in lowered
    assert "do not ask the user to reply `1`, `2`, or `3`" in lowered
    assert "scope reduction still requires explicit user confirmation" in lowered
    assert "out-of-scope conflicts still require explicit user confirmation" in lowered


def test_workflow_state_driven_templates_prefer_capture_auto_for_learning_closeout():
    for rel_path, cli_name in (
        ("templates/commands/specify.md", "specify"),
        ("templates/commands/plan.md", "plan"),
        ("templates/commands/tasks.md", "tasks"),
        ("templates/commands/analyze.md", "analyze"),
    ):
        content = _read(rel_path).lower()
        assert "learning capture-auto" in content
        assert "workflow-state.md" in content


def test_tasks_templates_preserve_user_confirmed_delivery_scope_not_mvp():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")

    assert "## Planning Inputs" in template_content
    assert "Locked planning decisions" in template_content
    assert "Implementation constitution" in template_content
    assert "Alignment risks" in template_content
    assert "Validation references" in template_content
    assert "Task Contract Mapping" in template_content
    assert "task-index.json" in template_content
    assert "Do not silently drop a locked planning decision" in template_content
    assert "protected obligations" in command_content.lower()
    assert "forbidden drift" in command_content.lower()
    assert "Phase 0: Implementation Guardrails" in template_content
    assert "framework ownership, preserved boundary pattern, forbidden drift, and review checks" in template_content
    assert "complete confirmed scope" in command_content.lower()
    assert "valid deferral references user confirmation" in command_content.lower()
    assert "suggested first release scope" not in command_content.lower()
    assert "smallest coherent release slice" not in command_content.lower()
    assert "parallel batch" in command_content.lower()
    assert "join point" in command_content.lower()
    assert "write set" in command_content.lower()
    assert "outcome-oriented tasks" in command_content.lower()
    assert "bounded expected write scope" in template_content.lower()
    assert "grouped parallelism is the default" in template_content.lower()
    assert "pipeline tasks should still stop at explicit checkpoints" in template_content.lower()
    assert "mvp first" not in command_content.lower()
    assert "suggested mvp scope" not in command_content.lower()

    assert "user-confirmed delivery sequence" in template_content.lower()
    assert "confirmed delivery boundary" in template_content.lower()
    assert "first release candidate" not in template_content.lower()
    assert "release/demo if ready" not in template_content.lower()
    assert "release/demo" not in template_content.lower()
    assert "parallel batch" in template_content.lower()
    assert "join point" in template_content.lower()
    assert "write set" in template_content.lower()
    assert "**[AGENT]**" in template_content
    assert "independent from `[P]`" in template_content
    assert "mvp first" not in template_content.lower()
    assert "mvp increment" not in template_content.lower()
    assert "mvp!" not in template_content.lower()


def test_plan_tasks_templates_enforce_complete_first_scope_preservation() -> None:
    surfaces = {
        "templates/commands/plan.md": _read("templates/commands/plan.md").lower(),
        "templates/plan-template.md": _read("templates/plan-template.md").lower(),
        "templates/commands/tasks.md": _read("templates/commands/tasks.md").lower(),
        "templates/tasks-template.md": _read("templates/tasks-template.md").lower(),
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md": _read(
            "templates/passive-skills/spec-kit-workflow-routing/SKILL.md"
        ).lower(),
    }

    expected_by_surface = {
        "templates/commands/plan.md": (
            "complete-first scope preservation",
            "complete user-confirmed scope",
            "complexity alone is not a valid reason",
            "shrink scope",
            "invent `v1/v2`",
            "`p0/p1`",
            "future-work delivery slice",
        ),
        "templates/plan-template.md": (
            "complete-first scope preservation",
            "complete user-confirmed scope",
            "complexity alone is not a valid reason",
            "do not shrink scope",
            "agent-invented `v1/v2`",
            "agent-invented `p0/p1`",
            "future-work delivery slice",
        ),
        "templates/commands/tasks.md": (
            "complete-first scope preservation",
            "do not shrink scope",
            "execution phases and user-story priorities order",
            "not delivery deferral",
            "agent-invented `v1/v2`",
            "`p0/p1`",
            "future-work delivery slice",
        ),
        "templates/tasks-template.md": (
            "complete-first scope preservation",
            "do not shrink scope",
            "execution phases are ordering, not delivery deferral",
            "user story priorities such as `p1`, `p2`, and `p3` remain ordering labels",
            "agent-invented `v1/v2`",
            "agent-invented `p0/p1`",
            "future-work delivery slice",
        ),
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md": (
            "complete-first scope preservation",
            "do not shrink scope",
            "runtime capability limits are blockers only under the adaptive execution policy",
            "heavy, safety-critical, or unpacketizable",
        ),
    }

    for path, phrases in expected_by_surface.items():
        for phrase in phrases:
            assert phrase in surfaces[path], f"{path} missing {phrase!r}"

    task_surfaces = {
        "templates/commands/tasks.md": surfaces["templates/commands/tasks.md"],
        "templates/tasks-template.md": surfaces["templates/tasks-template.md"],
    }
    for path, content in task_surfaces.items():
        assert "explicit deferred note" not in content, f"{path} still permits generic deferred-note language"
        assert "deferred-note coverage" not in content, f"{path} still permits generic deferred-note coverage"
        assert (
            "user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact"
            in content
        ), f"{path} missing full user-confirmed deferral contract"


def test_complete_first_deferrals_require_full_contract_fields() -> None:
    surfaces = {
        "templates/commands/plan.md": _read("templates/commands/plan.md").lower(),
        "templates/plan-template.md": _read("templates/plan-template.md").lower(),
        "templates/commands/tasks.md": _read("templates/commands/tasks.md").lower(),
        "templates/tasks-template.md": _read("templates/tasks-template.md").lower(),
    }
    required_fields = (
        "confirmation source",
        "exact excluded behavior",
        "residual risk",
        "reopen or stop condition",
        "downstream artifact",
    )
    fallback_by_surface = {
        "templates/commands/plan.md": (
            "if the user did not confirm the deferral",
            "create a refinement or validation checkpoint",
        ),
        "templates/plan-template.md": (
            "if the user did not confirm the deferral",
            "create a refinement or validation checkpoint",
        ),
        "templates/commands/tasks.md": (
            "if the user did not confirm the deferral",
            "task the behavior",
        ),
        "templates/tasks-template.md": (
            "if the user did not confirm the deferral",
            "task the behavior",
        ),
    }

    for path, content in surfaces.items():
        for phrase in required_fields:
            assert phrase in content, f"{path} missing deferral field {phrase!r}"
        for phrase in fallback_by_surface[path]:
            assert phrase in content, f"{path} missing unconfirmed-deferral fallback {phrase!r}"

    combined = "\n".join(surfaces.values())
    assert "explicit deferral" not in combined
    assert "explicit deferred note" not in combined
    assert "deferred-note coverage" not in combined
    assert "explicitly user-confirmed deferral" not in combined
    assert "explicitly deferred" not in combined
    assert "explicit consuming artifact section, deferral, or blocker reason" not in combined
    assert "dependency edge, deferral, escalation, or blocker reason" not in combined
    assert "mark the handoff as `integrated`, `deferred`, or `blocked`" not in combined
    assert "resolved`, `deferred" not in combined
    assert "deferred count" not in combined
    assert "if it is deferred, say so explicitly" not in combined
    assert "deferred behavior]" not in combined


def test_structured_templates_carry_complete_first_scope_contract() -> None:
    plan_contract = json.loads(_read("templates/plan-contract-template.json"))
    task_index = json.loads(_read("templates/task-index-template.json"))
    task_packet = json.loads(_read("templates/task-packet-template.json"))
    implement_state = json.loads(_read("templates/implement-execution-state-template.json"))

    assert "complete_first_scope_preservation" in plan_contract
    assert "user_confirmed_deferrals" in plan_contract
    assert "deferral_contract_required_fields" in plan_contract
    assert plan_contract["deferral_contract_required_fields"] == [
        "confirmation_source",
        "exact_excluded_behavior",
        "residual_risk",
        "reopen_or_stop_condition",
        "downstream_artifact",
    ]
    assert set(plan_contract["user_confirmed_deferral_entry_template"]) == set(
        plan_contract["deferral_contract_required_fields"]
    )

    for payload in (task_index, task_packet, implement_state):
        assert payload["policy_refs"] == ["plan-contract.json#/complete_first_scope_preservation"]
        assert "complete_first_scope_preservation" not in payload
        assert "deferral_contract_required_fields" not in payload

    assert plan_contract["complete_first_scope_preservation"]["default"] == "plan_and_task_complete_confirmed_scope"
    assert "do not delete capability" in plan_contract["capability_preservation"]["surface_minimization_policy"]


def test_workflow_templates_preserve_create_scaffold_capabilities_when_surface_is_minimized() -> None:
    specify = _read("templates/commands/specify.md")
    spec_template = _read("templates/spec-template.md")
    plan = _read("templates/commands/plan.md")
    plan_template = _read("templates/plan-template.md")
    plan_contract_template = _read("templates/plan-contract-template.json")
    tasks = _read("templates/commands/tasks.md")
    tasks_template = _read("templates/tasks-template.md")
    task_packet_template = _read("templates/task-packet-template.json")

    specify_lower = specify.lower()
    for action_signal in ("create", "scaffold", "authoring"):
        assert action_signal in specify_lower

    assert "manual copy" in specify_lower
    assert "static template" in specify_lower
    assert "capability operation" in specify_lower
    assert "capability preservation ledger" in spec_template.lower()

    plan_combined = f"{plan}\n{plan_template}"
    plan_lower = plan_combined.lower()
    assert "command-surface minimization" in plan_lower
    assert "entry-point remapping" in plan_lower
    assert "must not delete capability" in plan_lower
    assert "tui route" in plan_lower
    assert "core api" in plan_lower
    assert "scaffold operation" in plan_lower

    tasks_combined = f"{tasks}\n{tasks_template}"
    tasks_lower = tasks_combined.lower()
    assert "does-not-remove guard" in tasks_lower
    assert "anti_goal" in tasks_lower or "anti-goal" in tasks_lower
    assert "semantic degradation" in tasks_lower
    assert "manual copy docs" in tasks_lower
    assert "template-only task" in tasks_lower
    assert "create/scaffold" in tasks_lower

    packet = json.loads(task_packet_template)
    assert "forbidden_drift" in packet
    assert "capability_operation_refs" in packet

    plan_contract = json.loads(plan_contract_template)
    assert "capability_operations" in plan_contract
    assert "capability_preservation" in plan_contract


def test_generated_workflow_templates_do_not_default_to_product_minimization() -> None:
    checked_paths = [
        "templates/commands/discussion.md",
        "templates/commands/specify.md",
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/spec-template.md",
        "templates/plan-template.md",
        "templates/tasks-template.md",
    ]
    forbidden = [
        "minimal viable path",
        "smallest coherent release slice",
        "suggested mvp scope",
        "mvp first",
        "mvp increment",
        "mvp!",
        "first story release",
        "user story 1 - [title] (priority: p1) first release candidate",
        "release/demo if ready",
        "smallest integration scenario",
    ]

    for rel_path in checked_paths:
        lowered = _read(rel_path).lower()
        for phrase in forbidden:
            assert phrase not in lowered, f"{phrase!r} should not appear in {rel_path}"

    specify = _read("templates/commands/specify.md").lower()
    assert "do not treat product minimization as the default strategy" in specify
    assert "scope reduction requires user confirmation" in specify


def test_shared_workflow_templates_mark_hard_gates_with_agent_marker() -> None:
    paths = {
        "specify": Path("templates/commands/specify.md"),
        "plan": Path("templates/commands/plan.md"),
        "tasks": Path("templates/commands/tasks.md"),
        "implement": Path("templates/commands/implement.md"),
        "debug": Path("templates/commands/debug.md"),
        "prd": Path("templates/commands/prd.md"),
    }

    for name, path in paths.items():
        content = read_template(path.as_posix())
        assert "[AGENT]" in content, f"{name} template missing [AGENT] marker"


def _legacy_implement_template_supports_capability_aware_parallel_batches():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    step_6 = _extract_step_6_strategy_block(content)
    context_loading = _extract_outline_step_block(
        content,
        "3. Load and analyze the implementation context:",
        "4. **Project Setup Verification**:",
    )
    batch_acceptance = _extract_outline_step_block(
        content,
        "9. Progress tracking and error handling:",
        "10. Completion validation:",
    )
    completion_gate = _extract_outline_step_block(
        content,
        "10. Completion validation:",
        "Note: This command assumes a complete task breakdown exists in tasks.md.",
    )

    _assert_agent_assisted_cognition_gate(content, "implement")
    assert "minimal_live_reads" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content
    assert "PRODUCT-AND-CAPABILITY-MAP" not in content
    assert "CHANGE-ENTRYPOINTS" not in content
    assert "IMPLEMENTATION-PLAYBOOKS" not in content
    assert "CHANGE-PROPAGATION-RISKS" not in content
    assert "VERIFICATION-ROUTES" not in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:specify-runtime learning start --command implement --format json}}" in content
    assert "Required options: `--command`, `--type`, `--summary`, `--evidence`" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "follow-up `/sp-map-update` is useful for external map maintenance" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert ".specify/memory/constitution.md" in content
    assert "Extract `Implementation Constitution` from `plan.md`" in content
    assert "What framework or boundary pattern owns the touched surface?" in content
    assert "Which files define the existing pattern that must be preserved?" in content
    assert "What implementation drift is forbidden for this batch?" in content
    assert "compile a `WorkerTaskPacket` for each subagent task" in content
    assert "dispatch only from validated `WorkerTaskPacket`" in content
    assert "Do not dispatch from raw task text alone" in content
    assert ".specify/templates/worker-prompts/implementer.md" in content
    assert ".specify/templates/worker-prompts/task-reviewer.md" in content
    assert ".specify/templates/worker-prompts/spec-reviewer.md" in content
    assert ".specify/templates/worker-prompts/code-quality-reviewer.md" in content
    assert "ordinary post-task review" in lowered
    assert "runtime-managed result channel" in lowered
    assert "feature_dir/worker-results/<task-id>.json" in lowered
    assert '{{specify-subcmd:specify-runtime result path --command implement --feature-dir "$feature_dir" --task-id <task-id>}}' in lowered
    assert '{{specify-subcmd:specify-runtime result submit --command implement --feature-dir "$feature_dir" --task-id <task-id> --result-file <path>}}' in lowered
    assert "{{specify-subcmd:specify-runtime result path --command implement --request-id <request-id>}}" in lowered
    assert "active runtime-managed result channel for that request id" in lowered
    assert "does not accept `--format`" in lowered
    assert "reported_status" in lowered
    assert "idle subagent is not an accepted result" in lowered
    assert "must wait for and consume the structured handoff before closing the join point" in lowered
    assert "boundary-pattern preservation" in lowered
    assert "implement-tracker.md" in content
    assert "execution-state source of truth" in lowered
    assert "## execution intent" in lowered
    assert "intent_outcome:" in lowered
    assert "intent_constraints:" in lowered
    assert "success_evidence:" in lowered
    _assert_reference_evidence_contract(context_loading)
    _assert_reference_evidence_contract(batch_acceptance)
    _assert_reference_evidence_contract(completion_gate)
    assert "profile-matched evidence" in context_loading.lower()
    assert "profile-matched evidence" in batch_acceptance.lower()
    assert "profile-matched evidence" in completion_gate.lower()
    assert "standard delivery" in context_loading.lower()
    assert "standard delivery" in completion_gate.lower()
    assert "lighter default" in context_loading.lower()
    assert "lighter default" in completion_gate.lower()
    assert "generic `tests passed` output is not sufficient" in batch_acceptance.lower()
    assert "generic `tests passed` output" in completion_gate.lower()
    assert "comparison evidence" in lowered
    assert "deviation log" in lowered
    assert "first-class implementation context" in lowered
    assert "user execution notes" in lowered
    assert "build or compile order" in lowered
    assert "resume_decision" in content
    assert "status: gathering | executing | recovering | replanning | validating | blocked | resolved" in lowered
    assert "open_gaps" in lowered
    assert "parallel batches" in lowered
    assert "current agent" in lowered
    assert "ready tasks" in lowered
    assert "join point" in lowered
    assert "shared registration files" in lowered
    assert "refine only the current executable window after each join point" in lowered
    assert "grouped parallelism is the default when multiple ready tasks have isolated write sets" in lowered
    assert "pipeline execution is preferred when outputs flow stage-by-stage" in lowered
    assert "classify_review_gate_policy(workload_shape)" in content
    assert "three-layer check" in lowered
    assert "optional read-only peer-review lane" in lowered
    assert "blocked subagent results must include" in lowered
    assert "failed assumption" in lowered
    assert "smallest safe recovery step" in lowered
    assert "subagent dispatch" in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "native-subagents" in lowered
    assert "dispatch-blocking runtime condition" in lowered
    assert "Dispatch failure is not permission to continue locally." in content
    assert "A lane is dispatch-ready only if its validated `WorkerTaskPacket` includes" in content
    assert "If any required packet field is missing, do not dispatch and do not execute inline." in content
    assert "The only legal action is to repair the packet or stop as `subagent-blocked`." in content
    assert "Dispatch failure is not permission to continue locally." in content
    assert "Do not persist native subagent dispatch failures" in content
    assert "runtime-surface failure metadata" in lowered
    assert "without writing a durable fallback decision to `implement-tracker.md`" in content
    assert "dispatch fallback" not in lowered
    assert "actual_surface: leader-inline" not in lowered
    assert "delegation_confidence" not in lowered
    assert "enough context" not in lowered
    assert "low-context" not in lowered
    assert "two or more safe validated packets" in lowered
    assert "dispatch-blocking runtime condition is present" in lowered
    assert "exactly one safe validated packet is ready" in lowered
    assert "two or more safe validated packets with isolated write sets" in lowered
    assert "`subagent-blocked`" in lowered
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in lowered
    assert "specify-runtime cognition closeout-plan --workflow" in lowered
    assert "update_mode=delta_session" in lowered
    assert "update_mode=payload_file" in lowered
    assert "update_argv" in lowered
    assert "clean closeout keys on `result_state`" in lowered
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in lowered
    assert "verification is truthfully green and no explicit blocker prevents completion" in lowered
    assert "including unresolved `open_gaps`" in lowered
    assert "dirty only when inline update cannot complete" in lowered
    assert ".specify/project-map/index/status.json" not in lowered
    assert "delta_append_draft.argv_prefix" in lowered
    assert "only when inline update cannot complete" in lowered
    assert "specify team" not in lowered
    assert "auto-dispatch" not in lowered
    assert "codex runtime rule" not in lowered

    no_safe_batch = step_6.find("dispatch-blocking runtime condition is present")
    one_subagent = step_6.find("exactly one safe validated packet")
    parallel_subagents = step_6.find("two or more safe validated packets")
    subagent_blocked = step_6.find("subagent-blocked")

    assert no_safe_batch != -1
    assert one_subagent != -1
    assert parallel_subagents != -1
    assert subagent_blocked != -1
    assert no_safe_batch < one_subagent < parallel_subagents


def test_mutation_workflows_require_inline_cognition_update_before_dirty_fallback() -> None:
    for path in (
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
    ):
        content = _read(path).lower()

        assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
        assert "specify-runtime cognition closeout-plan --workflow" in content
        assert "update_mode=delta_session" in content
        assert "update_mode=payload_file" in content
        assert "update_argv" in content
        assert "clean closeout keys on `result_state`" in content
        assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
        assert "specify-runtime cognition mark-dirty" in content
        assert "dirty only when inline update" in content

        for stale_closeout_phrase in (
            "actual `{{invoke:map-update}}` refresh",
            "refresh the project cognition runtime through `{{invoke:map-update}}` using the changed paths",
            "if the fast-path change unexpectedly touched",
            "tell the user to run `{{invoke:map-update}}` with the changed paths before the next brownfield workflow proceeds",
            "project_cognition_refresh` recommending",
            "project_cognition_refresh recommending",
            "recommended `{{invoke:map-update}}` refresh when applicable",
            "recommended `{{invoke:map-update}}` refresh when project cognition might be affected",
            "and recommend `{{invoke:map-update}}` with the changed paths",
        ):
            assert stale_closeout_phrase not in content


def test_inline_cognition_closeout_shared_surfaces_are_consistent() -> None:
    required_paths = (
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/senior-consequence-analysis-gate.md",
        "templates/command-partials/common/navigation-check.md",
        "templates/command-partials/fast/shell.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        "templates/project-handbook-template.md",
        "templates/constitution-template.md",
    )

    for path in required_paths:
        content = _read(path).lower()
        assert "workflow-owned mutation closeout" in content, path
        assert "external map maintenance" in content, path
        assert (
            "inline project cognition update" in content
            or "planner-first" in content
        ), path
        assert "sp-map-update is for manual/external maintenance" in content.replace("`", ""), path
        if path in {
            "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
            "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        }:
            assert "rendered planner-first closeout command" in content, path
            assert "registry-owned literal `sp-*` workflow id" in content, path
            assert "unknown_path_dispositions" in content, path

    planning_context = _read(
        "templates/command-partials/common/planning-context-loading-gradient.md"
    ).lower()
    assert "planning-only artifact writes do not require" in planning_context
    assert "hand off to the appropriate mutation workflow" in planning_context
    assert "inline-project-cognition-update.md" not in planning_context

    for path in (
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        "templates/project-handbook-template.md",
    ):
        content = _read(path).lower()
        if path.endswith("context-loading-gradient.md") or path.endswith("planning-context-loading-gradient.md"):
            assert "entry-time stale or weak cognition is still an advisory navigation concern" in content
            assert "does not waive closeout ownership" in content
        if path == "templates/project-handbook-template.md":
            assert "verification_evidence" in content
            assert "generated_surface_notes" in content
            assert "failed verification evidence" in content or "failed verification cannot produce" in content

    passive_gate = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md").lower()
    assert "do not silently switch into `sp-map-update`" not in passive_gate
    assert "user-invoked workflow handoff" not in passive_gate


def test_constitution_workflow_reports_cognition_followup_without_mutating_it() -> None:
    content = _read("templates/commands/constitution.md").lower()

    assert "this workflow writes only `.specify/memory/constitution.md`" in content
    assert "does not own project cognition mutation closeout" in content
    assert "do not run `specify-runtime cognition update`, `specify-runtime cognition mark-dirty`" in content
    assert "report that follow-up instead" in content
    assert "routine cleanup for constitution-only changes" in content


def test_runtime_cognition_partials_preserve_mutation_closeout_rule() -> None:
    context = _read("templates/command-partials/common/context-loading-gradient.md").lower()
    consequence_gate = _read(
        "templates/command-partials/common/senior-consequence-analysis-gate.md"
    ).lower()
    passive_gate = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md").lower()

    for content in (context, consequence_gate, passive_gate):
        assert "mutation closeout" in content
        assert "entry-time stale" in content or "entry stale" in content
        assert (
            "inline project cognition update" in content
            or "planner-first closeout command" in content
            or "workflow-local planner-first contract" in content
        )

    for content in (context, passive_gate):
        assert "dirty only when inline update cannot complete" in content or "mark-dirty" in content

    assert "does not waive closeout ownership" in context
    assert "does not allow source/runtime mutation workflows to defer closeout" in consequence_gate
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in passive_gate


def test_map_update_template_does_not_rebuild_after_successful_incremental_update():
    content = _read("templates/commands/map-update.md")
    lowered = content.lower()

    assert "do not tell the user to run" in lowered
    assert "merely because refreshed source changes are not committed yet" in lowered
    assert "after those source changes are committed" in lowered
    assert "specify-runtime cognition record-refresh" in lowered
    assert "without rerunning `{{invoke:map-scan}}` or `{{invoke:map-build}}`" in lowered

    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        doc = _read(path).lower()
        assert "committing the refreshed source changes does not require a full rebuild by itself" in doc
        assert "specify-runtime cognition record-refresh" in doc
        assert "specify-runtime cognition complete-refresh" in doc


def test_implement_template_requires_resume_audit_before_trusting_terminal_state():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    assert "resume audit" in lowered
    assert "checked tasks as claims" in lowered
    assert "implement resume-audit" in lowered
    assert "consumer evidence" in lowered
    assert "real_entrypoint_evidence" in content
    assert "synthetic-only" in lowered
    assert "do not preserve resolved status" in lowered


def test_implement_template_defines_adaptive_leader_scheduler_contract():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "## Orchestration Model" in content
    assert "workflow leader" in lowered
    assert "execution_model: adaptive" in lowered
    assert "leader-direct" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "compile and validate a `workertaskpacket` just in time only for delegated work" in lowered


def _legacy_runtime_alignment_prefers_cognition_gate_over_layered_atlas() -> None:
    debug_template = _read("templates/commands/debug.md")
    build_template = _read("templates/commands/implement.md")
    shared_gate = _read("templates/command-partials/common/context-loading-gradient.md")
    planning_shared_gate = _read("templates/command-partials/common/planning-context-loading-gradient.md")
    navigation_shim = _read("templates/command-partials/common/navigation-check.md")
    lowered = build_template.lower()
    lowered_gate = shared_gate.lower()
    lowered_planning_gate = planning_shared_gate.lower()
    lowered_shim = navigation_shim.lower()

    assert "DEBUG-HANDBOOK.md" not in debug_template
    _assert_agent_assisted_cognition_gate(debug_template, "debug")
    assert "minimal_live_reads" in debug_template
    assert "BUILD-HANDBOOK.md" not in build_template
    _assert_agent_assisted_cognition_gate(build_template, "implement")
    assert "minimal_live_reads" in build_template
    assert "project cognition runtime" in lowered_gate
    assert "default project cognition intake" in lowered_gate
    assert "raw" in lowered_gate
    assert "compass --intent <intent>" in lowered_gate
    assert "if cognition freshness is `stale`, treat map output as advisory" in shared_gate
    assert "continue with live repository evidence" in shared_gate
    assert "external/manual maintenance" in shared_gate
    for gate in (lowered_gate, lowered_planning_gate):
        assert "changed paths missing from `path_index`" in gate
        assert "recommend `{{invoke:map-update}}` first for ordinary existing-baseline gaps" in gate
        assert "use `{{invoke:map-scan}} -> {{invoke:map-build}}` only for brownfield first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows outside baseline-kind exceptions described below, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`" in gate
        stale_scan_build_phrase = "recommend `sp-map-scan -> sp-map-build` only if the user wants " + "map " + "repair"
        assert stale_scan_build_phrase not in gate
    assert "cannot create absent path coverage" not in shared_gate
    assert "`support_drift` -> warn and continue with live repository evidence" in shared_gate
    assert "`partial_refresh` -> warn that refresh data was recorded but readiness did not pass" in shared_gate
    assert "`recommended_next_action`" in shared_gate
    assert "PROJECT-HANDBOOK.md" not in shared_gate
    assert "atlas.entry" not in shared_gate
    assert "compatibility shim" in lowered_shim
    assert "context-loading-gradient.md" in navigation_shim
    assert "project cognition runtime" in lowered_shim
    assert "PROJECT-HANDBOOK.md" not in navigation_shim
    assert ".specify/project-map/index/" not in navigation_shim
    assert "dispatch `parallel-subagents` when multiple validated packets have isolated write sets" in lowered
    assert "use `execution_surface: native-subagents`" in lowered
    assert "blocker" in lowered
    assert "invoking runtime acts as the leader" in lowered
    assert "subagent execution" in lowered
    assert "next executable phase" in lowered
    assert "shared implement template is the primary source of truth" in lowered
    assert "join point" in lowered
    assert "retry-pending" in lowered or "retry pending" in lowered
    assert "blocker" in lowered
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in build_template
    assert "core implementation complete" in lowered
    assert "ready for integration testing" in lowered
    assert "overall feature completion" in lowered
    assert "e2e" in lowered
    assert "polish" in lowered
    assert "do not stop to ask whether validation should start" in lowered
    assert "`research_gap`" in build_template
    assert "`plan_gap`" in build_template
    assert "`spec_gap`" in build_template
    assert "/sp.clarify" in build_template
    assert "planned validation tasks are still ready work" in lowered
    assert "do not stop to ask whether validation should start" in lowered
    assert "manual-only check or approval step is explicitly recorded in the tracker or task plan" in lowered


def test_shared_implement_teams_contract_preserves_explicit_execution_packet_fields():
    content = _read("src/specify_cli/integrations/base.py").lower()

    assert "every team-managed task in the teams-backed flow must still behave like an explicit execution packet" in content
    assert "write set and shared surfaces" in content
    assert "explicit verification command or acceptance check" in content
    assert "canonical result handoff path or runtime-managed result channel expectation" in content
    assert "completion-handoff protocol covering start, blocker, and final completion evidence" in content
    assert "platform guardrails" in content
    assert "status flip alone" in content
    assert "specify-runtime cognition compass --intent implement" in content
    assert "minimal_live_reads" in content
    assert "first_pass_paths" in content
    assert "coverage_diagnostics" in content
    assert "expansion_ref" in content
    assert "lexicon -> semantic_intake -> query" in content
    assert "specify-runtime cognition lexicon --intent implement" not in content


def test_implement_template_requires_explicit_join_point_validation_blocks():
    content = _read("templates/commands/implement.md").lower()

    assert "at a parallel join" in content
    assert "validation target" in content
    assert "validation command or concrete check" in content
    assert "pass condition" in content
    assert "if validation metadata is missing" in content


def test_tasks_templates_require_join_point_validation_details():
    command_content = _read("templates/commands/tasks.md").lower()
    template_content = _read("templates/tasks-template.md").lower()

    assert "every explicit join point includes a validation target" in command_content
    assert "validation command or concrete check" in command_content
    assert "join point validation:" in template_content
    assert "validation target:" in template_content
    assert "validation command:" in template_content
    assert "pass condition:" in template_content


def test_tasks_template_clean_completion_hands_off_to_implement():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "default_handoff: '/sp.implement" in content
    assert "Implement Project" not in content
    assert "hand off directly to `{{invoke:implement}}`" in lowered
    assert "`next_command: /sp.implement`" in content
    assert "clean result" in lowered
    assert "legacy or diagnostic state explicitly records that route" in lowered
    assert "the analyze gate is mandatory" not in lowered


def test_tasks_template_requires_implementation_readiness_self_audit_and_remediation_mode():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "default_handoff: '/sp.implement for a clean completed task package" in content
    assert "/sp.plan, /sp.clarify, or /sp.deep-research when escalated remediation exposes missing upstream truth" in content
    assert "send: false" in content
    assert "Deterministic Task-Graph Review" in content
    assert "User-Observable Path Coverage" in content
    assert "real_entrypoint_evidence" in content
    assert "synthetic component" in lowered
    assert "repair task-layer defects locally" in lowered
    assert "route upstream truth defects to their owner" in lowered
    assert "goal, confirmed scope, architecture, feasibility, target boundary" in lowered
    assert "transition to `sp-implement`" in lowered


def test_tasks_template_delegates_packet_shape_to_canonical_json_template():
    content = _read("templates/tasks-template.md")
    packet_template = _read("templates/task-packet-template.json")
    task_index_template = _read("templates/task-index-template.json")

    assert "## Canonical Agent Shapes" in content
    assert "templates/task-packet-template.json" in content
    assert "task-index.json#/tasks/T###/ui_contract" in content
    assert "task-index-template.json#/ui_contract_schema_ref" in content
    assert "contract_version" not in content
    for field in (
        "ui_work_type",
        "surface_type",
        "platforms",
        "visual_thesis",
        "content_thesis",
        "interaction_thesis",
        "approved_visual_ref",
        "reference_intents",
        "real_content_plan",
        "image_plan",
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
    ):
        assert field in content
    assert "do not reproduce those schemas as long markdown examples" in content.lower()
    assert "ui_contract_schema_ref" in task_index_template
    assert "required_consumer_evidence" in packet_template
    assert "capability_operation_refs" in packet_template


def test_implement_template_honors_pending_analyze_gate_from_workflow_state():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "Read `FEATURE_DIR/workflow-state.md` when present" in content
    assert "canonical `next_command` still points to `/sp.analyze`" in lowered
    assert "honor that pending diagnostic gate" in lowered
    assert "self-authorizing implementation from chat memory" in lowered


def test_debug_and_quick_templates_reference_shared_worker_prompt_assets() -> None:
    debug_content = _read("templates/commands/debug.md")
    quick_content = _read("templates/commands/quick.md")

    assert ".specify/templates/worker-prompts/debug-investigator.md" in debug_content
    assert ".specify/templates/worker-prompts/quick-worker.md" in quick_content
    assert "dispatch-blocking" in debug_content.lower() or "subagent-blocked" in debug_content.lower()
    assert "delegation_confidence" in quick_content.lower()
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in debug_content.lower()
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in quick_content.lower()
    assert "{{specify-subcmd:specify-runtime result submit" in debug_content.lower()
    assert "{{specify-subcmd:specify-runtime result submit" in quick_content.lower()
    assert "reported_status" in debug_content.lower()
    assert "reported_status" in quick_content.lower()
    assert "idle subagent is not an accepted result" in debug_content.lower()
    assert "idle subagent is not an accepted result" in quick_content.lower()
    assert "must wait for and consume the structured handoff before closing the join point" in debug_content.lower()
    assert "must wait for and consume the structured handoff before closing the join point" in quick_content.lower()


def test_worker_prompt_templates_exist_and_define_controller_worker_contracts() -> None:
    implementer = _read("templates/worker-prompts/implementer.md")
    debug_investigator = _read("templates/worker-prompts/debug-investigator.md")
    quick_worker = _read("templates/worker-prompts/quick-worker.md")
    task_reviewer = _read("templates/worker-prompts/task-reviewer.md")
    spec_reviewer = _read("templates/worker-prompts/spec-reviewer.md")
    code_quality = _read("templates/worker-prompts/code-quality-reviewer.md")

    assert "# Implementer Worker Prompt" in implementer
    assert "full task text" in implementer.lower()
    assert "worker packet" in implementer.lower()
    assert "status: `done | done_with_concerns | blocked | needs_context`" in implementer.lower()
    assert "platform guardrails" in implementer.lower()
    assert "completion-handoff protocol" in implementer.lower()
    assert "task_started" in implementer.lower()
    assert "must not enter `idle` before the required handoff is written or returned" in implementer.lower()
    assert "test-authoring-only" in implementer.lower()
    assert "accepted change-set red/baseline" in implementer.lower()
    assert "must not run a test suite" in implementer.lower()
    assert "per txx" in implementer.lower()
    assert "only the leader may open an attempt" in " ".join(
        implementer.lower().split()
    )
    assert "do not claim verification that was not run" in implementer.lower()
    assert "consumer evidence" in implementer.lower()
    assert "created but not wired" in implementer.lower()
    assert "real_entrypoint_evidence" in implementer
    assert "kind: real_entrypoint" in " ".join(implementer.split())
    assert "synthetic component" in implementer.lower()

    assert "# Debug Investigator Worker Prompt" in debug_investigator
    assert "current hypothesis" in debug_investigator.lower()
    assert "must not update the debug file" in debug_investigator.lower()
    assert "must not enter `idle` before the required handoff is written or returned" in debug_investigator.lower()

    assert "# Quick Worker Prompt" in quick_worker
    assert "status.md remains leader-owned" in quick_worker.lower()
    assert "smallest safe lane" in quick_worker.lower()
    assert "must not enter `idle` before the required handoff is written or returned" in quick_worker.lower()
    assert "surface-only" in quick_worker.lower() or "symptom-only" in quick_worker.lower()
    assert "/sp-debug" in quick_worker.lower()

    assert "# Spec Reviewer Worker Prompt" in spec_reviewer
    assert "do not trust implementer summaries" in spec_reviewer.lower()
    assert "read the actual code" in spec_reviewer.lower()

    assert "# Code Quality Reviewer Worker Prompt" in code_quality
    assert "only run after spec review passes" in code_quality.lower()
    assert "file responsibility" in code_quality.lower()
    for content in (spec_reviewer, code_quality):
        assert "Inline Project Cognition Handoff" not in content
        assert "changed_paths" not in content
        assert "behavior_surfaces" not in content
        assert "state_contracts" not in content

    assert "# Task Reviewer Worker Prompt" in task_reviewer
    assert "spec_verdict" in task_reviewer
    assert "quality_verdict" in task_reviewer


def test_specify_template_explicitly_reads_constitution() -> None:
    content = _read("templates/commands/specify.md")

    assert ".specify/memory/constitution.md" in content


def test_checklist_template_prefers_native_question_tools_with_textual_fallback() -> None:
    content = _read("templates/commands/checklist.md")
    lowered = content.lower()

    assert "When the runtime exposes a native structured question tool" in content
    assert "Treat the textual Q1/Q2/Q3 and Q4/Q5 format as fallback-only guidance" in content
    assert "native tool fields" in lowered
    assert "Output the questions (label Q1/Q2/Q3)." in content
    assert ".specify/memory/constitution.md" in content
    assert "learning start --command <classic-command-name> --format json" in content
    assert ".specify/memory/learnings/INDEX.md" not in content
    assert "capture-auto" in lowered
    assert "specify-runtime cognition query" in lowered
    assert "--query-plan" in lowered
    assert "specify-runtime cognition compass --intent plan" in lowered
    assert "lexicon -> semantic_intake -> query" in lowered
    assert "query-plan" in lowered
    assert "readiness values" in lowered
    assert "minimal_live_reads" in lowered
    assert "build-handbook.md" not in lowered
    assert "coverage_diagnostics" in lowered
    assert "if the checklist reveals planning-critical requirement gaps" in lowered
    assert "recommend `/sp-specify`" in lowered or "recommend `/sp.specify`" in lowered
    assert "recommend `/sp-plan`" in lowered
    assert "recommend `/sp-tasks`" in lowered


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Specification Alignment Report:" in content
    assert "## Current Understanding" in content
    assert "## Confirmed Facts" in content
    assert "## Low-Risk Assumptions" in content
    assert "## Open Questions" in content
    assert "## Semantic Term Decisions" in content
    assert "## Upstream Intent Disposition" in content
    assert "## Out-Of-Scope Conflicts" in content
    assert "## Readiness Decision" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "# Requirement Alignment Report:" not in content
    assert "## Observer Gate" not in content
    assert "## Coverage Mode Outcomes" not in content


def test_script_contracts_expose_context_artifact_paths():
    ps_common = _read("scripts/powershell/common.ps1")
    ps_check = _read("scripts/powershell/check-prerequisites.ps1")
    ps_setup = _read("scripts/powershell/setup-plan.ps1")
    sh_common = _read("scripts/bash/common.sh")
    sh_check = _read("scripts/bash/check-prerequisites.sh")
    sh_setup = _read("scripts/bash/setup-plan.sh")

    assert "CONTEXT       = Join-Path $featureDir 'context.md'" in ps_common
    assert "CONTEXT      = $paths.CONTEXT" in ps_check
    assert "[string]$FeatureDir" in ps_check
    assert "PROJECT_COGNITION_STATUS = (Get-ProjectCognitionStatusPath -RepoRoot $paths.REPO_ROOT)" in ps_check
    assert "PROJECT_COGNITION_HELPER = (Get-ProjectCognitionHelperPath -RepoRoot $paths.REPO_ROOT)" in ps_check
    assert "context.md" in ps_check
    assert "CONTEXT = $paths.CONTEXT" in ps_setup
    assert "SPECIFY_DRAFT = Join-Path $featureDir 'specify-draft.md'" in ps_common
    assert "FEATURE_DIR = $paths.FEATURE_DIR" in ps_setup
    assert "[string]$FeatureDir" in ps_setup
    assert "CONTEXT=%q\\n" in sh_common
    assert "SPECIFY_DRAFT=%q\\n" in sh_common
    assert "find_feature_dir_from_lane_state" in sh_common
    assert "feature_specs_roots" in sh_common
    assert "Find-FeatureDirFromLaneState" in ps_common
    assert "Get-FeatureSpecsRoots" in ps_common
    assert '--arg context "$CONTEXT"' in sh_check
    assert '--feature-dir' in sh_check
    assert '--arg project_cognition_status "$(project_cognition_status_path "$REPO_ROOT")"' in sh_check
    assert '--arg project_cognition_helper "$(project_cognition_helper_path "$REPO_ROOT")"' in sh_check
    assert '"CONTEXT":"%s"' in sh_check
    assert '--arg context "$CONTEXT"' in sh_setup
    assert '--arg feature_dir "$FEATURE_DIR"' in sh_setup
    assert '"FEATURE_DIR":"%s"' in sh_setup
    assert '"CONTEXT":"%s"' in sh_setup


def test_project_map_refresh_guidance_uses_git_baseline_and_dirty_fallback():
    refresh_owned_surfaces = [
        "README.md",
        "docs/quickstart.md",
        "scripts/bash/update-agent-context.sh",
        "scripts/powershell/update-agent-context.ps1",
    ]

    stale_normal_path_phrases = [
        "should mark `.specify/project-cognition/status.json` dirty and run",
        "mark `.specify/project-cognition/status.json` dirty through the project cognition freshness helper and recommend",
        "prefer `specify-runtime cognition mark-dirty` as the shared dirty-mark path",
    ]
    for path in refresh_owned_surfaces:
        lowered = _read(path).lower()
        if path in {"README.md", "docs/quickstart.md"}:
            assert "advisory project cognition index" in lowered
            assert "advisory navigation inputs" in lowered
            assert "map points, code proves" in lowered
            assert "map-update" in lowered
            assert "map-scan" in lowered
            assert "map-build" in lowered
            if path == "README.md":
                assert "committing the refreshed source changes does not require a full rebuild by itself" in lowered
        else:
            assert "project cognition freshness truthful" in lowered
            assert "architecture" in lowered
            assert "ownership" in lowered
            assert "verification entry points" in lowered
        for phrase in stale_normal_path_phrases:
            assert phrase not in lowered

    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]:
        lowered = _read(path).lower()
        assert "cognition follow-up" in lowered
        assert "artifact-only" in lowered
        assert "actual source/runtime truth changes" in lowered
        assert "specify-runtime cognition complete-refresh" not in lowered

    for path in [
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/fast.md",
    ]:
        lowered = _read(path).lower()
        assert "project cognition runtime" in lowered
        assert "map-update" in lowered
        assert "specify-runtime cognition closeout-plan --workflow" in lowered
        assert "update_mode=delta_session" in lowered
        assert "dirty only when inline update cannot complete" in lowered
        assert "git-baseline freshness" not in lowered


def test_planning_only_workflows_do_not_dirty_project_cognition_after_artifact_writes():
    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]:
        lowered = _read(path).lower()

        assert "do not mark project cognition dirty" in lowered
        assert "specify-runtime cognition complete-refresh" not in lowered
        assert "specify-runtime cognition validate-build --format json" not in lowered
        assert "artifact-only" in lowered
        assert "cognition follow-up" in lowered
        assert "actual source/runtime truth changes" in lowered


def test_specify_plan_and_tasks_treat_needs_update_as_planning_advisory():
    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]:
        lowered = _read(path).lower()

        assert "specify-runtime cognition compass --intent plan" in lowered
        assert "minimal_live_reads" in lowered
        assert "planning advisories" in lowered
        assert "`needs_update`: route through `{{invoke:map-update}}`" not in lowered


def test_clarify_command_requires_persisted_clarification_lane_handoffs():
    content = _read("templates/commands/clarify.md")
    lowered = content.lower()

    assert "clarification/handoffs/<lane-id>.json" in content
    assert "clarification/evidence-index.json" in content
    assert "clarification/checkpoints.ndjson" in content
    assert "persist a `clarification_checkpoint` record" in lowered
    assert "persist the lane's structured handoff" in lowered
    assert "consume `clarification/evidence-index.json` before final artifact updates" in lowered
    assert "mark the handoff as `integrated`, `deferred`, or `blocked`" in lowered
    assert "without an explicit consuming artifact section, deferral, or blocker reason" in lowered
    assert "do not update `spec.md`, `alignment.md`, `context.md`, or `references.md` from chat-only lane results" in lowered


def test_analyze_command_consumes_canonical_contracts_and_lane_manifests():
    content = _read("templates/commands/analyze.md")
    lowered = content.lower()

    assert "SPEC_CONTRACT = FEATURE_DIR/spec-contract.json" in content
    assert "PLAN_CONTRACT = FEATURE_DIR/plan-contract.json" in content
    assert "TASK_INDEX = FEATURE_DIR/task-index.json" in content
    assert "PLANNING_LANE_MANIFEST = FEATURE_DIR/planning/lane-manifest.json when present" in content
    assert "TASK_GENERATION_LANE_MANIFEST = FEATURE_DIR/task-generation/lane-manifest.json when present" in content
    assert "read `planning/lane-manifest.json` and only the accepted lane results it names" in lowered
    assert "read `task-generation/lane-manifest.json` and only the accepted lane results it names" in lowered
    assert "accepted planning handoff with no downstream consumer as a plan-layer blocker" in lowered
    assert "accepted task-generation handoff with no downstream consumer as a task-layer blocker" in lowered


def test_specify_and_plan_treat_stale_cognition_as_planning_advisory():
    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
    ]:
        lowered = _read(path).lower()

        assert "`fresh`, `stale`, `possibly_stale`, `needs_update`, and `partial_refresh`" in lowered
        assert "planning advisories" in lowered
        assert "if freshness is `stale`, stop" not in lowered
        assert "if freshness is `stale`, stop and tell the user to run `{{invoke:map-update}}`" not in lowered
        assert "do not stop solely because the index is stale" in lowered
        assert "minimal_live_reads" in lowered


def test_project_map_freshness_scripts_exist_and_share_status_contract():
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")
    sh_freshness = _read("scripts/bash/project-map-freshness.sh")
    ps_freshness = _read("scripts/powershell/project-map-freshness.ps1")

    assert "project_map_status_path" in sh_common
    assert "Get-ProjectMapStatusPath" in ps_common

    assert "project_map_status_path" in sh_freshness
    assert "record-refresh" in sh_freshness
    assert "complete-refresh" in sh_freshness
    assert "mark-dirty" in sh_freshness
    assert "ORIGIN_COMMAND" in sh_freshness
    assert "dirty_origin_command" in sh_freshness
    assert "DIRTY_SCOPE_PATHS_JSON" in sh_freshness
    assert "dirty_scope_paths" in sh_freshness
    assert "clear-dirty" in sh_freshness
    assert '"freshness": "missing"' not in sh_freshness  # sanity: not hardcoded-only output
    assert "project-map status missing" in sh_freshness
    assert "high-impact compatibility/export change" in sh_freshness
    assert "git baseline unavailable for project-map compatibility/export freshness" in sh_freshness

    assert "Get-ProjectMapStatusPath" in ps_freshness
    assert "record-refresh" in ps_freshness
    assert "complete-refresh" in ps_freshness
    assert "mark-dirty" in ps_freshness
    assert "OriginCommand" in ps_freshness
    assert "dirty_origin_command" in ps_freshness
    assert "DirtyScopePathsJson" in ps_freshness
    assert "dirty_scope_paths" in ps_freshness
    assert "clear-dirty" in ps_freshness
    assert "project-map status missing" in ps_freshness
    assert "high-impact compatibility/export change" in ps_freshness
    assert "git baseline unavailable for project-map compatibility/export freshness" in ps_freshness


def test_project_cognition_freshness_scripts_are_launcher_backed_and_map_free():
    sh_freshness = _read("scripts/bash/project-cognition-freshness.sh")
    ps_freshness = _read("scripts/powershell/project-cognition-freshness.ps1")

    for content in (sh_freshness, ps_freshness):
        assert "specify-runtime" in content
        assert "SPECIFY_RUNTIME_BIN" in content
        assert ".specify/bin" in content
        assert ".specify/config.json" in content
        assert "runtime_launcher" in content
        assert "do not fall back" in content
        assert "integration repair" not in content
        assert ".specify/project-map" not in content
        assert "project-map-freshness" not in content
    assert "command -v node" in sh_freshness
    assert "command -v jq" in sh_freshness
    assert "awk '" in sh_freshness
    assert 'configured" == .specify/bin/*' in sh_freshness
    assert "cygpath -u" not in sh_freshness
    assert "wslpath -u" not in sh_freshness
    assert "command -v specify-runtime" not in sh_freshness
    assert "${SPECIFY_RUNTIME_BIN:-}" not in sh_freshness
    assert "[System.IO.Path]::IsPathRooted" not in ps_freshness
    assert "Get-Command specify-runtime" not in ps_freshness
    assert "$env:SPECIFY_RUNTIME_BIN" not in ps_freshness


def test_update_agent_context_emitters_share_managed_block_v2_contract() -> None:
    bash_script = _read("scripts/bash/update-agent-context.sh")
    powershell_script = _read("scripts/powershell/update-agent-context.ps1")

    bash_block = _extract_bash_managed_block(bash_script)
    powershell_block = _extract_powershell_managed_block(powershell_script)

    _assert_managed_block_v2_contract(bash_block)
    _assert_managed_block_v2_contract(powershell_block)


def test_plan_shell_requires_anchorable_headings():
    """plan shell.md must require anchorable section headings for downstream context pointers."""
    plan_shell = (PROJECT_ROOT / "templates" / "command-partials" / "plan" / "shell.md").read_text(encoding="utf-8")
    assert "anchorable" in plan_shell.lower()


def test_create_new_feature_scripts_scaffold_and_report_context():
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_create = _read("scripts/bash/create-new-feature.sh")

    assert "$contextFile = Join-Path $featureDir 'context.md'" in ps_create
    assert "$specifyDraftFile = Join-Path $featureDir 'specify-draft.md'" in ps_create
    assert "Resolve-Template -TemplateName 'context-template'" in ps_create
    assert "Resolve-Template -TemplateName 'specify-draft-template'" in ps_create
    assert "CONTEXT_FILE = $contextFile" in ps_create
    assert "SPECIFY_DRAFT_FILE = $specifyDraftFile" in ps_create
    assert "FEATURE_DIR = $featureDir" in ps_create
    assert "LANE_ID = $laneId" in ps_create
    assert "LANE_WORKTREE = $laneWorktree" in ps_create
    assert 'CONTEXT_FILE="$FEATURE_DIR/context.md"' in sh_create
    assert 'SPECIFY_DRAFT_FILE="$FEATURE_DIR/specify-draft.md"' in sh_create
    assert 'resolve_template "context-template"' in sh_create
    assert 'resolve_template "specify-draft-template"' in sh_create
    assert '"CONTEXT_FILE":"%s"' in sh_create
    assert '"SPECIFY_DRAFT_FILE":"%s"' in sh_create
    assert '"FEATURE_DIR":"%s"' in sh_create
    assert '"LANE_ID":"%s"' in sh_create
    assert '"LANE_WORKTREE":"%s"' in sh_create


def test_specify_draft_template_and_feature_scripts_scaffold_draft_artifact():
    draft_template = _read("templates/specify-draft-template.md")
    sh_create = _read("scripts/bash/create-new-feature.sh")
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")
    pyproject = _read("pyproject.toml")

    assert "# Specification Draft Ledger:" in draft_template
    assert "## Intent Analysis Record" in draft_template
    assert "## Domain Progress Ledger" in draft_template
    assert "## Question Batch Ledger" in draft_template
    assert "## Adversarial Review Ledger" in draft_template
    assert "## Completeness Gap Register" in draft_template
    assert "## Final Audit Inputs" in draft_template
    assert "SPECIFY_DRAFT_FILE" in sh_create
    assert "specify-draft-template" in sh_create
    assert "$specifyDraftFile = Join-Path $featureDir 'specify-draft.md'" in ps_create
    assert "Resolve-Template -TemplateName 'specify-draft-template'" in ps_create
    assert "SPECIFY_DRAFT=%q\\n" in sh_common
    assert "SPECIFY_DRAFT = Join-Path $featureDir 'specify-draft.md'" in ps_common
    assert '"templates/specify-draft-template.md" = "specify_cli/core_pack/templates/specify-draft-template.md"' in pyproject


def test_feature_scaffolding_and_packaging_include_brainstorming_truth_templates() -> None:
    pyproject = _read("pyproject.toml")
    sh_create = _read("scripts/bash/create-new-feature.sh")
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")

    for path in (
        "templates/brainstorming-facts-template.json",
        "templates/brainstorming-route-template.json",
        "templates/brainstorming-intent-template.json",
        "templates/brainstorming-complexity-template.json",
        "templates/brainstorming-handoff-specify-template.json",
    ):
        assert path in pyproject

    assert "BRAINSTORMING_FACTS" in sh_common
    assert "BRAINSTORMING_ROUTE" in sh_common
    assert "BRAINSTORMING_INTENT" in sh_common
    assert "BRAINSTORMING_COMPLEXITY" in sh_common
    assert "HANDOFF_TO_SPECIFY" in sh_common

    assert "BRAINSTORMING_FACTS" in ps_common
    assert "BRAINSTORMING_ROUTE" in ps_common
    assert "BRAINSTORMING_INTENT" in ps_common
    assert "BRAINSTORMING_COMPLEXITY" in ps_common
    assert "HANDOFF_TO_SPECIFY" in ps_common

    assert "brainstorming/facts.json" in sh_create
    assert "brainstorming/route.json" in sh_create
    assert "brainstorming/intent.json" in sh_create
    assert "brainstorming/complexity.json" in sh_create
    assert "handoff-to-specify.json" in sh_create

    assert "brainstorming\\facts.json" in ps_create or "brainstorming/facts.json" in ps_create
    assert "handoff-to-specify.json" in ps_create


def test_lossless_specify_state_templates_are_packaged_and_scaffolded() -> None:
    pyproject = _read("pyproject.toml")
    sh_create = _read("scripts/bash/create-new-feature.sh")
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")

    for path in (
        "templates/brainstorming-stage-manifest-template.json",
        "templates/brainstorming-domains-template.json",
        "templates/brainstorming-evidence-index-template.json",
        "templates/brainstorming-evidence-record-template.json",
    ):
        assert path in pyproject

    for token in (
        "BRAINSTORMING_JOURNAL",
        "BRAINSTORMING_STAGE_MANIFEST",
        "BRAINSTORMING_DOMAINS",
        "BRAINSTORMING_EVIDENCE_INDEX",
        "BRAINSTORMING_EVIDENCE_DIR",
    ):
        assert token in sh_common
        assert token in ps_common
        assert token in sh_create
        assert token in ps_create

    assert "brainstorming-stage-manifest-template" in sh_create
    assert "brainstorming-domains-template" in sh_create
    assert "brainstorming-evidence-index-template" in sh_create
    assert "brainstorming-evidence-record-template" in sh_create
    assert "brainstorming-stage-manifest-template" in ps_create
    assert "brainstorming-domains-template" in ps_create
    assert "brainstorming-evidence-index-template" in ps_create
    assert "brainstorming-evidence-record-template" in ps_create


def _legacy_brainstorming_handoff_template_supports_context_boundary_quality_gate_and_source_evidence_contract() -> None:
    template = json.loads(_read("templates/brainstorming-handoff-specify-template.json"))

    assert template["version"] == 2
    assert template["entry_source"] is None
    boundary = template.get("context_boundary")
    assert isinstance(boundary, dict)
    assert boundary.get("current_project_root") is None
    assert boundary.get("current_project_roles") == []
    assert boundary.get("target_project_root") is None
    assert boundary.get("target_project_roles") == []
    assert boundary.get("reference_projects") == []
    assert boundary.get("external_systems") == []
    assert boundary.get("path_status") == "unknown"
    assert boundary.get("boundary_confidence") == "unknown"
    assert boundary.get("boundary_unknowns") == []
    role_contract = boundary.get("role_object_contract")
    assert isinstance(role_contract, dict)
    assert role_contract.get("required_fields") == [
        "role",
        "scope",
        "evidence_source",
        "notes",
    ]
    implementation_target = template.get("implementation_target")
    assert isinstance(implementation_target, dict)
    assert implementation_target.get("target_root") is None
    assert implementation_target.get("target_paths") == []
    assert "current project cognition cannot prove another project's implementation facts" in (
        implementation_target.get("current_project_cognition_scope_note") or ""
    ).lower()
    assert template.get("source_evidence") == []
    source_evidence_contract = template.get("source_evidence_contract")
    assert isinstance(source_evidence_contract, dict)
    assert source_evidence_contract.get("required_fields") == [
        "source_type",
        "evidence_status",
        "source",
        "claim",
    ]
    assert source_evidence_contract.get("optional_fields") == [
        "project_cognition_route",
        "live_code_evidence",
        "needs_refresh",
        "notes",
    ]
    assert source_evidence_contract.get("allowed_source_types") == [
        "project_cognition_route",
        "live_code_evidence",
        "user_confirmation",
        "explicit_assumption",
        "external_source",
        "missing",
        "conflict",
    ]
    assert source_evidence_contract.get("allowed_evidence_statuses") == [
        "proven",
        "inferred",
        "stale-advisory",
        "missing",
        "conflict",
    ]
    assert (
        source_evidence_contract.get("authority_rule")
        == "Project cognition navigates; live repository evidence proves current behavior."
    )
    assert template.get("blocking_unknowns") == []
    downstream_instructions = template.get("downstream_instructions")
    assert isinstance(downstream_instructions, dict)
    assert downstream_instructions.get("capability_map") == []
    assert downstream_instructions.get("planning_constraints") == []
    assert "recommended_sequence" not in downstream_instructions
    assert downstream_instructions.get("deferred_scope") == []
    quality_gate = template.get("quality_gate")
    assert isinstance(quality_gate, dict)
    assert quality_gate.get("status") == "draft"
    assert quality_gate.get("user_review_required") is True
    assert quality_gate.get("user_confirmed_at") is None
    assert quality_gate.get("blocked_reasons") == []
    assert template.get("candidate_id") is None
    assert template.get("source_split_plan") is None


def test_specify_template_does_not_require_fixed_heavy_discovery_contract() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "two or three approaches" in lowered or "2-3 approaches" in lowered
    assert "semantic term" in lowered
    assert "user review" in lowered
    assert "content ledger for the whole discovery run" not in lowered
    assert "recent question-batch disposition" not in lowered
    assert "adversarial-review findings" not in lowered
    assert "reopen the current domain" not in lowered
    assert "completeness gaps" not in lowered


def test_specify_template_does_not_require_lossless_journal_stage_manifest_and_checkpoints() -> None:
    specify = _read("templates/commands/specify.md")
    shell = _read("templates/command-partials/specify/shell.md")
    workflow_state = _read("templates/workflow-state-template.md")
    handoff = _read("templates/brainstorming-handoff-specify-template.json")

    combined = "\n".join([specify, shell, workflow_state, handoff])
    for obsolete in (
        "brainstorming/journal.ndjson",
        "brainstorming/stage-manifest.json",
        "compiled_from",
        "facts_file",
        "route_file",
        "intent_file",
        "complexity_file",
        "journal replay wins",
        "Markdown is not a trusted recovery source",
    ):
        assert obsolete not in combined

    assert (
        "Create or resume `BRAINSTORMING_JOURNAL_FILE` and `BRAINSTORMING_STAGE_MANIFEST_FILE` "
        "immediately after `FEATURE_DIR` is known"
    ) not in shell
    assert "before relying on workflow-state, draft Markdown, or chat history" not in shell
    assert "brainstorming/handoff-to-specify.json" in specify
    assert "source_files_read" not in specify
    assert "source_signal_disposition" not in specify
    assert "decision digest" in specify.lower()
    assert "spec-contract.json" in specify
    assert "pointer-only agent transition" in specify.lower()
    assert "20. Apply `final-handoff-decision`." not in specify
    assert "until `final-handoff-decision` determines the appropriate next command" not in specify
    assert "Legacy compatibility wording: Only `final-handoff-decision`" not in specify
    assert "last_user_reviewed_artifact_state" in workflow_state

    for obsolete_stage in (
        "facts-lock",
        "route-lock",
        "intent-lock",
        "complexity-lock",
        "release-decision",
    ):
        assert obsolete_stage not in workflow_state
        assert obsolete_stage not in specify


def test_specify_template_uses_compatibility_handoff_without_brainstorming_lock_flow() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "brainstorming/handoff-to-specify.json" in content
    assert "source_signal_disposition" not in content
    assert "decision digest" in content.lower()
    assert "source_files_read" not in content
    assert "coverage_status" in content
    assert "planning_gate_status" in content
    assert "hard_unknown_count" in content
    assert "open_conflict_count" in content
    assert "source_contract" in content
    assert "semantic_delta" in content
    assert "read the canonical contract once" in lowered
    assert "brainstorming kernel" not in lowered
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content
    assert "brainstorming/facts.json" not in content
    assert "brainstorming/route.json" not in content
    assert "brainstorming/intent.json" not in content
    assert "brainstorming/complexity.json" not in content


def test_specify_artifact_templates_use_semantic_traceability_not_route_complexity_locks() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")

    assert "Confirmed Scope" in spec
    assert "Acceptance Proof" in spec
    assert "Semantic Term Decisions" in alignment
    assert "Upstream Intent Disposition" in alignment
    assert "Out-Of-Scope Conflicts" in alignment
    assert "Planning Context" in context
    assert "Canonical References" in context

    combined = "\n".join([spec, alignment, context, references])
    assert "## Brainstorming Truth Inputs" not in combined
    assert "**Locked route**" not in combined
    assert "`brainstorming/route.json`" not in combined
    assert "**Locked complexity**" not in combined
    assert "`brainstorming/complexity.json`" not in combined
    assert "## Route And Complexity Summary" not in combined
    assert "## Brainstorming-Derived Execution Context" not in combined
    assert "## Truth Sources Used For Route And Intent Lock" not in references


def test_compiled_artifact_templates_do_not_require_lossless_source_maps() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")
    checklist = _read("templates/checklist-template.md")

    for content in (spec, alignment, context, references, checklist):
        assert "Lossless Source Map" not in content
        assert "brainstorming/journal.ndjson" not in content
        assert "brainstorming/stage-manifest.json" not in content
        assert "EVT-" not in content
        assert "EVD-" not in content
        assert "`compiled_from`" not in content


def test_compiled_artifact_templates_preserve_must_preserve_ids() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")

    assert "Must-Preserve" in spec
    assert "MP-" in spec
    assert "Must-Preserve" in alignment
    assert "MP-" in alignment
    assert "Must-Preserve" in context
    assert "MP-" in context
    assert "Must-Preserve" in references
    assert "MP-" in references


def test_specify_plan_tasks_artifact_templates_preserve_consequence_analysis() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")
    plan = _read("templates/plan-template.md")
    tasks = _read("templates/tasks-template.md")

    for content in (spec, alignment, context, references, plan, tasks):
        lowered = content.lower()
        assert "consequence" in lowered
        assert "ca-###" in lowered or "ca-*" in lowered

    assert "Lifecycle And State Behavior" in spec
    assert "Consequence Completeness" in alignment
    assert "Affected Object Map" in context
    assert "Consequence Evidence" in references
    assert "Operational Consequence Design" in plan
    assert "Consequence Obligation Mapping" in tasks


def _legacy_structured_consequence_json_templates_exist() -> None:
    for rel_path in (
        "templates/brainstorming-handoff-specify-template.json",
        "templates/plan-contract-template.json",
        "templates/task-index-template.json",
        "templates/task-packet-template.json",
        "templates/implement-execution-state-template.json",
    ):
        _assert_consequence_json_contract(_read(rel_path))


def test_plan_tasks_and_implement_templates_consume_structured_handoff_contracts() -> None:
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")

    assert "spec-contract.json" in plan
    assert "plan-contract.json" in plan
    assert "plan-contract.json" in tasks
    assert "task-index.json" in tasks
    assert "task-index.json" in implement
    assert "task lifecycle record" in implement.lower()
    assert "stop/reopen" in implement.lower()


def test_plan_tasks_and_implement_preserve_discussion_fidelity_obligations() -> None:
    plan = _read("templates/commands/plan.md")
    plan_template = _read("templates/plan-template.md")
    tasks = _read("templates/commands/tasks.md")
    tasks_template = _read("templates/tasks-template.md")
    implement = _read("templates/commands/implement.md")
    implement_shell = _read("templates/command-partials/implement/shell.md")

    for content in (plan, plan_template, tasks, tasks_template, implement, implement_shell):
        lowered = content.lower()
        assert "mp-*" in lowered or "MP-" in content
        assert "must-preserve" in lowered
        assert "conflict" in lowered

    assert "Must-Preserve Carry-Forward" in plan_template
    assert "Task Contract Mapping" in tasks_template
    assert "task-index.json" in tasks_template
    assert "WorkerTaskPacket" in implement
    assert "result handoff" in implement_shell.lower()


def test_plan_template_rejects_cross_project_handoff_without_target_context() -> None:
    plan = _read("templates/commands/plan.md")
    shell = _read("templates/command-partials/plan/shell.md")
    plan_template = _read("templates/plan-template.md")
    contract = json.loads(_read("templates/plan-contract-template.json"))
    combined = "\n".join([plan, shell, plan_template])
    lowered = combined.lower()

    assert "implementation target" in lowered
    assert "locked target boundary" in lowered
    assert "hard unknowns" in lowered
    assert "current project cognition" in lowered
    assert "cannot prove target-project implementation facts" in lowered
    assert "minimal live reads in the target" in lowered
    assert contract.get("implementation_target_ref") is None


def test_tasks_template_inherits_implementation_target_boundary() -> None:
    tasks = _read("templates/commands/tasks.md")
    shell = _read("templates/command-partials/tasks/shell.md")
    task_template = _read("templates/tasks-template.md")
    packet = json.loads(_read("templates/task-packet-template.json"))
    combined = "\n".join([tasks, shell, task_template])
    lowered = combined.lower()

    assert "target boundary" in lowered
    assert "mp-*" in lowered
    assert "boundary constraints" in lowered
    assert "forbidden drift" in lowered
    assert "silently falls back to the current repository" in lowered
    assert "reference-only" in lowered
    assert packet.get("implementation_target_ref") is None
    assert packet.get("authoritative_refs") == []
    assert packet.get("forbidden_drift") == []


def test_tasks_template_ui_fidelity_levels_match_packet_schema() -> None:
    task_template = _read("templates/tasks-template.md")
    match = re.search(
        r"\| T### \| \[manual check[^\n]*\| \[(?P<levels>[^\]]+)\] \| "
        r"\[command, screenshot, or human review when needed\] \|",
        task_template,
    )

    assert match, "tasks template must advertise packet UI fidelity levels"
    advertised_levels = {
        level.strip(" `").lower()
        for level in match.group("levels").split("|")
        if level.strip()
    }
    supported_levels = set(get_args(UIFidelityLevel))

    assert supported_levels <= advertised_levels
    assert advertised_levels == supported_levels
    assert not (advertised_levels & {"low", "medium", "not_applicable"})


def test_ui_task_specific_templates_require_active_fidelity() -> None:
    task_template = _read("templates/tasks-template.md")
    classic_match = re.search(
        r"(?m)^\| fidelity_level \| \[(?P<levels>[^\]]+)\] \|$",
        task_template,
    )
    assert classic_match, "tasks template must render task-local UI fidelity"
    classic_levels = {
        level.strip(" `").lower()
        for level in classic_match.group("levels").split("|")
        if level.strip()
    }

    advanced_markdown = _read(
        "templates/advanced-skills/spx-tasks/assets/ui-task.md"
    )
    advanced_match = re.search(
        r"(?m)^\| fidelity_level \| \{\{(?P<levels>[^}]+)\}\} \|$",
        advanced_markdown,
    )
    assert advanced_match, "SPX UI task asset must render task-local fidelity"
    advanced_markdown_levels = set(advanced_match.group("levels").split("_or_"))

    advanced_json = json.loads(
        _read("templates/advanced-skills/spx-tasks/assets/ui-task-index-entry.json")
    )
    advanced_json_levels = set(
        advanced_json["ui_contract"]["fidelity_level"]
        .strip("{}")
        .split("_or_")
    )

    expected_active_levels = {"approximate", "high", "inspiration"}
    assert classic_levels == expected_active_levels
    assert advanced_markdown_levels == expected_active_levels
    assert advanced_json_levels == expected_active_levels


def test_structured_json_templates_preserve_fidelity_status_fields() -> None:
    spec_contract = json.loads(_read("templates/spec-contract-template.json"))
    plan_contract = json.loads(_read("templates/plan-contract-template.json"))
    task_index = json.loads(_read("templates/task-index-template.json"))
    task_packet = json.loads(_read("templates/task-packet-template.json"))
    task_lifecycle = json.loads(_read("templates/task-lifecycle-template.json"))
    implement_state = json.loads(
        _read("templates/implement-execution-state-template.json")
    )

    assert "design_contract" in spec_contract
    assert "ui_applicable" in spec_contract["design_contract"]
    assert "ui_brief_ref" in spec_contract["design_contract"]
    assert "ui_contract_version" not in spec_contract["design_contract"]
    assert "approved_visual_ref" in spec_contract["design_contract"]
    assert "reference_intents" in spec_contract["design_contract"]
    assert "real_content_plan" in spec_contract["design_contract"]
    assert "image_plan" in spec_contract["design_contract"]
    assert "required_evidence" in spec_contract["design_contract"]
    assert "visual_acceptance" in spec_contract["design_contract"]
    assert "must_preserve_refs" in spec_contract
    assert "ui_design_contract" in plan_contract
    assert "ui_brief_ref" in plan_contract["ui_design_contract"]
    assert "ui_contract_version" not in plan_contract["ui_design_contract"]
    assert "human_review_conditions" in plan_contract["ui_design_contract"]
    assert "must_preserve_refs" in plan_contract
    assert "fidelity_refs" in task_index
    assert task_index["ui_contract_schema_ref"].endswith("#/ui_contract")
    assert "ui_contract" in task_packet
    assert "contract_version" not in task_packet["ui_contract"]
    assert "surface_type" in task_packet["ui_contract"]
    assert "approved_visual_ref" in task_packet["ui_contract"]
    assert "ui_fidelity_requirements" not in task_packet
    assert "ui_verification" in task_lifecycle
    assert "evidence" in task_lifecycle["ui_verification"]
    assert "evidence_refs" not in task_lifecycle["ui_verification"]
    assert task_lifecycle["ui_verification"]["evidence_scope"] == "integrated"
    assert task_lifecycle["ui_verification"]["applicable"] is False
    assert "required_obligation_refs" in implement_state


def test_implement_template_rejects_locked_goal_redefinition() -> None:
    implement = _read("templates/commands/implement.md").lower()

    assert "task-index.json" in implement
    assert "protected requirement" in implement
    assert "user decision" in implement
    assert "stop and route to the owning upstream phase" in implement


def test_implement_template_requires_actionable_blocked_closeout() -> None:
    implement = _read("templates/commands/implement.md")
    shell = _read("templates/command-partials/implement/shell.md")
    combined = "\n".join([implement, shell])
    lowered = combined.lower()

    assert "actionable blocker resolution" in lowered
    assert "owner: agent | user | maintainer | external-system" in lowered
    assert "exact_next_action" in lowered
    assert "unblock_criteria" in lowered
    assert "approval_question" in lowered
    assert "verification_policy" in lowered
    assert "do not leave the user to infer whether to handle the blocker" in lowered


def test_implement_execution_state_template_requires_structured_execution_contract_from_tasks() -> None:
    content = _read("templates/implement-execution-state-template.json")

    assert '"status": "gathering"' in content
    assert '"current_batch": null' in content
    assert '"source_contract": "task-index.json"' in content
    assert '"source_revision": null' in content
    assert '"current_task": null' in content
    assert '"completed_task_ids": []' in content
    assert '"failed_task_ids": []' in content
    assert '"required_obligation_refs": []' in content
    assert '"blockers": []' in content


def test_implement_execution_state_template_includes_embedded_review_defaults() -> None:
    payload = json.loads(_read("templates/implement-execution-state-template.json"))

    assert payload["last_review_event"] is None
    assert payload["review_window_policy"] == {
        "max_completed_tasks_before_review": 5,
        "max_unreviewed_changed_paths": 8,
        "max_unreviewed_validation_failures": 0,
    }


def test_specify_template_uses_simplified_collaborative_spec_flow() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "2-3 approaches" in lowered or "two or three approaches" in lowered
    assert "semantic term" in lowered
    assert "user review" in lowered
    assert "source_signal_disposition" not in content
    assert "capability operations" in content.lower()
    assert "spec-contract.json" in content
    assert "semantic_delta" in content
    assert "compile mode" in lowered
    assert "brainstorming/handoff-to-specify.json" in content
    assert "checklists/requirements.md" in content
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content
    assert "brainstorming/journal.ndjson" not in content
    assert "stage-manifest.json" not in content


def test_specify_artifact_templates_use_semantic_traceability_surfaces() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    workflow_state = _read("templates/workflow-state-template.md")
    checklist = _read("templates/checklist-template.md")

    assert "Semantic Term Decisions" in alignment
    assert "Upstream Intent Disposition" in alignment
    assert "Out-Of-Scope Conflicts" in alignment
    assert "User Confirmation" in alignment
    assert "Confirmed Scope" in spec
    assert "Acceptance Proof" in spec
    assert "Planning Context" in context
    assert "last_user_reviewed_artifact_state" in workflow_state
    assert "checklists/requirements.md" in _read("templates/commands/specify.md")

    combined = "\n".join([spec, alignment, context, workflow_state, checklist])
    assert "brainstorming/journal.ndjson" not in combined
    assert "stage-manifest.json" not in combined
    assert "`compiled_from`" not in combined


def test_specify_artifact_templates_preserve_discussion_decision_digest() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    handoff = json.loads(_read("templates/discussion-handoff-template.json"))
    combined = "\n".join([spec, alignment, context])
    lowered = combined.lower()

    assert "Discussion Decision Digest" in alignment
    assert "Locked Direction" in alignment
    assert "Rejected Alternatives" in alignment
    assert "Accepted Tradeoffs" in alignment
    assert "Experience Commitments" in alignment
    assert "Review Criteria Carry-Forward" in alignment
    assert "Must Not Dilute" in alignment

    assert "Discussion Decision Digest" in spec
    assert "Selected Direction" in spec
    assert "Rejected Alternatives" in spec
    assert "Accepted Tradeoffs" in spec
    assert "Experience Commitments" in spec
    assert "Review Criteria Carry-Forward" in spec

    assert "Discussion Decision Carry-Forward" in context
    assert "Experience Commitments" in context
    assert "Must Not Dilute" in context

    assert "selected direction" in lowered
    assert "rejected alternatives" in lowered
    assert "accepted tradeoffs" in lowered
    assert "review criteria" in lowered
    assert "ui/tui" in lowered or "ui" in lowered

    digest = handoff.get("discussion_decision_digest")
    assert isinstance(digest, dict)
    assert digest.get("locked_direction") == []
    assert digest.get("rejected_alternatives") == []
    assert digest.get("accepted_tradeoffs") == []
    assert digest.get("experience_commitments") == []
    assert digest.get("review_criteria_carried_forward") == []
    assert digest.get("must_not_dilute") == []


def test_agent_file_template_keeps_project_specific_context_only():
    content = _read("templates/agent-file-template.md")
    lowered = content.lower()

    assert "## Active Technologies" in content
    assert "## Project Structure" in content
    assert "## Commands" in content
    assert "## Code Style" in content
    assert "## Recent Changes" in content
    assert "## Command Surface Rules" not in content
    assert "## Workflow Recovery Rules" not in content
    assert "workflow routing" not in lowered


def test_prd_scan_template_uses_shared_subagent_dispatch_contract() -> None:
    content = _read("templates/commands/prd-scan.md")
    _assert_subagent_dispatch_contract(content, "prd-scan")


def test_prd_build_template_uses_shared_subagent_dispatch_contract() -> None:
    content = _read("templates/commands/prd-build.md")
    _assert_subagent_dispatch_contract(content, "prd-build")


def test_implement_template_requires_structured_execution_contract_from_tasks() -> None:
    implement = _read("templates/commands/implement.md").lower()

    assert "task-index.json" in implement
    assert "required refs" in implement
    assert "protected requirement" in implement
    assert "stop and route to the owning upstream phase" in implement


def test_ui_reference_artifact_templates_define_strict_formats() -> None:
    def _h2_headings(markdown: str) -> list[str]:
        return [
            line.strip() for line in markdown.splitlines() if line.startswith("## ")
        ]

    notes = _read("templates/ui-reference-notes-template.md")
    brief = _read("templates/ui-brief-template.md")
    specify = _read("templates/commands/specify.md")
    target = _read("templates/ui-target-template.html")
    target_lower = target.lower()
    specify_lower = specify.lower()

    assert _h2_headings(notes) == [
        "## Reference Inputs",
        "## Fidelity Mode",
        "## Ownership And Reuse Constraints",
        "## Visual Facts",
        "## Layout Facts",
        "## Density And Visible Data",
        "## Component Facts",
        "## State Facts",
        "## Interaction Facts",
        "## Responsive Facts",
        "## Must Preserve Candidates",
        "## Adaptation Candidates",
        "## Risks And Gaps",
    ]

    assert _h2_headings(brief) == [
        "## Source Design System",
        "## Experience Core",
        "## Approved Direction",
        "## Reference Inputs",
        "## Fidelity Contract",
        "## Screen Structure",
        "## Information Hierarchy",
        "## Real Content And Imagery",
        "## Components And States",
        "## Interactions",
        "## Responsive Behavior",
        "## Color Modes And Content Stress",
        "## Accessibility And Keyboard Requirements",
        "## Must Preserve",
        "## May Adapt",
        "## Must Not",
        "## Required Evidence",
        "## Worker Contract",
    ]

    assert "<!doctype html>" in target_lower
    assert 'data-ui-target-schema="spec-kit-ui-target-v1"' in target
    assert 'data-fidelity="__FIDELITY_MODE__"' in target
    assert 'data-width="1440"' in target
    assert 'data-width="390"' in target
    assert 'data-state="empty"' in target
    assert 'data-state="error"' in target
    assert "spec-kit-ui-target-manifest-v1" in target
    assert 'id="ui-target-manifest"' in target
    assert "<script" in target_lower
    assert "URLSearchParams" in target
    assert "location.hash" in target
    assert "addEventListener" in target
    assert not re.search(r"\son[a-z]+\s*=", target_lower)
    assert "<link" not in target_lower
    assert "@import" not in target_lower
    assert "src=" not in target_lower
    assert "href=" not in target_lower
    assert "url(" not in target_lower
    assert "http://" not in target_lower
    assert "https://" not in target_lower
    assert "cdn" not in target_lower
    assert "ui-target-lint" in specify
    assert "bounded inline JavaScript" in specify
    assert "no inline event-handler" in specify
    assert "onclick" in specify_lower
    assert "external CSS/JS" in specify
    assert "network calls" in specify
    assert "persistence" in specify
    assert "production-source claim" in specify
