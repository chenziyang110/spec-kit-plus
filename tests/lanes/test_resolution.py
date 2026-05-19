from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.resolution import resolve_lane_for_command
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


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


def test_resolve_lane_returns_unique_resumable_candidate(tmp_path: Path):
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
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="implement")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-001"


def test_resolve_lane_requires_choice_for_multiple_resumable_candidates(tmp_path: Path):
    feature_dir_a = tmp_path / "specs" / "001-alpha"
    feature_dir_b = tmp_path / "specs" / "002-beta"
    _write_workflow_state(feature_dir_a, "/sp.implement")
    _write_implement_tracker(feature_dir_a, "executing")
    _write_workflow_state(feature_dir_b, "/sp.implement")
    _write_implement_tracker(feature_dir_b, "executing")
    lane_a = LaneRecord(
        lane_id="lane-001",
        feature_id="001-alpha",
        feature_dir="specs/001-alpha",
        branch_name="001-alpha",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )
    lane_b = LaneRecord(
        lane_id="lane-002",
        feature_id="002-beta",
        feature_dir="specs/002-beta",
        branch_name="002-beta",
        worktree_path=".specify/lanes/worktrees/lane-002",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane_a)
    write_lane_record(tmp_path, lane_b)
    write_lane_index(
        tmp_path,
        {"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]},
    )

    result = resolve_lane_for_command(tmp_path, command_name="implement")

    assert result.mode == "choose"
    assert result.selected_lane_id == ""
    assert [candidate.feature_id for candidate in result.candidates] == ["001-alpha", "002-beta"]


def test_resolve_lane_auto_inferrs_implement_from_tracker_and_workflow_state(tmp_path: Path):
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
        recovery_state="resumable",
        last_command="specify",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="auto")

    assert result.mode == "resume"
    assert result.candidates[0].last_command == "implement"


def test_resolve_lane_auto_routes_clean_tasks_handoff_to_implement_without_tracker(tmp_path: Path):
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
        recovery_state="resumable",
        last_command="tasks",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="auto")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-001"
    assert result.candidates[0].last_command == "implement"
    assert result.candidates[0].last_stable_checkpoint == "handoff-to-implement"


def test_resolve_lane_auto_preserves_explicit_legacy_analyze_state(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.analyze",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="run legacy analyze gate",
    )
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        recovery_state="resumable",
        last_command="tasks",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="auto")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-001"
    assert result.candidates[0].last_command == "analyze"


def test_resolve_lane_matches_canonical_slash_prefixed_next_command(tmp_path: Path):
    feature_dir = tmp_path / ".specify" / "specs" / "001-legacy"
    _write_workflow_state(feature_dir, "/sp.plan")
    lane = LaneRecord(
        lane_id="lane-legacy",
        feature_id="001-legacy",
        feature_dir=".specify/specs/001-legacy",
        branch_name="001-legacy-hotfix",
        worktree_path=".specify/lanes/worktrees/lane-legacy",
        lifecycle_state="specified",
        recovery_state="resumable",
        last_command="specify",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-legacy"}]})

    result = resolve_lane_for_command(tmp_path, command_name="plan")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-legacy"
