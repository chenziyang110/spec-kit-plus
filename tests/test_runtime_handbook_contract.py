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


def test_context_loading_gradient_uses_cognition_runtime_gate() -> None:
    content = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered = content.lower()

    assert "launcher-backed project cognition query planning flow" in lowered
    assert "project-cognition lexicon" in lowered
    assert "query_plan" in content
    assert "task-local project" in lowered
    assert "raw" in lowered
    assert "graph json artifacts as obsolete runtime surfaces" in lowered
    assert "runtime handbook gate" not in lowered
    assert "workflow handbooks as the mandatory pre-source knowledge base" not in lowered
    assert "PROJECT-HANDBOOK.md" not in content
    assert "atlas.entry" not in content
    assert "root topic document" not in lowered
    assert "module overview document" not in lowered


def test_upstream_workflow_templates_are_query_backed_cognition_first() -> None:
    for rel_path in (
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ):
        content = _read(rel_path)
        lowered = content.lower()

        assert "project-cognition lexicon --intent plan" in content
        assert "project-cognition query --intent plan" in content
        assert "--query-plan" in content
        assert "minimal_live_reads" in content
        assert "graph-native" not in lowered
        assert "build-handbook.md" not in lowered
        assert "build-workflow-contract" not in lowered
        assert "runtime handbook" not in lowered


def test_runtime_handbook_docs_are_query_backed() -> None:
    content = _read("PROJECT-HANDBOOK.md")
    lowered = content.lower()

    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "task-local project cognition query bundle" in lowered
    assert "agent-planned `project-cognition query`" in lowered
    assert "project-cognition lexicon" in lowered
    assert "query_plan" in content
    assert "workflow-appropriate slices" not in lowered


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
