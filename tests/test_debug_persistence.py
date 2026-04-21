from pathlib import Path

import pytest

from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState, OwnershipEntry, SuggestedEvidenceLane


def test_persistence_round_trips_full_state(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="roundtrip")
    state.diagnostic_profile = "scheduler-admission"
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="queue-snapshot",
            focus="waiting and promotion flow",
            evidence_to_collect=["queue contents before the decision"],
            join_goal="Decide whether queue state and promotion order are consistent.",
        )
    ]
    state.current_focus.hypothesis = "Parser bug"
    state.current_focus.next_action = "Line 1\nline 2: still same field"
    state.symptoms.expected = "final token preserved"
    state.symptoms.actual = "final token missing"
    state.symptoms.reproduction_verified = True
    state.truth_ownership.append(
        OwnershipEntry(
            layer="scheduler",
            owns="admitted running set",
            evidence="allocation decisions are made here",
        )
    )
    state.control_state = ["activeCount", "runningOrder_"]
    state.observation_state = ["allTasks_", "ui polling result"]
    state.closed_loop.input_event = "slot released"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "assign freed slot"
    state.closed_loop.state_transition = "queued task enters running set"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion not reflected in running set"
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale admitted ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "slot release did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "runningOrder_=[], waitingQueue_=[task-2], activeCount=1",
    }
    state.context.feature_id = "002-autonomous-execution"
    state.context.modified_files = ["src/specify_cli/debug/graph.py", "tests/test_debug_graph_nodes.py"]
    state.recently_modified = ["src/specify_cli/debug/persistence.py"]
    state.resolution.files_changed = ["src/specify_cli/debug/graph.py"]
    state.resolution.report = "## Awaiting Human Review\n- Investigate parser boundary"
    state.resolution.decisive_signals = ["runningOrder_=[], waitingQueue_=[task-2], activeCount=1"]
    state.resolution.rejected_surface_fixes = ["normalized UI state without fixing scheduler admission"]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.diagnostic_profile == "scheduler-admission"
    assert restored.suggested_evidence_lanes[0].name == "queue-snapshot"
    assert restored.suggested_evidence_lanes[0].focus == "waiting and promotion flow"
    assert restored.current_focus.next_action == "Line 1\nline 2: still same field"
    assert restored.symptoms.reproduction_verified is True
    assert restored.truth_ownership[0].layer == "scheduler"
    assert restored.truth_ownership[0].owns == "admitted running set"
    assert restored.control_state == ["activeCount", "runningOrder_"]
    assert restored.observation_state == ["allTasks_", "ui polling result"]
    assert restored.closed_loop.input_event == "slot released"
    assert restored.closed_loop.break_point == "promotion not reflected in running set"
    assert restored.resolution.root_cause is not None
    assert restored.resolution.root_cause.summary == "Scheduler kept stale admitted ownership after slot release"
    assert restored.resolution.root_cause.owning_layer == "scheduler"
    assert restored.context.feature_id == "002-autonomous-execution"
    assert restored.context.modified_files == [
        "src/specify_cli/debug/graph.py",
        "tests/test_debug_graph_nodes.py",
    ]
    assert restored.recently_modified == ["src/specify_cli/debug/persistence.py"]
    assert restored.resolution.files_changed == ["src/specify_cli/debug/graph.py"]
    assert restored.resolution.report == "## Awaiting Human Review\n- Investigate parser boundary"
    assert restored.resolution.decisive_signals == ["runningOrder_=[], waitingQueue_=[task-2], activeCount=1"]
    assert restored.resolution.rejected_surface_fixes == [
        "normalized UI state without fixing scheduler admission"
    ]


def test_resolution_root_cause_string_assignment_is_normalized():
    state = DebugGraphState(slug="session", trigger="string root cause")

    state.resolution.root_cause = "Parser boundary issue"

    assert state.resolution.root_cause is not None
    assert state.resolution.root_cause.summary == "Parser boundary issue"


def test_handoff_report_includes_diagnostic_profile(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="profile handoff", diagnostic_profile="ui-projection")

    report = handler.build_handoff_report(state)

    assert "Diagnostic profile: ui-projection" in report


def test_handoff_report_includes_suggested_evidence_lanes(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="lane handoff", diagnostic_profile="scheduler-admission")
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="queue-snapshot",
            focus="waiting and promotion flow",
            evidence_to_collect=["queue contents before the decision"],
            join_goal="Decide whether queue state and promotion order are consistent.",
        )
    ]

    report = handler.build_handoff_report(state)

    assert "Suggested Evidence Lanes" in report
    assert "queue-snapshot: waiting and promotion flow" in report
    assert "Suggested Codex Dispatch" in report
    assert "role: evidence-collector" in report
    assert "Suggested Codex Spawn Payloads" in report
    assert "queue-snapshot: explorer (medium)" in report


def test_persistence_round_trips_trigger_with_frontmatter_delimiter(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="parser --- bug")

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.trigger == "parser --- bug"


def test_persistence_rejects_path_like_slug(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="../escape", trigger="bad slug")

    with pytest.raises(ValueError):
        handler.save(state)


def test_persistence_load_rejects_executable_files_changed_payload(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    sentinel = (tmp_path / "executed.txt").as_posix()
    session_path = tmp_path / "session.md"
    session_path.write_text(
        "\n".join(
            [
                "---",
                "slug: session",
                "status: gathering",
                "trigger: malicious",
                "current_node_id: GatheringNode",
                "created: 2026-04-13T00:00:00",
                "updated: 2026-04-13T00:00:00",
                "---",
                "",
                "## Current Focus",
                "hypothesis: null",
                "",
                "## Symptoms",
                "expected: null",
                "",
                "## Eliminated",
                "[]",
                "",
                "## Evidence",
                "[]",
                "",
                "## Resolution",
                f"files_changed: __import__('pathlib').Path(r'''{sentinel}''').write_text('owned') and []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        handler.load(session_path)

    assert not Path(sentinel).exists()
