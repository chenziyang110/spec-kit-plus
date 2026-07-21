import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from specify_cli import app, learnings


runner = CliRunner()


def _seed_learning_templates(project: Path) -> None:
    source = Path(__file__).parents[1] / "templates"
    target = project / ".specify" / "templates"
    target.mkdir(parents=True, exist_ok=True)
    for name in (
        "project-rules-template.md",
        "project-confirmed-learnings-template.md",
        "project-learnings-index-template.md",
        "project-learning-detail-template.md",
    ):
        (target / name).write_text(
            (source / name).read_text(encoding="utf-8"), encoding="utf-8"
        )


def _invoke(project: Path, args: list[str]):
    previous = Path.cwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(previous)


def _capture(
    project: Path,
    *,
    recurrence_key: str,
    command: str = "implement",
    facets: dict[str, list[str]] | None = None,
    signal: str = "medium",
) -> dict[str, object]:
    return learnings.capture_learning(
        project,
        command_name=command,
        learning_type="pitfall",
        summary=f"Learning for {recurrence_key}",
        evidence=f"Evidence for {recurrence_key}",
        recurrence_key=recurrence_key,
        signal_strength=signal,
        applies_to=[f"sp-{command}"],
        trigger_signals=["live operation evidence"],
        facets=facets,
    )


def test_capture_projects_and_merges_structured_learning_facets(tmp_path: Path) -> None:
    _seed_learning_templates(tmp_path)
    first = _capture(
        tmp_path,
        recurrence_key="archive.password-bridge",
        facets={
            "operation_owners": ["BestZipImmediateExtractFlow"],
            "consumer_owners": ["BestZipAppShellView"],
        },
    )
    second = _capture(
        tmp_path,
        recurrence_key="archive.password-bridge",
        facets={
            "operation_owners": ["bestzipimmediateextractflow"],
            "outcomes": ["passwordMissing", "passwordIncorrect"],
        },
    )

    expected_facets = {
        "operation_owners": ["BestZipImmediateExtractFlow"],
        "consumer_owners": ["BestZipAppShellView"],
        "outcomes": ["passwordIncorrect", "passwordMissing"],
    }
    assert first["entry"]["facets"]["operation_owners"] == [
        "BestZipImmediateExtractFlow"
    ]
    assert second["entry"]["facets"] == expected_facets
    assert second["index_entry"]["facets"] == expected_facets

    detail = learnings.show_learning_detail(
        tmp_path, learning_ref="archive.password-bridge"
    )
    assert detail["applicability"]["facets"] == expected_facets
    detail_text = Path(second["detail_path"]).read_text(encoding="utf-8")
    assert "## Structured Facets" in detail_text
    assert "operation_owners: BestZipImmediateExtractFlow" in detail_text


def test_exact_operation_owner_recalls_cross_command_learning_and_outranks_generic(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    _capture(
        tmp_path,
        recurrence_key="archive.password-bridge",
        facets={
            "operation_owners": ["BestZipImmediateExtractFlow"],
            "consumer_owners": ["BestZipAppShellView"],
        },
        signal="low",
    )
    for _ in range(3):
        _capture(
            tmp_path,
            recurrence_key="specify.generic-high-frequency",
            command="specify",
            signal="high",
        )

    payload = learnings.list_learning_summaries(
        tmp_path,
        command_name="specify",
        task_context={
            "operation_owners": ["bestzipimmediateextractflow"],
            "consumer_owners": ["FinderSyncConsumer"],
        },
    )

    assert payload["items"][0]["ref"] == "archive.password-bridge"
    assert payload["items"][0]["context_match"] == {
        "matched_facets": {"operation_owners": ["BestZipImmediateExtractFlow"]},
        "matched_dimensions": 1,
        "matched_values": 1,
        "exact_operation_owner": True,
        "cross_command": True,
    }
    assert payload["task_context"]["consumer_owners"] == ["FinderSyncConsumer"]


def test_cross_command_context_requires_owner_or_two_matching_dimensions(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    _capture(
        tmp_path,
        recurrence_key="archive.outcome-only",
        facets={"outcomes": ["passwordMissing"]},
    )
    _capture(
        tmp_path,
        recurrence_key="archive.outcome-and-state",
        facets={
            "outcomes": ["passwordMissing"],
            "states": ["awaitingUserInput"],
        },
    )
    _capture(
        tmp_path,
        recurrence_key="archive.owner-prefix",
        facets={"operation_owners": ["ZipLegacy"]},
    )

    outcome_only = learnings.list_learning_summaries(
        tmp_path,
        command_name="specify",
        task_context={"outcomes": ["passwordMissing"]},
    )
    assert outcome_only["items"] == []

    two_dimensions = learnings.list_learning_summaries(
        tmp_path,
        command_name="specify",
        task_context={
            "outcomes": ["passwordMissing"],
            "states": ["awaitingUserInput"],
        },
    )
    assert [item["ref"] for item in two_dimensions["items"]] == [
        "archive.outcome-and-state"
    ]

    exact_owner = learnings.list_learning_summaries(
        tmp_path,
        command_name="specify",
        task_context={"operation_owners": ["Zip"]},
    )
    assert exact_owner["items"] == []


def test_contextual_start_promotes_owner_match_into_top_twenty(tmp_path: Path) -> None:
    _seed_learning_templates(tmp_path)
    _capture(
        tmp_path,
        recurrence_key="archive.owner-match",
        facets={"operation_owners": ["ArchiveFlow"]},
        signal="low",
    )
    for index in range(21):
        _capture(
            tmp_path,
            recurrence_key=f"specify.frequent-{index:02d}",
            command="specify",
            signal="high",
        )

    default = learnings.start_learning_session(tmp_path, command_name="specify")
    contextual = learnings.start_learning_session(
        tmp_path,
        command_name="specify",
        task_context={"operation_owners": ["archiveflow"]},
    )

    assert all(item["ref"] != "archive.owner-match" for item in default["items"])
    assert contextual["items"][0]["ref"] == "archive.owner-match"
    assert contextual["task_context"] == {"operation_owners": ["archiveflow"]}


def test_context_cli_validates_values_and_preserves_pagination_argv(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    ensure = _invoke(tmp_path, ["learning", "ensure", "--format", "json"])
    assert ensure.exit_code == 0, ensure.stdout
    captured = _invoke(
        tmp_path,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Preserve operation-owned recovery",
            "--evidence",
            "A new consumer dropped a recoverable result.",
            "--recurrence-key",
            "archive.context-cli",
            "--context",
            "operation_owner=ArchiveFlow",
            "--format",
            "json",
        ],
    )
    assert captured.exit_code == 0, captured.stdout
    _capture(
        tmp_path,
        recurrence_key="specify.context-pagination",
        command="specify",
    )

    listed = _invoke(
        tmp_path,
        [
            "learning",
            "list",
            "--command",
            "specify",
            "--context",
            "operation_owner=ArchiveFlow",
            "--limit",
            "1",
            "--format",
            "json",
        ],
    )
    assert listed.exit_code == 0, listed.stdout
    payload = json.loads(listed.stdout)
    assert payload["items"][0]["ref"] == "archive.context-cli"
    assert "--context" not in payload["items"][0]["show_argv"]
    next_argv = payload["pagination"]["next_argv"]
    assert next_argv is not None
    context_index = next_argv.index("--context")
    assert next_argv[context_index + 1] == "operation_owner=ArchiveFlow"

    invalid = _invoke(
        tmp_path,
        [
            "learning",
            "start",
            "--command",
            "specify",
            "--context",
            "unknown_owner=ArchiveFlow",
            "--format",
            "json",
        ],
    )
    assert invalid.exit_code == 2
    assert "unknown context facet" in (invalid.stdout + invalid.stderr).lower()


def test_malformed_optional_facets_warn_without_dropping_index_row(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    _capture(
        tmp_path,
        recurrence_key="archive.legacy-owner-signal",
        facets=None,
    )
    index_path = tmp_path / ".specify" / "memory" / "learnings" / "INDEX.md"
    content = index_path.read_text(encoding="utf-8")
    begin = "<!-- SPECKIT_LEARNING_DATA_BEGIN -->"
    end = "<!-- SPECKIT_LEARNING_DATA_END -->"
    before, rest = content.split(begin, 1)
    payload_text, after = rest.split(end, 1)
    payloads = json.loads(payload_text)
    payloads[0]["trigger_signals"].append("ArchiveFlow")
    payloads[0]["facets"] = {
        "operation_owners": ["ArchiveFlow", 7],
        "unknown": ["ignored"],
    }
    index_path.write_text(
        before + begin + "\n" + json.dumps(payloads, indent=2) + "\n" + end + after,
        encoding="utf-8",
    )

    payload = learnings.list_learning_summaries(
        tmp_path,
        command_name="specify",
        task_context={"operation_owners": ["ArchiveFlow"]},
    )

    assert payload["items"][0]["ref"] == "archive.legacy-owner-signal"
    assert any("facet_warning" in warning for warning in payload["warnings"])
    assert not any("skipped" in warning for warning in payload["warnings"])


def test_legacy_trigger_signal_supports_exact_operation_owner_context(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    _capture(
        tmp_path,
        recurrence_key="archive.legacy-owner-signal",
        facets=None,
    )
    index_path = tmp_path / ".specify" / "memory" / "learnings" / "INDEX.md"
    content = index_path.read_text(encoding="utf-8")
    begin = "<!-- SPECKIT_LEARNING_DATA_BEGIN -->"
    end = "<!-- SPECKIT_LEARNING_DATA_END -->"
    before, rest = content.split(begin, 1)
    payload_text, after = rest.split(end, 1)
    payloads = json.loads(payload_text)
    payloads[0]["trigger_signals"].append("ArchiveFlow")
    payloads[0].pop("facets", None)
    index_path.write_text(
        before + begin + "\n" + json.dumps(payloads, indent=2) + "\n" + end + after,
        encoding="utf-8",
    )

    payload = learnings.list_learning_summaries(
        tmp_path,
        command_name="specify",
        task_context={"operation_owners": ["ArchiveFlow"]},
    )

    assert payload["items"][0]["ref"] == "archive.legacy-owner-signal"
    assert payload["items"][0]["context_match"]["cross_command"] is True


def test_contextual_payloads_validate_against_agent_read_schema(tmp_path: Path) -> None:
    _seed_learning_templates(tmp_path)
    _capture(
        tmp_path,
        recurrence_key="archive.schema-context",
        command="specify",
        facets={"operation_owners": ["ArchiveFlow"]},
    )
    context = {"operation_owners": ["ArchiveFlow"]}
    listed = learnings.list_learning_summaries(
        tmp_path, command_name="specify", task_context=context
    )
    started = learnings.start_learning_session(
        tmp_path, command_name="specify", task_context=context
    )
    detailed = learnings.show_learning_detail(
        tmp_path, learning_ref="archive.schema-context"
    )
    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "templates"
            / "project-learning-record-schema.json"
        ).read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(listed)) == []
    assert list(validator.iter_errors(started)) == []
    assert list(validator.iter_errors(detailed)) == []
