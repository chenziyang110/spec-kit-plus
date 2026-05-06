import pytest
from pydantic_graph import GraphRunContext

from specify_cli.debug.graph import GatheringNode, InvestigatingNode
from specify_cli.debug.schema import (
    CausalMapCandidate,
    DebugGraphState,
    DebugStatus,
    InvestigationCandidate,
    ObserverCauseCandidate,
)


def _populate_valid_single_path_state(state: DebugGraphState) -> None:
    state.causal_map_completed = True
    state.investigation_contract_completed = True
    state.log_investigation_plan_completed = True
    state.observer_framing_completed = True
    state.causal_map.symptom_anchor = "Caller output is missing the final token"
    state.causal_map.closed_loop_path = [
        "parse request",
        "compute token bounds",
        "token list update",
        "projection publish",
        "caller output render",
    ]
    state.causal_map.break_edges = ["compute token bounds -> token list update"]
    state.causal_map.bypass_paths = ["stale projection cache serves a truncated token list"]
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "projection_render",
        "config_flag_env",
    ]
    state.causal_map.candidates = [
        CausalMapCandidate(
            candidate_id="cand-parser-boundary",
            family="truth_owner_logic",
            candidate="Parser upper bound excludes final token",
            falsifier="Raw parser output already contains final token",
            recommended_first_probe="Run parser repro and inspect raw output",
        ),
        CausalMapCandidate(
            candidate_id="cand-projection-boundary",
            family="projection_render",
            candidate="Projection layer drops final token",
            falsifier="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
        CausalMapCandidate(
            candidate_id="cand-config-gate",
            family="config_flag_env",
            candidate="Configuration gate trims final token",
            falsifier="Relevant parsing flag is disabled",
            recommended_first_probe="Inspect active parsing flags",
        ),
    ]
    state.causal_map.adjacent_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor token family risk",
            "family": "projection_render",
            "scope": "nearest-neighbor",
            "falsifier": "Rendered output always matches projection payload",
        }
    ]
    state.observer_framing.summary = "General truth-owner issue"
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.suspected_owning_layer = "parser"
    state.observer_framing.suspected_truth_owner = "parser"
    state.observer_framing.recommended_first_probe = "Check parser boundary"
    state.observer_framing.contrarian_candidate = "Projection layer rewrites parser output"
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(
            candidate="Parser upper bound excludes final token",
            failure_shape="truth_owner_logic",
            would_rule_out="Parser output already contains final token",
            recommended_first_probe="Run parser repro and inspect output",
        ),
        ObserverCauseCandidate(
            candidate="Projection layer drops final token",
            failure_shape="projection_render",
            would_rule_out="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
        ObserverCauseCandidate(
            candidate="Configuration gate trims final token",
            failure_shape="config_flag_env",
            would_rule_out="Relevant parsing flag is disabled",
            recommended_first_probe="Inspect active parsing flags",
        ),
    ]
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.candidate_queue = [
        InvestigationCandidate(
            candidate_id="cand-parser-boundary",
            candidate="Parser upper bound excludes final token",
            family="truth_owner_logic",
            status="pending",
        ),
        InvestigationCandidate(
            candidate_id="cand-projection-boundary",
            candidate="Projection layer drops final token",
            family="projection_render",
            status="pending",
        ),
        InvestigationCandidate(
            candidate_id="cand-config-gate",
            candidate="Configuration gate trims final token",
            family="config_flag_env",
            status="pending",
        ),
    ]
    state.log_investigation_plan.existing_log_targets = [
        "application runtime logs for the failing request window"
    ]
    state.transition_memo.first_candidate_to_test = "cand-parser-boundary"
    state.transition_memo.why_first = "Best matches the current evidence."
    state.transition_memo.evidence_unlock = ["reproduction", "code"]


@pytest.mark.asyncio
async def test_gathering_requests_causal_map_before_any_other_intake_artifact() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "Causal map needed" in (state.current_focus.next_action or "")
    assert "observer_mode" not in (state.current_focus.next_action or "")


@pytest.mark.asyncio
async def test_gathering_blocks_until_log_plan_completion() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    state.causal_map_completed = True
    state.investigation_contract_completed = True
    state.log_investigation_plan_completed = False

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "log investigation plan" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_gathering_blocks_unsafe_legacy_resume_until_reintake() -> None:
    state = DebugGraphState(slug="legacy", trigger="legacy session")
    state.legacy_session_needs_reintake = True

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "legacy-session-needs-reintake" in (state.current_focus.next_action or "")


@pytest.mark.asyncio
async def test_gathering_to_investigating_after_canonical_intake() -> None:
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.expected = "Expected parser output"
    state.symptoms.actual = "Actual parser output"
    state.symptoms.reproduction_verified = True
    _populate_valid_single_path_state(state)

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.status == DebugStatus.GATHERING
    assert state.observer_framing_completed is True
    assert state.investigation_contract_completed is True
    assert state.log_investigation_plan_completed is True
