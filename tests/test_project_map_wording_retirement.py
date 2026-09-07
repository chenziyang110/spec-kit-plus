from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_WORKFLOW_DIRS = (
    PROJECT_ROOT / "templates" / "commands",
    PROJECT_ROOT / "templates" / "command-partials",
    PROJECT_ROOT / "templates" / "command-references",
)

RETIRED_POSITIVE_TERMS = (
    "project-map-backed intake contract",
    "project-map first",
    "project map state protocol",
)
REQUIRED_SCANNED_FILES = {
    "templates/command-partials/common/pre-analysis-protocol.md",
    "templates/command-references/debug/intake-and-debug-checkpoint.md",
    "templates/commands/map-build.md",
}


def test_active_workflow_surfaces_do_not_use_retired_project_map_authority_terms() -> None:
    matches: list[str] = []
    scanned_files: set[str] = set()

    for root in ACTIVE_WORKFLOW_DIRS:
        for path in sorted(root.rglob("*.md")):
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            scanned_files.add(relative_path)
            lowered = path.read_text(encoding="utf-8").lower()
            for term in RETIRED_POSITIVE_TERMS:
                if term in lowered:
                    matches.append(f"{relative_path}: {term}")

    assert REQUIRED_SCANNED_FILES <= scanned_files
    assert matches == []
