from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_modifying_workflows_use_the_shared_execution_overview() -> None:
    classic = (ROOT / "templates/command-partials/common/execution-bootstrap.md").read_text(encoding="utf-8")
    advanced = (ROOT / "templates/advanced-skills/_shared/execution-bootstrap.md").read_text(encoding="utf-8")

    for content in (classic, advanced):
        lowered = content.lower()
        assert "specify-runtime execution overview" in lowered
        assert "execution-overview-v1" in lowered
        assert "fast, debug, implement, and quick" in lowered
        assert "before guard" in lowered
        assert "--since-revision" in lowered
        assert "do not" in lowered and "poll on a timer" in lowered
        assert "coordination_revision" in lowered
        assert "snapshot_sha256" in lowered
        assert "not an ambient file capture" in " ".join(lowered.split())
        assert "nonterminal run" not in lowered


def test_quick_uses_execution_overview_as_primary_and_keeps_preflight_compatible() -> None:
    paths = (
        ROOT / "templates/commands/quick.md",
        ROOT / "templates/advanced-skills/spx-quick/SKILL.md",
    )

    for path in paths:
        content = path.read_text(encoding="utf-8").lower()
        assert "specify-runtime execution overview" in content
        assert "quick preflight" in content
        assert "compatibility" in content


def test_handbooks_define_one_execution_overview_as_the_global_view() -> None:
    for path in (
        ROOT / "PROJECT-HANDBOOK.md",
        ROOT / "templates/project-handbook-template.md",
    ):
        content = path.read_text(encoding="utf-8").lower()
        assert "execution-overview-v1" in content
        assert "task state" in content
        assert "work/activity" in content
        assert "coordination context" in content
        assert "not task selection authority" in content
        assert "nonterminal run" not in content


def test_implement_treats_global_overview_as_context_not_target_authority() -> None:
    for path in (
        ROOT / "templates/commands/implement.md",
        ROOT / "templates/advanced-skills/spx-implement/SKILL.md",
    ):
        content = path.read_text(encoding="utf-8").lower()
        assert "execution overview" in content
        assert "coordination context" in content
        assert "task selection authority" in content
