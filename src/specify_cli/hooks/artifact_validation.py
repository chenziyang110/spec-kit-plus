"""Validation hooks for workflow artifact completeness."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .checkpoint_serializers import extract_field, normalize_command_name
from .events import WORKFLOW_ARTIFACTS_VALIDATE
from .types import HookResult, QualityHookError

FILE_REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": (
        "spec.md",
        "alignment.md",
        "context.md",
        "specify-draft.md",
        "workflow-state.md",
        "brainstorming/facts.json",
        "brainstorming/route.json",
        "brainstorming/intent.json",
        "brainstorming/complexity.json",
        "brainstorming/handoff-to-specify.json",
    ),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": ("plan.md", "workflow-state.md"),
    "tasks": ("tasks.md", "workflow-state.md"),
    "analyze": ("workflow-state.md",),
    "map-scan": (
        "status.json",
        "coverage.json",
        "provisional/nodes.json",
        "provisional/edges.json",
        "provisional/observations.json",
    ),
    "map-build": (
        "status.json",
        "project-cognition.db",
    ),
    "map-update": (
        "status.json",
        "project-cognition.db",
    ),
    "prd-scan": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
    ),
    "prd-build": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "master/master-pack.md",
        "exports/README.md",
        "exports/prd.md",
        "exports/reconstruction-appendix.md",
        "exports/data-model.md",
        "exports/integration-contracts.md",
        "exports/runtime-behaviors.md",
    ),
    "prd": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
    ),
}

DIRECTORY_REQUIRED_ARTIFACTS = {
    "map-scan": ("evidence",),
    "prd-scan": ("scan-packets", "evidence", "worker-results"),
    "prd-build": ("scan-packets", "evidence", "worker-results"),
    "prd": ("scan-packets", "evidence", "worker-results"),
}


REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": (
        "spec.md",
        "alignment.md",
        "context.md",
        "specify-draft.md",
        "workflow-state.md",
        "brainstorming/facts.json",
        "brainstorming/route.json",
        "brainstorming/intent.json",
        "brainstorming/complexity.json",
        "brainstorming/handoff-to-specify.json",
    ),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": ("plan.md", "workflow-state.md"),
    "tasks": ("tasks.md", "workflow-state.md"),
    "analyze": ("workflow-state.md",),
    "map-scan": (
        "status.json",
        "coverage.json",
        "provisional/nodes.json",
        "provisional/edges.json",
        "provisional/observations.json",
        "evidence",
    ),
    "map-build": (
        "status.json",
        "project-cognition.db",
    ),
    "map-update": (
        "status.json",
        "project-cognition.db",
    ),
    "prd-scan": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "scan-packets",
        "evidence",
        "worker-results",
    ),
    "prd-build": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "scan-packets",
        "evidence",
        "worker-results",
        "master/master-pack.md",
        "exports/README.md",
        "exports/prd.md",
    ),
    "prd": (
        "workflow-state.md",
        "prd-scan.md",
        "coverage-ledger.md",
        "coverage-ledger.json",
        "capability-ledger.json",
        "artifact-contracts.json",
        "reconstruction-checklist.json",
        "scan-packets",
        "evidence",
        "worker-results",
    ),
}

DEEP_RESEARCH_REQUIRED_SECTIONS = (
    "## Planning Handoff",
    "## Evidence Quality Rubric",
    "## Planning Traceability Index",
)

DEEP_RESEARCH_HANDOFF_FIELDS = (
    "**Handoff IDs**",
    "**Recommended approach**",
    "**Architecture implications**",
    "**Module boundaries**",
    "**API / library choices**",
    "**Data flow notes**",
    "**Demo artifacts to reference**",
    "**Constraints `/sp.plan` must preserve**",
    "**Validation implications**",
    "**Residual risks requiring design mitigation**",
    "**Decisions already proven by research**",
)

PLAN_DEEP_RESEARCH_TRACEABILITY_COLUMNS = (
    "Plan Decision",
    "Handoff ID",
    "Evidence / Spike ID",
    "Evidence Quality",
    "Plan Action",
)

DEEP_RESEARCH_NOT_NEEDED_REQUIRED_SECTIONS = (
    "## Feasibility Decision",
    "## Planning Handoff",
    "## Next Command",
)

SPECIFY_DRAFT_REQUIRED_HEADINGS = (
    "## Intent Analysis Record",
    "## Domain Progress Ledger",
    "## Question Batch Ledger",
    "## Adversarial Review Ledger",
    "## Completeness Gap Register",
    "## Final Audit Inputs",
)

SPECIFY_ALIGNMENT_REQUIRED_HEADINGS = ("## Alignment Summary",)

SPECIFY_CONTEXT_REQUIRED_HEADINGS = ("## Change Propagation Matrix",)

PRD_BUILD_REQUIRED_EXPORTS = (
    "exports/README.md",
    "exports/reconstruction-appendix.md",
    "exports/data-model.md",
    "exports/integration-contracts.md",
    "exports/runtime-behaviors.md",
)

PRD_BUILD_REQUIRED_HEAVY_EXPORTS = (
    "exports/config-contracts.md",
    "exports/protocol-contracts.md",
    "exports/state-machines.md",
    "exports/error-semantics.md",
    "exports/verification-surface.md",
    "exports/reconstruction-risks.md",
)

PRD_HEAVY_SCAN_JSON_ARTIFACTS = {
    "entrypoint-ledger.json": "entrypoints",
    "config-contracts.json": "configs",
    "protocol-contracts.json": "protocols",
    "state-machines.json": "machines",
    "error-semantics.json": "errors",
    "verification-surfaces.json": "surfaces",
}

PRD_WORKER_RESULT_REQUIRED_KEYS = frozenset(
    {
        "paths_read",
        "unknowns",
        "confidence",
        "recommended_ledger_updates",
    }
)

GRAPH_NODE_REQUIRED_KEYS = frozenset({"nodes"})
GRAPH_EDGE_REQUIRED_KEYS = frozenset({"edges"})
GRAPH_CLAIM_REQUIRED_KEYS = frozenset({"claims"})
GRAPH_CONFLICT_REQUIRED_KEYS = frozenset({"conflicts"})
GRAPH_UPDATE_REQUIRED_KEYS = frozenset({"updates"})

PRD_RECONSTRUCTION_READY_STATUSES = frozenset(
    {
        "reconstruction-ready",
        "l4 reconstruction-ready",
    }
)

PRD_EXPORT_REQUIRED_SECTIONS = (
    "## Capability Overview",
    "## Critical Capability Notes",
    "## Unknowns and Evidence Confidence",
)

REFERENCE_IMPLEMENTATION_PROFILE = "reference-implementation"

REFERENCE_IMPLEMENTATION_SPEC_REQUIRED_SECTIONS = (
    "## Fidelity Requirements",
    "### Reference Object",
    "### Required Fidelity",
    "### Reference Behavior Inventory",
)

REFERENCE_IMPLEMENTATION_SECTION_HEADINGS = {
    "fidelity requirements": "## Fidelity Requirements",
    "reference object": "### Reference Object",
    "required fidelity": "### Required Fidelity",
    "reference behavior inventory": "### Reference Behavior Inventory",
    "reference fidelity": "## Fidelity Requirements",
}

PRD_COVERAGE_REQUIRED_TOKENS = (
    "Tier",
    "Depth Status",
    "Overall Status",
)

PRD_OPTIONAL_CONTROL_ARTIFACTS: dict[str, tuple[Path, tuple[str, ...]]] = {
    "capability-triage.md": (
        Path("capability-triage.md"),
        ("## Core Value Proposition", "## Capability Tiers"),
    ),
    "depth-policy.md": (
        Path("depth-policy.md"),
        ("## Tier Expectations",),
    ),
    "quality-check.md": (
        Path("quality-check.md"),
        ("## Gates",),
    ),
}
DEEP_RESEARCH_NOT_NEEDED_STATUS_RE = re.compile(
    r"(?im)^\*\*Status\*\*:\s*(?:\[)?Not needed(?:\])?\s*$"
)


def _extract_markdown_section(content: str, heading: str) -> str:
    heading_match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", content)
    if not heading_match:
        return ""

    section_body = content[heading_match.end() :]
    next_heading = re.search(r"(?m)^##\s+", section_body)
    if next_heading:
        return section_body[: next_heading.start()]
    return section_body


def _validate_markdown_contains(path: Path, required_items: tuple[str, ...], label: str) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    return [f"{label} is missing required section: {item}" for item in required_items if item not in content]


def _validate_markdown_headings(path: Path, required_headings: tuple[str, ...], label: str) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    present_headings = {match.group(0).strip() for match in re.finditer(r"(?m)^#{1,6}\s+.+$", content)}
    return [
        f"{label} is missing required heading: {heading}"
        for heading in required_headings
        if heading not in present_headings
    ]


def _normalize_bullet_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    return cleaned


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _read_json_artifact(path: Path, label: str) -> tuple[Any | None, list[str]]:
    if path.exists() and path.is_dir():
        return None, [f"{label} must be a file, not a directory"]
    try:
        return _read_json(path), []
    except OSError as exc:
        return None, [f"{label} could not be read: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label} is not valid JSON: {exc}"]


def _validate_json_object_with_array_key(feature_dir: Path, filename: str, array_key: str) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / filename, filename)
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return [f"{filename} must contain a top-level JSON object"]
    if not isinstance(payload.get(array_key), list):
        return [f"{filename} must define a top-level {array_key} array"]
    return []


def _validate_unknown_objects(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be a JSON object"]
    unknowns = payload.get("unknowns", [])
    if unknowns is None:
        return []
    if not isinstance(unknowns, list):
        return [f"{label} unknowns must be a list"]
    errors: list[str] = []
    required_keys = ("field", "question", "blocking_level", "resolver", "latest_resolve_phase", "status")
    for index, item in enumerate(unknowns):
        if not isinstance(item, dict):
            errors.append(f"{label} unknowns[{index}] must be an object")
            continue
        for key in required_keys:
            if not str(item.get(key, "")).strip():
                errors.append(f"{label} unknowns[{index}] missing {key}")
    return errors


def _validate_brainstorming_json_artifact(feature_dir: Path, relative_path: str, *, validate_unknowns: bool) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / relative_path, relative_path)
    if read_errors:
        return read_errors
    if validate_unknowns:
        return _validate_unknown_objects(payload, relative_path)
    if not isinstance(payload, dict):
        return [f"{relative_path} must be a JSON object"]
    return []


def _validate_capability_ledger(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "capability-ledger.json", "capability-ledger.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["capability-ledger.json must contain a top-level JSON object"]
    if not isinstance(payload.get("capabilities"), list):
        return ["capability-ledger.json must define a top-level capabilities array"]
    return []


def _validate_control_ledger(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "control-ledger.json", "control-ledger.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["control-ledger.json must contain a top-level JSON object"]
    if not isinstance(payload.get("control_nodes"), list):
        return ["control-ledger.json must define a top-level control_nodes array"]
    return []


def _workflow_state_mentions_heavy_prd_scan(feature_dir: Path) -> bool:
    workflow_state_path = feature_dir / "workflow-state.md"
    if not workflow_state_path.exists() or not workflow_state_path.is_file():
        return False
    content = workflow_state_path.read_text(encoding="utf-8", errors="replace").lower()
    return (
        "sp-prd-scan" in content
        or "entrypoint-ledger.json" in content
        or "config-contracts.json" in content
        or "protocol-contracts.json" in content
        or "state-machines.json" in content
        or "error-semantics.json" in content
        or "verification-surfaces.json" in content
    )


def _extract_handoff_ids(content: str) -> set[str]:
    return set(re.findall(r"\bPH-\d{3}\b", content))


def _is_deep_research_not_needed(content: str) -> bool:
    return bool(DEEP_RESEARCH_NOT_NEEDED_STATUS_RE.search(content))


def _validate_deep_research_not_needed_artifact(content: str) -> list[str]:
    errors: list[str] = []

    for section in DEEP_RESEARCH_NOT_NEEDED_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"deep-research.md not-needed output is missing required section: {section}")

    feasibility_section = _extract_markdown_section(content, "Feasibility Decision")
    handoff_section = _extract_markdown_section(content, "Planning Handoff")
    next_command_section = _extract_markdown_section(content, "Next Command")

    if "**Recommendation**" not in feasibility_section:
        errors.append("deep-research.md not-needed Feasibility Decision is missing **Recommendation**")
    elif "/sp.plan" not in feasibility_section:
        errors.append("deep-research.md not-needed Feasibility Decision must recommend `/sp.plan`")

    if "**Reason**" not in feasibility_section:
        errors.append("deep-research.md not-needed Feasibility Decision is missing **Reason**")

    if "**Handoff IDs**" not in handoff_section:
        errors.append("deep-research.md not-needed Planning Handoff is missing **Handoff IDs**")
    elif "not needed" not in handoff_section.lower():
        errors.append("deep-research.md not-needed Planning Handoff must mark handoff IDs as Not needed")

    if "**Recommended approach**" not in handoff_section:
        errors.append("deep-research.md not-needed Planning Handoff is missing **Recommended approach**")
    if "**Constraints `/sp.plan` must preserve**" not in handoff_section:
        errors.append(
            "deep-research.md not-needed Planning Handoff is missing **Constraints `/sp.plan` must preserve**"
        )

    if "/sp.plan" not in next_command_section:
        errors.append("deep-research.md not-needed Next Command must be `/sp.plan`")

    return errors


def _validate_deep_research_artifact(feature_dir: Path) -> list[str]:
    deep_research_path = feature_dir / "deep-research.md"
    if not deep_research_path.exists():
        return []

    content = deep_research_path.read_text(encoding="utf-8", errors="replace")
    if _is_deep_research_not_needed(content):
        return _validate_deep_research_not_needed_artifact(content)

    errors: list[str] = []

    for section in DEEP_RESEARCH_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"deep-research.md is missing required section: {section}")

    handoff_section = _extract_markdown_section(content, "Planning Handoff")

    for field in DEEP_RESEARCH_HANDOFF_FIELDS:
        if field not in handoff_section:
            errors.append(f"deep-research.md Planning Handoff is missing field: {field}")

    if "CAP-" not in content:
        errors.append("deep-research.md is missing capability traceability IDs such as CAP-001")
    if "TRK-" not in content:
        errors.append("deep-research.md is missing research track IDs such as TRK-001")
    if "EVD-" not in content and "SPK-" not in content:
        errors.append("deep-research.md is missing evidence or spike IDs such as EVD-001 or SPK-001")
    if "PH-" not in handoff_section and "not needed" not in handoff_section.lower():
        errors.append("deep-research.md is missing Planning Handoff IDs such as PH-001")

    return errors


def _validate_plan_consumes_deep_research(feature_dir: Path) -> list[str]:
    deep_research_path = feature_dir / "deep-research.md"
    plan_path = feature_dir / "plan.md"
    if not deep_research_path.exists() or not plan_path.exists():
        return []

    deep_research_content = deep_research_path.read_text(encoding="utf-8", errors="replace")
    handoff_section = _extract_markdown_section(deep_research_content, "Planning Handoff")
    handoff_ids = _extract_handoff_ids(handoff_section)
    if not handoff_ids:
        return []

    plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    if "Deep Research Traceability Matrix" not in plan_content:
        errors.append("plan.md is missing Deep Research Traceability Matrix for deep-research handoff IDs")

    traceability_section = _extract_markdown_section(plan_content, "Deep Research Traceability Matrix")
    if not traceability_section and "Deep Research Traceability Matrix" in plan_content:
        errors.append("plan.md Deep Research Traceability Matrix must be a level-2 markdown section")

    missing_columns = [
        column for column in PLAN_DEEP_RESEARCH_TRACEABILITY_COLUMNS if column not in traceability_section
    ]
    if missing_columns:
        joined = ", ".join(missing_columns)
        errors.append(f"plan.md Deep Research Traceability Matrix is missing required columns: {joined}")

    missing_ids = sorted(handoff_id for handoff_id in handoff_ids if handoff_id not in traceability_section)
    if missing_ids:
        joined = ", ".join(missing_ids)
        errors.append(f"plan.md does not consume deep-research Planning Handoff IDs: {joined}")

    return errors


def _validate_prd_scan_artifacts(feature_dir: Path, *, require_heavy_scan_json: bool = False) -> list[str]:
    errors: list[str] = []
    for directory_name in ("scan-packets", "evidence", "worker-results"):
        target = feature_dir / directory_name
        if target.exists() and not target.is_dir():
            errors.append(f"{directory_name} must be a directory")

    coverage_payload, coverage_errors = _read_json_artifact(feature_dir / "coverage-ledger.json", "coverage-ledger.json")
    if coverage_errors:
        errors.extend(coverage_errors)
        return errors
    if not isinstance(coverage_payload, dict):
        errors.append("coverage-ledger.json must contain a top-level JSON object")
    elif not isinstance(coverage_payload.get("rows"), list):
        errors.append("coverage-ledger.json must define a top-level rows array")

    capability_payload, capability_errors = _read_json_artifact(
        feature_dir / "capability-ledger.json", "capability-ledger.json"
    )
    if capability_errors:
        errors.extend(capability_errors)
        return errors
    if not isinstance(capability_payload, dict):
        errors.append("capability-ledger.json must contain a top-level JSON object")
    elif not isinstance(capability_payload.get("capabilities"), list):
        errors.append("capability-ledger.json must define a top-level capabilities array")

    artifact_payload, artifact_errors = _read_json_artifact(feature_dir / "artifact-contracts.json", "artifact-contracts.json")
    if artifact_errors:
        errors.extend(artifact_errors)
        return errors
    if not isinstance(artifact_payload, dict):
        errors.append("artifact-contracts.json must contain a top-level JSON object")
    elif not isinstance(artifact_payload.get("artifacts"), list):
        errors.append("artifact-contracts.json must define a top-level artifacts array")

    checklist_payload, checklist_errors = _read_json_artifact(
        feature_dir / "reconstruction-checklist.json", "reconstruction-checklist.json"
    )
    if checklist_errors:
        errors.extend(checklist_errors)
        return errors
    if not isinstance(checklist_payload, dict):
        errors.append("reconstruction-checklist.json must contain a top-level JSON object")
    elif not isinstance(checklist_payload.get("checks"), list):
        errors.append("reconstruction-checklist.json must define a top-level checks array")

    if require_heavy_scan_json:
        for filename, array_key in PRD_HEAVY_SCAN_JSON_ARTIFACTS.items():
            errors.extend(_validate_json_object_with_array_key(feature_dir, filename, array_key))

    return errors


def _validate_prd_worker_results(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    worker_results_dir = feature_dir / "worker-results"
    if not worker_results_dir.is_dir():
        return errors

    for result_path in sorted(path for path in worker_results_dir.iterdir() if path.suffix == ".json"):
        relative_label = result_path.relative_to(feature_dir).as_posix()
        payload, read_errors = _read_json_artifact(result_path, relative_label)
        if read_errors:
            errors.extend(read_errors)
            continue
        if not isinstance(payload, dict):
            errors.append(f"{relative_label} must contain a top-level JSON object")
            continue

        for key in sorted(PRD_WORKER_RESULT_REQUIRED_KEYS - payload.keys()):
            errors.append(f"{relative_label} is missing required worker result key: {key}")

    return errors


def _validate_graph_artifact(feature_dir: Path, relative_path: str, required_keys: frozenset[str]) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / relative_path, relative_path)
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return [f"{relative_path} must contain a top-level JSON object"]
    errors: list[str] = []
    for key in sorted(required_keys - payload.keys()):
        errors.append(f"{relative_path} is missing required key: {key}")
    for key in required_keys:
        if key in payload and not isinstance(payload.get(key), list):
            errors.append(f"{relative_path} must define a top-level {key} array")
    return errors


def _validate_cognition_status_artifact(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "status.json", "status.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["status.json must contain a top-level JSON object"]
    return []


def _validate_cognition_database_artifact(feature_dir: Path) -> list[str]:
    db_path = feature_dir / "project-cognition.db"
    if not db_path.exists() or not db_path.is_file():
        return ["project-cognition.db must exist for the SQLite project cognition runtime"]
    if db_path.stat().st_size == 0:
        return ["project-cognition.db must not be empty"]
    return []


def _normalize_result_path(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _validate_map_scan_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_cognition_status_artifact(feature_dir))
    errors.extend(_validate_graph_artifact(feature_dir, "provisional/nodes.json", GRAPH_NODE_REQUIRED_KEYS))
    errors.extend(_validate_graph_artifact(feature_dir, "provisional/edges.json", GRAPH_EDGE_REQUIRED_KEYS))
    errors.extend(
        _validate_json_object_with_array_key(feature_dir, "provisional/observations.json", "observations")
    )
    errors.extend(_validate_json_object_with_array_key(feature_dir, "coverage.json", "rows"))
    return errors


def _validate_map_build_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_cognition_status_artifact(feature_dir))
    errors.extend(_validate_cognition_database_artifact(feature_dir))
    return errors


def _validate_map_update_artifacts(feature_dir: Path) -> list[str]:
    errors = _validate_map_build_artifacts(feature_dir)
    payload, read_errors = _read_json_artifact(feature_dir / "status.json", "status.json")
    if read_errors:
        errors.extend(read_errors)
        return errors
    if not isinstance(payload, dict):
        errors.append("status.json must contain a top-level JSON object")
        return errors
    if not payload.get("last_update_id") and payload.get("freshness") not in {"fresh", "partial_refresh"}:
        errors.append("status.json must record last_update_id or a post-update freshness state")
    return errors


def _capability_diagram_fields(capability: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        field
        for field in ("lifecycle_mermaid", "flow_mermaid")
        if isinstance(capability.get(field), str) and str(capability.get(field)).strip()
    )


def _capability_deep_workflow_page(capability: dict[str, object]) -> str:
    for key in ("deep_workflow_path", "deep_workflow_page", "deep_workflow", "page", "path"):
        value = capability.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resolve_map_build_page_path(feature_dir: Path, page: str) -> tuple[Path | None, str | None]:
    page_path = Path(page)
    if page_path.is_absolute():
        return None, "absolute deep workflow page paths are not allowed"

    normalized = _normalize_result_path(page)
    project_map_prefix = ".specify/project-map/"
    if normalized.lower().startswith(project_map_prefix):
        normalized = normalized[len(project_map_prefix) :]
    resolved = (feature_dir / normalized).resolve(strict=False)
    try:
        resolved.relative_to(feature_dir.resolve(strict=False))
    except ValueError:
        return None, "deep workflow page path escapes the map-build feature directory"
    return resolved, None


def _normalize_mermaid_content(content: str) -> str:
    return re.sub(r"\s+", " ", content).strip()


def _extract_mermaid_blocks(content: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(r"(?ims)^```\s*mermaid\s*\r?\n(.*?)^```\s*$", content)
    ]


def _missing_rendered_mermaid_fields(content: str, capability: dict[str, object]) -> list[str]:
    normalized_blocks = [_normalize_mermaid_content(block) for block in _extract_mermaid_blocks(content)]
    missing: list[str] = []
    for field in ("lifecycle_mermaid", "flow_mermaid"):
        value = capability.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        normalized_value = _normalize_mermaid_content(value)
        if not any(normalized_value and normalized_value in block for block in normalized_blocks):
            missing.append(field)
    return missing


def _validate_map_build_capability_diagrams(feature_dir: Path) -> list[str]:
    payload, read_errors = _read_json_artifact(feature_dir / "index" / "capabilities.json", "index/capabilities.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict):
        return ["index/capabilities.json must contain a top-level JSON object"]
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list):
        return ["index/capabilities.json must define a top-level capabilities array"]

    errors: list[str] = []
    for index, capability in enumerate(capabilities, start=1):
        if not isinstance(capability, dict):
            continue
        diagram_fields = _capability_diagram_fields(capability)
        if not diagram_fields:
            continue

        capability_id = str(capability.get("id") or f"capability #{index}")
        page = _capability_deep_workflow_page(capability)
        if not page:
            joined = ", ".join(diagram_fields)
            errors.append(
                f"index/capabilities.json capability {capability_id} defines {joined} but has no deep workflow page"
            )
            continue

        page_path, page_error = _resolve_map_build_page_path(feature_dir, page)
        if page_error is not None:
            errors.append(
                f"index/capabilities.json capability {capability_id} references invalid deep workflow page "
                f"{page}: {page_error}"
            )
            continue
        if page_path is None:
            continue
        if not page_path.exists() or not page_path.is_file():
            errors.append(
                f"index/capabilities.json capability {capability_id} references missing deep workflow page: {page}"
            )
            continue

        content = page_path.read_text(encoding="utf-8", errors="replace")
        missing_mermaid_fields = _missing_rendered_mermaid_fields(content, capability)
        if missing_mermaid_fields:
            joined = ", ".join(missing_mermaid_fields)
            errors.append(
                f"index/capabilities.json capability {capability_id} defines Mermaid diagram fields "
                f"but {page} does not render declared Mermaid content for: {joined}"
            )

    return errors


def _validate_prd_build_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    missing_exports = [
        relative_path
        for relative_path in PRD_BUILD_REQUIRED_HEAVY_EXPORTS
        if not (feature_dir / relative_path).exists()
    ]
    errors.extend(f"missing required artifact: {relative_path}" for relative_path in missing_exports)
    for relative_path in PRD_BUILD_REQUIRED_HEAVY_EXPORTS:
        target = feature_dir / relative_path
        if target.exists() and not target.is_file():
            errors.append(f"required artifact must be a file: {relative_path}")

    coverage_payload, coverage_errors = _read_json_artifact(feature_dir / "coverage-ledger.json", "coverage-ledger.json")
    if coverage_errors:
        return coverage_errors
    if not isinstance(coverage_payload, dict):
        return ["coverage-ledger.json must contain a top-level JSON object"]
    if not isinstance(coverage_payload.get("rows"), list):
        return ["coverage-ledger.json must define a top-level rows array"]

    capability_payload, capability_errors = _read_json_artifact(
        feature_dir / "capability-ledger.json", "capability-ledger.json"
    )
    if capability_errors:
        return capability_errors
    if not isinstance(capability_payload, dict):
        return ["capability-ledger.json must contain a top-level JSON object"]

    capabilities = capability_payload.get("capabilities")
    if not isinstance(capabilities, list):
        return ["capability-ledger.json must define a top-level capabilities array"]

    critical_capabilities = [item for item in capabilities if isinstance(item, dict) and item.get("tier") == "critical"]
    if not critical_capabilities:
        errors.append("capability-ledger.json must include at least one critical capability before prd-build can pass")
    else:
        non_ready = [
            str(item.get("status") or "").strip() or "missing"
            for item in critical_capabilities
            if str(item.get("status") or "").strip().lower() not in PRD_RECONSTRUCTION_READY_STATUSES
        ]
        if non_ready:
            joined = ", ".join(sorted(set(non_ready)))
            errors.append(
                "prd-build is blocked because critical capabilities must be reconstruction-ready; "
                f"found: {joined}"
            )

    artifact_payload, artifact_errors = _read_json_artifact(feature_dir / "artifact-contracts.json", "artifact-contracts.json")
    if artifact_errors:
        errors.extend(artifact_errors)
        return errors
    if not isinstance(artifact_payload, dict):
        errors.append("artifact-contracts.json must contain a top-level JSON object")
        return errors

    artifacts = artifact_payload.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifact-contracts.json must define a top-level artifacts array")
    elif not artifacts:
        errors.append("artifact-contracts.json must include at least one artifact before prd-build can pass")

    checklist_payload, checklist_errors = _read_json_artifact(
        feature_dir / "reconstruction-checklist.json", "reconstruction-checklist.json"
    )
    if checklist_errors:
        errors.extend(checklist_errors)
        return errors
    if not isinstance(checklist_payload, dict):
        errors.append("reconstruction-checklist.json must contain a top-level JSON object")
        return errors
    checks = checklist_payload.get("checks")
    if not isinstance(checks, list):
        errors.append("reconstruction-checklist.json must define a top-level checks array")
    elif not checks:
        errors.append("reconstruction-checklist.json must include at least one check before prd-build can pass")

    scan_packets_dir = feature_dir / "scan-packets"
    if not scan_packets_dir.is_dir():
        errors.append("scan-packets must be a directory")
    elif not any(scan_packets_dir.iterdir()):
        errors.append("scan-packets must contain at least one packet file before prd-build can pass")

    worker_results_dir = feature_dir / "worker-results"
    if not worker_results_dir.is_dir():
        errors.append("worker-results must be a directory")
    elif not any(worker_results_dir.iterdir()):
        errors.append("worker-results must contain at least one result file before prd-build can pass")
    else:
        errors.extend(_validate_prd_worker_results(feature_dir))

    evidence_dir = feature_dir / "evidence"
    if not evidence_dir.is_dir():
        errors.append("evidence must be a directory")
    elif not any(evidence_dir.iterdir()):
        errors.append("evidence must contain at least one file or subdirectory entry before prd-build can pass")

    return errors


def _validate_specify_draft_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    draft_path = feature_dir / "specify-draft.md"
    alignment_path = feature_dir / "alignment.md"
    context_path = feature_dir / "context.md"
    workflow_state_path = feature_dir / "workflow-state.md"

    errors.extend(_validate_markdown_headings(draft_path, SPECIFY_DRAFT_REQUIRED_HEADINGS, "specify-draft.md"))
    errors.extend(_validate_markdown_headings(alignment_path, SPECIFY_ALIGNMENT_REQUIRED_HEADINGS, "alignment.md"))
    errors.extend(_validate_markdown_headings(context_path, SPECIFY_CONTEXT_REQUIRED_HEADINGS, "context.md"))

    workflow_state_content = workflow_state_path.read_text(encoding="utf-8", errors="replace")
    fixed_lifecycle_state = _extract_markdown_section(workflow_state_content, "Fixed Lifecycle State")
    required_state_fields = (
        "current_stage",
        "current_domain",
        "next_action",
        "blocker_reason",
        "final_handoff_decision",
    )
    for field in required_state_fields:
        value = extract_field(fixed_lifecycle_state, field)
        if not value.strip():
            errors.append(f"workflow-state.md is missing Fixed Lifecycle State field: {field}")

    for legacy_field in ("active_profile", "coverage_mode", "observer_status", "last_observer_pass", "draft_file"):
        if re.search(rf"(?im)^\s*-\s*{re.escape(legacy_field)}\s*:", workflow_state_content):
            errors.append(f"workflow-state.md still uses legacy sp-specify state field: {legacy_field}")

    errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/facts.json", validate_unknowns=True))
    errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/route.json", validate_unknowns=False))
    errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/intent.json", validate_unknowns=False))
    errors.extend(_validate_brainstorming_json_artifact(feature_dir, "brainstorming/complexity.json", validate_unknowns=False))
    errors.extend(
        _validate_brainstorming_json_artifact(
            feature_dir,
            "brainstorming/handoff-to-specify.json",
            validate_unknowns=True,
        )
    )

    return errors


def _workflow_state_active_profile(feature_dir: Path) -> str:
    workflow_state_path = feature_dir / "workflow-state.md"
    if not workflow_state_path.exists() or not workflow_state_path.is_file():
        return ""
    workflow_state_content = workflow_state_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?im)^\s*-\s*active_profile\s*:\s*`?([^`\r\n]+)`?\s*$", workflow_state_content)
    if not match:
        return ""
    return match.group(1).strip().lower()


def _validate_reference_implementation_spec(feature_dir: Path) -> list[str]:
    spec_path = feature_dir / "spec.md"
    spec_content = spec_path.read_text(encoding="utf-8", errors="replace")
    if (
        _workflow_state_active_profile(feature_dir) != REFERENCE_IMPLEMENTATION_PROFILE
        and "## Fidelity Requirements" not in spec_content
    ):
        return []

    return _validate_markdown_contains(
        spec_path,
        REFERENCE_IMPLEMENTATION_SPEC_REQUIRED_SECTIONS,
        "spec.md",
    )


def validate_artifacts_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    if command_name not in REQUIRED_ARTIFACTS:
        raise QualityHookError(f"unsupported command_name '{command_name}' for workflow.artifacts.validate")

    raw = str(payload.get("feature_dir") or "").strip()
    if not raw:
        raise QualityHookError("feature_dir is required")
    feature_dir = Path(raw)
    if not feature_dir.is_absolute():
        feature_dir = (project_root / feature_dir).resolve()

    missing = [name for name in REQUIRED_ARTIFACTS[command_name] if not (feature_dir / name).exists()]
    type_errors: list[str] = []
    for relative_path in FILE_REQUIRED_ARTIFACTS.get(command_name, ()):
        target = feature_dir / relative_path
        if target.exists() and not target.is_file():
            type_errors.append(f"required artifact must be a file: {relative_path}")
    for relative_path in DIRECTORY_REQUIRED_ARTIFACTS.get(command_name, ()):
        target = feature_dir / relative_path
        if target.exists() and not target.is_dir():
            type_errors.append(f"required artifact must be a directory: {relative_path}")
    if command_name == "constitution":
        constitution_path = project_root / ".specify" / "memory" / "constitution.md"
        if not constitution_path.exists():
            missing.append(".specify/memory/constitution.md")
    if missing or type_errors:
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[*([f"missing required artifact: {name}" for name in missing]), *type_errors],
            data={"feature_dir": str(feature_dir)},
        )
    validation_errors: list[str] = []
    if command_name == "specify":
        validation_errors.extend(_validate_specify_draft_artifacts(feature_dir))
        validation_errors.extend(_validate_reference_implementation_spec(feature_dir))
    if command_name == "deep-research":
        validation_errors.extend(_validate_deep_research_artifact(feature_dir))
    if command_name == "plan":
        validation_errors.extend(_validate_plan_consumes_deep_research(feature_dir))
    if command_name == "map-scan":
        validation_errors.extend(_validate_map_scan_artifacts(feature_dir))
    if command_name == "map-build":
        validation_errors.extend(_validate_map_build_artifacts(feature_dir))
    if command_name == "map-update":
        validation_errors.extend(_validate_map_update_artifacts(feature_dir))
    if command_name == "prd-scan":
        validation_errors.extend(
            _validate_prd_scan_artifacts(
                feature_dir,
                require_heavy_scan_json=_workflow_state_mentions_heavy_prd_scan(feature_dir),
            )
        )
    if command_name == "prd-build":
        validation_errors.extend(_validate_prd_build_artifacts(feature_dir))
    if command_name == "prd":
        validation_errors.extend(_validate_prd_scan_artifacts(feature_dir))
    if validation_errors:
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="blocked",
            severity="critical",
            errors=validation_errors,
            data={"feature_dir": str(feature_dir)},
        )
    return HookResult(
        event=WORKFLOW_ARTIFACTS_VALIDATE,
        status="ok",
        severity="info",
        data={"feature_dir": str(feature_dir)},
    )
