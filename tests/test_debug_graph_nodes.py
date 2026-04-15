import pytest
import sys
import asyncio
from pydantic_graph import GraphRunContext
from specify_cli.debug.schema import (
    DebugGraphState,
    DebugStatus,
    EliminatedEntry,
    EvidenceEntry,
)
from specify_cli.debug.graph import (
    AwaitingHumanNode,
    FixingNode,
    GatheringNode,
    InvestigatingNode,
    ResolvedNode,
    VerifyingNode,
    run_debug_session,
)
from specify_cli.debug.persistence import MarkdownPersistenceHandler

@pytest.mark.asyncio
async def test_gathering_node_missing_symptoms():
    state = DebugGraphState(slug="test", trigger="test")
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
    
    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, InvestigatingNode)

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
    
    node = FixingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert result.data == "Awaiting more debugging input"
    assert "Please propose a fix" in state.current_focus.next_action

@pytest.mark.asyncio
async def test_fixing_node_with_fix():
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
    state.resolution.fix = "Update line 42 to fix the typo"
    
    node = FixingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, VerifyingNode)

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
    
    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, ResolvedNode)
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

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, ResolvedNode)
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

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, ResolvedNode)
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
    assert "expected and actual behavior" in (state.current_focus.next_action or "").lower()


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
