"""Validation hooks for workflow artifact completeness."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .checkpoint_serializers import normalize_command_name, serialize_workflow_state
from .events import WORKFLOW_ARTIFACTS_VALIDATE
from .types import HookResult, QualityHookError

FILE_REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": ("spec.md", "alignment.md", "context.md", "specify-draft.md", "workflow-state.md"),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": ("plan.md", "workflow-state.md"),
    "tasks": ("tasks.md", "workflow-state.md"),
    "analyze": ("workflow-state.md",),
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
    "prd-scan": ("scan-packets", "evidence", "worker-results"),
    "prd-build": ("scan-packets", "evidence", "worker-results"),
    "prd": ("scan-packets", "evidence", "worker-results"),
}


REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": ("spec.md", "alignment.md", "context.md", "specify-draft.md", "workflow-state.md"),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": ("plan.md", "workflow-state.md"),
    "tasks": ("tasks.md", "workflow-state.md"),
    "analyze": ("workflow-state.md",),
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
    "## Recovery Capsule",
    "## Observer Findings",
)

SPECIFY_ALIGNMENT_REQUIRED_HEADINGS = (
    "## Observer Gate",
    "## Coverage Mode Outcomes",
)

SPECIFY_CONTEXT_REQUIRED_HEADINGS = ("## Change Propagation Matrix",)

SPECIFY_FULL_COVERAGE_TRIGGER_PHRASES = (
    "cross-module impact",
    "external boundary, contract, or integration behavior",
    "migration or compatibility preservation",
    "asynchronous, event-driven, queue, or state-propagation behavior",
    "configuration-driven behavior",
    "security, permission, or trust-boundary semantics",
    "observability or rollback requirements",
    "performance or capacity risk",
)

PRD_BUILD_REQUIRED_EXPORTS = (
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
)

REFERENCE_IMPLEMENTATION_SECTION_HEADINGS = {
    "fidelity requirements": "## Fidelity Requirements",
    "reference object": "### Reference Object",
    "required fidelity": "### Required Fidelity",
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


def _validate_specify_profile_artifacts(feature_dir: Path) -> list[str]:
    checkpoint = serialize_workflow_state(feature_dir / "workflow-state.md")
    active_profile = checkpoint.get("active_profile")
    required_sections = checkpoint.get("required_sections")
    if not isinstance(required_sections, list):
        required_sections = []

    if active_profile != REFERENCE_IMPLEMENTATION_PROFILE:
        return []

    persisted_required_headings = {
        heading
        for section_name in required_sections
        if (heading := REFERENCE_IMPLEMENTATION_SECTION_HEADINGS.get(str(section_name).strip().lower()))
    }
    mapped_headings = [
        heading for heading in REFERENCE_IMPLEMENTATION_SPEC_REQUIRED_SECTIONS if heading in persisted_required_headings
    ]
    required_headings = tuple(dict.fromkeys([*mapped_headings, *REFERENCE_IMPLEMENTATION_SPEC_REQUIRED_SECTIONS]))

    return _validate_markdown_headings(
        feature_dir / "spec.md",
        required_headings,
        "spec.md reference-implementation profile",
    )


def _validate_specify_draft_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    draft_path = feature_dir / "specify-draft.md"
    alignment_path = feature_dir / "alignment.md"
    context_path = feature_dir / "context.md"
    workflow_state_path = feature_dir / "workflow-state.md"

    errors.extend(_validate_markdown_headings(draft_path, SPECIFY_DRAFT_REQUIRED_HEADINGS, "specify-draft.md"))
    errors.extend(_validate_markdown_headings(alignment_path, SPECIFY_ALIGNMENT_REQUIRED_HEADINGS, "alignment.md"))
    errors.extend(_validate_markdown_headings(context_path, SPECIFY_CONTEXT_REQUIRED_HEADINGS, "context.md"))

    checkpoint = serialize_workflow_state(workflow_state_path)
    if checkpoint.get("draft_file") != "specify-draft.md":
        errors.append("workflow-state.md is missing Resume Checklist field: draft_file: `specify-draft.md`")
    if checkpoint.get("observer_status") == "blocked":
        errors.append("workflow-state.md records observer_status as blocked; `Aligned: ready for plan` cannot pass")

    draft_content = draft_path.read_text(encoding="utf-8", errors="replace")
    alignment = alignment_path.read_text(encoding="utf-8", errors="replace").lower()
    observer_gate = _extract_markdown_section(alignment_path.read_text(encoding="utf-8", errors="replace"), "Observer Gate")
    if "**Status**: blocked" in observer_gate:
        errors.append("alignment.md records Observer Gate status as blocked; planning-ready handoff is not allowed")

    release_blockers_match = re.search(
        r"(?ms)^###\s+Release Blockers\s*$\n(?P<body>.*?)(?=^##\s+|^###\s+|\Z)",
        draft_content,
    )
    if release_blockers_match:
        blocker_lines = [
            _normalize_bullet_value(line.strip()[2:].strip())
            for line in release_blockers_match.group("body").splitlines()
            if line.strip().startswith("- ")
        ]
        nonempty_blockers = [line for line in blocker_lines if line and line.lower() not in {"none", "resolved"}]
        if nonempty_blockers:
            joined = ", ".join(nonempty_blockers)
            errors.append(f"specify-draft.md still records unresolved release blockers: {joined}")

    if "coverage mode" in alignment and "coverage mode**: core" in alignment:
        hit_triggers = [phrase for phrase in SPECIFY_FULL_COVERAGE_TRIGGER_PHRASES if phrase in alignment]
        if hit_triggers:
            joined = ", ".join(hit_triggers)
            errors.append(
                "specify artifacts require full coverage evidence when escalation triggers were recorded: "
                f"{joined}"
            )

    return errors


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
        validation_errors.extend(_validate_specify_profile_artifacts(feature_dir))
    if command_name == "deep-research":
        validation_errors.extend(_validate_deep_research_artifact(feature_dir))
    if command_name == "plan":
        validation_errors.extend(_validate_plan_consumes_deep_research(feature_dir))
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
