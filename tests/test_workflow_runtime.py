from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.workflow_runtime import (
    InvalidTransition,
    RevisionConflict,
    WorkflowRuntimeError,
    block_workflow,
    complete_workflow_stage,
    enter_workflow,
    reopen_acceptance_workflow,
    reopen_workflow,
    resolve_workflow_blocker,
    show_workflow,
    terminal_acceptance_snapshot_path,
    transition_workflow,
    workflow_runtime_path,
)

pytestmark = pytest.mark.usefixtures("unified_runtime_env")


def _project(tmp_path: Path, feature_id: str) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / feature_id
    feature.mkdir(parents=True)
    return project, feature


def _seed_existing_workflow_state(
    feature: Path,
    *,
    revision: int,
    stage: str,
    status: str = "active",
) -> None:
    """Create an existing-state fixture; mutations under test still use the CLI."""

    workflow_runtime_path(feature).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": feature.name,
                "revision": revision,
                "stage": stage,
                "status": status,
                "summary": "existing workflow fixture",
                "blocker": None,
                "last_resolution_evidence": [],
                "last_reopen": None,
                "last_blocker_resolution": None,
                "acceptance_sha256": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _acceptance_repair_files(
    feature: Path,
    *,
    revision: int,
    route: str,
    finding_id: str,
) -> None:
    acceptance = {
        "status": "draft",
        "repair_resume": {"finding_id": finding_id},
        "overall": {"verdict": "pending", "next_command": route},
    }
    acceptance_raw = (
        json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    (feature / "human-acceptance.json").write_bytes(acceptance_raw)
    journal = {
        "version": 1,
        "phase": "acceptance-invalidated",
        "finding_id": finding_id,
        "route": route,
        "target_stage": "review",
        "expected_revision": revision,
        "invalidated_acceptance_sha256": hashlib.sha256(
            acceptance_raw
        ).hexdigest(),
        "acceptance_file": "human-acceptance.json",
    }
    (feature / ".human-acceptance-repair.json").write_text(
        json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_real_runtime_refuses_stage_completion_without_go_validated_artifacts(
    tmp_path: Path,
) -> None:
    _root, feature = _project(tmp_path, "001-lifecycle")
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = int(entered["data"]["revision"])

    with pytest.raises(WorkflowRuntimeError) as exc_info:
        complete_workflow_stage(feature, expected_revision=revision)

    assert exc_info.value.code == "artifact-validation-failed"
    shown = show_workflow(feature)
    assert shown["data"]["revision"] == revision
    assert shown["data"]["stage"] == "specify"
    assert shown["data"]["status"] == "active"
    assert not terminal_acceptance_snapshot_path(feature).exists()
    assert workflow_runtime_path(feature).name == "workflow.json"
    assert not (feature / "workflow-runtime.json").exists()


def test_real_runtime_serializes_same_revision_competitors(tmp_path: Path) -> None:
    _root, feature = _project(tmp_path, "002-concurrency")
    entered = enter_workflow(feature, stage="discussion", expected_revision=0)
    completed = complete_workflow_stage(
        feature,
        expected_revision=int(entered["data"]["revision"]),
    )
    revision = int(completed["data"]["revision"])

    def compete() -> dict[str, Any] | Exception:
        try:
            return transition_workflow(
                feature,
                target_stage="specify",
                expected_revision=revision,
            )
        except Exception as exc:  # noqa: BLE001 - the losing result is asserted below
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: compete(), range(2)))

    assert sum(isinstance(item, dict) for item in outcomes) == 1
    failures = [item for item in outcomes if isinstance(item, Exception)]
    assert len(failures) == 1
    assert isinstance(failures[0], RevisionConflict)
    assert show_workflow(feature)["data"] == {
        **show_workflow(feature)["data"],
        "revision": revision + 1,
        "stage": "specify",
        "status": "active",
    }


def test_real_runtime_block_resolve_and_normal_reopen(tmp_path: Path) -> None:
    _root, feature = _project(tmp_path, "003-block-reopen")
    entered = enter_workflow(feature, stage="discussion", expected_revision=0)
    blocked = block_workflow(
        feature,
        expected_revision=int(entered["data"]["revision"]),
        category="external-system",
        owner="external-system",
        cause="The upstream health probe returned HTTP 503.",
        evidence=["sanitized probe: HTTP 503"],
        attempted_recovery=[
            {"action": "retried read-only probe", "result": "HTTP 503 persisted"}
        ],
        affected_scope=["specification handoff"],
        exact_next_action="Retry the probe after provider recovery.",
        unblock_criteria="The probe returns HTTP 200.",
        human_action_required=False,
    )

    assert blocked["status"] == "blocked"
    assert show_workflow(feature)["status"] == "blocked"
    resolved = resolve_workflow_blocker(
        feature,
        expected_revision=int(blocked["data"]["revision"]),
        resolution_evidence=["sanitized probe: HTTP 200"],
    )
    plan_revision = int(resolved["data"]["revision"]) + 1
    _seed_existing_workflow_state(feature, revision=plan_revision, stage="plan")
    reopened = reopen_workflow(
        feature,
        target_stage="specify",
        expected_revision=plan_revision,
        reason="The specification contract changed.",
        evidence=["finding F-12"],
        invalidated_artifacts=["spec-contract.json", "plan.md"],
    )

    assert reopened["data"]["stage"] == "specify"
    assert reopened["data"]["status"] == "active"
    assert reopened["data"]["revision"] == plan_revision + 1


def test_real_runtime_acceptance_repair_uses_guarded_go_reopen(
    tmp_path: Path,
) -> None:
    _root, feature = _project(tmp_path, "004-acceptance-repair")
    revision = 11
    _seed_existing_workflow_state(feature, revision=revision, stage="accept")
    _acceptance_repair_files(
        feature,
        revision=revision,
        route="sp-review",
        finding_id="HA-9",
    )

    repaired = reopen_acceptance_workflow(
        feature,
        target_stage="review",
        repair_route="sp-review",
        finding_id="HA-9",
        expected_revision=revision,
        evidence=["scenario HA-9 failed at the mobile viewport"],
    )

    assert repaired["data"]["stage"] == "review"
    assert repaired["data"]["status"] == "active"
    assert repaired["data"]["revision"] == revision + 1
    assert repaired["data"]["last_reopen"]["repair_route"] == "sp-review"


def test_review_cannot_reopen_implement_for_routine_repair(tmp_path: Path) -> None:
    _root, feature = _project(tmp_path, "005-review-owned-repair")
    revision = 9
    _seed_existing_workflow_state(feature, revision=revision, stage="review")

    with pytest.raises(InvalidTransition) as exc_info:
        reopen_workflow(
            feature,
            target_stage="implement",
            expected_revision=revision,
            reason="A system journey exposed a wiring defect.",
            evidence=["finding SRF-001"],
            invalidated_artifacts=["review-state.json"],
        )

    assert exc_info.value.code == "review-repair-owned-by-review"
    assert show_workflow(feature)["data"]["stage"] == "review"
