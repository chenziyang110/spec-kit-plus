import re
from pathlib import Path

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


def _read(path: str) -> str:
    return read_template(path)


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


def test_core_sp_templates_use_learning_review_hooks():
    command_templates_with_signal = {
        "specify": "templates/commands/specify.md",
        "clarify": "templates/commands/clarify.md",
        "deep-research": "templates/commands/deep-research.md",
        "plan": "templates/commands/plan.md",
        "tasks": "templates/commands/tasks.md",
        "analyze": "templates/commands/analyze.md",
        "test-scan": "templates/commands/test-scan.md",
        "test-build": "templates/commands/test-build.md",
        "implement": "templates/commands/implement.md",
        "debug": "templates/commands/debug.md",
        "map-scan": "templates/commands/map-scan.md",
        "map-build": "templates/commands/map-build.md",
    }

    for command_name, template_path in command_templates_with_signal.items():
        content = _read(template_path)
        assert f"{{{{specify-subcmd:hook signal-learning --command {command_name} ...}}}}" in content
        assert f"{{{{specify-subcmd:hook review-learning --command {command_name}" in content

    quick_content = _read("templates/commands/quick.md")
    assert "{{specify-subcmd:learning start --command quick --format json}}" in quick_content or "Passive Project Learning Layer" in quick_content
    assert "{{specify-subcmd:hook review-learning --command quick --terminal-status <resolved|blocked> ...}}" in quick_content or "Before final completion or blocked reporting" in quick_content

    fast_content = _read("templates/commands/fast.md")
    assert "{{specify-subcmd:learning capture --command fast ...}}" in fast_content


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
        "templates/commands/test-scan.md": ["/sp-test-build", "/sp.specify", "/sp.quick", "/sp.fast"],
        "templates/commands/test-build.md": [
            "/sp.specify",
            "/sp.plan",
            "/sp.tasks",
            "/sp.implement",
            "/sp.debug",
            "/sp-test-build",
        ],
    }

    assert len(task3_owned_handoffs) == 8

    for template_path, expected_fragments in task3_owned_handoffs.items():
        content = _read(template_path)
        for expected_fragment in expected_fragments:
            _assert_default_handoff_contract(content, expected_fragment)

    for template_path in ("templates/commands/test-scan.md", "templates/commands/test-build.md"):
        content = _read(template_path)
        assert "/sp.test-build" not in content
        assert "/sp.test-scan" not in content


def test_project_learning_skill_documents_product_level_hooks():
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md")

    assert "First-Party Learning Hooks" in content
    assert "{{specify-subcmd:hook signal-learning" in content
    assert "{{specify-subcmd:hook review-learning" in content
    assert "{{specify-subcmd:hook capture-learning" in content
    assert "{{specify-subcmd:hook inject-learning" in content
    assert "tooling_trap" in content
    assert "map_coverage_gap" in content
    assert "Do NOT" in content


def test_specify_template_uses_alignment_first_contract():
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "PROJECT-HANDBOOK.md" in content
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
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "{{specify-subcmd:learning start --command specify --format json}}" in content
    assert "{{specify-subcmd:learning capture --command specify ...}}" in content
    assert ".specify/project-map/index/status.json" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" in content
    assert ".specify/project-map/root/STRUCTURE.md" in content
    assert ".specify/project-map/root/WORKFLOWS.md" in content
    assert "Treat `PROJECT-HANDBOOK.md` as the root navigation artifact" in content
    assert "Use `Topic Map` to choose the smallest relevant topical documents" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before continuing" in content
    assert ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md" in content
    assert "primary brownfield testing-program input" in content
    assert "module priority waves" in content
    assert "small / medium / large" in lowered
    assert "project-map freshness helper" in lowered
    assert "freshness is `missing` or `stale`" in lowered
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

    assert "## Scenario Profile Routing" in content
    assert "active_profile" in content
    assert "routing_reason" in content
    assert "Reference-Implementation" in content
    assert "Standard Delivery" in content
    assert "Debug / Repair" in content
    assert "Brownfield Enhancement" in content
    assert "If the success criterion is fidelity to a reference object" in content
    assert "persist at least these fields for the active pass" in lowered
    assert "required_sections" in content
    assert "activated_gates" in content
    assert "`active_profile` must always be the supported profile whose obligations are persisted downstream" in content
    assert "record the inferred unsupported taxonomy profile separately from `active_profile`" in content
    assert "surface every profile narrowing to the user and allow correction before proceeding" in lowered
    assert re.search(r"`Standard Delivery`:\s+- `required_sections`:", content)
    assert re.search(r"`Standard Delivery`:[\s\S]*?- `transition_policy`: permit `/sp\.plan`", content)
    assert re.search(r"`Reference-Implementation`:\s+- `required_sections`:", content)
    assert re.search(r"`Reference-Implementation`:[\s\S]*?- `transition_policy`: permit `/sp\.plan` only", content)

    assert "alignment.md" in content
    assert "aligned: ready for plan" in lowered
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "Task Classification" in content or "task classification" in lowered
    assert "user's current language" in lowered
    assert "Business Goals" in content
    assert "Users & Roles" in content
    assert "Technical Constraints / Assumptions" in content
    assert "Outstanding Questions" in content
    assert "Default to concise clarification turns" in content
    assert "Do not restate the full current understanding after every answer" in content
    assert "Save the full synthesis for the alignment-ready turn" in content
    assert "Treat the shared open question block structure below as fallback-only text format guidance" in content
    assert "before generating any clarification question, confirmation, or bounded selection, check whether a native structured question tool is available" in lowered
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
    assert "first-release scope" in lowered
    assert "mvp scope" not in lowered
    _assert_subagent_dispatch_contract(content, "specify")
    assert "repository and local context analysis" in lowered
    assert "external references and supporting material analysis" in lowered
    assert "ambiguity, risk, and gap analysis" in lowered
    assert "before capability decomposition" in lowered
    assert "before writing `spec.md`, `alignment.md`, and `context.md`" in content
    assert "specify team" not in lowered
    assert "Docs/config/process change:" in content
    assert "compatibility/process constraints" in content
    assert "completion criteria" in content
    assert "Task classification changes which requirement dimensions are probed" in content
    assert "impacted surfaces and consumers" in content
    assert "affected surfaces and change-propagation path" in content
    assert "affected surfaces and compatibility boundaries" in content
    assert "impacted surfaces and change-propagation expectations" in content
    assert "verification entry points and minimum evidence expectations" in content
    assert "known unknowns or stale evidence boundaries that could change planning safety" in content
    assert "planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria" in content
    assert "Make the next question build directly on the user's most recent answer" in content
    assert "rather than resetting to generic prompts" in content
    assert "vague, shallow, or contradictory" in content
    assert "targeted narrowing question, example, or recommendation" in content
    assert "Do not accept long but still ambiguous answers as sufficient." in content
    assert "Do not turn this into a freeform brainstorming workflow." in content
    assert "guided requirement discovery" in lowered
    assert "recommendation and example scaffolding" in lowered
    assert "current-understanding or confirmation gate" in lowered
    assert "confirm or correct the current understanding before `Aligned: ready for plan`" in content
    assert "Identify 3-5 planning-relevant gray areas" in content
    assert "Derive gray areas from the combination of user intent, `PROJECT-HANDBOOK.md`, and targeted repository evidence" in content
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


def test_core_planning_templates_use_logical_atlas_references() -> None:
    for rel_path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/implement.md",
    ]:
        content = _read(rel_path)
        lowered = content.lower()
        assert "atlas.entry" in lowered
        assert "atlas.index.status" in lowered
        assert "atlas.index.atlas" in lowered
        assert "at least one relevant root topic document" in lowered
        assert "at least one relevant module overview document" in lowered


def test_project_map_root_templates_document_scenario_profile_contracts() -> None:
    workflows = _read("templates/project-map/root/WORKFLOWS.md").lower()
    testing = _read("templates/project-map/root/TESTING.md").lower()

    assert "scenario profile" in workflows
    assert "standard delivery" in workflows
    assert "reference-implementation" in workflows
    assert "profile routing" in workflows
    assert "sp-specify -> sp-plan -> sp-tasks -> sp-implement" in workflows

    assert "profile-matched evidence" in testing
    assert "reference fidelity" in testing
    assert "standard delivery" in testing
    assert "reference-implementation" in testing


def test_constitution_template_uses_current_shared_context_and_reentry_contract() -> None:
    content = _read("templates/commands/constitution.md")
    lowered = content.lower()

    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "{{specify-subcmd:learning start --command constitution --format json}}" in content
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/index/status.json" in content
    assert "`/sp-map-scan` followed by `/sp-map-build`" in content
    assert "workflow-state.md" in content
    assert "/sp-plan" in content
    assert "/sp-tasks" in content
    assert "/sp-analyze" in content
    assert "active_command: sp-constitution" in lowered
    assert "phase_mode: planning-only" in lowered
    assert "{{specify-subcmd:hook validate-state --command constitution --feature-dir \"$feature_dir\"}}" in lowered
    assert "{{specify-subcmd:hook validate-artifacts --command constitution --feature-dir \"$feature_dir\"}}" in lowered
    assert "{{specify-subcmd:hook checkpoint --command constitution --feature-dir \"$feature_dir\"}}" in lowered
    assert "highest affected downstream stage" in lowered
    assert "do not always hand off directly to `/sp-specify`" in lowered
    assert "active `spec.md`, `plan.md`, `tasks.md`, or `workflow-state.md`" in content
    assert "project rules or learnings that conflict with the amended constitution" in lowered
    assert "mark the related handbook/project-map surface for refresh" in lowered
    assert "if the navigation system is missing or stale for an existing codebase" in lowered


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


def test_plan_template_requires_alignment_report_before_planning():
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    assert "PROJECT-HANDBOOK.md" in content
    assert "workflow-state.md" in content
    assert "WORKFLOW_STATE_FILE" in content
    assert "Read `templates/workflow-state-template.md`" in content
    assert "Create or resume `WORKFLOW_STATE_FILE` before substantial planning analysis." in content
    assert "phase_mode: design-only" in content
    assert "Do not implement code, edit source files, edit tests, or treat planning as implicit permission to start execution." in content
    assert "When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding." in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "{{specify-subcmd:learning start --command plan --format json}}" in content
    assert "{{specify-subcmd:learning capture --command plan ...}}" in content
    assert ".specify/project-map/index/status.json" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" in content
    assert ".specify/project-map/root/STRUCTURE.md" in content
    assert ".specify/project-map/root/WORKFLOWS.md" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before continuing" in content
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
    assert "Add `Implementation Constitution` whenever one or more of these heuristics is true" in content
    assert "established framework-owned boundary or adapter pattern" in content
    assert "native bridge, plugin surface, protocol seam, generated API surface" in content
    assert "generic implementation instinct would likely drift away" in content
    assert "canonical boundary files or examples" in content
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
    _assert_subagent_dispatch_contract(content, "plan")
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
    assert "mark `.specify/project-map/index/status.json` dirty" in lowered
    assert "recommend `/sp-map-scan` followed by `/sp-map-build`" in content
    assert "specify team" not in lowered
    assert "specify -> clarify -> plan" not in lowered


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
    assert "technical background" in lowered
    assert "execution constraints" in lowered
    assert "consumed research.md" in lowered
    assert "background reading" in lowered


def test_tasks_template_documents_shared_routing_before_decomposition():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "PROJECT-HANDBOOK.md" in content
    assert "workflow-state.md" in content
    assert "WORKFLOW_STATE_FILE" in content
    assert "Read `templates/workflow-state-template.md`" in content
    assert "Create or resume `WORKFLOW_STATE_FILE` before substantial task-generation analysis." in content
    assert "phase_mode: task-generation-only" in content
    assert "Do not implement code, edit source files, edit tests, or treat task generation as permission to start execution." in content
    assert "When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding." in content
    assert ".specify/project-map/root/ARCHITECTURE.md" in content
    assert ".specify/project-map/root/STRUCTURE.md" in content
    assert ".specify/project-map/root/WORKFLOWS.md" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert ".specify/memory/constitution.md" in content
    _assert_subagent_dispatch_contract(content, "tasks")
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
    assert "Locked Planning Decisions" in content
    assert "Decision Preservation Check" in content
    assert "quickstart.md exists: extract validation scenarios" in lowered
    assert "validate decision preservation" in lowered
    assert "instead of silently dropping it" in lowered
    assert "top-level tasks should usually fit one bounded implementation slice" in lowered
    assert "roughly 10-20 minutes" in lowered
    assert "subagent can still execute the task internally through smaller 2-5 minute atomic steps" in lowered
    assert "stop decomposition once the current executable window is atomic" in lowered
    assert "leave later phases at the coarser story or phase level" in lowered
    assert "grouped parallelism is the default" in lowered
    assert "pipeline is preferred when outputs flow linearly from one bounded lane to the next" in lowered
    assert "every pipeline stage still needs an explicit checkpoint" in lowered
    assert "classify_review_gate_policy(workload_shape)" in content
    assert "high-risk review checkpoint" in lowered
    assert "peer-review lane is available" in lowered
    assert "Planning inputs section" in content
    assert "before writing `tasks.md`" in content
    assert "before emitting canonical parallel batches and join points" in lowered
    assert "mark `.specify/project-map/index/status.json` dirty" in lowered
    assert "recommend `/sp-map-scan` followed by `/sp-map-build`" in content
    assert "specify team" not in lowered


def test_explain_template_documents_conservative_routing_contract():
    content = _read("templates/commands/explain.md")
    lowered = content.lower()

    assert ".specify/memory/constitution.md" in content
    _assert_subagent_dispatch_contract(content, "explain")
    assert "leader may render the explanation directly" in lowered
    assert "primary artifact reading" in lowered
    assert "supporting artifact cross-check" in lowered
    assert "before rendering the final explanation" in lowered
    assert "handbook, `project-handbook.md`, `project-map`, `architecture`, `structure`, `conventions`, `integrations`, `workflows`, `testing`, or `operations`" in lowered
    assert "explain the architecture or atlas artifact directly instead of forcing a planning-stage fallback" in lowered
    assert "verified facts, inferred relationships, important unknowns, and the next relevant atlas view" in lowered
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
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/index/status.json" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" in content
    assert ".specify/project-map/root/STRUCTURE.md" in content
    assert ".specify/project-map/root/WORKFLOWS.md" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "(`spec.md`, `context.md`, `plan.md`, `tasks.md`)" in content
    assert "- CONTEXT = FEATURE_DIR/context.md" in content
    assert ".specify/memory/constitution.md" in content
    assert "Read `PROJECT-HANDBOOK.md`" in content
    assert "Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`" in content
    assert "**From context.md:**" in content
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
    assert "| BG1 | Boundary Guardrail Gap | HIGH |" in content
    assert "| BG2 | Boundary Guardrail Gap | HIGH |" in content
    assert "| BG3 | Boundary Guardrail Gap | HIGH |" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content
    assert "Boundary Signal" in content
    assert "Seen In Plan Constitution?" in content
    assert "Boundary Guardrail Gap Count" in content
    assert "If a `Boundary Guardrail Gap` exists" in content
    assert "recommend `{{invoke:plan}}` to add `Implementation Constitution`" in content
    assert "If `BG2` exists" in content
    assert "If `BG3` exists" in content
    assert "Closed-loop requirement" in content
    assert "Recommended Next Command" in content
    assert "### 9. Define Workflow Re-entry" in content
    assert "Recommended Re-entry" in content
    assert "If the highest-impact issue lives in `spec.md` or `context.md`" in content
    assert "If the highest-impact issue lives in `plan.md`" in content
    assert "If the highest-impact issue lives only in `tasks.md`" in content
    assert "If the constitution itself must change" in content
    assert "`next_command: /sp.constitution`" in content
    assert "If analysis runs after the canonical `/sp.implement` workflow has already started or finished" in content
    assert "exact workflow re-entry path" in content


def test_analyze_template_separates_canonical_state_token_from_manual_invocation_guidance():
    content = _read("templates/commands/analyze.md")

    assert "Preserve canonical `/sp.implement` only in workflow-state fields." in content
    assert "When recommending manual implementation resumption to the user, tell them to run `{{invoke:implement}}`." in content
    assert "tell the user to run `{{invoke:implement}}` while preserving canonical `/sp.implement`" not in content
    assert "tell them to run `{{invoke:implement}}` while preserving canonical `/sp.implement`" not in content


def test_workflow_state_template_supports_analyze_gate_phase():
    content = _read("templates/workflow-state-template.md")
    lowered = content.lower()

    assert "analysis-only" in lowered
    assert "research-only" in lowered
    assert "/sp.analyze" in content
    assert "/sp.deep-research" in content
    assert "/sp.constitution" in content


def test_workflow_state_template_includes_lane_context():
    content = _read("templates/workflow-state-template.md")

    assert "## Lane Context" in content
    assert "lane_id:" in content
    assert "branch_name:" in content
    assert "worktree_path:" in content
    assert "recovery_state:" in content
    assert "last_stable_checkpoint:" in content


def test_debug_template_reads_constitution_and_feature_context_before_fixing() -> None:
    content = _read("templates/commands/debug.md")

    assert "### Required Context Inputs" in content
    assert ".specify/memory/constitution.md" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "{{specify-subcmd:learning start --command debug --format json}}" in content
    assert "spec.md`, `plan.md`, and `tasks.md`" in content
    assert "`context.md` exists for the active feature" in content


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

    assert "`next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`" in content
    assert "Default handoff: /sp-plan" not in content
    assert "Default handoff: /sp.plan" not in content
    assert "{{invoke:plan}}" in content
    assert "{{specify-subcmd:lane register" in content
    assert "LANE_ID" in content
    assert "LANE_WORKTREE" in content


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

    assert "{{specify-subcmd:lane resolve --command plan --ensure-worktree}}" in plan
    assert "{{specify-subcmd:lane resolve --command tasks --ensure-worktree}}" in tasks
    assert "{{specify-subcmd:lane resolve --command implement --ensure-worktree}}" in implement
    assert "{{specify-subcmd:lane resolve --command deep-research --ensure-worktree}}" in deep_research
    assert "{{specify-subcmd:lane resolve --command clarify --ensure-worktree}}" in clarify
    assert "{{specify-subcmd:lane resolve --command explain --ensure-worktree}}" in explain
    assert "isolated worktree context" in plan.lower()
    assert "isolated worktree context" in tasks.lower()
    assert "execution context for this implementation lane" in implement.lower()
    assert "uncertain" in implement.lower()


def test_specify_and_plan_templates_route_feasibility_gaps_through_deep_research():
    specify = _read("templates/commands/specify.md")
    plan = _read("templates/commands/plan.md")

    assert "Run a feasibility and implementation-chain gate." in specify
    assert "label: Prove Feasibility Before Plan" in specify
    assert "agent: sp.deep-research" in specify
    assert "record `/sp.deep-research` as the canonical next command instead of `/sp.plan`" in specify
    assert "tell them to run `{{invoke:deep-research}}` instead of `{{invoke:plan}}`" in specify
    assert "minor adjustments to capabilities that already exist" in specify
    assert "research-to-plan handoff path" in specify
    assert "Feasibility Evidence From Deep Research" in plan
    assert "Planning Handoff From Deep Research" in plan
    assert "Deep Research Traceability Matrix" in plan
    assert "every architecture, module-boundary, API/library, data-flow, validation, or residual-risk decision derived from deep research must cite at least one `PH-###` item" in plan
    assert "Treat the `Planning Handoff` section in `deep-research.md` as a direct planning input" in plan
    assert "Run {{invoke:deep-research}} before planning" in plan


def test_map_scan_template_generates_complete_build_package() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert ".specify/project-map/map-scan.md" in content
    assert ".specify/project-map/coverage-ledger.md" in content
    assert ".specify/project-map/coverage-ledger.json" in content
    assert ".specify/project-map/scan-packets/<lane-id>.md" in content
    assert ".specify/project-map/map-state.md" in content
    _assert_subagent_dispatch_contract(content, "map-scan")
    assert "full project-relevant inventory" in lowered
    assert "scan packets are executable read instructions" in lowered
    assert "must still execute the packet reads" in lowered
    assert "project map state protocol" in lowered
    assert "mapscanpacket" in lowered
    assert "result_handoff_path" in content
    assert "coverage classification" in lowered
    assert "criticality scoring" in lowered
    assert "reading depth" in lowered
    assert "project shape and stack" in lowered
    assert "module dependency graph" in lowered
    assert "entry and api surfaces" in lowered
    assert "data and state flows" in lowered
    assert "template and generated-surface propagation" in lowered
    assert "coverage reverse index" in lowered


def test_map_build_template_generates_handbook_navigation_system_from_scan_package() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/index/*.json" in content
    assert ".specify/project-map/root/*.md" in content
    assert ".specify/project-map/modules/<module-id>/*.md" in content
    _assert_subagent_dispatch_contract(content, "map-build")
    assert "atlas output contract" in lowered
    assert ".specify/project-map/map-state.md" in content
    assert ".specify/project-map/worker-results/*.json" in content
    assert "validate scan inputs before execution" in lowered
    assert "compile and validate mapbuildpacket inputs" in lowered
    assert "machine-readable row source" in lowered
    assert "raw scan prose or raw markdown checklist items alone" in lowered
    assert "not a scaffold, migration, or file-moving command" in lowered
    assert "inputs, not evidence" in lowered
    assert "packet evidence intake" in lowered
    assert "structural-only refresh is a failed build" in lowered
    assert "complete-refresh" in content
    assert "do not create `.planning/codebase/`" in lowered
    assert "capability cards must capture" in lowered
    assert "purpose" in lowered
    assert "owner" in lowered
    assert "truth lives" in lowered
    assert "extend here" in lowered
    assert "do not extend here" in lowered
    assert "minimum verification" in lowered
    assert "failure modes" in lowered
    assert "confidence" in lowered
    assert "confidence must use only: verified, inferred, or unknown-stale" in lowered


def test_map_build_template_preserves_full_detail_and_reverse_coverage() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "do not stop at repository shape" in lowered
    assert "do not stop at naming a file family or subsystem" in lowered
    assert "high-value contracts must preserve concrete signatures, fields, return shapes, handoff data, compatibility rules, or protocol semantics" in lowered
    assert "`project-handbook.md` must stay concise and index-first" in lowered
    assert "root docs carry cross-module truth; module docs carry module-local truth" in lowered
    assert "method families, parameter semantics, return shapes, error fields, state transitions, compatibility notes, or invariants" in lowered
    assert "every `critical` row appears in at least one final atlas target" in lowered
    assert "every `important` row appears in a final atlas target" in lowered
    assert "every scan packet is consumed" in lowered
    assert "every accepted packet result has paths read and confidence" in lowered
    assert "every final atlas target is backed by at least one accepted packet evidence row" in lowered
    assert "no final report claims success for a structural-only refresh" in lowered
    assert "`map_state_file` records accepted packet results" in lowered
    assert "owner, consumer, change propagation, and verification" in lowered
    assert "known unknowns" in lowered
    assert "low-confidence areas" in lowered
    assert "deep_stale" in content


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
    assert "mark `.specify/project-map/index/status.json` dirty" in lowered
    assert "recommend `/sp-map-scan` followed by `/sp-map-build`" in content


def test_spec_template_defines_scope_boundaries_without_open_clarification_examples():
    content = _read("templates/spec-template.md")

    assert "## Scope Boundaries" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content
    assert "## Decision Capture" in content
    assert "### Locked Decisions" in content
    assert "### Claude Discretion" in content
    assert "### Canonical References" in content
    assert "### Deferred / Future Ideas" in content
    assert "planning-facing analysis, not an implementation prescription" in content
    assert "If the feature touches an established boundary pattern" in content
    assert "`Implementation Constitution`" in content
    assert "Established boundary pattern or framework-owned surface" in content
    assert "Boundary-sensitive area that `plan` should turn into `Implementation Constitution`" in content
    assert "### Event / Trigger Model" in content
    assert "### Protocol / Contract Notes" in content
    assert "### Failure, Retry, and Visibility Semantics" in content
    assert "### Configuration and Rollout Notes" in content
    assert "retention, archival, or cleanup concern" in content
    assert "[NEEDS CLARIFICATION:" not in content
    assert "coherent first release" in content.lower()
    assert "viable mvp" not in content.lower()


def test_shared_artifact_templates_include_profile_fidelity_overlays():
    spec_content = _read("templates/spec-template.md")
    spec_lowered = spec_content.lower()
    assert "## Fidelity Requirements" in spec_content
    _assert_contains_any(spec_lowered, "reference-implementation", "copy-exact")
    assert "reference object" in spec_lowered

    plan_lowered = _read("templates/plan-template.md").lower()
    assert "reference fidelity contract" in plan_lowered
    _assert_contains_any(
        plan_lowered,
        "profile-driven implementation constraints",
        "profile obligations",
    )

    tasks_content = _read("templates/tasks-template.md")
    tasks_lowered = tasks_content.lower()
    prerequisites_match = re.search(r"(?m)^\*\*Prerequisites\*\*: (?P<value>.+)$", tasks_content)
    assert prerequisites_match is not None
    prerequisites = prerequisites_match.group("value")
    assert "alignment.md" in prerequisites
    assert "context.md" in prerequisites
    assert re.search(
        r"scenario profile inputs.*alignment\.md.*context\.md",
        tasks_lowered,
    )
    assert "Fidelity Checkpoint" in tasks_content
    assert "Deviation Review" in tasks_content
    assert "required evidence" in tasks_lowered


def test_context_template_exists_and_captures_planning_context():
    content = _read("templates/context-template.md")

    assert "# Feature Context:" in content
    assert "## Phase / Feature Boundary" in content
    assert "## Locked Decisions" in content
    assert "## Capability Checkpoints" in content
    assert "## Decision Fork Outcomes" in content
    assert "## Claude Discretion" in content
    assert "## Canonical References" in content
    assert "## Existing Code Insights" in content
    assert "## Boundary Contracts and Lifecycle Notes" in content
    assert "## Configuration Surface" in content
    assert "## Specific User Signals" in content
    assert "## Outstanding Questions" in content
    assert "## Deferred / Future Ideas" in content


def test_workflow_state_template_exists_and_captures_phase_lock_contract():
    content = _read("templates/workflow-state-template.md")

    assert "# Workflow State:" in content
    assert "## Current Command" in content
    assert "## Phase Mode" in content
    assert "## Allowed Artifact Writes" in content
    assert "## Forbidden Actions" in content
    assert "## Authoritative Files" in content
    assert "## Resume Checklist" in content
    assert "## Exit Criteria" in content
    assert "## Next Action" in content
    assert "## Next Command" in content
    assert "## Learning Signals" in content
    assert "### False Starts" in content
    assert "### Hidden Dependencies" in content
    assert "### Reusable Constraints" in content
    assert "planning-only" in content
    assert "design-only" in content
    assert "task-generation-only" in content
    assert "/sp.constitution" in content


def test_auto_template_routes_from_existing_state_surfaces():
    content = _read("templates/commands/auto.md")
    lowered = content.lower()

    assert "recommended next spec kit plus workflow step" in lowered
    assert "launcher/router" in lowered or "routing entrypoint" in lowered or "resume entrypoint" in lowered
    assert "workflow-state.md" in content
    assert "implement-tracker.md" in content
    assert "testing-state.md" in content
    assert "status.md" in lowered
    assert "debug" in lowered
    assert "next_command" in content
    assert "do not rewrite the underlying workflow state to `/sp.auto`" in lowered
    assert "obey the recorded upstream gate" in lowered or "must obey the recorded upstream gate" in lowered
    assert "if state is missing, stale, conflicting, or cannot identify one safe next step" in lowered
    assert "stop in read-only diagnosis" in lowered or "diagnostic mode" in lowered
    assert "read `.specify/templates/commands/<target>.md`" in lowered or "follow the routed command's shared contract" in lowered
    assert "/sp.plan" in content
    assert "/sp.tasks" in content
    assert "/sp.analyze" in content
    assert "/sp.implement" in content
    assert "/sp.debug" in content
    assert "/sp.quick" in content
    assert "/sp.fast" in content


def test_workflow_state_driven_templates_prefer_capture_auto_for_learning_closeout():
    for rel_path, cli_name in (
        ("templates/commands/specify.md", "specify"),
        ("templates/commands/plan.md", "plan"),
        ("templates/commands/tasks.md", "tasks"),
        ("templates/commands/analyze.md", "analyze"),
        ("templates/commands/test-scan.md", "test-scan"),
        ("templates/commands/test-build.md", "test-build"),
    ):
        content = _read(rel_path).lower()
        assert f"capture-auto --command {cli_name}" in content
        assert "workflow-state.md" in content or "testing-state.md" in content


def test_tasks_templates_default_to_phased_delivery_not_mvp():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")

    assert "## Planning Inputs" in template_content
    assert "Locked planning decisions" in template_content
    assert "Implementation constitution" in template_content
    assert "Alignment risks" in template_content
    assert "Validation references" in template_content
    assert "Task Guardrail Index" in template_content
    assert "Do not silently drop a locked planning decision" in template_content
    assert "task-to-guardrail mapping" in command_content.lower()
    assert "{{specify-subcmd:learning start --command tasks --format json}}" in command_content
    assert "implementation-guardrails phase" in command_content.lower()
    assert "boundary-defining references or forbidden drift" in command_content.lower()
    assert "Phase 0: Implementation Guardrails" in template_content
    assert "framework ownership, preserved boundary pattern, forbidden drift, and review checks" in template_content
    assert "phased delivery" in command_content.lower()
    assert "suggested first release scope" in command_content.lower()
    assert "parallel batch" in command_content.lower()
    assert "join point" in command_content.lower()
    assert "write set" in command_content.lower()
    assert "bounded implementation slice" in command_content.lower()
    assert "coffee break" in template_content.lower()
    assert "grouped parallelism is the default" in template_content.lower()
    assert "pipeline tasks should still stop at explicit checkpoints" in template_content.lower()
    assert "mvp first" not in command_content.lower()
    assert "suggested mvp scope" not in command_content.lower()

    assert "phased delivery" in template_content.lower()
    assert "first release candidate" in template_content.lower()
    assert "parallel batch" in template_content.lower()
    assert "join point" in template_content.lower()
    assert "write set" in template_content.lower()
    assert "**[AGENT]**" in template_content
    assert "independent from `[P]`" in template_content
    assert "mvp first" not in template_content.lower()
    assert "mvp increment" not in template_content.lower()
    assert "mvp!" not in template_content.lower()


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


def test_implement_template_supports_capability_aware_parallel_batches():
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

    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "{{specify-subcmd:learning start --command implement --format json}}" in content
    assert "{{specify-subcmd:learning capture --command implement ...}}" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" in content
    assert ".specify/project-map/root/STRUCTURE.md" in content
    assert ".specify/project-map/root/WORKFLOWS.md" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before continuing" in content
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
    assert ".specify/templates/worker-prompts/spec-reviewer.md" in content
    assert ".specify/templates/worker-prompts/code-quality-reviewer.md" in content
    assert "runtime-managed result channel" in lowered
    assert "feature_dir/worker-results/<task-id>.json" in lowered
    assert "{{specify-subcmd:result submit" in lowered
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
    assert "delegation_confidence" in lowered
    assert "low confidence -> `subagent-blocked`" in lowered
    assert "multiple safe validated packets" in lowered
    assert "no safe delegated lane" in lowered
    assert "one safe validated packet is ready" in lowered
    assert "multiple safe validated packets have isolated write sets" in lowered
    assert "`subagent-blocked` with a recorded reason" in lowered
    assert "run `/sp-map-scan` followed by `/sp-map-build` before final completion reporting" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in lowered
    assert "including unresolved `open_gaps`" in lowered
    assert "if you cannot complete that refresh in the current pass" in lowered
    assert "mark `.specify/project-map/index/status.json` dirty" in lowered
    assert "specify team" not in lowered
    assert "auto-dispatch" not in lowered
    assert "codex runtime rule" not in lowered

    no_safe_batch = step_6.find("no safe delegated lane")
    one_subagent = step_6.find("one safe validated packet")
    parallel_subagents = step_6.find("multiple safe validated packets")
    subagent_blocked = step_6.find("subagent-blocked")

    assert no_safe_batch != -1
    assert one_subagent != -1
    assert parallel_subagents != -1
    assert subagent_blocked != -1
    assert no_safe_batch < one_subagent < parallel_subagents


def test_implement_template_defines_leader_only_milestone_scheduler_contract():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "## Orchestration Model" in content
    assert "leader and orchestrator" in lowered
    assert "not the concrete implementer" in lowered
    assert "use `execution_model: subagent-mandatory` for ready implementation batches" in lowered
    assert "dispatch `one-subagent` when one validated `workertaskpacket` is ready" in lowered
    assert "dispatch `parallel-subagents` when multiple validated packets have isolated write sets" in lowered
    assert "use `execution_surface: native-subagents`" in lowered
    assert "record the blocker in `implement-tracker.md`" in lowered
    assert "invoking runtime acts as the leader" in lowered
    assert "subagent execution" in lowered
    assert "next executable phase" in lowered
    assert "shared implement template is the primary source of truth" in lowered
    assert "join point" in lowered
    assert "retry-pending" in lowered or "retry pending" in lowered
    assert "blocker" in lowered
    assert "do not stop to ask whether validation should start" in lowered
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in content
    assert "core implementation complete" in lowered
    assert "ready for integration testing" in lowered
    assert "overall feature completion" in lowered
    assert "e2e" in lowered
    assert "polish" in lowered
    assert "`research_gap`" in content
    assert "`plan_gap`" in content
    assert "`spec_gap`" in content
    assert "/sp.clarify" in content
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


def test_implement_template_requires_explicit_join_point_validation_blocks():
    content = _read("templates/commands/implement.md").lower()

    assert "join point validation" in content
    assert "validation target" in content
    assert "validation command" in content
    assert "pass condition" in content
    assert "if the validation command is missing" in content


def test_tasks_templates_require_join_point_validation_details():
    command_content = _read("templates/commands/tasks.md").lower()
    template_content = _read("templates/tasks-template.md").lower()

    assert "for every explicit join point, include a validation target" in command_content
    assert "join point validation notes" in command_content
    assert "join point validation:" in template_content
    assert "validation target:" in template_content
    assert "validation command:" in template_content
    assert "pass condition:" in template_content


def test_tasks_template_fail_closes_into_analyze_before_implement():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "default_handoff: '/sp.analyze" in content
    assert "Implement Project" not in content
    assert "recommended next command: `{{invoke:analyze}}`" in lowered
    assert "`next_command: /sp.analyze`" in content
    assert "implementation remains blocked until `{{invoke:analyze}}`" in lowered
    assert "do not hand off directly to `{{invoke:implement}}` from `sp-tasks`" in lowered


def test_implement_template_honors_pending_analyze_gate_from_workflow_state():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "Read `FEATURE_DIR/workflow-state.md` if present" in content
    assert "if `workflow_state_file` still points to `/sp.analyze`" in lowered
    assert "stop and run `/sp-analyze` first" in lowered
    assert "do not self-authorize an `/sp-implement` start from chat memory alone" in lowered


def test_debug_and_quick_templates_reference_shared_worker_prompt_assets() -> None:
    debug_content = _read("templates/commands/debug.md")
    quick_content = _read("templates/commands/quick.md")

    assert ".specify/templates/worker-prompts/debug-investigator.md" in debug_content
    assert ".specify/templates/worker-prompts/quick-worker.md" in quick_content
    assert "delegation_confidence" in debug_content.lower()
    assert "delegation_confidence" in quick_content.lower()
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in debug_content.lower()
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in quick_content.lower()
    assert "{{specify-subcmd:result submit" in debug_content.lower()
    assert "{{specify-subcmd:result submit" in quick_content.lower()
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
    assert "write the failing test first" in implementer.lower()
    assert "red state" in implementer.lower()
    assert "green state" in implementer.lower()
    assert "do not claim verification that was not run" in implementer.lower()

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
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "{{specify-subcmd:learning start --command checklist --format json}}" in lowered
    assert "{{specify-subcmd:learning capture --command checklist ...}}" in lowered
    assert "project-handbook.md" in lowered
    assert ".specify/project-map/index/status.json" in lowered
    assert "run `/sp-map-scan` followed by `/sp-map-build` before continuing" in lowered
    assert "if the checklist reveals planning-critical requirement gaps" in lowered
    assert "recommend `/sp-specify`" in lowered or "recommend `/sp.specify`" in lowered
    assert "recommend `/sp-plan`" in lowered
    assert "recommend `/sp-analyze`" in lowered


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Requirement Alignment Report:" in content
    assert "### Planning Summary" in content
    assert "## Locked Decisions For Planning" in content
    assert "## Engineering Closure For Planning" in content
    assert "## Capability Checkpoints" in content
    assert "## High-Impact Decision Forks" in content
    assert "## Artifact Review Gate" in content
    assert "## Outstanding Questions" in content
    assert "## Planning Gate Recommendation" in content
    assert "## Release Decision" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content


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
    assert "PROJECT_MAP_STATUS = (Get-ProjectMapStatusPath -RepoRoot $paths.REPO_ROOT)" in ps_check
    assert 'PROJECT_MAP_HELPER = (Join-Path $paths.REPO_ROOT ".specify/scripts/powershell/project-map-freshness.ps1")' in ps_check
    assert "context.md" in ps_check
    assert "CONTEXT = $paths.CONTEXT" in ps_setup
    assert "FEATURE_DIR = $paths.FEATURE_DIR" in ps_setup
    assert "[string]$FeatureDir" in ps_setup
    assert "CONTEXT=%q\\n" in sh_common
    assert "find_feature_dir_from_lane_state" in sh_common
    assert "feature_specs_roots" in sh_common
    assert "Find-FeatureDirFromLaneState" in ps_common
    assert "Get-FeatureSpecsRoots" in ps_common
    assert '--arg context "$CONTEXT"' in sh_check
    assert '--feature-dir' in sh_check
    assert '--arg project_map_status "$(project_map_status_path "$REPO_ROOT")"' in sh_check
    assert '--arg project_map_helper "$REPO_ROOT/.specify/scripts/bash/project-map-freshness.sh"' in sh_check
    assert '"CONTEXT":"%s"' in sh_check
    assert '--arg context "$CONTEXT"' in sh_setup
    assert '--arg feature_dir "$FEATURE_DIR"' in sh_setup
    assert '"FEATURE_DIR":"%s"' in sh_setup
    assert '"CONTEXT":"%s"' in sh_setup


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
    assert "clear-dirty" in sh_freshness
    assert '"freshness": "missing"' not in sh_freshness  # sanity: not hardcoded-only output
    assert "project-map status missing" in sh_freshness
    assert "high-impact project-map change" in sh_freshness
    assert "git baseline unavailable for project-map freshness" in sh_freshness

    assert "Get-ProjectMapStatusPath" in ps_freshness
    assert "record-refresh" in ps_freshness
    assert "complete-refresh" in ps_freshness
    assert "mark-dirty" in ps_freshness
    assert "clear-dirty" in ps_freshness
    assert "project-map status missing" in ps_freshness
    assert "high-impact project-map change" in ps_freshness
    assert "git baseline unavailable for project-map freshness" in ps_freshness


def test_plan_shell_requires_anchorable_headings():
    """plan shell.md must require anchorable section headings for downstream context pointers."""
    plan_shell = (PROJECT_ROOT / "templates" / "command-partials" / "plan" / "shell.md").read_text(encoding="utf-8")
    assert "anchorable" in plan_shell.lower()


def test_create_new_feature_scripts_scaffold_and_report_context():
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_create = _read("scripts/bash/create-new-feature.sh")

    assert "$contextFile = Join-Path $featureDir 'context.md'" in ps_create
    assert "Resolve-Template -TemplateName 'context-template'" in ps_create
    assert "CONTEXT_FILE = $contextFile" in ps_create
    assert "FEATURE_DIR = $featureDir" in ps_create
    assert "LANE_ID = $laneId" in ps_create
    assert "LANE_WORKTREE = $laneWorktree" in ps_create
    assert 'CONTEXT_FILE="$FEATURE_DIR/context.md"' in sh_create
    assert 'resolve_template "context-template"' in sh_create
    assert '"CONTEXT_FILE":"%s"' in sh_create
    assert '"FEATURE_DIR":"%s"' in sh_create
    assert '"LANE_ID":"%s"' in sh_create
    assert '"LANE_WORKTREE":"%s"' in sh_create
