from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_plan_command_research_contract_is_prescriptive() -> None:
    content = _read("templates/commands/plan.md")

    assert "Read `templates/research-template.md`" in content
    assert "high-risk architectural choice -> stack/pattern/pitfall task" in content
    assert "external tool, runtime, or service dependency -> availability and fallback task" in content
    assert "Prefer official documentation, standards, and primary sources" in content
    assert "Treat model memory as provisional" in content
    assert "Research must reduce planning ambiguity, not accumulate background reading." in content
    assert "Source confidence (`verified`, `cited`, or `assumed`)" in content
    assert "`Don't hand-roll` guidance" in content
    assert "Assumptions log" in content
    assert "Validation notes" in content
    assert "Environment or dependency notes" in content
    assert "Do not present unverified claims as settled facts." in content
    assert "Prefer prescriptive recommendations over broad option dumps" in content
    assert "Use `templates/research-template.md` as the default structure for `research.md`" in content


def test_research_template_and_plan_template_are_linked() -> None:
    research_template = _read("templates/research-template.md")
    plan_template = _read("templates/plan-template.md")

    assert "## Standard Stack" in research_template
    assert "## Don't Hand-Roll" in research_template
    assert "## Common Pitfalls" in research_template
    assert "## Assumptions Log" in research_template
    assert "## Validation Notes" in research_template
    assert "## Environment / Dependency Notes" in research_template

    assert "## Research Inputs" in plan_template
    assert "### Standard Stack" in plan_template
    assert "### Don't Hand-Roll" in plan_template
    assert "### Common Pitfalls" in plan_template
    assert "### Assumptions To Validate" in plan_template
    assert "### Environment / Dependency Notes" in plan_template
    assert "## Research Adoption Check" in plan_template
