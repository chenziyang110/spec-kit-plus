import re
from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_TUI_TEMPLATE_PATHS = (
    "templates/commands/specify.md",
    "templates/commands/spec-extend.md",
    "templates/commands/explain.md",
)
ASCII_CARD_HEADER_RE = re.compile(r"(?m)^\s*\+--")
ASCII_CARD_LINE_RE = re.compile(r"(?m)^\s*\| .+\|\s*$")
ASCII_CARD_FOOTER_RE = re.compile(r"(?m)^\s*\+-{10,}\+?\s*$")


def _read(path: str) -> str:
    return read_template(path)


def _extract_step_6_strategy_block(content: str) -> str:
    lowered = content.lower()
    start = lowered.find("6. select an execution strategy for each ready batch before writing code:")
    assert start != -1
    end = lowered.find("\n7. execute implementation following the task plan:", start)
    assert end != -1
    return lowered[start:end]


def _assert_contains_any(text: str, *needles: str) -> None:
    assert any(needle in text for needle in needles), f"Expected one of: {needles}"


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
    assert "specify learning start --command specify --format json" in content
    assert "specify learning capture --command specify" in content
    assert ".specify/project-map/status.json" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "Treat `PROJECT-HANDBOOK.md` as the root navigation artifact" in content
    assert "Use `Topic Map` to choose the smallest relevant topical documents" in content
    assert "run `/sp-map-codebase` before continuing" in content
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
    assert "choose_execution_strategy(command_name=\"specify\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
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
    assert "acceptance proof: what evidence would show this decision was implemented correctly" in content
    assert "Let unresolved gray areas drive the next question" in content
    assert "Before asking a planning-critical question, check whether `PROJECT-HANDBOOK.md` or touched-area topical documents already answer it" in content
    assert "Keep the active gray area open until the decision is specific enough" in content
    assert "Use code-aware follow-ups when possible" in content
    assert "Apply a specificity test before leaving a gray area" in content
    assert "Do not leave a gray area merely because the user expressed a preference" in content
    assert "default minimum depth as: happy path, failure path, compatibility impact, and acceptance proof" in content
    assert "Keep progress tracking scoped to the current capability or bounded spec slice rather than to a fixed global question budget." in content
    assert "Do not present the clarification loop as a fixed total such as `2 / 5`." in content
    assert "Treat this as an explicit pre-release check" in content
    assert "recommend `/sp.spec-extend` as the next command instead of `/sp.plan`" in content
    assert "Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`." in content
    assert "Read `templates/context-template.md`." in content
    assert "run a short checkpoint for each high-risk capability" in lowered
    assert "purpose / outcome" in lowered
    assert "boundary and non-goals" in lowered
    assert "acceptance proof" in lowered
    assert "artifact review gate" in lowered
    assert "review the written artifact set before handoff" in lowered
    assert "use one read-only reviewer lane" in lowered
    assert "placeholders/todos" in lowered
    assert "requirement-vs-implementation drift" in lowered
    assert "revise current artifacts" in lowered
    assert "continue analysis with `/sp.spec-extend`" in content
    assert "primary codebase-scout input" in content
    assert "module ownership, reusable components/services/hooks, integration points" in content
    assert "truth-owning surfaces" in content
    assert "change-propagation hotspots" in content
    assert "verification entry points" in content
    assert "known unknowns relevant to the request" in content
    assert "If the topical coverage for the touched area is missing, stale, or too broad" in content
    assert "Run a codebase scout before clarification." in content
    assert "Build a concise internal scout summary for the request area" in content
    assert "truth-owning surfaces and shared coordination surfaces" in content
    assert "change-propagation hotspots, consumer surfaces, and neighboring surfaces likely to require review" in content
    assert "verification entry points and regression-sensitive checks" in content
    assert "known unknowns, stale evidence boundaries, or observability gaps" in content
    assert "adjacent user flows or screens that this work could accidentally break" in content
    assert "grounded in the project handbook and touched-area topical map" in content
    assert "currently owning modules, services, screens, commands, or workflows" in content
    assert "truth-owning surfaces, consumer surfaces, and change-propagation hotspots" in content
    assert "verification entry points and regression-sensitive surfaces that will need proof before release" in content
    assert "known unknowns, stale evidence boundaries, or weakly mapped surfaces" in content
    assert "Synthesize these decisions into `context.md`" in content
    assert "22. Write `context.md` to `CONTEXT_FILE`." in content
    assert "- [ ] context.md exists" in content
    assert "- [ ] Locked decisions are preserved in context.md" in content
    assert "- [ ] workflow-state.md exists" in content
    assert "- [ ] workflow-state.md records `sp-specify` with planning-only restrictions" in content
    assert "- context file path" in content
    assert "common docs/config/process-change flows can reach planning-ready alignment inside `sp-specify`" in content
    assert "explicit pre-release check" in lowered
    assert "without needing `/sp.spec-extend`" in content
    assert "`Capability 1 / 3 | Question 2`" in content
    assert "SPECIFY SESSION - Capability 1 / 3 | Question 2" in content
    assert "SPECIFY SESSION - 2 / 5" not in content


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
    assert "specify learning start --command plan --format json" in content
    assert "specify learning capture --command plan" in content
    assert ".specify/project-map/status.json" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "run `/sp-map-codebase` before continuing" in content
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
    assert "locked planning decisions from `alignment.md`, `context.md`, and `spec.md`" in content
    assert "silently omitted from the generated plan artifacts" in content
    assert "Add `Implementation Constitution` whenever one or more of these heuristics is true" in content
    assert "established framework-owned boundary or adapter pattern" in content
    assert "native bridge, plugin surface, protocol seam, generated API surface" in content
    assert "generic implementation instinct would likely drift away" in content
    assert "canonical boundary files or examples" in content
    assert "choose_execution_strategy(command_name=\"plan\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
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
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert ".specify/memory/constitution.md" in content
    assert "choose_execution_strategy(command_name=\"tasks\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "story and phase decomposition" in lowered
    assert "dependency graph analysis" in lowered
    assert "write-set and parallel-safety analysis" in lowered
    assert "plan.md (tech stack, libraries, structure), spec.md (user stories with priorities), context.md (implementation context)" in content
    assert "alignment.md (locked decisions, outstanding questions, planning gate context)" in content
    assert "Locked Planning Decisions" in content
    assert "Decision Preservation Check" in content
    assert "quickstart.md exists: extract validation scenarios" in lowered
    assert "validate decision preservation" in lowered
    assert "instead of silently dropping it" in lowered
    assert "top-level tasks should usually fit one bounded implementation slice" in lowered
    assert "roughly 10-20 minutes" in lowered
    assert "delegated worker can still execute the task internally through smaller 2-5 minute atomic steps" in lowered
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
    assert "specify team" not in lowered


def test_explain_template_documents_conservative_routing_contract():
    content = _read("templates/commands/explain.md")
    lowered = content.lower()

    assert ".specify/memory/constitution.md" in content
    assert "choose_execution_strategy(command_name=\"explain\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "default to `single-agent`" in lowered
    assert "primary artifact reading" in lowered
    assert "supporting artifact cross-check" in lowered
    assert "before rendering the final explanation" in lowered
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
    assert ".specify/project-map/status.json" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "(`spec.md`, `context.md`, `plan.md`, `tasks.md`)" in content
    assert "- CONTEXT = FEATURE_DIR/context.md" in content
    assert ".specify/memory/constitution.md" in content
    assert "Read `PROJECT-HANDBOOK.md`" in content
    assert "Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`" in content
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
    assert "recommend `/sp.plan` to add `Implementation Constitution`" in content
    assert "If `BG2` exists" in content
    assert "If `BG3` exists" in content
    assert "Closed-loop requirement" in content
    assert "Recommended Next Command" in content
    assert "### 9. Define Workflow Re-entry" in content
    assert "Recommended Re-entry" in content
    assert "If the highest-impact issue lives in `spec.md` or `context.md`" in content
    assert "If the highest-impact issue lives in `plan.md`" in content
    assert "If the highest-impact issue lives only in `tasks.md`" in content
    assert "If analysis runs after `/sp-implement` has already started or finished" in content
    assert "exact workflow re-entry path" in content


def test_workflow_state_template_supports_analyze_gate_phase():
    content = _read("templates/workflow-state-template.md")
    lowered = content.lower()

    assert "analysis-only" in lowered
    assert "/sp.analyze" in content


def test_debug_template_reads_constitution_and_feature_context_before_fixing() -> None:
    content = _read("templates/commands/debug.md")

    assert "### Required Context Inputs" in content
    assert ".specify/memory/constitution.md" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "specify learning start --command debug --format json" in content
    assert "spec.md`, `plan.md`, and `tasks.md`" in content
    assert "`context.md` exists for the active feature" in content


def test_new_analysis_workflow_command_templates_exist():
    command_dir = PROJECT_ROOT / "templates" / "commands"
    template_stems = {path.stem for path in command_dir.glob("*.md")}

    assert "map-codebase" in template_stems
    assert "spec-extend" in template_stems
    assert "explain" in template_stems
    assert "clarify" not in template_stems


def test_map_codebase_template_generates_handbook_navigation_system() -> None:
    content = _read("templates/commands/map-codebase.md")
    lowered = content.lower()

    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/CONVENTIONS.md" in content
    assert ".specify/project-map/INTEGRATIONS.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert ".specify/project-map/TESTING.md" in content
    assert ".specify/project-map/OPERATIONS.md" in content
    assert 'choose_execution_strategy(command_name="map-codebase"' in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "support skills" not in lowered
    assert "refresh the handbook/project-map navigation system" in lowered
    assert "complete-refresh" in content
    assert "do not create `.planning/codebase/`" in content
    assert "Treat the map as a coverage system, not just a navigation summary." in content
    assert "what owns it" in content
    assert "where the truth lives" in content
    assert "what other surfaces consume it or feed it" in content
    assert "what minimum verification evidence proves the mapped surface still works" in content
    assert "what important unknowns, assumptions, or stale coverage remain" in content
    assert "for each high-value capability, core module, or critical workflow, emit at least one capability card" in lowered
    assert "purpose" in lowered
    assert "owner" in lowered
    assert "truth lives" in lowered
    assert "extend here" in lowered
    assert "do not extend here" in lowered
    assert "minimum verification" in lowered
    assert "failure modes" in lowered
    assert "confidence" in lowered
    assert "confidence must use only: verified, inferred, or unknown-stale" in lowered
    assert "when a capability card is marked inferred or unknown-stale, summarize that gap again in known unknowns, low-confidence areas, or both" in lowered
    assert "task-relevant coverage" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "runtime units, execution surfaces, and major capability surfaces" in lowered
    assert "key consumer surfaces and shared coordination surfaces" in lowered
    assert "change-propagation hotspots, validation entry points, and known unknowns" in lowered
    assert "evidence that reveals propagation paths" in lowered
    assert "change propagation paths" in lowered
    assert "what shared or consumer surfaces exist" in lowered
    assert "recovery paths" in lowered
    assert "verification entry points" in lowered
    assert "known runtime unknowns" in lowered
    assert "change-propagation hotspots" in lowered
    assert "\u9879\u76ee\u6280\u672f\u6587\u6863.md" not in content
    assert "`status.json` must preserve the current freshness contract" in content
    assert "last_mapped_commit" in content
    assert "last_refresh_topics" in content
    assert "dirty_reasons" in content


def test_map_codebase_template_preserves_full_detail_through_layering() -> None:
    content = _read("templates/commands/map-codebase.md")
    lowered = content.lower()

    assert "Layering exists so map consumers can read detail on demand instead of re-reading one monolithic technical document." in content
    assert "Do not treat layering as permission to discard technical detail." in content
    assert "without relying on any older monolithic technical writeup" in lowered
    assert "high-value contract or implementation detail" in lowered
    assert "external or exported api contracts" in lowered
    assert "core data models, state semantics, and handoff fields" in lowered
    assert "ipc, bridge, native-host, message, pipe, or protocol seams" in lowered
    assert "build, packaging, toolchain, platform, architecture, and runtime invariants" in lowered
    assert "key components whose responsibilities, inputs/outputs, or downstream effects" in lowered
    assert "do not collapse those details into vague summaries" in lowered
    assert "do not stop at naming a file family or subsystem" in lowered
    assert "record the responsibility, important inputs/outputs or fields, adjacent dependencies, compatibility constraints, and minimum verification route" in lowered
    assert "`PROJECT-HANDBOOK.md` must stay concise and index-first" in content
    assert "the topical documents must carry the deeper detail" in lowered
    assert "method families, parameter semantics, return shapes, error fields, state transitions, compatibility notes, or invariants" in lowered
    assert "if the repository is too large to card every capability, prioritize the capabilities that are most central, most risky to change, shared by multiple workflows, or exposed at external boundaries" in lowered
    assert "macro scan and architecture identification" in lowered
    assert "directory structure deep analysis" in lowered
    assert "dependency relationships and module analysis" in lowered
    assert "core code element review" in lowered
    assert "data flow and api surface mapping" in lowered
    assert "patterns and conventions synthesis" in lowered
    assert "project type, technology stack, and build tooling" in lowered
    assert "top-level architecture pattern and deployment shape" in lowered
    assert "major directories and representative subdirectories" in lowered
    assert "import/require relationships, core modules, utility modules, and strong-coupling hotspots" in lowered
    assert "core classes, abstract classes, interfaces, enums, and major functions" in lowered
    assert "key business flows from entry to exit" in lowered
    assert "route definitions, controllers, exported endpoints, or command surfaces" in lowered
    assert "design patterns, naming rules, directory customs, configuration management, and utility locations" in lowered
    assert "the generated navigation system should collectively cover the equivalent of these seven technical-document chapters" in lowered
    assert "project architecture overview" in lowered
    assert "directory structure and responsibilities" in lowered
    assert "key module dependency relationships" in lowered
    assert "core classes and interfaces" in lowered
    assert "core data flows" in lowered
    assert "api inventory" in lowered
    assert "common patterns and conventions" in lowered
    assert "capability-card prioritization does not waive area coverage" in lowered
    assert "when an area does not receive a full capability card" in lowered


def test_map_codebase_template_requires_fixed_topic_structure_and_handbook_routing() -> None:
    content = _read("templates/commands/map-codebase.md")
    lowered = content.lower()

    assert "every topical document should begin with a metadata block" in lowered
    assert "**last updated:** yyyy-mm-dd" in lowered
    assert "**coverage scope:** [what area this document covers]" in lowered
    assert "**primary evidence:** [main files, directories, commands, or tests used]" in lowered
    assert "**update when:** [what changes should trigger edits here]" in lowered
    assert "if local templates are absent, default to these section sets instead of free-form prose" in lowered
    assert "pattern overview" in lowered
    assert "directory responsibilities" in lowered
    assert "external services and tools" in lowered
    assert "core user flows" in lowered
    assert "smallest meaningful checks" in lowered
    assert "startup and execution paths" in lowered
    assert "do not put code blocks, api inventories, or the only precise explanation in `project-handbook.md`" in lowered
    assert "each subsystem or topic-map item in the handbook should stay to one short paragraph" in lowered
    assert "end with an explicit route to the relevant topical file" in lowered


def test_map_codebase_template_requires_detail_acceptance_checklist() -> None:
    content = _read("templates/commands/map-codebase.md")
    lowered = content.lower()

    assert "detail acceptance checklist" in lowered
    assert "before reporting completion" in lowered
    assert "no critical topic document stops at directory names or file-family names without explaining responsibilities" in lowered
    assert "high-value contracts keep concrete signatures, fields, return shapes, handoff data, or compatibility rules when those facts exist" in lowered
    assert "workflow and integration sections preserve protocol seams, bridge semantics, or runtime invariants when those facts govern behavior" in lowered
    assert "build, packaging, runtime, and recovery instructions remain actionable instead of being reduced to generic prose" in lowered
    assert "the handbook stays index-first and points to the topic docs instead of duplicating them" in lowered
    assert "high-value capabilities include owner, truth lives, extension guidance, change propagation, minimum verification, failure modes, and confidence" in lowered
    assert "capability cards use the canonical confidence levels verified, inferred, or unknown-stale" in lowered
    assert "each major directory has at least one responsibility statement and one placement cue" in lowered
    assert "each major api or command surface lists an entrypoint, owner, consumer, and verification route" in lowered
    assert "each high-value workflow or capability records a runnable minimum verification path or the explicit marker `missing runnable verification`" in lowered


def test_spec_extend_template_positions_itself_as_planning_gap_rescue_lane():
    content = _read("templates/commands/spec-extend.md")
    lowered = content.lower()

    assert "closing planning-critical gaps" in lowered
    assert "`FEATURE_DIR/context.md` if present" in content
    assert "- update `context.md`" in content
    assert "Existing Code Insights" in content
    assert "unresolved gray areas that still change plan structure" in lowered
    assert "missing locked decisions, canonical references, or deferred-scope notes" in lowered
    assert "whether the spec package is now ready for `/sp.plan` or still needs more clarification" in content
    assert "whether another `/sp.specify` or `/sp.spec-extend` pass is still justified before planning" in content
    assert "avoid implying an automatic handoff to `/sp.plan`" in lowered
    assert "default rescue lane" in lowered
    assert "recommend another clarification pass instead of implying that `/sp.plan` is now safe" in content


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
    assert "[NEEDS CLARIFICATION:" not in content
    assert "coherent first release" in content.lower()
    assert "viable mvp" not in content.lower()


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
    assert "planning-only" in content
    assert "design-only" in content
    assert "task-generation-only" in content


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
    assert "specify learning start --command tasks --format json" in command_content
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
    }

    for name, path in paths.items():
        content = read_template(path.as_posix())
        assert "[AGENT]" in content, f"{name} template missing [AGENT] marker"


def test_implement_template_supports_capability_aware_parallel_batches():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    step_6 = _extract_step_6_strategy_block(content)

    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "specify learning start --command implement --format json" in content
    assert "specify learning capture --command implement" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert ".specify/memory/constitution.md" in content
    assert "Extract `Implementation Constitution` from `plan.md`" in content
    assert "What framework or boundary pattern owns the touched surface?" in content
    assert "Which files define the existing pattern that must be preserved?" in content
    assert "What implementation drift is forbidden for this batch?" in content
    assert "compile a `WorkerTaskPacket` for each delegated task" in content
    assert "dispatch only from validated `WorkerTaskPacket`" in content
    assert "Do not dispatch from raw task text alone" in content
    assert ".specify/templates/worker-prompts/implementer.md" in content
    assert ".specify/templates/worker-prompts/spec-reviewer.md" in content
    assert ".specify/templates/worker-prompts/code-quality-reviewer.md" in content
    assert "runtime-managed result channel" in lowered
    assert "feature_dir/worker-results/<task-id>.json" in lowered
    assert "specify result submit" in lowered
    assert "reported_status" in lowered
    assert "idle delegated worker is not an accepted result" in lowered
    assert "must wait for and consume the structured handoff before closing the join point" in lowered
    assert "boundary-pattern preservation" in lowered
    assert "implement-tracker.md" in content
    assert "execution-state source of truth" in lowered
    assert "## execution intent" in lowered
    assert "intent_outcome:" in lowered
    assert "intent_constraints:" in lowered
    assert "success_evidence:" in lowered
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
    assert "blocked delegated worker results must include" in lowered
    assert "failed assumption" in lowered
    assert "smallest safe recovery step" in lowered
    assert "execution strategy" in lowered
    assert "single-agent" in lowered
    assert "single-lane" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "delegation_confidence" in lowered
    assert "native-low-confidence" in lowered
    assert "parallel_batches" in lowered
    assert "no-safe-batch" in lowered
    assert "native-supported" in lowered
    assert "native-missing" in lowered
    assert "run `/sp-map-codebase` before final completion reporting" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in lowered
    assert "including unresolved `open_gaps`" in lowered
    assert "if you cannot complete that refresh in the current pass" in lowered
    assert "mark `.specify/project-map/status.json` dirty" in lowered
    assert "specify team" not in lowered
    assert "auto-dispatch" not in lowered
    assert "codex runtime rule" not in lowered

    no_safe_batch = step_6.find("parallel_batches <= 0")
    native_supported = step_6.find("native_multi_agent")
    native_missing = step_6.find("sidecar_runtime_supported")
    fallback = step_6.find("fallback")

    assert no_safe_batch != -1
    assert native_supported != -1
    assert native_missing != -1
    assert fallback != -1
    assert no_safe_batch < native_supported < native_missing < fallback


def test_implement_template_defines_leader_only_milestone_scheduler_contract():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "## Leader Role" in content
    assert "you are the implementation leader for this run" in lowered
    assert "you are not the default implementer for the current batch" in lowered
    assert "`single-lane` as one delegated worker lane" in content or "`single-lane` still means one delegated worker lane" in content
    assert "fallback reason is recorded in `implement-tracker.md`" in lowered
    assert "invoking runtime acts as the leader" in lowered
    assert "delegated worker lane" in lowered
    assert "next executable phase" in lowered
    assert "shared implement template is the primary source of truth" in lowered
    assert "join point" in lowered
    assert "retry-pending" in lowered or "retry pending" in lowered
    assert "blocker" in lowered
    assert "do not stop to ask the user whether the `single-lane` batch should switch to delegated execution" in lowered
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in content
    assert "core implementation complete" in lowered
    assert "ready for integration testing" in lowered
    assert "overall feature completion" in lowered
    assert "e2e" in lowered
    assert "polish" in lowered
    assert "`research_gap`" in content
    assert "`plan_gap`" in content
    assert "`spec_gap`" in content
    assert "/sp.spec-extend" in content


def test_shared_implement_teams_contract_preserves_explicit_execution_packet_fields():
    content = _read("src/specify_cli/integrations/base.py").lower()

    assert "every delegated task in the teams-backed flow must still behave like an explicit execution packet" in content
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

    assert "default_handoff: /sp-analyze" in content
    assert "Implement Project" not in content
    assert "`next_command: /sp.analyze`" in content
    assert "implementation remains blocked until `/sp-analyze`" in lowered
    assert "do not hand off directly to `/sp-implement` from `sp-tasks`" in lowered


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
    assert "specify result submit" in debug_content.lower()
    assert "specify result submit" in quick_content.lower()
    assert "reported_status" in debug_content.lower()
    assert "reported_status" in quick_content.lower()
    assert "idle delegated worker is not an accepted result" in debug_content.lower()
    assert "idle delegated worker is not an accepted result" in quick_content.lower()
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


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Requirement Alignment Report:" in content
    assert "### Planning Summary" in content
    assert "## Locked Decisions For Planning" in content
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
    assert "PROJECT_MAP_STATUS = (Get-ProjectMapStatusPath -RepoRoot $paths.REPO_ROOT)" in ps_check
    assert 'PROJECT_MAP_HELPER = (Join-Path $paths.REPO_ROOT ".specify/scripts/powershell/project-map-freshness.ps1")' in ps_check
    assert "context.md" in ps_check
    assert "CONTEXT = $paths.CONTEXT" in ps_setup
    assert "CONTEXT=%q\\n" in sh_common
    assert '--arg context "$CONTEXT"' in sh_check
    assert '--arg project_map_status "$(project_map_status_path "$REPO_ROOT")"' in sh_check
    assert '--arg project_map_helper "$REPO_ROOT/.specify/scripts/bash/project-map-freshness.sh"' in sh_check
    assert '"CONTEXT":"%s"' in sh_check
    assert '--arg context "$CONTEXT"' in sh_setup
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


def test_create_new_feature_scripts_scaffold_and_report_context():
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_create = _read("scripts/bash/create-new-feature.sh")

    assert "$contextFile = Join-Path $featureDir 'context.md'" in ps_create
    assert "Resolve-Template -TemplateName 'context-template'" in ps_create
    assert "CONTEXT_FILE = $contextFile" in ps_create
    assert "FEATURE_DIR = $featureDir" in ps_create
    assert 'CONTEXT_FILE="$FEATURE_DIR/context.md"' in sh_create
    assert 'resolve_template "context-template"' in sh_create
    assert '"CONTEXT_FILE":"%s"' in sh_create
    assert '"FEATURE_DIR":"%s"' in sh_create
