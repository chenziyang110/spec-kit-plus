"""Hash-bound, human-confirmed Implement-to-Review deferrals."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .atomic_io import (
    atomic_write_text,
    interprocess_lock,
    read_local_state_text,
)


DEFERRAL_SCHEMA_REF = ".specify/templates/implementation-deferral-schema.json"
DEFERRAL_DIR_REF = "implementation-review/deferrals"
_TASK_BLOCKER_REF = re.compile(r"^(T\d+)-B(\d{2})$")
_VALIDATION_BLOCKER_REF = re.compile(r"^VALIDATION-(BASELINE|CONVERGENCE)$")
_DEFERRAL_ID = re.compile(r"^DEF-[0-9a-f]{12}$")
_ALLOWED_PROPOSAL_FIELDS = frozenset(
    {
        "blocker_refs",
        "affected_task_ids",
        "affected_acceptance_refs",
        "deferred_validation_purposes",
        "exact_excluded_behavior",
        "residual_risk",
        "risk_severity",
        "claims_withheld",
        "reopen_or_stop_condition",
        "downstream_artifact",
        "downstream_owner",
        "defer_until",
    }
)


class ImplementationDeferralError(ValueError):
    """Raised when a deferral is incomplete, stale, or not human-confirmed."""


def _canonical_sha256(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _project_feature(
    project_root: Path, feature_dir: Path | str
) -> tuple[Path, Path]:
    root = project_root.resolve(strict=False)
    feature = Path(feature_dir)
    if not feature.is_absolute():
        feature = root / feature
    feature = feature.resolve(strict=False)
    try:
        relative = feature.relative_to(root)
    except ValueError as exc:
        raise ImplementationDeferralError(
            "feature_dir must stay inside project_root"
        ) from exc
    if not relative.parts:
        raise ImplementationDeferralError(
            "feature_dir must identify a child directory"
        )
    return root, feature


def infer_project_root(feature_dir: Path) -> Path:
    feature = feature_dir.resolve(strict=False)
    if feature.parent.name == "features" and feature.parent.parent.name == ".specify":
        return feature.parent.parent.parent
    if len(feature.parents) < 2:
        raise ImplementationDeferralError("cannot infer project root from feature_dir")
    return feature.parents[1]


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImplementationDeferralError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(
    value: object, label: str, *, required: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise ImplementationDeferralError(f"{label} must be a list")
    result: list[str] = []
    for item in value:
        normalized = _required_text(item, label)
        if normalized not in result:
            result.append(normalized)
    if required and not result:
        raise ImplementationDeferralError(f"{label} must not be empty")
    return result


def _read_json(path: Path, *, root: Path) -> dict[str, Any]:
    try:
        payload = json.loads(read_local_state_text(path, root=root))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ImplementationDeferralError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ImplementationDeferralError(f"{path} must contain a JSON object")
    return payload


def _task_index_acceptance_refs(feature: Path) -> set[str]:
    path = feature / "task-index.json"
    if not path.is_file():
        return set()
    payload = _read_json(path, root=feature)
    values = payload.get("acceptance_refs")
    if not isinstance(values, list):
        return set()
    return {
        str(value).strip()
        for value in values
        if isinstance(value, str) and value.strip()
    }


def _task_index_task_ids(feature: Path) -> set[str]:
    path = feature / "task-index.json"
    if not path.is_file():
        return set()
    payload = _read_json(path, root=feature)
    values = payload.get("tasks")
    if not isinstance(values, list):
        return set()
    return {
        str(value.get("id") or "").strip().upper()
        for value in values
        if isinstance(value, Mapping) and str(value.get("id") or "").strip()
    }


def _normalize_proposal(
    feature: Path, raw: Mapping[str, Any]
) -> dict[str, Any]:
    unknown = set(raw) - _ALLOWED_PROPOSAL_FIELDS
    if unknown:
        raise ImplementationDeferralError(
            "deferral proposal contains unsupported fields: "
            + ", ".join(sorted(unknown))
        )
    blocker_refs = _string_list(
        raw.get("blocker_refs"), "blocker_refs", required=True
    )
    for blocker_ref in blocker_refs:
        if not (
            _TASK_BLOCKER_REF.fullmatch(blocker_ref)
            or _VALIDATION_BLOCKER_REF.fullmatch(blocker_ref)
        ):
            raise ImplementationDeferralError(
                f"unsupported blocker_ref: {blocker_ref}"
            )
    affected_task_ids = [
        value.upper()
        for value in _string_list(
            raw.get("affected_task_ids"),
            "affected_task_ids",
            required=True,
        )
    ]
    if any(not re.fullmatch(r"T\d+", task_id) for task_id in affected_task_ids):
        raise ImplementationDeferralError(
            "affected_task_ids must contain canonical Txx identifiers"
        )
    known_task_ids = _task_index_task_ids(feature)
    unknown_task_ids = set(affected_task_ids) - known_task_ids
    if known_task_ids and unknown_task_ids:
        raise ImplementationDeferralError(
            "deferral references unknown task ids: "
            + ", ".join(sorted(unknown_task_ids))
        )
    affected_acceptance_refs = _string_list(
        raw.get("affected_acceptance_refs", []),
        "affected_acceptance_refs",
    )
    known_acceptance_refs = _task_index_acceptance_refs(feature)
    if known_acceptance_refs and not affected_acceptance_refs:
        raise ImplementationDeferralError(
            "affected_acceptance_refs must identify the frozen acceptance scope"
        )
    unknown_acceptance_refs = set(affected_acceptance_refs) - known_acceptance_refs
    if known_acceptance_refs and unknown_acceptance_refs:
        raise ImplementationDeferralError(
            "deferral references unknown acceptance refs: "
            + ", ".join(sorted(unknown_acceptance_refs))
        )
    validation_purposes = [
        value.lower()
        for value in _string_list(
            raw.get("deferred_validation_purposes", []),
            "deferred_validation_purposes",
        )
    ]
    unsupported_purposes = set(validation_purposes) - {
        "baseline",
        "convergence",
    }
    if unsupported_purposes:
        raise ImplementationDeferralError(
            "Implement may defer only baseline or convergence validation"
        )
    for purpose in validation_purposes:
        if f"VALIDATION-{purpose.upper()}" not in blocker_refs:
            raise ImplementationDeferralError(
                f"deferred validation purpose {purpose} requires "
                f"blocker_ref VALIDATION-{purpose.upper()}"
            )
    risk_severity = _required_text(
        raw.get("risk_severity"), "risk_severity"
    ).lower()
    if risk_severity not in {"low", "medium"}:
        raise ImplementationDeferralError(
            "only low or medium delivery risk may be deferred; high/critical "
            "risk remains a hard blocker"
        )
    downstream_owner = _required_text(
        raw.get("downstream_owner"), "downstream_owner"
    ).lower()
    if downstream_owner != "review":
        raise ImplementationDeferralError(
            "Implement deferrals must transfer ownership to Review"
        )
    defer_until = _required_text(raw.get("defer_until"), "defer_until").lower()
    if defer_until != "review":
        raise ImplementationDeferralError(
            "Implement deferrals expire at Review and cannot waive final delivery"
        )
    downstream_artifact = _required_text(
        raw.get("downstream_artifact"), "downstream_artifact"
    )
    if downstream_artifact != "implementation-handoff.json":
        raise ImplementationDeferralError(
            "Implement deferrals must be carried by implementation-handoff.json"
        )
    proposal = {
        "blocker_refs": blocker_refs,
        "affected_task_ids": affected_task_ids,
        "affected_acceptance_refs": affected_acceptance_refs,
        "deferred_validation_purposes": validation_purposes,
        "exact_excluded_behavior": _required_text(
            raw.get("exact_excluded_behavior"), "exact_excluded_behavior"
        ),
        "residual_risk": _required_text(
            raw.get("residual_risk"), "residual_risk"
        ),
        "risk_severity": risk_severity,
        "claims_withheld": _string_list(
            raw.get("claims_withheld"), "claims_withheld", required=True
        ),
        "reopen_or_stop_condition": _required_text(
            raw.get("reopen_or_stop_condition"),
            "reopen_or_stop_condition",
        ),
        "downstream_artifact": downstream_artifact,
        "downstream_owner": downstream_owner,
        "defer_until": defer_until,
    }
    return proposal


def deferral_relative_ref(deferral_id: str) -> str:
    if not _DEFERRAL_ID.fullmatch(deferral_id):
        raise ImplementationDeferralError(f"invalid deferral_id: {deferral_id}")
    return f"{DEFERRAL_DIR_REF}/{deferral_id}.json"


def _deferral_path(feature: Path, deferral_id: str) -> Path:
    return feature / Path(*deferral_relative_ref(deferral_id).split("/"))


def _validate_blocker_refs(feature: Path, proposal: Mapping[str, Any]) -> None:
    for blocker_ref in proposal["blocker_refs"]:
        match = _TASK_BLOCKER_REF.fullmatch(str(blocker_ref))
        if match is None:
            continue
        task_id, raw_index = match.groups()
        if task_id not in proposal["affected_task_ids"]:
            raise ImplementationDeferralError(
                f"{blocker_ref} task must appear in affected_task_ids"
            )
        path = feature / "implementation-review" / "tasks" / f"{task_id}.json"
        if not path.is_file():
            raise ImplementationDeferralError(
                f"{blocker_ref} references missing task lifecycle {path.name}"
            )
        lifecycle = _read_json(path, root=feature)
        blockers = lifecycle.get("blockers")
        index = int(raw_index) - 1
        if not isinstance(blockers, list) or not 0 <= index < len(blockers):
            raise ImplementationDeferralError(
                f"{blocker_ref} references a missing task blocker"
            )
        if not isinstance(blockers[index], dict):
            raise ImplementationDeferralError(
                f"{blocker_ref} references a malformed task blocker"
            )
        blocker = blockers[index]
        classification = str(blocker.get("classification") or "").strip()
        owner = str(blocker.get("owner") or "").strip()
        if owner == "agent" or classification in {
            "technical",
            "project_cognition_readiness",
        }:
            raise ImplementationDeferralError(
                f"{blocker_ref} is agent-owned and must be repaired or routed, "
                "not human-deferred"
            )
        if classification not in {
            "external",
            "human-action",
            "verification_policy",
            "baseline_timeout",
        }:
            raise ImplementationDeferralError(
                f"{blocker_ref} classification {classification or 'missing'} "
                "is not eligible for Implement-to-Review deferral"
            )


def _current_implementation_fingerprint(root: Path, feature: Path) -> str:
    from .review_runtime import implementation_snapshot_sha256

    return implementation_snapshot_sha256(root, feature)


def _reusable_deferral(
    feature: Path,
    *,
    proposal_sha256: str,
    current_fingerprint: str,
) -> dict[str, Any] | None:
    directory = feature / DEFERRAL_DIR_REF
    if not directory.is_dir():
        return None
    for path in sorted(directory.glob("DEF-*.json")):
        record = _read_json(path, root=feature)
        if record.get("proposal_sha256") != proposal_sha256:
            continue
        status = record.get("status")
        if (
            status == "proposed"
            and record.get("source_fingerprint") == current_fingerprint
        ):
            return record
        confirmation = record.get("confirmation")
        if (
            status == "confirmed"
            and isinstance(confirmation, Mapping)
            and confirmation.get("implementation_fingerprint")
            == current_fingerprint
        ):
            return record
    return None


def propose_implementation_deferral(
    project_root: Path,
    feature_dir: Path | str,
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist an immutable proposal that still has no effect until confirmed."""

    root, feature = _project_feature(project_root, feature_dir)
    normalized = _normalize_proposal(feature, proposal)
    _validate_blocker_refs(feature, normalized)
    proposal_sha256 = _canonical_sha256(normalized)
    source_fingerprint = _current_implementation_fingerprint(root, feature)
    deferral_identity = _canonical_sha256(
        {
            "proposal_sha256": proposal_sha256,
            "source_fingerprint": source_fingerprint,
        }
    )
    deferral_id = f"DEF-{deferral_identity[:12]}"
    path = _deferral_path(feature, deferral_id)

    record = {
        "version": 1,
        "schema_ref": DEFERRAL_SCHEMA_REF,
        "deferral_id": deferral_id,
        "status": "proposed",
        "source_stage": "implement",
        "source_fingerprint": source_fingerprint,
        "proposal": normalized,
        "proposal_sha256": proposal_sha256,
        "confirmation": None,
    }
    lock_path = feature / DEFERRAL_DIR_REF / ".lock"
    with interprocess_lock(lock_path):
        reusable = _reusable_deferral(
            feature,
            proposal_sha256=proposal_sha256,
            current_fingerprint=source_fingerprint,
        )
        if reusable is not None:
            reusable_id = str(reusable.get("deferral_id") or "")
            reusable_path = _deferral_path(feature, reusable_id)
            return {
                "status": reusable.get("status"),
                "reused": True,
                "deferral_id": reusable_id,
                "proposal_sha256": proposal_sha256,
                "path": str(reusable_path),
                "confirmation_required": reusable.get("status") != "confirmed",
            }
        if path.is_file():
            existing = _read_json(path, root=feature)
            if (
                existing.get("proposal_sha256") != proposal_sha256
                or existing.get("source_fingerprint") != source_fingerprint
            ):
                raise ImplementationDeferralError(
                    f"deferral id collision for {deferral_id}"
                )
            return {
                "status": existing.get("status"),
                "reused": True,
                "deferral_id": deferral_id,
                "proposal_sha256": proposal_sha256,
                "path": str(path),
                "confirmation_required": existing.get("status") != "confirmed",
            }
        atomic_write_text(
            path, json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        )
    return {
        "status": "proposed",
        "reused": False,
        "deferral_id": deferral_id,
        "proposal_sha256": proposal_sha256,
        "path": str(path),
        "confirmation_required": True,
    }


def _bind_task_blockers(
    feature: Path, record: Mapping[str, Any], relative_ref: str
) -> None:
    proposal = record["proposal"]
    for blocker_ref in proposal["blocker_refs"]:
        match = _TASK_BLOCKER_REF.fullmatch(str(blocker_ref))
        if match is None:
            continue
        task_id, raw_index = match.groups()
        path = feature / "implementation-review" / "tasks" / f"{task_id}.json"
        lifecycle = _read_json(path, root=feature)
        blockers = lifecycle.get("blockers")
        index = int(raw_index) - 1
        if not isinstance(blockers, list) or not 0 <= index < len(blockers):
            raise ImplementationDeferralError(
                f"{blocker_ref} changed after the deferral proposal"
            )
        blocker = blockers[index]
        if not isinstance(blocker, dict):
            raise ImplementationDeferralError(
                f"{blocker_ref} changed after the deferral proposal"
            )
        blocker["disposition"] = "user_confirmed_deferral"
        blocker["disposition_ref"] = relative_ref
        lifecycle["status"] = "deferred"
        atomic_write_text(
            path, json.dumps(lifecycle, ensure_ascii=False, indent=2) + "\n"
        )


def _task_lifecycle_snapshots(
    feature: Path, proposal: Mapping[str, Any]
) -> dict[Path, str]:
    snapshots: dict[Path, str] = {}
    for blocker_ref in proposal["blocker_refs"]:
        match = _TASK_BLOCKER_REF.fullmatch(str(blocker_ref))
        if match is None:
            continue
        task_id = match.group(1)
        path = feature / "implementation-review" / "tasks" / f"{task_id}.json"
        if path not in snapshots:
            snapshots[path] = read_local_state_text(path, root=feature)
    return snapshots


def _restore_task_lifecycles(snapshots: Mapping[Path, str]) -> None:
    restore_errors: list[str] = []
    for path, content in snapshots.items():
        try:
            atomic_write_text(path, content)
        except OSError as exc:  # pragma: no cover - catastrophic storage failure
            restore_errors.append(f"{path}: {exc}")
    if restore_errors:
        raise ImplementationDeferralError(
            "deferral confirmation failed and task lifecycle rollback was "
            "incomplete: " + "; ".join(restore_errors)
        )


def confirm_implementation_deferral(
    project_root: Path,
    feature_dir: Path | str,
    *,
    deferral_id: str,
    proposal_sha256: str,
    confirmation_source: str,
    statement: str,
) -> dict[str, Any]:
    """Bind an exact human statement to a proposal and transfer it to Review."""

    root, feature = _project_feature(project_root, feature_dir)
    path = _deferral_path(feature, deferral_id)
    normalized_sha = _required_text(proposal_sha256, "proposal_sha256")
    source = _required_text(confirmation_source, "confirmation_source")
    confirmation_statement = _required_text(statement, "statement")
    relative_ref = deferral_relative_ref(deferral_id)
    lock_path = feature / DEFERRAL_DIR_REF / ".lock"
    with interprocess_lock(lock_path):
        if not path.is_file():
            raise ImplementationDeferralError(
                f"unknown deferral_id: {deferral_id}"
            )
        record = _read_json(path, root=feature)
        proposal = record.get("proposal")
        if not isinstance(proposal, dict):
            raise ImplementationDeferralError("deferral proposal is malformed")
        actual_sha = _canonical_sha256(proposal)
        if (
            actual_sha != record.get("proposal_sha256")
            or actual_sha != normalized_sha
        ):
            raise ImplementationDeferralError(
                "proposal sha256 does not match the immutable deferral proposal"
            )
        existing_confirmation = record.get("confirmation")
        if record.get("status") == "confirmed":
            current_fingerprint = _current_implementation_fingerprint(
                root, feature
            )
            _validate_confirmed_record(
                record,
                expected_id=deferral_id,
                current_fingerprint=current_fingerprint,
                feature=feature,
            )
            if (
                isinstance(existing_confirmation, dict)
                and existing_confirmation.get("source") == source
                and existing_confirmation.get("statement")
                == confirmation_statement
            ):
                return {
                    "status": "confirmed",
                    "reused": True,
                    "deferral_id": deferral_id,
                    "proposal_sha256": actual_sha,
                    "confirmation_id": existing_confirmation.get(
                        "confirmation_id"
                    ),
                    "path": str(path),
                    "disposition": "transferred_to_review",
                }
            raise ImplementationDeferralError(
                "confirmed deferrals are immutable; create a new proposal"
            )
        if record.get("status") != "proposed":
            raise ImplementationDeferralError(
                f"deferral cannot be confirmed from status {record.get('status')}"
            )
        current_fingerprint = _current_implementation_fingerprint(root, feature)
        if record.get("source_fingerprint") != current_fingerprint:
            raise ImplementationDeferralError(
                "deferral proposal is stale for the current implementation; "
                "propose the same exact scope again to obtain a new DEF id"
            )
        _validate_blocker_refs(feature, proposal)
        lifecycle_snapshots = _task_lifecycle_snapshots(feature, proposal)
        try:
            _bind_task_blockers(feature, record, relative_ref)
            fingerprint = _current_implementation_fingerprint(root, feature)
            confirmation_id = "HC-" + hashlib.sha256(
                (
                    actual_sha
                    + "\0"
                    + source
                    + "\0"
                    + confirmation_statement
                    + "\0"
                    + fingerprint
                ).encode("utf-8")
            ).hexdigest()[:24]
            record["status"] = "confirmed"
            record["confirmation"] = {
                "actor": "human",
                "source": source,
                "statement": confirmation_statement,
                "confirmation_id": confirmation_id,
                "confirmed_payload_sha256": actual_sha,
                "implementation_fingerprint": fingerprint,
            }
            atomic_write_text(
                path, json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
        except Exception:
            _restore_task_lifecycles(lifecycle_snapshots)
            raise
    return {
        "status": "confirmed",
        "reused": False,
        "deferral_id": deferral_id,
        "proposal_sha256": actual_sha,
        "confirmation_id": confirmation_id,
        "path": str(path),
        "disposition": "transferred_to_review",
    }


def _validate_confirmed_record(
    record: Mapping[str, Any],
    *,
    expected_id: str,
    current_fingerprint: str | None,
    feature: Path,
) -> dict[str, Any]:
    if record.get("version") != 1 or record.get("schema_ref") != DEFERRAL_SCHEMA_REF:
        raise ImplementationDeferralError(
            f"{expected_id} has an unsupported deferral schema"
        )
    if record.get("deferral_id") != expected_id:
        raise ImplementationDeferralError(f"{expected_id} id does not match its file")
    if record.get("source_stage") != "implement":
        raise ImplementationDeferralError(
            f"{expected_id} source_stage must be implement"
        )
    source_fingerprint = _required_text(
        record.get("source_fingerprint"),
        f"{expected_id} source_fingerprint",
    )
    if not re.fullmatch(r"[0-9a-f]{64}", source_fingerprint):
        raise ImplementationDeferralError(
            f"{expected_id} source_fingerprint must be a sha256 digest"
        )
    proposal = record.get("proposal")
    if not isinstance(proposal, Mapping):
        raise ImplementationDeferralError(f"{expected_id} proposal is malformed")
    proposal_sha = _canonical_sha256(proposal)
    if proposal_sha != record.get("proposal_sha256"):
        raise ImplementationDeferralError(f"{expected_id} proposal was modified")
    normalized_proposal = _normalize_proposal(feature, proposal)
    if dict(proposal) != normalized_proposal:
        raise ImplementationDeferralError(
            f"{expected_id} proposal is not canonical"
        )
    _validate_blocker_refs(feature, normalized_proposal)
    if record.get("status") != "confirmed":
        raise ImplementationDeferralError(f"{expected_id} is not confirmed")
    confirmation = record.get("confirmation")
    if not isinstance(confirmation, Mapping):
        raise ImplementationDeferralError(f"{expected_id} confirmation is missing")
    if confirmation.get("actor") != "human":
        raise ImplementationDeferralError(
            f"{expected_id} confirmation actor must be human"
        )
    source = _required_text(
        confirmation.get("source"), f"{expected_id} confirmation.source"
    )
    statement = _required_text(
        confirmation.get("statement"), f"{expected_id} confirmation.statement"
    )
    fingerprint = _required_text(
        confirmation.get("implementation_fingerprint"),
        f"{expected_id} confirmation.implementation_fingerprint",
    )
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ImplementationDeferralError(
            f"{expected_id} confirmation fingerprint must be a sha256 digest"
        )
    expected_confirmation_id = "HC-" + hashlib.sha256(
        (
            proposal_sha
            + "\0"
            + source
            + "\0"
            + statement
            + "\0"
            + fingerprint
        ).encode("utf-8")
    ).hexdigest()[:24]
    if confirmation.get("confirmation_id") != expected_confirmation_id:
        raise ImplementationDeferralError(
            f"{expected_id} confirmation digest does not match"
        )
    if confirmation.get("confirmed_payload_sha256") != proposal_sha:
        raise ImplementationDeferralError(
            f"{expected_id} confirmation is not bound to the proposal"
        )
    if current_fingerprint and fingerprint != current_fingerprint:
        raise ImplementationDeferralError(
            f"{expected_id} is stale for the current implementation fingerprint"
        )
    relative_ref = deferral_relative_ref(expected_id)
    for blocker_ref in normalized_proposal["blocker_refs"]:
        match = _TASK_BLOCKER_REF.fullmatch(str(blocker_ref))
        if match is None:
            continue
        task_id, raw_index = match.groups()
        lifecycle_path = (
            feature / "implementation-review" / "tasks" / f"{task_id}.json"
        )
        lifecycle = _read_json(lifecycle_path, root=feature)
        blockers = lifecycle.get("blockers")
        index = int(raw_index) - 1
        if not isinstance(blockers, list) or not 0 <= index < len(blockers):
            raise ImplementationDeferralError(
                f"{expected_id} task blocker binding is missing: {blocker_ref}"
            )
        blocker = blockers[index]
        if (
            not isinstance(blocker, Mapping)
            or blocker.get("disposition") != "user_confirmed_deferral"
            or blocker.get("disposition_ref") != relative_ref
        ):
            raise ImplementationDeferralError(
                f"{expected_id} task blocker binding drifted: {blocker_ref}"
            )
    return deepcopy(dict(record))


def confirmed_implementation_deferrals(
    project_root: Path,
    feature_dir: Path | str,
    *,
    current_fingerprint: str | None = None,
) -> list[dict[str, Any]]:
    """Return only fresh, hash-bound deferrals; reject any corrupt confirmed file."""

    root, feature = _project_feature(project_root, feature_dir)
    if current_fingerprint is None:
        from .review_runtime import implementation_snapshot_sha256

        current_fingerprint = implementation_snapshot_sha256(root, feature)
    directory = feature / DEFERRAL_DIR_REF
    if not directory.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("DEF-*.json")):
        record = _read_json(path, root=feature)
        if record.get("status") != "confirmed":
            continue
        confirmation = record.get("confirmation")
        if (
            not isinstance(confirmation, Mapping)
            or confirmation.get("implementation_fingerprint")
            != current_fingerprint
        ):
            # Keep stale confirmations as immutable history. They no longer
            # authorize a disposition for the current implementation.
            continue
        records.append(
            _validate_confirmed_record(
                record,
                expected_id=path.stem,
                current_fingerprint=current_fingerprint,
                feature=feature,
            )
        )
    return records


def confirmed_deferral_for_blocker(
    project_root: Path,
    feature_dir: Path | str,
    blocker_ref: str,
) -> dict[str, Any] | None:
    for record in confirmed_implementation_deferrals(project_root, feature_dir):
        proposal = record["proposal"]
        if blocker_ref in proposal["blocker_refs"]:
            return record
    return None


def confirmed_deferral_for_validation(
    project_root: Path,
    feature_dir: Path | str,
    *,
    purpose: str,
    covered_task_ids: set[str],
) -> dict[str, Any] | None:
    normalized_purpose = purpose.strip().lower()
    for record in confirmed_implementation_deferrals(project_root, feature_dir):
        proposal = record["proposal"]
        if (
            normalized_purpose in proposal["deferred_validation_purposes"]
            and covered_task_ids
            <= {str(value).upper() for value in proposal["affected_task_ids"]}
        ):
            return record
    return None


def implementation_deferral_handoff_projection(
    records: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return the compact immutable subset Review needs to resume the scope."""

    projection: list[dict[str, Any]] = []
    for record in records:
        proposal = record["proposal"]
        confirmation = record["confirmation"]
        deferral_id = str(record["deferral_id"])
        projection.append(
            {
                "deferral_id": deferral_id,
                "deferral_ref": deferral_relative_ref(deferral_id),
                "proposal_sha256": record["proposal_sha256"],
                "confirmation_id": confirmation["confirmation_id"],
                "implementation_fingerprint": confirmation[
                    "implementation_fingerprint"
                ],
                "blocker_refs": list(proposal["blocker_refs"]),
                "affected_task_ids": list(proposal["affected_task_ids"]),
                "affected_acceptance_refs": list(
                    proposal["affected_acceptance_refs"]
                ),
                "deferred_validation_purposes": list(
                    proposal["deferred_validation_purposes"]
                ),
                "exact_excluded_behavior": proposal[
                    "exact_excluded_behavior"
                ],
                "residual_risk": proposal["residual_risk"],
                "risk_severity": proposal["risk_severity"],
                "claims_withheld": list(proposal["claims_withheld"]),
                "reopen_or_stop_condition": proposal[
                    "reopen_or_stop_condition"
                ],
                "downstream_artifact": proposal["downstream_artifact"],
                "downstream_owner": proposal["downstream_owner"],
                "defer_until": proposal["defer_until"],
            }
        )
    return projection


__all__ = [
    "DEFERRAL_DIR_REF",
    "DEFERRAL_SCHEMA_REF",
    "ImplementationDeferralError",
    "confirm_implementation_deferral",
    "confirmed_deferral_for_blocker",
    "confirmed_deferral_for_validation",
    "confirmed_implementation_deferrals",
    "deferral_relative_ref",
    "infer_project_root",
    "implementation_deferral_handoff_projection",
    "propose_implementation_deferral",
]
