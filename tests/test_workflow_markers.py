from specify_cli.workflow_markers import (
    has_agent_marker,
    has_parallel_marker,
    strip_known_markers,
)


def test_agent_marker_is_independent_from_parallel_marker() -> None:
    assert has_agent_marker("- [ ] T017 [AGENT] Read PROJECT-HANDBOOK.md") is True
    assert has_parallel_marker("- [ ] T017 [AGENT] Read PROJECT-HANDBOOK.md") is False
    assert has_agent_marker("- [ ] T018 [P] Build batch") is False
    assert has_parallel_marker("- [ ] T018 [P] Build batch") is True


def test_strip_known_markers_preserves_human_summary() -> None:
    cleaned = strip_known_markers(" [P] [AGENT] Re-evaluate strategy after join point ")
    assert cleaned == "Re-evaluate strategy after join point"


def test_marker_helpers_ignore_literal_marker_text_inside_prose() -> None:
    text = "Document the literal [AGENT] and [P] tokens in docs/markers.md"

    assert has_agent_marker(text) is False
    assert has_parallel_marker(text) is False


def test_strip_known_markers_only_removes_supported_leading_markers() -> None:
    cleaned = strip_known_markers(
        " [P] [AGENT] Preserve literal [P] and [AGENT] text in docs/markers.md "
    )

    assert cleaned == "Preserve literal [P] and [AGENT] text in docs/markers.md"


def test_marker_helpers_recognize_bullet_list_actionable_prefixes() -> None:
    text = "- [P] [AGENT] Preserve literal [AGENT] token in docs/parallel.md"

    assert has_agent_marker(text) is True
    assert has_parallel_marker(text) is True
    assert strip_known_markers(text) == "- Preserve literal [AGENT] token in docs/parallel.md"


def test_marker_helpers_recognize_numbered_list_actionable_prefixes() -> None:
    text = "1. [AGENT] Read PROJECT-HANDBOOK.md and note literal [P] text"

    assert has_agent_marker(text) is True
    assert has_parallel_marker(text) is False
    assert strip_known_markers(text) == "1. Read PROJECT-HANDBOOK.md and note literal [P] text"
