from pathlib import Path

from specify_cli.learnings import LearningEntry, capture_learning, ensure_learning_files
from specify_cli.learning_aggregate import (
    aggregate_learning_patterns,
    aggregate_learning_state,
    render_learning_aggregate_report,
)


def _entry(
    *,
    recurrence_key: str,
    status: str,
    occurrence_count: int,
    summary: str,
    source_command: str = "sp-implement",
    learning_type: str = "pitfall",
    signal_strength: str = "medium",
    first_seen: str = "2026-04-20T00:00:00Z",
    last_seen: str = "2026-04-24T00:00:00Z",
) -> LearningEntry:
    return LearningEntry(
        id=f"{status}-{occurrence_count}",
        summary=summary,
        learning_type=learning_type,
        source_command=source_command,
        evidence="captured during test setup",
        recurrence_key=recurrence_key,
        default_scope="implementation-heavy",
        applies_to=["sp-implement", "sp-debug"],
        signal_strength=signal_strength,
        status=status,
        first_seen=first_seen,
        last_seen=last_seen,
        occurrence_count=occurrence_count,
    )


def test_aggregate_learning_patterns_groups_same_recurrence_key_across_layers() -> None:
    patterns = aggregate_learning_patterns(
        candidate_entries=[
            _entry(
                recurrence_key="shared.boundary.pattern",
                status="candidate",
                occurrence_count=2,
                summary="Preserve shared boundary pattern",
            )
        ],
        confirmed_entries=[
            _entry(
                recurrence_key="shared.boundary.pattern",
                status="confirmed",
                occurrence_count=1,
                summary="Preserve shared boundary pattern",
                source_command="sp-plan",
            )
        ],
        rule_entries=[],
    )

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.recurrence_key == "shared.boundary.pattern"
    assert pattern.total_occurrences == 3
    assert pattern.layer_counts == {"candidate": 1, "confirmed": 1, "rule": 0}
    assert pattern.source_commands == ["sp-implement", "sp-plan"]
    assert pattern.top_summary == "Preserve shared boundary pattern"


def test_aggregate_learning_patterns_marks_candidate_with_three_occurrences_as_promotion_ready() -> None:
    patterns = aggregate_learning_patterns(
        candidate_entries=[
            _entry(
                recurrence_key="workflow.validation.tasks",
                status="candidate",
                occurrence_count=3,
                summary="Always preserve validation tasks",
                learning_type="workflow_gap",
            )
        ],
        confirmed_entries=[],
        rule_entries=[],
    )

    pattern = patterns[0]
    assert pattern.promotion_state == "promotion_ready"
    assert pattern.recommended_target == "learning"


def test_aggregate_learning_patterns_marks_confirmed_project_constraint_as_rule_candidate() -> None:
    patterns = aggregate_learning_patterns(
        candidate_entries=[],
        confirmed_entries=[
            _entry(
                recurrence_key="shared.surfaces.must.be.named",
                status="confirmed",
                occurrence_count=3,
                summary="Always name touched shared surfaces explicitly",
                learning_type="project_constraint",
                signal_strength="high",
            )
        ],
        rule_entries=[],
    )

    pattern = patterns[0]
    assert pattern.promotion_state == "promotion_ready"
    assert pattern.recommended_target == "rule"


def test_aggregate_learning_state_reads_candidates_confirmed_and_rules(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    for name in ("project-rules-template.md", "project-learnings-template.md"):
        (project / ".specify" / "templates" / name).write_text(
            (templates_root / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    ensure_learning_files(project)
    capture_learning(
        project,
        command_name="implement",
        learning_type="pitfall",
        summary="Preserve shared boundary pattern",
        evidence="first capture",
        recurrence_key="shared.boundary.pattern",
    )
    capture_learning(
        project,
        command_name="implement",
        learning_type="pitfall",
        summary="Preserve shared boundary pattern",
        evidence="second capture",
        recurrence_key="shared.boundary.pattern",
        confirm=True,
    )

    report = aggregate_learning_state(project)

    assert report["counts"]["patterns"] == 1
    assert report["counts"]["confirmed"] == 1
    assert report["counts"]["candidates"] == 0
    assert report["patterns"][0]["recurrence_key"] == "shared.boundary.pattern"


def test_render_learning_aggregate_report_includes_promotion_ready_and_stale_sections() -> None:
    report = {
        "generated_at": "2026-04-24T00:00:00Z",
        "counts": {
            "patterns": 2,
            "promotion_ready": 1,
            "approaching_threshold": 0,
            "stale": 1,
            "candidates": 1,
            "confirmed": 0,
            "rules": 0,
        },
        "patterns": [
            {
                "recurrence_key": "workflow.validation.tasks",
                "top_summary": "Always preserve validation tasks",
                "promotion_state": "promotion_ready",
                "recommended_target": "learning",
                "total_occurrences": 3,
                "source_commands": ["sp-plan"],
                "learning_types": ["workflow_gap"],
                "last_seen": "2026-04-24T00:00:00Z",
            },
            {
                "recurrence_key": "debug.snapshot.drift",
                "top_summary": "Re-check snapshot drift",
                "promotion_state": "stale",
                "recommended_target": None,
                "total_occurrences": 1,
                "source_commands": ["sp-debug"],
                "learning_types": ["recovery_path"],
                "last_seen": "2025-12-01T00:00:00Z",
            },
        ],
    }

    content = render_learning_aggregate_report(report)

    assert "Promotion-Ready Patterns" in content
    assert "workflow.validation.tasks" in content
    assert "Stale Patterns" in content
    assert "debug.snapshot.drift" in content
