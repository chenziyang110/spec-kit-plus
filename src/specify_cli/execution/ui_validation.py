"""Shared UI contract and lifecycle validation helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TASK_DETAIL_RE = re.compile(
    r"(?ms)^##\s+(?P<task_id>T\d+)\b[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)"
)


def _task_contract_applies(task: dict[str, Any]) -> bool:
    ui_contract = task.get("ui_contract")
    ui_requirements = task.get("ui_fidelity_requirements")
    contract_applies = isinstance(ui_contract, dict) and (
        any(
            bool(ui_contract.get(field))
            for field in (
                "design_sources",
                "reference_notes",
                "visual_target",
                "must_preserve",
                "required_states",
                "required_evidence",
            )
        )
        or str(ui_contract.get("fidelity_level") or "none").strip().lower()
        != "none"
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
) -> list[str]:
    """Validate accepted UI lifecycle evidence against persisted artifacts."""

    errors: list[str] = []
    verification = lifecycle.get("ui_verification")
    if not isinstance(verification, dict):
        return [f"{relative} ui_verification is required for a UI-bearing task"]
    if verification.get("applicable") is not True:
        errors.append(f"{relative} ui_verification.applicable must be true")

    contract_check = str(verification.get("contract_check") or "").strip().lower()
    if contract_check not in {"pass", "passed", "approved"}:
        errors.append(f"{relative} ui_verification.contract_check must pass")

    evidence_refs = verification.get("evidence_refs")
    valid_refs = (
        [item.strip() for item in evidence_refs if isinstance(item, str) and item.strip()]
        if isinstance(evidence_refs, list)
        else []
    )
    if not valid_refs:
        errors.append(f"{relative} ui_verification.evidence_refs must be non-empty")
    else:
        for evidence_ref in valid_refs:
            if resolve_feature_artifact_ref(feature_dir, evidence_ref) is None:
                errors.append(
                    f"{relative} ui_verification evidence is missing or outside the feature: "
                    f"{evidence_ref}"
                )

    fidelity_status = (
        str(verification.get("fidelity_status") or "")
        .strip()
        .lower()
        .replace("_", "-")
    )
    if fidelity_status == "pending-human-review":
        human_review_ref = str(verification.get("human_review_ref") or "").strip()
        review_target = f"; review target: {human_review_ref}" if human_review_ref else ""
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
