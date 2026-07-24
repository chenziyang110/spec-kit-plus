"""Shared UI contract and lifecycle validation helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .packet_schema import UI_CONTRACT_FIELDS, UIContract
from .packet_validator import PacketValidationError, validate_ui_contract


TASK_DETAIL_RE = re.compile(
    r"(?ms)^##\s+(?P<task_id>T\d+)\b[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)"
)
UI_EVIDENCE_KINDS = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
}
OBSOLETE_TASK_UI_FIELDS = {
    "ui_contract_version",
    "ui_fidelity_requirements",
}
OBSOLETE_UI_CONTRACT_FIELDS = {"contract_version"}
PASSING_VISUAL_STATUSES = {
    "pass",
    "passed",
    "success",
    "approved",
    "match",
    "matched",
    "matches",
}


def _canonical_records(values: object) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(
        sorted(
            json.dumps(item, sort_keys=True, separators=(",", ":"), default=str)
            for item in values
            if isinstance(item, dict)
        )
    )


def validate_accepted_task_lifecycle(
    lifecycle: dict[str, Any],
    relative: str,
    expected_task_id: str,
) -> list[str]:
    """Validate the shared acceptance envelope for a task lifecycle record."""

    errors: list[str] = []
    if str(lifecycle.get("task_id") or "").strip().upper() != expected_task_id.upper():
        errors.append(f"{relative} has mismatched task_id")
    if lifecycle.get("status") != "accepted":
        errors.append(f"{relative} status must be accepted")
    if not isinstance(lifecycle.get("changed_paths"), list):
        errors.append(f"{relative} changed_paths must be a list")
    validation = lifecycle.get("validation")
    if not isinstance(validation, list) or not validation:
        errors.append(f"{relative} validation must be a non-empty list")
    blockers = lifecycle.get("blockers")
    if not isinstance(blockers, list):
        errors.append(f"{relative} blockers must be a list")
    elif any(
        not isinstance(blocker, dict)
        or blocker.get("disposition") != "resolved"
        for blocker in blockers
    ):
        errors.append(f"{relative} accepted lifecycle must not retain unresolved blockers")
    review = lifecycle.get("review")
    if review is not None and (
        not isinstance(review, dict)
        or not str(review.get("trigger") or "").strip()
        or not str(review.get("verdict") or "").strip()
    ):
        errors.append(
            f"{relative} review must contain trigger and verdict when present"
        )
    return errors


def _task_contract_applies(task: dict[str, Any]) -> bool:
    ui_contract = task.get("ui_contract")
    if not isinstance(ui_contract, dict):
        return False
    return any(
        bool(value)
        for field, value in ui_contract.items()
        if field != "fidelity_level"
    ) or str(ui_contract.get("fidelity_level") or "none").strip().lower() != "none"


def task_index_ui_contracts(feature_dir: Path) -> dict[str, dict[str, Any]]:
    """Return canonical task-index entries carrying a meaningful UI contract."""

    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return {}
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list):
        return {}

    contracts: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id") or task.get("task_id") or "").strip().upper()
        if task_id and _task_contract_applies(task):
            contracts[task_id] = task
    return contracts


def obsolete_task_ui_contract_fields(feature_dir: Path) -> dict[str, list[str]]:
    """Return obsolete UI fields that must not survive current-contract closeout."""

    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return {}
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list):
        return {}

    obsolete: dict[str, list[str]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id") or task.get("task_id") or "<unknown>").strip().upper()
        fields = sorted(OBSOLETE_TASK_UI_FIELDS & task.keys())
        ui_contract = task.get("ui_contract")
        if isinstance(ui_contract, dict):
            fields.extend(
                f"ui_contract.{field}"
                for field in sorted(OBSOLETE_UI_CONTRACT_FIELDS & ui_contract.keys())
            )
        if fields:
            obsolete[task_id] = fields
    return obsolete


def invalid_task_ui_contracts(feature_dir: Path) -> dict[str, list[str]]:
    """Return task-index UI contracts that do not satisfy the current shape."""

    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return {}
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list):
        return {}

    invalid: dict[str, list[str]] = {}
    for task in tasks:
        if not isinstance(task, dict) or "ui_contract" not in task:
            continue
        task_id = str(task.get("id") or task.get("task_id") or "<unknown>").strip().upper()
        raw_contract = task.get("ui_contract")
        errors: list[str] = []
        if not isinstance(raw_contract, dict) or not raw_contract:
            errors.append("ui_contract must be a non-empty object")
        else:
            unknown = sorted(set(raw_contract) - UI_CONTRACT_FIELDS)
            missing = sorted(UI_CONTRACT_FIELDS - set(raw_contract))
            if unknown:
                errors.append("unsupported fields: " + ", ".join(unknown))
            if missing:
                errors.append("missing current fields: " + ", ".join(missing))
            if not unknown and not missing:
                try:
                    contract = UIContract(**raw_contract)
                    validate_ui_contract(contract)
                except (PacketValidationError, TypeError, ValueError) as exc:
                    errors.append(str(exc))
        if errors:
            invalid[task_id] = errors
    return invalid


def markdown_ui_task_ids(feature_dir: Path) -> set[str]:
    """Return task IDs with a task-local Markdown UI contract."""

    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.is_file():
        return set()
    content = tasks_path.read_text(encoding="utf-8", errors="replace")
    return {
        match.group("task_id").upper()
        for match in TASK_DETAIL_RE.finditer(content)
        if re.search(
            r"(?m)^###\s+UI Implementation Contract\s*$",
            match.group("body"),
        )
    }


def ui_task_ids(feature_dir: Path) -> set[str]:
    """Find UI tasks from both canonical JSON and leader-direct Markdown."""

    return (
        set(task_index_ui_contracts(feature_dir))
        | set(obsolete_task_ui_contract_fields(feature_dir))
        | markdown_ui_task_ids(feature_dir)
    )


def resolve_feature_artifact_ref(feature_dir: Path, raw_ref: str) -> Path | None:
    """Resolve a persisted feature-local artifact reference, if it exists."""

    reference = raw_ref.split("#", 1)[0].strip()
    if not reference or "://" in reference:
        return None
    candidate = Path(reference)
    if candidate.is_absolute():
        return None

    feature_root = feature_dir.resolve(strict=False)
    bases = [feature_root, *list(feature_root.parents)[:4]]
    for base in bases:
        resolved = (base / candidate).resolve(strict=False)
        try:
            resolved.relative_to(feature_root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def validate_lifecycle_ui_verification(
    feature_dir: Path,
    lifecycle: dict[str, Any],
    relative: str,
    *,
    require_integrated: bool = False,
) -> list[str]:
    """Validate accepted UI lifecycle evidence against persisted artifacts."""

    errors: list[str] = []
    verification = lifecycle.get("ui_verification")
    if not isinstance(verification, dict):
        return [f"{relative} ui_verification is required for a UI-bearing task"]
    if "evidence_refs" in verification:
        errors.append(
            f"{relative} ui_verification.evidence_refs is obsolete; use typed evidence entries"
        )
    if verification.get("applicable") is not True:
        errors.append(f"{relative} ui_verification.applicable must be true")

    task_id = str(lifecycle.get("task_id") or Path(relative).stem).strip().upper()
    task_entry = task_index_ui_contracts(feature_dir).get(task_id, {})
    ui_contract = (
        task_entry.get("ui_contract") if isinstance(task_entry, dict) else None
    )
    ui_contract = ui_contract if isinstance(ui_contract, dict) else {}
    evidence_scope = str(verification.get("evidence_scope") or "").strip().lower()
    accepted_scopes = {"task", "integrated"}
    if evidence_scope not in accepted_scopes:
        errors.append(
            f"{relative} ui_verification.evidence_scope must be task or integrated"
        )
    if require_integrated and evidence_scope != "integrated":
        errors.append(
            f"{relative} UI evidence must be recaptured with evidence_scope integrated"
        )
    if (
        require_integrated
        and not str(verification.get("integration_base_ref") or "").strip()
    ):
        errors.append(
            f"{relative} integrated UI evidence requires integration_base_ref"
        )

    contract_check = str(verification.get("contract_check") or "").strip().lower()
    if contract_check not in {"pass", "passed", "approved"}:
        errors.append(f"{relative} ui_verification.contract_check must pass")

    typed_evidence = verification.get("evidence")
    typed_entries = (
        [item for item in typed_evidence if isinstance(item, dict)]
        if isinstance(typed_evidence, list)
        else []
    )
    for item in typed_entries:
        kind = str(item.get("kind") or "").strip().lower().replace("-", "_")
        if kind not in UI_EVIDENCE_KINDS:
            errors.append(
                f"{relative} ui_verification.evidence uses unsupported kind {kind or '<blank>'}"
            )
    typed_refs = [
        str(item.get("ref") or "").strip()
        for item in typed_entries
        if str(item.get("ref") or "").strip()
    ]
    valid_refs = list(dict.fromkeys(typed_refs))
    if not valid_refs:
        errors.append(f"{relative} ui_verification evidence refs must be non-empty")
    else:
        for evidence_ref in valid_refs:
            if resolve_feature_artifact_ref(feature_dir, evidence_ref) is None:
                errors.append(
                    f"{relative} ui_verification evidence is missing or outside the feature: "
                    f"{evidence_ref}"
                )

    required_evidence = {
        str(item).strip()
        for item in ui_contract.get("required_evidence", [])
        if isinstance(item, str) and item.strip()
    }
    for required_kind in UI_EVIDENCE_KINDS:
        if required_kind not in required_evidence:
            continue
        matching = [
            item
            for item in typed_entries
            if str(item.get("kind") or "").strip().lower().replace("-", "_")
            == required_kind
            and str(item.get("ref") or "").strip()
        ]
        if not matching:
            errors.append(
                f"{relative} ui_verification.evidence is missing required kind {required_kind}"
            )
    if "runtime_diagnostics" in required_evidence:
        runtime_status = (
            str(verification.get("runtime_evidence") or "")
            .strip()
            .lower()
            .replace("_", "-")
        )
        if runtime_status not in {"pass", "passed", "success", "approved"}:
            errors.append(f"{relative} ui_verification.runtime_evidence must pass")

    fidelity_status = (
        str(verification.get("fidelity_status") or "").strip().lower().replace("_", "-")
    )
    if fidelity_status == "pending-human-review":
        human_review_ref = str(verification.get("human_review_ref") or "").strip()
        review_target = (
            f"; review target: {human_review_ref}" if human_review_ref else ""
        )
        errors.append(
            f"{relative} pending-human-review blocks UI task acceptance{review_target}"
        )
    elif fidelity_status not in {"pass", "passed", "success", "approved"}:
        errors.append(f"{relative} ui_verification.fidelity_status must pass")

    visual_comparison = (
        str(verification.get("visual_comparison") or "")
        .strip()
        .lower()
        .replace("_", "-")
    )
    if visual_comparison not in PASSING_VISUAL_STATUSES:
        errors.append(f"{relative} ui_verification.visual_comparison must pass")
    design_decision_ids = {
        str(item).strip()
        for item in ui_contract.get("design_decision_ids", [])
        if isinstance(item, str) and item.strip()
    }
    if (
        visual_comparison in PASSING_VISUAL_STATUSES
        and design_decision_ids
    ):
        approved_visual_ref = str(
            verification.get("approved_visual_ref") or ""
        ).strip()
        if approved_visual_ref != str(
            ui_contract.get("approved_visual_ref") or ""
        ).strip():
            errors.append(
                f"{relative} ui_verification.approved_visual_ref must preserve the task contract"
            )
        for field in (
            "approved_preview_sha256",
            "approved_manifest_sha256",
            "comparison_tolerance",
        ):
            if str(verification.get(field) or "").strip() != str(
                ui_contract.get(field) or ""
            ).strip():
                errors.append(
                    f"{relative} ui_verification.{field} must preserve the task contract"
                )
        covered_decision_ids = {
            str(item).strip()
            for item in verification.get("covered_decision_ids", [])
            if isinstance(item, str) and item.strip()
        }
        if covered_decision_ids != design_decision_ids:
            errors.append(
                f"{relative} ui_verification.covered_decision_ids must exactly cover the task contract"
            )
        visual_capture_refs = {
            str(item.get("ref") or "").strip()
            for item in typed_entries
            if str(item.get("kind") or "").strip().lower().replace("-", "_")
            == "visual_capture"
            and str(item.get("ref") or "").strip()
        }
        implementation_capture_refs = {
            str(item).strip()
            for item in verification.get("implementation_capture_refs", [])
            if isinstance(item, str) and item.strip()
        }
        if (
            not implementation_capture_refs
            or not implementation_capture_refs <= visual_capture_refs
        ):
            errors.append(
                f"{relative} ui_verification.implementation_capture_refs must reference visual_capture evidence"
            )
        if _canonical_records(
            verification.get("accepted_deviations")
        ) != _canonical_records(ui_contract.get("accepted_deviations")):
            errors.append(
                f"{relative} ui_verification.accepted_deviations must preserve task approvals"
            )

        comparison_report_ref = str(
            verification.get("comparison_report_ref") or ""
        ).strip()
        comparison_report_sha256 = str(
            verification.get("comparison_report_sha256") or ""
        ).strip()
        comparison_report_path = (
            resolve_feature_artifact_ref(feature_dir, comparison_report_ref)
            if comparison_report_ref
            else None
        )
        if comparison_report_path is None:
            errors.append(
                f"{relative} passing visual comparison requires an existing comparison_report_ref"
            )
        else:
            try:
                comparison_report_bytes = comparison_report_path.read_bytes()
                comparison_report = json.loads(
                    comparison_report_bytes.decode("utf-8")
                )
            except (OSError, json.JSONDecodeError):
                comparison_report = None
                comparison_report_bytes = b""
            except UnicodeDecodeError:
                comparison_report = None
                comparison_report_bytes = b""
            actual_report_sha256 = hashlib.sha256(
                comparison_report_bytes
            ).hexdigest()
            if comparison_report_sha256 != actual_report_sha256:
                errors.append(
                    f"{relative} ui_verification.comparison_report_sha256 must bind the comparison report"
                )
            if not isinstance(comparison_report, dict):
                errors.append(
                    f"{relative} comparison report must contain a JSON object"
                )
            else:
                if comparison_report.get("schema") != "spec-kit-visual-comparison-v1":
                    errors.append(
                        f"{relative} comparison report schema must be spec-kit-visual-comparison-v1"
                    )
                if (
                    str(comparison_report.get("task_id") or "").strip().upper()
                    != task_id
                ):
                    errors.append(
                        f"{relative} comparison report task_id must match"
                    )
                approved = comparison_report.get("approved")
                approved = approved if isinstance(approved, dict) else {}
                approved_pairs = (
                    ("visual_ref", "approved_visual_ref"),
                    ("preview_sha256", "approved_preview_sha256"),
                    ("manifest_sha256", "approved_manifest_sha256"),
                )
                for report_field, contract_field in approved_pairs:
                    if str(approved.get(report_field) or "").strip() != str(
                        ui_contract.get(contract_field) or ""
                    ).strip():
                        errors.append(
                            f"{relative} comparison report approved.{report_field} must preserve the task contract"
                        )
                report_decision_ids = {
                    str(item).strip()
                    for item in approved.get("decision_ids", [])
                    if isinstance(item, str) and item.strip()
                }
                if report_decision_ids != design_decision_ids:
                    errors.append(
                        f"{relative} comparison report approved.decision_ids must exactly cover the task contract"
                    )
                implementation = comparison_report.get("implementation")
                implementation = (
                    implementation if isinstance(implementation, dict) else {}
                )
                report_capture_refs = {
                    str(item).strip()
                    for item in implementation.get("capture_refs", [])
                    if isinstance(item, str) and item.strip()
                }
                if report_capture_refs != implementation_capture_refs:
                    errors.append(
                        f"{relative} comparison report capture_refs must match lifecycle verification"
                    )
                if require_integrated and str(
                    implementation.get("revision") or ""
                ).strip() != str(
                    verification.get("integration_base_ref") or ""
                ).strip():
                    errors.append(
                        f"{relative} integrated comparison report revision must match integration_base_ref"
                    )
                matrix = comparison_report.get("matrix")
                matrix = matrix if isinstance(matrix, list) else []
                matrix_decision_ids: set[str] = set()
                if not matrix:
                    errors.append(
                        f"{relative} comparison report matrix must be non-empty"
                    )
                for index, item in enumerate(matrix):
                    if not isinstance(item, dict):
                        errors.append(
                            f"{relative} comparison report matrix[{index}] must be an object"
                        )
                        continue
                    for field in (
                        "viewport",
                        "state",
                        "implementation_capture_ref",
                    ):
                        if not str(item.get(field) or "").strip():
                            errors.append(
                                f"{relative} comparison report matrix[{index}].{field} must be non-empty"
                            )
                    if (
                        str(item.get("implementation_capture_ref") or "").strip()
                        not in implementation_capture_refs
                    ):
                        errors.append(
                            f"{relative} comparison report matrix[{index}] references an unknown capture"
                        )
                    row_decisions = {
                        str(value).strip()
                        for value in item.get("covered_decision_ids", [])
                        if isinstance(value, str) and value.strip()
                    }
                    matrix_decision_ids.update(row_decisions)
                    if (
                        str(item.get("result") or "")
                        .strip()
                        .lower()
                        .replace("_", "-")
                        not in PASSING_VISUAL_STATUSES
                    ):
                        errors.append(
                            f"{relative} comparison report matrix[{index}].result must pass"
                        )
                if matrix_decision_ids != design_decision_ids:
                    errors.append(
                        f"{relative} comparison report matrix must exactly cover task design decisions"
                    )
                if str(
                    comparison_report.get("comparison_tolerance") or ""
                ).strip() != str(ui_contract.get("comparison_tolerance") or "").strip():
                    errors.append(
                        f"{relative} comparison report comparison_tolerance must preserve the task contract"
                    )
                if _canonical_records(
                    comparison_report.get("accepted_deviations")
                ) != _canonical_records(ui_contract.get("accepted_deviations")):
                    errors.append(
                        f"{relative} comparison report accepted_deviations must preserve task approvals"
                    )
                if (
                    str(comparison_report.get("verdict") or "")
                    .strip()
                    .lower()
                    .replace("_", "-")
                    not in PASSING_VISUAL_STATUSES
                ):
                    errors.append(
                        f"{relative} comparison report verdict must pass"
                    )
    return errors
