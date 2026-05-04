from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRD_TEMPLATE_DIR = PROJECT_ROOT / "templates" / "prd"

EXPECTED_PRD_TEMPLATES = {
    "master-pack-template.md": [
        "# PRD Master Pack",
        "single truth source",
        "Evidence",
        "Inference",
        "Unknown",
        "Export Map",
        "Critical Capability Dossiers",
        "Coverage and Export Map",
    ],
    "export-prd-template.md": [
        "# Product Requirements Document",
        "master-pack.md",
        "Users and Roles",
        "Capability Overview",
        "Unknowns and Evidence Confidence",
    ],
    "export-ui-spec-template.md": [
        "# UI Specification",
        "`ui`",
        "`mixed`",
        "Navigation Model",
        "Page Inventory",
        "UI Unknowns",
    ],
    "export-service-spec-template.md": [
        "# Service Specification",
        "`service`",
        "`mixed`",
        "Entrypoint Inventory",
        "Service Flows",
        "Service Unknowns",
    ],
    "export-flows-ia-template.md": [
        "# Flows and Information Architecture",
        "Page Tree",
        "Task Flows",
        "Navigation Transitions",
    ],
    "export-data-rules-template.md": [
        "# Data and Rules Appendix",
        "Entities",
        "State Model",
        "Validation Rules",
        "Permission Rules",
    ],
    "export-internal-brief-template.md": [
        "# Internal Implementation Brief",
        "Critical Capability-to-Code Mapping",
        "Screen/Service-to-Code Mapping",
        "Planning Handoff Notes",
        "Verification Clues",
    ],
    "export-config-contracts-template.md": [
        "# Configuration Contracts",
        "Config Surface",
        "Default Value",
        "Precedence",
    ],
    "export-protocol-contracts-template.md": [
        "# Protocol Contracts",
        "Boundary",
        "Field Mapping",
        "Compatibility",
    ],
    "export-state-machines-template.md": [
        "# State Machines",
        "State Set",
        "Transition Trigger",
        "Recovery",
    ],
    "export-error-semantics-template.md": [
        "# Error Semantics",
        "Trigger",
        "Exposure",
        "Recovery Behavior",
    ],
    "export-verification-surface-template.md": [
        "# Verification Surface",
        "Minimum Verification Command",
        "Locked Behavior",
        "Parity Checkpoint",
    ],
    "export-reconstruction-risks-template.md": [
        "# Reconstruction Risks",
        "Critical Gap",
        "Unknown",
        "Fidelity Risk",
    ],
}


def test_prd_template_asset_directory_contains_expected_files() -> None:
    assert PRD_TEMPLATE_DIR.is_dir()

    actual = {path.name for path in PRD_TEMPLATE_DIR.glob("*.md")}

    assert actual == set(EXPECTED_PRD_TEMPLATES)


def test_prd_export_templates_have_minimal_required_structure() -> None:
    for filename, expected_fragments in EXPECTED_PRD_TEMPLATES.items():
        content = (PRD_TEMPLATE_DIR / filename).read_text(encoding="utf-8")

        assert "[PROJECT]" in content
        assert "[RUN_ID]" in content
        assert "Evidence/Inference/Unknown" in content
        for fragment in expected_fragments:
            assert fragment in content


def test_prd_master_pack_template_is_export_truth_source() -> None:
    content = (PRD_TEMPLATE_DIR / "master-pack-template.md").read_text(encoding="utf-8")

    assert "All exports must derive from this master pack" in content
    assert "Do not maintain export-only facts" in content
    assert "Export Completeness Check" in content
    assert "every master capability appears in at least one export" in content
    assert "Config Dossiers" in content
    assert "Protocol Dossiers" in content
    assert "State Machine Dossiers" in content
    assert "Error Semantic Dossiers" in content
    assert "Verification Dossiers" in content
    assert "Export Landing Map" in content


def test_prd_master_pack_template_requires_tiered_capability_fields() -> None:
    content = (PRD_TEMPLATE_DIR / "master-pack-template.md").read_text(encoding="utf-8")

    assert "Core Value Proposition" in content
    assert "| Capability ID | Tier |" in content
    assert "## Critical Capability Dossiers" in content
    assert "Implementation Mechanisms" in content
    assert "Format or Protocol Matrix" in content
    assert "Edge Cases and Failure Paths" in content
    assert "Source Traceability" in content


def test_prd_export_template_calls_out_depth_qualified_capabilities() -> None:
    content = (PRD_TEMPLATE_DIR / "export-prd-template.md").read_text(encoding="utf-8")

    assert "Critical Capability Notes" in content
    assert "depth-qualified" in content
    assert "surface-covered" in content


def test_internal_brief_template_maps_critical_capabilities_to_code() -> None:
    content = (PRD_TEMPLATE_DIR / "export-internal-brief-template.md").read_text(encoding="utf-8")

    assert "Critical Capability-to-Code Mapping" in content
    assert "Primary Files or Functions" in content
    assert "Verification Clues" in content
