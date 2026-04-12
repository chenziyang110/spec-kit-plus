import pytest
from pydantic_graph import GraphRunContext
from specify_cli.debug.schema import DebugGraphState, DebugStatus
from specify_cli.debug.graph import GatheringNode, InvestigatingNode
from specify_cli.debug.persistence import MarkdownPersistenceHandler

@pytest.mark.asyncio
async def test_gathering_node_missing_symptoms():
    state = DebugGraphState(slug="test", trigger="test")
    # symptoms are empty by default
    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, GatheringNode)
    assert state.status == DebugStatus.GATHERING
    assert state.context is not None

@pytest.mark.asyncio
async def test_gathering_node_with_symptoms():
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.expected = "Something should happen"
    state.symptoms.actual = "Something else happened"
    
    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    # Task 1 result: if symptoms present, move to InvestigatingNode
    assert isinstance(result, InvestigatingNode)
