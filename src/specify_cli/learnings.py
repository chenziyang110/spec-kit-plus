from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
import yaml

from specify_cli.atomic_io import atomic_write_text, interprocess_lock
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
}
SIGNAL_STRENGTHS = {"low", "medium", "high"}
PROMOTION_TARGETS = {"learning", "rule"}
MAP_WORKFLOW_COMMANDS = (
    "sp-map-scan",
    "sp-map-build",
    "sp-map-update",
    "sp-map-rebuild",
)
KNOWN_COMMANDS = (
    "sp-accept",
    "sp-analyze",
    "sp-ask",
    "sp-auto",
    "sp-checklist",
    "sp-clarify",
    "sp-constitution",
    "sp-debug",
    "sp-deep-research",
    "sp-design",
    "sp-discussion",
    "sp-explain",
    "sp-fast",
    "sp-implement",
    "sp-implement-teams",
    "sp-integrate",
    *MAP_WORKFLOW_COMMANDS,
    "sp-plan",
    "sp-prd",
    "sp-prd-build",
    "sp-prd-scan",
    "sp-quick",
    "sp-specify",
    "sp-tasks",
    "sp-taskstoissues",
    "sp-team",
)
COMMAND_ALIASES = {
    "sp-research": "sp-deep-research",
}

# Consumption is always read-only. Capture policy tells workflow prompts whether
# closeout may write a candidate directly, must defer capture to an owning
# workflow, or should skip learning entirely for a deliberately trivial path.
LEARNING_WORKFLOW_POLICIES = {command: "consume-capture" for command in KNOWN_COMMANDS}
LEARNING_WORKFLOW_POLICIES.update(
    {
        "sp-accept": "consume-only",
        "sp-analyze": "consume-only",
        "sp-ask": "consume-only",
        "sp-auto": "consume-only",
        "sp-constitution": "consume-only",
        "sp-explain": "consume-only",
        "sp-fast": "skip",
        "sp-implement-teams": "consume-only",
        "sp-taskstoissues": "consume-only",
        "sp-team": "consume-only",
    }
)

MACHINE_BEGIN = "<!-- SPECKIT_LEARNING_DATA_BEGIN -->"
MACHINE_END = "<!-- SPECKIT_LEARNING_DATA_END -->"

RULES_TEMPLATE_TEXT = (
    "# Project Rules\n\n"
    "Shared defaults that later `sp-xxx` workflows should follow across specification,\n"
    "planning, implementation, debugging, and quick-task execution.\n\n"
    "Promote only stable project rules through `specify learning promote --target rule`.\n"
    "Keep one-off observations as CLI-managed candidates until recurrence or explicit\n"
    "confirmation proves they belong in this shared rule layer.\n\n"
    "---\n"
)
CONFIRMED_LEARNINGS_TEMPLATE_TEXT = (
    "# Confirmed Project Learning\n\n"
    "Runtime-maintained confirmed Learning behind `specify learning start`, `list`,\n"
    "and `show`. Agents should use those CLI surfaces instead of parsing this file.\n\n"
    "---\n"
)
LEARNING_INDEX_TEMPLATE_TEXT = (
    "# Project Learning Index\n\n"
    "Runtime-maintained compact index behind `specify learning start` and\n"
    "`specify learning list`. Agents should use those CLI surfaces and expand one\n"
    "selected record with `specify learning show`; do not parse this file directly\n"
    "during normal workflow execution.\n\n"
    "---\n\n"
    f"{MACHINE_BEGIN}\n[]\n{MACHINE_END}\n\n"
    "## Managed Entries\n\n"
    "_No learning index entries recorded yet._\n"
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
    confirmed_learnings: Path
    learning_index: Path
    learning_detail_template: Path
    candidates: Path
    review: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "constitution": str(self.constitution),
            "project_rules": str(self.project_rules),
            "confirmed_learnings": str(self.confirmed_learnings),
            "learning_index": str(self.learning_index),
            "learning_detail_template": str(self.learning_detail_template),
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
    problem: str = ""
    recommended_action: str = ""
    avoid: list[str] = field(default_factory=list)
    trigger_signals: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)

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
            problem=str(payload.get("problem") or ""),
            recommended_action=str(payload.get("recommended_action") or ""),
            avoid=_coerce_str_list(payload.get("avoid")),
            trigger_signals=_coerce_str_list(payload.get("trigger_signals")),
            success_criteria=_coerce_str_list(payload.get("success_criteria")),
            exceptions=_coerce_str_list(payload.get("exceptions")),
        )


@dataclass
class LearningIndexEntry:
    id: str
    problem: str
    lesson: str
    learning_type: str
    source_command: str
    recurrence_key: str
    applies_to: list[str]
    trigger_signals: list[str]
    detail: str
    first_seen: str
    last_seen: str
    occurrence_count: int = 1
    signal_strength: str = "medium"

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LearningIndexEntry":
        required = {
            "id",
            "problem",
            "lesson",
            "learning_type",
            "source_command",
            "recurrence_key",
            "applies_to",
            "trigger_signals",
            "detail",
            "first_seen",
            "last_seen",
            "occurrence_count",
            "signal_strength",
        }
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(
                f"learning index entry is missing required fields: {', '.join(missing)}"
            )
        if not isinstance(payload["applies_to"], list):
            raise ValueError("learning index applies_to must be a list")
        if not isinstance(payload["trigger_signals"], list):
            raise ValueError("learning index trigger_signals must be a list")
        learning_type = normalize_learning_type(str(payload["learning_type"]))
        source_command = normalize_command_name(str(payload["source_command"]))
        recurrence_key = str(payload["recurrence_key"]).strip().lower()
        if not recurrence_key:
            raise ValueError("learning index recurrence_key is required")
        signal_strength = normalize_signal_strength(str(payload["signal_strength"]))
        problem = str(payload["problem"]).strip()
        lesson = str(payload["lesson"]).strip()
        first_seen = str(payload["first_seen"]).strip()
        last_seen = str(payload["last_seen"]).strip()
        index_id = str(payload["id"]).strip()
        if not index_id.startswith("learn-"):
            raise ValueError("learning index id must start with 'learn-'")
        if not problem or not lesson or not first_seen or not last_seen:
            raise ValueError(
                "learning index problem, lesson, first_seen, and last_seen are required"
            )
        detail = str(payload["detail"]).strip()
        if not _is_valid_detail_ref(detail):
            raise ValueError(
                "learning index detail must be a safe relative Markdown path"
            )
        applies_to = _coerce_str_list(payload["applies_to"])
        trigger_signals = _coerce_str_list(payload["trigger_signals"])
        if not applies_to or not trigger_signals:
            raise ValueError(
                "learning index applies_to and trigger_signals must not be empty"
            )
        occurrence_count = _coerce_int(payload["occurrence_count"])
        if occurrence_count < 1:
            raise ValueError("learning index occurrence_count must be at least 1")
        return cls(
            id=index_id,
            problem=problem,
            lesson=lesson,
            learning_type=learning_type,
            source_command=source_command,
            recurrence_key=recurrence_key,
            applies_to=[normalize_command_name(item) for item in applies_to],
            trigger_signals=trigger_signals,
            detail=detail,
            first_seen=first_seen,
            last_seen=last_seen,
            occurrence_count=occurrence_count,
            signal_strength=signal_strength,
        )


@dataclass(frozen=True)
class AutoCaptureSuggestion:
    learning_type: str
    summary: str
    evidence: str
    recurrence_key: str
    signal_strength: str = "medium"
    applies_to: tuple[str, ...] | None = None
    problem: str = ""
    recommended_action: str = ""
    trigger_signals: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()


SEMANTIC_TRIGGER_GUIDANCE: dict[str, tuple[str, str, str, str]] = {
    "user_correction": (
        "user_preference",
        "Apply the corrected assumption, preference, or boundary before repeating the affected work.",
        "The next affected workflow reflects the correction without requiring the user to repeat it.",
        "Continuing from the superseded assumption.",
    ),
    "repeated_attempt": (
        "pitfall",
        "Reuse the proven recovery path and skip attempts already disproved by evidence.",
        "The next run reaches the verified path without replaying the same failed attempts.",
        "Repeating a failed attempt without new contradictory evidence.",
    ),
    "route_change": (
        "routing_mistake",
        "Resume from the recorded next command and route reason instead of inferring the route from chat history.",
        "The resumed workflow can explain and follow the selected route from durable state.",
        "Routing from chat memory alone.",
    ),
    "blocker_recovery": (
        "recovery_path",
        "Reuse the recorded recovery action and verify its unblock condition before resuming.",
        "The blocker is cleared by recorded evidence and the workflow resumes at the stated next action.",
        "Retrying unrelated technical actions while the unblock condition remains false.",
    ),
    "false_lead": (
        "false_lead_pattern",
        "Check the rejected path and its decisive evidence before reopening that hypothesis.",
        "The rejected path is skipped unless new evidence directly contradicts the prior decision.",
        "Repeating a disproved route or diagnosis without new evidence.",
    ),
    "decisive_signal": (
        "pitfall",
        "Look for the recorded decisive signal before widening investigation or implementation scope.",
        "The future decision cites the decisive signal and reaches the correct route earlier.",
        "Treating low-value surrounding symptoms as stronger than the decisive signal.",
    ),
    "hidden_dependency": (
        "project_constraint",
        "Resolve or honor the hidden dependency before changing the affected surface.",
        "Downstream work names the dependency and verifies its required precondition.",
        "Starting dependent work before the hidden precondition is satisfied.",
    ),
    "validation_gap": (
        "verification_gap",
        "Add or run the missing real acceptance check before making the affected completion claim.",
        "The completion claim is backed by the recorded verification surface and green evidence.",
        "Using source-only or indirect checks as proof of real behavior.",
    ),
    "tooling_trap": (
        "tooling_trap",
        "Verify the environment and tool boundary before diagnosing the same symptom as a product defect.",
        "The environment/tool cause is ruled in or out before production code changes.",
        "Changing product code before checking the recorded tooling condition.",
    ),
    "state_loss": (
        "state_surface_gap",
        "Persist the missing decision, evidence, and next action before handoff or compaction.",
        "A resumed run continues safely without reconstructing the lost state from chat.",
        "Stopping with required recovery context only in conversation history.",
    ),
    "cognition_gap": (
        "map_coverage_gap",
        "Use live evidence for the missing surface and refresh cognition coverage through the owning map workflow.",
        "The truth-owning surface is queryable and the active workflow no longer depends on a stale omission.",
        "Treating missing cognition coverage as evidence that the surface does not exist.",
    ),
    "reusable_constraint": (
        "project_constraint",
        "Apply the recorded constraint before planning or modifying the affected surface.",
        "Later work names and honors the constraint in its plan, task, or verification route.",
        "Rediscovering the constraint after implementation begins.",
    ),
    "near_miss": (
        "near_miss",
        "Preserve the guard or check that prevented the risky action and run it before similar work.",
        "The same risk is detected before any destructive or hard-to-reverse action.",
        "Relying on luck or operator memory to avoid the same risk.",
    ),
}


def _semantic_trigger_suggestions(
    *,
    command_name: str,
    feature_dir: Path,
    trigger_signals: Iterable[str],
) -> list[AutoCaptureSuggestion]:
    suggestions: list[AutoCaptureSuggestion] = []
    for raw_signal in trigger_signals:
        signal = str(raw_signal).strip()
        if not signal:
            continue
        raw_kind, separator, raw_detail = signal.partition(":")
        kind = raw_kind.strip().lower().replace("-", "_").replace(" ", "_")
        detail = " ".join((raw_detail.strip() if separator else signal).split())
        learning_type, action, success, avoid = SEMANTIC_TRIGGER_GUIDANCE.get(
            kind,
            (
                "pitfall",
                "Apply the recorded signal before repeating the affected work.",
                "The next affected workflow uses the signal and records confirming evidence.",
                "Ignoring an explicit reusable-learning signal.",
            ),
        )
        signal_label = kind.replace("_", " ")
        summary = f"{signal_label}: {detail}"
        recurrence_suffix = _slugify(detail)[:72]
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type=learning_type,
                summary=summary,
                recurrence_key=f"{command_name}.trigger.{kind}.{recurrence_suffix}",
                evidence=_format_evidence(
                    "Observed explicit Learning trigger from workflow-state.md",
                    [
                        ("feature_dir", feature_dir),
                        ("command", command_name),
                        ("trigger_kind", kind),
                        ("trigger_detail", detail),
                    ],
                ),
                problem=f"The recorded {signal_label} signal could be lost after handoff or compaction: {detail}",
                recommended_action=action,
                trigger_signals=(signal,),
                success_criteria=(success,),
                avoid=(avoid,),
            )
        )
    return suggestions


def build_learning_paths(project_root: Path) -> LearningPaths:
    memory_dir = project_root / ".specify" / "memory"
    learning_memory_dir = memory_dir / "learnings"
    learning_dir = project_root / ".planning" / "learnings"
    return LearningPaths(
        constitution=memory_dir / "constitution.md",
        project_rules=memory_dir / "project-rules.md",
        confirmed_learnings=learning_memory_dir / "confirmed.md",
        learning_index=learning_memory_dir / "INDEX.md",
        learning_detail_template=project_root
        / ".specify"
        / "templates"
        / "project-learning-detail-template.md",
        candidates=learning_dir / "candidates.md",
        review=learning_dir / "review.md",
    )


def now_iso() -> str:
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def normalize_command_name(command_name: str) -> str:
    raw = str(command_name or "").strip().lower()
    if not raw:
        raise ValueError("command name is required")
    while raw.startswith("/"):
        raw = raw[1:]
    if not raw:
        raise ValueError("command name is required")
    if raw.startswith("spx-"):
        raw = f"sp-{raw[4:]}"
    elif raw.startswith("spx."):
        raw = f"sp-{raw[4:]}"
    if raw.startswith("sp-"):
        normalized = raw
    elif raw.startswith("sp."):
        normalized = f"sp-{raw[3:]}"
    else:
        normalized = f"sp-{raw}"
    if not re.fullmatch(r"sp-[a-z0-9][a-z0-9-]*", normalized):
        raise ValueError(f"invalid command name '{command_name}'")
    return COMMAND_ALIASES.get(normalized, normalized)


def _slugify(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return lowered or "learning"


def default_scope_for_type(learning_type: str) -> str:
    normalized = learning_type.strip().lower()
    if normalized in {"user_preference", "project_constraint"}:
        return "global"
    if normalized in {
        "workflow_gap",
        "routing_mistake",
        "state_surface_gap",
        "decision_debt",
    }:
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
        return [
            "sp-fast",
            "sp-quick",
            "sp-specify",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-debug",
        ]
    if normalized_type == "verification_gap":
        return ["sp-implement", "sp-accept", "sp-debug", "sp-quick", "sp-fast"]
    if normalized_type == "state_surface_gap":
        return [
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-accept",
            "sp-debug",
            "sp-quick",
            *MAP_WORKFLOW_COMMANDS,
        ]
    if normalized_type == "map_coverage_gap":
        return [
            *MAP_WORKFLOW_COMMANDS,
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            "sp-implement",
            "sp-debug",
        ]
    if normalized_type == "tooling_trap":
        return ["sp-implement", "sp-debug", "sp-quick", *MAP_WORKFLOW_COMMANDS]
    if normalized_type == "false_lead_pattern":
        return ["sp-debug", "sp-implement", "sp-quick"]
    if normalized_type == "near_miss":
        return sorted({normalized_source, "sp-implement", "sp-debug", "sp-quick"})
    if normalized_type == "decision_debt":
        return [
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-tasks",
            *MAP_WORKFLOW_COMMANDS,
        ]
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
    problem: str | None = None,
    recommended_action: str | None = None,
    avoid: Iterable[str] | None = None,
    trigger_signals: Iterable[str] | None = None,
    success_criteria: Iterable[str] | None = None,
    exceptions: Iterable[str] | None = None,
) -> LearningEntry:
    normalized_summary = str(summary or "").strip()
    normalized_evidence = str(evidence or "").strip()
    if not normalized_summary:
        raise ValueError("learning summary is required")
    if not normalized_evidence:
        raise ValueError("learning evidence is required")
    normalized_command = normalize_command_name(command_name)
    normalized_type = normalize_learning_type(learning_type)
    normalized_signal = normalize_signal_strength(signal_strength)
    normalized_status = normalize_status(status)
    normalized_applies = (
        [normalize_command_name(item) for item in applies_to]
        if applies_to
        else default_applies_to_for_type(normalized_type, normalized_command)
    )
    normalized_recurrence_key = (
        str(
            recurrence_key or derive_recurrence_key(normalized_type, normalized_summary)
        )
        .strip()
        .lower()
    )
    if not normalized_recurrence_key:
        raise ValueError("learning recurrence_key is required")
    timestamp = now_iso()
    return LearningEntry(
        id=build_learning_id(),
        summary=normalized_summary,
        learning_type=normalized_type,
        source_command=normalized_command,
        evidence=normalized_evidence,
        recurrence_key=normalized_recurrence_key,
        default_scope=(default_scope or default_scope_for_type(normalized_type))
        .strip()
        .lower(),
        applies_to=sorted(dict.fromkeys(normalized_applies)),
        signal_strength=normalized_signal,
        status=normalized_status,
        first_seen=timestamp,
        last_seen=timestamp,
        occurrence_count=1,
        pain_score=max(0, _coerce_int(pain_score)),
        false_starts=sorted(
            dict.fromkeys(
                str(item).strip() for item in (false_starts or []) if str(item).strip()
            )
        ),
        rejected_paths=sorted(
            dict.fromkeys(
                str(item).strip()
                for item in (rejected_paths or [])
                if str(item).strip()
            )
        ),
        decisive_signal=str(decisive_signal or "").strip(),
        root_cause_family=str(root_cause_family or "").strip(),
        injection_targets=sorted(
            dict.fromkeys(
                str(item).strip()
                for item in (injection_targets or [])
                if str(item).strip()
            )
        ),
        promotion_hint=str(promotion_hint or "").strip(),
        problem=str(problem or normalized_summary).strip(),
        recommended_action=str(recommended_action or normalized_summary).strip(),
        avoid=sorted(
            dict.fromkeys(
                str(item).strip() for item in (avoid or []) if str(item).strip()
            )
        ),
        trigger_signals=sorted(
            dict.fromkeys(
                str(item).strip()
                for item in (trigger_signals or [])
                if str(item).strip()
            )
        ),
        success_criteria=sorted(
            dict.fromkeys(
                str(item).strip()
                for item in (success_criteria or [])
                if str(item).strip()
            )
        ),
        exceptions=sorted(
            dict.fromkeys(
                str(item).strip() for item in (exceptions or []) if str(item).strip()
            )
        ),
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
                sections[current_section] = (
                    yaml.safe_load(section_text) if section_text else None
                )
            current_section = match.group("title").strip()
            current_lines = []
            continue
        if current_section is not None:
            current_lines.append(raw_line)
    if current_section is not None:
        section_text = "\n".join(current_lines).strip()
        sections[current_section] = (
            yaml.safe_load(section_text) if section_text else None
        )
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
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


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
                "problem": item.problem,
                "recommended_action": item.recommended_action,
                "trigger_signals": list(item.trigger_signals),
                "success_criteria": list(item.success_criteria),
                "avoid": list(item.avoid),
                "exceptions": list(item.exceptions),
            }
            for item in suggestions
        ],
    }
    payload = json.dumps(normalized_payload, ensure_ascii=False, sort_keys=True).encode(
        "utf-8"
    )
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
        structured_lines.append(
            f"- Injection Targets: {', '.join(entry.injection_targets)}"
        )
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
        sections.append(
            "\n\n---\n\n".join(_render_entry_summary(entry) for entry in entries)
        )
    sections.append("")
    return "\n".join(sections)


def _learning_index_date_prefix(first_seen: str) -> str:
    prefix = str(first_seen or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", prefix):
        return prefix
    return "unknown-date"


def _learning_index_id(recurrence_key: str, first_seen: str) -> str:
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    return f"learn-{_learning_index_date_prefix(first_seen)}-{_slugify(recurrence_key)[:56]}-{recurrence_hash}"


def _detail_ref_for_index_id(index_id: str) -> str:
    return f"./{index_id}.md"


def _trigger_signals_from_entry(entry: LearningEntry) -> list[str]:
    signals = [entry.learning_type, entry.signal_strength]
    signals.extend(entry.trigger_signals)
    signals.extend(entry.false_starts)
    signals.extend(entry.rejected_paths)
    if entry.decisive_signal:
        signals.append(entry.decisive_signal)
    if entry.root_cause_family:
        signals.append(entry.root_cause_family)
    return sorted(dict.fromkeys(signal for signal in signals if str(signal).strip()))


def _index_entry_from_learning(entry: LearningEntry) -> LearningIndexEntry:
    index_id = _learning_index_id(entry.recurrence_key, entry.first_seen)
    return LearningIndexEntry(
        id=index_id,
        problem=entry.problem or entry.summary,
        lesson=(
            entry.recommended_action
            or (
                entry.evidence.splitlines()[0]
                if entry.evidence.strip()
                else entry.summary
            )
        ),
        learning_type=entry.learning_type,
        source_command=entry.source_command,
        recurrence_key=entry.recurrence_key,
        applies_to=entry.applies_to,
        trigger_signals=_trigger_signals_from_entry(entry),
        detail=_detail_ref_for_index_id(index_id),
        first_seen=entry.first_seen,
        last_seen=entry.last_seen,
        occurrence_count=entry.occurrence_count,
        signal_strength=entry.signal_strength,
    )


def _render_index_entry_summary(entry: LearningIndexEntry) -> str:
    applies = ", ".join(entry.applies_to)
    triggers = ", ".join(entry.trigger_signals)
    return (
        f"### {entry.id} - {entry.problem}\n\n"
        f"- Type: `{entry.learning_type}`\n"
        f"- Source Command: `{entry.source_command}`\n"
        f"- Recurrence Key: `{entry.recurrence_key}`\n"
        f"- Applies To: {applies}\n"
        f"- Trigger Signals: {triggers}\n"
        f"- Signal: `{entry.signal_strength}`\n"
        f"- Occurrence Count: {entry.occurrence_count}\n"
        f"- First Seen: `{entry.first_seen}`\n"
        f"- Last Seen: `{entry.last_seen}`\n"
        f"- Detail: `{entry.detail}`\n\n"
        f"#### Lesson\n\n{entry.lesson}\n"
    )


def _empty_learning_index_diagnostics() -> dict[str, Any]:
    return {
        "skipped_malformed_entries": 0,
        "file_level_errors": 0,
        "details": [],
        "warnings": [],
    }


def _read_index_entries_with_diagnostics(
    path: Path,
    *,
    tolerate_file_errors: bool = True,
) -> tuple[str, list[LearningIndexEntry], dict[str, Any]]:
    diagnostics = _empty_learning_index_diagnostics()
    if not path.exists():
        return "", [], diagnostics

    try:
        preamble, payloads = _extract_payload_block(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        if not tolerate_file_errors:
            raise
        message = f"learning_index_parse_error:{type(exc).__name__}"
        diagnostics["file_level_errors"] = 1
        diagnostics["warnings"].append(message)
        diagnostics["details"].append(
            {
                "index": None,
                "action": "fallback_internal_store_catalog",
                "reason": str(exc),
            }
        )
        return "", [], diagnostics

    entries: list[LearningIndexEntry] = []
    for index, payload in enumerate(payloads):
        entry_id = payload.get("id") if isinstance(payload, dict) else None
        try:
            if not isinstance(payload, dict):
                raise ValueError("learning index entry is not an object")
            entry = LearningIndexEntry.from_payload(payload)
        except Exception as exc:  # noqa: BLE001 - diagnostics must report and continue after malformed current entries.
            diagnostics["skipped_malformed_entries"] += 1
            warning = f"learning_index_entry_{index}_skipped:{type(exc).__name__}"
            diagnostics["warnings"].append(warning)
            diagnostics["details"].append(
                {
                    "index": index,
                    "id": str(entry_id or ""),
                    "action": "skipped",
                    "reason": str(exc),
                }
            )
            continue

        entries.append(entry)

    return preamble, entries, diagnostics


def _read_index_entries(path: Path) -> tuple[str, list[LearningIndexEntry]]:
    preamble, entries, _diagnostics = _read_index_entries_with_diagnostics(
        path, tolerate_file_errors=False
    )
    return preamble, entries


def _render_learning_index_file(
    preamble: str, entries: list[LearningIndexEntry]
) -> str:
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
        sections.append("_No learning index entries recorded yet._")
    else:
        sections.append(
            "\n\n---\n\n".join(_render_index_entry_summary(entry) for entry in entries)
        )
    sections.append("")
    return "\n".join(sections)


def _write_index_entries(
    path: Path, preamble: str, entries: list[LearningIndexEntry]
) -> None:
    atomic_write_text(path, _render_learning_index_file(preamble, entries))


def _read_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    if not path.exists():
        return "", []
    preamble, payloads = _extract_payload_block(path.read_text(encoding="utf-8"))
    return preamble, [LearningEntry.from_payload(payload) for payload in payloads]


def read_learning_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    return _read_entries(path)


def read_learning_index_entries(path: Path) -> tuple[str, list[LearningIndexEntry]]:
    return _read_index_entries(path)


def _write_entries(path: Path, preamble: str, entries: list[LearningEntry]) -> None:
    atomic_write_text(path, _render_learning_file(preamble, entries))


def _seed_from_template(
    destination: Path, template_path: Path, fallback_text: str
) -> bool:
    if destination.exists():
        return False
    if template_path.is_file():
        atomic_write_text(destination, template_path.read_text(encoding="utf-8"))
    else:
        atomic_write_text(destination, fallback_text)
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
        paths.confirmed_learnings,
        templates_root / "project-confirmed-learnings-template.md",
        CONFIRMED_LEARNINGS_TEMPLATE_TEXT,
    ):
        created.append("learnings/confirmed.md")
    if _seed_from_template(
        paths.learning_index,
        templates_root / "project-learnings-index-template.md",
        LEARNING_INDEX_TEMPLATE_TEXT,
    ):
        created.append("learnings/INDEX.md")

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
    with interprocess_lock(_learning_lock_path(project_root)):
        return _ensure_learning_files_unlocked(
            project_root,
            include_runtime=include_runtime,
            tracker=tracker,
        )


def _ensure_learning_files_unlocked(
    project_root: Path,
    *,
    include_runtime: bool = True,
    tracker: Any | None = None,
) -> LearningPaths:
    paths = ensure_learning_memory_from_templates(project_root, tracker=tracker)
    if include_runtime:
        ensure_learning_runtime_files(project_root)
    return paths


def _learning_lock_path(project_root: Path) -> Path:
    return build_learning_paths(project_root).review.parent / ".learning.lock"


def _merge_entry(
    existing: LearningEntry, new_entry: LearningEntry, *, status: str | None = None
) -> LearningEntry:
    merged_applies = sorted(
        dict.fromkeys([*existing.applies_to, *new_entry.applies_to])
    )
    merged_false_starts = sorted(
        dict.fromkeys([*existing.false_starts, *new_entry.false_starts])
    )
    merged_rejected_paths = sorted(
        dict.fromkeys([*existing.rejected_paths, *new_entry.rejected_paths])
    )
    merged_injection_targets = sorted(
        dict.fromkeys([*existing.injection_targets, *new_entry.injection_targets])
    )
    merged_avoid = sorted(dict.fromkeys([*existing.avoid, *new_entry.avoid]))
    merged_trigger_signals = sorted(
        dict.fromkeys([*existing.trigger_signals, *new_entry.trigger_signals])
    )
    merged_success_criteria = sorted(
        dict.fromkeys([*existing.success_criteria, *new_entry.success_criteria])
    )
    merged_exceptions = sorted(
        dict.fromkeys([*existing.exceptions, *new_entry.exceptions])
    )
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
        problem=new_entry.problem or existing.problem,
        recommended_action=new_entry.recommended_action or existing.recommended_action,
        avoid=merged_avoid,
        trigger_signals=merged_trigger_signals,
        success_criteria=merged_success_criteria,
        exceptions=merged_exceptions,
    )


def _upsert_entry(
    entries: list[LearningEntry], new_entry: LearningEntry, *, status: str | None = None
) -> tuple[list[LearningEntry], LearningEntry]:
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


def _merge_index_entry(
    existing: LearningIndexEntry, new_entry: LearningIndexEntry
) -> LearningIndexEntry:
    return LearningIndexEntry(
        id=existing.id,
        problem=new_entry.problem or existing.problem,
        lesson=new_entry.lesson or existing.lesson,
        learning_type=existing.learning_type,
        source_command=new_entry.source_command or existing.source_command,
        recurrence_key=existing.recurrence_key,
        applies_to=sorted(dict.fromkeys([*existing.applies_to, *new_entry.applies_to])),
        trigger_signals=sorted(
            dict.fromkeys([*existing.trigger_signals, *new_entry.trigger_signals])
        ),
        detail=existing.detail,
        first_seen=existing.first_seen,
        last_seen=new_entry.last_seen,
        occurrence_count=new_entry.occurrence_count,
        signal_strength="high"
        if "high" in {existing.signal_strength, new_entry.signal_strength}
        else "medium"
        if "medium" in {existing.signal_strength, new_entry.signal_strength}
        else "low",
    )


def _upsert_index_entry(
    entries: list[LearningIndexEntry], new_entry: LearningIndexEntry
) -> tuple[list[LearningIndexEntry], LearningIndexEntry]:
    updated = list(entries)
    for index, existing in enumerate(updated):
        if existing.recurrence_key == new_entry.recurrence_key:
            merged = _merge_index_entry(existing, new_entry)
            updated[index] = merged
            return updated, merged
    updated.append(new_entry)
    return updated, new_entry


def _render_learning_detail(
    entry: LearningEntry, index_entry: LearningIndexEntry
) -> str:
    payload = [entry.to_payload()]
    false_starts = (
        "\n".join(f"- {item}" for item in entry.false_starts)
        or "_No false starts recorded._"
    )
    rejected_paths = (
        "\n".join(f"- {item}" for item in entry.rejected_paths)
        or "_No rejected paths recorded._"
    )
    avoid = (
        "\n".join(f"- {item}" for item in entry.avoid)
        or "_No explicit avoid list recorded._"
    )
    success = (
        "\n".join(f"- {item}" for item in entry.success_criteria)
        or "_No explicit success criteria recorded._"
    )
    exceptions = (
        "\n".join(f"- {item}" for item in entry.exceptions)
        or "_No exceptions recorded._"
    )
    triggers = (
        "\n".join(f"- {item}" for item in index_entry.trigger_signals)
        or "_No trigger signals recorded._"
    )
    return "\n".join(
        [
            f"# {index_entry.problem}",
            "",
            MACHINE_BEGIN,
            json.dumps(payload, ensure_ascii=False, indent=2),
            MACHINE_END,
            "",
            "## Problem",
            "",
            index_entry.problem,
            "",
            "## Lesson",
            "",
            index_entry.lesson,
            "",
            "## Recommended Action",
            "",
            entry.recommended_action or index_entry.lesson,
            "",
            "## When To Apply",
            "",
            ", ".join(index_entry.applies_to),
            "",
            "## Trigger Signals",
            "",
            triggers,
            "",
            "## Evidence",
            "",
            entry.evidence,
            "",
            "## Prevention Or Recovery",
            "",
            f"Decisive signal: {entry.decisive_signal or 'not recorded'}",
            "",
            "False starts:",
            false_starts,
            "",
            "Rejected paths:",
            rejected_paths,
            "",
            "Avoid:",
            avoid,
            "",
            "## Success Criteria",
            "",
            success,
            "",
            "## Exceptions",
            "",
            exceptions,
            "",
        ]
    )


def _is_valid_detail_ref(detail_ref: str) -> bool:
    detail_ref = str(detail_ref)
    if not detail_ref.startswith("./"):
        return False
    detail_name = detail_ref.removeprefix("./")
    return bool(re.fullmatch(r"learn-[A-Za-z0-9][A-Za-z0-9._-]*\.md", detail_name))


def _detail_path_for_ref(learning_dir: Path, detail_ref: str) -> Path:
    return learning_dir / str(detail_ref).removeprefix("./")


def _detail_ref_resolves_inside(learning_dir: Path, detail_ref: str) -> bool:
    return (
        _detail_path_for_ref(learning_dir, detail_ref)
        .resolve()
        .is_relative_to(learning_dir.resolve())
    )


def _normalized_detail_path_key(learning_dir: Path, detail_ref: str) -> str:
    return str(_detail_path_for_ref(learning_dir, detail_ref).resolve()).casefold()


def _repair_detail_ref_from_learning(
    learning_dir: Path, entry: LearningEntry, index_entry: LearningIndexEntry
) -> None:
    if _is_valid_detail_ref(index_entry.detail) and _detail_ref_resolves_inside(
        learning_dir, index_entry.detail
    ):
        return
    index_entry.id = _learning_index_id(entry.recurrence_key, entry.first_seen)
    index_entry.detail = _detail_ref_for_index_id(index_entry.id)
    if not _is_valid_detail_ref(index_entry.detail) or not _detail_ref_resolves_inside(
        learning_dir, index_entry.detail
    ):
        raise ValueError("learning detail path escapes learning memory directory")


def _write_learning_detail(
    paths: LearningPaths, entry: LearningEntry, index_entry: LearningIndexEntry
) -> Path:
    learning_dir = paths.learning_index.parent
    _repair_detail_ref_from_learning(learning_dir, entry, index_entry)
    detail_path = _detail_path_for_ref(learning_dir, index_entry.detail)
    atomic_write_text(detail_path, _render_learning_detail(entry, index_entry))
    return detail_path


def _detail_ref_used_by_other(
    entries: list[LearningIndexEntry],
    detail_ref: str,
    recurrence_key: str,
    learning_dir: Path,
) -> bool:
    detail_key = _normalized_detail_path_key(learning_dir, detail_ref)
    return any(
        entry.recurrence_key != recurrence_key
        and _normalized_detail_path_key(learning_dir, entry.detail) == detail_key
        for entry in entries
    )


def _unused_detail_ref(
    entries: list[LearningIndexEntry],
    recurrence_key: str,
    first_seen: str,
    learning_dir: Path,
) -> tuple[str, str]:
    base_id = _learning_index_id(recurrence_key, first_seen)
    candidate_id = base_id
    candidate_detail = _detail_ref_for_index_id(candidate_id)
    suffix = 2
    while _detail_ref_used_by_other(
        entries, candidate_detail, recurrence_key, learning_dir
    ):
        candidate_id = f"{base_id}-{suffix}"
        candidate_detail = _detail_ref_for_index_id(candidate_id)
        suffix += 1
    return candidate_id, candidate_detail


def _sync_learning_index_detail(
    paths: LearningPaths, stored: LearningEntry
) -> tuple[LearningIndexEntry, Path]:
    index_preamble, index_entries = _read_index_entries(paths.learning_index)
    index_entries, stored_index = _upsert_index_entry(
        index_entries, _index_entry_from_learning(stored)
    )
    learning_dir = paths.learning_index.parent
    _repair_detail_ref_from_learning(learning_dir, stored, stored_index)
    if _detail_ref_used_by_other(
        index_entries, stored_index.detail, stored_index.recurrence_key, learning_dir
    ):
        stored_index.id, stored_index.detail = _unused_detail_ref(
            index_entries,
            stored.recurrence_key,
            stored.first_seen,
            learning_dir,
        )
        if not _is_valid_detail_ref(
            stored_index.detail
        ) or not _detail_ref_resolves_inside(learning_dir, stored_index.detail):
            raise ValueError("learning detail path escapes learning memory directory")
    if _detail_ref_used_by_other(
        index_entries, stored_index.detail, stored_index.recurrence_key, learning_dir
    ):
        raise ValueError(
            "learning detail ref is already used by another recurrence key"
        )
    detail_path = _write_learning_detail(paths, stored, stored_index)
    _write_index_entries(
        paths.learning_index,
        index_preamble or LEARNING_INDEX_TEMPLATE_TEXT.rstrip(),
        index_entries,
    )
    return stored_index, detail_path


def _remove_by_recurrence(
    entries: list[LearningEntry], recurrence_key: str
) -> list[LearningEntry]:
    return [entry for entry in entries if entry.recurrence_key != recurrence_key]


def _append_review_note(path: Path, note: str) -> None:
    timestamp = now_iso()
    if not path.exists():
        atomic_write_text(path, REVIEW_TEMPLATE_TEXT)
    content = path.read_text(encoding="utf-8").rstrip()
    content += f"\n- `{timestamp}` {note}\n"
    atomic_write_text(path, content + "\n")


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


def _suggest_implement_auto_capture(
    feature_dir: Path,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
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
                problem="Implementation recovery can be marked resolved before the planned validation is rerun.",
                recommended_action="Rerun the planned validation after recovery and record green evidence before resolving the feature.",
                trigger_signals=(
                    "implementation retry completed",
                    "recovery before terminal resolution",
                ),
                success_criteria=(
                    "all planned post-recovery checks are recorded green",
                ),
                avoid=("resolving from the code change alone",),
            )
        )
    if (
        retry_attempts >= 1
        and failed_tasks
        and (completed_checks or planned_checks or blockers)
    ):
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
                        (
                            "blockers",
                            [
                                item.get("recovery_action", "")
                                for item in blockers
                                if item.get("recovery_action")
                            ],
                        ),
                    ],
                ),
                problem="A failed task can be treated as finished while its recovery validation is still incomplete.",
                recommended_action="Keep execution in recovery, clear the failed task, and rerun its planned checks before continuing.",
                trigger_signals=(
                    "failed task after retry",
                    "validation incomplete after task failure",
                ),
                success_criteria=(
                    "failed tasks are cleared and their planned checks are green",
                ),
                avoid=(
                    "continuing later batches while failed-task validation is unresolved",
                ),
            )
        )
    gap_types = [
        str(item.get("type", "")).strip()
        for item in open_gaps
        if str(item.get("type", "")).strip()
    ]
    planning_gap_types = [
        value
        for value in gap_types
        if value in {"plan_gap", "research_gap", "spec_gap"}
    ]
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
                            [
                                str(item.get("summary", "")).strip()
                                for item in open_gaps
                                if str(item.get("summary", "")).strip()
                            ],
                        ),
                        (
                            "open_gap_next_actions",
                            [
                                str(item.get("next_action", "")).strip()
                                for item in open_gaps
                                if str(item.get("next_action", "")).strip()
                            ],
                        ),
                    ],
                ),
                problem="An execution blocker can change task shape while implementation continues against stale planning artifacts.",
                recommended_action="Reopen the highest invalid planning stage, update the affected artifacts, then resume implementation.",
                trigger_signals=(
                    "plan gap during implementation",
                    "research gap during implementation",
                    "spec gap during implementation",
                ),
                success_criteria=(
                    "the corrected planning artifacts and tasks reflect the blocker-driven shape change",
                ),
                avoid=(
                    "patching a planning-shape change only inside the current implementation task",
                ),
            )
        )
    blocker_types = [
        str(item.get("type", "")).strip()
        for item in blockers
        if str(item.get("type", "")).strip()
    ]
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
                            [
                                str(item.get("evidence", "")).strip()
                                for item in blockers
                                if str(item.get("evidence", "")).strip()
                            ],
                        ),
                        (
                            "recovery_actions",
                            [
                                str(item.get("recovery_action", "")).strip()
                                for item in blockers
                                if str(item.get("recovery_action", "")).strip()
                            ],
                        ),
                    ],
                ),
                problem="A human or external precondition cannot be cleared by repeating technical implementation attempts.",
                recommended_action="Record the owner, exact human steps, unblock condition, and required evidence; stop technical retries until it is satisfied.",
                trigger_signals=("external blocker", "human-action blocker"),
                success_criteria=(
                    "the precondition has explicit completion evidence before implementation resumes",
                ),
                avoid=(
                    "repeating technical retries while the external precondition remains false",
                ),
            )
        )
    return tracker_path, suggestions


def _suggest_quick_auto_capture(
    workspace: Path,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
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
    if (
        status == "resolved"
        and retry_attempts >= 1
        and (completed_checks or blocker_reason or recovery_action)
    ):
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
                problem="A quick task can be marked resolved before the recovery step and scoped checks prove the fix.",
                recommended_action="Run the smallest recorded recovery action, then rerun the scoped checks before resolving.",
                trigger_signals=(
                    "quick task recovered after retry",
                    "quick blocker cleared",
                ),
                success_criteria=(
                    "the recorded recovery action is followed by green scoped checks",
                ),
                avoid=("resolving immediately after the retry without validation",),
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
                problem="An inline fallback can hide a reusable runtime limitation and cause future dispatch attempts to repeat the same failure.",
                recommended_action="Check the recorded runtime limitation before dispatch and reuse the approved fallback only while it still applies.",
                trigger_signals=(
                    "leader-inline fallback used",
                    "agent runtime unavailable",
                ),
                success_criteria=(
                    "future routing checks runtime readiness before selecting the fallback",
                ),
                avoid=(
                    "retrying unavailable execution infrastructure without a state change",
                ),
            )
        )
    return status_path, suggestions


WORKFLOW_STATE_AUTO_CAPTURE_COMMANDS = {
    "sp-constitution",
    "sp-specify",
    "sp-clarify",
    "sp-deep-research",
    "sp-plan",
    "sp-checklist",
    "sp-tasks",
    "sp-analyze",
    "sp-accept",
    "sp-prd-scan",
    "sp-prd-build",
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
    if route_reason.casefold() in {
        "none",
        "n/a",
        "not-applicable",
    } or route_reason.startswith("["):
        route_reason = ""
    if blocked_reason.casefold() in {
        "none",
        "n/a",
        "not-applicable",
    } or blocked_reason.startswith("["):
        blocked_reason = ""
    false_starts = _coerce_str_list(checkpoint.get("false_starts"))
    hidden_dependencies = _coerce_str_list(checkpoint.get("hidden_dependencies"))
    reusable_constraints = _coerce_str_list(checkpoint.get("reusable_constraints"))
    trigger_signals = _coerce_str_list(checkpoint.get("trigger_signals"))
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
                problem="A changed workflow route can lose its exact re-entry reason between stages or after resume.",
                recommended_action="Preserve the next command, next action, and exact route reason before handoff.",
                trigger_signals=(
                    "next command changed",
                    "route reason recorded",
                    "workflow re-entry",
                ),
                success_criteria=(
                    "the resumed workflow can explain and follow the route without chat history",
                ),
                avoid=("routing from chat memory alone",),
            )
        )
    if blocked_reason and not (next_command and route_reason):
        suggestions.append(
            AutoCaptureSuggestion(
                learning_type="workflow_gap",
                summary="Blocked workflow-state closeout should preserve the blocker as a reusable learning signal",
                recurrence_key=f"{command_name}.workflow-state-preserves-blocked-reason",
                evidence=_format_evidence(
                    "Observed auto-capture evidence from workflow-state.md",
                    [
                        ("feature_dir", feature_dir),
                        ("command", command_name),
                        ("status", status),
                        ("phase_mode", phase_mode),
                        ("blocked_reason", blocked_reason),
                        ("next_command", next_command),
                        ("next_action", next_action),
                    ],
                ),
                problem="A blocked terminal state can lose the blocker detail needed for safe recovery.",
                recommended_action="Preserve the blocker, owner, next action, and unblock condition before stopping.",
                trigger_signals=("workflow blocked", "blocked_reason present"),
                success_criteria=(
                    "resume can continue from the recorded unblock condition",
                ),
                avoid=("reporting blocked without a durable reason",),
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
                problem="A later run can repeat a route or diagnosis already disproved by evidence.",
                recommended_action="Check recorded false starts before repeating a route or hypothesis.",
                trigger_signals=(
                    "false start recorded",
                    "hypothesis changed",
                    "route rejected",
                ),
                success_criteria=(
                    "the rejected path is not retried without new contradictory evidence",
                ),
                avoid=("replaying a false start without new evidence",),
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
                problem="A hidden dependency or reusable constraint can disappear when it remains only in workflow-local state.",
                recommended_action="Apply the recorded dependency or constraint before planning or changing the affected surface.",
                trigger_signals=(
                    "hidden dependency",
                    "reusable constraint",
                    "cross-workflow dependency",
                ),
                success_criteria=(
                    "downstream work names and honors the dependency or constraint",
                ),
                avoid=("rediscovering the constraint after implementation starts",),
            )
        )
    suggestions.extend(
        _semantic_trigger_suggestions(
            command_name=command_name,
            feature_dir=feature_dir,
            trigger_signals=trigger_signals,
        )
    )
    return state_path, suggestions


def _suggest_debug_auto_capture(
    session_file: Path,
) -> tuple[Path, list[AutoCaptureSuggestion]]:
    if not session_file.exists():
        return session_file, []

    state = MarkdownPersistenceHandler(session_file.parent).load(session_file)
    validation_summary = summarize_validation_results(
        state.resolution.validation_results
    )
    validation_commands = [item.command for item in state.resolution.validation_results]
    suggestions: list[AutoCaptureSuggestion] = []

    if (
        state.status.value == "resolved"
        and state.resolution.fail_count >= 1
        and validation_summary.failed == 0
        and validation_summary.passed >= 1
    ):
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
                        (
                            "failure_mechanism",
                            state.resolution.root_cause.failure_mechanism
                            if state.resolution.root_cause
                            else "",
                        ),
                        ("validation_commands", validation_commands),
                        (
                            "loop_restoration_proof",
                            state.resolution.loop_restoration_proof,
                        ),
                    ],
                ),
                problem="A failed verification can lead to stacked fixes without returning to the evidence and root-cause model.",
                recommended_action="Return to investigation with the failed check as new evidence, update the hypothesis, then apply one justified fix.",
                trigger_signals=(
                    "debug verification failed before eventual resolution",
                ),
                success_criteria=(
                    "the final fix restores the loop and all recorded validation commands pass",
                ),
                avoid=("stacking another fix without updating the investigation",),
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
                        (
                            "root_cause_summary",
                            state.resolution.root_cause.summary
                            if state.resolution.root_cause
                            else "",
                        ),
                    ],
                ),
                problem="Repeated failed verification indicates the current debug model or capability evidence is insufficient.",
                recommended_action="Pause the fix loop, open a focused research checkpoint, and return with evidence that changes the hypothesis or implementation chain.",
                trigger_signals=("two or more debug verification failures",),
                success_criteria=(
                    "new evidence resolves the uncertainty before another production fix is attempted",
                ),
                avoid=("repeating the same debug-fix loop with unchanged evidence",),
            )
        )
    if (
        state.status.value == "resolved"
        and state.resolution.fix_scope == "surface-only"
        and state.resolution.rejected_surface_fixes
    ):
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
                        (
                            "rejected_surface_fixes",
                            state.resolution.rejected_surface_fixes,
                        ),
                        (
                            "loop_restoration_proof",
                            state.resolution.loop_restoration_proof,
                        ),
                    ],
                ),
                problem="A surface-only fix can suppress the symptom while leaving the broken causal loop unchanged.",
                recommended_action="Reject the surface patch unless loop-restoration proof shows the underlying behavior is restored.",
                trigger_signals=(
                    "surface-only debug fix",
                    "rejected surface fixes present",
                ),
                success_criteria=(
                    "loop-restoration proof and targeted validation demonstrate the causal behavior is fixed",
                ),
                avoid=("accepting symptom disappearance as root-cause resolution",),
            )
        )
    return session_file, suggestions


def is_relevant_to_command(entry: LearningEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to


def is_index_relevant_to_command(entry: LearningIndexEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to


def is_highest_signal(entry: LearningEntry) -> bool:
    return entry.signal_strength == "high" or entry.occurrence_count >= 2


def learning_workflow_policy(command_name: str) -> str:
    """Return the explicit Learning consumption/capture policy for a workflow."""

    normalized = normalize_command_name(command_name)
    return LEARNING_WORKFLOW_POLICIES.get(normalized, "consume-capture")


def _read_entries_if_present(path: Path) -> list[LearningEntry]:
    if not path.is_file():
        return []
    try:
        return _read_entries(path)[1]
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return []


def _learning_catalog(
    project_root: Path,
) -> tuple[
    LearningPaths,
    list[tuple[LearningIndexEntry, LearningEntry | None, str]],
    dict[str, Any],
]:
    """Merge internal Learning stores into one deterministic consumer catalog."""

    paths = build_learning_paths(project_root)
    source_layers: list[tuple[str, list[LearningEntry]]] = [
        ("candidate", _read_entries_if_present(paths.candidates)),
        ("confirmed-learning", _read_entries_if_present(paths.confirmed_learnings)),
        ("project-rule", _read_entries_if_present(paths.project_rules)),
    ]
    source_by_key: dict[str, tuple[LearningEntry, str]] = {}
    for layer, entries in source_layers:
        for entry in entries:
            source_by_key[entry.recurrence_key] = (entry, layer)

    if paths.learning_index.is_file():
        _preamble, index_entries, diagnostics = _read_index_entries_with_diagnostics(
            paths.learning_index
        )
    else:
        index_entries = []
        diagnostics = _empty_learning_index_diagnostics()
        diagnostics["warnings"].append(
            "Learning index is missing; run `specify learning ensure` before capture."
        )

    catalog: list[tuple[LearningIndexEntry, LearningEntry | None, str]] = []
    seen: set[str] = set()
    for index_entry in index_entries:
        source = source_by_key.get(index_entry.recurrence_key)
        entry, layer = source if source else (None, "index-only")
        catalog.append((index_entry, entry, layer))
        seen.add(index_entry.recurrence_key)

    for recurrence_key, (entry, layer) in source_by_key.items():
        if recurrence_key in seen:
            continue
        catalog.append((_index_entry_from_learning(entry), entry, layer))

    catalog.sort(
        key=lambda item: (
            -item[0].occurrence_count,
            {"high": 0, "medium": 1, "low": 2}.get(item[0].signal_strength, 3),
            item[0].recurrence_key,
        )
    )
    return paths, catalog, diagnostics


def _learning_summary_card(
    index_entry: LearningIndexEntry,
    entry: LearningEntry | None,
    source_layer: str,
    *,
    command_name: str | None,
) -> dict[str, Any]:
    status = entry.status if entry else "indexed"
    summary = entry.summary if entry else index_entry.problem
    action = (
        entry.recommended_action
        if entry and entry.recommended_action
        else index_entry.lesson
    )
    card: dict[str, Any] = {
        "ref": index_entry.recurrence_key,
        "summary": summary,
        "action": action,
        "type": index_entry.learning_type,
        "status": status,
        "signal": index_entry.signal_strength,
        "occurrences": index_entry.occurrence_count,
        "applies_to": index_entry.applies_to,
        "trigger_signals": index_entry.trigger_signals,
        "source_layer": source_layer,
        "show_argv": [
            "specify",
            "learning",
            "show",
            "--ref",
            index_entry.recurrence_key,
            "--format",
            "json",
        ],
    }
    if command_name:
        card["why_relevant"] = f"applies to {command_name}"
    return card


def list_learning_summaries(
    project_root: Path,
    *,
    command_name: str | None = None,
    learning_type: str | None = None,
    status: str | None = None,
    query: str | None = None,
    cursor: int = 0,
    limit: int = 50,
    include_all: bool = False,
) -> dict[str, Any]:
    """Return compact Learning cards; detail expansion is owned by ``show``."""

    normalized_command = normalize_command_name(command_name) if command_name else None
    normalized_type = normalize_learning_type(learning_type) if learning_type else None
    normalized_status = status.strip().lower() if status else None
    if normalized_status and normalized_status not in {*LEARNING_STATUSES, "indexed"}:
        raise ValueError(f"unsupported learning status '{status}'")
    normalized_query = query.strip().casefold() if query else ""
    cursor = max(0, int(cursor))
    if include_all:
        limit = 0
    elif limit < 1:
        raise ValueError("limit must be at least 1 unless --all is used")
    else:
        limit = min(int(limit), 200)

    _paths, catalog, diagnostics = _learning_catalog(project_root)
    cards: list[dict[str, Any]] = []
    for index_entry, entry, source_layer in catalog:
        if normalized_command and not is_index_relevant_to_command(
            index_entry, normalized_command
        ):
            continue
        if normalized_type and index_entry.learning_type != normalized_type:
            continue
        entry_status = entry.status if entry else "indexed"
        if normalized_status and entry_status != normalized_status:
            continue
        searchable = " ".join(
            [
                index_entry.recurrence_key,
                index_entry.problem,
                index_entry.lesson,
                index_entry.learning_type,
                *index_entry.trigger_signals,
                *index_entry.applies_to,
            ]
        ).casefold()
        if normalized_query and normalized_query not in searchable:
            continue
        cards.append(
            _learning_summary_card(
                index_entry,
                entry,
                source_layer,
                command_name=normalized_command,
            )
        )

    total = len(cards)
    page = cards[cursor:] if include_all else cards[cursor : cursor + limit]
    next_cursor = None if cursor + len(page) >= total else cursor + len(page)
    next_argv: list[str] | None = None
    if next_cursor is not None:
        next_argv = ["specify", "learning", "list"]
        if normalized_command:
            next_argv.extend(["--command", normalized_command])
        if normalized_type:
            next_argv.extend(["--type", normalized_type])
        if normalized_status:
            next_argv.extend(["--status", normalized_status])
        if query:
            next_argv.extend(["--query", query])
        next_argv.extend(
            ["--cursor", str(next_cursor), "--limit", str(limit), "--format", "json"]
        )
    return {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/summaryList",
        "command": normalized_command,
        "policy": learning_workflow_policy(normalized_command)
        if normalized_command
        else None,
        "filters": {
            "type": normalized_type,
            "status": normalized_status,
            "query": query or None,
        },
        "pagination": {
            "cursor": cursor,
            "limit": None if include_all else limit,
            "returned": len(page),
            "total": total,
            "next_cursor": next_cursor,
            "next_argv": next_argv,
        },
        "items": page,
        "warnings": list(diagnostics.get("warnings", [])),
    }


def show_learning_detail(project_root: Path, *, learning_ref: str) -> dict[str, Any]:
    """Expand exactly one Learning into an agent-oriented detail record."""

    requested = learning_ref.strip()
    if not requested:
        raise ValueError("learning ref is required")
    paths, catalog, diagnostics = _learning_catalog(project_root)
    match = next(
        (item for item in catalog if requested in {item[0].id, item[0].recurrence_key}),
        None,
    )
    if match is None:
        raise ValueError(f"learning '{requested}' not found")
    index_entry, entry, source_layer = match

    detail_path: Path | None = None
    if _is_valid_detail_ref(index_entry.detail) and _detail_ref_resolves_inside(
        paths.learning_index.parent, index_entry.detail
    ):
        candidate_path = _detail_path_for_ref(
            paths.learning_index.parent, index_entry.detail
        )
        if candidate_path.is_file():
            detail_path = candidate_path
            detail_entries = _read_entries_if_present(candidate_path)
            detail_entry = next(
                (
                    item
                    for item in detail_entries
                    if item.recurrence_key == index_entry.recurrence_key
                ),
                None,
            )
            if detail_entry is not None:
                entry = detail_entry

    problem = entry.problem if entry and entry.problem else index_entry.problem
    action = (
        entry.recommended_action
        if entry and entry.recommended_action
        else index_entry.lesson
    )
    return {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/detailRecord",
        "ref": index_entry.recurrence_key,
        "id": index_entry.id,
        "summary": entry.summary if entry else index_entry.problem,
        "type": index_entry.learning_type,
        "status": entry.status if entry else "indexed",
        "guidance": {
            "problem": problem,
            "action": action,
            "avoid": entry.avoid if entry else [],
            "success_criteria": entry.success_criteria if entry else [],
            "exceptions": entry.exceptions if entry else [],
        },
        "applicability": {
            "commands": index_entry.applies_to,
            "trigger_signals": index_entry.trigger_signals,
            "scope": entry.default_scope if entry else "",
        },
        "evidence": {
            "observation": entry.evidence if entry else index_entry.lesson,
            "decisive_signal": entry.decisive_signal if entry else "",
            "false_starts": entry.false_starts if entry else [],
            "rejected_paths": entry.rejected_paths if entry else [],
            "root_cause_family": entry.root_cause_family if entry else "",
        },
        "provenance": {
            "source_command": index_entry.source_command,
            "first_seen": index_entry.first_seen,
            "last_seen": index_entry.last_seen,
            "occurrences": index_entry.occurrence_count,
            "source_layer": source_layer,
        },
        "lifecycle": {
            "signal": index_entry.signal_strength,
            "pain_score": entry.pain_score if entry else 0,
            "injection_targets": entry.injection_targets if entry else [],
            "promotion_hint": entry.promotion_hint if entry else "",
        },
        "detail_path": str(detail_path) if detail_path else None,
        "warnings": list(diagnostics.get("warnings", [])),
    }


def start_learning_session(project_root: Path, *, command_name: str) -> dict[str, Any]:
    """Return the compact, read-only Learning intake for one workflow."""

    paths = build_learning_paths(project_root)
    normalized_command = normalize_command_name(command_name)
    catalog = list_learning_summaries(
        project_root,
        command_name=normalized_command,
        limit=20,
    )
    candidates = [
        entry
        for entry in _read_entries_if_present(paths.candidates)
        if is_relevant_to_command(entry, normalized_command)
    ]
    return {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/startSummary",
        "command": normalized_command,
        "policy": learning_workflow_policy(normalized_command),
        "read_only": True,
        "items": catalog["items"],
        "pagination": catalog["pagination"],
        "promotion_ready": [
            {
                "ref": entry.recurrence_key,
                "summary": entry.summary,
                "occurrences": entry.occurrence_count,
            }
            for entry in candidates
            if entry.occurrence_count >= 2
        ],
        "needs_confirmation": [
            {
                "ref": entry.recurrence_key,
                "summary": entry.summary,
                "signal": entry.signal_strength,
            }
            for entry in candidates
            if is_highest_signal(entry)
        ],
        "warnings": catalog["warnings"],
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
    problem: str | None = None,
    recommended_action: str | None = None,
    avoid: Iterable[str] | None = None,
    trigger_signals: Iterable[str] | None = None,
    success_criteria: Iterable[str] | None = None,
    exceptions: Iterable[str] | None = None,
) -> dict[str, Any]:
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
        problem=problem,
        recommended_action=recommended_action,
        avoid=avoid,
        trigger_signals=trigger_signals,
        success_criteria=success_criteria,
        exceptions=exceptions,
    )

    with interprocess_lock(_learning_lock_path(project_root)):
        paths = _ensure_learning_files_unlocked(project_root)
        return _store_learning_entry(paths, entry, confirm=confirm)


def _store_learning_entry(
    paths: LearningPaths,
    entry: LearningEntry,
    *,
    confirm: bool,
) -> dict[str, Any]:

    if confirm:
        preamble, learning_entries = _read_entries(paths.confirmed_learnings)
        learning_entries, stored = _upsert_entry(
            learning_entries, entry, status="confirmed"
        )
        _write_entries(
            paths.confirmed_learnings,
            preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
            learning_entries,
        )
        candidate_preamble, candidate_entries = _read_entries(paths.candidates)
        candidate_entries = _remove_by_recurrence(
            candidate_entries, stored.recurrence_key
        )
        _write_entries(
            paths.candidates,
            candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
            candidate_entries,
        )
        _append_review_note(
            paths.review,
            f"confirmed `{stored.recurrence_key}` from `{stored.source_command}`",
        )
        stored_index, detail_path = _sync_learning_index_detail(paths, stored)
        return {
            "status": "confirmed",
            "entry": stored.to_payload(),
            "index_entry": stored_index.to_payload(),
            "detail_path": str(detail_path),
            "needs_confirmation": False,
        }

    preamble, candidate_entries = _read_entries(paths.candidates)
    candidate_entries, stored = _upsert_entry(
        candidate_entries, entry, status="candidate"
    )
    _write_entries(
        paths.candidates,
        preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
        candidate_entries,
    )
    _append_review_note(
        paths.review,
        f"captured candidate `{stored.recurrence_key}` from `{stored.source_command}`",
    )
    stored_index, detail_path = _sync_learning_index_detail(paths, stored)
    return {
        "status": "candidate",
        "entry": stored.to_payload(),
        "index_entry": stored_index.to_payload(),
        "detail_path": str(detail_path),
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
    with interprocess_lock(_learning_lock_path(project_root)):
        paths = _ensure_learning_files_unlocked(project_root)
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
            entry = build_learning_entry(
                command_name=normalized_command,
                learning_type=suggestion.learning_type,
                summary=suggestion.summary,
                evidence=suggestion.evidence,
                recurrence_key=suggestion.recurrence_key,
                signal_strength=suggestion.signal_strength,
                applies_to=suggestion.applies_to,
                status="candidate",
                problem=suggestion.problem or None,
                recommended_action=suggestion.recommended_action or None,
                trigger_signals=suggestion.trigger_signals,
                success_criteria=suggestion.success_criteria,
                avoid=suggestion.avoid,
                exceptions=suggestion.exceptions,
            )
            captured.append(_store_learning_entry(paths, entry, confirm=False))

        registry[fingerprint] = {
            "command": normalized_command,
            "source_path": str(source_path),
            "recurrence_keys": [item["entry"]["recurrence_key"] for item in captured],
            "captured_entries": [item["entry"] for item in captured],
            "captured_at": now_iso(),
        }
        _write_auto_capture_registry(project_root, registry)
        _append_review_note(
            paths.review,
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
    normalized_recurrence_key = str(recurrence_key or "").strip().lower()
    if not normalized_recurrence_key:
        raise ValueError("learning recurrence_key is required")

    with interprocess_lock(_learning_lock_path(project_root)):
        paths = _ensure_learning_files_unlocked(project_root)
        return _promote_learning_locked(
            paths,
            recurrence_key=normalized_recurrence_key,
            normalized_target=normalized_target,
        )


def _promote_learning_locked(
    paths: LearningPaths,
    *,
    recurrence_key: str,
    normalized_target: str,
) -> dict[str, Any]:

    candidate_preamble, candidate_entries = _read_entries(paths.candidates)
    learning_preamble, learning_entries = _read_entries(paths.confirmed_learnings)
    rule_preamble, rule_entries = _read_entries(paths.project_rules)

    source_entry = next(
        (
            entry
            for entry in candidate_entries
            if entry.recurrence_key == recurrence_key
        ),
        None,
    )
    source_layer = "candidates"
    if source_entry is None:
        source_entry = next(
            (
                entry
                for entry in learning_entries
                if entry.recurrence_key == recurrence_key
            ),
            None,
        )
        source_layer = "confirmed_learnings"
    if source_entry is None:
        source_entry = next(
            (entry for entry in rule_entries if entry.recurrence_key == recurrence_key),
            None,
        )
        source_layer = "project_rules"
    if source_entry is None:
        raise ValueError(f"learning '{recurrence_key}' not found")

    if normalized_target == "learning":
        source_entry.status = "confirmed"
        learning_entries, stored = _upsert_entry(
            learning_entries, source_entry, status="confirmed"
        )
        candidate_entries = _remove_by_recurrence(candidate_entries, recurrence_key)
        _write_entries(
            paths.confirmed_learnings,
            learning_preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
            learning_entries,
        )
        _write_entries(
            paths.candidates,
            candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
            candidate_entries,
        )
        _append_review_note(
            paths.review,
            f"promoted `{recurrence_key}` to project learnings from `{source_layer}`",
        )
        stored_index, detail_path = _sync_learning_index_detail(paths, stored)
        return {
            "status": "confirmed",
            "entry": stored.to_payload(),
            "index_entry": stored_index.to_payload(),
            "detail_path": str(detail_path),
        }

    source_entry.status = "promoted-rule"
    rule_entries, stored = _upsert_entry(
        rule_entries, source_entry, status="promoted-rule"
    )
    candidate_entries = _remove_by_recurrence(candidate_entries, recurrence_key)
    learning_entries = _remove_by_recurrence(learning_entries, recurrence_key)
    _write_entries(
        paths.project_rules, rule_preamble or RULES_TEMPLATE_TEXT.rstrip(), rule_entries
    )
    _write_entries(
        paths.confirmed_learnings,
        learning_preamble or CONFIRMED_LEARNINGS_TEMPLATE_TEXT.rstrip(),
        learning_entries,
    )
    _write_entries(
        paths.candidates,
        candidate_preamble or CANDIDATES_TEMPLATE_TEXT.rstrip(),
        candidate_entries,
    )
    _append_review_note(
        paths.review,
        f"promoted `{recurrence_key}` to project rules from `{source_layer}`",
    )
    stored_index, detail_path = _sync_learning_index_detail(paths, stored)
    return {
        "status": "promoted-rule",
        "entry": stored.to_payload(),
        "index_entry": stored_index.to_payload(),
        "detail_path": str(detail_path),
    }


def _entry_counts(project_root: Path) -> dict[str, int]:
    paths = build_learning_paths(project_root)
    _, candidate_entries = (
        _read_entries(paths.candidates) if paths.candidates.exists() else ("", [])
    )
    _, learning_entries = (
        _read_entries(paths.confirmed_learnings)
        if paths.confirmed_learnings.exists()
        else ("", [])
    )
    _, rule_entries = (
        _read_entries(paths.project_rules) if paths.project_rules.exists() else ("", [])
    )
    return {
        "candidates": len(candidate_entries),
        "confirmed_learnings": len(learning_entries),
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
            "confirmed_learnings": paths.confirmed_learnings.exists(),
            "learning_index": paths.learning_index.exists(),
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
