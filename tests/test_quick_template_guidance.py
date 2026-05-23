from pathlib import Path

from .template_utils import read_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _assert_tier_roles(content: str) -> None:
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in content
    fast_smoke_index = content.index("fast smoke")
    focused_index = content.index("focused", fast_smoke_index)
    full_index = content.index("full", focused_index)

    fast_smoke_context = content[fast_smoke_index : fast_smoke_index + 200]
    focused_context = content[focused_index : focused_index + 220]
    full_context = content[full_index : full_index + 220]

    assert "early signal" in fast_smoke_context or "first signal" in fast_smoke_context
    assert "acceptance check" in focused_context or "acceptance command" in focused_context
    assert (
        "broader regression" in full_context
        or "final verification" in full_context
        or "regression-sensitive verification" in full_context
    )


def test_quick_template_exists_and_defines_lightweight_tracked_flow() -> None:
    content = read_template("templates/commands/quick.md").lower()
    raw_content = (PROJECT_ROOT / "templates/commands/quick.md").read_text(encoding="utf-8").lower()

    assert "dispatch mode follows command tier" in content
    assert "subagent-preferred" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "subagent-blocked" in content
    assert "fall back to leader-inline" not in content
    assert "dispatch to one subagent" not in raw_content
    assert "## leader role" in content
    assert "you are the quick-task leader" in content
    assert "you are not the default implementer for the quick task" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/learnings/index.md" in content
    assert "linked detail markdown document" in content
    assert "passive project learning layer" in content
    assert "passive project learning layer" in content
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
    assert "`needs_rebuild`: record that `{{invoke:map-scan}}`, then `{{invoke:map-build}}`, is required after the understanding checkpoint is confirmed" in content
    assert "`needs_update`: record that `{{invoke:map-update}}` is required after the understanding checkpoint is confirmed" in content
    assert "returned task-local bundle" in content
    assert "must_refresh_topics" not in content
    assert "review_topics" not in content
    assert "task-relevant coverage as insufficient" in content
    assert "ownership, placement, workflow, integration, or verification guidance" in content
    assert ".specify/testing/" not in content
    assert "shared surface" in content or "multiple modules" in content or "shared surfaces" in content
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
    assert "changed_code_paths" in content
    assert "changed_behavior_surfaces" in content
    assert "project_cognition_refresh" in content
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
    assert "choose_subagent_dispatch" in content
    assert "one-subagent" in content
    assert "parallel-subagents" in content
    assert "native-subagents" in content
    assert "record `subagent-blocked`" in content
    assert "leader" in content
    assert "join point" in content
    assert "task contract" in content
    assert (
        "the first actionable execution step after scope lock and understanding confirmation "
        "is to dispatch the first subagent"
    ) in content
    assert "if two or more independent subagent lanes can safely run in parallel" in content
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


def test_quick_template_requires_one_time_understanding_checkpoint() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "## understanding checkpoint" in content
    assert "problem understood" in content
    assert "planned outcome" in content
    assert "scope boundary" in content
    assert "execution approach" in content
    assert "validation" in content
    assert "wait for user confirmation" in content
    assert "revise the checkpoint" in content
    assert "not a full spec" in content
    assert "not a `sp-plan` substitute" in content


def test_quick_template_includes_concrete_status_template() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "## status.md template" in content
    assert "id: [quick-task id]" in content
    assert "slug: [quick-task slug]" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "understanding_confirmed: false | true" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "## current focus" in content
    assert "## execution intent" in content
    assert "intent_outcome:" in content
    assert "intent_constraints:" in content
    assert "success_evidence:" in content
    assert "## understanding checkpoint" in content
    assert "confirmed_problem:" in content
    assert "confirmed_outcome:" in content
    assert "confirmed_scope_boundary:" in content
    assert "confirmed_execution_approach:" in content
    assert "confirmed_validation:" in content
    assert "status.md" in content
    assert "validation route" in content
    assert "known risk" in content
    assert "## execution" in content
    assert "blocked_dispatch:" in content
    assert "## validation" in content
    assert "## summary pointer" in content
    assert "## senior consequence analysis" in content
    assert "affected_objects:" in content
    assert "state_behavior_matrix:" in content
    assert "dependency_impact:" in content
    assert "recovery_and_validation:" in content
    assert "project_cognition_evidence:" in content
    assert "coverage_gaps:" in content
    assert "escalation_decision:" in content


def test_quick_template_defines_explicit_specify_escalation_triggers() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "upgrade to `{{invoke:specify}}` immediately if" in content or "upgrade to `/sp-specify` immediately if" in content
    assert "architecture" in content
    assert "cross-cutting" in content
    assert "change-propagation hotspot" in content
    assert "truth-owning shared surface" in content
    assert "known unknowns" in content
    assert "multiple independent capabilities" in content
    assert "new durable spec" in content or "long-lived feature spec" in content
    assert "rollout" in content or "migration" in content
    assert "acceptance criteria" in content


def test_quick_template_escalates_when_consequence_model_is_not_bounded() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "senior consequence analysis gate" in content
    assert "continue in quick only when the consequence model is bounded" in content
    assert "upgrade to `{{invoke:specify}}` immediately if" in content or "upgrade to `/sp-specify` immediately if" in content
    assert "user-level lifecycle decisions" in content
    assert "broad compatibility handling" in content
    assert "multi-capability scope" in content


def test_quick_template_reads_constitution_and_drives_to_terminal_state() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert ".specify/memory/constitution.md" in content
    assert "constitution first" in content
    assert "record that requirement in `status.md` while `understanding_confirmed: false`" in content
    assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in content
    assert (
        "after `status.md` is initialized, `understanding_confirmed: true` is recorded, "
        "and the first lane is defined, dispatch that subagent path before doing any further local repository deep dive"
    ) in content
    assert "resolved" in content
    assert "blocked" in content


def test_quick_template_requires_self_recovery_before_blocking() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "attempt the smallest safe recovery step before declaring the task blocked" in content
    assert "read additional local context" in content
    assert "run the smallest meaningful verification or repro command" in content
    assert "use `--research`-style focused investigation" in content or "focused investigation" in content
    assert "use the native subagent workflow when subagent dispatch is unavailable" not in content
    assert "retry or recompile the same native-subagent path when contract or context was insufficient" in content
    assert "only then consider subagent-blocked status if no safe subagent path is currently available" in content
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


def test_quick_template_refreshes_project_cognition_when_truth_surfaces_change() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "refresh the project cognition runtime through `{{invoke:map-update}}` using the changed paths" in content
    assert "ordinary uncertain closure" in content
    assert "partial/low-confidence facts, known unknowns, and `minimal_live_reads`" in content
    assert "use map-update for ordinary existing-baseline gaps" in content
    assert "use map-scan -> map-build only for first/missing/unusable baseline, schema failure, zero active-generation path_index rows, explicit_rebuild_requested, or baseline_identity_invalid" in content
    assert "complete-refresh" in content
    assert "project-cognition validate-build --format json" in content
    assert "incremental freshness finalization" in content
    assert "do not run `complete-refresh` as a rebuild finalizer" in content
    assert "if a refresh cannot be completed now" in content
    assert "{{specify-subcmd:project-cognition mark-dirty --reason \"<reason>\" --format json}}" in content
    assert "manual override/fallback" in content


def test_quick_template_requires_constitution_before_status_and_subagent_dispatch() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "constitution first" in content
    assert "before workspace setup, clarification, lane selection, subagent dispatch, or local analysis" in content


def test_quick_template_defines_empty_call_recovery_and_lifecycle_management() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
    assert "unfinished quick-task states" in content or "unfinished quick tasks" in content
    assert "close" in content
    assert "archive" in content


def test_quick_template_blocks_resume_until_understanding_is_confirmed() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "understanding_confirmed: false" in content
    assert "blocks substantive execution" in content
    assert "create or update `status.md` with `understanding_confirmed: false` before any map maintenance handoff" in content
    assert "must not proceed to code edits" in content
    assert "broad repository analysis" in content
    assert "delegation" in content
    assert "validation commands" in content
    assert "{{invoke:map-update}}" in content
    assert "{{invoke:map-scan}}" in content
    assert "{{invoke:map-build}}" in content
    assert "until the checkpoint is confirmed" in content
    assert "do not start execution routing while `understanding_confirmed: false`" in content
    assert "do not dispatch until `understanding_confirmed: true` is recorded" in content
    assert "start execution only after `understanding_confirmed: true` is recorded in `status.md`" in content
    assert "the first concrete execution action after understanding confirmation" in content


def test_quick_template_marks_learning_and_fail_closed_coverage_gates_with_agent_marker() -> None:
    content = read_template("templates/commands/quick.md")
    lowered = content.lower()

    assert "`needs_rebuild`: record that `{{invoke:map-scan}}`, then `{{invoke:map-build}}`, is required after the understanding checkpoint is confirmed" in lowered
    assert "`needs_update`: record that `{{invoke:map-update}}` is required after the understanding checkpoint is confirmed" in lowered
    assert "must_refresh_topics" not in lowered
    assert "review_topics" not in lowered
    assert "ownership, placement, workflow, integration, or verification guidance" in content
    assert "status.md" in lowered
    assert "[AGENT] Use the shared policy function before execution begins and again at each join point" in content
    assert "auto-capture learnings on resolution only" in lowered
    assert "no review, no signal" in lowered


def test_quick_template_requires_tdd_gate_for_behavior_changes() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "behavior-changing" in content or "behavior changing" in content
    assert "bugfix" in content or "bug fix" in content
    assert "refactor" in content
    assert "first executable lane must produce a failing automated test or failing repro check before production edits begin" in content
    assert "do not write production code until the red state is captured" in content
    assert "if no reliable automated test surface exists for the touched behavior" in content
    assert "bootstrap the smallest viable test surface first" in content
    assert "{{invoke:specify}}" in content
    assert "sp-test" not in content


def test_quick_template_routes_uncertain_bugfixes_into_debug() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "root cause is still unknown" in content or "root cause is not yet known" in content
    assert "{{invoke:debug}}" in content or "/sp-debug" in content
    assert "surface-only" in content or "symptom-only" in content
    assert "cannot satisfy the quick-task contract" in content or "cannot satisfy the quick contract" in content
