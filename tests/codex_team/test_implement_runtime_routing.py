"""Runtime routing tests for the adaptive implement workflow."""

from pathlib import Path

from tests.template_utils import read_command_with_references


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_template() -> str:
    return read_command_with_references("implement")


def test_sp_implement_documents_canonical_decision_order() -> None:
    content = _read_template().lower()
    start = content.index("route in this order:")
    route = content[start : start + 700]

    leader_direct = route.index("`leader-direct`")
    one_subagent = route.index("`one-subagent`")
    parallel_subagents = route.index("`parallel-subagents`")
    managed_team = route.index("`managed-team`")
    blocked = route.index("`subagent-blocked`")

    assert leader_direct < one_subagent < parallel_subagents < managed_team < blocked


def test_sp_implement_preserves_join_point_semantics() -> None:
    content = _read_template().lower()

    assert "explicit join point" in content
    assert "task-graph revision" in content
    assert "one task lifecycle record" in content
    assert "user execution notes" in content
    assert "first-class implementation context" in content
    assert "resume-audit" in content


def test_sp_implement_distinguishes_execution_modes() -> None:
    content = _read_template().lower()

    assert "execution_model: adaptive" in content
    assert "leader-direct" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "managed-team" in content
    assert "subagent-blocked" in content
    assert "execution_model: subagent-mandatory" not in content
    assert "auto-dispatch" not in content


def test_sp_implement_positions_the_runtime_as_adaptive_leader() -> None:
    content = _read_template().lower()

    assert "you are the workflow leader" in content
    assert "you own routing, execution-state truth, acceptance, and recovery" in content
    assert "whether work is leader-direct or delegated" in content
    assert "delegated workers own bounded implementation lanes only" in content
    assert "compile and validate a `workertaskpacket` just in time only for delegated work" in content


def test_sp_implement_continues_until_terminal_state() -> None:
    content = _read_template().lower()

    assert "continue automatically until complete or genuinely blocked" in content
    assert "select the smallest ready task/batch whose dependencies are satisfied" in content
    assert "do not declare completion because tasks look checked off" in content
    assert "plan_gap" in content
    assert "spec_gap" in content


def test_sp_implement_requires_user_facing_closeout_summary() -> None:
    content = _read_template().lower()

    assert "implementation-summary.md" in content
    assert "implementation_summary" in content
    assert "what changed, how to verify it, and what differs from the previous version" in content
    assert "git diff --stat" in content
    assert "git diff --name-status" in content
