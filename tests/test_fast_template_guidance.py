from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_fast_template_exists_and_defines_scope_gate() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "dispatch mode follows command tier" in content
    assert "leader-direct" in content
    assert "project-map hard gate" in content
    assert "must pass an atlas gate before" in content
    assert "project-handbook.md" in content
    assert "atlas.entry" in content
    assert "atlas.index.status" in content
    assert "atlas.index.atlas" in content
    assert "pass the atlas gate" in content
    assert "freshness" in content
    assert "atlas.index.status" in content
    assert "shared surfaces" in content
    assert "change-propagation hotspot" in content
    assert "verification entry points" in content
    assert "known unknowns" in content
    assert ".specify/testing/unit_test_system_request.md" in content or ".specify/testing/unit-test-system-request.md" in content
    assert "tiny harness, command, fixture, or helper repair" in content
    assert "## workflow contract summary" in content
    assert "prepare the smallest task contract" in content
    assert "allowed write scope local and explicit" in content
    assert "scope gate" in content
    assert "≤3 files touched" in content or "3 files touched" in content
    assert "verify" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before the final report" in content
    assert "if a full refresh can be completed now" in content
    assert "complete-refresh" in content
    assert "manual override/fallback" in content
    assert "highest-signal" in content
    assert "pass the atlas gate" in content


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

    assert "[AGENT] Before the final report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning" in content


def test_fast_template_requires_tdd_gate_for_behavior_changes() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "behavior-changing" in content or "behavior changing" in content
    assert "write a failing targeted test or failing repro check before editing production code" in content
    assert "do not use manual sanity checks as a substitute for red" in content
    assert "docs-only" in content or "docs only" in content
    assert "if no reliable automated test surface exists" in content
    assert "/sp-test-scan" in content


def test_fast_template_routes_unknown_root_cause_bugfixes_to_debug() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "bug fix" in content or "bugfix" in content
    assert "/sp-debug" in content
    assert "root cause is still unknown" in content or "root cause is not yet known" in content
    assert "symptom patch" in content
