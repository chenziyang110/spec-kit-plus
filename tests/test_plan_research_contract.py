from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return read_template(path)


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


def test_plan_command_requires_persisted_delegated_planning_lane_handoffs() -> None:
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    assert "planning/handoffs/<lane-id>.json" in content
    assert "planning/evidence-index.json" in content
    assert "planning/checkpoints.ndjson" in content
    assert "persist a `planning_checkpoint` record" in lowered
    assert "persist the lane's structured handoff" in lowered
    assert "consume `planning/evidence-index.json` before final synthesis" in lowered
    assert "mark the handoff as `integrated`, assigned to a refinement checkpoint" in lowered
    assert "recorded in `user_confirmed_deferrals` with confirmation source" in lowered
    assert "without an explicit consuming artifact section, refinement checkpoint" in lowered
    assert (
        "do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results"
        in lowered
    )


def test_plan_command_scaffolds_plan_contract_with_project_relative_path() -> None:
    content = _read("templates/commands/plan.md").lower()

    assert "artifact scaffold --kind plan-contract" in content
    assert "project-relative" in content
    assert "do not pass absolute `feature_dir`" in content
    assert "convert it to a project-relative output path" in content
    assert "create the fixed json envelope when it is missing" in content
    assert "if `plan-contract.json` already exists, read, validate, and preserve it" in content
    assert "<project-relative-feature-dir>/plan-contract.json" in content
    assert "<project-relative-feature-dir>/plan/plan-contract.json" in content
    assert "use the existing location on reruns and scaffold only the missing target" in content
    assert "artifact scaffold --out` must use a project-relative path" in content
    assert "never pass an absolute `feature_dir` to scaffold commands" in content
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
