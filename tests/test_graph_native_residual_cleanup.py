from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANNED_FILES = [
    "tests/execution/test_packet_validator.py",
    "tests/codex_team/test_worker_bootstrap.py",
]
LEGACY_TOKENS = (
    "BUILD-HANDBOOK.md",
    "DEBUG-HANDBOOK.md",
    "PROJECT-HANDBOOK.md",
    "root navigation artifact",
    "runtime handbook",
)
ALLOWLIST = {
    "docs/project-cognition-compatibility-inventory.md",
}


def test_handbook_first_tokens_do_not_reappear_in_migrate_now_surfaces() -> None:
    unexpected: list[str] = []
    for rel_path in SCANNED_FILES:
        if rel_path in ALLOWLIST:
            continue
        text = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
        if any(token in text for token in LEGACY_TOKENS):
            unexpected.append(rel_path)
    assert unexpected == []
