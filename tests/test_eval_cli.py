import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


runner = CliRunner()


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in ("project-rules-template.md", "project-learnings-template.md"):
        (target_root / name).write_text(
            (templates_root / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _invoke_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def test_eval_create_command_writes_case_and_index(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(
        project,
        [
            "eval",
            "create",
            "--recurrence-key",
            "shared.contract.names",
            "--summary",
            "Shared contract naming rule remains present",
            "--verification-method",
            "rule-check",
            "--target",
            ".specify/memory/project-rules.md",
            "--contains",
            "Shared contract naming rule remains present",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    case_path = Path(payload["case_path"])
    index_path = project / ".specify" / "evals" / "index.json"
    assert case_path.exists()
    assert index_path.exists()
    assert payload["case"]["recurrence_key"] == "shared.contract.names"


def test_eval_status_reports_case_counts(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(
        project,
        [
            "eval",
            "create",
            "--recurrence-key",
            "shared.contract.names",
            "--summary",
            "Shared contract naming rule remains present",
            "--verification-method",
            "rule-check",
            "--target",
            ".specify/memory/project-rules.md",
            "--contains",
            "Shared contract naming rule remains present",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["eval", "status", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["counts"]["cases"] == 1


def test_eval_run_updates_last_result(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    (project / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "memory" / "project-rules.md").write_text(
        "# Project Rules\n\nShared contract naming rule remains present\n",
        encoding="utf-8",
    )

    _invoke_in_project(
        project,
        [
            "eval",
            "create",
            "--recurrence-key",
            "shared.contract.names",
            "--summary",
            "Shared contract naming rule remains present",
            "--verification-method",
            "rule-check",
            "--target",
            ".specify/memory/project-rules.md",
            "--contains",
            "Shared contract naming rule remains present",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["eval", "run", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["counts"]["passed"] == 1
    assert payload["cases"][0]["last_result"] == "pass"
