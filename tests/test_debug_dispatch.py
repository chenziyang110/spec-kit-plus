from specify_cli.debug.dispatch import (
    build_codex_dispatch_plan,
    build_codex_spawn_plan,
    format_dispatch_plan,
    format_spawn_plan,
)
from specify_cli.debug.schema import DebugGraphState, SuggestedEvidenceLane


def test_build_codex_dispatch_plan_uses_suggested_lanes() -> None:
    state = DebugGraphState(
        slug="session",
        trigger="queue stuck",
        diagnostic_profile="scheduler-admission",
    )
    state.current_focus.hypothesis = "Scheduler failed to promote queued work"
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="queue-snapshot",
            focus="waiting and promotion flow",
            evidence_to_collect=["queue contents before the decision", "promotion ordering evidence"],
            join_goal="Decide whether queue state and promotion order are consistent.",
        )
    ]

    tasks = build_codex_dispatch_plan(state)

    assert len(tasks) == 1
    assert tasks[0].lane_name == "queue-snapshot"
    assert tasks[0].agent_role == "evidence-collector"
    assert "scheduler-admission" in tasks[0].task_summary
    assert "Diagnostic profile: scheduler-admission" in tasks[0].prompt
    assert "Do not mutate the debug session file." in tasks[0].prompt


def test_format_dispatch_plan_renders_lane_summaries() -> None:
    state = DebugGraphState(
        slug="session",
        trigger="stale cache",
        diagnostic_profile="cache-snapshot",
    )
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="snapshot-drift-trace",
            focus="cache or snapshot divergence",
            evidence_to_collect=["cached state", "snapshot write timestamp"],
        )
    ]

    rendered = format_dispatch_plan(build_codex_dispatch_plan(state))

    assert "Suggested Codex Dispatch" in rendered
    assert "snapshot-drift-trace: cache or snapshot divergence [cache-snapshot]" in rendered
    assert "role: evidence-collector" in rendered


def test_build_codex_spawn_plan_generates_spawn_ready_payloads() -> None:
    state = DebugGraphState(
        slug="session",
        trigger="ui mismatch",
        diagnostic_profile="ui-projection",
    )
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="source-truth-trace",
            focus="publish-time source state",
            evidence_to_collect=["source-of-truth state at publish time"],
        )
    ]

    payloads = build_codex_spawn_plan(state)

    assert len(payloads) == 1
    assert payloads[0].lane_name == "source-truth-trace"
    assert payloads[0].agent_type == "explorer"
    assert payloads[0].reasoning_effort == "medium"
    assert "Investigate lane `source-truth-trace`" in payloads[0].message


def test_format_spawn_plan_renders_spawn_payloads() -> None:
    state = DebugGraphState(
        slug="session",
        trigger="ui mismatch",
        diagnostic_profile="ui-projection",
    )
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="source-truth-trace",
            focus="publish-time source state",
            evidence_to_collect=["source-of-truth state at publish time"],
        )
    ]

    rendered = format_spawn_plan(build_codex_spawn_plan(state))

    assert "Suggested Codex Spawn Payloads" in rendered
    assert "source-truth-trace: explorer (medium)" in rendered
