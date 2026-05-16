"""Compile subagent execution packets from planning artifacts."""

from __future__ import annotations

import re
from pathlib import Path

from .packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    PacketReference,
    PacketScope,
    WorkerTaskPacket,
)
from .packet_validator import validate_worker_task_packet


SECTION_RE = re.compile(r"(?ms)^#{2,3}\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#{2,3}\s+|\Z)")
BULLET_RE = re.compile(r"(?m)^\s*-\s+`?(?P<value>.+?)`?\s*$")
TASK_RE = re.compile(r"(?m)^\s*-\s\[[ xX]\]\s(?P<task_id>T\d+)(?P<body>.+)$")
PATH_RE = re.compile(r"[\w./-]+/[\w./-]+")
STORY_RE = re.compile(r"\[(US\d+)\]")
CONSEQUENCE_ID_RE = re.compile(r"\bCA-\d{3}\b")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _section_body(text: str, title: str) -> str:
    for match in SECTION_RE.finditer(text):
        if match.group("title").strip().lower() == title.strip().lower():
            return match.group("body").strip()
    return ""


def _bullet_values(text: str) -> list[str]:
    return [match.group("value").strip() for match in BULLET_RE.finditer(text)]


def _leading_bullet_values(text: str) -> list[str]:
    values: list[str] = []
    collecting = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = BULLET_RE.match(raw_line)
        if match:
            collecting = True
            values.append(match.group("value").strip())
            continue
        if collecting:
            break
    return values


def _story_id_from_task_body(task_body: str) -> str:
    match = STORY_RE.search(task_body)
    return match.group(1) if match else "UNASSIGNED"


def _paths_from_task_body(task_body: str) -> list[str]:
    return PATH_RE.findall(task_body)


def _task_body(tasks_text: str, task_id: str) -> str:
    for match in TASK_RE.finditer(tasks_text):
        if match.group("task_id") == task_id:
            return match.group("body").strip()
    raise ValueError(f"Task {task_id} not found in tasks.md")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _normalized_header_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    aliases = {
        "affected_state_dependency": "affected_objects",
        "affected_state": "affected_objects",
        "affected_dependency": "affected_objects",
        "task_ids": "task_ids",
        "obligation_id": "obligation_id",
        "required_references": "required_references",
        "validation": "validation",
        "stop_reopen_condition": "stop_and_reopen_condition",
        "stop_and_reopen_condition": "stop_and_reopen_condition",
    }
    return aliases.get(normalized, normalized)


def _is_table_separator(parts: list[str]) -> bool:
    return bool(parts) and all(re.fullmatch(r":?-{3,}:?", part.strip()) for part in parts)


def _parse_pipe_fields(line: str, headers: list[str] | None = None) -> dict[str, str]:
    fields: dict[str, str] = {}
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    if headers:
        for header, value in zip(headers, parts):
            if header and value:
                fields[header] = value
    elif len(parts) >= 6:
        fields.update(
            {
                "obligation_id": parts[0],
                "task_ids": parts[1],
                "affected_objects": parts[2],
                "required_references": parts[3],
                "validation": parts[4],
                "stop_and_reopen_condition": parts[5],
            }
        )
    for raw_part in parts:
        part = raw_part.strip().strip("-").strip()
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def _split_csv_field(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _line_mentions_task(line: str, task_id: str) -> bool:
    return any(part.strip() == task_id for part in re.split(r"[,;\s]+", line) if part.strip())


def _consequence_obligations_for_task(
    tasks_text: str,
    task_id: str,
) -> list[ConsequenceObligation]:
    section = _section_body(tasks_text, "Consequence Obligation Mapping")
    obligations: list[ConsequenceObligation] = []
    seen: set[str] = set()
    headers: list[str] | None = None
    for raw_line in section.splitlines():
        if raw_line.strip().startswith("|"):
            parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
            if _is_table_separator(parts):
                continue
            if any(part.strip().lower() == "obligation id" for part in parts):
                headers = [_normalized_header_name(part) for part in parts]
                continue
        if not _line_mentions_task(raw_line, task_id):
            continue
        match = CONSEQUENCE_ID_RE.search(raw_line)
        if not match:
            continue
        obligation_id = match.group(0)
        if obligation_id in seen:
            continue
        seen.add(obligation_id)
        fields = _parse_pipe_fields(raw_line, headers)
        affected_objects = _split_csv_field(fields.get("affected_objects", "")) or [task_id]
        stop_and_reopen_condition = fields.get(
            "stop_and_reopen_condition",
            f"No validation evidence supplied for {obligation_id}",
        )
        obligations.append(
            ConsequenceObligation(
                obligation_id=obligation_id,
                claim=fields.get("claim", f"{obligation_id} consequence obligation for {task_id}"),
                affected_objects=affected_objects,
                state_behavior_refs=_split_csv_field(fields.get("state_behavior_refs", "")),
                dependency_refs=_split_csv_field(fields.get("dependency_refs", "")),
                recovery_validation_refs=_split_csv_field(fields.get("validation", "")),
                owner=fields.get("owner", "sp-tasks"),
                latest_resolve_phase=fields.get("latest_resolve_phase", "tasks"),
                status=fields.get("status", "open"),
                stop_and_reopen_condition=stop_and_reopen_condition,
            )
        )
    return obligations


def _section_or_subsection_values(text: str, *titles: str) -> list[str]:
    values: list[str] = []
    for title in titles:
        values.extend(_bullet_values(_section_body(text, title)))
    return _unique(values)


def _context_bundle_from_project_docs(
    project_root: Path,
    *,
    required_references: list[PacketReference],
) -> list[ContextBundleItem]:
    specs: list[tuple[str, str, str, list[str], str]] = [
        (
            ".specify/project-cognition/status.json",
            "project_cognition",
            "Project cognition freshness entrypoint for query-backed runtime readiness and refresh metadata.",
            ["workflow_boundary", "architecture_boundary", "validation"],
            "status is the lightweight entrypoint before requesting a task-local cognition query bundle",
        ),
        (
            ".specify/project-cognition/project-cognition.db",
            "project_cognition",
            "Canonical SQLite project cognition graph store queried for task-local bundle, readiness, and minimal_live_reads.",
            ["workflow_boundary", "architecture_boundary", "forbidden_drift"],
            "project-cognition query resolves touched-area execution context without raw slice reads",
        ),
        (
            ".specify/testing/TESTING_CONTRACT.md",
            "testing_contract",
            "Project-level testing control plane for covered-module obligations and regression requirements.",
            ["validation", "forbidden_drift"],
            "testing contract constrains what counts as complete",
        ),
        (
            ".specify/testing/TESTING_PLAYBOOK.md",
            "testing_playbook",
            "Testing control-plane command-tier guidance for targeted and full verification during execution.",
            ["validation"],
            "testing playbook provides runnable verification commands",
        ),
        (
            ".specify/testing/COVERAGE_BASELINE.json",
            "coverage_baseline",
            "Testing control-plane coverage baseline for current covered-module status and coverage gaps.",
            ["validation"],
            "coverage baseline captures current covered-module status",
        ),
    ]

    items: list[ContextBundleItem] = []
    seen: set[str] = set()
    read_order = 1

    for relative_path, kind, purpose, required_for, selection_reason in specs:
        if not (project_root / relative_path).exists():
            continue
        normalized = relative_path.replace("\\", "/")
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(
            ContextBundleItem(
                path=normalized,
                kind=kind,
                purpose=purpose,
                required_for=required_for,
                read_order=read_order,
                must_read=True,
                selection_reason=selection_reason,
            )
        )
        read_order += 1

    for reference in required_references:
        normalized = reference.path.replace("\\", "/")
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(
            ContextBundleItem(
                path=normalized,
                kind="task_reference",
                purpose=reference.reason,
                required_for=["forbidden_drift"],
                read_order=read_order,
                must_read=True,
                selection_reason="compiled from Required Implementation References",
            )
        )
        read_order += 1

    return items


def compile_worker_task_packet(
    *,
    project_root: Path,
    feature_dir: Path,
    task_id: str,
    task_body: str | None = None,
) -> WorkerTaskPacket:
    """Compile a delegated execution packet from constitution, plan, and tasks."""

    constitution_text = _read(project_root / ".specify" / "memory" / "constitution.md")
    plan_text = _read(feature_dir / "plan.md")
    tasks_text = _read(feature_dir / "tasks.md")

    resolved_task_body = task_body if task_body is not None else _task_body(tasks_text, task_id)
    objective = resolved_task_body

    required_references = [
        PacketReference(
            path=value,
            reason="compiled from Required Implementation References",
        )
        for value in _bullet_values(_section_body(plan_text, "Required Implementation References"))
    ]
    forbidden_drift = _bullet_values(_section_body(plan_text, "Forbidden Implementation Drift"))
    platform_guardrails = _section_or_subsection_values(
        plan_text,
        "Platform Guardrails",
        "Platform Constraints",
    )
    hard_rules = _unique(
        _bullet_values(constitution_text)
        + _bullet_values(_section_body(plan_text, "Task-Level Quality Floor"))
    )
    validation_gates = [
        value
        for value in _leading_bullet_values(_section_body(tasks_text, "Validation Gates"))
        if not value.startswith("[ ]")
    ]

    handoff_requirements = _unique(
        [
            "return changed files",
            "return validation results",
            "return blockers",
        ]
        + _section_or_subsection_values(
            plan_text,
            "Completion Handoff Protocol",
            "Result Handoff Requirements",
        )
    )

    if not platform_guardrails:
        platform_guardrails = [
            "Respect the repository's supported platforms and do not assume a platform-specific API is always available without evidence.",
            "Use conditional guards or equivalent isolation when implementation details differ across supported platforms.",
        ]

    context_bundle = _context_bundle_from_project_docs(
        project_root,
        required_references=required_references,
    )
    read_scope = _unique([item.path for item in context_bundle] + [ref.path for ref in required_references])

    packet = WorkerTaskPacket(
        feature_id=feature_dir.name,
        task_id=task_id,
        story_id=_story_id_from_task_body(resolved_task_body),
        objective=objective,
        intent=ExecutionIntent(
            outcome=objective,
            constraints=_unique([*forbidden_drift, *hard_rules]),
            success_signals=done_criteria if (done_criteria := [objective]) else [objective],
        ),
        scope=PacketScope(
            write_scope=_paths_from_task_body(resolved_task_body),
            read_scope=read_scope,
        ),
        context_bundle=context_bundle,
        required_references=required_references,
        hard_rules=hard_rules,
        forbidden_drift=forbidden_drift,
        validation_gates=validation_gates,
        done_criteria=done_criteria,
        handoff_requirements=handoff_requirements,
        platform_guardrails=platform_guardrails,
        consequence_obligations=_consequence_obligations_for_task(tasks_text, task_id),
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )
    return validate_worker_task_packet(packet)
