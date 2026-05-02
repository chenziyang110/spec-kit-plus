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
        "Capability-to-Module Mapping",
        "Screen/Service-to-Code Mapping",
        "Planning Handoff Notes",
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
