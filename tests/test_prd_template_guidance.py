from pathlib import Path

import yaml

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRD_TEMPLATE = PROJECT_ROOT / "templates" / "commands" / "prd.md"


def _content() -> str:
    return read_template(PRD_TEMPLATE.relative_to(PROJECT_ROOT).as_posix())


def _frontmatter() -> dict:
    parts = _content().split("---", 2)
    return yaml.safe_load(parts[1])


def test_prd_template_defines_primary_workflow_contract() -> None:
    frontmatter = _frontmatter()
    contract = frontmatter["workflow_contract"]

    assert frontmatter["description"].startswith("Use when")
    assert "existing repository" in contract["when_to_use"]
    assert "professional PRD suite" in contract["when_to_use"]
    assert "delivery-grade PRD suite" in contract["primary_objective"]
    assert "repository-backed product truth" in contract["primary_objective"]
    assert ".specify/prd-runs/<run-id>/workflow-state.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/master/master-pack.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in contract["primary_outputs"]
    assert "No automatic handoff into implementation planning" in contract["default_handoff"]


def test_prd_template_uses_shared_command_sections() -> None:
    content = _content()

    assert "## Objective" in content
    assert "## Context" in content
    assert "## Process" in content
    assert "## Output Contract" in content
    assert "## Guardrails" in content
    assert "## Workflow Contract Summary" in content
    assert "routing metadata only" in content.lower()


def test_prd_template_requires_brownfield_state_and_artifact_paths() -> None:
    content = _content()

    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/index/status.json" in content
    assert "workflow-state.md" in content
    assert ".specify/prd-runs/<run-id>/" in content
    assert ".specify/prd-runs/<run-id>/coverage-matrix.md" in content
    assert ".specify/prd-runs/<run-id>/evidence/" in content
    assert ".specify/prd-runs/<run-id>/master/master-pack.md" in content
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in content


def test_prd_template_requires_mode_classification_and_confidence_marking() -> None:
    content = _content()
    lowered = content.lower()

    assert "classify" in lowered
    assert "`ui`" in content
    assert "`service`" in content
    assert "`mixed`" in content
    assert "Evidence/Inference/Unknown" in content
    assert "`Evidence`" in content
    assert "`Inference`" in content
    assert "`Unknown`" in content
    assert "Unknowns must remain visible" in content


def test_prd_template_keeps_master_pack_as_export_truth_source() -> None:
    content = _content()
    lowered = content.lower()

    assert "master-pack.md" in content
    assert "exports/prd.md" in content
    assert "unified master pack" in lowered
    assert "export completeness" in lowered
    assert "every master capability appears in at least one export" in lowered
    assert "No automatic handoff into implementation planning" in content
