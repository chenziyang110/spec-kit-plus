from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

import specify_cli as specify_cli_module
from specify_cli import app
from specify_cli import human_acceptance as human_acceptance_module
from specify_cli import workflow_runtime as workflow_runtime_module
from specify_cli.human_acceptance import (
    acceptance_closeout_blockers,
    new_human_acceptance_state,
    prepare_human_acceptance,
    route_human_acceptance_repair,
    validate_human_acceptance,
)
from specify_cli.workflow_runtime import (
    WorkflowRuntimeError,
    block_workflow,
    complete_workflow_stage,
    enter_workflow,
    show_workflow,
    terminal_acceptance_snapshot_path,
    transition_workflow,
    workflow_runtime_path,
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


def _complete_then_transition(
    feature: Path,
    *,
    target_stage: str,
    revision: int,
) -> dict[str, object]:
    completed = complete_workflow_stage(feature, expected_revision=revision)
    return transition_workflow(
        feature,
        target_stage=target_stage,
        expected_revision=completed["data"]["revision"],
    )


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


def _rejected_acceptance_at_active_accept(
    project: Path,
    feature: Path,
    *,
    route: str = "spx-implement",
) -> int:
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    _rejected_state(feature / "human-acceptance.json", route=route)
    return int(revision)


def _accepted_acceptance_at_active_accept(project: Path, feature: Path) -> int:
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    _accepted_state(feature / "human-acceptance.json")
    return int(revision)


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


def test_validate_rejects_acceptance_state_symlink_even_with_valid_content(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _accepted_state(state_path)
    external = tmp_path / "external-acceptance.json"
    state_path.replace(external)
    try:
        state_path.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    validation = validate_human_acceptance(
        project,
        feature,
        require_accepted=True,
    )

    assert validation["valid"] is False
    assert validation["accepted"] is False
    assert "symlink" in " ".join(validation["errors"]).lower()


def test_acceptance_closeout_blocker_is_schema_valid_and_guides_a_novice(
    tmp_path: Path,
) -> None:
    _, feature = _feature(tmp_path)
    blocker = acceptance_closeout_blockers(
        feature,
        acceptance={
            "status": "draft",
            "contract_valid": True,
            "errors": ["human acceptance closeout requires status=accepted"],
            "finding_routes": [],
        },
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


def test_corrupt_acceptance_is_agent_owned_before_any_human_review(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    state_path = feature / "human-acceptance.json"
    state_path.write_text("{broken", encoding="utf-8")

    validation = validate_human_acceptance(
        project,
        feature,
        require_accepted=True,
    )
    blocker = acceptance_closeout_blockers(
        feature,
        acceptance=validation,
    )[0]

    assert validation["contract_valid"] is False
    assert blocker["owner"] == "agent"
    assert blocker["human_action_required"] is False
    assert blocker["human_action_guide"] is None
    assert blocker["resume"]["argv"][:3] == ["specify", "accept", "prepare"]


def test_rejected_acceptance_routes_agent_work_without_a_human_tutorial(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    _rejected_state(feature / "human-acceptance.json", route="spx-implement")

    validation = validate_human_acceptance(
        project,
        feature,
        require_accepted=True,
    )
    blocker = acceptance_closeout_blockers(
        feature,
        acceptance=validation,
    )[0]

    assert validation["contract_valid"] is True
    assert validation["finding_routes"][0]["route"] == "spx-implement"
    assert blocker["owner"] == "agent"
    assert blocker["human_action_required"] is False
    assert "route-repair" in blocker["exact_next_action"]


def test_human_action_finding_remains_human_owned(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    _rejected_state(feature / "human-acceptance.json", route="human-action")

    validation = validate_human_acceptance(
        project,
        feature,
        require_accepted=True,
    )
    blocker = acceptance_closeout_blockers(
        feature,
        acceptance=validation,
    )[0]

    assert blocker["owner"] == "user"
    assert blocker["human_action_required"] is True
    assert blocker["human_action_guide"]["steps"]


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
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
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
    returned = _complete_then_transition(
        feature,
        target_stage="accept",
        revision=routed["data"]["revision"],
    )
    assert returned["data"]["stage"] == "accept"
    assert show_workflow(feature)["data"]["status"] == "active"


@pytest.mark.parametrize("route", ["sp-review", "spx-review"])
def test_product_defect_acceptance_repair_returns_to_review_by_default(
    tmp_path: Path,
    route: str,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "review", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _rejected_state(state_path, route=route)

    routed = route_human_acceptance_repair(
        project,
        feature,
        route=route,
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )

    assert routed["data"]["stage"] == "review"
    assert routed["data"]["repair_route"] == route
    assert routed["data"]["owning_stage_command"] == route
    assert routed["data"]["acceptance_return_argv"][:3] == [
        "specify",
        "accept",
        "prepare",
    ]
    assert json.loads(state_path.read_text(encoding="utf-8"))["status"] == "draft"


def test_acceptance_route_repair_cannot_supersede_a_human_blocker(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(
        project,
        feature,
        route="spx-debug",
    )
    state_path = feature / "human-acceptance.json"
    state_path.write_bytes(state_path.read_bytes().replace(b"\n", b"\r\n"))
    acceptance_before = state_path.read_bytes()
    blocked = block_workflow(
        feature,
        expected_revision=revision,
        category="human-review",
        owner="user",
        cause="Device approval is still required.",
        evidence=["device D-7 displays approval pending"],
        attempted_recovery=[],
        affected_scope=["acceptance scenario HA-001"],
        exact_next_action="Approve device D-7 on its local screen.",
        unblock_criteria="Device D-7 displays approval granted.",
    )
    original = blocked["blockers"][0]

    with pytest.raises(WorkflowRuntimeError) as captured:
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-debug",
            finding_id="HAF-001",
            expected_revision=blocked["data"]["revision"],
            evidence=["The acceptance failure remains reproducible."],
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "blocked-reopen-requires-resolution"
    assert error["blockers"][0]["human_action_guide"] == original[
        "human_action_guide"
    ]
    assert state_path.read_bytes() == acceptance_before
    shown = show_workflow(feature)
    assert shown["data"]["status"] == "blocked"
    assert shown["blockers"][0]["owner"] == "user"


def test_acceptance_repair_rejects_a_route_that_does_not_match_the_finding(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _rejected_state(state_path)
    workflow_before = workflow_runtime_path(feature).read_bytes()
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

    assert workflow_runtime_path(feature).read_bytes() == workflow_before
    assert state_path.read_bytes() == acceptance_before


def test_accept_route_repair_cli_returns_the_deterministic_resume_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
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
    assert payload["data"]["acceptance_return_argv"][:3] == [
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
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _rejected_state(state_path)
    workflow_before = workflow_runtime_path(feature).read_bytes()
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

    assert workflow_runtime_path(feature).read_bytes() == workflow_before
    assert state_path.read_bytes() == acceptance_before


@pytest.mark.parametrize(
    ("route", "target_stage", "owning_command"),
    (
        ("sp-implement", "implement", "sp-implement"),
        ("sp-debug", "implement", "sp-implement"),
        ("sp-clarify", "specify", "sp-specify"),
        ("sp-specify", "specify", "sp-specify"),
        ("spx-implement", "implement", "spx-implement"),
        ("spx-debug", "implement", "spx-implement"),
        ("spx-clarify", "specify", "spx-specify"),
        ("spx-specify", "specify", "spx-specify"),
    ),
)
def test_every_acceptance_repair_route_returns_through_its_owning_stage(
    tmp_path: Path,
    route: str,
    target_stage: str,
    owning_command: str,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(
        project,
        feature,
        route=route,
    )

    routed = route_human_acceptance_repair(
        project,
        feature,
        route=route,
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )

    assert routed["data"]["stage"] == target_stage
    assert routed["data"]["repair_handoff_command"] == route
    assert routed["data"]["owning_stage_command"] == owning_command
    assert routed["data"]["acceptance_return_argv"][:3] == [
        "specify",
        "accept",
        "prepare",
    ]
    current_revision = routed["data"]["revision"]
    remaining = (
        ("accept",)
        if target_stage == "implement"
        else ("plan", "tasks", "implement", "accept")
    )
    for target in remaining:
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=current_revision,
        )
        current_revision = transitioned["data"]["revision"]
    assert show_workflow(feature)["data"]["stage"] == "accept"
    assert show_workflow(feature)["data"]["status"] == "active"

    (feature / "implementation-summary.md").write_text(
        f"# Implementation Summary\n\nRepair through {route} completed.\n",
        encoding="utf-8",
    )
    prepared = prepare_human_acceptance(project, feature)
    assert prepared["status"] == "draft"
    assert not (feature / ".human-acceptance-repair.json").exists()
    assert not (feature / ".human-acceptance-repair-backup.json").exists()


def test_acceptance_repair_recovers_a_crash_after_acceptance_invalidation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    real_reopen = workflow_runtime_module.reopen_acceptance_workflow

    def crash_before_workflow(*_args, **_kwargs):
        raise SystemExit("simulated crash after acceptance invalidation")

    monkeypatch.setattr(
        workflow_runtime_module,
        "reopen_acceptance_workflow",
        crash_before_workflow,
    )
    with pytest.raises(SystemExit, match="acceptance invalidation"):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-implement",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )
    assert (feature / ".human-acceptance-repair.json").is_file()
    assert (feature / ".human-acceptance-repair-backup.json").is_file()
    assert show_workflow(feature)["data"]["stage"] == "accept"

    monkeypatch.setattr(
        workflow_runtime_module,
        "reopen_acceptance_workflow",
        real_reopen,
    )
    recovered = route_human_acceptance_repair(
        project,
        feature,
        route="spx-implement",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert recovered["data"]["stage"] == "implement"
    assert recovered["data"]["acceptance_return_argv"][:3] == [
        "specify",
        "accept",
        "prepare",
    ]
    assert not (feature / ".human-acceptance-repair.json").exists()
    assert not (feature / ".human-acceptance-repair-backup.json").exists()


def test_acceptance_repair_recovers_equivalent_payload_after_workflow_reopen_crash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(
        project,
        feature,
        route="spx-debug",
    )
    real_write_journal = human_acceptance_module._write_acceptance_repair_journal

    def crash_after_workflow(path: Path, payload: dict[str, object]) -> None:
        if payload.get("phase") == "workflow-reopened":
            raise SystemExit("simulated crash after workflow reopen")
        real_write_journal(path, payload)

    monkeypatch.setattr(
        human_acceptance_module,
        "_write_acceptance_repair_journal",
        crash_after_workflow,
    )
    with pytest.raises(SystemExit, match="workflow reopen"):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-debug",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )
    assert show_workflow(feature)["data"]["stage"] == "implement"

    monkeypatch.setattr(
        human_acceptance_module,
        "_write_acceptance_repair_journal",
        real_write_journal,
    )
    recovered = route_human_acceptance_repair(
        project,
        feature,
        route="spx-debug",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert recovered["summary"].startswith("Recovered completed")
    assert recovered["data"]["repair_handoff_command"] == "spx-debug"
    assert recovered["data"]["owning_stage_command"] == "spx-implement"
    assert recovered["data"]["acceptance_return_argv"][:3] == [
        "specify",
        "accept",
        "prepare",
    ]
    assert not (feature / ".human-acceptance-repair.json").exists()


def test_acceptance_repair_recovers_when_runtime_commits_then_return_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(
        project,
        feature,
        route="spx-debug",
    )
    real_reopen = workflow_runtime_module.reopen_acceptance_workflow

    def commit_then_raise(*args, **kwargs):
        real_reopen(*args, **kwargs)
        raise OSError("simulated response failure after runtime commit")

    monkeypatch.setattr(
        workflow_runtime_module,
        "reopen_acceptance_workflow",
        commit_then_raise,
    )
    recovered = route_human_acceptance_repair(
        project,
        feature,
        route="spx-debug",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert recovered["summary"].startswith("Recovered completed")
    shown = show_workflow(feature)["data"]
    assert shown["stage"] == "implement"
    assert shown["status"] == "active"
    assert shown["revision"] == revision + 1
    acceptance = json.loads(
        (feature / "human-acceptance.json").read_text(encoding="utf-8")
    )
    assert acceptance["status"] == "draft"
    assert acceptance["overall"]["next_command"] == "spx-debug"
    assert not (feature / ".human-acceptance-repair.json").exists()
    assert not (feature / ".human-acceptance-repair-backup.json").exists()


def test_corrupt_acceptance_repair_backup_blocks_without_deleting_recovery_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    real_reopen = workflow_runtime_module.reopen_acceptance_workflow
    monkeypatch.setattr(
        workflow_runtime_module,
        "reopen_acceptance_workflow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SystemExit("crash")),
    )
    with pytest.raises(SystemExit):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-implement",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )
    backup = feature / ".human-acceptance-repair-backup.json"
    journal = feature / ".human-acceptance-repair.json"
    backup.write_text('{"status":"truncated"}\n', encoding="utf-8")
    acceptance_before = (feature / "human-acceptance.json").read_bytes()
    workflow_before = workflow_runtime_path(feature).read_bytes()
    journal_before = journal.read_bytes()
    backup_before = backup.read_bytes()
    monkeypatch.setattr(
        workflow_runtime_module,
        "reopen_acceptance_workflow",
        real_reopen,
    )

    with pytest.raises(WorkflowRuntimeError) as captured:
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-implement",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )

    payload = captured.value.to_envelope()
    assert payload["data"]["error_code"] == "acceptance-repair-recovery-required"
    assert payload["blockers"][0]["human_action_required"] is True
    assert len(payload["blockers"][0]["human_action_guide"]["steps"]) == 4
    assert (feature / "human-acceptance.json").read_bytes() == acceptance_before
    assert workflow_runtime_path(feature).read_bytes() == workflow_before
    assert journal.read_bytes() == journal_before
    assert backup.read_bytes() == backup_before


def test_modified_invalidated_acceptance_blocks_committed_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    real_write_journal = human_acceptance_module._write_acceptance_repair_journal

    def crash_after_workflow(path: Path, payload: dict[str, object]) -> None:
        if payload.get("phase") == "workflow-reopened":
            raise SystemExit("crash")
        real_write_journal(path, payload)

    monkeypatch.setattr(
        human_acceptance_module,
        "_write_acceptance_repair_journal",
        crash_after_workflow,
    )
    with pytest.raises(SystemExit):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-implement",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )
    state_path = feature / "human-acceptance.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["overall"]["summary"] = "External modification after crash."
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    acceptance_before = state_path.read_bytes()
    journal = feature / ".human-acceptance-repair.json"
    backup = feature / ".human-acceptance-repair-backup.json"
    monkeypatch.setattr(
        human_acceptance_module,
        "_write_acceptance_repair_journal",
        real_write_journal,
    )

    with pytest.raises(WorkflowRuntimeError):
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-implement",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )

    assert state_path.read_bytes() == acceptance_before
    assert journal.exists()
    assert backup.exists()


def test_interrupted_backup_cleanup_does_not_turn_success_into_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    backup_name = ".human-acceptance-repair-backup.json"
    real_unlink = Path.unlink
    backup_unlinks = 0

    def interrupt_second_backup_unlink(path: Path, *args, **kwargs):
        nonlocal backup_unlinks
        if path.name == backup_name:
            backup_unlinks += 1
            if backup_unlinks == 2:
                raise OSError("simulated cleanup interruption")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", interrupt_second_backup_unlink)

    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-implement",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert routed["status"] == "ok"
    assert not (feature / ".human-acceptance-repair.json").exists()
    assert (feature / backup_name).exists()


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
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
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
    assert payload["status"] == "ok"
    assert payload["data"]["human_acceptance"]["accepted"] is True
    assert payload["data"]["hook_result"]["status"] == "ok"
    assert payload["next_argv"][:3] == ["specify", "workflow", "closeout"]
    assert payload["next_argv"][
        payload["next_argv"].index("--expected-revision") + 1
    ] == str(revision)


def test_workflow_closeout_revalidates_acceptance_after_the_artifact_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=revision,
        )
        revision = transitioned["data"]["revision"]
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    _accepted_state(state_path)

    def mutate_after_initial_validation(**_kwargs) -> None:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["status"] = "draft"
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return None

    monkeypatch.setattr(
        specify_cli_module,
        "_workflow_artifact_gate",
        mutate_after_initial_validation,
    )
    monkeypatch.chdir(project)

    result = CliRunner().invoke(
        app,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 10
    payload = json.loads(result.output)
    assert payload["data"]["error_code"] == "human-acceptance-required"
    assert payload["blockers"][0]["owner"] == "agent"
    assert show_workflow(feature)["data"]["status"] == "active"


def test_terminal_closeout_snapshots_acceptance_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _accepted_acceptance_at_active_accept(project, feature)
    acceptance_path = feature / "human-acceptance.json"
    accepted_bytes = acceptance_path.read_bytes()
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
    monkeypatch.setattr(
        specify_cli_module,
        "_workflow_artifact_gate",
        lambda **_kwargs: None,
    )
    monkeypatch.chdir(project)

    closed = CliRunner().invoke(
        app,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert closed.exit_code == 0, closed.output
    closed_payload = json.loads(closed.output)
    snapshot_path = terminal_acceptance_snapshot_path(feature)
    assert snapshot_path.read_bytes() == accepted_bytes
    assert closed_payload["data"]["acceptance_snapshot_path"] == str(snapshot_path)
    assert show_workflow(feature)["data"]["status"] == "completed"

    repeated = CliRunner().invoke(
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

    assert repeated.exit_code == 0, repeated.output
    repeated_payload = json.loads(repeated.output)
    assert repeated_payload["status"] == "ok"
    assert repeated_payload["data"]["already_completed"] is True
    assert repeated_payload["blockers"] == []

    acceptance_before_prepare = acceptance_path.read_bytes()
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nChanged after terminal closeout.\n",
        encoding="utf-8",
    )
    prepared = CliRunner().invoke(
        app,
        [
            "accept",
            "prepare",
            "--feature-dir",
            str(feature),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert prepared.exit_code == 10
    prepared_payload = json.loads(prepared.output)
    assert prepared_payload["error_code"] == "terminal-feature-immutable"
    assert prepared_payload["blockers"][0]["owner"] == "agent"
    assert acceptance_path.read_bytes() == acceptance_before_prepare
    assert show_workflow(feature)["data"]["status"] == "completed"


def test_terminal_show_fails_closed_when_current_acceptance_drifts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _accepted_acceptance_at_active_accept(project, feature)
    monkeypatch.setattr(
        specify_cli_module,
        "_workflow_artifact_gate",
        lambda **_kwargs: None,
    )
    monkeypatch.chdir(project)
    closed = CliRunner().invoke(
        app,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )
    assert closed.exit_code == 0, closed.output

    state_path = feature / "human-acceptance.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "draft"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    closeout = CliRunner().invoke(
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
    assert closeout.exit_code == 10
    closeout_payload = json.loads(closeout.output)
    assert (
        closeout_payload["data"]["error_code"]
        == "terminal-acceptance-evidence-drift"
    )
    assert closeout_payload["blockers"][0]["owner"] == "maintainer"
    assert closeout_payload["blockers"][0]["human_action_guide"]["steps"]

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature)

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "terminal-acceptance-evidence-drift"
    assert "current human acceptance digest" in json.dumps(error)
    assert error["blockers"][0]["owner"] == "maintainer"
    assert error["blockers"][0]["human_action_guide"]["steps"]
    prepared = prepare_human_acceptance(project, feature)
    recovery = acceptance_closeout_blockers(feature, acceptance=prepared)[0]
    assert recovery["code"] == "terminal-acceptance-evidence-drift"
    assert "restore human-acceptance.json" in recovery["exact_next_action"]
    assert terminal_acceptance_snapshot_path(feature).read_bytes() != state_path.read_bytes()


def test_accept_closeout_preserves_the_authoritative_runtime_human_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _accepted_acceptance_at_active_accept(project, feature)
    blocked = block_workflow(
        feature,
        expected_revision=revision,
        category="human-review",
        owner="user",
        cause="Device D-7 requires approval on its physical screen.",
        evidence=["device D-7 reports approval pending"],
        attempted_recovery=[],
        affected_scope=["acceptance scenario HA-DEVICE"],
        exact_next_action="Approve device D-7 on its physical screen.",
        unblock_criteria="Device D-7 reports approval granted.",
    )
    original = blocked["blockers"][0]
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

    assert result.exit_code == 10
    payload = json.loads(result.output)
    returned = payload["blockers"][0]
    assert returned["blocker_id"] == original["blocker_id"]
    assert returned["owner"] == "user"
    assert returned["details"] == original["details"]
    assert returned["exact_next_action"] == original["exact_next_action"]
    assert returned["unblock_criteria"] == original["unblock_criteria"]
    assert returned["human_action_guide"] == original["human_action_guide"]
    assert payload["data"]["resolution_action"] == blocked["data"][
        "resolution_action"
    ]


def test_closeout_detects_acceptance_change_between_snapshot_and_runtime_cas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _accepted_acceptance_at_active_accept(project, feature)
    state_path = feature / "human-acceptance.json"
    real_closeout = specify_cli_module.closeout_workflow

    def mutate_then_closeout(*args, **kwargs):
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["status"] = "draft"
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return real_closeout(*args, **kwargs)

    monkeypatch.setattr(
        specify_cli_module,
        "_workflow_artifact_gate",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        specify_cli_module,
        "closeout_workflow",
        mutate_then_closeout,
    )
    monkeypatch.chdir(project)

    result = CliRunner().invoke(
        app,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 10
    payload = json.loads(result.output)
    assert payload["data"]["error_code"] == "acceptance-snapshot-conflict"
    assert show_workflow(feature)["data"]["status"] == "active"
