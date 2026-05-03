from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.resolution import resolve_lane_for_command
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


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
