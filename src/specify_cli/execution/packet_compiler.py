"""Compile subagent execution packets from planning artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .packet_schema import (
    ConsequenceObligation,
    ContextBundleItem,
    DispatchPolicy,
    ExecutionIntent,
    MustPreserveObligation,
    PacketInterfaces,
    PacketReference,
    PacketScope,
    UI_CONTRACT_FIELDS,
    UIContract,
    WorkerTaskPacket,
)
from .packet_validator import PacketValidationError, validate_worker_task_packet


SECTION_RE = re.compile(
    r"(?ms)^#{2,3}\s+(?P<title>.+?)\n(?P<body>.*?)(?=^#{2,3}\s+|\Z)"
)
TASK_DETAIL_RE = re.compile(
    r"(?ms)^##\s+(?P<task_id>T\d+)\b[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)"
)
FENCED_CODE_BLOCK_RE = re.compile(r"(?ms)^```.*?^```")
BULLET_RE = re.compile(r"(?m)^\s*-\s+`?(?P<value>.+?)`?\s*$")
TASK_RE = re.compile(r"(?m)^\s*-\s\[[ xX]\]\s(?P<task_id>T\d+)(?P<body>.+)$")
PATH_RE = re.compile(r"[\w./-]+/[\w./-]+")
STORY_RE = re.compile(r"\[(US\d+)\]")
MP_LINE_RE = re.compile(r"\b(MP-\d{3})\b\s*:?\s*(?P<claim>.+)")
MP_ID_ONLY_RE = re.compile(r"\bMP-\d{3}\b")
CONSEQUENCE_ID_RE = re.compile(r"\bCA-\d{3}\b")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PacketValidationError(
            "DP0", f"{path.name} could not be read: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise PacketValidationError(
            "DP0", f"{path.name} is malformed JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PacketValidationError(
            "DP0", f"{path.name} must contain a top-level object"
        )
    return payload


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            for key in ("ref", "path", "id", "value"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    result.append(candidate.strip())
                    break
    return result


def _task_index_entry(payload: dict[str, object], task_id: str) -> dict[str, object]:
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return {}
    normalized = task_id.upper()
    for item in tasks:
        if not isinstance(item, dict):
            continue
        candidate = item.get("task_id", item.get("id"))
        if isinstance(candidate, str) and candidate.upper() == normalized:
            return item
    return {}


def _task_contract_mapping_body(tasks_text: str) -> str:
    return _section_body(tasks_text, "Task Contract Mapping") or _section_body(
        tasks_text, "Task Guardrail Index"
    )


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


def _without_fenced_code_blocks(text: str) -> str:
    return FENCED_CODE_BLOCK_RE.sub("", text)


def _task_detail_body(tasks_text: str, task_id: str) -> str:
    searchable_text = _without_fenced_code_blocks(tasks_text)
    for match in TASK_DETAIL_RE.finditer(searchable_text):
        if match.group("task_id") == task_id:
            return match.group("body").strip()
    return ""


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
    return bool(parts) and all(
        re.fullmatch(r":?-{3,}:?", part.strip()) for part in parts
    )


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


def _split_list_field(value: str) -> list[str]:
    normalized = value.strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    return [
        item.strip().strip("`\"'")
        for item in normalized.split(",")
        if item.strip().strip("`\"'")
    ]


def _task_detail_table_field_values(
    task_detail: str, section_title: str, field_name: str
) -> list[str]:
    section = _section_body(task_detail, section_title)
    values: list[str] = []
    expected_field = _normalized_header_name(field_name)
    for raw_line in section.splitlines():
        if not raw_line.strip().startswith("|"):
            continue
        parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
        if len(parts) < 2 or _is_table_separator(parts):
            continue
        if parts[0].strip().lower() == "field":
            continue
        if _normalized_header_name(parts[0]) == expected_field:
            values.extend(_split_list_field(parts[1]))
    return _unique(values)


def _mapping_string(payload: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _unique_dicts(values: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    ordered: list[dict[str, object]] = []
    for value in values:
        marker = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
        if marker not in seen:
            ordered.append(value)
            seen.add(marker)
    return ordered


def _ui_contract_from_task_entry(
    task_entry: dict[str, object],
) -> UIContract:
    if "ui_fidelity_requirements" in task_entry:
        raise PacketValidationError(
            "DP0", "task-index uses obsolete ui_fidelity_requirements"
        )
    payload = task_entry.get("ui_contract")
    if not isinstance(payload, dict):
        if "ui_contract" in task_entry:
            raise PacketValidationError(
                "DP0", "task-index ui_contract must be an object"
            )
        return UIContract()
    if not payload:
        raise PacketValidationError("DP0", "task-index ui_contract must not be empty")
    unknown_fields = set(payload) - UI_CONTRACT_FIELDS
    if unknown_fields:
        raise PacketValidationError(
            "DP0",
            "task-index ui_contract contains unsupported fields: "
            + ", ".join(sorted(unknown_fields)),
        )
    missing_fields = UI_CONTRACT_FIELDS - set(payload)
    if missing_fields:
        raise PacketValidationError(
            "DP0",
            "task-index ui_contract is missing current fields: "
            + ", ".join(sorted(missing_fields)),
        )
    return UIContract(
        ui_work_type=_mapping_string(payload, "ui_work_type"),
        surface_type=_mapping_string(payload, "surface_type"),
        platforms=_unique(_string_list(payload.get("platforms"))),
        subject=_mapping_string(payload, "subject"),
        audience=_mapping_string(payload, "audience"),
        single_job=_mapping_string(payload, "single_job"),
        visual_thesis=_mapping_string(payload, "visual_thesis"),
        content_thesis=_mapping_string(payload, "content_thesis"),
        interaction_thesis=_mapping_string(payload, "interaction_thesis"),
        signature_element=_mapping_string(payload, "signature_element"),
        approved_visual_ref=_mapping_string(payload, "approved_visual_ref"),
        design_sources=_unique(_string_list(payload.get("design_sources"))),
        reference_notes=_mapping_string(payload, "reference_notes"),
        visual_target=_mapping_string(payload, "visual_target"),
        reference_intents=_unique_dicts(_dict_list(payload.get("reference_intents"))),
        real_content_plan=_unique_dicts(_dict_list(payload.get("real_content_plan"))),
        image_plan=_unique_dicts(_dict_list(payload.get("image_plan"))),
        fidelity_level=_mapping_string(payload, "fidelity_level") or "none",
        must_preserve=_unique(_string_list(payload.get("must_preserve"))),
        may_adapt=_unique(_string_list(payload.get("may_adapt"))),
        must_not=_unique(_string_list(payload.get("must_not"))),
        required_states=_unique(_string_list(payload.get("required_states"))),
        required_evidence=_unique(_string_list(payload.get("required_evidence"))),
    )


def _line_mentions_task(line: str, task_id: str) -> bool:
    return any(
        part.strip() == task_id for part in re.split(r"[,;\s]+", line) if part.strip()
    )


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
        affected_objects = _split_csv_field(fields.get("affected_objects", "")) or [
            task_id
        ]
        stop_and_reopen_condition = fields.get(
            "stop_and_reopen_condition",
            f"No validation evidence supplied for {obligation_id}",
        )
        obligations.append(
            ConsequenceObligation(
                obligation_id=obligation_id,
                claim=fields.get(
                    "claim", f"{obligation_id} consequence obligation for {task_id}"
                ),
                affected_objects=affected_objects,
                state_behavior_refs=_split_csv_field(
                    fields.get("state_behavior_refs", "")
                ),
                dependency_refs=_split_csv_field(fields.get("dependency_refs", "")),
                recovery_validation_refs=_split_csv_field(fields.get("validation", "")),
                owner=fields.get("owner", "sp-tasks"),
                latest_resolve_phase=fields.get("latest_resolve_phase", "tasks"),
                status=fields.get("status", "open"),
                stop_and_reopen_condition=stop_and_reopen_condition,
            )
        )
    return obligations


def _does_not_remove_for_task(tasks_text: str, task_id: str) -> list[str]:
    values: list[str] = []
    guardrail_body = _task_contract_mapping_body(tasks_text)
    for line in guardrail_body.splitlines():
        if task_id not in line:
            continue
        match = re.search(
            r"does-not-remove guard:\s*(?P<value>.+)", line, re.IGNORECASE
        )
        if match:
            values.append(match.group("value").strip(" ."))
    return _unique(values)


def _capability_operations_for_task(tasks_text: str, task_id: str) -> list[str]:
    section = _section_body(tasks_text, "Capability Operation Coverage")
    operations: list[str] = []
    headers: list[str] | None = None
    for raw_line in section.splitlines():
        if raw_line.strip().startswith("|"):
            parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
            if _is_table_separator(parts):
                continue
            if any(part.strip().lower() == "operation" for part in parts):
                headers = [_normalized_header_name(part) for part in parts]
                continue
        if not _line_mentions_task(raw_line, task_id):
            continue
        fields = _parse_pipe_fields(raw_line, headers)
        operation = fields.get("operation", "").strip()
        entry_point = fields.get("selected_entry_point", "").strip()
        if operation and entry_point:
            operations.append(f"{operation} -> {entry_point}")
        elif operation:
            operations.append(operation)
    return _unique(operations)


def _section_or_subsection_values(text: str, *titles: str) -> list[str]:
    values: list[str] = []
    for title in titles:
        values.extend(_bullet_values(_section_body(text, title)))
    return _unique(values)


def _task_contract_bullet_values(task_detail: str, *titles: str) -> list[str]:
    return [
        value
        for value in _section_or_subsection_values(task_detail, *titles)
        if not re.match(r"\[[ xX]\]\s*T\d+\b", value)
    ]


def _must_preserve_obligations_from_text(
    text: str, *, source: str
) -> list[MustPreserveObligation]:
    obligations: list[MustPreserveObligation] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = MP_LINE_RE.search(line)
        if not match:
            continue
        mp_id = match.group(1)
        if mp_id in seen:
            continue
        seen.add(mp_id)
        claim = match.group("claim").strip(" -|")
        obligations.append(
            MustPreserveObligation(
                id=mp_id,
                type="execution",
                claim=claim or line.strip(),
                source=source,
                downstream_requirement="Preserve this discussion-derived obligation during implementation.",
                mapped_to=[source],
            )
        )
    return obligations


def _applicable_mp_ids_from_tasks(
    tasks_text: str, task_id: str, task_body: str
) -> set[str]:
    applicable = set(MP_ID_ONLY_RE.findall(task_body))
    guardrail_body = _task_contract_mapping_body(tasks_text)
    for line in guardrail_body.splitlines():
        if task_id not in line:
            continue
        applicable.update(MP_ID_ONLY_RE.findall(line))
    return applicable


def _global_must_preserve_ids(plan_text: str) -> set[str]:
    ids: set[str] = set()
    for line in plan_text.splitlines():
        lowered = line.lower()
        if (
            "applies to all" not in lowered
            and "all implementation tasks" not in lowered
        ):
            continue
        ids.update(MP_ID_ONLY_RE.findall(line))
    return ids


def _unique_obligations(
    values: list[MustPreserveObligation],
) -> list[MustPreserveObligation]:
    seen: set[str] = set()
    unique: list[MustPreserveObligation] = []
    for value in values:
        if value.id in seen:
            continue
        seen.add(value.id)
        unique.append(value)
    return unique


def _unique_consequence_obligations(
    values: list[ConsequenceObligation],
) -> list[ConsequenceObligation]:
    seen: set[str] = set()
    unique: list[ConsequenceObligation] = []
    for value in values:
        if value.obligation_id in seen:
            continue
        seen.add(value.obligation_id)
        unique.append(value)
    return unique


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


def _plan_contract(feature_dir: Path) -> dict[str, object]:
    direct = _read_json_object(feature_dir / "plan-contract.json")
    if direct:
        return direct
    return _read_json_object(feature_dir / "plan" / "plan-contract.json")


def _ui_context_nav(
    plan_contract: dict[str, object],
    ui_contract: UIContract,
) -> list[dict[str, str]]:
    if ui_contract.fidelity_level == "none" and not ui_contract.design_sources:
        return []
    ui_plan = plan_contract.get("ui_design_contract")
    context_capsule = plan_contract.get("context_capsule")
    ui_plan = ui_plan if isinstance(ui_plan, dict) else {}
    context_capsule = context_capsule if isinstance(context_capsule, dict) else {}
    candidates: list[tuple[str, str, str]] = []

    def add(kind: str, values: list[str], source: str) -> None:
        candidates.extend((kind, value, source) for value in values if value)

    add(
        "ui_entrypoint", _string_list(ui_plan.get("entry_points")), "plan-contract.json"
    )
    add("design_source", ui_contract.design_sources, "task-index.json")
    add(
        "token_component_route",
        _string_list(ui_plan.get("token_strategy"))
        + _string_list(ui_plan.get("component_strategy")),
        "plan-contract.json",
    )
    add(
        "minimal_live_read",
        _string_list(context_capsule.get("minimal_live_reads")),
        "plan-contract.json#/context_capsule",
    )
    add(
        "visual_test_route",
        _string_list(context_capsule.get("validation_routes")),
        "plan-contract.json#/context_capsule",
    )
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for kind, value, source in candidates:
        marker = (kind, value, source)
        if marker in seen:
            continue
        seen.add(marker)
        result.append({"kind": kind, "value": value, "source": source})
    return result


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
    task_index = _read_json_object(feature_dir / "task-index.json")
    plan_contract = _plan_contract(feature_dir)
    task_entry = _task_index_entry(task_index, task_id)
    task_index_version = task_index.get("version")
    canonical_task_index = (
        isinstance(task_index_version, int)
        and not isinstance(task_index_version, bool)
        and task_index_version >= 2
    )
    if canonical_task_index and not task_entry:
        raise PacketValidationError(
            "DP0", f"{task_id} is missing from canonical task-index.json"
        )

    indexed_objective = str(task_entry.get("objective") or "").strip()
    resolved_task_body = (
        task_body
        if task_body is not None
        else indexed_objective or _task_body(tasks_text, task_id)
    )
    task_detail = _task_detail_body(tasks_text, task_id)
    objective = resolved_task_body
    if (
        "### UI Implementation Contract" in task_detail
        and "ui_contract" not in task_entry
    ):
        raise PacketValidationError(
            "DP0",
            f"{task_id} has a UI projection but no canonical task-index ui_contract",
        )
    ui_contract = _ui_contract_from_task_entry(task_entry)
    review_inputs = _task_detail_table_field_values(
        task_detail,
        "Scope Boundaries",
        "review_inputs",
    )

    required_references = [
        PacketReference(
            path=value,
            reason="compiled from Required Implementation References",
        )
        for value in _bullet_values(
            _section_body(plan_text, "Required Implementation References")
        )
    ]
    for value in _unique(
        _string_list(task_entry.get("required_refs"))
        + _string_list(task_entry.get("authoritative_refs"))
        + _string_list(task_entry.get("fidelity_refs"))
    ):
        if value not in {reference.path for reference in required_references}:
            required_references.append(
                PacketReference(path=value, reason="canonical task-index reference")
            )
    existing_reference_paths = {reference.path for reference in required_references}
    ui_reference_candidates = [
        *ui_contract.design_sources,
        *review_inputs,
        ui_contract.approved_visual_ref,
        ui_contract.reference_notes,
        ui_contract.visual_target,
        *[
            str(item.get("ref") or "").strip()
            for item in ui_contract.reference_intents
            if isinstance(item, dict)
        ],
        *[
            str(item.get("source_ref") or "").strip()
            for item in ui_contract.real_content_plan
            if isinstance(item, dict)
        ],
        *[
            str(item.get("ref") or "").strip()
            for item in ui_contract.image_plan
            if isinstance(item, dict)
        ],
    ]
    for value in ui_reference_candidates:
        if not value or value in existing_reference_paths:
            continue
        required_references.append(
            PacketReference(
                path=value,
                reason="UI implementation contract reference",
            )
        )
        existing_reference_paths.add(value)
    forbidden_drift = _unique(
        _bullet_values(_section_body(plan_text, "Forbidden Implementation Drift"))
        + _task_detail_table_field_values(task_detail, "Scope Boundaries", "forbidden")
        + _string_list(task_entry.get("forbidden_drift"))
    )
    platform_guardrails = _section_or_subsection_values(
        plan_text,
        "Platform Guardrails",
        "Platform Constraints",
    )
    hard_rules = _unique(
        _bullet_values(constitution_text)
        + _bullet_values(_section_body(plan_text, "Task-Level Quality Floor"))
        + _string_list(task_entry.get("hard_rules"))
    )
    validation_gates = [
        value
        for value in _leading_bullet_values(
            _section_body(tasks_text, "Validation Gates")
        )
        if not value.startswith("[ ]")
    ]
    validation_gates = _unique(
        validation_gates
        + _string_list(task_entry.get("verification"))
        + _string_list(task_entry.get("required_validation"))
    )

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
    context_nav = _ui_context_nav(plan_contract, ui_contract)
    existing_context_paths = {item.path for item in context_bundle}
    next_read_order = max((item.read_order for item in context_bundle), default=0) + 1
    for item in context_nav:
        if item["kind"] != "minimal_live_read":
            continue
        path = item["value"]
        if not path or "://" in path or path in existing_context_paths:
            continue
        context_bundle.append(
            ContextBundleItem(
                path=path,
                kind="task_reference",
                purpose="Live UI owner or boundary read selected by the planning cognition capsule.",
                required_for=["ui_implementation", "live_verification"],
                read_order=next_read_order,
                must_read=True,
                selection_reason="carried from plan-contract context_capsule minimal_live_reads",
            )
        )
        existing_context_paths.add(path)
        next_read_order += 1
    read_scope = _unique(
        [item.path for item in context_bundle]
        + [ref.path for ref in required_references]
    )
    scope_write_scope = _unique(
        _paths_from_task_body(resolved_task_body)
        + _task_detail_table_field_values(
            task_detail, "Scope Boundaries", "write_scope"
        )
        + _string_list(task_entry.get("expected_write_scope"))
        + _string_list(task_entry.get("write_scope"))
    )
    scope_read_scope = _unique(
        read_scope
        + _task_detail_table_field_values(task_detail, "Scope Boundaries", "read_scope")
        + _string_list(task_entry.get("read_scope"))
    )
    indexed_mp_ids = set(_string_list(task_entry.get("must_preserve_refs")))
    applicable_mp_ids = (
        _applicable_mp_ids_from_tasks(tasks_text, task_id, resolved_task_body)
        | _global_must_preserve_ids(plan_text)
        | indexed_mp_ids
    )
    must_preserve_obligations = _unique_obligations(
        [
            *[
                obligation
                for obligation in _must_preserve_obligations_from_text(
                    plan_text, source="plan.md"
                )
                if not applicable_mp_ids or obligation.id in applicable_mp_ids
            ],
            *[
                obligation
                for obligation in _must_preserve_obligations_from_text(
                    tasks_text, source="tasks.md"
                )
                if not applicable_mp_ids or obligation.id in applicable_mp_ids
            ],
        ]
    )
    existing_mp_ids = {item.id for item in must_preserve_obligations}
    must_preserve_obligations.extend(
        MustPreserveObligation(
            id=mp_id,
            type="execution",
            claim=f"Preserve canonical obligation {mp_id}",
            source="task-index.json",
            downstream_requirement="Preserve this task-relevant obligation during implementation.",
            mapped_to=[f"task-index.json#/tasks/{task_id}"],
        )
        for mp_id in sorted(indexed_mp_ids - existing_mp_ids)
        if MP_ID_ONLY_RE.fullmatch(mp_id)
    )

    indexed_consequence_obligations = [
        ConsequenceObligation(
            obligation_id=obligation_id,
            claim=f"Satisfy canonical consequence obligation {obligation_id}",
            affected_objects=[task_id],
            recovery_validation_refs=validation_gates,
            owner="sp-implement",
            latest_resolve_phase="implement",
            status="open",
            stop_and_reopen_condition=f"Required evidence for {obligation_id} cannot be produced",
        )
        for obligation_id in _string_list(task_entry.get("consequence_obligation_refs"))
        if CONSEQUENCE_ID_RE.fullmatch(obligation_id)
    ]

    packet = WorkerTaskPacket(
        feature_id=feature_dir.name,
        task_id=task_id,
        story_id=_story_id_from_task_body(resolved_task_body),
        objective=objective,
        intent=ExecutionIntent(
            outcome=objective,
            constraints=_unique([*forbidden_drift, *hard_rules]),
            success_signals=done_criteria
            if (done_criteria := [objective])
            else [objective],
        ),
        scope=PacketScope(
            write_scope=scope_write_scope,
            read_scope=scope_read_scope,
        ),
        context_bundle=context_bundle,
        required_references=required_references,
        hard_rules=hard_rules,
        forbidden_drift=forbidden_drift,
        validation_gates=validation_gates,
        done_criteria=_unique(
            done_criteria
            + _string_list(task_entry.get("acceptance"))
            + _string_list(task_entry.get("acceptance_refs"))
        ),
        handoff_requirements=handoff_requirements,
        platform_guardrails=platform_guardrails,
        context_nav=context_nav,
        anti_goals=_task_contract_bullet_values(task_detail, "Anti-Goals"),
        does_not_remove=_unique(
            _does_not_remove_for_task(tasks_text, task_id)
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "does_not_remove"
            )
        ),
        capability_operations=_unique(
            _capability_operations_for_task(tasks_text, task_id)
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "capability_operations"
            )
            + _string_list(task_entry.get("capability_operation_refs"))
        ),
        verify_commands=_unique(
            _task_contract_bullet_values(
                task_detail, "Verify Commands", "Verification Commands"
            )
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "verify_commands"
            )
            + _string_list(task_entry.get("verification"))
            + _string_list(task_entry.get("required_validation"))
        ),
        acceptance_criteria=_unique(
            _task_contract_bullet_values(task_detail, "Acceptance Criteria")
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "acceptance_criteria"
            )
            + _string_list(task_entry.get("acceptance"))
            + _string_list(task_entry.get("acceptance_refs"))
        ),
        consumer_surfaces=_unique(
            _task_contract_bullet_values(task_detail, "Consumer Surfaces")
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "consumer_surfaces"
            )
        ),
        required_evidence=_unique(
            _task_contract_bullet_values(task_detail, "Required Evidence")
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "required_evidence"
            )
            + _string_list(task_entry.get("required_consumer_evidence"))
            + _string_list(task_entry.get("required_evidence"))
        ),
        global_constraints=_unique(
            _section_or_subsection_values(
                plan_text,
                "Global Constraints",
                "Profile-Driven Implementation Constraints",
            )
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "global_constraints"
            )
        ),
        interfaces=PacketInterfaces(
            consumes=_task_detail_table_field_values(
                task_detail, "Scope Boundaries", "consumes"
            ),
            produces=_task_detail_table_field_values(
                task_detail, "Scope Boundaries", "produces"
            ),
        ),
        review_inputs=review_inputs,
        review_risks=_unique(
            _section_or_subsection_values(plan_text, "Review-Risk Notes")
            + _task_detail_table_field_values(
                task_detail, "Scope Boundaries", "review_risks"
            )
        ),
        controller_checks_required=_task_detail_table_field_values(
            task_detail,
            "Scope Boundaries",
            "controller_checks_required",
        ),
        ui_contract=ui_contract,
        must_preserve_obligations=must_preserve_obligations,
        consequence_obligations=_unique_consequence_obligations(
            _consequence_obligations_for_task(tasks_text, task_id)
            + indexed_consequence_obligations
        ),
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )
    return validate_worker_task_packet(packet)
