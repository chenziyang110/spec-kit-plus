from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_map_scan_template_defines_complete_scan_package_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "sp-map-scan" in content
    assert "sp-map-build" in content
    assert ".specify/project-map/map-scan.md" in content
    assert ".specify/project-map/coverage-ledger.md" in content
    assert ".specify/project-map/coverage-ledger.json" in content
    assert ".specify/project-map/scan-packets/<lane-id>.md" in content
    assert "full project-relevant inventory" in lowered
    assert "nested directories" in lowered
    assert "rg --files" in content
    assert "Git-tracked files" in content
    assert "excluded_from_deep_read" in content
    assert "vendor-cache-build-output" in content
    assert "`unknown` is a scan failure" in content
    assert "`inventory`" in content
    assert "`sampled`" in content
    assert "`deep-read`" in content
    assert "`critical`" in content
    assert "`important`" in content
    assert "`low-risk`" in content
    assert "scan-packets/<lane-id>.md" in content
    assert "Coverage Classification" in content
    assert "Criticality Scoring" in content


def test_map_scan_template_preserves_required_scan_dimensions() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    required_phrases = [
        "project shape and stack",
        "architecture overview",
        "directory ownership",
        "module dependency graph",
        "core code elements",
        "entry and api surfaces",
        "data and state flows",
        "user and maintainer workflows",
        "integrations and protocol boundaries",
        "build, release, and runtime",
        "testing and verification",
        "risk, security, observability, and evolution",
        "template and generated-surface propagation",
        "coverage reverse index",
    ]

    for phrase in required_phrases:
        assert phrase in lowered


def test_map_build_template_refuses_incomplete_scan_packages() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "sp-map-build" in content
    assert "sp-map-scan" in content
    assert "coverage-ledger.json" in content
    assert "scan-packets" in content
    assert "begins with validation, not writing" in lowered
    assert "must not guess and continue" in lowered
    assert "scan gap report" in lowered
    assert "packet results without paths read" in lowered
    assert "packet results that only summarize without evidence" in lowered
    assert "unresolved critical rows" in lowered
    assert "reverse coverage validation" in lowered
    assert "complete-refresh" in content
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/index/*.json" in content
    assert ".specify/project-map/root/*.md" in content
    assert ".specify/project-map/modules/<module-id>/*.md" in content


def test_map_build_template_requires_reverse_coverage_closure() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    required_phrases = [
        "every `critical` row appears in at least one final atlas target",
        "every `important` row appears in a final atlas target",
        "every scan packet is consumed",
        "every accepted packet result has paths read and confidence",
        "owner, consumer, change propagation, and verification",
        "known unknowns",
        "low-confidence areas",
        "deep_stale",
        "excluded bucket has a reason and revisit condition",
    ]

    for phrase in required_phrases:
        assert phrase in lowered
