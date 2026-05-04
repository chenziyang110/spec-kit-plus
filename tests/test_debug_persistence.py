from pathlib import Path

import pytest

from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import (
    CandidateResolution,
    CandidateStatus,
    CausalMapCandidate,
    CausalMapRiskTarget,
    CausalCoverageState,
    DebugGraphState,
    DebugStatus,
    EvidenceEntry,
    ExpandedObserverCandidateBoardEntry,
    ExpandedObserverEngineeringScores,
    ExpandedObserverLightScores,
    ExpandedObserverTopCandidate,
    InvestigationCandidate,
    InvestigationMode,
    LogCandidateSignalMapEntry,
    LogReadiness,
    ObserverCauseCandidate,
    ObserverExpansionStatus,
    OwnershipEntry,
    ProjectRuntimeProfile,
    RelatedRiskStatus,
    RelatedRiskTarget,
    SymptomShape,
    SuggestedEvidenceLane,
    UserRequestPacketEntry,
)


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
    state.observer_mode = "compressed"
    state.observer_framing_completed = True
    state.skip_observer_reason = "user supplied an explicit reproduction command"
    state.observer_framing.summary = "Observer framing points to a parser boundary issue before code inspection."
    state.observer_framing.primary_suspected_loop = "parser-boundary"
    state.observer_framing.suspected_owning_layer = "parser"
    state.observer_framing.suspected_truth_owner = "token boundary logic"
    state.observer_framing.recommended_first_probe = "Verify the parse boundary against the reproduction before reading helper code."
    state.observer_framing.missing_questions = ["Does the final token disappear on every reproduction path?"]
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(
            candidate="parser upper bound excludes final token",
            why_it_fits="The symptom is a missing final token rather than random corruption.",
            map_evidence="Parser owns token boundary truth.",
            would_rule_out="A reproduction showing the parser output already contains the final token.",
        )
    ]
    state.transition_memo.first_candidate_to_test = "parser upper bound excludes final token"
    state.transition_memo.why_first = "Best matches the observer framing and the user report."
    state.transition_memo.evidence_unlock = ["reproduction", "code", "tests"]
    state.transition_memo.carry_forward_notes = ["Treat the parser boundary as the first truth owner to verify."]
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
    state.parent_slug = "parent-session"
    state.child_slugs = ["child-session"]
    state.resume_after_child = True
    state.resolution.files_changed = ["src/specify_cli/debug/graph.py"]
    state.resolution.report = "## Awaiting Human Review\n- Investigate parser boundary"
    state.resolution.decisive_signals = ["runningOrder_=[], waitingQueue_=[task-2], activeCount=1"]
    state.resolution.rejected_surface_fixes = ["normalized UI state without fixing scheduler admission"]
    state.resolution.alternative_hypotheses_considered = [
        "Scheduler kept stale admitted ownership after slot release",
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = [
        "Repro proves the slot is released, the next task is admitted, and the UI matches the running set.",
    ]
    state.execution_intent.outcome = "Verify the current fix against the recorded reproduction"
    state.execution_intent.constraints = [
        "Do not mark resolved without verification evidence",
    ]
    state.execution_intent.success_signals = [
        "reproduction command passes",
        "targeted pytest command passes",
    ]
    state.resolution.validation_results = [
        {
            "command": "python tests/repro.py",
            "status": "passed",
            "output": "PASS",
        }
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.diagnostic_profile == "scheduler-admission"
    assert restored.suggested_evidence_lanes[0].name == "queue-snapshot"
    assert restored.suggested_evidence_lanes[0].focus == "waiting and promotion flow"
    assert restored.current_focus.next_action == "Line 1\nline 2: still same field"
    assert restored.symptoms.reproduction_verified is True
    assert restored.observer_mode == "compressed"
    assert restored.observer_framing_completed is True
    assert restored.skip_observer_reason == "user supplied an explicit reproduction command"
    assert restored.observer_framing.summary == "Observer framing points to a parser boundary issue before code inspection."
    assert restored.observer_framing.primary_suspected_loop == "parser-boundary"
    assert restored.observer_framing.alternative_cause_candidates[0].candidate == "parser upper bound excludes final token"
    assert restored.transition_memo.first_candidate_to_test == "parser upper bound excludes final token"
    assert restored.transition_memo.evidence_unlock == ["reproduction", "code", "tests"]
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
    assert restored.parent_slug == "parent-session"
    assert restored.child_slugs == ["child-session"]
    assert restored.resume_after_child is True
    assert restored.resolution.files_changed == ["src/specify_cli/debug/graph.py"]
    assert restored.resolution.report == "## Awaiting Human Review\n- Investigate parser boundary"
    assert restored.resolution.decisive_signals == ["runningOrder_=[], waitingQueue_=[task-2], activeCount=1"]
    assert restored.resolution.rejected_surface_fixes == [
        "normalized UI state without fixing scheduler admission"
    ]
    assert restored.resolution.alternative_hypotheses_considered == [
        "Scheduler kept stale admitted ownership after slot release",
        "Resource counters or slot accounting are stale",
    ]
    assert restored.resolution.alternative_hypotheses_ruled_out == [
        "Resource counters or slot accounting are stale",
    ]
    assert restored.resolution.root_cause_confidence == "confirmed"
    assert restored.resolution.fix_scope == "truth-owner"
    assert restored.resolution.loop_restoration_proof == [
        "Repro proves the slot is released, the next task is admitted, and the UI matches the running set."
    ]
    assert restored.execution_intent.outcome == "Verify the current fix against the recorded reproduction"
    assert restored.execution_intent.success_signals == [
        "reproduction command passes",
        "targeted pytest command passes",
    ]
    assert restored.resolution.validation_results[0].command == "python tests/repro.py"


def test_persistence_round_trips_lifecycle_hardening_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="human verify loop")
    state.status = DebugStatus.AWAITING_HUMAN
    state.waiting_on_child_human_followup = True
    state.framing_gate_passed = True
    state.resolution.human_verification_outcome = "derived_issue"
    state.resolution.agent_fail_count = 2
    state.resolution.human_reopen_count = 1
    state.observer_framing.contrarian_candidate = "Projection layer drops correct source state"
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(
            candidate="Scheduler ownership state never released correctly",
            failure_shape="truth_owner_logic",
            recommended_first_probe="Inspect scheduler ownership sets before and after slot release",
        )
    ]
    state.candidate_resolutions = [
        CandidateResolution(
            candidate="Scheduler ownership state never released correctly",
            disposition="confirmed",
        )
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.waiting_on_child_human_followup is True
    assert restored.framing_gate_passed is True
    assert restored.resolution.human_verification_outcome == "derived_issue"
    assert restored.resolution.agent_fail_count == 2
    assert restored.resolution.human_reopen_count == 1
    assert restored.observer_framing.contrarian_candidate == "Projection layer drops correct source state"
    assert restored.observer_framing.alternative_cause_candidates[0].failure_shape == "truth_owner_logic"
    assert restored.observer_framing.alternative_cause_candidates[0].recommended_first_probe.startswith(
        "Inspect scheduler ownership sets"
    )
    assert restored.candidate_resolutions[0].disposition == "confirmed"


def test_persistence_round_trips_causal_map_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="queue stuck after slot release")
    state.causal_map_completed = True
    state.causal_map.symptom_anchor = "UI queue badge remains non-zero"
    state.causal_map.closed_loop_path = [
        "job release event",
        "scheduler admission decision",
        "slot ownership update",
        "queue projection refresh",
        "UI queue badge render",
    ]
    state.causal_map.break_edges = [
        "slot ownership update -> queue projection refresh",
    ]
    state.causal_map.bypass_paths = [
        "snapshot cache serves stale queue count after ownership update",
    ]
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
            why_it_fits="Queue stays blocked after release",
            map_evidence="Scheduler owns slot allocation truth",
            falsifier="Ownership set is empty before the UI refresh begins",
            break_edge="scheduler admission decision -> slot ownership update",
            bypass_path="stale ownership cache",
            recommended_first_probe="Inspect ownership set immediately after release",
        )
    ]
    state.causal_map.adjacent_risk_targets = [
        CausalMapRiskTarget(
            target="release-retry-loop",
            reason="Same ownership path governs retry admission",
            family="truth_owner_logic",
            scope="nearest-neighbor",
            falsifier="Retry path bypasses slot ownership state",
        )
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.causal_map_completed is True
    assert restored.causal_map.symptom_anchor == "UI queue badge remains non-zero"
    assert restored.causal_map.closed_loop_path[1] == "scheduler admission decision"
    assert restored.causal_map.candidates[0].candidate_id == "cand-slot-ownership"
    assert restored.causal_map.candidates[0].falsifier == "Ownership set is empty before the UI refresh begins"
    assert restored.causal_map.adjacent_risk_targets[0].target == "release-retry-loop"


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


def test_handoff_report_includes_parent_return_hint(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="child-session",
        trigger="follow-up issue",
        parent_slug="parent-session",
    )

    report = handler.build_handoff_report(state)

    assert "parent-session" in report
    assert "return to the parent session" in report.lower()


def test_handoff_report_includes_split_verification_and_human_outcome(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="human verify loop")
    state.status = DebugStatus.AWAITING_HUMAN
    state.resolution.verification = "success"
    state.resolution.agent_fail_count = 1
    state.resolution.human_reopen_count = 2
    state.resolution.human_verification_outcome = "same_issue"
    state.waiting_on_child_human_followup = True

    report = handler.build_handoff_report(state)

    assert "Agent verification status: success" in report
    assert "Agent verification failures: 1" in report
    assert "Human verification outcome: same_issue" in report
    assert "Human reopen count: 2" in report
    assert "waiting on child human follow-up" in report.lower()


def test_research_checkpoint_is_written_for_repeated_failures(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="looping verification failure", diagnostic_profile="general")
    state.resolution.fail_count = 2
    state.resolution.fix = "Try another parser boundary tweak"
    state.resolution.root_cause = {"summary": "Parser boundary issue"}
    state.observer_expansion_status = ObserverExpansionStatus.SUGGESTED
    state.project_runtime_profile = ProjectRuntimeProfile.WORKER_QUEUE_CRON
    state.log_readiness = LogReadiness.INSUFFICIENT_NEED_INSTRUMENTATION
    state.investigation_contract.log_investigation_plan.existing_log_targets = [
        "worker scheduler logs",
        "queue retry logs",
    ]
    state.investigation_contract.log_investigation_plan.log_sufficiency_judgment = (
        "Current logs do not show whether dequeue and ack are paired."
    )
    state.investigation_contract.log_investigation_plan.instrumentation_targets = [
        "worker ack boundary"
    ]
    state.investigation_contract.log_investigation_plan.user_request_packet = [
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
    assert path.name == "session.research.md"
    assert "# Debug Research: session" in content
    assert "Failed verification attempts: 2" in content
    assert "Try another parser boundary tweak" in content
    assert "Observer expansion status: suggested" in content
    assert "Project runtime profile: worker/queue/cron" in content
    assert "Log readiness: insufficient_need_instrumentation" in content
    assert "Runtime Log Investigation Context" in content
    assert "worker scheduler logs" in content
    assert "worker ack boundary" in content
    assert "worker retry logs for failing job" in content
    assert "Research Questions" in content
    assert "Exit Criteria" in content


def test_persistence_round_trips_evidence_source_metadata(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="log evidence")
    state.evidence.append(
        EvidenceEntry(
            source_type="log",
            source_ref="runtime-test-output.log",
            checked="runtime stderr",
            found="FAIL: parser still drops final token",
            implication="Existing runtime logs already localize the failure before code edits",
        )
    )

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.evidence[0].source_type == "log"
    assert restored.evidence[0].source_ref == "runtime-test-output.log"

def test_persistence_round_trips_investigation_contract_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="candidate-driven debug")
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.investigation_mode = InvestigationMode.ROOT_CAUSE
    state.investigation_contract.escalation_reason = "two verification failures"
    state.investigation_contract.candidate_queue = [
        InvestigationCandidate(
            candidate_id="cand-parser-boundary",
            candidate="Parser boundary truncates final token",
            family="truth_owner_logic",
            status=CandidateStatus.ACTIVE,
            why_it_fits="Final token is consistently missing",
            map_evidence="Parser owns token boundary truth",
            would_rule_out="Raw parser output already includes final token",
            recommended_first_probe="Inspect raw parser output before rendering",
            evidence_needed=["raw parser output", "boundary indices"],
            evidence_found=[],
            related_targets=["projection-boundary", "verification-repro"],
        )
    ]
    state.investigation_contract.related_risk_targets = [
        RelatedRiskTarget(
            target="projection-boundary",
            reason="Same token family may be dropped after publish",
            scope="nearest-neighbor",
            status=RelatedRiskStatus.PENDING,
            evidence=[],
        )
    ]
    state.investigation_contract.causal_coverage_state = CausalCoverageState(
        competing_candidate_ruled_out=False,
        truth_owner_confirmed=True,
        boundary_break_localized=True,
        related_risk_scan_completed=False,
        closeout_ready=False,
    )

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.investigation_contract.primary_candidate_id == "cand-parser-boundary"
    assert restored.investigation_contract.investigation_mode == "root_cause"
    assert restored.investigation_contract.escalation_reason == "two verification failures"
    assert restored.investigation_contract.candidate_queue[0].status == "active"
    assert restored.investigation_contract.related_risk_targets[0].status == "pending"
    assert restored.investigation_contract.causal_coverage_state.closeout_ready is False


def test_persistence_round_trips_expanded_observer_runtime_log_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="runtime log expansion")
    state.observer_expansion_status = ObserverExpansionStatus.COMPLETED
    state.observer_expansion_reason = "runtime_cross_layer_symptom"
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.symptom_shape = SymptomShape.PHENOMENON_ONLY
    state.log_readiness = LogReadiness.USER_MUST_PROVIDE_LOGS
    state.expanded_observer.dimension_scan.symptom_layer = "UI shows stale queue badge after retry"
    state.expanded_observer.dimension_scan.truth_owner_or_business_layer = (
        "Scheduler admission state owns queue truth"
    )
    state.expanded_observer.candidate_board = [
        ExpandedObserverCandidateBoardEntry(
            candidate_id="cand-scheduler-truth-owner",
            dimension_origin="truth_owner_or_business_layer",
            family="truth_owner_logic",
            candidate="Scheduler ownership state never clears after release",
            why_it_fits="Cross-layer symptom persists after worker release",
            indirect_path="release event -> stale ownership -> stale projection",
            surface_vs_truth_owner_note="UI is surface; scheduler is truth owner",
            light_scores=ExpandedObserverLightScores(
                likelihood=5,
                impact_radius=4,
                falsifiability=5,
                log_observability=3,
            ),
        )
    ]
    state.expanded_observer.top_candidates = [
        ExpandedObserverTopCandidate(
            candidate_id="cand-scheduler-truth-owner",
            family="truth_owner_logic",
            investigation_priority=1,
            recommended_log_probe="Correlate release and ownership-clearing logs by request id",
            engineering_scores=ExpandedObserverEngineeringScores(
                cross_layer_span=5,
                indirect_causality_risk=4,
                evidence_gap=3,
                investigation_cost=2,
            ),
        )
    ]
    state.expanded_observer.log_investigation_plan.existing_log_targets = [
        "browser console around retry flow",
        "server application log for release handler",
    ]
    state.expanded_observer.log_investigation_plan.candidate_signal_map = [
        LogCandidateSignalMapEntry(
            candidate_id="cand-scheduler-truth-owner",
            signals=[
                "release request logged without ownership-clear event",
                "projection refresh runs before ownership mutation",
            ],
        )
    ]
    state.expanded_observer.log_investigation_plan.log_sufficiency_judgment = (
        "Current logs miss the ownership-clear transition."
    )
    state.expanded_observer.log_investigation_plan.missing_observability = [
        "No structured field for ownership set size after release"
    ]
    state.expanded_observer.log_investigation_plan.instrumentation_targets = [
        "scheduler.release_slot",
        "queue projection refresh",
    ]
    state.expanded_observer.log_investigation_plan.instrumentation_style = [
        "structured application logs",
        "request-scoped correlation ids",
    ]
    state.expanded_observer.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="server release-handler logs",
            time_window="from retry click through next queue refresh",
            keywords_or_fields=["request_id", "slot_id", "ownership_set_size"],
            why_this_matters="Distinguishes scheduler truth-owner drift from a UI-only projection bug.",
            expected_signal_examples=[
                "If release is logged without ownership_set_size dropping, candidate stays active.",
                "If ownership_set_size drops before refresh, deprioritize scheduler truth-owner drift.",
            ],
        )
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.observer_expansion_status == "completed"
    assert restored.observer_expansion_reason == "runtime_cross_layer_symptom"
    assert restored.project_runtime_profile == "full-stack/web-app"
    assert restored.symptom_shape == "phenomenon_only"
    assert restored.log_readiness == "user_must_provide_logs"
    assert restored.expanded_observer.dimension_scan.symptom_layer == "UI shows stale queue badge after retry"
    assert restored.expanded_observer.candidate_board[0].light_scores.likelihood == 5
    assert restored.expanded_observer.top_candidates[0].engineering_scores.cross_layer_span == 5
    assert restored.expanded_observer.log_investigation_plan.candidate_signal_map[0].signals == [
        "release request logged without ownership-clear event",
        "projection refresh runs before ownership mutation",
    ]
    assert (
        restored.expanded_observer.log_investigation_plan.user_request_packet[0].target_source
        == "server release-handler logs"
    )
    assert (
        restored.expanded_observer.log_investigation_plan.user_request_packet[0].expected_signal_examples[1]
        == "If ownership_set_size drops before refresh, deprioritize scheduler truth-owner drift."
    )


def test_handoff_report_includes_expanded_observer_runtime_log_summary(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="runtime handoff")
    state.observer_expansion_status = ObserverExpansionStatus.ENABLED
    state.observer_expansion_reason = "logs_insufficient"
    state.project_runtime_profile = ProjectRuntimeProfile.BACKEND_API_SERVICE
    state.symptom_shape = SymptomShape.EXACT_ERROR
    state.log_readiness = LogReadiness.INSUFFICIENT_NEED_INSTRUMENTATION
    state.expanded_observer.top_candidates = [
        ExpandedObserverTopCandidate(
            candidate_id="cand-api-cache",
            family="cache_snapshot",
            investigation_priority=1,
            recommended_log_probe="Inspect cache invalidation logs around POST /release",
        )
    ]
    state.expanded_observer.log_investigation_plan.existing_log_targets = [
        "api server logs around POST /release"
    ]
    state.expanded_observer.log_investigation_plan.instrumentation_targets = [
        "cache invalidation branch"
    ]
    state.expanded_observer.log_investigation_plan.log_sufficiency_judgment = (
        "Existing API logs do not reveal whether cache invalidation ran."
    )
    state.expanded_observer.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="production API logs for POST /release",
            time_window="2026-05-05T09:00Z to 2026-05-05T09:10Z",
            keywords_or_fields=["request_id", "cache_key", "invalidated"],
            why_this_matters="Shows whether cache invalidation executed after the release handler.",
            expected_signal_examples=[
                "Missing invalidated=true keeps cache candidate active."
            ],
        )
    ]

    report = handler.build_handoff_report(state)

    assert "Observer expansion status: enabled" in report
    assert "Observer expansion reason: logs_insufficient" in report
    assert "Project runtime profile: backend/api-service" in report
    assert "Symptom shape: exact_error" in report
    assert "Log readiness: insufficient_need_instrumentation" in report
    assert "Expanded Observer" in report
    assert "cand-api-cache" in report
    assert "Inspect cache invalidation logs around POST /release" in report
    assert "Runtime Log Investigation Plan" in report
    assert "api server logs around POST /release" in report
    assert "cache invalidation branch" in report
    assert "User Log Request Packet" in report
    assert "production API logs for POST /release" in report


def test_handoff_report_prefers_investigation_contract_runtime_log_plan(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="contract log handoff")
    state.expanded_observer.log_investigation_plan.existing_log_targets = [
        "stale expanded observer log target"
    ]
    state.expanded_observer.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="stale expanded observer packet",
            time_window="obsolete window",
            keywords_or_fields=["obsolete"],
            why_this_matters="Old observer copy should not drive the active handoff.",
            expected_signal_examples=["ignore this packet"],
        )
    ]
    state.investigation_contract.log_investigation_plan.existing_log_targets = [
        "current investigation log target"
    ]
    state.investigation_contract.log_investigation_plan.candidate_signal_map = [
        LogCandidateSignalMapEntry(
            candidate_id="cand-live-contract",
            signals=["current signal for the active investigation contract"],
        )
    ]
    state.investigation_contract.log_investigation_plan.log_sufficiency_judgment = (
        "Current investigation logs still miss the state transition."
    )
    state.investigation_contract.log_investigation_plan.instrumentation_targets = [
        "current instrumentation target"
    ]
    state.investigation_contract.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="current contract packet",
            time_window="active repro window",
            keywords_or_fields=["request_id", "state_transition"],
            why_this_matters="This is the active log request for the current investigation phase.",
            expected_signal_examples=["transition missing after request_id is logged"],
        )
    ]

    report = handler.build_handoff_report(state)

    assert "Runtime Log Investigation Plan" in report
    assert "current investigation log target" in report
    assert "current signal for the active investigation contract" in report
    assert "Current investigation logs still miss the state transition." in report
    assert "current instrumentation target" in report
    assert "User Log Request Packet" in report
    assert "current contract packet" in report
    assert "active repro window" in report
    assert "request_id, state_transition" in report
    assert "stale expanded observer log target" not in report
    assert "stale expanded observer packet" not in report


def test_persistence_round_trips_investigation_contract_user_log_request_packet(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="contract log packet")
    state.investigation_contract.top_candidates = [
        ExpandedObserverTopCandidate(
            candidate_id="cand-worker-retry",
            family="queue_retry",
            investigation_priority=2,
            recommended_log_probe="Check retry dequeue and ack logs in the same job window",
        )
    ]
    state.investigation_contract.log_investigation_plan.existing_log_targets = [
        "worker retry logs",
        "scheduler ack logs",
    ]
    state.investigation_contract.log_investigation_plan.candidate_signal_map = [
        LogCandidateSignalMapEntry(
            candidate_id="cand-worker-retry",
            signals=["retry logged without ack completion"],
        )
    ]
    state.investigation_contract.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="worker retry command output",
            time_window="single failing retry attempt",
            keywords_or_fields=["job_id", "retry_count", "ack_status"],
            why_this_matters="Separates worker retry loss from scheduler acknowledgment drift.",
            expected_signal_examples=[
                "retry_count increments while ack_status stays pending"
            ],
        )
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.investigation_contract.top_candidates[0].candidate_id == "cand-worker-retry"
    assert restored.investigation_contract.top_candidates[0].recommended_log_probe == (
        "Check retry dequeue and ack logs in the same job window"
    )
    assert restored.investigation_contract.log_investigation_plan.existing_log_targets == [
        "worker retry logs",
        "scheduler ack logs",
    ]
    assert restored.investigation_contract.log_investigation_plan.candidate_signal_map[0].signals == [
        "retry logged without ack completion"
    ]
    assert restored.investigation_contract.log_investigation_plan.user_request_packet[0].keywords_or_fields == [
        "job_id",
        "retry_count",
        "ack_status",
    ]

def test_handoff_report_shows_evidence_source_metadata(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="log evidence")
    state.evidence.append(
        EvidenceEntry(
            source_type="log",
            source_ref="logs/app.log",
            checked="application error log",
            found="scheduler released slot but ownership set stayed populated",
            implication="Log evidence points at scheduler truth-owner drift",
        )
    )

    report = handler.build_handoff_report(state)

    assert "[log]" in report
    assert "logs/app.log" in report


def test_handoff_report_includes_investigation_contract_sections(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="candidate report")
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.investigation_mode = InvestigationMode.ROOT_CAUSE
    state.investigation_contract.candidate_queue = [
        InvestigationCandidate(
            candidate_id="cand-parser-boundary",
            candidate="Parser boundary truncates final token",
            family="truth_owner_logic",
            status=CandidateStatus.ACTIVE,
        )
    ]
    state.investigation_contract.related_risk_targets = [
        RelatedRiskTarget(
            target="projection-boundary",
            reason="Nearest-neighbor token drop risk",
            scope="nearest-neighbor",
            status=RelatedRiskStatus.PENDING,
        )
    ]

    report = handler.build_handoff_report(state)

    assert "Investigation mode: root_cause" in report
    assert "Primary candidate: cand-parser-boundary" in report
    assert "Parser boundary truncates final token" in report
    assert "Related Risk Targets" in report
    assert "projection-boundary" in report

def test_handoff_report_points_to_research_checkpoint_after_repeated_failures(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="looping verification failure")
    state.resolution.fail_count = 2

    report = handler.build_handoff_report(state)

    assert ".planning/debug/session.research.md" in report
    assert "repeated verification failed" in report.lower()


def test_load_resume_target_prefers_parent_awaiting_human_after_child_resolves(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    parent = DebugGraphState(slug="parent-session", trigger="original issue")
    parent.status = DebugStatus.AWAITING_HUMAN
    parent.child_slugs = ["child-session"]
    parent.resume_after_child = True
    handler.save(parent)

    child = DebugGraphState(
        slug="child-session",
        trigger="follow-up issue",
        parent_slug="parent-session",
    )
    child.status = DebugStatus.RESOLVED
    handler.save(child)

    state, reason = handler.load_resume_target()

    assert state is not None
    assert state.slug == "parent-session"
    assert reason == "parent_after_child"


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
