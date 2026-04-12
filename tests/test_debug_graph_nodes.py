import pytest
from pydantic_graph import GraphRunContext
from specify_cli.debug.schema import DebugGraphState, DebugStatus
from specify_cli.debug.graph import GatheringNode, InvestigatingNode, FixingNode, VerifyingNode
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
async def test_gathering_node_with_symptoms_not_verified():
    state = DebugGraphState(slug="test", trigger="test")
    state.symptoms.expected = "Something should happen"
    state.symptoms.actual = "Something else happened"
    
    node = GatheringNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    # move to InvestigatingNode ONLY if reproduction_verified is True
    assert isinstance(result, GatheringNode)
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
    
    assert isinstance(result, InvestigatingNode)
    assert "Prioritizing files from recent history" in state.current_focus.next_action
    assert "src/buggy.py" in state.current_focus.next_action

@pytest.mark.asyncio
async def test_investigating_node_elimination():
    state = DebugGraphState(slug="test", trigger="test")
    state.current_focus.hypothesis = "Database is down"
    state.current_focus.next_action = "Eliminate: DB is actually up, checked via ping."
    
    node = InvestigatingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, InvestigatingNode)
    assert len(state.eliminated) == 1
    assert state.eliminated[0].hypothesis == "Database is down"
    assert "DB is actually up" in state.eliminated[0].evidence
    # Focus should be reset
    assert state.current_focus.hypothesis is None
    assert state.current_focus.next_action is None

@pytest.mark.asyncio
async def test_investigating_node_finds_root_cause():
    state = DebugGraphState(slug="test", trigger="test")
    state.resolution.root_cause = "Typo in line 42"
    
    node = InvestigatingNode()
    ctx = GraphRunContext(state=state, deps=None)
    
    result = await node.run(ctx)
    
    assert isinstance(result, FixingNode)
