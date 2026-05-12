# Self-Learning V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the self-learning v2 memory model so downstream projects read a thin learning index first and write one detail document per reusable engineering lesson during normal workflow closeout.

**Architecture:** Extend the existing `specify_cli.learnings` file-backed runtime instead of adding a separate subsystem. Keep old `project-learnings.md` and `.planning/learnings/candidates.md` readable for compatibility, but make `.specify/memory/learnings/INDEX.md` plus per-lesson markdown files the primary write path. Propagate the new Learning Reflex through shared templates, generated context renderers, passive skills, and integration tests.

**Tech Stack:** Python 3.11, Typer CLI, PyYAML, pytest, markdown templates, existing Spec Kit integration renderers.

---

## File Structure

Create:

- `templates/project-learnings-index-template.md`: downstream template for `.specify/memory/learnings/INDEX.md`.
- `templates/project-learning-detail-template.md`: downstream template and documentation source for per-lesson detail markdown files.

Modify:

- `pyproject.toml`: include the two new templates in packaged wheel assets.
- `src/specify_cli/learnings.py`: add learning-index paths, data model, index/detail read-write helpers, start/capture/capture-auto integration, and compatibility reads.
- `src/specify_cli/__init__.py`: show index/detail state in learning CLI output and expose capture results.
- `src/specify_cli/learning_aggregate.py`: include index entries in aggregate reports without dropping old compatibility layers.
- `templates/project-learnings-template.md`: mark this file as compatibility/stable-summary storage rather than the primary read layer.
- `templates/command-partials/common/learning-layer.md`: replace candidate-first guidance with index/detail guidance and Learning Reflex.
- `templates/commands/{specify,clarify,constitution,deep-research,plan,tasks,analyze,checklist,implement,debug,quick,test-scan,test-build,map-scan,map-build}.md`: align command-local learning sections with index/detail closeout.
- `templates/passive-skills/spec-kit-project-learning/SKILL.md`: rewrite around the two-layer read path and Learning Reflex.
- `scripts/bash/update-agent-context.sh`: add generated AGENTS/CLAUDE Learning Reflex managed-block lines.
- `scripts/powershell/update-agent-context.ps1`: mirror the same managed-block lines.
- `README.md`: update the passive project learning section and helper command descriptions.
- `PROJECT-HANDBOOK.md`: update source-surface guidance for self-learning v2.
- `tests/test_constitution_defaults.py`: cover template materialization.
- `tests/test_learning_cli.py`: cover index/detail ensure, start, capture, auto-capture, and compatibility behavior.
- `tests/test_learning_aggregate.py`: cover aggregate reads from index/detail plus old layers.
- `tests/test_alignment_templates.py`: update learning guidance assertions.
- `tests/test_command_surface_semantics.py`: ensure generated learning command guidance remains executable/clearly labeled and now points to index/detail storage.
- `tests/test_extension_skills.py`: assert generated template assets include the new learning templates and Learning Reflex.
- `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_base_toml.py`, `tests/integrations/test_integration_base_skills.py`, `tests/integrations/test_integration_codex.py`, `tests/integrations/test_integration_claude.py`, `tests/integrations/test_integration_gemini.py`, and `tests/integrations/test_cli.py`: update generated file inventories and rendered guidance expectations.

Do not modify unrelated dirty files unless the current task explicitly requires the file listed above. Preserve any existing user changes by reading before editing and staging only task-owned hunks.

## Data Contracts

Add a new index entry payload that can be serialized in a managed markdown block:

```python
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
```

Use the existing `LearningEntry` as the compatibility-rich detail payload for v1 fields. The index entry should be derived from `LearningEntry` on capture so old callers do not need new required options.

Recommended id/detail derivation:

```python
def learning_index_id(recurrence_key: str, first_seen: str) -> str:
    date_part = first_seen[:10]
    return f"learn-{date_part}-{_slugify(recurrence_key)[:72]}"

def detail_filename(entry_id: str) -> str:
    return f"{entry_id}.md"
```

The detail document should include a managed JSON block with the full `LearningEntry` payload and a human-readable summary. Reuse `MACHINE_BEGIN` / `MACHINE_END` for consistency.

---

### Task 1: Add Learning Index Templates And Packaging

**Files:**
- Create: `templates/project-learnings-index-template.md`
- Create: `templates/project-learning-detail-template.md`
- Modify: `pyproject.toml`
- Test: `tests/test_constitution_defaults.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_toml.py`
- Test: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Write failing tests for template materialization and inventory**

In `tests/test_constitution_defaults.py`, update `_seed_learning_templates()` so it copies the new templates:

```python
for name in (
    "project-rules-template.md",
    "project-learnings-template.md",
    "project-learnings-index-template.md",
    "project-learning-detail-template.md",
):
```

In `test_ensure_learning_memory_from_templates_materializes_defaults`, add:

```python
index_path = project_path / ".specify" / "memory" / "learnings" / "INDEX.md"

assert index_path.exists()
index_content = index_path.read_text(encoding="utf-8")
assert "Project Learning Index" in index_content
assert "detail" in index_content
assert "trigger_signals" in index_content
```

In `tests/test_extension_skills.py`, near the existing project learning template assertions, add:

```python
assert (project_dir / ".specify" / "templates" / "project-learnings-index-template.md").exists()
assert (project_dir / ".specify" / "templates" / "project-learning-detail-template.md").exists()
```

In each integration inventory test that currently lists `.specify/memory/project-learnings.md`, add:

```python
".specify/memory/learnings/INDEX.md",
".specify/templates/project-learnings-index-template.md",
".specify/templates/project-learning-detail-template.md",
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_constitution_defaults.py::test_ensure_learning_memory_from_templates_materializes_defaults tests/test_extension_skills.py -q
```

Expected: FAIL because the new template files and materialized index do not exist.

- [ ] **Step 3: Create the index template**

Create `templates/project-learnings-index-template.md`:

```markdown
# Project Learning Index

Thin first-read index of reusable engineering lessons for later `sp-xxx` workflows.

Read this file after `.specify/memory/project-rules.md` and before command-local
context. Open only the linked detail documents whose `applies_to` or
`trigger_signals` match the current work.

---

<!-- SPECKIT_LEARNING_DATA_BEGIN -->
[]
<!-- SPECKIT_LEARNING_DATA_END -->

## Managed Entries

_No learning index entries recorded yet._
```

- [ ] **Step 4: Create the detail template**

Create `templates/project-learning-detail-template.md`:

```markdown
# Project Learning Detail

Reusable engineering lesson detail. One lesson per file.

---

<!-- SPECKIT_LEARNING_DATA_BEGIN -->
[]
<!-- SPECKIT_LEARNING_DATA_END -->

## Problem

_No problem recorded yet._

## Lesson

_No lesson recorded yet._

## When To Apply

_No applicability notes recorded yet._

## Trigger Signals

_No trigger signals recorded yet._

## Evidence

_No evidence recorded yet._

## Prevention Or Recovery

_No prevention or recovery notes recorded yet._

## Exceptions

_No exceptions recorded yet._
```

- [ ] **Step 5: Include templates in the wheel**

In `pyproject.toml`, add these force-includes near the existing project learning templates:

```toml
"templates/project-learnings-index-template.md" = "specify_cli/core_pack/templates/project-learnings-index-template.md"
"templates/project-learning-detail-template.md" = "specify_cli/core_pack/templates/project-learning-detail-template.md"
```

- [ ] **Step 6: Run focused template tests**

Run:

```powershell
pytest tests/test_constitution_defaults.py::test_ensure_learning_memory_from_templates_materializes_defaults tests/test_extension_skills.py -q
```

Expected: tests still fail until Task 2 wires `ensure_learning_memory_from_templates()`.

- [ ] **Step 7: Commit template assets after Task 2 passes**

Do not commit yet if Task 2 has not passed. When Task 2 completes, include these files in that commit:

```powershell
git add templates/project-learnings-index-template.md templates/project-learning-detail-template.md pyproject.toml tests/test_constitution_defaults.py tests/test_extension_skills.py tests/integrations
git commit -m "feat: add learning index templates"
```

---

### Task 2: Extend Learning Paths And Ensure Logic

**Files:**
- Modify: `src/specify_cli/learnings.py`
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/test_constitution_defaults.py`
- Test: `tests/test_learning_cli.py`

- [ ] **Step 1: Write failing tests for ensure/status path payload**

In `tests/test_learning_cli.py`, update `_seed_learning_templates()` the same way as Task 1.

Add:

```python
def test_learning_ensure_creates_learning_index(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["learning_index"] is True
    assert payload["paths"]["learning_index"].endswith(".specify/memory/learnings/INDEX.md")
    assert (project / ".specify" / "memory" / "learnings" / "INDEX.md").exists()
```

Update `test_learning_status_reports_missing_runtime_files_without_mutation`:

```python
assert payload["exists"]["learning_index"] is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_ensure_creates_learning_index tests/test_learning_cli.py::test_learning_status_reports_missing_runtime_files_without_mutation -q
```

Expected: FAIL because `learning_index` is not in `paths` or `exists`.

- [ ] **Step 3: Extend `LearningPaths`**

In `src/specify_cli/learnings.py`, add `learning_index` and `learning_detail_template`:

```python
@dataclass(frozen=True)
class LearningPaths:
    constitution: Path
    project_rules: Path
    project_learnings: Path
    learning_index: Path
    learning_detail_template: Path
    candidates: Path
    review: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "constitution": str(self.constitution),
            "project_rules": str(self.project_rules),
            "project_learnings": str(self.project_learnings),
            "learning_index": str(self.learning_index),
            "learning_detail_template": str(self.learning_detail_template),
            "candidates": str(self.candidates),
            "review": str(self.review),
        }
```

Update `build_learning_paths()`:

```python
memory_dir = project_root / ".specify" / "memory"
learning_memory_dir = memory_dir / "learnings"
learning_dir = project_root / ".planning" / "learnings"
return LearningPaths(
    constitution=memory_dir / "constitution.md",
    project_rules=memory_dir / "project-rules.md",
    project_learnings=memory_dir / "project-learnings.md",
    learning_index=learning_memory_dir / "INDEX.md",
    learning_detail_template=project_root / ".specify" / "templates" / "project-learning-detail-template.md",
    candidates=learning_dir / "candidates.md",
    review=learning_dir / "review.md",
)
```

- [ ] **Step 4: Add fallback template text**

Near `LEARNINGS_TEMPLATE_TEXT`, add:

```python
LEARNING_INDEX_TEMPLATE_TEXT = (
    "# Project Learning Index\n\n"
    "Thin first-read index of reusable engineering lessons for later `sp-xxx` workflows.\n\n"
    "Read this file after `.specify/memory/project-rules.md` and before command-local\n"
    "context. Open only the linked detail documents whose `applies_to` or\n"
    "`trigger_signals` match the current work.\n\n"
    "---\n\n"
    f"{MACHINE_BEGIN}\n[]\n{MACHINE_END}\n\n"
    "## Managed Entries\n\n"
    "_No learning index entries recorded yet._\n"
)
```

- [ ] **Step 5: Materialize the index**

In `ensure_learning_memory_from_templates()`, after project learnings, add:

```python
if _seed_from_template(
    paths.learning_index,
    templates_root / "project-learnings-index-template.md",
    LEARNING_INDEX_TEMPLATE_TEXT,
):
    created.append("learnings/INDEX.md")
```

Keep `project-learnings.md` creation unchanged.

- [ ] **Step 6: Report index state**

In `learning_status_payload()`, add:

```python
"learning_index": paths.learning_index.exists(),
```

to the `exists` map. Ensure `paths.to_dict()` now includes the new paths.

In `src/specify_cli/__init__.py`, update `learning_ensure_command()` and `learning_status_command()` row lists with:

```python
("Learning Index", f"[dim]{payload['paths']['learning_index']}[/dim]")
```

and:

```python
("Learning Index", "present" if payload["exists"]["learning_index"] else "missing")
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
pytest tests/test_constitution_defaults.py::test_ensure_learning_memory_from_templates_materializes_defaults tests/test_learning_cli.py::test_learning_ensure_creates_learning_index tests/test_learning_cli.py::test_learning_status_reports_missing_runtime_files_without_mutation -q
```

Expected: PASS.

- [ ] **Step 8: Commit ensure/path changes**

```powershell
git add src/specify_cli/learnings.py src/specify_cli/__init__.py templates/project-learnings-index-template.md templates/project-learning-detail-template.md pyproject.toml tests/test_constitution_defaults.py tests/test_learning_cli.py tests/test_extension_skills.py tests/integrations
git commit -m "feat: materialize learning index memory"
```

---

### Task 3: Add Index Entry Read/Write Helpers

**Files:**
- Modify: `src/specify_cli/learnings.py`
- Test: `tests/test_learning_cli.py`

- [ ] **Step 1: Write failing tests for capture index/detail writes**

Add to `tests/test_learning_cli.py`:

```python
def test_learning_capture_writes_index_and_detail_doc(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "tooling_trap",
            "--summary",
            "Run generated helper commands from the project launcher",
            "--evidence",
            "A stale global specify executable produced helper behavior that differed from the generated project launcher.",
            "--recurrence-key",
            "cli.project-launcher-helper-drift",
            "--signal",
            "high",
            "--false-start",
            "Retried the global CLI before checking .specify/config.json",
            "--decisive-signal",
            "The rendered {{specify-subcmd}} path differed from PATH specify",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    index_entry = payload["index_entry"]
    assert index_entry["recurrence_key"] == "cli.project-launcher-helper-drift"
    assert index_entry["problem"] == "Run generated helper commands from the project launcher"
    assert "sp-implement" in index_entry["applies_to"]
    assert index_entry["detail"].startswith("./learn-")

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_content = index_path.read_text(encoding="utf-8")
    assert "cli.project-launcher-helper-drift" in index_content
    assert index_entry["detail"] in index_content

    detail_path = index_path.parent / index_entry["detail"].removeprefix("./")
    detail_content = detail_path.read_text(encoding="utf-8")
    assert "Run generated helper commands from the project launcher" in detail_content
    assert "A stale global specify executable" in detail_content
    assert "Retried the global CLI" in detail_content
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_capture_writes_index_and_detail_doc -q
```

Expected: FAIL because capture payload has no `index_entry` and no detail doc.

- [ ] **Step 3: Add `LearningIndexEntry` dataclass**

In `src/specify_cli/learnings.py`, after `LearningEntry`, add:

```python
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
        return cls(
            id=str(payload["id"]),
            problem=str(payload["problem"]),
            lesson=str(payload["lesson"]),
            learning_type=normalize_learning_type(str(payload["learning_type"])),
            source_command=normalize_command_name(str(payload["source_command"])),
            recurrence_key=str(payload["recurrence_key"]),
            applies_to=[normalize_command_name(item) for item in _coerce_str_list(payload.get("applies_to"))],
            trigger_signals=_coerce_str_list(payload.get("trigger_signals")),
            detail=str(payload["detail"]),
            first_seen=str(payload["first_seen"]),
            last_seen=str(payload["last_seen"]),
            occurrence_count=int(payload.get("occurrence_count", 1)),
            signal_strength=normalize_signal_strength(str(payload.get("signal_strength") or "medium")),
        )
```

- [ ] **Step 4: Add index rendering helpers**

Add helper functions near `_render_learning_file()`:

```python
def _learning_index_id(recurrence_key: str, first_seen: str) -> str:
    return f"learn-{first_seen[:10]}-{_slugify(recurrence_key)[:72]}"

def _detail_ref_for_index_id(index_id: str) -> str:
    return f"./{index_id}.md"

def _trigger_signals_from_entry(entry: LearningEntry) -> list[str]:
    signals = [entry.learning_type, entry.signal_strength]
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
        problem=entry.summary,
        lesson=entry.evidence.splitlines()[0] if entry.evidence.strip() else entry.summary,
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
```

Add `_render_index_entry_summary()`:

```python
def _render_index_entry_summary(entry: LearningIndexEntry) -> str:
    applies = ", ".join(entry.applies_to)
    signals = ", ".join(entry.trigger_signals)
    return (
        f"### {entry.id} - {entry.problem}\n\n"
        f"- Type: `{entry.learning_type}`\n"
        f"- Source Command: `{entry.source_command}`\n"
        f"- Recurrence Key: `{entry.recurrence_key}`\n"
        f"- Applies To: {applies}\n"
        f"- Trigger Signals: {signals}\n"
        f"- Signal: `{entry.signal_strength}`\n"
        f"- Occurrence Count: {entry.occurrence_count}\n"
        f"- First Seen: `{entry.first_seen}`\n"
        f"- Last Seen: `{entry.last_seen}`\n"
        f"- Detail: `{entry.detail}`\n\n"
        f"#### Lesson\n\n{entry.lesson}\n"
    )
```

Add generic index read/write helpers:

```python
def _read_index_entries(path: Path) -> tuple[str, list[LearningIndexEntry]]:
    if not path.exists():
        return "", []
    preamble, payloads = _extract_payload_block(path.read_text(encoding="utf-8"))
    return preamble, [LearningIndexEntry.from_payload(payload) for payload in payloads]

def _render_learning_index_file(preamble: str, entries: list[LearningIndexEntry]) -> str:
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
        sections.append("\n\n---\n\n".join(_render_index_entry_summary(entry) for entry in entries))
    sections.append("")
    return "\n".join(sections)

def _write_index_entries(path: Path, preamble: str, entries: list[LearningIndexEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_learning_index_file(preamble, entries), encoding="utf-8")
```

- [ ] **Step 5: Add index merge and detail write**

Add:

```python
def _merge_index_entry(existing: LearningIndexEntry, new_entry: LearningIndexEntry) -> LearningIndexEntry:
    return LearningIndexEntry(
        id=existing.id,
        problem=new_entry.problem or existing.problem,
        lesson=new_entry.lesson or existing.lesson,
        learning_type=existing.learning_type,
        source_command=new_entry.source_command or existing.source_command,
        recurrence_key=existing.recurrence_key,
        applies_to=sorted(dict.fromkeys([*existing.applies_to, *new_entry.applies_to])),
        trigger_signals=sorted(dict.fromkeys([*existing.trigger_signals, *new_entry.trigger_signals])),
        detail=existing.detail,
        first_seen=existing.first_seen,
        last_seen=new_entry.last_seen,
        occurrence_count=existing.occurrence_count + 1,
        signal_strength="high" if "high" in {existing.signal_strength, new_entry.signal_strength} else "medium" if "medium" in {existing.signal_strength, new_entry.signal_strength} else "low",
    )

def _upsert_index_entry(entries: list[LearningIndexEntry], new_entry: LearningIndexEntry) -> tuple[list[LearningIndexEntry], LearningIndexEntry]:
    updated = list(entries)
    for index, existing in enumerate(updated):
        if existing.recurrence_key == new_entry.recurrence_key:
            merged = _merge_index_entry(existing, new_entry)
            updated[index] = merged
            return updated, merged
    updated.append(new_entry)
    return updated, new_entry
```

Add detail rendering:

```python
def _render_learning_detail(entry: LearningEntry, index_entry: LearningIndexEntry) -> str:
    payload = [entry.to_payload()]
    false_starts = "\n".join(f"- {item}" for item in entry.false_starts) or "_No false starts recorded._"
    rejected_paths = "\n".join(f"- {item}" for item in entry.rejected_paths) or "_No rejected paths recorded._"
    triggers = "\n".join(f"- {item}" for item in index_entry.trigger_signals) or "_No trigger signals recorded._"
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
            "## Exceptions",
            "",
            "_No exceptions recorded yet._",
            "",
        ]
    )

def _write_learning_detail(paths: LearningPaths, entry: LearningEntry, index_entry: LearningIndexEntry) -> Path:
    detail_name = index_entry.detail.removeprefix("./")
    detail_path = paths.learning_index.parent / detail_name
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    detail_path.write_text(_render_learning_detail(entry, index_entry), encoding="utf-8")
    return detail_path
```

- [ ] **Step 6: Wire capture to index/detail**

In `capture_learning()`, after `stored` is determined in both confirm and candidate branches, call:

```python
index_preamble, index_entries = _read_index_entries(paths.learning_index)
new_index_entry = _index_entry_from_learning(stored)
index_entries, stored_index = _upsert_index_entry(index_entries, new_index_entry)
_write_index_entries(paths.learning_index, index_preamble or LEARNING_INDEX_TEMPLATE_TEXT.rstrip(), index_entries)
detail_path = _write_learning_detail(paths, stored, stored_index)
```

Add to the returned payload:

```python
"index_entry": stored_index.to_payload(),
"detail_path": str(detail_path),
```

Keep old candidate/project-learning writes for compatibility.

- [ ] **Step 7: Run focused capture tests**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_capture_writes_index_and_detail_doc tests/test_learning_cli.py::test_learning_capture_merges_by_recurrence_key_and_increments_count -q
```

Expected: PASS.

- [ ] **Step 8: Commit index/detail capture**

```powershell
git add src/specify_cli/learnings.py tests/test_learning_cli.py
git commit -m "feat: write learning index and detail docs"
```

---

### Task 4: Update Learning Start To Return Relevant Index Entries

**Files:**
- Modify: `src/specify_cli/learnings.py`
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/test_learning_cli.py`

- [ ] **Step 1: Write failing test for start relevance**

Add:

```python
def test_learning_start_returns_relevant_index_entries_and_detail_refs(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "recovery_path",
            "--summary",
            "Re-run the focused repro before widening debug scope",
            "--evidence",
            "The failing behavior disappeared only after the minimal repro was restored.",
            "--recurrence-key",
            "debug.focused-repro-before-scope-widening",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["learning", "start", "--command", "debug", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [entry["recurrence_key"] for entry in payload["relevant_index_entries"]] == [
        "debug.focused-repro-before-scope-widening"
    ]
    assert payload["recommended_detail_docs"][0].endswith(".specify/memory/learnings/learn-")
    assert payload["summary_counts"]["relevant_index_entries"] == 1
```

Use `assert "debug.focused-repro-before-scope-widening" in payload["recommended_detail_docs"][0]` if the exact `learn-` prefix makes the assertion too brittle.

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_start_returns_relevant_index_entries_and_detail_refs -q
```

Expected: FAIL because payload lacks `relevant_index_entries`.

- [ ] **Step 3: Add relevance helper for index entries**

In `src/specify_cli/learnings.py`, add:

```python
def is_index_relevant_to_command(entry: LearningIndexEntry, command_name: str) -> bool:
    return normalize_command_name(command_name) in entry.applies_to
```

- [ ] **Step 4: Read index entries in `start_learning_session()`**

After reading candidates:

```python
index_preamble, index_entries = _read_index_entries(paths.learning_index)
```

Use `_ = index_preamble` only if lint complains about unused variables.

Compute:

```python
relevant_index_entries = [
    entry.to_payload()
    for entry in index_entries
    if is_index_relevant_to_command(entry, normalized_command)
]
recommended_detail_docs = [
    str((paths.learning_index.parent / entry.detail.removeprefix("./")).resolve())
    for entry in index_entries
    if is_index_relevant_to_command(entry, normalized_command)
]
```

Add both to return payload and update `summary_counts`.

- [ ] **Step 5: Update CLI text rows**

In `learning_start_command()`, add:

```python
("Relevant Index Entries", str(len(payload["relevant_index_entries"]))),
("Recommended Details", str(len(payload["recommended_detail_docs"]))),
```

- [ ] **Step 6: Run focused start tests**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_start_returns_relevant_index_entries_and_detail_refs tests/test_learning_cli.py::test_learning_start_filters_relevant_candidates_by_command -q
```

Expected: PASS.

- [ ] **Step 7: Commit start payload changes**

```powershell
git add src/specify_cli/learnings.py src/specify_cli/__init__.py tests/test_learning_cli.py
git commit -m "feat: surface learning index at workflow start"
```

---

### Task 5: Update Auto-Capture To Write Index/Detail And Broaden Friction Signals

**Files:**
- Modify: `src/specify_cli/learnings.py`
- Test: `tests/test_learning_cli.py`

- [ ] **Step 1: Write failing test for auto-capture index/detail output**

Update `test_learning_capture_auto_implement_writes_candidates_from_tracker_state` or add a new test:

```python
def test_learning_capture_auto_implement_writes_index_details(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T004"],
        completed_checks=["pytest tests/test_demo.py -q"],
    )

    result = _invoke_in_project(
        project,
        ["learning", "capture-auto", "--command", "implement", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "captured"
    captured = payload["captured"][0]
    assert "index_entry" in captured
    detail_path = Path(captured["detail_path"])
    assert detail_path.exists()
    assert "Observed auto-capture evidence" in detail_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_capture_auto_implement_writes_index_details -q
```

Expected: FAIL because `captured` currently contains only `payload["entry"]`.

- [ ] **Step 3: Return full capture payloads from auto-capture**

In `capture_auto_learning()`, change:

```python
captured.append(payload["entry"])
```

to:

```python
captured.append(payload)
```

Update registry recurrence keys:

```python
"recurrence_keys": [item["entry"]["recurrence_key"] for item in captured],
```

Keep existing callers compatible by adding `captured_entries` if useful:

```python
"captured_entries": [item["entry"] for item in captured],
```

- [ ] **Step 4: Broaden workflow-state friction auto-capture**

In `_suggest_workflow_state_auto_capture()`, after existing suggestions, add:

```python
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
        )
    )
```

- [ ] **Step 5: Add focused blocked-state test**

Add:

```python
def test_learning_capture_auto_workflow_state_records_blocked_reason(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "002-demo"
    _write_workflow_state(
        feature_dir,
        next_command="",
        status="blocked",
        blocked_reason="Generated command guidance omitted the runtime helper argument required by the CLI.",
    )

    result = _invoke_in_project(
        project,
        ["learning", "capture-auto", "--command", "plan", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "captured"
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
    assert "sp-plan.workflow-state-preserves-blocked-reason" in keys
```

- [ ] **Step 6: Run focused auto-capture tests**

Run:

```powershell
pytest tests/test_learning_cli.py::test_learning_capture_auto_implement_writes_index_details tests/test_learning_cli.py::test_learning_capture_auto_workflow_state_records_blocked_reason tests/test_learning_cli.py::test_learning_capture_auto_skips_duplicate_snapshot -q
```

Expected: PASS.

- [ ] **Step 7: Commit auto-capture changes**

```powershell
git add src/specify_cli/learnings.py tests/test_learning_cli.py
git commit -m "feat: auto-capture learning details"
```

---

### Task 6: Update Aggregate And Compatibility Reads

**Files:**
- Modify: `src/specify_cli/learning_aggregate.py`
- Modify: `src/specify_cli/learnings.py`
- Test: `tests/test_learning_aggregate.py`
- Test: `tests/test_learning_cli.py`

- [ ] **Step 1: Write failing aggregate test**

In `tests/test_learning_aggregate.py`, add:

```python
def test_aggregate_learning_state_reads_index_entries(tmp_path: Path) -> None:
    project = tmp_path
    _seed_learning_templates(project)
    capture_learning(
        project,
        command_name="implement",
        learning_type="tooling_trap",
        summary="Use the project launcher for generated helper commands",
        evidence="The generated launcher selected a different specify executable than PATH.",
        recurrence_key="cli.project-launcher-helper-drift",
        signal_strength="high",
    )

    report = aggregate_learning_state(project)

    patterns = report["patterns"]
    keys = [item["recurrence_key"] for item in patterns]
    assert "cli.project-launcher-helper-drift" in keys
    matched = next(item for item in patterns if item["recurrence_key"] == "cli.project-launcher-helper-drift")
    assert "learning_index" in matched["layers"]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_learning_aggregate.py::test_aggregate_learning_state_reads_index_entries -q
```

Expected: FAIL because aggregate ignores the index.

- [ ] **Step 3: Export read helper**

In `src/specify_cli/learnings.py`, add:

```python
def read_learning_index_entries(path: Path) -> tuple[str, list[LearningIndexEntry]]:
    return _read_index_entries(path)
```

- [ ] **Step 4: Include index layer in aggregate**

In `src/specify_cli/learning_aggregate.py`, import `read_learning_index_entries`.

In `aggregate_learning_state()`, read:

```python
_index_preamble, index_entries = read_learning_index_entries(paths.learning_index) if paths.learning_index.exists() else ("", [])
```

When converting to aggregate input, map `LearningIndexEntry` to the existing aggregate shape:

```python
index_as_learning_entries = [
    LearningEntry(
        id=entry.id,
        summary=entry.problem,
        learning_type=entry.learning_type,
        source_command=entry.source_command,
        evidence=entry.lesson,
        recurrence_key=entry.recurrence_key,
        default_scope=default_scope_for_type(entry.learning_type),
        applies_to=entry.applies_to,
        signal_strength=entry.signal_strength,
        status="candidate",
        first_seen=entry.first_seen,
        last_seen=entry.last_seen,
        occurrence_count=entry.occurrence_count,
    )
    for entry in index_entries
]
```

Add them with layer label `learning_index`.

- [ ] **Step 5: Run aggregate tests**

Run:

```powershell
pytest tests/test_learning_aggregate.py tests/test_learning_cli.py::test_learning_start_auto_promotes_repeated_medium_signal_candidates -q
```

Expected: PASS and old candidate promotion behavior remains compatible.

- [ ] **Step 6: Commit aggregate changes**

```powershell
git add src/specify_cli/learnings.py src/specify_cli/learning_aggregate.py tests/test_learning_aggregate.py tests/test_learning_cli.py
git commit -m "feat: aggregate learning index entries"
```

---

### Task 7: Rewrite Shared Learning Guidance And Passive Skill

**Files:**
- Modify: `templates/command-partials/common/learning-layer.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Modify: `templates/project-learnings-template.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_passive_skill_guidance.py`
- Test: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Write failing guidance assertions**

In `tests/test_alignment_templates.py`, update the passive learning assertions to require:

```python
assert ".specify/memory/learnings/INDEX.md" in block
assert "Learning Reflex" in block
assert "detail document" in block.lower()
```

In `tests/test_passive_skill_guidance.py`, update `test_project_learning_focuses_on_memory_triggers_storage_and_promotion()`:

```python
assert ".specify/memory/learnings/INDEX.md" in content
assert "Learning Reflex" in content
assert "one detailed markdown document per lesson" in content
assert "candidate/confirmed" not in content.lower()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_core_sp_templates_use_learning_review_hooks tests/test_passive_skill_guidance.py::test_project_learning_focuses_on_memory_triggers_storage_and_promotion -q
```

Expected: FAIL because templates still describe candidates as primary.

- [ ] **Step 3: Update common learning partial**

Replace `templates/command-partials/common/learning-layer.md` with:

```markdown
## Passive Project Learning Layer

Learning capture is proportional to command complexity:

| Tier | Learning Behavior |
|------|-------------------|
| trivial | Skip learning unless the task escalates or exposes reusable project memory. |
| light | Read the learning index and auto-capture from durable state on resolution when useful. |
| heavy | Full learning: start -> read index -> signal friction -> closeout capture into index/detail. |

### Learning Reflex

Before final closeout, ask whether a future senior engineer would benefit from
seeing this lesson before related work. If yes, update the learning index and
detail document. Do not ask the user for routine permission to record low-risk
project memory. Do not bury reusable lessons only in chat, task files, or
workflow-state.

### Tier: trivial
- Do not run `{{specify-subcmd:learning start}}` unless the task escalates.
- Do not invoke learning hooks for ordinary one-off edits.

### Tier: light
- Run `{{specify-subcmd:learning start}}` with the current command name when available.
- Read `.specify/memory/project-rules.md` and `.specify/memory/learnings/INDEX.md` before local context.
- Open only detail docs linked from relevant index entries.
- On resolution, prefer `{{specify-subcmd:learning capture-auto}}` when durable state contains reusable friction.

### Tier: heavy
- Run `{{specify-subcmd:learning start}}` with the current command name so shared memory and relevant detail refs are visible.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader command-local context.
- Open only linked detail docs whose `applies_to` or `trigger_signals` match the current work.
- When friction appears, signal it through `{{specify-subcmd:hook signal-learning}}` with relevant counts.
- Before final completion or blocked reporting, perform learning closeout: capture or merge an index/detail lesson when future reuse is plausible, or explicitly decide the run was one-off.
- Prefer `{{specify-subcmd:learning capture-auto}}` when durable state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Use manual `capture-learning` only when durable state does not capture the lesson cleanly.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
- Promote to `project-rules.md` or constitution only after recurrence, explicit user confirmation, or stable cross-workflow governance value.
```

- [ ] **Step 4: Rewrite passive skill**

Edit `templates/passive-skills/spec-kit-project-learning/SKILL.md` to preserve the frontmatter and replace the body with sections:

```markdown
# Spec Kit Project Learning

This skill is about preserving reusable engineering judgment in project memory.

## Core Principle

Do not keep reusable operational knowledge in transient chat memory.

## Learning Reflex

Before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update the learning index and detail document.

## Memory Layers

1. `.specify/memory/constitution.md`
2. `.specify/memory/project-rules.md`
3. `.specify/memory/learnings/INDEX.md`
4. `.specify/memory/learnings/learn-2026-05-11-cli-helper-drift.md`

## What To Record

Record a lesson when a task exposes repeated attempts, hidden constraints, user corrections, route mistakes, missing validation, state gaps, tooling traps, false leads, or any "next time check this first" insight.

## What To Skip

Skip one-off typos, transient network/cache issues with no project-specific recovery, and feature-only business choices with no reusable engineering value.

## Command Surface

- `{{specify-subcmd:learning start --command implement --format json}}`
- `{{specify-subcmd:learning capture}}`
  - Required options: `--command`, `--type`, `--summary`, `--evidence`
- `{{specify-subcmd:learning capture-auto --command implement --feature-dir "$FEATURE_DIR" --format json}}`
- `{{specify-subcmd:learning promote --recurrence-key cli.project-launcher-helper-drift --target learning}}`

## Promotion

Normal capture writes index/detail memory. Promotion is only for stable rules or constitution-level governance.
```

Keep existing first-party hook descriptions if tests require them, but make index/detail storage the primary model and avoid saying candidate/confirmed is the main everyday flow.

- [ ] **Step 5: Update compatibility template wording**

In `templates/project-learnings-template.md`, change the opening paragraph to:

```markdown
Compatibility summary of confirmed project learnings that are reusable across
later `sp-xxx` workflows. New learning capture should use
`.specify/memory/learnings/INDEX.md` plus one detail markdown document per
lesson. Keep stable defaults in `project-rules.md`.
```

- [ ] **Step 6: Run guidance tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_command_surface_semantics.py -q
```

Expected: PASS after updating assertions that intentionally referenced candidates as primary.

- [ ] **Step 7: Commit guidance changes**

```powershell
git add templates/command-partials/common/learning-layer.md templates/passive-skills/spec-kit-project-learning/SKILL.md templates/project-learnings-template.md tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_command_surface_semantics.py
git commit -m "docs: shift learning guidance to index detail model"
```

---

### Task 8: Propagate Learning Reflex To Commands And Generated Context

**Files:**
- Modify: `templates/commands/*.md` listed in File Structure
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_command_surface_semantics.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Write failing generated context tests**

In `tests/test_command_surface_semantics.py`, update managed block assertions:

```python
assert "Learning Reflex" in bash
assert ".specify/memory/learnings/INDEX.md" in bash
assert "future senior engineer" in bash
assert "Learning Reflex" in powershell
assert ".specify/memory/learnings/INDEX.md" in powershell
```

In `tests/test_alignment_templates.py`, add a loop:

```python
def test_non_trivial_workflow_templates_use_learning_index_reflex():
    commands = [
        "specify", "clarify", "constitution", "deep-research", "plan", "tasks",
        "analyze", "checklist", "implement", "debug", "quick", "test-scan",
        "test-build", "map-scan", "map-build",
    ]
    for command in commands:
        content = _read(f"templates/commands/{command}.md")
        assert ".specify/memory/learnings/INDEX.md" in content
        assert "Learning Reflex" in content or "future senior engineer" in content
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_non_trivial_workflow_templates_use_learning_index_reflex tests/test_command_surface_semantics.py -q
```

Expected: FAIL until templates/scripts are updated.

- [ ] **Step 3: Update managed context renderers**

In `scripts/bash/update-agent-context.sh`, in the managed learning block, add lines:

```bash
'- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work.'
'- If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.'
'- Do not bury reusable lessons only in chat, task files, or workflow-state.'
```

In `scripts/powershell/update-agent-context.ps1`, add the equivalent strings to the managed block array.

- [ ] **Step 4: Update command templates**

For each listed command template, replace mentions that make `.planning/learnings/candidates.md` the primary read layer with:

```markdown
- [AGENT] Run `{{specify-subcmd:learning start --command plan --format json}}` when available so passive learning files exist, the current run sees relevant shared project memory, and relevant detail docs can be opened selectively.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader command-local context.
- Open only learning detail docs linked from index entries whose `applies_to` or `trigger_signals` match this work.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, capture or merge an index/detail learning.
```

Keep command-specific `signal-learning`, `review-learning`, and `capture-auto` shapes, but update any prose that says candidates are the primary learning layer.

- [ ] **Step 5: Run guidance tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit propagation changes**

```powershell
git add templates/commands scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/integrations/test_cli.py
git commit -m "docs: add learning reflex to generated workflows"
```

---

### Task 9: Update Integration Rendering Expectations

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_gemini.py`
- Modify: `src/specify_cli/integrations/base.py` only if shared rendering needs a supplemental Learning Reflex append

- [ ] **Step 1: Add integration assertions**

In generated integration tests that already assert `.specify/memory/project-rules.md`, add:

```python
assert ".specify/memory/learnings/INDEX.md" in content
assert "Learning Reflex" in content or "future senior engineer" in content
```

For Codex generated skills, add:

```python
assert ".specify/memory/learnings/INDEX.md" in content
assert "future senior engineer" in content
assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
```

Do not require every generated file to omit candidates; compatibility mentions are allowed.

- [ ] **Step 2: Run integration tests and verify failures**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py -q
```

Expected: FAIL where rendered content lacks the new wording.

- [ ] **Step 3: Prefer template fixes over renderer hacks**

If failures are from command templates, fix the template. Only modify `src/specify_cli/integrations/base.py` if a shared appended section is the established pattern for that integration surface.

If adding a shared append is necessary, add a helper:

```python
def _append_learning_reflex(self, *, content: str) -> str:
    if "Learning Reflex" in content and ".specify/memory/learnings/INDEX.md" in content:
        return content
    return content.rstrip() + "\n\n## Learning Reflex\n\nBefore final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document.\n"
```

Call it from shared setup after `process_template()`.

- [ ] **Step 4: Run integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit integration expectations**

```powershell
git add src/specify_cli/integrations/base.py tests/integrations
git commit -m "test: assert learning reflex in generated integrations"
```

---

### Task 10: Update Docs And Runtime Diagnostics

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `src/specify_cli/launcher.py`
- Test: `tests/test_command_surface_semantics.py`
- Test: `tests/test_launcher.py`

- [ ] **Step 1: Update README assertions**

In `tests/test_command_surface_semantics.py`, update README learning assertions:

```python
assert ".specify/memory/learnings/INDEX.md" in readme
assert "one detail markdown document per lesson" in readme.lower()
assert "Learning Reflex" in readme
```

- [ ] **Step 2: Add launcher diagnostic test**

In `tests/test_launcher.py`, add a diagnostic test:

```python
def test_runtime_diagnostics_warn_when_learning_index_missing(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning").mkdir(parents=True)
    (project / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning" / "SKILL.md").write_text(
        "Learning Reflex\n.specify/memory/learnings/INDEX.md\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(project)

    codes = [issue["code"] for issue in issues]
    assert "missing-learning-index" in codes
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
pytest tests/test_command_surface_semantics.py tests/test_launcher.py::test_runtime_diagnostics_warn_when_learning_index_missing -q
```

Expected: FAIL until README and diagnostics update.

- [ ] **Step 4: Update docs**

In `README.md`, revise the passive learning section to say:

```markdown
- Generated projects include `.specify/memory/learnings/INDEX.md` as the thin first-read learning layer.
- Each reusable lesson may link to one detail markdown document under `.specify/memory/learnings/`.
- `project-learnings.md` remains a compatibility summary; new captures write index/detail memory first.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work.
```

In `PROJECT-HANDBOOK.md`, update the learning helper surface description similarly.

- [ ] **Step 5: Add launcher diagnostic**

In `src/specify_cli/launcher.py`, inside `diagnose_project_runtime_compatibility()`, add:

```python
learning_index = project_root / ".specify" / "memory" / "learnings" / "INDEX.md"
if (project_root / ".specify").exists() and not learning_index.exists():
    issues.append(
        {
            "code": "missing-learning-index",
            "summary": "Generated project memory is missing the self-learning v2 index.",
            "repair": "Run `specify learning ensure` or refresh generated assets with `specify integration repair`.",
        }
    )
```

- [ ] **Step 6: Run docs/diagnostics tests**

Run:

```powershell
pytest tests/test_command_surface_semantics.py tests/test_launcher.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit docs/diagnostics**

```powershell
git add README.md PROJECT-HANDBOOK.md src/specify_cli/launcher.py tests/test_command_surface_semantics.py tests/test_launcher.py
git commit -m "docs: document self-learning v2 memory"
```

---

### Task 11: Full Verification And Cleanup

**Files:**
- Review all files modified in previous tasks.

- [ ] **Step 1: Run focused learning suite**

Run:

```powershell
pytest tests/test_learning_cli.py tests/test_learning_aggregate.py tests/test_constitution_defaults.py -q
```

Expected: PASS.

- [ ] **Step 2: Run template and command-surface suite**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_passive_skill_guidance.py tests/test_extension_skills.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration rendering suite**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Run style/checks**

Run:

```powershell
python -m compileall src
git diff --check
```

Expected: compile succeeds and `git diff --check` prints no whitespace errors.

- [ ] **Step 5: Review final diff**

Run:

```powershell
git status --short
git diff --stat HEAD
```

Expected: only intentional self-learning v2 implementation changes remain.

- [ ] **Step 6: Final commit if any verification-only fixes were needed**

If Step 4 or Step 5 required fixes after previous commits:

```powershell
git add src/specify_cli/learnings.py tests/test_learning_cli.py
git commit -m "fix: stabilize self-learning v2 verification"
```

Otherwise no commit is needed.

## Self-Review Notes

- Spec coverage: tasks cover templates, packaging, CLI ensure/start/capture/capture-auto, aggregate compatibility, generated command guidance, generated context files, docs, diagnostics, and tests.
- Placeholder scan: no step uses TBD/TODO/fill-in language; code snippets and commands are concrete.
- Type consistency: `LearningIndexEntry`, `learning_index`, `recommended_detail_docs`, `index_entry`, and `detail_path` are introduced before later tasks depend on them.
- Scope check: the plan is one cohesive subsystem. Runtime hardening beyond existing closeout helpers is intentionally limited to learning auto-capture and diagnostics in this implementation pass.
