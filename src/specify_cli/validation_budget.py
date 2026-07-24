"""Shared logical validation gates for the Implement-to-Review delivery flow."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal

from .atomic_io import atomic_write_text, interprocess_lock, read_local_state_text


ValidationStage = Literal["implement", "review"]
ValidationPurpose = Literal["baseline", "convergence", "delivery"]
ValidationStatus = Literal["running", "passed", "failed", "interrupted"]
ValidationFailureKind = Literal[
    "assertion",
    "verification",
    "harness",
    "environment",
    "runner_timeout",
    "runner_terminated",
    "cancelled",
    "unknown",
]
DEFAULT_BUDGET_REF = "implementation-review/validation-runs.json"
MAX_VALIDATION_EPOCHS = 3
LEDGER_VERSION = 2

_VALID_STAGES = {"implement", "review"}
_VALID_PURPOSES = {"baseline", "convergence", "delivery"}
_VALID_STATUSES = {"running", "passed", "failed", "interrupted"}
_VALID_FAILURE_KINDS = {
    "assertion",
    "verification",
    "harness",
    "environment",
    "runner_timeout",
    "runner_terminated",
    "cancelled",
    "unknown",
}


class ValidationBudgetError(ValueError):
    """Raised when a validation attempt would violate the shared gate contract."""


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
        or max_epochs != MAX_VALIDATION_EPOCHS
    ):
        raise ValidationBudgetError(
            "validation max_epochs must equal 3 so Review always retains its "
            "delivery gate"
        )
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


def _validate_active_stage_owner(feature: Path, stage: str) -> None:
    """Prevent Implement from pre-authoring Review delivery evidence."""

    if not (feature / "workflow.json").is_file():
        return
    from .workflow_runtime import WorkflowRuntimeError, show_workflow

    try:
        workflow = show_workflow(feature).get("data")
    except (WorkflowRuntimeError, OSError, ValueError) as exc:
        raise ValidationBudgetError(
            f"validation cannot verify active workflow ownership: {exc}"
        ) from exc
    if not isinstance(workflow, dict):
        raise ValidationBudgetError(
            "validation cannot verify active workflow ownership"
        )
    if workflow.get("stage") != stage or workflow.get("status") != "active":
        raise ValidationBudgetError(
            f"validation {stage} gate requires active {stage} workflow ownership"
        )


def _new_ledger(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": LEDGER_VERSION,
        "mode": "feature_epochs",
        "budget_scope": "implement-review",
        "max_epochs": policy["max_epochs"],
        "runs": [],
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runs_sha256(runs: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        runs,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _required_string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationBudgetError(f"{label} must be a list")
    return _unique_strings(value, label=label, required=False)


def _legacy_purpose(value: object) -> tuple[str, str | None]:
    normalized = str(value or "").strip().lower()
    if normalized in _VALID_PURPOSES:
        return normalized, None
    for purpose in ("baseline", "convergence", "delivery"):
        if normalized.startswith(f"{purpose}-"):
            return purpose, f"purpose:{normalized}->{purpose}"
    raise ValidationBudgetError(
        f"legacy validation run has unsupported purpose: {normalized or 'empty'}"
    )


def _legacy_status(value: object) -> tuple[str, str | None, str | None]:
    normalized = str(value or "").strip().lower()
    if normalized in {"running", "passed"}:
        return normalized, None, None
    if normalized == "failed":
        return "failed", "assertion", None
    if normalized in {
        "failed-timeout",
        "timeout",
        "timed-out",
        "runner-timeout",
    }:
        return (
            "interrupted",
            "runner_timeout",
            f"status:{normalized}->interrupted",
        )
    if normalized in {"interrupted", "runner-terminated", "cancelled"}:
        failure_kind = (
            "cancelled" if normalized == "cancelled" else "runner_terminated"
        )
        return "interrupted", failure_kind, None
    raise ValidationBudgetError(
        f"legacy validation run has unsupported status: {normalized or 'empty'}"
    )


def _attempt_payload(
    *,
    attempt_id: str,
    fingerprint: str,
    commands: list[str],
    covered_task_ids: list[str],
    status: str,
    failure_kind: str | None,
    evidence_refs: list[str],
    summary: str,
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    return {
        "attempt_id": attempt_id,
        "fingerprint": fingerprint,
        "commands": commands,
        "covered_task_ids": covered_task_ids,
        "status": status,
        "failure_kind": failure_kind,
        "evidence_refs": evidence_refs,
        "summary": summary,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _sync_run_from_attempt(run: dict[str, Any], attempt: dict[str, Any]) -> None:
    for field in (
        "attempt_id",
        "fingerprint",
        "commands",
        "covered_task_ids",
        "status",
        "failure_kind",
        "evidence_refs",
        "summary",
        "started_at",
        "completed_at",
    ):
        value = attempt[field]
        run[field] = list(value) if isinstance(value, list) else value


def _migrate_v1_ledger(
    ledger: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    raw_runs = ledger.get("runs")
    if not isinstance(raw_runs, list) or any(
        not isinstance(item, dict) for item in raw_runs
    ):
        raise ValidationBudgetError("validation ledger runs must be a list of objects")
    legacy_digest = _runs_sha256(raw_runs)
    gates: list[dict[str, Any]] = []
    by_gate: dict[tuple[str, str], dict[str, Any]] = {}
    normalization_codes: list[str] = []
    for legacy_index, raw in enumerate(raw_runs, start=1):
        stage = str(raw.get("stage") or "").strip().lower()
        if stage not in _VALID_STAGES:
            raise ValidationBudgetError(
                f"legacy validation run {legacy_index} has unsupported stage: "
                f"{stage or 'empty'}"
            )
        purpose, purpose_code = _legacy_purpose(raw.get("purpose"))
        if (stage == "review") != (purpose == "delivery"):
            raise ValidationBudgetError(
                f"legacy validation run {legacy_index} has incompatible stage/purpose"
            )
        status, failure_kind, status_code = _legacy_status(raw.get("status"))
        fingerprint = str(raw.get("fingerprint") or "").strip()
        if not fingerprint:
            raise ValidationBudgetError(
                f"legacy validation run {legacy_index} fingerprint is required"
            )
        commands = _required_string_list(
            raw.get("commands"), label=f"legacy run {legacy_index} commands"
        )
        if not commands:
            raise ValidationBudgetError(
                f"legacy validation run {legacy_index} commands must not be empty"
            )
        covered_task_ids = _required_string_list(
            raw.get("covered_task_ids", []),
            label=f"legacy run {legacy_index} covered_task_ids",
        )
        evidence_refs = _required_string_list(
            raw.get("evidence_refs", []),
            label=f"legacy run {legacy_index} evidence_refs",
        )
        summary = str(raw.get("summary") or "").strip()
        gate_key = (stage, purpose)
        run = by_gate.get(gate_key)
        if run is None:
            run = {
                "run_id": f"V{len(gates) + 1}",
                "stage": stage,
                "purpose": purpose,
                "attempts": [],
            }
            gates.append(run)
            by_gate[gate_key] = run
        attempt_number = len(run["attempts"]) + 1
        attempt = _attempt_payload(
            attempt_id=f"{run['run_id']}-A{attempt_number}",
            fingerprint=fingerprint,
            commands=commands,
            covered_task_ids=covered_task_ids,
            status=status,
            failure_kind=failure_kind,
            evidence_refs=evidence_refs,
            summary=summary,
            started_at=str(raw.get("started_at") or ""),
            completed_at=str(raw.get("completed_at") or ""),
        )
        run["attempts"].append(attempt)
        _sync_run_from_attempt(run, attempt)
        for code in (purpose_code, status_code):
            if code:
                normalization_codes.append(
                    f"{raw.get('run_id') or f'V{legacy_index}'}:{code}"
                )
    migrated = {
        "version": LEDGER_VERSION,
        "mode": "feature_epochs",
        "budget_scope": "implement-review",
        "max_epochs": policy["max_epochs"],
        "runs": gates,
        "migration": {
            "from_version": 1,
            "legacy_run_count": len(raw_runs),
            "legacy_runs_sha256": legacy_digest,
            "legacy_runs": deepcopy(raw_runs),
            "normalization_codes": normalization_codes,
        },
    }
    return migrated


def _validate_attempt(
    attempt: dict[str, Any],
    *,
    run_id: str,
    attempt_index: int,
) -> None:
    label = f"validation {run_id} attempt {attempt_index}"
    expected_id = f"{run_id}-A{attempt_index}"
    if attempt.get("attempt_id") != expected_id:
        raise ValidationBudgetError(f"{label} attempt_id must be {expected_id}")
    fingerprint = attempt.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint.strip():
        raise ValidationBudgetError(f"{label} fingerprint is required")
    commands = _required_string_list(
        attempt.get("commands"), label=f"{label} commands"
    )
    if not commands:
        raise ValidationBudgetError(f"{label} commands must not be empty")
    _required_string_list(
        attempt.get("covered_task_ids", []),
        label=f"{label} covered_task_ids",
    )
    status = str(attempt.get("status") or "").strip()
    if status not in _VALID_STATUSES:
        raise ValidationBudgetError(
            f"{label} has unsupported status: {status or 'empty'}"
        )
    failure_kind = attempt.get("failure_kind")
    if failure_kind is not None and failure_kind not in _VALID_FAILURE_KINDS:
        raise ValidationBudgetError(
            f"{label} has unsupported failure_kind: {failure_kind}"
        )
    if status in {"failed", "interrupted"} and failure_kind is None:
        raise ValidationBudgetError(f"{label} {status} requires failure_kind")
    if status in {"running", "passed"} and failure_kind is not None:
        raise ValidationBudgetError(
            f"{label} {status} must not declare failure_kind"
        )
    if status == "failed" and failure_kind not in {"assertion", "verification"}:
        raise ValidationBudgetError(
            f"{label} failed requires assertion or verification failure_kind"
        )
    if status == "interrupted" and failure_kind not in {
        "harness",
        "environment",
        "runner_timeout",
        "runner_terminated",
        "cancelled",
        "unknown",
    }:
        raise ValidationBudgetError(
            f"{label} interrupted cannot use assertion or verification failure_kind"
        )
    evidence_refs = _required_string_list(
        attempt.get("evidence_refs", []), label=f"{label} evidence_refs"
    )
    summary = attempt.get("summary")
    if not isinstance(summary, str):
        raise ValidationBudgetError(f"{label} summary must be a string")
    if status != "running" and (not evidence_refs or not summary.strip()):
        raise ValidationBudgetError(
            f"{label} terminal state requires evidence_refs and summary"
        )
    for field in ("started_at", "completed_at"):
        if not isinstance(attempt.get(field, ""), str):
            raise ValidationBudgetError(f"{label} {field} must be a string")
    if status == "running" and attempt.get("completed_at"):
        raise ValidationBudgetError(f"{label} running state cannot be completed")


def _validate_v2_ledger(
    ledger: dict[str, Any], policy: dict[str, Any]
) -> None:
    if ledger.get("version") != LEDGER_VERSION:
        raise ValidationBudgetError(
            f"validation ledger version must be {LEDGER_VERSION}"
        )
    if ledger.get("mode") != "feature_epochs":
        raise ValidationBudgetError("validation ledger mode must be feature_epochs")
    if ledger.get("budget_scope") != "implement-review":
        raise ValidationBudgetError(
            "validation ledger budget_scope must be implement-review"
        )
    if ledger.get("max_epochs") != policy["max_epochs"]:
        raise ValidationBudgetError(
            "validation ledger max_epochs conflicts with task-index"
        )
    runs = ledger.get("runs")
    if not isinstance(runs, list) or any(not isinstance(item, dict) for item in runs):
        raise ValidationBudgetError("validation ledger runs must be a list of objects")
    if len(runs) > policy["max_epochs"]:
        raise ValidationBudgetError(
            "validation ledger already exceeds its logical-gate budget"
        )
    seen_gates: set[tuple[str, str]] = set()
    running_attempts = 0
    last_purpose_order = -1
    purpose_order = {"baseline": 0, "convergence": 1, "delivery": 2}
    for index, run in enumerate(runs, start=1):
        run_id = f"V{index}"
        if run.get("run_id") != run_id:
            raise ValidationBudgetError(
                f"validation logical gate {index} run_id must be {run_id}"
            )
        stage = str(run.get("stage") or "").strip()
        purpose = str(run.get("purpose") or "").strip()
        if stage not in _VALID_STAGES:
            raise ValidationBudgetError(
                f"validation {run_id} has unsupported stage: {stage or 'empty'}"
            )
        if purpose not in _VALID_PURPOSES:
            raise ValidationBudgetError(
                f"validation {run_id} has unsupported purpose: {purpose or 'empty'}"
            )
        if (stage == "review") != (purpose == "delivery"):
            raise ValidationBudgetError(
                f"validation {run_id} has incompatible stage/purpose"
            )
        if purpose_order[purpose] <= last_purpose_order:
            raise ValidationBudgetError(
                "validation logical gates must remain ordered as "
                "baseline, convergence, then delivery"
            )
        last_purpose_order = purpose_order[purpose]
        gate_key = (stage, purpose)
        if gate_key in seen_gates:
            raise ValidationBudgetError(
                f"validation ledger has duplicate logical gate: {stage}/{purpose}"
            )
        seen_gates.add(gate_key)
        attempts = run.get("attempts")
        if not isinstance(attempts, list) or not attempts or any(
            not isinstance(item, dict) for item in attempts
        ):
            raise ValidationBudgetError(
                f"validation {run_id} attempts must be a non-empty list of objects"
            )
        for attempt_index, attempt in enumerate(attempts, start=1):
            _validate_attempt(
                attempt, run_id=run_id, attempt_index=attempt_index
            )
            if (
                attempt.get("status") == "running"
                and attempt_index != len(attempts)
            ):
                raise ValidationBudgetError(
                    f"validation {run_id} only its latest attempt may be running"
                )
            running_attempts += attempt.get("status") == "running"
        latest = attempts[-1]
        for field in (
            "attempt_id",
            "fingerprint",
            "commands",
            "covered_task_ids",
            "status",
            "failure_kind",
            "evidence_refs",
            "summary",
            "started_at",
            "completed_at",
        ):
            if run.get(field) != latest.get(field):
                raise ValidationBudgetError(
                    f"validation {run_id} {field} must match its latest attempt"
                )
    if running_attempts > 1:
        raise ValidationBudgetError(
            "validation ledger may contain only one running attempt"
        )
    _validate_migration_provenance(ledger, policy)


def _legacy_attempt_matches(
    actual: Mapping[str, Any], expected: Mapping[str, Any]
) -> bool:
    immutable_fields = (
        "attempt_id",
        "fingerprint",
        "commands",
        "covered_task_ids",
        "started_at",
    )
    if any(actual.get(field) != expected.get(field) for field in immutable_fields):
        return False
    if expected.get("status") != "running":
        return actual == expected
    if actual.get("status") == "running":
        return actual == expected
    return actual.get("status") in {"passed", "failed", "interrupted"}


def _validate_migration_provenance(
    ledger: Mapping[str, Any], policy: dict[str, Any]
) -> None:
    migration = ledger.get("migration")
    if migration is None:
        return
    if not isinstance(migration, Mapping) or migration.get("from_version") != 1:
        raise ValidationBudgetError(
            "validation ledger migration provenance is invalid"
        )
    legacy_runs = migration.get("legacy_runs")
    if not isinstance(legacy_runs, list) or any(
        not isinstance(item, dict) for item in legacy_runs
    ):
        raise ValidationBudgetError(
            "validation ledger migration must preserve legacy_runs"
        )
    if migration.get("legacy_run_count") != len(legacy_runs):
        raise ValidationBudgetError(
            "validation ledger migration legacy_run_count is invalid"
        )
    if migration.get("legacy_runs_sha256") != _runs_sha256(legacy_runs):
        raise ValidationBudgetError(
            "validation ledger migration legacy history digest is invalid"
        )
    expected = _migrate_v1_ledger({"runs": deepcopy(legacy_runs)}, policy)
    expected_runs = expected["runs"]
    actual_runs = ledger.get("runs")
    if not isinstance(actual_runs, list) or len(actual_runs) < len(expected_runs):
        raise ValidationBudgetError(
            "validation ledger dropped migrated logical-gate history"
        )
    for gate_index, expected_gate in enumerate(expected_runs):
        actual_gate = actual_runs[gate_index]
        if (
            actual_gate.get("run_id") != expected_gate.get("run_id")
            or actual_gate.get("stage") != expected_gate.get("stage")
            or actual_gate.get("purpose") != expected_gate.get("purpose")
        ):
            raise ValidationBudgetError(
                "validation ledger rewrote migrated logical-gate history"
            )
        expected_attempts = expected_gate["attempts"]
        actual_attempts = actual_gate.get("attempts")
        if not isinstance(actual_attempts, list) or len(actual_attempts) < len(
            expected_attempts
        ):
            raise ValidationBudgetError(
                "validation ledger dropped migrated attempt history"
            )
        for attempt_index, expected_attempt in enumerate(expected_attempts):
            if not _legacy_attempt_matches(
                actual_attempts[attempt_index], expected_attempt
            ):
                raise ValidationBudgetError(
                    "validation ledger rewrote migrated attempt history"
                )


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
    migration = ledger.get("migration")
    legacy_floor_matches = (
        isinstance(migration, dict)
        and migration.get("legacy_run_count") == used_epochs
        and str(migration.get("legacy_runs_sha256") or "").strip()
        == str(floor.get("consumed_runs_sha256") or "").strip()
    )
    if len(runs) < used_epochs and not legacy_floor_matches:
        raise ValidationBudgetError(
            "validation ledger was reset below the implementation handoff floor"
        )
    expected_digest = str(floor.get("consumed_runs_sha256") or "").strip()
    if (
        expected_digest
        and _runs_sha256(runs[:used_epochs]) != expected_digest
        and not legacy_floor_matches
    ):
        raise ValidationBudgetError(
            "validation ledger history digest conflicts with the implementation handoff"
        )


def _load_ledger(path: Path, *, feature: Path, policy: dict[str, Any]) -> dict[str, Any]:
    ledger = (
        _read_json_object(path, root=feature)
        if path.exists()
        else _new_ledger(policy)
    )
    version = ledger.get("version")
    if version == 1:
        ledger = _migrate_v1_ledger(ledger, policy)
    elif version != LEDGER_VERSION:
        raise ValidationBudgetError(
            f"validation ledger version must be 1 or {LEDGER_VERSION}"
        )
    _validate_v2_ledger(ledger, policy)
    _validate_handoff_history(feature, ledger, policy)
    return ledger


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def _validation_next_action(run: Mapping[str, Any] | None) -> str:
    if run is None:
        return "Open the next applicable logical validation gate."
    status = str(run.get("status") or "")
    if status == "running":
        return (
            "Run or resume this exact attempt. If its runner no longer exists, "
            "finish it as interrupted before starting the retry."
        )
    if status == "interrupted":
        if run.get("failure_kind") == "runner_timeout":
            return (
                "Do not rerun the whole gate blindly. Determine whether the suite "
                "legitimately exceeds the runner ceiling; isolate the last active "
                "test with open-handle/process-exit diagnostics, or split the "
                "recorded command into deterministic bounded shards, then retry "
                "this same logical gate."
            )
        return (
            "Repair or re-establish the runner/harness, then retry this same "
            "logical gate; no additional gate is consumed."
        )
    if status == "failed":
        return (
            "Diagnose and repair the assertion or verification failure, produce "
            "a new source fingerprint, then retry this same logical gate."
        )
    return (
        "Continue to the next applicable logical gate; do not rerun the same "
        "scope on an unchanged fingerprint."
    )


def _run_response(
    run: dict[str, Any],
    *,
    reused: bool,
    policy: dict[str, Any],
    used_epochs: int,
    used_attempts: int,
) -> dict[str, Any]:
    return {
        **run,
        "reused": reused,
        "ledger_ref": policy["budget_ref"],
        "max_epochs": policy["max_epochs"],
        "used_epochs": used_epochs,
        "remaining_epochs": policy["max_epochs"] - used_epochs,
        "used_attempts": used_attempts,
        "next_action": _validation_next_action(run),
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
    """Reserve an attempt inside one logical validation gate.

    The three-epoch budget counts baseline, convergence, and delivery gates.
    Retries stay inside their gate, so an interrupted tool execution cannot
    consume Review's delivery gate.
    """

    root, feature = _resolved_feature(project_root, feature_dir)
    policy = _policy(feature, root=root)
    if stage not in _VALID_STAGES:
        raise ValidationBudgetError("validation stage must be implement or review")
    if purpose not in _VALID_PURPOSES:
        raise ValidationBudgetError(
            "validation purpose must be baseline, convergence, or delivery"
        )
    if (stage == "review") != (purpose == "delivery"):
        raise ValidationBudgetError(
            "implement epochs use baseline/convergence; review epochs use delivery"
        )
    _validate_active_stage_owner(feature, stage)
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
        used_attempts = sum(len(run["attempts"]) for run in runs)
        gate = next(
            (
                run
                for run in runs
                if run.get("stage") == stage and run.get("purpose") == purpose
            ),
            None,
        )
        active_run = next(
            (run for run in runs if run.get("status") == "running"),
            None,
        )
        if gate is not None:
            same_scope = (
                gate.get("fingerprint") == normalized_fingerprint
                and gate.get("commands") == normalized_commands
                and gate.get("covered_task_ids") == normalized_tasks
            )
            if gate.get("status") == "running":
                if not same_scope:
                    raise ValidationBudgetError(
                        f"validation attempt {gate.get('attempt_id')} is already running"
                    )
                return _run_response(
                    gate,
                    reused=True,
                    policy=policy,
                    used_epochs=len(runs),
                    used_attempts=used_attempts,
                )
            if active_run is not None and active_run is not gate:
                raise ValidationBudgetError(
                    f"validation attempt {active_run.get('attempt_id')} is already running"
                )
            if gate.get("status") == "passed" and same_scope:
                return _run_response(
                    gate,
                    reused=True,
                    policy=policy,
                    used_epochs=len(runs),
                    used_attempts=used_attempts,
                )
            if (
                gate.get("status") == "failed"
                and gate.get("fingerprint") == normalized_fingerprint
            ):
                raise ValidationBudgetError(
                    "failed validation cannot be retried with an unchanged fingerprint"
                )
            attempt_id = f"{gate['run_id']}-A{len(gate['attempts']) + 1}"
            attempt = _attempt_payload(
                attempt_id=attempt_id,
                fingerprint=normalized_fingerprint,
                commands=normalized_commands,
                covered_task_ids=normalized_tasks,
                status="running",
                failure_kind=None,
                evidence_refs=[],
                summary="",
                started_at=_utc_now(),
                completed_at="",
            )
            gate["attempts"].append(attempt)
            _sync_run_from_attempt(gate, attempt)
            _write_ledger(path, ledger)
            return _run_response(
                gate,
                reused=False,
                policy=policy,
                used_epochs=len(runs),
                used_attempts=used_attempts + 1,
            )
        purposes = [
            str(run.get("purpose") or "")
            for run in runs
            if isinstance(run, dict)
        ]
        if purpose == "baseline" and purposes:
            raise ValidationBudgetError(
                "baseline is an early optional gate and cannot start after "
                "another logical gate"
            )
        if purpose == "convergence" and "delivery" in purposes:
            raise ValidationBudgetError(
                "convergence cannot start after Review delivery"
            )
        if any(
            run.get("status") == "failed"
            and run.get("fingerprint") == normalized_fingerprint
            for run in runs
        ):
            raise ValidationBudgetError(
                "failed validation cannot be retried with an unchanged fingerprint"
            )
        if active_run is not None:
            raise ValidationBudgetError(
                f"validation attempt {active_run.get('attempt_id')} is already running"
            )
        if len(runs) >= policy["max_epochs"]:
            raise ValidationBudgetError(
                "validation logical-gate budget exhausted: maximum of "
                f"{policy['max_epochs']} epochs"
            )
        run_id = f"V{len(runs) + 1}"
        attempt = _attempt_payload(
            attempt_id=f"{run_id}-A1",
            fingerprint=normalized_fingerprint,
            commands=normalized_commands,
            covered_task_ids=normalized_tasks,
            status="running",
            failure_kind=None,
            evidence_refs=[],
            summary="",
            started_at=_utc_now(),
            completed_at="",
        )
        run = {
            "run_id": run_id,
            "stage": stage,
            "purpose": purpose,
            "attempts": [attempt],
        }
        _sync_run_from_attempt(run, attempt)
        runs.append(run)
        _write_ledger(path, ledger)
        return _run_response(
            run,
            reused=False,
            policy=policy,
            used_epochs=len(runs),
            used_attempts=used_attempts + 1,
        )


def complete_validation_epoch(
    project_root: Path,
    feature_dir: Path | str,
    *,
    run_id: str,
    status: Literal["passed", "failed", "interrupted"],
    evidence_refs: list[str],
    summary: str,
    failure_kind: ValidationFailureKind | None = None,
) -> dict[str, Any]:
    """Close the active attempt without conflating interruption with failure."""

    root, feature = _resolved_feature(project_root, feature_dir)
    policy = _policy(feature, root=root)
    normalized_id = run_id.strip()
    if status not in {"passed", "failed", "interrupted"}:
        raise ValidationBudgetError(
            "validation status must be passed, failed, or interrupted"
        )
    normalized_failure_kind = (
        str(failure_kind).strip() if failure_kind is not None else None
    )
    if status == "passed" and normalized_failure_kind is not None:
        raise ValidationBudgetError(
            "passed validation must not declare failure_kind"
        )
    if status == "failed" and normalized_failure_kind is None:
        normalized_failure_kind = "assertion"
    if status == "interrupted" and normalized_failure_kind is None:
        normalized_failure_kind = "runner_terminated"
    if (
        normalized_failure_kind is not None
        and normalized_failure_kind not in _VALID_FAILURE_KINDS
    ):
        raise ValidationBudgetError(
            "validation failure_kind must be assertion, verification, harness, "
            "environment, runner_timeout, runner_terminated, cancelled, or unknown"
        )
    if status == "failed" and normalized_failure_kind not in {
        "assertion",
        "verification",
    }:
        raise ValidationBudgetError(
            "failed validation requires assertion or verification failure_kind; "
            "runner, harness, and environment loss is interrupted"
        )
    if status == "interrupted" and normalized_failure_kind in {
        "assertion",
        "verification",
    }:
        raise ValidationBudgetError(
            "assertion or verification verdict must be failed, not interrupted"
        )
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
                and run.get("failure_kind") == normalized_failure_kind
                and run.get("evidence_refs") == normalized_evidence
                and run.get("summary") == normalized_summary
            ):
                return _run_response(
                    run,
                    reused=True,
                    policy=policy,
                    used_epochs=len(ledger["runs"]),
                    used_attempts=sum(
                        len(item["attempts"]) for item in ledger["runs"]
                    ),
                )
            raise ValidationBudgetError(f"validation run {normalized_id} is already closed")
        _validate_active_stage_owner(feature, str(run.get("stage") or ""))
        attempt = run["attempts"][-1]
        attempt["status"] = status
        attempt["failure_kind"] = normalized_failure_kind
        attempt["evidence_refs"] = normalized_evidence
        attempt["summary"] = normalized_summary
        attempt["completed_at"] = _utc_now()
        _sync_run_from_attempt(run, attempt)
        _write_ledger(path, ledger)
        return _run_response(
            run,
            reused=False,
            policy=policy,
            used_epochs=len(ledger["runs"]),
            used_attempts=sum(len(item["attempts"]) for item in ledger["runs"]),
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
    used_attempts = sum(len(run["attempts"]) for run in runs)
    return {
        **ledger,
        "used_epochs": used,
        "remaining_epochs": policy["max_epochs"] - used,
        "used_attempts": used_attempts,
        "ledger_ref": policy["budget_ref"],
        "runs_sha256": _runs_sha256(runs),
        "next_action": _validation_next_action(runs[-1] if runs else None),
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
