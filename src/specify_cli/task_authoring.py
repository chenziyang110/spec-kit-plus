"""Deterministic authoring control plane for task-index.json and tasks.md."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import stat
from typing import Any, Mapping

from .atomic_io import (
    read_local_state_bytes,
    read_local_state_text,
    safe_local_state_path,
)
from .test_intelligence import (
    TestIntelligenceValidationError,
    validate_test_intelligence_bundle,
)
from .workflow_transaction import (
    WorkflowTransactionError,
    apply_workflow_transaction,
)


class TaskAuthoringError(RuntimeError):
    """Raised when a task package mutation is invalid or unsafe."""


_TASK_ID_RE = re.compile(r"^T\d+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TEST_DESIGN_EVIDENCE_REF_RE = re.compile(
    r"^\.specify/evidence/records/evd-[0-9a-f]{24}\.json$"
)
_TEST_DESIGN_OBLIGATION_RE = re.compile(r"^TO-[0-9]{3,}$")
_TEST_DESIGN_GAP_RE = re.compile(r"^GAP-[0-9]{3,}$")
_TEST_DESIGN_AUDIT_CHECK_RE = re.compile(r"^[a-z][a-z0-9_-]+$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)
_TEST_DESIGN_SOURCE_FRESHNESS_POLICIES = frozenset(
    {"strict", "bound_snapshot"}
)
_TERMINAL_STATUSES = {"accepted", "deferred"}
_AUTHORING_MUTABLE_STATUSES = {"pending", "ready", "blocked", "failed"}
_TEST_DESIGN_ROOT_FIELDS = {
    "test_design_handoff_ref",
    "test_design_handoff_sha256",
    "test_design_source_fingerprint",
    "test_design_state_revision",
    "test_design_artifact_digests",
}
_TEST_DESIGN_PROJECTION_BINDING_FIELDS = {
    "publication_ref",
    "publication_sha256",
    "projection_ref",
    "projection_sha256",
    "source_fingerprint",
    "state_revision",
}
_PROTECTED_ROOT_FIELDS = {
    "version",
    "status",
    "tasks",
    "transition",
    *_TEST_DESIGN_ROOT_FIELDS,
}
_PROTECTED_TASK_FIELDS = {"status", "lifecycle_ref", "packet_ref", "result_ref"}
_AUTHORED_TASK_FIELDS = {
    "id",
    "task_id",
    "story_id",
    "phase",
    "objective",
    "title",  # alias for objective; normalized away
    "description",
    "dependencies",
    "depends_on",
    "parallel",
    "batch",
    "batch_id",
    "join_point",
    "join_point_id",
    "owner",
    "execution_mode",
    "task_kind",
    "priority",
    "risk",
    "risk_level",
    "expected_write_scope",
    "write_scope",
    "read_scope",
    "required_refs",
    "authoritative_refs",
    "policy_refs",
    "forbidden_drift",
    "hard_rules",
    "acceptance",
    "done_condition",  # alias for acceptance; normalized away
    "acceptance_refs",
    "verification",
    "required_validation",
    "task_checks",
    "consumer_surfaces",
    "required_consumer_evidence",
    "required_evidence",
    "test_case_refs",
    "test_data_refs",
    "must_preserve_ids",
    "must_preserve_refs",
    "consequence_obligation_ids",
    "consequence_obligation_refs",
    "capability_operations",
    "capability_operation_refs",
    "fidelity_refs",
    "user_confirmed_deferral_refs",
    "implementation_target_ref",
    "stop_and_reopen_conditions",
    "recovery",
    "ui_contract",
    "no_new_test_rationale",
    "replacement_validation",
    "residual_risk",
    "skills",
    "notes",
}
_OBSOLETE_TASK_FIELDS = {
    "ui_contract_version",
    "ui_fidelity_requirements",
    "ui_fidelity_evidence",
}
_TEST_DESIGN_HANDOFF_FIELDS = {
    "schema_version",
    "source_fingerprint",
    "state_revision",
    "claim_status",
    "artifact_refs",
    "artifact_digests",
    "test_case_refs",
    "test_data_refs",
    "gap_ref",
    "audit_result_ref",
    "next_command",
}
_TEST_DESIGN_ARTIFACT_REFS = {
    "state": "test-state.json",
    "universe": "test-universe.json",
    "catalog": "test-catalog.json",
    "data_manifest": "test-data-manifest.json",
    "coverage_matrix": "coverage-matrix.json",
}
_TEST_DESIGN_BUNDLE_FILES = {
    "universe": "test-universe.json",
    "catalog": "test-catalog.json",
    "data_manifest": "test-data-manifest.json",
    "coverage_matrix": "coverage-matrix.json",
    "gaps": "test-gaps.json",
}
_TEST_DESIGN_FORBIDDEN_CLAIMS = [
    "tests_executed",
    "tests_passed",
    "behavior_fixed",
    "implementation_complete",
    "release_safe",
    "absolute_complete",
]
_TEST_DESIGN_AUDIT_CORE_CHECK_IDS = {
    "obligation_accounting",
    "traceability",
    "oracle_quality",
    "harness_feasibility",
    "data_readiness",
    "evidence_freshness",
    "risk_dimensions",
    "contradictions",
}


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _go_json_bytes(payload: object, *, pretty: bool) -> bytes:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=(",", ": ") if pretty else (",", ":"),
    )
    rendered = (
        rendered.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return (rendered + ("\n" if pretty else "")).encode("utf-8")


def _canonical_json_sha256(payload: object) -> str:
    return _sha256(_go_json_bytes(payload, pretty=False))


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _project_feature(
    project_root: Path, feature_dir: Path | str
) -> tuple[Path, Path]:
    root = safe_local_state_path(Path(project_root))
    candidate = Path(feature_dir)
    if not candidate.is_absolute():
        candidate = root / candidate
    feature = safe_local_state_path(candidate, root=root)
    if not feature.is_dir():
        raise TaskAuthoringError(f"feature directory does not exist: {feature}")
    return root, feature


def _read_object(path: Path, *, root: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(read_local_state_text(path, root=root))
    except FileNotFoundError as exc:
        raise TaskAuthoringError(f"{label} is missing: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskAuthoringError(f"{label} is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskAuthoringError(f"{label} must contain a JSON object")
    return payload


def _read_object_with_raw(
    path: Path, *, root: Path, label: str
) -> tuple[dict[str, Any], bytes]:
    try:
        target = safe_local_state_path(path, root=root)
        metadata = target.lstat()
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise TaskAuthoringError(
                f"{label} must be a regular non-symlink file"
            )
        raw = read_local_state_bytes(target, root=root)
        payload = json.loads(raw)
    except TaskAuthoringError:
        raise
    except FileNotFoundError as exc:
        raise TaskAuthoringError(f"{label} is missing: {path}") from exc
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise TaskAuthoringError(f"{label} is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskAuthoringError(f"{label} must contain a JSON object")
    return payload, raw


def _strict_string_list(
    payload: Mapping[str, Any],
    field: str,
    *,
    label: str,
    require_nonempty: bool,
) -> list[str]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        raise TaskAuthoringError(f"{label} {field} must be an array")
    values: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise TaskAuthoringError(
                f"{label} {field}[{index}] must be a non-empty string"
            )
        value = item.strip()
        if value in values:
            raise TaskAuthoringError(
                f"{label} {field} must contain unique values"
            )
        values.append(value)
    if require_nonempty and not values:
        raise TaskAuthoringError(f"{label} {field} must not be empty")
    return values


def _required_text(payload: Mapping[str, Any], field: str, *, label: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TaskAuthoringError(f"{label} {field} must be a non-empty string")
    return value.strip()


def _required_positive_int(
    payload: Mapping[str, Any], field: str, *, label: str
) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TaskAuthoringError(f"{label} {field} must be a positive integer")
    return value


def _normalized_ref(value: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _path_covered(candidate: str, scopes: list[str]) -> bool:
    normalized_candidate = _normalized_ref(candidate).rstrip("/")
    for raw_scope in scopes:
        scope = _normalized_ref(raw_scope).rstrip("/")
        if (
            scope == "."
            or normalized_candidate == scope
            or normalized_candidate.startswith(scope + "/")
        ):
            return True
    return False


def _fingerprint_path_excluded(
    ref: str, *, excluded_paths: list[str], artifact_root: str
) -> bool:
    normalized = _normalized_ref(ref)
    if normalized == ".git" or normalized.startswith(".git/"):
        return True
    for runtime_root in (".specify/runtime", ".specify/evidence"):
        if normalized == runtime_root or normalized.startswith(runtime_root + "/"):
            return True
    if artifact_root and _path_covered(normalized, [artifact_root]):
        return True
    return _path_covered(normalized, excluded_paths)


def _project_ref_path(root: Path, ref: str) -> Path:
    normalized = _normalized_ref(ref)
    candidate = Path(normalized.replace("/", os.sep))
    if not candidate.is_absolute():
        candidate = root / candidate
    return safe_local_state_path(candidate, root=root)


def _test_design_source_fingerprint(
    root: Path,
    *,
    source_refs: list[str],
    included_paths: list[str],
    excluded_paths: list[str],
    risk_dimensions: list[str],
    artifact_root: str,
) -> str:
    files: dict[str, str] = {}

    def add_file(ref: str) -> None:
        normalized = _normalized_ref(ref)
        if _fingerprint_path_excluded(
            normalized,
            excluded_paths=excluded_paths,
            artifact_root=artifact_root,
        ):
            return
        path = _project_ref_path(root, normalized)
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise TaskAuthoringError(
                "fingerprinted path must be a regular non-symlink file: "
                + normalized
            )
        files[normalized] = _sha256(read_local_state_bytes(path, root=root))

    for source_ref in source_refs:
        if _fingerprint_path_excluded(
            source_ref,
            excluded_paths=excluded_paths,
            artifact_root=artifact_root,
        ):
            raise TaskAuthoringError(
                f"source_ref {source_ref} is excluded from the fingerprint boundary"
            )
        try:
            add_file(source_ref)
        except (OSError, ValueError) as exc:
            raise TaskAuthoringError(
                f"fingerprint source {source_ref}: {exc}"
            ) from exc

    for included in included_paths:
        try:
            included_path = _project_ref_path(root, included)
            metadata = included_path.lstat()
        except (OSError, ValueError) as exc:
            raise TaskAuthoringError(
                f"fingerprint included path {included}: {exc}"
            ) from exc
        if stat.S_ISREG(metadata.st_mode):
            try:
                add_file(included)
            except (OSError, ValueError) as exc:
                raise TaskAuthoringError(
                    f"fingerprint included path {included}: {exc}"
                ) from exc
            continue
        if not stat.S_ISDIR(metadata.st_mode):
            raise TaskAuthoringError(
                "included path must be a directory or regular file: " + included
            )
        if _fingerprint_path_excluded(
            included,
            excluded_paths=excluded_paths,
            artifact_root=artifact_root,
        ):
            continue
        try:
            for current, directory_names, file_names in os.walk(
                included_path, followlinks=False
            ):
                current_path = Path(current)
                retained_directories: list[str] = []
                for directory_name in directory_names:
                    candidate = current_path / directory_name
                    relative = candidate.relative_to(root).as_posix()
                    if _fingerprint_path_excluded(
                        relative,
                        excluded_paths=excluded_paths,
                        artifact_root=artifact_root,
                    ):
                        continue
                    safe_local_state_path(candidate, root=root)
                    retained_directories.append(directory_name)
                directory_names[:] = retained_directories
                for file_name in file_names:
                    candidate = current_path / file_name
                    relative = candidate.relative_to(root).as_posix()
                    if _fingerprint_path_excluded(
                        relative,
                        excluded_paths=excluded_paths,
                        artifact_root=artifact_root,
                    ):
                        continue
                    safe_local_state_path(candidate, root=root)
                    add_file(relative)
        except (OSError, ValueError) as exc:
            raise TaskAuthoringError(
                f"fingerprint included path {included}: {exc}"
            ) from exc

    payload = {
        "sources": [
            {"ref": ref, "sha256": files[ref]} for ref in sorted(files)
        ],
        "source_refs": list(source_refs),
        "included_paths": list(included_paths),
        "excluded_paths": list(excluded_paths),
        "risk_dimensions": list(risk_dimensions),
        "artifact_root": artifact_root,
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(raw)


def _validate_test_design_gaps(payload: Mapping[str, Any]) -> None:
    label = "test-gaps.json"
    if payload.get("schema_version") != "spec-kit-test-design-gaps-v1":
        raise TaskAuthoringError(f"{label} has an unsupported runtime contract")
    if payload.get("status") not in {"open", "qualified", "blocked", "clear"}:
        raise TaskAuthoringError(f"{label} status is invalid")
    gaps = payload.get("gaps")
    if not isinstance(gaps, list):
        raise TaskAuthoringError(f"{label} gaps must be an array")
    required = {
        "gap_id",
        "category",
        "severity",
        "disposition",
        "source_refs",
        "affected_obligation_refs",
        "coverage_refs",
        "affected_test_case_refs",
        "affected_test_data_refs",
        "owner",
        "residual_risk",
        "next_action",
        "unblock_criteria",
    }
    for index, raw_gap in enumerate(gaps):
        if not isinstance(raw_gap, Mapping):
            raise TaskAuthoringError(f"{label} gaps[{index}] must be an object")
        missing = sorted(required - set(raw_gap))
        if missing:
            raise TaskAuthoringError(
                f"{label} gaps[{index}] is missing: " + ", ".join(missing)
            )
        unsupported = sorted(set(raw_gap) - required)
        if unsupported:
            raise TaskAuthoringError(
                f"{label} gaps[{index}] contains unsupported fields: "
                + ", ".join(unsupported)
            )
        enums = {
            "category": {
                "coverage",
                "oracle",
                "harness",
                "data",
                "evidence",
                "scope",
                "audit",
            },
            "severity": {"blocking", "high", "medium", "low"},
            "disposition": {
                "open",
                "deferred",
                "waived",
                "excluded",
                "resolved",
                "blocked",
            },
        }
        for field, allowed in enums.items():
            value = str(raw_gap.get(field) or "").strip().lower()
            if value not in allowed:
                raise TaskAuthoringError(
                    f"{label} gaps[{index}] {field} is invalid"
                )
        for field in (
            "source_refs",
            "affected_obligation_refs",
            "coverage_refs",
            "affected_test_case_refs",
            "affected_test_data_refs",
        ):
            _strict_string_list(
                raw_gap,
                field,
                label=f"{label} gaps[{index}]",
                require_nonempty=field == "affected_obligation_refs",
            )
        for field in ("gap_id", "owner", "residual_risk", "next_action", "unblock_criteria"):
            _required_text(raw_gap, field, label=f"{label} gaps[{index}]")


def _validate_test_design_gap_links_and_qualifiers(
    *,
    universe: Mapping[str, Any],
    catalog: Mapping[str, Any],
    data_manifest: Mapping[str, Any],
    coverage_matrix: Mapping[str, Any],
    gaps: Mapping[str, Any],
) -> None:
    obligations = {
        str(row.get("obligation_id") or "").strip(): row
        for row in universe.get("obligations", [])
        if isinstance(row, Mapping)
    }
    coverage_rows = {
        str(row.get("coverage_id") or "").strip(): row
        for row in coverage_matrix.get("rows", [])
        if isinstance(row, Mapping)
    }
    case_ids = {
        str(row.get("test_case_id") or "").strip()
        for row in catalog.get("cases", [])
        if isinstance(row, Mapping)
    }
    data_ids = {
        str(row.get("test_data_id") or "").strip()
        for row in data_manifest.get("datasets", [])
        if isinstance(row, Mapping)
    }
    coverage_by_obligation: set[str] = set()
    active_case_refs: set[str] = set()
    active_data_refs: set[str] = set()
    active_gap_count = 0
    gap_rows: dict[str, Mapping[str, Any]] = {}
    for raw_gap in gaps.get("gaps", []):
        gap = dict(raw_gap)
        gap_id = str(gap.get("gap_id") or "").strip()
        gap_rows[gap_id] = gap
        disposition = str(gap.get("disposition") or "").strip().lower()
        if disposition != "resolved":
            active_gap_count += 1
            active_case_refs.update(gap.get("affected_test_case_refs", []))
            active_data_refs.update(gap.get("affected_test_data_refs", []))
        for obligation_id in gap.get("affected_obligation_refs", []):
            obligation = obligations.get(obligation_id)
            if obligation is None:
                raise TaskAuthoringError(
                    f"{gap_id} references missing obligation {obligation_id}"
                )
            if gap_id not in obligation.get("gap_refs", []):
                raise TaskAuthoringError(
                    f"{gap_id} and {obligation_id} are missing a "
                    "bidirectional gap/obligation link"
                )
        for coverage_id in gap.get("coverage_refs", []):
            coverage = coverage_rows.get(coverage_id)
            if coverage is None:
                raise TaskAuthoringError(
                    f"{gap_id} references missing coverage row {coverage_id}"
                )
            if gap_id not in coverage.get("gap_refs", []):
                raise TaskAuthoringError(
                    f"{gap_id} and {coverage_id} are missing a "
                    "bidirectional gap/coverage link"
                )
        for case_id in gap.get("affected_test_case_refs", []):
            if case_id not in case_ids:
                raise TaskAuthoringError(
                    f"{gap_id} references missing test case {case_id}"
                )
        for data_id in gap.get("affected_test_data_refs", []):
            if data_id not in data_ids:
                raise TaskAuthoringError(
                    f"{gap_id} references missing test data {data_id}"
                )

    for coverage_id, row in coverage_rows.items():
        obligation_id = str(row.get("obligation_ref") or "").strip()
        obligation = obligations.get(obligation_id)
        if obligation is None:
            raise TaskAuthoringError(
                f"{coverage_id} references missing obligation {obligation_id}"
            )
        coverage_by_obligation.add(obligation_id)
        status_value = str(row.get("status") or "").strip().lower()
        applicability = str(
            obligation.get("applicability") or ""
        ).strip().lower()
        gap_refs = _strict_string_list(
            row,
            "gap_refs",
            label=coverage_id,
            require_nonempty=False,
        )
        if applicability == "not_applicable" and status_value != "not_applicable":
            raise TaskAuthoringError(
                f"{coverage_id} status {status_value} is incompatible with "
                f"not_applicable obligation {obligation_id}"
            )
        if applicability in {"excluded", "deferred"} and status_value != applicability:
            raise TaskAuthoringError(
                f"{coverage_id} status {status_value} must match obligation "
                f"{obligation_id} applicability {applicability}"
            )
        if applicability == "blocked" and status_value != "blocked":
            raise TaskAuthoringError(
                f"{coverage_id} status {status_value} must be blocked for "
                f"obligation {obligation_id}"
            )
        if applicability == "applicable" and status_value in {
            "not_applicable",
            "excluded",
            "deferred",
        }:
            raise TaskAuthoringError(
                f"{coverage_id} status {status_value} is incompatible with "
                f"applicable obligation {obligation_id}"
            )
        if status_value in {"covered", "not_applicable"} and gap_refs:
            raise TaskAuthoringError(
                f"{coverage_id} {status_value} row must not declare gap_refs"
            )
        if status_value in {
            "partial",
            "missing",
            "waived",
            "gap",
            "blocked",
            "deferred",
            "excluded",
        } and not gap_refs:
            raise TaskAuthoringError(
                f"{coverage_id} status {status_value} requires gap_refs"
            )
        active_coverage_gaps = 0
        for gap_id in gap_refs:
            gap = gap_rows.get(gap_id)
            if gap is None:
                raise TaskAuthoringError(
                    f"{coverage_id} references missing gap {gap_id}"
                )
            if gap_id not in obligation.get("gap_refs", []):
                raise TaskAuthoringError(
                    f"{coverage_id} gap {gap_id} is not declared by obligation "
                    f"{obligation_id}"
                )
            if coverage_id not in gap.get("coverage_refs", []):
                raise TaskAuthoringError(
                    f"{coverage_id} and {gap_id} are missing a bidirectional "
                    "coverage/gap link"
                )
            disposition = str(gap.get("disposition") or "").strip().lower()
            if disposition == "resolved":
                continue
            active_coverage_gaps += 1
            matches = False
            if status_value in {"partial", "missing", "gap"}:
                matches = disposition == "open"
            elif status_value in {"waived", "deferred", "excluded"}:
                matches = disposition == status_value
            elif status_value == "blocked":
                matches = disposition == "blocked" or (
                    str(gap.get("severity") or "").strip().lower()
                    == "blocking"
                    and disposition == "open"
                )
            if not matches:
                raise TaskAuthoringError(
                    f"{coverage_id} status {status_value} is inconsistent with "
                    f"active gap {gap_id} disposition {disposition}"
                )
        if gap_refs and active_coverage_gaps == 0:
            raise TaskAuthoringError(
                f"{coverage_id} non-covered status has no active gap"
            )

    for obligation_id, obligation in obligations.items():
        if (
            str(obligation.get("applicability") or "").strip().lower()
            == "applicable"
            and obligation_id not in coverage_by_obligation
        ):
            raise TaskAuthoringError(
                f"applicable obligation {obligation_id} is absent from the "
                "coverage matrix"
            )

    for row in data_manifest.get("datasets", []):
        readiness = str(row.get("readiness") or "").strip().lower()
        if readiness not in {
            "deferred",
            "evidence-needed",
            "human-input-required",
            "blocked",
        }:
            continue
        data_id = str(row.get("test_data_id") or "").strip()
        if data_id not in active_data_refs:
            raise TaskAuthoringError(
                f"{data_id} readiness {readiness} requires a non-resolved GAP "
                "affected_test_data_refs entry"
            )
    for row in catalog.get("cases", []):
        variants = row.get("variants")
        if not isinstance(variants, Mapping) or not any(
            str(value).strip().lower() == "deferred"
            for value in variants.values()
        ):
            continue
        case_id = str(row.get("test_case_id") or "").strip()
        if case_id not in active_case_refs:
            raise TaskAuthoringError(
                f"{case_id} deferred variant requires a non-resolved GAP "
                "affected_test_case_refs entry"
            )

    classified = _classify_test_design_claim(
        universe=universe,
        catalog=catalog,
        data_manifest=data_manifest,
        coverage_matrix=coverage_matrix,
        gaps=gaps,
    )
    if classified == "qualified_with_declared_gaps" and active_gap_count == 0:
        raise TaskAuthoringError(
            "qualified_with_declared_gaps requires at least one real "
            "non-resolved GAP"
        )


def _classify_test_design_claim(
    *,
    universe: Mapping[str, Any],
    catalog: Mapping[str, Any],
    data_manifest: Mapping[str, Any],
    coverage_matrix: Mapping[str, Any],
    gaps: Mapping[str, Any],
) -> str:
    claim = "complete_against_frozen_scope"
    for obligation in universe.get("obligations", []):
        applicability = str(obligation.get("applicability") or "").strip().lower()
        if applicability == "blocked":
            return "blocked"
        if applicability in {"excluded", "deferred"}:
            claim = "qualified_with_declared_gaps"
    for row in coverage_matrix.get("rows", []):
        status = str(row.get("status") or "").strip().lower()
        if status in {"blocked", "missing", "gap"}:
            return "blocked"
        if status in {
            "partial",
            "waived",
            "deferred",
            "excluded",
        }:
            claim = "qualified_with_declared_gaps"
    for gap in gaps.get("gaps", []):
        disposition = str(gap.get("disposition") or "").strip().lower()
        severity = str(gap.get("severity") or "").strip().lower()
        if severity == "blocking" and disposition not in {
            "resolved",
            "waived",
            "excluded",
        }:
            return "blocked"
        if disposition != "resolved":
            claim = "qualified_with_declared_gaps"
    if str(gaps.get("status") or "").strip().lower() == "blocked":
        return "blocked"
    for dataset in data_manifest.get("datasets", []):
        readiness = str(dataset.get("readiness") or "").strip().lower()
        if readiness in {"blocked", "human-input-required", "evidence-needed"}:
            return "blocked"
        if readiness == "deferred":
            claim = "qualified_with_declared_gaps"
    for candidate in catalog.get("cases", []):
        variants = candidate.get("variants")
        if isinstance(variants, Mapping) and any(
            str(value).strip().lower() == "deferred"
            for value in variants.values()
        ):
            claim = "qualified_with_declared_gaps"
    return claim


def _contained_test_design_path(test_design_root: Path, ref: str) -> Path:
    candidate = Path(ref.replace("/", os.sep))
    if not candidate.is_absolute():
        candidate = test_design_root / candidate
    try:
        return safe_local_state_path(candidate, root=test_design_root)
    except ValueError as exc:
        raise TaskAuthoringError(
            f"test-design artifact ref escapes its root: {ref}"
        ) from exc


def _digest_map(
    value: object,
    *,
    label: str,
    expected_keys: set[str],
) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise TaskAuthoringError(f"{label} is invalid")
    result: dict[str, str] = {}
    for key in sorted(expected_keys):
        raw = value.get(key)
        if not isinstance(raw, str):
            raise TaskAuthoringError(f"{label} {key} is invalid")
        digest = raw.strip()
        if not _SHA256_RE.fullmatch(digest):
            raise TaskAuthoringError(f"{label} {key} is invalid")
        result[key] = digest
    return result


def _verify_test_design_evidence_refs(root: Path, refs: list[str]) -> None:
    for ref in refs:
        normalized_ref = ref.replace("\\", "/").strip()
        if not _TEST_DESIGN_EVIDENCE_REF_RE.fullmatch(normalized_ref):
            raise TaskAuthoringError(
                f'evidence ref "{ref}" is not a canonical evidence record_ref'
            )
        record, _ = _read_object_with_raw(
            _project_ref_path(root, normalized_ref),
            root=root,
            label=f"evidence record {normalized_ref}",
        )
        expected_id = Path(normalized_ref).stem
        identity_fields = {
            "created_at": record.get("created_at"),
            "scope": record.get("scope"),
            "task_id": record.get("task_id", ""),
            "scenario_id": record.get("scenario_id", ""),
            "source": record.get("source"),
            "provenance": record.get("provenance"),
        }
        if any(not isinstance(value, str) for value in identity_fields.values()):
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} identity is forged"
            )
        for field in ("created_at", "mime", "source", "provenance"):
            if not isinstance(record.get(field), str) or not str(
                record[field]
            ).strip():
                raise TaskAuthoringError(
                    f"evidence record {normalized_ref} has invalid metadata"
                )
        created_at = str(record["created_at"]).strip()
        try:
            parsed_created_at = datetime.fromisoformat(
                created_at[:-1] + "+00:00" if created_at.endswith("Z") else created_at
            )
        except ValueError as exc:
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} created_at is not RFC3339"
            ) from exc
        if (
            not _RFC3339_RE.fullmatch(created_at)
            or parsed_created_at.tzinfo is None
            or parsed_created_at.utcoffset() is None
        ):
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} created_at is not RFC3339"
            )
        identity_seed = "\0".join(
            str(identity_fields[field]).strip()
            for field in (
                "created_at",
                "scope",
                "task_id",
                "scenario_id",
                "source",
                "provenance",
            )
        )
        recomputed_id = "evd-" + _sha256(identity_seed.encode("utf-8"))[:24]
        if (
            record.get("schema_version") != "spec-kit-evidence-v1"
            or record.get("record_ref") != normalized_ref
            or record.get("evidence_id") != expected_id
            or expected_id != recomputed_id
        ):
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} identity is forged"
            )
        if record.get("status") != "ready":
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} is not registered and ready"
            )
        if record.get("scope") != "test-design":
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} has incompatible scope "
                f"{record.get('scope')!r}"
            )
        sha256 = record.get("sha256")
        size = record.get("size")
        if (
            not isinstance(sha256, str)
            or not _SHA256_RE.fullmatch(sha256)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} has invalid content metadata"
            )
        expected_object_ref = (
            f".specify/evidence/objects/sha256/{sha256[:2]}/{sha256}"
        )
        if record.get("object_ref") != expected_object_ref:
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} object_ref is forged"
            )
        try:
            object_path = _project_ref_path(root, expected_object_ref)
            metadata = object_path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise OSError("object is not a regular non-symlink file")
            object_raw = read_local_state_bytes(object_path, root=root)
        except (OSError, ValueError) as exc:
            raise TaskAuthoringError(
                f"evidence object for {normalized_ref} is unavailable: {exc}"
            ) from exc
        if len(object_raw) != size or _sha256(object_raw) != sha256:
            raise TaskAuthoringError(
                f"evidence record {normalized_ref} failed content verification"
            )


def _validate_test_design_bundle_evidence(
    root: Path,
    *,
    coverage_matrix: Mapping[str, Any],
    data_manifest: Mapping[str, Any],
) -> None:
    for row in coverage_matrix.get("rows", []):
        coverage_id = str(row.get("coverage_id") or "").strip()
        refs = _strict_string_list(
            row,
            "evidence_refs",
            label=coverage_id,
            require_nonempty=False,
        )
        try:
            _verify_test_design_evidence_refs(root, refs)
        except TaskAuthoringError as exc:
            raise TaskAuthoringError(
                f"{coverage_id} evidence is invalid: {exc}"
            ) from exc
    for row in data_manifest.get("datasets", []):
        disposition = str(row.get("disposition") or "").strip().lower()
        readiness = str(row.get("readiness") or "").strip().lower()
        if disposition != "search" or readiness != "ready":
            continue
        data_id = str(row.get("test_data_id") or "").strip()
        refs = _strict_string_list(
            row,
            "provenance_refs",
            label=data_id,
            require_nonempty=True,
        )
        canonical = [
            ref for ref in refs if _TEST_DESIGN_EVIDENCE_REF_RE.fullmatch(ref)
        ]
        if not canonical:
            raise TaskAuthoringError(
                f"{data_id} has no canonical provenance evidence"
            )
        _verify_test_design_evidence_refs(root, canonical)


def _validate_test_design_audit_obligations(
    root: Path,
    value: object,
    *,
    lane_id: str,
    obligation_ids: set[str],
    canonical_gaps: Mapping[str, Mapping[str, Any]],
) -> None:
    if not isinstance(value, list):
        raise TaskAuthoringError("result obligation_results must be an array")
    seen: set[str] = set()
    expected_fields = {
        "obligation_id",
        "status",
        "evidence_refs",
        "gap_refs",
        "summary",
    }
    for index, raw_row in enumerate(value):
        if not isinstance(raw_row, Mapping) or set(raw_row) != expected_fields:
            raise TaskAuthoringError(
                f"result obligation_results[{index}] must use the canonical fields"
            )
        obligation_id = _required_text(
            raw_row,
            "obligation_id",
            label=f"result obligation_results[{index}]",
        )
        if (
            not _TEST_DESIGN_OBLIGATION_RE.fullmatch(obligation_id)
            or obligation_id not in obligation_ids
        ):
            raise TaskAuthoringError(
                f"result obligation_results[{index}] references unassigned "
                f"obligation {obligation_id}"
            )
        if obligation_id in seen:
            raise TaskAuthoringError(
                f"result obligation_results duplicates {obligation_id}"
            )
        seen.add(obligation_id)
        status_value = str(raw_row.get("status") or "").strip().lower()
        if status_value not in {"covered", "gap", "unknown", "not_applicable"}:
            raise TaskAuthoringError(
                f"result obligation_results[{index}] status is invalid"
            )
        evidence_refs = _strict_string_list(
            raw_row,
            "evidence_refs",
            label=obligation_id,
            require_nonempty=False,
        )
        _verify_test_design_evidence_refs(root, evidence_refs)
        gap_refs = _strict_string_list(
            raw_row,
            "gap_refs",
            label=obligation_id,
            require_nonempty=False,
        )
        for gap_id in gap_refs:
            if not _TEST_DESIGN_GAP_RE.fullmatch(gap_id):
                raise TaskAuthoringError(
                    f"{obligation_id} gap_ref {gap_id} is not canonical"
                )
            gap = canonical_gaps.get(gap_id)
            if gap is None:
                raise TaskAuthoringError(
                    f"{obligation_id} references missing canonical gap {gap_id}"
                )
            if str(gap.get("disposition") or "").strip().lower() == "resolved":
                raise TaskAuthoringError(
                    f"{obligation_id} references inactive canonical gap {gap_id}"
                )
            affected_obligations = gap.get("affected_obligation_refs")
            if (
                not isinstance(affected_obligations, list)
                or obligation_id not in affected_obligations
            ):
                raise TaskAuthoringError(
                    f"canonical gap {gap_id} does not affect {obligation_id}"
                )
        if status_value in {"covered", "not_applicable"} and (
            not evidence_refs or gap_refs
        ):
            raise TaskAuthoringError(
                f"{obligation_id} {status_value} accounting requires verified "
                "evidence and no gaps"
            )
        if status_value in {"gap", "unknown"} and not gap_refs:
            raise TaskAuthoringError(
                f"{obligation_id} {status_value} accounting requires gap_refs"
            )
        _required_text(raw_row, "summary", label=obligation_id)
    if seen != obligation_ids:
        raise TaskAuthoringError(
            f"audit lane {lane_id} obligation_results must account for exactly "
            "the frozen obligation set"
        )


def _validate_test_design_audit_checks(
    root: Path,
    value: object,
    *,
    obligation_ids: set[str],
) -> None:
    if not isinstance(value, list):
        raise TaskAuthoringError("result checks must be an array")
    seen: set[str] = set()
    expected_fields = {
        "check_id",
        "status",
        "evidence_refs",
        "affected_obligation_refs",
        "finding_refs",
        "summary",
    }
    for index, raw_row in enumerate(value):
        if not isinstance(raw_row, Mapping) or set(raw_row) != expected_fields:
            raise TaskAuthoringError(
                f"result checks[{index}] must use the canonical fields"
            )
        check_id = _required_text(
            raw_row, "check_id", label=f"result checks[{index}]"
        )
        if (
            not _TEST_DESIGN_AUDIT_CHECK_RE.fullmatch(check_id)
            or check_id in seen
        ):
            raise TaskAuthoringError(
                f"result checks[{index}] check_id is invalid or duplicated"
            )
        seen.add(check_id)
        status_value = str(raw_row.get("status") or "").strip().lower()
        if status_value not in {"passed", "finding", "blocked", "not_applicable"}:
            raise TaskAuthoringError(f"audit check {check_id} status is invalid")
        evidence_refs = _strict_string_list(
            raw_row,
            "evidence_refs",
            label=check_id,
            require_nonempty=False,
        )
        _verify_test_design_evidence_refs(root, evidence_refs)
        if status_value == "passed" and not evidence_refs:
            raise TaskAuthoringError(
                f"audit check {check_id} passed status requires verified evidence"
            )
        affected = _strict_string_list(
            raw_row,
            "affected_obligation_refs",
            label=check_id,
            require_nonempty=False,
        )
        foreign = sorted(set(affected) - obligation_ids)
        if foreign:
            raise TaskAuthoringError(
                f"audit check {check_id} references unassigned obligation "
                + foreign[0]
            )
        finding_refs = _strict_string_list(
            raw_row,
            "finding_refs",
            label=check_id,
            require_nonempty=False,
        )
        if status_value in {"finding", "blocked"} and not finding_refs:
            raise TaskAuthoringError(
                f"audit check {check_id} {status_value} status requires finding_refs"
            )
        if status_value in {"finding", "blocked"}:
            raise TaskAuthoringError(
                f"audit contains unresolved check {check_id}"
            )
        _required_text(raw_row, "summary", label=f"audit check {check_id}")
    if seen != _TEST_DESIGN_AUDIT_CORE_CHECK_IDS:
        raise TaskAuthoringError(
            "audit checks must contain exactly the runtime core check IDs"
        )


def _validate_test_design_audit_result(
    root: Path,
    result: Mapping[str, Any],
    *,
    lane: Mapping[str, Any],
    lane_id: str,
    obligation_ids: set[str],
    canonical_gaps: Mapping[str, Mapping[str, Any]],
) -> None:
    required_fields = {
        "lane_id",
        "attempt_id",
        "status",
        "inspected_paths",
        "evidence_refs",
        "obligation_results",
        "checks",
        "candidate_cases",
        "data_requirements",
        "contradictions",
        "unknowns",
        "gaps",
        "summary",
        "findings",
    }
    if set(result) != required_fields:
        raise TaskAuthoringError(
            f"audit result for {lane_id} must use the canonical fields"
        )
    if result.get("lane_id") != lane_id or result.get("attempt_id") != lane.get(
        "attempt_id"
    ):
        raise TaskAuthoringError(
            f"audit result for {lane_id} identity does not match its lane"
        )
    if result.get("status") != "success":
        raise TaskAuthoringError(
            f"audit result for {lane_id} must have success status"
        )
    inspected = _strict_string_list(
        result,
        "inspected_paths",
        label=f"audit result for {lane_id}",
        require_nonempty=True,
    )
    read_paths = _strict_string_list(
        lane,
        "read_paths",
        label=f"audit lane {lane_id}",
        require_nonempty=True,
    )
    if set(inspected) != set(read_paths) or len(inspected) != len(read_paths):
        raise TaskAuthoringError(
            "audit inspected_paths must cover every canonical audit input"
        )
    evidence_refs = _strict_string_list(
        result,
        "evidence_refs",
        label=f"audit result for {lane_id}",
        require_nonempty=True,
    )
    _verify_test_design_evidence_refs(root, evidence_refs)
    _validate_test_design_audit_obligations(
        root,
        result.get("obligation_results"),
        lane_id=lane_id,
        obligation_ids=obligation_ids,
        canonical_gaps=canonical_gaps,
    )
    _validate_test_design_audit_checks(
        root,
        result.get("checks"),
        obligation_ids=obligation_ids,
    )
    for field in (
        "candidate_cases",
        "data_requirements",
        "contradictions",
        "unknowns",
        "gaps",
        "findings",
    ):
        rows = result.get(field)
        if not isinstance(rows, list) or any(
            not isinstance(row, Mapping) for row in rows
        ):
            raise TaskAuthoringError(
                f"audit result for {lane_id} {field} must be an object array"
            )
    if result["contradictions"] or result["unknowns"] or result["gaps"]:
        raise TaskAuthoringError(
            f"audit lane {lane_id} returned unresolved findings"
        )
    for finding in result["findings"]:
        status_value = str(finding.get("status") or "").strip().lower()
        if status_value in {"", "open", "blocked", "unresolved"}:
            raise TaskAuthoringError(
                f"audit lane {lane_id} contains unresolved finding"
            )
    _required_text(result, "summary", label=f"audit result for {lane_id}")


def _validate_accepted_test_design_audit(
    *,
    root: Path,
    test_design_root: Path,
    state: Mapping[str, Any],
    universe: Mapping[str, Any],
    gaps: Mapping[str, Any],
    source_fingerprint: str,
    bundle_digests: dict[str, str],
) -> tuple[str, bytes]:
    manifest, _ = _read_object_with_raw(
        test_design_root / "lane-manifest.json",
        root=root,
        label="lane-manifest.json",
    )
    if (
        manifest.get("version") != 1
        or manifest.get("artifact") != "test-design-lane-manifest"
    ):
        raise TaskAuthoringError(
            "lane-manifest.json has an unsupported runtime contract"
        )
    leader_id = _required_text(
        manifest, "leader_id", label="lane-manifest.json"
    )
    synthesis_owner_id = _required_text(
        manifest, "synthesis_owner_id", label="lane-manifest.json"
    )
    if synthesis_owner_id != leader_id:
        raise TaskAuthoringError(
            "lane-manifest synthesis owner must equal the generation leader"
        )
    if manifest.get("generation_id") != "tdg-" + source_fingerprint[:16]:
        raise TaskAuthoringError("lane-manifest generation_id is stale")
    if manifest.get("status") != "accepted":
        raise TaskAuthoringError("lane-manifest is not accepted")
    synthesis_digests = _digest_map(
        manifest.get("synthesis_artifact_digests"),
        label="lane-manifest synthesis_artifact_digests",
        expected_keys=set(_TEST_DESIGN_BUNDLE_FILES.values()),
    )
    if synthesis_digests != bundle_digests:
        raise TaskAuthoringError("lane-manifest synthesis artifacts are stale")
    lanes = manifest.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise TaskAuthoringError("lane-manifest.json lanes must be a non-empty array")
    frozen_obligations = {
        str(row.get("obligation_id") or "").strip()
        for row in universe.get("obligations", [])
        if isinstance(row, Mapping)
    }
    if not frozen_obligations or any(
        not _TEST_DESIGN_OBLIGATION_RE.fullmatch(value)
        for value in frozen_obligations
    ):
        raise TaskAuthoringError("test-design audit has no canonical frozen obligations")
    applicable_obligations = {
        str(row.get("obligation_id") or "").strip()
        for row in universe.get("obligations", [])
        if isinstance(row, Mapping)
        and str(row.get("applicability") or "").strip().lower() == "applicable"
    }
    canonical_gaps = {
        str(row.get("gap_id") or "").strip(): row
        for row in gaps.get("gaps", [])
        if isinstance(row, Mapping)
    }
    discovery_workers: set[str] = set()
    discovery_obligations: set[str] = set()
    for index, raw_lane in enumerate(lanes):
        if not isinstance(raw_lane, Mapping):
            raise TaskAuthoringError(
                f"lane-manifest.json lanes[{index}] must be an object"
            )
        if raw_lane.get("state") != "accepted":
            raise TaskAuthoringError("lane-manifest contains a non-accepted lane")
        if str(raw_lane.get("kind") or "").strip().lower() != "discovery":
            continue
        worker_id = _required_text(
            raw_lane,
            "worker_id",
            label=f"discovery lane {index}",
        )
        discovery_workers.add(worker_id)
        discovery_obligations.update(
            _strict_string_list(
                raw_lane,
                "obligation_ids",
                label=f"discovery lane {index}",
                require_nonempty=True,
            )
        )
    if not discovery_workers or not applicable_obligations.issubset(
        discovery_obligations
    ):
        raise TaskAuthoringError(
            "lane-manifest lacks accepted discovery coverage for frozen obligations"
        )

    audit_state = state.get("audit")
    if not isinstance(audit_state, Mapping) or audit_state.get("status") != "accepted":
        raise TaskAuthoringError("test-design state has no accepted audit result")
    audit_lane_id = _required_text(
        audit_state, "lane_id", label="test-design state audit"
    )
    audit_result_ref = _required_text(
        audit_state, "result_ref", label="test-design state audit"
    )
    state_lanes = state.get("lanes")
    if not isinstance(state_lanes, Mapping):
        raise TaskAuthoringError("test-design state lanes are invalid")
    if state_lanes.get("manifest_ref") != "lane-manifest.json":
        raise TaskAuthoringError("test-design state lane manifest reference is stale")
    accepted_refs = _strict_string_list(
        state_lanes,
        "accepted_result_refs",
        label="test-design state lanes",
        require_nonempty=True,
    )
    if audit_result_ref not in accepted_refs:
        raise TaskAuthoringError(
            "test-design accepted audit result is absent from state lanes"
        )

    selected_result: tuple[str, bytes] | None = None
    for index, raw_lane in enumerate(lanes):
        if str(raw_lane.get("kind") or "").strip().lower() != "audit":
            continue
        lane_id = _required_text(
            raw_lane, "lane_id", label=f"lane-manifest audit lane {index}"
        )
        worker_id = _required_text(
            raw_lane, "worker_id", label=f"audit lane {lane_id}"
        )
        if worker_id in {leader_id, synthesis_owner_id, *discovery_workers}:
            raise TaskAuthoringError(
                f"audit lane {lane_id} worker is not independent"
            )
        lane_obligations = set(
            _strict_string_list(
                raw_lane,
                "obligation_ids",
                label=f"audit lane {lane_id}",
                require_nonempty=True,
            )
        )
        if lane_obligations != frozen_obligations:
            raise TaskAuthoringError(
                f"audit lane {lane_id} must cover exactly the frozen obligation set"
            )
        artifact_root = test_design_root.relative_to(root).as_posix()
        expected_read_paths = {
            f"{artifact_root}/{name}"
            for name in _TEST_DESIGN_BUNDLE_FILES.values()
        }
        audit_read_paths = set(
            _strict_string_list(
                raw_lane,
                "read_paths",
                label=f"audit lane {lane_id}",
                require_nonempty=True,
            )
        )
        if audit_read_paths != expected_read_paths:
            raise TaskAuthoringError(
                f"audit lane {lane_id} read_paths must cover exactly the "
                "canonical audit inputs"
            )
        if raw_lane.get("source_fingerprint") != source_fingerprint:
            raise TaskAuthoringError(f"audit lane {lane_id} is stale")
        lane_digests = _digest_map(
            raw_lane.get("artifact_digests"),
            label=f"audit lane {lane_id} artifact_digests",
            expected_keys=set(_TEST_DESIGN_BUNDLE_FILES.values()),
        )
        if lane_digests != bundle_digests:
            raise TaskAuthoringError(f"audit lane {lane_id} is stale")
        result_ref = _required_text(
            raw_lane, "result_ref", label=f"audit lane {lane_id}"
        )
        result, result_raw = _read_object_with_raw(
            _contained_test_design_path(test_design_root, result_ref),
            root=root,
            label=f"audit result for {lane_id}",
        )
        result_sha256 = _required_text(
            raw_lane, "result_sha256", label=f"audit lane {lane_id}"
        )
        if (
            not _SHA256_RE.fullmatch(result_sha256)
            or _sha256(result_raw) != result_sha256
        ):
            raise TaskAuthoringError(f"audit lane {lane_id} result digest changed")
        _validate_test_design_audit_result(
            root,
            result,
            lane=raw_lane,
            lane_id=lane_id,
            obligation_ids=frozen_obligations,
            canonical_gaps=canonical_gaps,
        )
        if lane_id == audit_lane_id:
            if result_ref != audit_result_ref:
                raise TaskAuthoringError(
                    "test-design state audit result reference is stale"
                )
            selected_result = (result_ref, result_raw)
    if selected_result is None:
        raise TaskAuthoringError(
            "test-design state accepted audit lane is absent from the manifest"
        )
    return selected_result


def _verify_published_test_design_handoff(
    root: Path,
    feature: Path,
    *,
    source_freshness_policy: str = "strict",
) -> dict[str, Any]:
    if source_freshness_policy not in _TEST_DESIGN_SOURCE_FRESHNESS_POLICIES:
        raise TaskAuthoringError(
            "test-design source freshness policy must be strict or "
            "bound_snapshot"
        )
    test_design_root = safe_local_state_path(feature / "test-design", root=root)
    handoff, handoff_raw = _read_object_with_raw(
        test_design_root / "handoff-to-tasks.json",
        root=root,
        label="handoff-to-tasks.json",
    )
    if (
        set(handoff) != _TEST_DESIGN_HANDOFF_FIELDS
        or handoff.get("schema_version") != "spec-kit-test-design-handoff-v1"
        or handoff.get("next_command") != "/sp.tasks"
    ):
        raise TaskAuthoringError(
            "handoff-to-tasks.json has an unsupported canonical contract"
        )
    handoff_revision = _required_positive_int(
        handoff, "state_revision", label="test-design handoff"
    )
    handoff_fingerprint = _required_text(
        handoff, "source_fingerprint", label="test-design handoff"
    )
    if not _SHA256_RE.fullmatch(handoff_fingerprint):
        raise TaskAuthoringError("test-design handoff source_fingerprint is invalid")
    handoff_claim = _required_text(
        handoff, "claim_status", label="test-design handoff"
    )
    if handoff_claim not in {
        "complete_against_frozen_scope",
        "qualified_with_declared_gaps",
    }:
        raise TaskAuthoringError(
            f"test-design claim {handoff_claim} is not consumable"
        )

    state, state_raw = _read_object_with_raw(
        test_design_root / "test-state.json",
        root=root,
        label="test-state.json",
    )
    if state.get("schema_version") != "spec-kit-test-design-state-v1":
        raise TaskAuthoringError("test-state.json has an unsupported runtime contract")
    state_revision = _required_positive_int(
        state, "revision", label="test-design state"
    )
    if state.get("phase") != "handed-off" or state.get("status") != "complete":
        raise TaskAuthoringError(
            "test-design state is not handed-off and complete"
        )
    state_claim = _required_text(
        state, "claim_status", label="test-design state"
    )
    if state_claim not in {
        "complete_against_frozen_scope",
        "qualified_with_declared_gaps",
    }:
        raise TaskAuthoringError(
            f"test-design claim {state_claim} is not consumable"
        )
    if handoff_revision != state_revision:
        raise TaskAuthoringError("test-design handoff state_revision is stale")
    source = state.get("source")
    if not isinstance(source, Mapping):
        raise TaskAuthoringError("test-design state source is invalid")
    source_fingerprint = _required_text(
        source, "fingerprint", label="test-design state source"
    )
    if not _SHA256_RE.fullmatch(source_fingerprint):
        raise TaskAuthoringError("test-design state source fingerprint is invalid")
    if handoff_fingerprint != source_fingerprint or handoff_claim != state_claim:
        raise TaskAuthoringError(
            "test-design handoff source or claim does not match state"
        )
    artifact_root = _required_text(
        state, "artifact_root", label="test-design state"
    )
    feature_ref = feature.relative_to(root).as_posix()
    if state.get("scope") != "feature" or state.get("feature_dir") != feature_ref:
        raise TaskAuthoringError(
            "test-design state must identify the selected feature workspace"
        )
    actual_artifact_root = test_design_root.relative_to(root).as_posix()
    if artifact_root != actual_artifact_root:
        raise TaskAuthoringError("test-design artifact root does not match state")
    source_refs = _strict_string_list(
        source,
        "source_refs",
        label="test-design state source",
        require_nonempty=True,
    )
    included_paths = _strict_string_list(
        source,
        "included_paths",
        label="test-design state source",
        require_nonempty=True,
    )
    excluded_paths = _strict_string_list(
        source,
        "excluded_paths",
        label="test-design state source",
        require_nonempty=False,
    )
    risk_dimensions = _strict_string_list(
        source,
        "risk_dimensions",
        label="test-design state source",
        require_nonempty=True,
    )
    if source_freshness_policy == "strict":
        current_fingerprint = _test_design_source_fingerprint(
            root,
            source_refs=source_refs,
            included_paths=included_paths,
            excluded_paths=excluded_paths,
            risk_dimensions=risk_dimensions,
            artifact_root=artifact_root,
        )
        if current_fingerprint != source_fingerprint:
            raise TaskAuthoringError(
                "test-design sources are stale: source fingerprint changed from "
                f"{source_fingerprint} to {current_fingerprint}"
            )

    bundle: dict[str, dict[str, Any]] = {}
    bundle_raw: dict[str, bytes] = {}
    for key, name in _TEST_DESIGN_BUNDLE_FILES.items():
        payload, raw = _read_object_with_raw(
            test_design_root / name,
            root=root,
            label=name,
        )
        bundle[key] = payload
        bundle_raw[key] = raw
    try:
        validate_test_intelligence_bundle(
            universe=bundle["universe"],
            catalog=bundle["catalog"],
            data_manifest=bundle["data_manifest"],
            coverage_matrix=bundle["coverage_matrix"],
        )
    except (TestIntelligenceValidationError, RuntimeError) as exc:
        raise TaskAuthoringError(str(exc)) from exc
    _validate_test_design_gaps(bundle["gaps"])
    _validate_test_design_gap_links_and_qualifiers(
        universe=bundle["universe"],
        catalog=bundle["catalog"],
        data_manifest=bundle["data_manifest"],
        coverage_matrix=bundle["coverage_matrix"],
        gaps=bundle["gaps"],
    )
    _validate_test_design_bundle_evidence(
        root,
        coverage_matrix=bundle["coverage_matrix"],
        data_manifest=bundle["data_manifest"],
    )
    classified_claim = _classify_test_design_claim(
        universe=bundle["universe"],
        catalog=bundle["catalog"],
        data_manifest=bundle["data_manifest"],
        coverage_matrix=bundle["coverage_matrix"],
        gaps=bundle["gaps"],
    )
    if classified_claim == "blocked" or classified_claim != state_claim:
        raise TaskAuthoringError(
            "test-design claim no longer matches the current bundle: "
            + classified_claim
        )
    bundle_digests = {
        _TEST_DESIGN_BUNDLE_FILES[key]: _sha256(raw)
        for key, raw in bundle_raw.items()
    }
    audit_result_ref, audit_raw = _validate_accepted_test_design_audit(
        root=root,
        test_design_root=test_design_root,
        state=state,
        universe=bundle["universe"],
        gaps=bundle["gaps"],
        source_fingerprint=source_fingerprint,
        bundle_digests=bundle_digests,
    )

    artifact_refs = handoff.get("artifact_refs")
    if not isinstance(artifact_refs, Mapping) or dict(artifact_refs) != _TEST_DESIGN_ARTIFACT_REFS:
        raise TaskAuthoringError("test-design handoff artifact_refs is invalid")
    if handoff.get("gap_ref") != "test-gaps.json" or handoff.get(
        "audit_result_ref"
    ) != audit_result_ref:
        raise TaskAuthoringError("test-design gap or audit reference is stale")
    expected_digests = {
        "state": _sha256(state_raw),
        "universe": bundle_digests["test-universe.json"],
        "catalog": bundle_digests["test-catalog.json"],
        "data_manifest": bundle_digests["test-data-manifest.json"],
        "coverage_matrix": bundle_digests["coverage-matrix.json"],
        "gaps": bundle_digests["test-gaps.json"],
        "audit_result": _sha256(audit_raw),
    }
    actual_digests = _digest_map(
        handoff.get("artifact_digests"),
        label="test-design handoff artifact_digests",
        expected_keys=set(expected_digests),
    )
    for key, expected in expected_digests.items():
        if actual_digests[key] != expected:
            raise TaskAuthoringError(
                f"test-design handoff digest {key} is stale"
            )

    case_refs = _strict_string_list(
        handoff,
        "test_case_refs",
        label="test-design handoff",
        require_nonempty=True,
    )
    expected_case_refs = sorted(
        "test-catalog.json#/cases/" + str(row["test_case_id"]).strip()
        for row in bundle["catalog"]["cases"]
    )
    if set(case_refs) != set(expected_case_refs) or len(case_refs) != len(
        expected_case_refs
    ):
        raise TaskAuthoringError(
            "test-design handoff test_case_refs do not match the catalog"
        )
    data_refs = _strict_string_list(
        handoff,
        "test_data_refs",
        label="test-design handoff",
        require_nonempty=False,
    )
    expected_data_refs = sorted(
        "test-data-manifest.json#/datasets/"
        + str(row["test_data_id"]).strip()
        for row in bundle["data_manifest"]["datasets"]
    )
    if set(data_refs) != set(expected_data_refs) or len(data_refs) != len(
        expected_data_refs
    ):
        raise TaskAuthoringError(
            "test-design handoff test_data_refs do not match the data manifest"
        )
    obligation_refs = sorted(
        "test-universe.json#/obligations/" + str(row["obligation_id"]).strip()
        for row in bundle["universe"]["obligations"]
    )
    coverage_refs = sorted(
        "coverage-matrix.json#/rows/" + str(row["coverage_id"]).strip()
        for row in bundle["coverage_matrix"]["rows"]
    )
    gap_refs = sorted(
        "test-gaps.json#/gaps/" + str(row["gap_id"]).strip()
        for row in bundle["gaps"]["gaps"]
    )
    publication_identity = {
        "scope": "feature",
        "artifact_root": actual_artifact_root,
        "source_fingerprint": source_fingerprint,
        "state_revision": state_revision,
        "claim_status": state_claim,
        "artifact_digests": expected_digests,
    }
    publication_payload = {
        "schema_version": "spec-kit-test-design-publication-v1",
        "publication_id": "tdpub-"
        + _canonical_json_sha256(publication_identity)[:24],
        "scope": "feature",
        "artifact_root": actual_artifact_root,
        "source_fingerprint": source_fingerprint,
        "state_revision": state_revision,
        "claim_status": state_claim,
        "artifact_refs": {
            **_TEST_DESIGN_ARTIFACT_REFS,
            "gaps": "test-gaps.json",
            "audit_result": audit_result_ref,
        },
        "artifact_digests": expected_digests,
        "obligation_refs": obligation_refs,
        "test_case_refs": expected_case_refs,
        "test_data_refs": expected_data_refs,
        "coverage_refs": coverage_refs,
        "gap_ref": "test-gaps.json",
        "gap_refs": gap_refs,
        "audit_result_ref": audit_result_ref,
        "forbidden_claims": _TEST_DESIGN_FORBIDDEN_CLAIMS,
        "test_execution_status": "not_executed_by_test_design",
    }
    return {
        "ref": f"{actual_artifact_root}/handoff-to-tasks.json",
        "sha256": _sha256(handoff_raw),
        "source_fingerprint": source_fingerprint,
        "state_revision": state_revision,
        "claim_status": state_claim,
        "artifact_root": actual_artifact_root,
        "artifact_digests": expected_digests,
        "test_case_refs": case_refs,
        "test_data_refs": data_refs,
        "publication_payload": publication_payload,
        "bundle": bundle,
    }


def _test_design_binding_empty(payload: Mapping[str, Any]) -> bool:
    for field in (
        "test_design_handoff_ref",
        "test_design_handoff_sha256",
        "test_design_source_fingerprint",
    ):
        value = payload.get(field)
        if value is not None and str(value).strip():
            return False
    revision = payload.get("test_design_state_revision")
    if revision is not None and revision != 0:
        return False
    digests = payload.get("test_design_artifact_digests")
    return digests is None or (isinstance(digests, Mapping) and not digests)


def _parse_plan_test_design_gate(
    plan: Mapping[str, Any], *, label: str
) -> tuple[str, dict[str, Any] | None]:
    raw_gate = plan.get("test_design_gate")
    if raw_gate is None:
        return "not_selected", None
    if not isinstance(raw_gate, Mapping):
        raise TaskAuthoringError(
            f"{label} test_design_gate must contain an object"
        )
    flattened_binding = _TEST_DESIGN_PROJECTION_BINDING_FIELDS & set(raw_gate)
    if flattened_binding:
        raise TaskAuthoringError(
            f"{label} test_design_gate projection fields must be nested under "
            "projection_binding"
        )
    raw_decision = raw_gate.get("decision")
    if not isinstance(raw_decision, str):
        raise TaskAuthoringError(
            f"{label} test_design_gate.decision must be "
            "not_selected, selected, or required"
        )
    decision = raw_decision.strip().lower()
    if decision not in {"not_selected", "selected", "required"}:
        raise TaskAuthoringError(
            f"{label} test_design_gate.decision must be "
            "not_selected, selected, or required"
        )
    reason_refs = raw_gate.get("reason_refs", [])
    if not isinstance(reason_refs, list) or any(
        not isinstance(item, str) or not item.strip() for item in reason_refs
    ):
        raise TaskAuthoringError(
            f"{label} test_design_gate.reason_refs must be an array of "
            "non-empty strings"
        )
    if len({item.strip() for item in reason_refs}) != len(reason_refs):
        raise TaskAuthoringError(
            f"{label} test_design_gate.reason_refs must not contain duplicates"
        )
    projection_binding = raw_gate.get("projection_binding")
    if projection_binding is None:
        return decision, None
    if not isinstance(projection_binding, Mapping):
        raise TaskAuthoringError(
            f"{label} test_design_gate.projection_binding must contain an object"
        )
    if set(projection_binding) != _TEST_DESIGN_PROJECTION_BINDING_FIELDS:
        raise TaskAuthoringError(
            f"{label} test_design_gate.projection_binding must contain exactly "
            + ", ".join(sorted(_TEST_DESIGN_PROJECTION_BINDING_FIELDS))
        )
    values = [projection_binding[field] for field in _TEST_DESIGN_PROJECTION_BINDING_FIELDS]
    if any(value is not None for value in values) and any(
        value is None for value in values
    ):
        raise TaskAuthoringError(
            f"{label} test_design_gate.projection_binding must be entirely null "
            "or entirely populated"
        )
    if all(value is None for value in values):
        return decision, None
    normalized_binding: dict[str, Any] = {}
    for field in ("publication_ref", "projection_ref"):
        value = projection_binding[field]
        if not isinstance(value, str) or not value.strip():
            raise TaskAuthoringError(
                f"{label} test_design_gate.projection_binding.{field} must be a "
                "non-empty project-relative reference"
            )
        normalized_binding[field] = _normalized_ref(value)
    for field in (
        "publication_sha256",
        "projection_sha256",
        "source_fingerprint",
    ):
        value = projection_binding[field]
        if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
            raise TaskAuthoringError(
                f"{label} test_design_gate.projection_binding.{field} must be a "
                "lowercase SHA-256 digest"
            )
        normalized_binding[field] = value
    revision = projection_binding["state_revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise TaskAuthoringError(
            f"{label} test_design_gate.projection_binding.state_revision must be "
            "a positive integer"
        )
    if decision == "not_selected":
        raise TaskAuthoringError(
            f"{label} not_selected test_design_gate must not retain a projection binding"
        )
    normalized_binding["state_revision"] = revision
    return decision, normalized_binding


def _plan_test_design_gate(
    root: Path, feature: Path
) -> tuple[str, dict[str, Any] | None]:
    decisions: list[tuple[str, str, dict[str, Any] | None]] = []
    for candidate in (
        feature / "plan-contract.json",
        feature / "plan" / "plan-contract.json",
    ):
        try:
            safe_candidate = safe_local_state_path(candidate, root=root)
            metadata = safe_candidate.lstat()
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            raise TaskAuthoringError(
                f"inspect plan-contract.json test_design_gate: {exc}"
            ) from exc
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise TaskAuthoringError(
                "plan-contract.json must be a regular non-symlink file"
            )
        label = candidate.relative_to(feature).as_posix()
        plan = _read_object(candidate, root=root, label=label)
        decisions.append(
            (label, *_parse_plan_test_design_gate(plan, label=label))
        )
    if not decisions:
        return "not_selected", None
    if len({decision for _, decision, _ in decisions}) != 1:
        rendered = ", ".join(
            f"{label}={decision}" for label, decision, _ in decisions
        )
        raise TaskAuthoringError(
            "conflicting plan-contract test_design_gate decisions: " + rendered
        )
    first_binding = decisions[0][2]
    if any(binding != first_binding for _, _, binding in decisions[1:]):
        rendered = ", ".join(
            f"{label}={binding!r}" for label, _, binding in decisions
        )
        raise TaskAuthoringError(
            "conflicting plan-contract test_design_gate bindings: " + rendered
        )
    return decisions[0][1], first_binding


def _test_design_row_index(
    payload: Mapping[str, Any], collection: str, id_field: str
) -> dict[str, Mapping[str, Any]]:
    rows = payload.get(collection)
    if not isinstance(rows, list):
        raise TaskAuthoringError(
            f"test-design {collection} must be an array for projection verification"
        )
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise TaskAuthoringError(
                f"test-design {collection} rows must contain objects"
            )
        row_id = str(row.get(id_field) or "").strip()
        if not row_id or row_id in indexed:
            raise TaskAuthoringError(
                f"test-design {collection} contains an invalid or duplicate {id_field}"
            )
        indexed[row_id] = row
    return indexed


def _test_design_string_values(row: Mapping[str, Any], field: str) -> list[str]:
    raw = row.get(field)
    if raw is None:
        return []
    if not isinstance(raw, list) or any(
        not isinstance(value, str) or not value.strip() for value in raw
    ):
        raise TaskAuthoringError(
            f"test-design projection source {field} must contain strings"
        )
    return [value.strip() for value in raw]


def _canonical_plan_projection_selection(
    bundle: Mapping[str, Mapping[str, Any]], selection: Any
) -> dict[str, list[str]]:
    prefixes = {
        "obligation_refs": "test-universe.json#/obligations/",
        "test_case_refs": "test-catalog.json#/cases/",
        "test_data_refs": "test-data-manifest.json#/datasets/",
        "coverage_refs": "coverage-matrix.json#/rows/",
        "gap_refs": "test-gaps.json#/gaps/",
    }
    if not isinstance(selection, Mapping) or set(selection) != set(prefixes):
        raise TaskAuthoringError(
            "test-design projection selection must contain exactly the five pointer arrays"
        )
    selected_ids: list[str] = []
    for field, prefix in prefixes.items():
        refs = selection.get(field)
        if not isinstance(refs, list) or (field == "obligation_refs" and not refs):
            raise TaskAuthoringError(
                f"test-design projection selection {field} is invalid"
            )
        if any(
            not isinstance(ref, str)
            or not ref.startswith(prefix)
            or not ref.removeprefix(prefix)
            for ref in refs
        ) or len(set(refs)) != len(refs):
            raise TaskAuthoringError(
                f"test-design projection selection {field} has non-canonical pointers"
            )
        if field == "obligation_refs":
            selected_ids = sorted(ref.removeprefix(prefix) for ref in refs)

    obligations = _test_design_row_index(
        bundle["universe"], "obligations", "obligation_id"
    )
    cases = _test_design_row_index(bundle["catalog"], "cases", "test_case_id")
    datasets = _test_design_row_index(
        bundle["data_manifest"], "datasets", "test_data_id"
    )
    coverage = _test_design_row_index(
        bundle["coverage_matrix"], "rows", "coverage_id"
    )
    gaps = _test_design_row_index(bundle["gaps"], "gaps", "gap_id")
    case_ids: set[str] = set()
    data_ids: set[str] = set()
    coverage_ids: set[str] = set()
    gap_ids: set[str] = set()
    selected = set(selected_ids)
    for obligation_id in selected_ids:
        obligation = obligations.get(obligation_id)
        if obligation is None:
            raise TaskAuthoringError(
                f"test-design projection selects missing obligation {obligation_id}"
            )
        case_ids.update(_test_design_string_values(obligation, "test_case_ids"))
        gap_ids.update(_test_design_string_values(obligation, "gap_refs"))
    for coverage_id, row in coverage.items():
        if str(row.get("obligation_ref") or "").strip() not in selected:
            continue
        coverage_ids.add(coverage_id)
        case_id = str(row.get("test_case_ref") or "").strip()
        if case_id:
            case_ids.add(case_id)
        data_ids.update(_test_design_string_values(row, "test_data_refs"))
        gap_ids.update(_test_design_string_values(row, "gap_refs"))
    for case_id in case_ids:
        case = cases.get(case_id)
        if case is None:
            raise TaskAuthoringError(
                f"test-design projection selects missing test case {case_id}"
            )
        data_ids.update(_test_design_string_values(case, "test_data_refs"))
    missing_data = data_ids - set(datasets)
    missing_gaps = gap_ids - set(gaps)
    if missing_data or missing_gaps:
        raise TaskAuthoringError(
            "test-design projection selection closure references missing data or gaps"
        )
    expected = {
        "obligation_refs": [prefixes["obligation_refs"] + value for value in selected_ids],
        "test_case_refs": [prefixes["test_case_refs"] + value for value in sorted(case_ids)],
        "test_data_refs": [prefixes["test_data_refs"] + value for value in sorted(data_ids)],
        "coverage_refs": [prefixes["coverage_refs"] + value for value in sorted(coverage_ids)],
        "gap_refs": [prefixes["gap_refs"] + value for value in sorted(gap_ids)],
    }
    if dict(selection) != expected:
        raise TaskAuthoringError(
            "test-design projection selection is stale or non-canonical"
        )
    return expected


def _verify_plan_test_design_projection_binding(
    root: Path,
    feature: Path,
    projection_binding: Mapping[str, Any],
    handoff_binding: Mapping[str, Any],
) -> None:
    feature_ref = feature.relative_to(root).as_posix()
    artifact_root = str(handoff_binding["artifact_root"]).strip()
    expected_publication_ref = f"{artifact_root}/test-design-publication.json"
    publication_ref = str(projection_binding["publication_ref"]).strip()
    if publication_ref != expected_publication_ref:
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.publication_ref is "
            "foreign or stale"
        )
    if str(projection_binding["source_fingerprint"]).strip() != str(
        handoff_binding["source_fingerprint"]
    ):
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.source_fingerprint is stale"
        )
    if int(projection_binding["state_revision"]) != int(
        handoff_binding["state_revision"]
    ):
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.state_revision is stale"
        )
    publication, publication_raw = _read_object_with_raw(
        _project_ref_path(root, publication_ref),
        root=root,
        label="test-design publication",
    )
    publication_sha256 = str(projection_binding["publication_sha256"]).strip()
    if _sha256(publication_raw) != publication_sha256:
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.publication_sha256 is stale"
        )
    expected_publication = handoff_binding["publication_payload"]
    if (
        publication != expected_publication
        or publication_raw != _go_json_bytes(expected_publication, pretty=True)
    ):
        raise TaskAuthoringError(
            "test-design publication is stale, non-canonical, or contains copied truth"
        )

    projection_ref = str(projection_binding["projection_ref"]).strip()
    expected_projection_prefix = f"{artifact_root}/projections/"
    if not projection_ref.startswith(expected_projection_prefix) or not projection_ref.endswith(
        ".json"
    ):
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.projection_ref is "
            "foreign or stale"
        )
    projection, projection_raw = _read_object_with_raw(
        _project_ref_path(root, projection_ref),
        root=root,
        label="test-design projection",
    )
    projection_sha256 = str(projection_binding["projection_sha256"]).strip()
    if _sha256(projection_raw) != projection_sha256:
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.projection_sha256 is stale"
        )
    if projection.get("schema_version") != "spec-kit-test-design-projection-v1":
        raise TaskAuthoringError("test-design projection has an unsupported contract")
    if _required_text(projection, "consumer", label="test-design projection") != "plan":
        raise TaskAuthoringError(
            "test-design projection must target the plan consumer before Tasks"
        )
    if _required_text(projection, "scope", label="test-design projection") != "feature":
        raise TaskAuthoringError(
            "test-design projection must stay on feature scope for Tasks"
        )
    if (
        _required_text(projection, "artifact_root", label="test-design projection")
        != artifact_root
    ):
        raise TaskAuthoringError("test-design projection artifact_root is stale")
    if (
        _required_text(projection, "publication_ref", label="test-design projection")
        != publication_ref
    ):
        raise TaskAuthoringError("test-design projection publication_ref is stale")
    if (
        _required_text(
            projection, "publication_sha256", label="test-design projection"
        )
        != publication_sha256
    ):
        raise TaskAuthoringError("test-design projection publication_sha256 is stale")
    if (
        _required_text(
            projection, "source_fingerprint", label="test-design projection"
        )
        != handoff_binding["source_fingerprint"]
    ):
        raise TaskAuthoringError(
            "test-design projection source_fingerprint is stale"
        )
    if (
        _required_positive_int(
            projection, "state_revision", label="test-design projection"
        )
        != handoff_binding["state_revision"]
    ):
        raise TaskAuthoringError("test-design projection state_revision is stale")
    if (
        _required_text(projection, "claim_status", label="test-design projection")
        != handoff_binding["claim_status"]
    ):
        raise TaskAuthoringError("test-design projection claim_status is stale")
    basis_ref = _normalized_ref(
        _required_text(projection, "basis_ref", label="test-design projection")
    )
    expected_basis_ref = f"{feature_ref}/spec-contract.json"
    if basis_ref != expected_basis_ref:
        raise TaskAuthoringError(
            "test-design projection basis_ref must target the current feature "
            "spec-contract.json"
        )
    _, basis_raw = _read_object_with_raw(
        _project_ref_path(root, basis_ref),
        root=root,
        label="test-design projection basis",
    )
    basis_sha256 = _required_text(
        projection, "basis_sha256", label="test-design projection"
    )
    if _sha256(basis_raw) != basis_sha256:
        raise TaskAuthoringError("test-design projection basis_sha256 is stale")
    selection = _canonical_plan_projection_selection(
        handoff_binding["bundle"], projection.get("selection")
    )
    selection_sha256 = _canonical_json_sha256(selection)
    projection_identity = {
        "consumer": "plan",
        "basis_ref": basis_ref,
        "selection_sha256": selection_sha256,
    }
    projection_id = "tdproj-" + _canonical_json_sha256(projection_identity)[:24]
    expected_projection_ref = (
        f"{artifact_root}/projections/{projection_id}.json"
    )
    if projection_ref != expected_projection_ref:
        raise TaskAuthoringError(
            "plan-contract test-design projection_binding.projection_ref does not "
            "match the canonical plan projection slot"
        )
    expected_projection = {
        "schema_version": "spec-kit-test-design-projection-v1",
        "projection_id": projection_id,
        "publication_ref": publication_ref,
        "publication_sha256": publication_sha256,
        "consumer": "plan",
        "basis_ref": basis_ref,
        "basis_sha256": basis_sha256,
        "scope": "feature",
        "artifact_root": artifact_root,
        "source_fingerprint": handoff_binding["source_fingerprint"],
        "state_revision": handoff_binding["state_revision"],
        "claim_status": handoff_binding["claim_status"],
        "selection": selection,
        "selection_sha256": selection_sha256,
        "forbidden_claims": _TEST_DESIGN_FORBIDDEN_CLAIMS,
        "test_execution_status": "not_executed_by_test_design",
    }
    if (
        projection != expected_projection
        or projection_raw != _go_json_bytes(expected_projection, pretty=True)
    ):
        raise TaskAuthoringError(
            "test-design projection is stale, non-canonical, or contains copied truth"
        )


def _clear_test_design_binding(payload: dict[str, Any]) -> None:
    payload["test_design_handoff_ref"] = None
    payload["test_design_handoff_sha256"] = None
    payload["test_design_source_fingerprint"] = None
    payload["test_design_state_revision"] = None
    payload["test_design_artifact_digests"] = {}


def _set_test_design_binding(
    payload: dict[str, Any], binding: Mapping[str, Any]
) -> None:
    payload["test_design_handoff_ref"] = binding["ref"]
    payload["test_design_handoff_sha256"] = binding["sha256"]
    payload["test_design_source_fingerprint"] = binding["source_fingerprint"]
    payload["test_design_state_revision"] = binding["state_revision"]
    payload["test_design_artifact_digests"] = deepcopy(
        binding["artifact_digests"]
    )


def _compare_test_design_binding(
    payload: Mapping[str, Any], binding: Mapping[str, Any]
) -> None:
    expected_scalars = {
        "test_design_handoff_ref": binding["ref"],
        "test_design_handoff_sha256": binding["sha256"],
        "test_design_source_fingerprint": binding["source_fingerprint"],
        "test_design_state_revision": binding["state_revision"],
    }
    if any(payload.get(key) != value for key, value in expected_scalars.items()):
        raise TaskAuthoringError(
            "task-index test-design binding is stale; rebuild tasks against "
            "the current handoff"
        )
    actual_digests = payload.get("test_design_artifact_digests")
    expected_digests = binding["artifact_digests"]
    if not isinstance(actual_digests, Mapping) or set(actual_digests) != set(
        expected_digests
    ):
        raise TaskAuthoringError(
            "task-index test-design artifact digests are missing or stale"
        )
    for key, expected in expected_digests.items():
        if actual_digests.get(key) != expected:
            raise TaskAuthoringError(
                f"task-index test-design artifact digest {key} is stale"
            )


def _validate_test_design_binding(
    root: Path,
    feature: Path,
    payload: dict[str, Any],
    *,
    bind: bool,
    require_all: bool,
    source_freshness_policy: str = "strict",
) -> None:
    if source_freshness_policy not in _TEST_DESIGN_SOURCE_FRESHNESS_POLICIES:
        raise TaskAuthoringError(
            "test-design source freshness policy must be strict or "
            "bound_snapshot"
        )
    plan_gate_decision, plan_projection_binding = _plan_test_design_gate(
        root, feature
    )
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise TaskAuthoringError("task-index tasks must be an array")
    used_cases: set[str] = set()
    used_data: set[str] = set()
    for raw_task in tasks:
        if not isinstance(raw_task, Mapping):
            raise TaskAuthoringError("task-index tasks must contain objects")
        for value in raw_task.get("test_case_refs", []):
            used_cases.add(str(value).strip())
        for value in raw_task.get("test_data_refs", []):
            used_data.add(str(value).strip())
    has_task_refs = bool(used_cases or used_data)
    handoff_path = feature / "test-design" / "handoff-to-tasks.json"
    try:
        safe_handoff_path = safe_local_state_path(handoff_path, root=root)
        safe_handoff_path.lstat()
    except FileNotFoundError:
        if plan_gate_decision in {"selected", "required"}:
            raise TaskAuthoringError(
                "plan-contract test-design gate decision "
                f"{plan_gate_decision} requires a current feature "
                "test-design/handoff-to-tasks.json before Tasks can continue"
            )
        existing_workspace_paths: list[str] = []
        for candidate in (
            feature / "test-design",
            feature / "test-design" / "test-state.json",
        ):
            try:
                safe_local_state_path(candidate, root=root).lstat()
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as exc:
                raise TaskAuthoringError(
                    f"inspect test-design workspace: {exc}"
                ) from exc
            existing_workspace_paths.append(candidate.relative_to(root).as_posix())
        if existing_workspace_paths:
            raise TaskAuthoringError(
                "test-design workspace exists without a current "
                "test-design/handoff-to-tasks.json; resume and complete or "
                "repair test-design before authoring or compiling tasks"
            )
        if has_task_refs:
            raise TaskAuthoringError(
                "task test_case_refs/test_data_refs require a current "
                "test-design/handoff-to-tasks.json"
            )
        if not bind and not _test_design_binding_empty(payload):
            raise TaskAuthoringError(
                "task-index test-design binding is stale because its handoff "
                "is missing"
            )
        if bind:
            _clear_test_design_binding(payload)
        return
    except (OSError, ValueError) as exc:
        raise TaskAuthoringError(f"inspect test-design handoff: {exc}") from exc
    try:
        binding = _verify_published_test_design_handoff(
            root,
            feature,
            source_freshness_policy=source_freshness_policy,
        )
    except TaskAuthoringError as exc:
        raise TaskAuthoringError(
            f"test-design handoff is stale or invalid: {exc}"
        ) from exc
    if plan_projection_binding is not None:
        _verify_plan_test_design_projection_binding(
            root,
            feature,
            plan_projection_binding,
            binding,
        )

    allowed_cases = set(binding["test_case_refs"])
    allowed_data = set(binding["test_data_refs"])
    for ref in sorted(used_cases):
        if ref not in allowed_cases:
            raise TaskAuthoringError(
                f"task test_case_ref {ref} is not a member of the "
                "test-design handoff"
            )
    for ref in sorted(used_data):
        if ref not in allowed_data:
            raise TaskAuthoringError(
                f"task test_data_ref {ref} is not a member of the "
                "test-design handoff"
            )
    if require_all:
        for ref in binding["test_case_refs"]:
            if ref not in used_cases:
                raise TaskAuthoringError(
                    f"test-design case {ref} is not consumed by any task"
                )
        for ref in binding["test_data_refs"]:
            if ref not in used_data:
                raise TaskAuthoringError(
                    f"test-design data {ref} is not consumed by any task"
                )
    if bind:
        _set_test_design_binding(payload, binding)
    else:
        _compare_test_design_binding(payload, binding)


def validate_task_test_design_binding(
    project_root: Path,
    feature_dir: Path | str,
    task_index: Mapping[str, Any],
    *,
    require_all: bool,
    source_freshness_policy: str = "strict",
) -> dict[str, Any]:
    """Revalidate and return the runtime-owned test-design packet binding."""

    root, feature = _project_feature(project_root, feature_dir)
    payload = deepcopy(dict(task_index))
    _validate_test_design_binding(
        root,
        feature,
        payload,
        bind=False,
        require_all=require_all,
        source_freshness_policy=source_freshness_policy,
    )
    return {
        "test_design_handoff_ref": deepcopy(
            payload.get("test_design_handoff_ref")
        ),
        "test_design_handoff_sha256": deepcopy(
            payload.get("test_design_handoff_sha256")
        ),
        "test_design_source_fingerprint": deepcopy(
            payload.get("test_design_source_fingerprint")
        ),
        "test_design_state_revision": deepcopy(
            payload.get("test_design_state_revision")
        ),
        "test_design_artifact_digests": deepcopy(
            payload.get("test_design_artifact_digests") or {}
        ),
    }


def _load_template(root: Path) -> dict[str, Any]:
    return _read_object(
        root / ".specify" / "templates" / "task-index-template.json",
        root=root,
        label="task-index template",
    )


def _normalize_task_id(value: object) -> str:
    task_id = str(value or "").strip().upper()
    if not _TASK_ID_RE.fullmatch(task_id):
        raise TaskAuthoringError(f"task id must match T<digits>: {value!r}")
    return task_id


def _string_list(value: object, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TaskAuthoringError(f"{label} must be an array")
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise TaskAuthoringError(f"{label} must contain non-empty strings")
        if text not in result:
            result.append(text)
    return result


def _normalize_task(
    raw_task: object, *, allow_runtime_fields: bool
) -> dict[str, Any]:
    if not isinstance(raw_task, Mapping):
        raise TaskAuthoringError("each task must be a JSON object")
    task = deepcopy(dict(raw_task))
    title = str(task.get("title") or "").strip()
    if title and not str(task.get("objective") or "").strip():
        task["objective"] = title
    task.pop("title", None)
    if "acceptance" not in task and "done_condition" in task:
        task["acceptance"] = task["done_condition"]
    task.pop("done_condition", None)
    obsolete = sorted(_OBSOLETE_TASK_FIELDS & task.keys())
    if obsolete:
        raise TaskAuthoringError(
            "task contains obsolete fields: " + ", ".join(obsolete)
        )
    protected = sorted(_PROTECTED_TASK_FIELDS & task.keys())
    if protected and not allow_runtime_fields:
        raise TaskAuthoringError(
            "task contains CLI-owned fields: " + ", ".join(protected)
        )
    unknown = sorted(set(task) - _AUTHORED_TASK_FIELDS - _PROTECTED_TASK_FIELDS)
    if unknown and not allow_runtime_fields:
        raise TaskAuthoringError(
            "task contains unsupported fields: "
            + ", ".join(unknown)
            + "; accepted fields include objective (alias: title), acceptance (alias: done_condition)"
        )
    task_id = _normalize_task_id(task.get("id", task.get("task_id")))
    objective = str(task.get("objective") or "").strip()
    if not objective:
        raise TaskAuthoringError(
            f"{task_id} objective is required (title is accepted as an alias)"
        )
    task.pop("task_id", None)
    task["id"] = task_id
    task["objective"] = objective
    task["dependencies"] = [
        _normalize_task_id(item)
        for item in _string_list(
            task.get("dependencies", task.get("depends_on", [])),
            label=f"{task_id} dependencies",
        )
    ]
    task.pop("depends_on", None)
    task["expected_write_scope"] = _string_list(
        task.get("expected_write_scope", task.get("write_scope", [])),
        label=f"{task_id} expected_write_scope",
    )
    task.pop("write_scope", None)
    for key in (
        "read_scope",
        "required_refs",
        "authoritative_refs",
        "policy_refs",
        "forbidden_drift",
        "hard_rules",
        "acceptance",
        "verification",
        "required_validation",
        "task_checks",
        "consumer_surfaces",
        "required_consumer_evidence",
        "required_evidence",
        "test_case_refs",
        "test_data_refs",
        "must_preserve_ids",
        "must_preserve_refs",
        "consequence_obligation_ids",
        "consequence_obligation_refs",
        "capability_operations",
        "capability_operation_refs",
        "fidelity_refs",
        "acceptance_refs",
        "user_confirmed_deferral_refs",
        "stop_and_reopen_conditions",
        "skills",
    ):
        if key in task:
            task[key] = _string_list(task[key], label=f"{task_id} {key}")
    status = str(task.get("status") or "pending").strip().lower()
    if status not in {
        "pending",
        "ready",
        "in_progress",
        "implemented",
        "accepted",
        "blocked",
        "failed",
        "deferred",
    }:
        raise TaskAuthoringError(f"{task_id} status is invalid: {status}")
    task["status"] = status
    return task


def _normalize_tasks(
    raw_tasks: object, *, allow_runtime_fields: bool
) -> list[dict[str, Any]]:
    if not isinstance(raw_tasks, list):
        raise TaskAuthoringError("tasks must be an array")
    tasks = [
        _normalize_task(item, allow_runtime_fields=allow_runtime_fields)
        for item in raw_tasks
    ]
    seen: set[str] = set()
    for task in tasks:
        task_id = task["id"]
        if task_id in seen:
            raise TaskAuthoringError(f"duplicate task id: {task_id}")
        seen.add(task_id)
    return tasks


def _expand_ui_contracts(
    root: Path, tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    defaults: dict[str, Any] | None = None
    for task in tasks:
        if "ui_contract" not in task or task["ui_contract"] is None:
            continue
        ui_contract = task["ui_contract"]
        if not isinstance(ui_contract, Mapping):
            raise TaskAuthoringError(
                f"{task['id']} ui_contract must be a JSON object"
            )
        if not ui_contract:
            continue
        if defaults is None:
            packet_template = _read_object(
                root / ".specify" / "templates" / "task-packet-template.json",
                root=root,
                label="task-packet template",
            )
            raw_defaults = packet_template.get("ui_contract")
            if not isinstance(raw_defaults, dict) or not raw_defaults:
                raise TaskAuthoringError(
                    "task-packet template ui_contract must be a non-empty JSON object"
                )
            defaults = raw_defaults
        unknown = sorted(set(ui_contract) - set(defaults))
        if unknown:
            raise TaskAuthoringError(
                f"{task['id']} ui_contract contains unsupported fields: "
                + ", ".join(unknown)
            )
        expanded = deepcopy(defaults)
        expanded.update(deepcopy(dict(ui_contract)))
        task["ui_contract"] = expanded
    return tasks


def _overlay_definition(
    root: Path, template: dict[str, Any], definition: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    allowed = set(template) | {"title"}
    unknown = sorted(set(definition) - allowed)
    if unknown:
        raise TaskAuthoringError(
            "task definition contains unsupported root fields: " + ", ".join(unknown)
        )
    payload = deepcopy(template)
    title = str(definition.get("title") or "Feature implementation").strip()
    for key, value in definition.items():
        if key == "title":
            continue
        if key in {
            "version",
            "status",
            "transition",
            *_TEST_DESIGN_ROOT_FIELDS,
        }:
            raise TaskAuthoringError(f"{key} is CLI-owned and cannot be authored")
        payload[key] = deepcopy(value)
    payload["version"] = 2
    payload["status"] = "draft"
    payload["tasks"] = _expand_ui_contracts(
        root,
        _normalize_tasks(payload.get("tasks"), allow_runtime_fields=False),
    )
    transition = payload.get("transition")
    if not isinstance(transition, dict):
        transition = {}
        payload["transition"] = transition
    transition.update(
        {
            "version": 1,
            "status": "blocked",
            "source_ref": "task-index.json",
            "blockers": ["task package has not been finalized"],
            "next_action": "Run `specify-runtime tasks finalize` after task review.",
        }
    )
    return payload, title or "Feature implementation"


def _render_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    return ", ".join(f"`{str(value)}`" for value in values)


def _render_tasks_markdown(task_index: Mapping[str, Any], *, title: str) -> str:
    tasks = task_index.get("tasks")
    if not isinstance(tasks, list):
        raise TaskAuthoringError("task-index tasks must be an array")
    lines = [
        f"# Tasks: {title}",
        "",
        "> Generated by `specify-runtime tasks`; `task-index.json` is canonical.",
        "",
        "## Task List",
        "",
    ]
    for raw_task in tasks:
        task = dict(raw_task)
        checked = "x" if task.get("status") in _TERMINAL_STATUSES else " "
        markers: list[str] = []
        if task.get("parallel") is True:
            markers.append("[P]")
        story_id = str(task.get("story_id") or "").strip()
        if story_id:
            markers.append(f"[{story_id}]")
        marker_text = (" " + " ".join(markers)) if markers else ""
        lines.append(
            f"- [{checked}] {task['id']}{marker_text} {task['objective']}"
        )

    lines.extend(
        [
            "",
            "## Consequence Obligation Mapping",
            "",
            "| Obligation ID | Task IDs |",
            "| --- | --- |",
        ]
    )
    consequence_map: dict[str, list[str]] = {}
    for raw_task in tasks:
        task = dict(raw_task)
        for obligation_id in task.get("consequence_obligation_ids", []):
            consequence_map.setdefault(str(obligation_id), []).append(str(task["id"]))
    if consequence_map:
        for obligation_id, task_ids in consequence_map.items():
            lines.append(f"| {obligation_id} | {', '.join(task_ids)} |")
    else:
        lines.append("| None | None |")

    for raw_task in tasks:
        task = dict(raw_task)
        task_id = str(task["id"])
        lines.extend(
            [
                "",
                f"## {task_id} — {task['objective']}",
                "",
                "### Scope Boundaries",
                "",
                "| Field | Value |",
                "| --- | --- |",
                f"| read_scope | {_render_list(task.get('read_scope'))} |",
                f"| write_scope | {_render_list(task.get('expected_write_scope'))} |",
                f"| required_refs | {_render_list(task.get('required_refs'))} |",
                f"| test_case_refs | {_render_list(task.get('test_case_refs'))} |",
                f"| test_data_refs | {_render_list(task.get('test_data_refs'))} |",
                f"| dependencies | {_render_list(task.get('dependencies'))} |",
                "",
                "### Acceptance and Verification",
                "",
                f"- Acceptance: {_render_list(task.get('acceptance'))}",
                f"- Verification: {_render_list(task.get('verification'))}",
            ]
        )
        ui_contract = task.get("ui_contract")
        if isinstance(ui_contract, dict) and any(ui_contract.values()):
            lines.extend(
                [
                    "",
                    "### UI Implementation Contract",
                    "",
                    "| Field | Value |",
                    "| --- | --- |",
                    f"| ui_contract_ref | task-index.json#/tasks/{task_id}/ui_contract |",
                    f"| fidelity_level | {ui_contract.get('fidelity_level', 'none')} |",
                    f"| required_states | {_render_list(ui_contract.get('required_states'))} |",
                    f"| required_evidence | {_render_list(ui_contract.get('required_evidence'))} |",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _receipt(
    *,
    status: str,
    task_index: Mapping[str, Any],
    task_index_bytes: bytes,
    markdown_bytes: bytes,
    transaction: object,
) -> dict[str, Any]:
    transaction_payload = transaction.to_dict()
    return {
        "status": "ok",
        "package_status": status,
        **transaction_payload,
        "task_count": len(task_index.get("tasks", [])),
        "task_index_ref": next(
            path
            for path in transaction_payload["changed_paths"]
            if path.endswith("/task-index.json")
        ),
        "tasks_ref": next(
            path
            for path in transaction_payload["changed_paths"]
            if path.endswith("/tasks.md")
        ),
        "task_index_sha256": _sha256(task_index_bytes),
        "tasks_sha256": _sha256(markdown_bytes),
    }


def _commit(
    root: Path,
    feature: Path,
    task_index: dict[str, Any],
    *,
    title: str,
    kind: str,
    require_all_test_design_refs: bool = False,
) -> dict[str, Any]:
    _validate_test_design_binding(
        root,
        feature,
        task_index,
        bind=False,
        require_all=require_all_test_design_refs,
    )
    task_index_bytes = _json_bytes(task_index)
    markdown_bytes = _render_tasks_markdown(task_index, title=title).encode("utf-8")
    try:
        transaction = apply_workflow_transaction(
            root,
            kind=kind,
            updates={
                feature / "task-index.json": task_index_bytes,
                feature / "tasks.md": markdown_bytes,
            },
        )
    except WorkflowTransactionError as exc:
        raise TaskAuthoringError(str(exc)) from exc
    return _receipt(
        status=str(task_index["status"]),
        task_index=task_index,
        task_index_bytes=task_index_bytes,
        markdown_bytes=markdown_bytes,
        transaction=transaction,
    )


def build_task_package(
    project_root: Path,
    feature_dir: Path | str,
    definition: Mapping[str, Any],
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    if (feature / "task-index.json").exists() or (feature / "tasks.md").exists():
        raise TaskAuthoringError(
            "task package already exists; use tasks upsert, set-root, or remove"
        )
    task_index, title = _overlay_definition(root, _load_template(root), definition)
    _validate_test_design_binding(
        root,
        feature,
        task_index,
        bind=True,
        require_all=False,
    )
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.build",
    )


def _load_task_package(
    project_root: Path, feature_dir: Path | str
) -> tuple[Path, Path, dict[str, Any], str]:
    root, feature = _project_feature(project_root, feature_dir)
    task_index = _read_object(
        feature / "task-index.json", root=root, label="task-index.json"
    )
    if task_index.get("version") != 2:
        raise TaskAuthoringError("task-index.json must use version 2")
    tasks = _expand_ui_contracts(
        root,
        _normalize_tasks(task_index.get("tasks"), allow_runtime_fields=True),
    )
    task_index["tasks"] = tasks
    title = feature.name
    tasks_path = feature / "tasks.md"
    if tasks_path.is_file():
        try:
            first_line = read_local_state_text(tasks_path, root=root).splitlines()[0]
            if first_line.startswith("# Tasks:"):
                title = first_line.partition(":")[2].strip() or title
        except (OSError, UnicodeError, IndexError):
            pass
    return root, feature, task_index, title


def upsert_task(
    project_root: Path,
    feature_dir: Path | str,
    task: Mapping[str, Any],
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    normalized = _expand_ui_contracts(
        root,
        [_normalize_task(task, allow_runtime_fields=False)],
    )[0]
    tasks = task_index["tasks"]
    for index, existing in enumerate(tasks):
        if existing["id"] != normalized["id"]:
            continue
        existing_status = str(existing.get("status") or "pending")
        if existing_status not in _AUTHORING_MUTABLE_STATUSES:
            raise TaskAuthoringError(
                f"{normalized['id']} has runtime status {existing_status} and cannot "
                "be replaced through task authoring"
            )
        tasks[index] = normalized
        break
    else:
        tasks.append(normalized)
    task_index["status"] = "draft"
    transition = task_index.get("transition")
    if isinstance(transition, dict):
        transition["status"] = "blocked"
        transition["blockers"] = ["task package changed after its last finalize"]
        transition["next_action"] = "Run `specify-runtime tasks finalize`."
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.upsert",
    )


def remove_task(
    project_root: Path, feature_dir: Path | str, task_id: str
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    normalized_id = _normalize_task_id(task_id)
    tasks = task_index["tasks"]
    existing = next((task for task in tasks if task["id"] == normalized_id), None)
    if existing is None:
        raise TaskAuthoringError(f"unknown task: {normalized_id}")
    existing_status = str(existing.get("status") or "pending")
    if existing_status not in _AUTHORING_MUTABLE_STATUSES:
        raise TaskAuthoringError(
            f"{normalized_id} has runtime status {existing_status} and cannot be "
            "removed through task authoring"
        )
    task_index["tasks"] = [task for task in tasks if task["id"] != normalized_id]
    for task in task_index["tasks"]:
        if normalized_id in task.get("dependencies", []):
            raise TaskAuthoringError(
                f"{normalized_id} is still required by {task['id']}; update that task first"
            )
    task_index["status"] = "draft"
    transition = task_index.get("transition")
    if isinstance(transition, dict):
        transition["status"] = "blocked"
        transition["blockers"] = ["task package changed after its last finalize"]
        transition["next_action"] = "Run `specify-runtime tasks finalize`."
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.remove",
    )


def set_task_root_fields(
    project_root: Path,
    feature_dir: Path | str,
    patch: Mapping[str, Any],
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    template = _load_template(root)
    unknown = sorted(set(patch) - set(template))
    protected = sorted(set(patch) & _PROTECTED_ROOT_FIELDS)
    if unknown:
        raise TaskAuthoringError(
            "root patch contains unsupported fields: " + ", ".join(unknown)
        )
    if protected:
        detail = ", ".join(protected)
        if "transition" in protected:
            raise TaskAuthoringError(
                "root patch contains CLI-owned fields: "
                + detail
                + "; transition is written only by tasks finalize/handoff "
                "(do not set next_action/status via set-root)"
            )
        raise TaskAuthoringError(
            "root patch contains CLI-owned fields: " + detail
        )
    for key, value in patch.items():
        task_index[key] = deepcopy(value)
    task_index["status"] = "draft"
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.set-root",
    )


def _validate_dependency_graph(tasks: list[dict[str, Any]]) -> None:
    ids = {task["id"] for task in tasks}
    for task in tasks:
        for dependency in task["dependencies"]:
            if dependency not in ids:
                raise TaskAuthoringError(
                    f"{task['id']} references unknown dependency {dependency}"
                )
            if dependency == task["id"]:
                raise TaskAuthoringError(f"{task['id']} cannot depend on itself")

    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {task["id"]: task for task in tasks}

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise TaskAuthoringError(f"task dependency cycle contains {task_id}")
        visiting.add(task_id)
        for dependency in by_id[task_id]["dependencies"]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)


def _validate_acceptance_projection(feature: Path, task_index: dict[str, Any]) -> None:
    plan_path = feature / "plan-contract.json"
    if not plan_path.is_file():
        nested = feature / "plan" / "plan-contract.json"
        plan_path = nested if nested.is_file() else plan_path
    if not plan_path.is_file():
        return
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskAuthoringError(f"plan-contract.json is invalid: {exc}") from exc
    if not isinstance(plan, dict):
        raise TaskAuthoringError("plan-contract.json must contain an object")
    expected = plan.get("acceptance_refs", [])
    if not isinstance(expected, list):
        raise TaskAuthoringError("plan-contract acceptance_refs must be an array")
    task_index["acceptance_refs"] = _normalize_task_index_acceptance_refs(
        task_index.get("acceptance_refs"),
        expected,
        plan_label="plan-contract.json",
    )
    _rewrite_acceptance_source_refs(
        task_index,
        expected,
        plan_label="plan-contract.json",
    )
    if expected:
        for field in (
            "official_entrypoints",
            "system_review_scenarios",
            "review_obligations",
            "human_acceptance_obligations",
            "human_acceptance_scenarios",
        ):
            if not isinstance(task_index.get(field), list) or not task_index[field]:
                raise TaskAuthoringError(
                    f"task-index {field} is required when acceptance_refs are present"
                )


def _parse_plan_acceptance_pointer(value: str, plan_label: str) -> int | None:
    text = str(value or "").strip()
    for prefix in (
        f"{plan_label}#/acceptance_refs/",
        "plan-contract.json#/acceptance_refs/",
        "#/acceptance_refs/",
    ):
        if not text.startswith(prefix):
            continue
        suffix = text[len(prefix) :]
        if not suffix.isdigit():
            return None
        return int(suffix)
    return None


def _normalize_task_index_acceptance_refs(
    actual: object,
    expected: list[Any],
    *,
    plan_label: str,
) -> list[Any]:
    if actual is None:
        if not expected:
            return []
        preview = ", ".join(str(item) for item in expected) or "[]"
        raise TaskAuthoringError(
            "task-index acceptance_refs must exactly copy "
            "plan-contract.acceptance_refs values in order "
            f"(example values: [{preview}]); pointer form "
            f"{plan_label}#/acceptance_refs/N is also accepted and rewritten"
        )
    if not isinstance(actual, list):
        raise TaskAuthoringError("task-index acceptance_refs must be an array")
    if actual == expected:
        return deepcopy(expected)
    expanded: list[Any] = []
    for item in actual:
        text = str(item).strip()
        if not text:
            raise TaskAuthoringError(
                "task-index acceptance_refs must contain non-empty strings"
            )
        index = _parse_plan_acceptance_pointer(text, plan_label)
        if index is not None:
            if index < 0 or index >= len(expected):
                raise TaskAuthoringError(
                    f"task-index acceptance_refs pointer {text!r} is out of range "
                    f"for {plan_label} ({len(expected)} refs)"
                )
            expanded.append(expected[index])
            continue
        expanded.append(text)
    if expanded != expected:
        expected_preview = ", ".join(str(item) for item in expected)
        actual_preview = ", ".join(str(item) for item in expanded)
        raise TaskAuthoringError(
            "task-index acceptance_refs must exactly preserve "
            "plan-contract.acceptance_refs values and order; "
            f"expected [{expected_preview}], got [{actual_preview}] "
            f"(pointer form {plan_label}#/acceptance_refs/N is accepted and rewritten)"
        )
    return deepcopy(expected)


def _rewrite_acceptance_source_refs(
    task_index: dict[str, Any],
    expected: list[Any],
    *,
    plan_label: str,
) -> None:
    pointer_to_value: dict[str, Any] = {}
    for index, value in enumerate(expected):
        pointer_to_value[f"{plan_label}#/acceptance_refs/{index}"] = value
        pointer_to_value[f"plan-contract.json#/acceptance_refs/{index}"] = value
        pointer_to_value[f"#/acceptance_refs/{index}"] = value
    for field in ("human_acceptance_obligations", "review_obligations"):
        rows = task_index.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source_ref") or "").strip()
            if source in pointer_to_value:
                row["source_ref"] = pointer_to_value[source]
    for field in ("system_review_scenarios", "human_acceptance_scenarios"):
        rows = task_index.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or "acceptance_refs" not in row:
                continue
            refs = row.get("acceptance_refs")
            if not isinstance(refs, list):
                continue
            row["acceptance_refs"] = [
                pointer_to_value.get(str(item).strip(), item) for item in refs
            ]


def finalize_task_package(
    project_root: Path, feature_dir: Path | str
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    tasks = task_index["tasks"]
    if not tasks:
        raise TaskAuthoringError("task package must contain at least one task")
    _validate_dependency_graph(tasks)
    _validate_acceptance_projection(feature, task_index)
    _validate_test_design_binding(
        root,
        feature,
        task_index,
        bind=False,
        require_all=True,
    )
    task_index["status"] = "ready"
    transition = task_index.get("transition")
    if not isinstance(transition, dict):
        transition = {}
        task_index["transition"] = transition
    transition.update(
        {
            "version": 1,
            "status": "ready",
            "source_ref": "task-index.json",
            "required_refs": list(task_index.get("acceptance_refs", [])),
            "blockers": [],
            "next_action": "Run sp-implement or spx-implement.",
            "recovery": None,
        }
    )
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.finalize",
        require_all_test_design_refs=True,
    )


def write_task_handoff(
    project_root: Path,
    feature_dir: Path | str,
    *,
    target: str,
) -> dict[str, Any]:
    normalized_target = target.strip().lower()
    if normalized_target not in {"tasks", "implement"}:
        raise TaskAuthoringError("target must be tasks or implement")
    root, feature, task_index, _ = _load_task_package(project_root, feature_dir)
    _validate_test_design_binding(
        root,
        feature,
        task_index,
        bind=False,
        require_all=True,
    )
    transition = task_index.get("transition")
    if (
        task_index.get("status") != "ready"
        or not isinstance(transition, dict)
        or transition.get("status") != "ready"
    ):
        raise TaskAuthoringError(
            "task package must be finalized before creating a handoff"
        )

    task_index_bytes = read_local_state_bytes(
        feature / "task-index.json", root=root
    )
    handoff = {
        "version": 1,
        "status": "ready",
        "target": normalized_target,
        "task_index_ref": "task-index.json",
        "tasks_ref": "tasks.md",
        "task_index_sha256": _sha256(task_index_bytes),
        "source_revision": deepcopy(task_index.get("source_revision")),
        "task_count": len(task_index["tasks"]),
        "test_design_handoff_ref": deepcopy(
            task_index.get("test_design_handoff_ref")
        ),
        "test_design_handoff_sha256": deepcopy(
            task_index.get("test_design_handoff_sha256")
        ),
        "test_design_source_fingerprint": deepcopy(
            task_index.get("test_design_source_fingerprint")
        ),
        "test_design_state_revision": deepcopy(
            task_index.get("test_design_state_revision")
        ),
    }
    raw = _json_bytes(handoff)
    name = f"handoff-to-{normalized_target}.json"
    try:
        transaction = apply_workflow_transaction(
            root,
            kind="tasks.handoff",
            updates={feature / name: raw},
        )
    except WorkflowTransactionError as exc:
        raise TaskAuthoringError(str(exc)) from exc
    transaction_payload = transaction.to_dict()
    handoff_ref = next(
        path
        for path in transaction_payload["changed_paths"]
        if path.endswith(f"/{name}") or path == name
    )
    return {
        "status": "ok",
        **transaction_payload,
        "target": normalized_target,
        "handoff_ref": handoff_ref,
        "handoff_sha256": _sha256(raw),
        "task_count": len(task_index["tasks"]),
    }


__all__ = [
    "TaskAuthoringError",
    "build_task_package",
    "finalize_task_package",
    "remove_task",
    "set_task_root_fields",
    "upsert_task",
    "validate_task_test_design_binding",
    "write_task_handoff",
]
