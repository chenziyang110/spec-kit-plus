from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_project_handbook_template_exists_and_routes_to_project_map():
    content = _read("templates/project-handbook-template.md")

    assert "# Project Handbook" in content
    assert "## System Summary" in content
    assert "## Shared Surfaces" in content
    assert "## Risky Coordination Points" in content
    assert "## Change-Propagation Hotspots" in content
    assert "## Verification Entry Points" in content
    assert "## Known Unknowns" in content
    assert "## Topic Map" in content
    assert ".specify/project-map/ARCHITECTURE.md" in content
    assert ".specify/project-map/OPERATIONS.md" in content


def test_project_map_templates_share_metadata_contract():
    for rel_path in [
        "templates/project-map/ARCHITECTURE.md",
        "templates/project-map/STRUCTURE.md",
        "templates/project-map/CONVENTIONS.md",
        "templates/project-map/INTEGRATIONS.md",
        "templates/project-map/WORKFLOWS.md",
        "templates/project-map/TESTING.md",
        "templates/project-map/OPERATIONS.md",
    ]:
        content = _read(rel_path)
        assert "**Last Updated:**" in content
        assert "**Coverage Scope:**" in content
        assert "**Primary Evidence:**" in content
        assert "**Update When:**" in content


def test_project_map_templates_encode_coverage_model_sections():
    architecture = _read("templates/project-map/ARCHITECTURE.md")
    structure = _read("templates/project-map/STRUCTURE.md")
    integrations = _read("templates/project-map/INTEGRATIONS.md")
    workflows = _read("templates/project-map/WORKFLOWS.md")
    testing = _read("templates/project-map/TESTING.md")
    operations = _read("templates/project-map/OPERATIONS.md")

    assert "## Change Propagation Paths" in architecture
    assert "## Known Architectural Unknowns" in architecture
    assert "## Consumer and Entry Surfaces" in structure
    assert "## Contract Boundaries" in integrations
    assert "## Failure and Recovery Flows" in workflows
    assert "## Verification Entry Points" in testing
    assert "## Known Runtime Unknowns" in operations
