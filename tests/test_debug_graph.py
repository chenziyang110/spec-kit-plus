import pytest
from pydantic_graph import GraphRunContext

import specify_cli.debug.graph as graph_module
from specify_cli.debug.graph import (
    FixingNode,
    GatheringNode,
    InvestigatingNode,
    ResolvedNode,
    VerifyingNode,
)
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState, DebugStatus

@pytest.mark.asyncio
async def test_gathering_to_investigating():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.expected = "Expected parser output"
    state.symptoms.actual = "Actual parser output"
    state.symptoms.reproduction_verified = True
    ctx = GraphRunContext(state=state, deps=None)
    node = GatheringNode()

    result = await node.run(ctx)
    assert isinstance(result, InvestigatingNode)
    assert state.status == DebugStatus.GATHERING
    assert state.observer_framing_completed is True
    assert state.observer_mode == "full"
    assert state.observer_framing.primary_suspected_loop is not None
    assert state.transition_memo.first_candidate_to_test is not None


@pytest.mark.asyncio
async def test_gathering_node_uses_compressed_observer_framing_for_strong_low_level_evidence():
    state = DebugGraphState(trigger="Traceback in parser.py line 42", slug="test-slug")
    state.symptoms.expected = "Expected parser output"
    state.symptoms.actual = "Actual parser output"
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.symptoms.reproduction_verified = True
    ctx = GraphRunContext(state=state, deps=None)
    node = GatheringNode()

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.observer_framing_completed is True
    assert state.observer_mode == "compressed"
    assert state.skip_observer_reason is not None
    assert state.observer_framing.recommended_first_probe is not None

@pytest.mark.asyncio
async def test_investigating_to_fixing():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale running ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "released slot did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "running set stayed non-empty while promotion should have occurred",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "running set"}]
    state.control_state = ["running_set"]
    state.observation_state = ["task_table"]
    state.closed_loop.input_event = "task completion"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "waiting task becomes admitted"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion stage"
    state.resolution.decisive_signals = ["running_set empty while task_table still showed running"]
    state.resolution.alternative_hypotheses_considered = [
        "Scheduler kept stale running ownership after slot release",
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, FixingNode)
    assert state.status == DebugStatus.INVESTIGATING

@pytest.mark.asyncio
async def test_fixing_to_verifying():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale running ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "released slot did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "running set stayed non-empty while promotion should have occurred",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "running set"}]
    state.control_state = ["running_set"]
    state.observation_state = ["task_table"]
    state.closed_loop.input_event = "task completion"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "waiting task becomes admitted"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion stage"
    state.resolution.decisive_signals = ["running_set empty while task_table still showed running"]
    state.resolution.alternative_hypotheses_considered = [
        "Scheduler kept stale running ownership after slot release",
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Applied fix"
    state.resolution.fix_scope = "truth-owner"
    ctx = GraphRunContext(state=state, deps=None)
    node = FixingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, VerifyingNode)
    assert state.status == DebugStatus.FIXING

@pytest.mark.asyncio
async def test_verifying_to_resolved_on_success(monkeypatch):
    seen: list[str] = []

    def fake_run_verification_commands(commands, *, runner=None, stop_on_failure=False):
        seen.extend(commands)
        return [
            graph_module.ValidationResult(command=command, status="passed", output="PASS")
            for command in commands
        ]

    monkeypatch.setattr(graph_module, "run_verification_commands", fake_run_verification_commands)

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph.py"]
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = [
        "Repro now shows the scheduler releases ownership and the UI reflects the promoted task.",
    ]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)
    assert isinstance(result, ResolvedNode)
    assert state.resolution.verification == "success"
    assert seen == ["python tests/repro.py", "pytest tests/test_debug_graph.py"]
    assert [item.command for item in state.resolution.validation_results] == seen
    assert state.status == DebugStatus.VERIFYING

@pytest.mark.asyncio
async def test_verifying_to_investigating_on_failure(monkeypatch):
    calls = []

    def mock_run(_cmd: str) -> str:
        calls.append(_cmd)
        return "PASS" if len(calls) == 1 else "FAIL"

    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph.py"]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)
    assert isinstance(result, InvestigatingNode)
    assert state.resolution.verification == "failed"
    assert state.resolution.fail_count == 1
    assert state.status == DebugStatus.VERIFYING


@pytest.mark.asyncio
async def test_investigating_blocks_fixing_without_control_plane_framing():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.root_cause = {"summary": "Found it"}
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "fixing is blocked" in (state.current_focus.next_action or "").lower()
    assert "truth ownership map" in (state.current_focus.next_action or "").lower()
    assert "- [ ] truth ownership map" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_investigating_blocks_fixing_without_alternative_hypothesis_coverage():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.observer_framing.alternative_cause_candidates = [
        {"candidate": "Scheduler kept stale running ownership after slot release"},
        {"candidate": "Resource counters or slot accounting are stale"},
    ]
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale running ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "released slot did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "running set stayed non-empty while promotion should have occurred",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "running set"}]
    state.control_state = ["running_set"]
    state.observation_state = ["task_table"]
    state.closed_loop.input_event = "task completion"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "waiting task becomes admitted"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion stage"
    state.resolution.decisive_signals = ["running_set empty while task_table still showed running"]
    state.resolution.root_cause_confidence = "confirmed"
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "alternative hypothesis" in (state.current_focus.next_action or "").lower()
    assert "ruled-out" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_verifying_second_failure_requests_diagnostic_escalation(monkeypatch):
    calls = []

    def mock_run(_cmd: str) -> str:
        calls.append(_cmd)
        return "FAIL"

    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize UI status"
    state.resolution.fail_count = 1
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.resolution.fail_count == 2
    assert "decisive instrumentation" in (state.current_focus.next_action or "").lower()
    assert "control plane" in (state.current_focus.next_action or "").lower()
    assert "detected profile: ui projection" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture ownership sets at the decision layer" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture source-of-truth state at publish time" in (state.current_focus.next_action or "").lower()
    assert "Normalize UI status" in state.resolution.rejected_surface_fixes


@pytest.mark.asyncio
async def test_verifying_second_failure_writes_research_checkpoint_when_persistence_available(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "FAIL")

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize UI status"
    state.resolution.fail_count = 1
    handler = MarkdownPersistenceHandler(tmp_path)
    ctx = GraphRunContext(state=state, deps=handler)
    node = VerifyingNode()

    result = await node.run(ctx)

    research_path = tmp_path / "test-slug.research.md"
    assert isinstance(result, InvestigatingNode)
    assert research_path.exists()
    assert "Debug Research: test-slug" in research_path.read_text(encoding="utf-8")
    assert "review" in (state.current_focus.next_action or "").lower()
    assert "research" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_scheduler_admission_profile_gets_targeted_diagnostic_checklist(monkeypatch):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "FAIL")

    state = DebugGraphState(trigger="scheduler queue stuck after slot release", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize queue status"
    state.resolution.fail_count = 1
    state.control_state = ["running set", "activeCount"]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert "detected profile: scheduler/admission" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture queue contents before and after the decision point" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture running/admitted ownership sets before and after slot release" in (state.current_focus.next_action or "").lower()
