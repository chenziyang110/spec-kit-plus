# PR1 Learning Aggregation Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** add a first-party `specify learning aggregate` capability that groups passive learning entries by recurrence key, classifies promotion readiness, optionally writes a report, and enriches `specify learning start` with pre-flight warning summaries.

**Architecture:** keep the existing learning storage model in `src/specify_cli/learnings.py`, add a focused sibling module for aggregation and report rendering, then wire a new CLI command in `src/specify_cli/__init__.py`. Reuse the current `.specify/memory/` and `.planning/learnings/` state instead of creating new top-level directories.

**Tech Stack:** Python 3.13, Typer CLI, dataclasses, JSON-backed markdown sections, pytest, typer `CliRunner`

---

## File Structure

### Existing files to modify

- `src/specify_cli/learnings.py`
  - Keep ownership of learning paths, entry schema, candidate/confirmed/rule promotion, and learning-start payloads.
  - Add only the minimum public helpers needed by the new aggregation module.
- `src/specify_cli/__init__.py`
  - Add the new `learning aggregate` subcommand under the existing `learning_app`.
  - Keep the CLI output style aligned with the current `learning ensure/status/start/capture/promote` commands.
- `tests/test_learning_cli.py`
  - Extend the current CLI suite with `learning aggregate` command coverage and the new `learning start` summary fields.
- `README.md`
  - Document the new aggregation helper in the passive project learning section.
- `docs/quickstart.md`
  - Add one short mention of when to use `specify learning aggregate`.

### New files to create

- `src/specify_cli/learning_aggregate.py`
  - Own pure aggregation logic, classification rules, JSON payload assembly, markdown report rendering, and optional report writing.
- `tests/test_learning_aggregate.py`
  - Own pure aggregation/report tests so CLI failures and aggregation-logic failures stay separated.

### Design boundaries

- Do not create `.learnings/`, `.context-surfing/`, or `.evals/`.
- Do not change the existing `LearningEntry` storage format in this PR.
- Do not add CI automation in this PR.
- Do not introduce a new top-level workflow; keep everything under `specify learning`.

## Task 1: Add Pure Aggregation Models And Classification Rules

**Files:**
- Create: `src/specify_cli/learning_aggregate.py`
- Create: `tests/test_learning_aggregate.py`
- Modify: `src/specify_cli/learnings.py`

- [ ] **Step 1: Write the failing aggregation tests**

```python
from specify_cli.learnings import LearningEntry
from specify_cli.learning_aggregate import aggregate_learning_patterns


def _entry(
    *,
    recurrence_key: str,
    status: str,
    occurrence_count: int,
    summary: str,
    source_command: str = "sp-implement",
    learning_type: str = "pitfall",
    signal_strength: str = "medium",
    first_seen: str = "2026-04-20T00:00:00Z",
    last_seen: str = "2026-04-24T00:00:00Z",
) -> LearningEntry:
    return LearningEntry(
        id=f"{status}-{occurrence_count}",
        summary=summary,
        learning_type=learning_type,
        source_command=source_command,
        evidence="captured during test setup",
        recurrence_key=recurrence_key,
        default_scope="implementation-heavy",
        applies_to=["sp-implement", "sp-debug"],
        signal_strength=signal_strength,
        status=status,
        first_seen=first_seen,
        last_seen=last_seen,
        occurrence_count=occurrence_count,
    )


def test_aggregate_learning_patterns_groups_same_recurrence_key_across_layers() -> None:
    patterns = aggregate_learning_patterns(
        candidate_entries=[
            _entry(
                recurrence_key="shared.boundary.pattern",
                status="candidate",
                occurrence_count=2,
                summary="Preserve shared boundary pattern",
            )
        ],
        confirmed_entries=[
            _entry(
                recurrence_key="shared.boundary.pattern",
                status="confirmed",
                occurrence_count=1,
                summary="Preserve shared boundary pattern",
                source_command="sp-plan",
            )
        ],
        rule_entries=[],
    )

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.recurrence_key == "shared.boundary.pattern"
    assert pattern.total_occurrences == 3
    assert pattern.layer_counts == {"candidate": 1, "confirmed": 1, "rule": 0}
    assert pattern.source_commands == ["sp-implement", "sp-plan"]
    assert pattern.top_summary == "Preserve shared boundary pattern"


def test_aggregate_learning_patterns_marks_candidate_with_three_occurrences_as_promotion_ready() -> None:
    patterns = aggregate_learning_patterns(
        candidate_entries=[
            _entry(
                recurrence_key="workflow.validation.tasks",
                status="candidate",
                occurrence_count=3,
                summary="Always preserve validation tasks",
                learning_type="workflow_gap",
            )
        ],
        confirmed_entries=[],
        rule_entries=[],
    )

    pattern = patterns[0]
    assert pattern.promotion_state == "promotion_ready"
    assert pattern.recommended_target == "learning"


def test_aggregate_learning_patterns_marks_confirmed_project_constraint_as_rule_candidate() -> None:
    patterns = aggregate_learning_patterns(
        candidate_entries=[],
        confirmed_entries=[
            _entry(
                recurrence_key="shared.surfaces.must.be.named",
                status="confirmed",
                occurrence_count=3,
                summary="Always name touched shared surfaces explicitly",
                learning_type="project_constraint",
                signal_strength="high",
            )
        ],
        rule_entries=[],
    )

    pattern = patterns[0]
    assert pattern.promotion_state == "promotion_ready"
    assert pattern.recommended_target == "rule"
```

- [ ] **Step 2: Run the pure aggregation test file and verify it fails**

Run:

```powershell
python -m pytest tests/test_learning_aggregate.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'specify_cli.learning_aggregate'
```

- [ ] **Step 3: Add the new aggregation module with pure dataclasses and classifiers**

Create `src/specify_cli/learning_aggregate.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal

from .learnings import LearningEntry


PromotionState = Literal["informational", "approaching_threshold", "promotion_ready", "already_promoted", "stale"]


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
            ordered.append(value)
            seen.add(value)
    return ordered


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _rank_signal(values: list[str]) -> list[str]:
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(_unique(values), key=lambda item: order.get(item, 99))


def _recommended_target(learning_types: list[str], layer_counts: dict[str, int], total_occurrences: int, strongest_signal: str) -> str | None:
    if layer_counts["rule"] > 0:
        return None
    if layer_counts["confirmed"] > 0 and total_occurrences >= 3:
        if strongest_signal == "high" or any(item in {"project_constraint", "user_preference"} for item in learning_types):
            return "rule"
    if layer_counts["candidate"] > 0 and total_occurrences >= 3:
        return "learning"
    return None


def _promotion_state(layer_counts: dict[str, int], total_occurrences: int, strongest_signal: str, last_seen: str, stale_after_days: int) -> PromotionState:
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
        entries = [item for _layer, item in grouped_entries]
        layers = [layer for layer, _item in grouped_entries]
        layer_counts = {
            "candidate": layers.count("candidate"),
            "confirmed": layers.count("confirmed"),
            "rule": layers.count("rule"),
        }
        first_seen = min(entry.first_seen for entry in entries)
        last_seen = max(entry.last_seen for entry in entries)
        total_occurrences = sum(entry.occurrence_count for entry in entries)
        signal_strengths = _rank_signal([entry.signal_strength for entry in entries])
        strongest_signal = signal_strengths[0]
        learning_types = _unique([entry.learning_type for entry in entries])
        patterns.append(
            AggregatedLearningPattern(
                recurrence_key=recurrence_key,
                top_summary=entries[0].summary,
                learning_types=learning_types,
                source_commands=sorted(_unique([entry.source_command for entry in entries])),
                applies_to=sorted(_unique([command for entry in entries for command in entry.applies_to])),
                signal_strengths=signal_strengths,
                first_seen=first_seen,
                last_seen=last_seen,
                total_occurrences=total_occurrences,
                layer_counts=layer_counts,
                recommended_target=_recommended_target(learning_types, layer_counts, total_occurrences, strongest_signal),
                promotion_state=_promotion_state(layer_counts, total_occurrences, strongest_signal, last_seen, stale_after_days),
            )
        )
    return sorted(patterns, key=lambda item: (item.promotion_state != "promotion_ready", -item.total_occurrences, item.recurrence_key))
```

- [ ] **Step 4: Export a public entry reader from `learnings.py` for reuse**

Modify `src/specify_cli/learnings.py` by adding this helper after `_read_entries()`:

```python
def read_learning_entries(path: Path) -> tuple[str, list[LearningEntry]]:
    return _read_entries(path)
```

- [ ] **Step 5: Re-run the pure aggregation tests**

Run:

```powershell
python -m pytest tests/test_learning_aggregate.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/learning_aggregate.py src/specify_cli/learnings.py tests/test_learning_aggregate.py
git commit -m "feat: add learning aggregation primitives"
```

## Task 2: Add Project-Level Aggregation Payload And Report Writer

**Files:**
- Modify: `src/specify_cli/learning_aggregate.py`
- Modify: `tests/test_learning_aggregate.py`

- [ ] **Step 1: Write the failing project-level aggregation and report tests**

Append to `tests/test_learning_aggregate.py`:

```python
from pathlib import Path

from specify_cli.learning_aggregate import aggregate_learning_state, render_learning_aggregate_report
from specify_cli.learnings import ensure_learning_files, capture_learning


def test_aggregate_learning_state_reads_candidates_confirmed_and_rules(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    for name in ("project-rules-template.md", "project-learnings-template.md"):
        (project / ".specify" / "templates" / name).write_text((templates_root / name).read_text(encoding="utf-8"), encoding="utf-8")

    ensure_learning_files(project)
    capture_learning(
        project,
        command_name="implement",
        learning_type="pitfall",
        summary="Preserve shared boundary pattern",
        evidence="first capture",
        recurrence_key="shared.boundary.pattern",
    )
    capture_learning(
        project,
        command_name="implement",
        learning_type="pitfall",
        summary="Preserve shared boundary pattern",
        evidence="second capture",
        recurrence_key="shared.boundary.pattern",
        confirm=True,
    )

    report = aggregate_learning_state(project)

    assert report["counts"]["patterns"] == 1
    assert report["counts"]["confirmed"] == 1
    assert report["counts"]["candidates"] == 0
    assert report["patterns"][0]["recurrence_key"] == "shared.boundary.pattern"


def test_render_learning_aggregate_report_includes_promotion_ready_and_stale_sections() -> None:
    report = {
        "generated_at": "2026-04-24T00:00:00Z",
        "counts": {
            "patterns": 2,
            "promotion_ready": 1,
            "approaching_threshold": 0,
            "stale": 1,
            "candidates": 1,
            "confirmed": 0,
            "rules": 0,
        },
        "patterns": [
            {
                "recurrence_key": "workflow.validation.tasks",
                "top_summary": "Always preserve validation tasks",
                "promotion_state": "promotion_ready",
                "recommended_target": "learning",
                "total_occurrences": 3,
                "source_commands": ["sp-plan"],
                "learning_types": ["workflow_gap"],
                "last_seen": "2026-04-24T00:00:00Z",
            },
            {
                "recurrence_key": "debug.snapshot.drift",
                "top_summary": "Re-check snapshot drift",
                "promotion_state": "stale",
                "recommended_target": None,
                "total_occurrences": 1,
                "source_commands": ["sp-debug"],
                "learning_types": ["recovery_path"],
                "last_seen": "2025-12-01T00:00:00Z",
            },
        ],
    }

    content = render_learning_aggregate_report(report)

    assert "Promotion-Ready Patterns" in content
    assert "workflow.validation.tasks" in content
    assert "Stale Patterns" in content
    assert "debug.snapshot.drift" in content
```

- [ ] **Step 2: Run the test file and verify the new tests fail**

Run:

```powershell
python -m pytest tests/test_learning_aggregate.py -q
```

Expected:

```text
E   ImportError: cannot import name 'aggregate_learning_state'
```

- [ ] **Step 3: Add project-level aggregation and report rendering functions**

Append to `src/specify_cli/learning_aggregate.py`:

```python
from pathlib import Path

from .learnings import build_learning_paths, ensure_learning_files, read_learning_entries


def aggregate_learning_state(project_root: Path, *, command_name: str | None = None, stale_after_days: int = 90) -> dict[str, object]:
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
        normalized = command_name if command_name.startswith("sp-") else f"sp-{command_name}"
        patterns = [pattern for pattern in patterns if normalized in pattern.applies_to]

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
```

- [ ] **Step 4: Add report-path helper and write function**

Append to `src/specify_cli/learning_aggregate.py`:

```python
def learning_aggregate_report_path(project_root: Path, *, generated_at: str) -> Path:
    stamp = generated_at.replace(":", "").replace("-", "").replace("T", "-").replace("Z", "")
    return project_root / ".planning" / "learnings" / "reports" / f"{stamp}.md"


def write_learning_aggregate_report(project_root: Path, report: dict[str, object]) -> Path:
    path = learning_aggregate_report_path(project_root, generated_at=str(report["generated_at"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_learning_aggregate_report(report), encoding="utf-8")
    return path
```

- [ ] **Step 5: Re-run aggregation tests**

Run:

```powershell
python -m pytest tests/test_learning_aggregate.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/learning_aggregate.py tests/test_learning_aggregate.py
git commit -m "feat: add learning aggregate report generation"
```

## Task 3: Add `specify learning aggregate` CLI Surface

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_learning_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_learning_cli.py`:

```python
def test_learning_aggregate_json_reports_grouped_patterns(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Need to preserve shared boundary pattern",
            "--evidence",
            "Observed during implementation",
            "--recurrence-key",
            "shared.boundary.pattern",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["learning", "aggregate", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["counts"]["patterns"] == 1
    assert payload["patterns"][0]["recurrence_key"] == "shared.boundary.pattern"


def test_learning_aggregate_write_report_creates_markdown_output(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(project, ["learning", "aggregate", "--format", "json", "--write-report"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    report_path = Path(payload["report_path"])
    assert report_path.exists()
    assert "Learning Aggregate Report" in report_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the learning CLI tests and verify the new tests fail**

Run:

```powershell
python -m pytest tests/test_learning_cli.py -q
```

Expected:

```text
AssertionError: "aggregate" not available under the learning CLI
```

- [ ] **Step 3: Wire the new command into `src/specify_cli/__init__.py`**

Add imports near the top:

```python
from specify_cli.learning_aggregate import (
    aggregate_learning_state,
    write_learning_aggregate_report,
)
```

Add the command after `learning_promote_command`:

```python
@learning_app.command("aggregate")
def learning_aggregate_command(
    command_name: str | None = typer.Option(None, "--command", help="Optional workflow command filter, for example plan or sp-implement"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    write_report: bool = typer.Option(False, "--write-report", help="Also write a markdown report under .planning/learnings/reports/"),
    stale_after_days: int = typer.Option(90, "--stale-after-days", help="Mark inactive patterns as stale after this many days"),
):
    \"\"\"Aggregate passive project learnings into a promotion-oriented report.\"\"\"
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = aggregate_learning_state(
        project_root,
        command_name=command_name,
        stale_after_days=stale_after_days,
    )
    if write_report:
        payload["report_path"] = str(write_learning_aggregate_report(project_root, payload))
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Patterns", str(payload["counts"]["patterns"])),
        ("Promotion Ready", str(payload["counts"]["promotion_ready"])),
        ("Approaching", str(payload["counts"]["approaching_threshold"])),
        ("Stale", str(payload["counts"]["stale"])),
    ]
    if "report_path" in payload:
        rows.append(("Report", f"[dim]{payload['report_path']}[/dim]"))
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Aggregate", border_style="cyan"))
```

- [ ] **Step 4: Re-run the learning CLI tests**

Run:

```powershell
python -m pytest tests/test_learning_cli.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 5: Commit**

```powershell
git add src/specify_cli/__init__.py tests/test_learning_cli.py
git commit -m "feat: add learning aggregate command"
```

## Task 4: Enrich `learning start` With Pre-Flight Warning Summaries

**Files:**
- Modify: `src/specify_cli/learnings.py`
- Modify: `tests/test_learning_cli.py`

- [ ] **Step 1: Write the failing `learning start` summary test**

Append to `tests/test_learning_cli.py`:

```python
def test_learning_start_exposes_top_warnings_and_summary_counts(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "pitfall",
        "--summary",
        "Need to preserve shared boundary pattern",
        "--evidence",
        "Observed during implementation",
        "--recurrence-key",
        "shared.boundary.pattern",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _invoke_in_project(project, ["learning", "start", "--command", "implement", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary_counts"]["relevant_candidates"] == 1
    assert payload["top_warnings"][0]["recurrence_key"] == "shared.boundary.pattern"
    assert payload["top_warnings"][0]["summary"] == "Need to preserve shared boundary pattern"
```

- [ ] **Step 2: Run the targeted learning CLI test and verify it fails**

Run:

```powershell
python -m pytest tests/test_learning_cli.py::test_learning_start_exposes_top_warnings_and_summary_counts -q
```

Expected:

```text
KeyError: 'summary_counts'
```

- [ ] **Step 3: Add warning summarization in `start_learning_session()`**

Modify the end of `start_learning_session()` in `src/specify_cli/learnings.py`:

```python
    top_warning_entries = sorted(
        [
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
        "summary_counts": {
            "relevant_rules": len(relevant_rules),
            "relevant_learnings": len(relevant_learnings),
            "relevant_candidates": len(relevant_candidates),
            "auto_promoted": len(auto_promoted),
            "promotable_candidates": len(promotable),
            "confirmation_candidates": len(confirmation_candidates),
        },
        "top_warnings": top_warnings,
    }
```

- [ ] **Step 4: Re-run the targeted test**

Run:

```powershell
python -m pytest tests/test_learning_cli.py::test_learning_start_exposes_top_warnings_and_summary_counts -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run the full learning CLI suite**

Run:

```powershell
python -m pytest tests/test_learning_cli.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/learnings.py tests/test_learning_cli.py
git commit -m "feat: surface pre-flight learning warnings"
```

## Task 5: Update Docs And Run Full PR Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add failing documentation assertions**

Append to `tests/test_specify_guidance_docs.py`:

```python
def test_guidance_docs_include_learning_aggregate_surface() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = Path("docs/quickstart.md").read_text(encoding="utf-8")

    assert "specify learning aggregate" in readme
    assert "specify learning aggregate" in quickstart
```

- [ ] **Step 2: Run the targeted doc test and verify it fails**

Run:

```powershell
python -m pytest tests/test_specify_guidance_docs.py::test_guidance_docs_include_learning_aggregate_surface -q
```

Expected:

```text
AssertionError: 'specify learning aggregate' not found
```

- [ ] **Step 3: Update the passive learning documentation**

In `README.md`, add this bullet under the passive project learning helper surface:

```markdown
- `specify learning aggregate --format json`
```

Then add this explanatory sentence after the helper list:

```markdown
Use `specify learning aggregate` when you want a grouped, promotion-oriented summary of candidate, confirmed, and promoted learning patterns before deciding what should become a shared rule.
```

In `docs/quickstart.md`, add this bullet near the passive learning layer section:

```markdown
- `specify learning aggregate --format json` groups repeated patterns so operators can decide what to promote into shared learnings or rules.
```

- [ ] **Step 4: Re-run the doc test**

Run:

```powershell
python -m pytest tests/test_specify_guidance_docs.py::test_guidance_docs_include_learning_aggregate_surface -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run the full PR verification set**

Run:

```powershell
python -m pytest tests/test_learning_aggregate.py tests/test_learning_cli.py tests/test_specify_guidance_docs.py tests/test_alignment_templates.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Run the repo-wide proving command**

Run:

```powershell
python -m pytest
```

Expected:

```text
full suite passes with zero new failures
```

- [ ] **Step 7: Commit**

```powershell
git add README.md docs/quickstart.md tests/test_specify_guidance_docs.py
git commit -m "docs: document learning aggregate workflow"
```

## Self-Review

### Spec Coverage

- Aggregation API: covered in Task 1 and Task 2
- CLI surface: covered in Task 3
- In-session pre-flight warnings: covered in Task 4
- Docs and operator discoverability: covered in Task 5

### Placeholder Scan

- No `TODO`, `TBD`, or “similar to Task N” references remain.
- Every code-changing step includes explicit file paths and code blocks.
- Every test-running step includes an exact command and expected result.

### Type Consistency

- Aggregation model names stay consistent:
  - `AggregatedLearningPattern`
  - `aggregate_learning_patterns`
  - `aggregate_learning_state`
  - `render_learning_aggregate_report`
  - `write_learning_aggregate_report`
- CLI name is consistent everywhere:
  - `specify learning aggregate`

Plan complete and saved to `docs/superpowers/plans/2026-04-24-pr1-learning-aggregation-foundation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
