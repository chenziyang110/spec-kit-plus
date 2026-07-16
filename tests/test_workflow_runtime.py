from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from specify_cli.hooks.checkpoint_serializers import serialize_workflow_state
from specify_cli.hooks.state_validation import validate_state_hook
from specify_cli.workflow_runtime import (
    InvalidTransition,
    RevisionConflict,
    block_workflow,
    closeout_workflow,
    enter_workflow,
    next_workflow,
    show_workflow,
    transition_workflow,
    workflow_state_path,
)


def _feature(tmp_path: Path) -> Path:
    feature_dir = tmp_path / ".specify" / "features" / "001-agent-api"
    feature_dir.mkdir(parents=True)
    return feature_dir


def test_enter_creates_parseable_state_atomically_with_revision_guard(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)

    payload = enter_workflow(
        feature_dir,
        stage="specify",
        expected_revision=0,
        summary="Turn a user goal into the canonical specification.",
    )

    state_path = workflow_state_path(feature_dir)
    checkpoint = serialize_workflow_state(state_path)
    assert payload["status"] == "ok"
    assert payload["data"]["revision"] == 1
    assert payload["data"]["stage"] == "specify"
    assert checkpoint["active_command"] == "sp-specify"
    assert checkpoint["phase_mode"] == "planning-only"
    assert checkpoint["current_stage"] == "specify"
    assert checkpoint["allowed_artifact_writes"]
    assert checkpoint["forbidden_actions"]
    assert checkpoint["authoritative_files"]
    assert list(state_path.parent.glob("workflow-state.md.*.tmp")) == []


def test_discussion_is_optional_but_every_required_stage_is_sequential(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="discussion", expected_revision=0)

    revision = entered["data"]["revision"]
    for target in ("specify", "plan", "tasks", "implement", "accept"):
        result = transition_workflow(
            feature_dir,
            target_stage=target,
            expected_revision=revision,
        )
        revision = result["data"]["revision"]
        assert result["data"]["stage"] == target

    assert revision == 6


def test_generated_planning_stages_pass_the_existing_state_validator(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-agent-api"
    feature_dir.mkdir(parents=True)

    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for stage in ("specify", "plan", "tasks"):
        if stage != "specify":
            transitioned = transition_workflow(
                feature_dir,
                target_stage=stage,
                expected_revision=revision,
            )
            revision = transitioned["data"]["revision"]
        result = validate_state_hook(
            project_root,
            {"command_name": stage, "feature_dir": str(feature_dir)},
        )
        assert result.status == "ok", result.errors


def test_enter_cannot_start_after_specify(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)

    with pytest.raises(InvalidTransition, match="may only enter") as captured:
        enter_workflow(feature_dir, stage="plan", expected_revision=0)

    error = captured.value.to_envelope()
    assert error["status"] == "blocked"
    assert error["blockers"][0]["stage"] == "plan"
    assert not workflow_state_path(feature_dir).exists()


def test_transition_refuses_skips_and_preserves_file(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    before = workflow_state_path(feature_dir).read_bytes()

    with pytest.raises(InvalidTransition, match="expected plan") as captured:
        transition_workflow(
            feature_dir,
            target_stage="tasks",
            expected_revision=1,
        )

    blocker = captured.value.to_envelope()["blockers"][0]
    assert blocker["code"] == "invalid-transition"
    assert blocker["exact_next_action"] == "Complete specify, then transition to plan."
    assert blocker["resume"]["argv"][-2:] == ["--format", "json"]
    assert workflow_state_path(feature_dir).read_bytes() == before


def test_revision_conflict_is_blocked_and_never_overwrites_newer_state(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    transition_workflow(feature_dir, target_stage="plan", expected_revision=1)
    before = workflow_state_path(feature_dir).read_bytes()

    with pytest.raises(
        RevisionConflict, match="expected revision 1, found 2"
    ) as captured:
        transition_workflow(
            feature_dir,
            target_stage="tasks",
            expected_revision=1,
        )

    payload = captured.value.to_envelope()
    assert payload["status"] == "blocked"
    assert payload["data"]["actual_revision"] == 2
    assert payload["blockers"][0]["category"] == "conflict-or-drift"
    assert workflow_state_path(feature_dir).read_bytes() == before


def test_concurrent_transitions_with_the_same_revision_commit_exactly_once(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    def transition() -> str:
        try:
            transition_workflow(
                feature_dir,
                target_stage="plan",
                expected_revision=1,
            )
        except RevisionConflict:
            return "conflict"
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(lambda _index: transition(), range(2)))

    assert outcomes == ["committed", "conflict"]
    shown = show_workflow(feature_dir)
    assert shown["data"]["stage"] == "plan"
    assert shown["data"]["revision"] == 2


def test_show_and_next_are_read_only_progressive_disclosure(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    before = workflow_state_path(feature_dir).read_bytes()

    shown = show_workflow(feature_dir)
    upcoming = next_workflow(feature_dir)

    assert shown["data"]["stage"] == "specify"
    assert shown["next_argv"] == [
        "specify",
        "workflow",
        "next",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]
    assert upcoming["data"]["next_stage"] == "plan"
    assert upcoming["next_argv"][:3] == ["specify", "workflow", "transition"]
    assert "--to" in upcoming["next_argv"]
    assert "--target-stage" not in upcoming["next_argv"]
    assert "--expected-revision" in upcoming["next_argv"]
    assert workflow_state_path(feature_dir).read_bytes() == before


def test_human_blocker_contains_a_novice_tutorial_and_exact_resume_argv(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    payload = block_workflow(
        feature_dir,
        expected_revision=1,
        category="credentials-or-permission",
        owner="maintainer",
        cause="The protected repository setting cannot be changed by the agent.",
        evidence=["Sanitized API response: HTTP 403 for repository setting"],
        attempted_recovery=[
            {"action": "Checked current token scope", "result": "Write scope is absent"}
        ],
        affected_scope=["specify gate"],
        exact_next_action="Enable the required repository setting.",
        unblock_criteria="A read-only probe reports the setting as enabled.",
        resume_argv=[
            "specify",
            "workflow",
            "transition",
            "--feature-dir",
            str(feature_dir),
            "--target-stage",
            "plan",
            "--expected-revision",
            "2",
            "--format",
            "json",
        ],
    )

    blocker = payload["blockers"][0]
    guide = blocker["human_action_guide"]
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "workflow-blocker-schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(blocker)
    assert payload["status"] == "blocked"
    assert payload["data"]["revision"] == 2
    assert blocker["owner"] == "maintainer"
    assert guide["why_human"]
    assert guide["prerequisites"]
    assert guide["safety_notes"]
    assert len(guide["steps"]) >= 3
    assert all(
        {"order", "action", "expected_result", "if_failed"} <= step.keys()
        for step in guide["steps"]
    )
    assert guide["verification"]
    assert guide["evidence_to_return"]
    assert blocker["resume"]["argv"] == payload["next_argv"]
    json.dumps(payload)


def test_partial_human_action_override_keeps_the_novice_tutorial(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    payload = block_workflow(
        feature_dir,
        expected_revision=1,
        category="human-decision",
        owner="user",
        cause="A product decision is required.",
        evidence=["Decision D-4 has two valid alternatives"],
        attempted_recovery=[],
        affected_scope=["specification acceptance"],
        exact_next_action="Select alternative A or B.",
        unblock_criteria="One alternative is selected with a reason.",
        resume_argv=["specify", "workflow", "transition"],
        human_action={"goal": "Choose A or B in the decision record."},
    )

    guide = payload["blockers"][0]["human_action_guide"]
    assert guide["goal"] == "Choose A or B in the decision record."
    assert guide["why_human"]
    assert len(guide["steps"]) >= 3
    assert guide["verification"]


def test_human_owned_blocker_cannot_suppress_the_required_tutorial(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    with pytest.raises(ValueError, match="cannot be false"):
        block_workflow(
            feature_dir,
            expected_revision=1,
            category="human-decision",
            owner="user",
            cause="A human product decision is required.",
            evidence=["Decision D-4 remains open"],
            attempted_recovery=[],
            affected_scope=["specification acceptance"],
            exact_next_action="Choose alternative A or B.",
            unblock_criteria="One alternative is selected with a reason.",
            resume_argv=["specify", "workflow", "transition"],
            human_action_required=False,
        )


def test_human_action_override_rejects_unknown_or_malformed_fields(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    with pytest.raises(ValueError, match="unknown field"):
        block_workflow(
            feature_dir,
            expected_revision=1,
            category="human-decision",
            owner="user",
            cause="A human product decision is required.",
            evidence=["Decision D-4 remains open"],
            attempted_recovery=[],
            affected_scope=["specification acceptance"],
            exact_next_action="Choose alternative A or B.",
            unblock_criteria="One alternative is selected with a reason.",
            resume_argv=["specify", "workflow", "transition"],
            human_action={"unexpected": "silently suppress the canonical guide"},
        )


def test_external_system_blocker_does_not_default_to_human_action(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    payload = block_workflow(
        feature_dir,
        expected_revision=1,
        category="external-system",
        owner="external-system",
        cause="The provider status page reports an active outage.",
        evidence=["Sanitized status incident INC-42 is unresolved"],
        attempted_recovery=[],
        affected_scope=["remote verification"],
        exact_next_action="Wait for incident INC-42 to resolve, then rerun the probe.",
        unblock_criteria="The read-only probe reaches the provider successfully.",
        resume_argv=["specify", "workflow", "show"],
    )

    blocker = payload["blockers"][0]
    assert blocker["owner"] == "external-system"
    assert blocker["human_action_required"] is False
    assert blocker["human_action_guide"] is None


def test_blocked_transition_requires_resolution_evidence(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    block_workflow(
        feature_dir,
        expected_revision=1,
        category="external-system",
        owner="maintainer",
        cause="Protected validation is pending.",
        evidence=["pipeline 42 is pending"],
        attempted_recovery=[],
        affected_scope=["specification handoff"],
        exact_next_action="Approve pipeline 42.",
        unblock_criteria="pipeline 42 passes",
        resume_argv=["specify", "workflow", "transition"],
    )

    with pytest.raises(InvalidTransition, match="resolution_evidence"):
        transition_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=2,
        )

    resumed = transition_workflow(
        feature_dir,
        target_stage="plan",
        expected_revision=2,
        resolution_evidence=["pipeline 42 passed for commit abc123"],
    )
    assert resumed["status"] == "ok"
    assert resumed["data"]["revision"] == 3
    assert resumed["data"]["resolution_evidence"] == [
        "pipeline 42 passed for commit abc123"
    ]


def test_closeout_is_only_legal_from_active_accept(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)

    with pytest.raises(InvalidTransition, match="only close out from accept"):
        closeout_workflow(
            feature_dir,
            expected_revision=entered["data"]["revision"],
        )

    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        result = transition_workflow(
            feature_dir,
            target_stage=target,
            expected_revision=revision,
        )
        revision = result["data"]["revision"]

    closed = closeout_workflow(
        feature_dir,
        expected_revision=revision,
        summary="Human acceptance completed.",
    )
    assert closed["status"] == "ok"
    assert closed["data"]["status"] == "completed"
    assert closed["data"]["revision"] == revision + 1
    assert closed["next_argv"] == []
    assert next_workflow(feature_dir)["data"]["next_stage"] is None
