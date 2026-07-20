from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest

from specify_cli.workflow_runtime import (
    complete_workflow_stage,
    enter_workflow,
    show_workflow,
    transition_workflow,
)


def _review_runtime() -> ModuleType:
    return importlib.import_module("specify_cli.review_runtime")


def _feature_at_review(tmp_path: Path) -> tuple[Path, Path, int]:
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-system-review"
    feature_dir.mkdir(parents=True)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "review"):
        completed = complete_workflow_stage(feature_dir, expected_revision=revision)
        transitioned = transition_workflow(
            feature_dir,
            target_stage=target,
            expected_revision=completed["data"]["revision"],
        )
        revision = transitioned["data"]["revision"]
    return project_root, feature_dir, revision


def _write_implementation_handoff(feature_dir: Path, revision: int) -> Path:
    handoff_path = feature_dir / "implementation-handoff.json"
    handoff_path.write_text(
        json.dumps(
            {
                "version": 1,
                "source_revision": revision,
                "implementation_fingerprint": "a" * 64,
                "official_entrypoints": [
                    {
                        "id": "web",
                        "command": "npm run dev",
                        "ready_signal": "GET /health returns 200",
                    }
                ],
                "system_review_scenarios": [
                    {
                        "id": "SR-START-001",
                        "kind": "startup",
                        "title": "Start the product from its official entrypoint",
                        "required": True,
                        "entrypoint_id": "web",
                        "preconditions": ["Dependencies are installed."],
                        "actions": ["Run npm run dev."],
                        "expected_results": ["GET /health returns 200."],
                        "required_evidence": ["runtime_diagnostics"],
                    },
                    {
                        "id": "SR-UI-001",
                        "kind": "interaction",
                        "title": "Complete the primary user journey",
                        "required": True,
                        "entrypoint_id": "web",
                        "preconditions": ["The product is ready."],
                        "actions": ["Open the home page.", "Select Demo."],
                        "expected_results": ["The Demo screen opens."],
                        "required_evidence": [
                            "structure_snapshot",
                            "visual_capture",
                            "runtime_diagnostics",
                        ],
                    },
                ],
                "review_obligations": [
                    {
                        "id": "RO-START-001",
                        "kind": "entrypoint",
                        "source_ref": "implementation-handoff:web",
                        "surface": "web startup and readiness",
                        "required": True,
                        "scenario_ids": ["SR-START-001"],
                    },
                    {
                        "id": "RO-UI-001",
                        "kind": "user-journey",
                        "source_ref": "acceptance:primary-demo-journey",
                        "surface": "home to Demo interaction",
                        "required": True,
                        "scenario_ids": ["SR-UI-001"],
                    },
                ],
                "human_acceptance_obligations": [
                    {
                        "id": "HAO-DEMO-001",
                        "source_ref": "plan-contract.json#/acceptance_refs/0",
                        "change_kind": "new",
                        "user_outcome": "A user can open the Demo screen.",
                        "required": True,
                        "scenario_ids": ["HA-DEMO-001"],
                    }
                ],
                "human_acceptance_scenarios": [
                    {
                        "id": "HA-DEMO-001",
                        "title": "Open the new Demo experience",
                        "user_value": "The user can reach the new Demo capability.",
                        "required": True,
                        "obligation_ids": ["HAO-DEMO-001"],
                        "entrypoint_id": "web",
                        "review_scenario_ids": ["SR-UI-001"],
                        "start_state": "The reviewed application is ready on its home page.",
                        "steps": [
                            {
                                "id": "HA-DEMO-001-S01",
                                "action": "Select Demo.",
                                "expected_result": "The Demo screen opens.",
                                "evidence_requirement": "Human reports the visible Demo screen.",
                                "risk": "low",
                            }
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["human_acceptance_scenarios"][0]["actor"] = "human user"
    contract = {
        "human_acceptance_obligations": handoff["human_acceptance_obligations"],
        "human_acceptance_scenarios": handoff["human_acceptance_scenarios"],
    }
    handoff["human_acceptance_contract_sha256"] = hashlib.sha256(
        json.dumps(
            contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    handoff["human_acceptance_contract_origin"] = "legacy-derived"
    handoff_path.write_text(
        json.dumps(handoff, indent=2) + "\n", encoding="utf-8"
    )
    return handoff_path


def _prepare(tmp_path: Path) -> tuple[ModuleType, Path, Path, int, dict[str, object]]:
    runtime = _review_runtime()
    project_root, feature_dir, revision = _feature_at_review(tmp_path)
    _write_implementation_handoff(feature_dir, revision)
    prepared = runtime.prepare_review(
        project_root,
        feature_dir,
        expected_revision=revision,
    )
    return runtime, project_root, feature_dir, revision, prepared


def _write_scenario_evidence(
    feature_dir: Path,
    state: dict[str, object],
    *,
    snapshot_sha256: str = "a" * 64,
) -> None:
    for scenario in state["scenarios"]:
        scenario["result"] = "pass"
        scenario["evidence"] = []
        for kind in scenario["required_evidence"]:
            relative_path = Path("review-evidence") / scenario["id"] / f"{kind}.json"
            evidence_path = feature_dir / relative_path
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text("{}\n", encoding="utf-8")
            scenario["evidence"].append(
                {
                    "kind": kind,
                    "path": relative_path.as_posix(),
                    "evidence_scope": "integrated",
                    "snapshot_sha256": snapshot_sha256,
                }
            )


def _complete_leader_review(
    state: dict[str, object],
    *,
    feature_dir: Path,
    snapshot_sha256: str = "a" * 64,
) -> None:
    obligation_ids = [item["id"] for item in state["obligations"]]
    scenario_ids = [item["id"] for item in state["scenarios"]]
    for obligation in state["obligations"]:
        obligation["status"] = "covered"
        obligation["review_assignment_ids"] = ["RA-COVERAGE-001"]
    state["review_assignments"] = [
        {
            "id": "RA-COVERAGE-001",
            "kind": "coverage_audit",
            "worker_id": "coverage-auditor",
            "obligation_ids": obligation_ids,
            "scenario_ids": scenario_ids,
            "read_only": True,
            "packet_ref": "review-results/RA-COVERAGE-001.packet.json",
            "result_ref": "review-results/RA-COVERAGE-001.json",
            "observed_snapshot_sha256": snapshot_sha256,
            "status": "accepted",
            "leader_verdict": "accepted",
        }
    ]
    results_dir = feature_dir / "review-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for name in ("RA-COVERAGE-001.packet.json", "RA-COVERAGE-001.json"):
        (results_dir / name).write_text("{}\n", encoding="utf-8")
    state["coverage"].update(
        {
            "discovery_complete": True,
            "blind_audit_complete": True,
            "uncovered_obligation_ids": [],
            "uncovered_surface_ids": [],
            "final_gap_scan": "pass",
        }
    )
    state["leader"].update(
        {
            "strategy": "leader-plus-subagents",
            "review_plan_complete": True,
            "all_review_results_joined": True,
            "fix_plan_complete": True,
            "all_fix_results_joined": True,
            "final_revalidation_complete": True,
            "verdict": "pass",
        }
    )
    state["final"].update(
        {
            "verdict": "pass",
            "coverage_verdict": "pass",
            "repair_verdict": "pass",
            "integration_verdict": "pass",
            "all_packets_joined": True,
            "reviewed_snapshot_sha256": snapshot_sha256,
        }
    )


def test_prepare_review_compiles_handoff_into_resumable_review_state(
    tmp_path: Path,
) -> None:
    runtime, _project_root, feature_dir, revision, prepared = _prepare(tmp_path)

    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    handoff_bytes = (feature_dir / "implementation-handoff.json").read_bytes()

    assert prepared["status"] == "ok"
    assert prepared["data"]["status"] == "reviewing"
    assert state_path == feature_dir / "review-state.json"
    assert state["version"] == 2
    assert state["status"] == "reviewing"
    handoff_sha256 = hashlib.sha256(handoff_bytes).hexdigest()
    assert state["source"] == {
        "workflow_revision": revision,
        "implementation_fingerprint": "a" * 64,
        "implementation_handoff_sha256": handoff_sha256,
        "review_cycle": 1,
        "review_cycle_id": runtime._review_cycle_id(
            workflow_revision=revision,
            handoff_sha256=handoff_sha256,
            review_cycle=1,
            previous_review_state_sha256="",
            acceptance_finding_id="",
        ),
        "previous_review_state_sha256": "",
        "acceptance_finding_id": "",
    }
    assert [scenario["id"] for scenario in state["scenarios"]] == [
        "SR-START-001",
        "SR-UI-001",
    ]
    assert all(scenario["result"] == "pending" for scenario in state["scenarios"])
    assert state["findings"] == []
    assert [obligation["id"] for obligation in state["obligations"]] == [
        "RO-START-001",
        "RO-UI-001",
    ]
    assert state["review_assignments"] == []
    assert state["fix_assignments"] == []
    assert state["revalidations"] == []
    assert state["coverage"]["blind_audit_complete"] is False
    assert state["leader"]["strategy"] == "pending"
    assert state["cursor"]["scenario_id"] == "SR-START-001"
    assert [item["id"] for item in state["human_acceptance_obligations"]] == [
        "HAO-DEMO-001"
    ]
    assert [item["id"] for item in state["human_acceptance_scenarios"]] == [
        "HA-DEMO-001"
    ]


def test_build_implementation_handoff_carries_the_human_acceptance_universe(
    tmp_path: Path,
) -> None:
    runtime = _review_runtime()
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    task_index = {
        "version": 2,
        "status": "ready",
        "acceptance_refs": ["plan-contract.json#/acceptance_refs/0"],
        "official_entrypoints": [
            {
                "id": "web",
                "command": "npm run dev",
                "ready_signal": "GET /health returns 200",
            }
        ],
        "system_review_scenarios": [
            {
                "id": "SR-DEMO-001",
                "kind": "interaction",
                "title": "Open Demo",
                "required": True,
                "entrypoint_id": "web",
                "preconditions": ["The product is ready."],
                "actions": ["Select Demo."],
                "expected_results": ["The Demo screen opens."],
                "required_evidence": ["runtime_diagnostics"],
            }
        ],
        "review_obligations": [],
        "human_acceptance_obligations": [
            {
                "id": "HAO-DEMO-001",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "change_kind": "changed",
                "user_outcome": "A user can open Demo.",
                "required": True,
                "scenario_ids": ["HA-DEMO-001"],
            }
        ],
        "human_acceptance_scenarios": [
            {
                "id": "HA-DEMO-001",
                "title": "Open Demo",
                "user_value": "A user reaches Demo.",
                "actor": "human user",
                "required": True,
                "obligation_ids": ["HAO-DEMO-001"],
                "entrypoint_id": "web",
                "review_scenario_ids": ["SR-DEMO-001"],
                "start_state": "The home page is open.",
                "steps": [
                    {
                        "id": "HA-DEMO-001-S01",
                        "action": "Select Demo.",
                        "expected_result": "The Demo screen opens.",
                        "evidence_requirement": "Human-visible Demo screen.",
                        "risk": "low",
                    }
                ],
            }
        ],
    }
    (feature_dir / "task-index.json").write_text(
        json.dumps(task_index, indent=2) + "\n", encoding="utf-8"
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": [
                    "spec-contract.json#/acceptance_criteria/0"
                ],
            }
        ),
        encoding="utf-8",
    )

    runtime.build_implementation_handoff(
        project_root, feature_dir, source_revision=7
    )
    handoff = json.loads(
        (feature_dir / "implementation-handoff.json").read_text(encoding="utf-8")
    )

    assert handoff["human_acceptance_obligations"] == task_index[
        "human_acceptance_obligations"
    ]
    assert handoff["human_acceptance_scenarios"] == task_index[
        "human_acceptance_scenarios"
    ]
    assert len(handoff["human_acceptance_contract_sha256"]) == 64


def test_modern_handoff_rejects_missing_human_acceptance_universe(
    tmp_path: Path,
) -> None:
    runtime = _review_runtime()
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["plan-contract.json#/acceptance_refs/0"],
                "official_entrypoints": [
                    {
                        "id": "web",
                        "command": "npm run dev",
                        "ready_signal": "ready",
                    }
                ],
                "system_review_scenarios": [
                    {
                        "id": "SR-001",
                        "kind": "interaction",
                        "title": "Use the changed journey",
                        "required": True,
                        "entrypoint_id": "web",
                        "actions": ["Use it."],
                        "expected_results": ["It works."],
                        "required_evidence": ["runtime_diagnostics"],
                    }
                ],
                "human_acceptance_obligations": [],
                "human_acceptance_scenarios": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(runtime.ReviewRuntimeError, match="Human Acceptance Universe"):
        runtime.build_implementation_handoff(
            project_root, feature_dir, source_revision=7
        )


@pytest.mark.parametrize("failure", ("entrypoint", "required-review"))
def test_handoff_revalidates_human_to_system_review_links(
    tmp_path: Path, failure: str
) -> None:
    runtime = _review_runtime()
    _project_root, feature_dir, revision = _feature_at_review(tmp_path)
    handoff_path = _write_implementation_handoff(feature_dir, revision)
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["official_entrypoints"].append(
        {"id": "mobile", "command": "open app", "ready_signal": "home visible"}
    )
    if failure == "entrypoint":
        handoff["human_acceptance_scenarios"][0]["entrypoint_id"] = "mobile"
        expected = "different entrypoint"
    else:
        handoff["system_review_scenarios"][1]["required"] = False
        expected = "required Review scenario"

    with pytest.raises(runtime.ReviewRuntimeError, match=expected):
        runtime._normalized_handoff(handoff, expected_revision=revision)


def test_handoff_binds_acceptance_denominator_and_task_contract_digests(
    tmp_path: Path,
) -> None:
    runtime = _review_runtime()
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    plan_path = feature_dir / "plan-contract.json"
    plan_path.write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": [
                    "spec-contract.json#/acceptance_criteria/0"
                ],
            }
        ),
        encoding="utf-8",
    )
    task_index = {
        "version": 2,
        "status": "ready",
        "acceptance_refs": ["plan-contract.json#/acceptance_refs/0"],
        "official_entrypoints": [
            {"id": "web", "command": "npm run dev", "ready_signal": "ready"}
        ],
        "system_review_scenarios": [
            {
                "id": "SR-001",
                "kind": "interaction",
                "title": "Use the changed journey",
                "required": True,
                "entrypoint_id": "web",
                "actions": ["Use it."],
                "expected_results": ["It works."],
                "required_evidence": ["runtime_diagnostics"],
            }
        ],
        "human_acceptance_obligations": [
            {
                "id": "HAO-001",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "change_kind": "new",
                "user_outcome": "A human can use the changed journey.",
                "required": True,
                "scenario_ids": ["HA-001"],
            }
        ],
        "human_acceptance_scenarios": [
            {
                "id": "HA-001",
                "title": "Use the changed journey",
                "user_value": "The changed journey works.",
                "actor": "human user",
                "required": True,
                "obligation_ids": ["HAO-001"],
                "entrypoint_id": "web",
                "review_scenario_ids": ["SR-001"],
                "start_state": "The reviewed app is ready.",
                "steps": [
                    {
                        "id": "HA-001-S01",
                        "action": "Use it.",
                        "expected_result": "It works.",
                        "evidence_requirement": "Human observation.",
                        "risk": "low",
                    }
                ],
            }
        ],
    }
    task_path = feature_dir / "task-index.json"
    task_path.write_text(json.dumps(task_index), encoding="utf-8")

    runtime.build_implementation_handoff(
        project_root, feature_dir, source_revision=7
    )
    handoff = json.loads(
        (feature_dir / "implementation-handoff.json").read_text(encoding="utf-8")
    )

    assert handoff["acceptance_refs"] == task_index["acceptance_refs"]
    assert handoff["task_index_sha256"] == hashlib.sha256(
        task_path.read_bytes()
    ).hexdigest()
    assert handoff["plan_contract_sha256"] == hashlib.sha256(
        plan_path.read_bytes()
    ).hexdigest()


def test_validate_review_rejects_failed_scenario_and_open_finding(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "repairing"
    state["scenarios"][0]["result"] = "fail"
    state["findings"] = [
        {
            "id": "SRF-001",
            "scenario_id": "SR-START-001",
            "classification": "startup",
            "summary": "The official entrypoint exits before becoming ready.",
            "status": "open",
        }
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert validation["fresh"] is True
    assert any("SR-START-001" in error for error in validation["errors"])
    assert any("SRF-001" in error for error in validation["errors"])


def test_approved_review_requires_a_snapshot_bound_runtime_target(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state["reviewed_runtime_targets"] = []
    state["final"]["runtime_targets_sha256"] = ""
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("reviewed runtime target" in error for error in validation["errors"])


def test_approved_review_rejects_runtime_target_identity_digest_drift(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state["reviewed_runtime_targets"][0]["instance_ref"] = "old deployment"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("runtime_targets_sha256" in error for error in validation["errors"])


def test_validate_review_marks_changed_implementation_handoff_stale(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    handoff_path = feature_dir / "implementation-handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["implementation_fingerprint"] = "b" * 64
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert validation["fresh"] is False
    assert any("stale" in error.lower() for error in validation["errors"])


@pytest.mark.parametrize(
    "mutate",
    (
        lambda state: state["scenarios"].pop(),
        lambda state: state["scenarios"][0].update({"required": False}),
        lambda state: state["scenarios"][0].update({"actions": ["Pretend it ran."]}),
        lambda state: state["scenarios"][0].update({"required_evidence": []}),
    ),
)
def test_validate_review_rejects_canonical_scenario_contract_drift(
    tmp_path: Path,
    mutate,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    mutate(state)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("canonical scenario contract" in error for error in validation["errors"])


def test_validate_review_rejects_approved_state_without_zero_gap_subagent_coverage(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    state["status"] = "approved"
    state["final"]["reviewed_snapshot_sha256"] = "a" * 64
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("coverage audit" in error for error in validation["errors"])
    assert any("required obligation" in error for error in validation["errors"])
    assert any("Leader" in error for error in validation["errors"])


def test_validate_review_rejects_declared_evidence_without_a_real_file(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for scenario in state["scenarios"]:
        scenario["result"] = "pass"
        scenario["evidence"] = [
            {
                "kind": kind,
                "path": f"review-evidence/{scenario['id']}/{kind}.json",
                "evidence_scope": "integrated",
            }
            for kind in scenario["required_evidence"]
        ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("does not exist" in error for error in validation["errors"])


def test_closeout_review_requires_approved_fresh_evidence_and_does_not_advance_workflow(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state["findings"] = []
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    closed = runtime.closeout_review(
        project_root,
        feature_dir,
        expected_revision=revision,
    )

    assert closed["status"] == "ok"
    assert closed["data"]["status"] == "approved"
    assert closed["data"]["fresh"] is True
    assert closed["next_argv"] == [
        "specify",
        "workflow",
        "complete-stage",
        "--feature-dir",
        str(feature_dir.resolve()),
        "--expected-revision",
        str(revision),
        "--format",
        "json",
    ]
    workflow = show_workflow(feature_dir)["data"]
    assert workflow["stage"] == "review"
    assert workflow["status"] == "active"
    assert workflow["revision"] == revision


def test_closeout_review_preserves_state_when_review_is_not_approved(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    before = state_path.read_bytes()

    with pytest.raises(runtime.ReviewRuntimeError, match="approved"):
        runtime.closeout_review(
            project_root,
            feature_dir,
            expected_revision=revision,
        )

    assert state_path.read_bytes() == before
    assert show_workflow(feature_dir)["data"]["stage"] == "review"


def test_approved_review_requires_snapshot_bound_final_claim_and_joined_results(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state["final"]["reviewed_snapshot_sha256"] = ""
    (feature_dir / "review-results" / "RA-COVERAGE-001.json").unlink()
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("final reviewed snapshot" in error for error in validation["errors"])
    assert any("result file does not exist" in error for error in validation["errors"])


def test_validate_review_requires_independent_fix_and_revalidation_for_every_finding(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state["findings"] = [
        {
            "id": "SRF-001",
            "scenario_id": "SR-UI-001",
            "obligation_ids": ["RO-UI-001"],
            "classification": "wiring",
            "severity": "high",
            "blocking": True,
            "summary": "The Demo button is disconnected.",
            "expected": "Selecting Demo opens the Demo screen.",
            "observed": "Selecting Demo has no effect.",
            "discovered_by_review_assignment_id": "RA-COVERAGE-001",
            "status": "accepted_residual_risk",
            "fix_assignment_id": "",
            "revalidation_ids": [],
        }
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("blocking finding" in error for error in validation["errors"])
    assert any("independent Fix assignment" in error for error in validation["errors"])
    assert any("independent revalidation" in error for error in validation["errors"])


def test_closeout_accepts_review_worker_to_independent_fix_to_revalidation_loop(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state["findings"] = [
        {
            "id": "SRF-001",
            "scenario_id": "SR-UI-001",
            "obligation_ids": ["RO-UI-001"],
            "classification": "wiring",
            "severity": "high",
            "blocking": True,
            "summary": "The Demo button was disconnected.",
            "expected": "Selecting Demo opens the Demo screen.",
            "observed": "The repaired button opens Demo.",
            "discovered_by_review_assignment_id": "RA-COVERAGE-001",
            "status": "verified",
            "fix_assignment_id": "FX-001",
            "revalidation_ids": ["RV-001"],
        }
    ]
    state["fix_assignments"] = [
        {
            "id": "FX-001",
            "finding_ids": ["SRF-001"],
            "worker_id": "fixer",
            "allowed_write_paths": ["src/demo"],
            "changed_paths": ["src/demo/button.ts"],
            "packet_ref": "review-results/FX-001.packet.json",
            "result_ref": "review-results/FX-001.json",
            "status": "accepted",
            "leader_verdict": "accepted",
        }
    ]
    state["revalidations"] = [
        {
            "id": "RV-001",
            "worker_id": "independent-validator",
            "finding_ids": ["SRF-001"],
            "fix_assignment_ids": ["FX-001"],
            "scenario_ids": ["SR-UI-001"],
            "snapshot_sha256": "a" * 64,
            "result": "pass",
            "evidence_refs": ["review-evidence/SR-UI-001/runtime_diagnostics.json"],
            "leader_verdict": "accepted",
        }
    ]
    for name in ("FX-001.packet.json", "FX-001.json"):
        (feature_dir / "review-results" / name).write_text("{}\n", encoding="utf-8")
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    closed = runtime.closeout_review(project_root, feature_dir, expected_revision=revision)

    assert closed["status"] == "ok"


def test_approved_review_becomes_stale_when_live_source_changes(tmp_path: Path) -> None:
    runtime = _review_runtime()
    project_root, feature_dir, revision = _feature_at_review(tmp_path)
    source_path = project_root / "src" / "app.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("print('ready')\n", encoding="utf-8")
    handoff_path = _write_implementation_handoff(feature_dir, revision)
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["fingerprint_algorithm"] = "git-working-tree-v1"
    handoff["implementation_fingerprint"] = runtime.implementation_snapshot_sha256(
        project_root, feature_dir
    )
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    runtime.prepare_review(project_root, feature_dir, expected_revision=revision)

    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    reviewed_snapshot = runtime.implementation_snapshot_sha256(project_root, feature_dir)
    _write_scenario_evidence(
        feature_dir,
        state,
        snapshot_sha256=reviewed_snapshot,
    )
    _complete_leader_review(
        state,
        feature_dir=feature_dir,
        snapshot_sha256=reviewed_snapshot,
    )
    state["status"] = "approved"
    state["final"]["reviewed_snapshot_sha256"] = reviewed_snapshot
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    assert runtime.validate_review(project_root, feature_dir)["valid"] is True

    source_path.write_text("print('changed after review')\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)
    assert validation["valid"] is False
    assert validation["fresh"] is False
    assert any("reviewed snapshot" in error for error in validation["errors"])
