import pytest
from specify_cli.debug.schema import DebugGraphState
from specify_cli.debug.think_agent import (
    build_think_subagent_prompt,
    parse_think_subagent_result,
)


class TestBuildThinkSubagentPrompt:
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
        assert "observer_framing:" in prompt
        assert "alternative_cause_candidates:" in prompt
        assert "transition_memo:" in prompt

    def test_prompt_marks_hard_constraints(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="general issue",
            diagnostic_profile="general",
        )

        prompt = build_think_subagent_prompt(state)

        assert "Do NOT read source code" in prompt
        assert "Do NOT run commands" in prompt


class TestParseThinkSubagentResult:
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

    def test_no_yaml_block_returns_empty_dict(self) -> None:
        raw = "Just some free text without any YAML block."

        result = parse_think_subagent_result(raw)

        assert result == {}
