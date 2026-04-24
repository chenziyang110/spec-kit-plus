from pathlib import Path

from specify_cli.evals import (
    EvalCase,
    create_eval_case,
    ensure_eval_store,
)
from specify_cli.eval_runner import run_eval_suite
from specify_cli.learnings import capture_learning, ensure_learning_files, promote_learning


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in ("project-rules-template.md", "project-learnings-template.md"):
        (target_root / name).write_text(
            (templates_root / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def test_create_eval_case_infers_rule_check_from_promoted_rule(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    ensure_learning_files(project)

    capture_learning(
        project,
        command_name="implement",
        learning_type="project_constraint",
        summary="Always name touched shared surfaces explicitly",
        evidence="confirmed reusable rule",
        recurrence_key="shared.surfaces.must.be.named",
        confirm=True,
    )
    promote_learning(
        project,
        recurrence_key="shared.surfaces.must.be.named",
        target="rule",
    )

    payload = create_eval_case(
        project,
        recurrence_key="shared.surfaces.must.be.named",
    )

    case = payload["case"]
    assert case.recurrence_key == "shared.surfaces.must.be.named"
    assert case.verification_method == "rule-check"
    assert case.target == ".specify/memory/project-rules.md"
    assert case.contains == "Always name touched shared surfaces explicitly"


def test_run_eval_suite_marks_rule_check_case_pass(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    ensure_learning_files(project)
    ensure_eval_store(project)
    (project / ".specify" / "memory" / "project-rules.md").write_text(
        "# Project Rules\n\nAlways use shared contract names.\n",
        encoding="utf-8",
    )

    create_eval_case(
        project,
        recurrence_key="shared.contract.names",
        summary="Shared contract naming rule remains present",
        verification_method="rule-check",
        target=".specify/memory/project-rules.md",
        contains="Always use shared contract names.",
        expect="found",
    )

    payload = run_eval_suite(project)

    assert payload["counts"]["total"] == 1
    assert payload["counts"]["passed"] == 1
    assert payload["cases"][0]["last_result"] == "pass"


def test_run_eval_suite_marks_command_check_case_fail(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    ensure_eval_store(project)

    create_eval_case(
        project,
        recurrence_key="verify.command.failure",
        summary="Command should pass",
        verification_method="command-check",
        command='python -c "import sys; sys.exit(2)"',
        expect="pass",
    )

    payload = run_eval_suite(project)

    assert payload["counts"]["failed"] == 1
    assert payload["cases"][0]["last_result"] == "fail"
