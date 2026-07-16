import json
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from specify_cli import app
from tests.conftest import strip_ansi
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import (
    DebugGraphState,
    DebugStatus,
    RootCause,
    ValidationCheck,
)
from specify_cli.learnings import (
    build_learning_paths,
    capture_learning,
    list_learning_summaries,
    normalize_command_name,
    read_learning_entries,
)
from specify_cli.launcher import SpecifyLauncherSpec, render_command, write_project_specify_launcher_config


runner = CliRunner()


def test_learning_normalizes_research_alias_to_deep_research() -> None:
    assert normalize_command_name("research") == "sp-deep-research"
    assert normalize_command_name("sp-research") == "sp-deep-research"
    assert normalize_command_name("sp.research") == "sp-deep-research"
    assert normalize_command_name("/sp.plan") == "sp-plan"
    assert normalize_command_name("spx-implement") == "sp-implement"
    assert normalize_command_name("spx.research") == "sp-deep-research"


@pytest.mark.parametrize("command_name", ["", "/", "sp-", "spx-", "plan now"])
def test_learning_rejects_blank_or_malformed_command_names(command_name: str) -> None:
    with pytest.raises(ValueError):
        normalize_command_name(command_name)


@pytest.mark.parametrize(
    ("summary", "evidence", "message"),
    [("", "evidence", "summary"), ("summary", "   ", "evidence")],
)
def test_learning_capture_rejects_blank_required_fields(
    tmp_path: Path,
    summary: str,
    evidence: str,
    message: str,
) -> None:
    _seed_learning_templates(tmp_path)

    with pytest.raises(ValueError, match=message):
        capture_learning(
            tmp_path,
            command_name="plan",
            learning_type="pitfall",
            summary=summary,
            evidence=evidence,
        )


def test_concurrent_learning_capture_merges_without_lost_occurrences(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    recurrence_key = "sp-plan.concurrent-capture"

    def capture(index: int) -> int:
        payload = capture_learning(
            tmp_path,
            command_name="plan",
            learning_type="pitfall",
            summary="Serialize Learning mutations through the CLI",
            evidence=f"Concurrent evidence packet {index}",
            recurrence_key=recurrence_key,
        )
        return int(payload["entry"]["occurrence_count"])

    with ThreadPoolExecutor(max_workers=4) as pool:
        occurrence_counts = sorted(pool.map(capture, range(4)))

    paths = build_learning_paths(tmp_path)
    _, candidates = read_learning_entries(paths.candidates)
    matching = [entry for entry in candidates if entry.recurrence_key == recurrence_key]
    assert occurrence_counts == [1, 2, 3, 4]
    assert len(matching) == 1
    assert matching[0].occurrence_count == 4


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in (
        "project-rules-template.md",
        "project-confirmed-learnings-template.md",
        "project-learnings-index-template.md",
        "project-learning-detail-template.md",
    ):
        (target_root / name).write_text(
            (templates_root / name).read_text(encoding="utf-8"), encoding="utf-8"
        )


def _invoke_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def _start_in_project(project: Path, command_name: str):
    return _invoke_in_project(
        project,
        [
            "learning",
            "start",
            "--command",
            command_name,
            "--format",
            "json",
        ],
    )


def _write_learning_index_payload(project: Path, payloads: list[object]) -> None:
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(payloads, indent=2),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _current_and_malformed_index_payloads(command_name: str) -> list[object]:
    normalized_command = normalize_command_name(command_name)
    return [
        {
            "id": "learn-2026-06-03-valid-entry",
            "problem": "Use focused preflight context before workflow execution",
            "lesson": "Read relevant learning detail docs before repeating the same workflow mistake.",
            "learning_type": "pitfall",
            "source_command": normalized_command,
            "recurrence_key": f"{normalized_command}.valid-index-entry",
            "applies_to": [normalized_command],
            "trigger_signals": ["pitfall", "medium"],
            "detail": "./learn-2026-06-03-valid-entry.md",
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
            "occurrence_count": 1,
            "signal_strength": "medium",
        },
        {
            "id": "learn-2026-06-03-missing-type",
            "problem": "Invalid index row omitted its learning type",
            "lesson": "Reject rows that do not satisfy the current schema.",
            "source_command": normalized_command,
            "recurrence_key": f"{normalized_command}.missing-learning-type",
            "applies_to": [normalized_command],
            "trigger_signals": ["medium"],
            "detail": "./learn-2026-06-03-missing-type.md",
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
            "occurrence_count": 1,
            "signal_strength": "medium",
        },
        {
            "id": "LRN-obsolete-summary-only",
            "summary": "Obsolete summary-only row",
            "evidence": "Obsolete evidence-only row.",
            "learning_type": "recovery_path",
            "recurrence_key": f"{normalized_command}.summary-only",
            "applies_to": [normalized_command],
            "signal_strength": "medium",
            "status": "confirmed",
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
            "occurrence_count": 1,
        },
        {
            "id": "learn-2026-06-03-malformed-entry",
            "problem": "Malformed entry has no recoverable command routing",
            "lesson": "This row should be skipped with diagnostics.",
            "learning_type": "pitfall",
            "recurrence_key": f"{normalized_command}.malformed-entry",
            "applies_to": {"not": "a-list"},
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
        },
    ]


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
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(flattened) + "\n", encoding="utf-8"
    )


def _write_tasks_and_worker_result(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [X] T001 Refresh validation fixture evidence",
                "",
            ]
        ),
        encoding="utf-8",
    )
    worker_results = feature_dir / "worker-results"
    worker_results.mkdir(parents=True, exist_ok=True)
    (worker_results / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "success",
                "validation_results": [
                    {
                        "command": "pytest -q",
                        "status": "passed",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


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
    trigger_signals: list[str] | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    false_starts = false_starts or []
    hidden_dependencies = hidden_dependencies or []
    reusable_constraints = reusable_constraints or []
    trigger_signals = trigger_signals or []
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
    if (
        route_reason
        or blocked_reason
        or false_starts
        or hidden_dependencies
        or reusable_constraints
        or trigger_signals
    ):
        lines.extend(
            [
                "",
                "## Learning Signals",
                "",
                f"- route_reason: {route_reason}",
                f"- blocked_reason: {blocked_reason}",
                "",
                "### Learning Triggers",
            ]
        )
        lines.extend([f"- {item}" for item in trigger_signals] or ["-"])
        lines.extend(
            [
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
        ValidationCheck(
            command="pytest tests/test_cache.py -q", status="passed", output="1 passed"
        )
    ]
    state.resolution.loop_restoration_proof = [
        "Fresh cache validation passed end-to-end"
    ]
    handler.save(state)
    return debug_dir / f"{slug}.md"


def test_learning_ensure_creates_stable_and_runtime_files(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["project_rules"] is True
    assert payload["exists"]["confirmed_learnings"] is True
    assert payload["exists"]["candidates"] is True
    assert payload["exists"]["review"] is True
    assert (project / ".specify" / "memory" / "project-rules.md").exists()
    assert (project / ".specify" / "memory" / "learnings" / "confirmed.md").exists()
    assert (project / ".planning" / "learnings" / "candidates.md").exists()
    assert (project / ".planning" / "learnings" / "review.md").exists()


def test_learning_ensure_creates_learning_index(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["learning_index"] is True
    assert (
        payload["paths"]["learning_index"]
        .replace("\\", "/")
        .endswith(".specify/memory/learnings/INDEX.md")
    )
    assert (
        payload["paths"]["learning_detail_template"]
        .replace("\\", "/")
        .endswith(".specify/templates/project-learning-detail-template.md")
    )
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    assert index_path.exists()
    index_content = index_path.read_text(encoding="utf-8")
    assert "# Project Learning Index" in index_content
    assert "<!-- SPECKIT_LEARNING_DATA_BEGIN -->" in index_content
    assert "<!-- SPECKIT_LEARNING_DATA_END -->" in index_content


def test_learning_ensure_migrates_legacy_confirmed_store_without_data_loss(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify" / "memory").mkdir(parents=True)
    _seed_learning_templates(project)
    legacy_path = project / ".specify" / "memory" / "project-learnings.md"
    legacy_path.write_text(
        "\n".join(
            [
                "# Project Learnings",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "LRN-legacy-confirmed",
                            "summary": "Preserve confirmed Learning during upgrades",
                            "learning_type": "project_constraint",
                            "source_command": "sp-plan",
                            "evidence": "Confirmed in the legacy v0.5.20 store",
                            "recurrence_key": "sp-plan.legacy-confirmed",
                            "default_scope": "project",
                            "applies_to": ["sp-plan"],
                            "signal_strength": "high",
                            "status": "confirmed",
                            "first_seen": "2026-06-01T00:00:00Z",
                            "last_seen": "2026-06-02T00:00:00Z",
                            "occurrence_count": 2,
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    repeated = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    assert repeated.exit_code == 0, repeated.stdout
    paths = build_learning_paths(project)
    _, confirmed = read_learning_entries(paths.confirmed_learnings)
    migrated = [
        entry
        for entry in confirmed
        if entry.recurrence_key == "sp-plan.legacy-confirmed"
    ]
    assert len(migrated) == 1
    assert migrated[0].occurrence_count == 2
    assert migrated[0].evidence == "Confirmed in the legacy v0.5.20 store"


def test_learning_status_reports_missing_runtime_files_without_mutation(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "status", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["project_rules"] is False
    assert payload["exists"]["confirmed_learnings"] is False
    assert payload["exists"]["learning_index"] is False
    assert payload["exists"]["candidates"] is False
    assert payload["exists"]["review"] is False


def test_learning_capture_merges_by_recurrence_key_and_increments_count(
    tmp_path: Path,
) -> None:
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


def test_learning_capture_writes_index_and_detail_doc(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    summary = "Run generated helper commands from the project launcher"
    evidence_fragment = (
        "Launcher command wiring drifted from generated helper expectations."
    )
    false_start = (
        "patched only the generated helper without updating the shared launcher surface"
    )
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "workflow_gap",
            "--summary",
            summary,
            "--evidence",
            f"{evidence_fragment}\nShared helper tests exposed the mismatch.",
            "--recurrence-key",
            "cli.project-launcher-helper-drift",
            "--applies-to",
            "sp-implement",
            "--false-start",
            false_start,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    index_entry = payload["index_entry"]
    assert index_entry["recurrence_key"] == "cli.project-launcher-helper-drift"
    assert (
        index_entry["problem"]
        == "Run generated helper commands from the project launcher"
    )
    assert "sp-implement" in index_entry["applies_to"]
    assert index_entry["detail"].startswith("./learn-")

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_content = index_path.read_text(encoding="utf-8")
    assert "cli.project-launcher-helper-drift" in index_content
    assert index_entry["detail"] in index_content

    detail_path = index_path.parent / index_entry["detail"].removeprefix("./")
    detail_content = detail_path.read_text(encoding="utf-8")
    assert summary in detail_content
    assert evidence_fragment in detail_content
    assert false_start in detail_content


def test_learning_capture_uses_unique_detail_refs_for_long_common_recurrence_prefixes(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    common_prefix = "cli." + "project-launcher-helper-drift-" * 4
    first_summary = "First long-prefix launcher learning"
    second_summary = "Second long-prefix launcher learning"
    first_evidence = "First evidence must stay in its own detail file."
    second_evidence = "Second evidence must stay in its own detail file."

    first = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            first_summary,
            "--evidence",
            first_evidence,
            "--recurrence-key",
            f"{common_prefix}first",
            "--format",
            "json",
        ],
    )
    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            second_summary,
            "--evidence",
            second_evidence,
            "--recurrence-key",
            f"{common_prefix}second",
            "--format",
            "json",
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    first_detail = first_payload["index_entry"]["detail"]
    second_detail = second_payload["index_entry"]["detail"]
    assert first_detail != second_detail

    learning_dir = project / ".specify" / "memory" / "learnings"
    first_detail_content = (learning_dir / first_detail.removeprefix("./")).read_text(
        encoding="utf-8"
    )
    second_detail_content = (learning_dir / second_detail.removeprefix("./")).read_text(
        encoding="utf-8"
    )
    assert first_summary in first_detail_content
    assert first_evidence in first_detail_content
    assert second_summary in second_detail_content
    assert second_evidence in second_detail_content


def test_learning_capture_repairs_existing_duplicate_valid_detail_ref(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    shared_detail_ref = "./learn-2026-05-11-shared.md"
    shared_other_summary = "Other stale detail owner"
    shared_other_evidence = "Other stale detail content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-duplicate-first",
                            "problem": "Captured duplicate detail owner",
                            "lesson": "First duplicate row should get a repaired detail ref.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.first",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                        {
                            "id": "learn-2026-05-11-duplicate-other",
                            "problem": shared_other_summary,
                            "lesson": shared_other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    shared_detail_path = learning_dir / shared_detail_ref.removeprefix("./")
    shared_detail_path.write_text(
        f"# {shared_other_summary}\n\n## Evidence\n\n{shared_other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured duplicate detail owner"
    evidence = "Captured detail content must move to a unique detail document."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            "cli.duplicate-detail.first",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != shared_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    shared_detail_content = shared_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert shared_other_summary in shared_detail_content
    assert shared_other_evidence in shared_detail_content
    assert evidence not in shared_detail_content


def test_learning_capture_repairs_duplicate_ref_when_canonical_is_already_taken(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.duplicate-detail.canonical-first"
    stale_first_seen = "2026-05-11T00:00:00Z"
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    canonical_id = (
        f"learn-2026-05-11-cli-duplicate-detail-canonical-first-{recurrence_hash}"
    )
    shared_detail_ref = f"./{canonical_id}.md"
    other_summary = "Other canonical detail owner"
    other_evidence = "Other canonical detail content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": canonical_id,
                            "problem": "Captured canonical duplicate owner",
                            "lesson": "Canonical duplicate should get an alternate detail ref.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": recurrence_key,
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                        {
                            "id": "learn-2026-05-11-other-canonical-owner",
                            "problem": other_summary,
                            "lesson": other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.canonical-other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    shared_detail_path = learning_dir / shared_detail_ref.removeprefix("./")
    shared_detail_path.write_text(
        f"# {other_summary}\n\n## Evidence\n\n{other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured canonical duplicate owner"
    evidence = "Captured canonical collision content must use an alternate detail file."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != shared_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    shared_detail_content = shared_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert other_summary in shared_detail_content
    assert other_evidence in shared_detail_content
    assert evidence not in shared_detail_content


def test_learning_capture_repairs_case_variant_detail_ref_collision(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.duplicate-detail.case-variant"
    stale_first_seen = "2026-05-11T00:00:00Z"
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    canonical_id = (
        f"learn-2026-05-11-cli-duplicate-detail-case-variant-{recurrence_hash}"
    )
    canonical_detail_ref = f"./{canonical_id}.md"
    case_variant_ref = f"./{canonical_id.upper()}.MD"
    other_summary = "Other case-variant detail owner"
    other_evidence = "Other case-variant detail content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-other-case-owner",
                            "problem": other_summary,
                            "lesson": other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.case-other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": case_variant_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    canonical_detail_path = learning_dir / canonical_detail_ref.removeprefix("./")
    canonical_detail_path.write_text(
        f"# {other_summary}\n\n## Evidence\n\n{other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured case-variant detail owner"
    evidence = "Captured case-variant content must use an alternate detail file."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != case_variant_ref
    assert repaired_detail_ref != canonical_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    canonical_detail_content = canonical_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert other_summary in canonical_detail_content
    assert other_evidence in canonical_detail_content
    assert evidence not in canonical_detail_content


def test_learning_capture_sanitizes_malformed_legacy_first_seen_for_detail_ref(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.malformed-first-seen.detail-ref"
    summary = "Sanitize malformed first seen for detail refs"
    evidence = "Malformed legacy timestamps must not create nested detail paths."
    legacy_payload = {
        "id": "LRN-legacy-malformed-first-seen",
        "summary": "Legacy malformed first seen",
        "learning_type": "pitfall",
        "source_command": "sp-implement",
        "evidence": "Legacy evidence",
        "recurrence_key": recurrence_key,
        "default_scope": "implementation-heavy",
        "applies_to": ["sp-implement"],
        "signal_strength": "medium",
        "status": "candidate",
        "first_seen": "../../bad",
        "last_seen": "../../bad",
        "occurrence_count": 1,
        "pain_score": 0,
        "false_starts": [],
        "rejected_paths": [],
        "decisive_signal": "",
        "root_cause_family": "",
        "injection_targets": [],
        "promotion_hint": "",
    }
    candidate_path = project / ".planning" / "learnings" / "candidates.md"
    candidate_path.write_text(
        "\n".join(
            [
                "# Candidate Learnings",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps([legacy_payload], indent=2),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-legacy-malformed-first-seen",
                            "problem": "Legacy malformed first seen",
                            "lesson": "Legacy evidence",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": recurrence_key,
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "../../outside.md",
                            "first_seen": "../../bad",
                            "last_seen": "../../bad",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    detail_ref = payload["index_entry"]["detail"]
    detail_name = detail_ref.removeprefix("./")
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = Path(payload["detail_path"]).resolve()
    assert detail_ref.startswith("./learn-")
    assert "/" not in detail_name
    assert "\\" not in detail_name
    assert detail_path.is_relative_to(learning_dir)
    assert detail_path.exists()
    detail_content = detail_path.read_text(encoding="utf-8")
    assert summary in detail_content
    assert evidence in detail_content


def test_learning_capture_repairs_unsafe_ref_before_canonical_duplicate_check(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.duplicate-detail.unsafe-current"
    stale_first_seen = "2026-05-11T00:00:00Z"
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    canonical_id = (
        f"learn-2026-05-11-cli-duplicate-detail-unsafe-current-{recurrence_hash}"
    )
    canonical_detail_ref = f"./{canonical_id}.md"
    unsafe_detail_ref = "../../outside.md"
    other_summary = "Other unsafe-canonical owner"
    other_evidence = "Other unsafe-canonical content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "../unsafe-current-id",
                            "problem": "Captured unsafe current detail owner",
                            "lesson": "Unsafe detail should repair before duplicate detection.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": recurrence_key,
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": unsafe_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                        {
                            "id": "learn-2026-05-11-other-unsafe-canonical-owner",
                            "problem": other_summary,
                            "lesson": other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.unsafe-other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": canonical_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    canonical_detail_path = learning_dir / canonical_detail_ref.removeprefix("./")
    canonical_detail_path.write_text(
        f"# {other_summary}\n\n## Evidence\n\n{other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured unsafe current detail owner"
    evidence = "Unsafe current detail content must use a unique repaired detail file."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != unsafe_detail_ref
    assert repaired_detail_ref != canonical_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    canonical_detail_content = canonical_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert other_summary in canonical_detail_content
    assert other_evidence in canonical_detail_content
    assert evidence not in canonical_detail_content


def test_learning_capture_confirm_keeps_index_occurrence_count_aligned(
    tmp_path: Path,
) -> None:
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
        "Keep launcher helper recurrence counts aligned",
        "--evidence",
        "Candidate capture should not make index counts drift on confirm.",
        "--recurrence-key",
        "cli.launcher-helper.count-alignment",
        "--format",
        "json",
    ]
    candidate = _invoke_in_project(project, args)
    confirmed = _invoke_in_project(project, [*args[:-2], "--confirm", *args[-2:]])

    assert candidate.exit_code == 0, candidate.stdout
    assert confirmed.exit_code == 0, confirmed.stdout
    payload = json.loads(confirmed.stdout)
    assert payload["entry"]["occurrence_count"] == 1
    assert (
        payload["index_entry"]["occurrence_count"]
        == payload["entry"]["occurrence_count"]
    )


def test_learning_promote_refreshes_index_detail_status(tmp_path: Path) -> None:
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
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Refresh detail docs after explicit promotion",
            "--evidence",
            "Promotion should update the linked detail machine payload.",
            "--recurrence-key",
            "cli.detail-doc.promotion-refresh",
            "--format",
            "json",
        ],
    )
    assert captured.exit_code == 0, captured.stdout
    detail_path = Path(json.loads(captured.stdout)["detail_path"])

    promoted = _invoke_in_project(
        project,
        [
            "learning",
            "promote",
            "--recurrence-key",
            "cli.detail-doc.promotion-refresh",
            "--target",
            "learning",
            "--format",
            "json",
        ],
    )

    assert promoted.exit_code == 0, promoted.stdout
    detail_content = detail_path.read_text(encoding="utf-8")
    assert '"status": "confirmed"' in detail_content
    assert '"status": "candidate"' not in detail_content


def test_learning_start_is_read_only_and_does_not_promote_detail_status(
    tmp_path: Path,
) -> None:
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
        "Refresh detail docs after auto promotion",
        "--evidence",
        "Auto-promotion should update the linked detail machine payload.",
        "--recurrence-key",
        "cli.detail-doc.auto-promotion-refresh",
        "--format",
        "json",
    ]
    captured = _invoke_in_project(project, args)
    _invoke_in_project(project, args)
    assert captured.exit_code == 0, captured.stdout
    detail_path = Path(json.loads(captured.stdout)["detail_path"])

    started = _start_in_project(project, "plan")

    assert started.exit_code == 0, started.stdout
    payload = json.loads(started.stdout)
    detail_content = detail_path.read_text(encoding="utf-8")
    assert payload["read_only"] is True
    assert (
        payload["promotion_ready"][0]["ref"] == "cli.detail-doc.auto-promotion-refresh"
    )
    assert payload["items"][0]["status"] == "candidate"
    assert '"status": "candidate"' in detail_content
    assert '"status": "confirmed"' not in detail_content


def test_learning_capture_sanitizes_existing_index_detail_path(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-cli-detail-path-escape",
                            "problem": "Existing malicious detail path must not escape",
                            "lesson": "Keep generated learning detail writes contained.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.detail-path.escape",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "../../outside.md",
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Existing malicious detail path must not escape",
            "--evidence",
            "Capture should rewrite unsafe detail paths inside learning memory.",
            "--recurrence-key",
            "cli.detail-path.escape",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = Path(payload["detail_path"]).resolve()
    assert detail_path.is_relative_to(learning_dir)
    assert payload["index_entry"]["detail"].startswith("./learn-")
    assert not (project / ".specify" / "outside.md").exists()


def test_learning_capture_sanitizes_existing_index_detail_path_and_id(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "../outside-via-id",
                            "problem": "Existing malicious detail id must not escape",
                            "lesson": "Keep fallback detail writes contained.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.detail-path.escape-via-id",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "../../outside.md",
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Existing malicious detail id must not escape",
            "--evidence",
            "Capture should not trust an existing index id when repairing detail paths.",
            "--recurrence-key",
            "cli.detail-path.escape-via-id",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = Path(payload["detail_path"]).resolve()
    assert detail_path.is_relative_to(learning_dir)
    assert payload["index_entry"]["detail"].startswith("./learn-")
    assert not (project / ".specify" / "outside.md").exists()
    assert not (project / ".specify" / "memory" / "outside-via-id.md").exists()


def test_learning_capture_sanitizes_existing_index_detail_ref_to_index_file(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-cli-index-ref",
                            "problem": "Existing detail ref must not target index",
                            "lesson": "Keep detail docs separate from the index file.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.detail-path.index-ref",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "./INDEX.md",
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
                "## Managed Entries",
                "",
                "Index sentinel content",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Existing detail ref must not target index",
            "--evidence",
            "Capture should not use INDEX.md as a detail document.",
            "--recurrence-key",
            "cli.detail-path.index-ref",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = Path(payload["detail_path"]).resolve()
    assert detail_path.is_relative_to(learning_dir)
    assert detail_path != index_path.resolve()
    assert payload["index_entry"]["detail"].startswith("./learn-")
    index_content = index_path.read_text(encoding="utf-8")
    assert "# Project Learning Index" in index_content
    assert "## Managed Entries" in index_content


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

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summaries = [entry["summary"] for entry in payload["items"]]
    assert "Re-run focused repro before widening scope" in summaries
    assert "Need explicit validation tasks" not in summaries


def test_learning_start_rejects_obsolete_index_shape_without_translation(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "LRN-obsolete-quick-learning",
                            "summary": "Obsolete quick learning summary",
                            "learning_type": "workflow_gap",
                            "source_command": "sp-quick",
                            "evidence": "Obsolete evidence must not become the current lesson.",
                            "recurrence_key": "quick.obsolete-index-shape",
                            "default_scope": "quick-task",
                            "applies_to": ["sp-quick"],
                            "signal_strength": "medium",
                            "status": "confirmed",
                            "first_seen": "2026-05-14T00:00:00Z",
                            "last_seen": "2026-05-14T00:00:00Z",
                            "occurrence_count": 1,
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _start_in_project(project, "quick")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["items"] == []
    assert payload["warnings"]


def test_learning_start_keeps_valid_current_rows_and_rejects_malformed_rows(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _write_learning_index_payload(
        project, _current_and_malformed_index_payloads("debug")
    )

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    recurrence_keys = {entry["ref"] for entry in payload["items"]}
    assert "sp-debug.valid-index-entry" in recurrence_keys
    assert "sp-debug.missing-learning-type" not in recurrence_keys
    assert "sp-debug.summary-only" not in recurrence_keys
    assert "sp-debug.malformed-entry" not in recurrence_keys
    assert payload["warnings"]


@pytest.mark.parametrize("command_name", ["constitution", "map-scan", "map-build"])
def test_learning_start_rejects_non_current_rows_for_all_workflows(
    tmp_path: Path,
    command_name: str,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _write_learning_index_payload(
        project, _current_and_malformed_index_payloads(command_name)
    )

    result = _start_in_project(project, command_name)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    normalized_command = normalize_command_name(command_name)
    recurrence_keys = {entry["ref"] for entry in payload["items"]}
    assert f"{normalized_command}.valid-index-entry" in recurrence_keys
    assert f"{normalized_command}.summary-only" not in recurrence_keys
    assert f"{normalized_command}.malformed-entry" not in recurrence_keys
    assert payload["warnings"]


def test_learning_start_returns_relevant_cards_with_show_argv(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
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
            "Re-run the focused repro before widening debug scope",
            "--evidence",
            "The failing behavior disappeared only after the minimal repro was restored.",
            "--recurrence-key",
            "debug.focused-repro-before-scope-widening",
            "--format",
            "json",
        ],
    )

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [entry["ref"] for entry in payload["items"]] == [
        "debug.focused-repro-before-scope-widening"
    ]
    assert payload["items"][0]["show_argv"][1:3] == ["learning", "show"]
    assert "evidence" not in payload["items"][0]


def test_learning_summary_argv_uses_the_persisted_project_launcher(tmp_path: Path) -> None:
    project = tmp_path / "learning project 项目"
    project.mkdir()
    _seed_learning_templates(project)
    launcher_argv = (
        "uvx",
        "--from",
        "git+https://github.com/chenziyang110/spec-kit-plus.git@abc1234",
        "specify",
    )
    write_project_specify_launcher_config(
        project,
        SpecifyLauncherSpec(
            command=render_command(launcher_argv),
            argv=launcher_argv,
            source="test",
            kind="source_bound",
        ),
    )
    for index in range(2):
        capture_learning(
            project,
            command_name="implement",
            learning_type="pitfall",
            summary=f"Bound launcher learning {index}",
            evidence=f"Evidence {index}",
            recurrence_key=f"launcher.bound-{index}",
        )

    payload = list_learning_summaries(
        project,
        command_name="implement",
        limit=1,
    )

    assert payload["items"][0]["show_argv"][: len(launcher_argv)] == list(
        launcher_argv
    )
    assert payload["pagination"]["next_argv"][: len(launcher_argv)] == list(
        launcher_argv
    )


def test_learning_start_surfaces_repeated_medium_candidate_without_promoting(
    tmp_path: Path,
) -> None:
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

    result = _start_in_project(project, "plan")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promotion_ready = [entry["summary"] for entry in payload["promotion_ready"]]
    relevant_cards = [entry["summary"] for entry in payload["items"]]
    assert "Always preserve verification tasks in planning" in promotion_ready
    assert "Always preserve verification tasks in planning" in relevant_cards
    assert payload["items"][0]["source_layer"] == "candidate"


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
    start = _start_in_project(project, "implement")

    assert captured.exit_code == 0, captured.stdout
    assert promoted.exit_code == 0, promoted.stdout
    promoted_payload = json.loads(promoted.stdout)
    start_payload = json.loads(start.stdout)
    assert promoted_payload["status"] == "promoted-rule"
    rule_summaries = [entry["summary"] for entry in start_payload["items"]]
    assert "Always name touched shared surfaces explicitly" in rule_summaries
    assert start_payload["items"][0]["source_layer"] == "project-rule"


def test_learning_start_exposes_confirmed_project_constraint_for_all_workflows(
    tmp_path: Path,
) -> None:
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
        "accept",
        "analyze",
        "ask",
        "auto",
        "checklist",
        "clarify",
        "constitution",
        "debug",
        "deep-research",
        "design",
        "discussion",
        "explain",
        "fast",
        "implement",
        "implement-teams",
        "integrate",
        "map-build",
        "map-rebuild",
        "map-scan",
        "map-update",
        "plan",
        "prd",
        "prd-build",
        "prd-scan",
        "quick",
        "specify",
        "tasks",
        "taskstoissues",
        "team",
    )

    for command_name in workflow_commands:
        result = _start_in_project(project, command_name)
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        relevant_learnings = [entry["summary"] for entry in payload["items"]]
        assert (
            "Use the validated build surface before retrying native compilation"
            in relevant_learnings
        )
        assert any(
            item["summary"]
            == "Use the validated build surface before retrying native compilation"
            and item["source_layer"] == "confirmed-learning"
            for item in payload["items"]
        )


def test_learning_start_surfaces_single_high_signal_candidate_for_confirmation(
    tmp_path: Path,
) -> None:
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

    result = _start_in_project(project, "implement")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    confirmation = [entry["summary"] for entry in payload["needs_confirmation"]]

    assert (
        "Validate the shell and solution platform before retrying MSBuild"
        in confirmation
    )
    assert any(
        item["summary"]
        == "Validate the shell and solution platform before retrying MSBuild"
        and item["source_layer"] == "candidate"
        and "sp-implement" in item["why_relevant"]
        for item in payload["items"]
    )


def test_learning_start_surfaces_repeated_high_signal_candidate_without_promoting(
    tmp_path: Path,
) -> None:
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

    result = _start_in_project(project, "implement")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promotion_ready = [entry["summary"] for entry in payload["promotion_ready"]]
    relevant_candidates = [entry["summary"] for entry in payload["items"]]
    assert "Always name touched shared surfaces explicitly" in promotion_ready
    assert "Always name touched shared surfaces explicitly" in relevant_candidates
    assert payload["items"][0]["source_layer"] == "candidate"


def test_learning_start_promotion_ready_preserves_structured_learning_fields(
    tmp_path: Path,
) -> None:
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

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promotion_ready = next(
        entry
        for entry in payload["promotion_ready"]
        if entry["ref"] == "build.shell.must.be.validated"
    )
    assert set(promotion_ready) == {"ref", "summary", "occurrences"}

    shown = _invoke_in_project(
        project,
        ["learning", "show", "--ref", promotion_ready["ref"], "--format", "json"],
    )
    detail = json.loads(shown.stdout)
    assert detail["lifecycle"]["pain_score"] == 7
    assert detail["evidence"]["false_starts"] == [
        "retrying msbuild from the wrong shell"
    ]
    assert detail["evidence"]["rejected_paths"] == ["source-code regression"]
    assert (
        detail["evidence"]["decisive_signal"]
        == "the same build passed immediately after switching shells"
    )
    assert detail["evidence"]["root_cause_family"] == "native-build-shell-mismatch"
    assert detail["lifecycle"]["injection_targets"] == ["sp-debug"]
    assert (
        detail["lifecycle"]["promotion_hint"]
        == "promote whenever native build setup is involved"
    )


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


def test_learning_aggregate_write_report_creates_markdown_output(
    tmp_path: Path,
) -> None:
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


def test_learning_start_exposes_compact_promotion_and_confirmation_cards(
    tmp_path: Path,
) -> None:
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

    result = _start_in_project(project, "implement")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["items"][0]["ref"] == "shared.boundary.pattern"
    assert payload["promotion_ready"] == [
        {
            "ref": "shared.boundary.pattern",
            "summary": "Need to preserve shared boundary pattern",
            "occurrences": 2,
        }
    ]
    assert payload["needs_confirmation"][0]["ref"] == "shared.boundary.pattern"


def test_learning_start_defaults_to_compact_read_only_intake(tmp_path: Path) -> None:
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
            "Use the project-pinned launcher",
            "--evidence",
            "The global executable resolved to another checkout.",
            "--recurrence-key",
            "tooling.project-pinned-launcher",
            "--format",
            "json",
        ],
    )

    result = _start_in_project(project, "spx-debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "detail_level" not in payload
    assert payload["read_only"] is True
    assert payload["command"] == "sp-debug"
    assert payload["policy"] == "consume-capture"
    assert payload["items"][0]["ref"] == "tooling.project-pinned-launcher"
    assert "evidence" not in payload["items"][0]
    assert payload["items"][0]["show_argv"][1:3] == ["learning", "show"]
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "project-learning-record-schema.json"
        ).read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_learning_list_and_show_use_progressive_agent_contract(tmp_path: Path) -> None:
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
            "implement",
            "--type",
            "verification_gap",
            "--summary",
            "Verify the real entrypoint after generated-surface changes",
            "--problem",
            "Unit tests can pass while the generated integration remains stale.",
            "--action",
            "Regenerate the integration and verify its real entrypoint.",
            "--trigger",
            "generated surface changed",
            "--success",
            "installed output matches the source template",
            "--avoid",
            "claiming completion from source-only tests",
            "--exception",
            "no generated or mirrored consumer exists",
            "--evidence",
            "A prior source-only fix left installed commands stale.",
            "--recurrence-key",
            "verification.generated-entrypoint",
            "--format",
            "json",
        ],
    )
    assert captured.exit_code == 0, captured.stdout
    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Keep a second low-signal summary for pagination",
            "--evidence",
            "This record verifies deterministic continuation arguments.",
            "--recurrence-key",
            "verification.pagination-second",
            "--signal",
            "low",
            "--format",
            "json",
        ],
    )
    assert second.exit_code == 0, second.stdout

    listed = _invoke_in_project(
        project,
        [
            "learning",
            "list",
            "--command",
            "spx-implement",
            "--limit",
            "1",
            "--format",
            "json",
        ],
    )
    assert listed.exit_code == 0, listed.stdout
    list_payload = json.loads(listed.stdout)
    assert "detail_level" not in list_payload
    assert list_payload["pagination"]["returned"] == 1
    assert list_payload["pagination"]["next_argv"][1:3] == ["learning", "list"]
    assert "--cursor" in list_payload["pagination"]["next_argv"]
    assert (
        list_payload["items"][0]["action"]
        == "Regenerate the integration and verify its real entrypoint."
    )
    assert "evidence" not in list_payload["items"][0]

    all_listed = _invoke_in_project(
        project,
        ["learning", "list", "--command", "spx-implement", "--all", "--format", "json"],
    )
    assert all_listed.exit_code == 0, all_listed.stdout
    all_payload = json.loads(all_listed.stdout)
    assert (
        all_payload["pagination"]["returned"] == all_payload["pagination"]["total"] == 2
    )
    assert all_payload["pagination"]["next_argv"] is None

    shown = _invoke_in_project(
        project,
        [
            "learning",
            "show",
            "--ref",
            "verification.generated-entrypoint",
            "--format",
            "json",
        ],
    )
    assert shown.exit_code == 0, shown.stdout
    detail = json.loads(shown.stdout)
    assert "detail_level" not in detail
    assert detail["guidance"] == {
        "problem": "Unit tests can pass while the generated integration remains stale.",
        "action": "Regenerate the integration and verify its real entrypoint.",
        "avoid": ["claiming completion from source-only tests"],
        "success_criteria": ["installed output matches the source template"],
        "exceptions": ["no generated or mirrored consumer exists"],
    }
    assert "generated surface changed" in detail["applicability"]["trigger_signals"]
    assert (
        detail["evidence"]["observation"]
        == "A prior source-only fix left installed commands stale."
    )

    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "project-learning-record-schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(list_payload)) == []
    assert list(Draft202012Validator(schema).iter_errors(all_payload)) == []
    assert list(Draft202012Validator(schema).iter_errors(detail)) == []


def test_learning_start_does_not_create_missing_learning_files(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)

    result = _start_in_project(project, "plan")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["items"] == []
    assert payload["warnings"]
    assert not (project / ".specify" / "memory" / "learnings" / "INDEX.md").exists()
    assert not (project / ".planning" / "learnings").exists()


def test_learning_consumer_commands_do_not_mutate_existing_storage(
    tmp_path: Path,
) -> None:
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
            "Keep consumption read-only",
            "--evidence",
            "Read commands must not update timestamps, recurrence, or lifecycle state.",
            "--recurrence-key",
            "learning.reads-are-pure",
            "--format",
            "json",
        ],
    )

    def snapshot() -> dict[str, bytes]:
        return {
            path.relative_to(project).as_posix(): path.read_bytes()
            for root in (
                project / ".specify" / "memory",
                project / ".planning" / "learnings",
            )
            for path in root.rglob("*")
            if path.is_file()
        }

    before = snapshot()
    commands = [
        ["learning", "start", "--command", "spx-plan", "--format", "json"],
        ["learning", "list", "--command", "spx-plan", "--all", "--format", "json"],
        ["learning", "show", "--ref", "learning.reads-are-pure", "--format", "json"],
    ]
    for args in commands:
        result = _invoke_in_project(project, args)
        assert result.exit_code == 0, result.stdout

    assert snapshot() == before


def test_learning_help_surfaces_low_level_helper_commands() -> None:
    result = runner.invoke(app, ["learning", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    assert "ensure" in result.stdout
    assert "status" in result.stdout
    assert "start" in result.stdout
    assert "list" in result.stdout
    assert "show" in result.stdout
    assert "capture" in result.stdout
    assert "capture-auto" in result.stdout
    assert "promote" in result.stdout


def test_learning_start_exposes_only_the_current_compact_contract(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)

    help_result = runner.invoke(
        app, ["learning", "start", "--help"], catch_exceptions=False
    )
    obsolete_result = _invoke_in_project(
        project,
        [
            "learning",
            "start",
            "--command",
            "plan",
            "--detail-level",
            "full",
            "--format",
            "json",
        ],
    )

    assert help_result.exit_code == 0, help_result.stdout
    assert "--detail-level" not in strip_ansi(help_result.stdout)
    assert obsolete_result.exit_code != 0


def test_learning_capture_auto_help_mentions_broader_state_surfaces() -> None:
    result = runner.invoke(
        app, ["learning", "capture-auto", "--help"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.stdout
    output = strip_ansi(result.stdout)
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


def test_project_constraint_default_applies_to_includes_test_and_map_codebase(
    tmp_path: Path,
) -> None:
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
    assert "sp-implement" in applies_to
    assert "sp-debug" in applies_to
    assert "sp-map-scan" in applies_to
    assert "sp-map-build" in applies_to


def test_learning_capture_accepts_structured_path_learning_fields(
    tmp_path: Path,
) -> None:
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


def test_learning_capture_auto_implement_writes_candidates_from_tracker_state(
    tmp_path: Path,
) -> None:
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
    summaries = [item["entry"]["summary"] for item in payload["captured"]]
    assert payload["status"] == "captured"
    assert (
        "Rerun planned validation after implementation recovery before resolving the feature"
        in summaries
    )
    assert (
        "Failed implementation tasks should keep execution in recovery until validation turns green"
        in summaries
    )


def test_learning_capture_auto_implement_writes_index_details(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T004"],
        completed_checks=["pytest tests/test_demo.py -q"],
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
    assert payload["status"] == "captured"
    captured = payload["captured"][0]
    assert "index_entry" in captured
    detail_path = Path(captured["detail_path"])
    assert detail_path.exists()
    assert "Observed auto-capture evidence" in detail_path.read_text(encoding="utf-8")


def test_learning_capture_auto_implement_extracts_gap_and_constraint_patterns(
    tmp_path: Path,
) -> None:
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
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
    assert "implement.execution-blockers-feed-back-into-planning" in keys
    assert "implement.external-or-human-blockers-are-project-constraints" in keys


def test_learning_capture_auto_debug_writes_candidates_from_resolved_session(
    tmp_path: Path,
) -> None:
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
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
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


def test_learning_capture_auto_ignores_timestamp_only_tracker_changes(
    tmp_path: Path,
) -> None:
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


def test_learning_capture_auto_quick_extracts_fallback_constraint(
    tmp_path: Path,
) -> None:
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
                "active_lane: leader-inline-fallback",
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
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
    assert (
        "quick.leader-inline-fallback-preserves-runtime-unavailability-reason" in keys
    )


def test_learning_capture_auto_workflow_state_records_blocked_reason(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "002-demo"
    _write_workflow_state(
        feature_dir,
        next_command="",
        status="blocked",
        blocked_reason="Generated command guidance omitted the runtime helper argument required by the CLI.",
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
    assert payload["status"] == "captured"
    entries = [item["entry"] for item in payload["captured"]]
    keys = [entry["recurrence_key"] for entry in entries]
    assert "sp-plan.workflow-state-preserves-blocked-reason" in keys
    blocked = next(
        entry
        for entry in entries
        if entry["recurrence_key"] == "sp-plan.workflow-state-preserves-blocked-reason"
    )
    assert blocked["recommended_action"].startswith("Preserve the blocker")


def test_learning_capture_auto_plan_extracts_route_reason_false_starts_and_constraints(
    tmp_path: Path,
) -> None:
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
    entries = [item["entry"] for item in payload["captured"]]
    keys = [entry["recurrence_key"] for entry in entries]
    assert payload["status"] == "captured"
    assert "sp-plan.workflow-state-preserves-reentry-reason" in keys
    assert "sp-plan.workflow-state-preserves-false-starts" in keys
    assert "sp-plan.workflow-state-promotes-discovered-constraints" in keys
    by_key = {entry["recurrence_key"]: entry for entry in entries}
    assert by_key["sp-plan.workflow-state-preserves-reentry-reason"][
        "recommended_action"
    ].startswith("Preserve the next command")
    assert by_key["sp-plan.workflow-state-preserves-false-starts"][
        "recommended_action"
    ].startswith("Check recorded false starts")
    assert by_key["sp-plan.workflow-state-promotes-discovered-constraints"][
        "recommended_action"
    ].startswith("Apply the recorded dependency")


def test_learning_capture_auto_materializes_explicit_semantic_triggers(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "semantic-trigger"
    long_correction = (
        "sp-plan must not create tasks.md before sp-tasks, and it must preserve the "
        "complete user rationale even when that rationale exceeds a compact summary "
        "length because the detail is durable evidence rather than display-only output"
    )
    _write_workflow_state(
        feature_dir,
        trigger_signals=[
            f"user_correction: {long_correction}",
            "cognition_gap: generated integration was absent from the path index",
        ],
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
    entries = [item["entry"] for item in payload["captured"]]
    by_type = {entry["learning_type"]: entry for entry in entries}
    assert by_type["user_preference"]["recommended_action"].startswith(
        "Apply the corrected assumption"
    )
    assert long_correction in by_type["user_preference"]["summary"]
    assert long_correction in by_type["user_preference"]["evidence"]
    assert by_type["map_coverage_gap"]["trigger_signals"] == [
        "cognition_gap: generated integration was absent from the path index"
    ]


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
    _write_tasks_and_worker_result(feature_dir)

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


def test_implement_closeout_returns_blocked_json_when_session_state_is_missing(
    tmp_path: Path,
) -> None:
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

    assert result.exit_code == 10, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["hook_result"]["status"] == "blocked"
    assert payload["blockers"]
    assert any(
        "workflow-state.md" in message or "implement-tracker.md" in message
        for message in payload["hook_result"]["errors"]
    )


def test_implement_help_surfaces_closeout_command() -> None:
    result = runner.invoke(app, ["implement", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    assert "closeout" in result.stdout
