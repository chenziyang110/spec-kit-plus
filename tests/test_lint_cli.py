from __future__ import annotations

import importlib

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.command_catalog import show_catalog_command


def test_lint_cli_forwards_compact_agent_output_options(monkeypatch) -> None:
    specify_lint = importlib.import_module("specify_cli.lint")
    captured: dict[str, object] = {}

    def fake_run(args: list[str], *, force: bool = False) -> int:
        captured["args"] = args
        captured["force"] = force
        return 0

    monkeypatch.setattr(specify_lint, "run", fake_run)

    result = CliRunner().invoke(
        app,
        [
            "lint",
            "--dir",
            ".specify/features/001-demo",
            "--tier",
            "deep",
            "--format",
            "json",
            "--show-passes",
            "--force-download",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "args": [
            "-dir",
            ".specify/features/001-demo",
            "-tier",
            "deep",
            "-format",
            "json",
            "-show-passes",
        ],
        "force": True,
    }


def test_lint_cli_contract_is_strict_and_agent_discoverable(monkeypatch) -> None:
    specify_lint = importlib.import_module("specify_cli.lint")
    called = False

    def fake_run(args: list[str], *, force: bool = False) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(specify_lint, "run", fake_run)

    invalid = CliRunner().invoke(app, ["lint", "--format", "yaml"])
    detail = show_catalog_command(app, "lint")["data"]
    parameters = {parameter["name"]: parameter for parameter in detail["parameters"]}

    assert invalid.exit_code == 2
    assert called is False
    assert parameters["output_format"]["type"]["choices"] == ["text", "json"]
    assert parameters["tier"]["type"]["choices"] == ["light", "standard", "deep"]
    assert "--show-passes" in parameters["show_passes"]["flags"]
    assert detail["machine_output"] == {
        "declared": True,
        "format_option": "--format",
        "choices": ["text", "json"],
    }


def test_learning_agent_formats_are_strict_and_discoverable() -> None:
    invalid = CliRunner().invoke(
        app,
        ["learning", "start", "--command", "plan", "--format", "yaml"],
    )
    detail = show_catalog_command(app, "learning.start")["data"]
    output_format = next(
        parameter
        for parameter in detail["parameters"]
        if "--format" in parameter["flags"]
    )

    assert invalid.exit_code == 2
    assert output_format["type"]["choices"] == ["text", "json"]
