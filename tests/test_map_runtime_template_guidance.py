from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_workflows_use_project_cognition_query_instead_of_raw_graph_reads() -> None:
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
    readiness_states = ["ready", "review", "ambiguous", "needs_update", "needs_rebuild", "blocked"]

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
        assert "project-cognition lexicon" in content
        assert f"project-cognition lexicon --intent {intent}" in content
        assert "project-cognition query" in content
        assert f"project-cognition query --intent {intent}" in content
        assert "--query-plan" in content
        assert "query_plan" in content
        for state in readiness_states:
            assert f"`{state}`" in content, f"{name} missing readiness state {state}"
        assert ".specify/project-cognition/graph/nodes.json" not in content
        assert ".specify/project-cognition/graph/edges.json" not in content
        assert ".specify/project-cognition/graph/claims.json" not in content
        assert ".specify/project-cognition/graph/conflicts.json" not in content
        assert ".specify/project-cognition/slices/change.json" not in content
        assert ".specify/project-cognition/slices/debug.json" not in content
        for phrase in obsolete_primary_input_phrases:
            assert phrase not in content, f"{name} contains obsolete runtime input phrase: {phrase}"


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
    assert "{{specify-subcmd:project-cognition lexicon" in content
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
