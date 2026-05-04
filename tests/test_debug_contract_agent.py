from specify_cli.debug.schema import (
    CausalMapCandidate,
    DebugGraphState,
    ExpandedObserverCandidateBoardEntry,
    ExpandedObserverEngineeringScores,
    ExpandedObserverLightScores,
    ExpandedObserverTopCandidate,
    ObserverTopCandidateSummary,
    UserRequestPacketEntry,
)


def test_build_contract_subagent_prompt_includes_causal_map_inputs() -> None:
    from specify_cli.debug.contract_agent import build_contract_subagent_prompt

    state = DebugGraphState(slug="test-session", trigger="queue badge remains non-zero")
    state.observer_expansion_status = "completed"
    state.observer_expansion_reason = "runtime_cross_layer_symptom"
    state.project_runtime_profile = "full-stack/web-app"
    state.symptom_shape = "phenomenon_only"
    state.log_readiness = "user_must_provide_logs"
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
    state.expanded_observer.dimension_scan.truth_owner_or_business_layer = "Scheduler owns slot state"
    state.expanded_observer.candidate_board = [
        ExpandedObserverCandidateBoardEntry(
            candidate_id="cand-slot-ownership",
            dimension_origin="truth_owner_or_business_layer",
            family="truth_owner_logic",
            candidate="Scheduler does not clear slot ownership on release",
            why_it_fits="Queue remains blocked after release",
            indirect_path="Surface success hides stale truth-owner state",
            surface_vs_truth_owner_note="UI symptom is downstream of scheduler state",
            light_scores=ExpandedObserverLightScores(
                likelihood=4,
                impact_radius=4,
                falsifiability=3,
                log_observability=2,
            ),
        )
    ]
    state.expanded_observer.top_candidates = [
        ExpandedObserverTopCandidate(
            candidate_id="cand-slot-ownership",
            family="truth_owner_logic",
            investigation_priority=1,
            recommended_log_probe="Check release and admission logs in the same request window",
            engineering_scores=ExpandedObserverEngineeringScores(
                cross_layer_span=4,
                indirect_causality_risk=4,
                evidence_gap=3,
                investigation_cost=2,
            ),
        )
    ]
    state.observer_framing.top_candidate_summary = ObserverTopCandidateSummary(
        candidate_id="cand-slot-ownership",
        family="truth_owner_logic",
        investigation_priority=1,
        recommended_log_probe="Check release and admission logs in the same request window",
        why_it_fits="Scheduler state owns the truth behind the UI symptom",
    )
    state.expanded_observer.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="application runtime log for the failing request path",
            time_window="The exact failing request window covering release and the next admission",
            keywords_or_fields=[
                "request_id",
                "job_id",
                "ownership clear",
                "admission denied",
            ],
            why_this_matters="This log slice separates stale truth-owner state from projection-only lag.",
            expected_signal_examples=[
                "A release event without a matching ownership-clear event supports the slot-ownership candidate.",
                "A clean ownership-clear event before projection refresh weakens the slot-ownership candidate.",
            ],
        )
    ]

    prompt = build_contract_subagent_prompt(state)

    assert "cand-slot-ownership" in prompt
    assert "contrarian_candidate" in prompt
    assert "candidate_queue" in prompt
    assert "fix_gate_conditions" in prompt
    assert "observer_expansion_status: completed" in prompt
    assert "project_runtime_profile: full-stack/web-app" in prompt
    assert "expanded_observer:" in prompt
    assert "dimension_scan:" in prompt
    assert "log_investigation_plan:" in prompt
    assert "user_request_packet:" in prompt


def test_parse_contract_subagent_result_extracts_investigation_contract() -> None:
    from specify_cli.debug.contract_agent import parse_contract_subagent_result

    raw = """Use slot ownership as the first probe.

---
observer_framing:
  summary: "Queue badge is downstream of slot ownership truth"
  contrarian_candidate: "Projection layer renders stale queue counts"
transition_memo:
  first_candidate_to_test: "cand-slot-ownership"
  why_first: "It decides the shared truth"
  evidence_unlock:
    - "reproduction"
    - "logs"
investigation_contract:
  primary_candidate_id: "cand-slot-ownership"
  investigation_mode: "normal"
  escalation_reason: null
  candidate_queue:
    - candidate_id: "cand-slot-ownership"
      candidate: "Scheduler does not clear slot ownership on release"
      family: "truth_owner_logic"
      status: "pending"
  related_risk_targets:
    - target: "release-retry-loop"
      reason: "Retry admission also depends on slot ownership"
      scope: "nearest-neighbor"
      status: "pending"
"""

    data = parse_contract_subagent_result(raw)

    assert data["investigation_contract"]["primary_candidate_id"] == "cand-slot-ownership"
    assert data["transition_memo"]["first_candidate_to_test"] == "cand-slot-ownership"
    assert data["observer_framing"]["contrarian_candidate"] == "Projection layer renders stale queue counts"


def test_parse_contract_subagent_result_extracts_expanded_observer_contract_fields() -> None:
    from specify_cli.debug.contract_agent import parse_contract_subagent_result

    raw = """Use runtime logs before fixing.

---
observer_framing:
  summary: "Queue badge is downstream of scheduler state"
  primary_suspected_loop: "scheduler-admission"
  suspected_owning_layer: "admission control"
  suspected_truth_owner: "scheduler slot ownership"
  recommended_first_probe: "Check release and admission logs in the same request window"
  contrarian_candidate: "Projection layer renders stale queue counts"
  project_runtime_profile: "full-stack/web-app"
  symptom_shape: "phenomenon_only"
  log_readiness: "user_must_provide_logs"
  top_candidate_summary:
    candidate_id: "cand-slot-ownership"
    family: "truth_owner_logic"
    investigation_priority: 1
    recommended_log_probe: "Check release and admission logs in the same request window"
    why_it_fits: "Scheduler state owns the truth behind the UI symptom"
  surface_truth_owner_distinction: "The UI shows the symptom, but scheduler state owns the truth."
transition_memo:
  first_candidate_to_test: "cand-slot-ownership"
  why_first: "It decides the shared truth"
  evidence_unlock:
    - "existing runtime logs"
    - "request-scoped identifiers"
  carry_forward_notes:
    - "Do not start fixing until logs separate the candidates."
investigation_contract:
  primary_candidate_id: "cand-slot-ownership"
  investigation_mode: "root_cause"
  escalation_reason: "logs_insufficient"
  candidate_queue:
    - candidate_id: "cand-slot-ownership"
      candidate: "Scheduler does not clear slot ownership on release"
      family: "truth_owner_logic"
      status: "pending"
  related_risk_targets:
    - target: "release-retry-loop"
      reason: "Retry admission also depends on slot ownership"
      scope: "nearest-neighbor"
      status: "pending"
  causal_coverage_state:
    competing_candidate_ruled_out: false
    truth_owner_confirmed: false
    boundary_break_localized: false
    related_risk_scan_completed: false
    closeout_ready: false
  top_candidates:
    - candidate_id: "cand-slot-ownership"
      family: "truth_owner_logic"
      investigation_priority: 1
      recommended_log_probe: "Check release and admission logs in the same request window"
      engineering_scores:
        cross_layer_span: 4
        indirect_causality_risk: 4
        evidence_gap: 3
        investigation_cost: 2
  log_investigation_plan:
    existing_log_targets:
      - "application runtime logs for the failing request window"
    candidate_signal_map:
      - candidate_id: "cand-slot-ownership"
        signals:
          - "release recorded without ownership clear"
    log_sufficiency_judgment: "Existing logs are insufficient to separate candidates."
    missing_observability:
      - "No correlated ownership transition logs"
    instrumentation_targets:
      - "slot ownership transition boundaries"
    instrumentation_style:
      - "correlation-scoped before/after state logs"
    user_request_packet:
      - target_source: "application runtime log for the failing request path"
        time_window: "The exact failing request window covering release and the next admission"
        keywords_or_fields:
          - "request_id"
          - "job_id"
          - "ownership clear"
          - "admission denied"
        why_this_matters: "This log slice separates stale truth-owner state from projection-only lag."
        expected_signal_examples:
          - "A release event without a matching ownership-clear event supports the slot-ownership candidate."
          - "A clean ownership-clear event before projection refresh weakens the slot-ownership candidate."
fix_gate_conditions:
  - "Do not begin fixing until existing logs are checked."
  - "Escalate to instrumentation before guessing."
"""

    data = parse_contract_subagent_result(raw)

    assert data["observer_framing"]["project_runtime_profile"] == "full-stack/web-app"
    assert data["observer_framing"]["log_readiness"] == "user_must_provide_logs"
    assert data["observer_framing"]["top_candidate_summary"]["family"] == "truth_owner_logic"
    assert data["investigation_contract"]["escalation_reason"] == "logs_insufficient"
    assert data["investigation_contract"]["top_candidates"][0]["investigation_priority"] == 1
    assert (
        data["investigation_contract"]["log_investigation_plan"]["user_request_packet"][0]["target_source"]
        == "application runtime log for the failing request path"
    )
    assert (
        data["investigation_contract"]["log_investigation_plan"]["user_request_packet"][0]["expected_signal_examples"][0]
        == "A release event without a matching ownership-clear event supports the slot-ownership candidate."
    )
