import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState, DebugStatus, RootCause, ValidationCheck


runner = CliRunner()


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in ("project-rules-template.md", "project-learnings-template.md"):
        (target_root / name).write_text((templates_root / name).read_text(encoding="utf-8"), encoding="utf-8")


def _invoke_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def _write_implement_tracker(
    feature_dir: Path,
    *,
    status: str,
    retry_attempts: int,
    failed_tasks: list[str],
    completed_checks: list[str],
    blockers: list[dict[str, str]] | None = None,
    open_gaps: list[dict[str, str]] | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    blockers = blockers or []
    open_gaps = open_gaps or []
    content = [
        "---",
        f'status: "{status}"',
        'feature: "demo-feature"',
        'resume_decision: "resume-here"',
        "---",
        "",
        "## Current Focus",
        "current_batch: batch-2",
        "goal: finish validation after recovery",
        "next_action: close the feature",
        "",
        "## Execution State",
        "completed_tasks:",
        "  - T001",
        "in_progress_tasks: []",
        "failed_tasks:",
        *[f"  - {task}" for task in failed_tasks],
        f"retry_attempts: {retry_attempts}",
        "",
        "## Validation",
        "planned_checks:",
        "  - pytest -q",
        "completed_checks:",
        *[f"  - {check}" for check in completed_checks],
        "",
        "## Blockers",
        *(
            [
                f"- task: {item['task']}",
                f"  type: {item['type']}",
                f"  evidence: {item['evidence']}",
                f"  recovery_action: {item['recovery_action']}",
            ]
            for item in blockers
        ),
        "",
        "## Open Gaps",
        *(
            [
                f"- type: {item['type']}",
                f"  summary: {item['summary']}",
                f"  source: {item['source']}",
                f"  next_action: {item['next_action']}",
            ]
            for item in open_gaps
        ),
        "",
    ]
    flattened: list[str] = []
    for item in content:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    (feature_dir / "implement-tracker.md").write_text("\n".join(flattened) + "\n", encoding="utf-8")


def _write_workflow_state(
    feature_dir: Path,
    *,
    next_command: str = "/sp.implement",
    status: str = "completed",
    route_reason: str = "",
    blocked_reason: str = "",
    false_starts: list[str] | None = None,
    hidden_dependencies: list[str] | None = None,
    reusable_constraints: list[str] | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    false_starts = false_starts or []
    hidden_dependencies = hidden_dependencies or []
    reusable_constraints = reusable_constraints or []
    lines = [
        "# Workflow State: Demo",
        "",
        "## Current Command",
        "",
        "- active_command: `sp-analyze`",
        f"- status: `{status}`",
        "",
        "## Phase Mode",
        "",
        "- phase_mode: `analysis-only`",
        "- summary: demo",
        "",
        "## Next Action",
        "",
        "- continue",
        "",
        "## Next Command",
        "",
        f"- `{next_command}`",
    ]
    if route_reason or blocked_reason or false_starts or hidden_dependencies or reusable_constraints:
        lines.extend(
            [
                "",
                "## Learning Signals",
                "",
                f"- route_reason: {route_reason}",
                f"- blocked_reason: {blocked_reason}",
                "",
                "### False Starts",
            ]
        )
        lines.extend([f"- {item}" for item in false_starts] or ["-"])
        lines.extend(["", "### Hidden Dependencies"])
        lines.extend([f"- {item}" for item in hidden_dependencies] or ["-"])
        lines.extend(["", "### Reusable Constraints"])
        lines.extend([f"- {item}" for item in reusable_constraints] or ["-"])
    lines.append("")
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _write_resolved_debug_session(project: Path, slug: str) -> Path:
    debug_dir = project / ".planning" / "debug"
    handler = MarkdownPersistenceHandler(debug_dir)
    state = DebugGraphState(slug=slug, trigger="Intermittent validation failure")
    state.status = DebugStatus.RESOLVED
    state.resolution.fail_count = 2
    state.resolution.fix = "Re-run validation after refreshing the fixture cache"
    state.resolution.root_cause = RootCause(
        summary="Fixture cache drifted after the first failing run",
        owning_layer="tests",
        broken_control_state="fixture cache freshness",
        failure_mechanism="stale fixture state persisted across retries",
        loop_break="verification observed stale state",
        decisive_signal="fresh cache run passed immediately",
    )
    state.resolution.validation_results = [
        ValidationCheck(command="pytest tests/test_cache.py -q", status="passed", output="1 passed")
    ]
    state.resolution.loop_restoration_proof = ["Fresh cache validation passed end-to-end"]
    handler.save(state)
    return debug_dir / f"{slug}.md"


def _write_testing_state(
    project: Path,
    *,
    status: str,
    mode: str,
    next_action: str,
    next_command: str,
    handoff_reason: str,
    unit_test_system_request: str = ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md",
    validation_commands: list[str] | None = None,
    validation_exit_status: str = "passed",
    validation_summary: str = "testing contract validated",
    open_gaps: list[dict[str, str]] | None = None,
) -> Path:
    testing_dir = project / ".specify" / "testing"
    testing_dir.mkdir(parents=True, exist_ok=True)
    validation_commands = validation_commands or []
    open_gaps = open_gaps or []
    lines = [
        "---",
        f"status: {status}",
        f"mode: {mode}",
        'updated: "2026-04-29T00:00:00Z"',
        "---",
        "",
        "# Testing State",
        "",
        "## Current Focus",
        f"- next_action: {next_action}",
        f"- next_command: {next_command}",
        f"- handoff_reason: {handoff_reason}",
        "- selected_modules: core-module",
        "- selected_language_skills: python-testing",
        "- inventory_source: specify testing inventory --format json",
        "",
        "## Testing Assets",
        "- testing_contract: .specify/testing/TESTING_CONTRACT.md",
        "- testing_playbook: .specify/testing/TESTING_PLAYBOOK.md",
        "- coverage_baseline: .specify/testing/COVERAGE_BASELINE.json",
        f"- unit_test_system_request: {unit_test_system_request}",
        "",
        "## Validation Evidence",
        "- last_manual_validation:",
    ]
    if validation_commands:
        lines.append("  - commands:")
        for command in validation_commands:
            lines.append(f"    - {command}")
        lines.append('  - run_at: "2026-04-29T00:10:00Z"')
        lines.append(f"  - exit_status: {validation_exit_status}")
        lines.append(f"  - summary: {validation_summary}")
    else:
        lines.append("  - commands:")
        lines.append("  - run_at:")
        lines.append("  - exit_status:")
        lines.append("  - summary:")
    lines.extend(["", "## Open Gaps"])
    for item in open_gaps:
        lines.extend(
            [
                "- module:",
                f"  - summary: {item['summary']}",
                f"  - next_action: {item['next_action']}",
            ]
        )
    lines.append("")
    path = testing_dir / "testing-state.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_learning_ensure_creates_stable_and_runtime_files(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["project_rules"] is True
    assert payload["exists"]["project_learnings"] is True
    assert payload["exists"]["candidates"] is True
    assert payload["exists"]["review"] is True
    assert (project / ".specify" / "memory" / "project-rules.md").exists()
    assert (project / ".specify" / "memory" / "project-learnings.md").exists()
    assert (project / ".planning" / "learnings" / "candidates.md").exists()
    assert (project / ".planning" / "learnings" / "review.md").exists()


def test_learning_status_reports_missing_runtime_files_without_mutation(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "status", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["project_rules"] is False
    assert payload["exists"]["project_learnings"] is False
    assert payload["exists"]["candidates"] is False
    assert payload["exists"]["review"] is False


def test_learning_capture_merges_by_recurrence_key_and_increments_count(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "pitfall",
        "--summary",
        "Need to preserve shared boundary pattern",
        "--evidence",
        "Observed during implementation",
        "--recurrence-key",
        "shared.boundary.pattern",
        "--format",
        "json",
    ]
    first = _invoke_in_project(project, args)
    second = _invoke_in_project(project, args)

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert first_payload["entry"]["occurrence_count"] == 1
    assert second_payload["entry"]["occurrence_count"] == 2
    assert second_payload["needs_confirmation"] is True


def test_learning_start_filters_relevant_candidates_by_command(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "plan",
            "--type",
            "workflow_gap",
            "--summary",
            "Need explicit validation tasks",
            "--evidence",
            "Missed twice in planning",
            "--recurrence-key",
            "workflow.validation.tasks",
            "--format",
            "json",
        ],
    )
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "recovery_path",
            "--summary",
            "Re-run focused repro before widening scope",
            "--evidence",
            "Resolved repeated debug loops",
            "--recurrence-key",
            "debug.focused.repro",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["learning", "start", "--command", "debug", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summaries = [entry["summary"] for entry in payload["relevant_candidates"]]
    assert "Re-run focused repro before widening scope" in summaries
    assert "Need explicit validation tasks" not in summaries


def test_learning_start_auto_promotes_repeated_medium_signal_candidates(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "plan",
        "--type",
        "workflow_gap",
        "--summary",
        "Always preserve verification tasks in planning",
        "--evidence",
        "Repeated omission in planning",
        "--recurrence-key",
        "workflow.verify.tasks",
        "--signal",
        "medium",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _invoke_in_project(project, ["learning", "start", "--command", "plan", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    auto_promoted = [entry["summary"] for entry in payload["auto_promoted"]]
    relevant_learnings = [entry["summary"] for entry in payload["relevant_learnings"]]
    relevant_candidates = [entry["summary"] for entry in payload["relevant_candidates"]]
    assert "Always preserve verification tasks in planning" in auto_promoted
    assert "Always preserve verification tasks in planning" in relevant_learnings
    assert "Always preserve verification tasks in planning" not in relevant_candidates


def test_learning_capture_confirm_and_promote_rule_flow(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    captured = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "specify",
            "--type",
            "project_constraint",
            "--summary",
            "Always name touched shared surfaces explicitly",
            "--evidence",
            "User confirmed this should become a default",
            "--recurrence-key",
            "shared.surfaces.must.be.named",
            "--signal",
            "high",
            "--confirm",
            "--format",
            "json",
        ],
    )
    promoted = _invoke_in_project(
        project,
        [
            "learning",
            "promote",
            "--recurrence-key",
            "shared.surfaces.must.be.named",
            "--target",
            "rule",
            "--format",
            "json",
        ],
    )
    start = _invoke_in_project(project, ["learning", "start", "--command", "implement", "--format", "json"])

    assert captured.exit_code == 0, captured.stdout
    assert promoted.exit_code == 0, promoted.stdout
    promoted_payload = json.loads(promoted.stdout)
    start_payload = json.loads(start.stdout)
    assert promoted_payload["status"] == "promoted-rule"
    rule_summaries = [entry["summary"] for entry in start_payload["relevant_rules"]]
    assert "Always name touched shared surfaces explicitly" in rule_summaries


def test_learning_start_exposes_confirmed_project_constraint_warning_for_all_workflows(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "project_constraint",
            "--summary",
            "Use the validated build surface before retrying native compilation",
            "--evidence",
            "Confirmed reusable build constraint",
            "--recurrence-key",
            "build.surface.must.be.validated",
            "--confirm",
            "--format",
            "json",
        ],
    )

    workflow_commands = (
        "constitution",
        "specify",
        "clarify",
        "deep-research",
        "plan",
        "checklist",
        "tasks",
        "analyze",
        "test",
        "implement",
        "debug",
        "fast",
        "quick",
        "map-scan",
        "map-build",
    )

    for command_name in workflow_commands:
        result = _invoke_in_project(project, ["learning", "start", "--command", command_name, "--format", "json"])
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        relevant_learnings = [entry["summary"] for entry in payload["relevant_learnings"]]
        preflight_warnings = payload["preflight_warnings"]

        assert "Use the validated build surface before retrying native compilation" in relevant_learnings
        assert any(
            item["summary"] == "Use the validated build surface before retrying native compilation"
            and item["source_layer"] == "project_learnings"
            for item in preflight_warnings
        )


def test_learning_start_surfaces_single_high_signal_candidate_as_preflight_warning(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "tooling_trap",
            "--summary",
            "Validate the shell and solution platform before retrying MSBuild",
            "--evidence",
            "Single high-signal build trap that should still shape the next run",
            "--recurrence-key",
            "build.shell-and-platform.must-be-validated",
            "--signal",
            "high",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["learning", "start", "--command", "implement", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    confirmation = [entry["summary"] for entry in payload["confirmation_candidates"]]
    preflight_warnings = payload["preflight_warnings"]

    assert "Validate the shell and solution platform before retrying MSBuild" in confirmation
    assert any(
        item["summary"] == "Validate the shell and solution platform before retrying MSBuild"
        and item["source_layer"] == "candidate"
        and item["requires_confirmation"] is True
        and "sp-implement" in item["why_now"]
        for item in preflight_warnings
    )


def test_learning_start_auto_promotes_repeated_high_signal_candidates(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "project_constraint",
        "--summary",
        "Always name touched shared surfaces explicitly",
        "--evidence",
        "Repeated and high-signal constraint",
        "--recurrence-key",
        "shared.surfaces.must.be.named",
        "--signal",
        "high",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _invoke_in_project(project, ["learning", "start", "--command", "implement", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    auto_promoted = [entry["summary"] for entry in payload["auto_promoted"]]
    relevant_learnings = [entry["summary"] for entry in payload["relevant_learnings"]]
    relevant_candidates = [entry["summary"] for entry in payload["relevant_candidates"]]
    assert "Always name touched shared surfaces explicitly" in auto_promoted
    assert "Always name touched shared surfaces explicitly" in relevant_learnings
    assert "Always name touched shared surfaces explicitly" not in relevant_candidates


def test_learning_start_auto_promote_preserves_structured_learning_fields(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "debug",
        "--type",
        "tooling_trap",
        "--summary",
        "Validate native shell before retrying the build",
        "--evidence",
        "Repeated build retries failed until the shell was corrected.",
        "--recurrence-key",
        "build.shell.must.be.validated",
        "--signal",
        "high",
        "--pain-score",
        "7",
        "--false-start",
        "retrying msbuild from the wrong shell",
        "--rejected-path",
        "source-code regression",
        "--decisive-signal",
        "the same build passed immediately after switching shells",
        "--root-cause-family",
        "native-build-shell-mismatch",
        "--injection-target",
        "sp-debug",
        "--promotion-hint",
        "promote whenever native build setup is involved",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _invoke_in_project(project, ["learning", "start", "--command", "debug", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promoted_entry = next(
        entry for entry in payload["auto_promoted"]
        if entry["recurrence_key"] == "build.shell.must.be.validated"
    )
    relevant_learning = next(
        entry for entry in payload["relevant_learnings"]
        if entry["recurrence_key"] == "build.shell.must.be.validated"
    )

    assert promoted_entry["pain_score"] == 7
    assert promoted_entry["false_starts"] == ["retrying msbuild from the wrong shell"]
    assert promoted_entry["rejected_paths"] == ["source-code regression"]
    assert promoted_entry["decisive_signal"] == "the same build passed immediately after switching shells"
    assert promoted_entry["root_cause_family"] == "native-build-shell-mismatch"
    assert promoted_entry["injection_targets"] == ["sp-debug"]
    assert promoted_entry["promotion_hint"] == "promote whenever native build setup is involved"
    assert relevant_learning["pain_score"] == 7


def test_learning_aggregate_json_reports_grouped_patterns(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Need to preserve shared boundary pattern",
            "--evidence",
            "Observed during implementation",
            "--recurrence-key",
            "shared.boundary.pattern",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["learning", "aggregate", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["counts"]["patterns"] == 1
    assert payload["patterns"][0]["recurrence_key"] == "shared.boundary.pattern"


def test_learning_aggregate_write_report_creates_markdown_output(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(
        project,
        ["learning", "aggregate", "--format", "json", "--write-report"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    report_path = Path(payload["report_path"])
    assert report_path.exists()
    assert "Learning Aggregate Report" in report_path.read_text(encoding="utf-8")


def test_learning_start_exposes_top_warnings_and_summary_counts(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "pitfall",
        "--summary",
        "Need to preserve shared boundary pattern",
        "--evidence",
        "Observed during implementation",
        "--recurrence-key",
        "shared.boundary.pattern",
        "--signal",
        "high",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _invoke_in_project(project, ["learning", "start", "--command", "implement", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary_counts"]["relevant_candidates"] == 0
    assert payload["summary_counts"]["relevant_learnings"] == 1
    assert payload["summary_counts"]["preflight_warnings"] == 1
    assert payload["top_warnings"][0]["recurrence_key"] == "shared.boundary.pattern"
    assert payload["top_warnings"][0]["summary"] == "Need to preserve shared boundary pattern"


def test_learning_help_surfaces_low_level_helper_commands() -> None:
    result = runner.invoke(app, ["learning", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    assert "ensure" in result.stdout
    assert "status" in result.stdout
    assert "start" in result.stdout
    assert "capture" in result.stdout
    assert "capture-auto" in result.stdout
    assert "promote" in result.stdout


def test_learning_capture_auto_help_mentions_broader_state_surfaces() -> None:
    result = runner.invoke(app, ["learning", "capture-auto", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    output = result.stdout
    assert "--command" in output
    assert "plan" in output
    assert "test" in output
    assert "implement" in output
    assert "quick" in output
    assert "debug" in output
    assert "--feature-dir" in output
    assert "workflow-state.md" in output
    assert "implement-tracker.md" in output
    assert "STATUS.md" in output
    assert "Debug session markdown file" in output


def test_project_constraint_default_applies_to_includes_test_and_map_codebase(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "project_constraint",
            "--summary",
            "Need to preserve shared execution constraints",
            "--evidence",
            "Observed across execution workflows",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    applies_to = payload["entry"]["applies_to"]
    assert "sp-test" in applies_to
    assert "sp-map-scan" in applies_to
    assert "sp-map-build" in applies_to


def test_learning_capture_accepts_structured_path_learning_fields(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "tooling_trap",
            "--summary",
            "Watcher loops can masquerade as process-manager failures",
            "--evidence",
            "Repeated process fixes failed; excluding the log directory stopped restarts.",
            "--pain-score",
            "6",
            "--false-start",
            "job object cleanup",
            "--rejected-path",
            "process manager root cause",
            "--decisive-signal",
            "watcher ignore stopped restarts",
            "--root-cause-family",
            "dev-tooling-watch-loop",
            "--injection-target",
            "sp-debug",
            "--promotion-hint",
            "promote after another watcher-loop recurrence",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    entry = payload["entry"]
    assert entry["learning_type"] == "tooling_trap"
    assert entry["pain_score"] == 6
    assert entry["false_starts"] == ["job object cleanup"]
    assert entry["rejected_paths"] == ["process manager root cause"]
    assert entry["decisive_signal"] == "watcher ignore stopped restarts"
    assert entry["root_cause_family"] == "dev-tooling-watch-loop"
    assert entry["injection_targets"] == ["sp-debug"]


def test_learning_capture_auto_implement_writes_candidates_from_tracker_state(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=2,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summaries = [entry["summary"] for entry in payload["captured"]]
    assert payload["status"] == "captured"
    assert "Rerun planned validation after implementation recovery before resolving the feature" in summaries
    assert "Failed implementation tasks should keep execution in recovery until validation turns green" in summaries


def test_learning_capture_auto_implement_extracts_gap_and_constraint_patterns(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="blocked",
        retry_attempts=0,
        failed_tasks=[],
        completed_checks=[],
        blockers=[
            {
                "task": "T009",
                "type": "external",
                "evidence": "API contract approval still pending",
                "recovery_action": "wait for API owner sign-off",
            }
        ],
        open_gaps=[
            {
                "type": "plan_gap",
                "summary": "Plan omitted the contract migration step",
                "source": "T009",
                "next_action": "update plan.md and tasks.md before resuming",
            }
        ],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    keys = [entry["recurrence_key"] for entry in payload["captured"]]
    assert "implement.execution-blockers-feed-back-into-planning" in keys
    assert "implement.external-or-human-blockers-are-project-constraints" in keys


def test_learning_capture_auto_debug_writes_candidates_from_resolved_session(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    session_file = _write_resolved_debug_session(project, "fixture-cache-drift")

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "debug",
            "--session-file",
            str(session_file),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "captured"
    keys = [entry["recurrence_key"] for entry in payload["captured"]]
    assert "debug.return-to-investigation-after-failed-verification" in keys
    assert "debug.research-checkpoint-after-repeated-verification-failure" in keys


def test_learning_capture_auto_skips_duplicate_snapshot(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    first = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    second_payload = json.loads(second.stdout)
    assert second_payload["status"] == "duplicate-snapshot"


def test_learning_capture_auto_ignores_timestamp_only_tracker_changes(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    tracker_path = feature_dir / "implement-tracker.md"
    tracker_path.write_text(
        tracker_path.read_text(encoding="utf-8").replace(
            'resume_decision: "resume-here"',
            'resume_decision: "resume-here"\nupdated: "2026-04-27T10:00:00Z"',
        ),
        encoding="utf-8",
    )

    first = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    tracker_path.write_text(
        tracker_path.read_text(encoding="utf-8").replace(
            'updated: "2026-04-27T10:00:00Z"',
            'updated: "2026-04-27T10:05:00Z"',
        ),
        encoding="utf-8",
    )

    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    second_payload = json.loads(second.stdout)
    assert second_payload["status"] == "duplicate-snapshot"


def test_learning_capture_auto_quick_extracts_fallback_constraint(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    workspace = project / ".planning" / "quick" / "260417-001-demo"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260417-001"',
                'title: "Demo quick task"',
                'status: "blocked"',
                "---",
                "",
                "## Current Focus",
                "goal: keep the worker result contract aligned",
                "current_focus: recover from runtime outage",
                "next_action: wait for runtime recovery",
                "",
                "## Execution",
                "active_lane: leader-local",
                "join_point:",
                "files_or_surfaces: src/specify_cli/__init__.py",
                "execution_fallback: native worker runtime unavailable",
                "blockers: []",
                "recovery_action: retry after runtime comes back",
                "retry_attempts: 1",
                "blocker_reason: runtime unavailable",
                "",
                "## Validation",
                "planned_checks:",
                "  - pytest tests/test_learning_cli.py -q",
                "completed_checks: []",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    keys = [entry["recurrence_key"] for entry in payload["captured"]]
    assert "quick.leader-local-fallback-preserves-runtime-unavailability-reason" in keys


def test_learning_capture_auto_test_extracts_followup_route_and_validation_gaps(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _write_testing_state(
        project,
        status="complete",
        mode="bootstrap",
        next_action="Route the brownfield testing program into specification",
        next_command="/sp-specify",
        handoff_reason="Multiple uncovered module waves still need scoped planning.",
        validation_commands=[],
        validation_exit_status="",
        validation_summary="",
        open_gaps=[
            {
                "summary": "Core module still lacks the baseline public-contract tests.",
                "next_action": "Plan the first coverage uplift wave before implementation resumes.",
            }
        ],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "test",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    keys = [entry["recurrence_key"] for entry in payload["captured"]]
    assert payload["status"] == "captured"
    assert "test.open-gaps-require-explicit-follow-up-route" in keys
    assert "test.complete-state-requires-manual-validation-evidence" in keys
    assert "test.brownfield-programs-start-from-unit-test-system-request" in keys


def test_learning_capture_auto_plan_extracts_route_reason_false_starts_and_constraints(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_workflow_state(
        feature_dir,
        next_command="/sp.tasks",
        status="blocked",
        route_reason="Planning cannot proceed until the ownership split is made explicit.",
        blocked_reason="Shared boundary ownership is still ambiguous.",
        false_starts=["assumed the adapter layer owned persistence concerns"],
        hidden_dependencies=["deployment workflow depends on the ownership split"],
        reusable_constraints=["keep persistence ownership explicit in plan artifacts"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    keys = [entry["recurrence_key"] for entry in payload["captured"]]
    assert payload["status"] == "captured"
    assert "sp-plan.workflow-state-preserves-reentry-reason" in keys
    assert "sp-plan.workflow-state-preserves-false-starts" in keys
    assert "sp-plan.workflow-state-promotes-discovered-constraints" in keys


def test_implement_closeout_validates_state_and_auto_captures(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_workflow_state(feature_dir)
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    result = _invoke_in_project(
        project,
        [
            "implement",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["hook_result"]["status"] == "ok"
    assert payload["auto_capture"]["status"] == "captured"


def test_implement_closeout_returns_blocked_json_when_session_state_is_missing(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)

    result = _invoke_in_project(
        project,
        [
            "implement",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["hook_result"]["status"] == "blocked"
    assert any("workflow-state.md" in message or "implement-tracker.md" in message for message in payload["hook_result"]["errors"])


def test_implement_help_surfaces_closeout_command() -> None:
    result = runner.invoke(app, ["implement", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    assert "closeout" in result.stdout
