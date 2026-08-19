from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLASSIC_GATE = (
    PROJECT_ROOT
    / "templates"
    / "command-partials"
    / "common"
    / "context-sufficiency-choice.md"
)
ADVANCED_GATE = (
    PROJECT_ROOT
    / "templates"
    / "advanced-skills"
    / "_shared"
    / "context-sufficiency-choice.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_classic_gate_requires_evidence_before_offering_context_direct() -> None:
    assert CLASSIC_GATE.exists()
    content = _read(CLASSIC_GATE)

    for required in (
        "pre-intake context sufficiency gate",
        "already present in the active conversation context",
        "no tool call",
        "exact owning files or symbols",
        "direct consumers",
        "verification entry points",
        "unknown means insufficient",
        "do not show a choice",
    ):
        assert required in content

    assert "direct change (recommended)" in content
    assert "continue full sp-quick" in content
    assert "direct fix (recommended)" in content
    assert "continue full sp-debug" in content


def test_context_direct_skips_only_entry_discovery_and_keeps_safety_gates() -> None:
    assert CLASSIC_GATE.exists()
    content = _read(CLASSIC_GATE)

    for required in (
        "skip entry-time `learning start`",
        "skip entry-time `cognition compass`",
        "must not create quick or debug workflow state",
        "failing test or executable reproduction",
        "fresh verification",
        "post-change project cognition closeout",
        "does not waive",
    ):
        assert required in content

    assert "large, cross-cutting, multi-item" in content
    assert "full quick branch" in content
    assert "proven failure mechanism" in content
    assert "full debug branch" in content


def test_classic_quick_and_debug_include_gate_before_full_workflow_intake() -> None:
    for command in ("quick", "debug"):
        shell = _read(
            PROJECT_ROOT / "templates" / "command-partials" / command / "shell.md"
        )
        assert (
            "{{spec-kit-include: ../common/context-sufficiency-choice.md}}" in shell
        )


def test_advanced_quick_and_debug_read_shared_gate_first() -> None:
    assert ADVANCED_GATE.exists()
    shared = _read(ADVANCED_GATE)
    assert "pre-intake context sufficiency gate" in shared
    assert "unknown means insufficient" in shared
    assert "post-change project cognition closeout" in shared

    for skill_name in ("spx-quick", "spx-debug"):
        skill = _read(
            PROJECT_ROOT
            / "templates"
            / "advanced-skills"
            / skill_name
            / "SKILL.md"
        )
        gate_index = skill.index("references/context-sufficiency-choice.md")
        learning_index = skill.index("references/project-learning.md")
        cognition_index = skill.index("references/project-cognition.md")
        assert gate_index < learning_index
        assert gate_index < cognition_index


def test_user_guidance_documents_context_direct_as_an_explicit_choice() -> None:
    for relative_path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    ):
        content = _read(PROJECT_ROOT / relative_path)
        assert "context-direct" in content
        assert "current conversation context" in content
        assert "full quick" in content
        assert "full debug" in content
