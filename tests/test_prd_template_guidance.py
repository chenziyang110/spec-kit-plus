from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRD_ALIAS_TEMPLATE = PROJECT_ROOT / "templates" / "commands" / "prd.md"


def test_prd_alias_template_is_retired() -> None:
    assert not PRD_ALIAS_TEMPLATE.exists()


def test_canonical_prd_scan_and_build_templates_remain_available() -> None:
    scan = read_template("templates/commands/prd-scan.md")
    build = read_template("templates/commands/prd-build.md")

    assert "sp-prd-scan" in scan
    assert "L4 Reconstruction-Ready" in scan
    assert "config-contracts.json" in scan
    assert "sp-prd-build" in build
    assert "do not reread the repository to fill gaps" in build.lower()
    assert "must not become a second repository scan" in build.lower()
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in build
