from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
import yaml

from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.hooks.checkpoint_serializers import (
    parse_frontmatter,
    serialize_workflow_state,
)
from specify_cli.verification import summarize_validation_results


LEARNING_TYPES = {
    "pitfall",
    "recovery_path",
    "user_preference",
    "workflow_gap",
    "project_constraint",
    "routing_mistake",
    "verification_gap",
    "state_surface_gap",
    "map_coverage_gap",
    "tooling_trap",
    "false_lead_pattern",
    "near_miss",
    "decision_debt",
}
LEARNING_STATUSES = {
    "candidate",
    "confirmed",
    "promoted-rule",
    "promoted-constitution",
}
SIGNAL_STRENGTHS = {"low", "medium", "high"}
PROMOTION_TARGETS = {"learning", "rule"}
MAP_WORKFLOW_COMMANDS = ("sp-map-scan", "sp-map-build")
KNOWN_COMMANDS = (
    "sp-constitution",
    "sp-specify",
    "sp-clarify",
    "sp-deep-research",
    "sp-plan",
    "sp-checklist",
    "sp-tasks",
    "sp-analyze",
    "sp-test-scan",
    "sp-test-build",
    "sp-implement",
    "sp-debug",
    "sp-fast",
    "sp-quick",
    *MAP_WORKFLOW_COMMANDS,
)
COMMAND_ALIASES = {
    "sp-research": "sp-deep-research",
}

MACHINE_BEGIN = "<!-- SPECKIT_LEARNING_DATA_BEGIN -->"
MACHINE_END = "<!-- SPECKIT_LEARNING_DATA_END -->"

RULES_TEMPLATE_TEXT = (
    "# Project Rules\n\n"
    "Shared defaults that later `sp-xxx` workflows should follow across specification,\n"
    "planning, implementation, debugging, and quick-task execution.\n\n"
    "Promote only stable project rules here. Keep one-off observations in passive\n"
    "candidate learning files until recurrence or explicit confirmation proves they\n"
    "belong in this shared rule layer.\n\n"
    "---\n"
)
LEARNINGS_TEMPLATE_TEXT = (
    "# Project Learnings\n\n"
    "Confirmed project learnings that are reusable across later `sp-xxx` workflows\n"
    "but are not yet strong enough to become project rules or constitution-level\n"
    "principles.\n\n"
    "Promote items here after recurrence, explicit confirmation, or clear\n"
    "cross-stage usefulness. Keep noisy or unproven observations in passive candidate\n"
    "learning files until they mature.\n\n"
    "---\n"
)
CANDIDATES_TEMPLATE_TEXT = (
    "# Candidate Learnings\n\n"
    "Passive candidate learnings captured from `sp-xxx` workflows.\n\n"
    "---\n"
)
REVIEW_TEMPLATE_TEXT = (
    "# Learning Review\n\n"
    "Pending recurrence, confirmation, and promotion notes for passive project learning.\n\n"
    "---\n"
)


@dataclass(frozen=True)
class LearningPaths:
    constitution: Path
    project_rules: Path
    project_learnings: Path
    candidates: Path
    review: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "constitution": str(self.constitution),
            "project_rules": str(self.project_rules),
            "project_learnings": str(self.project_learnings),
            "candidates": str(self.candidates),
            "review": str(self.review),
        }


@dataclass
class LearningEntry:
    id: str
    summary: str
    learning_type: str
    source_command: str
    evidence: str
    recurrence_key: str
    default_scope: str
    applies_to: list[str]
    signal_strength: str
    status: str
    first_seen: str
    last_seen: str
    occurrence_count: int = 1
    pain_score: int = 0
    false_starts: list[str] = field(default_factory=list)
    rejected_paths: list[str] = field(default_factory=list)
    decisive_signal: str = ""
    root_cause_family: str = ""
    injection_targets: list[str] = field(default_factory=list)
    promotion_hint: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LearningEntry":
        applies_to = payload.get("applies_to") or []
        if not isinstance(applies_to, list):
            applies_to = []
        return cls(
            id=str(payload["id"]),
            summary=str(payload["summary"]),
            learning_type=str(payload["learning_type"]),
            source_command=normalize_command_name(payload["source_command"]),
            evidence=str(payload["evidence"]),
            recurrence_key=str(payload["recurrence_key"]),
            default_scope=str(payload["default_scope"]),
            applies_to=[normalize_command_name(item) for item in applies_to],
            signal_strength=str(payload["signal_strength"]),
            status=str(payload["status"]),
            first_seen=str(payload["first_seen"]),
            last_seen=str(payload["last_seen"]),
            occurrence_count=int(payload.get("occurrence_count", 1)),
            pain_score=_coerce_int(payload.get("pain_score")),
            false_starts=_coerce_str_list(payload.get("false_starts")),
            rejected_paths=_coerce_str_list(payload.get("rejected_paths")),
            decisive_signal=str(payload.get("decisive_signal") or ""),
            root_cause_family=str(payload.get("root_cause_family") or ""),
            injection_targets=_coerce_str_list(payload.get("injection_targets")),
            promotion_hint=str(payload.get("promotion_hint") or ""),
        )


@dataclass(frozen=True)
class AutoCaptureSuggestion:
    learning_type: str
    summary: str
    evidence: str
    recurrence_key: str
    signal_strength: str = "medium"
    applies_to: tuple[str, ...] | None = None


def build_learning_paths(project_root: Path) -> LearningPaths:
    memory_dir = project_root / ".specify" / "memory"
    learning_dir = project_root / ".planning" / "learnings"
    return LearningPaths(
        constitution=memory_dir / "constitution.md",
        project_rules=memory_dir / "project-rules.md",
        project_learnings=memory_dir / "project-learnings.md",
        candidates=learning_dir / "candidates.md",
        review=learning_dir / "review.md",
    )


def now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_command_name(command_name: str) -> str:
    raw = str(command_name or "").strip().lower()
    if not raw:
        raise ValueError("command name is required")
    if raw.startswith("sp-"):
        normalized = raw
    elif raw.startswith("sp."):
        normalized = f"sp-{raw[3:]}"
    else:
        normalized = f"sp-{raw}"
    return COMMAND_ALIASES.get(normalized, normalized)


def _slugify(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return lowered or "learning"


def default_scope_for_type(learning_type: str) -> str:
    normalized = learning_type.strip().lower()
    if normalized in {"user_preference", "project_constraint"}:
        return "global"
    if normalized in {"workflow_gap", "routing_mistake", "state_surface_gap", "decision_debt"}:
        return "planning-heavy"
    if normalized in {"recovery_path", "verification_gap", "false_lead_pattern"}:
        return "execution-heavy"
    if normalized in {"map_coverage_gap", "tooling_trap", "near_miss"}:
        return "cross-workflow"
    return "implementation-heavy"


def default_applies_to_for_type(learning_type: str, source_command: str) -> list[str]:
    normalized_type = learning_type.strip().lower()
    normalized_source = normalize_command_name(source_command)
    if normalized_type in {"user_preference", "project_constraint"}:
        return list(KNOWN_COMMANDS)
    if normalized_type == "workflow_gap":
        return ["sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-quick"]
    if normalized_type == "routing_mistake":
        return ["sp-fast", "sp-quick", "sp-specify", "sp-plan", "sp-tasks", "sp-implement", "sp-debug"]
    if normalized_type == "verification_gap":
        return ["sp-test-scan", "sp-test-build", "sp-implement", "sp-debug", "sp-quick"]
    if normalized_type == "state_surface_gap":
        return [
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-debug",
            "sp-quick",
            *MAP_WORKFLOW_COMMANDS,
        ]
    if normalized_type == "map_coverage_gap":
        return [*MAP_WORKFLOW_COMMANDS, "sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-implement", "sp-debug"]
    if normalized_type == "tooling_trap":
        return ["sp-implement", "sp-debug", "sp-quick", *MAP_WORKFLOW_COMMANDS]
    if normalized_type == "false_lead_pattern":
        return ["sp-debug", "sp-implement", "sp-quick"]
    if normalized_type == "near_miss":
        return sorted({normalized_source, "sp-implement", "sp-debug", "sp-quick"})
    if normalized_type == "decision_debt":
        return ["sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", *MAP_WORKFLOW_COMMANDS]
    if normalized_type == "recovery_path":
        return ["sp-implement", "sp-debug", "sp-quick"]
    if normalized_type == "pitfall":
        return sorted({normalized_source, "sp-implement", "sp-debug", "sp-quick"})
    return [normalized_source]


def normalize_learning_type(learning_type: str) -> str:
    normalized = learning_type.strip().lower()
    if normalized not in LEARNING_TYPES:
        raise ValueError(f"unsupported learning type '{learning_type}'")
    return normalized


def normalize_signal_strength(signal_strength: str) -> str:
    normalized = signal_strength.strip().lower()
    if normalized not in SIGNAL_STRENGTHS:
        raise ValueError(f"unsupported signal strength '{signal_strength}'")
    return normalized


def normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in LEARNING_STATUSES:
        raise ValueError(f"unsupported learning status '{status}'")
    return normalized


def derive_recurrence_key(learning_type: str, summary: str) -> str:
    return f"{normalize_learning_type(learning_type)}.{_slugify(summary)}"


def build_learning_id() -> str:
    return datetime.now(tz=UTC).strftime("LRN-%Y%m%d-%H%M%S-%f")


def build_learning_entry(
    *,
    command_name: str,
    learning_type: str,
    summary: str,
    evidence: str,
    recurrence_key: str | None = None,
    signal_strength: str = "medium",
    applies_to: Iterable[str] | None = None,
    default_scope: str | None = None,
    status: str = "candidate",
    pain_score: int | None = None,
    false_starts: Iterable[str] | None = None,
    rejected_paths: Iterable[str] | None = None,
    decisive_signal: str | None = None,
    root_cause_family: str | None = None,
    injection_targets: Iterable[str] | None = None,
    promotion_hint: str | None = None,
) -> LearningEntry:
    normalized_command = normalize_command_name(command_name)
    normalized_type = normalize_learning_type(learning_type)
    normalized_signal = normalize_signal_strength(signal_strength)
    normalized_status = normalize_status(status)
    normalized_applies = (
        [normalize_command_name(item) for item in applies_to]
        if applies_to
        else default_applies_to_for_type(normalized_type, normalized_command)
    )
    timestamp = now_iso()
    return LearningEntry(
        id=build_learning_id(),
        summary=summary.strip(),
        learning_type=normalized_type,
        source_command=normalized_command,
        evidence=evidence.strip(),
        recurrence_key=(recurrence_key or derive_recurrence_key(normalized_type, summary)).strip().lower(),
        default_scope=(default_scope or default_scope_for_type(normalized_type)).strip().lower(),
        applies_to=sorted(dict.fromkeys(normalized_applies)),
        signal_strength=normalized_signal,
        status=normalized_status,
        first_seen=timestamp,
        last_seen=timestamp,
        occurrence_count=1,
        pain_score=max(0, _coerce_int(pain_score)),
        false_starts=sorted(dict.fromkeys(str(item).strip() for item in (false_starts or []) if str(item).strip())),
        rejected_paths=sorted(dict.fromkeys(str(item).strip() for item in (rejected_paths or []) if str(item).strip())),
        decisive_signal=str(decisive_signal or "").strip(),
        root_cause_family=str(root_cause_family or "").strip(),
        injection_targets=sorted(dict.fromkeys(str(item).strip() for item in (injection_targets or []) if str(item).strip())),
        promotion_hint=str(promotion_hint or "").strip(),
    )


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            return int(stripped)
        except ValueError:
            return 0
    return 0


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, list):
        return []
    values: list[str] = []
    for item in value:
        if item is None:
            continue
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                values.append(stripped)
            continue
        if isinstance(item, dict):
            dumped = yaml.safe_dump(item, sort_keys=False).strip()
            if dumped:
                values.append(dumped)
            continue
        dumped = str(item).strip()
        if dumped:
            values.append(dumped)
    return values


def _coerce_dict_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        return []
    values: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            values.append(item)
    return values


def _coerce_section_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, list):
        return {}
    merged: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        for key, nested in item.items():
            merged[str(key)] = nested
    return merged


def _coerce_grouped_mapping_list(value: Any, *, group_key: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    items: list[Any]
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict):
        items = [value]
    else:
        return []

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        grouped = item.get(group_key)
        mapping = _coerce_section_mapping(grouped)
        if mapping:
            results.append(mapping)
    return results


def _load_sectioned_markdown(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    frontmatter: dict[str, Any] = {}
    body = text
    parsed_frontmatter, parsed_body = parse_frontmatter(text)
    if parsed_frontmatter:
        frontmatter = dict(parsed_frontmatter)
        body = parsed_body

    sections: dict[str, Any] = {}
    current_section: str | None = None
    current_lines: list[str] = []
    for raw_line in body.splitlines():
        match = re.match(r"^##\s+(?P<title>.+?)\s*$", raw_line)
        if match:
            if current_section is not None:
                section_text = "\n".join(current_lines).strip()
                sections[current_section] = yaml.safe_load(section_text) if section_text else None
            current_section = match.group("title").strip()
            current_lines = []
            continue
        if current_section is not None:
            current_lines.append(raw_line)
    if current_section is not None:
        section_text = "\n".join(current_lines).strip()
        sections[current_section] = yaml.safe_load(section_text) if section_text else None
    return frontmatter, sections


def _auto_capture_registry_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / "auto-capture.json"


def _load_auto_capture_registry(project_root: Path) -> dict[str, Any]:
    path = _auto_capture_registry_path(project_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_auto_capture_registry(project_root: Path, payload: dict[str, Any]) -> None:
    path = _auto_capture_registry_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _snapshot_fingerprint(
    command_name: str,
    source_path: Path,
    suggestions: list[AutoCaptureSuggestion],
) -> str:
    normalized_payload = {
        "command": normalize_command_name(command_name),
        "source_path": str(source_path.resolve()),
        "suggestions": [
            {
                "learning_type": item.learning_type,
                "summary": item.summary,
                "evidence": item.evidence,
                "recurrence_key": item.recurrence_key,
                "signal_strength": item.signal_strength,
                "applies_to": list(item.applies_to or ()),
            }
            for item in suggestions
        ],
    }
    payload = json.dumps(normalized_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _extract_payload_block(content: str) -> tuple[str, list[dict[str, Any]]]:
    if MACHINE_BEGIN not in content or MACHINE_END not in content:
        return content.rstrip(), []
    before, rest = content.split(MACHINE_BEGIN, 1)
    payload_text, _after = rest.split(MACHINE_END, 1)
    payload_text = payload_text.strip()
    if not payload_text:
        return before.rstrip(), []
    payload = json.loads(payload_text)
    if not isinstance(payload, list):
        raise ValueError("learning payload must be a list")
    return before.rstrip(), payload


def _render_entry_summary(entry: LearningEntry) -> str:
    applies = ", ".join(entry.applies_to)
    base = (
        f"### {entry.id} - {entry.summary}\n\n"
        f"- Status: `{entry.status}`\n"
        f"- Type: `{entry.learning_type}`\n"
        f"- Source Command: `{entry.source_command}`\n"
        f"- Recurrence Key: `{entry.recurrence_key}`\n"
        f"- Scope: `{entry.default_scope}`\n"
        f"- Applies To: {applies}\n"
        f"- Signal: `{entry.signal_strength}`\n"
        f"- Occurrence Count: {entry.occurrence_count}\n"
        f"- First Seen: `{entry.first_seen}`\n"
        f"- Last Seen: `{entry.last_seen}`\n\n"
        f"#### Evidence\n\n{entry.evidence}\n"
    )
    structured_lines: list[str] = []
    if entry.pain_score:
        structured_lines.append(f"- Pain Score: `{entry.pain_score}`")
    if entry.false_starts:
        structured_lines.append(f"- False Starts: {', '.join(entry.false_starts)}")
    if entry.rejected_paths:
        structured_lines.append(f"- Rejected Paths: {', '.join(entry.rejected_paths)}")
    if entry.decisive_signal:
        structured_lines.append(f"- Decisive Signal: {entry.decisive_signal}")
    if entry.root_cause_family:
        structured_lines.append(f"- Root Cause Family: `{entry.root_cause_family}`")
    if entry.injection_targets:
        structured_lines.append(f"- Injection Targets: {', '.join(entry.injection_targets)}")
    if entry.promotion_hint:
        structured_lines.append(f"- Promotion Hint: {entry.promotion_hint}")
    if not structured_lines:
        return base
    return f"{base}\n#### Structured Learning\n\n" + "\n".join(structured_lines) + "\n"


def _render_learning_file(preamble: str, entries: list[LearningEntry]) -> str:
    payload = [entry.to_payload() for entry in entries]
    sections = [
        preamble.rstrip(),
        "",
        MACHINE_BEGIN,
        json.dumps(payload, ensure_ascii=False, indent=2),
        MACHINE_END,
        "",
        "## Managed Entries",
        "",
    ]
    if not entries:
        sections.append("_No entries recorded yet._")
    else:
        sections.append("\n\n---\n\n".join(_render_entry_summary(entry) for entry in entries))
    sections.append("")
    return "\n".join(sections)


def _read_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    if not path.exists():
        return "", []
    preamble, payloads = _extract_payload_block(path.read_text(encoding="utf-8"))
    return preamble, [LearningEntry.from_payload(payload) for payload in payloads]


def read_learning_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    return _read_entries(path)


def _write_entries(path: Path, preamble: str, entries: list[LearningEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_learning_file(preamble, entries), encoding="utf-8")


def _seed_from_template(destination: Path, template_path: Path, fallback_text: str) -> bool:
    if destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if template_path.is_file():
        destination.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        destination.write_text(fallback_text, encoding="utf-8")
    return True


def ensure_learning_memory_from_templates(
    project_root: Path,
    tracker: Any | None = None,
) -> LearningPaths:
    paths = build_learning_paths(project_root)
    templates_root = project_root / ".specify" / "templates"
    created: list[str] = []

    if _seed_from_template(
        paths.project_rules,
        templates_root / "project-rules-template.md",
        RULES_TEMPLATE_TEXT,
    ):
        created.append("project-rules.md")
    if _seed_from_template(
        paths.project_learnings,
        templates_root / "project-learnings-template.md",
        LEARNINGS_TEMPLATE_TEXT,
    ):
        created.append("project-learnings.md")

    if tracker:
        tracker.add("learning-memory", "Project learning memory")
        if created:
            tracker.complete("learning-memory", ", ".join(created))
        else:
            tracker.skip("learning-memory", "existing files preserved")

    return paths


def ensure_learning_runtime_files(project_root: Path) -> LearningPaths:
    paths = build_learning_paths(project_root)
    _seed_from_template(paths.candidates, Path(""), CANDIDATES_TEMPLATE_TEXT)
    _seed_from_template(paths.review, Path(""), REVIEW_TEMPLATE_TEXT)
    return paths


def ensure_learning_files(
    project_root: Path,
    *,
    include_runtime: bool = True,
    tracker: Any | None = None,
) -> LearningPaths:
    paths = ensure_learning_memory_from_templates(project_root, tracker=tracker)
    if include_runtime:
        ensure_learning_runtime_files(project_root)
    return paths


def _merge_entry(existing: LearningEntry, new_entry: LearningEntry, *, status: str | None = None) -> LearningEntry:
    merged_applies = sorted(dict.fromkeys([*existing.applies_to, *new_entry.applies_to]))
    merged_false_starts = sorted(dict.fromkeys([*existing.false_starts, *new_entry.false_starts]))
    merged_rejected_paths = sorted(dict.fromkeys([*existing.rejected_paths, *new_entry.rejected_paths]))
    merged_injection_targets = sorted(dict.fromkeys([*existing.injection_targets, *new_entry.injection_targets]))
    merged_status = status or existing.status
    merged_signal = (
        "high"
        if "high" in {existing.signal_strength, new_entry.signal_strength}
        else "medium"
        if "medium" in {existing.signal_strength, new_entry.signal_strength}
        else "low"
    )
    return LearningEntry(
        id=existing.id,
        summary=new_entry.summary or existing.summary,
        learning_type=existing.learning_type,
        source_command=new_entry.source_command or existing.source_command,
        evidence=new_entry.evidence or existing.evidence,
        recurrence_key=existing.recurrence_key,
        default_scope=new_entry.default_scope or existing.default_scope,
        applies_to=merged_applies,
        signal_strength=merged_signal,
        status=merged_status,
        first_seen=existing.first_seen,
        last_seen=new_entry.last_seen,
        occurrence_count=existing.occurrence_count + 1,
        pain_score=max(existing.pain_score, new_entry.pain_score),
        false_starts=merged_false_starts,
        rejected_paths=merged_rejected_paths,
        decisive_signal=new_entry.decisive_signal or existing.decisive_signal,
        root_cause_family=new_entry.root_cause_family or existing.root_cause_family,
        injection_targets=merged_injection_targets,
        promotion_hint=new_entry.promotion_hint or existing.promotion_hint,
    )


def _upsert_entry(entries: list[LearningEntry], new_entry: LearningEntry, *, status: str | None = None) -> tuple[list[LearningEntry], LearningEntry]:
    updated = list(entries)
    for index, existing in enumerate(updated):
        if existing.recurrence_key == new_entry.recurrence_key:
            merged = _merge_entry(existing, new_entry, status=status)
            updated[index] = merged
            return updated, merged
    if status:
        new_entry.status = status
    updated.append(new_entry)
    return updated, new_entry


def _remove_by_recurrence(entries: list[LearningEntry], recurrence_key: str) -> list[LearningEntry]:
    return [entry for entry in entries if entry.recurrence_key != recurrence_key]


def _append_review_note(path: Path, note: str) -> None:
    timestamp = now_iso()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(REVIEW_TEMPLATE_TEXT, encoding="utf-8")
    content = path.read_text(encoding="utf-8").rstrip()
    content += f"\n- `{timestamp}` {note}\n"
    path.write_text(content + "\n", encoding="utf-8")


def _format_evidence(title: str, items: list[tuple[str, Any]]) -> str:
    lines = [title]
    for key, value in items:
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            joined = ", ".join(str(item) for item in value if str(item).strip())
            if not joined:
                continue
            lines.append(f"- {key}: {joined}")
            continue
        dumped = str(value).strip()
        if dumped:
            lines.append(f"- {key}: {dumped}")
    return "\n".join(lines)


def _suggest_implement_auto_capture(feature_dir: Path) -> tuple[Path, list[AutoCaptureSuggestion]]:
    tracker_path = feature_dir / "implement-tracker.md"
    if not tracker_path.exists():
        return tracker_path, []

    frontmatter, sections = _load_sectioned_markdown(tracker_path)
    status = str(frontmatter.get("status", "")).strip().lower()
    current_focus = sections.get("Current Focus") or {}
    execution_state = sections.get("Execution State") or {}
    validation = sections.get("Validation") or {}
    blockers = _coerce_dict_list(sections.get("Blockers"))
    open_gaps = _coerce_dict_list(sections.get("Open Gaps"))
    retry_attempts = _coerce_int(execution_state.get("retry_attempts"))
    failed_tasks = _coerce_str_list(execution_state.get("failed_tasks"))
    completed_checks = _coerce_str_list(validation.get("completed_checks"))
    planned_checks = _coerce_str_list(validation.get("planned_checks"))
    current_batch = str(current_focus.get("current_batch", "")).strip()
    goal = str(current_focus.get("goal", "")).strip()

    suggestions: list[AutoCaptureSuggestion] = []
    if status == "resolved" and retry_attempts >= 1 and completed_checks:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="recovery_path",
                summary="Rerun planned validation after implementation recovery before resolving the feature",
                recurrence_key="implement.rerun-validation-after-recovery-before-resolve",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_dir),
                        ("tracker_status", status),
                        ("retry_attempts", retry_attempts),
                        ("current_batch", current_batch),
                        ("goal", goal),
                        ("failed_tasks", failed_tasks),
                        ("completed_checks", completed_checks),
                    ],
                ),
            )
        )
    if retry_attempts >= 1 and failed_tasks and (completed_checks or planned_checks or blockers):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="pitfall",
                summary="Failed implementation tasks should keep execution in recovery until validation turns green",
                recurrence_key="implement.failed-tasks-keep-recovery-active-until-validation",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_dir),
                        ("tracker_status", status),
                        ("retry_attempts", retry_attempts),
                        ("current_batch", current_batch),
                        ("failed_tasks", failed_tasks),
                        ("planned_checks", planned_checks),
                        ("completed_checks", completed_checks),
                        ("blockers", [item.get("recovery_action", "") for item in blockers if item.get("recovery_action")]),
                    ],
                ),
            )
        )
    gap_types = [str(item.get("type", "")).strip() for item in open_gaps if str(item.get("type", "")).strip()]
    planning_gap_types = [value for value in gap_types if value in {"plan_gap", "research_gap", "spec_gap"}]
    if planning_gap_types:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Execution blockers that change task shape must feed back into planning artifacts before implementation resumes",
                recurrence_key="implement.execution-blockers-feed-back-into-planning",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_dir),
                        ("tracker_status", status),
                        ("current_batch", current_batch),
                        ("open_gap_types", planning_gap_types),
                        (
                            "open_gap_summaries",
                            [str(item.get("summary", "")).strip() for item in open_gaps if str(item.get("summary", "")).strip()],
                        ),
                        (
                            "open_gap_next_actions",
                            [str(item.get("next_action", "")).strip() for item in open_gaps if str(item.get("next_action", "")).strip()],
                        ),
                    ],
                ),
            )
        )
    blocker_types = [str(item.get("type", "")).strip() for item in blockers if str(item.get("type", "")).strip()]
    if any(value in {"external", "human-action"} for value in blocker_types):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="External or human-action blockers should be treated as explicit implementation constraints instead of repeated technical retries",
                recurrence_key="implement.external-or-human-blockers-are-project-constraints",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from implement-tracker.md",
                    [
                        ("feature_dir", feature_dir),
                        ("tracker_status", status),
                        ("blocker_types", blocker_types),
                        (
                            "blocker_evidence",
                            [str(item.get("evidence", "")).strip() for item in blockers if str(item.get("evidence", "")).strip()],
                        ),
                        (
                            "recovery_actions",
                            [str(item.get("recovery_action", "")).strip() for item in blockers if str(item.get("recovery_action", "")).strip()],
                        ),
                    ],
                ),
            )
        )
    return tracker_path, suggestions


def _suggest_quick_auto_capture(workspace: Path) -> tuple[Path, list[AutoCaptureSuggestion]]:
    status_path = workspace / "STATUS.md"
    if not status_path.exists():
        return status_path, []

    frontmatter, sections = _load_sectioned_markdown(status_path)
    status = str(frontmatter.get("status", "")).strip().lower()
    current_focus = sections.get("Current Focus") or {}
    execution = sections.get("Execution") or {}
    validation = sections.get("Validation") or {}
    retry_attempts = _coerce_int(execution.get("retry_attempts"))
    blocker_reason = str(execution.get("blocker_reason", "")).strip()
    recovery_action = str(execution.get("recovery_action", "")).strip()
    execution_fallback = str(execution.get("execution_fallback", "")).strip()
    completed_checks = _coerce_str_list(validation.get("completed_checks"))
    goal = str(current_focus.get("goal", "")).strip()
    next_action = str(current_focus.get("next_action", "")).strip()

    suggestions: list[AutoCaptureSuggestion] = []
    if status == "resolved" and retry_attempts >= 1 and (completed_checks or blocker_reason or recovery_action):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="recovery_path",
                summary="Retry the smallest recorded recovery step and rerun scoped checks before resolving a quick task",
                recurrence_key="quick.retry-recovery-step-before-resolve",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from quick STATUS.md",
                    [
                        ("workspace", workspace),
                        ("status", status),
                        ("retry_attempts", retry_attempts),
                        ("goal", goal),
                        ("next_action", next_action),
                        ("blocker_reason", blocker_reason),
                        ("recovery_action", recovery_action),
                        ("completed_checks", completed_checks),
                    ],
                ),
            )
        )
    if execution_fallback and execution_fallback.lower() != "none":
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="Leader-inline quick-task fallback should preserve the runtime unavailability reason as a reusable execution constraint",
                recurrence_key="quick.leader-inline-fallback-preserves-runtime-unavailability-reason",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from quick STATUS.md",
                    [
                        ("workspace", workspace),
                        ("status", status),
                        ("goal", goal),
                        ("execution_fallback", execution_fallback),
                        ("blocker_reason", blocker_reason),
                        ("recovery_action", recovery_action),
                    ],
                ),
            )
        )
    return status_path, suggestions


def _suggest_test_auto_capture(project_root: Path) -> tuple[Path, list[AutoCaptureSuggestion]]:
    state_path = project_root / ".specify" / "testing" / "testing-state.md"
    if not state_path.exists():
        return state_path, []

    frontmatter, sections = _load_sectioned_markdown(state_path)
    status = str(frontmatter.get("status", "")).strip().lower()
    mode = str(frontmatter.get("mode", "")).strip().lower()
    current_focus = _coerce_section_mapping(sections.get("Current Focus"))
    testing_assets = _coerce_section_mapping(sections.get("Testing Assets"))
    validation_evidence = _coerce_section_mapping(sections.get("Validation Evidence"))
    last_manual_validation = _coerce_section_mapping(validation_evidence.get("last_manual_validation"))
    open_gaps = _coerce_grouped_mapping_list(sections.get("Open Gaps"), group_key="module")

    next_action = str(current_focus.get("next_action") or "").strip()
    next_command = str(current_focus.get("next_command") or "").strip()
    handoff_reason = str(current_focus.get("handoff_reason") or "").strip()
    unit_test_system_request = str(testing_assets.get("unit_test_system_request") or "").strip()
    validation_commands = _coerce_str_list(last_manual_validation.get("commands"))
    validation_exit_status = str(last_manual_validation.get("exit_status") or "").strip()
    validation_summary = str(last_manual_validation.get("summary") or "").strip()
    gap_summaries = [
        str(item.get("summary") or "").strip()
        for item in open_gaps
        if str(item.get("summary") or "").strip()
    ]
    gap_next_actions = [
        str(item.get("next_action") or "").strip()
        for item in open_gaps
        if str(item.get("next_action") or "").strip()
    ]

    suggestions: list[AutoCaptureSuggestion] = []
    if open_gaps and next_command:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Testing-system open gaps should drive an explicit follow-up route before later workflows resume",
                recurrence_key="test-scan.open-gaps-require-explicit-follow-up-route",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from testing-state.md",
                    [
                        ("state_path", state_path),
                        ("status", status),
                        ("mode", mode),
                        ("next_action", next_action),
                        ("next_command", next_command),
                        ("handoff_reason", handoff_reason),
                        ("open_gap_summaries", gap_summaries),
                        ("open_gap_next_actions", gap_next_actions),
                    ],
                ),
            )
        )
    if unit_test_system_request and next_command.lower() in {"/sp-specify", "/sp.specify"}:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="Brownfield testing programs should start from UNIT_TEST_SYSTEM_REQUEST instead of ad-hoc implementation work",
                recurrence_key="test-scan.brownfield-programs-start-from-unit-test-system-request",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from testing-state.md",
                    [
                        ("state_path", state_path),
                        ("mode", mode),
                        ("next_action", next_action),
                        ("next_command", next_command),
                        ("handoff_reason", handoff_reason),
                        ("unit_test_system_request", unit_test_system_request),
                    ],
                ),
            )
        )
    if status in {"complete", "completed"} and (not validation_commands or not validation_exit_status or not validation_summary):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="verification_gap",
                summary="Testing-system completion requires explicit manual validation evidence in testing-state",
                recurrence_key="test-scan.complete-state-requires-manual-validation-evidence",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from testing-state.md",
                    [
                        ("state_path", state_path),
                        ("status", status),
                        ("mode", mode),
                        ("validation_commands", validation_commands),
                        ("validation_exit_status", validation_exit_status),
                        ("validation_summary", validation_summary),
                    ],
                ),
            )
        )
    return state_path, suggestions


WORKFLOW_STATE_AUTO_CAPTURE_COMMANDS = {
    "sp-constitution",
    "sp-specify",
    "sp-clarify",
    "sp-deep-research",
    "sp-plan",
    "sp-checklist",
    "sp-tasks",
    "sp-analyze",
    *MAP_WORKFLOW_COMMANDS,
}


def _suggest_workflow_state_auto_capture(
    feature_dir: Path,
    *,
    command_name: str,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
    state_path = feature_dir / "workflow-state.md"
    if not state_path.exists():
        return state_path, []

    checkpoint = serialize_workflow_state(state_path)
    next_command = str(checkpoint.get("next_command") or "").strip()
    next_action = str(checkpoint.get("next_action") or "").strip()
    route_reason = str(checkpoint.get("route_reason") or "").strip()
    blocked_reason = str(checkpoint.get("blocked_reason") or "").strip()
    false_starts = _coerce_str_list(checkpoint.get("false_starts"))
    hidden_dependencies = _coerce_str_list(checkpoint.get("hidden_dependencies"))
    reusable_constraints = _coerce_str_list(checkpoint.get("reusable_constraints"))
    status = str(checkpoint.get("status") or "").strip()
    phase_mode = str(checkpoint.get("phase_mode") or "").strip()

    suggestions: list[AutoCaptureSuggestion] = []
    if next_command and route_reason:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Workflow-state handoff should preserve the exact re-entry reason so later stages do not rediscover why routing changed",
                recurrence_key=f"{command_name}.workflow-state-preserves-reentry-reason",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_dir),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("next_command", next_command),
                        ("next_action", next_action),
                        ("route_reason", route_reason),
                        ("blocked_reason", blocked_reason),
                    ],
                ),
            )
        )
    if false_starts:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="false_lead_pattern",
                summary="Workflow-state should preserve false starts so later runs do not repeat the same route or diagnosis loop",
                recurrence_key=f"{command_name}.workflow-state-preserves-false-starts",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_dir),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("false_starts", false_starts),
                        ("next_command", next_command),
                        ("next_action", next_action),
                    ],
                ),
            )
        )
    if hidden_dependencies or reusable_constraints:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="project_constraint",
                summary="Dependencies and reusable constraints discovered in workflow-state should be promoted into shared memory before later work resumes",
                recurrence_key=f"{command_name}.workflow-state-promotes-discovered-constraints",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_dir),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("hidden_dependencies", hidden_dependencies),
                        ("reusable_constraints", reusable_constraints),
                        ("next_command", next_command),
                    ],
                ),
            )
        )
    return state_path, suggestions


def _suggest_debug_auto_capture(session_file: Path) -> tuple[Path, list[AutoCaptureSuggestion]]:
    if not session_file.exists():
        return session_file, []

    state = MarkdownPersistenceHandler(session_file.parent).load(session_file)
    validation_summary = summarize_validation_results(state.resolution.validation_results)
    validation_commands = [item.command for item in state.resolution.validation_results]
    suggestions: list[AutoCaptureSuggestion] = []

    if state.status.value == "resolved" and state.resolution.fail_count >= 1 and validation_summary.failed == 0 and validation_summary.passed >= 1:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="recovery_path",
                summary="Return to investigation with new evidence after failed verification instead of stacking debug fixes",
                recurrence_key="debug.return-to-investigation-after-failed-verification",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from resolved debug session",
                    [
                        ("session_file", session_file),
                        ("trigger", state.trigger),
                        ("fail_count", state.resolution.fail_count),
                        ("fix", state.resolution.fix or ""),
                        ("failure_mechanism", state.resolution.root_cause.failure_mechanism if state.resolution.root_cause else ""),
                        ("validation_commands", validation_commands),
                        ("loop_restoration_proof", state.resolution.loop_restoration_proof),
                    ],
                ),
            )
        )
    if state.resolution.fail_count >= 2:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Repeated failed verification should trigger a research checkpoint before another debug fix loop",
                recurrence_key="debug.research-checkpoint-after-repeated-verification-failure",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from resolved debug session",
                    [
                        ("session_file", session_file),
                        ("trigger", state.trigger),
                        ("fail_count", state.resolution.fail_count),
                        ("validation_commands", validation_commands),
                        ("root_cause_summary", state.resolution.root_cause.summary if state.resolution.root_cause else ""),
                    ],
                ),
            )
        )
    if state.status.value == "resolved" and state.resolution.fix_scope == "surface-only" and state.resolution.rejected_surface_fixes:
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="pitfall",
                summary="Surface-only debug fixes are insufficient without loop-restoration proof",
                recurrence_key="debug.surface-only-fixes-need-loop-restoration-proof",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from resolved debug session",
                    [
                        ("session_file", session_file),
                        ("trigger", state.trigger),
                        ("rejected_surface_fixes", state.resolution.rejected_surface_fixes),
                        ("loop_restoration_proof", state.resolution.loop_restoration_proof),
                    ],
                ),
            )
        )
    return session_file, suggestions


def is_relevant_to_command(entry: LearningEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to


def is_highest_signal(entry: LearningEntry) -> bool:
    return entry.signal_strength == "high" or entry.occurrence_count >= 2


def should_auto_promote_on_start(entry: LearningEntry, command_name: str) -> bool:
    return (
        entry.status == "candidate"
        and is_relevant_to_command(entry, command_name)
        and entry.occurrence_count >= 2
    )


def _preflight_warning_payload(
    entry: LearningEntry,
    *,
    current_command: str,
    source_layer: str,
    requires_confirmation: bool = False,
) -> dict[str, Any]:
    layer_label_map = {
        "project_rules": "stable project rule",
        "project_learnings": "confirmed project learning",
        "candidate": "candidate learning",
    }
    label = layer_label_map.get(source_layer, "shared learning")
    why_now = (
        f"{label} applies to {current_command} and should shape this workflow run before the same issue repeats"
        if source_layer != "candidate"
        else f"high-signal candidate should be reviewed before {current_command} rediscovers the same issue from scratch"
    )
    return {
        "recurrence_key": entry.recurrence_key,
        "summary": entry.summary,
        "learning_type": entry.learning_type,
        "source_layer": source_layer,
        "signal_strength": entry.signal_strength,
        "occurrence_count": entry.occurrence_count,
        "requires_confirmation": requires_confirmation,
        "why_now": why_now,
    }


def start_learning_session(project_root: Path, *, command_name: str) -> dict[str, Any]:
    paths = ensure_learning_files(project_root)
    normalized_command = normalize_command_name(command_name)
    rule_preamble, rule_entries = _read_entries(paths.project_rules)
    learning_preamble, learning_entries = _read_entries(paths.project_learnings)
    candidate_preamble, candidate_entries = _read_entries(paths.candidates)

    auto_promoted: list[LearningEntry] = []
    remaining_candidates: list[LearningEntry] = []
    for entry in candidate_entries:
        if should_auto_promote_on_start(entry, normalized_command):
            promoted_entry = LearningEntry.from_payload(
                {
                    **entry.to_payload(),
                    "status": "confirmed",
                }
            )
            learning_entries, stored = _upsert_entry(learning_entries, promoted_entry, status="confirmed")
            auto_promoted.append(stored)
            _append_review_note(
                paths.review,
                f"auto-promoted `{stored.recurrence_key}` to project learnings during `{normalized_command}` start",
            )
        else:
            remaining_candidates.append(entry)

    if auto_promoted:
        _write_entries(
            paths.project_learnings,
            learning_preamble or LEARNINGS_TEMPLATE_TEXT.rstrip(),
            learning_entries,
        )
        _write_entries(
            paths.candidates,
            candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
            remaining_candidates,
        )
        candidate_entries = remaining_candidates

    relevant_rules = [entry.to_payload() for entry in rule_entries if is_relevant_to_command(entry, normalized_command)]
    relevant_learnings = [entry.to_payload() for entry in learning_entries if is_relevant_to_command(entry, normalized_command)]
    relevant_candidates = [entry.to_payload() for entry in candidate_entries if is_relevant_to_command(entry, normalized_command)]

    promotable = [
        entry.to_payload()
        for entry in candidate_entries
        if is_relevant_to_command(entry, normalized_command) and entry.occurrence_count >= 2
    ]
    confirmation_candidates = [
        entry.to_payload()
        for entry in candidate_entries
        if is_relevant_to_command(entry, normalized_command) and is_highest_signal(entry)
    ]

    preflight_warning_entries: list[dict[str, Any]] = []
    seen_preflight_keys: set[str] = set()

    for entry in rule_entries:
        if not is_relevant_to_command(entry, normalized_command):
            continue
        if entry.recurrence_key in seen_preflight_keys:
            continue
        preflight_warning_entries.append(
            _preflight_warning_payload(
                entry,
                current_command=normalized_command,
                source_layer="project_rules",
            )
        )
        seen_preflight_keys.add(entry.recurrence_key)

    for entry in learning_entries:
        if not is_relevant_to_command(entry, normalized_command):
            continue
        if entry.recurrence_key in seen_preflight_keys:
            continue
        preflight_warning_entries.append(
            _preflight_warning_payload(
                entry,
                current_command=normalized_command,
                source_layer="project_learnings",
            )
        )
        seen_preflight_keys.add(entry.recurrence_key)

    for entry in candidate_entries:
        if not is_relevant_to_command(entry, normalized_command):
            continue
        if not is_highest_signal(entry):
            continue
        if entry.recurrence_key in seen_preflight_keys:
            continue
        preflight_warning_entries.append(
            _preflight_warning_payload(
                entry,
                current_command=normalized_command,
                source_layer="candidate",
                requires_confirmation=True,
            )
        )
        seen_preflight_keys.add(entry.recurrence_key)

    top_warning_entries = sorted(
        [
            *auto_promoted,
            *[LearningEntry.from_payload(item) for item in promotable],
            *[LearningEntry.from_payload(item) for item in confirmation_candidates],
        ],
        key=lambda entry: (-entry.occurrence_count, entry.recurrence_key),
    )
    seen_warning_keys: set[str] = set()
    top_warnings: list[dict[str, Any]] = []
    for entry in top_warning_entries:
        if entry.recurrence_key in seen_warning_keys:
            continue
        top_warnings.append(
            {
                "recurrence_key": entry.recurrence_key,
                "summary": entry.summary,
                "signal_strength": entry.signal_strength,
                "occurrence_count": entry.occurrence_count,
                "status": entry.status,
            }
        )
        seen_warning_keys.add(entry.recurrence_key)
        if len(top_warnings) == 5:
            break

    return {
        "command": normalized_command,
        "paths": paths.to_dict(),
        "relevant_rules": relevant_rules,
        "relevant_learnings": relevant_learnings,
        "relevant_candidates": relevant_candidates,
        "auto_promoted": [entry.to_payload() for entry in auto_promoted],
        "promotable_candidates": promotable,
        "confirmation_candidates": confirmation_candidates,
        "preflight_warnings": preflight_warning_entries,
        "summary_counts": {
            "relevant_rules": len(relevant_rules),
            "relevant_learnings": len(relevant_learnings),
            "relevant_candidates": len(relevant_candidates),
            "auto_promoted": len(auto_promoted),
            "promotable_candidates": len(promotable),
            "confirmation_candidates": len(confirmation_candidates),
            "preflight_warnings": len(preflight_warning_entries),
        },
        "top_warnings": top_warnings,
    }


def capture_learning(
    project_root: Path,
    *,
    command_name: str,
    learning_type: str,
    summary: str,
    evidence: str,
    recurrence_key: str | None = None,
    signal_strength: str = "medium",
    applies_to: Iterable[str] | None = None,
    default_scope: str | None = None,
    confirm: bool = False,
    pain_score: int | None = None,
    false_starts: Iterable[str] | None = None,
    rejected_paths: Iterable[str] | None = None,
    decisive_signal: str | None = None,
    root_cause_family: str | None = None,
    injection_targets: Iterable[str] | None = None,
    promotion_hint: str | None = None,
) -> dict[str, Any]:
    paths = ensure_learning_files(project_root)
    entry = build_learning_entry(
        command_name=command_name,
        learning_type=learning_type,
        summary=summary,
        evidence=evidence,
        recurrence_key=recurrence_key,
        signal_strength=signal_strength,
        applies_to=applies_to,
        default_scope=default_scope,
        status="confirmed" if confirm else "candidate",
        pain_score=pain_score,
        false_starts=false_starts,
        rejected_paths=rejected_paths,
        decisive_signal=decisive_signal,
        root_cause_family=root_cause_family,
        injection_targets=injection_targets,
        promotion_hint=promotion_hint,
    )

    if confirm:
        preamble, learning_entries = _read_entries(paths.project_learnings)
        learning_entries, stored = _upsert_entry(learning_entries, entry, status="confirmed")
        _write_entries(paths.project_learnings, preamble or LEARNINGS_TEMPLATE_TEXT.rstrip(), learning_entries)
        candidate_preamble, candidate_entries = _read_entries(paths.candidates)
        candidate_entries = _remove_by_recurrence(candidate_entries, stored.recurrence_key)
        _write_entries(paths.candidates, candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(), candidate_entries)
        _append_review_note(paths.review, f"confirmed `{stored.recurrence_key}` from `{stored.source_command}`")
        return {
            "status": "confirmed",
            "entry": stored.to_payload(),
            "needs_confirmation": False,
        }

    preamble, candidate_entries = _read_entries(paths.candidates)
    candidate_entries, stored = _upsert_entry(candidate_entries, entry, status="candidate")
    _write_entries(paths.candidates, preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(), candidate_entries)
    _append_review_note(paths.review, f"captured candidate `{stored.recurrence_key}` from `{stored.source_command}`")
    return {
        "status": "candidate",
        "entry": stored.to_payload(),
        "needs_confirmation": is_highest_signal(stored),
    }


def capture_auto_learning(
    project_root: Path,
    *,
    command_name: str,
    feature_dir: Path | None = None,
    workspace: Path | None = None,
    session_file: Path | None = None,
) -> dict[str, Any]:
    normalized_command = normalize_command_name(command_name)
    if normalized_command == "sp-implement":
        if feature_dir is None:
            raise ValueError("feature_dir is required for implement auto-capture")
        source_path, suggestions = _suggest_implement_auto_capture(feature_dir)
    elif normalized_command == "sp-quick":
        if workspace is None:
            raise ValueError("workspace is required for quick auto-capture")
        source_path, suggestions = _suggest_quick_auto_capture(workspace)
    elif normalized_command in {"sp-test-scan", "sp-test-build"}:
        source_path, suggestions = _suggest_test_auto_capture(project_root)
    elif normalized_command in WORKFLOW_STATE_AUTO_CAPTURE_COMMANDS:
        if feature_dir is None:
            raise ValueError("feature_dir is required for workflow-state auto-capture")
        source_path, suggestions = _suggest_workflow_state_auto_capture(
            feature_dir,
            command_name=normalized_command,
        )
    elif normalized_command == "sp-debug":
        if session_file is None:
            raise ValueError("session_file is required for debug auto-capture")
        source_path, suggestions = _suggest_debug_auto_capture(session_file)
    else:
        raise ValueError(f"auto-capture is unsupported for '{command_name}'")

    if not suggestions:
        return {
            "status": "no-op",
            "command": normalized_command,
            "source_path": str(source_path),
            "captured": [],
            "reason": "no high-signal auto-capture patterns matched the current state",
        }

    fingerprint = _snapshot_fingerprint(normalized_command, source_path, suggestions)
    registry = _load_auto_capture_registry(project_root)
    if fingerprint in registry:
        return {
            "status": "duplicate-snapshot",
            "command": normalized_command,
            "source_path": str(source_path),
            "captured": [],
            "reason": "this workflow state snapshot was already auto-captured",
            "fingerprint": fingerprint,
        }

    captured: list[dict[str, Any]] = []
    for suggestion in suggestions:
        payload = capture_learning(
            project_root,
            command_name=normalized_command,
            learning_type=suggestion.learning_type,
            summary=suggestion.summary,
            evidence=suggestion.evidence,
            recurrence_key=suggestion.recurrence_key,
            signal_strength=suggestion.signal_strength,
            applies_to=suggestion.applies_to,
            confirm=False,
        )
        captured.append(payload["entry"])

    registry[fingerprint] = {
        "command": normalized_command,
        "source_path": str(source_path),
        "recurrence_keys": [entry["recurrence_key"] for entry in captured],
        "captured_at": now_iso(),
    }
    _write_auto_capture_registry(project_root, registry)
    _append_review_note(
        build_learning_paths(project_root).review,
        f"auto-captured {len(captured)} learning candidate(s) from `{normalized_command}` using `{source_path}`",
    )
    return {
        "status": "captured",
        "command": normalized_command,
        "source_path": str(source_path),
        "captured": captured,
        "fingerprint": fingerprint,
    }


def promote_learning(
    project_root: Path,
    *,
    recurrence_key: str,
    target: str,
) -> dict[str, Any]:
    normalized_target = target.strip().lower()
    if normalized_target not in PROMOTION_TARGETS:
        raise ValueError(f"unsupported promotion target '{target}'")

    paths = ensure_learning_files(project_root)
    recurrence_key = recurrence_key.strip().lower()
    candidate_preamble, candidate_entries = _read_entries(paths.candidates)
    learning_preamble, learning_entries = _read_entries(paths.project_learnings)
    rule_preamble, rule_entries = _read_entries(paths.project_rules)

    source_entry = next((entry for entry in candidate_entries if entry.recurrence_key == recurrence_key), None)
    source_layer = "candidates"
    if source_entry is None:
        source_entry = next((entry for entry in learning_entries if entry.recurrence_key == recurrence_key), None)
        source_layer = "project_learnings"
    if source_entry is None:
        source_entry = next((entry for entry in rule_entries if entry.recurrence_key == recurrence_key), None)
        source_layer = "project_rules"
    if source_entry is None:
        raise ValueError(f"learning '{recurrence_key}' not found")

    if normalized_target == "learning":
        source_entry.status = "confirmed"
        learning_entries, stored = _upsert_entry(learning_entries, source_entry, status="confirmed")
        candidate_entries = _remove_by_recurrence(candidate_entries, recurrence_key)
        _write_entries(paths.project_learnings, learning_preamble or LEARNINGS_TEMPLATE_TEXT.rstrip(), learning_entries)
        _write_entries(paths.candidates, candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(), candidate_entries)
        _append_review_note(paths.review, f"promoted `{recurrence_key}` to project learnings from `{source_layer}`")
        return {"status": "confirmed", "entry": stored.to_payload()}

    source_entry.status = "promoted-rule"
    rule_entries, stored = _upsert_entry(rule_entries, source_entry, status="promoted-rule")
    candidate_entries = _remove_by_recurrence(candidate_entries, recurrence_key)
    learning_entries = _remove_by_recurrence(learning_entries, recurrence_key)
    _write_entries(paths.project_rules, rule_preamble or RULES_TEMPLATE_TEXT.rstrip(), rule_entries)
    _write_entries(paths.project_learnings, learning_preamble or LEARNINGS_TEMPLATE_TEXT.rstrip(), learning_entries)
    _write_entries(paths.candidates, candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(), candidate_entries)
    _append_review_note(paths.review, f"promoted `{recurrence_key}` to project rules from `{source_layer}`")
    return {"status": "promoted-rule", "entry": stored.to_payload()}


def _entry_counts(project_root: Path) -> dict[str, int]:
    paths = build_learning_paths(project_root)
    _, candidate_entries = _read_entries(paths.candidates) if paths.candidates.exists() else ("", [])
    _, learning_entries = _read_entries(paths.project_learnings) if paths.project_learnings.exists() else ("", [])
    _, rule_entries = _read_entries(paths.project_rules) if paths.project_rules.exists() else ("", [])
    return {
        "candidates": len(candidate_entries),
        "project_learnings": len(learning_entries),
        "project_rules": len(rule_entries),
    }


def learning_status_payload(
    project_root: Path,
    *,
    include_runtime: bool = True,
) -> dict[str, Any]:
    paths = build_learning_paths(project_root)
    payload: dict[str, Any] = {
        "paths": paths.to_dict(),
        "exists": {
            "constitution": paths.constitution.exists(),
            "project_rules": paths.project_rules.exists(),
            "project_learnings": paths.project_learnings.exists(),
        },
        "counts": _entry_counts(project_root),
    }
    if include_runtime:
        payload["exists"].update(
            {
                "candidates": paths.candidates.exists(),
                "review": paths.review.exists(),
            }
        )
    return payload
