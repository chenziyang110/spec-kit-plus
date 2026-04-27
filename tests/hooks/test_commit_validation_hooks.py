from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-commit-validation-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_implement_tracker(feature_dir: Path, status: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                f"status: {status}",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: execute batch",
                "next_action: collect worker result",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_commit_validation_allows_conventional_message_with_resolved_tracker(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "resolved")

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {"commit_message": "feat: add workflow quality hooks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_commit_validation_blocks_nonterminal_tracker_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "blocked")

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {"commit_message": "feat: add workflow quality hooks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("blocked" in message for message in result.errors)


def test_commit_validation_blocks_nonconforming_commit_message(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {"commit_message": "workflow quality hooks"},
    )

    assert result.status == "blocked"
    assert any("commit message" in message.lower() for message in result.errors)
