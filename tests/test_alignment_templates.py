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


def _read_project_file(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _assert_learning_index_detail_model(content: str) -> None:
    assert ".specify/memory/learnings/INDEX.md" in content
    assert "detail document" in content or "detail docs" in content
    lowered = content.lower()
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
    assert "## Workflow Activation Discipline" in block
    assert "1% chance" in block
    assert "route before any response or action" in lowered
    assert "repository inspection belongs inside the selected workflow" in lowered
    assert "Treat `sp-*` names as canonical workflow identities." in block

    assert "## Brownfield Context Gate" in block
    assert "`.specify/project-cognition/status.json`" in block
    assert "`.specify/project-cognition/graph/nodes.json`" in block
    assert "`.specify/project-cognition/graph/edges.json`" in block
    assert "`.specify/project-cognition/graph/claims.json`" in block
    assert "`.specify/project-cognition/graph/conflicts.json`" in block
    assert "compatibility/export surfaces for ordinary workflow execution" in block
    assert "read the workflow-appropriate project cognition status and graph slice artifacts" in lowered

    assert "## Project Memory" in block
    assert "Treat the learning layer as workflow-execution infrastructure, not as optional notes." in block
    assert "`.specify/memory/constitution.md` is the principle-level source of truth when present." in block
    assert "`.specify/memory/project-rules.md` holds stable defaults and reusable constraints." in block
    _assert_learning_index_detail_model(block)

    assert "## Delegated Execution Defaults" in block
    assert "Dispatch native subagents by default for independent, bounded lanes when parallel work materially improves speed, quality, or verification confidence." in block
    assert "Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins." in block
    assert "Wait for each subagent's structured handoff, result file, or runtime-managed result before integrating or marking work complete. Idle state or a chat summary is not completion evidence." in block
    assert "Use the integration's durable team/runtime surface only when durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst is required." in block
    assert "For integrations that expose `sp-teams`, use `sp-teams` only in those cases." in block

    assert "## Artifact Priority" in block
    assert "`workflow-state.md` under the active feature directory is the stage/status source of truth" in block
    assert "`alignment.md` and `context.md` under the active feature directory carry locked decisions from `sp-specify` into planning." in block
    assert "`plan.md` under the active feature directory is the implementation design source of truth once planning begins." in block
    assert "`tasks.md` under the active feature directory is the execution breakdown source of truth once task generation begins." in block
    assert "Use `prd-scan -> prd-build` as the canonical existing-project reverse-PRD lane" in block
    assert "`.specify/prd-runs/<run-id>/`, including its workflow state and scan/build artifacts, is the current-state PRD reconstruction truth surface." in block
    assert "Treat it as documentation output unless later work explicitly adopts it as planning input." in block

    assert "`.specify/testing/testing-state.md`" in block
    assert "Treat testing artifacts by role:" in block
    assert "`TEST_SCAN.md`: scan evidence and module risk findings, not the executable build contract." in block
    assert "`TEST_BUILD_PLAN.md` / `.json`: build-ready testing-system lanes and validation commands; primary `sp-test-build` inputs." in block
    assert "`UNIT_TEST_SYSTEM_REQUEST.md`: brownfield testing-program input for later scoped spec/planning work." in block
    assert "`TESTING_CONTRACT.md`: durable downstream testing obligations that later workflows should honor automatically." in block
    assert "`TESTING_PLAYBOOK.md`: operator and maintainer runbook for test execution." in block
    assert "`COVERAGE_BASELINE.json`: observed baseline data, not acceptance proof by itself." in block

    assert "## Execution and Closeout Rules" in block
    assert "Do not substitute chat narration for workflow execution." in block
    assert "read the relevant durable state surface first" in lowered
    assert "do not claim completion until those artifacts exist" in lowered

    assert "## Map Maintenance" in block
    assert "Run `sp-map-scan`, then `sp-map-build` to create the initial cognition baseline." in block
    assert "Use `sp-map-update` after baseline creation when the graph runtime is stale or too weak for the touched area." in block
    assert "Do not treat consumed project cognition graph context as self-maintaining" in block
    assert "graph-native" in lowered
    assert "project-cognition" in block
    assert "map-update" in block

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


def test_core_sp_templates_use_direct_passive_learning_without_hook_gates():
    learning_layer = _read("templates/command-partials/common/learning-layer.md")
    assert ".specify/memory/learnings/INDEX.md" in learning_layer
    assert "Learning Reflex" in learning_layer
    assert "detail document" in learning_layer
    assert "learning capture-auto" in learning_layer

    command_templates = (
        "templates/commands/specify.md",
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/analyze.md",
        "templates/commands/test-scan.md",
        "templates/commands/test-build.md",
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
        assert ".specify/memory/learnings/INDEX.md" in content, (
            f"{template_path} should preserve the learning index reference"
        )
        assert "Learning Reflex" in content, f"{template_path} should preserve Learning Reflex guidance"
        assert "detail document" in content, (
            f"{template_path} should preserve learning detail document guidance"
        )

    quick_content = _read("templates/commands/quick.md")
    assert "{{specify-subcmd:learning start --command quick --format json}}" in quick_content or "Passive Project Learning Layer" in quick_content
    assert "{{specify-subcmd:hook review-learning --command quick" not in quick_content
    assert "{{specify-subcmd:hook capture-learning" not in quick_content
    assert ".specify/memory/learnings/INDEX.md" in quick_content
    assert "Learning Reflex" in quick_content
    assert "detail document" in quick_content

    fast_content = _read("templates/commands/fast.md")
    assert ".specify/memory/learnings/INDEX.md" in fast_content
    assert "Learning Reflex" in fast_content
    assert "detail document" in fast_content
    assert "{{specify-subcmd:learning capture --command fast ...}}" not in fast_content


def test_owned_workflow_templates_use_learning_index_reflex() -> None:
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
        "templates/commands/test-scan.md",
        "templates/commands/test-build.md",
        "templates/commands/map-scan.md",
        "templates/commands/map-build.md",
    )

    for template_path in owned_workflow_templates:
        content = _read(template_path)
        assert ".specify/memory/constitution.md" in content
        assert ".specify/memory/project-rules.md" in content
        assert ".specify/memory/learnings/INDEX.md" in content
        assert "Learning Reflex" in content or "future senior engineer" in content


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


def test_project_learning_skill_documents_direct_learning_helpers_not_hook_gates():
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md")

    assert "Direct Learning Helpers" in content
    assert "learning start" in content
    assert "learning capture-auto" in content
    assert "{{specify-subcmd:hook signal-learning" not in content
    assert "{{specify-subcmd:hook review-learning" not in content
    assert "{{specify-subcmd:hook capture-learning" not in content
    assert "{{specify-subcmd:hook inject-learning" not in content
    assert "tooling_trap" in content
    assert "map_coverage_gap" in content
    assert "Do NOT" in content


def test_specify_template_uses_alignment_first_contract():
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/edges.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/graph/conflicts.json" in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content
    assert "support-only project-map artifacts" in lowered
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
    assert "{{specify-subcmd:learning start --command specify --format json}}" in content
    assert "Required options: `--command`, `--type`, `--summary`, `--evidence`" in content
    assert ".specify/project-map/index/status.json" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "Treat `PROJECT-HANDBOOK.md` as the root navigation artifact" not in content
    assert "Use `Topic Map` to choose the smallest relevant topical documents" not in content
    assert "tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that refresh before continuing" in content.lower()
    assert ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md" in content
    assert "primary brownfield testing-program input" in content
    assert "module priority waves" in content
    assert "covered-module policy" in lowered
    assert "small / medium / large" in lowered
    assert "local integration seam expectations" in lowered
    assert "fast smoke" in lowered
    assert "focused" in lowered
    assert "full" in lowered
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
    assert 'choose_subagent_dispatch(command_name="specify"' in content
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "native-subagents" in lowered
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
    assert "fixed heavy discovery lifecycle" in lowered
    assert "always execute these six stages in order" in lowered
    assert "intent-analysis" in content
    assert "intent-confirmation" in content
    assert "question-batch" in content
    assert "batch-adversarial-review" in content
    assert "completeness-audit" in content
    assert "final-handoff-decision" in content
    assert "intent-analyst" in content
    assert "adversarial-reviewer" in content
    assert "completeness-auditor" in content
    assert "goal-and-users" in content
    assert "triggers-and-primary-flow" in content
    assert "boundaries-and-non-goals" in content
    assert "failure-paths-exceptions-and-permissions" in content
    assert "dependencies-constraints-and-upstream-downstream-impact" in content
    assert "acceptance-and-completeness-gap-closure" in content
    assert "Only `final-handoff-decision` may decide whether the canonical next command is `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`." in content
    assert "## Scenario Profile Routing" not in content
    assert "active_profile" not in content
    assert "coverage_mode" not in content
    assert "Task Classification" not in content



def test_readme_documents_runtime_atlas_refresh_scope_and_workbench_boundaries() -> None:
    readme = _read_project_file("README.md")
    lowered = readme.lower()

    assert ".specify/project-cognition/status.json" in lowered
    assert "default brownfield runtime truth surface" in lowered
    assert "compatibility/export surfaces only during the migration window" in lowered
    assert "map-update" in lowered
    assert "map-scan" in lowered
    assert "map-build" in lowered



def test_project_handbook_distinguishes_runtime_atlas_workbench_and_reference_only() -> None:
    handbook = _read_project_file("PROJECT-HANDBOOK.md")
    lowered = handbook.lower()

    assert "default brownfield runtime truth surface" in lowered
    assert "compatibility/export surfaces only during the migration window" in lowered
    assert "project cognition as the primary runtime truth surface" in lowered
    assert "generated `.specify/project-map/**` outputs in this repository are compatibility/export or refresh-workbench surfaces" in lowered
    assert "`debug-handbook.md` - compatibility/export debug view" in lowered
    assert "`build-handbook.md` - compatibility/export build/change view" in lowered


def test_templates_lock_cross_project_cognition_reference_rules() -> None:
    managed_block = _extract_bash_managed_block(_read("scripts/bash/update-agent-context.sh"))
    routing_skill = _read("templates/passive-skills/spec-kit-project-map-gate/SKILL.md")
    plan_shell = _read("templates/command-partials/plan/shell.md")
    map_scan_shell = _read("templates/command-partials/map-scan/shell.md")

    combined = "\n".join([managed_block, routing_skill, plan_shell, map_scan_shell])
    lowered = combined.lower()

    assert ".specify/project-cognition/status.json" in lowered
    assert ".specify/project-cognition/slices/change.json" in lowered
    assert "cross-project cognition reference" in lowered
    assert "explicit-only" in lowered
    assert "supplemental-only" in lowered
    assert "fresh-only" in lowered
    assert "minimal read" in lowered
    assert "compatibility/export surfaces" in lowered
    assert "primary runtime truth" in lowered or "primary brownfield context surface" in lowered
    assert "project-map" in lowered
    assert "project-map as primary truth" not in lowered
    assert "project-map primary truth" not in lowered


def test_core_planning_templates_use_logical_atlas_references() -> None:
    legacy_rel_paths = [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]
    for rel_path in legacy_rel_paths:
        content = _read(rel_path)
        lowered = content.lower()
        assert ".specify/project-cognition/status.json" in lowered
        assert ".specify/project-cognition/slices/change.json" in lowered
        assert "build-handbook.md" not in lowered
        assert "build-workflow-contract" not in lowered
        assert "product-and-capability-map" not in lowered
        assert "atlas.entry" not in lowered

    implement = _read("templates/commands/implement.md").lower()
    assert ".specify/project-cognition/status.json" in implement
    assert ".specify/project-cognition/slices/change.json" in implement
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
    assert "sp-specify -> sp-plan -> sp-tasks -> sp-implement" in workflows

    assert "profile-matched evidence" in testing
    assert "reference fidelity" in testing
    assert "standard delivery" in testing
    assert "reference-implementation" in testing


def test_constitution_template_uses_current_shared_context_and_reentry_contract() -> None:
    content = _read("templates/commands/constitution.md")
    lowered = content.lower()

    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:learning start --command constitution --format json}}" in content
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-map/index/status.json" in content
    assert "`/sp-map-scan` followed by `/sp-map-build`" in content
    assert "workflow-state.md" in content
    assert "/sp-plan" in content
    assert "/sp-tasks" in content
    assert "/sp-analyze" in content
    assert "active_command: sp-constitution" in lowered
    assert "phase_mode: planning-only" in lowered
    assert "{{specify-subcmd:hook" not in lowered
    assert "keep `workflow-state.md` current" in lowered
    assert "verify the constitution artifact set" in lowered
    assert "update durable state before handoff" in lowered
    assert "highest affected downstream stage" in lowered
    assert "do not always hand off directly to `/sp-specify`" in lowered
    assert "active `spec.md`, `plan.md`, `tasks.md`, or `workflow-state.md`" in content
    assert "project rules or learnings that conflict with the amended constitution" in lowered
    assert "project cognition runtime truth" in lowered
    assert "mark the related project cognition compatibility/export surface for refresh" in lowered
    assert "if the cognition baseline is missing" in lowered


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

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/edges.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/graph/conflicts.json" in content
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
    assert "{{specify-subcmd:learning start --command plan --format json}}" in content
    assert "Required options: `--command`, `--type`, `--summary`, `--evidence`" in content
    assert ".specify/project-map/index/status.json" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that refresh before continuing" in content.lower()
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
    assert "If exactly one validated isolated plan lane exists, dispatch `one-subagent`." in content
    assert "If two or more validated isolated plan lanes exist, dispatch `parallel-subagents`." in content
    assert "If no validated isolated plan lane can be packetized, mark `subagent-blocked` and stop." in content
    assert "leader-inline execution of substantive lane work is forbidden" in lowered
    assert "collaboration routing is determined only by validated lane count and isolation" in lowered
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
    assert "git-baseline freshness in `.specify/project-map/index/status.json` as the truth source" in lowered
    assert "successful-refresh finalizer" in lowered
    assert "manual override/fallback" in lowered
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
    assert "execution-rule surface" in lowered
    assert "constraint explicit" in lowered
    assert "consumed research.md" in lowered
    assert "background reading" in lowered


def test_tasks_template_documents_shared_routing_before_decomposition():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/edges.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/graph/conflicts.json" in content
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
    assert "tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that refresh before continuing" in content.lower()
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
    assert "split work only into the supported task-generation lanes" in lowered
    assert "If exactly one validated isolated lane exists, dispatch `one-subagent`." in content
    assert "If two or more validated isolated lanes exist, dispatch `parallel-subagents`." in content
    assert "If overlap or missing contract prevents safe dispatch, mark `subagent-blocked` and stop." in content
    assert "Leader-only decomposition is forbidden once a validated lane exists." in content
    assert "Task-generation collaboration is determined only by validated lane count and write-set isolation." in content
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
    assert "leave later phases at the coarser story or phase level" in lowered
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
    assert "git-baseline freshness in `.specify/project-map/index/status.json` as the truth source" in lowered
    assert "successful-refresh finalizer" in lowered
    assert "manual override/fallback" in lowered
    assert "specify team" not in lowered


def test_implement_template_wave_budget_contract():
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
    assert "handbook or project-map artifacts only when the user explicitly requests the compatibility/export surfaces themselves" in lowered
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
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
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
    assert "use `{{invoke:map-update}}` when the touched area is localized" in content
    assert "task-relevant coverage is insufficient" in lowered
    assert "ownership or placement guidance" in lowered
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in lowered
    assert "(`spec.md`, `context.md`, `plan.md`, `tasks.md`)" in content
    assert "- CONTEXT = FEATURE_DIR/context.md" in content
    assert ".specify/memory/constitution.md" in content
    assert "Read `.specify/project-cognition/status.json`" in content
    assert "Read `.specify/project-cognition/slices/change.json`" in content
    assert "Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`" not in content
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
    assert "finish the full detection matrix before selecting the single recommended next command" in lowered
    assert "Stable Finding Identity" in content
    assert "fingerprint-first" in lowered
    assert "reuse the prior ID" in content
    assert "Allocate a new ID only for a genuinely new fingerprint" in content
    assert "Revalidation Attribution" in content
    assert "missed_by_previous_analyze" in content
    assert "introduced_by_remediation" in content
    assert "upstream_artifact_changed" in content
    assert "detector_scope_changed" in content
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
    assert "artifact_fingerprint_basis" in content
    assert "If the remaining issue is execution-only, the re-entry chain MUST begin at `{{invoke:implement}}` or `{{invoke:debug}}`." in content
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

    assert "fixed lifecycle state" in lowered
    assert "intent-analysis" in content
    assert "question-batch" in content
    assert "final-handoff-decision" in content
    assert "/sp.plan" in content
    assert "/sp.clarify" in content
    assert "/sp.deep-research" in content
    assert "## Analyze Gate" in content
    assert "gate_status" in content
    assert "gate_cycle" in content
    assert "highest_invalid_stage" in content
    assert "blocker_bundle" in content
    assert "artifact_fingerprint_basis" in content
    assert "missed_by_previous_analyze" in content
    assert "introduced_by_remediation" in content
    assert "upstream_artifact_changed" in content
    assert "detector_scope_changed" in content
    assert "/sp.constitution" not in content


def test_workflow_state_template_includes_lane_context():
    content = _read("templates/workflow-state-template.md")

    assert "## Fixed Lifecycle State" in content
    assert "current_stage:" in content
    assert "current_domain:" in content
    assert "next_action:" in content
    assert "blocker_reason:" in content
    assert "final_handoff_decision:" in content
    assert "## Lane Context" not in content


def test_debug_template_reads_constitution_and_feature_context_before_fixing() -> None:
    content = _read("templates/commands/debug.md")

    assert "### Required Context Inputs" in content
    assert ".specify/memory/constitution.md" in content
    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:learning start --command debug --format json}}" in content
    assert "spec.md`, `plan.md`, and `tasks.md`" in content
    assert "`context.md` exists for the active feature" in content


def test_debug_templates_lock_single_path_intake_contract() -> None:
    debug_command = _read("templates/commands/debug.md").lower()
    debug_thinker = _read("templates/worker-prompts/debug-thinker.md").lower()
    debug_contract_planner = _read("templates/worker-prompts/debug-contract-planner.md").lower()

    assert "mandatory intake contract" in debug_command
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


def test_analyze_template_requires_lane_resolution_before_branch_guessing() -> None:
    content = _read("templates/commands/analyze.md")
    lowered = content.lower()

    assert "{{specify-subcmd:lane resolve --command analyze --ensure-worktree}}" in content
    assert "if `feature_dir` is not already explicit" in lowered
    assert "before guessing from branch-only context" in lowered
    assert "when lane resolution returns a materialized lane worktree" in lowered
    assert "must not switch branches" in lowered
    assert 'implicitly check out a "correct" feature branch' in lowered
    assert "mutate git state" in lowered


def test_specify_and_plan_templates_route_feasibility_gaps_through_deep_research():
    specify = _read("templates/commands/specify.md")
    plan = _read("templates/commands/plan.md")

    assert "label: Prove Feasibility Before Plan" in specify
    assert "agent: sp.deep-research" in specify
    assert "Only `final-handoff-decision` may decide whether the canonical next command is `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`." in specify
    assert "Use `/sp.deep-research` when the requirements are clear enough but a planning-critical implementation chain still needs external proof or a disposable demo." in specify
    assert "Feasibility Evidence From Deep Research" in plan
    assert "Planning Handoff From Deep Research" in plan
    assert "Deep Research Traceability Matrix" in plan
    assert "every architecture, module-boundary, API/library, data-flow, validation, or residual-risk decision derived from deep research must cite at least one `PH-###` item" in plan
    assert "Treat the `Planning Handoff` section in `deep-research.md` as a direct planning input" in plan
    assert "Run {{invoke:deep-research}} before planning" in plan


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
    assert "git-baseline freshness in `.specify/project-map/index/status.json` as the truth source" in lowered
    assert "successful-refresh finalizer" in lowered
    assert "manual override/fallback" in lowered


def test_spec_template_defines_scope_boundaries_without_open_clarification_examples():
    content = _read("templates/spec-template.md")
    lowered = content.lower()

    assert "## Ideal Complete Requirement Shape" in content
    assert "### Complete Capability Shape" in content
    assert "### Complete Usage Expectations" in content
    assert "### Domain-Expected Completeness Checks" in content
    assert "## Current Delivery Boundary" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content
    assert "### Boundary Constraints" in content
    assert "## Decision Capture" in content
    assert "### Locked Decisions" in content
    assert "### Claude Discretion" in content
    assert "### Canonical References" in content
    assert "### Deferred / Future Ideas" in content
    assert "### Event / Trigger Model" in content
    assert "### Protocol / Contract Notes" in content
    assert "### Failure, Retry, and Visibility Semantics" in content
    assert "### Configuration and Rollout Notes" in content
    assert "retention, archival, or cleanup concern" in content
    assert "[NEEDS CLARIFICATION:" not in content
    assert "coherent first release" in lowered
    assert "viable mvp" not in lowered
    assert "scope boundaries" not in lowered


def test_shared_artifact_templates_include_profile_fidelity_overlays():
    spec_content = _read("templates/spec-template.md")
    assert "Ideal Complete Requirement Shape" in spec_content
    assert "Current Delivery Boundary" in spec_content
    assert "## Fidelity Requirements" in spec_content
    assert "### Reference Object" in spec_content
    assert "### Required Fidelity" in spec_content
    assert "### Reference Behavior Inventory" in spec_content

    alignment_lowered = _read("templates/alignment-template.md").lower()
    assert "completeness convergence report" in alignment_lowered
    assert "domain closure log" in alignment_lowered
    assert "batch adversarial review summary" in alignment_lowered
    assert "critical gaps and reopen decisions" in alignment_lowered


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
    assert "fidelity requirements and reference behavior inventory" in specify_content.lower()
    assert "Reference Behavior Inventory" in plan_command
    assert "Reference Fidelity Inputs" in plan_command
    assert "reference behavior" in tasks_command.lower()

    context_lowered = _read("templates/context-template.md").lower()
    assert "impact and constraint map" in context_lowered
    assert "critical adjacent effects" in context_lowered
    assert "change propagation matrix" in context_lowered


def test_context_template_exists_and_captures_planning_context():
    content = _read("templates/context-template.md")

    assert "# Impact and Constraint Map:" in content
    assert "## Affected Surfaces" in content
    assert "## Upstream Dependencies" in content
    assert "## Downstream Dependencies and Consumers" in content
    assert "## Product Boundary Constraints" in content
    assert "## Domain-Expected Completeness Checks" in content
    assert "## Critical Adjacent Effects" in content
    assert "## Existing Capability and Reuse Notes" in content
    assert "## Change Propagation Matrix" in content
    assert "## Locked Decisions Carry-Forward" in content
    assert "## Canonical References" in content
    assert "## Outstanding Questions" in content
    assert "## Deferred / Future Ideas" in content
    assert "# Feature Context:" not in content


def test_workflow_state_template_exists_and_captures_phase_lock_contract():
    content = _read("templates/workflow-state-template.md")

    assert "# Workflow State:" in content
    assert "## Current Command" in content
    assert "active_command:" in content
    assert "status:" in content
    assert "## Phase Mode" in content
    assert "phase_mode:" in content
    assert "summary:" in content
    assert "## Fixed Lifecycle State" in content
    assert "current_stage:" in content
    assert "current_domain:" in content
    assert "next_action:" in content
    assert "blocker_reason:" in content
    assert "final_handoff_decision:" in content
    assert "intent-analysis" in content
    assert "intent-confirmation" in content
    assert "question-batch" in content
    assert "batch-adversarial-review" in content
    assert "completeness-audit" in content
    assert "final-handoff-decision" in content
    assert "goal-and-users" in content
    assert "acceptance-and-completeness-gap-closure" in content
    assert "/sp.plan" in content
    assert "/sp.clarify" in content
    assert "/sp.deep-research" in content


def test_workflow_state_template_documents_recovery_sections() -> None:
    content = _read("templates/workflow-state-template.md")

    assert "## Current Command" in content
    assert "## Phase Mode" in content
    assert "## Fixed Lifecycle State" in content
    assert "blocker_reason: [None | Why progress is blocked or why a domain was reopened]" in content
    assert "final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]" in content
    assert "Re-read this file first after compaction or session recovery." not in content


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


def test_testing_workflow_commands_preserve_downstream_control_plane_semantics() -> None:
    build_content = _read("templates/commands/test-build.md")
    asset_block = _extract_outline_step_block(
        build_content,
        "11. **Generate durable testing assets**",
        "12. **Push the contract back into the main workflow**",
    ).lower()

    contract_start = asset_block.find("write `.specify/testing/testing_contract.md` with:")
    playbook_start = asset_block.find("write `.specify/testing/testing_playbook.md` with:")
    baseline_start = asset_block.find("write `.specify/testing/coverage_baseline.json`", playbook_start)
    assert contract_start != -1
    assert playbook_start != -1
    assert baseline_start != -1

    contract_block = asset_block[contract_start:playbook_start]
    playbook_block = asset_block[playbook_start:baseline_start]
    assert "covered-module rules" in contract_block
    assert "covered-module status values" in contract_block
    assert "local integration seam expectations" in contract_block
    assert "covered-module rules" in playbook_block
    assert "adding or changing tests" in playbook_block
    assert "local integration seam expectations and examples" in playbook_block
    assert "preserve each lane's canonical `validation_command`" in asset_block
    assert re.search(r"`validation_command`\s+remains the lane acceptance command", asset_block)
    assert "compatibility field for existing packet consumers" in asset_block
    assert "do not replace it with a command-tier map" in asset_block
    assert re.search(r"`focused`\s+command should mirror the canonical `validation_command`", asset_block)
    assert "unless the build plan records an explicit exception" in asset_block
    assert "`full` command is the broader regression/final-verification tier" in asset_block
    assert "must not be treated as the lane acceptance command" in asset_block


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

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
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
    assert "{{specify-subcmd:learning start --command implement --format json}}" in content
    assert "Required options: `--command`, `--type`, `--summary`, `--evidence`" in content
    assert ".specify/project-map/root/ARCHITECTURE.md" not in content
    assert ".specify/project-map/root/STRUCTURE.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content
    assert "Use `/sp-map-update` when the touched area is localized" in content
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
    assert "dispatch-blocking runtime condition" in lowered
    assert "Dispatch failure is not permission to continue locally." in content
    assert "A lane is dispatch-ready only if its validated `WorkerTaskPacket` includes" in content
    assert "If any required packet field is missing, do not dispatch and do not execute inline." in content
    assert "The only legal action is to repair the packet or stop as `subagent-blocked`." in content
    assert "Dispatch failure is not permission to continue locally." in content
    assert "delegation_confidence" not in lowered
    assert "enough context" not in lowered
    assert "low-context" not in lowered
    assert "two or more safe validated packets" in lowered
    assert "dispatch-blocking runtime condition is present" in lowered
    assert "exactly one safe validated packet is ready" in lowered
    assert "two or more safe validated packets with isolated write sets" in lowered
    assert "`subagent-blocked`" in lowered
    assert "refresh the project cognition runtime through `{{invoke:map-update}}` when the touched area is localized" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in lowered
    assert "including unresolved `open_gaps`" in lowered
    assert "if you cannot complete that refresh in the current pass" in lowered
    assert ".specify/project-map/index/status.json" not in lowered
    assert "successful-refresh finalizer" in lowered
    assert "manual override/fallback" in lowered
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


def test_implement_template_requires_resume_audit_before_trusting_terminal_state():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    assert "resume audit" in lowered
    assert "terminal-audit-required" in lowered
    assert "checked tasks as claims" in lowered
    assert "consumer evidence" in lowered
    assert "do not preserve `resolved`" in lowered


def test_implement_template_defines_leader_only_milestone_scheduler_contract():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "## Orchestration Model" in content
    assert "leader and orchestrator" in lowered
    assert "not the concrete implementer" in lowered
    assert "use `execution_model: subagent-mandatory` for ready implementation batches" in lowered
    assert "dispatch `one-subagent` when one validated `workertaskpacket` is ready" in lowered


def test_runtime_alignment_prefers_cognition_gate_over_layered_atlas() -> None:
    debug_template = _read("templates/commands/debug.md")
    build_template = _read("templates/commands/implement.md")
    shared_gate = _read("templates/command-partials/common/context-loading-gradient.md")
    navigation_shim = _read("templates/command-partials/common/navigation-check.md")
    lowered = build_template.lower()
    lowered_gate = shared_gate.lower()
    lowered_shim = navigation_shim.lower()

    assert "DEBUG-HANDBOOK.md" not in debug_template
    assert ".specify/project-cognition/status.json" in debug_template
    assert ".specify/project-cognition/slices/debug.json" in debug_template
    assert ".specify/project-cognition/graph/claims.json" in debug_template
    assert ".specify/project-cognition/graph/conflicts.json" in debug_template
    assert "BUILD-HANDBOOK.md" not in build_template
    assert ".specify/project-cognition/status.json" in build_template
    assert ".specify/project-cognition/slices/change.json" in build_template
    assert "project cognition runtime" in lowered_gate
    assert ".specify/project-cognition/status.json" in shared_gate
    assert ".specify/project-cognition/graph/nodes.json" in shared_gate
    assert ".specify/project-cognition/graph/edges.json" in shared_gate
    assert ".specify/project-cognition/graph/claims.json" in shared_gate
    assert ".specify/project-cognition/graph/conflicts.json" in shared_gate
    assert "`stale` -> block and refresh through `sp-map-update`" in shared_gate
    assert "`support_drift` -> stop and tell the user to resolve support-surface drift" in shared_gate
    assert "`partial_refresh` -> tell the user the refresh was recorded but readiness did not pass" in shared_gate
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


def test_tasks_template_requires_analyze_compatible_self_audit_and_remediation_mode():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "Analyze-Compatible Task Self-Audit" in content
    assert "buildable `FR-*`" in content
    assert "locked planning decision" in lowered
    assert "Implementation Constitution" in content
    assert "Task Guardrail Index" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content
    assert "Analyze Remediation Mapping" in content
    assert "resolved | deferred | not_applicable | escalated" in content
    assert "Escalation is terminal for the current `sp-tasks` run" in content
    assert "sets `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`" in content
    assert "No more than one task-layer remediation cycle is expected" in content
    assert "Do not treat repeated task/analyze loops as normal workflow" in content


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
    assert "dispatch-blocking" in debug_content.lower() or "subagent-blocked" in debug_content.lower()
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
    assert "consumer evidence" in implementer.lower()
    assert "created but not wired" in implementer.lower()

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
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:learning start --command checklist --format json}}" in lowered
    assert "required options: `--command`, `--type`, `--summary`, `--evidence`" in lowered
    assert ".specify/project-cognition/status.json" in lowered
    assert ".specify/project-cognition/slices/change.json" in lowered
    assert "build-handbook.md" not in lowered
    assert "run `{{invoke:map-update}}`" in lowered
    assert "if the checklist reveals planning-critical requirement gaps" in lowered
    assert "recommend `/sp-specify`" in lowered or "recommend `/sp.specify`" in lowered
    assert "recommend `/sp-plan`" in lowered
    assert "recommend `/sp-analyze`" in lowered


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Completeness Convergence Report:" in content
    assert "## Initial Intent Analysis" in content
    assert "## Domain Closure Log" in content
    assert "## Batch Adversarial Review Summary" in content
    assert "## Critical Gaps and Reopen Decisions" in content
    assert "## Completeness Audit Outcome" in content
    assert "## Planning Gate Recommendation" in content
    assert "## Release Decision" in content
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
    assert "PROJECT_MAP_STATUS = (Get-ProjectMapStatusPath -RepoRoot $paths.REPO_ROOT)" in ps_check
    assert 'PROJECT_MAP_HELPER = (Join-Path $paths.REPO_ROOT ".specify/scripts/powershell/project-map-freshness.ps1")' in ps_check
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
    assert '--arg project_map_status "$(project_map_status_path "$REPO_ROOT")"' in sh_check
    assert '--arg project_map_helper "$REPO_ROOT/.specify/scripts/bash/project-map-freshness.sh"' in sh_check
    assert '"CONTEXT":"%s"' in sh_check
    assert '--arg context "$CONTEXT"' in sh_setup
    assert '--arg feature_dir "$FEATURE_DIR"' in sh_setup
    assert '"FEATURE_DIR":"%s"' in sh_setup
    assert '"CONTEXT":"%s"' in sh_setup


def test_project_map_refresh_guidance_uses_git_baseline_and_dirty_fallback():
    legacy_owned_surfaces = [
        "README.md",
        "docs/quickstart.md",
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/clarify.md",
        "scripts/bash/update-agent-context.sh",
        "scripts/powershell/update-agent-context.ps1",
    ]

    stale_normal_path_phrases = [
        "should mark `.specify/project-map/index/status.json` dirty and run",
        "mark `.specify/project-map/index/status.json` dirty through the project cognition freshness helper and recommend",
        "prefer `specify project-map mark-dirty` as the shared dirty-mark path",
    ]
    for path in legacy_owned_surfaces:
        lowered = _read(path).lower()
        if path in {"README.md", "docs/quickstart.md"}:
            assert "default brownfield runtime truth surface" in lowered
            assert "compatibility/export surfaces only during the migration window" in lowered
            assert "map-update" in lowered
            assert "map-scan" in lowered
            assert "map-build" in lowered
        else:
            assert "git-baseline freshness" in lowered
            assert "truth source" in lowered
            assert "complete-refresh" in lowered
            assert "successful-refresh finalizer" in lowered
            assert "manual override/fallback" in lowered
            assert "if a full refresh can be completed now" in lowered
            assert "otherwise use" in lowered
        for phrase in stale_normal_path_phrases:
            assert phrase not in lowered

    for path in [
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/fast.md",
    ]:
        lowered = _read(path).lower()
        assert "project cognition runtime" in lowered
        assert "map-update" in lowered
        assert "complete-refresh" in lowered
        assert "manual override/fallback" in lowered
        assert "git-baseline freshness" not in lowered


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


def test_specify_template_requires_fixed_heavy_draft_ledger_contract():
    content = _read("templates/commands/specify.md")
    observer_prompt = _read("templates/worker-prompts/specify-observer.md")
    lowered = content.lower()

    assert "specify-draft.md" in content
    assert "create or resume `specify_draft_file` immediately after `feature_dir` is known" in lowered
    assert "content ledger for the whole discovery run" in lowered
    assert "current domain" in lowered
    assert "recent question-batch disposition" in lowered
    assert "adversarial-review findings" in lowered
    assert "confirmed facts" in lowered
    assert "reopen the current domain" in lowered
    assert "completeness gaps" in lowered
    assert "next question target" in lowered
    assert "# Specify Observer Worker Prompt" in observer_prompt
    assert "missing_critical_capabilities" in observer_prompt
    assert "release_blockers" in observer_prompt


def test_specify_template_requires_brainstorming_lock_flow_and_handoff_chain() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "brainstorming kernel" in lowered
    assert "facts-lock" in lowered
    assert "route-lock" in lowered
    assert "intent-lock" in lowered
    assert "complexity-lock" in lowered
    assert "brainstorming/facts.json" in content
    assert "brainstorming/route.json" in content
    assert "brainstorming/intent.json" in content
    assert "brainstorming/complexity.json" in content
    assert "handoff-to-specify.json" in content
    assert "dynamic is allowed only" in lowered or "dynamic routing only" in lowered
    assert "hard unknown" in lowered
    assert "reopen upstream truth" in lowered or "reopen is a first-class workflow action" in lowered
    assert "reopen" in lowered


def test_compiled_artifact_templates_preserve_route_and_complexity_truth() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")

    assert "## Brainstorming Truth Inputs" in spec
    assert "**Locked route**" in spec
    assert "`brainstorming/route.json`" in spec
    assert "**Locked complexity**" in spec
    assert "`brainstorming/complexity.json`" in spec
    assert "Must Preserve" in spec
    assert "Allowed Optimization Scope" in spec

    assert "## Route And Complexity Summary" in alignment
    assert "Primary Route" in alignment
    assert "**Complexity Level**: [T1 Local | T2 Structured | T3 Cross-Boundary | T4 Reconstruction]" in alignment
    assert "Hard Unknowns Cleared" in alignment
    assert "Reopen Required" in alignment

    assert "## Brainstorming-Derived Execution Context" in context
    assert "Truth Owner" in context
    assert "Compatibility Constraints" in context
    assert "Allowed Internal Redesign" in context

    assert "## Truth Sources Used For Route And Intent Lock" in references


def test_plan_tasks_and_implement_templates_consume_structured_handoff_contracts() -> None:
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")

    assert "handoff-to-plan.json" in plan
    assert "route, intent, complexity" in plan.lower()
    assert "handoff-to-tasks.json" in tasks
    assert "task packet" in tasks.lower()
    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement.lower()
    assert "allowed optimization scope" in implement.lower()
    assert "stop-and-reopen conditions" in implement.lower()


def test_implement_template_requires_structured_execution_contract_from_tasks() -> None:
    implement = _read("templates/commands/implement.md").lower()

    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement
    assert "allowed optimization scope" in implement
    assert "stop-and-reopen conditions" in implement
    assert "cannot redefine the product goal" in implement or "must not redefine the product goal" in implement


def test_implement_execution_state_template_requires_structured_execution_contract_from_tasks() -> None:
    content = _read("templates/implement-execution-state-template.json")

    assert '"status": "gathering"' in content
    assert '"current_batch": null' in content
    assert '"complexity_level": null' in content
    assert '"active_packet_ids": []' in content
    assert '"must_preserve": []' in content
    assert '"allowed_optimization_scope": []' in content
    assert '"open_reopen_conditions": []' in content


def test_specify_template_locks_fixed_heavy_discovery_lifecycle_contract() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "intent-analysis" in content
    assert "intent-confirmation" in content
    assert "question-batch" in content
    assert "batch-adversarial-review" in content
    assert "completeness-audit" in content
    assert "final-handoff-decision" in content

    assert "intent-analyst" in content
    assert "adversarial-reviewer" in content
    assert "completeness-auditor" in content

    assert "goal-and-users" in content
    assert "triggers-and-primary-flow" in content
    assert "boundaries-and-non-goals" in content
    assert "failure-paths-exceptions-and-permissions" in content
    assert "dependencies-constraints-and-upstream-downstream-impact" in content
    assert "acceptance-and-completeness-gap-closure" in content

    assert "task classification" not in lowered
    assert "active_profile" not in content
    assert "coverage_mode" not in content
    assert "observer gate" not in lowered


def test_specify_artifact_templates_lock_fixed_heavy_discovery_shapes() -> None:
    alignment = _read("templates/alignment-template.md")
    alignment_lowered = alignment.lower()
    spec = _read("templates/spec-template.md")

    assert "completeness convergence report" in alignment_lowered
    assert "initial intent analysis" in alignment_lowered
    assert "domain closure log" in alignment_lowered
    assert "batch adversarial review summary" in alignment_lowered
    assert "Critical Gaps and Reopen Decisions" in alignment
    assert "completeness audit outcome" in alignment_lowered
    assert "High-Impact Decision Forks" not in alignment
    assert "active_profile" not in alignment
    assert "task classification" not in alignment_lowered
    assert "coverage mode" not in alignment_lowered
    assert "observer gate" not in alignment_lowered

    assert "Ideal Complete Requirement Shape" in spec
    assert "Current Delivery Boundary" in spec
    assert "This layer captures the complete useful feature form" in spec
    assert "This layer captures the current project-bound delivery boundary" in spec


def test_agent_file_template_captures_lane_recovery_rules():
    content = _read("templates/agent-file-template.md")
    lowered = content.lower()

    assert "## Workflow Recovery Rules" in content
    assert "lane-first, not branch-first" in lowered
    assert "durable lane state" in lowered
    assert "explicit feature paths" in lowered
    assert "/sp.plan" in content
    assert ".specify/features/<feature>/" in content


def test_prd_scan_template_uses_shared_subagent_dispatch_contract() -> None:
    content = _read("templates/commands/prd-scan.md")
    _assert_subagent_dispatch_contract(content, "prd-scan")


def test_prd_build_template_uses_shared_subagent_dispatch_contract() -> None:
    content = _read("templates/commands/prd-build.md")
    _assert_subagent_dispatch_contract(content, "prd-build")


def test_implement_template_requires_structured_execution_contract_from_tasks() -> None:
    implement = _read("templates/commands/implement.md").lower()

    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement
    assert "allowed optimization scope" in implement
    assert "stop-and-reopen conditions" in implement
    assert "redefining the user's locked goal" in implement or "must not redefine the product goal" in implement
