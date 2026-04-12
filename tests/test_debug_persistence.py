import pytest
from pathlib import Path
from datetime import datetime
from specify_cli.debug.schema import DebugGraphState, DebugStatus, EvidenceEntry, EliminatedEntry
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.utils import generate_slug

def test_save_new_state(tmp_path):
    # Arrange
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="test-slug",
        trigger="Unit test trigger",
        status=DebugStatus.INVESTIGATING,
        current_node_id="InvestigatingNode"
    )
    
    # Act
    handler.save(state)
    
    # Assert
    file_path = tmp_path / "test-slug.md"
    assert file_path.exists()
    content = file_path.read_text()
    assert "slug: test-slug" in content
    assert "status: investigating" in content
    assert "current_node_id: InvestigatingNode" in content

def test_load_state(tmp_path):
    # Arrange
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="load-test",
        trigger="Trigger for loading",
        status=DebugStatus.FIXING,
        current_node_id="FixingNode"
    )
    handler.save(state)
    
    # Act
    loaded_state = handler.load(tmp_path / "load-test.md")
    
    # Assert
    assert loaded_state.slug == state.slug
    assert loaded_state.trigger == state.trigger
    assert loaded_state.status == state.status
    assert loaded_state.current_node_id == state.current_node_id

def test_overwrite_state(tmp_path):
    # Arrange
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="overwrite-test",
        trigger="Overwrite trigger",
        status=DebugStatus.GATHERING
    )
    handler.save(state)
    
    # Act
    state.status = DebugStatus.INVESTIGATING
    state.current_node_id = "InvestigatingNode"
    handler.save(state)
    
    # Assert
    loaded_state = handler.load(tmp_path / "overwrite-test.md")
    assert loaded_state.status == DebugStatus.INVESTIGATING
    assert loaded_state.current_node_id == "InvestigatingNode"

def test_append_entries(tmp_path):
    # Arrange
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="append-test",
        trigger="Append trigger",
        status=DebugStatus.INVESTIGATING
    )
    state.evidence.append(EvidenceEntry(
        checked="logs",
        found="error 500",
        implication="server failure"
    ))
    state.eliminated.append(EliminatedEntry(
        hypothesis="client timeout",
        evidence="no timeout in logs"
    ))
    
    # Act
    handler.save(state)
    loaded_state = handler.load(tmp_path / "append-test.md")
    
    # Assert
    assert len(loaded_state.evidence) == 1
    assert loaded_state.evidence[0].checked == "logs"
    assert len(loaded_state.eliminated) == 1
    assert loaded_state.eliminated[0].hypothesis == "client timeout"

@pytest.mark.asyncio
async def test_graph_node_triggers_persistence(tmp_path):
    from specify_cli.debug.graph import GatheringNode, InvestigatingNode
    from pydantic_graph import GraphRunContext
    
    # Arrange
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="integration-test",
        trigger="integration trigger",
        status=DebugStatus.GATHERING
    )
    ctx = GraphRunContext(state=state, deps=handler)
    node = GatheringNode()
    
    # Act
    await node.run(ctx)
    
    # Assert
    file_path = tmp_path / "integration-test.md"
    assert file_path.exists()
    
    # Reload and verify state update
    loaded_state = handler.load(file_path)
    assert loaded_state.current_node_id == "GatheringNode"
    assert loaded_state.status == DebugStatus.GATHERING

def test_persistence_new_fields(tmp_path):
    # Arrange
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(
        slug="new-fields-test",
        trigger="New fields trigger",
        status=DebugStatus.FIXING
    )
    state.resolution.fail_count = 2
    state.symptoms.reproduction_command = "pytest tests/repro.py"
    
    # Act
    handler.save(state)
    loaded_state = handler.load(tmp_path / "new-fields-test.md")
    
    # Assert
    assert loaded_state.resolution.fail_count == 2
    assert loaded_state.symptoms.reproduction_command == "pytest tests/repro.py"
