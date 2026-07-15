from pathlib import Path

import json

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


def _write_external_evidence_blocker(feature_dir: Path, *, completion_impact: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Run protected pipeline verification\n",
        encoding="utf-8",
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True, exist_ok=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "changed_paths": [".gitlab-ci.yml"],
                "validation": [{"command": "tsc --noEmit", "status": "passed"}],
                "blockers": [
                    {
                        "classification": "external",
                        "owner": "external-system",
                        "evidence": "Protected pipeline requires a pushed commit",
                        "exact_next_action": "Push the checkpoint and run the protected pipeline",
                        "approval_question": None,
                        "unblock_criteria": "The protected pipeline reports success",
                        "implementation_can_continue": True,
                        "completion_impact": completion_impact,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_commit_validation_allows_explicit_external_evidence_checkpoint(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "validating")
    _write_external_evidence_blocker(
        feature_dir, completion_impact="mandatory_for_completion"
    )

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "ok"
    assert result.data["commit_intent"] == "external-evidence-checkpoint"
    assert result.data["workflow_finalized"] is False


def test_commit_validation_rejects_checkpoint_without_mandatory_external_blocker(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "validating")
    _write_external_evidence_blocker(feature_dir, completion_impact="optional_cleanup")

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "blocked"
    assert any("mandatory external" in message.lower() for message in result.errors)


def test_commit_validation_rejects_checkpoint_without_implement_tracker(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_external_evidence_blocker(
        feature_dir, completion_impact="mandatory_for_completion"
    )

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "blocked"
    assert any("nonterminal implement-tracker" in message for message in result.errors)


def test_commit_validation_rejects_checkpoint_with_unknown_tracker_status(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "banana")
    _write_external_evidence_blocker(
        feature_dir, completion_impact="mandatory_for_completion"
    )

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "blocked"
    assert any("status must be one of" in message for message in result.errors)


def test_commit_validation_rejects_checkpoint_for_orphan_lifecycle_task(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "blocked")
    _write_external_evidence_blocker(
        feature_dir, completion_impact="mandatory_for_completion"
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T002 Different task\n", encoding="utf-8"
    )

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "blocked"
    assert any("task-local mandatory external" in message for message in result.errors)


def test_commit_validation_rejects_feature_outside_project(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = tmp_path / "outside-feature"
    _write_implement_tracker(feature_dir, "blocked")
    _write_external_evidence_blocker(
        feature_dir, completion_impact="mandatory_for_completion"
    )

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "blocked"
    assert any("inside project_root" in message for message in result.errors)


def test_commit_validation_rejects_unknown_commit_intent(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {"commit_message": "chore: checkpoint", "commit_intent": "skip-gates"},
    )

    assert result.status == "blocked"
    assert any("commit_intent" in message for message in result.errors)


def test_commit_validation_rejects_checkpoint_with_incomplete_blocker_contract(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_implement_tracker(feature_dir, "validating")
    _write_external_evidence_blocker(
        feature_dir, completion_impact="mandatory_for_completion"
    )
    lifecycle_path = feature_dir / "implementation-review" / "tasks" / "T001.json"
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    del lifecycle["blockers"][0]["approval_question"]
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {
            "commit_message": "chore(ci): checkpoint protected pipeline config",
            "feature_dir": str(feature_dir),
            "commit_intent": "external-evidence-checkpoint",
        },
    )

    assert result.status == "blocked"
    assert any("mandatory external" in message.lower() for message in result.errors)


def test_commit_validation_blocks_nonconforming_commit_message(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.commit.validate",
        {"commit_message": "workflow quality hooks"},
    )

    assert result.status == "blocked"
    assert any("commit message" in message.lower() for message in result.errors)
