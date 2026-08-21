from __future__ import annotations

import json
import hashlib
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
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
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
                "tasks": [
                    {
                        "id": "T001",
                        "ui_contract": {
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

    report_bytes = b'{"schema":"spec-kit-smoothness-lab-v1","verdict":"pass"}\n'
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
    assert not any("smoothness lab report" in error.lower() for error in errors)

    lifecycle["ui_verification"]["smoothness_lab_report_sha256"] = "0" * 64
    errors = validate_lifecycle_ui_verification(
        feature_dir,
        lifecycle,
        "implementation-review/tasks/T001.json",
    )
    assert any("smoothness lab report" in error.lower() for error in errors)
