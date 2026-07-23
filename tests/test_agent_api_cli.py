import json

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.command_catalog import command_catalog


runner = CliRunner()


@pytest.mark.parametrize("retired", ("handshake", "list"))
def test_python_api_does_not_duplicate_runtime_discovery_commands(retired: str) -> None:
    result = runner.invoke(app, ["api", retired, "--help"])

    assert result.exit_code != 0
    assert f"No such command '{retired}'" in result.output


def test_agent_api_show_and_schema_expand_one_record() -> None:
    show_result = runner.invoke(
        app,
        ["api", "show", "learning.start", "--format", "json"],
        catch_exceptions=False,
    )
    schema_result = runner.invoke(
        app,
        ["api", "schema", "workflow-blocker", "--format", "json"],
        catch_exceptions=False,
    )

    assert show_result.exit_code == 0
    assert json.loads(show_result.stdout)["data"]["id"] == "learning.start"
    assert schema_result.exit_code == 0
    schema_payload = json.loads(schema_result.stdout)
    assert schema_payload["data"]["schema_id"] == "workflow-blocker"
    assert schema_payload["data"]["schema"]["type"] == "object"


def test_agent_api_commands_catalog_lists_all_surfaces_progressively() -> None:
    result = runner.invoke(
        app,
        [
            "api",
            "commands",
            "--query",
            "learning",
            "--limit",
            "3",
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["data"]["total_catalog"] > 100
    assert payload["data"]["total_matching"] >= 3
    assert len(payload["items"]) == 3
    assert all("learning" in item["id"] for item in payload["items"])
    assert all("parameters" not in item for item in payload["items"])
    assert all(
        item["show_argv"][:3] == ["specify", "api", "command"]
        for item in payload["items"]
    )


def test_agent_api_command_expands_only_one_cli_operation() -> None:
    result = runner.invoke(
        app,
        ["api", "command", "learning.start", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["id"] == "learning.start"
    assert payload["data"]["argv"] == ["specify", "learning", "start"]
    command_option = next(
        item for item in payload["data"]["parameters"] if "--command" in item["flags"]
    )
    assert command_option["required"] is True
    assert payload["data"]["machine_output"]["format_option"] == "--format"


@pytest.mark.parametrize(
    ("schema_id", "command_id", "runtime_subcommand"),
    [
        ("workflow-enter-input", "workflow.enter", "enter"),
        ("workflow-transition-input", "workflow.transition", "transition"),
        ("workflow-reopen-input", "workflow.reopen", "reopen"),
        ("workflow-resolve-input", "workflow.resolve", "resolve"),
    ],
)
def test_workflow_capabilities_publish_runtime_owned_commands_and_schemas(
    schema_id: str,
    command_id: str,
    runtime_subcommand: str,
) -> None:
    schema_result = runner.invoke(
        app,
        ["api", "schema", schema_id, "--format", "json"],
        catch_exceptions=False,
    )
    capability_result = runner.invoke(
        app,
        ["api", "show", command_id, "--format", "json"],
        catch_exceptions=False,
    )

    assert schema_result.exit_code == 0
    assert capability_result.exit_code == 0
    schema = json.loads(schema_result.stdout)["data"]["schema"]
    capability = json.loads(capability_result.stdout)["data"]

    assert schema["type"] == "object"
    assert capability["input_schema"] == schema_id
    assert capability["command"] == [
        "specify-runtime",
        "workflow",
        runtime_subcommand,
    ]


def test_agent_api_command_recognizes_boolean_json_output_switches() -> None:
    result = runner.invoke(
        app,
        ["api", "command", "discussion.status", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    machine_output = json.loads(result.stdout)["data"]["machine_output"]
    assert machine_output == {
        "declared": True,
        "format_option": "--json",
        "choices": ["json"],
    }


def test_agent_api_command_extracts_declared_format_values_from_live_help() -> None:
    expected = {
        "api.show": ["json"],
        "design.export": ["json", "tailwind"],
        "debug": ["text", "json", "spawn-json"],
    }

    for command_id, choices in expected.items():
        result = runner.invoke(
            app,
            ["api", "command", command_id, "--format", "json"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        machine_output = json.loads(result.stdout)["data"]["machine_output"]
        assert machine_output["choices"] == choices


def test_agent_api_commands_catalog_covers_the_actual_cross_domain_cli() -> None:
    result = runner.invoke(
        app,
        ["api", "commands", "--limit", "200", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    ids = {item["id"] for item in payload["items"]}
    assert payload["data"]["total_catalog"] == len(ids)
    assert {
        "init",
        "check",
        "lint",
        "learning.start",
        "learning.capture",
        "accept.closeout",
        "hook.validate-artifacts",
        "integration.install",
        "extension.add",
        "sp-teams.status",
    } <= ids
    assert "artifact.scaffold" not in ids
    assert "sp-teams.notify-hook" not in ids


def test_agent_command_catalog_never_requires_side_effect_or_summary_guessing() -> None:
    records = command_catalog(app)
    hints = {record["id"]: record["mutation_hint"] for record in records}
    workflow_records = [
        record for record in records if record["id"].startswith("workflow.")
    ]

    assert [
        record["id"] for record in records if record["mutation_hint"] == "unknown"
    ] == []
    assert [
        record["id"]
        for record in records
        if record["summary"] == "No command summary is declared."
    ] == []
    assert hints["accept.validate"] == "read-only"
    assert hints["discussion.validate-handoff"] == "read-only"
    assert hints["discussion.confirm-handoff"] == "local-write"
    assert hints["hook.build-compaction"] == "local-write"
    assert hints["hook.validate-artifacts"] == "read-only"
    assert hints["hook.validate-state"] == "conditional-local-write"
    assert hints["learning.aggregate"] == "conditional-local-write"
    assert hints["eval.run"] == "inspect-before-execution"
    assert hints["sp-teams.live-probe"] == "inspect-before-execution"
    assert workflow_records == []


def test_python_cli_does_not_publish_a_duplicate_workflow_namespace() -> None:
    result = runner.invoke(app, ["workflow", "show", "--help"])

    assert result.exit_code != 0
    assert "No such command 'workflow'" in result.output
