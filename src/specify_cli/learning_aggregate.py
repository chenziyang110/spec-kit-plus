from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .learnings import (
    LearningEntry,
    build_learning_paths,
    ensure_learning_files,
    read_learning_entries,
)


PromotionState = Literal[
    "informational",
    "approaching_threshold",
    "promotion_ready",
    "already_promoted",
    "stale",
]


@dataclass(slots=True, frozen=True)
class AggregatedLearningPattern:
    recurrence_key: str
    top_summary: str
    learning_types: list[str]
    source_commands: list[str]
    applies_to: list[str]
    signal_strengths: list[str]
    first_seen: str
    last_seen: str
    total_occurrences: int
    layer_counts: dict[str, int]
    recommended_target: str | None
    promotion_state: PromotionState

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _rank_signal(values: list[str]) -> list[str]:
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(_unique(values), key=lambda item: order.get(item, 99))


def _recommended_target(
    learning_types: list[str],
    layer_counts: dict[str, int],
    total_occurrences: int,
    strongest_signal: str,
) -> str | None:
    if layer_counts["rule"] > 0:
        return None
    if layer_counts["confirmed"] > 0 and total_occurrences >= 3:
        if strongest_signal == "high" or any(
            item in {"project_constraint", "user_preference"} for item in learning_types
        ):
            return "rule"
    if layer_counts["candidate"] > 0 and total_occurrences >= 3:
        return "learning"
    return None


def _promotion_state(
    layer_counts: dict[str, int],
    total_occurrences: int,
    strongest_signal: str,
    last_seen: str,
    stale_after_days: int,
) -> PromotionState:
    if layer_counts["rule"] > 0:
        return "already_promoted"
    age_days = (datetime.now(tz=UTC) - _parse_iso(last_seen)).days
    if age_days >= stale_after_days:
        return "stale"
    if total_occurrences >= 3:
        return "promotion_ready"
    if total_occurrences >= 2 or strongest_signal == "high":
        return "approaching_threshold"
    return "informational"


def aggregate_learning_patterns(
    *,
    candidate_entries: list[LearningEntry],
    confirmed_entries: list[LearningEntry],
    rule_entries: list[LearningEntry],
    stale_after_days: int = 90,
) -> list[AggregatedLearningPattern]:
    grouped: dict[str, list[tuple[str, LearningEntry]]] = {}
    for layer_name, entries in (
        ("candidate", candidate_entries),
        ("confirmed", confirmed_entries),
        ("rule", rule_entries),
    ):
        for entry in entries:
            grouped.setdefault(entry.recurrence_key, []).append((layer_name, entry))

    patterns: list[AggregatedLearningPattern] = []
    for recurrence_key, grouped_entries in grouped.items():
        entries = [entry for _layer, entry in grouped_entries]
        layers = [layer for layer, _entry in grouped_entries]
        layer_counts = {
            "candidate": layers.count("candidate"),
            "confirmed": layers.count("confirmed"),
            "rule": layers.count("rule"),
        }
        signal_strengths = _rank_signal([entry.signal_strength for entry in entries])
        strongest_signal = signal_strengths[0]
        learning_types = _unique([entry.learning_type for entry in entries])
        patterns.append(
            AggregatedLearningPattern(
                recurrence_key=recurrence_key,
                top_summary=entries[0].summary,
                learning_types=learning_types,
                source_commands=sorted(_unique([entry.source_command for entry in entries])),
                applies_to=sorted(
                    _unique([command for entry in entries for command in entry.applies_to])
                ),
                signal_strengths=signal_strengths,
                first_seen=min(entry.first_seen for entry in entries),
                last_seen=max(entry.last_seen for entry in entries),
                total_occurrences=sum(entry.occurrence_count for entry in entries),
                layer_counts=layer_counts,
                recommended_target=_recommended_target(
                    learning_types,
                    layer_counts,
                    sum(entry.occurrence_count for entry in entries),
                    strongest_signal,
                ),
                promotion_state=_promotion_state(
                    layer_counts,
                    sum(entry.occurrence_count for entry in entries),
                    strongest_signal,
                    max(entry.last_seen for entry in entries),
                    stale_after_days,
                ),
            )
        )
    return sorted(
        patterns,
        key=lambda item: (
            item.promotion_state != "promotion_ready",
            -item.total_occurrences,
            item.recurrence_key,
        ),
    )


def aggregate_learning_state(
    project_root: Path,
    *,
    command_name: str | None = None,
    stale_after_days: int = 90,
) -> dict[str, object]:
    ensure_learning_files(project_root)
    paths = build_learning_paths(project_root)
    _candidate_preamble, candidate_entries = read_learning_entries(paths.candidates)
    _learning_preamble, confirmed_entries = read_learning_entries(paths.project_learnings)
    _rule_preamble, rule_entries = read_learning_entries(paths.project_rules)

    patterns = aggregate_learning_patterns(
        candidate_entries=candidate_entries,
        confirmed_entries=confirmed_entries,
        rule_entries=rule_entries,
        stale_after_days=stale_after_days,
    )
    if command_name:
        normalized_command = command_name if command_name.startswith("sp-") else f"sp-{command_name}"
        patterns = [pattern for pattern in patterns if normalized_command in pattern.applies_to]

    payload_patterns = [pattern.to_payload() for pattern in patterns]
    return {
        "generated_at": datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "paths": paths.to_dict(),
        "counts": {
            "patterns": len(payload_patterns),
            "promotion_ready": sum(1 for pattern in patterns if pattern.promotion_state == "promotion_ready"),
            "approaching_threshold": sum(1 for pattern in patterns if pattern.promotion_state == "approaching_threshold"),
            "stale": sum(1 for pattern in patterns if pattern.promotion_state == "stale"),
            "candidates": len(candidate_entries),
            "confirmed": len(confirmed_entries),
            "rules": len(rule_entries),
        },
        "patterns": payload_patterns,
    }


def render_learning_aggregate_report(report: dict[str, object]) -> str:
    patterns = report["patterns"]
    promotion_ready = [item for item in patterns if item["promotion_state"] == "promotion_ready"]
    approaching = [item for item in patterns if item["promotion_state"] == "approaching_threshold"]
    stale = [item for item in patterns if item["promotion_state"] == "stale"]

    def _section(title: str, rows: list[dict[str, object]]) -> list[str]:
        if not rows:
            return [f"## {title}", "", "_None._", ""]
        lines = [f"## {title}", ""]
        for item in rows:
            lines.extend(
                [
                    f"### {item['recurrence_key']} - {item['top_summary']}",
                    "",
                    f"- Promotion State: `{item['promotion_state']}`",
                    f"- Recommended Target: `{item['recommended_target'] or 'none'}`",
                    f"- Occurrences: {item['total_occurrences']}",
                    f"- Learning Types: {', '.join(item['learning_types'])}",
                    f"- Source Commands: {', '.join(item['source_commands'])}",
                    f"- Last Seen: `{item['last_seen']}`",
                    "",
                ]
            )
        return lines

    lines = [
        "# Learning Aggregate Report",
        "",
        f"- Generated At: `{report['generated_at']}`",
        f"- Patterns: {report['counts']['patterns']}",
        f"- Promotion Ready: {report['counts']['promotion_ready']}",
        f"- Approaching Threshold: {report['counts']['approaching_threshold']}",
        f"- Stale: {report['counts']['stale']}",
        "",
    ]
    lines.extend(_section("Promotion-Ready Patterns", promotion_ready))
    lines.extend(_section("Approaching Threshold", approaching))
    lines.extend(_section("Stale Patterns", stale))
    return "\n".join(lines).rstrip() + "\n"


def learning_aggregate_report_path(project_root: Path, *, generated_at: str) -> Path:
    stamp = generated_at.replace(":", "").replace("-", "").replace("T", "-").replace("Z", "")
    return project_root / ".planning" / "learnings" / "reports" / f"{stamp}.md"


def write_learning_aggregate_report(project_root: Path, report: dict[str, object]) -> Path:
    path = learning_aggregate_report_path(project_root, generated_at=str(report["generated_at"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_learning_aggregate_report(report), encoding="utf-8")
    return path
