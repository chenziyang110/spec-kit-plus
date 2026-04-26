from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_template_exists_and_defines_lightweight_tracked_flow() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "## leader role" in content
    assert "you are the quick-task leader" in content
    assert "you are not the default worker for the quick task" in content
    assert "dispatch the lane instead of continuing leader-local implementation work" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "specify learning start --command quick --format json" in content
    assert "specify learning capture --command quick" in content
    assert "read `project-handbook.md`" in content
    assert ".specify/project-map/status.json" in content
    assert "project-map freshness helper" in content
    assert "freshness is `missing` or `stale`" in content
    assert "freshness is `possibly_stale`" in content
    assert "must_refresh_topics" in content
    assert "review_topics" in content
    assert "topic map" in content
    assert "touched-area topical files" in content
    assert "if `project-handbook.md` or the required `.specify/project-map/` files are missing" in content
    assert "run `/sp-map-codebase` before continuing" in content
    assert "task-relevant coverage is insufficient" in content
    assert "ownership or placement guidance" in content
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in content
    assert "coverage-model check" in content
    assert "truth-owning surfaces" in content
    assert "change-propagation hotspots" in content
    assert "verification entry points" in content
    assert "known unknowns or stale evidence boundaries" in content
    assert "before choosing the quick-task lane shape" in content
    assert "ad-hoc task" in content or "small, ad-hoc task" in content
    assert "lightweight" in content
    assert ".planning/quick/" in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "skip the full" in content and "specify" in content
    assert "summary.md" in content or "summary artifact" in content
    assert "before any substantial repository analysis" in content
    assert "read `.specify/memory/constitution.md` first" in content
    assert "highest-signal" in content


def test_quick_template_preserves_quality_guardrails() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "scope gate" in content
    assert "small but non-trivial" in content or "not for trivial work" in content
    assert "redirect to `/sp-fast`" in content or "use `/sp-fast`" in content
    assert "redirect to `/sp-specify`" in content or "use `/sp-specify`" in content
    assert "validate" in content
    assert "verify" in content
    assert "completion standard" in content
    assert "small, transparent closed loop" in content
    assert "at least one meaningful verification step" in content or "at least one smallest meaningful executable verification step has run" in content
    assert "unverified surface" in content or "not checked" in content


def test_quick_template_defines_capability_aware_execution_strategy() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "choose_execution_strategy" in content
    assert "single-agent" in content
    assert "single-lane" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "leader" in content
    assert "join point" in content
    assert "`single-lane` still means one delegated worker lane" in content
    assert "not as permission to personally do the task" in content
    assert "leader-local execution is an exception path" in content
    assert "only when the current quick-task batch cannot proceed through native delegation" in content
    assert "the first actionable execution step after scope lock is to dispatch the first delegated worker lane" in content
    assert "if two or more independent delegated lanes can safely run in parallel" in content


def test_quick_template_defines_recoverable_quick_task_artifacts() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

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
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "## status.md template" in content
    assert "id: [quick-task id]" in content
    assert "slug: [quick-task slug]" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "strategy: single-lane | native-multi-agent | sidecar-runtime" in content
    assert "## current focus" in content
    assert "## execution intent" in content
    assert "intent_outcome:" in content
    assert "intent_constraints:" in content
    assert "success_evidence:" in content
    assert "## execution" in content
    assert "execution_fallback:" in content
    assert "## validation" in content
    assert "## summary pointer" in content


def test_quick_template_defines_explicit_specify_escalation_triggers() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "upgrade to `/sp-specify` immediately if" in content
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
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert ".specify/memory/constitution.md" in content
    assert "constitution first" in content
    assert "before `status.md` initialization or touched-area analysis proceeds" in content
    assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in content
    assert "treat `single-lane` as a delegated single-worker path by default" in content
    assert "dispatch that worker path before doing any further local repository deep dive" in content
    assert "resolved" in content
    assert "blocked" in content


def test_quick_template_requires_self_recovery_before_blocking() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "attempt the smallest safe recovery step before declaring the task blocked" in content
    assert "read additional local context" in content
    assert "run the smallest meaningful verification or repro command" in content
    assert "attempt the next safe execution surface before switching to leader-local work" in content
    assert "use `--research`-style focused investigation" in content or "focused investigation" in content
    assert "retry_attempts" in content
    assert "recovery_action" in content
    assert "blocker_reason" in content


def test_quick_template_requires_minimal_plan_for_propagating_changes() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

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
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "sampling is not sufficient" in content
    assert "full-coverage check" in content or "full coverage check" in content
    assert "every affected callsite" in content or "every affected call site" in content
    assert "do not claim completion" in content


def test_quick_template_requires_summary_transparency_for_verified_and_unverified_surfaces() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "summary artifact" in content
    assert "which surfaces were left unverified" in content
    assert "separate `verified` coverage from `not checked` coverage" in content
    assert "for each declared surface, give the terminal status conclusion" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-codebase` before marking the quick task `resolved`" in content
    assert "if you cannot complete that refresh in the current pass" in content
    assert "mark `.specify/project-map/status.json` dirty" in content


def test_quick_template_requires_constitution_before_status_and_delegation() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "do not create or update `status.md`" in content
    assert "until the constitution has been read or confirmed absent" in content
    assert "before workspace setup, clarification, lane selection, delegation, or local analysis" in content


def test_quick_template_prefers_parallel_worker_fanout_when_safe() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "materially improve throughput" in content
    assert "dispatch them in parallel" in content
    assert "instead of artificially serializing the work" in content


def test_quick_template_defines_empty_call_recovery_and_lifecycle_management() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
    assert "resumable unfinished work" in content
    assert "close" in content
    assert "archive" in content


def test_quick_template_marks_learning_and_fail_closed_coverage_gates_with_agent_marker() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8")

    assert "[AGENT] Run `specify learning start --command quick --format json`" in content
    assert "[AGENT] If freshness is `missing` or `stale`, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts." in content
    assert "[AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`." in content
    assert "[AGENT] If `PROJECT-HANDBOOK.md` or the required `.specify/project-map/` files are missing, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts." in content
    assert "[AGENT] If task-relevant coverage is insufficient for the current quick task, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts." in content
    assert "[AGENT] Create or resume `STATUS.md`" in content
    assert "[AGENT] Use the shared policy function before execution begins and again at each join point" in content
    assert "[AGENT] Before the final summary, capture any new `pitfall`, `recovery_path`, or `project_constraint` learning" in content


def test_quick_template_requires_tdd_gate_for_behavior_changes() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "behavior-changing" in content or "behavior changing" in content
    assert "bugfix" in content or "bug fix" in content
    assert "refactor" in content
    assert "first executable lane must produce a failing automated test or failing repro check before production edits begin" in content
    assert "do not write production code until the red state is captured" in content
    assert "if no reliable automated test surface exists for the touched behavior" in content
    assert "bootstrap the smallest viable test surface first" in content
    assert "/sp-test" in content
