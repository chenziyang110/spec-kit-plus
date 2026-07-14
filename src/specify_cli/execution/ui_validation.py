"""Shared UI contract and lifecycle validation helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TASK_DETAIL_RE = re.compile(
    r"(?ms)^##\s+(?P<task_id>T\d+)\b[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)"
)
UI_EVIDENCE_KIND_ALIASES = {
    "structure_snapshot": {
        "structure_snapshot",
        "accessibility_snapshot",
        "dom_snapshot",
        "semantic_snapshot",
        "structured_output",
    },
    "visual_capture": {
        "visual_capture",
        "desktop_screenshot",
        "mobile_screenshot",
        "screenshot",
        "screenshot_desktop",
        "screenshot_mobile",
        "platform_capture",
        "terminal_capture",
    },
    "runtime_diagnostics": {
        "runtime_diagnostics",
        "console_runtime",
        "console_check",
        "runtime_check",
        "terminal_check",
        "stderr_exit_check",
    },
}


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
    if not isinstance(lifecycle.get("blockers"), list):
        errors.append(f"{relative} blockers must be a list")
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
    ui_requirements = task.get("ui_fidelity_requirements")
    contract_applies = isinstance(ui_contract, dict) and (
        any(
            bool(ui_contract.get(field))
            for field in (
                "surface_type",
                "platforms",
                "approved_visual_ref",
                "design_sources",
                "reference_notes",
                "visual_target",
                "must_preserve",
                "required_states",
                "required_evidence",
            )
        )
        or str(ui_contract.get("fidelity_level") or "none").strip().lower() != "none"
    )
    fidelity_applies = isinstance(ui_requirements, dict) and (
        ui_requirements.get("applicable") is True
        or str(ui_requirements.get("level") or "none").strip().lower() != "none"
    )
    return contract_applies or fidelity_applies


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

    return set(task_index_ui_contracts(feature_dir)) | markdown_ui_task_ids(feature_dir)


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
    if verification.get("applicable") is not True:
        errors.append(f"{relative} ui_verification.applicable must be true")

    task_id = str(lifecycle.get("task_id") or Path(relative).stem).strip().upper()
    task_entry = task_index_ui_contracts(feature_dir).get(task_id, {})
    ui_contract = (
        task_entry.get("ui_contract") if isinstance(task_entry, dict) else None
    )
    ui_contract = ui_contract if isinstance(ui_contract, dict) else {}
    contract_version = ui_contract.get("contract_version", 1)
    enhanced_contract = isinstance(contract_version, int) and contract_version >= 2

    if enhanced_contract:
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

    evidence_refs = verification.get("evidence_refs")
    legacy_refs = (
        [
            item.strip()
            for item in evidence_refs
            if isinstance(item, str) and item.strip()
        ]
        if isinstance(evidence_refs, list)
        else []
    )
    typed_evidence = verification.get("evidence")
    typed_entries = (
        [item for item in typed_evidence if isinstance(item, dict)]
        if isinstance(typed_evidence, list)
        else []
    )
    typed_refs = [
        str(item.get("ref") or "").strip()
        for item in typed_entries
        if str(item.get("ref") or "").strip()
    ]
    valid_refs = list(dict.fromkeys([*legacy_refs, *typed_refs]))
    if not valid_refs:
        errors.append(f"{relative} ui_verification evidence refs must be non-empty")
    else:
        for evidence_ref in valid_refs:
            if resolve_feature_artifact_ref(feature_dir, evidence_ref) is None:
                errors.append(
                    f"{relative} ui_verification evidence is missing or outside the feature: "
                    f"{evidence_ref}"
                )

    if enhanced_contract:
        required_evidence = {
            str(item).strip()
            for item in ui_contract.get("required_evidence", [])
            if isinstance(item, str) and item.strip()
        }
        for required_kind, accepted_kinds in UI_EVIDENCE_KIND_ALIASES.items():
            if required_kind not in required_evidence:
                continue
            matching = [
                item
                for item in typed_entries
                if str(item.get("kind") or "").strip().lower().replace("-", "_")
                in accepted_kinds
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
    if visual_comparison not in {
        "pass",
        "passed",
        "success",
        "approved",
        "match",
        "matched",
        "matches",
    }:
        errors.append(f"{relative} ui_verification.visual_comparison must pass")
    return errors
