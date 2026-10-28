"""Debug prompt contracts: source coverage, not simulated LLM/runtime acceptance.

Installation and native-format delivery are tested separately. These tests
intentionally inspect the owning surfaces rather than copied generated skills.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = "templates/command-references/debug/"
ADVANCED = "templates/advanced-skills/spx-debug/"


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def compact(path: str) -> str:
    return re.sub(r"\s+", " ", text(path)).lower()


@pytest.mark.parametrize("path", [
    "templates/commands/debug.md", ADVANCED + "SKILL.md",
])
def test_entrypoints_retain_preflight_and_guarded_human_closeout(path: str) -> None:
    content = compact(path)
    assert "context-direct" in content
    assert "execution guard" in content
    assert "awaiting_human_verify" in content
    assert "explicit human confirmation" in content
    assert "earliest" in content
    assert "same invocation" in content


def test_advanced_preflight_still_precedes_reads_and_requires_branch_choice() -> None:
    content = text(ADVANCED + "SKILL.md")
    assert content.index("## Hard preflight stop") < content.index("Read `references/project-learning.md`")
    assert "The invoking request is not a branch selection" in content
    assert "**Direct fix (Recommended)** or **Continue full sp-debug**" in content
    assert "Before opening any reference or calling any tool" in content
    assert "without clearing still-valid confirmations" in content


@pytest.mark.parametrize("path", [
    CLASSIC + "intake-and-debug-checkpoint.md",
    CLASSIC + "debug-state.md",
    ADVANCED + "references/investigation-contract.md",
])
def test_resume_uses_identity_and_reuses_valid_confirmation(path: str) -> None:
    content = compact(path)
    assert "recency alone" in content
    assert "unambiguous" in content
    assert "confirmation" in content and "resume" in content
    assert "do not" in content
    assert "classification" in content and "not confirmation" in content
    assert "explicit human confirmation or an evidence-backed classification" not in content


@pytest.mark.parametrize("path", [
    CLASSIC + "reproduction-and-evidence.md",
    CLASSIC + "hypothesis-and-root-cause.md",
    CLASSIC + "regression-validation-and-closeout.md",
    CLASSIC + "intake-and-debug-checkpoint.md",
])
def test_generated_debug_does_not_wait_for_legacy_python_graph(path: str) -> None:
    content = compact(path)
    for obsolete in (
        "dispatched automatically by the graph engine",
        "the graph engine (gatheringnode) will return",
        "gathering returns an `await_input`",
        "when you receive the `think_subagent_prompt`",
        "when you receive `contract_subagent_prompt`",
        "execute_command: debug",
        "run or emulate:",
    ):
        assert obsolete not in content, (path, obsolete)


def test_deep_stages_are_scheduled_and_accepted_in_dependency_order() -> None:
    content = compact(CLASSIC + "reproduction-and-evidence.md")
    for required in (
        "the leader compiles the bounded stage 1a assignment",
        "set `causal_map_completed: true` only after acceptance",
        "stage 1b depends on this accepted output",
        "must not run concurrently with its producer",
        "repair missing rows before accepting the result",
        "only after both dependent stages are accepted",
    ):
        assert required in content


@pytest.mark.parametrize("path", [
    CLASSIC + "reproduction-and-evidence.md", CLASSIC + "debug-state.md",
    ADVANCED + "references/investigation-contract.md",
])
def test_minimum_intake_does_not_require_deep_only_fields(path: str) -> None:
    content = compact(path)
    assert "do not impose deep-only fields on" in content
    assert "map-backed" in content
    if path == CLASSIC + "reproduction-and-evidence.md":
        assert "transition memo comes from the selected accepted intake package" in content
        assert "after `session patch` persists the stage 1b package" not in content
        assert "validate their substantive contents" in content


def test_evidence_substeps_do_not_redefine_fix_and_verify_stage_numbers() -> None:
    content = text(CLASSIC + "reproduction-and-evidence.md")
    labels = re.findall(r"^### Stage ([0-9]+[A-Z]?): ([^\n]+)", content, re.MULTILINE)
    assert [label for label, _ in labels] == ["1A", "1B", "2", "2A", "2B", "2C", "2D", "2E", "2F"]
    assert "`Stage 3: Fix`" in content and "`Stage 4: Verify`" in content
    assert "return to Stage 5" not in content


@pytest.mark.parametrize("path", [
    CLASSIC + "hypothesis-and-root-cause.md",
    ADVANCED + "references/investigation-contract.md",
])
def test_parallel_lanes_are_bounded_revision_bound_and_joined(path: str) -> None:
    content = compact(path)
    for required in (
        "accepted prerequisites", "forbidden writes", "resource/timeout budget",
        "ports", "databases", "browser profiles", "fixtures", "caches",
        "stale", "wrong-session", "contradictory", "consumer acceptance",
        "quiesce", "redispatch", "independent", "pending",
    ):
        assert required in content, (path, required)
    assert "one active causal decision" in content
    assert "evidence" in content and "input revision" in content


@pytest.mark.parametrize("path", [
    "templates/worker-prompts/debug-investigator.md",
    ADVANCED + "references/investigator-worker.md",
])
def test_workers_return_reproducible_evidence_without_claiming_acceptance(path: str) -> None:
    content = compact(path)
    for required in (
        "session/lane identity", "input revision", "accepted prerequisites",
        "forbidden writes", "expected and observed outcomes", "exit codes",
        "unavailable/skipped", "actual side effects",
    ):
        assert required in content, (path, required)
    assert "target failure from a harness/import/permission/timeout failure" in content
    assert "a read-only evidence assignment does not authorize" in content
    assert "complete runtime-owned argv" in content
    assert "without a supplied channel" in content
    assert "a claim awaiting acceptance" in content
    assert "an unavailable review remains pending" in content


@pytest.mark.parametrize("path", [
    CLASSIC + "fix-gate.md", ADVANCED + "references/investigation-contract.md",
])
def test_target_red_and_owned_cleanup_precede_final_evidence(path: str) -> None:
    content = compact(path)
    assert "red must match the target" in content
    assert "diagnosis-only authority" in content
    assert "execution guard" in content
    assert "final integrated revision" in content
    assert "cleanup" in content
    assert "same invocation" in content
    assert "route it through `/sp-quick`" not in content


@pytest.mark.parametrize("path", [
    CLASSIC + "debug-state.md", ADVANCED + "references/investigation-contract.md",
])
def test_resume_preserves_newer_evidence_and_checks_completed_actions(path: str) -> None:
    content = compact(path)
    assert "lease conflict" in content
    assert "newer evidence" in content
    assert "before" in content and "redispatch" in content
    assert "parallel state file" in content
    assert "current focus" in content and "execution intent" in content


@pytest.mark.parametrize("path", [
    CLASSIC + "regression-validation-and-closeout.md",
    ADVANCED + "references/investigation-contract.md",
])
def test_closeout_keeps_open_rows_and_binds_human_approval_to_current_fix(path: str) -> None:
    content = compact(path)
    for required in (
        "failed, skipped, unavailable and stale", "accepted failure report",
        "awaiting_human_verify", "not `resolved`", "classification",
        "current", "explicit human confirmation", "closeout receipt",
        "archive only when requested", "same invocation",
    ):
        assert required in content, (path, required)
    assert "status=ok" in content
    assert "human" in content and "parent" in content and "child" in content


def test_hypothesis_reference_has_one_coherent_loop_not_orphaned_intake_steps() -> None:
    content = text(CLASSIC + "hypothesis-and-root-cause.md")
    assert content.count("## Hypothesis And Root Cause") == 1
    assert "candidate_queue" in content
    assert "alternative_hypotheses_considered" in content
    assert "decisive_signal" in content
    assert "After two failed verification cycles" in content
    assert not re.search(r"^  [45]\. Parse|^  [45]\. `SESSION PATCH`", content, re.MULTILINE)


def test_retained_debug_reference_coverage_is_not_lost() -> None:
    fixture = json.loads(text("tests/fixtures/command-reference-coverage/debug.json"))
    assert fixture["workflow"] == "debug"
    assert fixture["entries"]
    for entry in fixture["entries"]:
        assert entry["source_excerpt"].lower() in compact(entry["target"]), entry
