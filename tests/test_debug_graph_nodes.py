import pytest
from specify_cli.debug.schema import DebugGraphState

def test_debug_graph_state_initialization():
    state = DebugGraphState(slug="test", trigger="test")
    assert state.slug == "test"
    assert state.status == "gathering"
    assert hasattr(state, "context")
    assert state.context.modified_files == []
