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


def test_project_map_templates_require_full_detail_sections_for_high_value_facts():
    architecture = _read("templates/project-map/ARCHITECTURE.md")
    structure = _read("templates/project-map/STRUCTURE.md")
    conventions = _read("templates/project-map/CONVENTIONS.md")
    integrations = _read("templates/project-map/INTEGRATIONS.md")
    workflows = _read("templates/project-map/WORKFLOWS.md")
    testing = _read("templates/project-map/TESTING.md")
    operations = _read("templates/project-map/OPERATIONS.md")

    assert "## Key Components and Responsibilities" in architecture
    assert "## Internal Boundaries and Critical Seams" in architecture
    assert "## Critical File Families" in structure
    assert "## Key Components by Area" in structure
    assert "## Contract and Compatibility Conventions" in conventions
    assert "## State and Data Semantics" in conventions
    assert "## Config and Option Propagation" in conventions
    assert "## Protocol and Bridge Seams" in integrations
    assert "## Toolchain, Packaging, and Runtime Invariants" in integrations
    assert "## Entry Points, Contracts, and Handoffs" in workflows
    assert "## State Transitions and Compatibility Notes" in workflows
    assert "## Contract Verification Surfaces" in testing
    assert "## Build, Runtime, and Recovery Verification" in testing
    assert "## Build and Packaging Playbooks" in operations
    assert "## Runtime and Toolchain Invariants" in operations


def test_project_handbook_template_points_readers_to_deep_detail_layer():
    content = _read("templates/project-handbook-template.md")

    assert "The handbook is the index-first entrypoint." in content
    assert "The topical project-map documents hold the full technical detail." in content
