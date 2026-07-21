"""Shared validation-epoch budget for the implement-to-review delivery flow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal

from .atomic_io import atomic_write_text, interprocess_lock, read_local_state_text


ValidationStage = Literal["implement", "review"]
ValidationPurpose = Literal["baseline", "convergence", "delivery"]
ValidationStatus = Literal["running", "passed", "failed"]
DEFAULT_BUDGET_REF = "implementation-review/validation-runs.json"
MAX_VALIDATION_EPOCHS = 3


class ValidationBudgetError(ValueError):
    """Raised when a validation run would violate the shared epoch contract."""


def _unique_strings(values: list[str], *, label: str, required: bool) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValidationBudgetError(f"{label} must contain nonblank strings")
        normalized = value.strip()
        if normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    if required and not result:
        raise ValidationBudgetError(f"{label} must not be empty")
    return result


def _resolved_feature(project_root: Path, feature_dir: Path | str) -> tuple[Path, Path]:
    root = project_root.resolve(strict=False)
    feature = Path(feature_dir)
    if not feature.is_absolute():
        feature = root / feature
    feature = feature.resolve(strict=False)
    try:
        relative = feature.relative_to(root)
    except ValueError as exc:
        raise ValidationBudgetError("feature_dir must stay inside project_root") from exc
    if not relative.parts:
        raise ValidationBudgetError("feature_dir must identify a child directory")
    return root, feature


def _read_json_object(path: Path, *, root: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(read_local_state_text(path, root=root))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValidationBudgetError(f"invalid validation state at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationBudgetError(f"validation state at {path} must be an object")
    return payload


def _policy(feature: Path, *, root: Path) -> dict[str, Any]:
    task_index = _read_json_object(feature / "task-index.json", root=root)
    handoff = _read_json_object(feature / "implementation-handoff.json", root=root)
    raw_policy = task_index.get("validation_policy")
    if not isinstance(raw_policy, dict):
        raw_policy = handoff.get("validation_policy")
    if not isinstance(raw_policy, dict) or raw_policy.get("mode") != "feature_epochs":
        raise ValidationBudgetError(
            "task-index.json does not enable feature_epochs validation"
        )
    max_epochs = raw_policy.get("max_epochs")
    if (
        isinstance(max_epochs, bool)
        or not isinstance(max_epochs, int)
        or not 1 <= max_epochs <= MAX_VALIDATION_EPOCHS
    ):
        raise ValidationBudgetError("validation max_epochs must be an integer from 1 to 3")
    if raw_policy.get("budget_scope") != "implement-review":
        raise ValidationBudgetError("validation budget_scope must be implement-review")
    budget_ref = str(raw_policy.get("budget_ref") or "").strip()
    if not budget_ref:
        raise ValidationBudgetError("validation budget_ref is required")
    windows_ref = PureWindowsPath(budget_ref)
    posix_ref = PurePosixPath(budget_ref.replace("\\", "/"))
    if (
        windows_ref.is_absolute()
        or windows_ref.drive
        or posix_ref.is_absolute()
        or any(part in {"", ".", ".."} for part in posix_ref.parts)
    ):
        raise ValidationBudgetError("validation budget_ref must be a safe relative path")
    if raw_policy.get("heavy_gate_owner") != "leader":
        raise ValidationBudgetError("validation heavy_gate_owner must be leader")
    return {
        "max_epochs": max_epochs,
        "budget_ref": posix_ref.as_posix(),
    }


def _ledger_path(feature: Path, policy: dict[str, Any]) -> Path:
    path = (feature / Path(*PurePosixPath(policy["budget_ref"]).parts)).resolve(
        strict=False
    )
    try:
        path.relative_to(feature)
    except ValueError as exc:
        raise ValidationBudgetError("validation budget_ref escapes feature_dir") from exc
    return path


def _new_ledger(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": 1,
        "mode": "feature_epochs",
        "budget_scope": "implement-review",
        "max_epochs": policy["max_epochs"],
        "runs": [],
    }


def _runs_sha256(runs: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        runs,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_handoff_history(
    feature: Path,
    ledger: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    handoff_path = feature / "implementation-handoff.json"
    if not handoff_path.is_file():
        return
    handoff = _read_json_object(handoff_path, root=feature)
    floor = handoff.get("validation_budget")
    if not isinstance(floor, dict):
        return
    if floor.get("ledger_ref") != policy["budget_ref"]:
        raise ValidationBudgetError(
            "validation ledger_ref conflicts with the implementation handoff"
        )
    if floor.get("max_epochs") != policy["max_epochs"]:
        raise ValidationBudgetError(
            "validation max_epochs conflicts with the implementation handoff"
        )
    used_epochs = floor.get("used_epochs")
    if (
        isinstance(used_epochs, bool)
        or not isinstance(used_epochs, int)
        or not 0 <= used_epochs <= policy["max_epochs"]
    ):
        raise ValidationBudgetError(
            "implementation handoff validation used_epochs is invalid"
        )
    runs: list[dict[str, Any]] = ledger["runs"]
    if len(runs) < used_epochs:
        raise ValidationBudgetError(
            "validation ledger was reset below the implementation handoff floor"
        )
    expected_digest = str(floor.get("consumed_runs_sha256") or "").strip()
    if expected_digest and _runs_sha256(runs[:used_epochs]) != expected_digest:
        raise ValidationBudgetError(
            "validation ledger history digest conflicts with the implementation handoff"
        )


def _load_ledger(path: Path, *, feature: Path, policy: dict[str, Any]) -> dict[str, Any]:
    ledger = _read_json_object(path, root=feature) if path.exists() else _new_ledger(policy)
    runs = ledger.get("runs")
    if not isinstance(runs, list) or any(not isinstance(item, dict) for item in runs):
        raise ValidationBudgetError("validation ledger runs must be a list of objects")
    if ledger.get("max_epochs") != policy["max_epochs"]:
        raise ValidationBudgetError("validation ledger max_epochs conflicts with task-index")
    if len(runs) > policy["max_epochs"]:
        raise ValidationBudgetError("validation ledger already exceeds its epoch budget")
    _validate_handoff_history(feature, ledger, policy)
    return ledger


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def _run_response(
    run: dict[str, Any],
    *,
    reused: bool,
    policy: dict[str, Any],
    used_epochs: int,
) -> dict[str, Any]:
    return {
        **run,
        "reused": reused,
        "ledger_ref": policy["budget_ref"],
        "max_epochs": policy["max_epochs"],
        "used_epochs": used_epochs,
        "remaining_epochs": policy["max_epochs"] - used_epochs,
    }


def reserve_validation_epoch(
    project_root: Path,
    feature_dir: Path | str,
    *,
    stage: ValidationStage,
    purpose: ValidationPurpose,
    fingerprint: str,
    commands: list[str],
    covered_task_ids: list[str],
) -> dict[str, Any]:
    """Reserve one fingerprint-bound epoch, reusing an identical active/pass run."""

    root, feature = _resolved_feature(project_root, feature_dir)
    policy = _policy(feature, root=root)
    if stage not in {"implement", "review"}:
        raise ValidationBudgetError("validation stage must be implement or review")
    if purpose not in {"baseline", "convergence", "delivery"}:
        raise ValidationBudgetError(
            "validation purpose must be baseline, convergence, or delivery"
        )
    if (stage == "review") != (purpose == "delivery"):
        raise ValidationBudgetError(
            "implement epochs use baseline/convergence; review epochs use delivery"
        )
    normalized_fingerprint = fingerprint.strip()
    if not normalized_fingerprint:
        raise ValidationBudgetError("validation fingerprint is required")
    normalized_commands = _unique_strings(commands, label="commands", required=True)
    normalized_tasks = _unique_strings(
        covered_task_ids, label="covered_task_ids", required=False
    )
    path = _ledger_path(feature, policy)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with interprocess_lock(lock_path):
        ledger = _load_ledger(path, feature=feature, policy=policy)
        runs: list[dict[str, Any]] = ledger["runs"]
        for run in runs:
            same_epoch = (
                run.get("stage") == stage
                and run.get("purpose") == purpose
                and run.get("fingerprint") == normalized_fingerprint
            )
            if not same_epoch:
                continue
            if run.get("status") == "failed":
                raise ValidationBudgetError(
                    "failed validation cannot be retried with an unchanged fingerprint"
                )
            if (
                run.get("commands") != normalized_commands
                or run.get("covered_task_ids") != normalized_tasks
            ):
                raise ValidationBudgetError(
                    "an epoch already exists for this fingerprint and purpose with a different scope"
                )
            return _run_response(
                run,
                reused=True,
                policy=policy,
                used_epochs=len(runs),
            )
        if any(
            run.get("status") == "failed"
            and run.get("fingerprint") == normalized_fingerprint
            for run in runs
        ):
            raise ValidationBudgetError(
                "failed validation cannot be retried with an unchanged fingerprint"
            )
        active_run = next(
            (run for run in runs if run.get("status") == "running"),
            None,
        )
        if active_run is not None:
            raise ValidationBudgetError(
                f"validation epoch {active_run.get('run_id')} is already running"
            )
        if len(runs) >= policy["max_epochs"]:
            raise ValidationBudgetError(
                f"validation budget exhausted: maximum of {policy['max_epochs']} epochs"
            )
        run = {
            "run_id": f"V{len(runs) + 1}",
            "stage": stage,
            "purpose": purpose,
            "fingerprint": normalized_fingerprint,
            "commands": normalized_commands,
            "covered_task_ids": normalized_tasks,
            "status": "running",
            "evidence_refs": [],
            "summary": "",
        }
        runs.append(run)
        _write_ledger(path, ledger)
        return _run_response(
            run,
            reused=False,
            policy=policy,
            used_epochs=len(runs),
        )


def complete_validation_epoch(
    project_root: Path,
    feature_dir: Path | str,
    *,
    run_id: str,
    status: Literal["passed", "failed"],
    evidence_refs: list[str],
    summary: str,
) -> dict[str, Any]:
    """Close a reserved epoch with compact, reusable evidence references."""

    root, feature = _resolved_feature(project_root, feature_dir)
    policy = _policy(feature, root=root)
    normalized_id = run_id.strip()
    if status not in {"passed", "failed"}:
        raise ValidationBudgetError("validation status must be passed or failed")
    normalized_evidence = _unique_strings(
        evidence_refs, label="evidence_refs", required=True
    )
    normalized_summary = summary.strip()
    if not normalized_summary:
        raise ValidationBudgetError("validation summary is required")
    path = _ledger_path(feature, policy)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with interprocess_lock(lock_path):
        ledger = _load_ledger(path, feature=feature, policy=policy)
        run = next(
            (item for item in ledger["runs"] if item.get("run_id") == normalized_id),
            None,
        )
        if run is None:
            raise ValidationBudgetError(f"unknown validation run_id: {normalized_id}")
        if run.get("status") != "running":
            if (
                run.get("status") == status
                and run.get("evidence_refs") == normalized_evidence
                and run.get("summary") == normalized_summary
            ):
                return _run_response(
                    run,
                    reused=True,
                    policy=policy,
                    used_epochs=len(ledger["runs"]),
                )
            raise ValidationBudgetError(f"validation run {normalized_id} is already closed")
        run["status"] = status
        run["evidence_refs"] = normalized_evidence
        run["summary"] = normalized_summary
        _write_ledger(path, ledger)
        return _run_response(
            run,
            reused=False,
            policy=policy,
            used_epochs=len(ledger["runs"]),
        )


def validation_budget_status(
    project_root: Path, feature_dir: Path | str
) -> dict[str, Any]:
    """Return the shared implement/review budget and its compact run ledger."""

    root, feature = _resolved_feature(project_root, feature_dir)
    policy = _policy(feature, root=root)
    path = _ledger_path(feature, policy)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with interprocess_lock(lock_path):
        ledger = _load_ledger(path, feature=feature, policy=policy)
    runs = [dict(item) for item in ledger["runs"]]
    used = len(runs)
    return {
        **ledger,
        "used_epochs": used,
        "remaining_epochs": policy["max_epochs"] - used,
        "ledger_ref": policy["budget_ref"],
        "runs_sha256": _runs_sha256(runs),
        "runs": runs,
    }


__all__ = [
    "DEFAULT_BUDGET_REF",
    "MAX_VALIDATION_EPOCHS",
    "ValidationBudgetError",
    "complete_validation_epoch",
    "reserve_validation_epoch",
    "validation_budget_status",
]
