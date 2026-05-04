from pathlib import Path

import yaml

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _content(path: str) -> str:
    return read_template(path)


def _frontmatter(path: str) -> dict:
    parts = _content(path).split("---", 2)
    return yaml.safe_load(parts[1])


def test_prd_scan_template_defines_reconstruction_scan_contract() -> None:
    content = _content("templates/commands/prd-scan.md")
    frontmatter = _frontmatter("templates/commands/prd-scan.md")
    contract = frontmatter["workflow_contract"]
    lowered = content.lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert ".specify/prd-runs/<run-id>/prd-scan.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/artifact-contracts.json" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/reconstruction-checklist.json" in contract["primary_outputs"]
    assert "read-only reconstruction investigation" in lowered
    assert "must not write `master/master-pack.md`" in content
    assert "must not write `exports/**`" in content
    assert "capability" in lowered
    assert "artifact" in lowered
    assert "boundary" in lowered
    assert "`Evidence`" in content
    assert "`Inference`" in content
    assert "`Unknown`" in content
    assert "`critical`" in content
    assert "`high`" in content
    assert "`standard`" in content
    assert "`auxiliary`" in content
    assert "reconstruction-ready" in content
    assert "blocked-by-gap" in content
    assert "artifact-contracts.json" in content
    assert "reconstruction-checklist.json" in content
    assert "Capability Triage Gate" in content
    assert "Critical Depth Gate" in content
    assert "High Capability Gate" in content
    assert "Evidence Label Gate" in content
    assert "producer-consumer" in lowered
    assert "failure behavior" in lowered


def test_prd_scan_template_preserves_tiers_and_labeling_contract() -> None:
    content = _content("templates/commands/prd-scan.md")
    lowered = content.lower()

    assert "Every consequential claim must preserve `Evidence`, `Inference`, and `Unknown` labeling semantics" in content
    assert "Assign each capability a tier: `critical`, `high`, `standard`, or `auxiliary`." in content
    assert "For `critical` and `high` capabilities, capture stronger reconstruction detail" in content
    assert "must have more than path-only evidence" in lowered
    assert "must be assigned `critical`, `high`, `standard`, or `auxiliary`" in content


def test_prd_build_template_refuses_incomplete_scan_packages() -> None:
    content = _content("templates/commands/prd-build.md")
    frontmatter = _frontmatter("templates/commands/prd-build.md")
    contract = frontmatter["workflow_contract"]
    lowered = content.lower()

    assert "sp-prd-build" in content
    assert "sp-prd-scan" in content
    assert ".specify/prd-runs/<run-id>/workflow-state.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/reconstruction-appendix.md" in contract["primary_outputs"]
    assert "must not become a second repository scan" in lowered
    assert "must not silently fill critical evidence gaps" in lowered
    assert "No New Facts Gate" in content
    assert "Artifact Landing Gate" in content
    assert "Field-Level Coverage Gate" in content
    assert "Inference Ceiling Gate" in content
    assert "Evidence Label Gate" in content
    assert "Classification Export Gate" in content
    assert "`Evidence`" in content
    assert "`Inference`" in content
    assert "`Unknown`" in content
    assert "`ui`" in content
    assert "`service`" in content
    assert "`mixed`" in content
    assert "reverse coverage validation" in lowered


def test_prd_build_template_preserves_label_and_classification_semantics() -> None:
    content = _content("templates/commands/prd-build.md")
    lowered = content.lower()

    assert "Final outputs must preserve `Evidence`, `Inference`, and `Unknown` labels" in content
    assert "Project classification from the scan package: `ui`, `service`, or `mixed`." in content
    assert "Respect classification-aware export semantics" in content
    assert "outputs and build validation must preserve `Evidence`, `Inference`, and `Unknown` handling" in content
    assert "must not strip `Evidence`, `Inference`, or `Unknown` labels" in content
    assert "fixed export set" in lowered


def test_prd_template_is_deprecated_and_routes_to_scan_build() -> None:
    content = _content("templates/commands/prd.md")
    lowered = content.lower()

    assert "deprecated" in lowered
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "compatibility" in lowered
    assert "no longer" in lowered or "instead" in lowered
