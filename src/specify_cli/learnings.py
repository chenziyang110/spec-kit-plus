from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Any, Iterable


LEARNING_TYPES = {
    "pitfall",
    "recovery_path",
    "user_preference",
    "workflow_gap",
    "project_constraint",
}
LEARNING_STATUSES = {
    "candidate",
    "confirmed",
    "promoted-rule",
    "promoted-constitution",
}
SIGNAL_STRENGTHS = {"low", "medium", "high"}
PROMOTION_TARGETS = {"learning", "rule"}
KNOWN_COMMANDS = (
    "sp-specify",
    "sp-plan",
    "sp-tasks",
    "sp-implement",
    "sp-debug",
    "sp-fast",
    "sp-quick",
)

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
        )


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
    return normalized


def _slugify(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return lowered or "learning"


def default_scope_for_type(learning_type: str) -> str:
    normalized = learning_type.strip().lower()
    if normalized in {"user_preference", "project_constraint"}:
        return "global"
    if normalized == "workflow_gap":
        return "planning-heavy"
    if normalized == "recovery_path":
        return "execution-heavy"
    return "implementation-heavy"


def default_applies_to_for_type(learning_type: str, source_command: str) -> list[str]:
    normalized_type = learning_type.strip().lower()
    normalized_source = normalize_command_name(source_command)
    if normalized_type in {"user_preference", "project_constraint"}:
        return list(KNOWN_COMMANDS)
    if normalized_type == "workflow_gap":
        return ["sp-specify", "sp-plan", "sp-tasks", "sp-quick"]
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
    )


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
    return (
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


def is_relevant_to_command(entry: LearningEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to


def is_highest_signal(entry: LearningEntry) -> bool:
    return entry.signal_strength == "high" or entry.occurrence_count >= 2


def start_learning_session(project_root: Path, *, command_name: str) -> dict[str, Any]:
    paths = ensure_learning_files(project_root)
    normalized_command = normalize_command_name(command_name)
    _, rule_entries = _read_entries(paths.project_rules)
    _, learning_entries = _read_entries(paths.project_learnings)
    _, candidate_entries = _read_entries(paths.candidates)

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

    return {
        "command": normalized_command,
        "paths": paths.to_dict(),
        "relevant_rules": relevant_rules,
        "relevant_learnings": relevant_learnings,
        "relevant_candidates": relevant_candidates,
        "promotable_candidates": promotable,
        "confirmation_candidates": confirmation_candidates,
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
