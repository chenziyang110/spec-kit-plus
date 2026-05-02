from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.reconcile import reconcile_lane


def _write_workflow_state(feature_dir: Path, next_command: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-analyze`",
                "- status: `completed`",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_implement_tracker(feature_dir: Path, status: str = "executing") -> None:
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
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_reconcile_marks_consistent_implement_lane_resumable(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.implement")
    _write_implement_tracker(feature_dir, "executing")
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        last_command="implement",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "resumable"
    assert reconciled.last_stable_checkpoint != ""


def test_reconcile_marks_conflicting_implement_lane_uncertain(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.tasks")
    _write_implement_tracker(feature_dir, "executing")
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        last_command="implement",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "uncertain"
    assert "next_command" in reconciled.recovery_reason


def test_reconcile_marks_missing_stage_artifacts_blocked(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        last_command="implement",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "blocked"
