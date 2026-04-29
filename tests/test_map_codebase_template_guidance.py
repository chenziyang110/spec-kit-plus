from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_map_codebase_template_marks_learning_refresh_and_output_gates_with_agent_marker() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "map-codebase.md").read_text(encoding="utf-8")

    assert "[AGENT] Run `specify learning start --command map-codebase --format json`" in content
    assert "[AGENT] Read `.specify/project-map/index/status.json`" in content
    assert "[AGENT] Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/*.md` files if present." in content
    assert "[AGENT] Before broad scouting begins, assess workload shape" in content
    assert "[AGENT] Read only the live files needed to establish current facts" in content
    assert "[AGENT] Map the comprehensive scout into the canonical outputs instead of inventing a standalone technical-document file:" in content
    assert "[AGENT] Generate or refresh `PROJECT-HANDBOOK.md`." in content
    assert "[AGENT] Ensure `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md` agree on paths, ownership, and workflow names." in content
    assert "[AGENT] After the refresh succeeds, finalize the refresh through the project-map freshness helper using `complete-refresh`" in content
    assert "[AGENT] Before reporting completion, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning" in content
