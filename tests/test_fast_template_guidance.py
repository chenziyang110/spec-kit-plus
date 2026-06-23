from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _assert_tier_roles(content: str) -> None:
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in content
    fast_smoke_index = content.index("fast smoke")
    focused_index = content.index("focused", fast_smoke_index)
    full_index = content.index("full", focused_index)

    fast_smoke_context = content[fast_smoke_index : fast_smoke_index + 180]
    focused_context = content[focused_index : focused_index + 220]
    full_context = content[full_index : full_index + 220]

    assert "early signal" in fast_smoke_context or "first signal" in fast_smoke_context
    assert "acceptance check" in focused_context or "acceptance command" in focused_context
    assert "broader regression" in full_context or "final verification" in full_context


def test_fast_template_exists_and_defines_scope_gate() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "dispatch mode follows command tier" in content
    assert "leader-direct" in content
    assert "mandatory subagent execution" not in content
    assert "## execution mode" in content
    assert "delegated change" not in content
    assert "delegate it through" not in content
    assert "project cognition gate" in content
    assert "project-cognition compass --intent implement" in content
    assert "lexicon -> semantic_intake -> query" in content
    assert "project-cognition query --query-plan" in content
    assert "--query-plan" in content
    assert "query_plan" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "minimal_live_reads" in content
    assert "build-handbook.md" not in content
    assert "debug-handbook.md" not in content
    assert "build-workflow-contract" not in content
    assert "product-and-capability-map" not in content
    assert "change-entrypoints" not in content
    assert "default compass packet" in content
    assert "returned `minimal_live_reads`" in content
    assert "map-update" in content
    assert ".specify/project-map/index/status.json" not in content
    assert "shared surfaces" in content
    assert "change-propagation hotspot" in content
    assert "verification entry points" in content
    assert "known unknowns" in content
    assert "tiny harness, command, fixture, or helper repair" not in content
    assert "## workflow contract summary" in content
    assert "leader performs the change directly" in content
    assert "no subagent dispatch" in content
    assert "no task contract" in content
    assert "allowed write scope local and explicit" in content
    assert "scope gate" in content
    assert "≤3 files touched" in content or "3 files touched" in content
    assert "verify" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "changed_code_paths" in content
    assert "changed_behavior_surfaces" in content
    assert "verification_evidence" in content
    assert "project_cognition_refresh" in content
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "project-cognition closeout-plan --workflow" in content
    assert "update_mode=delta_session" in content
    assert "update_mode=payload_file" in content
    assert "update_argv" in content
    assert "delta_append_draft.argv_prefix" in content
    assert "unknown_path_dispositions" in content
    assert "clean closeout keys on `result_state`" in content
    assert "not `status=ok`, `update_id`, `last_update_id`, or freshness alone" in content
    assert "legacy recorded-only output" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "dirty only when inline update" in content
    assert "ordinary uncertain closure" in content
    assert "partial/low-confidence facts, known unknowns, and `minimal_live_reads`" in content
    assert "actual `{{invoke:map-update}}` refresh" not in content
    assert "if the fast-path change unexpectedly touched" not in content
    assert "use map-update for ordinary existing-baseline gaps" in content
    assert "use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid" in content
    assert "complete-refresh" in content
    assert "incremental freshness finalization" in content
    assert "do not run `complete-refresh` as a rebuild finalizer" in content
    assert "{{specify-subcmd:project-cognition mark-dirty --reason \"workflow-closeout-failed\" --format json}}" in content
    assert "skip all learning hooks" in content
    assert "skip all learning hooks" in content
    assert "default compass packet" in content
    assert "returned `minimal_live_reads`" in content
    assert "fast-task state or report" in content
    assert "verification route" in content
    assert "project-language search terms" in content
    assert "repository_search_terms" in content
    assert "do not search only the raw user words" in content
    assert "component names, state names, file names, command names, ui labels, and route names" in content
    assert "use these project-language search terms before broad repository search" in content


def test_fast_template_uses_leader_direct_contract() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "no spec.md" in content or "do not create spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "no subagent dispatch" in content
    assert "no task contract" in content
    assert "dispatch one subagent" not in content
    assert "prepare the smallest task contract" not in content
    assert "delegated change" not in content
    assert "delegate it through" not in content


def test_fast_template_defines_explicit_upgrade_triggers() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "upgrade to `/sp-quick` immediately if" in content
    assert "more than 3 files" in content
    assert "shared surface" in content
    assert "change-propagation hotspot" in content
    assert "known unknowns" in content
    assert "safe direct execution unavailable" in content
    assert "safe packetized delegation unavailable" not in content
    assert "needs research" in content or "research or clarification" in content
    assert "upgrade to `/sp-specify` immediately if" in content
    assert "new workflow" in content
    assert "compatibility" in content
    assert "acceptance criteria" in content


def test_fast_template_routes_consequence_triggers_out_of_fast_path() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "senior consequence analysis gate" in content
    assert "upgrade to `/sp-quick` immediately if the gate triggers" in content
    assert "upgrade to `/sp-specify` immediately if" in content
    assert "lifecycle" in content
    assert "running-state" in content
    assert "shared-state" in content
    assert "destructive-operation" in content
    assert "consumer impact" in content
    assert "stand-down reason" in content
    assert "do not add planning artifacts to satisfy this gate on the fast path" in content


def test_fast_template_marks_learning_and_fail_closed_routing_gates_with_agent_marker() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "skip all learning hooks" in content
    assert "do not run learning start, signal, review, or capture" in content
    assert "learning capture --command fast" not in content
    assert "skip all learning hooks" in content


def test_fast_template_requires_tdd_gate_for_behavior_changes() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "behavior-changing" in content or "behavior changing" in content
    assert "write a failing targeted test or failing repro check before editing production code" in content
    assert "do not use manual sanity checks as a substitute for red" in content
    assert "docs-only" in content or "docs only" in content
    assert "if no reliable automated test surface exists" in content
    assert "/sp-quick" in content
    assert "/sp-test-scan" not in content
    assert "use the fast smoke tier as the default fast-path verification" not in content
    assert "if playbook command tiers exist" in content
    assert "otherwise run the smallest meaningful local verification" in content


def test_fast_template_routes_unknown_root_cause_bugfixes_to_debug() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "bug fix" in content or "bugfix" in content
    assert "/sp-debug" in content
    assert "root cause is still unknown" in content or "root cause is not yet known" in content
    assert "symptom patch" in content
