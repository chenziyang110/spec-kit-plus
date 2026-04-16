from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_template_exists_and_defines_lightweight_tracked_flow() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

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
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert "leader" in content
    assert "join point" in content
    assert "single-agent still means one delegated worker lane" in content
    assert "leader-local execution is an exception path" in content
    assert "only when the current quick-task batch cannot proceed through native delegation" in content
    assert "the first actionable execution step after scope lock is to dispatch the first delegated worker lane" in content
    assert "if two or more independent delegated lanes can safely run in parallel" in content


def test_quick_template_defines_recoverable_quick_task_artifacts() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert ".planning/quick/<slug>/" in content
    assert "status.md" in content
    assert "first hard gate" in content
    assert "summary.md" in content
    assert "current focus" in content
    assert "next action" in content
    assert "resume" in content
    assert "resolved/" in content


def test_quick_template_includes_concrete_status_template() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "## status.md template" in content
    assert "slug: [quick-task slug]" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "strategy: single-agent | native-multi-agent | sidecar-runtime" in content
    assert "## current focus" in content
    assert "## execution" in content
    assert "execution_fallback:" in content
    assert "## validation" in content
    assert "## summary pointer" in content


def test_quick_template_defines_explicit_specify_escalation_triggers() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "upgrade to `/sp-specify` immediately if" in content
    assert "architecture" in content
    assert "cross-cutting" in content
    assert "multiple independent capabilities" in content
    assert "new durable spec" in content or "long-lived feature spec" in content
    assert "rollout" in content or "migration" in content
    assert "acceptance criteria" in content


def test_quick_template_reads_constitution_and_drives_to_terminal_state() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert ".specify/memory/constitution.md" in content
    assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in content
    assert "treat `single-agent` as a delegated single-worker path by default" in content
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


def test_quick_template_prefers_parallel_worker_fanout_when_safe() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8").lower()

    assert "materially improve throughput" in content
    assert "dispatch them in parallel" in content
    assert "instead of artificially serializing the work" in content
