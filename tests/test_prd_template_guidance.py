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


def test_prd_template_defines_deprecated_compatibility_contract() -> None:
    frontmatter = _frontmatter()
    contract = frontmatter["workflow_contract"]

    assert frontmatter["description"].startswith("Deprecated compatibility entrypoint")
    assert "deprecated compatibility" in contract["when_to_use"].lower()
    assert "sp-prd-scan" in contract["primary_objective"]
    assert "sp-prd-build" in contract["primary_objective"]
    assert ".specify/prd-runs/<run-id>/prd-scan.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in contract["primary_outputs"]
    assert "sp-prd-scan" in contract["default_handoff"]
    assert "sp-prd-build" in contract["default_handoff"]


def test_prd_template_routes_to_scan_then_build() -> None:
    content = _content()
    lowered = content.lower()

    assert "deprecated" in lowered
    assert "compatibility" in lowered
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "instead" in lowered or "no longer" in lowered
    assert "## Workflow Contract Summary" in content
    assert "## Migration Path" in content
    assert "## Guardrails" in content


def test_prd_template_is_compatibility_only_not_primary_reverse_prd_lane() -> None:
    content = _content()
    lowered = content.lower()

    assert "deprecated" in lowered
    assert "compatibility" in lowered
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
