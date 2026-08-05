from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_classic_and_advanced_consumers_require_exact_catalog_binding() -> None:
    surfaces = [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
        "templates/advanced-skills/_shared/project-cognition.md",
    ]

    for surface in surfaces:
        content = read(surface)
        assert "exact binding consumer" in content, surface
        assert "catalog_page" in content, surface
        assert "selected_concepts" in content, surface
        assert "lexicon_generation_id" in content, surface


def test_classic_and_advanced_creation_surfaces_emit_semantic_cards() -> None:
    surfaces = [
        "templates/commands/map-scan.md",
        "templates/advanced-skills/spx-map-scan/references/scan-worker.md",
    ]

    for surface in surfaces:
        content = read(surface)
        for field in (
            "responsibility",
            "capabilities",
            "symptoms",
            "user_terms",
            "exclusions",
        ):
            assert field in content, f"{surface}: missing {field}"


def test_classic_and_advanced_builds_verify_resolved_exact_binding() -> None:
    surfaces = [
        "templates/commands/map-build.md",
        "templates/advanced-skills/spx-map-build/SKILL.md",
    ]

    for surface in surfaces:
        content = read(surface)
        assert "lexicon --mode catalog" in content, surface
        assert "resolution_state=resolved_exact" in content, surface
        assert "symptom-first" in content, surface


def test_human_and_init_guidance_stays_aligned_with_exact_binding() -> None:
    surfaces = [
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "src/specify_cli/__init__.py",
    ]

    for surface in surfaces:
        content = read(surface).lower()
        assert "exact" in content and "binding" in content, surface
