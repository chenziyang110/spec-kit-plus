import json
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


def _launcher_query(intent: str) -> str:
    return f'{{{{specify-subcmd:project-cognition query --intent {intent} --query-plan "<query_plan_json>" --format json}}}}'


def _launcher_compass(intent: str) -> str:
    return f'{{{{specify-subcmd:project-cognition compass --intent {intent} --query="$ARGUMENTS" --format json}}}}'


def test_inline_project_cognition_update_uses_shared_partial() -> None:
    shared = _read("templates/command-partials/common/inline-project-cognition-update.md")
    required_planner_terms = (
        "project-cognition closeout-plan --workflow",
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
    )
    for term in required_planner_terms:
        assert term in shared, f"inline closeout partial missing {term}"

    assert "result_state" in shared
    assert "recorded" in shared
    assert "verification_evidence" in shared
    assert "generated_surface_notes" in shared

    for path in (
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ):
        content = _read(path)
        for term in required_planner_terms:
            assert term in content, f"{path} missing {term}"

    common_partials = [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/command-partials/common/navigation-check.md",
    ]
    for path in common_partials:
        content = _read_project_file(path)
        assert "inline-project-cognition-update.md" in content, path
        assert "project-cognition update --changed-path" not in content, path

    commands = [
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/map-update.md",
    ]
    for path in commands:
        assert "inline-project-cognition-update.md" in _read_project_file(path), path


def test_source_changing_sp_workflows_include_inline_cognition_closeout_contract() -> None:
    commands = [
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/analyze.md",
        "templates/commands/specify.md",
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]
    for path in commands:
        content = _read_project_file(path)
        assert "inline-project-cognition-update.md" in content, path
        assert "project-cognition mark-dirty" not in content or "inline-project-cognition-update.md" in content, path

    shared = _read("templates/command-partials/common/inline-project-cognition-update.md")
    for term in (
        "project-cognition closeout-plan --workflow",
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
        "templates/worker-prompts/code-quality-reviewer.md",
        "templates/worker-prompts/spec-reviewer.md",
    ):
        content = _read(path)
        assert "verification" in content, f"{path} missing canonical worker verification field"
        assert "generated_surfaces" in content, f"{path} missing canonical generated_surfaces field"


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
        "templates/worker-prompts/code-quality-reviewer.md",
        "templates/worker-prompts/spec-reviewer.md",
    ):
        content = _read(path)
        for field in required_fields:
            assert field in content, f"{path} missing {field}"


def _assert_agent_assisted_cognition_gate(content: str, intent: str) -> None:
    assert _launcher_compass(intent) in content
    assert "project-cognition query" in content
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
    assert "project cognition and project memory are always available" in lowered
    assert "even without an active `sp-*` workflow" in lowered
    assert "when existing-system truth matters" in lowered
    assert "before broad source inspection" in lowered
    assert "narrow live reads" in lowered
    assert ".specify/memory/project-rules.md" in block
    assert ".specify/memory/learnings/INDEX.md" in block

    assert "## Workflow Recommendations" in block
    assert "do not auto-enter an `sp-*` workflow" in lowered
    assert "unless the user invokes it" in lowered
    assert "recommend `sp-discussion`" in lowered
    assert "`sp-specify` for formal alignment" in lowered
    assert "`sp-deep-research` for feasibility proof" in lowered
    assert "`sp-debug` for root-cause diagnosis" in lowered

    assert "## Command Surface Rules" in block
    assert "specify --help" in block
    assert "specify create-feature" in block
    assert ".specify/scripts/bash/create-new-feature.sh" in block
    assert ".specify/scripts/powershell/create-new-feature.ps1" in block

    assert "## Durable State" in block
    assert "prefer durable workflow state and explicit feature paths" in lowered
    assert "over branch name or chat memory" in lowered
    assert "project cognition freshness truthful" in lowered
    assert "store reusable lessons in project memory" in lowered

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
        "primary_outputs: '`plan.md`, `research.md`, `quickstart.md`, `plan-contract.json`, "
        "and `workflow-state.md` under the active `FEATURE_DIR`; `data-model.md` and `contracts/` "
        "when the feature scope demands them; `planning/handoffs/<lane-id>.json`, "
        "`planning/evidence-index.json`, and `planning/checkpoints.ndjson` only when delegated "
        "planning lanes are used.'"
    ) in plan
    assert (
        "primary_outputs: '`FEATURE_DIR/tasks.md` and `workflow-state.md`; `task-index.json` "
        "when useful for light mode; `handoff-to-tasks.json`, `task-packets/*.json`, "
        "`task-generation/handoffs/<lane-id>.json`, `task-generation/evidence-index.json`, "
        "and `task-generation/checkpoints.ndjson` when standard/heavy mode uses delegated "
        "task-generation lanes or downstream delegated implementation needs packets.'"
    ) in tasks


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
    assert "ask only the highest-impact question" in lowered
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
    assert "discussion-state.md" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "technical-options.md" in content
    assert "project-context.md" in content
    assert "open-questions.md" in content
    assert "handoff-to-specify.md" in content
    assert "active | blocked | handoff-ready | completed | abandoned" in content
    assert "multiple incomplete discussions" in lowered
    assert "updated_at" in content
    assert "do not create feature branches" in lowered
    assert "do not edit source code" in lowered
    assert "do not edit tests" in lowered
    assert "do not automatically run" in lowered
    assert "explicit user" in lowered
    assert "{{spec-kit-include: ../command-partials/discussion/shell.md}}" in content
    _assert_discussion_advisor_upgrade_contract(content)


def test_discussion_command_locks_context_boundary_before_technicalization() -> None:
    content = _read_project_file("templates/commands/discussion.md")
    lowered = content.lower()

    assert "product manager perspective" in lowered
    assert "technical expert perspective" in lowered
    assert "context-grounding" in content
    assert "technical-options" in content
    assert "handoff-assessment" in content
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
    assert "project-cognition compass --intent discussion" in content
    assert "project-cognition query --query-plan" in content
    assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in content
    assert "project-cognition query --intent plan" not in content
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
    assert "judgment:" in lowered
    assert "evidence:" in lowered
    assert "risk:" in lowered
    assert "recommendation:" in lowered
    assert "next discussion paths:" in lowered
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
    assert "ask only the highest-impact question" in lowered


def test_discussion_offers_optional_ui_interaction_stage_for_ui_requirements() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    content_lower = content.lower()
    shell_lower = shell.lower()
    state_lower = state.lower()
    ui_section = content_lower.split("## optional ui and interaction discussion", 1)[1]
    ui_section = ui_section.split("## handoff assessment", 1)[0]

    assert "ui-interaction-discussion" in content
    assert "after functional discussion is stable" in content_lower
    assert "no explicit handoff request is active" in content_lower
    assert "handoff-assessment.md` first" in content
    assert "only when no explicit handoff request is active" in content_lower
    assert "handoff-assessment.md` first" in content.split("6. `ui-interaction-discussion`", 1)[1]
    assert "optional ui and interaction discussion" in content_lower
    assert "ui decisions are blocking readiness" in content_lower
    assert ui_section.index("handoff-assessment.md` first") < ui_section.index("return to `ui-interaction-discussion`")
    assert "ui_discussion_status: offered" in content
    assert "ui_discussion_status: accepted" in content
    assert "ui_discussion_status: completed" in content
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
    assert "ui-interaction-discussion" in state
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
    assert "ordinary turns append" in lowered
    assert "compact event" in lowered
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
    assert "handoff-to-specify.md" in content
    assert "handoff-to-specify.json" in content
    assert "handoffs/<candidate_id>" not in content
    assert "split-plan.md" not in content
    assert "truth pass" in lowered
    assert "boss-friendly advisor response" in lowered
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
    assert "ui-interaction-discussion" in content
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
    assert "discussion-state.md" in content
    assert "handoff-to-specify.md" in content
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
    assert "handoff_review_status: not-started | draft | self-review-passed | user-confirmed | blocked" in content
    assert "handoff_user_confirmed_at:" in content
    assert "handoff_blocker_reason:" in content
    assert "handoff_consumption_status: not_consumed | consumed" in content
    assert "consumed_at:" in content
    assert "consumed_by_feature_dir:" in content
    assert "handoff-to-specify.md draft after explicit user request and boundary lock" in content
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
    assert "before running `{SCRIPT}`" in content
    assert "no arguments with exactly one unconsumed `status: handoff-ready`" in content
    assert "If multiple unconsumed `handoff-ready` discussions exist" in content
    assert "SOURCE_HANDOFF_MD" in content
    assert "SOURCE_HANDOFF_JSON" in content
    assert "SOURCE_DISCUSSION_SLUG" in content
    assert "entry_source: sp-discussion" in content
    assert "handoff_status: handoff-ready" in content
    assert "quality_gate.status: user_confirmed" in content
    assert "planning_gate_status: ready" in content
    assert "hard_unknown_count: 0" in content
    assert "open_conflict_count: 0" in content
    assert "Handoff Reviewer Guide" in content
    assert "blocked_by_handoff_integrity" in content
    assert "block before feature creation" in lowered
    assert "If the Markdown carries protected source evidence or settled decisions that the JSON omits" in content
    assert "Do not pass the raw handoff file path" in content
    assert "Derive the feature description" in content
    assert "coverage_status" in content
    assert "planning_gate_status" in content
    assert "hard_unknown_count" in content
    assert "open_conflict_count" in content
    assert "read the handoff-declared source files" in lowered
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
    assert "technical-options.md" in content
    assert "project-context.md" in content
    assert "source_signal_disposition" in content
    assert "source_files_read" in content
    assert "capability-like" in lowered
    assert "not only the handoff summary" in lowered
    assert "specify discussion mark-consumed" in content
    assert "consumed_by_feature_dir" in content
    assert "handoff_consumption_status" in content


def test_discussion_handoff_requires_must_preserve_ledger_contract() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    _assert_must_preserve_ledger_contract(content)
    assert "handoff-to-specify.json" in content
    assert "Handoff Reviewer Guide" in content
    assert "Approve only if" in content
    assert "Request changes if" in content
    assert "does not know Spec Kit internals" in content
    assert "Do not ask for a bare yes/no confirmation without review criteria" in content
    assert "markdown" in lowered and "json" in lowered
    assert "id" in lowered
    assert "claim" in lowered
    assert "source" in lowered
    assert "downstream_requirement" in content
    assert "owner" in lowered
    assert "latest_resolve_phase" in content
    assert "stop_and_reopen_condition" in content
    assert "do not silently" in lowered


def test_specify_discussion_handoff_has_coverage_and_planning_gate_split() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    _assert_must_preserve_ledger_contract(content)
    assert "entry_source: sp-discussion" in content
    assert "blocked_by_hard_unknowns" in content
    assert "blocked_by_conflict" in content
    assert "blocked_by_incomplete_coverage" in content
    assert "blocked_by_handoff_integrity" in content
    assert "coverage and planning readiness are separate" in lowered
    assert "markdown" in lowered and "json" in lowered and "mismatch" in lowered


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
    assert "truth pass" in lowered
    assert "discussion compass" in lowered
    assert "proactive implication mapping" in lowered
    assert "handoff Markdown path, JSON path, or discussion slug" in content
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
    assert "project-cognition compass --intent discussion" in content
    assert "project-cognition query --intent discussion" in content
    assert "project-cognition compass --intent plan" not in content
    assert "project-cognition query --intent plan" not in content
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


def test_specify_template_uses_alignment_first_contract():
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
    assert "{{specify-subcmd:learning start --command specify --format json}}" in content
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
    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "two or three approaches" in lowered or "2-3 approaches" in lowered
    assert "semantic term" in lowered
    assert "user review" in lowered
    assert "source_signal_disposition" in content
    assert "source_files_read" in content
    assert "discussion-log.md" in content
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


def test_core_planning_templates_use_logical_atlas_references() -> None:
    legacy_rel_paths = [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ]
    for rel_path in legacy_rel_paths:
        content = _read(rel_path)
        lowered = content.lower()
        _assert_agent_assisted_cognition_gate(content, "plan")
        assert "project-cognition query" in lowered
        assert "minimal_live_reads" in lowered
        assert "build-handbook.md" not in lowered
        assert "build-workflow-contract" not in lowered
        assert "product-and-capability-map" not in lowered
        assert "atlas.entry" not in lowered

    implement = _read("templates/commands/implement.md").lower()
    assert "project-cognition compass --intent implement" in implement
    assert "project-cognition query --query-plan" in implement
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
    assert "sp-specify -> sp-plan -> sp-tasks -> sp-implement" in workflows

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

    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:learning start --command constitution --format json}}" in content
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
            "specify project-cognition query",
            "specify project-cognition complete-refresh",
            "specify project-cognition mark-dirty",
            "specify project-map complete-refresh",
            "specify project-map mark-dirty",
        ):
            if bare in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {bare}")
    assert offenders == []


def test_plan_template_requires_alignment_report_before_planning():
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
    assert "{{specify-subcmd:learning start --command plan --format json}}" in content
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
    assert "If the workload is lightweight safe, use `execution_mode: light`" in content
    assert "If the workload is standard and native subagents are available" in content
    assert "If the workload is heavy or safety-critical" in content


def test_plan_template_records_planning_evidence_paths() -> None:
    content = _read("templates/commands/plan.md")

    assert "planning evidence paths when delegated lanes were used" in content
    assert "delegated_planning_lanes: none" in content
    assert "planning/handoffs/<lane-id>.json" in content


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


def test_tasks_template_documents_shared_routing_before_decomposition():
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
    assert "cognition follow-up" in lowered
    assert "artifact-only task generation" in lowered
    assert "actual source/runtime changes" in lowered
    assert "specify team" not in lowered


def test_tasks_template_uses_adaptive_execution_modes() -> None:
    content = _read("templates/commands/tasks.md")

    _assert_adaptive_plan_tasks_contract(content, "tasks")
    assert "If the task-generation workload is lightweight safe, use `execution_mode: light`" in content
    assert "If the workload is standard and native subagents are available" in content
    assert "If the workload is heavy or safety-critical" in content


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


def test_tasks_and_implement_templates_embed_internal_review_loop_without_public_review_command() -> None:
    tasks = _read("templates/commands/tasks.md")
    task_template = _read("templates/tasks-template.md")
    implement = _read("templates/commands/implement.md")
    workflow_state = _read("templates/workflow-state-template.md")
    combined = "\n".join([tasks, task_template, implement, workflow_state])
    lowered = combined.lower()

    assert "embedded implement review" in lowered
    assert "pre-implement review" in lowered
    assert "join-point drift review" in lowered
    assert "review_window_policy" in combined
    assert "auto_repair_tasks" in combined
    assert "implementation-review/reviews.ndjson" in combined
    assert "implementation-review/repairs.ndjson" in combined
    assert "snapshots/" in lowered
    assert "/sp.review" not in combined
    assert "sp-review" not in combined


def test_implement_template_preserves_workflow_state_review_allowlist() -> None:
    implement = _read("templates/commands/implement.md")
    lowered = implement.lower()

    assert "workflow-state write allowlist" in lowered
    assert "active_profile" in implement
    assert "required_evidence" in implement
    assert "final_handoff_decision" in implement
    assert "analyze gate" in lowered
    assert "must not rewrite" in lowered
    assert "review_gate" in implement
    assert "review_window_policy" in implement


def test_tasks_template_requires_stable_task_identity_for_embedded_repair() -> None:
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "task identity" in lowered
    assert "completed task ids are immutable" in lowered
    assert "append-only" in lowered
    assert "repair_for" in content
    assert "task-index.json" in content
    assert "task-packets" in content
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
    assert "(`spec.md`, `context.md`, `plan.md`, `tasks.md`)" in content
    assert "- CONTEXT = FEATURE_DIR/context.md" in content
    assert ".specify/memory/constitution.md" in content
    assert "Consume the `project-cognition query` bundle." in content
    assert "choose the cognition intent" in lowered
    assert "--intent plan" in content
    assert "--intent implement" in content
    assert "selected_concepts" in content
    assert "rejected_concepts" in content
    assert "route_pack" in content
    assert "minimal_live_reads" in content
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
    assert "selected/rejected concepts" in lowered
    assert "`route_pack`" in content
    assert "Limit the visible findings table to 50 rows for readability" in content
    assert "`Blocker Bundle` and `workflow-state.md` MUST enumerate every blocking finding" in content
    assert "Do not place blocking findings only in overflow summaries" in content
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
    assert "source_files_read" in content
    assert "source_signal_disposition_status" in content
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


def test_debug_template_reads_constitution_and_feature_context_before_fixing() -> None:
    content = _read("templates/commands/debug.md")

    assert "### Required Context Inputs" in content
    assert ".specify/memory/constitution.md" in content
    assert ".specify/memory/project-rules.md" in content
    _assert_learning_index_detail_model(content)
    assert "{{specify-subcmd:learning start --command debug --format json}}" in content
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

    assert "`next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`" in content
    assert "Default handoff: /sp-plan" not in content
    assert "Default handoff: /sp.plan" not in content
    assert "/sp.plan" in content
    assert "brainstorming/handoff-to-specify.json" in content
    assert "source_signal_disposition" in content


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
    specify_lowered = specify.lower()

    assert "/sp.deep-research" in specify
    assert "/sp.plan" in specify
    assert "/sp.clarify" in specify
    assert "recommend exactly one next command" in specify_lowered
    assert "user review" in specify_lowered
    assert "planning-critical" in specify_lowered
    assert "release-decision" not in specify
    assert "final-handoff-decision" not in specify
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
    assert "fidelity requirements and reference behavior inventory" in specify_content.lower()
    assert "Reference Behavior Inventory" in plan_command
    assert "Reference Fidelity Inputs" in plan_command
    assert "reference behavior" in tasks_command.lower()

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
    assert "source_files_read" in content
    assert "source_signal_disposition_status" in content
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
    assert "discussion-state.md" in content
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
        assert f"capture-auto --command {cli_name}" in content
        assert "workflow-state.md" in content


def test_tasks_templates_preserve_user_confirmed_delivery_scope_not_mvp():
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
    assert "user-confirmed delivery sequence" in command_content.lower()
    assert "confirmed delivery scope" in command_content.lower()
    assert "scope reduction requires user confirmation" in command_content.lower()
    assert "suggested first release scope" not in command_content.lower()
    assert "smallest coherent release slice" not in command_content.lower()
    assert "parallel batch" in command_content.lower()
    assert "join point" in command_content.lower()
    assert "write set" in command_content.lower()
    assert "bounded implementation slice" in command_content.lower()
    assert "coffee break" in template_content.lower()
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
    assert "does_not_remove" in packet
    assert "capability_operations" in packet

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
    assert "{{specify-subcmd:learning start --command implement --format json}}" in content
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
    assert "project-cognition closeout-plan --workflow" in lowered
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

        assert "project_cognition_refresh" in content
        assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
        assert "project-cognition closeout-plan --workflow" in content
        assert "update_mode=delta_session" in content
        assert "update_mode=payload_file" in content
        assert "update_argv" in content
        assert "clean closeout keys on `result_state`" in content
        assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
        assert "project-cognition mark-dirty" in content
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
        "templates/command-partials/common/planning-context-loading-gradient.md",
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
        assert "inline project cognition update" in content, path
        assert "sp-map-update is for manual/external maintenance" in content, path
        if path in {
            "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
            "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        }:
            assert "closeout-plan" in content, path
            assert "unknown_path_dispositions" in content, path

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
        if "passive-skills" not in path:
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
    assert "do not run `project-cognition update`, `project-cognition mark-dirty`" in content
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
        assert "inline project cognition update" in content
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
    assert "project-cognition record-refresh" in lowered
    assert "without rerunning `{{invoke:map-scan}}` or `{{invoke:map-build}}`" in lowered

    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        doc = _read(path).lower()
        assert "committing the refreshed source changes does not require a full rebuild by itself" in doc
        assert "project-cognition record-refresh" in doc
        assert "project-cognition complete-refresh" in doc


def test_implement_template_requires_resume_audit_before_trusting_terminal_state():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    assert "resume audit" in lowered
    assert "terminal-audit-required" in lowered
    assert "checked tasks as claims" in lowered
    assert "consumer evidence" in lowered
    assert "real_entrypoint_evidence" in content
    assert "synthetic-only" in lowered
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
    assert "project-cognition compass --intent implement" in content
    assert "minimal_live_reads" in content
    assert "first_pass_paths" in content
    assert "coverage_diagnostics" in content
    assert "expansion_ref" in content
    assert "lexicon -> semantic_intake -> query" in content
    assert "project-cognition lexicon --intent implement" not in content


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


def test_tasks_template_clean_completion_hands_off_to_implement():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "default_handoff: '/sp.implement" in content
    assert "Implement Project" not in content
    assert "recommended next command: `{{invoke:implement}}`" in lowered
    assert "`next_command: /sp.implement`" in content
    assert "implementation remains blocked until this task package passes the implementation-readiness task self-audit" in lowered
    assert "run `{{invoke:analyze}}` only when an existing state file explicitly records a legacy or diagnostic analysis route" in lowered
    assert "hand off directly to `{{invoke:implement}}` from `sp-tasks`" in lowered
    assert "the analyze gate is mandatory" not in lowered


def test_tasks_template_requires_implementation_readiness_self_audit_and_remediation_mode():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "default_handoff: '/sp.implement for a clean completed task package" in content
    assert "/sp.plan, /sp.clarify, or /sp.deep-research when escalated remediation exposes missing upstream truth" in content
    assert "send: false" in content
    assert "Implementation-Readiness Task Self-Audit" in content
    assert "User-Observable Path Coverage" in content
    assert "real_entrypoint_evidence" in content
    assert "synthetic component" in lowered
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
    assert "normal completed or non-escalated task generation" in lowered
    assert "escalated remediation preserves the upstream `next_command`" in content
    assert "stops without an analyze handoff" in lowered


def test_tasks_template_enriched_example_includes_real_entrypoint_packet_fields():
    content = _read("templates/tasks-template.md")
    example = content[content.index("## Enriched Task Reference Example") :]

    assert "| consumer_surfaces |" in example
    assert "| required_evidence |" in example
    assert "real_entrypoint_evidence" in example


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
    assert "real_entrypoint_evidence" in implementer
    assert "kind: real_entrypoint" in implementer
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
    assert "project-cognition query" in lowered
    assert "--query-plan" in lowered
    assert "project-cognition compass --intent plan" in lowered
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
        "prefer `project-cognition mark-dirty` as the shared dirty-mark path",
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
        "templates/commands/clarify.md",
    ]:
        lowered = _read(path).lower()
        assert "cognition follow-up" in lowered
        assert "artifact-only" in lowered
        assert "actual source/runtime changes" in lowered
        assert '{{specify-subcmd:project-cognition mark-dirty --reason "workflow-closeout-failed" --format json}}' in lowered
        assert "project-cognition complete-refresh" not in lowered

    for path in [
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/fast.md",
    ]:
        lowered = _read(path).lower()
        assert "project cognition runtime" in lowered
        assert "map-update" in lowered
        assert "project-cognition closeout-plan --workflow" in lowered
        assert "update_mode=delta_session" in lowered
        assert "dirty only when inline update cannot complete" in lowered
        assert "git-baseline freshness" not in lowered


def test_planning_only_workflows_do_not_dirty_project_cognition_after_artifact_writes():
    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/clarify.md",
        "templates/commands/tasks.md",
    ]:
        lowered = _read(path).lower()

        assert "do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date" in lowered
        assert '{{specify-subcmd:project-cognition mark-dirty --reason "workflow-closeout-failed" --format json}}' in lowered
        assert "project-cognition complete-refresh" not in lowered
        assert "project-cognition validate-build --format json" not in lowered
        assert "artifact-only" in lowered
        assert "cognition follow-up" in lowered
        assert "actual source/runtime changes" in lowered


def test_specify_plan_and_clarify_treat_needs_update_as_planning_advisory():
    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/clarify.md",
        "templates/commands/tasks.md",
    ]:
        lowered = _read(path).lower()

        assert "project-cognition compass --intent plan" in lowered
        assert "minimal_live_reads" in lowered
        assert "coverage_diagnostics" in lowered
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


def test_analyze_command_consumes_planning_and_task_generation_evidence():
    content = _read("templates/commands/analyze.md")
    lowered = content.lower()

    assert "PLANNING_EVIDENCE_INDEX = FEATURE_DIR/planning/evidence-index.json when present" in content
    assert "TASK_GENERATION_EVIDENCE_INDEX = FEATURE_DIR/task-generation/evidence-index.json when present" in content
    assert "read `planning/evidence-index.json` and accepted `planning/handoffs/*.json`" in lowered
    assert "read `task-generation/evidence-index.json` and accepted `task-generation/handoffs/*.json`" in lowered
    assert "accepted planning handoff with no downstream consumer as a plan-layer blocker" in lowered
    assert "accepted task-generation handoff with no downstream consumer as a task-layer blocker" in lowered


def test_specify_and_plan_treat_stale_cognition_as_planning_advisory():
    for path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
    ]:
        lowered = _read(path).lower()

        assert "freshness is `stale`" in lowered
        assert "planning advisory" in lowered
        assert "if freshness is `stale`, stop" not in lowered
        assert "if freshness is `stale`, stop and tell the user to run `{{invoke:map-update}}`" not in lowered
        assert "if freshness is `possibly_stale`" in lowered
        assert "must_refresh_topics` is non-empty" not in lowered
        assert "if task-relevant coverage is insufficient" in lowered
        assert "continue with minimal live reads" in lowered


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
        assert "project-cognition" in content
        assert "PROJECT_COGNITION_BIN" in content
        assert ".specify/config.json" not in content
        assert ".specify/project-map" not in content
        assert "project-map-freshness" not in content


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


def test_brainstorming_handoff_template_supports_context_boundary_quality_gate_and_source_evidence_contract() -> None:
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
    assert downstream_instructions.get("recommended_sequence") == []
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
    assert "source_files_read" in specify
    assert "source_signal_disposition" in specify
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
    assert "source_signal_disposition" in content
    assert "source_files_read" in content
    assert "coverage_status" in content
    assert "planning_gate_status" in content
    assert "hard_unknown_count" in content
    assert "open_conflict_count" in content
    assert "capability-like" in lowered
    assert "not only the handoff summary" in lowered
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


def test_structured_consequence_json_templates_exist() -> None:
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

    assert "handoff-to-plan.json" in plan
    assert "route, intent, complexity" in plan.lower()
    assert "handoff-to-tasks.json" in tasks
    assert "task packet" in tasks.lower()
    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement.lower()
    assert "allowed optimization scope" in implement.lower()
    assert "stop-and-reopen conditions" in implement.lower()


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
    assert "Task Guardrail Index" in tasks_template
    assert "WorkerTaskPacket" in implement
    assert "result handoff" in implement_shell.lower()


def test_plan_template_rejects_cross_project_handoff_without_target_context() -> None:
    plan = _read("templates/commands/plan.md")
    shell = _read("templates/command-partials/plan/shell.md")
    plan_template = _read("templates/plan-template.md")
    contract = json.loads(_read("templates/plan-contract-template.json"))
    combined = "\n".join([plan, shell, plan_template])
    lowered = combined.lower()

    assert "target_project_root" in combined
    assert "quality_gate.user_confirmed" in combined
    assert "hard unknowns" in lowered
    assert "current project's cognition" in lowered
    assert "not proof of target-project implementation facts" in lowered
    assert "artifact-only planning may proceed only with explicit minimal live reads" in lowered
    assert "must not tell the user to run current-project" in lowered
    assert isinstance(contract.get("context_boundary"), dict)
    assert isinstance(contract.get("implementation_target"), dict)
    assert contract.get("target_project_root") is None
    assert contract.get("target_evidence_status") is None


def test_tasks_template_inherits_implementation_target_boundary() -> None:
    tasks = _read("templates/commands/tasks.md")
    shell = _read("templates/command-partials/tasks/shell.md")
    task_template = _read("templates/tasks-template.md")
    packet = json.loads(_read("templates/task-packet-template.json"))
    combined = "\n".join([tasks, shell, task_template])
    lowered = combined.lower()

    assert "target root" in lowered
    assert "target-relative path" in lowered
    assert "evidence status" in lowered
    assert "mp-*" in lowered
    assert "boundary constraints" in lowered
    assert "forbidden drift" in lowered
    assert "must not silently point to the current repository" in lowered
    assert "reference-only" in lowered
    assert isinstance(packet.get("implementation_target"), dict)
    assert packet.get("target_root") is None
    assert packet.get("target_relative_paths") == []
    assert packet.get("evidence_status") is None
    assert packet.get("boundary_constraints") == []


def test_structured_json_templates_preserve_fidelity_status_fields() -> None:
    handoff = _read("templates/brainstorming-handoff-specify-template.json")
    plan_contract = _read("templates/plan-contract-template.json")
    implement_state = _read("templates/implement-execution-state-template.json")

    for content in (handoff, plan_contract, implement_state):
        assert '"must_preserve"' in content
        assert "mp_obligations" in content or "must_preserve" in content

    assert '"coverage_status"' in handoff
    assert '"planning_gate_status"' in handoff
    assert '"hard_unknown_count"' in handoff
    assert '"open_conflict_count"' in handoff
    assert '"open_conflicts"' in plan_contract
    assert '"applied_mp_obligations"' in implement_state


def test_implement_template_rejects_locked_goal_redefinition() -> None:
    implement = _read("templates/commands/implement.md").lower()

    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement
    assert "allowed optimization scope" in implement
    assert "stop-and-reopen conditions" in implement
    assert "cannot redefine the product goal" in implement or "must not redefine the product goal" in implement


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
    assert '"complexity_level": null' in content
    assert '"active_packet_ids": []' in content
    assert '"must_preserve": []' in content
    assert '"applied_mp_obligations": []' in content
    assert '"allowed_optimization_scope": []' in content
    assert '"open_reopen_conditions": []' in content
    assert '"open_conflict_count": 0' in content
    assert '"hard_unknown_count": 0' in content


def test_implement_execution_state_template_includes_embedded_review_defaults() -> None:
    payload = json.loads(_read("templates/implement-execution-state-template.json"))

    assert payload["review_gate"] == {
        "mode": "embedded",
        "status": "pending",
        "scope": "pre-implement",
        "auto_repair_tasks": True,
        "last_reviewed_batch": None,
        "latest_review_id": None,
        "latest_repair_id": None,
    }
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
    assert "source_signal_disposition" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
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

    assert "handoff-to-implement.json" in implement
    assert "must-preserve invariants" in implement
    assert "allowed optimization scope" in implement
    assert "stop-and-reopen conditions" in implement
    assert "redefining the user's locked goal" in implement or "must not redefine the product goal" in implement
