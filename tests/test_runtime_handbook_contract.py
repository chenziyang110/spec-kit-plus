from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_map_build_runtime_outputs_are_two_workflow_handbooks() -> None:
    content = _read("templates/commands/map-build.md")

    assert "DEBUG-HANDBOOK.md" in content
    assert "BUILD-HANDBOOK.md" in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/project-map/QUICK-NAV.md" not in content
    assert ".specify/project-map/index/*.json" not in content
    assert ".specify/project-map/root/*.md" not in content
    assert ".specify/project-map/modules/<module-id>/*.md" not in content


def test_context_loading_gradient_uses_handbook_gate_instead_of_layered_atlas_gate() -> None:
    content = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered = content.lower()

    assert "DEBUG-HANDBOOK.md" in content
    assert "BUILD-HANDBOOK.md" in content
    assert "required chapter ids" in lowered
    assert "PROJECT-HANDBOOK.md" not in content
    assert "atlas.entry" not in content
    assert "root topic document" not in lowered
    assert "module overview document" not in lowered


def test_debug_template_requires_debug_handbook_only() -> None:
    content = _read("templates/commands/debug.md")
    lowered = content.lower()

    assert "DEBUG-HANDBOOK.md" in content
    assert "DEBUG-WORKFLOW-CONTRACT" in content
    assert "SYMPTOM-TO-SURFACE-ROUTING" in content
    assert "SYSTEM-TOPOLOGY-FOR-DEBUG" in content
    assert "INVESTIGATION-PLAYBOOKS" in content
    assert "VERIFICATION-AND-EXIT" in content
    assert "only primary runtime atlas read surface" in lowered
    assert "support-only project-map artifacts" in lowered
    assert "atlas.entry" not in content


def test_specify_plan_tasks_templates_require_build_handbook_only() -> None:
    expected_chapters = (
        "BUILD-WORKFLOW-CONTRACT",
        "PRODUCT-AND-CAPABILITY-MAP",
        "WORKFLOW-SEQUENCES",
        "MODULE-COLLABORATION",
        "CHANGE-PROPAGATION-RISKS",
    )

    for relative_path in (
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ):
        content = _read(relative_path)
        lowered = content.lower()
        assert "BUILD-HANDBOOK.md" in content
        for chapter in expected_chapters:
            assert chapter in content
        assert "build-handbook.md" in lowered
        assert "atlas.entry" not in content
