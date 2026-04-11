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
    assert "user's current language" in content.lower()
    assert "Business Goals" in content
    assert "Users & Roles" in content
    assert "Technical Constraints / Assumptions" in content
    assert "Outstanding Questions" in content
    assert "Default to concise clarification turns" in content
    assert "Do not restate the full current understanding after every answer" in content
    assert "Save the full synthesis for the alignment-ready turn" in content
    assert "question-card format" in content.lower()
    assert "[ RECOMMENDED ]" in content
    assert "Reply naturally, for example:" in content
    assert '选 C' in content
    assert "Recorded: C - Normalize first" in content
    assert "Do not repeat the same question" in content
    assert "Ask at most one unanswered high-impact question per message" in content
    assert "each clarification turn should contain at most one short checkpoint" in content
    assert "decompose" in content.lower()
    assert "first-release scope" in content.lower()
    assert "mvp scope" not in content.lower()


def test_plan_template_requires_alignment_report_before_planning():
    content = _read("templates/commands/plan.md")

    assert "alignment.md" in content
    assert "Missing alignment report" in content
    assert "Force proceed with known risks" in content
    assert "Input Risks From Alignment" in content
    assert "user's current language" in content.lower()


def test_clarify_template_updates_alignment_decision():
    content = _read("templates/commands/clarify.md")

    assert "alignment.md" in content
    assert "adding newly provided requirements or constraints" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "user's current language" in content.lower()


def test_spec_template_defines_scope_boundaries_without_open_clarification_examples():
    content = _read("templates/spec-template.md")

    assert "## Scope Boundaries" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content
    assert "[NEEDS CLARIFICATION:" not in content
    assert "coherent first release" in content.lower()
    assert "viable mvp" not in content.lower()


def test_tasks_templates_default_to_phased_delivery_not_mvp():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")

    assert "phased delivery" in command_content.lower()
    assert "suggested first release scope" in command_content.lower()
    assert "parallel batch" in command_content.lower()
    assert "join point" in command_content.lower()
    assert "write set" in command_content.lower()
    assert "mvp first" not in command_content.lower()
    assert "suggested mvp scope" not in command_content.lower()

    assert "phased delivery" in template_content.lower()
    assert "first release candidate" in template_content.lower()
    assert "parallel batch" in template_content.lower()
    assert "join point" in template_content.lower()
    assert "write set" in template_content.lower()
    assert "mvp first" not in template_content.lower()
    assert "mvp increment" not in template_content.lower()
    assert "mvp!" not in template_content.lower()


def test_implement_template_supports_capability_aware_parallel_batches():
    content = _read("templates/commands/implement.md")

    assert "parallel batches" in content.lower()
    assert "current agent" in content.lower()
    assert "ready tasks" in content.lower()
    assert "join point" in content.lower()
    assert "shared registration files" in content.lower()
    assert "execution strategy" in content.lower()
    assert "native subagents" in content.lower()
    assert "coordinated runtime" in content.lower()
    assert "sequential execution" in content.lower()
    assert "auto-dispatch" in content.lower()
    assert "feature_dir" in content.lower()


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Requirement Alignment Report:" in content
    assert "## Release Decision" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
