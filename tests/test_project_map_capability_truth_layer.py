from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_capability_and_symptom_index_templates_exist() -> None:
    assert (PROJECT_ROOT / "templates/project-map/index/capabilities.json").exists()
    assert (PROJECT_ROOT / "templates/project-map/index/symptoms.json").exists()


def test_module_workflow_template_requires_lifecycle_and_flow_maps() -> None:
    content = _read("templates/project-map/modules/WORKFLOWS.md")
    assert "## Module Lifecycle" in content
    assert "## Module Flow Map" in content
    assert "## Capability Deep Links" in content
    assert "## Failure and Recovery Notes" in content


def test_deep_workflow_template_requires_truth_layer_sections() -> None:
    content = _read("templates/project-map/modules/deep/workflows/TEMPLATE.md")
    required = [
        "## Lifecycle Diagram",
        "## Flow Diagram",
        "## Entry Points",
        "## Preconditions and Guards",
        "## Failure Branches",
        "## Control Nodes",
        "## Where To Inspect",
        "## Change Impact",
        "## Evidence Links",
        "## Minimum Verification",
        "## Confidence",
    ]
    for heading in required:
        assert heading in content


def test_capability_and_symptom_index_templates_expose_expected_keys() -> None:
    capabilities = json.loads(_read("templates/project-map/index/capabilities.json"))
    symptoms = json.loads(_read("templates/project-map/index/symptoms.json"))

    assert capabilities["version"] == 1
    assert "capabilities" in capabilities
    assert capabilities["module_registry_path"] == ".specify/project-map/index/modules.json"
    assert symptoms["version"] == 1
    assert "symptoms" in symptoms
    assert symptoms["capabilities_path"] == ".specify/project-map/index/capabilities.json"
