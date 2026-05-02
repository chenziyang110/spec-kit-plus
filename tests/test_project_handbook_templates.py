from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_project_handbook_template_exists_and_routes_to_project_map():
    content = _read("templates/project-handbook-template.md")

    assert "# Project Handbook" in content
    assert "## System Summary" in content
    assert "## System Boundaries" in content
    assert "## High-Value Capabilities" in content
    assert "## Shared Surfaces" in content
    assert "## Risky Coordination Points" in content
    assert "## Change-Propagation Hotspots" in content
    assert "## Change Impact Guide" in content
    assert "## Verification Entry Points" in content
    assert "## Known Unknowns" in content
    assert "## Low-Confidence Areas" in content
    assert "## Atlas Views" in content
    assert "## Where To Read Next" in content
    assert "## Topic Map" in content
    assert "## Quick Navigation (Layer 1)" in content
    assert "`.specify/project-map/QUICK-NAV.md`" in content
    assert "`.specify/project-map/index/atlas-index.json`" in content
    assert "`.specify/project-map/root/ARCHITECTURE.md`" in content
    assert "`.specify/project-map/modules/<module-id>/OVERVIEW.md`" in content
    assert "dictionary-style atlas entry surface" in content
    assert "task routes, symptom routes, shared-surface hotspots, verification routes, and propagation-risk routes" in content
    assert "which module most likely owns the touched area" in content


def test_project_map_templates_share_metadata_contract():
    for rel_path in [
        "templates/project-map/root/ARCHITECTURE.md",
        "templates/project-map/root/STRUCTURE.md",
        "templates/project-map/root/CONVENTIONS.md",
        "templates/project-map/root/INTEGRATIONS.md",
        "templates/project-map/root/WORKFLOWS.md",
        "templates/project-map/root/TESTING.md",
        "templates/project-map/root/OPERATIONS.md",
    ]:
        content = _read(rel_path)
        assert "**Last Updated:**" in content
        assert "**Coverage Scope:**" in content
        assert "**Primary Evidence:**" in content
        assert "**Update When:**" in content


def test_project_map_templates_encode_coverage_model_sections():
    architecture = _read("templates/project-map/root/ARCHITECTURE.md")
    structure = _read("templates/project-map/root/STRUCTURE.md")
    integrations = _read("templates/project-map/root/INTEGRATIONS.md")
    workflows = _read("templates/project-map/root/WORKFLOWS.md")
    testing = _read("templates/project-map/root/TESTING.md")
    operations = _read("templates/project-map/root/OPERATIONS.md")

    assert "## Change Propagation Paths" in architecture
    assert "## High-Value Capabilities" in architecture
    assert "## Ownership and Truth Map" in architecture
    assert "## Known Architectural Unknowns" in architecture
    assert "## Dependency Graph and Coupling Hotspots" in architecture
    assert "## Common Extension Paths" in structure
    assert "## Consumer and Entry Surfaces" in structure
    assert "## Change Surface Matrix" in structure
    assert "## API and Exported Surfaces" in integrations
    assert "## Contract Boundaries" in integrations
    assert "## Configuration and Feature-Control Surfaces" in integrations
    assert "## Compatibility and Versioning Strategy" in integrations
    assert "## Security and Trust Boundaries" in integrations
    assert "## Capability Flows" in workflows
    assert "## Runtime Data and Event Flows" in workflows
    assert "## Key Business Lifecycles" in workflows
    assert "## State and Entity Lifecycles" in workflows
    assert "## Failure and Recovery Flows" in workflows
    assert "## Capability Verification Map" in testing
    assert "## Test Pyramid and Quality Gates" in testing
    assert "## Change-Impact Verification Matrix" in testing
    assert "## Verification Entry Points" in testing
    assert "## Deployment and Runtime Topology" in operations
    assert "## Observability Design" in operations
    assert "## Failure Modes and Recovery Playbooks" in operations
    assert "## Runtime State Locations" in operations
    assert "## Known Runtime Unknowns" in operations


def test_project_map_templates_require_full_detail_sections_for_high_value_facts():
    architecture = _read("templates/project-map/root/ARCHITECTURE.md")
    structure = _read("templates/project-map/root/STRUCTURE.md")
    conventions = _read("templates/project-map/root/CONVENTIONS.md")
    integrations = _read("templates/project-map/root/INTEGRATIONS.md")
    workflows = _read("templates/project-map/root/WORKFLOWS.md")
    testing = _read("templates/project-map/root/TESTING.md")
    operations = _read("templates/project-map/root/OPERATIONS.md")

    assert "## Key Components and Responsibilities" in architecture
    assert "## Internal Boundaries and Critical Seams" in architecture
    assert "## Critical File Families" in structure
    assert "## Key Components by Area" in structure
    assert "## Change Surface Matrix" in structure
    assert "## Contract and Compatibility Conventions" in conventions
    assert "## State and Data Semantics" in conventions
    assert "## Config and Option Propagation" in conventions
    assert "## Development Workflow and Review Conventions" in conventions
    assert "## Protocol and Bridge Seams" in integrations
    assert "## Toolchain, Packaging, and Runtime Invariants" in integrations
    assert "## Configuration and Feature-Control Surfaces" in integrations
    assert "## Security and Trust Boundaries" in integrations
    assert "## Entry Points, Contracts, and Handoffs" in workflows
    assert "## State Transitions and Compatibility Notes" in workflows
    assert "## Runtime Data and Event Flows" in workflows
    assert "## State and Entity Lifecycles" in workflows
    assert "`sp-prd` as a peer workflow to `sp-specify`" in workflows
    assert "does not automatically hand off to planning" in workflows
    assert "## Contract Verification Surfaces" in testing
    assert "## Build, Runtime, and Recovery Verification" in testing
    assert "## Test Pyramid and Quality Gates" in testing
    assert "## Build and Packaging Playbooks" in operations
    assert "## Runtime and Toolchain Invariants" in operations
    assert "## Observability Design" in operations
    assert "## Failure Modes and Recovery Playbooks" in operations
    assert "### Capability:" in architecture
    assert "- Owner:" in architecture
    assert "- Truth lives:" in architecture
    assert "- Extend here:" in architecture
    assert "- Minimum verification:" in architecture
    assert "- Failure modes:" in architecture
    assert "- Confidence:" in architecture


def test_project_handbook_template_points_readers_to_deep_detail_layer():
    content = _read("templates/project-handbook-template.md")

    assert "open `.specify/project-map/QUICK-NAV.md`" in content
    assert "The handbook is the index-first entrypoint." in content
    assert "The topical project-map documents hold the full technical detail." in content
    assert "Treat the combined handbook/project-map set as the repository's atlas-style technical encyclopedia." in content
    assert "Use `Where To Read Next` for task-oriented routing." in content


def test_project_handbook_template_guides_architecture_level_summary_content():
    content = _read("templates/project-handbook-template.md")

    assert "project type, primary technology stack, build/dependency tooling, and deployment shape" in content.lower()
    assert "major capability surfaces, runtime units, and architectural boundaries" in content.lower()
    assert "the fastest route from a proposed code change to the affected atlas views" in content.lower()
    assert "point to the topic docs instead of duplicating deep detail" in content.lower()
    assert "list the highest-value capabilities a newcomer should understand first" in content.lower()
    assert "current stale, inferred, or weakly evidenced areas" in content.lower()
    assert "tie low-confidence areas back to specific capabilities, workflows, or boundaries" in content.lower()


def test_project_map_templates_guide_technical_document_grade_depth():
    architecture = _read("templates/project-map/root/ARCHITECTURE.md").lower()
    structure = _read("templates/project-map/root/STRUCTURE.md").lower()
    conventions = _read("templates/project-map/root/CONVENTIONS.md").lower()
    integrations = _read("templates/project-map/root/INTEGRATIONS.md").lower()
    workflows = _read("templates/project-map/root/WORKFLOWS.md").lower()
    testing = _read("templates/project-map/root/TESTING.md").lower()
    operations = _read("templates/project-map/root/OPERATIONS.md").lower()

    assert "top-level architecture pattern, deployment shape, and major module dependencies" in architecture
    assert "core classes, interfaces, abstract types, enums, or major functions" in architecture
    assert "dependency direction, shared abstractions, coupling hotspots, and blast radius" in architecture
    assert "major directories, representative subdirectories, and the kinds of files they own" in structure
    assert "what belongs there and what should not be added there" in structure
    assert "what breaks, what must be reviewed, and which shared surfaces are affected when a file family changes" in structure
    assert "design patterns, naming rules, directory customs, configuration management, and utility locations" in conventions
    assert "state semantics, compatibility assumptions, and project-specific contract rules" in conventions
    assert "branch strategy, review expectations, and local-development conventions" in conventions
    assert "api surfaces, external tools, protocol seams, and runtime boundaries" in integrations
    assert "request/response shapes, command/query surfaces, or exported endpoint families" in integrations
    assert "feature flags, environment switches, hidden config coupling, compatibility rules, and trust boundaries" in integrations
    assert "entry-to-exit data flow for core business or runtime workflows" in workflows
    assert "handoff fields, state transitions, and compatibility notes" in workflows
    assert "runtime data flow, event flow, workflow orchestration, and entity or state-machine lifecycles" in workflows
    assert "smallest trustworthy proofs for mapped contracts, flows, and integrations" in testing
    assert "regression-sensitive areas that deserve explicit verification callouts" in testing
    assert "test pyramid, quality gates, and the verification matrix for change-impact hotspots" in testing
    assert "build, startup, runtime, troubleshooting, and recovery details" in operations
    assert "operator-facing playbooks and runtime unknowns" in operations
    assert "deployment topology, process or network dependencies, observability design, and fmea-style recovery framing" in operations
    assert "owner, truth lives, extend here, minimum verification, failure modes, and confidence" in architecture
    assert "verified / inferred / unknown-stale" in architecture
