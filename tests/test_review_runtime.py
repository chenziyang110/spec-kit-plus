from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest
from tests.conftest import install_passing_workflow_gate

from specify_cli.workflow_runtime import (
    complete_workflow_stage,
    enter_workflow,
    show_workflow,
    transition_workflow,
)


pytestmark = pytest.mark.usefixtures("unified_runtime_env")


def _review_runtime() -> ModuleType:
    return importlib.import_module("specify_cli.review_runtime")


def _mock_workflow_stage(
    runtime: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    *,
    stage: str = "implement",
    status: str = "active",
) -> dict[str, str]:
    state = {"stage": stage, "status": status}
    monkeypatch.setattr(runtime, "show_workflow", lambda _feature: {"data": state})
    return state


def test_review_findings_require_orthogonal_gap_classification() -> None:
    runtime = _review_runtime()
    findings = [
        {"id": "SRF-MISSING"},
        {"id": "SRF-INVALID", "gap_classification": "task_gap"},
        {"id": "SRF-IMPLEMENT", "gap_classification": "implementation_gap"},
        {"id": "SRF-TRACE", "gap_classification": "traceability_gap"},
        {"id": "SRF-TRUTH", "gap_classification": "upstream_truth_gap"},
    ]

    errors = runtime._review_finding_gap_classification_errors(findings)

    assert errors == [
        "finding SRF-MISSING requires gap_classification",
        "finding SRF-INVALID has unsupported gap_classification task_gap",
    ]


def _feature_at_review(tmp_path: Path) -> tuple[Path, Path, int]:
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-system-review"
    feature_dir.mkdir(parents=True)
    install_passing_workflow_gate(project_root)
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
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
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
    review_cycle = state.get("source", {}).get("review_cycle", 1)
    review_cycle_id = state.get("source", {}).get("review_cycle_id")
    evidence_root = Path("review-evidence")
    if isinstance(review_cycle, int) and review_cycle >= 2:
        evidence_root /= f"cycle-{review_cycle}"
    for scenario in state["scenarios"]:
        scenario["result"] = "pass"
        scenario["evidence"] = []
        for kind in scenario["required_evidence"]:
            relative_path = evidence_root / scenario["id"] / f"{kind}.json"
            evidence_path = feature_dir / relative_path
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text("{}\n", encoding="utf-8")
            scenario["evidence"].append(
                {
                    "kind": kind,
                    "path": relative_path.as_posix(),
                    "evidence_scope": "integrated",
                    "snapshot_sha256": snapshot_sha256,
                    "review_cycle_id": review_cycle_id,
                    "artifact_sha256": hashlib.sha256(
                        evidence_path.read_bytes()
                    ).hexdigest(),
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
    review_cycle = state.get("source", {}).get("review_cycle", 1)
    review_cycle_id = state.get("source", {}).get("review_cycle_id")
    results_root = Path("review-results")
    if isinstance(review_cycle, int) and review_cycle >= 2:
        results_root /= f"cycle-{review_cycle}"
    packet_ref = results_root / "RA-COVERAGE-001.packet.json"
    result_ref = results_root / "RA-COVERAGE-001.json"
    for artifact_ref in (packet_ref, result_ref):
        artifact_path = feature_dir / artifact_ref
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("{}\n", encoding="utf-8")
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
            "packet_ref": packet_ref.as_posix(),
            "result_ref": result_ref.as_posix(),
            "packet_sha256": hashlib.sha256(
                (feature_dir / packet_ref).read_bytes()
            ).hexdigest(),
            "result_sha256": hashlib.sha256(
                (feature_dir / result_ref).read_bytes()
            ).hexdigest(),
            "review_cycle_id": review_cycle_id,
            "observed_snapshot_sha256": snapshot_sha256,
            "status": "accepted",
            "leader_verdict": "accepted",
        }
    ]
    reviewed_runtime_targets = []
    for index, entrypoint in enumerate(state["entrypoints"]):
        linked_scenarios = [
            scenario
            for scenario in state["scenarios"]
            if scenario["entrypoint_id"] == entrypoint["id"]
        ]
        ready_evidence_refs = [
            evidence["path"]
            for scenario in linked_scenarios
            for evidence in scenario.get("evidence", [])
            if evidence.get("kind") == "runtime_diagnostics"
        ]
        if not ready_evidence_refs:
            ready_root = Path("review-evidence")
            if isinstance(review_cycle, int) and review_cycle >= 2:
                ready_root /= f"cycle-{review_cycle}"
            ready_ref = (ready_root / f"runtime-target-{index + 1}.json").as_posix()
            ready_path = feature_dir / ready_ref
            ready_path.parent.mkdir(parents=True, exist_ok=True)
            ready_path.write_text("{}\n", encoding="utf-8")
            ready_evidence_refs = [ready_ref]
        target = {
            "id": f"RRT-{entrypoint['id'].upper()}-{index + 1:03d}",
            "mode": "source",
            "status": "ready",
            "entrypoint_id": entrypoint["id"],
            "environment_ref": "isolated Review environment",
            "instance_ref": f"review://{entrypoint['id']}",
            "configuration_ref": "reviewed default configuration",
            "reviewed_snapshot_sha256": snapshot_sha256,
            "artifact_ref": None,
            "artifact_sha256": None,
            "deployment_id": None,
            "observed_version": None,
            "test_data_refs": ["isolated Review fixture"],
            "ready_evidence_refs": ready_evidence_refs,
            "review_scenario_ids": [scenario["id"] for scenario in linked_scenarios],
        }
        identity_root = Path("review-evidence")
        if isinstance(review_cycle, int) and review_cycle >= 2:
            identity_root /= f"cycle-{review_cycle}"
        identity_ref = identity_root / f"runtime-target-{index + 1}.identity.json"
        identity_path = feature_dir / identity_ref
        identity_path.parent.mkdir(parents=True, exist_ok=True)
        identity_path.write_text(
            json.dumps(
                _review_runtime()._review_runtime_identity_claim(target), indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        target["identity_evidence_ref"] = identity_ref.as_posix()
        target["identity_evidence_sha256"] = hashlib.sha256(
            identity_path.read_bytes()
        ).hexdigest()
        reviewed_runtime_targets.append(target)
    state["reviewed_runtime_targets"] = reviewed_runtime_targets
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
            "runtime_targets_sha256": _review_runtime()._review_runtime_targets_sha256(
                reviewed_runtime_targets
            ),
        }
    )


def _accepted_fix_assignments_sha256(
    fix_assignments: list[dict[str, object]],
) -> str:
    payload = [
        {
            key: assignment.get(key)
            for key in (
                "id",
                "finding_ids",
                "worker_id",
                "allowed_write_paths",
                "changed_paths",
                "packet_ref",
                "packet_sha256",
                "result_ref",
                "result_sha256",
                "review_cycle_id",
            )
        }
        for assignment in sorted(fix_assignments, key=lambda item: str(item.get("id")))
        if assignment.get("status") == "accepted"
        and assignment.get("leader_verdict") == "accepted"
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _add_fix_revalidation_loop(
    feature_dir: Path,
    state: dict[str, object],
    *,
    full_matrix: bool,
    manifest_snapshot_sha256: str = "a" * 64,
) -> Path:
    review_cycle = state["source"]["review_cycle"]
    review_cycle_id = state["source"]["review_cycle_id"]
    result_root = Path("review-results")
    if review_cycle >= 2:
        result_root /= f"cycle-{review_cycle}"
    result_dir = feature_dir / result_root
    result_dir.mkdir(parents=True, exist_ok=True)

    packet_ref = result_root / "FX-001.packet.json"
    result_ref = result_root / "FX-001.json"
    for artifact_ref in (packet_ref, result_ref):
        (feature_dir / artifact_ref).write_text("{}\n", encoding="utf-8")

    state["findings"] = [
        {
            "id": "SRF-001",
            "scenario_id": "SR-UI-001",
            "obligation_ids": ["RO-UI-001"],
            "classification": "wiring",
            "gap_classification": "implementation_gap",
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
            "packet_ref": packet_ref.as_posix(),
            "result_ref": result_ref.as_posix(),
            "packet_sha256": hashlib.sha256(
                (feature_dir / packet_ref).read_bytes()
            ).hexdigest(),
            "result_sha256": hashlib.sha256(
                (feature_dir / result_ref).read_bytes()
            ).hexdigest(),
            "review_cycle_id": review_cycle_id,
            "status": "accepted",
            "leader_verdict": "accepted",
        }
    ]
    fix_assignments_sha256 = _accepted_fix_assignments_sha256(state["fix_assignments"])
    scenario_ids = [
        scenario["id"]
        for scenario in state["scenarios"]
        if full_matrix or scenario["id"] == "SR-UI-001"
    ]
    scenario_evidence = sorted(
        [
            {
                "scenario_id": scenario["id"],
                "kind": evidence["kind"],
                "path": evidence["path"],
                "artifact_sha256": evidence["artifact_sha256"],
            }
            for scenario in state["scenarios"]
            if scenario["id"] in scenario_ids
            for evidence in scenario["evidence"]
            if evidence["kind"] in scenario["required_evidence"]
        ],
        key=lambda item: (item["scenario_id"], item["kind"], item["path"]),
    )
    manifest_ref = result_root / "RV-001.manifest.json"
    manifest_path = feature_dir / manifest_ref
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "revalidation_id": "RV-001",
                "review_cycle_id": review_cycle_id,
                "snapshot_sha256": manifest_snapshot_sha256,
                "fix_assignments_sha256": fix_assignments_sha256,
                "scenario_evidence": scenario_evidence,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    state["revalidations"] = [
        {
            "id": "RV-001",
            "worker_id": "independent-validator",
            "finding_ids": ["SRF-001"],
            "fix_assignment_ids": ["FX-001"],
            "fix_assignments_sha256": fix_assignments_sha256,
            "scenario_ids": scenario_ids,
            "snapshot_sha256": "a" * 64,
            "result": "pass",
            "evidence_refs": [manifest_ref.as_posix()],
            "evidence_sha256": {manifest_ref.as_posix(): manifest_sha256},
            "evidence_manifest_ref": manifest_ref.as_posix(),
            "review_cycle_id": review_cycle_id,
            "leader_verdict": "accepted",
        }
    ]
    return manifest_path


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
        "acceptance_finding_sha256": "",
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _review_runtime()
    _mock_workflow_stage(runtime, monkeypatch)
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
        "review_obligations": [
            {
                "id": "RO-DEMO-001",
                "kind": "acceptance",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "surface": "Demo journey",
                "required": True,
                "scenario_ids": ["SR-DEMO-001"],
            }
        ],
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
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {"in": ["Open Demo"], "out": [], "deferred": []},
                "acceptance_criteria": ["A human can open Demo."],
                "capability_operations": [],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )

    runtime.build_implementation_handoff(project_root, feature_dir, source_revision=7)
    handoff = json.loads(
        (feature_dir / "implementation-handoff.json").read_text(encoding="utf-8")
    )

    assert (
        handoff["human_acceptance_obligations"]
        == task_index["human_acceptance_obligations"]
    )
    assert (
        handoff["human_acceptance_scenarios"]
        == task_index["human_acceptance_scenarios"]
    )
    assert len(handoff["human_acceptance_contract_sha256"]) == 64


def test_modern_handoff_rejects_missing_human_acceptance_universe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _review_runtime()
    _mock_workflow_stage(runtime, monkeypatch)
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _review_runtime()
    workflow_state = _mock_workflow_stage(runtime, monkeypatch)
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    spec_path = feature_dir / "spec-contract.json"
    spec_path.write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "scope": {
                    "in": ["Use the changed journey"],
                    "out": [],
                    "deferred": [],
                },
                "acceptance_criteria": ["A human can use the changed journey."],
                "capability_operations": [],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": "spec-contract.json#/acceptance_criteria/0",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    plan_path = feature_dir / "plan-contract.json"
    plan_path.write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
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
        "review_obligations": [
            {
                "id": "RO-001",
                "kind": "acceptance",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "surface": "Changed journey",
                "required": True,
                "scenario_ids": ["SR-001"],
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

    runtime.build_implementation_handoff(project_root, feature_dir, source_revision=7)
    handoff = json.loads(
        (feature_dir / "implementation-handoff.json").read_text(encoding="utf-8")
    )

    assert handoff["acceptance_refs"] == task_index["acceptance_refs"]
    assert (
        handoff["task_index_sha256"]
        == hashlib.sha256(task_path.read_bytes()).hexdigest()
    )
    assert (
        handoff["plan_contract_sha256"]
        == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    )
    assert (
        handoff["spec_contract_sha256"]
        == hashlib.sha256(spec_path.read_bytes()).hexdigest()
    )

    spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_payload["acceptance_criteria"][0] = (
        "A human can use only a narrowed version of the changed journey."
    )
    spec_path.write_text(json.dumps(spec_payload), encoding="utf-8")

    with pytest.raises(runtime.ReviewRuntimeError, match="already frozen"):
        runtime.build_implementation_handoff(
            project_root, feature_dir, source_revision=7
        )

    workflow_state.update({"stage": "review", "status": "active"})
    (feature_dir / "implementation-handoff.json").unlink()
    with pytest.raises(runtime.ReviewRuntimeError, match="active Implement"):
        runtime.build_implementation_handoff(
            project_root, feature_dir, source_revision=7
        )


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
            "gap_classification": "implementation_gap",
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


def test_approved_review_rejects_changed_runtime_identity_evidence_bytes(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    identity_path = (
        feature_dir / state["reviewed_runtime_targets"][0]["identity_evidence_ref"]
    )
    identity_path.write_text('{"target": "different"}\n', encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("identity_evidence_sha256" in error for error in validation["errors"])


def test_build_runtime_target_binds_current_artifact_bytes(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    artifact_ref = "runtime-artifacts/demo-build.bin"
    artifact_path = feature_dir / artifact_ref
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"reviewed build\n")
    reviewed_snapshot = runtime.implementation_snapshot_sha256(
        project_root, feature_dir
    )
    _write_scenario_evidence(feature_dir, state, snapshot_sha256=reviewed_snapshot)
    _complete_leader_review(
        state,
        feature_dir=feature_dir,
        snapshot_sha256=reviewed_snapshot,
    )
    state["status"] = "approved"
    target = state["reviewed_runtime_targets"][0]
    target["mode"] = "build"
    target["artifact_ref"] = artifact_ref
    target["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    identity_path = feature_dir / target["identity_evidence_ref"]
    identity_path.write_text(
        json.dumps(runtime._review_runtime_identity_claim(target), indent=2) + "\n",
        encoding="utf-8",
    )
    target["identity_evidence_sha256"] = hashlib.sha256(
        identity_path.read_bytes()
    ).hexdigest()
    state["final"]["runtime_targets_sha256"] = runtime._review_runtime_targets_sha256(
        state["reviewed_runtime_targets"]
    )
    _targets, errors, fresh = runtime._validate_review_runtime_targets(
        state,
        feature_dir=feature_dir,
        expected_snapshot=reviewed_snapshot,
        status="approved",
    )

    assert errors == []
    assert fresh is True

    artifact_path.write_bytes(b"different build\n")
    _targets, errors, _fresh = runtime._validate_review_runtime_targets(
        state,
        feature_dir=feature_dir,
        expected_snapshot=reviewed_snapshot,
        status="approved",
    )

    assert any(
        "artifact_sha256 must bind current artifact bytes" in error for error in errors
    )

    target["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    identity_path.write_text(
        json.dumps(runtime._review_runtime_identity_claim(target), indent=2) + "\n",
        encoding="utf-8",
    )
    target["identity_evidence_sha256"] = hashlib.sha256(
        identity_path.read_bytes()
    ).hexdigest()

    assert (
        runtime.implementation_snapshot_sha256(project_root, feature_dir)
        != reviewed_snapshot
    )


def test_build_runtime_target_rejects_artifact_in_review_evidence(
    tmp_path: Path,
) -> None:
    runtime, _project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state = json.loads(
        runtime.review_state_path(feature_dir).read_text(encoding="utf-8")
    )
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    target = state["reviewed_runtime_targets"][0]
    artifact_ref = "review-evidence/audited-build.bin"
    artifact_path = feature_dir / artifact_ref
    artifact_path.write_bytes(b"self-signed build\n")
    target["mode"] = "build"
    target["artifact_ref"] = artifact_ref
    target["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    identity_path = feature_dir / target["identity_evidence_ref"]
    identity_path.write_text(
        json.dumps(runtime._review_runtime_identity_claim(target), indent=2) + "\n",
        encoding="utf-8",
    )
    target["identity_evidence_sha256"] = hashlib.sha256(
        identity_path.read_bytes()
    ).hexdigest()
    state["final"]["runtime_targets_sha256"] = runtime._review_runtime_targets_sha256(
        state["reviewed_runtime_targets"]
    )

    _targets, errors, _fresh = runtime._validate_review_runtime_targets(
        state,
        feature_dir=feature_dir,
        expected_snapshot="a" * 64,
        status="approved",
    )

    assert any("included in the implementation snapshot" in error for error in errors)


def test_approved_review_requires_one_unambiguous_target_per_human_scenario(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    duplicate = dict(state["reviewed_runtime_targets"][0])
    duplicate["id"] = "RRT-WEB-002"
    duplicate["instance_ref"] = "review://web/other"
    state["reviewed_runtime_targets"].append(duplicate)
    state["final"]["runtime_targets_sha256"] = runtime._review_runtime_targets_sha256(
        state["reviewed_runtime_targets"]
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any(
        "exactly one reviewed runtime target" in error for error in validation["errors"]
    )


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
        "specify-runtime",
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


def test_cycle_one_review_artifacts_are_root_confined_and_byte_bound(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"

    misplaced = next(
        evidence
        for scenario in state["scenarios"]
        if scenario["id"] == "SR-UI-001"
        for evidence in scenario["evidence"]
        if evidence["kind"] == "visual_capture"
    )
    misplaced_path = feature_dir / "review-results" / "misplaced-visual.json"
    misplaced_path.write_text("{}\n", encoding="utf-8")
    misplaced["path"] = "review-results/misplaced-visual.json"
    misplaced["artifact_sha256"] = hashlib.sha256(
        misplaced_path.read_bytes()
    ).hexdigest()

    evidence_path = feature_dir / state["scenarios"][0]["evidence"][0]["path"]
    evidence_path.write_text('{"changed": true}\n', encoding="utf-8")
    packet_path = feature_dir / state["review_assignments"][0]["packet_ref"]
    packet_path.write_text('{"changed": true}\n', encoding="utf-8")
    result_path = feature_dir / state["review_assignments"][0]["result_ref"]
    result_path.write_text('{"changed": true}\n', encoding="utf-8")
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any(
        "must belong to the current Review cycle" in error
        for error in validation["errors"]
    )
    assert any(
        "artifact_sha256 must bind current evidence bytes" in error
        for error in validation["errors"]
    )
    assert any(
        "packet_sha256 must bind current artifact bytes" in error
        for error in validation["errors"]
    )
    assert any(
        "result_sha256 must bind current artifact bytes" in error
        for error in validation["errors"]
    )


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
            "gap_classification": "implementation_gap",
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


def test_review_rejects_finding_only_revalidation_after_a_fix(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    _add_fix_revalidation_loop(feature_dir, state, full_matrix=False)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("full-matrix revalidation" in error for error in validation["errors"])


def test_review_rejects_full_matrix_revalidation_manifest_for_old_snapshot(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    _add_fix_revalidation_loop(
        feature_dir,
        state,
        full_matrix=True,
        manifest_snapshot_sha256="b" * 64,
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any(
        "manifest must bind the final reviewed snapshot" in error
        for error in validation["errors"]
    )


@pytest.mark.parametrize("artifact_kind", ("packet", "result"))
def test_cycle_one_fix_artifacts_are_byte_bound(
    tmp_path: Path,
    artifact_kind: str,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    _add_fix_revalidation_loop(feature_dir, state, full_matrix=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    artifact_path = feature_dir / state["fix_assignments"][0][f"{artifact_kind}_ref"]
    artifact_path.write_text('{"changed": true}\n', encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any(
        f"{artifact_kind}_sha256 must bind current artifact bytes" in error
        for error in validation["errors"]
    )


def test_cycle_one_revalidation_evidence_is_byte_bound(tmp_path: Path) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    manifest_path = _add_fix_revalidation_loop(feature_dir, state, full_matrix=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text('{"changed": true}\n', encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any(
        "evidence_sha256 must bind current cycle artifact bytes" in error
        for error in validation["errors"]
    )


def test_closeout_accepts_independent_fix_and_full_matrix_revalidation(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    _add_fix_revalidation_loop(feature_dir, state, full_matrix=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    closed = runtime.closeout_review(
        project_root, feature_dir, expected_revision=revision
    )

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
    reviewed_snapshot = runtime.implementation_snapshot_sha256(
        project_root, feature_dir
    )
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


def test_feature_epoch_review_requires_one_shared_delivery_epoch(
    tmp_path: Path,
) -> None:
    from specify_cli.validation_budget import (
        complete_validation_epoch,
        reserve_validation_epoch,
    )

    runtime = _review_runtime()
    project_root, feature_dir, revision = _feature_at_review(tmp_path)
    handoff_path = _write_implementation_handoff(feature_dir, revision)
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["validation_policy"] = {
        "mode": "feature_epochs",
        "max_epochs": 3,
        "budget_scope": "implement-review",
        "budget_ref": "implementation-review/validation-runs.json",
        "heavy_gate_owner": "leader",
    }
    handoff["task_ids"] = ["T001"]
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    runtime.prepare_review(
        project_root,
        feature_dir,
        expected_revision=revision,
    )
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    _complete_leader_review(state, feature_dir=feature_dir)
    state["status"] = "approved"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    missing = runtime.validate_review(project_root, feature_dir)
    assert missing["valid"] is False
    assert any("delivery epoch" in error for error in missing["errors"]), missing

    run = reserve_validation_epoch(
        project_root,
        feature_dir,
        stage="review",
        purpose="delivery",
        fingerprint="a" * 64,
        commands=["pytest -q", "npm run e2e"],
        covered_task_ids=["T001"],
    )
    complete_validation_epoch(
        project_root,
        feature_dir,
        run_id=run["run_id"],
        status="passed",
        evidence_refs=["review-evidence/final-validation.json"],
        summary="Integrated delivery validation passed.",
    )

    assert runtime.validate_review(project_root, feature_dir)["valid"] is True
