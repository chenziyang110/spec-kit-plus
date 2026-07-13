from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_root_agents_documents_current_managed_context_and_schema_v5_rules() -> None:
    content = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "specify --help" in content
    assert "generated create-feature script" in lowered
    assert "default feature workspace names use `yyyy-mm-dd-<slug>`" in lowered
    assert "frontstage-only deferred persistence" in lowered
    assert "do not write discussion files, counters, dirty markers, receipts, or status summaries for every user reply" in lowered
    assert "suggest `checkpoint, continue`" in lowered
    assert "prompt does not write files by itself" in lowered
    assert ".specify/scripts/bash/create-new-feature.sh" in lowered
    assert ".specify/scripts/powershell/create-new-feature.ps1" in lowered
    assert "do not invent" in lowered
    assert "specify create-feature" in lowered
    assert "## Always-On Context" in content
    assert "project cognition and project memory are always available" in lowered
    assert ".specify/memory/learnings/INDEX.md" in content
    assert ".specify/memory/project-learnings.md` remains a compatibility summary" in content
    assert "## Workflow Activation Discipline" not in content
    assert "## Lane Recovery Rules" not in content
    assert "### Project Cognition Schema v5 Maintenance" in content
    assert "schema v5 runtime readiness is graph, alias, and revision-bound typed graph-claim reconciliation first" in lowered
    assert "`alias_index` is the route vocabulary" in lowered
    assert "v1 through v4 and old broad-schema dbs are diagnostic/inspect-only" in lowered
    assert "does not migrate schema v4" in lowered
    assert "agents supply semantic reconciliation intent only" in lowered
    assert "runtime owns contract versions" in lowered
    assert "`apply_argv`" in content
    assert "does not archive or replace" in lowered
    assert "do not reintroduce old broad-schema tables" in lowered
    assert "verified_in_graph_generation" in content
    assert "never authorize source changes or set workflow `claim_ready=true`" in content
    assert "claims" in content
    assert "conflicts" in content
    assert "slice_members" in content


def test_root_claude_context_documents_lane_first_recovery_rules() -> None:
    content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "AGENTS.md" in content
    assert "specify --help" in content
    assert "generated create-feature script" in lowered
    assert ".specify/scripts/bash/create-new-feature.sh" in lowered
    assert ".specify/scripts/powershell/create-new-feature.ps1" in lowered
    assert "do not invent" in lowered
    assert "specify create-feature" in lowered
    assert "## Lane Recovery Rules" in content
    assert "lane-first, not branch-first" in lowered
    assert "explicit `feature_dir`" in content
    assert "/sp.plan" in content
    assert ".specify/features/<feature>/" in content
    assert "capability deep workflow" in lowered
    assert "symptom -> capability deep workflow -> module workflows -> root workflows" in content
