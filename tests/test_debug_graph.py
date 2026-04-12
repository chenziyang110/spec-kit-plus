import pytest
from pydantic_graph import GraphRunContext, End
from specify_cli.debug.graph import (
    GatheringNode, InvestigatingNode, FixingNode, VerifyingNode, 
    ResolvedNode, AwaitingHumanNode
)
from specify_cli.debug.schema import DebugGraphState, DebugStatus

@pytest.mark.asyncio
async def test_gathering_to_investigating():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    ctx = GraphRunContext(state=state, deps=None)
    node = GatheringNode()
    
    # In Task 2, it returns End. We want it to return InvestigatingNode.
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
async def test_verifying_to_resolved_on_success():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.verification = "Passed"
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, ResolvedNode)
    assert state.status == DebugStatus.VERIFYING

@pytest.mark.asyncio
async def test_verifying_to_investigating_on_failure():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.verification = None # Failed/not passed
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, InvestigatingNode)
    assert state.status == DebugStatus.VERIFYING
