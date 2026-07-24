import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from specify_cli.implementation_deferrals import (
    ImplementationDeferralError,
    confirm_implementation_deferral,
    confirmed_deferral_for_blocker,
    confirmed_deferral_for_validation,
    confirmed_implementation_deferrals,
    propose_implementation_deferral,
)


def _project_with_blocker(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / "001-deferral"
    lifecycle_dir = feature / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (project / "src").mkdir()
    (project / "src" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    (feature / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["FR-001", "CA-001"],
                "tasks": [{"id": "T001"}],
            }
        ),
        encoding="utf-8",
    )
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "changed_paths": ["src/service.py"],
                "validation": [],
                "blockers": [
                    {
                        "classification": "external",
                        "owner": "user",
                        "evidence": "Remote evidence is not available yet.",
                        "exact_next_action": "Provide the remote evidence.",
                        "approval_question": "Defer this check to Review?",
                        "unblock_criteria": "Review obtains the remote evidence.",
                        "implementation_can_continue": True,
                        "completion_impact": "mandatory_for_completion",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return project, feature


def _proposal() -> dict[str, object]:
    return {
        "blocker_refs": ["T001-B01", "VALIDATION-CONVERGENCE"],
        "affected_task_ids": ["T001"],
        "affected_acceptance_refs": ["FR-001"],
        "deferred_validation_purposes": ["convergence"],
        "exact_excluded_behavior": "Remote convergence evidence is not yet available.",
        "residual_risk": "Review may discover an integration mismatch.",
        "risk_severity": "medium",
        "claims_withheld": ["full convergence verified", "integration-ready"],
        "reopen_or_stop_condition": "Review must rerun convergence before approval.",
        "downstream_artifact": "implementation-handoff.json",
        "downstream_owner": "review",
        "defer_until": "review",
    }


def test_human_confirmation_transfers_blocker_without_marking_it_passed(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_blocker(tmp_path)
    proposed = propose_implementation_deferral(project, feature, _proposal())

    assert proposed["status"] == "proposed"
    assert proposed["confirmation_required"] is True
    assert confirmed_implementation_deferrals(project, feature) == []

    confirmed = confirm_implementation_deferral(
        project,
        feature,
        deferral_id=proposed["deferral_id"],
        proposal_sha256=proposed["proposal_sha256"],
        confirmation_source="human-reply",
        statement="同意先移交到 Review，但不能算测试通过。",
    )

    assert confirmed["status"] == "confirmed"
    assert confirmed["disposition"] == "transferred_to_review"
    lifecycle = json.loads(
        (
            feature / "implementation-review" / "tasks" / "T001.json"
        ).read_text(encoding="utf-8")
    )
    assert lifecycle["status"] == "deferred"
    blocker = lifecycle["blockers"][0]
    assert blocker["disposition"] == "user_confirmed_deferral"
    assert blocker["disposition_ref"].endswith(
        f"{proposed['deferral_id']}.json"
    )
    record = confirmed_deferral_for_blocker(
        project, feature, "T001-B01"
    )
    assert record is not None
    assert record["proposal"]["claims_withheld"] == [
        "full convergence verified",
        "integration-ready",
    ]
    validation = confirmed_deferral_for_validation(
        project,
        feature,
        purpose="convergence",
        covered_task_ids={"T001"},
    )
    assert validation is not None

    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "implementation-deferral-schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(record)


def test_confirmed_deferral_is_ignored_after_source_change(tmp_path: Path) -> None:
    project, feature = _project_with_blocker(tmp_path)
    proposed = propose_implementation_deferral(project, feature, _proposal())
    confirm_implementation_deferral(
        project,
        feature,
        deferral_id=proposed["deferral_id"],
        proposal_sha256=proposed["proposal_sha256"],
        confirmation_source="human-reply",
        statement="同意仅对当前实现移交。",
    )

    (project / "src" / "service.py").write_text("VALUE = 2\n", encoding="utf-8")

    assert confirmed_implementation_deferrals(project, feature) == []


def test_stale_confirmation_can_be_reproposed_for_the_new_fingerprint(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_blocker(tmp_path)
    first = propose_implementation_deferral(project, feature, _proposal())
    confirm_implementation_deferral(
        project,
        feature,
        deferral_id=first["deferral_id"],
        proposal_sha256=first["proposal_sha256"],
        confirmation_source="human-reply",
        statement="同意仅对当前实现移交。",
    )
    (project / "src" / "service.py").write_text("VALUE = 2\n", encoding="utf-8")

    second = propose_implementation_deferral(project, feature, _proposal())

    assert second["deferral_id"] != first["deferral_id"]
    confirmed = confirm_implementation_deferral(
        project,
        feature,
        deferral_id=second["deferral_id"],
        proposal_sha256=second["proposal_sha256"],
        confirmation_source="human-reply",
        statement="同意对修改后的实现重新移交。",
    )
    assert confirmed["status"] == "confirmed"
    records = confirmed_implementation_deferrals(project, feature)
    assert [record["deferral_id"] for record in records] == [
        second["deferral_id"]
    ]


def test_tampered_confirmed_proposal_is_rejected(tmp_path: Path) -> None:
    project, feature = _project_with_blocker(tmp_path)
    proposed = propose_implementation_deferral(project, feature, _proposal())
    confirm_implementation_deferral(
        project,
        feature,
        deferral_id=proposed["deferral_id"],
        proposal_sha256=proposed["proposal_sha256"],
        confirmation_source="human-reply",
        statement="同意按当前精确范围移交。",
    )
    path = Path(proposed["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["proposal"]["claims_withheld"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ImplementationDeferralError, match="modified"):
        confirmed_implementation_deferrals(project, feature)


def test_high_risk_cannot_be_deferred_from_implement(tmp_path: Path) -> None:
    project, feature = _project_with_blocker(tmp_path)
    proposal = _proposal()
    proposal["risk_severity"] = "high"

    with pytest.raises(ImplementationDeferralError, match="high/critical"):
        propose_implementation_deferral(project, feature, proposal)


def test_agent_owned_blocker_cannot_be_human_deferred(tmp_path: Path) -> None:
    project, feature = _project_with_blocker(tmp_path)
    lifecycle_path = (
        feature / "implementation-review" / "tasks" / "T001.json"
    )
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    lifecycle["blockers"][0].update(
        {
            "classification": "technical",
            "owner": "agent",
            "exact_next_action": "Repair the local implementation defect.",
        }
    )
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    with pytest.raises(ImplementationDeferralError, match="agent-owned"):
        propose_implementation_deferral(project, feature, _proposal())


def test_task_blocker_must_be_inside_the_declared_affected_scope(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_blocker(tmp_path)
    proposal = _proposal()
    proposal["affected_task_ids"] = ["T002"]

    with pytest.raises(ImplementationDeferralError, match="unknown task ids"):
        propose_implementation_deferral(project, feature, proposal)


def test_deferral_must_expire_through_the_implementation_handoff(
    tmp_path: Path,
) -> None:
    project, feature = _project_with_blocker(tmp_path)
    proposal = _proposal()
    proposal["downstream_artifact"] = "backlog.md"

    with pytest.raises(
        ImplementationDeferralError,
        match="implementation-handoff.json",
    ):
        propose_implementation_deferral(project, feature, proposal)
