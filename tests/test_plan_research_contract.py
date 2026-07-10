from pathlib import Path

from .template_utils import read_command_with_references, read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return read_template(path)


def test_plan_command_research_contract_is_prescriptive() -> None:
    content = read_command_with_references("plan")

    assert "read `templates/research-template.md`" in content
    assert "Prefer official documentation, standards, and primary sources" in content
    assert "Treat model memory as provisional" in content
    assert "Research must reduce planning ambiguity" in content
    assert "confidence, assumptions, validation, environment/dependency notes" in content
    assert "why hand-rolling is or is not justified" in content


def test_plan_command_requires_persisted_delegated_planning_lane_handoffs() -> None:
    content = read_command_with_references("plan")
    lowered = content.lower()

    assert "planning/lane-manifest.json" in content
    assert "each lane writes one agent-only result" in lowered
    assert "every accepted lane result is integrated" in lowered
    assert "do not require separate evidence-index and checkpoint logs" in lowered
    assert "do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results" in lowered


def test_plan_command_scaffolds_plan_contract_with_project_relative_path() -> None:
    content = read_command_with_references("plan").lower()

    assert "artifact scaffold --kind plan-contract" in content
    assert "project-relative" in content
    assert "never pass an absolute `feature_dir`" in content
    assert "if no contract exists" in content
    assert "<project-relative-feature-dir>/plan-contract.json" in content
    assert "preserve the existing top-level or `plan/plan-contract.json` location" in content
    assert "plan-contract.json" in content


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
    assert "## Implementation Constitution" in plan_template
    assert "### Architecture Invariants" in plan_template
    assert "### Forbidden Implementation Drift" in plan_template
    assert "### Required Implementation References" in plan_template
    assert "### Standard Stack" in plan_template
    assert "### Don't Hand-Roll" in plan_template
    assert "### Common Pitfalls" in plan_template
    assert "### Assumptions To Validate" in plan_template
    assert "### Environment / Dependency Notes" in plan_template
    assert "## Research Adoption Check" in plan_template
