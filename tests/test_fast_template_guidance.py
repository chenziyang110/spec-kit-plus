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
    assert "project-cognition lexicon --intent implement" in content
    assert "project-cognition query --intent implement" in content
    assert "--query-plan" in content
    assert "query_plan" in content
    assert "minimal_live_reads" in content
    assert "build-handbook.md" not in content
    assert "debug-handbook.md" not in content
    assert "build-workflow-contract" not in content
    assert "product-and-capability-map" not in content
    assert "change-entrypoints" not in content
    assert "returned task-local bundle" in content
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
    assert "completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs" in content
    assert "changed_code_paths" in content
    assert "changed_behavior_surfaces" in content
    assert "verification_evidence" in content
    assert "project_cognition_refresh" in content
    assert "recommend `{{invoke:map-update}}` as follow-up map maintenance" in content
    assert "do not call `project-cognition mark-dirty`" in content
    assert "`needs_rebuild`: treat map output as advisory" in content
    assert "when the user wants map repair" in content
    assert "completion requirement for this ordinary workflow" in content
    assert "manual override/fallback" not in content
    assert "skip all learning hooks" in content
    assert "skip all learning hooks" in content
    assert "returned task-local bundle" in content
    assert "fast-task state or report" in content
    assert "verification route" in content


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
