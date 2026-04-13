from pathlib import Path

import pytest

from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState


def test_persistence_round_trips_full_state(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="roundtrip")
    state.current_focus.hypothesis = "Parser bug"
    state.current_focus.next_action = "Line 1\nline 2: still same field"
    state.symptoms.expected = "final token preserved"
    state.symptoms.actual = "final token missing"
    state.symptoms.reproduction_verified = True
    state.context.feature_id = "002-autonomous-execution"
    state.context.modified_files = ["src/specify_cli/debug/graph.py", "tests/test_debug_graph_nodes.py"]
    state.recently_modified = ["src/specify_cli/debug/persistence.py"]
    state.resolution.files_changed = ["src/specify_cli/debug/graph.py"]
    state.resolution.report = "## Awaiting Human Review\n- Investigate parser boundary"

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.current_focus.next_action == "Line 1\nline 2: still same field"
    assert restored.symptoms.reproduction_verified is True
    assert restored.context.feature_id == "002-autonomous-execution"
    assert restored.context.modified_files == [
        "src/specify_cli/debug/graph.py",
        "tests/test_debug_graph_nodes.py",
    ]
    assert restored.recently_modified == ["src/specify_cli/debug/persistence.py"]
    assert restored.resolution.files_changed == ["src/specify_cli/debug/graph.py"]
    assert restored.resolution.report == "## Awaiting Human Review\n- Investigate parser boundary"


def test_persistence_round_trips_trigger_with_frontmatter_delimiter(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="parser --- bug")

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.trigger == "parser --- bug"


def test_persistence_rejects_path_like_slug(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="../escape", trigger="bad slug")

    with pytest.raises(ValueError):
        handler.save(state)


def test_persistence_load_rejects_executable_files_changed_payload(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    sentinel = (tmp_path / "executed.txt").as_posix()
    session_path = tmp_path / "session.md"
    session_path.write_text(
        "\n".join(
            [
                "---",
                "slug: session",
                "status: gathering",
                "trigger: malicious",
                "current_node_id: GatheringNode",
                "created: 2026-04-13T00:00:00",
                "updated: 2026-04-13T00:00:00",
                "---",
                "",
                "## Current Focus",
                "hypothesis: null",
                "",
                "## Symptoms",
                "expected: null",
                "",
                "## Eliminated",
                "[]",
                "",
                "## Evidence",
                "[]",
                "",
                "## Resolution",
                f"files_changed: __import__('pathlib').Path(r'''{sentinel}''').write_text('owned') and []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        handler.load(session_path)

    assert not Path(sentinel).exists()
