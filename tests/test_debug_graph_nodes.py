import pytest
import sys
import asyncio
from pydantic_graph import GraphRunContext
from specify_cli.debug.schema import (
    CausalMapCandidate,
    DebugGraphState,
    DebugStatus,
    EliminatedEntry,
    EvidenceEntry,
    UserRequestPacketEntry,
    LogReadiness,
    ObserverCauseCandidate,
    ObserverExpansionStatus,
    ProjectRuntimeProfile,
    SymptomShape,
)
from specify_cli.debug.graph import (
    AwaitingHumanNode,
    FixingNode,
    GatheringNode,
    InvestigatingNode,
    VerifyingNode,
    run_debug_session,
)
from specify_cli.debug.persistence import MarkdownPersistenceHandler


def _populate_valid_observer_framing(state: DebugGraphState, *, mode: str = "full") -> None:
    state.causal_map_completed = True
    state.contract_generation_completed = True
    state.observer_framing_completed = True
    state.observer_mode = mode
    if mode == "compressed":
        state.skip_observer_reason = "Strong low-level evidence present"
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
    state.causal_map.family_coverage = ["truth_owner_logic", "projection_render"]
    state.causal_map.candidates = [
        CausalMapCandidate(
            candidate_id="cand-parser-boundary",
            family="truth_owner_logic",
            candidate="Parser upper bound excludes final token",
            falsifier="Raw parser output already contains the final token",
            recommended_first_probe="Run parser repro and inspect raw output",
        ),
        CausalMapCandidate(
            candidate_id="cand-projection-boundary",
            family="projection_render",
            candidate="Projection layer drops final token",
            falsifier="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
    ]
    if mode != "compressed":
        state.causal_map.family_coverage.append("config_flag_env")
        state.causal_map.candidates.append(
            CausalMapCandidate(
                candidate_id="cand-config-gate",
                family="config_flag_env",
                candidate="Configuration gate trims final token",
                falsifier="Relevant parsing flag is disabled",
                recommended_first_probe="Inspect active parsing flags",
            )
        )
    state.causal_map.adjacent_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor risk for missing final token",
            "family": "projection_render",
            "scope": "nearest-neighbor",
            "falsifier": "Rendered output always matches projection payload",
        }
    ]
    state.observer_framing.summary = "Observer framing identifies a bounded control-plane issue."
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.suspected_owning_layer = "parser"
    state.observer_framing.suspected_truth_owner = "parser"
    state.observer_framing.recommended_first_probe = "Check parser boundary against output."
    state.observer_framing.contrarian_candidate = "Projection layer rewrites correct parser output"
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(
            candidate="Parser upper bound excludes final token",
            failure_shape="truth_owner_logic",
            would_rule_out="Parser output already contains final token",
            recommended_first_probe="Run parser repro and inspect raw output",
        ),
        ObserverCauseCandidate(
            candidate="Projection layer drops final token",
            failure_shape="projection_render",
            would_rule_out="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
    ]
    if mode != "compressed":
        state.observer_framing.alternative_cause_candidates.append(
            ObserverCauseCandidate(
                candidate="Configuration gate trims final token",
                failure_shape="config_flag_env",
                would_rule_out="Relevant parsing flag is disabled",
                recommended_first_probe="Inspect active parsing flags",
            )
        )
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-parser-boundary",
            "candidate": "Parser upper bound excludes final token",
            "family": "truth_owner_logic",
            "status": "pending",
        },
        {
            "candidate_id": "cand-projection-boundary",
            "candidate": "Projection layer drops final token",
            "family": "projection_render",
            "status": "pending",
        },
    ]
    if mode != "compressed":
        state.investigation_contract.candidate_queue.append(
            {
                "candidate_id": "cand-config-gate",
                "candidate": "Configuration gate trims final token",
                "family": "config_flag_env",
                "status": "pending",
            }
        )
    state.transition_memo.first_candidate_to_test = "cand-parser-boundary"
    state.transition_memo.why_first = "Best matches the outsider framing."
    state.transition_memo.evidence_unlock = ["reproduction", "code"]

@pytest.mark.asyncio
async def test_gathering_node_missing_symptoms():
    state = DebugGraphState(slug="test", trigger="test")
    _populate_valid_observer_framing(state)
    # symptoms are empty by default
    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert result.data == "Awaiting more debugging input"
    assert state.status == DebugStatus.GATHERING
    assert state.context is not None
    assert "expected and actual behavior" in (state.current_focus.next_action or "").lower()

@pytest.mark.asyncio
async def test_gathering_node_with_symptoms_not_verified():
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.expected = "Something should happen"
    state.symptoms.actual = "Something else happened"
    _populate_valid_observer_framing(state)

    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    # move to InvestigatingNode ONLY if reproduction_verified is True
    assert result.data == "Awaiting more debugging input"
    assert "Reproduction not verified" in state.current_focus.next_action

@pytest.mark.asyncio
async def test_gathering_node_with_verified_reproduction():
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.expected = "Something should happen"
    state.symptoms.actual = "Something else happened"
    state.symptoms.reproduction = "tests/repro.py"
    state.symptoms.reproduction_verified = True
    _populate_valid_observer_framing(state)

    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, InvestigatingNode)


@pytest.mark.asyncio
async def test_gathering_blocks_until_dual_observer_is_complete() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    state.causal_map_completed = True
    state.contract_generation_completed = False
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

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert state.observer_framing_completed is False
    assert state.contract_subagent_prompt is not None

@pytest.mark.asyncio
async def test_investigating_node_prioritization():
    state = DebugGraphState(slug="test", trigger="test")
    state.recently_modified = ["src/buggy.py", "tests/test_bug.py"]
    
    node = InvestigatingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert result.data == "Awaiting more debugging input"
    assert "Prioritizing files from recent history" in state.current_focus.next_action
    assert "src/buggy.py" in state.current_focus.next_action


@pytest.mark.asyncio
async def test_graph_refreshes_diagnostic_profile_from_symptoms():
    state = DebugGraphState(slug="test", trigger="stale snapshot shows old task state")
    state.symptoms.expected = "Fresh task state visible"
    state.symptoms.actual = "Stale snapshot cache remains visible"
    state.symptoms.reproduction_verified = True
    _populate_valid_observer_framing(state)

    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.diagnostic_profile == "cache-snapshot"
    assert state.suggested_evidence_lanes[0].name == "authoritative-state-trace"

@pytest.mark.asyncio
async def test_investigating_node_elimination():
    state = DebugGraphState(slug="test", trigger="test")
    state.current_focus.hypothesis = "Database is down"
    state.current_focus.next_action = "Eliminate: DB is actually up, checked via ping."
    
    node = InvestigatingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert result.data == "Awaiting more debugging input"
    assert len(state.eliminated) == 1
    assert state.eliminated[0].hypothesis == "Database is down"
    assert "DB is actually up" in state.eliminated[0].evidence
    # Focus should be reset
    assert state.current_focus.hypothesis is None
    assert state.current_focus.next_action is None

@pytest.mark.asyncio
async def test_investigating_node_finds_root_cause():
    state = DebugGraphState(slug="test", trigger="test")
    state.log_readiness = LogReadiness.SUFFICIENT_EXISTING_LOGS
    state.resolution.root_cause = {
        "summary": "Parser upper bound excludes the final token",
        "owning_layer": "parser",
        "broken_control_state": "token boundary decisions",
        "failure_mechanism": "upper bound truncates the last token during slicing",
        "loop_break": "control decision -> state transition",
        "decisive_signal": "upper bound excludes final token while caller only sees missing output",
    }
    state.truth_ownership = [{"layer": "parser", "owns": "token boundary decisions"}]
    state.control_state = ["token index", "upper bound"]
    state.observation_state = ["rendered token stream"]
    state.closed_loop.input_event = "parse request"
    state.closed_loop.control_decision = "compute token bounds"
    state.closed_loop.resource_allocation = "assign final token slice"
    state.closed_loop.state_transition = "token included in parse result"
    state.closed_loop.external_observation = "caller sees full token list"
    state.closed_loop.break_point = "upper bound truncates token"
    state.resolution.decisive_signals = ["upper bound excludes final token while UI only shows missing output"]
    state.resolution.alternative_hypotheses_considered = [
        "Parser upper bound excludes final token",
        "Projection layer drops the final token",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Projection layer drops the final token",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-parser-boundary",
            "candidate": "Parser upper bound excludes the final token",
            "family": "truth_owner_logic",
            "status": "confirmed",
        },
        {
            "candidate_id": "cand-projection-boundary",
            "candidate": "Projection layer drops the final token",
            "family": "projection_render",
            "status": "ruled_out",
        },
    ]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor risk for published token output",
            "scope": "nearest-neighbor",
            "status": "checked",
        }
    ]
    
    node = InvestigatingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, FixingNode)

@pytest.mark.asyncio
async def test_fixing_node_no_fix():
    state = DebugGraphState(slug="test", trigger="test")
    state.resolution.root_cause = {
        "summary": "Parser upper bound excludes the final token",
        "owning_layer": "parser",
        "broken_control_state": "token boundary decisions",
        "failure_mechanism": "upper bound truncates the last token during slicing",
        "loop_break": "control decision -> state transition",
        "decisive_signal": "upper bound excludes final token while caller only sees missing output",
    }
    state.truth_ownership = [{"layer": "parser", "owns": "token boundary decisions"}]
    state.control_state = ["token index", "upper bound"]
    state.observation_state = ["rendered token stream"]
    state.closed_loop.input_event = "parse request"
    state.closed_loop.control_decision = "compute token bounds"
    state.closed_loop.resource_allocation = "assign final token slice"
    state.closed_loop.state_transition = "token included in parse result"
    state.closed_loop.external_observation = "caller sees full token list"
    state.closed_loop.break_point = "upper bound truncates token"
    state.resolution.decisive_signals = ["upper bound excludes final token while UI only shows missing output"]
    state.resolution.alternative_hypotheses_considered = [
        "Parser upper bound excludes final token",
        "Projection layer drops the final token",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Projection layer drops the final token",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    
    node = FixingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert result.data == "Awaiting more debugging input"
    assert "Please propose a fix" in state.current_focus.next_action

@pytest.mark.asyncio
async def test_fixing_node_with_fix():
    state = DebugGraphState(slug="test", trigger="test")
    state.log_readiness = LogReadiness.SUFFICIENT_EXISTING_LOGS
    state.resolution.root_cause = {
        "summary": "Parser upper bound excludes the final token",
        "owning_layer": "parser",
        "broken_control_state": "token boundary decisions",
        "failure_mechanism": "upper bound truncates the last token during slicing",
        "loop_break": "control decision -> state transition",
        "decisive_signal": "upper bound excludes final token while caller only sees missing output",
    }
    state.truth_ownership = [{"layer": "parser", "owns": "token boundary decisions"}]
    state.control_state = ["token index", "upper bound"]
    state.observation_state = ["rendered token stream"]
    state.closed_loop.input_event = "parse request"
    state.closed_loop.control_decision = "compute token bounds"
    state.closed_loop.resource_allocation = "assign final token slice"
    state.closed_loop.state_transition = "token included in parse result"
    state.closed_loop.external_observation = "caller sees full token list"
    state.closed_loop.break_point = "upper bound truncates token"
    state.resolution.decisive_signals = ["upper bound excludes final token while UI only shows missing output"]
    state.resolution.alternative_hypotheses_considered = [
        "Parser upper bound excludes final token",
        "Projection layer drops the final token",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Projection layer drops the final token",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Update line 42 to fix the typo"
    state.resolution.fix_scope = "truth-owner"
    
    node = FixingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, VerifyingNode)


@pytest.mark.asyncio
async def test_fixing_blocks_until_contrarian_candidate_is_resolved() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.log_readiness = LogReadiness.SUFFICIENT_EXISTING_LOGS
    state.resolution.root_cause = {
        "summary": "Scheduler does not clear slot ownership on release",
        "owning_layer": "scheduler",
        "broken_control_state": "slot ownership set",
        "failure_mechanism": "release path leaves ownership set dirty",
        "loop_break": "truth owner update -> projection refresh",
        "decisive_signal": "ownership set remains non-empty after release",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "slot ownership set"}]
    state.control_state = ["slot ownership set"]
    state.observation_state = ["queue badge"]
    state.closed_loop.input_event = "slot release"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "queued task becomes admitted"
    state.closed_loop.external_observation = "queue badge resets"
    state.closed_loop.break_point = "truth owner update -> projection refresh"
    state.resolution.decisive_signals = ["ownership set remains non-empty after release"]
    state.resolution.alternative_hypotheses_considered = [
        "Scheduler does not clear slot ownership on release",
        "Projection layer renders stale queue counts",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Projection layer renders stale queue counts",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.investigation_contract.primary_candidate_id = "cand-slot-ownership"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-slot-ownership",
            "candidate": "Scheduler does not clear slot ownership on release",
            "family": "truth_owner_logic",
            "status": "confirmed",
        },
        {
            "candidate_id": "cand-stale-projection",
            "candidate": "Projection layer renders stale queue counts",
            "family": "projection_render",
            "status": "pending",
        },
    ]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "release-retry-loop",
            "reason": "Retry admission also depends on slot ownership",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]

    result = await InvestigatingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "competing candidate" in (state.current_focus.next_action or "").lower()

@pytest.mark.asyncio
async def test_verifying_node_success(monkeypatch):
    # Mock run_command to always succeed
    calls = []
    def mock_run(cmd):
        calls.append(cmd)
        return "PASS"
    
    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)
    
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph_nodes.py"]
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = [
        "Repro proves the final token survives parse and reaches the caller output.",
    ]
    
    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, AwaitingHumanNode)
    assert state.resolution.verification == "success"
    # Should call run_command twice (reproduction + feature tests)
    assert len(calls) == 2
    assert "python tests/repro.py" in calls[0]
    assert "pytest tests/test_debug_graph_nodes.py" in calls[1]

@pytest.mark.asyncio
async def test_verifying_node_failure(monkeypatch):
    # Mock run_command to fail on the second call (feature tests)
    calls = []
    def mock_run(cmd):
        calls.append(cmd)
        if len(calls) == 1:
            return "PASS"
        return "FAIL"
    
    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)
    
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.feature_id = "src/specify_cli/debug"
    state.resolution.fail_count = 0
    
    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, InvestigatingNode)
    assert state.resolution.verification == "failed"
    assert state.resolution.fail_count == 1
    assert len(calls) == 2
    assert "python tests/repro.py" in state.evidence[-1].checked or "pytest" in state.evidence[-1].checked

@pytest.mark.asyncio
async def test_verifying_node_uses_changed_test_files(monkeypatch):
    calls = []

    def mock_run(cmd):
        calls.append(cmd)
        return "PASS"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.files_changed = [
        "src/specify_cli/debug/graph.py",
        "tests/test_debug_cli.py",
    ]
    state.resolution.fix = "Release stale parser ownership before projection"
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = [
        "Targeted pytest and repro both prove the final token reaches the caller output.",
    ]

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, AwaitingHumanNode)
    assert calls == ["python tests/repro.py", "pytest tests/test_debug_cli.py"]

@pytest.mark.asyncio
async def test_verifying_node_falls_back_to_project_tests(monkeypatch):
    calls = []

    def mock_run(cmd):
        calls.append(cmd)
        return "PASS"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.feature_id = "002-autonomous-execution"
    state.resolution.fix = "Release stale scheduler ownership before promotion"
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = [
        "Repro and project-level tests prove the next queued task is admitted and observed correctly.",
    ]

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, AwaitingHumanNode)
    assert calls == ["python tests/repro.py", "pytest tests"]

@pytest.mark.asyncio
async def test_verifying_node_triggers_safety_gate_after_third_failure(monkeypatch):
    def mock_run(_cmd):
        return "FAIL"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.files_changed = ["tests/test_debug_graph_nodes.py"]
    state.resolution.fail_count = 2

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, AwaitingHumanNode)
    assert state.resolution.verification == "failed"
    assert state.resolution.fail_count == 3


@pytest.mark.asyncio
async def test_investigating_node_blocks_fixing_without_required_framing():
    state = DebugGraphState(slug="test", trigger="test")
    state.resolution.root_cause = {"summary": "Typo in line 42"}

    node = InvestigatingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "fixing is blocked" in (state.current_focus.next_action or "").lower()
    assert "truth ownership map" in (state.current_focus.next_action or "").lower()
    assert "decisive signals" in (state.current_focus.next_action or "").lower()
    assert "- [ ] truth ownership map" in (state.current_focus.next_action or "").lower()
    assert "fill in the missing items below before advancing" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_fixing_node_blocks_without_required_framing():
    state = DebugGraphState(slug="test", trigger="test")
    state.resolution.fix = "Update line 42 to fix the typo"

    node = FixingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "fixing is blocked" in (state.current_focus.next_action or "").lower()
    assert "confirmed root cause" in (state.current_focus.next_action or "").lower()
    assert "- [ ] confirmed root cause" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_investigating_node_generates_user_log_request_packet_when_runtime_logs_are_inaccessible():
    state = DebugGraphState(slug="runtime-logs", trigger="Order status stays stale after retry in production")
    state.symptoms.expected = "Status becomes completed after retry succeeds"
    state.symptoms.actual = "UI still shows processing and agent cannot access production logs directly"
    state.symptoms.reproduction_verified = True
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.symptom_shape = SymptomShape.PHENOMENON_ONLY
    state.observer_expansion_status = ObserverExpansionStatus.SUGGESTED
    state.log_readiness = LogReadiness.USER_MUST_PROVIDE_LOGS
    state.investigation_contract.top_candidates = [
        {
            "candidate_id": "cand-publish-boundary",
            "family": "publish_boundary",
            "investigation_priority": 1,
            "recommended_log_probe": "Server request logs around the retry request and browser console/network logs",
        }
    ]

    result = await InvestigatingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert state.expanded_observer.log_investigation_plan.user_request_packet
    packet = state.expanded_observer.log_investigation_plan.user_request_packet[0]
    assert "log" in packet.target_source.lower() or "console" in packet.target_source.lower()
    assert packet.time_window
    assert packet.keywords_or_fields
    assert "candidate" in packet.why_this_matters.lower() or "distinguish" in packet.why_this_matters.lower()
    assert packet.expected_signal_examples


@pytest.mark.asyncio
async def test_investigating_node_preserves_existing_contract_user_log_request_packet():
    state = DebugGraphState(slug="runtime-logs-existing-contract", trigger="Order status stays stale after retry in production")
    state.symptoms.expected = "Status becomes completed after retry succeeds"
    state.symptoms.actual = "UI still shows processing and agent cannot access production logs directly"
    state.symptoms.reproduction_verified = True
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.symptom_shape = SymptomShape.PHENOMENON_ONLY
    state.observer_expansion_status = ObserverExpansionStatus.ENABLED
    state.log_readiness = LogReadiness.USER_MUST_PROVIDE_LOGS
    state.investigation_contract.top_candidates = [
        {
            "candidate_id": "cand-publish-boundary",
            "family": "publish_boundary",
            "investigation_priority": 1,
            "recommended_log_probe": "Use the tailored contract probe",
        }
    ]
    state.investigation_contract.log_investigation_plan.user_request_packet = [
        UserRequestPacketEntry(
            target_source="tailored contract packet",
            time_window="contract window",
            keywords_or_fields=["request_id"],
            why_this_matters="Tailored contract packet should win.",
            expected_signal_examples=["tailored contract signal"],
        )
    ]

    result = await InvestigatingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert (
        state.investigation_contract.log_investigation_plan.user_request_packet[0].target_source
        == "tailored contract packet"
    )
    assert not state.expanded_observer.log_investigation_plan.user_request_packet


@pytest.mark.asyncio
async def test_fixing_node_blocks_runtime_bug_when_log_readiness_is_insufficient():
    state = DebugGraphState(slug="runtime-fix-gate", trigger="Queue item stays visible after completion")
    state.project_runtime_profile = ProjectRuntimeProfile.WORKER_QUEUE_CRON
    state.symptom_shape = SymptomShape.PHENOMENON_ONLY
    state.log_readiness = LogReadiness.INSUFFICIENT_NEED_INSTRUMENTATION
    state.resolution.root_cause = {
        "summary": "Worker completion path likely misses dequeue publish event",
        "owning_layer": "queue worker",
        "broken_control_state": "job completion publish signal",
        "failure_mechanism": "completed jobs may not emit the dequeue event that clears projections",
        "loop_break": "state transition -> external observation",
        "decisive_signal": "projection sometimes remains stale after completion",
    }
    state.truth_ownership = [{"layer": "queue worker", "owns": "job completion publish signal"}]
    state.control_state = ["job completion publish signal"]
    state.observation_state = ["queue projection"]
    state.closed_loop.input_event = "job completion"
    state.closed_loop.control_decision = "emit dequeue publish event"
    state.closed_loop.resource_allocation = "mark worker slot complete"
    state.closed_loop.state_transition = "queue projection clears completed item"
    state.closed_loop.external_observation = "completed item disappears from queue UI"
    state.closed_loop.break_point = "publish event may be missing"
    state.resolution.decisive_signals = ["projection sometimes remains stale after completion"]
    state.resolution.alternative_hypotheses_considered = [
        "Worker completion path misses dequeue publish event",
        "Projection refresh is delayed but publish event exists",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Projection refresh is delayed but publish event exists",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Force projection clear unconditionally on completion"
    state.resolution.fix_scope = "truth-owner"

    result = await FixingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "log readiness" in (state.current_focus.next_action or "").lower()
    assert "instrumentation" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_fixing_node_blocks_runtime_bug_when_log_readiness_is_unknown():
    state = DebugGraphState(slug="runtime-log-unknown", trigger="Order state remains stale after a runtime retry")
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.symptom_shape = SymptomShape.PHENOMENON_ONLY
    state.log_readiness = LogReadiness.UNKNOWN
    state.resolution.root_cause = {
        "summary": "Retry completion may not reach the publish boundary",
        "owning_layer": "retry publish boundary",
        "broken_control_state": "published order state",
        "failure_mechanism": "publish path may not emit the completion update",
        "loop_break": "state transition -> external observation",
        "decisive_signal": "order state remains stale after retry completion",
    }
    state.truth_ownership = [{"layer": "retry publish boundary", "owns": "published order state"}]
    state.control_state = ["published order state"]
    state.observation_state = ["order status badge"]
    state.closed_loop.input_event = "retry completion"
    state.closed_loop.control_decision = "publish completed state"
    state.closed_loop.resource_allocation = "mark retry workflow complete"
    state.closed_loop.state_transition = "order status badge refreshes"
    state.closed_loop.external_observation = "user sees completed"
    state.closed_loop.break_point = "publish may not carry the completed state"
    state.resolution.decisive_signals = ["order state remains stale after retry completion"]
    state.resolution.alternative_hypotheses_considered = [
        "Retry completion may not reach the publish boundary",
        "Badge polls stale cache data",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Badge polls stale cache data",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Force a completed-state republish after retry"
    state.resolution.fix_scope = "truth-owner"

    result = await FixingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "log readiness" in (state.current_focus.next_action or "").lower()
    assert "existing logs" in (state.current_focus.next_action or "").lower() or "assess" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_fixing_node_blocks_runtime_bug_when_log_readiness_is_unset():
    state = DebugGraphState(slug="runtime-log-unset", trigger="Queue projection remains stale after job completion")
    state.project_runtime_profile = ProjectRuntimeProfile.WORKER_QUEUE_CRON
    state.symptom_shape = SymptomShape.PHENOMENON_ONLY
    state.resolution.root_cause = {
        "summary": "Queue-clear signal may not be emitted after completion",
        "owning_layer": "queue worker",
        "broken_control_state": "queue-clear signal",
        "failure_mechanism": "completion path may skip the clear signal entirely",
        "loop_break": "state transition -> external observation",
        "decisive_signal": "completed item remains visible in queue projection",
    }
    state.truth_ownership = [{"layer": "queue worker", "owns": "queue-clear signal"}]
    state.control_state = ["queue-clear signal"]
    state.observation_state = ["queue projection"]
    state.closed_loop.input_event = "job completion"
    state.closed_loop.control_decision = "emit queue-clear signal"
    state.closed_loop.resource_allocation = "release worker slot"
    state.closed_loop.state_transition = "queue projection clears completed item"
    state.closed_loop.external_observation = "queue UI removes the completed item"
    state.closed_loop.break_point = "clear signal may be absent"
    state.resolution.decisive_signals = ["completed item remains visible in queue projection"]
    state.resolution.alternative_hypotheses_considered = [
        "Queue-clear signal may not be emitted after completion",
        "Projection refresh applies too late",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Projection refresh applies too late",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Always emit queue-clear signal on completion"
    state.resolution.fix_scope = "truth-owner"

    result = await FixingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "log readiness" in (state.current_focus.next_action or "").lower()
    assert "assess" in (state.current_focus.next_action or "").lower() or "existing logs" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_fixing_node_blocks_surface_only_fix_scope():
    state = DebugGraphState(slug="test", trigger="test")
    state.log_readiness = LogReadiness.SUFFICIENT_EXISTING_LOGS
    state.resolution.root_cause = {
        "summary": "Projection layer drops the final token",
        "owning_layer": "projection boundary",
        "broken_control_state": "published token view-model",
        "failure_mechanism": "final token is stripped after publish",
        "loop_break": "state transition -> external observation",
        "decisive_signal": "source tokens are correct but projected output drops the last entry",
    }
    state.truth_ownership = [{"layer": "projection boundary", "owns": "published token view-model"}]
    state.control_state = ["published token view-model"]
    state.observation_state = ["rendered token stream"]
    state.closed_loop.input_event = "parse request"
    state.closed_loop.control_decision = "publish token list"
    state.closed_loop.resource_allocation = "assign published token payload"
    state.closed_loop.state_transition = "view-model receives final token"
    state.closed_loop.external_observation = "caller sees full token list"
    state.closed_loop.break_point = "projection strips final token"
    state.resolution.decisive_signals = ["source tokens are correct but projection drops the last entry"]
    state.resolution.alternative_hypotheses_considered = [
        "Projection layer drops the final token",
        "Parser upper bound excludes final token",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Parser upper bound excludes final token",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Normalize display status and hide the missing final token"
    state.resolution.fix_scope = "surface-only"

    node = FixingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "surface-only" in (state.current_focus.next_action or "").lower()
    assert "cannot satisfy the debug contract" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_verifying_node_success_requires_loop_restoration_proof(monkeypatch):
    def mock_run(cmd):
        return "PASS"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph_nodes.py"]
    state.resolution.fix_scope = "truth-owner"

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "loop restoration proof" in (state.current_focus.next_action or "").lower()
    assert "resolved" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_verifying_node_second_failure_demands_diagnostic_escalation(monkeypatch):
    def mock_run(_cmd):
        return "FAIL"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize display status"
    state.resolution.fail_count = 1

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.resolution.fail_count == 2
    assert "decisive instrumentation" in (state.current_focus.next_action or "").lower()
    assert "control plane" in (state.current_focus.next_action or "").lower()
    assert "detected profile: ui projection" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture ownership sets at the decision layer" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture source-of-truth state at publish time" in (state.current_focus.next_action or "").lower()
    assert "Normalize display status" in state.resolution.rejected_surface_fixes


@pytest.mark.asyncio
async def test_verifying_second_failure_switches_to_root_cause_mode(monkeypatch):
    import specify_cli.debug.graph as graph_module

    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "FAIL")

    state = DebugGraphState(slug="test-session", trigger="hard bug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize display status"
    state.resolution.fail_count = 1
    state.investigation_contract.investigation_mode = "normal"

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.investigation_contract.investigation_mode.value == "root_cause"
    assert state.investigation_contract.escalation_reason == "two verification failures"


@pytest.mark.asyncio
async def test_cache_snapshot_profile_gets_targeted_diagnostic_checklist(monkeypatch):
    def mock_run(_cmd):
        return "FAIL"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test", trigger="stale snapshot keeps old state visible")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.symptoms.actual = "Polling returns stale cached task table"
    state.resolution.fix = "Refresh cache on publish"
    state.resolution.fail_count = 1
    state.observation_state = ["snapshot cache", "task table"]

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert "detected profile: cache/snapshot drift" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture the authoritative control state and the cached/snapshot state side by side" in (state.current_focus.next_action or "").lower()
    assert "- [ ] trace any cache invalidation or refresh path" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_verifying_blocks_closeout_until_related_risk_scan_completes(monkeypatch):
    import specify_cli.debug.graph as graph_module

    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "PASS")

    state = DebugGraphState(slug="test-session", trigger="hard bug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph_nodes.py"]
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = ["Loop restored end-to-end"]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor risk",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]
    state.investigation_contract.causal_coverage_state.related_risk_scan_completed = False

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "related risk" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_verifying_blocks_until_adjacent_risk_target_checked(monkeypatch) -> None:
    import specify_cli.debug.graph as graph_module

    monkeypatch.setattr(graph_module, "run_verification_commands", lambda commands, runner, stop_on_failure: [])
    monkeypatch.setattr(graph_module, "verification_passed", lambda results: True)

    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.reproduction_command = "pytest tests/test_debug_graph.py::test_gathering_to_investigating -q"
    state.resolution.fix = "clear slot ownership on release"
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = ["Loop restored end-to-end"]
    state.resolution.root_cause = {
        "summary": "Scheduler does not clear slot ownership on release",
        "owning_layer": "scheduler",
        "broken_control_state": "slot ownership set",
        "failure_mechanism": "release path leaves ownership set dirty",
        "loop_break": "truth owner update -> projection refresh",
        "decisive_signal": "ownership set remains non-empty after release",
    }
    state.investigation_contract.related_risk_targets = [
        {
            "target": "release-retry-loop",
            "reason": "Retry admission also depends on slot ownership",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]

    result = await VerifyingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "related-risk review is incomplete" in (state.current_focus.next_action or "").lower()

@pytest.mark.asyncio
async def test_verifying_node_treats_silent_nonzero_exit_as_failure():
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.reproduction_command = f'"{sys.executable}" -c "import sys; sys.exit(3)"'
    state.resolution.fix = "Try a different parser boundary"

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.resolution.verification == "failed"
    assert state.resolution.fail_count == 1

@pytest.mark.asyncio
async def test_run_debug_session_stops_when_more_input_is_needed(tmp_path):
    state = DebugGraphState(slug="test-session", trigger="Intermittent failure")
    handler = MarkdownPersistenceHandler(tmp_path)

    await asyncio.wait_for(run_debug_session(state, handler), timeout=1)

    assert state.status == DebugStatus.GATHERING
    assert "causal map needed" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_run_debug_session_pauses_before_resume_verification(tmp_path):
    sentinel = tmp_path / "should-not-exist.txt"
    state = DebugGraphState(slug="resume-session", trigger="Intermittent failure")
    state.current_node_id = "VerifyingNode"
    state.symptoms.reproduction_command = (
        f'"{sys.executable}" -c "from pathlib import Path; '
        f"Path(r'{sentinel.as_posix()}').write_text('executed')\""
    )
    handler = MarkdownPersistenceHandler(tmp_path)

    await asyncio.wait_for(run_debug_session(state, handler, resumed=True), timeout=1)

    assert state.status == DebugStatus.AWAITING_HUMAN
    assert "confirm" in (state.current_focus.next_action or "").lower()
    assert not sentinel.exists()

@pytest.mark.asyncio
async def test_awaiting_human_node_generates_handoff_report(tmp_path):
    state = DebugGraphState(slug="test-session", trigger="Intermittent failure")
    state.resolution.root_cause = {
        "summary": "Off-by-one check in parser",
        "owning_layer": "parser",
        "broken_control_state": "token boundary decisions",
        "failure_mechanism": "loop upper bound used exclusive index incorrectly",
        "loop_break": "control decision -> state transition",
        "decisive_signal": "last token disappears while upstream parse request is unchanged",
    }
    state.resolution.fix = "Adjusted boundary condition in parser"
    state.resolution.fail_count = 3
    state.eliminated.append(
        EliminatedEntry(
            hypothesis="Cache invalidation bug",
            evidence="Bug reproduces with cache disabled",
        )
    )
    state.evidence.append(
        EvidenceEntry(
            checked="parser bounds",
            found="Upper bound skips the final token",
            implication="Parser fix is the most likely path",
        )
    )

    handler = MarkdownPersistenceHandler(tmp_path)
    node = AwaitingHumanNode()
    ctx = GraphRunContext(state=state, deps=handler)

    await node.run(ctx)

    report = state.resolution.report or ""
    saved_session = (tmp_path / "test-session.md").read_text(encoding="utf-8")

    assert state.status == DebugStatus.AWAITING_HUMAN
    assert "Awaiting Human Review" in report
    assert "Root cause" in report
    assert "Attempted fix" in report
    assert "Cache invalidation bug" in report
    assert "Upper bound skips the final token" in report
    assert "Awaiting Human Review" in saved_session


@pytest.mark.asyncio
async def test_awaiting_human_node_points_child_session_back_to_parent(tmp_path):
    state = DebugGraphState(
        slug="child-session",
        trigger="Follow-up issue discovered during verification",
        parent_slug="parent-session",
    )
    handler = MarkdownPersistenceHandler(tmp_path)
    node = AwaitingHumanNode()
    ctx = GraphRunContext(state=state, deps=handler)

    await node.run(ctx)

    report = state.resolution.report or ""

    assert "parent-session" in report
    assert "return to the parent session" in report.lower()
    assert "parent-session" in (state.current_focus.next_action or "")

@pytest.mark.asyncio
async def test_verifying_node_records_attempt_output_in_session(tmp_path, monkeypatch):
    def mock_run(_cmd):
        return "FAIL: parser still drops the final token"

    import specify_cli.debug.graph as graph_module
    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(slug="test-session", trigger="Intermittent failure")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Adjust parser boundary condition"
    handler = MarkdownPersistenceHandler(tmp_path)

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=handler)

    result = await node.run(ctx)
    saved_session = (tmp_path / "test-session.md").read_text(encoding="utf-8")

    assert isinstance(result, InvestigatingNode)
    assert state.evidence[-1].checked == "python tests/repro.py"
    assert "FAIL: parser still drops the final token" in state.evidence[-1].found
    assert "Adjust parser boundary condition" in state.evidence[-1].implication
    assert "FAIL: parser still drops the final token" in saved_session

@pytest.mark.asyncio
async def test_tool_access():
    # Verify that the required tools are imported and available in graph module
    import specify_cli.debug.graph as graph_module
    assert hasattr(graph_module, "run_command")
    assert hasattr(graph_module, "edit_file")
    assert hasattr(graph_module, "read_file")
