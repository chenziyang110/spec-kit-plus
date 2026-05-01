from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_project_handbook_template_routes_to_index_root_and_module_layers():
    handbook = _read("templates/project-handbook-template.md")

    assert "`.specify/project-map/QUICK-NAV.md`" in handbook
    assert "`.specify/project-map/index/atlas-index.json`" in handbook
    assert "`.specify/project-map/index/modules.json`" in handbook
    assert "`.specify/project-map/index/relations.json`" in handbook
    assert "`.specify/project-map/index/status.json`" in handbook
    assert "`.specify/project-map/root/ARCHITECTURE.md`" in handbook
    assert "`.specify/project-map/modules/<module-id>/OVERVIEW.md`" in handbook


def test_quick_nav_includes_symptom_and_verification_lookup_routes():
    quick_nav = _read("templates/project-map/QUICK-NAV.md").lower()

    assert "## by symptom" in quick_nav
    assert "## verification routes" in quick_nav
    assert "shared-surface hotspots" in quick_nav


def test_layered_project_map_template_files_exist():
    for rel_path in [
        "templates/project-map/index/atlas-config.json",
        "templates/project-map/index/atlas-index.json",
        "templates/project-map/index/modules.json",
        "templates/project-map/index/relations.json",
        "templates/project-map/map-state-template.md",
        "templates/project-map/QUICK-NAV.md",
        "templates/project-map/root/ARCHITECTURE.md",
        "templates/project-map/root/STRUCTURE.md",
        "templates/project-map/root/CONVENTIONS.md",
        "templates/project-map/root/INTEGRATIONS.md",
        "templates/project-map/root/WORKFLOWS.md",
        "templates/project-map/root/TESTING.md",
        "templates/project-map/root/OPERATIONS.md",
        "templates/project-map/modules/OVERVIEW.md",
        "templates/project-map/modules/ARCHITECTURE.md",
        "templates/project-map/modules/STRUCTURE.md",
        "templates/project-map/modules/WORKFLOWS.md",
        "templates/project-map/modules/TESTING.md",
        "templates/project-map/modules/deep/capabilities/TEMPLATE.md",
        "templates/project-map/modules/deep/workflows/TEMPLATE.md",
        "templates/project-map/modules/deep/integrations/TEMPLATE.md",
        "templates/project-map/modules/deep/runtime/TEMPLATE.md",
        "templates/project-map/modules/deep/references/TEMPLATE.md",
    ]:
        assert (PROJECT_ROOT / rel_path).exists(), rel_path
