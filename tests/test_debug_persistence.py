from pathlib import Path

from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import (
    CausalMapCandidate,
    DebugGraphState,
    DebugStatus,
    EvidenceEntry,
    ExpandedObserverCandidateBoardEntry,
    ExpandedObserverLightScores,
    LogCandidateSignalMapEntry,
    ProjectRuntimeProfile,
    SuggestedEvidenceLane,
    UserRequestPacketEntry,
)


def test_persistence_round_trips_canonical_intake_state(tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="roundtrip")
    state.status = DebugStatus.INVESTIGATING
    state.diagnostic_profile = "scheduler-admission"
    state.causal_map_completed = True
    state.investigation_contract_completed = True
    state.log_investigation_plan_completed = True
    state.observer_framing_completed = True
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.causal_map.symptom_anchor = "UI queue badge remains non-zero"
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.candidates = [
        CausalMapCandidate(
            candidate_id="cand-slot-ownership",
            family="truth_owner_logic",
            candidate="Scheduler does not clear slot ownership on release",
        )
    ]
    state.causal_map.dimension_scan.truth_owner_or_business_layer = "Scheduler slot ownership"
    state.causal_map.candidate_board = [
        ExpandedObserverCandidateBoardEntry(
            candidate_id="cand-slot-ownership",
            dimension_origin="truth_owner_or_business_layer",
            family="truth_owner_logic",
            candidate="Scheduler does not clear slot ownership on release",
            light_scores=ExpandedObserverLightScores(
                likelihood=4,
                impact_radius=4,
                falsifiability=3,
                log_observability=2,
            ),
        )
    ]
    state.log_investigation_plan.existing_log_targets = [
        "application runtime logs for the failing request window"
    ]
    state.log_investigation_plan.candidate_signal_map = [
        LogCandidateSignalMapEntry(
            candidate_id="cand-slot-ownership",
            signals=["release recorded without ownership clear"],
        )
    ]
    state.suggested_evidence_lanes = [
        SuggestedEvidenceLane(
            name="queue-snapshot",
            focus="waiting and promotion flow",
            evidence_to_collect=["queue contents before the decision"],
            join_goal="Decide whether queue state and promotion order are consistent.",
        )
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.investigation_contract_completed is True
    assert restored.log_investigation_plan_completed is True
    assert restored.observer_framing_completed is True
    assert restored.causal_map.dimension_scan.truth_owner_or_business_layer == "Scheduler slot ownership"
    assert restored.causal_map.candidate_board[0].candidate_id == "cand-slot-ownership"
    assert restored.log_investigation_plan.existing_log_targets == [
        "application runtime logs for the failing request window"
    ]
    assert restored.log_investigation_plan.candidate_signal_map[0].signals == [
        "release recorded without ownership clear"
    ]
    assert restored.suggested_evidence_lanes[0].name == "queue-snapshot"


def test_load_normalizes_legacy_expanded_observer_session(tmp_path: Path) -> None:
    session = tmp_path / "legacy.md"
    session.write_text(
        """---
slug: legacy
status: gathering
trigger: "legacy session"
causal_map_completed: true
contract_generation_completed: true
observer_mode: compressed
observer_framing_completed: true
created: "2026-05-06T00:00:00"
updated: "2026-05-06T00:00:00"
---

## Causal Map
symptom_anchor: "UI queue badge remains non-zero"

## Expanded Observer
dimension_scan:
  truth_owner_or_business_layer: "Scheduler slot ownership"
candidate_board:
  - candidate_id: "cand-slot-ownership"
    dimension_origin: "truth_owner_or_business_layer"
    family: "truth_owner_logic"
    candidate: "Scheduler does not clear slot ownership on release"
log_investigation_plan:
  existing_log_targets:
    - "application runtime logs for the failing request window"
""",
        encoding="utf-8",
    )

    restored = MarkdownPersistenceHandler(tmp_path).load(session)

    assert restored.investigation_contract_completed is True
    assert restored.log_investigation_plan_completed is True
    assert restored.legacy_session_needs_reintake is True
    assert restored.causal_map.dimension_scan.truth_owner_or_business_layer == "Scheduler slot ownership"
    assert restored.causal_map.candidate_board[0].candidate_id == "cand-slot-ownership"
    assert restored.log_investigation_plan.existing_log_targets == [
        "application runtime logs for the failing request window"
    ]


def test_handoff_report_uses_canonical_log_plan_surface(tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="handoff")
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.log_investigation_plan.existing_log_targets = [
        "application runtime logs for the failing request window"
    ]
    state.log_investigation_plan.instrumentation_targets = [
        "truth-owner state transition at release and next admission"
    ]
    state.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="application runtime log for the failing request path",
            time_window="The exact failing request window covering release and the next admission",
            keywords_or_fields=["request_id", "job_id"],
            why_this_matters="Separates stale truth-owner state from projection-only lag.",
            expected_signal_examples=[
                "A release event without a matching ownership-clear event supports the slot-ownership candidate."
            ],
        )
    ]

    report = handler.build_handoff_report(state)

    assert "Runtime Log Investigation Plan" in report
    assert "application runtime logs for the failing request window" in report
    assert "application runtime log for the failing request path" in report
    assert "truth-owner state transition at release and next admission" in report
    assert "Expanded Observer" not in report


def test_research_checkpoint_prefers_top_level_log_plan(tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="looping verification failure")
    state.resolution.fail_count = 2
    state.project_runtime_profile = ProjectRuntimeProfile.WORKER_QUEUE_CRON
    state.log_investigation_plan.existing_log_targets = [
        "worker scheduler logs",
        "queue retry logs",
    ]
    state.log_investigation_plan.log_sufficiency_judgment = (
        "Current logs do not show whether dequeue and ack are paired."
    )
    state.log_investigation_plan.instrumentation_targets = [
        "worker ack boundary"
    ]
    state.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="worker retry logs for failing job",
            time_window="single retry window",
            keywords_or_fields=["job_id", "retry_count", "ack_status"],
            why_this_matters="Separates retry churn from missing ack completion.",
            expected_signal_examples=[
                "retry_count increments while ack_status remains pending"
            ],
        )
    ]
    state.evidence.append(
        EvidenceEntry(
            checked="python tests/repro.py",
            found="FAIL: parser still drops final token",
            implication="Current fix did not restore the closed loop",
        )
    )

    path = handler.save_research_checkpoint(state)
    content = path.read_text(encoding="utf-8")

    assert "Runtime Log Investigation Context" in content
    assert "worker scheduler logs" in content
    assert "worker ack boundary" in content
    assert "worker retry logs for failing job" in content
