from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return read_template(rel_path)


TARGETS = [
    "templates/commands/fast.md",
    "templates/commands/quick.md",
    "templates/commands/debug.md",
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
    "templates/commands/implement.md",
]


def test_ordinary_sp_workflows_use_shared_project_map_hard_gate() -> None:
    required_phrases = [
        "project-map hard gate",
        "must pass an atlas gate before",
        "PROJECT-HANDBOOK.md",
        "atlas.entry",
        "atlas.index.status",
        "atlas.index.atlas",
        "at least one relevant root topic document",
        "at least one relevant module overview document",
    ]

    for rel_path in TARGETS:
        content = _read(rel_path)
        lowered = content.lower()
        for phrase in required_phrases:
            assert phrase.lower() in lowered, f"{rel_path} missing: {phrase}"
