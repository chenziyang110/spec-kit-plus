"""Recovery edge contracts; text checks do not prove model execution or acceptance."""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "templates/command-references/debug"
ADVANCED = ROOT / "templates/advanced-skills/spx-debug"
CONTRACT = ADVANCED / "references/investigation-contract.md"


def compact(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).lower()


@pytest.mark.parametrize("path", [
    ROOT / "templates/commands/debug.md",
    ADVANCED / "SKILL.md",
    ROOT / "templates/command-partials/debug/shell.md",
])
def test_diagnosis_only_delivery_is_reachable_from_both_entrypoints(path: Path) -> None:
    content = compact(path)
    assert "diagnosis-only delivery" in content
    assert "diagnose only" in content
    assert "diagnosis" in content and "not" in content and "resolved" in content


@pytest.mark.parametrize("path", [CLASSIC / "debug-state.md", CONTRACT])
def test_diagnosis_only_does_not_manufacture_a_fix_lifecycle(path: Path) -> None:
    content = compact(path)
    for required in (
        "## diagnosis-only delivery", "confirmed", "diagnose only",
        "requested diagnosis", "not defect resolution", "nonexistent fix",
        "current focus", "resolution", "no new status",
        "unrequested repair", "unanswered diagnosis",
    ):
        assert required in content, (path, required)


@pytest.mark.parametrize("path", [CLASSIC / "fix-gate.md", CONTRACT])
def test_guard_covers_supporting_writes_and_must_be_refreshed(path: Path) -> None:
    content = compact(path)
    for required in (
        "before any source, test, harness, configuration, or instrumentation write",
        "execution guard", "scope expansion or source drift", "renew",
        "supporting repair", "original target", "diagnosis-only authority",
    ):
        assert required in content, (path, required)
    assert "does not bypass target red" in content


@pytest.mark.parametrize("path", [CLASSIC / "hypothesis-and-root-cause.md", CONTRACT])
def test_disconfirming_observations_are_not_rejected_to_protect_hypothesis(path: Path) -> None:
    content = compact(path)
    assert "contradictory observations are valid evidence" in content
    assert "do not ask a worker to change an observation" in content
    assert "preserve the raw evidence" in content
    assert "not a majority vote" in content
    for old in (
        "wrong-session, or contradictory returns for bounded repair",
        "wrong-session or contradictory returns for bounded repair",
    ):
        assert old not in content


@pytest.mark.parametrize("path", [CLASSIC / "hypothesis-and-root-cause.md", CONTRACT])
def test_unsafe_or_silent_worker_can_be_cancelled_without_false_acceptance(path: Path) -> None:
    content = compact(path)
    for required in (
        "without waiting for a missing handoff", "native owner",
        "cancellation is not task acceptance", "partial evidence",
        "no broad process kill", "independent", "pending",
    ):
        assert required in content, (path, required)
    assert "before closing the join point, declaring completion, requesting shutdown, or interrupting" not in content


@pytest.mark.parametrize("path", [CLASSIC / "hypothesis-and-root-cause.md", CONTRACT])
def test_live_capabilities_and_successful_fallback_replace_stale_dispatch(path: Path) -> None:
    content = compact(path)
    for required in (
        "installation metadata", "live tool surface", "not proof",
        "execution_model: leader-inline", "execution_surface: leader-inline",
        "historical dispatch failure", "evidence", "blocked_reason",
    ):
        assert required in content, (path, required)


@pytest.mark.parametrize("path", [
    ROOT / "templates/worker-prompts/debug-investigator.md",
    ADVANCED / "references/investigator-worker.md",
])
def test_workers_keep_disconfirming_facts_and_do_not_self_promote_to_fix(path: Path) -> None:
    content = compact(path)
    assert "a disconfirming observation is not a failed assignment" in content
    assert "do not rerun merely to obtain a preferred outcome" in content
    assert "partial evidence" in content
    assert "claim awaiting acceptance" in content
    assert "a read-only evidence assignment does not authorize" in content


def test_advanced_summary_does_not_jump_from_confirmation_to_reproduction() -> None:
    content = compact(ADVANCED / "SKILL.md")
    assert "after confirmation and accepted framing" in content
    assert "after confirmation, reproduce the symptom" not in content


def test_shell_distinguishes_dispatch_failure_from_terminal_debug_block() -> None:
    content = compact(ROOT / "templates/command-partials/debug/shell.md")
    assert "historical dispatch failure" in content
    assert "authorized fallback" in content
    assert "blocked debug execution records" not in content


@pytest.mark.parametrize("path", [
    CLASSIC / "intake-and-debug-checkpoint.md",
    CLASSIC / "reproduction-and-evidence.md",
    CONTRACT,
])
def test_navigation_hints_do_not_grant_early_evidence_reads(path: Path) -> None:
    content = compact(path)
    assert "navigation hints are not read authorization" in content
    assert "after confirmation and accepted framing" in content
    assert "minimal_live_reads" in content


@pytest.mark.parametrize("path", [
    CLASSIC / "reproduction-and-evidence.md", CONTRACT,
])
def test_missing_advisory_map_does_not_require_automatic_map_workflow(path: Path) -> None:
    content = compact(path)
    for required in (
        "report-grounded deep intake", "unknown", "hypotheses, not live facts",
        "canonical artifact runtime", "do not invoke map maintenance automatically",
    ):
        assert required in content, (path, required)


@pytest.mark.parametrize("path", [
    CLASSIC / "intake-and-debug-checkpoint.md",
    CLASSIC / "reproduction-and-evidence.md",
    CONTRACT,
])
def test_optional_feature_context_does_not_block_standalone_debug(path: Path) -> None:
    content = compact(path)
    assert "optional feature artifacts" in content
    assert "valid feature binding" in content
    assert "standalone debug" in content
    assert "do not create" in content


@pytest.mark.parametrize("path", [
    CLASSIC / "intake-and-debug-checkpoint.md",
    CLASSIC / "reproduction-and-evidence.md",
    CLASSIC / "regression-validation-and-closeout.md",
])
def test_diagnosis_delivery_does_not_fall_back_into_unconditional_repair(path: Path) -> None:
    content = compact(path)
    assert "diagnosis-only delivery" in content
    assert "diagnose only" in content
