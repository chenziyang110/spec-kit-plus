from specify_cli.debug.schema import CausalMapCandidate, DebugGraphState


def test_build_contract_subagent_prompt_includes_causal_map_inputs() -> None:
    from specify_cli.debug.contract_agent import build_contract_subagent_prompt

    state = DebugGraphState(slug="test-session", trigger="queue badge remains non-zero")
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
