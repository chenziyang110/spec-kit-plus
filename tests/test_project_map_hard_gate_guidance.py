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


def test_ordinary_sp_workflows_use_shared_runtime_handbook_gate() -> None:
    required_phrases = [
        "runtime handbook gate",
        ".specify/project-map/index/status.json",
    ]

    for rel_path in TARGETS:
        content = _read(rel_path)
        lowered = content.lower()
        for phrase in required_phrases:
            assert phrase.lower() in lowered, f"{rel_path} missing: {phrase}"

    debug_content = _read("templates/commands/debug.md").lower()
    assert "debug-handbook.md" in debug_content
    assert "debug-workflow-contract" in debug_content
    assert "pass the handbook gate before investigation moves" in debug_content

    for rel_path in [path for path in TARGETS if path != "templates/commands/debug.md"]:
        content = _read(rel_path).lower()
        assert "must pass the handbook gate before" in content, f"{rel_path} missing handbook-gate phrasing"
        assert "build-handbook.md" in content, f"{rel_path} missing BUILD-HANDBOOK gate"
        assert "build-workflow-contract" in content, f"{rel_path} missing BUILD-WORKFLOW-CONTRACT gate"
