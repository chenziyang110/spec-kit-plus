from specify_cli.debug.schema import DebugGraphState
from specify_cli.debug.think_agent import (
    build_think_subagent_prompt,
    parse_think_subagent_result,
)


class TestBuildThinkSubagentPrompt:
    def test_build_think_subagent_prompt_requires_family_coverage_output(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="queue badge remains non-zero after slot release",
            diagnostic_profile="scheduler-admission",
        )
        state.symptoms.expected = "queue badge resets to zero"
        state.symptoms.actual = "queue badge remains non-zero"

        prompt = build_think_subagent_prompt(state)

        assert "family_coverage" in prompt
        assert "falsifier" in prompt
        assert "adjacent_risk_targets" in prompt
        assert "closed_loop_path" in prompt

    def test_includes_symptoms_in_prompt(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="queue stuck after slot release",
            diagnostic_profile="scheduler-admission",
        )
        state.symptoms.expected = "queue drains within 100ms"
        state.symptoms.actual = "queue remains non-empty for 30s"
        state.symptoms.errors = "timeout waiting for slot"

        prompt = build_think_subagent_prompt(state)

        assert "queue drains within 100ms" in prompt
        assert "queue remains non-empty for 30s" in prompt
        assert "timeout waiting for slot" in prompt
        assert "scheduler-admission" in prompt

    def test_includes_feature_context_in_prompt(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="stale cache",
            diagnostic_profile="cache-snapshot",
        )
        state.context.feature_id = "FEAT-001"
        state.context.summary = "Cache invalidation for task table"

        prompt = build_think_subagent_prompt(state)

        assert "FEAT-001" in prompt
        assert "Cache invalidation" in prompt

    def test_prompt_contains_output_format_instruction(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="ui not updating",
            diagnostic_profile="ui-projection",
        )

        prompt = build_think_subagent_prompt(state)

        assert "---" in prompt
        assert "observer_mode:" in prompt
        assert "causal_map:" in prompt
        assert "family_coverage:" in prompt
        assert "adjacent_risk_targets:" in prompt

    def test_prompt_marks_hard_constraints(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="general issue",
            diagnostic_profile="general",
        )

        prompt = build_think_subagent_prompt(state)

        assert "Do NOT read source code" in prompt
        assert "Do NOT run commands" in prompt

    def test_prompt_requires_family_and_falsifier_fields(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="queue stuck after slot release",
            diagnostic_profile="scheduler-admission",
        )

        prompt = build_think_subagent_prompt(state)

        assert "family" in prompt
        assert "recommended_first_probe" in prompt
        assert "falsifier" in prompt
        assert "candidate_id" in prompt
        assert "adjacent_risk_targets" in prompt
        assert "break_edges" in prompt
        assert "bypass_paths" in prompt


class TestParseThinkSubagentResult:
    def test_parse_think_subagent_result_extracts_causal_map(self) -> None:
        raw = """Scheduler ownership looks stale after release.

---
observer_mode: "full"
causal_map:
  symptom_anchor: "UI queue badge remains non-zero"
  closed_loop_path:
    - "job release event"
    - "scheduler admission decision"
  family_coverage:
    - "truth_owner_logic"
    - "cache_snapshot"
  candidates:
    - candidate_id: "cand-slot-ownership"
      family: "truth_owner_logic"
      candidate: "Scheduler does not clear slot ownership on release"
      falsifier: "Ownership set is empty before projection refresh"
"""

        data = parse_think_subagent_result(raw)

        assert data["causal_map"]["symptom_anchor"] == "UI queue badge remains non-zero"
        assert data["causal_map"]["family_coverage"] == ["truth_owner_logic", "cache_snapshot"]
        assert data["causal_map"]["candidates"][0]["candidate_id"] == "cand-slot-ownership"

    def test_extracts_observer_framing_from_hybrid_output(self) -> None:
        raw = """The most likely failure is in the scheduler admission loop.

---
observer_framing:
  summary: "Scheduler admission control loop failure"
  primary_suspected_loop: "scheduler-admission"
  suspected_owning_layer: "admission control"
  suspected_truth_owner: "admission control"
  recommended_first_probe: "Verify queue contents before and after"
  missing_questions:
    - "What is the slot release timing?"
alternative_cause_candidates:
  - candidate: "Slot leak in admission handler"
    why_it_fits: "Queue never drains"
    map_evidence: "admission handler owns slot lifecycle"
    would_rule_out: "Slot counter matches expected"
transition_memo:
  first_candidate_to_test: "Slot leak in admission handler"
  why_first: "Best matches outsider framing"
  evidence_unlock:
    - "reproduction"
    - "logs"
  carry_forward_notes:
    - "Keep observer framing"
"""

        result = parse_think_subagent_result(raw)

        assert result["observer_framing"]["summary"] == "Scheduler admission control loop failure"
        assert result["observer_framing"]["primary_suspected_loop"] == "scheduler-admission"
        assert len(result["alternative_cause_candidates"]) == 1
        assert result["alternative_cause_candidates"][0]["candidate"] == "Slot leak in admission handler"
        assert result["transition_memo"]["first_candidate_to_test"] == "Slot leak in admission handler"

    def test_extracts_multiple_candidates(self) -> None:
        raw = """Analysis here.

---
observer_framing:
  summary: "Multiple possible causes"
  primary_suspected_loop: "general"
  suspected_owning_layer: "unknown"
  suspected_truth_owner: "unknown"
  recommended_first_probe: "Check logs"
  missing_questions: []
alternative_cause_candidates:
  - candidate: "Cause A"
    why_it_fits: "Fits A"
    map_evidence: "Evidence A"
    would_rule_out: "Rule out A"
  - candidate: "Cause B"
    why_it_fits: "Fits B"
    map_evidence: "Evidence B"
    would_rule_out: "Rule out B"
  - candidate: "Cause C"
    why_it_fits: "Fits C"
    map_evidence: "Evidence C"
    would_rule_out: "Rule out C"
transition_memo:
  first_candidate_to_test: "Cause A"
  why_first: "Most likely"
  evidence_unlock: ["reproduction"]
  carry_forward_notes: []
"""

        result = parse_think_subagent_result(raw)

        assert len(result["alternative_cause_candidates"]) == 3

    def test_parse_think_subagent_result_extracts_family_candidates(self) -> None:
        raw = """Observer analysis.

---
observer_mode: "full"
causal_map:
  symptom_anchor: "Rendered final token is missing"
  family_coverage:
    - "truth_owner_logic"
    - "projection_render"
  candidates:
    - candidate_id: "cand-parser-boundary"
      family: "truth_owner_logic"
      candidate: "Parser boundary truncates final token"
      falsifier: "Raw parser output contains final token"
    - candidate_id: "cand-projection-boundary"
      family: "projection_render"
      candidate: "Projection boundary drops final token"
      falsifier: "Published payload already lacks final token"
  adjacent_risk_targets:
    - target: "projection-boundary"
      reason: "Nearest-neighbor token family risk"
      family: "projection_render"
      scope: "nearest-neighbor"
"""

        result = parse_think_subagent_result(raw)

        assert result["causal_map"]["candidates"][0]["candidate_id"] == "cand-parser-boundary"
        assert result["causal_map"]["candidates"][0]["family"] == "truth_owner_logic"
        assert result["causal_map"]["adjacent_risk_targets"][0]["target"] == "projection-boundary"

    def test_no_yaml_block_returns_empty_dict(self) -> None:
        raw = "Just some free text without any YAML block."

        result = parse_think_subagent_result(raw)

        assert result == {}
