from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_map_build_runtime_outputs_are_project_cognition_database_artifacts() -> None:
    content = _read("templates/commands/map-build.md")

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "queryable task-local bundle generation" in content
    assert "raw graph JSON artifacts or slices as runtime truth" in content
    assert "build or refresh `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`" not in content
    assert "runtime handbook output contract" not in content.lower()


def test_runtime_docs_explain_alias_index_and_v1_rebuild_contract() -> None:
    handbook = _read("PROJECT-HANDBOOK.md").lower()
    readme = _read("README.md").lower()
    for content in (handbook, readme):
        assert "alias_index" in content
        assert "schema v2" in content
        assert "v1" in content
        assert "rebuild" in content
        assert "alias_index" in content
        assert "alias catalog" in content


def test_runtime_docs_describe_debug_understanding_checkpoint() -> None:
    for rel_path in ("README.md", "PROJECT-HANDBOOK.md"):
        content = _read(rel_path).lower()

        assert "debug understanding checkpoint" in content
        assert "before substantive investigation" in content
        assert "expected behavior" in content
        assert "investigation scope" in content
        assert "progress signal" in content


def test_context_loading_gradient_uses_cognition_runtime_gate() -> None:
    content = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered = content.lower()

    assert "default project cognition intake is `project-cognition compass" in lowered
    assert "project-cognition lexicon" in lowered
    assert "alias catalog" in lowered
    assert "semantic_intake" in lowered
    assert "facet coverage" in lowered
    assert "concept_candidates" in content
    assert "selected_concepts" in content
    assert "rejected_concepts" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "selection_reason" in content
    assert "query_plan" in content
    assert "expanded_queries" in content
    assert "paths" in content
    assert "route_pack" in content
    assert "colloquial_matches" in content
    assert "disambiguation" in lowered
    assert "task-local project" in lowered
    assert "raw" in lowered
    assert "graph json artifacts as obsolete runtime surfaces" in lowered
    assert "runtime handbook gate" not in lowered
    assert "workflow handbooks as the mandatory pre-source knowledge base" not in lowered
    assert "PROJECT-HANDBOOK.md" not in content
    assert "atlas.entry" not in content
    assert "root topic document" not in lowered
    assert "module overview document" not in lowered
    assert "a project-cognition compass intake is not complete when it returns json" in lowered
    assert "readiness drives routing" in lowered
    assert "minimal_live_reads constrains inspection" in lowered
    assert "carry forward the selected concepts" in lowered
    assert "rejected concepts" in lowered
    assert "next workflow artifact or execution state" in lowered
    assert "returned map " + "terms" not in lowered


def test_project_cognition_passive_skill_mirrors_query_completion_contract() -> None:
    content = " ".join(
        _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md")
        .lower()
        .split()
    )

    assert "a project-cognition compass intake is not complete when it returns json" in content
    assert "concept_candidates" in content
    assert "selected_concepts" in content
    assert "rejected_concepts" in content
    assert "readiness is interpreted as advisory navigation" in content
    assert "live evidence proves technical claims" in content
    assert "route_pack" in content
    assert "minimal_live_reads" in content
    assert "next workflow artifact or execution state" in content
    assert "affected nodes" in content
    assert "subgraph" in content
    assert "missing coverage" in content
    assert "verification routes" in content
    assert "weak coverage" in content
    assert "when inspecting or comparing another local directory" in content
    assert "check whether that directory or its children contain `.specify/` first" in content
    assert "project-cognition discover --root" in content
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "reference_readiness" in content
    assert "freshness is `fresh`" in content
    assert "`graph_ready` is true" in content
    assert "do not treat legacy `.specify/project-map/**` outputs" in content
    assert "fall back to minimal live reads" in content


def test_upstream_workflow_templates_are_query_backed_cognition_first() -> None:
    for rel_path in (
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ):
        content = _read(rel_path)
        lowered = content.lower()

        assert "project-cognition compass --intent plan" in content
        assert "lexicon -> semantic_intake -> query" in content
        assert "project-cognition query --query-plan" in content
        assert "--query-plan" in content
        assert "minimal_live_reads" in content
        assert "graph-native" not in lowered
        assert "build-handbook.md" not in lowered
        assert "build-workflow-contract" not in lowered
        assert "runtime handbook" not in lowered


def test_workflow_templates_carry_project_cognition_facts_forward() -> None:
    expectations = {
        "templates/commands/specify.md": ("context.md", "ownership", "verification routes"),
        "templates/commands/clarify.md": ("clarified spec package", "ownership", "verification"),
        "templates/commands/deep-research.md": ("deep-research.md", "repository facts", "external research"),
        "templates/commands/plan.md": ("Implementation Constitution", "verification strategy", "plan-contract.json"),
        "templates/commands/tasks.md": ("tasks.md", "task-index.json", "task packets"),
        "templates/commands/analyze.md": ("cognition-backed blocker evidence", "clarify", "deep-research"),
        "templates/commands/implement.md": ("implement-tracker.md", "WorkerTaskPacket", "minimal live reads"),
        "templates/commands/debug.md": ("debug session state", "competing truths", "coverage gaps"),
        "templates/commands/fast.md": ("fast-task state or report", "verification route", "minimal reads"),
        "templates/commands/quick.md": ("STATUS.md", "validation route", "known risk"),
    }

    for rel_path, phrases in expectations.items():
        content = _read(rel_path).lower()
        assert "project-cognition compass" in content, rel_path
        for phrase in phrases:
            assert phrase.lower() in content, f"{rel_path} missing {phrase!r}"


def test_runtime_handbook_docs_are_query_backed() -> None:
    content = _read("PROJECT-HANDBOOK.md")
    lowered = content.lower()

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "task-local `project-cognition compass` packet" in lowered
    assert "advanced agent-planned `project-cognition lexicon --mode catalog`" in lowered
    assert "project-cognition lexicon" in lowered
    assert "alias catalog" in lowered
    assert "semantic_intake" in lowered
    assert "facet coverage" in lowered
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "candidate_universe_version" in content
    assert "active_generation_id" in content
    assert "returned map " + "terms" not in lowered
    assert "project-cognition query --query-plan" in lowered
    assert "advisory navigation" in lowered
    assert "live repository evidence" in lowered or "live evidence" in lowered
    assert "workflow-owned mutation closeout is not external map maintenance" in lowered
    assert "run inline project cognition update" in lowered or "runs inline project cognition update" in lowered
    assert "project-cognition update --payload-file" in lowered
    assert "result_state" in lowered
    assert "verification_evidence" in lowered
    assert "generated_surface_notes" in lowered
    assert "failed verification evidence" in lowered
    assert (
        "sp-map-update remains the external/manual" in lowered
        or "`sp-map-update` remains the external/manual" in lowered
        or "sp-map-update is for manual/external maintenance" in lowered
    )
    assert "uncertain closure is recorded by inline update or `map-update` as partial/low-confidence facts" in lowered
    assert "workflow-appropriate slices" not in lowered


def test_runtime_docs_explain_graph_backed_project_cognition_lexicon() -> None:
    required_phrases = (
        "alias catalog",
        "semantic_intake",
        "facet coverage",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "concept_decisions",
        "lexicon_generation_id",
        "candidate_universe_version",
        "active_generation_id",
        "project-cognition lexicon",
        "project-cognition compass",
        "project-cognition query --query-plan",
    )

    for rel_path in ("README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"):
        content = _read(rel_path)
        lowered = content.lower()

        for phrase in required_phrases:
            assert phrase in content, f"{rel_path} missing {phrase!r}"
        assert "returned map " + "terms" not in lowered
        assert "raw user intent into a `query_plan`" not in lowered
        assert "raw user intent into a " + "query_plan" not in lowered
        assert "using returned map " + "terms" not in lowered
        assert "generate a query_plan from " + "returned" not in lowered


def test_runtime_docs_explain_project_cognition_ignore_rules() -> None:
    for rel_path in ("README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"):
        content = _read(rel_path)
        lowered = content.lower()

        assert ".cognitionignore" in content
        assert "gitignore-compatible" in lowered
        assert "map-scan" in lowered
        assert "map-build" in lowered
        assert "map-update" in lowered
        assert "excluded paths must not enter project cognition graph evidence" in lowered
        assert "generate-ignore" in content
        assert ".specify/project-cognition/.cognitionignore" in content
        assert "review" in lowered


def test_runtime_docs_explain_cross_project_reference_cognition_gate() -> None:
    for rel_path in ("README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"):
        content = _read(rel_path)
        lowered = " ".join(content.lower().split())

        assert "project-cognition discover --root" in lowered
        assert ".specify/project-cognition/status.json" in content
        assert ".specify/project-cognition/project-cognition.db" in content
        assert "reference_readiness" in content
        assert "freshness is `fresh`" in lowered
        assert "`graph_ready` is true" in lowered
        assert "do not treat legacy `.specify/project-map/**` outputs as current truth" in lowered


def test_docs_explain_project_cognition_supports_but_does_not_replace_consequence_analysis() -> None:
    for rel_path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    ):
        content = _read(rel_path).lower()

        assert "senior consequence analysis gate" in content
        assert "project cognition" in content
        assert "necessary but not sufficient" in content
        assert "affected object map" in content
        assert "state-behavior matrix" in content
        assert "dependency impact" in content
        assert "coverage gaps" in content
