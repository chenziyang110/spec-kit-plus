from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_map_codebase_template_marks_learning_refresh_and_output_gates_with_agent_marker() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "map-codebase.md").read_text(encoding="utf-8")

    assert "[AGENT] Run `specify learning start --command map-codebase --format json`" in content
    assert "[AGENT] Read `.specify/project-map/index/status.json`" in content
    assert "[AGENT] Read `.specify/project-map/index/atlas-index.json`, `.specify/project-map/index/modules.json`, and `.specify/project-map/index/relations.json` if present." in content
    assert "[AGENT] Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/root/*.md` files if present." in content
    assert "[AGENT] Before broad scouting begins, assess workload shape" in content
    assert "[AGENT] If the selected strategy is `native-multi-agent`, dispatch bounded explorer subagents" in content
    assert "[AGENT] Do not continue with broad sequential exploration after selecting `native-multi-agent`" in content
    assert "launch at least three independent explorer subagents" in content
    assert "Explorer subagents are read-only evidence collectors." in content
    assert "The leader must wait for every dispatched explorer lane" in content
    assert "[AGENT] Read only the live files needed to establish current facts" in content
    assert "[AGENT] Map the comprehensive scout into the canonical outputs instead of inventing a standalone technical-document file:" in content
    assert "[AGENT] Generate or refresh `PROJECT-HANDBOOK.md`." in content
    assert "[AGENT] Ensure `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, and `.specify/project-map/modules/*/*.md` agree on paths, ownership, module IDs, and workflow names." in content
    assert "[AGENT] After the refresh succeeds, finalize the refresh through the project-map freshness helper using `complete-refresh`" in content
    assert "[AGENT] Before reporting completion, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning" in content
    assert ".specify/project-map/index/atlas-index.json" in content
    assert ".specify/project-map/modules/<module-id>/OVERVIEW.md" in content
    assert "deep_stale" in content
