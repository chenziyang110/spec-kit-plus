from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANNED_FILES = [
    "README.md",
    "PROJECT-HANDBOOK.md",
    "docs/quickstart.md",
    "docs/project-cognition-compatibility-inventory.md",
    "templates/project-handbook-template.md",
    "templates/commands/fast.md",
    "templates/commands/quick.md",
    "templates/commands/implement.md",
    "templates/commands/analyze.md",
    "templates/commands/debug.md",
    "templates/commands/explain.md",
    "templates/commands/test-scan.md",
    "templates/commands/test-build.md",
    "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
]
LEGACY_TOKENS = ("BUILD-HANDBOOK.md", "DEBUG-HANDBOOK.md", ".specify/project-map/")
LOWERCASE_LEGACY_TOKENS = tuple(token.lower() for token in LEGACY_TOKENS)
ALLOWLIST = {
    "README.md",
    "PROJECT-HANDBOOK.md",
    "docs/quickstart.md",
    "docs/project-cognition-compatibility-inventory.md",
    "templates/project-handbook-template.md",
    "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
}


def test_legacy_runtime_surface_tokens_are_confined_to_the_allowlist() -> None:
    unexpected: list[str] = []

    for rel_path in SCANNED_FILES:
        path = PROJECT_ROOT / rel_path
        assert path.exists(), f"{rel_path} must exist for downstream convergence checks"

        if rel_path in ALLOWLIST:
            continue

        text = path.read_text(encoding="utf-8").lower()
        if any(token in text for token in LOWERCASE_LEGACY_TOKENS):
            unexpected.append(rel_path)

    assert unexpected == []
