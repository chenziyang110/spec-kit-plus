from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from specify_cli import app
from specify_cli import human_acceptance as human_acceptance_module
from specify_cli.human_acceptance import (
    acceptance_closeout_blockers,
    new_human_acceptance_state,
    prepare_human_acceptance,
    route_human_acceptance_repair,
    validate_human_acceptance,
)
from specify_cli.workflow_runtime import (
    enter_workflow,
    show_workflow,
    transition_workflow,
)


ROOT = Path(__file__).resolve().parents[1]


def _feature(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / "001-demo"
    feature.mkdir(parents=True)
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo feature complete.\n", encoding="utf-8"
    )
    return project, feature


def _accepted_state(state_path: Path) -> dict[str, object]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "accepted"
    state["orientation"] = {
        "outcome": "The user can complete the demo flow.",
        "why_it_matters": "The primary task no longer needs a workaround.",
        "user_visible_changes": ["A new Demo action is available."],
        "not_in_scope": ["Administrative reporting is unchanged."],
        "prerequisites": ["Open the demo workspace."],
        "start_here": "Open the application and select Demo.",
    }
    state["scenarios"] = [
        {
            "id": "HA-001",
            "title": "Complete the demo flow",
            "user_value": "The user reaches the expected result.",
            "required": True,
            "start_state": "The application is open on the home screen.",
            "steps": [
                {
                    "id": "HA-001-S01",
                    "action": "Select Demo.",
                    "expected_result": "The Demo screen opens.",
                    "if_failed": "Return the visible error or a screenshot.",
                    "response_prompt": "Reply `seen`; otherwise send the visible error.",
                    "result": "pass",
                    "observed_result": "The Demo screen opened.",
                    "evidence": ["human: seen"],
                }
            ],
            "verdict": "pass",
            "notes": None,
        }
    ]
    state["cursor"] = {"scenario_id": None, "step_id": None}
    state["overall"] = {
        "verdict": "pass",
        "summary": "The human completed the required demo scenario.",
        "next_command": "sp-integrate or spx-integrate",
    }
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return state


def _rejected_state(state_path: Path, *, route: str = "spx-implement") -> None:
    state = _accepted_state(state_path)
    state["status"] = "rejected"
    state["scenarios"][0]["verdict"] = "fail"
    state["scenarios"][0]["steps"][0]["result"] = "fail"
    state["scenarios"][0]["steps"][0]["observed_result"] = (
        "The Demo screen remained closed."
    )
    state["findings"] = [
        {
            "id": "HAF-001",
            "scenario_id": "HA-001",
            "step_id": "HA-001-S01",
            "classification": "product-defect",
            "route": route,
            "expected": "The Demo screen opens.",
            "observed": "The Demo screen remained closed.",
            "evidence": ["human: visible failure"],
            "status": "open",
        }
    ]
    state["cursor"] = {"scenario_id": "HA-001", "step_id": "HA-001-S01"}
    state["overall"] = {
        "verdict": "fail",
        "summary": "The required demo scenario failed.",
        "next_command": route,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def test_template_matches_runtime_empty_state() -> None:
    template = json.loads(
        (ROOT / "templates" / "human-acceptance-state-template.json").read_text(
            encoding="utf-8"
        )
    )

    assert template == new_human_acceptance_state()


def test_human_acceptance_schema_is_valid_and_accepts_the_draft_template() -> None:
    schema = json.loads(
        (ROOT / "templates" / "human-acceptance-state-schema.json").read_text(
            encoding="utf-8"
        )
    )
    template = new_human_acceptance_state()

    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(template)) == []


def test_advanced_acceptance_finding_routes_validate_in_schema_and_runtime(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["findings"] = [
        {
            "id": "HAF-001",
            "scenario_id": "HA-001",
            "step_id": "HA-001-S01",
            "classification": "product-defect",
            "route": "spx-debug",
            "expected": "The Demo screen opens.",
            "observed": "The repaired Demo screen opens.",
            "evidence": ["human: verified repaired behavior"],
            "status": "resolved",
        }
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    schema = json.loads(
        (ROOT / "templates" / "human-acceptance-state-schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(state)
    assert (
        validate_human_acceptance(project, feature, require_accepted=True)["valid"]
        is True
    )


def test_acceptance_paths_cannot_escape_the_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside-feature"
    outside.mkdir()
    (outside / "implementation-summary.md").write_text(
        "# Implementation Summary\n", encoding="utf-8"
    )

    for operation in (prepare_human_acceptance, validate_human_acceptance):
        try:
            operation(project, outside)
        except ValueError as exc:
            assert "inside the current project" in str(exc)
        else:
            raise AssertionError("outside feature_dir was accepted")
    assert not (outside / "human-acceptance.json").exists()


def test_acceptance_closeout_blocker_is_schema_valid_and_guides_a_novice(
    tmp_path: Path,
) -> None:
    _, feature = _feature(tmp_path)
    blocker = acceptance_closeout_blockers(
        feature,
        acceptance_errors=["human acceptance closeout requires status=accepted"],
    )[0]
    schema = json.loads(
        (ROOT / "templates" / "workflow-blocker-schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(blocker)
    assert blocker["human_action_required"] is True
    assert len(blocker["human_action_guide"]["steps"]) == 4
    assert blocker["resume"]["argv"][:3] == ["specify", "accept", "closeout"]


def test_prepare_creates_fingerprinted_state_and_marks_changed_summary_stale(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)

    prepared = prepare_human_acceptance(project, feature)

    assert prepared["status"] == "draft"
    state_path = feature / "human-acceptance.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["source"]["prepared_from_sha256"]
    assert state["source"]["prepared_from_sha256"] == state["source"]["current_sha256"]

    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nThe implementation changed.\n", encoding="utf-8"
    )
    stale = prepare_human_acceptance(project, feature)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert stale["status"] == "stale"
    assert state["status"] == "stale"
    assert state["source"]["prepared_from_sha256"] != state["source"]["current_sha256"]


def test_rejected_acceptance_routes_through_repair_and_returns_to_accept(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = transition_workflow(
            feature,
            target_stage=target,
            expected_revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _rejected_state(state_path)

    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-implement",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )

    assert routed["status"] == "ok"
    assert routed["data"]["stage"] == "implement"
    assert routed["data"]["repair_route"] == "spx-implement"
    reopened = json.loads(state_path.read_text(encoding="utf-8"))
    assert reopened["status"] == "draft"
    assert reopened["source"]["prepared_from_sha256"] == ""
    assert reopened["cursor"] == {
        "scenario_id": "HA-001",
        "step_id": "HA-001-S01",
    }
    assert reopened["scenarios"][0]["verdict"] == "pending"
    assert reopened["scenarios"][0]["steps"][0]["result"] == "pending"
    assert reopened["findings"][0]["status"] == "open"

    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo repair complete.\n", encoding="utf-8"
    )
    prepared = prepare_human_acceptance(project, feature)
    assert prepared["status"] == "draft"
    returned = transition_workflow(
        feature,
        target_stage="accept",
        expected_revision=routed["data"]["revision"],
    )
    assert returned["data"]["stage"] == "accept"
    assert show_workflow(feature)["data"]["status"] == "active"


def test_acceptance_repair_rejects_a_route_that_does_not_match_the_finding(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = transition_workflow(
            feature,
            target_stage=target,
            expected_revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _rejected_state(state_path)
    workflow_before = (feature / "workflow-state.md").read_bytes()
    acceptance_before = state_path.read_bytes()

    with pytest.raises(ValueError, match="routes to spx-implement"):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-debug",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )

    assert (feature / "workflow-state.md").read_bytes() == workflow_before
    assert state_path.read_bytes() == acceptance_before


def test_accept_route_repair_cli_returns_the_deterministic_resume_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = transition_workflow(
            feature,
            target_stage=target,
            expected_revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    _rejected_state(feature / "human-acceptance.json")
    monkeypatch.chdir(project)

    result = CliRunner().invoke(
        app,
        [
            "accept",
            "route-repair",
            "--feature-dir",
            str(feature),
            "--finding-id",
            "HAF-001",
            "--route",
            "spx-implement",
            "--expected-revision",
            str(revision),
            "--evidence",
            "Human observed the required screen did not open.",
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["repair_route"] == "spx-implement"
    assert payload["data"]["resume_after_repair_argv"][:3] == [
        "specify",
        "accept",
        "prepare",
    ]


def test_acceptance_write_failure_cannot_leave_workflow_reopened(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = transition_workflow(
            feature,
            target_stage=target,
            expected_revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _rejected_state(state_path)
    workflow_before = (feature / "workflow-state.md").read_bytes()
    acceptance_before = state_path.read_bytes()

    def fail_acceptance_write(_path: Path, _state: dict[str, object]) -> None:
        raise OSError("simulated read-only acceptance state")

    monkeypatch.setattr(human_acceptance_module, "_write_state", fail_acceptance_write)

    with pytest.raises(OSError, match="read-only"):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-implement",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )

    assert (feature / "workflow-state.md").read_bytes() == workflow_before
    assert state_path.read_bytes() == acceptance_before


def test_prepare_marks_source_change_after_closeout_stale(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    source = project / "src" / "demo.txt"
    source.parent.mkdir()
    source.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "acceptance@example.test"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Acceptance Test"],
        cwd=project,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    prepare_human_acceptance(project, feature)

    source.write_text("after\n", encoding="utf-8")
    stale = prepare_human_acceptance(project, feature)

    assert stale["status"] == "stale"
    state = json.loads((feature / "human-acceptance.json").read_text(encoding="utf-8"))
    assert state["source"]["prepared_from_sha256"] != state["source"]["current_sha256"]


def test_validate_requires_explicit_human_pass_for_every_required_scenario(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)

    accepted = validate_human_acceptance(project, feature, require_accepted=True)

    assert accepted["valid"] is True
    assert accepted["accepted"] is True

    state["scenarios"][0]["verdict"] = "pending"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    invalid = validate_human_acceptance(project, feature, require_accepted=True)

    assert invalid["valid"] is False
    assert (
        "accepted status requires every required scenario to pass" in invalid["errors"]
    )


def test_validate_rejects_accepted_state_with_an_open_finding(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["findings"] = [
        {
            "id": "HAF-001",
            "scenario_id": "HA-001",
            "step_id": "HA-001-S01",
            "classification": "product-defect",
            "route": "spx-debug",
            "expected": "The Demo screen opens.",
            "observed": "The Demo screen remained closed.",
            "evidence": ["human: visible failure"],
            "status": "open",
        }
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert validation["accepted"] is False
    assert any("open" in error and "finding" in error for error in validation["errors"])


def test_validate_detects_implementation_changes_without_a_git_repository(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    source = project / "src" / "demo.txt"
    source.parent.mkdir()
    source.write_text("before\n", encoding="utf-8")
    assert not (project / ".git").exists()
    prepare_human_acceptance(project, feature)
    _accepted_state(feature / "human-acceptance.json")
    assert (
        validate_human_acceptance(project, feature, require_accepted=True)["valid"]
        is True
    )

    source.write_text("after\n", encoding="utf-8")
    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["stale"] is True
    assert validation["valid"] is False


def test_no_git_snapshot_ignores_root_gitignore_matches(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    (project / ".gitignore").write_text(".cache/\n", encoding="utf-8")
    cache_file = project / ".cache" / "runtime.bin"
    cache_file.parent.mkdir()
    cache_file.write_text("before\n", encoding="utf-8")

    prepare_human_acceptance(project, feature)
    _accepted_state(feature / "human-acceptance.json")
    cache_file.write_text("after\n", encoding="utf-8")

    validation = validate_human_acceptance(
        project,
        feature,
        require_accepted=True,
    )

    assert validation["valid"] is True
    assert validation["stale"] is False


def test_in_progress_state_requires_a_real_resume_cursor(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["status"] = "in_progress"
    state["overall"]["verdict"] = "pending"
    state["scenarios"][0]["verdict"] = "pending"
    state["scenarios"][0]["steps"][0]["result"] = "pending"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    invalid = validate_human_acceptance(project, feature)

    assert invalid["valid"] is False
    assert any("cursor.scenario_id" in error for error in invalid["errors"])
    assert any("cursor.step_id" in error for error in invalid["errors"])


def test_accept_cli_closes_only_fresh_explicit_human_acceptance(
    monkeypatch, tmp_path: Path
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    _accepted_state(feature / "human-acceptance.json")
    (feature / "workflow-state.md").write_text(
        """# Workflow State: Demo

## Current Command

- active_command: sp-accept
- status: completed

## Phase Mode

- phase_mode: acceptance-only
- summary: Human accepted every required scenario.

## Allowed Artifact Writes

- human-acceptance.json
- workflow-state.md

## Forbidden Actions

- edit production source code
- edit tests

## Authoritative Files

- implementation-summary.md
- human-acceptance.json

## Next Command

- `/sp.integrate`
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)

    result = CliRunner().invoke(
        app,
        [
            "accept",
            "closeout",
            "--feature-dir",
            str(feature),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "accepted"
    assert payload["human_acceptance"]["accepted"] is True
    assert payload["hook_result"]["status"] == "ok"
