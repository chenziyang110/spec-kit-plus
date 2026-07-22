from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from specify_cli.workflow_runtime import (
    RevisionConflict,
    block_workflow,
    closeout_workflow,
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
    gate = project / ".specify" / "workflow-gate.py"
    gate.write_text(
        """import json

print(json.dumps({
    "status": "ok",
    "summary": "test artifact gate passed",
    "data": {},
    "items": [],
    "blockers": [],
    "show_argv": [],
    "next_argv": [],
}))
""",
        encoding="utf-8",
    )
    (project / ".specify" / "config.json").write_text(
        json.dumps({"specify_launcher": {"argv": [sys.executable, str(gate)]}}),
        encoding="utf-8",
    )
    return project, feature


def _advance(
    feature: Path,
    *,
    revision: int,
    targets: tuple[str, ...],
) -> int:
    for target in targets:
        completed = complete_workflow_stage(
            feature,
            expected_revision=revision,
            summary=f"{target} handoff ready",
        )
        transitioned = transition_workflow(
            feature,
            target_stage=target,
            expected_revision=int(completed["data"]["revision"]),
        )
        revision = int(transitioned["data"]["revision"])
    return revision


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


def test_real_runtime_lifecycle_and_terminal_acceptance_closeout(
    tmp_path: Path,
) -> None:
    _root, feature = _project(tmp_path, "001-lifecycle")
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = _advance(
        feature,
        revision=int(entered["data"]["revision"]),
        targets=("plan", "tasks", "implement", "review", "accept"),
    )
    acceptance_raw = b'{"status":"accepted","overall":{"verdict":"pass"}}\n'
    (feature / "human-acceptance.json").write_bytes(acceptance_raw)

    closed = closeout_workflow(
        feature,
        expected_revision=revision,
        summary="Human acceptance passed.",
    )
    shown = show_workflow(feature)

    assert closed["data"]["stage"] == "accept"
    assert closed["data"]["status"] == "completed"
    assert shown["data"]["acceptance_sha256"] == hashlib.sha256(
        acceptance_raw
    ).hexdigest()
    assert terminal_acceptance_snapshot_path(feature).read_bytes() == acceptance_raw
    assert workflow_runtime_path(feature).name == "workflow.json"
    assert not (feature / "workflow-runtime.json").exists()


def test_real_runtime_serializes_same_revision_competitors(tmp_path: Path) -> None:
    _root, feature = _project(tmp_path, "002-concurrency")
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    completed = complete_workflow_stage(
        feature,
        expected_revision=int(entered["data"]["revision"]),
    )
    revision = int(completed["data"]["revision"])

    def compete() -> dict[str, Any] | Exception:
        try:
            return transition_workflow(
                feature,
                target_stage="plan",
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
        "stage": "plan",
        "status": "active",
    }


def test_real_runtime_block_resolve_and_normal_reopen(tmp_path: Path) -> None:
    _root, feature = _project(tmp_path, "003-block-reopen")
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
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
    plan_revision = _advance(
        feature,
        revision=int(resolved["data"]["revision"]),
        targets=("plan",),
    )
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
    entered = enter_workflow(feature, stage="specify", expected_revision=0)
    revision = _advance(
        feature,
        revision=int(entered["data"]["revision"]),
        targets=("plan", "tasks", "implement", "review", "accept"),
    )
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
