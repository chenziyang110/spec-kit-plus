from __future__ import annotations

import hashlib
import json
from pathlib import Path

from specify_cli.execution.ui_validation import validate_lifecycle_ui_verification


def test_lifecycle_requires_exact_smoothness_acceptance_coverage(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "official_entrypoints": [
                    {
                        "id": "EP-WEB-SETTINGS",
                        "kind": "web",
                        "route": "/settings",
                        "url": "",
                        "command": "npm run dev",
                        "ready_signal": "Settings route ready.",
                    }
                ],
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "surface_catalog": [
                                {
                                    "id": "SURFACE-SETTINGS",
                                    "entrypoint_id": "EP-WEB-SETTINGS",
                                }
                            ],
                            "usability_validation": {
                                "smoothness_acceptance_ids": [
                                    "focus-continuity",
                                    "pending-cancel-feedback",
                                ]
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    lifecycle = {
        "task_id": "T001",
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "task",
            "contract_check": "pass",
            "evidence": [],
            "runtime_evidence": "pass",
            "fidelity_status": "pass",
            "visual_comparison": "pass",
            "covered_smoothness_acceptance_ids": ["focus-continuity"],
        },
    }

    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )

    assert any(
        "covered_smoothness_acceptance_ids must exactly cover" in error
        for error in errors
    )


def test_lifecycle_requires_bound_smoothness_lab_report_for_smoothness_acceptance(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "official_entrypoints": [
                    {
                        "id": "EP-WEB-SETTINGS",
                        "kind": "web",
                        "route": "/settings",
                        "url": "",
                        "command": "npm run dev",
                        "ready_signal": "Settings route ready.",
                    }
                ],
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
                            "surface_catalog": [
                                {
                                    "id": "SURFACE-SETTINGS",
                                    "entrypoint_id": "EP-WEB-SETTINGS",
                                }
                            ],
                            "usability_validation": {
                                "smoothness_acceptance_ids": [
                                    "focus-continuity",
                                    "reduced-motion",
                                ]
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    lifecycle = {
        "task_id": "T001",
        "ui_verification": {
            "applicable": True,
            "evidence_scope": "task",
            "contract_check": "pass",
            "evidence": [],
            "runtime_evidence": "pass",
            "fidelity_status": "pass",
            "visual_comparison": "pass",
            "covered_smoothness_acceptance_ids": [
                "focus-continuity",
                "reduced-motion",
            ],
        },
    }

    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert any("smoothness lab report" in error.lower() for error in errors)

    report_bytes = (
        json.dumps(
            {
                "schema": "spec-kit-smoothness-lab-report-v1",
                "task_id": "T001",
                "verdict": "passed",
                "covered_smoothness_acceptance_ids": [
                    "focus-continuity",
                    "reduced-motion",
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    report_path = feature_dir / "smoothness-lab-T001.json"
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"].update(
        {
            "smoothness_lab_report_ref": "smoothness-lab-T001.json",
            "smoothness_lab_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        }
    )
    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert any("smoothness lab report" in error.lower() for error in errors)

    manifest_ref = (
        "implementation-review/smoothness/smoothness-manifest-T001.json"
    )
    manifest_path = feature_dir / manifest_ref
    manifest_path.parent.mkdir(parents=True)
    task_index_bytes = (feature_dir / "task-index.json").read_bytes()
    manifest_bytes = (
        json.dumps(
            {
                "schema": "spec-kit-smoothness-lab-manifest-v1",
                "task_id": "T001",
                "smoothness_acceptance_ids": [
                    "focus-continuity",
                    "reduced-motion",
                ],
                "required_evidence": [
                    "structure_snapshot",
                    "visual_capture",
                    "runtime_diagnostics",
                ],
                "entrypoint": {
                    "id": "EP-WEB-SETTINGS",
                    "kind": "web",
                    "route": "/settings",
                    "url": "",
                },
                "viewports": ["desktop", "mobile"],
                "performance_budgets": {
                    "inp_ms": 200,
                    "long_task_ms": 50,
                    "cls": 0.1,
                    "animation_dropped_frame_pct": 5,
                    "bundle_delta_kb": 30,
                },
                "source": {
                    "task_index_ref": "task-index.json",
                    "task_index_sha256": hashlib.sha256(
                        task_index_bytes
                    ).hexdigest(),
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    report_ref = "implementation-review/smoothness/smoothness-lab-T001.json"
    report_path = feature_dir / report_ref
    report_bytes = (
        json.dumps(
            {
                "schema": "spec-kit-smoothness-lab-report-v1",
                "task_id": "T001",
                "verdict": "passed",
                "manifest_ref": manifest_ref,
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "covered_smoothness_acceptance_ids": [
                    "focus-continuity",
                    "reduced-motion",
                ],
                "evidence_refs": [
                    {"kind": "structure_snapshot", "ref": "evidence://structure"},
                    {"kind": "visual_capture", "ref": "evidence://visual"},
                    {"kind": "runtime_diagnostics", "ref": "evidence://runtime"},
                ],
                "scenario_results": [
                    {
                        "smoothness_acceptance_id": "focus-continuity",
                        "verdict": "passed",
                    },
                    {
                        "smoothness_acceptance_id": "reduced-motion",
                        "verdict": "passed",
                    },
                ],
                "performance": {
                    "inp_ms": 120,
                    "long_task_ms": 40,
                    "cls": 0.02,
                    "animation_dropped_frame_pct": 1,
                    "bundle_delta_kb": 10,
                },
                "source": {"result_schema": "spec-kit-smoothness-lab-result-v1"},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"].update(
        {
            "smoothness_lab_report_ref": report_ref,
            "smoothness_lab_report_sha256": hashlib.sha256(
                report_bytes
            ).hexdigest(),
        }
    )
    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert not any("smoothness lab report" in error.lower() for error in errors)

    lifecycle["ui_verification"]["covered_smoothness_acceptance_ids"] = [
        "focus-continuity",
        "reduced-motion",
        "reduced-motion",
    ]
    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert any("must exactly cover" in error for error in errors)
    lifecycle["ui_verification"]["covered_smoothness_acceptance_ids"] = [
        "focus-continuity",
        "reduced-motion",
    ]

    valid_report = json.loads(report_bytes.decode("utf-8"))
    invalid_reports = [
        (
            {
                **valid_report,
                "evidence_refs": valid_report["evidence_refs"][:-1],
            },
            "structure, visual, and runtime evidence",
        ),
        (
            {
                **valid_report,
                "scenario_results": valid_report["scenario_results"][:-1],
            },
            "one passing scenario result",
        ),
        (
            {
                **valid_report,
                "performance": {
                    **valid_report["performance"],
                    "inp_ms": 201,
                },
            },
            "task-bound budget",
        ),
    ]
    for invalid_report, expected_error in invalid_reports:
        invalid_bytes = (
            json.dumps(
                invalid_report,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        report_path.write_bytes(invalid_bytes)
        lifecycle["ui_verification"]["smoothness_lab_report_sha256"] = (
            hashlib.sha256(invalid_bytes).hexdigest()
        )
        errors = validate_lifecycle_ui_verification(
            feature_dir,
            lifecycle,
            "implementation-review/tasks/T001.json",
        )
        assert any(expected_error in error for error in errors)

    invalid_manifest = {
        **json.loads(manifest_bytes.decode("utf-8")),
        "entrypoint": {
            "id": "EP-WEB-OTHER",
            "kind": "web",
            "route": "/other",
            "url": "",
        },
    }
    invalid_manifest_bytes = (
        json.dumps(invalid_manifest, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    manifest_path.write_bytes(invalid_manifest_bytes)
    invalid_entrypoint_report = {
        **valid_report,
        "manifest_sha256": hashlib.sha256(invalid_manifest_bytes).hexdigest(),
    }
    invalid_entrypoint_report_bytes = (
        json.dumps(
            invalid_entrypoint_report,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    report_path.write_bytes(invalid_entrypoint_report_bytes)
    lifecycle["ui_verification"]["smoothness_lab_report_sha256"] = hashlib.sha256(
        invalid_entrypoint_report_bytes
    ).hexdigest()
    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert any("manifest is stale" in error for error in errors)

    manifest_path.write_bytes(manifest_bytes)
    report_path.write_bytes(report_bytes)
    lifecycle["ui_verification"]["smoothness_lab_report_sha256"] = hashlib.sha256(
        report_bytes
    ).hexdigest()

    lifecycle["ui_verification"]["smoothness_lab_report_sha256"] = "0" * 64
    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert any("smoothness lab report" in error.lower() for error in errors)
