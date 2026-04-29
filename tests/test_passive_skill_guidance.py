from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def test_workflow_routing_references_map_gate_and_project_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "spec-kit-project-map-gate" in content
    assert "spec-kit-project-learning" in content
    assert "sp-test" in content
    assert "sp-auto" in content
    assert "sp-deep-research" in content
    assert "implementation chain" in content or "implementation-chain" in content
    assert "planning handoff" in content
    assert "route into the right active `sp-*` workflow" in content
    assert "hard brownfield context gate" in content
    assert "learning-start" in content
    assert "learning-capture" in content
    assert "recommended next step" in content or "continue without naming the exact workflow" in content


def test_project_map_gate_references_routing_and_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-project-map-gate/SKILL.md").lower()

    assert "spec-kit-workflow-routing" in content
    assert "spec-kit-project-learning" in content
    assert "route selection" in content
    assert "shared memory capture layer" in content
    assert "sp-map-codebase" in content


def test_project_learning_focuses_on_memory_triggers_storage_and_promotion() -> None:
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md").lower()

    assert "this skill is about the memory system itself" in content
    assert "it is not a catalog of `sp-*` workflows" in content
    assert "the user should not have to manually remind the agent to remember recurring pitfalls" in content
    assert "what counts as memory-worthy knowledge" in content
    assert "memory layers" in content
    assert "learning types" in content
    assert "required behavior" in content
    assert "capture heuristics" in content
    assert "promotion heuristics" in content
    assert "injection goal" in content
    assert "specify learning start --command <command-name>" in content
    assert "specify hook review-learning --command <command-name>" in content
    assert "specify hook capture-learning --command <command-name>" in content
    assert "native hooks are an optional enhancement" in content
    assert "without native hooks" in content
    assert "single high-signal candidates should still appear in start-time warnings" in content
    assert "repeated high-signal candidates" in content
    assert "should auto-promote" in content
    assert "testing-state.md" in content
    assert "workflow-state.md" in content


def test_subagent_implementer_prompt_requires_unconditional_tdd() -> None:
    content = _read("templates/passive-skills/subagent-driven-development/implementer-prompt.md").lower()

    assert "write the failing test first" in content
    assert "verify the red state" in content
    assert "do not edit production code until the red state is verified" in content
