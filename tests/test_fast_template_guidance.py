from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_fast_template_exists_and_defines_scope_gate() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
    assert "the leader orchestrates:" in content
    assert "before dispatch, every subagent lane needs a task contract" in content
    assert "structured handoff" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "specify learning start --command fast --format json" in content
    assert "specify learning capture --command fast" in content
    assert "read `project-handbook.md`" in content
    assert ".specify/project-map/index/status.json" in content
    assert "project-map freshness helper" in content
    assert "freshness is `missing` or `stale`" in content
    assert "freshness is `possibly_stale`" in content
    assert "must_refresh_topics" in content
    assert "review_topics" in content
    assert "shared surfaces" in content
    assert "risky coordination points" in content
    assert "change-propagation hotspots" in content
    assert "verification entry points" in content
    assert "known unknowns" in content
    assert ".specify/testing/unit_test_system_request.md" in content or ".specify/testing/unit-test-system-request.md" in content
    assert "tiny harness, command, fixture, or helper repair" in content
    assert "if `project-handbook.md` or `.specify/project-map/` is missing" in content
    assert "redirect to `/sp-quick` so the navigation system can be rebuilt safely" in content
    assert "## workflow contract summary" in content
    assert "prepare the smallest task contract" in content
    assert "dispatch one subagent" in content
    assert "wait for the structured handoff" in content
    assert "allowed write scope local and explicit" in content
    assert "scope gate" in content
    assert "at most 3 files" in content or "no more than 3 files" in content
    assert "no new dependencies" in content
    assert "no architecture changes" in content or "no api changes" in content
    assert "use `/sp.quick`" in content or "use `/sp-quick`" in content or "use `/sp.quick`" in content
    assert "verify" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before the final report" in content
    assert "if that refresh would break the fast-path scope" in content
    assert "mark `.specify/project-map/index/status.json` dirty" in content
    assert "highest-signal" in content


def test_fast_template_uses_lightweight_subagent_contract() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "no spec.md" in content or "do not create spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "subagent" in content
    assert "task contract" in content


def test_fast_template_defines_explicit_upgrade_triggers() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "upgrade to `/sp-quick` immediately if" in content
    assert "more than 3 files" in content
    assert "shared surface" in content
    assert "change-propagation hotspot" in content
    assert "known unknowns" in content
    assert "known unknowns that make direct execution unsafe" not in content
    assert "safe packetized delegation unavailable" in content
    assert "needs research" in content or "research or clarification" in content
    assert "upgrade to `/sp-specify` immediately if" in content
    assert "unit test system program" in content or "testing-system program" in content
    assert "new workflow" in content
    assert "compatibility" in content
    assert "acceptance criteria" in content


def test_fast_template_marks_learning_and_fail_closed_routing_gates_with_agent_marker() -> None:
    content = read_template("templates/commands/fast.md")

    assert "[AGENT] Run `specify learning start --command fast --format json`" in content
    assert "[AGENT] If freshness is `missing` or `stale`, stop and redirect to `/sp-quick` or `/sp-map-scan` followed by `/sp-map-build`" in content
    assert "[AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`." in content
    assert "[AGENT] If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick`" in content
    assert "[AGENT] If the requested change touches a shared surface, risky coordination point, propagation hotspot, non-trivial verification entry point, or known-unknown-heavy area, stop and redirect to `/sp-quick`." in content
    assert "[AGENT] Before the final report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning" in content


def test_fast_template_requires_tdd_gate_for_behavior_changes() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "behavior-changing" in content or "behavior changing" in content
    assert "write a failing targeted test or failing repro check before editing production code" in content
    assert "do not use manual sanity checks as a substitute for red" in content
    assert "docs-only" in content or "docs only" in content
    assert "if no reliable automated test surface exists" in content
    assert "/sp-test" in content


def test_fast_template_routes_unknown_root_cause_bugfixes_to_debug() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "bug fix" in content or "bugfix" in content
    assert "/sp-debug" in content
    assert "root cause is still unknown" in content or "root cause is not yet known" in content
    assert "symptom-fix lane" in content or "symptom fix lane" in content
