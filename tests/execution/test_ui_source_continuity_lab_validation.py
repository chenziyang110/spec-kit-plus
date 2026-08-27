from __future__ import annotations

import hashlib
import json
from pathlib import Path

from specify_cli.execution.ui_validation import validate_lifecycle_ui_verification


def _canonical_bytes(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


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
    continuity = _source_continuity()
    task_index = {
        "version": 2,
        "status": "ready",
        "tasks": [
            {
                "id": "T001",
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

    manifest_ref = (
        "implementation-review/source-continuity/"
        "source-continuity-manifest-T001.json"
    )
    manifest = {
        "schema": "spec-kit-source-continuity-lab-manifest-v1",
        "task_id": "T001",
        "source_continuity_schema": "spec-kit-ui-source-continuity-v1",
        "source_continuity_sha256": hashlib.sha256(
            _canonical_bytes(continuity)
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
    assert not any("source continuity" in error.lower() for error in errors)

    lifecycle["ui_verification"]["source_continuity_lab_report_sha256"] = "0" * 64
    errors = validate_lifecycle_ui_verification(
        feature_dir, lifecycle, "implementation-review/tasks/T001.json"
    )
    assert any("source continuity lab report sha-256" in error.lower() for error in errors)
