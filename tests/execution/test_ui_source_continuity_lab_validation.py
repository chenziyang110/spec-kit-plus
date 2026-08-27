from __future__ import annotations

import hashlib
import json
from pathlib import Path

from specify_cli.execution.ui_validation import (
    _source_continuity_target_snapshot,
    validate_lifecycle_ui_verification,
)


def _canonical_bytes(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _runtime_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def _write_evidence_record(project_root: Path, label: str, adapter_id: str) -> str:
    content = f"{label}\n".encode()
    digest = hashlib.sha256(content).hexdigest()
    object_ref = f".specify/evidence/objects/sha256/{digest[:2]}/{digest}"
    object_path = project_root / object_ref
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(content)
    record_ref = f".specify/evidence/records/{label}.json"
    record_path = project_root / record_ref
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(
        _canonical_bytes(
            {
                "schema_version": "spec-kit-evidence-v1",
                "evidence_id": label,
                "status": "ready",
                "sha256": digest,
                "size": len(content),
                "mime": "text/plain",
                "scope": "review",
                "source": "source-continuity-lab-test",
                "provenance": f"adapter:{adapter_id}",
                "object_ref": object_ref,
                "record_ref": record_ref,
                "created_at": "2026-08-27T00:00:00Z",
            }
        )
    )
    return record_ref


def _adapter_plan(
    *,
    manifest_ref: str,
    manifest_sha256: str,
    source_continuity_sha256: str,
    task_index_sha256: str,
    target_snapshot_sha256: str,
) -> dict[str, object]:
    adapters: list[dict[str, object]] = [
        {
            "id": "structure-reader",
            "version": "1.0.0",
            "roles": ["source", "target"],
            "capabilities": ["surface-enumeration"],
            "actions": ["enumerate-surfaces", "capture-structure"],
            "evidence_kinds": ["structure_snapshot"],
            "execution_mode": "agent-tool",
            "tool_ref": "tool://structure-reader",
            "write_policy": "read-only",
            "network_policy": "denied",
        },
        {
            "id": "behavior-runner",
            "version": "1.0.0",
            "roles": ["source", "target"],
            "capabilities": ["action-execution", "side-effect-observation"],
            "actions": [
                "enumerate-actions",
                "activate-action",
                "observe-side-effects",
                "capture-runtime",
            ],
            "evidence_kinds": ["runtime_diagnostics"],
            "execution_mode": "external-runner",
            "tool_ref": "runner://behavior",
            "write_policy": "isolated-test-data",
            "network_policy": "declared-read-only",
        },
        {
            "id": "asset-inspector",
            "version": "1.0.0",
            "roles": ["source", "target"],
            "capabilities": ["asset-inspection", "visual-capture"],
            "actions": ["enumerate-assets", "capture-visual"],
            "evidence_kinds": ["visual_capture"],
            "execution_mode": "manual-attested",
            "tool_ref": "guide://asset-inspection",
            "write_policy": "read-only",
            "network_policy": "denied",
        },
    ]
    adapter_by_capability = {
        "surface-enumeration": "structure-reader",
        "action-execution": "behavior-runner",
        "side-effect-observation": "behavior-runner",
        "asset-inspection": "asset-inspector",
        "visual-capture": "asset-inspector",
    }
    capabilities = list(adapter_by_capability)
    assignments = [
        {
            "side": side,
            "capability": capability,
            "adapter_id": adapter_by_capability[capability],
            "selection_reason": "Selected for the declared capability and evidence contract.",
        }
        for side in ("source", "target")
        for capability in capabilities
    ]
    return {
        "schema": "spec-kit-source-continuity-adapter-plan-v1",
        "adapter_protocol": "spec-kit-source-continuity-adapter-v1",
        "plan_id": "SCAP-0123456789ab",
        "subject_id": "T001",
        "status": "ready",
        "binding": {
            "mode": "formal",
            "subject_id": "T001",
            "manifest_ref": manifest_ref,
            "manifest_sha256": manifest_sha256,
            "source_continuity_sha256": source_continuity_sha256,
            "target_snapshot_sha256": target_snapshot_sha256,
            "task_index_sha256": task_index_sha256,
        },
        "required_lanes": [
            f"{side}.{capability}"
            for side in ("source", "target")
            for capability in capabilities
        ],
        "adapters": adapters,
        "assignments": assignments,
        "unresolved_gaps": [],
    }


def _source_continuity() -> dict[str, object]:
    return {
        "schema": "spec-kit-ui-source-continuity-v1",
        "applicability": "required",
        "mode": "mixed",
        "reason": "A runnable source product governs the migration.",
        "coverage": {
            "surface_ids": ["DH-SURFACE-001"],
            "interaction_ids": ["DH-INT-001"],
            "component_ids": ["DH-COMP-001"],
        },
        "authority_refs": ["evidence://source/runtime"],
        "surface_bindings": [
            {
                "id": "SC-SURFACE-001",
                "surface_id": "DH-SURFACE-001",
                "source_refs": ["legacy/main"],
                "discovery": "measured",
                "disposition": "adapt",
                "rationale": "Preserve the primary surface.",
            }
        ],
        "action_bindings": [
            {
                "id": "SC-ACTION-001",
                "interaction_id": "DH-INT-001",
                "source_refs": ["legacy/export"],
                "user_promise": "Export the document.",
                "business_outcome": "The file is written once.",
                "side_effects": ["write one file"],
                "final_state": "The exported path is visible.",
                "verification": "Run source and target with equal data.",
            }
        ],
        "asset_bindings": [
            {
                "id": "SC-ASSET-001",
                "component_id": "DH-COMP-001",
                "semantic_role": "export action",
                "source_refs": ["legacy/export.svg"],
                "target_strategy": "preserve",
                "target_ref": "src/assets/export.svg",
                "provenance": "project-owned",
                "fallback": "Export label",
                "placeholder_policy": "forbid-character-substitution",
            }
        ],
        "unresolved_gaps": [],
    }


def test_lifecycle_requires_byte_bound_source_continuity_lab_report(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-source-continuity"
    feature_dir.mkdir(parents=True)
    source_file = tmp_path / "src" / "app.ts"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("export const ready = true;\n", encoding="utf-8")
    continuity = _source_continuity()
    task_index = {
        "version": 2,
        "status": "ready",
        "tasks": [
            {
                "id": "T001",
                "scope": {"write_scope": ["src/**"]},
                "ui_contract": {
                    "source_continuity": continuity,
                    "usability_validation": {"smoothness_acceptance_ids": []},
                },
            }
        ],
    }
    task_index_bytes = _canonical_bytes(task_index)
    (feature_dir / "task-index.json").write_bytes(task_index_bytes)
    lifecycle = {
        "task_id": "T001",
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "integrated",
            "contract_check": "pass",
            "runtime_evidence": "pass",
            "fidelity_status": "pass",
            "visual_comparison": "pass",
        },
    }

    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert any("source continuity lab report" in error.lower() for error in errors)

    target_snapshot = _source_continuity_target_snapshot(tmp_path, ["src/**"])
    assert target_snapshot is not None

    manifest_ref = (
        "implementation-review/source-continuity/"
        "source-continuity-manifest-T001.json"
    )
    manifest = {
        "schema": "spec-kit-source-continuity-lab-manifest-v1",
        "task_id": "T001",
        "source_continuity_schema": "spec-kit-ui-source-continuity-v1",
        "source_continuity_sha256": hashlib.sha256(
            _runtime_bytes(continuity)
        ).hexdigest(),
        "source_continuity": continuity,
        "required_adapter_capabilities": [
            "surface-enumeration",
            "action-execution",
            "side-effect-observation",
            "asset-inspection",
            "visual-capture",
        ],
        "required_evidence": [
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
        ],
        "source": {
            "task_index_ref": "task-index.json",
            "task_index_sha256": hashlib.sha256(task_index_bytes).hexdigest(),
            "feature_ref": "specs/001-source-continuity",
            "target_snapshot_sha256": target_snapshot,
        },
    }
    manifest_bytes = _canonical_bytes(manifest)
    manifest_path = feature_dir / manifest_ref
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(manifest_bytes)
    report_ref = (
        "implementation-review/source-continuity/"
        "source-continuity-lab-T001.json"
    )
    report = {
        "schema": "spec-kit-source-continuity-lab-report-v1",
        "task_id": "T001",
        "verdict": "passed",
        "manifest_ref": manifest_ref,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_revision": "legacy@abc",
        "target_revision": "target@def",
        "adapter": {"id": "fixture", "version": "1"},
        "evidence_refs": [],
        "discovery": {},
        "surface_results": [],
        "action_results": [],
        "asset_results": [],
        "coverage": continuity["coverage"],
        "metrics": {
            "source_discovery_coverage": 1,
            "target_surface_reachability": 1,
            "action_operability": 1,
            "business_outcome_parity": 1,
            "asset_fidelity": 1,
        },
        "reviewer": "agent:source-continuity-lab",
        "source": {
            "result_schema": "spec-kit-source-continuity-lab-result-v1",
            "task_index_sha256": hashlib.sha256(task_index_bytes).hexdigest(),
            "target_snapshot_sha256": target_snapshot,
        },
    }
    report_bytes = _canonical_bytes(report)
    report_path = feature_dir / report_ref
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"].update(
        {
            "source_continuity_lab_report_ref": report_ref,
            "source_continuity_lab_report_sha256": hashlib.sha256(
                report_bytes
            ).hexdigest(),
            "covered_source_continuity_surface_ids": ["DH-SURFACE-001"],
            "covered_source_continuity_interaction_ids": ["DH-INT-001"],
            "covered_source_continuity_component_ids": ["DH-COMP-001"],
        }
    )

    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert any("source continuity lab report semantics" in error.lower() for error in errors)

    adapter_plan_ref = (
        "implementation-review/source-continuity/"
        "source-continuity-adapter-plan-T001.json"
    )
    adapter_plan = _adapter_plan(
        manifest_ref=manifest_ref,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        source_continuity_sha256=str(manifest["source_continuity_sha256"]),
        task_index_sha256=hashlib.sha256(task_index_bytes).hexdigest(),
        target_snapshot_sha256=target_snapshot,
    )
    adapter_plan_bytes = _canonical_bytes(adapter_plan)
    adapter_plan_path = feature_dir / adapter_plan_ref
    adapter_plan_path.write_bytes(adapter_plan_bytes)
    adapter_plan_sha256 = hashlib.sha256(adapter_plan_bytes).hexdigest()
    adapter_by_kind = {
        "structure_snapshot": "structure-reader",
        "runtime_diagnostics": "behavior-runner",
        "visual_capture": "asset-inspector",
    }
    project_root = tmp_path
    evidence_refs = {
        (side, kind): _write_evidence_record(
            project_root, f"{side}-{kind}", adapter_by_kind[kind]
        )
        for side in ("source", "target")
        for kind in (
            "structure_snapshot",
            "visual_capture",
            "runtime_diagnostics",
        )
    }
    report.update(
        {
            "adapter_plan_ref": adapter_plan_ref,
            "adapter_plan_sha256": adapter_plan_sha256,
            "adapter": {
                "id": f"adapter-plan:{adapter_plan_sha256[:12]}",
                "version": "1",
                "capabilities": [
                    "surface-enumeration",
                    "action-execution",
                    "side-effect-observation",
                    "asset-inspection",
                    "visual-capture",
                ],
            },
            "evidence_refs": [
                {
                    "side": side,
                    "kind": kind,
                    "ref": ref,
                    "adapter_id": adapter_by_kind[kind],
                }
                for (side, kind), ref in evidence_refs.items()
            ],
            "discovery": {
                "surface_binding_ids": ["SC-SURFACE-001"],
                "action_binding_ids": ["SC-ACTION-001"],
                "asset_binding_ids": ["SC-ASSET-001"],
                "unexpected_candidates": [],
            },
            "surface_results": [
                {
                    "surface_id": "DH-SURFACE-001",
                    "source_reachable": True,
                    "target_reachable": True,
                    "disposition_verified": True,
                    "verdict": "passed",
                }
            ],
            "action_results": [
                {
                    "interaction_id": "DH-INT-001",
                    "source_reachable": True,
                    "target_reachable": True,
                    "source_evidence_ref": evidence_refs[
                        ("source", "runtime_diagnostics")
                    ],
                    "target_evidence_ref": evidence_refs[
                        ("target", "runtime_diagnostics")
                    ],
                    "observed_side_effects": ["write one file"],
                    "business_outcome_verified": True,
                    "final_state_verified": True,
                    "verdict": "passed",
                }
            ],
            "asset_results": [
                {
                    "component_id": "DH-COMP-001",
                    "source_evidence_ref": evidence_refs[("source", "visual_capture")],
                    "target_evidence_ref": evidence_refs[("target", "visual_capture")],
                    "semantic_match": True,
                    "provenance_match": True,
                    "render_match": True,
                    "character_substitution": False,
                    "verdict": "passed",
                }
            ],
        }
    )
    report_bytes = _canonical_bytes(report)
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"]["source_continuity_lab_report_sha256"] = (
        hashlib.sha256(report_bytes).hexdigest()
    )
    lifecycle["ui_verification"].update(
        {
            "source_continuity_adapter_plan_ref": adapter_plan_ref,
            "source_continuity_adapter_plan_sha256": adapter_plan_sha256,
        }
    )
    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert not any("source continuity" in error.lower() for error in errors), errors

    target_runtime = next(
        row
        for row in report["evidence_refs"]
        if row["side"] == "target" and row["kind"] == "runtime_diagnostics"
    )
    target_runtime["adapter_id"] = "asset-inspector"
    report_bytes = _canonical_bytes(report)
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"]["source_continuity_lab_report_sha256"] = (
        hashlib.sha256(report_bytes).hexdigest()
    )
    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert any("adapter" in error.lower() for error in errors)
    target_runtime["adapter_id"] = "behavior-runner"
    report_bytes = _canonical_bytes(report)
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"]["source_continuity_lab_report_sha256"] = (
        hashlib.sha256(report_bytes).hexdigest()
    )

    source_file.write_text("export const ready = false;\n", encoding="utf-8")
    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert any("target snapshot" in error.lower() for error in errors)
    source_file.write_text("export const ready = true;\n", encoding="utf-8")

    lifecycle["ui_verification"]["source_continuity_lab_report_sha256"] = "0" * 64
    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert any("source continuity lab report sha-256" in error.lower() for error in errors)
