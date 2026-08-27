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
HUMAN_UI_REVIEWERS = {
    "human",
    "human_review",
    "human_reviewer",
    "manual",
    "manual_review",
    "manual_reviewer",
}
SMOOTHNESS_EVIDENCE_KINDS = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
}
SMOOTHNESS_PERFORMANCE_FIELDS = (
    "inp_ms",
    "long_task_ms",
    "cls",
    "animation_dropped_frame_pct",
    "bundle_delta_kb",
)
SOURCE_CONTINUITY_METRIC_FIELDS = (
    "source_discovery_coverage",
    "target_surface_reachability",
    "action_operability",
    "business_outcome_parity",
    "asset_fidelity",
)
SOURCE_CONTINUITY_ADAPTER_CAPABILITIES = {
    "surface-enumeration",
    "action-execution",
    "side-effect-observation",
    "asset-inspection",
    "visual-capture",
}
SOURCE_CONTINUITY_EVIDENCE_KINDS = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
}
SOURCE_CONTINUITY_ADAPTER_ACTIONS = {
    "enumerate-surfaces",
    "enumerate-actions",
    "enumerate-assets",
    "activate-action",
    "observe-side-effects",
    "capture-structure",
    "capture-visual",
    "capture-runtime",
    "prepare-isolated-test-data",
}
SOURCE_CONTINUITY_ADAPTER_CAPABILITY_ACTIONS = {
    "surface-enumeration": {"enumerate-surfaces", "capture-structure"},
    "action-execution": {
        "enumerate-actions",
        "activate-action",
        "capture-runtime",
    },
    "side-effect-observation": {"observe-side-effects", "capture-runtime"},
    "asset-inspection": {"enumerate-assets", "capture-visual"},
    "visual-capture": {"capture-visual"},
}
SOURCE_CONTINUITY_ADAPTER_CAPABILITY_EVIDENCE = {
    "surface-enumeration": "structure_snapshot",
    "action-execution": "runtime_diagnostics",
    "side-effect-observation": "runtime_diagnostics",
    "asset-inspection": "visual_capture",
    "visual-capture": "visual_capture",
}
SOURCE_CONTINUITY_ADAPTER_FIELDS = {
    "id",
    "version",
    "roles",
    "capabilities",
    "actions",
    "evidence_kinds",
    "execution_mode",
    "tool_ref",
    "write_policy",
    "network_policy",
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


def _source_continuity_coverage(value: object) -> dict[str, list[str]] | None:
    if not isinstance(value, dict):
        return None
    coverage = value.get("coverage")
    if not isinstance(coverage, dict):
        return None
    result: dict[str, list[str]] = {}
    for field in ("surface_ids", "interaction_ids", "component_ids"):
        ids = _exact_smoothness_ids(coverage.get(field))
        if ids is None:
            return None
        result[field] = ids
    return result


def _source_continuity_project_root(feature_dir: Path) -> Path:
    for candidate in (feature_dir, *feature_dir.parents):
        if candidate.name.lower() in {".specify", "specs"}:
            return candidate.parent
    return feature_dir.parent


def _source_continuity_contract_sha(value: dict[str, Any]) -> str:
    raw = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_continuity_write_scope(task: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for candidate in (task.get("write_scope"), (task.get("scope") or {}).get("write_scope") if isinstance(task.get("scope"), dict) else None):
        if isinstance(candidate, list):
            values.extend(
                item.strip()
                for item in candidate
                if isinstance(item, str) and item.strip()
            )
    return list(dict.fromkeys(values))


def _source_continuity_ignored_snapshot_dir(name: str) -> bool:
    normalized = name.strip().lower()
    return normalized in {
        ".git",
        ".specify",
        ".planning",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    } or normalized.startswith((".codex-", "pytest-", "test-tmp", "test-run-"))


def _source_continuity_target_snapshot(
    project_root: Path, declared: list[str]
) -> str | None:
    paths: set[Path] = set()
    try:
        if declared:
            for raw in declared:
                normalized = raw.replace("\\", "/").strip()
                if normalized.endswith("/**"):
                    normalized = normalized[:-3]
                elif normalized.endswith("/*"):
                    normalized = normalized[:-2]
                normalized = normalized.rstrip("/")
                first_segment = normalized.removeprefix("./").split("/", 1)[0].lower()
                if first_segment in {".specify", ".planning"}:
                    return None
                target = (project_root / Path(normalized)).resolve()
                target.relative_to(project_root.resolve())
                if target.is_dir():
                    paths.update(
                        path
                        for path in target.rglob("*")
                        if path.is_file()
                        and not any(
                            _source_continuity_ignored_snapshot_dir(part)
                            for part in path.relative_to(project_root).parts[:-1]
                        )
                    )
                else:
                    paths.add(target)
        else:
            for path in project_root.rglob("*"):
                relative = path.relative_to(project_root)
                if any(_source_continuity_ignored_snapshot_dir(part) for part in relative.parts[:-1]):
                    continue
                if path.is_file():
                    paths.add(path)
    except (OSError, ValueError):
        return None
    digest = hashlib.sha256()
    digest.update(b"source-continuity-target-snapshot-v1\n")
    for path in sorted(paths, key=lambda item: item.as_posix()):
        try:
            relative = path.relative_to(project_root).as_posix()
        except ValueError:
            return None
        digest.update(f"PATH\n{relative}\n".encode())
        try:
            digest.update(path.read_bytes())
        except FileNotFoundError:
            digest.update(b"MISSING\n")
            continue
        except OSError:
            return None
        digest.update(b"\n")
    return digest.hexdigest()


def _source_continuity_evidence_record_valid(
    project_root: Path, ref: str, adapter_id: str
) -> bool:
    normalized = ref.strip().replace("\\", "/")
    if not normalized.startswith(".specify/evidence/records/"):
        return False
    record_path = project_root / Path(normalized)
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if (
        not isinstance(record, dict)
        or record.get("schema_version") != "spec-kit-evidence-v1"
        or record.get("status") != "ready"
    ):
        return False
    digest = str(record.get("sha256") or "").strip()
    object_ref = str(record.get("object_ref") or "").strip().replace("\\", "/")
    if (
        not re.fullmatch(r"[0-9a-f]{64}", digest)
        or not object_ref.startswith(".specify/evidence/objects/sha256/")
        or not str(record.get("source") or "").strip()
        or record.get("provenance") != f"adapter:{adapter_id}"
    ):
        return False
    try:
        raw = (project_root / Path(object_ref)).read_bytes()
    except OSError:
        return False
    return (
        hashlib.sha256(raw).hexdigest() == digest
        and record.get("size") == len(raw)
        and record.get("record_ref") == normalized
    )


def _source_continuity_passing(value: object) -> bool:
    return str(value or "").strip().lower() in {
        "pass",
        "passed",
        "success",
        "matched",
        "approved",
    }


def _source_continuity_rows(value: object) -> list[dict[str, Any]] | None:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        return None
    return [dict(row) for row in value]


def _source_continuity_adapter_plan_errors(
    feature_dir: Path,
    task_id: str,
    continuity: dict[str, Any],
    report: dict[str, Any],
    manifest_ref: str,
    manifest_sha256: str,
    task_index_sha256: str,
    target_snapshot_sha256: str | None,
    adapter_plan_ref: str,
    adapter_plan_sha256: str,
) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    canonical_ref = (
        "implementation-review/source-continuity/"
        f"source-continuity-adapter-plan-{task_id}.json"
    )
    if (
        adapter_plan_ref != canonical_ref
        or report.get("adapter_plan_ref") != adapter_plan_ref
        or report.get("adapter_plan_sha256") != adapter_plan_sha256
        or not re.fullmatch(r"[0-9a-f]{64}", adapter_plan_sha256)
    ):
        errors.append("adapter-plan-binding-mismatch")
    plan_path = resolve_feature_artifact_ref(feature_dir, adapter_plan_ref)
    if plan_path is None:
        return [*errors, "adapter-plan-missing"], None
    try:
        plan_bytes = plan_path.read_bytes()
        plan = json.loads(plan_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [*errors, "adapter-plan-invalid-json"], None
    if hashlib.sha256(plan_bytes).hexdigest() != adapter_plan_sha256:
        errors.append("adapter-plan-sha256-mismatch")
    if not isinstance(plan, dict):
        return [*errors, "adapter-plan-invalid-object"], None
    if set(plan) != {
        "schema",
        "adapter_protocol",
        "plan_id",
        "subject_id",
        "status",
        "binding",
        "selection",
        "required_lanes",
        "adapters",
        "assignments",
        "unresolved_gaps",
    }:
        errors.append("adapter-plan-invalid-fields")
    if (
        plan.get("schema") != "spec-kit-source-continuity-adapter-plan-v1"
        or plan.get("adapter_protocol") != "spec-kit-source-continuity-adapter-v1"
        or not re.fullmatch(r"SCAP-[0-9a-f]{12}", str(plan.get("plan_id") or ""))
        or str(plan.get("subject_id") or "").strip().upper() != task_id
        or plan.get("status") != "ready"
        or plan.get("unresolved_gaps") != []
    ):
        errors.append("adapter-plan-invalid-identity")

    capabilities = sorted(SOURCE_CONTINUITY_ADAPTER_CAPABILITIES)
    required_lanes = {
        f"{side}.{capability}"
        for side in ("source", "target")
        for capability in capabilities
    }
    lanes = _exact_smoothness_ids(plan.get("required_lanes"))
    if lanes is None or set(lanes) != required_lanes:
        errors.append("adapter-plan-lane-coverage-mismatch")

    binding = plan.get("binding")
    if not isinstance(binding, dict) or set(binding) != {
        "mode",
        "subject_id",
        "manifest_ref",
        "manifest_sha256",
        "source_continuity_sha256",
        "target_snapshot_sha256",
        "task_index_sha256",
    }:
        errors.append("adapter-plan-invalid-binding")
    elif binding != {
        "mode": "formal",
        "subject_id": task_id,
        "manifest_ref": manifest_ref,
        "manifest_sha256": manifest_sha256,
        "source_continuity_sha256": _source_continuity_contract_sha(continuity),
        "target_snapshot_sha256": target_snapshot_sha256,
        "task_index_sha256": task_index_sha256,
    }:
        errors.append("adapter-plan-stale-binding")

    errors.extend(
        _source_continuity_adapter_selection_errors(
            feature_dir, task_id, plan, adapter_plan_sha256
        )
    )

    adapters = _source_continuity_rows(plan.get("adapters"))
    adapter_by_id: dict[str, dict[str, Any]] = {}
    if not adapters:
        errors.append("adapter-plan-requires-adapters")
        adapters = []
    for adapter in adapters:
        adapter_id = str(adapter.get("id") or "").strip()
        roles = _exact_smoothness_ids(adapter.get("roles"))
        adapter_capabilities = _exact_smoothness_ids(adapter.get("capabilities"))
        actions = _exact_smoothness_ids(adapter.get("actions"))
        evidence_kinds = _exact_smoothness_ids(adapter.get("evidence_kinds"))
        if set(adapter) != SOURCE_CONTINUITY_ADAPTER_FIELDS:
            errors.append(f"adapter-invalid-fields:{adapter_id}")
            continue
        if (
            not re.fullmatch(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*", adapter_id)
            or adapter_id in adapter_by_id
            or not str(adapter.get("version") or "").strip()
            or not re.fullmatch(
                r"[a-z][a-z0-9+.-]*://\S+", str(adapter.get("tool_ref") or "")
            )
        ):
            errors.append(f"adapter-invalid-identity:{adapter_id}")
        adapter_by_id[adapter_id] = adapter
        if roles is None or not roles or not set(roles) <= {"source", "target"}:
            errors.append(f"adapter-invalid-role:{adapter_id}")
        if (
            adapter_capabilities is None
            or not adapter_capabilities
            or not set(adapter_capabilities) <= SOURCE_CONTINUITY_ADAPTER_CAPABILITIES
        ):
            errors.append(f"adapter-invalid-capability:{adapter_id}")
        if actions is None or not set(actions) <= SOURCE_CONTINUITY_ADAPTER_ACTIONS:
            errors.append(f"adapter-unsupported-action:{adapter_id}")
        if (
            evidence_kinds is None
            or not set(evidence_kinds) <= SOURCE_CONTINUITY_EVIDENCE_KINDS
        ):
            errors.append(f"adapter-invalid-evidence-kind:{adapter_id}")
        if adapter.get("execution_mode") not in {
            "runtime-managed",
            "agent-tool",
            "app-connector",
            "external-runner",
            "manual-attested",
        }:
            errors.append(f"adapter-invalid-execution-mode:{adapter_id}")
        if adapter.get("write_policy") not in {
            "read-only",
            "evidence-store-only",
            "isolated-test-data",
        }:
            errors.append(f"adapter-invalid-write-policy:{adapter_id}")
        if adapter.get("network_policy") not in {"denied", "declared-read-only"}:
            errors.append(f"adapter-invalid-network-policy:{adapter_id}")
        if (
            adapter_capabilities is not None
            and actions is not None
            and evidence_kinds is not None
        ):
            for capability in adapter_capabilities:
                if capability not in SOURCE_CONTINUITY_ADAPTER_CAPABILITY_ACTIONS:
                    continue
                if (
                    not SOURCE_CONTINUITY_ADAPTER_CAPABILITY_ACTIONS[capability]
                    <= set(actions)
                    or SOURCE_CONTINUITY_ADAPTER_CAPABILITY_EVIDENCE[capability]
                    not in evidence_kinds
                ):
                    errors.append(
                        f"adapter-capability-contract-mismatch:{adapter_id}:{capability}"
                    )

    assignments = _source_continuity_rows(plan.get("assignments"))
    seen_lanes: set[str] = set()
    if assignments is None:
        errors.append("adapter-plan-requires-assignments")
        assignments = []
    for assignment in assignments:
        if set(assignment) != {
            "side",
            "capability",
            "adapter_id",
            "selection_reason",
        }:
            errors.append("adapter-plan-invalid-assignment")
            continue
        side = str(assignment.get("side") or "").strip()
        capability = str(assignment.get("capability") or "").strip()
        adapter_id = str(assignment.get("adapter_id") or "").strip()
        lane = f"{side}.{capability}"
        adapter = adapter_by_id.get(adapter_id, {})
        if lane in seen_lanes:
            errors.append(f"adapter-plan-duplicate-lane:{lane}")
        seen_lanes.add(lane)
        if (
            lane not in required_lanes
            or side not in (adapter.get("roles") or [])
            or capability not in (adapter.get("capabilities") or [])
        ):
            errors.append(f"adapter-plan-assignment-mismatch:{lane}")
        if not str(assignment.get("selection_reason") or "").strip():
            errors.append(f"adapter-plan-assignment-reason-missing:{lane}")
    if seen_lanes != required_lanes:
        errors.append("adapter-plan-lane-coverage-mismatch")
    return sorted(set(errors)), plan


def _source_continuity_adapter_selection_errors(
    feature_dir: Path,
    task_id: str,
    plan: dict[str, Any],
    adapter_plan_sha256: str,
) -> list[str]:
    selection = plan.get("selection")
    expected_fields = {
        "mode",
        "registry_schema",
        "registry_sha256",
        "probe_ref",
        "probe_sha256",
        "inventory_sha256",
    }
    if not isinstance(selection, dict) or set(selection) != expected_fields:
        return ["adapter-selection-invalid-fields"]
    mode = str(selection.get("mode") or "").strip()
    if mode == "explicit":
        if any(str(selection.get(field) or "").strip() for field in expected_fields - {"mode"}):
            return ["adapter-selection-invalid-explicit-binding"]
        return []
    if mode != "registry-probe":
        return ["adapter-selection-invalid-mode"]
    registry_sha256 = str(selection.get("registry_sha256") or "").strip()
    probe_ref = str(selection.get("probe_ref") or "").strip().replace("\\", "/")
    probe_sha256 = str(selection.get("probe_sha256") or "").strip()
    inventory_sha256 = str(selection.get("inventory_sha256") or "").strip()
    canonical_probe_ref = (
        "implementation-review/source-continuity/"
        f"source-continuity-adapter-probe-{task_id}.json"
    )
    if (
        selection.get("registry_schema")
        != "spec-kit-source-continuity-adapter-registry-v1"
        or not re.fullmatch(r"[0-9a-f]{64}", registry_sha256)
        or probe_ref != canonical_probe_ref
        or not re.fullmatch(r"[0-9a-f]{64}", probe_sha256)
        or not re.fullmatch(r"[0-9a-f]{64}", inventory_sha256)
    ):
        return ["adapter-selection-invalid-registry-binding"]
    probe_path = resolve_feature_artifact_ref(feature_dir, probe_ref)
    if probe_path is None:
        return ["adapter-probe-missing"]
    try:
        probe_bytes = probe_path.read_bytes()
        probe = json.loads(probe_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ["adapter-probe-invalid-json"]
    if hashlib.sha256(probe_bytes).hexdigest() != probe_sha256:
        return ["adapter-probe-sha256-mismatch"]
    if not isinstance(probe, dict) or set(probe) != {
        "schema",
        "subject_id",
        "status",
        "binding",
        "registry_schema",
        "registry_sha256",
        "inventory_sha256",
        "adapters",
        "assignments",
        "unavailable_bindings",
        "unselected_bindings",
        "unresolved_gaps",
    }:
        return ["adapter-probe-invalid-fields"]
    if (
        probe.get("schema") != "spec-kit-source-continuity-adapter-probe-v1"
        or str(probe.get("subject_id") or "").strip().upper() != task_id
        or probe.get("status") != "ready"
        or probe.get("binding") != plan.get("binding")
        or probe.get("registry_schema") != selection.get("registry_schema")
        or probe.get("registry_sha256") != registry_sha256
        or probe.get("inventory_sha256") != inventory_sha256
        or probe.get("adapters") != plan.get("adapters")
        or probe.get("assignments") != plan.get("assignments")
        or probe.get("unresolved_gaps") != []
    ):
        return ["adapter-probe-stale-binding"]
    if not adapter_plan_sha256:
        return ["adapter-plan-sha256-missing"]
    return []


def _source_continuity_lab_semantic_errors(
    feature_dir: Path,
    report: dict[str, Any],
    continuity: dict[str, Any],
    adapter_plan: dict[str, Any] | None,
    adapter_plan_sha256: str,
) -> list[str]:
    errors: list[str] = []
    adapter = report.get("adapter")
    expected_adapter = {
        "id": f"adapter-plan:{adapter_plan_sha256[:12]}",
        "version": "1",
        "capabilities": [
            "surface-enumeration",
            "action-execution",
            "side-effect-observation",
            "asset-inspection",
            "visual-capture",
        ],
    }
    if adapter != expected_adapter:
        errors.append("adapter-plan-composite-mismatch")

    adapter_by_id = {
        str(row.get("id") or "").strip(): row
        for row in _source_continuity_rows(
            adapter_plan.get("adapters") if isinstance(adapter_plan, dict) else None
        )
        or []
    }
    assignments = (
        _source_continuity_rows(
            adapter_plan.get("assignments") if isinstance(adapter_plan, dict) else None
        )
        or []
    )

    project_root = _source_continuity_project_root(feature_dir)
    evidence_rows = _source_continuity_rows(report.get("evidence_refs"))
    evidence_sides: dict[str, str] = {}
    evidence_bindings: dict[str, tuple[str, str, str]] = {}
    covered_evidence: set[tuple[str, str]] = set()
    observed_adapter_evidence: set[tuple[str, str, str]] = set()
    if evidence_rows is None:
        errors.append("invalid-evidence-refs")
        evidence_rows = []
    for row in evidence_rows:
        if set(row) != {"side", "kind", "ref", "adapter_id"}:
            errors.append("invalid-evidence-ref")
            continue
        side = str(row.get("side") or "").strip()
        kind = str(row.get("kind") or "").strip()
        ref = str(row.get("ref") or "").strip()
        adapter_id = str(row.get("adapter_id") or "").strip()
        assigned_adapter = adapter_by_id.get(adapter_id, {})
        if (
            side not in {"source", "target"}
            or kind not in SOURCE_CONTINUITY_EVIDENCE_KINDS
            or side not in (assigned_adapter.get("roles") or [])
            or kind not in (assigned_adapter.get("evidence_kinds") or [])
            or not _source_continuity_evidence_record_valid(
                project_root, ref, adapter_id
            )
        ):
            errors.append("evidence-adapter-assignment-mismatch")
            continue
        if ref in evidence_sides and evidence_sides[ref] != side:
            errors.append("evidence-ref-side-conflict")
        binding = (side, kind, adapter_id)
        if ref in evidence_bindings and evidence_bindings[ref] != binding:
            errors.append("evidence-ref-binding-conflict")
        evidence_sides[ref] = side
        evidence_bindings[ref] = binding
        covered_evidence.add((side, kind))
        observed_adapter_evidence.add((adapter_id, side, kind))
    for side in ("source", "target"):
        for kind in SOURCE_CONTINUITY_EVIDENCE_KINDS:
            if (side, kind) not in covered_evidence:
                errors.append(f"missing-{side}-{kind.replace('_', '-')}")
    for assignment in assignments:
        adapter_id = str(assignment.get("adapter_id") or "").strip()
        side = str(assignment.get("side") or "").strip()
        capability = str(assignment.get("capability") or "").strip()
        kind = SOURCE_CONTINUITY_ADAPTER_CAPABILITY_EVIDENCE.get(capability, "")
        if (adapter_id, side, kind) not in observed_adapter_evidence:
            errors.append(f"evidence-adapter-assignment-mismatch:{side}.{capability}")

    expected_binding_ids: dict[str, list[str]] = {}
    for field in ("surface_bindings", "action_bindings", "asset_bindings"):
        rows = _source_continuity_rows(continuity.get(field))
        ids = (
            [str(row.get("id") or "").strip() for row in rows]
            if rows is not None
            else []
        )
        if not ids or any(not item for item in ids) or len(ids) != len(set(ids)):
            errors.append(f"invalid-{field.replace('_', '-')}")
        expected_binding_ids[field] = ids

    discovery = report.get("discovery")
    if not isinstance(discovery, dict) or set(discovery) != {
        "surface_binding_ids",
        "action_binding_ids",
        "asset_binding_ids",
        "unexpected_candidates",
    }:
        errors.append("invalid-discovery")
    else:
        for field, binding_field in (
            ("surface_binding_ids", "surface_bindings"),
            ("action_binding_ids", "action_bindings"),
            ("asset_binding_ids", "asset_bindings"),
        ):
            values = _exact_smoothness_ids(discovery.get(field))
            if values is None or set(values) != set(expected_binding_ids[binding_field]):
                errors.append(f"{field.replace('_binding_ids', '')}-discovery-coverage-mismatch")
        unexpected = discovery.get("unexpected_candidates")
        if not isinstance(unexpected, list) or unexpected:
            errors.append("unbound-source-candidate")

    coverage = _source_continuity_coverage(continuity) or {
        "surface_ids": [],
        "interaction_ids": [],
        "component_ids": [],
    }
    surface_rows = _source_continuity_rows(report.get("surface_results"))
    surface_passed = 0
    surface_ids: list[str] = []
    if surface_rows is None:
        errors.append("invalid-surface-results")
        surface_rows = []
    for row in surface_rows:
        expected_fields = {
            "surface_id",
            "source_reachable",
            "target_reachable",
            "disposition_verified",
            "verdict",
        }
        if set(row) != expected_fields:
            errors.append("invalid-surface-result")
            continue
        surface_id = str(row.get("surface_id") or "").strip()
        surface_ids.append(surface_id)
        if (
            row.get("source_reachable") is True
            and row.get("target_reachable") is True
            and row.get("disposition_verified") is True
            and _source_continuity_passing(row.get("verdict"))
        ):
            surface_passed += 1
        else:
            errors.append("target-surface-unreachable")
    if len(surface_ids) != len(set(surface_ids)) or set(surface_ids) != set(
        coverage["surface_ids"]
    ):
        errors.append("surface-coverage-mismatch")

    action_bindings = {
        str(row.get("interaction_id") or "").strip(): row
        for row in _source_continuity_rows(continuity.get("action_bindings")) or []
    }
    action_rows = _source_continuity_rows(report.get("action_results"))
    action_passed = 0
    outcome_passed = 0
    action_ids: list[str] = []
    if action_rows is None:
        errors.append("invalid-action-results")
        action_rows = []
    for row in action_rows:
        expected_fields = {
            "interaction_id",
            "source_reachable",
            "target_reachable",
            "source_evidence_ref",
            "target_evidence_ref",
            "observed_side_effects",
            "business_outcome_verified",
            "final_state_verified",
            "verdict",
        }
        if set(row) != expected_fields:
            errors.append("invalid-action-result")
            continue
        interaction_id = str(row.get("interaction_id") or "").strip()
        action_ids.append(interaction_id)
        source_ref = str(row.get("source_evidence_ref") or "").strip()
        target_ref = str(row.get("target_evidence_ref") or "").strip()
        if evidence_sides.get(source_ref) != "source" or evidence_sides.get(target_ref) != "target":
            errors.append("action-evidence-unbound")
        elif (
            evidence_bindings[source_ref][1] != "runtime_diagnostics"
            or evidence_bindings[target_ref][1] != "runtime_diagnostics"
        ):
            errors.append("action-evidence-kind-mismatch")
        observed = _exact_smoothness_ids(row.get("observed_side_effects"))
        expected_effects = _exact_smoothness_ids(
            action_bindings.get(interaction_id, {}).get("side_effects")
        )
        if observed is None or expected_effects is None or set(observed) != set(
            expected_effects
        ):
            errors.append("side-effect-mismatch")
        if (
            row.get("source_reachable") is True
            and row.get("target_reachable") is True
            and _source_continuity_passing(row.get("verdict"))
        ):
            action_passed += 1
        else:
            errors.append("target-action-unreachable")
        if (
            row.get("business_outcome_verified") is True
            and row.get("final_state_verified") is True
        ):
            outcome_passed += 1
        else:
            errors.append("business-outcome-mismatch")
    if len(action_ids) != len(set(action_ids)) or set(action_ids) != set(
        coverage["interaction_ids"]
    ):
        errors.append("action-coverage-mismatch")

    asset_bindings = {
        str(row.get("component_id") or "").strip(): row
        for row in _source_continuity_rows(continuity.get("asset_bindings")) or []
    }
    asset_rows = _source_continuity_rows(report.get("asset_results"))
    asset_passed = 0
    asset_ids: list[str] = []
    if asset_rows is None:
        errors.append("invalid-asset-results")
        asset_rows = []
    for row in asset_rows:
        expected_fields = {
            "component_id",
            "source_evidence_ref",
            "target_evidence_ref",
            "semantic_match",
            "provenance_match",
            "render_match",
            "character_substitution",
            "verdict",
        }
        if set(row) != expected_fields:
            errors.append("invalid-asset-result")
            continue
        component_id = str(row.get("component_id") or "").strip()
        asset_ids.append(component_id)
        source_ref = str(row.get("source_evidence_ref") or "").strip()
        target_ref = str(row.get("target_evidence_ref") or "").strip()
        if evidence_sides.get(source_ref) != "source" or evidence_sides.get(target_ref) != "target":
            errors.append("asset-evidence-unbound")
        elif (
            evidence_bindings[source_ref][1] != "visual_capture"
            or evidence_bindings[target_ref][1] != "visual_capture"
        ):
            errors.append("asset-evidence-kind-mismatch")
        character_violation = (
            row.get("character_substitution") is True
            and asset_bindings.get(component_id, {}).get("placeholder_policy")
            == "forbid-character-substitution"
        )
        fidelity = all(
            row.get(field) is True
            for field in ("semantic_match", "provenance_match", "render_match")
        )
        if character_violation:
            errors.append("asset-character-substitution")
        if not fidelity:
            errors.append("asset-fidelity-mismatch")
        if fidelity and not character_violation and _source_continuity_passing(
            row.get("verdict")
        ):
            asset_passed += 1
    if len(asset_ids) != len(set(asset_ids)) or set(asset_ids) != set(
        coverage["component_ids"]
    ):
        errors.append("asset-coverage-mismatch")

    denominator = sum(len(values) for values in expected_binding_ids.values())
    discovery_covered = denominator if isinstance(discovery, dict) and not errors else 0

    def ratio(passed: int, total: int) -> float:
        return 1.0 if total == 0 else passed / total

    recomputed_metrics = {
        "source_discovery_coverage": ratio(discovery_covered, denominator),
        "target_surface_reachability": ratio(
            surface_passed, len(coverage["surface_ids"])
        ),
        "action_operability": ratio(action_passed, len(coverage["interaction_ids"])),
        "business_outcome_parity": ratio(
            outcome_passed, len(coverage["interaction_ids"])
        ),
        "asset_fidelity": ratio(asset_passed, len(coverage["component_ids"])),
    }
    if report.get("metrics") != recomputed_metrics:
        errors.append("metrics-mismatch")
    return sorted(set(errors))


def _validate_source_continuity_lab_report(
    feature_dir: Path,
    relative: str,
    task_id: str,
    source_continuity: dict[str, Any],
    report_ref: str,
    report_sha256: str,
    adapter_plan_ref: str,
    adapter_plan_sha256: str,
) -> list[str]:
    errors: list[str] = []
    report_path = resolve_feature_artifact_ref(feature_dir, report_ref)
    if report_path is None:
        return [f"{relative} source continuity lab report must exist inside the feature"]
    try:
        report_bytes = report_path.read_bytes()
        report = json.loads(report_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [f"{relative} source continuity lab report must contain a JSON object"]
    if hashlib.sha256(report_bytes).hexdigest() != report_sha256:
        errors.append(f"{relative} source continuity lab report SHA-256 must bind the report")
    if not isinstance(report, dict):
        errors.append(f"{relative} source continuity lab report must contain a JSON object")
        return errors

    expected_coverage = _source_continuity_coverage(source_continuity)
    report_coverage = _source_continuity_coverage({"coverage": report.get("coverage")})
    canonical_report_ref = (
        "implementation-review/source-continuity/"
        f"source-continuity-lab-{task_id}.json"
    )
    manifest_ref = str(report.get("manifest_ref") or "").strip()
    canonical_manifest_ref = (
        "implementation-review/source-continuity/"
        f"source-continuity-manifest-{task_id}.json"
    )
    manifest_sha256 = str(report.get("manifest_sha256") or "").strip()
    manifest_path = (
        resolve_feature_artifact_ref(feature_dir, manifest_ref)
        if manifest_ref
        else None
    )
    manifest: object = None
    manifest_bytes = b""
    if manifest_path is None:
        errors.append(f"{relative} source continuity lab manifest must exist inside the feature")
    else:
        try:
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            errors.append(f"{relative} source continuity lab manifest must contain a JSON object")
    if manifest_bytes and hashlib.sha256(manifest_bytes).hexdigest() != manifest_sha256:
        errors.append(f"{relative} source continuity lab manifest SHA-256 must bind the manifest")

    task_index_path = feature_dir / "task-index.json"
    try:
        task_index_bytes = task_index_path.read_bytes()
        task_index_sha256 = hashlib.sha256(task_index_bytes).hexdigest()
        task_index = json.loads(task_index_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        task_index_sha256 = ""
        task_index = None
    current_task = next(
        (
            item
            for item in (task_index or {}).get("tasks", [])
            if isinstance(item, dict)
            and str(item.get("id") or "").strip().upper() == task_id
        ),
        None,
    )
    project_root = _source_continuity_project_root(feature_dir)
    target_snapshot = (
        _source_continuity_target_snapshot(
            project_root, _source_continuity_write_scope(current_task)
        )
        if isinstance(current_task, dict)
        else None
    )
    manifest_source = manifest.get("source") if isinstance(manifest, dict) else None
    report_source = report.get("source")
    if (
        report.get("schema") != "spec-kit-source-continuity-lab-report-v1"
        or report_ref != canonical_report_ref
        or str(report.get("task_id") or "").strip().upper() != task_id
        or str(report.get("verdict") or "").strip().lower() != "passed"
        or expected_coverage is None
        or report_coverage != expected_coverage
        or not isinstance(manifest, dict)
        or manifest.get("schema")
        != "spec-kit-source-continuity-lab-manifest-v1"
        or str(manifest.get("task_id") or "").strip().upper() != task_id
        or manifest_ref != canonical_manifest_ref
        or manifest.get("source_continuity") != source_continuity
        or manifest.get("source_continuity_sha256")
        != _source_continuity_contract_sha(source_continuity)
        or not isinstance(manifest_source, dict)
        or manifest_source.get("task_index_ref") != "task-index.json"
        or manifest_source.get("task_index_sha256") != task_index_sha256
        or manifest_source.get("target_snapshot_sha256") != target_snapshot
        or not isinstance(report_source, dict)
        or report_source.get("result_schema")
        != "spec-kit-source-continuity-lab-result-v1"
        or report_source.get("task_index_sha256") != task_index_sha256
        or report_source.get("target_snapshot_sha256") != target_snapshot
    ):
        errors.append(
            f"{relative} source continuity lab report must preserve the canonical path, current task contract, target snapshot, and task-index digest"
        )
    metrics = report.get("metrics")
    if not isinstance(metrics, dict) or any(
        metrics.get(field) != 1 for field in SOURCE_CONTINUITY_METRIC_FIELDS
    ):
        errors.append(
            f"{relative} source continuity lab report metrics must all pass"
        )
    adapter_plan_errors, adapter_plan = _source_continuity_adapter_plan_errors(
        feature_dir,
        task_id,
        source_continuity,
        report,
        manifest_ref,
        manifest_sha256,
        task_index_sha256,
        target_snapshot,
        adapter_plan_ref,
        adapter_plan_sha256,
    )
    if adapter_plan_errors:
        errors.append(
            f"{relative} source continuity adapter plan is invalid: "
            + ", ".join(adapter_plan_errors)
        )
    semantic_errors = _source_continuity_lab_semantic_errors(
        feature_dir,
        report,
        source_continuity,
        adapter_plan,
        adapter_plan_sha256,
    )
    if semantic_errors:
        errors.append(
            f"{relative} source continuity lab report semantics are invalid: "
            + ", ".join(semantic_errors)
        )
    return errors


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


def _exact_smoothness_ids(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized = [
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    ]
    if len(normalized) != len(value) or len(normalized) != len(set(normalized)):
        return None
    return normalized


def _validate_smoothness_report(
    feature_dir: Path,
    relative: str,
    task_id: str,
    expected_ids: list[str],
    report_ref: str,
    report_sha256: str,
) -> list[str]:
    errors: list[str] = []
    expected_id_set = set(expected_ids)
    canonical_report_ref = (
        f"implementation-review/smoothness/smoothness-lab-{task_id}.json"
    )
    if report_ref != canonical_report_ref:
        errors.append(
            f"{relative} smoothness lab report must use the runtime-owned canonical task path"
        )
    report_path = resolve_feature_artifact_ref(feature_dir, report_ref)
    if report_path is None:
        errors.append(
            f"{relative} smoothness lab report must reference an existing feature artifact"
        )
        return errors
    try:
        report_bytes = report_path.read_bytes()
        report = json.loads(report_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(f"{relative} smoothness lab report must contain a JSON object")
        return errors
    if report_sha256 != hashlib.sha256(report_bytes).hexdigest():
        errors.append(f"{relative} smoothness lab report SHA-256 must bind the report")
    if not isinstance(report, dict):
        errors.append(f"{relative} smoothness lab report must contain a JSON object")
        return errors

    report_ids = _exact_smoothness_ids(
        report.get("covered_smoothness_acceptance_ids")
    )
    source = report.get("source")
    if (
        report.get("schema") != "spec-kit-smoothness-lab-report-v1"
        or str(report.get("task_id") or "").strip().upper() != task_id
        or str(report.get("verdict") or "").strip().lower() != "passed"
        or report_ids is None
        or set(report_ids) != expected_id_set
        or not isinstance(source, dict)
        or source.get("result_schema") != "spec-kit-smoothness-lab-result-v1"
    ):
        errors.append(
            f"{relative} smoothness lab report must pass for the exact task acceptance IDs"
        )

    canonical_manifest_ref = (
        f"implementation-review/smoothness/smoothness-manifest-{task_id}.json"
    )
    manifest_ref = str(report.get("manifest_ref") or "").strip()
    if manifest_ref != canonical_manifest_ref:
        errors.append(
            f"{relative} smoothness lab report must bind the runtime-owned task manifest"
        )
    manifest_path = resolve_feature_artifact_ref(feature_dir, manifest_ref)
    if manifest_path is None:
        errors.append(
            f"{relative} smoothness lab report manifest must reference an existing feature artifact"
        )
        return errors
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(
            f"{relative} smoothness lab report manifest must contain a JSON object"
        )
        return errors
    if str(report.get("manifest_sha256") or "").strip() != hashlib.sha256(
        manifest_bytes
    ).hexdigest():
        errors.append(
            f"{relative} smoothness lab report manifest SHA-256 must bind the manifest"
        )
    if not isinstance(manifest, dict):
        errors.append(
            f"{relative} smoothness lab report manifest must contain a JSON object"
        )
        return errors

    manifest_ids = _exact_smoothness_ids(
        manifest.get("smoothness_acceptance_ids")
    )
    manifest_source = manifest.get("source")
    entrypoint = manifest.get("entrypoint")
    task_index_path = feature_dir / "task-index.json"
    try:
        task_index_bytes = task_index_path.read_bytes()
        task_index_sha256 = hashlib.sha256(task_index_bytes).hexdigest()
        task_index = json.loads(task_index_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        task_index_sha256 = ""
        task_index = None
    expected_entrypoint: dict[str, Any] | None = None
    if isinstance(task_index, dict):
        tasks = task_index.get("tasks")
        task = next(
            (
                item
                for item in tasks or []
                if isinstance(item, dict)
                and str(item.get("id") or "").strip().upper() == task_id
            ),
            None,
        )
        ui_contract = task.get("ui_contract") if isinstance(task, dict) else None
        surface_entrypoint_ids = {
            str(item.get("entrypoint_id") or "").strip()
            for item in (
                ui_contract.get("surface_catalog", [])
                if isinstance(ui_contract, dict)
                else []
            )
            if isinstance(item, dict) and str(item.get("entrypoint_id") or "").strip()
        }
        official_entrypoints = {
            str(item.get("id") or "").strip(): item
            for item in task_index.get("official_entrypoints", [])
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        if len(surface_entrypoint_ids) == 1:
            official_entrypoint = official_entrypoints.get(
                next(iter(surface_entrypoint_ids))
            )
            if isinstance(official_entrypoint, dict):
                expected_entrypoint = {
                    field: str(official_entrypoint.get(field) or "")
                    for field in ("id", "kind", "route", "url")
                }
    if (
        manifest.get("schema") != "spec-kit-smoothness-lab-manifest-v1"
        or str(manifest.get("task_id") or "").strip().upper() != task_id
        or manifest_ids is None
        or set(manifest_ids) != expected_id_set
        or not isinstance(manifest_source, dict)
        or manifest_source.get("task_index_ref") != "task-index.json"
        or manifest_source.get("task_index_sha256") != task_index_sha256
        or not isinstance(entrypoint, dict)
        or not str(entrypoint.get("id") or "").strip()
        or expected_entrypoint is None
        or entrypoint != expected_entrypoint
    ):
        errors.append(
            f"{relative} smoothness lab report manifest is stale or does not bind the exact task"
        )

    required_evidence = _exact_smoothness_ids(manifest.get("required_evidence"))
    evidence_refs = report.get("evidence_refs")
    evidence_kinds = {
        str(item.get("kind") or "").strip()
        for item in evidence_refs or []
        if isinstance(item, dict) and str(item.get("ref") or "").strip()
    }
    if (
        required_evidence is None
        or not SMOOTHNESS_EVIDENCE_KINDS <= set(required_evidence)
        or not SMOOTHNESS_EVIDENCE_KINDS <= evidence_kinds
    ):
        errors.append(
            f"{relative} smoothness lab report must bind structure, visual, and runtime evidence"
        )

    scenario_results = report.get("scenario_results")
    scenario_ids = [
        str(item.get("smoothness_acceptance_id") or "").strip()
        for item in scenario_results or []
        if isinstance(item, dict)
        and str(item.get("smoothness_acceptance_id") or "").strip()
        and str(item.get("verdict") or "").strip().lower()
        in PASSING_VISUAL_STATUSES
    ]
    if (
        not isinstance(scenario_results, list)
        or len(scenario_ids) != len(scenario_results)
        or len(scenario_ids) != len(set(scenario_ids))
        or set(scenario_ids) != expected_id_set
    ):
        errors.append(
            f"{relative} smoothness lab report must contain one passing scenario result per acceptance ID"
        )

    performance = report.get("performance")
    budgets = manifest.get("performance_budgets")
    if not isinstance(performance, dict) or not isinstance(budgets, dict):
        errors.append(
            f"{relative} smoothness lab report must contain task-bound performance measurements"
        )
    else:
        for field in SMOOTHNESS_PERFORMANCE_FIELDS:
            measured = performance.get(field)
            budget = budgets.get(field)
            if (
                isinstance(measured, bool)
                or not isinstance(measured, (int, float))
                or measured < 0
                or isinstance(budget, bool)
                or not isinstance(budget, (int, float))
                or budget < 0
                or measured > budget
            ):
                errors.append(
                    f"{relative} smoothness lab report performance.{field} must satisfy the task-bound budget"
                )
    return errors


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
    usability_validation = ui_contract.get("usability_validation")
    usability_validation = (
        usability_validation if isinstance(usability_validation, dict) else {}
    )
    expected_smoothness_list = _exact_smoothness_ids(
        usability_validation.get("smoothness_acceptance_ids", [])
    )
    expected_smoothness_list = expected_smoothness_list or []
    expected_smoothness_ids = set(expected_smoothness_list)
    if expected_smoothness_ids:
        covered_smoothness_list = _exact_smoothness_ids(
            verification.get("covered_smoothness_acceptance_ids", [])
        )
        if (
            covered_smoothness_list is None
            or set(covered_smoothness_list) != expected_smoothness_ids
        ):
            errors.append(
                f"{relative} ui_verification.covered_smoothness_acceptance_ids must exactly cover the task contract"
            )
        smoothness_report_ref = str(
            verification.get("smoothness_lab_report_ref") or ""
        ).strip()
        smoothness_report_sha256 = str(
            verification.get("smoothness_lab_report_sha256") or ""
        ).strip()
        if not smoothness_report_ref or not re.fullmatch(
            r"[0-9a-f]{64}", smoothness_report_sha256
        ):
            errors.append(
                f"{relative} smoothness lab report ref and SHA-256 digest are required"
            )
        else:
            errors.extend(
                _validate_smoothness_report(
                    feature_dir,
                    relative,
                    task_id,
                    expected_smoothness_list,
                    smoothness_report_ref,
                    smoothness_report_sha256,
                )
            )
    source_continuity = ui_contract.get("source_continuity")
    if (
        isinstance(source_continuity, dict)
        and source_continuity.get("applicability") == "required"
    ):
        expected_coverage = _source_continuity_coverage(source_continuity)
        if expected_coverage is None:
            errors.append(
                f"{relative} source continuity coverage must use exact ID arrays"
            )
        else:
            for field, verification_field, label in (
                (
                    "surface_ids",
                    "covered_source_continuity_surface_ids",
                    "surface",
                ),
                (
                    "interaction_ids",
                    "covered_source_continuity_interaction_ids",
                    "interaction",
                ),
                (
                    "component_ids",
                    "covered_source_continuity_component_ids",
                    "component",
                ),
            ):
                covered = _exact_smoothness_ids(
                    verification.get(verification_field, [])
                )
                if covered is None or set(covered) != set(expected_coverage[field]):
                    errors.append(
                        f"{relative} source continuity {label} coverage must exactly cover the task contract"
                    )
            report_ref = str(
                verification.get("source_continuity_lab_report_ref") or ""
            ).strip()
            report_sha256 = str(
                verification.get("source_continuity_lab_report_sha256") or ""
            ).strip()
            adapter_plan_ref = str(
                verification.get("source_continuity_adapter_plan_ref") or ""
            ).strip()
            adapter_plan_sha256 = str(
                verification.get("source_continuity_adapter_plan_sha256") or ""
            ).strip()
            if not report_ref or not re.fullmatch(r"[0-9a-f]{64}", report_sha256):
                errors.append(
                    f"{relative} source continuity lab report ref and SHA-256 digest are required"
                )
            else:
                if not adapter_plan_ref or not re.fullmatch(
                    r"[0-9a-f]{64}", adapter_plan_sha256
                ):
                    errors.append(
                        f"{relative} source continuity adapter plan ref and SHA-256 digest are required"
                    )
                errors.extend(
                    _validate_source_continuity_lab_report(
                        feature_dir,
                        relative,
                        task_id,
                        source_continuity,
                        report_ref,
                        report_sha256,
                        adapter_plan_ref,
                        adapter_plan_sha256,
                    )
                )
    if usability_validation.get("human_review_required") is True:
        reviewer = (
            str(verification.get("reviewer") or "")
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if reviewer not in HUMAN_UI_REVIEWERS:
            errors.append(
                f"{relative} human usability validation requires a human reviewer"
            )
        human_review_ref = str(verification.get("human_review_ref") or "").strip()
        human_review_path = (
            resolve_feature_artifact_ref(feature_dir, human_review_ref)
            if human_review_ref
            else None
        )
        if human_review_path is None:
            errors.append(
                f"{relative} ui_verification.human_review_ref must reference an existing artifact"
            )
        else:
            try:
                human_review_size = human_review_path.stat().st_size
            except OSError:
                human_review_size = 0
            if human_review_size == 0:
                errors.append(
                    f"{relative} ui_verification.human_review_ref artifact must be non-empty"
                )
    design_decision_ids = {
        str(item).strip()
        for item in ui_contract.get("design_decision_ids", [])
        if isinstance(item, str) and item.strip()
    }
    handoff_contract_ids = {
        str(item).strip()
        for item in ui_contract.get("handoff_contract_ids", [])
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
            "approved_handoff_ref",
            "approved_handoff_sha256",
        ):
            if str(verification.get(field) or "").strip() != str(
                ui_contract.get(field) or ""
            ).strip():
                errors.append(
                    f"{relative} ui_verification.{field} must preserve the task contract"
                )
        if verification.get("comparison_tolerance") != ui_contract.get(
            "comparison_tolerance"
        ):
            errors.append(
                f"{relative} ui_verification.comparison_tolerance must preserve the task contract"
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
        covered_handoff_contract_ids = {
            str(item).strip()
            for item in verification.get("covered_handoff_contract_ids", [])
            if isinstance(item, str) and item.strip()
        }
        if covered_handoff_contract_ids != handoff_contract_ids:
            errors.append(
                f"{relative} ui_verification.covered_handoff_contract_ids must exactly cover the task contract"
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
                    ("handoff_ref", "approved_handoff_ref"),
                    ("handoff_sha256", "approved_handoff_sha256"),
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
                report_handoff_contract_ids = {
                    str(item).strip()
                    for item in approved.get("handoff_contract_ids", [])
                    if isinstance(item, str) and item.strip()
                }
                if report_handoff_contract_ids != handoff_contract_ids:
                    errors.append(
                        f"{relative} comparison report approved.handoff_contract_ids must exactly cover the task contract"
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
                matrix_handoff_contract_ids: set[str] = set()
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
                    row_handoff_contracts = {
                        str(value).strip()
                        for value in item.get("covered_handoff_contract_ids", [])
                        if isinstance(value, str) and value.strip()
                    }
                    matrix_handoff_contract_ids.update(row_handoff_contracts)
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
                if matrix_handoff_contract_ids != handoff_contract_ids:
                    errors.append(
                        f"{relative} comparison report matrix must exactly cover task handoff contracts"
                    )
                if comparison_report.get("comparison_tolerance") != ui_contract.get(
                    "comparison_tolerance"
                ):
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
