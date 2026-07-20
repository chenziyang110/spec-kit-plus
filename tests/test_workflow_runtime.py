from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from threading import Event

import pytest
from jsonschema import Draft202012Validator

from specify_cli import workflow_runtime as workflow_runtime_module

from specify_cli.workflow_runtime import (
    InvalidTransition,
    RevisionConflict,
    WorkflowRuntimeError,
    block_workflow,
    closeout_workflow,
    complete_workflow_stage,
    enter_workflow,
    next_workflow,
    reopen_workflow,
    resolve_workflow_blocker,
    show_workflow,
    terminal_acceptance_snapshot_path,
    transition_workflow,
    workflow_runtime_path,
    workflow_state_path,
)


def _feature(tmp_path: Path) -> Path:
    feature_dir = tmp_path / ".specify" / "features" / "001-agent-api"
    feature_dir.mkdir(parents=True)
    return feature_dir


def _complete_then_transition(
    feature_dir: Path,
    *,
    target_stage: str,
    revision: int,
) -> dict[str, object]:
    completed = complete_workflow_stage(
        feature_dir,
        expected_revision=revision,
    )
    return transition_workflow(
        feature_dir,
        target_stage=target_stage,
        expected_revision=completed["data"]["revision"],
    )


def _acceptance_snapshot(feature_dir: Path) -> str:
    acceptance_path = feature_dir / "human-acceptance.json"
    acceptance_path.write_text('{"status":"accepted"}\n', encoding="utf-8")
    acceptance_bytes = acceptance_path.read_bytes()
    terminal_acceptance_snapshot_path(feature_dir).write_bytes(acceptance_bytes)
    return hashlib.sha256(acceptance_bytes).hexdigest()


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

    state_path = workflow_runtime_path(feature_dir)
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["data"]["revision"] == 1
    assert payload["data"]["stage"] == "specify"
    assert persisted["workflow_runtime_version"] == 1
    assert persisted["revision"] == 1
    assert persisted["stage"] == "specify"
    assert persisted["status"] == "active"
    assert not workflow_state_path(feature_dir).exists()
    assert list(state_path.parent.glob("workflow-runtime.json.*.tmp")) == []


def test_runtime_transitions_never_overwrite_rich_workflow_state(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    rich_state = workflow_state_path(feature_dir)
    rich_state.write_text(
        "# Rich workflow state\n\n## Learning Triggers\n\n"
        "- tooling_trap: preserve this reusable signal\n\n"
        "## Analyze Gate\n\n- gate_status: blocked\n",
        encoding="utf-8",
    )
    before = rich_state.read_bytes()

    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    completed = complete_workflow_stage(feature_dir, expected_revision=1)
    transition_workflow(
        feature_dir,
        target_stage="plan",
        expected_revision=completed["data"]["revision"],
    )

    assert rich_state.read_bytes() == before
    assert show_workflow(feature_dir)["data"]["stage"] == "plan"


def test_runtime_rejects_legacy_or_corrupt_phase_state_with_typed_recovery(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    runtime_path = workflow_runtime_path(feature_dir)
    runtime_path.write_text(
        json.dumps({"revision": 1, "stage": "sp-clarify", "status": "active"}),
        encoding="utf-8",
    )

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    payload = captured.value.to_envelope()
    assert payload["status"] == "blocked"
    assert payload["data"]["error_code"] == "invalid-workflow-runtime"
    blocker = payload["blockers"][0]
    assert blocker["owner"] == "maintainer"
    assert blocker["category"] == "artifact-or-state"
    assert blocker["human_action_required"] is True
    assert blocker["human_action_guide"]["steps"]
    assert blocker["resume"]["argv"][:3] == ["specify", "workflow", "show"]


def test_discussion_is_optional_but_every_required_stage_is_sequential(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="discussion", expected_revision=0)

    revision = entered["data"]["revision"]
    for target in ("specify", "plan", "tasks", "implement", "review", "accept"):
        result = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = result["data"]["revision"]
        assert result["data"]["stage"] == target

    assert revision == 13


def test_completed_nonterminal_stage_still_hands_off_to_its_required_next_stage(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement"):
        result = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = result["data"]["revision"]

    completed = complete_workflow_stage(
        feature_dir,
        expected_revision=revision,
        summary="Technical implementation closeout completed.",
    )
    revision = completed["data"]["revision"]
    assert completed["data"]["status"] == "completed"

    upcoming = next_workflow(feature_dir)
    assert upcoming["data"]["stage"] == "implement"
    assert upcoming["data"]["status"] == "completed"
    assert upcoming["data"]["next_stage"] == "review"
    assert upcoming["next_argv"][upcoming["next_argv"].index("--to") + 1] == "review"

    reviewed = transition_workflow(
        feature_dir,
        target_stage="review",
        expected_revision=revision,
    )
    assert reviewed["data"]["stage"] == "review"
    assert reviewed["data"]["status"] == "active"


def test_completed_implement_cannot_skip_mandatory_review(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    completed = complete_workflow_stage(feature_dir, expected_revision=revision)

    with pytest.raises(InvalidTransition, match="expected review") as captured:
        transition_workflow(
            feature_dir,
            target_stage="accept",
            expected_revision=completed["data"]["revision"],
        )

    blocker = captured.value.to_envelope()["blockers"][0]
    assert blocker["code"] == "invalid-transition"
    assert blocker["exact_next_action"] == (
        "Complete implement, then transition to review."
    )
    assert show_workflow(feature_dir)["data"]["stage"] == "implement"
    assert show_workflow(feature_dir)["data"]["status"] == "completed"


def test_generated_planning_stages_do_not_claim_the_rich_state_validator(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-agent-api"
    feature_dir.mkdir(parents=True)

    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for stage in ("specify", "plan", "tasks"):
        if stage != "specify":
            transitioned = _complete_then_transition(
                feature_dir,
                target_stage=stage,
                revision=revision,
            )
            revision = transitioned["data"]["revision"]
        assert show_workflow(feature_dir)["data"]["stage"] == stage
        assert not workflow_state_path(feature_dir).exists()


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
    before = workflow_runtime_path(feature_dir).read_bytes()

    with pytest.raises(InvalidTransition, match="expected plan") as captured:
        transition_workflow(
            feature_dir,
            target_stage="tasks",
            expected_revision=1,
        )

    blocker = captured.value.to_envelope()["blockers"][0]
    assert blocker["code"] == "invalid-transition"
    assert blocker["exact_next_action"] == "Complete specify, then transition to plan."
    assert blocker["resume"]["argv"][:3] == [
        "specify",
        "workflow",
        "complete-stage",
    ]
    assert blocker["resume"]["argv"][-2:] == ["--format", "json"]
    assert workflow_runtime_path(feature_dir).read_bytes() == before


def test_transition_requires_runtime_owned_source_completion(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    with pytest.raises(InvalidTransition, match="complete the source stage") as captured:
        transition_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=1,
        )

    payload = captured.value.to_envelope()
    assert payload["data"]["error_code"] == "source-stage-not-completed"
    assert payload["next_argv"][:3] == ["specify", "workflow", "complete-stage"]
    assert show_workflow(feature_dir)["data"]["status"] == "active"


def test_revision_conflict_is_blocked_and_never_overwrites_newer_state(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    advanced = _complete_then_transition(
        feature_dir,
        target_stage="plan",
        revision=1,
    )
    before = workflow_runtime_path(feature_dir).read_bytes()

    with pytest.raises(
        RevisionConflict, match=f"expected revision 1, found {advanced['data']['revision']}"
    ) as captured:
        transition_workflow(
            feature_dir,
            target_stage="tasks",
            expected_revision=1,
        )

    payload = captured.value.to_envelope()
    assert payload["status"] == "blocked"
    assert payload["data"]["actual_revision"] == advanced["data"]["revision"]
    assert payload["blockers"][0]["category"] == "conflict-or-drift"
    assert any(
        "workflow-runtime.json" in item
        for item in payload["blockers"][0]["evidence"]
    )
    assert "workflow-runtime.json" in payload["blockers"][0]["affected_scope"]
    assert all(
        "workflow-state.md" not in item
        for item in payload["blockers"][0]["evidence"]
    )
    assert workflow_runtime_path(feature_dir).read_bytes() == before


def test_concurrent_transitions_with_the_same_revision_commit_exactly_once(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    completed = complete_workflow_stage(feature_dir, expected_revision=1)
    revision = completed["data"]["revision"]

    def transition() -> str:
        try:
            transition_workflow(
                feature_dir,
                target_stage="plan",
                expected_revision=revision,
            )
        except RevisionConflict:
            return "conflict"
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(lambda _index: transition(), range(2)))

    assert outcomes == ["committed", "conflict"]
    shown = show_workflow(feature_dir)
    assert shown["data"]["stage"] == "plan"
    assert shown["data"]["revision"] == revision + 1


def test_mutation_envelope_uses_its_own_committed_snapshot_under_interleaving(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    write_committed = Event()
    allow_first_caller_to_continue = Event()
    real_write = workflow_runtime_module._atomic_guarded_write
    pause_once = {"value": True}

    def pause_after_commit(*args, **kwargs):
        committed = real_write(*args, **kwargs)
        if pause_once["value"]:
            pause_once["value"] = False
            write_committed.set()
            assert allow_first_caller_to_continue.wait(timeout=5)
        return committed

    monkeypatch.setattr(
        workflow_runtime_module,
        "_atomic_guarded_write",
        pause_after_commit,
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(
            complete_workflow_stage,
            feature_dir,
            expected_revision=1,
        )
        assert write_committed.wait(timeout=5)
        transitioned = transition_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=2,
        )
        allow_first_caller_to_continue.set()
        completed = first.result(timeout=5)

    assert transitioned["data"]["stage"] == "plan"
    assert completed["data"]["stage"] == "specify"
    assert completed["data"]["status"] == "completed"
    assert completed["data"]["revision"] == 2
    assert completed["next_argv"][completed["next_argv"].index("--to") + 1] == "plan"
    assert completed["next_argv"][
        completed["next_argv"].index("--expected-revision") + 1
    ] == "2"


def test_show_and_next_are_read_only_progressive_disclosure(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    before = workflow_runtime_path(feature_dir).read_bytes()

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
    assert upcoming["next_argv"][:3] == ["specify", "workflow", "complete-stage"]
    assert "--to" not in upcoming["next_argv"]
    assert "--target-stage" not in upcoming["next_argv"]
    assert "--expected-revision" in upcoming["next_argv"]
    assert workflow_runtime_path(feature_dir).read_bytes() == before


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
    assert payload["next_argv"] == []
    assert payload["show_argv"][:3] == ["specify", "workflow", "show"]
    assert str(feature_dir) in payload["show_argv"]
    assert "resolution_action" not in blocker
    assert payload["data"]["resolution_action"]["capability_id"] == "workflow.resolve"
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
    )

    blocker = payload["blockers"][0]
    assert blocker["owner"] == "external-system"
    assert blocker["human_action_required"] is False
    assert blocker["human_action_guide"] is None


def test_blocked_transition_requires_guarded_resolution_before_completion(
    tmp_path: Path,
) -> None:
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
    )

    with pytest.raises(InvalidTransition, match="complete the source stage") as captured:
        transition_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=2,
        )
    assert captured.value.to_envelope()["next_argv"] == []
    assert captured.value.to_envelope()["data"]["resolution_action"]

    with pytest.raises(InvalidTransition, match="workflow resolve") as completion:
        complete_workflow_stage(feature_dir, expected_revision=2)
    assert completion.value.to_envelope()["data"]["resolution_action"]

    resolved = resolve_workflow_blocker(
        feature_dir,
        expected_revision=2,
        resolution_evidence=["pipeline 42 passed for commit abc123"],
    )
    completed = complete_workflow_stage(
        feature_dir,
        expected_revision=resolved["data"]["revision"],
    )
    resumed = transition_workflow(
        feature_dir,
        target_stage="plan",
        expected_revision=completed["data"]["revision"],
    )
    assert resumed["status"] == "ok"
    assert resumed["data"]["revision"] == 5
    assert show_workflow(feature_dir)["data"]["status"] == "active"
    assert completed["data"]["status"] == "completed"
    assert show_workflow(feature_dir)["data"]["stage"] == "plan"
    state = json.loads(workflow_runtime_path(feature_dir).read_text(encoding="utf-8"))
    assert "pipeline 42 passed for commit abc123" in state["last_resolution_evidence"]
    assert completed["data"]["next_stage"] == "plan"
    assert completed["next_argv"][completed["next_argv"].index("--to") + 1] == "plan"


def test_blocked_wrong_target_resume_preserves_resolution_evidence(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    block_workflow(
        feature_dir,
        expected_revision=1,
        category="external-system",
        owner="external-system",
        cause="Protected validation is pending.",
        evidence=["pipeline 42 is pending"],
        attempted_recovery=[],
        affected_scope=["specification handoff"],
        exact_next_action="Wait for pipeline 42.",
        unblock_criteria="pipeline 42 passes",
    )
    evidence = "pipeline 42 passed for commit abc123"

    with pytest.raises(InvalidTransition, match="expected plan") as captured:
        transition_workflow(
            feature_dir,
            target_stage="tasks",
            expected_revision=2,
        )

    error = captured.value.to_envelope()
    assert error["next_argv"] == []
    assert error["data"]["resolution_action"]
    resolved = resolve_workflow_blocker(
        feature_dir,
        expected_revision=2,
        resolution_evidence=[evidence],
    )
    completed = complete_workflow_stage(
        feature_dir,
        expected_revision=resolved["data"]["revision"],
    )
    assert completed["data"]["status"] == "completed"
    persisted = json.loads(
        workflow_runtime_path(feature_dir).read_text(encoding="utf-8")
    )
    assert persisted["last_blocker_resolution"]["resolution_evidence"] == [evidence]


def test_resolve_reactivates_blocked_accept_and_preserves_the_full_blocker(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    blocked = block_workflow(
        feature_dir,
        expected_revision=revision,
        category="human-review",
        owner="user",
        cause="A physical device approval is required.",
        evidence=["scenario HA-2 requires device approval"],
        attempted_recovery=[],
        affected_scope=["human acceptance scenario HA-2"],
        exact_next_action="Approve the device on its local screen.",
        unblock_criteria="The device reports approval granted.",
    )
    original = blocked["blockers"][0]

    resolved = resolve_workflow_blocker(
        feature_dir,
        expected_revision=blocked["data"]["revision"],
        resolution_evidence=["Device screen reports approval granted for device D-7."],
    )

    assert resolved["data"]["stage"] == "accept"
    assert resolved["data"]["status"] == "active"
    assert resolved["next_argv"][:3] == ["specify", "workflow", "closeout"]
    persisted = json.loads(
        workflow_runtime_path(feature_dir).read_text(encoding="utf-8")
    )
    audit = persisted["last_blocker_resolution"]
    assert audit["blocker"] == original
    assert audit["stage"] == "accept"
    assert audit["resolution_evidence"] == [
        "Device screen reports approval granted for device D-7."
    ]


def test_second_blocker_cannot_replace_an_unresolved_human_boundary(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    first = block_workflow(
        feature_dir,
        expected_revision=1,
        category="human-decision",
        owner="user",
        cause="The user must approve data retention.",
        evidence=["retention decision R-2 is open"],
        attempted_recovery=[],
        affected_scope=["specification"],
        exact_next_action="Approve or reject retention option R-2.",
        unblock_criteria="R-2 has an explicit human decision.",
    )

    with pytest.raises(InvalidTransition) as captured:
        block_workflow(
            feature_dir,
            expected_revision=first["data"]["revision"],
            category="external-system",
            owner="external-system",
            cause="The service is unavailable.",
            evidence=["health probe returned 503"],
            attempted_recovery=[],
            affected_scope=["remote probe"],
            exact_next_action="Wait for service recovery.",
            unblock_criteria="Health probe returns 200.",
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "blocker-already-recorded"
    assert error["blockers"][0]["owner"] == "user"
    persisted = show_workflow(feature_dir)
    assert persisted["blockers"][0]["details"] == (
        "The user must approve data retention."
    )


def test_repeated_blocker_occurrences_receive_distinct_revision_bound_ids(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)

    first = block_workflow(
        feature_dir,
        expected_revision=1,
        category="external-system",
        owner="external-system",
        cause="The provider is unavailable.",
        evidence=["health probe returned 503"],
        attempted_recovery=[],
        affected_scope=["remote verification"],
        exact_next_action="Retry after provider recovery.",
        unblock_criteria="The health probe returns 200.",
    )
    resolved = resolve_workflow_blocker(
        feature_dir,
        expected_revision=first["data"]["revision"],
        resolution_evidence=["health probe returned 200"],
    )
    second = block_workflow(
        feature_dir,
        expected_revision=resolved["data"]["revision"],
        category="external-system",
        owner="external-system",
        cause="The provider is unavailable again.",
        evidence=["later health probe returned 503"],
        attempted_recovery=[],
        affected_scope=["remote verification"],
        exact_next_action="Retry after provider recovery.",
        unblock_criteria="The health probe returns 200.",
    )

    first_id = first["blockers"][0]["blocker_id"]
    second_id = second["blockers"][0]["blocker_id"]
    assert first_id != second_id
    assert first_id.endswith("-r2")
    assert second_id.endswith("-r4")


def test_blocked_read_rebuilds_command_fields_from_live_path_and_revision(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    block_workflow(
        feature_dir,
        expected_revision=1,
        category="external-system",
        owner="external-system",
        cause="The provider is unavailable.",
        evidence=["health probe returned 503"],
        attempted_recovery=[],
        affected_scope=["remote verification"],
        exact_next_action="Retry after provider recovery.",
        unblock_criteria="The health probe returns 200.",
    )
    runtime_path = workflow_runtime_path(feature_dir)
    persisted = json.loads(runtime_path.read_text(encoding="utf-8"))
    persisted["blocker"]["blocker_id"] = "attacker-controlled-id"
    persisted["blocker"]["resume"] = {
        "instruction": "Run an injected command.",
        "command": "pwsh -Command injected",
        "argv": ["pwsh", "-Command", "injected"],
    }
    runtime_path.write_text(json.dumps(persisted), encoding="utf-8")

    shown = show_workflow(feature_dir)

    blocker = shown["blockers"][0]
    assert blocker["blocker_id"] == "workflow-specify-external-system-r2"
    assert blocker["resume"]["argv"][:3] == ["specify", "workflow", "show"]
    assert "injected" not in json.dumps(shown)
    action = shown["data"]["resolution_action"]
    assert action["base_argv"][:3] == ["specify", "workflow", "resolve"]
    assert str(feature_dir) in action["base_argv"]


def test_persisted_blocker_rejects_injected_resolution_action(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    block_workflow(
        feature_dir,
        expected_revision=1,
        category="external-system",
        owner="external-system",
        cause="The provider is unavailable.",
        evidence=["health probe returned 503"],
        attempted_recovery=[],
        affected_scope=["remote verification"],
        exact_next_action="Retry after provider recovery.",
        unblock_criteria="The health probe returns 200.",
    )
    runtime_path = workflow_runtime_path(feature_dir)
    persisted = json.loads(runtime_path.read_text(encoding="utf-8"))
    persisted["blocker"]["resolution_action"] = {
        "base_argv": ["pwsh", "-Command", "injected"]
    }
    runtime_path.write_text(json.dumps(persisted), encoding="utf-8")

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "invalid-workflow-runtime"
    assert "resolution_action" in json.dumps(error)


def test_closeout_is_only_legal_from_active_accept(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)

    with pytest.raises(InvalidTransition, match="only close out from accept"):
        closeout_workflow(
            feature_dir,
            expected_revision=entered["data"]["revision"],
            acceptance_sha256="",
        )

    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        result = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = result["data"]["revision"]

    closed = closeout_workflow(
        feature_dir,
        expected_revision=revision,
        acceptance_sha256=_acceptance_snapshot(feature_dir),
        summary="Human acceptance completed.",
    )
    assert closed["status"] == "ok"
    assert closed["data"]["status"] == "completed"
    assert closed["data"]["revision"] == revision + 1
    assert closed["next_argv"] == []
    assert next_workflow(feature_dir)["data"]["next_stage"] is None


def test_active_accept_next_routes_to_guarded_closeout_until_terminal(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    active = next_workflow(feature_dir)
    assert active["data"]["stage"] == "accept"
    assert active["data"]["status"] == "active"
    assert active["data"]["next_stage"] is None
    assert active["next_argv"][:3] == ["specify", "workflow", "closeout"]
    assert active["next_argv"][active["next_argv"].index("--expected-revision") + 1] == str(
        revision
    )
    assert "acceptance" in active["summary"].lower()

    closed = closeout_workflow(
        feature_dir,
        expected_revision=revision,
        acceptance_sha256=_acceptance_snapshot(feature_dir),
    )
    assert closed["data"]["status"] == "completed"
    assert next_workflow(feature_dir)["next_argv"] == []


def test_runtime_closeout_requires_a_revision_bound_acceptance_snapshot(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    before = workflow_runtime_path(feature_dir).read_bytes()

    with pytest.raises(ValueError, match="acceptance_sha256"):
        closeout_workflow(
            feature_dir,
            expected_revision=revision,
            acceptance_sha256="",
        )

    assert workflow_runtime_path(feature_dir).read_bytes() == before
    assert show_workflow(feature_dir)["data"]["status"] == "active"


@pytest.mark.parametrize("target_name", ["snapshot", "acceptance"])
@pytest.mark.parametrize("error_type", [PermissionError, FileNotFoundError])
def test_completed_accept_reports_unreadable_or_raced_terminal_evidence(
    monkeypatch,
    tmp_path: Path,
    target_name: str,
    error_type: type[OSError],
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    closed = closeout_workflow(
        feature_dir,
        expected_revision=revision,
        acceptance_sha256=_acceptance_snapshot(feature_dir),
    )
    assert closed["data"]["status"] == "completed"
    target_path = (
        terminal_acceptance_snapshot_path(feature_dir)
        if target_name == "snapshot"
        else feature_dir / "human-acceptance.json"
    )
    original_read_bytes = workflow_runtime_module.read_local_state_bytes

    def fail_selected(path: Path, *, root: Path | None = None) -> bytes:
        if path == target_path:
            raise error_type("simulated acceptance evidence race")
        return original_read_bytes(path, root=root)

    monkeypatch.setattr(
        workflow_runtime_module,
        "read_local_state_bytes",
        fail_selected,
    )

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    error = captured.value.to_envelope()
    blocker = error["blockers"][0]
    assert error["data"]["error_code"] == "terminal-acceptance-evidence-drift"
    assert blocker["owner"] == "maintainer"
    assert blocker["human_action_required"] is True
    assert blocker["human_action_guide"] is not None
    evidence = " ".join(blocker["evidence"]).lower()
    assert target_name in evidence or (
        target_name == "acceptance" and "current human acceptance" in evidence
    )
    assert "unreadable" in evidence or "replaced during read" in evidence


@pytest.mark.parametrize("target_name", ["snapshot", "acceptance"])
def test_closeout_converts_acceptance_read_errors_to_a_typed_blocker(
    monkeypatch,
    tmp_path: Path,
    target_name: str,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    acceptance_sha256 = _acceptance_snapshot(feature_dir)
    before = workflow_runtime_path(feature_dir).read_bytes()
    target_path = (
        terminal_acceptance_snapshot_path(feature_dir)
        if target_name == "snapshot"
        else feature_dir / "human-acceptance.json"
    )
    original_read_bytes = workflow_runtime_module.read_local_state_bytes

    def fail_selected(path: Path, *, root: Path | None = None) -> bytes:
        if path == target_path:
            raise PermissionError("simulated unreadable acceptance evidence")
        return original_read_bytes(path, root=root)

    monkeypatch.setattr(
        workflow_runtime_module,
        "read_local_state_bytes",
        fail_selected,
    )

    with pytest.raises(InvalidTransition) as captured:
        closeout_workflow(
            feature_dir,
            expected_revision=revision,
            acceptance_sha256=acceptance_sha256,
        )

    error = captured.value.to_envelope()
    blocker = error["blockers"][0]
    assert error["data"]["error_code"] == "acceptance-snapshot-conflict"
    assert blocker["owner"] == "maintainer"
    assert blocker["human_action_guide"] is not None
    assert "unreadable" in " ".join(blocker["evidence"]).lower()
    assert workflow_runtime_path(feature_dir).read_bytes() == before


def test_completed_accept_rejects_equal_content_snapshot_symlink(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    closeout_workflow(
        feature_dir,
        expected_revision=revision,
        acceptance_sha256=_acceptance_snapshot(feature_dir),
    )
    snapshot_path = terminal_acceptance_snapshot_path(feature_dir)
    external = tmp_path / "external-terminal-acceptance.json"
    snapshot_path.replace(external)
    try:
        snapshot_path.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "terminal-acceptance-evidence-drift"
    assert "unsafe" in " ".join(error["blockers"][0]["evidence"]).lower()


def test_closeout_rejects_preexisting_terminal_snapshot_symlink(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    acceptance_path = feature_dir / "human-acceptance.json"
    acceptance_bytes = b'{"status":"accepted"}\n'
    acceptance_path.write_bytes(acceptance_bytes)
    external = tmp_path / "external-precloseout-snapshot.json"
    external.write_bytes(acceptance_bytes)
    snapshot_path = terminal_acceptance_snapshot_path(feature_dir)
    try:
        snapshot_path.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(InvalidTransition) as captured:
        closeout_workflow(
            feature_dir,
            expected_revision=revision,
            acceptance_sha256=hashlib.sha256(acceptance_bytes).hexdigest(),
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "acceptance-snapshot-conflict"
    assert "unsafe" in " ".join(error["blockers"][0]["evidence"]).lower()
    assert json.loads(external.read_text(encoding="utf-8"))["status"] == "accepted"


def test_runtime_state_read_rejects_equal_content_symlink(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    runtime_path = workflow_runtime_path(feature_dir)
    external = tmp_path / "external-workflow-runtime.json"
    runtime_path.replace(external)
    try:
        runtime_path.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "invalid-workflow-runtime"
    assert "symlink" in " ".join(error["blockers"][0]["evidence"]).lower()


def test_runtime_rejects_terminal_accept_without_an_acceptance_snapshot(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    runtime_path = workflow_runtime_path(feature_dir)
    persisted = json.loads(runtime_path.read_text(encoding="utf-8"))
    persisted.update(
        {
            "revision": revision + 1,
            "status": "completed",
            "summary": "Forged terminal state.",
            "blocker": None,
            "acceptance_sha256": None,
        }
    )
    runtime_path.write_text(json.dumps(persisted), encoding="utf-8")

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "invalid-workflow-runtime"
    assert "acceptance_sha256" in json.dumps(error)


def test_reopen_invalidated_upstream_stage_then_revalidates_forward_order(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    reopened = reopen_workflow(
        feature_dir,
        target_stage="plan",
        expected_revision=revision,
        reason="Analyze found a plan-level interface contradiction.",
        evidence=["AN-004: plan.md conflicts with spec requirement R-7"],
        invalidated_artifacts=["plan.md", "tasks.md", "implementation evidence"],
    )

    assert reopened["data"]["stage"] == "plan"
    assert reopened["data"]["status"] == "active"
    assert reopened["data"]["revision"] == revision + 1
    assert reopened["data"]["last_reopen"] == {
        "source_stage": "implement",
        "source_status": "active",
        "target_stage": "plan",
        "reason": "Analyze found a plan-level interface contradiction.",
        "evidence": ["AN-004: plan.md conflicts with spec requirement R-7"],
        "invalidated_artifacts": [
            "plan.md",
            "tasks.md",
            "implementation evidence",
        ],
    }
    assert reopened["next_argv"][:3] == ["specify", "workflow", "complete-stage"]

    with pytest.raises(InvalidTransition, match="complete the source stage"):
        transition_workflow(
            feature_dir,
            target_stage="tasks",
            expected_revision=revision + 1,
        )


@pytest.mark.parametrize("target_stage", ["implement", "tasks", "plan"])
def test_review_can_reopen_the_owning_upstream_stage(
    tmp_path: Path,
    target_stage: str,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "review"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    reopened = reopen_workflow(
        feature_dir,
        target_stage=target_stage,
        expected_revision=revision,
        reason="System review found an upstream-owned product gap.",
        evidence=["SR-001: the primary action is unreachable from the real entrypoint"],
        invalidated_artifacts=["review-state.json", "human-acceptance.json"],
    )

    assert reopened["data"]["stage"] == target_stage
    assert reopened["data"]["status"] == "active"
    assert reopened["data"]["last_reopen"]["source_stage"] == "review"
    assert reopened["data"]["last_reopen"]["target_stage"] == target_stage


@pytest.mark.parametrize("stage", ["tasks", "implement"])
def test_reopen_reactivates_the_same_completed_stage(
    tmp_path: Path,
    stage: str,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
        if target == stage:
            break
    completed = complete_workflow_stage(feature_dir, expected_revision=revision)

    reopened = reopen_workflow(
        feature_dir,
        target_stage=stage,
        expected_revision=completed["data"]["revision"],
        reason=f"Fresh evidence invalidated the completed {stage} output.",
        evidence=[f"AN-{stage}-01"],
        invalidated_artifacts=[f"{stage} artifacts", "downstream evidence"],
    )

    assert reopened["data"]["stage"] == stage
    assert reopened["data"]["status"] == "active"
    assert reopened["data"]["last_reopen"]["source_status"] == "completed"
    assert reopened["next_argv"][:3] == ["specify", "workflow", "complete-stage"]


@pytest.mark.parametrize("target_stage", ["implement", "accept", "discussion"])
def test_reopen_rejects_same_forward_or_nonfeature_targets(
    tmp_path: Path,
    target_stage: str,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    with pytest.raises(InvalidTransition) as captured:
        reopen_workflow(
            feature_dir,
            target_stage=target_stage,
            expected_revision=revision,
            reason="Invalidated upstream truth.",
            evidence=["AN-009"],
            invalidated_artifacts=["tasks.md"],
        )

    payload = captured.value.to_envelope()
    assert payload["status"] == "blocked"
    assert payload["data"]["error_code"] == "invalid-reopen-target"
    assert show_workflow(feature_dir)["data"]["stage"] == "implement"


def test_reopen_cannot_discard_a_persisted_human_blocker(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    blocked = block_workflow(
        feature_dir,
        expected_revision=revision,
        category="external-system",
        owner="maintainer",
        cause="Protected CI evidence is pending.",
        evidence=["pipeline 42 has not run"],
        attempted_recovery=[],
        affected_scope=["protected main pipeline"],
        exact_next_action="Run pipeline 42 for the current commit.",
        unblock_criteria="Pipeline 42 succeeds for the current commit.",
    )

    with pytest.raises(InvalidTransition) as captured:
        reopen_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=blocked["data"]["revision"],
            reason="Analyze invalidated the plan.",
            evidence=["AN-011"],
            invalidated_artifacts=["plan.md", "tasks.md"],
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "blocked-reopen-requires-resolution"
    assert error["blockers"][0]["details"] == "Protected CI evidence is pending."
    assert "workflow resolve" in error["data"]["recovery"]
    persisted = show_workflow(feature_dir)
    assert persisted["data"]["stage"] == "implement"
    assert persisted["data"]["status"] == "blocked"
    assert persisted["blockers"][0]["owner"] == "maintainer"


def test_reopen_preserves_a_blocked_accept_human_guide(tmp_path: Path) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    blocked = block_workflow(
        feature_dir,
        expected_revision=revision,
        category="human-review",
        owner="user",
        cause="The physical device is not connected for acceptance.",
        evidence=["acceptance scenario H-2 requires the device"],
        attempted_recovery=[],
        affected_scope=["human acceptance scenario H-2"],
        exact_next_action="Connect the device and confirm it is visible.",
        unblock_criteria="The device appears in the product's device list.",
    )
    original = blocked["blockers"][0]

    with pytest.raises(InvalidTransition) as captured:
        reopen_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=blocked["data"]["revision"],
            reason="An upstream plan concern was reported.",
            evidence=["AN-012"],
            invalidated_artifacts=["plan.md"],
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "blocked-reopen-requires-resolution"
    assert error["blockers"][0]["owner"] == "user"
    assert error["blockers"][0]["human_action_guide"] == original["human_action_guide"]
    assert error["blockers"][0]["exact_next_action"] == original["exact_next_action"]
    assert error["next_argv"] == []
    assert error["data"]["resolution_action"] == blocked["data"]["resolution_action"]
    persisted = show_workflow(feature_dir)
    assert persisted["blockers"][0]["human_action_guide"] == original[
        "human_action_guide"
    ]


def test_completed_accept_reopen_reports_terminal_policy_not_route_repair(
    tmp_path: Path,
) -> None:
    feature_dir = _feature(tmp_path)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=target,
            revision=revision,
        )
        revision = advanced["data"]["revision"]
    closed = closeout_workflow(
        feature_dir,
        expected_revision=revision,
        acceptance_sha256=_acceptance_snapshot(feature_dir),
    )

    with pytest.raises(InvalidTransition) as captured:
        reopen_workflow(
            feature_dir,
            target_stage="plan",
            expected_revision=closed["data"]["revision"],
            reason="A new requirement appeared after acceptance.",
            evidence=["change request CR-9"],
            invalidated_artifacts=["plan.md"],
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "terminal-workflow-immutable"
    assert "new specification workflow" in error["blockers"][0]["exact_next_action"]
    assert "route-repair" not in error["blockers"][0]["exact_next_action"]
    assert show_workflow(feature_dir)["data"]["status"] == "completed"


@pytest.mark.parametrize(
    "runtime_mutation",
    [
        {"status": "blocked", "blocker": None},
        {"status": "blocked", "blocker": {"summary": "partial"}},
        {"status": "active", "blocker": {"summary": "unexpected"}},
    ],
)
def test_runtime_rejects_inconsistent_or_partial_blocker_state(
    tmp_path: Path,
    runtime_mutation: dict[str, object],
) -> None:
    feature_dir = _feature(tmp_path)
    enter_workflow(feature_dir, stage="specify", expected_revision=0)
    runtime_path = workflow_runtime_path(feature_dir)
    payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    payload.update(runtime_mutation)
    runtime_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(WorkflowRuntimeError) as captured:
        show_workflow(feature_dir)

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "invalid-workflow-runtime"
    assert error["blockers"][0]["owner"] == "maintainer"
    assert error["blockers"][0]["human_action_guide"]["steps"]
