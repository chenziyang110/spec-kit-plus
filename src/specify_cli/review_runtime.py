"""Deterministic state and closeout gates for post-implementation review."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .agent_api import envelope
from .atomic_io import atomic_write_text, interprocess_lock, read_local_state_bytes
from .workflow_runtime import show_workflow


REVIEW_STATE_FILENAME = "review-state.json"
IMPLEMENTATION_HANDOFF_FILENAME = "implementation-handoff.json"
REVIEW_SCHEMA_REF = ".specify/templates/review-state-schema.json"
REVIEW_STATE_VERSION = 2
REVIEW_STATUSES = frozenset(
    {"gathering", "reviewing", "repairing", "validating", "approved", "blocked", "stale"}
)
SCENARIO_RESULTS = frozenset({"pending", "pass", "fail", "blocked", "not_run"})
FINDING_STATUSES = frozenset(
    {"open", "repairing", "fixed", "verified", "accepted_residual_risk"}
)
EVIDENCE_KINDS = frozenset(
    {"structure_snapshot", "visual_capture", "runtime_diagnostics", "invocation", "side_effect"}
)


class ReviewRuntimeError(ValueError):
    """Raised when system review state cannot safely prepare or close."""


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
        raise ReviewRuntimeError("feature_dir must identify a directory below project_root")
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
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def implementation_snapshot_sha256(project_root: Path, feature_dir: Path | str) -> str:
    """Hash the live Git implementation while excluding review-owned evidence."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    root = _nearest_project_root(feature, root)
    try:
        feature_prefix = feature.relative_to(root).as_posix().rstrip("/") + "/"
    except ValueError as exc:  # pragma: no cover - guarded by _resolve_feature_dir
        raise ReviewRuntimeError("feature_dir must stay inside project_root") from exc
    excluded_names = {
        IMPLEMENTATION_HANDOFF_FILENAME,
        REVIEW_STATE_FILENAME,
        "implementation-summary.md",
        "human-acceptance.json",
    }

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
                if suffix in excluded_names or suffix.startswith(
                    ("review-evidence/", "review-results/")
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
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ignored_tree_names.intersection(path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(feature_prefix):
            suffix = relative[len(feature_prefix) :]
            if suffix in excluded_names or suffix.startswith(
                ("review-evidence/", "review-results/")
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
    task_index_path = feature / "task-index.json"
    task_index = (
        _read_json_object(task_index_path, label="task-index.json")
        if task_index_path.is_file()
        else {}
    )
    raw_entrypoints = task_index.get("official_entrypoints")
    raw_scenarios = task_index.get("system_review_scenarios")
    raw_obligations = task_index.get("review_obligations")
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
    payload: dict[str, Any] = {
        "version": 1,
        "source_revision": source_revision,
        "implementation_fingerprint": implementation_snapshot_sha256(root, feature),
        "fingerprint_algorithm": "git-working-tree-v1",
        "official_entrypoints": entrypoints,
        "system_review_scenarios": scenarios,
        "review_obligations": obligations,
    }
    _normalized_handoff(payload, expected_revision=source_revision)
    output_path = implementation_handoff_path(feature)
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
    }


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
        evidence_items = consumer_evidence if isinstance(consumer_evidence, list) else []
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
            expected_result = "The recorded verification entrypoint passes from a clean invocation."
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
                "title": str(result.get("summary") or f"Review {task_id} from the real entrypoint"),
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


def _validate_workflow_owner(feature_dir: Path, expected_revision: int) -> None:
    workflow = show_workflow(feature_dir)["data"]
    if workflow.get("stage") != "review" or workflow.get("status") != "active":
        raise ReviewRuntimeError(
            "system review requires workflow stage review with active status"
        )
    if workflow.get("revision") != expected_revision:
        raise ReviewRuntimeError(
            "system review workflow revision is stale; refresh workflow show before retrying"
        )


def _normalized_handoff(
    handoff: Mapping[str, Any], *, expected_revision: int
) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    if handoff.get("version") != 1:
        raise ReviewRuntimeError("implementation-handoff.json version must equal 1")
    if handoff.get("source_revision") != expected_revision:
        raise ReviewRuntimeError(
            "implementation handoff source_revision does not match the active review revision"
        )
    fingerprint = _required_text(
        handoff.get("implementation_fingerprint"),
        "implementation_fingerprint",
    )
    if len(fingerprint) != 64 or any(char not in "0123456789abcdef" for char in fingerprint.lower()):
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
        entrypoint_id = _required_text(item.get("id"), f"official_entrypoints[{index}].id")
        _required_text(item.get("command"), f"official_entrypoints[{index}].command")
        _required_text(
            item.get("ready_signal"), f"official_entrypoints[{index}].ready_signal"
        )
        if entrypoint_id in entrypoint_ids:
            raise ReviewRuntimeError(f"duplicate official entrypoint id: {entrypoint_id}")
        entrypoint_ids.add(entrypoint_id)
        entrypoints.append(item)

    raw_scenarios = handoff.get("system_review_scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ReviewRuntimeError("at least one system_review_scenario is required")
    scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for index, raw in enumerate(raw_scenarios):
        if not isinstance(raw, Mapping):
            raise ReviewRuntimeError(f"system_review_scenarios[{index}] must be an object")
        item = dict(raw)
        scenario_id = _required_text(item.get("id"), f"system_review_scenarios[{index}].id")
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
            raise ReviewRuntimeError(f"duplicate system review scenario id: {scenario_id}")
        scenario_ids.add(scenario_id)
        for field in ("actions", "expected_results", "required_evidence"):
            values = item.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise ReviewRuntimeError(f"scenario {scenario_id} requires non-empty {field}")
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
        obligation_id = _required_text(item.get("id"), f"review_obligations[{index}].id")
        _required_text(item.get("kind"), f"review_obligations[{index}].kind")
        _required_text(item.get("source_ref"), f"review_obligations[{index}].source_ref")
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
            str(value) for value in referenced_scenarios if str(value) not in scenario_ids
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
    return fingerprint, entrypoints, scenarios, obligations


def prepare_review(
    project_root: Path,
    feature_dir: Path | str,
    *,
    expected_revision: int,
) -> dict[str, Any]:
    """Create or resume the system review state from a trusted implementation handoff."""

    root = project_root.resolve(strict=False)
    feature = _resolve_feature_dir(root, feature_dir)
    _validate_workflow_owner(feature, expected_revision)
    handoff_file = implementation_handoff_path(feature)
    handoff = _read_json_object(handoff_file, label=IMPLEMENTATION_HANDOFF_FILENAME)
    fingerprint, entrypoints, scenarios, obligations = _normalized_handoff(
        handoff, expected_revision=expected_revision
    )
    handoff_digest = _sha256(handoff_file)
    state_file = review_state_path(feature)

    with interprocess_lock(feature / ".review-state.lock"):
        if state_file.is_file():
            existing = _read_json_object(state_file, label=REVIEW_STATE_FILENAME)
            source = existing.get("source")
            if isinstance(source, Mapping) and source.get(
                "implementation_handoff_sha256"
            ) == handoff_digest:
                return envelope(
                    "ok",
                    "System review state is already prepared.",
                    data=existing,
                )
            raise ReviewRuntimeError(
                "existing review state is stale; preserve its evidence and explicitly restart review"
            )

        (feature / "review-evidence").mkdir(parents=True, exist_ok=True)
        (feature / "review-results").mkdir(parents=True, exist_ok=True)
        state: dict[str, Any] = {
            "version": REVIEW_STATE_VERSION,
            "schema_ref": REVIEW_SCHEMA_REF,
            "status": "reviewing",
            "source": {
                "workflow_revision": expected_revision,
                "implementation_fingerprint": fingerprint,
                "implementation_handoff_sha256": handoff_digest,
            },
            "entrypoints": entrypoints,
            "scenarios": scenarios,
            "obligations": obligations,
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
            "rounds": [],
            "findings": [],
            "repair_cycles": [],
            "validation": {
                "startup": "pending",
                "real_entrypoint_journeys": "pending",
                "regression": "pending",
                "ui_verification": "pending",
            },
            "cursor": {
                "scenario_id": scenarios[0]["id"] if scenarios else None,
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
            },
        }
        atomic_write_text(state_file, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
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
    return {
        key: value.get(key)
        for key in ("id", "command", "ready_signal")
    }


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
    if not str(value or "").strip() or candidate.is_absolute():
        return False
    resolved = (feature_dir / candidate).resolve(strict=False)
    try:
        resolved.relative_to(feature_dir.resolve(strict=False))
    except ValueError:
        return False
    return True


def _path_within_any(relative: str, allowed: list[str]) -> bool:
    candidate = relative.replace("\\", "/").strip("/")
    return any(
        candidate == root.replace("\\", "/").strip("/")
        or candidate.startswith(root.replace("\\", "/").strip("/") + "/")
        for root in allowed
        if root.strip("/\\")
    )


def _review_validation_errors(
    state: Mapping[str, Any],
    handoff: Mapping[str, Any],
    *,
    feature_dir: Path,
    handoff_digest: str,
    live_fingerprint: str | None,
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
    if not fresh:
        errors.append("review state source metadata is missing")
    else:
        fresh = (
            source.get("implementation_handoff_sha256") == handoff_digest
            and source.get("implementation_fingerprint")
            == handoff.get("implementation_fingerprint")
        )
        if not fresh:
            errors.append(
                "review evidence is stale because the implementation handoff changed"
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
        expected_revision = int(handoff.get("source_revision"))
        _, canonical_entrypoints, canonical_scenarios, canonical_obligations = (
            _normalized_handoff(handoff, expected_revision=expected_revision)
        )
    except (ReviewRuntimeError, TypeError, ValueError) as exc:
        errors.append(f"invalid canonical review contract: {exc}")
        canonical_entrypoints = []
        canonical_scenarios = []
        canonical_obligations = []

    actual_entrypoints = _indexed_objects(state.get("entrypoints"))
    for duplicate in sorted(_duplicate_ids(state.get("entrypoints"))):
        errors.append(f"duplicate review entrypoint id: {duplicate}")
    for canonical in canonical_entrypoints:
        actual = actual_entrypoints.get(str(canonical["id"]))
        if actual is None or _entrypoint_contract(actual) != _entrypoint_contract(canonical):
            errors.append(
                f"canonical entrypoint contract drift for {canonical['id']}"
            )

    actual_scenarios = _indexed_objects(state.get("scenarios"))
    for duplicate in sorted(_duplicate_ids(state.get("scenarios"))):
        errors.append(f"duplicate review scenario id: {duplicate}")
    for canonical in canonical_scenarios:
        actual = actual_scenarios.get(str(canonical["id"]))
        if actual is None or _scenario_contract(actual) != _scenario_contract(canonical):
            errors.append(f"canonical scenario contract drift for {canonical['id']}")

    actual_obligations = _indexed_objects(state.get("obligations"))
    for duplicate in sorted(_duplicate_ids(state.get("obligations"))):
        errors.append(f"duplicate review obligation id: {duplicate}")
    for canonical in canonical_obligations:
        actual = actual_obligations.get(str(canonical["id"]))
        if actual is None or _obligation_contract(actual) != _obligation_contract(canonical):
            errors.append(f"canonical review obligation drift for {canonical['id']}")

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
            errors.append(f"scenario {scenario_id} has unsupported result {result or 'missing'}")
            continue
        if bool(raw.get("required", True)) and result != "pass":
            errors.append(f"required scenario {scenario_id} must pass before review closeout")
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
            errors.append(f"Review assignment {assignment_id} requires a subagent worker_id")
        packet_ref = assignment.get("packet_ref")
        result_ref = assignment.get("result_ref")
        if not _safe_feature_ref(feature_dir, packet_ref) or not _safe_feature_ref(
            feature_dir, result_ref
        ):
            errors.append(f"Review assignment {assignment_id} requires packet and result refs")
        elif assignment.get("status") == "accepted":
            for label, artifact_ref in (("packet", packet_ref), ("result", result_ref)):
                artifact_path = (feature_dir / Path(str(artifact_ref))).resolve(strict=False)
                if not artifact_path.is_file():
                    errors.append(
                        f"Review assignment {assignment_id} {label} file does not exist: "
                        f"{artifact_ref}"
                    )
        if assignment.get("status") == "accepted" and str(
            assignment.get("observed_snapshot_sha256") or ""
        ) != expected_snapshot:
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
            str(actual_scenarios.get(str(scenario_id), {}).get("result") or "") == "pass"
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
    for raw in findings:
        if not isinstance(raw, Mapping):
            errors.append("review finding must be an object")
            continue
        finding_id = str(raw.get("id") or "missing-finding")
        finding_status = str(raw.get("status") or "")
        if finding_status not in FINDING_STATUSES:
            errors.append(
                f"finding {finding_id} has unsupported status {finding_status or 'missing'}"
            )
        elif finding_status not in {"verified", "accepted_residual_risk"}:
            errors.append(f"finding {finding_id} must be verified before review closeout")

        blocking = bool(raw.get("blocking", True))
        if finding_status == "accepted_residual_risk" and blocking:
            errors.append(f"blocking finding {finding_id} cannot be accepted as residual risk")

        discovering_assignment_id = str(
            raw.get("discovered_by_review_assignment_id") or ""
        )
        discovering_worker = review_workers.get(discovering_assignment_id, "")
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
                and _safe_feature_ref(feature_dir, fix_assignment.get("packet_ref"))
                and _safe_feature_ref(feature_dir, fix_assignment.get("result_ref"))
            )
            if valid_fix:
                for label, artifact_ref in (
                    ("packet", fix_assignment.get("packet_ref")),
                    ("result", fix_assignment.get("result_ref")),
                ):
                    artifact_path = (
                        feature_dir / Path(str(artifact_ref))
                    ).resolve(strict=False)
                    if not artifact_path.is_file():
                        errors.append(
                            f"Fix assignment {fix_assignment_id} {label} file does not exist: "
                            f"{artifact_ref}"
                        )
                        valid_fix = False
        if not valid_fix:
            errors.append(
                f"finding {finding_id} requires an independent Fix assignment accepted by the Leader"
            )

        revalidation_ids = raw.get("revalidation_ids")
        revalidation_ids = revalidation_ids if isinstance(revalidation_ids, list) else []
        valid_revalidation = False
        for revalidation_id in revalidation_ids:
            revalidation = revalidations.get(str(revalidation_id))
            if revalidation is None or fix_assignment is None:
                continue
            revalidation_worker = str(revalidation.get("worker_id") or "")
            evidence_refs = revalidation.get("evidence_refs")
            evidence_refs = evidence_refs if isinstance(evidence_refs, list) else []
            evidence_refs_exist = True
            for evidence_ref in evidence_refs:
                candidate = Path(str(evidence_ref))
                resolved = (feature_dir / candidate).resolve(strict=False)
                try:
                    resolved.relative_to(feature_dir.resolve(strict=False))
                except ValueError:
                    evidence_refs_exist = False
                    break
                if candidate.is_absolute() or not resolved.is_file():
                    evidence_refs_exist = False
                    break
            valid_revalidation = (
                revalidation.get("result") == "pass"
                and revalidation.get("leader_verdict") == "accepted"
                and finding_id in (revalidation.get("finding_ids") or [])
                and fix_assignment_id
                in (revalidation.get("fix_assignment_ids") or [])
                and str(raw.get("scenario_id") or "")
                in (revalidation.get("scenario_ids") or [])
                and revalidation_worker
                not in {discovering_worker, str(fix_assignment.get("worker_id") or "")}
                and str(revalidation.get("snapshot_sha256") or "")
                == expected_snapshot
                and bool(evidence_refs)
                and evidence_refs_exist
            )
            if valid_revalidation:
                break
        if not valid_revalidation:
            errors.append(
                f"finding {finding_id} requires independent revalidation accepted by the Leader"
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
        raise ReviewRuntimeError("review closeout blocked: " + "; ".join(validation["errors"]))
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
