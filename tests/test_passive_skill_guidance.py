from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def test_workflow_routing_references_map_gate_and_project_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "spec-kit-project-map-gate" in content
    assert "spec-kit-project-learning" in content
    assert "sp-test-scan" in content
    assert "sp-test-build" in content
    assert "{{invoke:test}}" not in content
    assert "sp-auto" in content
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "peer\n  workflow path to `sp-specify`" in content or "peer workflow path to `sp-specify`" in content
    assert "do not automatically hand off to planning" in content
    assert "sp-deep-research" in content
    assert "implementation chain" in content or "implementation-chain" in content
    assert "planning handoff" in content
    assert "route into the right active `sp-*` workflow" in content
    assert "hard brownfield context gate" in content
    assert "learning-start" in content
    assert "learning-capture" in content
    assert "recommended next step" in content or "continue without naming the exact workflow" in content


def test_project_to_prd_routes_existing_project_prd_extraction() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md").lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "deprecated" in content
    assert "current-state prd suite" in content
    assert "repository evidence" in content
    assert "evidence, inference, and unknown" in content
    assert ".specify/prd-runs/<run-id>/workflow-state.md" in content
    assert "do not automatically hand off to `sp-plan`" in content


def test_project_to_prd_mentions_depth_aware_reconstruction() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md").lower()

    assert "capability triage" in content
    assert "targeted evidence harvest" in content
    assert "critical capabilities" in content
    assert "depth-aware" in content


def test_project_to_prd_mentions_heavy_reconstruction_contract() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md")
    lowered = content.lower()

    assert "heavy reconstruction" in lowered
    assert "L4 Reconstruction-Ready" in content
    assert "subagent-mandatory" in content
    assert "config-contracts.json" in content
    assert "second repository scan" in lowered
    assert "critical evidence" in lowered


def test_project_to_prd_skill_routes_to_prd_scan_then_prd_build() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md")
    lowered = content.lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "deprecated" in lowered


def test_workflow_routing_uses_prd_scan_then_prd_build_as_canonical_prd_flow() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "sp-prd-scan -> sp-prd-build" in content
    assert "{{invoke:prd-scan}} -> {{invoke:prd-build}}" in content
    assert "deprecated compatibility alias" in content


def test_workflow_routing_mentions_heavy_prd_reconstruction_contract() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "heavy reconstruction" in lowered
    assert "L4 Reconstruction-Ready" in content
    assert "subagent-mandatory" in content
    assert "config-contracts.json" in content
    assert "must not reread the repository" in lowered
    assert "critical evidence gaps" in lowered


def test_workflow_routing_forces_route_selection_before_any_action() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "1% chance" in content
    assert "before any response or action" in content
    assert "clarifying question" in content
    assert "file read" in content
    assert "shell command" in content
    assert "red flags" in content


def test_subagent_driven_development_prefers_native_dispatch_contract() -> None:
    content = _read("templates/passive-skills/subagent-driven-development/SKILL.md").lower()

    assert "native subagents" in content
    assert "validated `workertaskpacket`" in content
    assert "must not dispatch from raw task text" in content
    assert "structured handoff" in content
    assert "spec compliance review" in content
    assert "code quality review" in content
    assert "`sp-teams` only" in content
    assert "we do not manually dispatch ad-hoc subagents" not in content


def test_dispatching_parallel_agents_uses_current_runtime_before_external_sessions() -> None:
    content = _read("templates/passive-skills/dispatching-parallel-agents/SKILL.md").lower()

    assert "2+ independent lanes" in content
    assert "current runtime" in content
    assert "native subagents" in content
    assert "write-set" in content
    assert "structured handoff" in content
    assert "separate terminal" in content
    assert "advise the user to run multiple parallel instances" not in content


def test_project_map_gate_references_routing_and_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-project-map-gate/SKILL.md").lower()

    assert "spec-kit-workflow-routing" in content
    assert "spec-kit-project-learning" in content
    assert "route selection" in content
    assert "shared memory capture layer" in content
    assert "sp-map-scan" in content
    assert "sp-map-build" in content


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
    assert "learning start --command <command-name>" in content
    assert "hook review-learning --command <command-name>" in content
    assert "command shape: `{{specify-subcmd:hook capture-learning --command <command-name>" in content
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
