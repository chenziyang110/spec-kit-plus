from __future__ import annotations

from typer.testing import CliRunner

import specify_cli
from specify_cli import app
from specify_cli.command_catalog import show_catalog_command
from specify_cli import specify_runtime


def test_lint_cli_forwards_compact_agent_output_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        args: list[str], *, cwd, check: bool = True, install_if_missing: bool = False
    ) -> dict[str, object]:
        captured["args"] = args
        captured["check"] = check
        captured["install_if_missing"] = install_if_missing
        return {"status": "ok", "summary": "spec valid"}

    def fake_ensure_binary(*, force: bool = False):
        captured["force"] = force

    monkeypatch.setattr(specify_cli, "run_specify_runtime", fake_run)
    monkeypatch.setattr(specify_runtime, "ensure_binary", fake_ensure_binary)

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
            "validate",
            "spec",
            "--dir",
            ".specify/features/001-demo",
            "--tier",
            "deep",
            "--format",
            "json",
            "--show-passes",
        ],
        "check": False,
        "install_if_missing": True,
        "force": True,
    }


def test_lint_cli_contract_is_strict_and_agent_discoverable(monkeypatch) -> None:
    called = False

    def fake_run(
        args: list[str], *, cwd, check: bool = True, install_if_missing: bool = False
    ) -> dict[str, object]:
        nonlocal called
        called = True
        return {"status": "ok"}

    monkeypatch.setattr(specify_cli, "run_specify_runtime", fake_run)

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
