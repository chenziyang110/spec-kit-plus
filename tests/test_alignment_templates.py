import re
from pathlib import Path


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
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


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
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "Treat `PROJECT-HANDBOOK.md` as the root navigation artifact" in content
    assert "Use `Topic Map` to choose the smallest relevant topical documents" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "coverage is insufficient when the touched area is named only vaguely" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

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
    assert "primary codebase-scout input" in content
    assert "module ownership, reusable components/services/hooks, integration points" in content
    assert "If the topical coverage for the touched area is missing, stale, or too broad" in content
    assert "Run a codebase scout before clarification." in content
    assert "Build a concise internal scout summary for the request area" in content
    assert "adjacent user flows or screens that this work could accidentally break" in content
    assert "grounded in the project handbook and touched-area topical map" in content
    assert "currently owning modules, services, screens, commands, or workflows" in content
    assert "Synthesize these decisions into `context.md`" in content
    assert "22. Write `context.md` to `CONTEXT_FILE`." in content
    assert "- [ ] context.md exists" in content
    assert "- [ ] Locked decisions are preserved in context.md" in content
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
    assert "### Standard Stack" in content
    assert "### Don't Hand-Roll" in content
    assert "### Common Pitfalls" in content
    assert "### Assumptions To Validate" in content
    assert "### Environment / Dependency Notes" in content
    assert "## Decision Preservation Check" in content
    assert "## Research Adoption Check" in content
    assert "cannot be silently dropped" in lowered
    assert "where it appears in the plan" in lowered
    assert "consumed research.md" in lowered
    assert "background reading" in lowered


def test_tasks_template_documents_shared_routing_before_decomposition():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "PROJECT-HANDBOOK.md" in content
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

    assert "(`spec.md`, `context.md`, `plan.md`, `tasks.md`)" in content
    assert "- CONTEXT = FEATURE_DIR/context.md" in content
    assert ".specify/memory/constitution.md" in content
    assert "**From context.md:**" in content
    assert "Locked Decisions" in content
    assert "Locked Planning Decisions" in content
    assert "Locked decision inventory" in content
    assert "#### F. Locked Decision Drift" in content
    assert "silently weakened, deferred, or renamed" in lowered
    assert "locked decision silently dropped between artifacts" in lowered
    assert "**Locked Decision Preservation Table:**" in content


def test_debug_template_reads_constitution_and_feature_context_before_fixing() -> None:
    content = _read("templates/commands/debug.md")

    assert "### Required Context Inputs" in content
    assert ".specify/memory/constitution.md" in content
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
    assert "do not create `.planning/codebase/`" in content
    assert "task-relevant coverage" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "legacy `项目技术文档.md`" in content


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
    assert "[NEEDS CLARIFICATION:" not in content
    assert "coherent first release" in content.lower()
    assert "viable mvp" not in content.lower()


def test_context_template_exists_and_captures_planning_context():
    content = _read("templates/context-template.md")

    assert "# Feature Context:" in content
    assert "## Phase / Feature Boundary" in content
    assert "## Locked Decisions" in content
    assert "## Claude Discretion" in content
    assert "## Canonical References" in content
    assert "## Existing Code Insights" in content
    assert "## Specific User Signals" in content
    assert "## Outstanding Questions" in content
    assert "## Deferred / Future Ideas" in content


def test_tasks_templates_default_to_phased_delivery_not_mvp():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")

    assert "## Planning Inputs" in template_content
    assert "Locked planning decisions" in template_content
    assert "Alignment risks" in template_content
    assert "Validation references" in template_content
    assert "Do not silently drop a locked planning decision" in template_content
    assert "phased delivery" in command_content.lower()
    assert "suggested first release scope" in command_content.lower()
    assert "parallel batch" in command_content.lower()
    assert "join point" in command_content.lower()
    assert "write set" in command_content.lower()
    assert "mvp first" not in command_content.lower()
    assert "suggested mvp scope" not in command_content.lower()

    assert "phased delivery" in template_content.lower()
    assert "first release candidate" in template_content.lower()
    assert "parallel batch" in template_content.lower()
    assert "join point" in template_content.lower()
    assert "write set" in template_content.lower()
    assert "mvp first" not in template_content.lower()
    assert "mvp increment" not in template_content.lower()
    assert "mvp!" not in template_content.lower()


def test_implement_template_supports_capability_aware_parallel_batches():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    step_6 = _extract_step_6_strategy_block(content)

    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/STRUCTURE.md" in content
    assert ".specify/project-map/WORKFLOWS.md" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered

    assert ".specify/memory/constitution.md" in content
    assert "implement-tracker.md" in content
    assert "execution-state source of truth" in lowered
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
    assert "execution strategy" in lowered
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "parallel_batches" in lowered
    assert "no-safe-batch" in lowered
    assert "native-supported" in lowered
    assert "native-missing" in lowered
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

    assert "invoking runtime acts as the leader" in lowered
    assert "delegated worker lane" in lowered
    assert "next executable phase" in lowered
    assert "shared implement template is the primary source of truth" in lowered
    assert "join point" in lowered
    assert "retry-pending" in lowered or "retry pending" in lowered
    assert "blocker" in lowered
    assert "tasks.md` being fully checked off is not sufficient for completion by itself" in content
    assert "`research_gap`" in content
    assert "`plan_gap`" in content
    assert "`spec_gap`" in content
    assert "/sp.spec-extend" in content


def test_specify_template_explicitly_reads_constitution() -> None:
    content = _read("templates/commands/specify.md")

    assert ".specify/memory/constitution.md" in content


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Requirement Alignment Report:" in content
    assert "### Planning Summary" in content
    assert "## Locked Decisions For Planning" in content
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
    assert "context.md" in ps_check
    assert "CONTEXT = $paths.CONTEXT" in ps_setup
    assert "CONTEXT=%q\\n" in sh_common
    assert '--arg context "$CONTEXT"' in sh_check
    assert '"CONTEXT":"%s"' in sh_check
    assert '--arg context "$CONTEXT"' in sh_setup
    assert '"CONTEXT":"%s"' in sh_setup


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
