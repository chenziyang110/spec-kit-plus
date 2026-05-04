from pathlib import Path

from .template_utils import read_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_template_exists_and_defines_lightweight_tracked_flow() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "dispatch mode follows command tier" in content
    assert "subagent-preferred" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "## leader role" in content
    assert "you are the quick-task leader" in content
    assert "you are not the default implementer for the quick task" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "passive project learning layer" in content
    assert "passive project learning layer" in content
    assert "project-map hard gate" in content
    assert "must pass an atlas gate before" in content
    assert "project-handbook.md" in content
    assert "atlas.entry" in content
    assert "atlas.index.status" in content
    assert "atlas.index.atlas" in content
    assert "treat `missing` and `stale` as blocking" in content
    assert "`possibly_stale`" in content
    assert "must_refresh_topics" in content
    assert "review_topics" in content
    assert "at least one relevant root topic document" in content
    assert "at least one relevant module overview document" in content
    assert "root topic" in content
    assert "module overview" in content
    assert ".specify/testing/unit_test_system_request.md" in content or ".specify/testing/unit-test-system-request.md" in content
    assert "risk tranche" in content or "coverage wave" in content
    assert "shared-surface" in content or "cross-module" in content
    assert "lane shape" in content or "execution strategy" in content
    assert "ad-hoc task" in content or "small, ad-hoc task" in content
    assert "lightweight" in content
    assert ".planning/quick/" in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "skip the full" in content and "specify" in content
    assert "summary.md" in content or "summary artifact" in content
    assert "repository analysis" in content
    assert "read `.specify/memory/constitution.md` first" in content
    assert "summary artifact" in content or "final summary artifact" in content


def test_quick_template_preserves_quality_guardrails() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "scope gate" in content
    assert "small but non-trivial" in content or "not for trivial work" in content
    assert "{{invoke:fast}}" in content or "/sp-fast" in content
    assert "{{invoke:specify}}" in content or "/sp-specify" in content
    assert "validate" in content
    assert "verify" in content
    assert "completion standard" in content
    assert "small, transparent closed loop" in content
    assert "at least one meaningful verification step" in content or "at least one smallest meaningful executable verification step has run" in content
    assert "unverified surface" in content or "not checked" in content


def test_quick_template_defines_capability_aware_execution_strategy() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "choose_subagent_dispatch" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "one-subagent" in content
    assert "parallel-subagents" in content
    assert "native-subagents" in content
    assert "leader" in content
    assert "join point" in content
    assert "task contract" in content
    assert "the first actionable execution step after scope lock is to dispatch the first subagent" in content
    assert "if two or more independent subagent lanes can safely run in parallel" in content


def test_quick_template_defines_recoverable_quick_task_artifacts() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert ".planning/quick/<id>-<slug>/" in content
    assert ".planning/quick/index.json" in content
    assert "status.md" in content
    assert "first hard gate" in content
    assert "constitution read is the first hard gate" in content
    assert "summary.md" in content
    assert "current focus" in content
    assert "next action" in content
    assert "resume" in content
    assert "resolved/" in content


def test_quick_template_includes_concrete_status_template() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "## status.md template" in content
    assert "id: [quick-task id]" in content
    assert "slug: [quick-task slug]" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "## current focus" in content
    assert "## execution intent" in content
    assert "intent_outcome:" in content
    assert "intent_constraints:" in content
    assert "success_evidence:" in content
    assert "## execution" in content
    assert "blocked_dispatch:" in content
    assert "## validation" in content
    assert "## summary pointer" in content


def test_quick_template_defines_explicit_specify_escalation_triggers() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "upgrade to `{{invoke:specify}}` immediately if" in content or "upgrade to `/sp-specify` immediately if" in content
    assert "unit test system program" in content or "testing-system program" in content
    assert "architecture" in content
    assert "cross-cutting" in content
    assert "change-propagation hotspot" in content
    assert "truth-owning shared surface" in content
    assert "known unknowns" in content
    assert "multiple independent capabilities" in content
    assert "new durable spec" in content or "long-lived feature spec" in content
    assert "rollout" in content or "migration" in content
    assert "acceptance criteria" in content


def test_quick_template_reads_constitution_and_drives_to_terminal_state() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert ".specify/memory/constitution.md" in content
    assert "constitution first" in content
    assert "before `status.md` initialization or touched-area analysis proceeds" in content
    assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in content
    assert "dispatch that subagent path before doing any further local repository deep dive" in content
    assert "resolved" in content
    assert "blocked" in content


def test_quick_template_requires_self_recovery_before_blocking() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "attempt the smallest safe recovery step before declaring the task blocked" in content
    assert "read additional local context" in content
    assert "run the smallest meaningful verification or repro command" in content
    assert "use `--research`-style focused investigation" in content or "focused investigation" in content
    assert "retry_attempts" in content
    assert "recovery_action" in content
    assert "blocker_reason" in content


def test_quick_template_requires_minimal_plan_for_propagating_changes() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "surface sweep rule" in content
    assert "small-scope complete sweep" in content
    assert "affected surfaces" in content
    assert "propagation hotspots, consumer surfaces, verification entry points, and known unknowns" in content
    assert "confirmed correct" in content
    assert "fixed in this quick task" in content
    assert "not checked in this pass (with reason)" in content
    assert "propagating change" in content
    assert "must write a minimal plan before editing" in content
    assert "implementation" in content
    assert "export or declaration layer" in content
    assert "examples" in content
    assert "tests" in content
    assert "docs" in content
    assert "callsites" in content or "call sites" in content
    assert "all affected surfaces" in content
    assert "not just the files already inspected" in content


def test_quick_template_rejects_sampling_for_propagating_change_completion() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "sampling is not sufficient" in content
    assert "full-coverage check" in content or "full coverage check" in content
    assert "every affected callsite" in content or "every affected call site" in content
    assert "do not claim completion" in content


def test_quick_template_requires_summary_transparency_for_verified_and_unverified_surfaces() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "summary artifact" in content
    assert "which surfaces were left unverified" in content
    assert "separate `verified` coverage from `not checked` coverage" in content
    assert "for each declared surface, give the terminal status conclusion" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "git-baseline freshness in `.specify/project-map/index/status.json` as the truth source" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before marking the quick task `resolved`" in content
    assert "complete-refresh" in content
    assert "successful-refresh finalizer" in content
    assert "if a full refresh can be completed now" in content
    assert "otherwise use" in content
    assert "manual override/fallback" in content


def test_quick_template_requires_constitution_before_status_and_subagent_dispatch() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "constitution first" in content
    assert "before workspace setup, clarification, lane selection, subagent dispatch, or local analysis" in content


def test_quick_template_prefers_parallel_subagent_fanout_when_safe() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "materially improve throughput" in content
    assert "dispatch them in parallel" in content
    assert "instead of artificially serializing the work" in content


def test_quick_template_defines_empty_call_recovery_and_lifecycle_management() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
    assert "unfinished quick-task states" in content or "unfinished quick tasks" in content
    assert "close" in content
    assert "archive" in content


def test_quick_template_marks_learning_and_fail_closed_coverage_gates_with_agent_marker() -> None:
    content = read_template("templates/commands/quick.md")

    assert "**freshness**: treat `missing` and `stale` as blocking" in content.lower()
    assert "[AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`." in content or "must_refresh_topics" in content
    assert "ownership, placement, workflow, integration, or verification guidance" in content
    assert "status.md" in content.lower()
    assert "[AGENT] Use the shared policy function before execution begins and again at each join point" in content
    assert "review-learning" in content.lower() or "capture-learning" in content.lower()


def test_quick_template_requires_tdd_gate_for_behavior_changes() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "behavior-changing" in content or "behavior changing" in content
    assert "bugfix" in content or "bug fix" in content
    assert "refactor" in content
    assert "first executable lane must produce a failing automated test or failing repro check before production edits begin" in content
    assert "do not write production code until the red state is captured" in content
    assert "if no reliable automated test surface exists for the touched behavior" in content
    assert "bootstrap the smallest viable test surface first" in content
    assert "{{invoke:test-scan}}" in content or "/sp-test-scan" in content or "/sp-test" in content


def test_quick_template_routes_uncertain_bugfixes_into_debug() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "root cause is still unknown" in content or "root cause is not yet known" in content
    assert "{{invoke:debug}}" in content or "/sp-debug" in content
    assert "surface-only" in content or "symptom-only" in content
    assert "cannot satisfy the quick-task contract" in content or "cannot satisfy the quick contract" in content
