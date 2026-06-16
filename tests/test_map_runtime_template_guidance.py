import re
from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHARED_COGNITION_PARTIALS = (
    "templates/command-partials/common/context-loading-gradient.md",
    "templates/command-partials/common/planning-context-loading-gradient.md",
)
SHARED_COGNITION_GUIDANCE_SURFACES = (
    *SHARED_COGNITION_PARTIALS,
    "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
)
COGNITION_INTAKE_COMMANDS = (
    "discussion.md",
    "specify.md",
    "clarify.md",
    "deep-research.md",
    "plan.md",
    "tasks.md",
    "analyze.md",
    "fast.md",
    "quick.md",
    "implement.md",
    "debug.md",
    "checklist.md",
    "prd-scan.md",
    "map-build.md",
)


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _compact(text: str) -> str:
    return " ".join(text.split())


def _run_or_emulate_blocks(content: str) -> list[str]:
    blocks: list[str] = []
    for match in re.finditer(r"Run or emulate:\s*```text\n(?P<body>.*?)\n\s*```", content, re.DOTALL):
        blocks.append(match.group("body"))
    return blocks


def test_workflows_use_project_cognition_compass_as_default_intake() -> None:
    workflow_intents = {
        "fast.md": "implement",
        "quick.md": "implement",
        "specify.md": "plan",
        "clarify.md": "plan",
        "deep-research.md": "research",
        "plan.md": "plan",
        "tasks.md": "plan",
        "implement.md": "implement",
        "debug.md": "debug",
        "prd-scan.md": "research",
    }
    readiness_states = ["query_ready", "review", "needs_rebuild", "blocked", "unsupported_runtime"]

    obsolete_primary_input_phrases = [
        "required slices",
        "graph artifacts as primary workflow inputs",
        "graph artifacts as the primary",
        "graph slice artifacts as the primary",
        "status.json`, required slices",
        "status.json`, `slices/change.json`",
        "status.json`, `slices/debug.json`",
        ".specify/project-cognition/status.json`, required slices",
    ]

    for name, intent in workflow_intents.items():
        content = read_template(f"templates/commands/{name}").lower()
        assert "project-cognition compass" in content
        assert f"project-cognition compass --intent {intent}" in content
        assert "minimal_live_reads" in content
        assert "first_pass_paths" in content
        assert "coverage_diagnostics" in content
        assert (
            "lexicon -> semantic_intake -> query" in content
            or "lexicon -> semantic_intake -> project-cognition query" in content
        )
        assert "project-cognition query" in content
        assert "project-cognition query --query-plan" in content
        assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in content
        assert "--query-plan" in content
        assert "query_plan" in content
        assert "semantic_intake" in content
        assert "facet coverage" in content
        assert "concept_decisions" in content
        assert "lexicon_generation_id" in content
        assert "returned map terms" not in content
        assert "raw user intent plus returned map terms" not in content
        for state in readiness_states:
            assert f"`{state}`" in content, f"{name} missing readiness state {state}"
        assert "`ambiguous`" not in content
        assert "`needs_update`" not in content
        assert "read top-level `minimal_live_reads` first" in content
        assert "then use lane-level `first_pass_paths`" in content
        assert ".specify/project-cognition/graph/nodes.json" not in content
        assert ".specify/project-cognition/graph/edges.json" not in content
        assert ".specify/project-cognition/graph/claims.json" not in content
        assert ".specify/project-cognition/graph/conflicts.json" not in content
        assert ".specify/project-cognition/slices/change.json" not in content
        assert ".specify/project-cognition/slices/debug.json" not in content
        for phrase in obsolete_primary_input_phrases:
            assert phrase not in content, f"{name} contains obsolete runtime input phrase: {phrase}"


def test_cognition_launchers_use_double_brace_generated_forms() -> None:
    for name in ("plan.md", "implement.md", "debug.md", "tasks.md"):
        content = read_template(f"templates/commands/{name}")
        raw_content = _read(f"templates/commands/{name}")
        assert not re.search(r"(?<!\{)\{specify-subcmd:project-cognition compass", raw_content)
        assert "{{specify-subcmd:project-cognition compass" in content


def test_default_runnable_cognition_blocks_only_run_compass() -> None:
    workflow_intents = {
        "fast.md": "implement",
        "quick.md": "implement",
        "specify.md": "plan",
        "clarify.md": "plan",
        "deep-research.md": "research",
        "plan.md": "plan",
        "tasks.md": "plan",
        "implement.md": "implement",
        "debug.md": "debug",
        "prd-scan.md": "research",
    }

    for name, intent in workflow_intents.items():
        content = read_template(f"templates/commands/{name}")
        blocks = _run_or_emulate_blocks(content)
        assert blocks, f"{name} missing Run or emulate fenced block"
        expected = f'{{{{specify-subcmd:project-cognition compass --intent {intent} --query="$ARGUMENTS" --format json}}}}'
        assert any(block.strip() == expected for block in blocks), f"{name} default runnable block must only contain compass"
        for block in blocks:
            assert "project-cognition query" not in block, f"{name} has advanced query in default runnable block"
            assert "semantic_intake" not in block, f"{name} has semantic-intake guidance in default runnable block"


def test_specify_default_intake_does_not_use_old_ready_readiness() -> None:
    content = read_template("templates/commands/specify.md").lower()
    assert "when cognition reports `ready`, use the returned task-local bundle" not in content
    assert "when compass reports `query_ready`" in content
    assert "read top-level `minimal_live_reads` first" in content
    assert "then use lane-level `first_pass_paths`" in content


def test_included_workflow_partials_use_query_backed_runtime_inputs() -> None:
    partials = [
        "templates/command-partials/plan/shell.md",
        "templates/command-partials/tasks/shell.md",
        "templates/command-partials/implement/shell.md",
        "templates/command-partials/debug/shell.md",
        "templates/command-partials/quick/shell.md",
        "templates/command-partials/analyze/shell.md",
        "templates/command-partials/common/navigation-check.md",
    ]

    for path in partials:
        content = _read(path).lower()
        assert "project-cognition query" in content or "project cognition query" in content
        assert "task-local" in content
        assert "bundle" in content
        assert "readiness" in content
        assert "minimal_live_reads" in content
        assert "required slices" not in content
        assert "graph artifacts" not in content
        assert "slices/change.json" not in content
        assert "slices/debug.json" not in content


def test_shared_project_cognition_partials_require_semantic_intake_contract() -> None:
    required_terms = [
        "alias catalog",
        "semantic_intake",
        "normalized_query",
        "intent_facets",
        "negative_constraints",
        "alias_interpretations",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "facet coverage",
        "do not trust top similarity alone",
    ]
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _read(path).lower()
        for term in required_terms:
            assert term in content, f"{path} missing shared semantic intake term: {term}"


def test_shared_project_cognition_partials_require_project_language_search_terms() -> None:
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _compact(_read(path).lower())
        assert "project-language search terms" in content, path
        assert "repository_search_terms" in content, path
        assert "derived from the alias catalog" in content, path
        assert "do not search only the raw user words" in content, path
        assert "component names, state names, file names, command names, ui labels, and route names" in content, path
        assert "use these project-language search terms before broad repository search" in content, path


def test_shared_project_cognition_partials_assign_semantic_normalization_to_agent() -> None:
    required_terms = (
        "agent-owned semantic normalization",
        "raw lexicon ranking is only a bootstrap",
        "score=0",
        "mixed-language or cjk text",
        "extract embedded project terms",
    )
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _compact(_read(path).lower())
        for term in required_terms:
            assert term in content, f"{path} missing agent semantic normalization rule: {term}"


def test_shared_cognition_guidance_explains_agent_normalization_diagnostic() -> None:
    required_terms = (
        "agent_normalization",
        "required=true",
        "write_semantic_intake_from_alias_catalog",
        "omitted",
        "required=false",
        "cjk or mixed cjk/ascii",
        "positive raw lexical matches",
        "agent still owns translation",
        "not a route decision",
    )

    for path in SHARED_COGNITION_GUIDANCE_SURFACES:
        content = _compact(_read(path).lower())
        for term in required_terms:
            assert term in content, f"{path} missing agent_normalization diagnostic term: {term}"


def test_shared_project_cognition_partials_include_canonical_query_plan_skeleton() -> None:
    required_skeleton_terms = (
        '"raw_query"',
        '"semantic_intake"',
        '"workflow_intent"',
        '"normalized_query"',
        '"intent_facets"',
        '"negative_constraints"',
        '"alias_interpretations"',
        '"open_semantic_questions"',
        '"selected_concepts"',
        '"rejected_concepts"',
        '"concept_decisions"',
        '"covered_facets"',
        '"missing_facets"',
        '"match_sources"',
        '"lexicon_generation_id"',
        '"expanded_queries"',
        '"repository_search_terms"',
        '"paths"',
    )

    for path in SHARED_COGNITION_PARTIALS:
        content = _read(path)
        compact = _compact(content)
        for term in required_skeleton_terms:
            assert term in content, f"{path} missing canonical query-plan skeleton term {term}"
        assert '"alias": "<user term>"' in compact, path
        assert '"meaning": "<project term>"' in compact, path
        assert '"confidence": "medium"' in compact, path
        assert '"alias_interpretations": ["' not in compact, path


def test_cognition_workflows_preserve_shared_intake_sequence() -> None:
    required_terms = (
        "project-cognition compass",
        "minimal_live_reads",
        "first_pass_paths",
        "coverage_diagnostics",
        "lexicon -> semantic_intake -> query",
        "semantic_intake",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "lexicon_generation_id",
        "project-cognition query",
        "--query-plan",
        "repository_search_terms",
        "agent-owned semantic normalization",
        "raw lexicon ranking is only a bootstrap",
    )

    for name in COGNITION_INTAKE_COMMANDS:
        content = read_template(f"templates/commands/{name}").lower()
        for term in required_terms:
            assert term in content, f"{name} missing shared cognition intake term {term}"


def test_docs_describe_compass_default_and_advanced_query_path() -> None:
    stale_default_query_phrases = (
        "project cognition query bundle as its default intake",
        "query bundle as its default intake",
        "agent-planned task-local project cognition query bundle",
        "task-local project cognition query bundle before broader",
        "default generated-project route to the alias catalog",
        "default route to the alias catalog",
    )

    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        content = _compact(_read(path).lower())
        assert "project-cognition compass" in content, path
        assert 'project-cognition compass --intent <intent> --query "$arguments" --format json' in content, path
        assert "minimal_live_reads" in content, path
        assert "first_pass_paths" in content, path
        assert "project-cognition lexicon --mode catalog" in content, path
        assert "agent-authored `semantic_intake`" in content, path
        assert "concept_decisions" in content, path
        assert "project-cognition query --query-plan" in content, path
        assert "lexicon -> semantic_intake -> query" in content, path
        assert "final edit scope" in content, path
        for phrase in stale_default_query_phrases:
            assert phrase not in content, f"{path} still contains stale default query wording: {phrase}"

    handbook = _compact(_read("PROJECT-HANDBOOK.md").lower())
    assert 'project-cognition compass --intent debug --query "$arguments" --format json' in handbook


def test_cognition_workflows_preserve_direct_agent_normalization_guidance() -> None:
    required_terms = (
        "agent_normalization",
        "write_semantic_intake_from_alias_catalog",
        "omitted",
        "required=false",
        "cjk or mixed cjk/ascii",
        "positive raw lexical matches",
        "agent still owns translation",
    )

    for name in COGNITION_INTAKE_COMMANDS:
        content = read_template(f"templates/commands/{name}").lower()
        for term in required_terms:
            assert term in content, f"{name} missing direct agent_normalization guidance term: {term}"


def test_map_update_preserves_semantic_intake_classification_without_user_intent_query() -> None:
    content = read_template("templates/commands/map-update.md").lower()

    for term in (
        "shared semantic intake contract",
        "semantic_intake",
        "alias catalog",
        "intent_facets",
        "negative_constraints",
        "alias_interpretations",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "repository_search_terms",
        "project-language search terms",
        "do not search only the raw user words",
        "do not trust top similarity alone",
    ):
        assert term in content


def test_shared_readiness_review_guidance_uses_minimal_live_reads() -> None:
    for path in (
        *SHARED_COGNITION_PARTIALS,
        "templates/command-partials/common/senior-consequence-analysis-gate.md",
    ):
        content = _compact(_read(path).lower())
        assert "`review`" in content, path
        assert "review" in content and "minimal_live_reads" in content, path
        assert (
            "inspect the returned `minimal_live_reads` before expanding" in content
            or "inspect the returned `minimal_live_reads` before continuing" in content
            or "perform only the returned `minimal_live_reads` before continuing" in content
        ), path


def test_learning_start_hardening_scope_matches_command_templates() -> None:
    commands_with_learning_start: set[str] = set()
    for path in (PROJECT_ROOT / "templates" / "commands").glob("*.md"):
        content = path.read_text(encoding="utf-8")
        for match in re.finditer(r"learning start --command ([a-z-]+) --format json", content):
            commands_with_learning_start.add(match.group(1))

    assert {"debug", "plan", "implement", "constitution", "map-scan", "map-build"} <= commands_with_learning_start


def test_semantic_intake_contract_is_not_debug_only() -> None:
    brownfield_workflows = {
        "discussion.md",
        "specify.md",
        "clarify.md",
        "deep-research.md",
        "plan.md",
        "tasks.md",
        "analyze.md",
        "fast.md",
        "quick.md",
        "implement.md",
        "debug.md",
        "checklist.md",
        "prd-scan.md",
        "map-update.md",
    }
    missing = []
    for name in brownfield_workflows:
        content = read_template(f"templates/commands/{name}").lower()
        if "semantic_intake" not in content or "facet coverage" not in content:
            missing.append(name)

    assert missing == [], f"semantic intake contract must not be limited to sp-debug; missing: {missing}"


def test_map_scan_template_targets_graph_native_runtime() -> None:
    content = _read("templates/commands/map-scan.md")

    assert ".specify/project-cognition/" in content
    assert "evidence" in content.lower()
    assert "provisional nodes" in content.lower()
    assert "candidate edges" in content.lower()
    assert "must not publish final cognition truth" in content.lower()


def test_map_build_template_targets_graph_reconstruction() -> None:
    content = _read("templates/commands/map-build.md")

    assert ".specify/project-cognition/project-cognition.db" in content
    assert "{{specify-subcmd:project-cognition compass" in content
    assert "{{specify-subcmd:project-cognition query" in content
    assert "--query-plan" in content
    assert "raw graph JSON artifacts or slices as runtime truth" in content
    assert "conflict" in content.lower()
    assert "claim" in content.lower()


def test_map_update_template_exists_and_is_incremental() -> None:
    template_path = PROJECT_ROOT / "templates/commands/map-update.md"
    assert template_path.exists(), "map-update command template must exist for incremental cognition runtime maintenance"
    content = _read("templates/commands/map-update.md")

    assert "map-update" in content
    assert "diff" in content.lower()
    assert "user supplement" in content.lower()
    assert "incremental" in content.lower()
    assert "after recording updates, re-evaluate runtime readiness through the shared freshness contract" in content.lower()
    assert "do not report refresh completion when the runtime remains blocked" in content.lower()
    assert "partial_refresh" in content.lower()
    assert "user-supplied scope is authoritative for the touched area unless repository evidence disproves it" in content.lower()
    assert "prefer the smallest update that can truthfully restore readiness" in content.lower()
    assert "git delta intake" in content.lower()
    assert "update-by-default rule" in content.lower()
    assert "ordinary uncertainty is not an update failure" in content.lower()
    assert "partial/low-confidence update" in content.lower()
    assert "known_unknowns" in content
    assert "minimal_live_reads" in content
    assert "do not read or rewrite raw graph json artifacts; they are not runtime truth" in content.lower()
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "do not split small localized updates into parallel scan-style lanes just because subagents are available" in content.lower()
    assert "escalate to `sp-map-scan`, then `sp-map-build` only when no query-backed baseline exists" in content.lower()
    assert "do not escalate merely because the affected closure is uncertain" in content.lower()
    assert "project-cognition validate-build --format json" in content
    assert "must not call" in content.lower()
    assert "needs_rebuild" in content
    assert "complete-refresh" in content


def test_map_update_template_handles_existing_baseline_gaps_without_rebuild() -> None:
    content = _read("templates/commands/map-update.md").lower()

    assert "existing-baseline ordinary gaps" in content
    assert "partial_refresh" in content
    assert "minimal_live_reads" in content
    assert "baseline_identity_invalid" in content
    assert "explicit_rebuild_requested" in content
    assert "path count" in content
    assert (
        "must not route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` "
        "for ordinary path gaps"
    ) in content
