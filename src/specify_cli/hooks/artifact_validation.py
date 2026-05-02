"""Validation hooks for workflow artifact completeness."""

from __future__ import annotations

import re
from pathlib import Path

from .checkpoint_serializers import normalize_command_name
from .events import WORKFLOW_ARTIFACTS_VALIDATE
from .types import HookResult, QualityHookError


REQUIRED_ARTIFACTS = {
    "constitution": ("workflow-state.md",),
    "specify": ("spec.md", "alignment.md", "context.md", "workflow-state.md"),
    "deep-research": ("deep-research.md", "workflow-state.md"),
    "plan": ("plan.md", "workflow-state.md"),
    "tasks": ("tasks.md", "workflow-state.md"),
    "analyze": ("workflow-state.md",),
    "prd": (
        "workflow-state.md",
        "coverage-matrix.md",
        "master/master-pack.md",
        "exports/prd.md",
        "master/exports",
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

PRD_MASTER_PACK_REQUIRED_SECTIONS = (
    "## Capability Inventory",
    "## Critical Capability Dossiers",
    "## Coverage and Export Map",
)

PRD_EXPORT_REQUIRED_SECTIONS = (
    "## Capability Overview",
    "## Critical Capability Notes",
    "## Unknowns and Evidence Confidence",
)

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


def _validate_prd_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    master_exports_dir = feature_dir / "master" / "exports"
    if master_exports_dir.exists() and not master_exports_dir.is_dir():
        errors.append("master/exports must be a directory")

    coverage_path = feature_dir / "coverage-matrix.md"
    coverage_content = coverage_path.read_text(encoding="utf-8", errors="replace")
    missing_coverage = [token for token in PRD_COVERAGE_REQUIRED_TOKENS if token not in coverage_content]
    if missing_coverage:
        joined = ", ".join(missing_coverage)
        errors.append(f"coverage-matrix.md is missing depth-aware columns or fields: {joined}")

    errors.extend(
        _validate_markdown_contains(
            feature_dir / "master" / "master-pack.md",
            PRD_MASTER_PACK_REQUIRED_SECTIONS,
            "master/master-pack.md",
        )
    )
    errors.extend(
        _validate_markdown_contains(
            feature_dir / "exports" / "prd.md",
            PRD_EXPORT_REQUIRED_SECTIONS,
            "exports/prd.md",
        )
    )
    for label, (relative_path, required_sections) in PRD_OPTIONAL_CONTROL_ARTIFACTS.items():
        artifact_path = feature_dir / relative_path
        if artifact_path.exists():
            errors.extend(_validate_markdown_contains(artifact_path, required_sections, label))
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
    if command_name == "constitution":
        constitution_path = project_root / ".specify" / "memory" / "constitution.md"
        if not constitution_path.exists():
            missing.append(".specify/memory/constitution.md")
    if missing:
        return HookResult(
            event=WORKFLOW_ARTIFACTS_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"missing required artifact: {name}" for name in missing],
            data={"feature_dir": str(feature_dir)},
        )
    validation_errors: list[str] = []
    if command_name == "deep-research":
        validation_errors.extend(_validate_deep_research_artifact(feature_dir))
    if command_name == "plan":
        validation_errors.extend(_validate_plan_consumes_deep_research(feature_dir))
    if command_name == "prd":
        validation_errors.extend(_validate_prd_artifacts(feature_dir))
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
