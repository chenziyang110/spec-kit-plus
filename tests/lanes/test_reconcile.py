from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.reconcile import reconcile_lane


def _write_workflow_state(
    feature_dir: Path,
    next_command: str,
    *,
    active_command: str = "sp-analyze",
    status: str = "completed",
    phase_mode: str = "analysis-only",
    next_action: str = "continue",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                f"- active_command: `{active_command}`",
                f"- status: `{status}`",
                "",
                "## Phase Mode",
                "",
                f"- phase_mode: `{phase_mode}`",
                "- summary: demo",
                "",
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `task-generation`",
                "- current_domain: `none`",
                f"- next_action: `{next_action}`",
                "- blocker_reason: `None`",
                f"- final_handoff_decision: `{next_command}`",
                "",
                "## Analyze Gate",
                "",
                "- gate_status: `cleared`",
                "- gate_cycle: `0`",
                "- highest_invalid_stage: `none`",
                "- blocker_bundle:",
                "  - none",
                "- blocker_attribution_values: `none`",
                "",
                "## Reopen Contract",
                "",
                "- reopen_source: `none`",
                "- reopen_target: `none`",
                "- reopen_reason: `none`",
                "",
                "## Handoff Files",
                "",
                "- handoff_to_implement: `handoff-to-implement.json`",
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


def _write_task_package(feature_dir: Path) -> None:
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- [ ] T001 Demo task\n", encoding="utf-8")
    (feature_dir / "task-index.json").write_text('{"tasks": [{"id": "T001"}]}\n', encoding="utf-8")
    (feature_dir / "handoff-to-implement.json").write_text('{"status": "ready"}\n', encoding="utf-8")


def _write_task_package_without_handoff(feature_dir: Path) -> None:
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- [ ] T001 Demo task\n", encoding="utf-8")
    (feature_dir / "task-index.json").write_text('{"tasks": [{"id": "T001"}]}\n', encoding="utf-8")


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


def test_reconcile_marks_clean_tasks_handoff_launchable_for_implement_without_tracker(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="hand off to implement",
    )
    _write_task_package(feature_dir)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        last_command="tasks",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "resumable"
    assert reconciled.last_stable_checkpoint == "handoff-to-implement"
    assert reconciled.recovery_reason == ""


def test_reconcile_blocks_clean_tasks_handoff_without_task_package(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="hand off to implement",
    )
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        last_command="tasks",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "blocked"
    assert reconciled.recovery_reason == "missing implement launch artifacts"


def test_reconcile_blocks_clean_tasks_handoff_without_implement_handoff_file(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="hand off to implement",
    )
    _write_task_package_without_handoff(feature_dir)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        last_command="tasks",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "blocked"
    assert reconciled.recovery_reason == "missing implement launch artifacts"


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
