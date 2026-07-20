"""Deterministic state and closeout gates for post-implementation review."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pathspec

from .agent_api import envelope
from .atomic_io import atomic_write_text, interprocess_lock, read_local_state_bytes
from .workflow_runtime import MissingWorkflowState, show_workflow


REVIEW_STATE_FILENAME = "review-state.json"
IMPLEMENTATION_HANDOFF_FILENAME = "implementation-handoff.json"
REVIEW_SCHEMA_REF = ".specify/templates/review-state-schema.json"
REVIEW_STATE_VERSION = 2
REVIEW_STATUSES = frozenset(
    {
        "gathering",
        "reviewing",
        "repairing",
        "validating",
        "approved",
        "blocked",
        "stale",
    }
)
SCENARIO_RESULTS = frozenset({"pending", "pass", "fail", "blocked", "not_run"})
FINDING_STATUSES = frozenset(
    {"open", "repairing", "fixed", "verified", "accepted_residual_risk"}
)
GAP_CLASSIFICATIONS = frozenset(
    {"implementation_gap", "traceability_gap", "upstream_truth_gap"}
)
EVIDENCE_KINDS = frozenset(
    {
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "invocation",
        "side_effect",
    }
)
REVIEW_RUNTIME_TARGET_MODES = frozenset({"source", "build", "deployment", "device"})
HUMAN_ACCEPTANCE_CHANGE_KINDS = frozenset({"new", "changed"})
HUMAN_ACCEPTANCE_RISKS = frozenset({"low", "medium", "high"})
SNAPSHOT_EXCLUDED_FEATURE_NAMES = frozenset(
    {
        IMPLEMENTATION_HANDOFF_FILENAME,
        REVIEW_STATE_FILENAME,
        "implementation-summary.md",
        "human-acceptance.json",
        ".human-acceptance.lock",
        ".human-acceptance-repair.json",
        ".human-acceptance-repair-backup.json",
        ".human-acceptance-terminal.json",
        "workflow-runtime.json",
        "workflow-state.md",
    }
)
SNAPSHOT_EXCLUDED_FEATURE_PREFIXES = ("review-evidence/", "review-results/")


class ReviewRuntimeError(ValueError):
    """Raised when system review state cannot safely prepare or close."""


def _review_finding_gap_classification_errors(findings: Any) -> list[str]:
    if not isinstance(findings, list):
        return []
    errors: list[str] = []
    for raw in findings:
        if not isinstance(raw, Mapping):
            continue
        finding_id = str(raw.get("id") or "missing-finding")
        classification = str(raw.get("gap_classification") or "").strip()
        if not classification:
            errors.append(f"finding {finding_id} requires gap_classification")
        elif classification not in GAP_CLASSIFICATIONS:
            errors.append(
                f"finding {finding_id} has unsupported gap_classification {classification}"
            )
    return errors


def review_state_path(feature_dir: Path | str) -> Path:
    """Return the leader-owned post-implementation review state path."""

    return Path(feature_dir) / REVIEW_STATE_FILENAME


def implementation_handoff_path(feature_dir: Path | str) -> Path:
    """Return the deterministic implementation-to-review handoff path."""

    return Path(feature_dir) / IMPLEMENTATION_HANDOFF_FILENAME


def _resolve_feature_dir(project_root: Path, feature_dir: Path | str) -> Path:
    root = project_root.resolve(strict=False)
    candidate = Path(feature_dir)
    resolved = (
        candidate.resolve(strict=False)
        if candidate.is_absolute()
        else (root / candidate).resolve(strict=False)
    )
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ReviewRuntimeError("feature_dir must stay inside project_root") from exc
    if not relative.parts:
        raise ReviewRuntimeError(
            "feature_dir must identify a directory below project_root"
        )
    return resolved


def _nearest_project_root(feature_dir: Path, boundary: Path) -> Path:
    """Prefer the nearest project marker over an overly broad caller cwd."""

    resolved_boundary = boundary.resolve(strict=False)
    for candidate in feature_dir.parents:
        try:
            candidate.relative_to(resolved_boundary)
        except ValueError:
            break
        if (candidate / ".specify").is_dir():
            return candidate
    return resolved_boundary


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = read_local_state_bytes(path, root=path.parent)
    except OSError as exc:
        raise ReviewRuntimeError(f"missing or unreadable {label}: {exc}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewRuntimeError(f"invalid {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReviewRuntimeError(f"{label} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(read_local_state_bytes(path, root=path.parent)).hexdigest()


def _git_lines(project_root: Path, *args: str) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def implementation_snapshot_sha256(project_root: Path, feature_dir: Path | str) -> str:
    """Hash the live Git implementation while excluding review-owned evidence."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    root = _nearest_project_root(feature, root)
    try:
        feature_prefix = feature.relative_to(root).as_posix().rstrip("/") + "/"
    except ValueError as exc:  # pragma: no cover - guarded by _resolve_feature_dir
        raise ReviewRuntimeError("feature_dir must stay inside project_root") from exc
    head = _git_lines(root, "rev-parse", "HEAD")
    changed = _git_lines(root, "diff", "--name-only", "HEAD", "--")
    untracked = _git_lines(root, "ls-files", "--others", "--exclude-standard")
    digest = hashlib.sha256()
    if head is not None and changed is not None and untracked is not None:
        digest.update((head[0] if head else "no-head").encode("utf-8"))
        candidates = sorted(set([*changed, *untracked]))
        for relative in candidates:
            normalized = relative.replace("\\", "/")
            if normalized.startswith(feature_prefix):
                suffix = normalized[len(feature_prefix) :]
                if (
                    suffix in SNAPSHOT_EXCLUDED_FEATURE_NAMES
                    or suffix.endswith(".lock")
                    or suffix.startswith(SNAPSHOT_EXCLUDED_FEATURE_PREFIXES)
                ):
                    continue
            digest.update(normalized.encode("utf-8"))
            path = root / Path(normalized)
            if path.is_file():
                digest.update(path.read_bytes())
            else:
                digest.update(b"<deleted>")
        return digest.hexdigest()

    ignored_tree_names = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
    }
    ignore_path = root / ".gitignore"
    try:
        ignore_lines = ignore_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
    except OSError:
        ignore_lines = []
    ignore_spec = (
        pathspec.GitIgnoreSpec.from_lines(ignore_lines) if ignore_lines else None
    )
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ignored_tree_names.intersection(path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if ignore_spec is not None and ignore_spec.match_file(relative):
            continue
        if relative.startswith(feature_prefix):
            suffix = relative[len(feature_prefix) :]
            if (
                suffix in SNAPSHOT_EXCLUDED_FEATURE_NAMES
                or suffix.endswith(".lock")
                or suffix.startswith(SNAPSHOT_EXCLUDED_FEATURE_PREFIXES)
            ):
                continue
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_implementation_handoff(
    project_root: Path,
    feature_dir: Path | str,
    *,
    source_revision: int,
) -> dict[str, Any]:
    """Compile the stable implement-to-review handoff from canonical task-index data."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    workflow_path = feature / "workflow-runtime.json"
    if workflow_path.is_file():
        workflow_state = _read_json_object(workflow_path, label="workflow-runtime.json")
        if (
            workflow_state.get("stage") != "implement"
            or workflow_state.get("status") != "active"
        ):
            raise ReviewRuntimeError(
                "implementation handoff may be generated only by the active "
                "Implement stage; reopen Tasks/Implement instead of rebuilding "
                "or replacing it from Review or Accept"
            )
    task_index_path = feature / "task-index.json"
    if not task_index_path.is_file():
        raise ReviewRuntimeError(
            "task-index.json is required before implementation closeout can freeze human acceptance"
        )
    task_index = _read_json_object(task_index_path, label="task-index.json")
    task_index_version = task_index.get("version")
    if task_index_version != 2 or task_index.get("status") != "ready":
        raise ReviewRuntimeError(
            "task-index.json must use version 2 with status ready before implementation closeout"
        )
    from .hooks.artifact_validation import (
        _validate_tasks_human_acceptance_contract,
    )

    contract_errors = _validate_tasks_human_acceptance_contract(feature)
    if contract_errors:
        raise ReviewRuntimeError(
            "Human Acceptance Universe is invalid: " + "; ".join(contract_errors)
        )
    raw_entrypoints = task_index.get("official_entrypoints")
    raw_scenarios = task_index.get("system_review_scenarios")
    raw_obligations = task_index.get("review_obligations")
    raw_human_obligations = task_index.get("human_acceptance_obligations")
    raw_human_scenarios = task_index.get("human_acceptance_scenarios")
    raw_acceptance_refs = task_index.get("acceptance_refs")
    entrypoints = list(raw_entrypoints) if isinstance(raw_entrypoints, list) else []
    scenarios = list(raw_scenarios) if isinstance(raw_scenarios, list) else []
    obligations = list(raw_obligations) if isinstance(raw_obligations, list) else []
    if not entrypoints or not scenarios:
        derived_entrypoints, derived_scenarios = _derive_review_contract(feature)
        entrypoints = entrypoints or derived_entrypoints
        scenarios = scenarios or derived_scenarios
    if not entrypoints or not scenarios:
        raise ReviewRuntimeError(
            "implementation closeout could not derive official entrypoints and system review scenarios; "
            "record them in task-index.json"
        )
    obligations = obligations or _derive_review_obligations(entrypoints, scenarios)
    (
        human_acceptance_obligations,
        human_acceptance_scenarios,
        human_acceptance_contract_sha256,
    ) = _normalized_human_acceptance_contract(
        raw_human_obligations,
        raw_human_scenarios,
        entrypoints=entrypoints,
        review_scenarios=scenarios,
        review_obligations=obligations,
        allow_legacy_derivation=False,
    )
    acceptance_refs = (
        [str(item).strip() for item in raw_acceptance_refs]
        if isinstance(raw_acceptance_refs, list)
        else []
    )
    task_index_digest = _sha256(task_index_path)
    plan_contract_digest = ""
    plan_contract_path: Path | None = None
    for plan_path, _label in (
        (feature / "plan-contract.json", "plan-contract.json"),
        (feature / "plan" / "plan-contract.json", "plan/plan-contract.json"),
    ):
        if plan_path.is_file():
            plan_contract_path = plan_path
            plan_contract_digest = _sha256(plan_path)
            break
    if plan_contract_path is None:
        raise ReviewRuntimeError(
            "plan-contract.json is required before implementation closeout"
        )
    spec_contract_path = feature / "spec-contract.json"
    if not spec_contract_path.is_file():
        raise ReviewRuntimeError(
            "spec-contract.json is required before implementation closeout"
        )
    spec_contract_digest = _sha256(spec_contract_path)
    acceptance_denominator_sha256 = _canonical_payload_sha256(
        {
            "acceptance_refs": acceptance_refs,
            "spec_contract_sha256": spec_contract_digest,
            "plan_contract_sha256": plan_contract_digest,
            "task_index_sha256": task_index_digest,
        }
    )
    payload: dict[str, Any] = {
        "version": 1,
        "source_revision": source_revision,
        "implementation_fingerprint": implementation_snapshot_sha256(root, feature),
        "fingerprint_algorithm": "git-working-tree-v1",
        "official_entrypoints": entrypoints,
        "system_review_scenarios": scenarios,
        "review_obligations": obligations,
        "acceptance_refs": acceptance_refs,
        "task_index_sha256": task_index_digest,
        "plan_contract_sha256": plan_contract_digest,
        "spec_contract_sha256": spec_contract_digest,
        "acceptance_denominator_sha256": acceptance_denominator_sha256,
        "human_acceptance_obligations": human_acceptance_obligations,
        "human_acceptance_scenarios": human_acceptance_scenarios,
        "human_acceptance_contract_sha256": human_acceptance_contract_sha256,
        "human_acceptance_contract_origin": "task-index-v2",
    }
    _normalized_handoff(payload, expected_revision=source_revision)
    _validate_handoff_against_live_sources(feature, payload)
    output_path = implementation_handoff_path(feature)
    if output_path.is_file():
        previous = _read_json_object(output_path, label=IMPLEMENTATION_HANDOFF_FILENAME)
        if (
            previous.get("source_revision") == source_revision
            and previous.get("human_acceptance_contract_origin") == "task-index-v2"
        ):
            frozen_fields = (
                "official_entrypoints",
                "system_review_scenarios",
                "review_obligations",
                "acceptance_refs",
                "task_index_sha256",
                "plan_contract_sha256",
                "spec_contract_sha256",
                "acceptance_denominator_sha256",
                "human_acceptance_obligations",
                "human_acceptance_scenarios",
                "human_acceptance_contract_sha256",
                "human_acceptance_contract_origin",
            )
            previous_scope = {key: deepcopy(previous.get(key)) for key in frozen_fields}
            next_scope = {key: deepcopy(payload.get(key)) for key in frozen_fields}
            if previous_scope != next_scope:
                raise ReviewRuntimeError(
                    "implementation-handoff.json scope is already frozen for this "
                    "workflow revision; reopen the owning Tasks/Implement stages "
                    "instead of resigning a changed acceptance or Review universe"
                )
    atomic_write_text(
        output_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return {
        "status": "ok",
        "path": str(output_path),
        "source_revision": source_revision,
        "implementation_fingerprint": payload["implementation_fingerprint"],
        "official_entrypoints": len(entrypoints),
        "system_review_scenarios": len(scenarios),
        "review_obligations": len(obligations),
        "human_acceptance_obligations": len(human_acceptance_obligations),
        "human_acceptance_scenarios": len(human_acceptance_scenarios),
        "human_acceptance_contract_sha256": human_acceptance_contract_sha256,
        "acceptance_denominator_sha256": acceptance_denominator_sha256,
    }


def _validate_handoff_against_live_sources(
    feature: Path,
    handoff: Mapping[str, Any],
) -> None:
    """Reject a self-consistent handoff that drifts from live Spec/Plan/Tasks."""

    origin = str(handoff.get("human_acceptance_contract_origin") or "legacy-derived")
    task_index_path = feature / "task-index.json"
    if origin == "legacy-derived" and not task_index_path.is_file():
        return
    if origin != "task-index-v2":
        raise ReviewRuntimeError(
            "current task-index workflow requires human_acceptance_contract_origin=task-index-v2"
        )
    if not task_index_path.is_file():
        raise ReviewRuntimeError(
            "task-index-v2 handoff requires the live task-index.json source"
        )

    from .hooks.artifact_validation import (
        _validate_tasks_human_acceptance_contract,
    )

    contract_errors = _validate_tasks_human_acceptance_contract(feature)
    if contract_errors:
        raise ReviewRuntimeError(
            "live Spec/Plan/Tasks acceptance contract is invalid: "
            + "; ".join(contract_errors)
        )
    task_index = _read_json_object(task_index_path, label="task-index.json")
    if task_index.get("version") != 2 or task_index.get("status") != "ready":
        raise ReviewRuntimeError(
            "live task-index.json must use version 2 with status ready"
        )

    plan_path = next(
        (
            path
            for path in (
                feature / "plan-contract.json",
                feature / "plan" / "plan-contract.json",
            )
            if path.is_file()
        ),
        None,
    )
    spec_path = feature / "spec-contract.json"
    if plan_path is None or not spec_path.is_file():
        raise ReviewRuntimeError(
            "live spec-contract.json and plan-contract.json are required"
        )

    entrypoints = task_index.get("official_entrypoints")
    scenarios = task_index.get("system_review_scenarios")
    obligations = task_index.get("review_obligations")
    if not isinstance(entrypoints, list) or not entrypoints:
        raise ReviewRuntimeError(
            "live task-index.json official_entrypoints are required"
        )
    if not isinstance(scenarios, list) or not scenarios:
        raise ReviewRuntimeError(
            "live task-index.json system_review_scenarios are required"
        )
    expected_obligations = (
        list(obligations)
        if isinstance(obligations, list) and obligations
        else _derive_review_obligations(list(entrypoints), list(scenarios))
    )
    (
        expected_human_obligations,
        expected_human_scenarios,
        expected_human_sha256,
    ) = _normalized_human_acceptance_contract(
        task_index.get("human_acceptance_obligations"),
        task_index.get("human_acceptance_scenarios"),
        entrypoints=list(entrypoints),
        review_scenarios=list(scenarios),
        review_obligations=expected_obligations,
        allow_legacy_derivation=False,
    )
    acceptance_refs = [
        str(item).strip() for item in (task_index.get("acceptance_refs") or [])
    ]
    task_sha256 = _sha256(task_index_path)
    plan_sha256 = _sha256(plan_path)
    spec_sha256 = _sha256(spec_path)
    denominator_sha256 = _canonical_payload_sha256(
        {
            "acceptance_refs": acceptance_refs,
            "spec_contract_sha256": spec_sha256,
            "plan_contract_sha256": plan_sha256,
            "task_index_sha256": task_sha256,
        }
    )
    expected = {
        "official_entrypoints": list(entrypoints),
        "system_review_scenarios": list(scenarios),
        "review_obligations": expected_obligations,
        "acceptance_refs": acceptance_refs,
        "task_index_sha256": task_sha256,
        "plan_contract_sha256": plan_sha256,
        "spec_contract_sha256": spec_sha256,
        "acceptance_denominator_sha256": denominator_sha256,
        "human_acceptance_obligations": expected_human_obligations,
        "human_acceptance_scenarios": expected_human_scenarios,
        "human_acceptance_contract_sha256": expected_human_sha256,
    }
    drifted = [key for key, value in expected.items() if handoff.get(key) != value]
    if drifted:
        raise ReviewRuntimeError(
            "implementation handoff drifted from live Spec/Plan/Tasks: "
            + ", ".join(drifted)
        )


def _stable_id_fragment(value: object) -> str:
    fragment = "".join(
        char if char.isalnum() else "-" for char in str(value or "").upper()
    )
    return "-".join(part for part in fragment.split("-") if part) or "UNKNOWN"


def _derive_review_obligations(
    entrypoints: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive a conservative compatibility baseline when Tasks predate obligations."""

    obligations: list[dict[str, Any]] = []
    scenario_ids_by_entrypoint: dict[str, list[str]] = {}
    for scenario in scenarios:
        scenario_id = str(scenario.get("id") or "").strip()
        entrypoint_id = str(scenario.get("entrypoint_id") or "").strip()
        if scenario_id and entrypoint_id:
            scenario_ids_by_entrypoint.setdefault(entrypoint_id, []).append(scenario_id)
        if scenario_id:
            obligations.append(
                {
                    "id": f"RO-SCENARIO-{_stable_id_fragment(scenario_id)}",
                    "kind": "scenario",
                    "source_ref": f"implementation-handoff:system_review_scenarios/{scenario_id}",
                    "surface": str(scenario.get("title") or scenario_id),
                    "required": bool(scenario.get("required", True)),
                    "scenario_ids": [scenario_id],
                }
            )
    for entrypoint in entrypoints:
        entrypoint_id = str(entrypoint.get("id") or "").strip()
        scenario_ids = scenario_ids_by_entrypoint.get(entrypoint_id, [])
        if entrypoint_id and scenario_ids:
            obligations.append(
                {
                    "id": f"RO-ENTRYPOINT-{_stable_id_fragment(entrypoint_id)}",
                    "kind": "entrypoint",
                    "source_ref": f"implementation-handoff:official_entrypoints/{entrypoint_id}",
                    "surface": f"{entrypoint_id} startup and readiness",
                    "required": True,
                    "scenario_ids": scenario_ids,
                }
            )
    return obligations


def _canonical_payload_sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _acceptance_finding_sha256(value: Mapping[str, Any]) -> str:
    return _canonical_payload_sha256(
        {
            key: deepcopy(value.get(key))
            for key in (
                "id",
                "scenario_id",
                "step_id",
                "classification",
                "expected",
                "observed",
                "evidence",
                "route",
            )
        }
    )


def _review_runtime_target_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value.get(key))
        for key in (
            "id",
            "mode",
            "status",
            "entrypoint_id",
            "environment_ref",
            "instance_ref",
            "configuration_ref",
            "reviewed_snapshot_sha256",
            "artifact_ref",
            "artifact_sha256",
            "deployment_id",
            "observed_version",
            "test_data_refs",
            "ready_evidence_refs",
            "review_scenario_ids",
            "identity_evidence_ref",
            "identity_evidence_sha256",
        )
    }


def _review_runtime_identity_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": 1,
        "status": "ready",
        "target": {
            key: deepcopy(value.get(key))
            for key in (
                "id",
                "mode",
                "entrypoint_id",
                "environment_ref",
                "instance_ref",
                "configuration_ref",
                "reviewed_snapshot_sha256",
                "artifact_ref",
                "artifact_sha256",
                "deployment_id",
                "observed_version",
                "review_scenario_ids",
                "ready_evidence_refs",
            )
        },
    }


def _review_runtime_targets_sha256(values: list[dict[str, Any]]) -> str:
    return _canonical_payload_sha256({"reviewed_runtime_targets": values})


def _required_text_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ReviewRuntimeError(f"{label} must be a non-empty array")
    normalized = [_required_text(item, f"{label} item") for item in value]
    if len(normalized) != len(set(normalized)):
        raise ReviewRuntimeError(f"{label} must not contain duplicates")
    return normalized


def _derive_human_acceptance_contract(
    review_scenarios: list[dict[str, Any]],
    review_obligations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Conservatively adapt legacy Review scope into human E2E obligations."""

    review_scenario_by_id = {
        str(item.get("id") or ""): item
        for item in review_scenarios
        if str(item.get("id") or "").strip()
    }
    acceptance_id_by_review_id = {
        scenario_id: f"HA-COMPAT-{_stable_id_fragment(scenario_id)}"
        for scenario_id in review_scenario_by_id
    }
    acceptance_obligations: list[dict[str, Any]] = []
    acceptance_obligation_ids_by_scenario: dict[str, list[str]] = {}
    for review_obligation in review_obligations:
        review_obligation_id = str(review_obligation.get("id") or "").strip()
        if not review_obligation_id:
            continue
        acceptance_obligation_id = (
            f"HAO-COMPAT-{_stable_id_fragment(review_obligation_id)}"
        )
        scenario_ids = [
            acceptance_id_by_review_id[str(review_scenario_id)]
            for review_scenario_id in review_obligation.get("scenario_ids") or []
            if str(review_scenario_id) in acceptance_id_by_review_id
        ]
        if not scenario_ids:
            continue
        acceptance_obligations.append(
            {
                "id": acceptance_obligation_id,
                "source_ref": str(
                    review_obligation.get("source_ref")
                    or f"implementation-handoff:review_obligations/{review_obligation_id}"
                ),
                "change_kind": "changed",
                "user_outcome": str(
                    review_obligation.get("surface") or review_obligation_id
                ),
                "required": bool(review_obligation.get("required", True)),
                "scenario_ids": scenario_ids,
            }
        )
        for scenario_id in scenario_ids:
            acceptance_obligation_ids_by_scenario.setdefault(scenario_id, []).append(
                acceptance_obligation_id
            )

    acceptance_scenarios: list[dict[str, Any]] = []
    for review_scenario_id, review_scenario in review_scenario_by_id.items():
        scenario_id = acceptance_id_by_review_id[review_scenario_id]
        obligation_ids = acceptance_obligation_ids_by_scenario.get(scenario_id, [])
        if not obligation_ids:
            continue
        actions = [str(item) for item in review_scenario.get("actions") or []]
        expected_results = [
            str(item) for item in review_scenario.get("expected_results") or []
        ]
        steps: list[dict[str, Any]] = []
        for index, action in enumerate(actions):
            expected_result = expected_results[min(index, len(expected_results) - 1)]
            steps.append(
                {
                    "id": f"{scenario_id}-S{index + 1:02d}",
                    "action": action,
                    "expected_result": expected_result,
                    "evidence_requirement": (
                        "Human reports the observable result: " + expected_result
                    ),
                    "risk": "medium",
                }
            )
        preconditions = [
            str(item) for item in review_scenario.get("preconditions") or []
        ]
        acceptance_scenarios.append(
            {
                "id": scenario_id,
                "title": str(review_scenario.get("title") or review_scenario_id),
                "user_value": " ".join(expected_results),
                "actor": "human user",
                "required": bool(review_scenario.get("required", True)),
                "obligation_ids": obligation_ids,
                "entrypoint_id": str(review_scenario.get("entrypoint_id") or ""),
                "review_scenario_ids": [review_scenario_id],
                "start_state": (
                    " ".join(preconditions)
                    if preconditions
                    else "The reviewed product is ready at its official entrypoint."
                ),
                "steps": steps,
            }
        )
    if not acceptance_obligations or not acceptance_scenarios:
        raise ReviewRuntimeError(
            "implementation closeout could not derive a non-empty human acceptance universe"
        )
    return acceptance_obligations, acceptance_scenarios


def _normalized_human_acceptance_contract(
    raw_obligations: object,
    raw_scenarios: object,
    *,
    entrypoints: list[dict[str, Any]],
    review_scenarios: list[dict[str, Any]],
    review_obligations: list[dict[str, Any]],
    recorded_sha256: object = None,
    allow_legacy_derivation: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    obligations_missing = raw_obligations is None or raw_obligations == []
    scenarios_missing = raw_scenarios is None or raw_scenarios == []
    if obligations_missing != scenarios_missing:
        raise ReviewRuntimeError(
            "human_acceptance_obligations and human_acceptance_scenarios must be provided together"
        )
    if obligations_missing:
        if not allow_legacy_derivation:
            raise ReviewRuntimeError(
                "modern task-index version 2 requires a non-empty Human Acceptance Universe"
            )
        obligation_values, scenario_values = _derive_human_acceptance_contract(
            review_scenarios, review_obligations
        )
    else:
        if not isinstance(raw_obligations, list):
            raise ReviewRuntimeError("human_acceptance_obligations must be an array")
        if not isinstance(raw_scenarios, list):
            raise ReviewRuntimeError("human_acceptance_scenarios must be an array")
        obligation_values = list(raw_obligations)
        scenario_values = list(raw_scenarios)

    entrypoint_ids = {str(item.get("id") or "") for item in entrypoints}
    review_scenario_ids = {str(item.get("id") or "") for item in review_scenarios}
    obligations: list[dict[str, Any]] = []
    obligation_ids: set[str] = set()
    for index, raw in enumerate(obligation_values):
        prefix = f"human_acceptance_obligations[{index}]"
        if not isinstance(raw, Mapping):
            raise ReviewRuntimeError(f"{prefix} must be an object")
        obligation_id = _required_text(raw.get("id"), f"{prefix}.id")
        if not obligation_id.startswith("HAO-"):
            raise ReviewRuntimeError(f"{prefix}.id must start with HAO-")
        if obligation_id in obligation_ids:
            raise ReviewRuntimeError(
                f"duplicate human acceptance obligation id: {obligation_id}"
            )
        obligation_ids.add(obligation_id)
        change_kind = _required_text(raw.get("change_kind"), f"{prefix}.change_kind")
        if change_kind not in HUMAN_ACCEPTANCE_CHANGE_KINDS:
            raise ReviewRuntimeError(f"{prefix}.change_kind must be new or changed")
        required = raw.get("required")
        if not isinstance(required, bool):
            raise ReviewRuntimeError(f"{prefix}.required must be a boolean")
        obligations.append(
            {
                "id": obligation_id,
                "source_ref": _required_text(
                    raw.get("source_ref"), f"{prefix}.source_ref"
                ),
                "change_kind": change_kind,
                "user_outcome": _required_text(
                    raw.get("user_outcome"), f"{prefix}.user_outcome"
                ),
                "required": required,
                "scenario_ids": _required_text_list(
                    raw.get("scenario_ids"), f"{prefix}.scenario_ids"
                ),
            }
        )

    scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    step_ids: set[str] = set()
    for index, raw in enumerate(scenario_values):
        prefix = f"human_acceptance_scenarios[{index}]"
        if not isinstance(raw, Mapping):
            raise ReviewRuntimeError(f"{prefix} must be an object")
        scenario_id = _required_text(raw.get("id"), f"{prefix}.id")
        if not scenario_id.startswith("HA-"):
            raise ReviewRuntimeError(f"{prefix}.id must start with HA-")
        if scenario_id in scenario_ids:
            raise ReviewRuntimeError(
                f"duplicate human acceptance scenario id: {scenario_id}"
            )
        scenario_ids.add(scenario_id)
        required = raw.get("required")
        if not isinstance(required, bool):
            raise ReviewRuntimeError(f"{prefix}.required must be a boolean")
        entrypoint_id = _required_text(
            raw.get("entrypoint_id"), f"{prefix}.entrypoint_id"
        )
        if entrypoint_id not in entrypoint_ids:
            raise ReviewRuntimeError(
                f"human acceptance scenario {scenario_id} references unknown entrypoint {entrypoint_id}"
            )
        scenario_obligation_ids = _required_text_list(
            raw.get("obligation_ids"), f"{prefix}.obligation_ids"
        )
        unknown_obligations = set(scenario_obligation_ids) - obligation_ids
        if unknown_obligations:
            raise ReviewRuntimeError(
                f"human acceptance scenario {scenario_id} references unknown obligations: "
                + ", ".join(sorted(unknown_obligations))
            )
        linked_review_scenario_ids = _required_text_list(
            raw.get("review_scenario_ids"), f"{prefix}.review_scenario_ids"
        )
        unknown_review_scenarios = set(linked_review_scenario_ids) - review_scenario_ids
        if unknown_review_scenarios:
            raise ReviewRuntimeError(
                f"human acceptance scenario {scenario_id} references unknown Review scenarios: "
                + ", ".join(sorted(unknown_review_scenarios))
            )
        raw_steps = raw.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ReviewRuntimeError(f"{prefix}.steps must be a non-empty array")
        steps: list[dict[str, Any]] = []
        for step_index, raw_step in enumerate(raw_steps):
            step_prefix = f"{prefix}.steps[{step_index}]"
            if not isinstance(raw_step, Mapping):
                raise ReviewRuntimeError(f"{step_prefix} must be an object")
            step_id = _required_text(raw_step.get("id"), f"{step_prefix}.id")
            if not step_id.startswith("HA-"):
                raise ReviewRuntimeError(f"{step_prefix}.id must start with HA-")
            if step_id in step_ids:
                raise ReviewRuntimeError(
                    f"duplicate human acceptance step id: {step_id}"
                )
            step_ids.add(step_id)
            risk = _required_text(raw_step.get("risk"), f"{step_prefix}.risk")
            if risk not in HUMAN_ACCEPTANCE_RISKS:
                raise ReviewRuntimeError(
                    f"{step_prefix}.risk must be low, medium, or high"
                )
            steps.append(
                {
                    "id": step_id,
                    "action": _required_text(
                        raw_step.get("action"), f"{step_prefix}.action"
                    ),
                    "expected_result": _required_text(
                        raw_step.get("expected_result"),
                        f"{step_prefix}.expected_result",
                    ),
                    "evidence_requirement": _required_text(
                        raw_step.get("evidence_requirement"),
                        f"{step_prefix}.evidence_requirement",
                    ),
                    "risk": risk,
                }
            )
        scenarios.append(
            {
                "id": scenario_id,
                "title": _required_text(raw.get("title"), f"{prefix}.title"),
                "user_value": _required_text(
                    raw.get("user_value"), f"{prefix}.user_value"
                ),
                "actor": _required_text(raw.get("actor"), f"{prefix}.actor"),
                "required": required,
                "obligation_ids": scenario_obligation_ids,
                "entrypoint_id": entrypoint_id,
                "review_scenario_ids": linked_review_scenario_ids,
                "start_state": _required_text(
                    raw.get("start_state"), f"{prefix}.start_state"
                ),
                "steps": steps,
            }
        )

    scenario_by_id = {item["id"]: item for item in scenarios}
    review_scenario_by_id = {
        str(item.get("id") or ""): item for item in review_scenarios
    }
    for obligation in obligations:
        unknown_scenarios = set(obligation["scenario_ids"]) - scenario_ids
        if unknown_scenarios:
            raise ReviewRuntimeError(
                f"human acceptance obligation {obligation['id']} references unknown scenarios: "
                + ", ".join(sorted(unknown_scenarios))
            )
        for scenario_id in obligation["scenario_ids"]:
            scenario = scenario_by_id[scenario_id]
            if obligation["id"] not in scenario["obligation_ids"]:
                raise ReviewRuntimeError(
                    f"human acceptance obligation {obligation['id']} and scenario {scenario_id} must reference each other"
                )
        if obligation["required"] and not any(
            scenario_by_id[scenario_id]["required"]
            for scenario_id in obligation["scenario_ids"]
        ):
            raise ReviewRuntimeError(
                f"required human acceptance obligation {obligation['id']} must be covered by a required scenario"
            )
    for scenario in scenarios:
        for obligation_id in scenario["obligation_ids"]:
            obligation = next(
                item for item in obligations if item["id"] == obligation_id
            )
            if scenario["id"] not in obligation["scenario_ids"]:
                raise ReviewRuntimeError(
                    f"human acceptance scenario {scenario['id']} and obligation {obligation_id} must reference each other"
                )
        linked_review_scenarios = [
            review_scenario_by_id[review_id]
            for review_id in scenario["review_scenario_ids"]
        ]
        if scenario["required"] and not any(
            item.get("required") is True for item in linked_review_scenarios
        ):
            raise ReviewRuntimeError(
                f"required human acceptance scenario {scenario['id']} requires at least one required Review scenario"
            )
        mismatched_entrypoints = sorted(
            str(item.get("id") or "")
            for item in linked_review_scenarios
            if str(item.get("entrypoint_id") or "") != scenario["entrypoint_id"]
        )
        if mismatched_entrypoints:
            raise ReviewRuntimeError(
                f"human acceptance scenario {scenario['id']} links Review scenarios for a different entrypoint: "
                + ", ".join(mismatched_entrypoints)
            )

    contract_sha256 = _canonical_payload_sha256(
        {
            "human_acceptance_obligations": obligations,
            "human_acceptance_scenarios": scenarios,
        }
    )
    if recorded_sha256 not in {None, ""}:
        normalized_recorded = _required_text(
            recorded_sha256, "human_acceptance_contract_sha256"
        ).lower()
        if normalized_recorded != contract_sha256:
            raise ReviewRuntimeError(
                "human_acceptance_contract_sha256 does not match the canonical human acceptance contract"
            )
    return obligations, scenarios, contract_sha256


def _derive_review_contract(
    feature_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive a compatibility review matrix from successful worker evidence."""

    result_dir = feature_dir / "worker-results"
    if not result_dir.is_dir():
        return [], []
    entrypoints: list[dict[str, Any]] = []
    scenarios: list[dict[str, Any]] = []
    known_entrypoints: dict[str, str] = {}
    for result_path in sorted(result_dir.glob("*.json")):
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(result, Mapping) or str(result.get("status") or "") not in {
            "success",
            "completed",
            "passed",
        }:
            continue
        task_id = str(result.get("task_id") or result_path.stem).upper()
        consumer_evidence = result.get("consumer_evidence")
        evidence_items = (
            consumer_evidence if isinstance(consumer_evidence, list) else []
        )
        real_entrypoint = next(
            (
                item
                for item in evidence_items
                if isinstance(item, Mapping)
                and str(item.get("kind") or "").replace("-", "_")
                in {"real_entrypoint", "real_entrypoint_evidence"}
                and str(item.get("entrypoint") or "").strip()
            ),
            None,
        )
        if real_entrypoint is not None:
            command = str(real_entrypoint.get("entrypoint") or "").strip()
            ready_signal = str(
                real_entrypoint.get("validation")
                or "The documented runtime surface is ready without blocking diagnostics."
            )
            scenario_kind = "interaction"
            expected_result = (
                "The implemented user-observable outcome is reachable and produces its "
                "documented result."
            )
        else:
            validation_results = result.get("validation_results")
            validations = (
                validation_results if isinstance(validation_results, list) else []
            )
            passing_validation = next(
                (
                    item
                    for item in validations
                    if isinstance(item, Mapping)
                    and str(item.get("status") or "").lower()
                    in {"pass", "passed", "success"}
                    and str(item.get("command") or "").strip()
                ),
                None,
            )
            if passing_validation is None:
                continue
            command = str(passing_validation.get("command") or "").strip()
            ready_signal = "The verification entrypoint exits successfully."
            scenario_kind = "regression"
            expected_result = (
                "The recorded verification entrypoint passes from a clean invocation."
            )
        entrypoint_id = known_entrypoints.get(command)
        if entrypoint_id is None:
            entrypoint_id = f"entrypoint-{len(entrypoints) + 1:02d}"
            known_entrypoints[command] = entrypoint_id
            entrypoints.append(
                {
                    "id": entrypoint_id,
                    "command": command,
                    "ready_signal": ready_signal,
                }
            )
        scenarios.append(
            {
                "id": f"SR-{task_id}",
                "kind": scenario_kind,
                "title": str(
                    result.get("summary")
                    or f"Review {task_id} from the real entrypoint"
                ),
                "required": True,
                "entrypoint_id": entrypoint_id,
                "preconditions": ["The official entrypoint is ready."],
                "actions": [f"Exercise {task_id} through {command}."],
                "expected_results": [expected_result],
                "required_evidence": ["invocation", "runtime_diagnostics"],
            }
        )
    return entrypoints, scenarios


def _required_text(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ReviewRuntimeError(f"{label} is required")
    return normalized


def _validate_workflow_owner(
    feature_dir: Path, expected_revision: int
) -> dict[str, Any]:
    workflow = show_workflow(feature_dir)["data"]
    if workflow.get("stage") != "review" or workflow.get("status") != "active":
        raise ReviewRuntimeError(
            "system review requires workflow stage review with active status"
        )
    if workflow.get("revision") != expected_revision:
        raise ReviewRuntimeError(
            "system review workflow revision is stale; refresh workflow show before retrying"
        )
    return workflow


def _normalized_handoff(
    handoff: Mapping[str, Any], *, expected_revision: int
) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    str,
]:
    if handoff.get("version") != 1:
        raise ReviewRuntimeError("implementation-handoff.json version must equal 1")
    if handoff.get("source_revision") != expected_revision:
        raise ReviewRuntimeError(
            "implementation handoff source_revision does not match the active review revision"
        )
    contract_origin = str(
        handoff.get("human_acceptance_contract_origin") or "legacy-derived"
    )
    if contract_origin not in {"task-index-v2", "legacy-derived"}:
        raise ReviewRuntimeError(
            "human_acceptance_contract_origin must be task-index-v2 or legacy-derived"
        )
    fingerprint = _required_text(
        handoff.get("implementation_fingerprint"),
        "implementation_fingerprint",
    )
    if len(fingerprint) != 64 or any(
        char not in "0123456789abcdef" for char in fingerprint.lower()
    ):
        raise ReviewRuntimeError("implementation_fingerprint must be a sha256 digest")

    raw_entrypoints = handoff.get("official_entrypoints")
    if not isinstance(raw_entrypoints, list) or not raw_entrypoints:
        raise ReviewRuntimeError("at least one official_entrypoint is required")
    entrypoints: list[dict[str, Any]] = []
    entrypoint_ids: set[str] = set()
    for index, raw in enumerate(raw_entrypoints):
        if not isinstance(raw, Mapping):
            raise ReviewRuntimeError(f"official_entrypoints[{index}] must be an object")
        item = dict(raw)
        entrypoint_id = _required_text(
            item.get("id"), f"official_entrypoints[{index}].id"
        )
        _required_text(item.get("command"), f"official_entrypoints[{index}].command")
        _required_text(
            item.get("ready_signal"), f"official_entrypoints[{index}].ready_signal"
        )
        if entrypoint_id in entrypoint_ids:
            raise ReviewRuntimeError(
                f"duplicate official entrypoint id: {entrypoint_id}"
            )
        entrypoint_ids.add(entrypoint_id)
        entrypoints.append(item)

    raw_scenarios = handoff.get("system_review_scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ReviewRuntimeError("at least one system_review_scenario is required")
    scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for index, raw in enumerate(raw_scenarios):
        if not isinstance(raw, Mapping):
            raise ReviewRuntimeError(
                f"system_review_scenarios[{index}] must be an object"
            )
        item = dict(raw)
        scenario_id = _required_text(
            item.get("id"), f"system_review_scenarios[{index}].id"
        )
        _required_text(item.get("kind"), f"system_review_scenarios[{index}].kind")
        _required_text(item.get("title"), f"system_review_scenarios[{index}].title")
        entrypoint_id = _required_text(
            item.get("entrypoint_id"),
            f"system_review_scenarios[{index}].entrypoint_id",
        )
        if entrypoint_id not in entrypoint_ids:
            raise ReviewRuntimeError(
                f"scenario {scenario_id} references unknown entrypoint {entrypoint_id}"
            )
        if scenario_id in scenario_ids:
            raise ReviewRuntimeError(
                f"duplicate system review scenario id: {scenario_id}"
            )
        scenario_ids.add(scenario_id)
        for field in ("actions", "expected_results", "required_evidence"):
            values = item.get(field)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and value.strip() for value in values)
            ):
                raise ReviewRuntimeError(
                    f"scenario {scenario_id} requires non-empty {field}"
                )
        unsupported = set(item["required_evidence"]) - EVIDENCE_KINDS
        if unsupported:
            raise ReviewRuntimeError(
                f"scenario {scenario_id} has unsupported evidence kinds: {', '.join(sorted(unsupported))}"
            )
        item["required"] = bool(item.get("required", True))
        item["result"] = "pending"
        item["evidence"] = []
        scenarios.append(item)

    raw_obligations = handoff.get("review_obligations")
    obligation_values = (
        list(raw_obligations)
        if isinstance(raw_obligations, list) and raw_obligations
        else _derive_review_obligations(entrypoints, scenarios)
    )
    obligations: list[dict[str, Any]] = []
    obligation_ids: set[str] = set()
    for index, raw in enumerate(obligation_values):
        if not isinstance(raw, Mapping):
            raise ReviewRuntimeError(f"review_obligations[{index}] must be an object")
        item = dict(raw)
        obligation_id = _required_text(
            item.get("id"), f"review_obligations[{index}].id"
        )
        _required_text(item.get("kind"), f"review_obligations[{index}].kind")
        _required_text(
            item.get("source_ref"), f"review_obligations[{index}].source_ref"
        )
        _required_text(item.get("surface"), f"review_obligations[{index}].surface")
        if obligation_id in obligation_ids:
            raise ReviewRuntimeError(f"duplicate review obligation id: {obligation_id}")
        obligation_ids.add(obligation_id)
        referenced_scenarios = item.get("scenario_ids")
        if not isinstance(referenced_scenarios, list) or not referenced_scenarios:
            raise ReviewRuntimeError(
                f"review obligation {obligation_id} requires non-empty scenario_ids"
            )
        unknown_scenarios = {
            str(value)
            for value in referenced_scenarios
            if str(value) not in scenario_ids
        }
        if unknown_scenarios:
            raise ReviewRuntimeError(
                f"review obligation {obligation_id} references unknown scenarios: "
                + ", ".join(sorted(unknown_scenarios))
            )
        item["required"] = bool(item.get("required", True))
        item["scenario_ids"] = [str(value) for value in referenced_scenarios]
        item["review_assignment_ids"] = []
        item["status"] = "pending"
        obligations.append(item)

    obligations_by_scenario: dict[str, list[str]] = {}
    for obligation in obligations:
        for scenario_id in obligation["scenario_ids"]:
            obligations_by_scenario.setdefault(scenario_id, []).append(obligation["id"])
    for scenario in scenarios:
        scenario["obligation_ids"] = obligations_by_scenario.get(scenario["id"], [])
    (
        human_acceptance_obligations,
        human_acceptance_scenarios,
        human_acceptance_contract_sha256,
    ) = _normalized_human_acceptance_contract(
        handoff.get("human_acceptance_obligations"),
        handoff.get("human_acceptance_scenarios"),
        entrypoints=entrypoints,
        review_scenarios=scenarios,
        review_obligations=obligations,
        recorded_sha256=handoff.get("human_acceptance_contract_sha256"),
        allow_legacy_derivation=contract_origin == "legacy-derived",
    )
    if not str(handoff.get("human_acceptance_contract_sha256") or "").strip():
        raise ReviewRuntimeError("human_acceptance_contract_sha256 is required")
    if contract_origin == "task-index-v2":
        acceptance_refs = _required_text_list(
            handoff.get("acceptance_refs"), "acceptance_refs"
        )
        task_index_sha256 = _required_text(
            handoff.get("task_index_sha256"), "task_index_sha256"
        )
        plan_contract_sha256 = _required_text(
            handoff.get("plan_contract_sha256"), "plan_contract_sha256"
        )
        spec_contract_sha256 = _required_text(
            handoff.get("spec_contract_sha256"), "spec_contract_sha256"
        )
        for label, digest in (
            ("task_index_sha256", task_index_sha256),
            ("plan_contract_sha256", plan_contract_sha256),
            ("spec_contract_sha256", spec_contract_sha256),
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ReviewRuntimeError(f"{label} must be a sha256 digest")
        denominator_sha256 = _required_text(
            handoff.get("acceptance_denominator_sha256"),
            "acceptance_denominator_sha256",
        )
        expected_denominator_sha256 = _canonical_payload_sha256(
            {
                "acceptance_refs": acceptance_refs,
                "spec_contract_sha256": spec_contract_sha256,
                "plan_contract_sha256": plan_contract_sha256,
                "task_index_sha256": task_index_sha256,
            }
        )
        if denominator_sha256 != expected_denominator_sha256:
            raise ReviewRuntimeError(
                "acceptance_denominator_sha256 does not match the frozen Plan/Tasks denominator"
            )
        obligation_source_refs = {
            str(item.get("source_ref") or "") for item in human_acceptance_obligations
        }
        if obligation_source_refs != set(acceptance_refs):
            raise ReviewRuntimeError(
                "human acceptance obligations must exactly cover frozen acceptance_refs"
            )
    return (
        fingerprint,
        entrypoints,
        scenarios,
        obligations,
        human_acceptance_obligations,
        human_acceptance_scenarios,
        human_acceptance_contract_sha256,
    )


def _review_cycle_id(
    *,
    workflow_revision: int,
    handoff_sha256: str,
    review_cycle: int,
    previous_review_state_sha256: str,
    acceptance_finding_id: str,
    acceptance_finding_sha256: str = "",
) -> str:
    return _canonical_payload_sha256(
        {
            "acceptance_finding_id": acceptance_finding_id,
            "acceptance_finding_sha256": acceptance_finding_sha256,
            "handoff_sha256": handoff_sha256,
            "previous_review_state_sha256": previous_review_state_sha256,
            "review_cycle": review_cycle,
            "workflow_revision": workflow_revision,
        }
    )


def _acceptance_repair_context(
    feature: Path,
    *,
    workflow: Mapping[str, Any],
    previous_review_state: Mapping[str, Any],
    previous_review_state_sha256: str,
) -> dict[str, Any]:
    last_reopen = workflow.get("last_reopen")
    if not isinstance(last_reopen, Mapping) or (
        last_reopen.get("source_stage") != "accept"
        or last_reopen.get("target_stage") != "review"
    ):
        raise ReviewRuntimeError("workflow is not an acceptance repair cycle")
    finding_id = _required_text(
        last_reopen.get("finding_id"), "acceptance repair finding_id"
    )
    acceptance_path = feature / "human-acceptance.json"
    acceptance = _read_json_object(acceptance_path, label="human-acceptance.json")
    repair_resume = acceptance.get("repair_resume")
    if not isinstance(repair_resume, Mapping):
        raise ReviewRuntimeError(
            "acceptance repair cycle requires human-acceptance.json repair_resume"
        )
    if repair_resume.get("finding_id") != finding_id:
        raise ReviewRuntimeError(
            "acceptance repair cycle finding does not match repair_resume"
        )
    if (
        repair_resume.get("previous_review_state_sha256")
        != previous_review_state_sha256
    ):
        raise ReviewRuntimeError(
            "previous approved Review changed after acceptance repair routing"
        )
    findings = acceptance.get("findings")
    finding = next(
        (
            item
            for item in (findings if isinstance(findings, list) else [])
            if isinstance(item, Mapping) and item.get("id") == finding_id
        ),
        None,
    )
    if not isinstance(finding, Mapping) or finding.get("status") != "open":
        raise ReviewRuntimeError(
            "acceptance repair cycle requires the routed open human finding"
        )
    finding_sha256 = _acceptance_finding_sha256(finding)
    if repair_resume.get("finding_contract_sha256") != finding_sha256:
        raise ReviewRuntimeError("acceptance repair finding changed after routing")
    scenario_id = _required_text(
        finding.get("scenario_id"), "acceptance finding scenario_id"
    )
    human_scenarios = previous_review_state.get("human_acceptance_scenarios")
    human_scenario = next(
        (
            item
            for item in (human_scenarios if isinstance(human_scenarios, list) else [])
            if isinstance(item, Mapping) and item.get("id") == scenario_id
        ),
        None,
    )
    if not isinstance(human_scenario, Mapping):
        raise ReviewRuntimeError(
            "acceptance repair scenario is absent from the frozen Human Acceptance Universe"
        )
    review_scenario_ids = human_scenario.get("review_scenario_ids")
    if not isinstance(review_scenario_ids, list) or not review_scenario_ids:
        raise ReviewRuntimeError(
            "acceptance repair scenario has no linked system Review scenario"
        )
    review_scenario_id = str(review_scenario_ids[0])
    review_scenarios = previous_review_state.get("scenarios")
    review_scenario = next(
        (
            item
            for item in (review_scenarios if isinstance(review_scenarios, list) else [])
            if isinstance(item, Mapping) and item.get("id") == review_scenario_id
        ),
        None,
    )
    if not isinstance(review_scenario, Mapping):
        raise ReviewRuntimeError(
            "acceptance repair references an unknown system Review scenario"
        )
    return {
        "acceptance_state_sha256": _sha256(acceptance_path),
        "finding_id": finding_id,
        "finding_sha256": finding_sha256,
        "route": str(finding.get("route") or ""),
        "human_scenario_id": scenario_id,
        "human_step_id": str(finding.get("step_id") or ""),
        "review_scenario_id": review_scenario_id,
        "review_obligation_ids": list(review_scenario.get("obligation_ids") or []),
        "expected": str(finding.get("expected") or ""),
        "observed": str(finding.get("observed") or ""),
        "evidence": list(finding.get("evidence") or []),
    }


ACCEPTANCE_ORIGIN_REVIEW_FINDING_FIELDS = (
    "id",
    "scenario_id",
    "obligation_ids",
    "classification",
    "severity",
    "blocking",
    "summary",
    "expected",
    "observed",
    "evidence",
    "origin_acceptance_finding_id",
)


def _acceptance_origin_review_finding(
    acceptance_repair: Mapping[str, Any],
) -> dict[str, Any]:
    finding_id = str(acceptance_repair.get("finding_id") or "")
    return {
        "id": f"SRF-ACCEPT-{_stable_id_fragment(finding_id)}",
        "scenario_id": str(acceptance_repair.get("review_scenario_id") or ""),
        "obligation_ids": list(acceptance_repair.get("review_obligation_ids") or []),
        "classification": "interaction",
        "gap_classification": "implementation_gap",
        "severity": "high",
        "blocking": True,
        "summary": (
            "Human acceptance observed a mismatch; Review Leader must "
            "diagnose, fix, and independently revalidate it."
        ),
        "expected": str(acceptance_repair.get("expected") or ""),
        "observed": str(acceptance_repair.get("observed") or ""),
        "evidence": list(acceptance_repair.get("evidence") or []),
        "origin_acceptance_finding_id": finding_id,
        "discovered_by_review_assignment_id": "",
        "status": "open",
        "fix_assignment_id": "",
        "revalidation_ids": [],
    }


def _acceptance_origin_review_finding_contract(
    finding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        key: deepcopy(finding.get(key))
        for key in ACCEPTANCE_ORIGIN_REVIEW_FINDING_FIELDS
    }


def _new_review_state(
    *,
    expected_revision: int,
    handoff_digest: str,
    fingerprint: str,
    entrypoints: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    obligations: list[dict[str, Any]],
    human_acceptance_obligations: list[dict[str, Any]],
    human_acceptance_scenarios: list[dict[str, Any]],
    review_cycle: int,
    previous_review_state_sha256: str = "",
    acceptance_repair: Mapping[str, Any] | None = None,
    previous_rounds: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    finding_id = (
        str(acceptance_repair.get("finding_id") or "")
        if isinstance(acceptance_repair, Mapping)
        else ""
    )
    finding_sha256 = (
        str(acceptance_repair.get("finding_sha256") or "")
        if isinstance(acceptance_repair, Mapping)
        else ""
    )
    cycle_id = _review_cycle_id(
        workflow_revision=expected_revision,
        handoff_sha256=handoff_digest,
        review_cycle=review_cycle,
        previous_review_state_sha256=previous_review_state_sha256,
        acceptance_finding_id=finding_id,
        acceptance_finding_sha256=finding_sha256,
    )
    findings: list[dict[str, Any]] = []
    repair_cycles: list[dict[str, Any]] = []
    if isinstance(acceptance_repair, Mapping):
        findings.append(_acceptance_origin_review_finding(acceptance_repair))
        repair_cycles.append(
            {
                **dict(acceptance_repair),
                "review_cycle": review_cycle,
                "review_cycle_id": cycle_id,
                "status": "reviewing",
            }
        )
    state: dict[str, Any] = {
        "version": REVIEW_STATE_VERSION,
        "schema_ref": REVIEW_SCHEMA_REF,
        "status": "reviewing",
        "source": {
            "workflow_revision": expected_revision,
            "implementation_fingerprint": fingerprint,
            "implementation_handoff_sha256": handoff_digest,
            "review_cycle": review_cycle,
            "review_cycle_id": cycle_id,
            "previous_review_state_sha256": previous_review_state_sha256,
            "acceptance_finding_id": finding_id,
            "acceptance_finding_sha256": finding_sha256,
        },
        "entrypoints": deepcopy(entrypoints),
        "scenarios": deepcopy(scenarios),
        "obligations": deepcopy(obligations),
        "human_acceptance_obligations": deepcopy(human_acceptance_obligations),
        "human_acceptance_scenarios": deepcopy(human_acceptance_scenarios),
        "reviewed_runtime_targets": [],
        "review_assignments": [],
        "fix_assignments": [],
        "revalidations": [],
        "coverage": {
            "discovery_complete": False,
            "blind_audit_complete": False,
            "uncovered_obligation_ids": [
                item["id"] for item in obligations if item["required"]
            ],
            "uncovered_surface_ids": [],
            "final_gap_scan": "pending",
        },
        "leader": {
            "strategy": "pending",
            "review_plan_complete": False,
            "all_review_results_joined": False,
            "fix_plan_complete": False,
            "all_fix_results_joined": False,
            "final_revalidation_complete": False,
            "verdict": "pending",
        },
        "rounds": list(previous_rounds or []),
        "findings": findings,
        "repair_cycles": repair_cycles,
        "validation": {
            "startup": "pending",
            "real_entrypoint_journeys": "pending",
            "regression": "pending",
            "ui_verification": "pending",
        },
        "cursor": {
            "scenario_id": (
                str(acceptance_repair.get("review_scenario_id") or "")
                if isinstance(acceptance_repair, Mapping)
                else (scenarios[0]["id"] if scenarios else None)
            ),
            "next_action": "Run the current scenario from its official entrypoint.",
        },
        "blocker": None,
        "final": {
            "verdict": "pending",
            "coverage_verdict": "pending",
            "repair_verdict": "pending",
            "integration_verdict": "pending",
            "all_packets_joined": False,
            "reviewed_snapshot_sha256": "",
            "implementation_summary_sha256": "",
            "runtime_targets_sha256": "",
        },
    }
    return state


def prepare_review(
    project_root: Path,
    feature_dir: Path | str,
    *,
    expected_revision: int,
) -> dict[str, Any]:
    """Create or resume the system review state from a trusted implementation handoff."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    workflow = _validate_workflow_owner(feature, expected_revision)
    last_reopen = workflow.get("last_reopen")
    is_acceptance_repair = isinstance(last_reopen, Mapping) and (
        last_reopen.get("source_stage") == "accept"
        and last_reopen.get("target_stage") == "review"
    )
    handoff_file = implementation_handoff_path(feature)
    handoff = _read_json_object(handoff_file, label=IMPLEMENTATION_HANDOFF_FILENAME)
    _validate_handoff_against_live_sources(feature, handoff)
    handoff_revision = handoff.get("source_revision")
    if isinstance(handoff_revision, bool) or not isinstance(handoff_revision, int):
        raise ReviewRuntimeError(
            "implementation-handoff.json source_revision must be an integer"
        )
    if not is_acceptance_repair and handoff_revision != expected_revision:
        raise ReviewRuntimeError(
            "implementation handoff source_revision does not match the active review revision"
        )
    (
        fingerprint,
        entrypoints,
        scenarios,
        obligations,
        human_acceptance_obligations,
        human_acceptance_scenarios,
        _,
    ) = _normalized_handoff(handoff, expected_revision=handoff_revision)
    handoff_digest = _sha256(handoff_file)
    state_file = review_state_path(feature)

    with interprocess_lock(feature / ".review-state.lock"):
        if state_file.is_file():
            existing = _read_json_object(state_file, label=REVIEW_STATE_FILENAME)
            source = existing.get("source")
            if (
                is_acceptance_repair
                and isinstance(source, Mapping)
                and source.get("workflow_revision") == expected_revision
                and source.get("acceptance_finding_id") == last_reopen.get("finding_id")
                and source.get("implementation_handoff_sha256") == handoff_digest
            ):
                return envelope(
                    "ok",
                    "Acceptance repair Review cycle is already prepared.",
                    data=existing,
                )
            if is_acceptance_repair:
                if existing.get("status") != "approved":
                    raise ReviewRuntimeError(
                        "acceptance repair cycle requires the previous Review to be approved"
                    )
                previous_digest = _sha256(state_file)
                repair_context = _acceptance_repair_context(
                    feature,
                    workflow=workflow,
                    previous_review_state=existing,
                    previous_review_state_sha256=previous_digest,
                )
                previous_source = existing.get("source")
                previous_cycle = (
                    int(previous_source.get("review_cycle") or 1)
                    if isinstance(previous_source, Mapping)
                    else 1
                )
                previous_final = existing.get("final")
                previous_rounds = list(existing.get("rounds") or [])
                previous_rounds.append(
                    {
                        "review_cycle": previous_cycle,
                        "review_state_sha256": previous_digest,
                        "reviewed_snapshot_sha256": (
                            str(previous_final.get("reviewed_snapshot_sha256") or "")
                            if isinstance(previous_final, Mapping)
                            else ""
                        ),
                        "status": "superseded-by-acceptance-repair",
                        "acceptance_finding_id": repair_context["finding_id"],
                    }
                )
                state = _new_review_state(
                    expected_revision=expected_revision,
                    handoff_digest=handoff_digest,
                    fingerprint=fingerprint,
                    entrypoints=entrypoints,
                    scenarios=scenarios,
                    obligations=obligations,
                    human_acceptance_obligations=human_acceptance_obligations,
                    human_acceptance_scenarios=human_acceptance_scenarios,
                    review_cycle=previous_cycle + 1,
                    previous_review_state_sha256=previous_digest,
                    acceptance_repair=repair_context,
                    previous_rounds=previous_rounds,
                )
                atomic_write_text(
                    state_file,
                    json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                )
                return envelope(
                    "ok", "Acceptance repair Review cycle prepared.", data=state
                )
            if (
                isinstance(source, Mapping)
                and source.get("implementation_handoff_sha256") == handoff_digest
                and source.get("workflow_revision") == expected_revision
            ):
                return envelope(
                    "ok",
                    "System review state is already prepared.",
                    data=existing,
                )
            raise ReviewRuntimeError(
                "existing review state is stale; preserve its evidence and explicitly restart review"
            )

        if is_acceptance_repair:
            raise ReviewRuntimeError(
                "acceptance repair cycle is missing the previous approved review-state.json"
            )
        (feature / "review-evidence").mkdir(parents=True, exist_ok=True)
        (feature / "review-results").mkdir(parents=True, exist_ok=True)
        state = _new_review_state(
            expected_revision=expected_revision,
            handoff_digest=handoff_digest,
            fingerprint=fingerprint,
            entrypoints=entrypoints,
            scenarios=scenarios,
            obligations=obligations,
            human_acceptance_obligations=human_acceptance_obligations,
            human_acceptance_scenarios=human_acceptance_scenarios,
            review_cycle=1,
        )
        atomic_write_text(
            state_file, json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        )
    return envelope("ok", "System review state prepared.", data=state)


def _scenario_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value.get(key)
        for key in (
            "id",
            "kind",
            "title",
            "required",
            "entrypoint_id",
            "preconditions",
            "actions",
            "expected_results",
            "required_evidence",
            "obligation_ids",
        )
    }


def _entrypoint_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in ("id", "command", "ready_signal")}


def _obligation_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value.get(key)
        for key in ("id", "kind", "source_ref", "surface", "required", "scenario_ids")
    }


def _indexed_objects(value: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        return {}
    return {
        str(item.get("id")): item
        for item in value
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    }


def _duplicate_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        if item_id in seen:
            duplicates.add(item_id)
        seen.add(item_id)
    return duplicates


def _safe_feature_ref(feature_dir: Path, value: object) -> bool:
    candidate = Path(str(value or ""))
    if (
        not str(value or "").strip()
        or candidate.is_absolute()
        or any(part in {".", ".."} for part in candidate.parts)
    ):
        return False
    resolved = (feature_dir / candidate).resolve(strict=False)
    try:
        resolved.relative_to(feature_dir.resolve(strict=False))
    except ValueError:
        return False
    return True


def _ref_is_bound_to_implementation_snapshot(feature_dir: Path, value: object) -> bool:
    if not _safe_feature_ref(feature_dir, value):
        return False
    resolved = (feature_dir / Path(str(value))).resolve(strict=False)
    try:
        relative = resolved.relative_to(feature_dir.resolve(strict=False)).as_posix()
    except ValueError:
        return False
    return (
        relative not in SNAPSHOT_EXCLUDED_FEATURE_NAMES
        and not relative.endswith(".lock")
        and not relative.startswith(SNAPSHOT_EXCLUDED_FEATURE_PREFIXES)
    )


def _ref_is_in_review_cycle(
    feature_dir: Path,
    value: object,
    *,
    root: str,
    cycle: object,
) -> bool:
    if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 1:
        return False
    if not _safe_feature_ref(feature_dir, value):
        return False
    candidate = Path(str(value or ""))
    resolved = (feature_dir / candidate).resolve(strict=False)
    artifact_root = (feature_dir / root).resolve(strict=False)
    cycle_root = (
        artifact_root
        if cycle == 1
        else (artifact_root / f"cycle-{cycle}").resolve(strict=False)
    )
    try:
        relative = resolved.relative_to(cycle_root)
    except ValueError:
        return False
    if resolved == cycle_root:
        return False
    if (
        cycle == 1
        and relative.parts
        and re.fullmatch(r"cycle-[0-9]+", relative.parts[0])
    ):
        return False
    return True


def _accepted_fix_assignments_sha256(
    fix_assignments: Mapping[str, Mapping[str, Any]],
) -> str:
    payload = [
        {
            key: deepcopy(assignment.get(key))
            for key in (
                "id",
                "finding_ids",
                "worker_id",
                "allowed_write_paths",
                "changed_paths",
                "packet_ref",
                "packet_sha256",
                "result_ref",
                "result_sha256",
                "review_cycle_id",
            )
        }
        for _, assignment in sorted(fix_assignments.items())
        if assignment.get("status") == "accepted"
        and assignment.get("leader_verdict") == "accepted"
    ]
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _path_within_any(relative: str, allowed: list[str]) -> bool:
    candidate = relative.replace("\\", "/").strip("/")
    return any(
        candidate == root.replace("\\", "/").strip("/")
        or candidate.startswith(root.replace("\\", "/").strip("/") + "/")
        for root in allowed
        if root.strip("/\\")
    )


def _validate_review_runtime_targets(
    state: Mapping[str, Any],
    *,
    feature_dir: Path,
    expected_snapshot: str,
    status: str,
) -> tuple[list[dict[str, Any]], list[str], bool]:
    errors: list[str] = []
    fresh = True
    raw_targets = state.get("reviewed_runtime_targets")
    if not isinstance(raw_targets, list):
        return [], ["reviewed_runtime_targets must be an array"], fresh
    if status == "approved" and not raw_targets:
        errors.append("approved Review requires at least one reviewed runtime target")
    entrypoints = _indexed_objects(state.get("entrypoints"))
    review_scenarios = _indexed_objects(state.get("scenarios"))
    source = state.get("source")
    source = source if isinstance(source, Mapping) else {}
    review_cycle = source.get("review_cycle")
    targets: list[dict[str, Any]] = []
    target_ids: set[str] = set()
    for index, raw in enumerate(raw_targets):
        prefix = f"reviewed_runtime_targets[{index}]"
        if not isinstance(raw, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        target = _review_runtime_target_contract(raw)
        target_id = str(target.get("id") or "").strip()
        if not target_id:
            errors.append(f"{prefix}.id is required")
        elif target_id in target_ids:
            errors.append(f"duplicate reviewed runtime target id: {target_id}")
        target_ids.add(target_id)
        mode = str(target.get("mode") or "")
        if mode not in REVIEW_RUNTIME_TARGET_MODES:
            errors.append(f"{prefix}.mode is invalid")
        if target.get("status") != "ready":
            errors.append(f"{prefix}.status must be ready")
        entrypoint_id = str(target.get("entrypoint_id") or "").strip()
        if entrypoint_id not in entrypoints:
            errors.append(f"{prefix}.entrypoint_id must name an official entrypoint")
        for field in (
            "environment_ref",
            "instance_ref",
            "configuration_ref",
            "reviewed_snapshot_sha256",
        ):
            if not str(target.get(field) or "").strip():
                errors.append(f"{prefix}.{field} is required")
        if target.get("reviewed_snapshot_sha256") != expected_snapshot:
            fresh = False
            errors.append(f"{prefix}.reviewed_snapshot_sha256 is stale")
        for field in (
            "test_data_refs",
            "ready_evidence_refs",
            "review_scenario_ids",
        ):
            values = target.get(field)
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in (values if isinstance(values, list) else [])
            ):
                errors.append(f"{prefix}.{field} must be a string array")
        ready_refs = target.get("ready_evidence_refs")
        if not isinstance(ready_refs, list) or not ready_refs:
            errors.append(f"{prefix}.ready_evidence_refs must be non-empty")
        else:
            for evidence_ref in ready_refs:
                if not _safe_feature_ref(feature_dir, evidence_ref):
                    errors.append(
                        f"{prefix}.ready_evidence_refs contains a missing or unsafe ref: {evidence_ref}"
                    )
                    continue
                evidence_path = (feature_dir / Path(str(evidence_ref))).resolve(
                    strict=False
                )
                if not evidence_path.is_file():
                    errors.append(
                        f"{prefix}.ready_evidence_refs file does not exist: {evidence_ref}"
                    )
                if not _ref_is_in_review_cycle(
                    feature_dir,
                    evidence_ref,
                    root="review-evidence",
                    cycle=review_cycle,
                ):
                    errors.append(
                        f"{prefix}.ready_evidence_refs must belong to the current Review cycle"
                    )
        linked_review_ids = target.get("review_scenario_ids")
        if not isinstance(linked_review_ids, list) or not linked_review_ids:
            errors.append(f"{prefix}.review_scenario_ids must be non-empty")
        else:
            linked_evidence_refs: set[str] = set()
            for review_id in linked_review_ids:
                review_scenario = review_scenarios.get(str(review_id))
                if review_scenario is None:
                    errors.append(
                        f"{prefix}.review_scenario_ids references unknown scenario: {review_id}"
                    )
                elif review_scenario.get("entrypoint_id") != entrypoint_id:
                    errors.append(
                        f"{prefix} links a Review scenario for a different entrypoint: {review_id}"
                    )
                else:
                    linked_evidence_refs.update(
                        str(item.get("path") or "")
                        for item in (review_scenario.get("evidence") or [])
                        if isinstance(item, Mapping)
                    )
            for evidence_ref in ready_refs if isinstance(ready_refs, list) else []:
                if str(evidence_ref) not in linked_evidence_refs:
                    errors.append(
                        f"{prefix}.ready_evidence_refs must reference evidence from its linked Review scenarios"
                    )
        if mode in {"build", "deployment"}:
            artifact_ref = str(target.get("artifact_ref") or "").strip()
            artifact_sha256 = str(target.get("artifact_sha256") or "").strip()
            if not artifact_ref:
                errors.append(f"{prefix}.artifact_ref is required for {mode}")
            if not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
                errors.append(
                    f"{prefix}.artifact_sha256 must be a sha256 digest for {mode}"
                )
            if artifact_ref:
                if not _ref_is_bound_to_implementation_snapshot(
                    feature_dir, artifact_ref
                ):
                    errors.append(
                        f"{prefix}.artifact_ref must be a safe feature-relative file included in the implementation snapshot"
                    )
                else:
                    artifact_path = (feature_dir / Path(artifact_ref)).resolve(
                        strict=False
                    )
                    if not artifact_path.is_file():
                        errors.append(
                            f"{prefix}.artifact_ref file does not exist: {artifact_ref}"
                        )
                    elif (
                        re.fullmatch(r"[0-9a-f]{64}", artifact_sha256)
                        and _sha256(artifact_path) != artifact_sha256
                    ):
                        errors.append(
                            f"{prefix}.artifact_sha256 must bind current artifact bytes"
                        )
        if mode == "deployment":
            for field in ("deployment_id", "observed_version"):
                if not str(target.get(field) or "").strip():
                    errors.append(f"{prefix}.{field} is required for deployment")

        identity_ref = str(target.get("identity_evidence_ref") or "").strip()
        identity_sha256 = str(target.get("identity_evidence_sha256") or "").strip()
        if not identity_ref:
            errors.append(f"{prefix}.identity_evidence_ref is required")
        elif not _safe_feature_ref(feature_dir, identity_ref) or not _path_within_any(
            identity_ref, ["review-evidence"]
        ):
            errors.append(
                f"{prefix}.identity_evidence_ref must be a safe file under review-evidence"
            )
        elif not _ref_is_in_review_cycle(
            feature_dir,
            identity_ref,
            root="review-evidence",
            cycle=review_cycle,
        ):
            errors.append(
                f"{prefix}.identity_evidence_ref must belong to the current Review cycle"
            )
        else:
            identity_path = (feature_dir / Path(identity_ref)).resolve(strict=False)
            if not identity_path.is_file():
                errors.append(
                    f"{prefix}.identity_evidence_ref file does not exist: {identity_ref}"
                )
            else:
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", identity_sha256)
                    or _sha256(identity_path) != identity_sha256
                ):
                    errors.append(
                        f"{prefix}.identity_evidence_sha256 must bind current identity evidence bytes"
                    )
                try:
                    identity_claim = _read_json_object(
                        identity_path,
                        label=f"{prefix} identity evidence",
                    )
                except ReviewRuntimeError as exc:
                    errors.append(str(exc))
                else:
                    if identity_claim != _review_runtime_identity_claim(target):
                        errors.append(
                            f"{prefix}.identity_evidence_ref must exactly identify the reviewed runtime target"
                        )
        targets.append(target)

    if status == "approved":
        human_scenarios = state.get("human_acceptance_scenarios")
        for scenario in human_scenarios if isinstance(human_scenarios, list) else []:
            if (
                not isinstance(scenario, Mapping)
                or scenario.get("required") is not True
            ):
                continue
            linked_review_ids = set(scenario.get("review_scenario_ids") or [])
            matching = [
                target
                for target in targets
                if target.get("status") == "ready"
                and target.get("entrypoint_id") == scenario.get("entrypoint_id")
                and linked_review_ids.issubset(
                    set(target.get("review_scenario_ids") or [])
                )
            ]
            if len(matching) != 1:
                errors.append(
                    "required human acceptance scenario "
                    f"{scenario.get('id') or 'unknown'} requires exactly one reviewed runtime target"
                )
        final = state.get("final")
        final = final if isinstance(final, Mapping) else {}
        expected_digest = _review_runtime_targets_sha256(targets)
        if final.get("runtime_targets_sha256") != expected_digest:
            errors.append(
                "final.runtime_targets_sha256 must match reviewed_runtime_targets"
            )
    return targets, errors, fresh


def _review_validation_errors(
    state: Mapping[str, Any],
    handoff: Mapping[str, Any],
    *,
    feature_dir: Path,
    handoff_digest: str,
    live_fingerprint: str | None,
    workflow: Mapping[str, Any] | None,
) -> tuple[list[str], bool]:
    errors: list[str] = []
    if state.get("version") != REVIEW_STATE_VERSION:
        errors.append(
            f"review-state.json version must equal {REVIEW_STATE_VERSION}; "
            "restart Review to migrate legacy evidence"
        )
    if state.get("schema_ref") != REVIEW_SCHEMA_REF:
        errors.append(f"schema_ref must equal {REVIEW_SCHEMA_REF}")
    status = str(state.get("status") or "")
    if status not in REVIEW_STATUSES:
        errors.append(f"unsupported review status: {status or 'missing'}")

    source = state.get("source")
    fresh = isinstance(source, Mapping)
    acceptance_finding_id = ""
    acceptance_finding_sha256 = ""
    if not fresh:
        errors.append("review state source metadata is missing")
    else:
        fresh = source.get(
            "implementation_handoff_sha256"
        ) == handoff_digest and source.get("implementation_fingerprint") == handoff.get(
            "implementation_fingerprint"
        )
        if not fresh:
            errors.append(
                "review evidence is stale because the implementation handoff changed"
            )
        workflow_revision = source.get("workflow_revision")
        review_cycle = source.get("review_cycle")
        review_cycle_id = str(source.get("review_cycle_id") or "")
        previous_review_state_sha256 = str(
            source.get("previous_review_state_sha256") or ""
        )
        acceptance_finding_id = str(source.get("acceptance_finding_id") or "")
        acceptance_finding_sha256 = str(source.get("acceptance_finding_sha256") or "")
        if (
            isinstance(workflow_revision, bool)
            or not isinstance(workflow_revision, int)
            or workflow_revision < 0
        ):
            errors.append(
                "review source workflow_revision must be a non-negative integer"
            )
        if (
            isinstance(review_cycle, bool)
            or not isinstance(review_cycle, int)
            or review_cycle < 1
        ):
            errors.append("review source review_cycle must be a positive integer")
        elif isinstance(workflow_revision, int):
            expected_cycle_id = _review_cycle_id(
                workflow_revision=workflow_revision,
                handoff_sha256=handoff_digest,
                review_cycle=review_cycle,
                previous_review_state_sha256=previous_review_state_sha256,
                acceptance_finding_id=acceptance_finding_id,
                acceptance_finding_sha256=acceptance_finding_sha256,
            )
            if review_cycle_id != expected_cycle_id:
                errors.append("review source review_cycle_id is invalid")
        if acceptance_finding_id:
            if (
                review_cycle is not None
                and isinstance(review_cycle, int)
                and review_cycle < 2
            ):
                errors.append(
                    "acceptance repair cycle must use review_cycle 2 or later"
                )
            if not re.fullmatch(r"[0-9a-f]{64}", previous_review_state_sha256):
                errors.append(
                    "acceptance repair cycle requires previous_review_state_sha256"
                )
            if not re.fullmatch(r"[0-9a-f]{64}", acceptance_finding_sha256):
                errors.append(
                    "acceptance repair cycle requires acceptance_finding_sha256"
                )
        elif previous_review_state_sha256 or acceptance_finding_sha256:
            errors.append(
                "initial Review must not declare prior Review or acceptance finding digests"
            )
        if workflow is not None and isinstance(workflow_revision, int):
            workflow_stage = str(workflow.get("stage") or "")
            workflow_status = str(workflow.get("status") or "")
            current_revision = workflow.get("revision")
            expected_current_revision: int | None = None
            if workflow_stage == "review" and workflow_status == "active":
                expected_current_revision = workflow_revision
            elif workflow_stage == "review" and workflow_status == "completed":
                expected_current_revision = workflow_revision + 1
            elif workflow_stage == "accept" and workflow_status == "active":
                expected_current_revision = workflow_revision + 2
            elif workflow_stage == "accept" and workflow_status == "completed":
                expected_current_revision = workflow_revision + 3
            if expected_current_revision is not None:
                revision_delta = (
                    current_revision - expected_current_revision
                    if isinstance(current_revision, int)
                    and not isinstance(current_revision, bool)
                    else -1
                )
                if revision_delta < 0 or revision_delta % 2:
                    errors.append(
                        "review source workflow_revision does not match the current workflow cycle"
                    )
            last_reopen = workflow.get("last_reopen")
            repair_reopen = isinstance(last_reopen, Mapping) and (
                last_reopen.get("source_stage") == "accept"
                and last_reopen.get("target_stage") == "review"
            )
            if repair_reopen and (
                not acceptance_finding_id
                or acceptance_finding_id != str(last_reopen.get("finding_id") or "")
            ):
                errors.append(
                    "acceptance repair cycle was not freshly prepared from the routed finding"
                )
    expected_snapshot = live_fingerprint or str(
        handoff.get("implementation_fingerprint") or ""
    )
    if status == "approved":
        final = state.get("final")
        reviewed_fingerprint = (
            str(final.get("reviewed_snapshot_sha256") or "")
            if isinstance(final, Mapping)
            else ""
        )
        if reviewed_fingerprint != expected_snapshot:
            fresh = False
            errors.append(
                "final reviewed snapshot must match the current implementation snapshot"
            )

    try:
        _validate_handoff_against_live_sources(feature_dir, handoff)
        expected_revision = int(handoff.get("source_revision"))
        (
            _,
            canonical_entrypoints,
            canonical_scenarios,
            canonical_obligations,
            canonical_human_acceptance_obligations,
            canonical_human_acceptance_scenarios,
            _,
        ) = _normalized_handoff(handoff, expected_revision=expected_revision)
    except (ReviewRuntimeError, TypeError, ValueError) as exc:
        errors.append(f"invalid canonical review contract: {exc}")
        canonical_entrypoints = []
        canonical_scenarios = []
        canonical_obligations = []
        canonical_human_acceptance_obligations = []
        canonical_human_acceptance_scenarios = []

    actual_entrypoints = _indexed_objects(state.get("entrypoints"))
    for duplicate in sorted(_duplicate_ids(state.get("entrypoints"))):
        errors.append(f"duplicate review entrypoint id: {duplicate}")
    for canonical in canonical_entrypoints:
        actual = actual_entrypoints.get(str(canonical["id"]))
        if actual is None or _entrypoint_contract(actual) != _entrypoint_contract(
            canonical
        ):
            errors.append(f"canonical entrypoint contract drift for {canonical['id']}")

    actual_scenarios = _indexed_objects(state.get("scenarios"))
    for duplicate in sorted(_duplicate_ids(state.get("scenarios"))):
        errors.append(f"duplicate review scenario id: {duplicate}")
    for canonical in canonical_scenarios:
        actual = actual_scenarios.get(str(canonical["id"]))
        if actual is None or _scenario_contract(actual) != _scenario_contract(
            canonical
        ):
            errors.append(f"canonical scenario contract drift for {canonical['id']}")

    actual_obligations = _indexed_objects(state.get("obligations"))
    for duplicate in sorted(_duplicate_ids(state.get("obligations"))):
        errors.append(f"duplicate review obligation id: {duplicate}")
    for canonical in canonical_obligations:
        actual = actual_obligations.get(str(canonical["id"]))
        if actual is None or _obligation_contract(actual) != _obligation_contract(
            canonical
        ):
            errors.append(f"canonical review obligation drift for {canonical['id']}")

    if (
        state.get("human_acceptance_obligations")
        != canonical_human_acceptance_obligations
    ):
        errors.append("canonical human acceptance obligation contract drift")
    if state.get("human_acceptance_scenarios") != canonical_human_acceptance_scenarios:
        errors.append("canonical human acceptance scenario contract drift")

    _, runtime_target_errors, runtime_targets_fresh = _validate_review_runtime_targets(
        state,
        feature_dir=feature_dir,
        expected_snapshot=expected_snapshot,
        status=status,
    )
    errors.extend(runtime_target_errors)
    fresh = fresh and runtime_targets_fresh

    current_review_cycle = (
        source.get("review_cycle") if isinstance(source, Mapping) else None
    )
    current_review_cycle_id = (
        source.get("review_cycle_id") if isinstance(source, Mapping) else None
    )
    scenarios = state.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("review state requires at least one scenario")
        scenarios = []
    for raw in scenarios:
        if not isinstance(raw, Mapping):
            errors.append("review scenario must be an object")
            continue
        scenario_id = str(raw.get("id") or "missing-scenario")
        result = str(raw.get("result") or "")
        if result not in SCENARIO_RESULTS:
            errors.append(
                f"scenario {scenario_id} has unsupported result {result or 'missing'}"
            )
            continue
        if bool(raw.get("required", True)) and result != "pass":
            errors.append(
                f"required scenario {scenario_id} must pass before review closeout"
            )
        evidence = raw.get("evidence")
        evidence_items = evidence if isinstance(evidence, list) else []
        evidence_by_kind = {
            str(item.get("kind") or ""): item
            for item in evidence_items
            if isinstance(item, Mapping)
        }
        for kind in raw.get("required_evidence") or []:
            item = evidence_by_kind.get(str(kind))
            if item is None:
                errors.append(f"scenario {scenario_id} is missing {kind} evidence")
                continue
            if str(item.get("evidence_scope") or "") != "integrated":
                errors.append(
                    f"scenario {scenario_id} {kind} evidence must use evidence_scope integrated"
                )
            evidence_path = str(item.get("path") or "").strip()
            if not evidence_path:
                errors.append(f"scenario {scenario_id} {kind} evidence requires a path")
                continue
            candidate = Path(evidence_path)
            if candidate.is_absolute():
                errors.append(
                    f"scenario {scenario_id} {kind} evidence path must be feature-relative"
                )
                continue
            resolved = (feature_dir / candidate).resolve(strict=False)
            try:
                resolved.relative_to(feature_dir.resolve(strict=False))
            except ValueError:
                errors.append(
                    f"scenario {scenario_id} {kind} evidence path escapes the feature directory"
                )
                continue
            if not resolved.is_file():
                errors.append(
                    f"scenario {scenario_id} {kind} evidence file does not exist: {evidence_path}"
                )
            if not _ref_is_in_review_cycle(
                feature_dir,
                evidence_path,
                root="review-evidence",
                cycle=current_review_cycle,
            ):
                errors.append(
                    f"scenario {scenario_id} {kind} evidence must belong to the current Review cycle"
                )
            if item.get("review_cycle_id") != current_review_cycle_id:
                errors.append(
                    f"scenario {scenario_id} {kind} evidence must bind the current review_cycle_id"
                )
            artifact_sha256 = str(item.get("artifact_sha256") or "")
            if (
                not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256)
                or not resolved.is_file()
                or _sha256(resolved) != artifact_sha256
            ):
                errors.append(
                    f"scenario {scenario_id} {kind} artifact_sha256 must bind current evidence bytes"
                )
            evidence_snapshot = str(item.get("snapshot_sha256") or "")
            if evidence_snapshot != expected_snapshot:
                fresh = False
                errors.append(
                    f"scenario {scenario_id} {kind} evidence snapshot is stale"
                )

    review_assignments = _indexed_objects(state.get("review_assignments"))
    for duplicate in sorted(_duplicate_ids(state.get("review_assignments"))):
        errors.append(f"duplicate Review assignment id: {duplicate}")
    accepted_review_assignments: dict[str, Mapping[str, Any]] = {}
    for assignment_id, assignment in review_assignments.items():
        if (
            assignment.get("status") == "accepted"
            and assignment.get("leader_verdict") == "accepted"
        ):
            accepted_review_assignments[assignment_id] = assignment
        if assignment.get("read_only") is not True:
            errors.append(f"Review assignment {assignment_id} must be read-only")
        if not str(assignment.get("worker_id") or "").strip():
            errors.append(
                f"Review assignment {assignment_id} requires a subagent worker_id"
            )
        packet_ref = assignment.get("packet_ref")
        result_ref = assignment.get("result_ref")
        if not _safe_feature_ref(feature_dir, packet_ref) or not _safe_feature_ref(
            feature_dir, result_ref
        ):
            errors.append(
                f"Review assignment {assignment_id} requires packet and result refs"
            )
        else:
            if assignment.get("review_cycle_id") != current_review_cycle_id:
                errors.append(
                    f"Review assignment {assignment_id} must bind the current review_cycle_id"
                )
            for label, artifact_ref in (("packet", packet_ref), ("result", result_ref)):
                artifact_path = (feature_dir / Path(str(artifact_ref))).resolve(
                    strict=False
                )
                if not artifact_path.is_file():
                    errors.append(
                        f"Review assignment {assignment_id} {label} file does not exist: "
                        f"{artifact_ref}"
                    )
                if not _ref_is_in_review_cycle(
                    feature_dir,
                    artifact_ref,
                    root="review-results",
                    cycle=current_review_cycle,
                ):
                    errors.append(
                        f"Review assignment {assignment_id} {label} must belong to the current Review cycle"
                    )
                recorded_sha256 = str(assignment.get(f"{label}_sha256") or "")
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", recorded_sha256)
                    or not artifact_path.is_file()
                    or _sha256(artifact_path) != recorded_sha256
                ):
                    errors.append(
                        f"Review assignment {assignment_id} {label}_sha256 must bind current artifact bytes"
                    )
        if (
            assignment.get("status") == "accepted"
            and str(assignment.get("observed_snapshot_sha256") or "")
            != expected_snapshot
        ):
            fresh = False
            errors.append(f"Review assignment {assignment_id} snapshot is stale")

    coverage = state.get("coverage")
    coverage = coverage if isinstance(coverage, Mapping) else {}
    coverage_audits = [
        assignment
        for assignment in accepted_review_assignments.values()
        if assignment.get("kind") == "coverage_audit"
    ]
    if (
        not coverage_audits
        or coverage.get("discovery_complete") is not True
        or coverage.get("blind_audit_complete") is not True
        or coverage.get("uncovered_obligation_ids") != []
        or coverage.get("uncovered_surface_ids") != []
        or coverage.get("final_gap_scan") != "pass"
    ):
        errors.append(
            "independent subagent coverage audit must finish with zero uncovered obligations and surfaces"
        )

    for obligation_id, obligation in actual_obligations.items():
        if not bool(obligation.get("required", True)):
            continue
        assignment_ids = obligation.get("review_assignment_ids")
        assignment_ids = assignment_ids if isinstance(assignment_ids, list) else []
        scenario_ids = obligation.get("scenario_ids")
        scenario_ids = scenario_ids if isinstance(scenario_ids, list) else []
        covered_by_assignment = any(
            assignment_id in accepted_review_assignments
            and obligation_id
            in (accepted_review_assignments[assignment_id].get("obligation_ids") or [])
            for assignment_id in assignment_ids
        )
        covered_by_scenario = bool(scenario_ids) and all(
            str(actual_scenarios.get(str(scenario_id), {}).get("result") or "")
            == "pass"
            for scenario_id in scenario_ids
        )
        if (
            obligation.get("status") != "covered"
            or not covered_by_assignment
            or not covered_by_scenario
        ):
            errors.append(
                f"required obligation {obligation_id} needs accepted subagent review and passing scenarios"
            )

    leader = state.get("leader")
    leader = leader if isinstance(leader, Mapping) else {}
    required_leader_values = {
        "strategy": "leader-plus-subagents",
        "review_plan_complete": True,
        "all_review_results_joined": True,
        "fix_plan_complete": True,
        "all_fix_results_joined": True,
        "final_revalidation_complete": True,
        "verdict": "pass",
    }
    if any(leader.get(key) != value for key, value in required_leader_values.items()):
        errors.append(
            "Leader must plan, join all Review/Fix subagents, and complete final revalidation"
        )

    findings = state.get("findings")
    if not isinstance(findings, list):
        errors.append("review findings must be an array")
        findings = []
    errors.extend(_review_finding_gap_classification_errors(findings))
    acceptance_finding_id = (
        str(source.get("acceptance_finding_id") or "")
        if isinstance(source, Mapping)
        else ""
    )
    if acceptance_finding_id:
        acceptance_path = feature_dir / "human-acceptance.json"
        try:
            acceptance_state = _read_json_object(
                acceptance_path, label="human-acceptance.json"
            )
        except ReviewRuntimeError as exc:
            errors.append(str(exc))
            acceptance_state = {}
        acceptance_findings = acceptance_state.get("findings")
        routed_finding = next(
            (
                item
                for item in (
                    acceptance_findings if isinstance(acceptance_findings, list) else []
                )
                if isinstance(item, Mapping) and item.get("id") == acceptance_finding_id
            ),
            None,
        )
        repair_resume = acceptance_state.get("repair_resume")
        if (
            not isinstance(routed_finding, Mapping)
            or _acceptance_finding_sha256(routed_finding) != acceptance_finding_sha256
            or not isinstance(repair_resume, Mapping)
            or repair_resume.get("finding_contract_sha256") != acceptance_finding_sha256
        ):
            errors.append(
                "routed acceptance finding changed after the Review cycle was prepared"
            )
        expected_acceptance_repair: dict[str, Any] | None = None
        if isinstance(routed_finding, Mapping):
            human_scenarios = state.get("human_acceptance_scenarios")
            routed_human_scenario = next(
                (
                    item
                    for item in (
                        human_scenarios if isinstance(human_scenarios, list) else []
                    )
                    if isinstance(item, Mapping)
                    and item.get("id") == routed_finding.get("scenario_id")
                ),
                None,
            )
            linked_review_ids = (
                routed_human_scenario.get("review_scenario_ids")
                if isinstance(routed_human_scenario, Mapping)
                else None
            )
            expected_review_scenario_id = (
                str(linked_review_ids[0])
                if isinstance(linked_review_ids, list) and linked_review_ids
                else ""
            )
            expected_review_scenario = actual_scenarios.get(expected_review_scenario_id)
            if not expected_review_scenario_id or not isinstance(
                expected_review_scenario, Mapping
            ):
                errors.append(
                    "routed acceptance finding no longer maps to a required Review scenario"
                )
            else:
                expected_acceptance_repair = {
                    "finding_id": acceptance_finding_id,
                    "finding_sha256": acceptance_finding_sha256,
                    "route": str(routed_finding.get("route") or ""),
                    "human_scenario_id": str(routed_finding.get("scenario_id") or ""),
                    "human_step_id": str(routed_finding.get("step_id") or ""),
                    "review_scenario_id": expected_review_scenario_id,
                    "review_obligation_ids": list(
                        expected_review_scenario.get("obligation_ids") or []
                    ),
                    "expected": str(routed_finding.get("expected") or ""),
                    "observed": str(routed_finding.get("observed") or ""),
                    "evidence": list(routed_finding.get("evidence") or []),
                }
                origin_findings = [
                    item
                    for item in findings
                    if isinstance(item, Mapping)
                    and item.get("origin_acceptance_finding_id")
                    == acceptance_finding_id
                ]
                if len(origin_findings) != 1 or (
                    _acceptance_origin_review_finding_contract(origin_findings[0])
                    != _acceptance_origin_review_finding_contract(
                        _acceptance_origin_review_finding(expected_acceptance_repair)
                    )
                ):
                    errors.append(
                        "acceptance-origin Review finding must exactly preserve the routed human observation and Review mapping"
                    )
        repair_cycles = state.get("repair_cycles")
        matching_cycles = [
            item
            for item in (repair_cycles if isinstance(repair_cycles, list) else [])
            if isinstance(item, Mapping)
            and item.get("review_cycle_id")
            == (source.get("review_cycle_id") if isinstance(source, Mapping) else None)
        ]
        if len(matching_cycles) != 1:
            errors.append(
                "acceptance repair requires exactly one matching repair_cycles record"
            )
        else:
            repair_cycle = matching_cycles[0]
            if (
                repair_cycle.get("finding_id") != acceptance_finding_id
                or repair_cycle.get("finding_sha256") != acceptance_finding_sha256
                or repair_cycle.get("review_cycle")
                != (source.get("review_cycle") if isinstance(source, Mapping) else None)
            ):
                errors.append(
                    "repair_cycles must bind the current routed acceptance state and Review cycle"
                )
            if not re.fullmatch(
                r"[0-9a-f]{64}",
                str(repair_cycle.get("acceptance_state_sha256") or ""),
            ):
                errors.append(
                    "repair_cycles.acceptance_state_sha256 must preserve the routed acceptance digest"
                )
            if expected_acceptance_repair is not None:
                for key, expected_value in expected_acceptance_repair.items():
                    if repair_cycle.get(key) != expected_value:
                        errors.append(
                            "repair_cycles must exactly preserve routed acceptance context"
                        )
                        break
    fix_assignments = _indexed_objects(state.get("fix_assignments"))
    revalidations = _indexed_objects(state.get("revalidations"))
    for duplicate in sorted(_duplicate_ids(state.get("fix_assignments"))):
        errors.append(f"duplicate Fix assignment id: {duplicate}")
    for duplicate in sorted(_duplicate_ids(state.get("revalidations"))):
        errors.append(f"duplicate revalidation id: {duplicate}")
    for duplicate in sorted(_duplicate_ids(findings)):
        errors.append(f"duplicate finding id: {duplicate}")
    review_workers = {
        assignment_id: str(assignment.get("worker_id") or "")
        for assignment_id, assignment in review_assignments.items()
    }
    fix_artifacts_valid: dict[str, bool] = {}
    for assignment_id, assignment in fix_assignments.items():
        artifacts_valid = True
        if assignment.get("review_cycle_id") != current_review_cycle_id:
            artifacts_valid = False
            errors.append(
                f"Fix assignment {assignment_id} must bind the current review_cycle_id"
            )
        for label in ("packet", "result"):
            artifact_ref = assignment.get(f"{label}_ref")
            if not _ref_is_in_review_cycle(
                feature_dir,
                artifact_ref,
                root="review-results",
                cycle=current_review_cycle,
            ):
                artifacts_valid = False
                errors.append(
                    f"Fix assignment {assignment_id} {label} must belong to the current Review cycle"
                )
                continue
            artifact_path = (feature_dir / Path(str(artifact_ref))).resolve(
                strict=False
            )
            if not artifact_path.is_file():
                artifacts_valid = False
                errors.append(
                    f"Fix assignment {assignment_id} {label} file does not exist: {artifact_ref}"
                )
                continue
            recorded_sha256 = str(assignment.get(f"{label}_sha256") or "")
            if (
                not re.fullmatch(r"[0-9a-f]{64}", recorded_sha256)
                or _sha256(artifact_path) != recorded_sha256
            ):
                artifacts_valid = False
                errors.append(
                    f"Fix assignment {assignment_id} {label}_sha256 must bind current artifact bytes"
                )
        fix_artifacts_valid[assignment_id] = artifacts_valid

    revalidation_artifacts_valid: dict[str, bool] = {}
    for revalidation_id, revalidation in revalidations.items():
        artifacts_valid = True
        if revalidation.get("review_cycle_id") != current_review_cycle_id:
            artifacts_valid = False
            errors.append(
                f"revalidation {revalidation_id} must bind the current review_cycle_id"
            )
        evidence_refs = revalidation.get("evidence_refs")
        evidence_refs = evidence_refs if isinstance(evidence_refs, list) else []
        evidence_sha256 = revalidation.get("evidence_sha256")
        evidence_sha256 = (
            evidence_sha256 if isinstance(evidence_sha256, Mapping) else {}
        )
        if not evidence_refs:
            artifacts_valid = False
            errors.append(f"revalidation {revalidation_id} requires evidence refs")
        for evidence_ref in evidence_refs:
            if not _ref_is_in_review_cycle(
                feature_dir,
                evidence_ref,
                root="review-results",
                cycle=current_review_cycle,
            ):
                artifacts_valid = False
                errors.append(
                    f"revalidation {revalidation_id} evidence must belong to the current Review cycle"
                )
                continue
            evidence_path = (feature_dir / Path(str(evidence_ref))).resolve(
                strict=False
            )
            if not evidence_path.is_file():
                artifacts_valid = False
                errors.append(
                    f"revalidation {revalidation_id} evidence file does not exist: {evidence_ref}"
                )
                continue
            recorded_sha256 = str(evidence_sha256.get(str(evidence_ref)) or "")
            if (
                not re.fullmatch(r"[0-9a-f]{64}", recorded_sha256)
                or _sha256(evidence_path) != recorded_sha256
            ):
                artifacts_valid = False
                errors.append(
                    f"revalidation {revalidation_id} evidence_sha256 must bind current cycle artifact bytes"
                )
        revalidation_artifacts_valid[revalidation_id] = artifacts_valid

    for raw in findings:
        if not isinstance(raw, Mapping):
            errors.append("review finding must be an object")
            continue
        finding_id = str(raw.get("id") or "missing-finding")
        finding_scenario_id = str(raw.get("scenario_id") or "")
        finding_scenario = actual_scenarios.get(finding_scenario_id)
        if not isinstance(finding_scenario, Mapping):
            errors.append(
                f"finding {finding_id} must reference an existing Review scenario"
            )
        finding_obligation_ids = raw.get("obligation_ids")
        if (
            not isinstance(finding_obligation_ids, list)
            or not finding_obligation_ids
            or any(
                not isinstance(item, str) or not item.strip()
                for item in (
                    finding_obligation_ids
                    if isinstance(finding_obligation_ids, list)
                    else []
                )
            )
        ):
            errors.append(
                f"finding {finding_id} must reference at least one Review obligation"
            )
        elif isinstance(finding_scenario, Mapping):
            scenario_obligation_ids = set(finding_scenario.get("obligation_ids") or [])
            if not set(finding_obligation_ids).issubset(scenario_obligation_ids):
                errors.append(
                    f"finding {finding_id} obligation_ids must belong to its Review scenario"
                )
        finding_status = str(raw.get("status") or "")
        if finding_status not in FINDING_STATUSES:
            errors.append(
                f"finding {finding_id} has unsupported status {finding_status or 'missing'}"
            )
        elif finding_status not in {"verified", "accepted_residual_risk"}:
            errors.append(
                f"finding {finding_id} must be verified before review closeout"
            )

        blocking = bool(raw.get("blocking", True))
        if finding_status == "accepted_residual_risk" and blocking:
            errors.append(
                f"blocking finding {finding_id} cannot be accepted as residual risk"
            )

        discovering_assignment_id = str(
            raw.get("discovered_by_review_assignment_id") or ""
        )
        discovering_worker = review_workers.get(discovering_assignment_id, "")
        if raw.get("origin_acceptance_finding_id") and (
            discovering_assignment_id not in accepted_review_assignments
        ):
            errors.append(
                f"acceptance-origin finding {finding_id} requires an accepted read-only diagnostic Review assignment"
            )
        fix_assignment_id = str(raw.get("fix_assignment_id") or "")
        fix_assignment = fix_assignments.get(fix_assignment_id)
        valid_fix = fix_assignment is not None
        if valid_fix:
            allowed_paths = fix_assignment.get("allowed_write_paths")
            changed_paths = fix_assignment.get("changed_paths")
            allowed_paths = allowed_paths if isinstance(allowed_paths, list) else []
            changed_paths = changed_paths if isinstance(changed_paths, list) else []
            fix_worker = str(fix_assignment.get("worker_id") or "")
            valid_fix = (
                fix_assignment.get("status") == "accepted"
                and fix_assignment.get("leader_verdict") == "accepted"
                and finding_id in (fix_assignment.get("finding_ids") or [])
                and bool(fix_worker)
                and fix_worker != discovering_worker
                and bool(allowed_paths)
                and bool(changed_paths)
                and all(
                    isinstance(path, str) and _path_within_any(path, allowed_paths)
                    for path in changed_paths
                )
                and fix_artifacts_valid.get(fix_assignment_id, False)
            )
        if not valid_fix:
            errors.append(
                f"finding {finding_id} requires an independent Fix assignment accepted by the Leader"
            )

        revalidation_ids = raw.get("revalidation_ids")
        revalidation_ids = (
            revalidation_ids if isinstance(revalidation_ids, list) else []
        )
        valid_revalidation = False
        for revalidation_id in revalidation_ids:
            revalidation = revalidations.get(str(revalidation_id))
            if revalidation is None or fix_assignment is None:
                continue
            revalidation_worker = str(revalidation.get("worker_id") or "")
            valid_revalidation = (
                revalidation.get("result") == "pass"
                and revalidation.get("leader_verdict") == "accepted"
                and finding_id in (revalidation.get("finding_ids") or [])
                and fix_assignment_id in (revalidation.get("fix_assignment_ids") or [])
                and str(raw.get("scenario_id") or "")
                in (revalidation.get("scenario_ids") or [])
                and revalidation_worker
                not in {discovering_worker, str(fix_assignment.get("worker_id") or "")}
                and str(revalidation.get("snapshot_sha256") or "") == expected_snapshot
                and revalidation_artifacts_valid.get(str(revalidation_id), False)
            )
            if valid_revalidation:
                break
        if not valid_revalidation:
            errors.append(
                f"finding {finding_id} requires independent revalidation accepted by the Leader"
            )

    if fix_assignments:
        accepted_fix_assignments = {
            assignment_id: assignment
            for assignment_id, assignment in fix_assignments.items()
            if assignment.get("status") == "accepted"
            and assignment.get("leader_verdict") == "accepted"
        }
        if len(accepted_fix_assignments) != len(fix_assignments):
            errors.append(
                "every Fix assignment must be accepted and joined before full-matrix revalidation"
            )
        fix_assignments_sha256 = _accepted_fix_assignments_sha256(
            accepted_fix_assignments
        )
        required_scenario_ids = sorted(
            scenario_id
            for scenario_id, scenario in actual_scenarios.items()
            if bool(scenario.get("required", True))
        )
        expected_scenario_evidence: list[dict[str, str]] = []
        for scenario_id in required_scenario_ids:
            scenario = actual_scenarios[scenario_id]
            evidence_by_kind = {
                str(item.get("kind") or ""): item
                for item in (scenario.get("evidence") or [])
                if isinstance(item, Mapping)
            }
            for kind in scenario.get("required_evidence") or []:
                item = evidence_by_kind.get(str(kind))
                if item is None:
                    continue
                expected_scenario_evidence.append(
                    {
                        "scenario_id": scenario_id,
                        "kind": str(kind),
                        "path": str(item.get("path") or ""),
                        "artifact_sha256": str(item.get("artifact_sha256") or ""),
                    }
                )
        expected_scenario_evidence.sort(
            key=lambda item: (item["scenario_id"], item["kind"], item["path"])
        )
        expected_fix_ids = sorted(accepted_fix_assignments)
        fix_workers = {
            str(assignment.get("worker_id") or "")
            for assignment in accepted_fix_assignments.values()
        }
        full_matrix_valid = False
        for revalidation_id, revalidation in revalidations.items():
            candidate_fix_ids = revalidation.get("fix_assignment_ids")
            candidate_scenario_ids = revalidation.get("scenario_ids")
            exact_fix_set = (
                isinstance(candidate_fix_ids, list)
                and len(candidate_fix_ids) == len(expected_fix_ids)
                and sorted(candidate_fix_ids) == expected_fix_ids
            )
            exact_scenario_set = (
                isinstance(candidate_scenario_ids, list)
                and len(candidate_scenario_ids) == len(required_scenario_ids)
                and sorted(candidate_scenario_ids) == required_scenario_ids
            )
            if (
                revalidation.get("result") != "pass"
                or revalidation.get("leader_verdict") != "accepted"
                or not exact_fix_set
                or not exact_scenario_set
                or str(revalidation.get("snapshot_sha256") or "") != expected_snapshot
                or revalidation.get("review_cycle_id") != current_review_cycle_id
                or revalidation.get("fix_assignments_sha256") != fix_assignments_sha256
                or not str(revalidation.get("worker_id") or "")
                or str(revalidation.get("worker_id") or "") in fix_workers
                or not revalidation_artifacts_valid.get(revalidation_id, False)
            ):
                continue
            evidence_refs = revalidation.get("evidence_refs")
            evidence_refs = evidence_refs if isinstance(evidence_refs, list) else []
            evidence_sha256 = revalidation.get("evidence_sha256")
            evidence_sha256 = (
                evidence_sha256 if isinstance(evidence_sha256, Mapping) else {}
            )
            manifest_ref = str(revalidation.get("evidence_manifest_ref") or "")
            if manifest_ref not in evidence_refs or not _ref_is_in_review_cycle(
                feature_dir,
                manifest_ref,
                root="review-results",
                cycle=current_review_cycle,
            ):
                continue
            manifest_path = (feature_dir / manifest_ref).resolve(strict=False)
            manifest_digest = str(evidence_sha256.get(manifest_ref) or "")
            if (
                not manifest_path.is_file()
                or not re.fullmatch(r"[0-9a-f]{64}", manifest_digest)
                or _sha256(manifest_path) != manifest_digest
            ):
                continue
            try:
                manifest = _read_json_object(
                    manifest_path, label=f"revalidation {revalidation_id} manifest"
                )
            except ReviewRuntimeError as exc:
                errors.append(str(exc))
                continue
            expected_manifest = {
                "version": 1,
                "revalidation_id": revalidation_id,
                "review_cycle_id": current_review_cycle_id,
                "snapshot_sha256": expected_snapshot,
                "fix_assignments_sha256": fix_assignments_sha256,
                "scenario_evidence": expected_scenario_evidence,
            }
            if manifest.get("snapshot_sha256") != expected_snapshot:
                errors.append(
                    f"revalidation {revalidation_id} manifest must bind the final reviewed snapshot"
                )
                continue
            if manifest != expected_manifest:
                errors.append(
                    f"revalidation {revalidation_id} manifest must exactly bind the accepted Fix set and every required scenario evidence item"
                )
                continue
            full_matrix_valid = True
            break
        if not full_matrix_valid:
            errors.append(
                "a final full-matrix revalidation must cover every required scenario after the accepted Fix set"
            )

    final = state.get("final")
    final = final if isinstance(final, Mapping) else {}
    required_final_values = {
        "verdict": "pass",
        "coverage_verdict": "pass",
        "repair_verdict": "pass",
        "integration_verdict": "pass",
        "all_packets_joined": True,
    }
    if status == "approved" and any(
        final.get(key) != value for key, value in required_final_values.items()
    ):
        errors.append("final Review verdicts and packet joins must all pass")
    return errors, fresh


def validate_review(project_root: Path, feature_dir: Path | str) -> dict[str, Any]:
    """Validate system review shape, freshness, scenarios, findings, and evidence."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    state_file = review_state_path(feature)
    handoff_file = implementation_handoff_path(feature)
    try:
        state = _read_json_object(state_file, label=REVIEW_STATE_FILENAME)
        handoff = _read_json_object(handoff_file, label=IMPLEMENTATION_HANDOFF_FILENAME)
        try:
            workflow = show_workflow(feature).get("data")
        except MissingWorkflowState:
            workflow = None
        live_fingerprint = (
            implementation_snapshot_sha256(root, feature)
            if handoff.get("fingerprint_algorithm") == "git-working-tree-v1"
            else None
        )
        errors, fresh = _review_validation_errors(
            state,
            handoff,
            feature_dir=feature,
            handoff_digest=_sha256(handoff_file),
            live_fingerprint=live_fingerprint,
            workflow=workflow if isinstance(workflow, Mapping) else None,
        )
    except ReviewRuntimeError as exc:
        return {
            "valid": False,
            "fresh": False,
            "errors": [str(exc)],
            "state": None,
            "state_path": str(state_file),
            "current_fingerprint": None,
        }
    return {
        "valid": not errors,
        "fresh": fresh,
        "errors": errors,
        "state": state,
        "state_path": str(state_file),
        "current_fingerprint": live_fingerprint,
    }


def closeout_review(
    project_root: Path,
    feature_dir: Path | str,
    *,
    expected_revision: int,
) -> dict[str, Any]:
    """Validate approved review evidence and return the guarded stage-completion argv."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    _validate_workflow_owner(feature, expected_revision)
    state = _read_json_object(review_state_path(feature), label=REVIEW_STATE_FILENAME)
    if state.get("status") != "approved":
        raise ReviewRuntimeError("review status must be approved before closeout")
    validation = validate_review(root, feature)
    if not validation["valid"]:
        raise ReviewRuntimeError(
            "review closeout blocked: " + "; ".join(validation["errors"])
        )
    return envelope(
        "ok",
        "System review is approved and ready for workflow stage completion.",
        data={
            "status": "approved",
            "fresh": True,
            "state_path": str(review_state_path(feature)),
        },
        next_argv=[
            "specify",
            "workflow",
            "complete-stage",
            "--feature-dir",
            str(feature),
            "--expected-revision",
            str(expected_revision),
            "--format",
            "json",
        ],
    )


__all__ = [
    "IMPLEMENTATION_HANDOFF_FILENAME",
    "REVIEW_SCHEMA_REF",
    "REVIEW_STATE_FILENAME",
    "ReviewRuntimeError",
    "closeout_review",
    "build_implementation_handoff",
    "implementation_handoff_path",
    "implementation_snapshot_sha256",
    "prepare_review",
    "review_state_path",
    "validate_review",
]
