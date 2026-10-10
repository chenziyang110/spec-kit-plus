"""Global recovery prompt contracts, not a simulation of an agent's decisions.

The installed/catalog coverage lives in integrations/test_global_blocker_recovery.py.
The older four-lane suite continues to cover specialized execution recovery.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLASSIC_EXIT = "templates/command-partials/common/blocker-resolution.md"
ADVANCED_EXIT = "templates/advanced-skills/_shared/blocker-resolution.md"
RECOVERY_POLICIES = (
    "templates/command-partials/common/autonomous-blocker-recovery.md",
    "templates/advanced-skills/_shared/autonomous-blocker-recovery.md",
    "templates/workflow-blocker-template.md",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _compact(path: str) -> str:
    return re.sub(r"\s+", " ", _read(path)).lower()


def test_classic_global_exit_routes_to_recovery_before_terminal_view() -> None:
    contract = _compact(CLASSIC_EXIT)
    assert "all `sp-*` workflows must recover before exiting" in contract
    assert "recovery decision" in contract
    assert ".specify/templates/workflow-blocker-template.md" in contract
    assert contract.index("recovery decision") < contract.index("use the terminal view")
    assert "same invocation" in contract
    assert "original workflow's full completion criteria" in contract


def test_advanced_global_exit_reads_recovery_before_deciding_to_stop() -> None:
    contract = _compact(ADVANCED_EXIT)
    assert "every `spx-*` workflow" in contract
    assert "references/autonomous-blocker-recovery.md" in contract
    assert "before deciding that a failure is terminal" in contract
    assert "do not wait for the user to request recovery" in contract
    assert contract.index("references/autonomous-blocker-recovery.md") < contract.index(
        "use this terminal view"
    )


@pytest.mark.parametrize("path", RECOVERY_POLICIES)
@pytest.mark.parametrize(
    "required",
    (
        "current goal",
        "available permissions",
        "routine permission",
        "unknown root cause",
        "read-only",
        "stage boundaries",
        "exit `10`",
        "same invocation",
        "resume the exact interrupted gate",
        "independent dependency-ready work",
        "retry count alone",
        "bounded backoff",
        "acceptance criteria",
        "mandatory checks",
        "fabricate evidence",
        "overwrite unrelated user changes",
        "human_action_required: false",
    ),
)
def test_global_policy_preserves_recovery_and_safety(path: str, required: str) -> None:
    assert required in _compact(path), (path, required)


@pytest.mark.parametrize("path", (CLASSIC_EXIT, ADVANCED_EXIT, *RECOVERY_POLICIES))
def test_global_recovery_is_not_restricted_to_four_execution_lanes(path: str) -> None:
    contract = _compact(path)
    assert "for fast, quick, implement, and debug" not in contract
    assert "this contract applies to `sp-fast`" not in contract
    assert "read this reference for `spx-fast`" not in contract


@pytest.mark.parametrize("path", (CLASSIC_EXIT, ADVANCED_EXIT))
@pytest.mark.parametrize(
    "binding",
    (
        "show_argv",
        "resolution_action",
        "next_argv",
        "pending_reopen_action",
        "workflow.reconcile-blocker",
        "workflow.resolve",
    ),
)
def test_recovery_keeps_runtime_resolution_and_reopen_ownership(
    path: str, binding: str
) -> None:
    assert binding in _read(path)


def test_terminal_view_is_distinct_from_recovery_instructions() -> None:
    template = _read("templates/workflow-blocker-template.md")
    assert template.index("## Recovery Decision (Agent-Only)") < template.index("## Blocked\n")
    assert template.index("## Blocked\n") < template.index("## Human Action Guide")
    assert "do not copy it into the user report" in template
    assert "self-verification is not independent acceptance" in template
    assert "no safe authorized recovery or independent work" in template
    assert "human guide null" in template
