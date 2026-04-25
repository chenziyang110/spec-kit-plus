from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def test_workflow_routing_references_map_gate_and_project_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "spec-kit-project-map-gate" in content
    assert "spec-kit-project-learning" in content
    assert "sp-test" in content
    assert "route into the right active `sp-*` workflow" in content
    assert "hard brownfield context gate" in content
    assert "learning-start" in content
    assert "learning-capture" in content


def test_project_map_gate_references_routing_and_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-project-map-gate/SKILL.md").lower()

    assert "spec-kit-workflow-routing" in content
    assert "spec-kit-project-learning" in content
    assert "route selection" in content
    assert "shared memory capture layer" in content
    assert "sp-map-codebase" in content


def test_project_learning_defines_explicit_start_and_capture_matrix_for_core_workflows() -> None:
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md").lower()

    workflow_commands = {
        "sp-specify": "specify",
        "sp-plan": "plan",
        "sp-tasks": "tasks",
        "sp-test": "test",
        "sp-implement": "implement",
        "sp-debug": "debug",
        "sp-fast": "fast",
        "sp-quick": "quick",
        "sp-map-codebase": "map-codebase",
    }

    for workflow_name, cli_name in workflow_commands.items():
        assert workflow_name in content
        assert f"specify learning start --command {cli_name}" in content
        assert f"specify learning capture --command {cli_name}" in content

    assert "learning-start trigger matrix" in content
    assert "learning-capture trigger matrix" in content
    assert "consume first" in content
