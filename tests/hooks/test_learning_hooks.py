import json
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-learning-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_learning_review_blocks_terminal_closeout_without_review(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {"command_name": "implement", "terminal_status": "resolved"},
    )

    assert result.status == "blocked"
    assert any("learning review" in message.lower() for message in result.errors)


def test_learning_review_allows_explicit_none_decision(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "debug",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No reusable pitfall or workflow gap was found.",
            },
        },
    )

    assert result.status == "ok"
    assert result.data["review"]["decision"] == "none"


def test_learning_review_blocks_none_decision_when_recent_friction_signal_exists(tmp_path: Path):
    project = _create_project(tmp_path)

    signal_result = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "implement",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
            "false_starts": ["retried the same build path without fixing the shell"],
        },
    )
    review_result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "The work eventually completed.",
            },
        },
    )

    assert signal_result.status == "warn"
    assert review_result.status == "blocked"
    assert any("recent friction signal" in message.lower() for message in review_result.errors)


def test_learning_review_clears_recent_signal_after_non_none_decision(tmp_path: Path):
    project = _create_project(tmp_path)

    run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "implement",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
        },
    )
    captured_review = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "captured",
                "rationale": "Captured the reusable lesson before closeout.",
            },
        },
    )
    followup_none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No new reusable learning remains after the previous capture.",
            },
        },
    )

    assert captured_review.status == "ok"
    assert followup_none.status == "ok"


def test_learning_signal_warns_when_pain_score_crosses_threshold(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "quick",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
            "false_starts": ["treated runtime issue as code issue"],
        },
    )

    assert result.status == "warn"
    assert result.data["pain_score"] >= 5
    assert "run `specify hook review-learning" in result.actions[0]


def test_learning_inject_derives_targets_from_learning_type(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.inject",
        {
            "command_name": "map-build",
            "learning_type": "map_coverage_gap",
            "summary": "Atlas omitted runtime watcher dependencies",
        },
    )

    assert result.status == "ok"
    assert "sp-map-scan" in result.data["injection_targets"]
    assert "sp-map-build" in result.data["injection_targets"]
    assert "PROJECT-HANDBOOK.md" in result.data["injection_targets"]


def test_learning_capture_hook_records_structured_candidate(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "debug",
            "learning_type": "tooling_trap",
            "summary": "Watcher loops can masquerade as process-manager failures",
            "evidence": "Repeated process fixes failed; excluding the log directory stopped restarts.",
            "pain_score": 6,
            "false_starts": ["job object cleanup", "port conflict"],
            "rejected_paths": ["process manager root cause"],
            "decisive_signal": "restart stopped when watcher ignored generated logs",
            "root_cause_family": "dev-tooling-watch-loop",
            "injection_targets": ["sp-debug", "sp-map-scan", "sp-map-build"],
            "promotion_hint": "promote after another watcher-loop recurrence",
        },
    )

    assert result.status == "repaired"
    entry = result.data["capture"]["entry"]
    assert entry["learning_type"] == "tooling_trap"
    assert entry["pain_score"] == 6
    assert entry["false_starts"] == ["job object cleanup", "port conflict"]

    candidates = project / ".planning" / "learnings" / "candidates.md"
    assert "Watcher loops can masquerade" in candidates.read_text(encoding="utf-8")
