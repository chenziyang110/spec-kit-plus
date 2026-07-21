"""Resume-audit helpers for sp-implement terminal-state validation."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from specify_cli.execution.evidence import (
    has_any_evidence,
    has_real_entrypoint_consumer_evidence,
    normalize_evidence_label,
)
from specify_cli.execution.implementation_review import (
    AcceptedResidualRisk,
    ControllerCheck,
    FollowUpWork,
    TaskReviewRecord,
    TaskReviewFinding,
    branch_review_path,
    ledger_path,
    load_task_ledger,
    task_review_is_accepted,
)
from specify_cli.execution.ui_validation import (
    invalid_task_ui_contracts,
    obsolete_task_ui_contract_fields,
    ui_task_ids,
    validate_lifecycle_ui_verification,
)
from specify_cli.hooks.checkpoint_serializers import serialize_implement_tracker


TASK_RE = re.compile(
    r"(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b(?P<body>.*)$"
)
TASK_DETAIL_RE = re.compile(
    r"(?ms)^##\s+(?P<task_id>T\d+)\b[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)"
)
CONSUMER_KEYWORDS = (
    "component",
    "form",
    "page",
    "route",
    "router",
    "provider",
    "factory",
    "registry",
    "panel",
    "modal",
    "endpoint",
    "api",
    "client",
    "config",
    "schema",
    "test",
)
TASK_REVIEW_SPEC_VERDICTS = frozenset({"pass", "fail", "cannot_verify_from_diff"})
TASK_REVIEW_QUALITY_VERDICTS = frozenset({"pass", "concerns", "fail"})
TASK_REVIEW_UI_FIDELITY_RESULTS = frozenset(
    {"not_applicable", "pass", "fail", "needs_visual_or_human_review"}
)
TASK_REVIEW_FINAL_ASSESSMENTS = frozenset(
    {"accepted", "fixes_required", "controller_check_required"}
)
TASK_REVIEW_FINDING_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
TASK_REVIEW_FINDING_CATEGORIES = frozenset(
    {"spec", "quality", "evidence", "ui_fidelity", "plan_mandated_defect"}
)
TASK_REVIEW_FINDING_DISPOSITIONS = frozenset(
    {"open", "fixed", "accepted_residual_risk", "follow_up"}
)
TASK_REVIEW_FINDING_SOURCES = frozenset({"findings", "plan_mandated_defects"})
TASK_BLOCKER_CLASSIFICATIONS = frozenset(
    {
        "technical",
        "external",
        "human-action",
        "verification_policy",
        "project_cognition_readiness",
        "baseline_timeout",
    }
)
TASK_BLOCKER_OWNERS = frozenset({"agent", "user", "maintainer", "external-system"})
TASK_BLOCKER_COMPLETION_IMPACTS = frozenset(
    {
        "mandatory_for_completion",
        "optional_cleanup",
        "external_baseline_maintenance",
        "follow_up_risk",
    }
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _parse_tasks(tasks_path: Path) -> list[dict[str, Any]]:
    text = _read_text(tasks_path)
    tasks: list[dict[str, Any]] = []
    for match in TASK_RE.finditer(text):
        task_id = match.group("task_id")
        body = match.group("body").strip()
        detail = _task_detail_body(text, task_id)
        tasks.append(
            {
                "task_id": task_id,
                "checked": match.group("checked").lower() == "x",
                "body": body,
                "consumer_facing": _looks_consumer_facing(body),
                "requires_real_entrypoint": _requires_real_entrypoint_evidence(
                    body, detail
                ),
            }
        )
    return tasks


def _task_detail_body(tasks_text: str, task_id: str) -> str:
    for match in TASK_DETAIL_RE.finditer(tasks_text):
        if match.group("task_id") == task_id:
            return match.group("body").strip()
    return ""


def _requires_real_entrypoint_evidence(*texts: str) -> bool:
    normalized = normalize_evidence_label(" ".join(text for text in texts if text))
    return "real_entrypoint_evidence" in normalized


def _looks_consumer_facing(task_body: str) -> bool:
    lowered = task_body.lower()
    return any(keyword in lowered for keyword in CONSUMER_KEYWORDS)


def _load_worker_result(
    project_root: Path,
    feature_dir: Path,
    task_id: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    gaps: list[str] = []
    ledger_reference, ledger_gaps = _ledger_worker_result_reference(
        feature_dir, task_id
    )
    gaps.extend(ledger_gaps)
    if ledger_reference:
        try:
            candidate = _safe_worker_result_path(
                project_root, feature_dir, ledger_reference
            )
        except ValueError as exc:
            gaps.append(f"unsafe worker_result {ledger_reference}: {exc}")
        else:
            if candidate.exists():
                return _read_worker_result(candidate, task_id), gaps
            gaps.append(f"worker_result is missing: {ledger_reference}")

    for candidate in (
        feature_dir / "worker-results" / f"{task_id}.json",
        feature_dir / "worker-results" / f"{task_id.lower()}.json",
    ):
        if not candidate.exists():
            continue
        return _read_worker_result(candidate, task_id), gaps
    return None, gaps


def _read_worker_result(path: Path, task_id: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"task_id": task_id, "status": "invalid-json", "path": str(path)}
    if not isinstance(payload, dict):
        return {"task_id": task_id, "status": "invalid-payload", "path": str(path)}
    result_task_ids = [
        value.strip()
        for key in ("task_id", "taskId")
        if isinstance((value := payload.get(key)), str) and value.strip()
    ]
    if not result_task_ids:
        return {
            "task_id": task_id,
            "status": "worker result missing task_id",
            "path": str(path),
        }
    mismatched_task_ids = [
        result_task_id
        for result_task_id in result_task_ids
        if result_task_id.upper() != task_id.upper()
    ]
    if mismatched_task_ids:
        return {
            "task_id": task_id,
            "status": "worker result task_id mismatch",
            "path": str(path),
            "result_task_id": mismatched_task_ids[0],
        }
    payload["path"] = str(path)
    return payload


def _ledger_worker_result_reference(
    feature_dir: Path, task_id: str
) -> tuple[str, list[str]]:
    review_ledger_path = ledger_path(feature_dir)
    if not review_ledger_path.is_file():
        return "", []
    ledger_relative = "implementation-review/ledger.json"
    try:
        ledger_entries = load_task_ledger(feature_dir)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return "", [f"{ledger_relative} is malformed for worker_result lookup: {exc}"]
    for entry in ledger_entries:
        if (
            not isinstance(entry.task_id, str)
            or entry.task_id.upper() != task_id.upper()
        ):
            continue
        if not isinstance(entry.worker_result, str):
            return "", [f"{task_id} in {ledger_relative} has malformed worker_result"]
        if not entry.worker_result.strip():
            return "", []
        return entry.worker_result, []
    return "", []


def _safe_worker_result_path(
    project_root: Path, feature_dir: Path, result_relative: str
) -> Path:
    if result_relative != result_relative.strip():
        raise ValueError("leading or trailing whitespace is not allowed")
    if "\\" in result_relative:
        raise ValueError("backslash path separators are not allowed")
    windows_source = PureWindowsPath(result_relative)
    normalized_result_relative = result_relative.replace("\\", "/")
    posix_source = PurePosixPath(normalized_result_relative)
    if (
        Path(result_relative).is_absolute()
        or windows_source.is_absolute()
        or posix_source.is_absolute()
    ):
        raise ValueError("absolute paths are not allowed")
    if windows_source.drive:
        raise ValueError("drive-qualified paths are not allowed")
    if result_relative.startswith(("//", "\\\\")):
        raise ValueError("UNC paths are not allowed")
    if any(part in {"", ".", ".."} for part in normalized_result_relative.split("/")):
        raise ValueError("dot path segments are not allowed")

    parts = posix_source.parts
    if (
        len(parts) == 2
        and parts[0] == "worker-results"
        and posix_source.suffix == ".json"
    ):
        root = feature_dir.resolve(strict=False)
        candidate = (feature_dir / Path(*parts)).resolve(strict=False)
    elif (
        len(parts) == 5
        and parts[:4] == (".specify", "teams", "state", "results")
        and posix_source.suffix == ".json"
    ):
        root = project_root.resolve(strict=False)
        candidate = (project_root / Path(*parts)).resolve(strict=False)
    else:
        raise ValueError(
            "expected worker-results/<task-id>.json or "
            ".specify/teams/state/results/<request-id>.json"
        )

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("resolved path escapes its allowed root") from exc
    return candidate


def _result_has_passed_validation(result: dict[str, Any]) -> bool:
    validations = (
        result.get("validation_results") or result.get("validationResults") or []
    )
    if not isinstance(validations, list) or not validations:
        return False
    statuses = [
        str(item.get("status", "")).lower()
        for item in validations
        if isinstance(item, dict)
    ]
    return bool(statuses) and all(status == "passed" for status in statuses)


def _uses_feature_epoch_validation(feature_dir: Path) -> bool:
    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return False
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    policy = payload.get("validation_policy") if isinstance(payload, dict) else None
    return isinstance(policy, dict) and policy.get("mode") == "feature_epochs"


def _shared_implement_validation_gaps(
    project_root: Path,
    feature_dir: Path,
    checked_task_ids: set[str],
) -> tuple[list[str], str]:
    from .review_runtime import implementation_snapshot_sha256
    from .validation_budget import ValidationBudgetError, validation_budget_status

    try:
        budget = validation_budget_status(project_root, feature_dir)
    except ValidationBudgetError as exc:
        return [f"shared validation budget is invalid: {exc}"], ""
    running = [
        run
        for run in budget["runs"]
        if isinstance(run, dict) and run.get("status") == "running"
    ]
    gaps = []
    if running:
        gaps.append("shared validation has an unfinished running epoch")
    fingerprint = implementation_snapshot_sha256(project_root, feature_dir)
    matching = [
        run
        for run in budget["runs"]
        if isinstance(run, dict)
        and run.get("stage") == "implement"
        and run.get("purpose") == "convergence"
        and run.get("status") == "passed"
        and run.get("fingerprint") == fingerprint
        and checked_task_ids
        <= {
            str(task_id).upper()
            for task_id in run.get("covered_task_ids", [])
            if isinstance(task_id, str)
        }
    ]
    if not matching:
        gaps.append(
            "shared validation requires a fresh passed implement/convergence epoch "
            "covering every checked task"
        )
        return gaps, ""
    run = matching[-1]
    return gaps, f"{budget['ledger_ref']}#{run['run_id']}"


def _shared_validation_lifecycle_gaps(
    feature_dir: Path,
    checked_task_ids: set[str],
    validation_run_ref: str,
) -> list[str]:
    if not validation_run_ref:
        return []
    gaps: list[str] = []
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    for task_id in sorted(checked_task_ids):
        relative = f"implementation-review/tasks/{task_id}.json"
        path = lifecycle_dir / f"{task_id}.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        validation = payload.get("validation") if isinstance(payload, dict) else None
        refs = (
            {
                str(item.get("validation_run_ref") or "").strip()
                for item in validation
                if isinstance(item, dict)
            }
            if isinstance(validation, list)
            else set()
        )
        if validation_run_ref not in refs:
            gaps.append(
                f"{relative} must reference shared validation run {validation_run_ref}"
            )
    return gaps


def _result_has_consumer_evidence(result: dict[str, Any]) -> bool:
    evidence = result.get("consumer_evidence") or result.get("consumerEvidence") or []
    return has_any_evidence(evidence)


def _result_has_real_entrypoint_consumer_evidence(result: dict[str, Any]) -> bool:
    evidence = result.get("consumer_evidence") or result.get("consumerEvidence") or []
    return has_real_entrypoint_consumer_evidence(evidence)


def _tracker_has_open_gaps(feature_dir: Path) -> bool:
    text = _read_text(feature_dir / "implement-tracker.md")
    marker = "## Open Gaps"
    if marker not in text:
        return False
    body = text.split(marker, 1)[1]
    next_section = re.split(r"(?m)^##\s+", body, maxsplit=1)[0]
    meaningful = [
        line.strip()
        for line in next_section.splitlines()
        if line.strip() and line.strip().lower() not in {"- none", "none", "[]"}
    ]
    return any(line.startswith("-") or line.startswith("type:") for line in meaningful)


def _has_nonempty_blocker_evidence(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and all(
            isinstance(item, str) and item.strip() for item in value
        )
    return False


def _task_lifecycle_blocker_gaps(feature_dir: Path) -> list[str]:
    """Validate and surface open task-local blockers, including active tasks."""

    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    if not lifecycle_dir.is_dir():
        return []

    gaps: list[str] = []
    required_fields = (
        "classification",
        "owner",
        "evidence",
        "exact_next_action",
        "approval_question",
        "unblock_criteria",
        "implementation_can_continue",
        "completion_impact",
    )
    for lifecycle_path in sorted(lifecycle_dir.glob("*.json")):
        relative = lifecycle_path.relative_to(feature_dir).as_posix()
        try:
            payload = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            gaps.append(f"{relative} is malformed: {exc}")
            continue
        if not isinstance(payload, dict):
            gaps.append(f"{relative} must contain a top-level object")
            continue
        task_id = str(payload.get("task_id") or lifecycle_path.stem).upper()
        blockers = payload.get("blockers")
        if blockers is None:
            if str(payload.get("status") or "").lower() == "blocked":
                gaps.append(f"{relative} blocked task {task_id} must record blockers")
            continue
        if not isinstance(blockers, list):
            gaps.append(f"{relative} blockers must be a list")
            continue
        if str(payload.get("status") or "").lower() == "blocked" and not blockers:
            gaps.append(f"{relative} blocked task {task_id} must record blockers")
            continue
        for index, blocker in enumerate(blockers, start=1):
            label = f"{relative} blocker {index}"
            if not isinstance(blocker, dict):
                gaps.append(f"{label} must be an object")
                continue
            missing = [field for field in required_fields if field not in blocker]
            if missing:
                gaps.append(f"{label} is missing required fields: {', '.join(missing)}")
                continue

            classification = str(blocker.get("classification") or "").strip()
            owner = str(blocker.get("owner") or "").strip()
            completion_impact = str(blocker.get("completion_impact") or "").strip()
            if classification not in TASK_BLOCKER_CLASSIFICATIONS:
                gaps.append(
                    f"{label} has invalid classification: {classification or 'empty'}"
                )
            if owner not in TASK_BLOCKER_OWNERS:
                gaps.append(f"{label} has invalid owner: {owner or 'empty'}")
            if completion_impact not in TASK_BLOCKER_COMPLETION_IMPACTS:
                gaps.append(
                    f"{label} has invalid completion_impact: {completion_impact or 'empty'}"
                )
            if not _has_nonempty_blocker_evidence(blocker.get("evidence")):
                gaps.append(
                    f"{label} evidence must be a non-empty string or string list"
                )
            for field in ("exact_next_action", "unblock_criteria"):
                if (
                    not isinstance(blocker.get(field), str)
                    or not str(blocker[field]).strip()
                ):
                    gaps.append(f"{label} {field} must be a non-empty string")
            if not isinstance(blocker.get("implementation_can_continue"), bool):
                gaps.append(f"{label} implementation_can_continue must be a boolean")
            approval_question = blocker.get("approval_question")
            if approval_question is not None and not isinstance(approval_question, str):
                gaps.append(f"{label} approval_question must be a string or null")
            if (
                owner in {"user", "maintainer"}
                and not str(approval_question or "").strip()
            ):
                gaps.append(f"{label} approval_question is required for owner {owner}")

            gaps.append(
                f"{task_id}: unresolved {classification or 'unknown'} blocker owned by "
                f"{owner or 'unknown'} ({completion_impact or 'unknown'})"
            )
    return gaps


def _packetized_task_ids(feature_dir: Path) -> tuple[list[str], list[str]]:
    task_packets_dir = feature_dir / "task-packets"
    if not task_packets_dir.is_dir():
        return [], []

    task_ids: set[str] = set()
    gaps: list[str] = []
    for path in sorted(task_packets_dir.glob("*.json")):
        packet_relative = path.relative_to(feature_dir).as_posix()
        expected_task_id = path.stem.upper()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            gaps.append(f"{packet_relative} has malformed packet JSON: {exc}")
            continue
        if not isinstance(payload, dict):
            gaps.append(
                f"{packet_relative} has malformed packet: packet must be a JSON object"
            )
            continue
        packet_task_id = payload.get("task_id")
        if not isinstance(packet_task_id, str) or not packet_task_id.strip():
            gaps.append(f"{packet_relative} has malformed packet task_id")
            continue
        normalized_task_id = packet_task_id.upper()
        if normalized_task_id != expected_task_id:
            gaps.append(
                f"{packet_relative} task_id mismatch: {packet_task_id} does not match {expected_task_id}"
            )
            continue
        task_ids.add(normalized_task_id)
    return sorted(task_ids), gaps


def _uses_agent_native_task_lifecycle(feature_dir: Path) -> bool:
    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.is_file():
        return False
    try:
        payload = json.loads(task_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(payload, dict):
        return False
    version = payload.get("version")
    return isinstance(version, int) and not isinstance(version, bool) and version >= 2


def _packetized_review_gaps(
    feature_dir: Path,
    tasks: list[dict[str, Any]],
    checked_tasks: list[dict[str, Any]],
    *,
    terminal: bool,
) -> list[str]:
    checked_task_ids = {str(task["task_id"]).upper() for task in checked_tasks}
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    obsolete_ui_fields = obsolete_task_ui_contract_fields(feature_dir)
    ui_tasks = ui_task_ids(feature_dir)
    contract_gaps = [
        "task-index.json task "
        f"{task_id} uses obsolete UI fields ({', '.join(fields)}); "
        "regenerate it with the current UI contract"
        for task_id, fields in sorted(obsolete_ui_fields.items())
    ]
    contract_gaps.extend(
        "task-index.json task "
        f"{task_id} has an invalid current UI contract: {', '.join(errors)}"
        for task_id, errors in sorted(invalid_task_ui_contracts(feature_dir).items())
    )
    if lifecycle_dir.is_dir() or _uses_agent_native_task_lifecycle(feature_dir):
        gaps = list(contract_gaps)
        for task_id in sorted(checked_task_ids):
            relative = f"implementation-review/tasks/{task_id}.json"
            lifecycle_path = lifecycle_dir / f"{task_id}.json"
            if not lifecycle_path.is_file():
                gaps.append(f"{relative} is missing for checked task {task_id}")
                continue
            try:
                payload = json.loads(lifecycle_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                gaps.append(f"{relative} is malformed: {exc}")
                continue
            if not isinstance(payload, dict):
                gaps.append(f"{relative} must contain a top-level object")
                continue
            if str(payload.get("task_id") or "").upper() != task_id:
                gaps.append(f"{relative} has mismatched task_id")
            if payload.get("status") != "accepted":
                gaps.append(f"{relative} status must be accepted")
            if not isinstance(payload.get("changed_paths"), list):
                gaps.append(f"{relative} changed_paths must be a list")
            validation = payload.get("validation")
            if not isinstance(validation, list) or not validation:
                gaps.append(f"{relative} validation must be a non-empty list")
            if not isinstance(payload.get("blockers"), list):
                gaps.append(f"{relative} blockers must be a list")
            review = payload.get("review")
            if review is not None and (
                not isinstance(review, dict)
                or not str(review.get("trigger") or "").strip()
                or not str(review.get("verdict") or "").strip()
            ):
                gaps.append(
                    f"{relative} review must contain trigger and verdict when present"
                )
            if task_id in ui_tasks:
                gaps.extend(
                    validate_lifecycle_ui_verification(
                        feature_dir,
                        payload,
                        relative,
                        require_integrated=_uses_feature_epoch_validation(feature_dir),
                    )
                )
        return gaps

    packet_task_ids, packet_gaps = _packetized_task_ids(feature_dir)
    gaps = list(contract_gaps)
    gaps.extend(packet_gaps)
    if not packet_task_ids:
        return gaps

    if terminal:
        for packet_task_id in packet_task_ids:
            if packet_task_id not in checked_task_ids:
                task_known = any(
                    str(task["task_id"]).upper() == packet_task_id for task in tasks
                )
                reason = (
                    "unchecked in tasks.md"
                    if task_known
                    else "missing checked task in tasks.md"
                )
                gaps.append(
                    f"{packet_task_id} packetized task is not checked: {reason}"
                )

    checked_packet_task_ids = sorted(checked_task_ids & set(packet_task_ids))
    if not terminal and not checked_packet_task_ids:
        return gaps

    ledger_relative = "implementation-review/ledger.json"
    branch_review_relative = "implementation-review/branch-review.md"
    review_ledger_path = ledger_path(feature_dir)
    if not review_ledger_path.is_file():
        if terminal:
            gaps.append(f"{ledger_relative} is missing for packetized terminal state")
        else:
            task_list = ", ".join(checked_packet_task_ids)
            gaps.append(
                f"{ledger_relative} is missing for checked packetized tasks: {task_list}"
            )
    else:
        try:
            ledger_entries = load_task_ledger(feature_dir)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            gaps.append(f"{ledger_relative} is malformed: {exc}")
            ledger_entries = []
        entries_by_task: dict[str, Any] = {}
        for entry in ledger_entries:
            if not isinstance(entry.task_id, str) or not isinstance(entry.status, str):
                gaps.append(f"{ledger_relative} contains a malformed task entry")
                continue
            entries_by_task[entry.task_id.upper()] = entry
        for task_id in checked_packet_task_ids:
            entry = entries_by_task.get(task_id)
            if entry is None:
                gaps.append(f"{task_id} is missing from {ledger_relative}")
            elif entry.status != "accepted":
                gaps.append(
                    f"{task_id} in {ledger_relative} is not accepted: {entry.status}"
                )
            else:
                task_brief_reference, task_brief_gap = (
                    _accepted_ledger_artifact_reference(
                        ledger_relative,
                        task_id,
                        "task_brief",
                        entry.task_brief,
                        f"implementation-review/task-briefs/{task_id}.md",
                    )
                )
                if task_brief_gap:
                    gaps.append(task_brief_gap)
                else:
                    gaps.extend(
                        _ledger_artifact_file_gaps(
                            feature_dir, task_id, "task brief", task_brief_reference
                        )
                    )

                review_package_reference, review_package_gap = (
                    _accepted_ledger_artifact_reference(
                        ledger_relative,
                        task_id,
                        "review_package",
                        entry.review_package,
                        f"implementation-review/review-packages/{task_id}.md",
                    )
                )
                if review_package_gap:
                    gaps.append(review_package_gap)
                else:
                    gaps.extend(
                        _ledger_artifact_file_gaps(
                            feature_dir,
                            task_id,
                            "review package",
                            review_package_reference,
                        )
                    )

                task_review_reference, task_review_gap = (
                    _accepted_ledger_task_review_reference(
                        ledger_relative, task_id, entry.task_review
                    )
                )
                if task_review_gap:
                    gaps.append(task_review_gap)
                else:
                    gaps.extend(
                        _task_review_gaps(feature_dir, task_id, task_review_reference)
                    )

    if terminal and not branch_review_path(feature_dir).is_file():
        gaps.append(
            f"{branch_review_relative} is missing for packetized terminal state"
        )

    return gaps


def _accepted_ledger_artifact_reference(
    ledger_relative: str,
    task_id: str,
    field_name: str,
    ledger_value: object,
    expected: str,
) -> tuple[str, str]:
    if not isinstance(ledger_value, str):
        return "", f"{task_id} in {ledger_relative} has malformed {field_name}"
    if not ledger_value.strip():
        return "", f"{task_id} in {ledger_relative} is missing {field_name}"
    if ledger_value != expected:
        return (
            "",
            f"{task_id} in {ledger_relative} has malformed unsafe {field_name} "
            f"{ledger_value}: expected {expected}",
        )
    return ledger_value, ""


def _accepted_ledger_task_review_reference(
    ledger_relative: str,
    task_id: str,
    ledger_task_review: object,
) -> tuple[str, str]:
    return _accepted_ledger_artifact_reference(
        ledger_relative,
        task_id,
        "task_review",
        ledger_task_review,
        f"implementation-review/task-reviews/{task_id}.json",
    )


def _ledger_artifact_file_gaps(
    feature_dir: Path,
    task_id: str,
    artifact_label: str,
    artifact_relative: str,
) -> list[str]:
    if not (feature_dir / artifact_relative).is_file():
        return [f"{task_id} {artifact_label} is missing: {artifact_relative}"]
    return []


def _task_review_gaps(
    feature_dir: Path, task_id: str, ledger_task_review: object
) -> list[str]:
    if isinstance(ledger_task_review, str) and ledger_task_review.strip():
        review_relative = ledger_task_review.strip()
    else:
        review_relative = f"implementation-review/task-reviews/{task_id}.json"

    try:
        review_path = _safe_task_review_path(feature_dir, task_id, review_relative)
    except ValueError as exc:
        return [f"{task_id} task review path is unsafe: {review_relative}: {exc}"]

    if not review_path.is_file():
        return [f"{task_id} task review is missing: {review_relative}"]

    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("task review must contain a JSON object")
        record = _task_review_record_from_payload(payload)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return [f"{task_id} task review is malformed at {review_relative}: {exc}"]

    try:
        if not isinstance(record.task_id, str) or record.task_id.upper() != task_id:
            return [
                f"{task_id} task review has mismatched task_id at {review_relative}"
            ]
        review_accepted = task_review_is_accepted(record)
    except (AttributeError, TypeError, ValueError) as exc:
        return [f"{task_id} task review is malformed at {review_relative}: {exc}"]

    if not review_accepted:
        return [f"{task_id} task review is not accepted at {review_relative}"]
    return []


def _safe_task_review_path(
    feature_dir: Path, task_id: str, review_relative: str
) -> Path:
    windows_source = PureWindowsPath(review_relative)
    normalized_review_relative = review_relative.replace("\\", "/")
    posix_source = PurePosixPath(normalized_review_relative)
    if (
        Path(review_relative).is_absolute()
        or windows_source.is_absolute()
        or posix_source.is_absolute()
    ):
        raise ValueError("absolute paths are not allowed")
    if windows_source.drive:
        raise ValueError("drive-qualified paths are not allowed")
    if review_relative.startswith(("//", "\\\\")):
        raise ValueError("UNC paths are not allowed")
    if any(part in {"", ".", ".."} for part in normalized_review_relative.split("/")):
        raise ValueError("dot path segments are not allowed")

    expected = PurePosixPath("implementation-review", "task-reviews", f"{task_id}.json")
    if posix_source != expected:
        raise ValueError(f"expected {expected.as_posix()}")

    feature_root = feature_dir.resolve(strict=False)
    candidate = (feature_dir / Path(*posix_source.parts)).resolve(strict=False)
    try:
        candidate.relative_to(feature_root)
    except ValueError as exc:
        raise ValueError("resolved path escapes feature directory") from exc
    return candidate


def _task_review_record_from_payload(payload: dict[str, Any]) -> TaskReviewRecord:
    return TaskReviewRecord(
        **{
            **payload,
            "spec_verdict": _required_choice(
                payload, "spec_verdict", TASK_REVIEW_SPEC_VERDICTS
            ),
            "quality_verdict": _required_choice(
                payload, "quality_verdict", TASK_REVIEW_QUALITY_VERDICTS
            ),
            "findings": _task_review_findings_from_payload(payload.get("findings", [])),
            "controller_checks": _controller_checks_from_payload(
                payload.get("controller_checks", [])
            ),
            "plan_mandated_defects": _task_review_findings_from_payload(
                payload.get("plan_mandated_defects", [])
            ),
            "accepted_residual_risks": _accepted_residual_risks_from_payload(
                payload.get("accepted_residual_risks", [])
            ),
            "follow_up_work": _follow_up_work_from_payload(
                payload.get("follow_up_work", [])
            ),
            "ui_fidelity_result": _optional_choice(
                payload,
                "ui_fidelity_result",
                TASK_REVIEW_UI_FIDELITY_RESULTS,
                "not_applicable",
            ),
            "final_assessment": _optional_choice(
                payload,
                "final_assessment",
                TASK_REVIEW_FINAL_ASSESSMENTS,
                "fixes_required",
            ),
        }
    )


def _required_choice(payload: dict[str, Any], key: str, allowed: frozenset[str]) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
    return value


def _optional_choice(
    payload: dict[str, Any],
    key: str,
    allowed: frozenset[str],
    default: str,
) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
    return value


def _required_string(payload: object, key: str) -> str:
    value = _payload_value(payload, key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    if not value.strip():
        raise ValueError(f"{key} must be a nonblank string")
    return value


def _required_int(payload: object, key: str) -> int:
    value = _payload_value(payload, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def _required_payload_choice(payload: object, key: str, allowed: frozenset[str]) -> str:
    value = _required_string(payload, key)
    if value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
    return value


def _optional_payload_choice(
    payload: object,
    key: str,
    allowed: frozenset[str],
    default: str,
) -> str:
    value = _payload_value(payload, key, default=default)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
    return value


def _payload_value(payload: object, key: str, *, default: object = ...):
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
    elif hasattr(payload, key):
        return getattr(payload, key)
    if default is not ...:
        return default
    raise ValueError(f"{key} is required")


def _task_review_findings_from_payload(value: object) -> list[TaskReviewFinding]:
    if not isinstance(value, list):
        raise ValueError("task review findings must be a list")
    findings: list[TaskReviewFinding] = []
    for item in value:
        if not isinstance(item, (TaskReviewFinding, dict)):
            raise ValueError("task review findings must contain objects")
        findings.append(
            TaskReviewFinding(
                severity=_required_payload_choice(
                    item, "severity", TASK_REVIEW_FINDING_SEVERITIES
                ),
                category=_required_payload_choice(
                    item, "category", TASK_REVIEW_FINDING_CATEGORIES
                ),
                file=_required_string(item, "file"),
                line=_required_int(item, "line"),
                summary=_required_string(item, "summary"),
                required_fix=_required_string(item, "required_fix"),
                disposition=_required_payload_choice(
                    item, "disposition", TASK_REVIEW_FINDING_DISPOSITIONS
                ),
            )
        )
    return findings


def _controller_checks_from_payload(value: object) -> list[ControllerCheck]:
    if not isinstance(value, list):
        raise ValueError("controller_checks must be a list")
    checks: list[ControllerCheck] = []
    for item in value:
        if not isinstance(item, (ControllerCheck, dict)):
            raise ValueError("controller_checks must contain objects")
        checks.append(
            ControllerCheck(
                check=_required_string(item, "check"),
                reason=_required_string(item, "reason"),
                evidence_required=_required_string(item, "evidence_required"),
            )
        )
    return checks


def _accepted_residual_risks_from_payload(value: object) -> list[AcceptedResidualRisk]:
    if not isinstance(value, list):
        raise ValueError("accepted_residual_risks must be a list")
    risks: list[AcceptedResidualRisk] = []
    for item in value:
        if not isinstance(item, (AcceptedResidualRisk, dict)):
            raise ValueError("accepted_residual_risks must contain objects")
        risks.append(
            AcceptedResidualRisk(
                finding_index=_required_int(item, "finding_index"),
                reason=_required_string(item, "reason"),
                owner=_required_string(item, "owner"),
                finding_source=_optional_payload_choice(
                    item, "finding_source", TASK_REVIEW_FINDING_SOURCES, "findings"
                ),
            )
        )
    return risks


def _follow_up_work_from_payload(value: object) -> list[FollowUpWork]:
    if not isinstance(value, list):
        raise ValueError("follow_up_work must be a list")
    work_items: list[FollowUpWork] = []
    for item in value:
        if not isinstance(item, (FollowUpWork, dict)):
            raise ValueError("follow_up_work must contain objects")
        work_items.append(
            FollowUpWork(
                finding_index=_required_int(item, "finding_index"),
                description=_required_string(item, "description"),
                target=_required_string(item, "target"),
                finding_source=_optional_payload_choice(
                    item, "finding_source", TASK_REVIEW_FINDING_SOURCES, "findings"
                ),
            )
        )
    return work_items


def audit_implement_resume(project_root: Path, feature_dir: Path) -> dict[str, Any]:
    """Return a conservative resume audit payload for an implement feature dir."""

    resolved_project_root = project_root.resolve(strict=False)
    resolved_feature_dir = (
        feature_dir.resolve(strict=False)
        if feature_dir.is_absolute()
        else (resolved_project_root / feature_dir).resolve(strict=False)
    )
    try:
        relative = resolved_feature_dir.relative_to(resolved_project_root)
    except ValueError as exc:
        raise ValueError("feature_dir must stay inside the current project") from exc
    if not relative.parts:
        raise ValueError("feature_dir must identify a directory below the project root")
    tracker_path = resolved_feature_dir / "implement-tracker.md"
    tasks_path = resolved_feature_dir / "tasks.md"

    if not tracker_path.exists():
        return _payload(
            status="conflict",
            feature_dir=resolved_feature_dir,
            classification="state-conflict",
            trusted=False,
            recommended_status="blocked",
            next_action="Recreate or recover implement-tracker.md before resuming implementation.",
            task_findings=[],
            open_gaps=["implement-tracker.md is missing"],
        )

    tracker = serialize_implement_tracker(tracker_path)
    tracker_status = str(tracker.get("status") or "").strip().lower()
    tasks = _parse_tasks(tasks_path)
    checked_tasks = [task for task in tasks if task["checked"]]
    checked_task_ids = {str(task["task_id"]).upper() for task in checked_tasks}
    feature_epoch_validation = _uses_feature_epoch_validation(resolved_feature_dir)
    all_checked = bool(tasks) and len(checked_tasks) == len(tasks)
    terminal = tracker_status == "resolved" or all_checked
    classification = "terminal-audit-required" if terminal else "clean-active"

    task_findings: list[dict[str, Any]] = []
    evidence_gaps: list[str] = []
    if terminal and not tasks:
        evidence_gaps.append("tasks.md has no task checklist evidence")
    for task in checked_tasks:
        missing: list[str] = []
        result, result_gaps = _load_worker_result(
            resolved_project_root,
            resolved_feature_dir,
            str(task["task_id"]),
        )
        missing.extend(result_gaps)
        if result is None:
            missing.append("missing worker result")
        else:
            result_status = str(result.get("status", "")).lower()
            if result_status in {
                "worker result missing task_id",
                "worker result task_id mismatch",
            }:
                missing.append(result_status)
            elif result_status not in {"success", "done", "done_with_concerns"}:
                missing.append("worker result is not successful")
            else:
                if (
                    not feature_epoch_validation
                    and not _result_has_passed_validation(result)
                ):
                    missing.append("missing passed validation evidence")
                if (
                    (task["requires_real_entrypoint"] or task["consumer_facing"])
                    and not _result_has_consumer_evidence(result)
                ):
                    missing.append("missing consumer evidence")
                elif (
                    not feature_epoch_validation
                    and task["requires_real_entrypoint"]
                    and not _result_has_real_entrypoint_consumer_evidence(result)
                ):
                    missing.append("missing real-entrypoint consumer evidence")

        if missing:
            evidence_gaps.append(f"{task['task_id']}: {', '.join(missing)}")
        task_findings.append(
            {
                "task_id": task["task_id"],
                "checked": task["checked"],
                "consumer_facing": task["consumer_facing"],
                "result_path": result.get("path", "")
                if isinstance(result, dict)
                else "",
                "missing_evidence": "; ".join(missing),
            }
        )

    if _tracker_has_open_gaps(resolved_feature_dir):
        evidence_gaps.append("implement-tracker.md has unresolved open_gaps")
    shared_validation_ref = ""
    if terminal and feature_epoch_validation:
        shared_gaps, shared_validation_ref = _shared_implement_validation_gaps(
            resolved_project_root,
            resolved_feature_dir,
            checked_task_ids,
        )
        evidence_gaps.extend(shared_gaps)
    evidence_gaps.extend(_task_lifecycle_blocker_gaps(resolved_feature_dir))
    evidence_gaps.extend(
        _packetized_review_gaps(
            resolved_feature_dir,
            tasks,
            checked_tasks,
            terminal=terminal,
        )
    )
    if terminal and feature_epoch_validation:
        evidence_gaps.extend(
            _shared_validation_lifecycle_gaps(
                resolved_feature_dir,
                checked_task_ids,
                shared_validation_ref,
            )
        )

    audit_passed = terminal and not evidence_gaps
    if audit_passed:
        return _payload(
            status="pass",
            feature_dir=resolved_feature_dir,
            classification=classification,
            trusted=True,
            recommended_status="resolved",
            next_action="Terminal implement state has closeout-quality evidence.",
            task_findings=task_findings,
            open_gaps=[],
        )

    if terminal:
        return _payload(
            status="fail",
            feature_dir=resolved_feature_dir,
            classification=classification,
            trusted=False,
            recommended_status="validating",
            next_action="Resume sp-implement in validation/recovery mode and close the evidence gaps before reporting completion.",
            task_findings=task_findings,
            open_gaps=evidence_gaps,
        )

    return _payload(
        status="pass",
        feature_dir=resolved_feature_dir,
        classification=classification,
        trusted=False,
        recommended_status=tracker_status or "executing",
        next_action=str(
            tracker.get("next_action") or "Resume the recorded implementation batch."
        ),
        task_findings=task_findings,
        open_gaps=evidence_gaps,
    )


def _payload(
    *,
    status: str,
    feature_dir: Path,
    classification: str,
    trusted: bool,
    recommended_status: str,
    next_action: str,
    task_findings: list[dict[str, Any]],
    open_gaps: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "feature_dir": str(feature_dir),
        "resume_classification": classification,
        "trusted_terminal_state": trusted,
        "task_findings": task_findings,
        "join_point_findings": [],
        "open_gaps": open_gaps,
        "recommended_tracker_status": recommended_status,
        "recommended_next_action": next_action,
    }
