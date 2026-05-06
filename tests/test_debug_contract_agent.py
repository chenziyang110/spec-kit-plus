from specify_cli.debug.schema import (
    CausalMapCandidate,
    DebugGraphState,
    ExpandedObserverCandidateBoardEntry,
    ExpandedObserverLightScores,
)


def test_build_contract_subagent_prompt_uses_canonical_intake_payload() -> None:
    from specify_cli.debug.contract_agent import build_contract_subagent_prompt

    state = DebugGraphState(slug="test-session", trigger="queue badge remains non-zero")
    state.project_runtime_profile = "full-stack/web-app"
    state.symptom_shape = "phenomenon_only"
    state.log_readiness = "unknown"
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
    prompt = build_contract_subagent_prompt(state)

    assert "cand-slot-ownership" in prompt
    assert "contrarian_candidate" in prompt
    assert "candidate_queue" in prompt
    assert "fix_gate_conditions" in prompt
    assert "project_runtime_profile: full-stack/web-app" in prompt
    assert "candidate_board:" in prompt
    assert "dimension_scan:" in prompt
    assert "log_investigation_plan:" in prompt
    assert "expanded_observer:" not in prompt
    assert "observer_expansion_status" not in prompt


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


def test_parse_contract_subagent_result_extracts_top_level_log_plan() -> None:
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
  investigation_mode: "normal"
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
  top_candidates:
    - candidate_id: "cand-slot-ownership"
      family: "truth_owner_logic"
      investigation_priority: 1
      recommended_log_probe: "Check release and admission logs in the same request window"
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

    assert data["investigation_contract"]["primary_candidate_id"] == "cand-slot-ownership"
    assert data["investigation_contract"]["top_candidates"][0]["investigation_priority"] == 1
    assert data["log_investigation_plan"]["existing_log_targets"][0] == (
        "application runtime logs for the failing request window"
    )
    assert (
        data["log_investigation_plan"]["candidate_signal_map"][0]["signals"][0]
        == "release recorded without ownership clear"
    )
    assert (
        data["log_investigation_plan"]["user_request_packet"][0]["target_source"]
        == "application runtime log for the failing request path"
    )
