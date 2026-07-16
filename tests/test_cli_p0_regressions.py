import json
import os
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import specify_cli
from specify_cli import app


runner = CliRunner()


def test_map_build_help_uses_current_schema() -> None:
    description = specify_cli.SKILL_DESCRIPTIONS["map-build"]

    assert "schema v5" in description
    assert "schema v4" not in description


def test_discussion_mark_consumed_archive_honors_json(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)
    calls: list[str] = []

    def fake_helper(mode: str, **_: object) -> dict[str, object]:
        calls.append(mode)
        return {
            "status": "ok",
            "discussion": {
                "slug": "cli-audit",
                "status": "archived" if mode == "archive" else "consumed",
                "workspace_path": ".specify/discussions/archive/cli-audit",
            },
        }

    monkeypatch.setattr(specify_cli, "_run_discussion_helper", fake_helper)
    previous = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "discussion",
                "mark-consumed",
                "cli-audit",
                "--feature-dir",
                ".specify/features/001-cli-audit",
                "--archive",
                "--json",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(previous)

    assert result.exit_code == 0
    assert calls == ["mark-consumed", "archive"]
    payload = json.loads(result.stdout)
    assert payload["discussion"]["status"] == "archived"


def test_quick_helper_prefers_bundled_core_pack(monkeypatch, tmp_path: Path) -> None:
    core_pack = tmp_path / "core-pack"
    script_dir = core_pack / "scripts" / ("powershell" if os.name == "nt" else "bash")
    script_dir.mkdir(parents=True)
    script_name = "quick-state.ps1" if os.name == "nt" else "quick-state.sh"
    expected = script_dir / script_name
    expected.write_text("# bundled helper\n", encoding="utf-8")

    monkeypatch.setattr(specify_cli, "_locate_core_pack", lambda: core_pack)
    if os.name == "nt":
        monkeypatch.setattr(specify_cli.shutil, "which", lambda name: name if name == "pwsh" else None)

    _, resolved = specify_cli._quick_helper_script()

    assert resolved == expected


def test_blocked_hook_uses_stable_blocked_exit_code(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / "001-hook"
    feature.mkdir(parents=True)
    result_object = SimpleNamespace(
        status="blocked",
        to_dict=lambda: {
            "status": "blocked",
            "summary": "workflow state is incomplete",
            "actions": [],
            "errors": ["missing workflow state"],
            "warnings": [],
            "writes": [],
            "data": {},
        },
    )
    monkeypatch.setattr(
        "specify_cli.hooks.engine.run_quality_hook",
        lambda *_args, **_kwargs: result_object,
    )
    previous = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "hook",
                "validate-state",
                "--command",
                "plan",
                "--feature-dir",
                str(feature),
                "--format",
                "json",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(previous)

    assert result.exit_code == 10
    assert json.loads(result.stdout)["status"] == "blocked"
