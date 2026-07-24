from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner
from tests.conftest import install_passing_workflow_gate

from specify_cli import app
from specify_cli import human_acceptance as human_acceptance_module
from specify_cli import review_runtime as review_runtime_module
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
    resolve_workflow_blocker,
    show_workflow,
    transition_workflow,
    workflow_runtime_path,
)


pytestmark = pytest.mark.usefixtures("unified_runtime_env")


ROOT = Path(__file__).resolve().parents[1]


def _attach_runtime_identity_evidence(
    feature: Path,
    target: dict[str, object],
    *,
    review_cycle: int = 1,
) -> None:
    identity_root = Path("review-evidence")
    if review_cycle >= 2:
        identity_root /= f"cycle-{review_cycle}"
    identity_ref = identity_root / f"{target['id']}.identity.json"
    identity_path = feature / identity_ref
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(
        json.dumps(
            review_runtime_module._review_runtime_identity_claim(target), indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    target["identity_evidence_ref"] = identity_ref.as_posix()
    target["identity_evidence_sha256"] = hashlib.sha256(
        identity_path.read_bytes()
    ).hexdigest()


def _feature(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / "001-demo"
    feature.mkdir(parents=True)
    install_passing_workflow_gate(project)
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo feature complete.\n", encoding="utf-8"
    )
    _install_approved_review(project, feature)
    return project, feature


def _install_approved_review(
    project: Path,
    feature: Path,
    *,
    source_revision: int = 1,
    include_optional_unbound_scenario: bool = False,
) -> None:
    task_index = {
        "version": 2,
        "status": "ready",
        "acceptance_refs": ["plan-contract.json#/acceptance_refs/0"],
        "official_entrypoints": [
            {
                "id": "demo-app",
                "command": "demo-app start",
                "ready_signal": "The home screen is visible.",
            }
        ],
        "system_review_scenarios": [
            {
                "id": "SR-DEMO-001",
                "kind": "interaction",
                "title": "Complete the reviewed Demo path",
                "required": True,
                "entrypoint_id": "demo-app",
                "preconditions": ["The Demo application is installed."],
                "actions": ["Start Demo.", "Open the Demo screen."],
                "expected_results": ["The Demo screen opens."],
                "required_evidence": ["runtime_diagnostics"],
            }
        ],
        "review_obligations": [
            {
                "id": "RO-DEMO-001",
                "kind": "user-journey",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "surface": "Demo user journey",
                "required": True,
                "scenario_ids": ["SR-DEMO-001"],
            }
        ],
        "human_acceptance_obligations": [
            {
                "id": "HAO-DEMO-001",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "change_kind": "new",
                "user_outcome": "The user can open the Demo experience.",
                "required": True,
                "scenario_ids": ["HA-DEMO-001"],
            }
        ],
        "human_acceptance_scenarios": [
            {
                "id": "HA-DEMO-001",
                "title": "Open the Demo experience",
                "user_value": "The user reaches the new Demo capability.",
                "actor": "human user",
                "required": True,
                "obligation_ids": ["HAO-DEMO-001"],
                "entrypoint_id": "demo-app",
                "review_scenario_ids": ["SR-DEMO-001"],
                "start_state": "The reviewed Demo home screen is visible.",
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
    if include_optional_unbound_scenario:
        task_index["system_review_scenarios"].append(
            {
                "id": "SR-OPTIONAL-001",
                "kind": "interaction",
                "title": "Inspect the optional diagnostics path",
                "required": False,
                "entrypoint_id": "demo-app",
                "preconditions": ["The Demo application is installed."],
                "actions": ["Open optional diagnostics."],
                "expected_results": ["Optional diagnostics can be inspected."],
                "required_evidence": ["runtime_diagnostics"],
            }
        )
        task_index["review_obligations"].append(
            {
                "id": "RO-OPTIONAL-001",
                "kind": "user-journey",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "surface": "Optional diagnostics",
                "required": False,
                "scenario_ids": ["SR-OPTIONAL-001"],
            }
        )
        task_index["human_acceptance_obligations"].append(
            {
                "id": "HAO-OPTIONAL-001",
                "source_ref": "plan-contract.json#/acceptance_refs/0",
                "change_kind": "changed",
                "user_outcome": "A human may inspect optional diagnostics.",
                "required": False,
                "scenario_ids": ["HA-OPTIONAL-001"],
            }
        )
        task_index["human_acceptance_scenarios"].append(
            {
                "id": "HA-OPTIONAL-001",
                "title": "Inspect optional diagnostics",
                "user_value": "Optional diagnostics are available for inspection.",
                "actor": "human user",
                "required": False,
                "obligation_ids": ["HAO-OPTIONAL-001"],
                "entrypoint_id": "demo-app",
                "review_scenario_ids": ["SR-OPTIONAL-001"],
                "start_state": "The reviewed Demo home screen is visible.",
                "steps": [
                    {
                        "id": "HA-OPTIONAL-001-S01",
                        "action": "Open optional diagnostics.",
                        "expected_result": "The diagnostics view opens.",
                        "evidence_requirement": "Human observation.",
                        "risk": "low",
                    }
                ],
            }
        )
    (feature / "task-index.json").write_text(
        json.dumps(task_index, indent=2) + "\n", encoding="utf-8"
    )
    (feature / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["A human can open the Demo experience."],
                    "out": [],
                    "deferred": [],
                },
                "acceptance_criteria": ["A human can open the Demo experience."],
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
    (feature / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            }
        ),
        encoding="utf-8",
    )
    review_runtime_module.build_implementation_handoff(
        project, feature, source_revision=source_revision
    )
    handoff_path = feature / "implementation-handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    (
        fingerprint,
        entrypoints,
        scenarios,
        obligations,
        human_obligations,
        human_scenarios,
        _contract_digest,
    ) = review_runtime_module._normalized_handoff(
        handoff, expected_revision=source_revision
    )
    review_cycle_id = review_runtime_module._review_cycle_id(
        workflow_revision=source_revision,
        handoff_sha256=hashlib.sha256(handoff_path.read_bytes()).hexdigest(),
        review_cycle=1,
        previous_review_state_sha256="",
        acceptance_finding_id="",
    )

    for scenario in scenarios:
        if scenario.get("required") is False:
            scenario["result"] = "pending"
            scenario["evidence"] = []
            continue
        scenario["result"] = "pass"
        scenario["evidence"] = []
        for kind in scenario["required_evidence"]:
            relative = Path("review-evidence") / scenario["id"] / f"{kind}.json"
            evidence_path = feature / relative
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text("{}\n", encoding="utf-8")
            scenario["evidence"].append(
                {
                    "kind": kind,
                    "path": relative.as_posix(),
                    "evidence_scope": "integrated",
                    "snapshot_sha256": fingerprint,
                    "review_cycle_id": review_cycle_id,
                    "artifact_sha256": hashlib.sha256(
                        evidence_path.read_bytes()
                    ).hexdigest(),
                }
            )
    for obligation in obligations:
        obligation["status"] = "covered"
        obligation["review_assignment_ids"] = ["RA-DEMO-001"]
    results_dir = feature / "review-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for name in ("RA-DEMO-001.packet.json", "RA-DEMO-001.json"):
        (results_dir / name).write_text("{}\n", encoding="utf-8")
    summary_path = feature / "implementation-summary.md"
    handoff_sha256 = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
    reviewed_runtime_targets = [
        {
            "id": "RRT-DEMO-001",
            "mode": "source",
            "status": "ready",
            "entrypoint_id": "demo-app",
            "environment_ref": "isolated Review environment",
            "instance_ref": "demo-app://local/home",
            "configuration_ref": "reviewed default configuration",
            "reviewed_snapshot_sha256": fingerprint,
            "artifact_ref": None,
            "artifact_sha256": None,
            "deployment_id": None,
            "observed_version": None,
            "test_data_refs": ["isolated demo fixture"],
            "ready_evidence_refs": [
                evidence["path"]
                for scenario in scenarios
                for evidence in scenario["evidence"]
                if evidence["kind"] == "runtime_diagnostics"
            ],
            "review_scenario_ids": [
                scenario["id"]
                for scenario in scenarios
                if scenario.get("required") is True
            ],
        }
    ]
    _attach_runtime_identity_evidence(
        feature,
        reviewed_runtime_targets[0],
        review_cycle=1,
    )
    review_state = {
        "version": 2,
        "schema_ref": ".specify/templates/review-state-schema.json",
        "status": "approved",
        "source": {
            "workflow_revision": source_revision,
            "implementation_fingerprint": fingerprint,
            "implementation_handoff_sha256": handoff_sha256,
            "review_cycle": 1,
            "review_cycle_id": review_cycle_id,
            "previous_review_state_sha256": "",
            "acceptance_finding_id": "",
            "acceptance_finding_sha256": "",
        },
        "entrypoints": entrypoints,
        "scenarios": scenarios,
        "obligations": obligations,
        "human_acceptance_obligations": human_obligations,
        "human_acceptance_scenarios": human_scenarios,
        "reviewed_runtime_targets": reviewed_runtime_targets,
        "review_assignments": [
            {
                "id": "RA-DEMO-001",
                "kind": "coverage_audit",
                "worker_id": "coverage-auditor",
                "obligation_ids": [item["id"] for item in obligations],
                "scenario_ids": [item["id"] for item in scenarios],
                "read_only": True,
                "packet_ref": "review-results/RA-DEMO-001.packet.json",
                "result_ref": "review-results/RA-DEMO-001.json",
                "packet_sha256": hashlib.sha256(
                    (results_dir / "RA-DEMO-001.packet.json").read_bytes()
                ).hexdigest(),
                "result_sha256": hashlib.sha256(
                    (results_dir / "RA-DEMO-001.json").read_bytes()
                ).hexdigest(),
                "review_cycle_id": review_cycle_id,
                "observed_snapshot_sha256": fingerprint,
                "status": "accepted",
                "leader_verdict": "accepted",
            }
        ],
        "fix_assignments": [],
        "revalidations": [],
        "coverage": {
            "discovery_complete": True,
            "blind_audit_complete": True,
            "uncovered_obligation_ids": [],
            "uncovered_surface_ids": [],
            "final_gap_scan": "pass",
        },
        "leader": {
            "strategy": "leader-plus-subagents",
            "review_plan_complete": True,
            "all_review_results_joined": True,
            "fix_plan_complete": True,
            "all_fix_results_joined": True,
            "final_revalidation_complete": True,
            "verdict": "pass",
        },
        "rounds": [],
        "findings": [],
        "repair_cycles": [],
        "validation": {
            "startup": "pass",
            "real_entrypoint_journeys": "pass",
            "regression": "pass",
            "ui_verification": "pass",
        },
        "cursor": {"scenario_id": None, "next_action": None},
        "blocker": None,
        "final": {
            "verdict": "pass",
            "coverage_verdict": "pass",
            "repair_verdict": "pass",
            "integration_verdict": "pass",
            "all_packets_joined": True,
            "reviewed_snapshot_sha256": fingerprint,
            "implementation_summary_sha256": hashlib.sha256(
                summary_path.read_bytes()
            ).hexdigest(),
            "runtime_targets_sha256": review_runtime_module._review_runtime_targets_sha256(
                reviewed_runtime_targets
            ),
        },
    }
    (feature / "review-state.json").write_text(
        json.dumps(review_state, indent=2) + "\n", encoding="utf-8"
    )


def _approve_current_acceptance_repair_review(
    project: Path, feature: Path, *, revision: int
) -> None:
    review_runtime_module.prepare_review(project, feature, expected_revision=revision)
    source_path = project / "src" / "demo-repair.txt"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        f"repaired in review revision {revision}\n", encoding="utf-8"
    )
    snapshot = review_runtime_module.implementation_snapshot_sha256(project, feature)
    state_path = feature / "review-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for scenario in state["scenarios"]:
        scenario["result"] = "pass"
        scenario["evidence"] = []
        for kind in scenario["required_evidence"]:
            relative = (
                Path("review-evidence")
                / f"cycle-{state['source']['review_cycle']}"
                / scenario["id"]
                / f"{kind}.json"
            )
            evidence_path = feature / relative
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text("{}\n", encoding="utf-8")
            scenario["evidence"].append(
                {
                    "kind": kind,
                    "path": relative.as_posix(),
                    "evidence_scope": "integrated",
                    "snapshot_sha256": snapshot,
                    "review_cycle_id": state["source"]["review_cycle_id"],
                    "artifact_sha256": hashlib.sha256(
                        evidence_path.read_bytes()
                    ).hexdigest(),
                }
            )
    obligation_ids = [item["id"] for item in state["obligations"]]
    scenario_ids = [item["id"] for item in state["scenarios"]]
    for obligation in state["obligations"]:
        obligation["status"] = "covered"
        obligation["review_assignment_ids"] = ["RA-REPAIR-COVERAGE"]
    results_dir = (
        feature / "review-results" / f"cycle-{state['source']['review_cycle']}"
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    artifact_names = (
        "RA-REPAIR-COVERAGE.packet.json",
        "RA-REPAIR-COVERAGE.json",
        "RA-REPAIR-DIAG.packet.json",
        "RA-REPAIR-DIAG.json",
        "FX-REPAIR.packet.json",
        "FX-REPAIR.json",
        "RV-REPAIR.json",
    )
    for name in artifact_names:
        (results_dir / name).write_text("{}\n", encoding="utf-8")
    result_prefix = results_dir.relative_to(feature).as_posix()
    state["review_assignments"] = [
        {
            "id": "RA-REPAIR-COVERAGE",
            "kind": "coverage_audit",
            "worker_id": "repair-coverage-auditor",
            "obligation_ids": obligation_ids,
            "scenario_ids": scenario_ids,
            "read_only": True,
            "packet_ref": f"{result_prefix}/RA-REPAIR-COVERAGE.packet.json",
            "result_ref": f"{result_prefix}/RA-REPAIR-COVERAGE.json",
            "packet_sha256": hashlib.sha256(
                (results_dir / "RA-REPAIR-COVERAGE.packet.json").read_bytes()
            ).hexdigest(),
            "result_sha256": hashlib.sha256(
                (results_dir / "RA-REPAIR-COVERAGE.json").read_bytes()
            ).hexdigest(),
            "review_cycle_id": state["source"]["review_cycle_id"],
            "observed_snapshot_sha256": snapshot,
            "status": "accepted",
            "leader_verdict": "accepted",
        },
        {
            "id": "RA-REPAIR-DIAG",
            "kind": "scenario_review",
            "worker_id": "repair-diagnostician",
            "obligation_ids": obligation_ids,
            "scenario_ids": scenario_ids,
            "read_only": True,
            "packet_ref": f"{result_prefix}/RA-REPAIR-DIAG.packet.json",
            "result_ref": f"{result_prefix}/RA-REPAIR-DIAG.json",
            "packet_sha256": hashlib.sha256(
                (results_dir / "RA-REPAIR-DIAG.packet.json").read_bytes()
            ).hexdigest(),
            "result_sha256": hashlib.sha256(
                (results_dir / "RA-REPAIR-DIAG.json").read_bytes()
            ).hexdigest(),
            "review_cycle_id": state["source"]["review_cycle_id"],
            "observed_snapshot_sha256": snapshot,
            "status": "accepted",
            "leader_verdict": "accepted",
        },
    ]
    finding = state["findings"][0]
    finding["discovered_by_review_assignment_id"] = "RA-REPAIR-DIAG"
    finding["status"] = "verified"
    finding["fix_assignment_id"] = "FX-REPAIR"
    finding["revalidation_ids"] = ["RV-REPAIR"]
    state["fix_assignments"] = [
        {
            "id": "FX-REPAIR",
            "finding_ids": [finding["id"]],
            "worker_id": "repair-fixer",
            "allowed_write_paths": ["src"],
            "changed_paths": ["src/demo-repair.txt"],
            "packet_ref": f"{result_prefix}/FX-REPAIR.packet.json",
            "result_ref": f"{result_prefix}/FX-REPAIR.json",
            "packet_sha256": hashlib.sha256(
                (results_dir / "FX-REPAIR.packet.json").read_bytes()
            ).hexdigest(),
            "result_sha256": hashlib.sha256(
                (results_dir / "FX-REPAIR.json").read_bytes()
            ).hexdigest(),
            "review_cycle_id": state["source"]["review_cycle_id"],
            "status": "accepted",
            "leader_verdict": "accepted",
        }
    ]
    fix_assignments_sha256 = review_runtime_module._accepted_fix_assignments_sha256(
        {item["id"]: item for item in state["fix_assignments"]}
    )
    scenario_evidence = sorted(
        [
            {
                "scenario_id": scenario["id"],
                "kind": evidence["kind"],
                "path": evidence["path"],
                "artifact_sha256": evidence["artifact_sha256"],
            }
            for scenario in state["scenarios"]
            if scenario.get("required", True)
            for evidence in scenario["evidence"]
            if evidence["kind"] in scenario["required_evidence"]
        ],
        key=lambda item: (item["scenario_id"], item["kind"], item["path"]),
    )
    manifest_ref = f"{result_prefix}/RV-REPAIR.manifest.json"
    manifest_path = feature / manifest_ref
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "revalidation_id": "RV-REPAIR",
                "review_cycle_id": state["source"]["review_cycle_id"],
                "snapshot_sha256": snapshot,
                "fix_assignments_sha256": fix_assignments_sha256,
                "scenario_evidence": scenario_evidence,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    state["revalidations"] = [
        {
            "id": "RV-REPAIR",
            "worker_id": "repair-revalidator",
            "finding_ids": [finding["id"]],
            "fix_assignment_ids": ["FX-REPAIR"],
            "fix_assignments_sha256": fix_assignments_sha256,
            "scenario_ids": scenario_ids,
            "snapshot_sha256": snapshot,
            "result": "pass",
            "evidence_refs": [manifest_ref],
            "evidence_sha256": {
                manifest_ref: hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            },
            "evidence_manifest_ref": manifest_ref,
            "review_cycle_id": state["source"]["review_cycle_id"],
            "leader_verdict": "accepted",
        }
    ]
    state["coverage"] = {
        "discovery_complete": True,
        "blind_audit_complete": True,
        "uncovered_obligation_ids": [],
        "uncovered_surface_ids": [],
        "final_gap_scan": "pass",
    }
    state["leader"] = {
        "strategy": "leader-plus-subagents",
        "review_plan_complete": True,
        "all_review_results_joined": True,
        "fix_plan_complete": True,
        "all_fix_results_joined": True,
        "final_revalidation_complete": True,
        "verdict": "pass",
    }
    ready_refs = [
        evidence["path"]
        for scenario in state["scenarios"]
        for evidence in scenario["evidence"]
        if evidence["kind"] == "runtime_diagnostics"
    ]
    state["reviewed_runtime_targets"] = [
        {
            "id": "RRT-DEMO-001",
            "mode": "source",
            "status": "ready",
            "entrypoint_id": "demo-app",
            "environment_ref": "isolated repaired Review environment",
            "instance_ref": "demo-app://local/home",
            "configuration_ref": "reviewed repaired configuration",
            "reviewed_snapshot_sha256": snapshot,
            "artifact_ref": None,
            "artifact_sha256": None,
            "deployment_id": None,
            "observed_version": None,
            "test_data_refs": ["isolated repaired demo fixture"],
            "ready_evidence_refs": ready_refs,
            "review_scenario_ids": scenario_ids,
        }
    ]
    _attach_runtime_identity_evidence(
        feature,
        state["reviewed_runtime_targets"][0],
        review_cycle=state["source"]["review_cycle"],
    )
    state["status"] = "approved"
    state["final"] = {
        "verdict": "pass",
        "coverage_verdict": "pass",
        "repair_verdict": "pass",
        "integration_verdict": "pass",
        "all_packets_joined": True,
        "reviewed_snapshot_sha256": snapshot,
        "implementation_summary_sha256": hashlib.sha256(
            (feature / "implementation-summary.md").read_bytes()
        ).hexdigest(),
        "runtime_targets_sha256": review_runtime_module._review_runtime_targets_sha256(
            state["reviewed_runtime_targets"]
        ),
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    review_runtime_module.closeout_review(project, feature, expected_revision=revision)


def _complete_then_transition(
    feature: Path,
    *,
    target_stage: str,
    revision: int,
) -> dict[str, object]:
    if target_stage == "review":
        # Implement closeout freezes the handoff for the revision that Review
        # will receive.  Build it while Implement is still the active owner;
        # Review may consume this state but must never recreate it.
        _install_approved_review(
            feature.parents[2],
            feature,
            source_revision=revision + 2,
        )
    completed = complete_workflow_stage(feature, expected_revision=revision)
    transitioned = transition_workflow(
        feature,
        target_stage=target_stage,
        expected_revision=completed["data"]["revision"],
    )
    return transitioned


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
    for target in state["runtime_targets"]:
        target["acceptance_status"] = "ready"
        target["acceptance_ready_evidence"] = ["agent: Demo home screen ready"]
        target["agent_actions"] = [
            "Started the official Demo entrypoint and prepared isolated data."
        ]
    for scenario in state["scenarios"]:
        scenario["verdict"] = "pass"
        for step in scenario["steps"]:
            step["result"] = "pass"
            step["observed_result"] = "The Demo screen opened."
            step["evidence"] = [
                {
                    "actor": "human",
                    "source": "human-reply",
                    "statement": "seen",
                    "confirmation_id": step["confirmation_id"],
                    "runtime_target_id": scenario["runtime_target_id"],
                    "reviewed_snapshot_sha256": state["source"][
                        "reviewed_snapshot_sha256"
                    ],
                }
            ]
    state["acceptance_universe"]["uncovered_obligation_ids"] = []
    state["acceptance_universe"]["verdict"] = "pass"
    state["cursor"] = {"scenario_id": None, "step_id": None}
    state["overall"] = {
        "verdict": "pass",
        "summary": "The human completed the required demo scenario.",
        "next_command": "sp-integrate or spx-integrate",
        "human_decision": "accept",
        "decision_confirmation_id": state["overall"]["decision_confirmation_id"],
        "decision_evidence": [
            {
                "actor": "human",
                "source": "human-reply",
                "statement": "accepted the completed Demo journey",
                "confirmation_id": state["overall"]["decision_confirmation_id"],
                "runtime_target_id": "all-reviewed-targets",
                "reviewed_snapshot_sha256": state["source"]["reviewed_snapshot_sha256"],
            }
        ],
    }
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return state


def _rejected_state(state_path: Path, *, route: str = "spx-review") -> None:
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
            "scenario_id": "HA-DEMO-001",
            "step_id": "HA-DEMO-001-S01",
            "classification": (
                "environment-or-access"
                if route == "human-action"
                else "observed-mismatch"
            ),
            "route": route,
            "expected": "The Demo screen opens.",
            "observed": "The Demo screen remained closed.",
            "evidence": ["human: visible failure"],
            "status": "open",
        }
    ]
    state["acceptance_universe"]["uncovered_obligation_ids"] = ["HAO-DEMO-001"]
    state["acceptance_universe"]["verdict"] = "fail"
    state["cursor"] = {
        "scenario_id": "HA-DEMO-001",
        "step_id": "HA-DEMO-001-S01",
    }
    state["overall"] = {
        "verdict": "fail",
        "summary": "The required demo scenario failed.",
        "next_command": route,
        "human_decision": "reject",
        "decision_confirmation_id": state["overall"]["decision_confirmation_id"],
        "decision_evidence": [
            {
                "actor": "human",
                "source": "human-reply",
                "statement": "the Demo screen remained closed",
                "confirmation_id": state["overall"]["decision_confirmation_id"],
                "runtime_target_id": "all-reviewed-targets",
                "reviewed_snapshot_sha256": state["source"]["reviewed_snapshot_sha256"],
            }
        ],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _rejected_acceptance_at_active_accept(
    project: Path,
    feature: Path,
    *,
    route: str = "spx-review",
) -> int:
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
    _rejected_state(feature / "human-acceptance.json", route=route)
    return int(revision)


def _accepted_acceptance_at_active_accept(project: Path, feature: Path) -> int:
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
    _accepted_state(feature / "human-acceptance.json")
    return int(revision)


def test_template_matches_runtime_empty_state() -> None:
    template = json.loads(
        (ROOT / "templates" / "human-acceptance-state-template.json").read_text(
            encoding="utf-8"
        )
    )

    assert template == new_human_acceptance_state()


def test_human_acceptance_v2_has_frozen_scope_runtime_identity_and_human_decision() -> (
    None
):
    state = new_human_acceptance_state()

    assert state["version"] == 2
    assert "implementation_handoff_sha256" in state["source"]
    assert "review_state_sha256" in state["source"]
    assert "reviewed_snapshot_sha256" in state["source"]
    assert "acceptance_universe_sha256" in state["source"]
    assert state["acceptance_universe"] == {
        "obligations": [],
        "uncovered_obligation_ids": [],
        "verdict": "pending",
    }
    assert state["runtime_targets"] == []
    assert state["repair_resume"] is None
    assert state["repair_history"] == []
    assert state["overall"]["human_decision"] == "pending"
    assert state["overall"]["decision_evidence"] == []


def test_optional_pending_acceptance_scenario_does_not_require_runtime_target(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / "001-demo"
    feature.mkdir(parents=True)
    install_passing_workflow_gate(project)
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo feature complete.\n",
        encoding="utf-8",
    )
    _install_approved_review(
        project,
        feature,
        include_optional_unbound_scenario=True,
    )
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "ready"
    state["orientation"] = {
        "outcome": "The user can complete the demo flow.",
        "why_it_matters": "The primary path is ready for human review.",
        "user_visible_changes": ["A new Demo action is available."],
        "not_in_scope": ["Optional diagnostics are not required."],
        "prerequisites": ["Open the demo workspace."],
        "start_here": "Open the application and select Demo.",
    }
    for target in state["runtime_targets"]:
        target["acceptance_status"] = "ready"
        target["acceptance_ready_evidence"] = ["agent: Demo home screen ready"]
        target["agent_actions"] = ["Started the official Demo entrypoint."]
    optional = next(
        scenario
        for scenario in state["scenarios"]
        if scenario["id"] == "HA-OPTIONAL-001"
    )
    assert optional["required"] is False
    assert optional["runtime_target_id"] is None
    assert optional["verdict"] == "pending"
    state_path.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )

    validation = validate_human_acceptance(project, feature)

    assert validation["valid"] is True, validation["errors"]


def test_acceptance_failure_routes_are_review_first_only() -> None:
    assert human_acceptance_module.FINDING_ROUTES == {
        "sp-review",
        "spx-review",
        "human-action",
    }
    assert human_acceptance_module.ACCEPTANCE_REPAIR_TARGETS == {
        "sp-review": "review",
        "spx-review": "review",
    }


@pytest.mark.parametrize(
    "legacy_route",
    (
        "sp-implement",
        "sp-debug",
        "sp-clarify",
        "sp-specify",
        "spx-implement",
        "spx-debug",
        "spx-clarify",
        "spx-specify",
    ),
)
def test_legacy_direct_acceptance_repair_routes_are_rejected(
    tmp_path: Path, legacy_route: str
) -> None:
    project, feature = _feature(tmp_path)

    with pytest.raises(ValueError, match="route must be one of"):
        route_human_acceptance_repair(
            project,
            feature,
            route=legacy_route,
            finding_id="HAF-001",
            expected_revision=1,
            evidence=["human: observed mismatch"],
        )


def test_human_acceptance_schema_is_valid_and_accepts_the_draft_template() -> None:
    schema = json.loads(
        (ROOT / "templates" / "human-acceptance-state-schema.json").read_text(
            encoding="utf-8"
        )
    )
    template = new_human_acceptance_state()

    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(template)) == []


def test_review_finding_cannot_be_marked_resolved_without_a_completed_review_cycle(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["findings"] = [
        {
            "id": "HAF-001",
            "scenario_id": "HA-DEMO-001",
            "step_id": "HA-DEMO-001-S01",
            "classification": "observed-mismatch",
            "route": "spx-review",
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
    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert any(
        "resolved Review finding requires a completed route-repair cycle" in error
        for error in validation["errors"]
    )


def test_fabricated_repair_history_cannot_resolve_a_review_finding(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    finding = {
        "id": "HAF-001",
        "scenario_id": "HA-DEMO-001",
        "step_id": "HA-DEMO-001-S01",
        "classification": "observed-mismatch",
        "route": "spx-review",
        "expected": "The Demo screen opens.",
        "observed": "The Demo screen opens after an unproven edit.",
        "evidence": ["human: claimed repair"],
        "status": "resolved",
    }
    state["findings"] = [finding]
    review_state = json.loads(
        (feature / "review-state.json").read_text(encoding="utf-8")
    )
    fake_repair = {
        "finding_id": finding["id"],
        "finding_contract_sha256": human_acceptance_module._acceptance_finding_sha256(
            finding
        ),
        "previous_review_state_sha256": state["source"]["review_state_sha256"],
        "new_review_state_sha256": state["source"]["review_state_sha256"],
        "review_cycle_id": review_state["source"]["review_cycle_id"],
        "affected_obligation_ids": ["HAO-DEMO-001"],
        "affected_scenario_ids": ["HA-DEMO-001"],
        "preserved_scenario_ids": [],
        "scenario_id": finding["scenario_id"],
        "step_id": finding["step_id"],
    }
    state["repair_resume"] = fake_repair
    state["repair_history"] = [fake_repair]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert any(
        "latest repair history entry must match the current Review repair source"
        in error
        for error in validation["errors"]
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
    _rejected_state(feature / "human-acceptance.json", route="spx-review")

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
    assert validation["finding_routes"][0]["route"] == "spx-review"
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


def test_prepare_requires_a_fresh_approved_review(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    (feature / "review-state.json").unlink()

    prepared = prepare_human_acceptance(project, feature)

    assert prepared["status"] == "blocked"
    assert prepared["error_code"] == "approved-review-required"
    assert not (feature / "human-acceptance.json").exists()


def test_prepare_materializes_the_frozen_human_acceptance_universe(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)

    prepared = prepare_human_acceptance(project, feature)
    state = json.loads((feature / "human-acceptance.json").read_text(encoding="utf-8"))

    assert prepared["required_obligations"] == 1
    assert prepared["required_scenarios"] == 1
    assert [item["id"] for item in state["acceptance_universe"]["obligations"]] == [
        "HAO-DEMO-001"
    ]
    assert [item["id"] for item in state["scenarios"]] == ["HA-DEMO-001"]
    assert state["acceptance_universe"]["uncovered_obligation_ids"] == ["HAO-DEMO-001"]
    assert [target["id"] for target in state["runtime_targets"]] == ["RRT-DEMO-001"]
    assert (
        state["runtime_targets"][0]["reviewed_snapshot_sha256"]
        == state["source"]["reviewed_snapshot_sha256"]
    )
    assert state["runtime_targets"][0]["acceptance_status"] == "pending"


@pytest.mark.parametrize(
    "mutate",
    (
        lambda state: state["acceptance_universe"]["obligations"].clear(),
        lambda state: state["scenarios"].clear(),
        lambda state: state["scenarios"][0].update({"required": False}),
        lambda state: state["scenarios"][0].update({"obligation_ids": []}),
    ),
)
def test_acceptance_closeout_rejects_universe_deletion_or_downgrade(
    tmp_path: Path, mutate
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    mutate(state)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert any(
        "human acceptance universe" in error.lower() or "obligation_ids" in error
        for error in validation["errors"]
    )


@pytest.mark.parametrize(
    "mutate, expected",
    (
        (
            lambda state: state.update({"runtime_targets": []}),
            "ready runtime target",
        ),
        (
            lambda state: state["scenarios"][0]["steps"][0].update(
                {"evidence": ["agent: automated check passed"]}
            ),
            "structured human confirmation",
        ),
        (
            lambda state: state["overall"].update(
                {"human_decision": "pending", "decision_evidence": []}
            ),
            "explicit human acceptance decision",
        ),
    ),
)
def test_acceptance_closeout_requires_correct_instance_and_human_authority(
    tmp_path: Path, mutate, expected: str
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    mutate(state)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert any(expected in error for error in validation["errors"])


def test_acceptance_rejects_runtime_identity_not_approved_by_review(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["runtime_targets"][0]["instance_ref"] = "deployment://old-unreviewed"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert any(
        "approved Review runtime target" in error for error in validation["errors"]
    )


def test_review_rejects_self_resigned_handoff_that_downgrades_live_task_scope(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    handoff_path = feature / "implementation-handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["human_acceptance_obligations"][0]["required"] = False
    handoff["human_acceptance_scenarios"][0]["required"] = False
    handoff["human_acceptance_contract_sha256"] = hashlib.sha256(
        json.dumps(
            {
                "human_acceptance_obligations": handoff["human_acceptance_obligations"],
                "human_acceptance_scenarios": handoff["human_acceptance_scenarios"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    state_path = feature / "review-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["human_acceptance_obligations"][0]["required"] = False
    state["human_acceptance_scenarios"][0]["required"] = False
    state["source"]["implementation_handoff_sha256"] = hashlib.sha256(
        handoff_path.read_bytes()
    ).hexdigest()
    state["source"]["review_cycle_id"] = review_runtime_module._review_cycle_id(
        workflow_revision=state["source"]["workflow_revision"],
        handoff_sha256=state["source"]["implementation_handoff_sha256"],
        review_cycle=state["source"]["review_cycle"],
        previous_review_state_sha256="",
        acceptance_finding_id="",
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = review_runtime_module.validate_review(project, feature)

    assert validation["valid"] is False
    assert any("live Spec/Plan/Tasks" in error for error in validation["errors"])


def test_acceptance_target_selection_uses_linked_review_scenarios() -> None:
    scenario = {
        "id": "HA-A",
        "entrypoint_id": "web",
        "review_scenario_ids": ["SR-A"],
    }
    targets = [
        {
            "id": "RRT-A",
            "entrypoint_id": "web",
            "review_scenario_ids": ["SR-A"],
        },
        {
            "id": "RRT-B",
            "entrypoint_id": "web",
            "review_scenario_ids": ["SR-B"],
        },
    ]

    assert (
        human_acceptance_module._runtime_target_id_for_scenario(scenario, targets)
        == "RRT-A"
    )


def test_acceptance_rejects_string_prefixed_human_evidence(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["scenarios"][0]["steps"][0]["evidence"] = ["human: fabricated"]
    state["overall"]["decision_evidence"] = ["human: fabricated"]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = validate_human_acceptance(project, feature, require_accepted=True)

    assert validation["valid"] is False
    assert any(
        "structured human confirmation" in error for error in validation["errors"]
    )


def test_rejected_acceptance_routes_through_review_and_returns_to_accept(
    tmp_path: Path,
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
    _rejected_state(state_path)

    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )

    assert routed["status"] == "ok"
    assert routed["data"]["stage"] == "review"
    assert routed["data"]["repair_route"] == "spx-review"
    reopened = json.loads(state_path.read_text(encoding="utf-8"))
    assert reopened["status"] == "draft"
    assert reopened["source"]["prepared_from_sha256"] == ""
    assert reopened["cursor"] == {
        "scenario_id": "HA-DEMO-001",
        "step_id": "HA-DEMO-001-S01",
    }
    assert reopened["scenarios"][0]["verdict"] == "pending"
    assert reopened["scenarios"][0]["steps"][0]["result"] == "pending"
    assert reopened["findings"][0]["status"] == "open"

    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo repair complete.\n", encoding="utf-8"
    )
    _approve_current_acceptance_repair_review(
        project,
        feature,
        revision=routed["data"]["revision"],
    )
    returned = _complete_then_transition(
        feature,
        target_stage="accept",
        revision=routed["data"]["revision"],
    )
    prepared = prepare_human_acceptance(project, feature)
    assert prepared["status"] == "draft"
    assert returned["data"]["stage"] == "accept"
    assert show_workflow(feature)["data"]["status"] == "active"
    repaired = json.loads(state_path.read_text(encoding="utf-8"))
    assert repaired["findings"][0]["status"] == "resolved"
    assert len(repaired["repair_history"]) == 1
    assert repaired["repair_history"][0] == repaired["repair_resume"]
    assert (
        repaired["repair_history"][0]["new_review_state_sha256"]
        == repaired["source"]["review_state_sha256"]
    )

    _accepted_state(state_path)
    accepted = validate_human_acceptance(project, feature, require_accepted=True)
    assert accepted["valid"] is True, "\n".join(accepted["errors"])


def test_acceptance_repair_prepares_a_new_review_cycle_from_the_old_handoff(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    previous_review_sha256 = hashlib.sha256(
        (feature / "review-state.json").read_bytes()
    ).hexdigest()

    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )
    prepared = review_runtime_module.prepare_review(
        project,
        feature,
        expected_revision=routed["data"]["revision"],
    )

    state = prepared["data"]
    assert state["status"] == "reviewing"
    assert state["source"]["workflow_revision"] == routed["data"]["revision"]
    assert state["source"]["review_cycle"] == 2
    assert state["source"]["previous_review_state_sha256"] == previous_review_sha256
    assert state["source"]["acceptance_finding_id"] == "HAF-001"
    assert len(state["source"]["review_cycle_id"]) == 64
    assert any(
        finding.get("origin_acceptance_finding_id") == "HAF-001"
        and finding.get("status") == "open"
        for finding in state["findings"]
    )


def test_acceptance_repair_cannot_reapprove_by_editing_the_old_review_hash(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )
    state_path = feature / "review-state.json"
    stale_approval = json.loads(state_path.read_text(encoding="utf-8"))
    stale_approval["source"]["workflow_revision"] = routed["data"]["revision"]
    state_path.write_text(json.dumps(stale_approval, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(
        review_runtime_module.ReviewRuntimeError, match="acceptance repair cycle"
    ):
        review_runtime_module.closeout_review(
            project,
            feature,
            expected_revision=routed["data"]["revision"],
        )


def test_acceptance_repair_review_rejects_evidence_reused_outside_new_cycle(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo repair complete.\n", encoding="utf-8"
    )
    _approve_current_acceptance_repair_review(
        project,
        feature,
        revision=routed["data"]["revision"],
    )
    state_path = feature / "review-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    evidence = state["scenarios"][0]["evidence"][0]
    stale_relative = (
        Path("review-evidence")
        / f"cycle-{state['source']['review_cycle']}"
        / ".."
        / "reused"
        / "old.json"
    )
    stale_path = feature / stale_relative
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text("{}\n", encoding="utf-8")
    evidence["path"] = stale_relative.as_posix()
    state["reviewed_runtime_targets"][0]["ready_evidence_refs"] = [
        stale_relative.as_posix()
    ]
    state["final"]["runtime_targets_sha256"] = (
        review_runtime_module._review_runtime_targets_sha256(
            state["reviewed_runtime_targets"]
        )
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = review_runtime_module.validate_review(project, feature)

    assert validation["valid"] is False
    assert any("current Review cycle" in error for error in validation["errors"])


def test_acceptance_repair_review_rejects_routed_finding_content_drift(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )
    review_runtime_module.prepare_review(
        project,
        feature,
        expected_revision=routed["data"]["revision"],
    )
    acceptance_path = feature / "human-acceptance.json"
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    acceptance["findings"][0]["observed"] = "A different unreviewed failure."
    acceptance_path.write_text(
        json.dumps(acceptance, indent=2) + "\n", encoding="utf-8"
    )

    validation = review_runtime_module.validate_review(project, feature)

    assert validation["valid"] is False
    assert any("finding changed" in error for error in validation["errors"])


def test_acceptance_repair_review_binds_current_cycle_evidence_bytes(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo repair complete.\n", encoding="utf-8"
    )
    _approve_current_acceptance_repair_review(
        project,
        feature,
        revision=routed["data"]["revision"],
    )
    state = json.loads((feature / "review-state.json").read_text(encoding="utf-8"))
    evidence_path = feature / state["scenarios"][0]["evidence"][0]["path"]
    evidence_path.write_text('{"replayed": true}\n', encoding="utf-8")

    validation = review_runtime_module.validate_review(project, feature)

    assert validation["valid"] is False
    assert any("artifact_sha256" in error for error in validation["errors"])


def test_acceptance_repair_review_rejects_drifted_origin_finding_contract(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    revision = _rejected_acceptance_at_active_accept(project, feature)
    routed = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed the required screen did not open."],
    )
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo repair complete.\n", encoding="utf-8"
    )
    _approve_current_acceptance_repair_review(
        project,
        feature,
        revision=routed["data"]["revision"],
    )
    state_path = feature / "review-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    origin_finding = next(
        item
        for item in state["findings"]
        if item.get("origin_acceptance_finding_id") == "HAF-001"
    )
    origin_finding["scenario_id"] = "SR-NONEXISTENT"
    origin_finding["obligation_ids"] = []
    origin_finding["expected"] = "A different expectation."
    for revalidation in state["revalidations"]:
        if origin_finding["id"] in revalidation["finding_ids"]:
            revalidation["scenario_ids"] = ["SR-NONEXISTENT"]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = review_runtime_module.validate_review(project, feature)

    assert validation["valid"] is False
    assert any(
        "exactly preserve the routed human observation" in error
        for error in validation["errors"]
    )


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
        route="spx-review",
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
        affected_scope=["acceptance scenario HA-DEMO-001"],
        exact_next_action="Approve device D-7 on its local screen.",
        unblock_criteria="Device D-7 displays approval granted.",
    )
    original = blocked["blockers"][0]

    with pytest.raises(WorkflowRuntimeError) as captured:
        route_human_acceptance_repair(
            project,
            feature,
            route="spx-review",
            finding_id="HAF-001",
            expected_revision=blocked["data"]["revision"],
            evidence=["The acceptance failure remains reproducible."],
        )

    error = captured.value.to_envelope()
    assert error["data"]["error_code"] == "blocked-stage-requires-resolution"
    assert error["blockers"][0]["human_action_guide"] == original["human_action_guide"]
    assert state_path.read_bytes() == acceptance_before
    shown = show_workflow(feature)
    assert shown["data"]["status"] == "blocked"
    assert shown["blockers"][0]["owner"] == "user"


def test_acceptance_remains_fresh_after_its_human_blocker_is_resolved(
    tmp_path: Path,
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
    assert prepare_human_acceptance(project, feature)["status"] == "draft"
    blocked = block_workflow(
        feature,
        expected_revision=revision,
        category="credentials-or-permission",
        owner="user",
        cause="The protected test account is temporarily unavailable.",
        evidence=["The login page reports that access is pending."],
        attempted_recovery=[
            {
                "action": "Retried the documented sandbox login.",
                "result": "Access is still pending.",
            }
        ],
        affected_scope=["human acceptance sandbox login"],
        exact_next_action="Restore the protected sandbox account.",
        unblock_criteria="The sandbox login succeeds without a production account.",
        human_action_required=True,
        human_action={
            "goal": "Restore sandbox access",
            "why_human": "Only the sandbox account owner can restore access.",
            "prerequisites": ["Use the sandbox account only."],
            "safety_notes": ["Do not enter production credentials."],
            "steps": [
                {
                    "order": 1,
                    "title": "Restore access",
                    "action": "Ask the sandbox owner to restore the account.",
                    "command": None,
                    "expected_result": "The sandbox login succeeds.",
                    "if_failed": "Return the sanitized access error.",
                }
            ],
            "verification": ["Log in to the sandbox."],
            "evidence_to_return": ["A sanitized successful-login observation."],
            "resume_instruction": (
                "Return the evidence, then execute the blocker resume argv exactly."
            ),
        },
    )
    resolved = resolve_workflow_blocker(
        feature,
        expected_revision=blocked["data"]["revision"],
        resolution_evidence=["The sandbox login now succeeds."],
    )

    prepared = prepare_human_acceptance(project, feature)

    assert resolved["data"]["status"] == "active"
    assert prepared["status"] == "draft"


def test_acceptance_repair_rejects_a_route_that_does_not_match_the_finding(
    tmp_path: Path,
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
    _rejected_state(state_path)
    workflow_before = workflow_runtime_path(feature).read_bytes()
    acceptance_before = state_path.read_bytes()

    with pytest.raises(ValueError, match="routes to spx-review"):
        route_human_acceptance_repair(
            project,
            feature,
            route="sp-review",
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
    for target in ("plan", "tasks", "implement", "review", "accept"):
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
            "spx-review",
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
    assert payload["data"]["repair_route"] == "spx-review"
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
    for target in ("plan", "tasks", "implement", "review", "accept"):
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
            route="spx-review",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )

    assert workflow_runtime_path(feature).read_bytes() == workflow_before
    assert state_path.read_bytes() == acceptance_before


@pytest.mark.parametrize(
    ("route", "target_stage", "owning_command"),
    (
        ("sp-review", "review", "sp-review"),
        ("spx-review", "review", "spx-review"),
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
    (feature / "implementation-summary.md").write_text(
        f"# Implementation Summary\n\nRepair through {route} completed.\n",
        encoding="utf-8",
    )
    current_revision = routed["data"]["revision"]
    if target_stage == "review":
        _approve_current_acceptance_repair_review(
            project,
            feature,
            revision=current_revision,
        )
        remaining = ("accept",)
    elif target_stage == "implement":
        remaining = ("review", "accept")
    else:
        remaining = ("plan", "tasks", "implement", "review", "accept")
    for target in remaining:
        transitioned = _complete_then_transition(
            feature,
            target_stage=target,
            revision=current_revision,
        )
        current_revision = transitioned["data"]["revision"]
    assert show_workflow(feature)["data"]["stage"] == "accept"
    assert show_workflow(feature)["data"]["status"] == "active"

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
            route="spx-review",
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
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert recovered["data"]["stage"] == "review"
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
        route="spx-review",
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
            route="spx-review",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )
    assert show_workflow(feature)["data"]["stage"] == "review"

    monkeypatch.setattr(
        human_acceptance_module,
        "_write_acceptance_repair_journal",
        real_write_journal,
    )
    recovered = route_human_acceptance_repair(
        project,
        feature,
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert recovered["summary"].startswith("Recovered completed")
    assert recovered["data"]["repair_handoff_command"] == "spx-review"
    assert recovered["data"]["owning_stage_command"] == "spx-review"
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
        route="spx-review",
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
        route="spx-review",
        finding_id="HAF-001",
        expected_revision=revision,
        evidence=["Human observed a visible product failure."],
    )

    assert recovered["summary"].startswith("Recovered completed")
    shown = show_workflow(feature)["data"]
    assert shown["stage"] == "review"
    assert shown["status"] == "active"
    assert shown["revision"] == revision + 1
    acceptance = json.loads(
        (feature / "human-acceptance.json").read_text(encoding="utf-8")
    )
    assert acceptance["status"] == "draft"
    assert acceptance["overall"]["next_command"] == "spx-review"
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
            route="spx-review",
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
            route="spx-review",
            finding_id="HAF-001",
            expected_revision=revision,
            evidence=["Human observed a visible product failure."],
        )

    payload = captured.value.to_envelope()
    assert payload["data"]["error_code"] == "acceptance-repair-recovery-required"
    assert payload["blockers"][0]["human_action_required"] is True
    assert len(payload["blockers"][0]["human_action_guide"]["steps"]) == 6
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
            route="spx-review",
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
            route="spx-review",
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
        route="spx-review",
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
    _install_approved_review(project, feature)
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
            "scenario_id": "HA-DEMO-001",
            "step_id": "HA-DEMO-001-S01",
            "classification": "observed-mismatch",
            "route": "spx-review",
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
    _install_approved_review(project, feature)
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

    _install_approved_review(project, feature)
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
    for target in ("plan", "tasks", "implement", "review", "accept"):
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
    assert payload["next_argv"][:3] == ["specify-runtime", "workflow", "closeout"]
    assert payload["next_argv"][
        payload["next_argv"].index("--expected-revision") + 1
    ] == str(revision)


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
    assert payload["data"]["resolution_action"] == blocked["data"]["resolution_action"]
