from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_specify_template_uses_alignment_first_contract():
    content = _read("templates/commands/specify.md")

    assert "alignment.md" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "Task Classification" in content or "task classification" in content.lower()
    assert "After every round, restate current understanding" in content


def test_plan_template_requires_alignment_report_before_planning():
    content = _read("templates/commands/plan.md")

    assert "alignment.md" in content
    assert "Missing alignment report" in content
    assert "Force proceed with known risks" in content
    assert "Input Risks From Alignment" in content


def test_clarify_template_updates_alignment_decision():
    content = _read("templates/commands/clarify.md")

    assert "alignment.md" in content
    assert "adding newly provided requirements or constraints" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content


def test_spec_template_defines_scope_boundaries_without_open_clarification_examples():
    content = _read("templates/spec-template.md")

    assert "## Scope Boundaries" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content
    assert "[NEEDS CLARIFICATION:" not in content


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Requirement Alignment Report:" in content
    assert "## Release Decision" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
