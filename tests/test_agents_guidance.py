from pathlib import Path

from .agent_guidance_utils import (
    GUIDANCE_ROOT,
    agent_guidance_reference_paths,
    read_agents_with_references,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_root_agents_routes_all_guidance_references() -> None:
    content = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    references = agent_guidance_reference_paths()
    unmanaged = content.split("<!-- SPEC-KIT:BEGIN -->", 1)[0]

    assert content.startswith("# AGENTS.md\n")
    assert references
    assert set(references) == {
        path.resolve() for path in GUIDANCE_ROOT.rglob("*.md")
    }
    for path in references:
        target = path.relative_to(PROJECT_ROOT.resolve()).as_posix()
        routes = [
            line.strip().strip("|").split("|")
            for line in unmanaged.splitlines()
            if line.lstrip().startswith("|") and f"]({target})" in line
        ]
        assert routes, f"Missing entrypoint read trigger for {target}"
        assert any(
            any(cell.strip() and target not in cell for cell in row)
            for row in routes
        ), f"Empty entrypoint read trigger for {target}"


def test_root_agents_documents_current_managed_context() -> None:
    content = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "specify --help" in content
    assert "generated create-feature script" in lowered
    assert "default feature workspace names use `yyyy-mm-dd-<slug>`" in lowered
    assert "frontstage-only deferred persistence" in lowered
    assert (
        "do not write discussion files, counters, dirty markers, receipts, or status summaries for every user reply"
        in lowered
    )
    assert "active discussion turns" in lowered
    assert "suppress the reminder" in lowered
    assert "end every discussion reply" not in lowered
    assert "prompt does not write files by itself" in lowered
    assert ".specify/scripts/bash/create-new-feature.sh" in lowered
    assert ".specify/scripts/powershell/create-new-feature.ps1" in lowered
    assert "do not invent" in lowered
    assert "specify create-feature" in lowered
    assert "## Always-On Context" in content
    assert "project cognition and project learning are always available" in lowered
    assert "specify-runtime learning start -> list -> show" in content
    assert "not by parsing storage files" in lowered
    assert "never auto-promote during workflow start" in lowered
    assert "## Workflow Activation Discipline" not in content
    assert "## Lane Recovery Rules" not in content


def test_linked_agents_guidance_preserves_schema_v5_rules() -> None:
    content = read_agents_with_references()
    lowered = content.lower()

    assert "### Project Cognition Schema v5 Maintenance" in content
    assert (
        "schema v5 runtime readiness is graph, alias, and revision-bound typed graph-claim reconciliation first"
        in lowered
    )
    assert "`alias_index` is the route vocabulary" in lowered
    assert (
        "v1 through v4 and old broad-schema dbs are diagnostic/inspect-only" in lowered
    )
    assert "does not migrate schema v4" in lowered
    assert "agents supply semantic reconciliation intent only" in lowered
    assert "runtime owns contract versions" in lowered
    assert "`apply_argv`" in content
    assert "never move, remove, archive, or replace" in lowered
    assert "do not reintroduce old broad-schema tables" in lowered
    assert "verified_in_graph_generation" in content
    assert (
        "never authorize source changes or set workflow `claim_ready=true`" in content
    )
    assert "claims" in content
    assert "conflicts" in content
    assert "slice_members" in content


def test_root_claude_context_documents_managed_run_recovery_rules() -> None:
    content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "AGENTS.md" in content
    assert "specify --help" in content
    assert "generated create-feature script" in lowered
    assert ".specify/scripts/bash/create-new-feature.sh" in lowered
    assert ".specify/scripts/powershell/create-new-feature.ps1" in lowered
    assert "do not invent" in lowered
    assert "specify create-feature" in lowered
    assert "## Run Recovery Rules" in content
    assert "specify_run_managed" in lowered
    assert "specify_run_workspace" in lowered
    assert "private git ref" in lowered
    assert "quarantines its workspace generation" in lowered
    assert "immutable candidate" in lowered
    assert "explicit `feature_dir`" in content
    assert "/sp.plan" in content
    assert ".specify/features/<feature>/" in content
    assert "capability deep workflow" in lowered
    assert (
        "symptom -> capability deep workflow -> module workflows -> root workflows"
        in content
    )
