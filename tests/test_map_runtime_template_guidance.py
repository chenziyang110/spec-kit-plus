from pathlib import Path


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
        "test-scan.md": "test",
        "test-build.md": "test",
        "prd-scan.md": "research",
    }
    readiness_states = ["ready", "review", "ambiguous", "needs_update", "needs_rebuild", "blocked"]

    for name, intent in workflow_intents.items():
        content = (PROJECT_ROOT / "templates" / "commands" / name).read_text(encoding="utf-8").lower()
        assert "project-cognition query" in content
        assert f"project-cognition query --intent {intent}" in content
        for state in readiness_states:
            assert f"`{state}`" in content, f"{name} missing readiness state {state}"
        assert ".specify/project-cognition/graph/nodes.json" not in content
        assert ".specify/project-cognition/graph/edges.json" not in content
        assert ".specify/project-cognition/graph/claims.json" not in content
        assert ".specify/project-cognition/graph/conflicts.json" not in content


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
    assert "specify project-cognition query" in content
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
    assert "do not read or rewrite raw graph json artifacts; they are not runtime truth" in content.lower()
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "do not split small localized updates into parallel scan-style lanes just because subagents are available" in content.lower()
    assert "escalate to `sp-map-scan`, then `sp-map-build` only when the current baseline is unusable or the affected closure cannot be bounded safely" in content.lower()
