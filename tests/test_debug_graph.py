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

@pytest.mark.asyncio
async def test_investigating_to_fixing():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.root_cause = "Found it"
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, FixingNode)
    assert state.status == DebugStatus.INVESTIGATING

@pytest.mark.asyncio
async def test_fixing_to_verifying():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.fix = "Applied fix"
    ctx = GraphRunContext(state=state, deps=None)
    node = FixingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, VerifyingNode)
    assert state.status == DebugStatus.FIXING

@pytest.mark.asyncio
async def test_verifying_to_resolved_on_success(monkeypatch):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "PASS")

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph.py"]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)
    assert isinstance(result, ResolvedNode)
    assert state.resolution.verification == "success"
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
