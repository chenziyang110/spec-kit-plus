import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


runner = CliRunner()


def _run_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def test_artifact_help_surface_is_registered() -> None:
    result = runner.invoke(app, ["artifact", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "audit-fixed-cost" in result.output
    assert "scaffold" in result.output


def test_artifact_audit_requires_specify_project(tmp_path: Path) -> None:
    result = _run_in_project(
        tmp_path,
        ["artifact", "audit-fixed-cost", "--format", "json"],
    )

    assert result.exit_code != 0
    assert "Not a Spec Kit Plus project" in result.output


def test_artifact_audit_emits_compact_json(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)

    result = _run_in_project(
        project,
        ["artifact", "audit-fixed-cost", "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["candidate_count"] == 2


def test_artifact_scaffold_writes_quick_status(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)

    result = _run_in_project(
        project,
        [
            "artifact",
            "scaffold",
            "--kind",
            "quick-status",
            "--out",
            ".planning/quick/001-demo/STATUS.md",
            "--vars",
            '{"id":"001","slug":"demo","title":"Demo","trigger":"Fix demo"}',
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "created"
    assert payload["path"] == ".planning/quick/001-demo/STATUS.md"
    assert (project / ".planning" / "quick" / "001-demo" / "STATUS.md").exists()


def test_artifact_scaffold_rejects_absolute_out_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)
    absolute_out = project / ".planning" / "quick" / "001-demo" / "STATUS.md"

    result = _run_in_project(
        project,
        [
            "artifact",
            "scaffold",
            "--kind",
            "quick-status",
            "--out",
            str(absolute_out),
            "--vars",
            '{"id":"001","slug":"demo","title":"Demo","trigger":"Fix demo"}',
            "--format",
            "json",
        ],
    )

    assert result.exit_code != 0
    assert "unsafe_path" in result.output
