# sp-* Workflow Compact Quality Standard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operationalize the approved compact quality standard so future `sp-*` workflow changes can be evaluated for quality retention and cost reduction before prompts or artifact contracts are changed.

**Architecture:** Add an active documentation surface under `docs/workflow-quality/`, a reusable evaluation template, a pattern catalog, and a lightweight Python metrics script that inventories prompt/artifact costs. Keep this first implementation artifact-only plus a small local metrics utility; do not rewrite any `sp-*` workflow prompt in this pass.

**Tech Stack:** Markdown documentation, Python 3.11+ standard library, pytest, existing repository template/test conventions.

---

## Preflight Constraints

- Existing uncommitted draft edits to `templates/commands/discussion.md` and `templates/command-partials/discussion/shell.md` are out of scope for this plan. Do not stage, commit, or build on those edits unless the user explicitly approves them.
- This plan implements the standard and measurement scaffolding only. It does not compress `sp-discussion`, `sp-plan`, `sp-tasks`, or any other workflow.
- The design source is `docs/superpowers/specs/2026-06-12-sp-workflow-compact-quality-standard-design.md`.

## File Structure

- Create `docs/workflow-quality/README.md`: active standard entrypoint for humans and agents.
- Create `docs/workflow-quality/reusable-pattern-catalog.md`: reusable prompt behavior patterns extracted from existing `sp-*` workflows.
- Create `docs/workflow-quality/evaluation-record-template.md`: required record for future optimization proposals.
- Create `tools/workflow-quality/measure_workflow_costs.py`: repository-local metrics utility for prompt/artifact cost baselines.
- Create `tests/test_workflow_quality_metrics.py`: pytest coverage for the metrics utility.
- Create `docs/workflow-quality/baseline-current-sp-workflows.md`: first baseline report for current SuperSpec workflow prompt surfaces.
- Modify `PROJECT-HANDBOOK.md`: add a short pointer that `sp-*` prompt optimization must use the compact quality standard before editing workflow prompts.

## Task 1: Add Active Standard Entry Point

**Files:**
- Create: `docs/workflow-quality/README.md`

- [ ] **Step 1: Create the workflow-quality docs directory**

Run:

```powershell
New-Item -ItemType Directory -Force docs\workflow-quality
```

Expected: `docs/workflow-quality` exists.

- [ ] **Step 2: Write the active standard entrypoint**

Create `docs/workflow-quality/README.md` with:

```markdown
# sp-* Workflow Compact Quality Standard

## Objective

Optimize `sp-*` workflow prompts and intermediate artifacts by maximizing cost reduction while preserving at least 98% of baseline quality.

```text
maximize prompt and intermediate-artifact cost reduction
subject to quality retention >= 98%
```

This standard applies before changing any `templates/commands/**`, `templates/command-partials/**`, `templates/passive-skills/**`, generated workflow artifact contract, handoff shape, state file, task packet format, or validation closeout surface.

## Required Principle

Shorter is not automatically better. A change is accepted only when it reduces whole-chain cost without moving ambiguity, evidence gathering, or interpretation burden downstream.

## Required Evaluation Layers

| Layer | Examples | Required Question |
| --- | --- | --- |
| Prompt | command templates, partials, passive skills | Does this text cause a concrete behavior? |
| Handoff | handoff Markdown/JSON, plan contract, task handoff | Can the next workflow consume this quickly and safely? |
| Planning artifacts | spec, alignment, context, plan, tasks, task packets | Did upstream intent become executable and verifiable work? |
| Execution evidence | quick/debug state, worker results, validation closeout | Did completion evidence prove acceptance and preserve residual risk? |

## Quality Score

| Dimension | Points |
| --- | ---: |
| Behavior correctness | 20 |
| Intent preservation | 15 |
| Evidence quality | 15 |
| Handoff consumability | 15 |
| Downstream executability | 15 |
| Validation closure | 15 |
| Residual risk handling | 5 |

Candidate quality must satisfy:

```text
candidate_quality_score / baseline_quality_score >= 0.98
```

## Cost Metrics

- Prompt cost: lines, words, estimated tokens, repeated rules, authority surfaces.
- Handoff cost: lines, fields, MP/CA count, duplicate sections, blocker clarity, downstream read time.
- Artifact cost: spec/plan/tasks/task packet size, repeated metadata, fields with no consumer.
- Cognitive cost: time to find goal, boundary, blockers, validation, and next action.
- Maintenance cost: number of places a rule must be changed.

## Required Workflow Before Optimizing

1. Measure baseline prompt and artifact costs.
2. Score baseline quality using real samples when available.
3. Run Behavior-Artifact Backtrace for candidate prompt or artifact units.
4. Identify keep, merge, move, tighten, and delete candidates.
5. Define replacement protection for every removed or moved rule.
6. Estimate candidate quality retention and cost reduction.
7. Apply only after review approval.
8. Validate tests, skill-flow maps, and sample artifact preservation.
9. Record the evaluation result.

## Related Files

- Design: `docs/superpowers/specs/2026-06-12-sp-workflow-compact-quality-standard-design.md`
- Pattern catalog: `docs/workflow-quality/reusable-pattern-catalog.md`
- Evaluation template: `docs/workflow-quality/evaluation-record-template.md`
- Metrics utility: `tools/workflow-quality/measure_workflow_costs.py`
```

- [ ] **Step 3: Verify the entrypoint contains the quality threshold**

Run:

```powershell
rg -n "quality retention >= 98%|candidate_quality_score / baseline_quality_score >= 0.98" docs\workflow-quality\README.md
```

Expected: two matches.

- [ ] **Step 4: Commit**

```powershell
git add docs\workflow-quality\README.md
git commit -m "docs: add workflow compact quality standard"
```

## Task 2: Add Reusable Pattern Catalog

**Files:**
- Create: `docs/workflow-quality/reusable-pattern-catalog.md`

- [ ] **Step 1: Write the catalog file**

Create `docs/workflow-quality/reusable-pattern-catalog.md` with:

```markdown
# Reusable sp-* Workflow Pattern Catalog

Use this catalog when adding or modifying `sp-*` workflows. Reuse the smallest applicable pattern contract instead of copying long prompt blocks.

## Pattern Record Format

Each pattern records:

- Pattern name
- When to use
- Behavior it enforces
- Minimal prompt contract
- Required artifacts
- Handoff fields
- Validation signals
- Failure modes prevented
- Anti-patterns
- Reusable location
- Example workflows

## State Management Pattern

**When to use:** A workflow must resume, survive context compaction, track blockers, or preserve current phase.

**Minimal prompt contract:**

```text
Create or resume workflow state before substantive work.
Keep state compact and current at phase transitions.
Record status, current stage, blockers, next action, allowed writes, forbidden actions, authoritative files, and terminal state.
Do not continue from stale or contradictory state without resolving it.
```

**Required artifacts:** `discussion-state.md`, `workflow-state.md`, quick `STATUS.md`, debug state, implement tracker, or equivalent.

**Validation signals:** Resume behavior is deterministic; next action, blockers, and terminal states are explicit.

**Failure modes prevented:** Lost context, duplicate sessions, stale state, skipped blockers, phase jumps.

**Example workflows:** `sp-discussion`, `sp-quick`, `sp-debug`, `sp-plan`, `sp-tasks`, `sp-implement`.

## Handoff Contract Pattern

**When to use:** A workflow transfers decisions, obligations, or execution contracts to another workflow.

**Minimal prompt contract:**

```text
Write handoff only when the handoff gate is satisfied.
Include goal, boundary, source evidence, blockers, preserved decisions, downstream instructions, quality gate, and reopen conditions.
Use Markdown for human review and JSON only when downstream automation consumes it.
Do not mark ready until self-review and required user confirmation are recorded.
```

**Required artifacts:** `handoff-to-specify.md/json`, `plan-contract.json`, `handoff-to-tasks.json`, task packets, or worker result envelopes.

**Validation signals:** Downstream artifacts preserve key decisions; Markdown and JSON agree on shared identifiers; hard blockers do not disappear.

**Failure modes prevented:** Context dumping, JSON/Markdown drift, unconfirmed handoff, lost MP/CA obligations, downstream guessing.

**Example workflows:** `sp-discussion -> sp-specify`, `sp-plan -> sp-tasks`, `sp-tasks -> sp-implement`.

## Evidence Gate Pattern

**When to use:** A workflow makes claims about current project behavior, affected files, APIs, tests, runtime state, or external documentation.

**Minimal prompt contract:**

```text
Before project-specific claims, inspect bounded live evidence.
Record verified facts, assumptions, evidence checked, and confidence.
Use project cognition as navigation, not proof.
Ask the user only when evidence cannot answer the question or judgment is required.
```

**Validation signals:** Claims cite files, commands, tests, docs, or user-confirmed assumptions; unknowns have owners and resolve phases.

**Example workflows:** `sp-discussion`, `sp-specify`, `sp-plan`, `sp-debug`, `sp-quick`, `sp-implement`.

## Boundary Gate Pattern

**When to use:** The active repository, target repository, reference source, external system, or implementation path is ambiguous.

**Minimal prompt contract:**

```text
If target, reference, current repository role, external system, or target path is ambiguous, stop technical claims and ask one boundary question.
Record current project roles, target project roles, reference sources, external systems, path status, boundary confidence, and boundary unknowns.
```

**Failure modes prevented:** Wrong repository, wrong evidence source, treating examples as implementation targets.

## Must-Preserve Pattern

**When to use:** Goals, non-goals, decisions, references, trade-offs, or unresolved questions would cause drift if lost.

**Minimal prompt contract:**

```text
Record only drift-causing decisions as MP items.
Each item has id, type, claim, source, downstream requirement, blocking level, owner, latest resolve phase, status, and reopen condition when needed.
Map MP items into spec, plan, tasks, validation, or explicit deferral.
```

**Failure modes prevented:** Scope drift, lost non-goals, accidental reversal of user decisions, downstream reinterpretation.

## Consequence Analysis Pattern

**When to use:** Changes affect lifecycle operations, running state, destructive behavior, shared state, compatibility, security-sensitive behavior, downstream consumers, or multiple plausible product behaviors.

**Minimal prompt contract:**

```text
When consequence risk triggers, record affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and CA obligations.
Each CA item has claim, affected objects, owner workflow, latest resolve phase, status, and stop-and-reopen condition.
Do not mark ready while triggered obligations are unmapped or unsupported by validation.
```

## Subagent Dispatch Pattern

**When to use:** Work can be split into bounded independent lanes or needs parallel verification confidence.

**Minimal prompt contract:**

```text
Choose dispatch shape from workload and safety.
Each lane has purpose, read scope, write scope, forbidden scope, acceptance, verification, result format, and join condition.
Do not dispatch if the work cannot be packetized safely.
At join, consume structured results before declaring completion.
```

## Task Packet Pattern

**When to use:** A task needs to be executable by a worker or resumed independently.

**Minimal prompt contract:**

```text
Each task packet includes task id, objective, dependencies, read scope, write scope, forbidden scope, acceptance criteria, verification commands, preserved MP/CA items, result envelope, and escalation path.
Use batch defaults for repeated fields and per-task deltas for differences.
```

## Validation Closeout Pattern

**When to use:** A workflow claims completion, readiness, resolution, or handoff-ready status.

**Minimal prompt contract:**

```text
Record validation commands, results, acceptance coverage, unmapped obligations, residual risks, external validation gaps, dirty-state assumptions, and next action.
Do not merge residual risk into completion language.
```

## Escalation Pattern

**When to use:** Scope growth, missing evidence, root-cause uncertainty, unsafe consequence obligations, or impossible handoff prevents safe continuation.

**Minimal prompt contract:**

```text
When the current workflow cannot safely continue, record blocker, owner, latest safe resolve phase, stop condition, and recommended next workflow.
Do not downgrade hard blockers to soft unknowns.
Do not escalate when a bounded local resolution exists.
```
```

- [ ] **Step 2: Verify all first-pass patterns are present**

Run:

```powershell
rg -n "State Management Pattern|Handoff Contract Pattern|Evidence Gate Pattern|Boundary Gate Pattern|Must-Preserve Pattern|Consequence Analysis Pattern|Subagent Dispatch Pattern|Task Packet Pattern|Validation Closeout Pattern|Escalation Pattern" docs\workflow-quality\reusable-pattern-catalog.md
```

Expected: ten pattern headings.

- [ ] **Step 3: Commit**

```powershell
git add docs\workflow-quality\reusable-pattern-catalog.md
git commit -m "docs: add reusable sp workflow pattern catalog"
```

## Task 3: Add Evaluation Record Template

**Files:**
- Create: `docs/workflow-quality/evaluation-record-template.md`

- [ ] **Step 1: Write the evaluation template**

Create `docs/workflow-quality/evaluation-record-template.md` with:

```markdown
# sp-* Workflow Compactness Evaluation Record

## Summary

- workflow:
- target_layer:
- optimization_goal:
- protected_quality:
- decision: proposed | accepted | rejected | needs-revision

## Baseline Metrics

- baseline_prompt_cost_lines:
- baseline_prompt_cost_words:
- baseline_artifact_cost_lines:
- baseline_artifact_cost_words:
- baseline_quality_score:
- baseline_samples:

## Candidate Metrics

- candidate_prompt_cost_lines:
- candidate_prompt_cost_words:
- candidate_artifact_cost_lines:
- candidate_artifact_cost_words:
- candidate_quality_score:
- quality_retention:
- prompt_reduction:
- artifact_reduction:

## Behavior-Artifact Backtrace

| Unit ID | Source Location | Intended Behavior | Artifact Trace | Failure Mode Prevented | Cost | Duplication | Score | Decision | Rationale |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| example.unit.01 | templates/commands/example.md#Section | Trigger specific behavior | spec.md / plan.md / tests | Specific failure | low | unique | 3 | keep | Behavior is required and traceable. |

## Replacement Protection

| Removed or Moved Content | Replacement Protection | Validation |
| --- | --- | --- |
|  |  |  |

## Validation Plan

- Static contract checks:
- Artifact contract checks:
- Efficiency checks:
- Sample chains inspected:

## Result

- quality_retention_passed:
- cost_reduction_passed:
- downstream_cost_not_transferred:
- accepted_changes:
- rejected_changes:
- follow_up:
```

- [ ] **Step 2: Verify the template contains required scoring fields**

Run:

```powershell
rg -n "quality_retention|prompt_reduction|artifact_reduction|Behavior-Artifact Backtrace|Replacement Protection" docs\workflow-quality\evaluation-record-template.md
```

Expected: five or more matches.

- [ ] **Step 3: Commit**

```powershell
git add docs\workflow-quality\evaluation-record-template.md
git commit -m "docs: add workflow compactness evaluation template"
```

## Task 4: Add Workflow Cost Metrics Utility

**Files:**
- Create: `tools/workflow-quality/measure_workflow_costs.py`

- [ ] **Step 1: Create the tool directory**

Run:

```powershell
New-Item -ItemType Directory -Force tools\workflow-quality
```

Expected: `tools/workflow-quality` exists.

- [ ] **Step 2: Add the metrics script**

Create `tools/workflow-quality/measure_workflow_costs.py` with:

```python
#!/usr/bin/env python3
"""Measure prompt and workflow artifact size for compactness baselines."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


WORD_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")

DEFAULT_PROMPT_GLOBS = (
    "templates/commands/*.md",
    "templates/command-partials/**/*.md",
    "templates/passive-skills/**/SKILL.md",
    "templates/worker-prompts/*.md",
)

DEFAULT_ARTIFACT_GLOBS = (
    ".specify/discussions/**/*.md",
    ".specify/discussions/**/*.json",
    ".specify/features/**/*.md",
    ".specify/features/**/*.json",
    ".planning/quick/**/*.md",
    ".planning/quick/**/*.json",
)


@dataclass(frozen=True)
class FileMetric:
    path: str
    kind: str
    lines: int
    words: int
    bytes: int


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def measure_file(root: Path, path: Path, kind: str) -> FileMetric:
    text = path.read_text(encoding="utf-8", errors="replace")
    return FileMetric(
        path=path.relative_to(root).as_posix(),
        kind=kind,
        lines=0 if text == "" else text.count("\n") + (0 if text.endswith("\n") else 1),
        words=count_words(text),
        bytes=len(text.encode("utf-8")),
    )


def iter_matches(root: Path, globs: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def summarize(metrics: list[FileMetric]) -> dict[str, object]:
    totals_by_kind: dict[str, dict[str, int]] = {}
    for metric in metrics:
        bucket = totals_by_kind.setdefault(
            metric.kind,
            {"files": 0, "lines": 0, "words": 0, "bytes": 0},
        )
        bucket["files"] += 1
        bucket["lines"] += metric.lines
        bucket["words"] += metric.words
        bucket["bytes"] += metric.bytes
    return {
        "totals": totals_by_kind,
        "files": [asdict(metric) for metric in sorted(metrics, key=lambda item: item.path)],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to inspect.")
    parser.add_argument("--include-artifacts", action="store_true", help="Also measure .specify/.planning artifact samples.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def render_markdown(summary: dict[str, object]) -> str:
    totals = summary["totals"]
    assert isinstance(totals, dict)
    lines = [
        "# Workflow Cost Metrics",
        "",
        "| Kind | Files | Lines | Words | Bytes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for kind, values in sorted(totals.items()):
        assert isinstance(values, dict)
        lines.append(
            f"| {kind} | {values['files']} | {values['lines']} | {values['words']} | {values['bytes']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    metrics = [measure_file(root, path, "prompt") for path in iter_matches(root, DEFAULT_PROMPT_GLOBS)]
    if args.include_artifacts:
        metrics.extend(measure_file(root, path, "artifact") for path in iter_matches(root, DEFAULT_ARTIFACT_GLOBS))
    summary = summarize(metrics)
    if args.format == "json":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the script in JSON mode**

Run:

```powershell
python tools\workflow-quality\measure_workflow_costs.py --root . --format json | ConvertFrom-Json | Select-Object -ExpandProperty totals
```

Expected: output includes a `prompt` object with positive `files`, `lines`, `words`, and `bytes` counts.

- [ ] **Step 4: Run the script in Markdown mode**

Run:

```powershell
python tools\workflow-quality\measure_workflow_costs.py --root . --format markdown
```

Expected: output starts with `# Workflow Cost Metrics` and includes a `prompt` row.

- [ ] **Step 5: Commit**

```powershell
git add tools\workflow-quality\measure_workflow_costs.py
git commit -m "tools: add workflow cost metrics utility"
```

## Task 5: Add Metrics Utility Tests

**Files:**
- Create: `tests/test_workflow_quality_metrics.py`

- [ ] **Step 1: Write pytest coverage for word counting and summaries**

Create `tests/test_workflow_quality_metrics.py` with:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "workflow-quality" / "measure_workflow_costs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("measure_workflow_costs", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_count_words_handles_ascii_identifiers_and_chinese_text():
    module = load_module()

    assert module.count_words("sp-discussion Truth Pass 质量") == 6


def test_measure_file_counts_lines_words_and_bytes(tmp_path):
    module = load_module()
    root = tmp_path
    path = root / "templates" / "commands" / "example.md"
    path.parent.mkdir(parents=True)
    path.write_text("hello world\nsecond line\n", encoding="utf-8")

    metric = module.measure_file(root, path, "prompt")

    assert metric.path == "templates/commands/example.md"
    assert metric.kind == "prompt"
    assert metric.lines == 2
    assert metric.words == 4
    assert metric.bytes == len("hello world\nsecond line\n".encode("utf-8"))


def test_summarize_groups_by_kind(tmp_path):
    module = load_module()
    root = tmp_path
    prompt = root / "templates" / "commands" / "example.md"
    artifact = root / ".specify" / "features" / "001-demo" / "spec.md"
    prompt.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    prompt.write_text("prompt text\n", encoding="utf-8")
    artifact.write_text("artifact text\n", encoding="utf-8")

    summary = module.summarize(
        [
            module.measure_file(root, prompt, "prompt"),
            module.measure_file(root, artifact, "artifact"),
        ]
    )

    assert summary["totals"]["prompt"]["files"] == 1
    assert summary["totals"]["artifact"]["files"] == 1
    assert summary["totals"]["prompt"]["lines"] == 1
    assert summary["totals"]["artifact"]["lines"] == 1
```

- [ ] **Step 2: Run the new tests**

Run:

```powershell
pytest tests/test_workflow_quality_metrics.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run the existing workflow template alignment tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: all tests pass. The workflow-quality docs and tool should not affect workflow template alignment.

- [ ] **Step 4: Commit**

```powershell
git add tests\test_workflow_quality_metrics.py
git commit -m "test: cover workflow cost metrics utility"
```

## Task 6: Add First Baseline Report

**Files:**
- Create: `docs/workflow-quality/baseline-current-sp-workflows.md`

- [ ] **Step 1: Generate current prompt metrics**

Run:

```powershell
python tools\workflow-quality\measure_workflow_costs.py --root . --format markdown > .tmp-workflow-costs.md
```

Expected: `.tmp-workflow-costs.md` contains the `prompt` totals table.

- [ ] **Step 2: Generate the baseline report**

Run:

```powershell
$metrics = Get-Content -Raw .tmp-workflow-costs.md
@"
# Current sp-* Workflow Prompt Cost Baseline

## Scope

This baseline measures prompt-source cost for the current SuperSpec workflow surfaces:

- `templates/commands/*.md`
- `templates/command-partials/**/*.md`
- `templates/passive-skills/**/SKILL.md`
- `templates/worker-prompts/*.md`

It does not score quality. Quality scoring requires Behavior-Artifact Backtrace against real downstream samples.

## Metrics Command

```powershell
python tools\workflow-quality\measure_workflow_costs.py --root . --format markdown
```

## Current Totals

$metrics

## Interpretation

- This baseline is a cost baseline, not a quality baseline.
- Future workflow prompt changes should record prompt reduction against this baseline or a workflow-specific baseline.
- A prompt reduction is acceptable only when the related quality retention score remains at or above 98%.

## Next Baselines

- Add artifact-cost baselines from a copied or locally available downstream sample set such as `F:\AI_WORK\jx-skills`.
- Add workflow-specific baselines for the first pilot workflow before changing that workflow.
"@ | Set-Content -Encoding UTF8 docs\workflow-quality\baseline-current-sp-workflows.md
```

Expected: `docs/workflow-quality/baseline-current-sp-workflows.md` contains the generated metrics table under `## Current Totals`.

- [ ] **Step 3: Verify there are no unresolved markers**

Run:

```powershell
rg -n "NEEDS CLARIFICATION|\[FEATURE|\[DATE|\[PROJECT NAME\]" docs\workflow-quality\baseline-current-sp-workflows.md
```

Expected: no matches.

- [ ] **Step 4: Remove temporary metrics output**

Run:

```powershell
Remove-Item .tmp-workflow-costs.md
```

Expected: `.tmp-workflow-costs.md` no longer exists.

- [ ] **Step 5: Commit**

```powershell
git add docs\workflow-quality\baseline-current-sp-workflows.md
git commit -m "docs: add current workflow prompt cost baseline"
```

## Task 7: Link the Standard From Project Guidance

**Files:**
- Modify: `PROJECT-HANDBOOK.md`

- [ ] **Step 1: Add compact quality standard guidance**

In `PROJECT-HANDBOOK.md`, add this bullet near the existing workflow contract guidance:

```markdown
- **sp-* compact quality standard**: Before adding, modifying, or compressing any `sp-*` workflow prompt, handoff shape, state artifact, task packet, or validation closeout contract, use `docs/workflow-quality/README.md`. A candidate optimization must show quality retention of at least 98% and whole-chain cost reduction; do not shorten prompts by moving ambiguity or interpretation burden downstream.
```

- [ ] **Step 2: Verify the handbook link**

Run:

```powershell
rg -n "compact quality standard|docs/workflow-quality/README.md|98%" PROJECT-HANDBOOK.md
```

Expected: one guidance bullet.

- [ ] **Step 3: Commit**

```powershell
git add PROJECT-HANDBOOK.md
git commit -m "docs: link workflow compact quality standard"
```

## Task 8: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run targeted docs/tool tests**

Run:

```powershell
pytest tests/test_workflow_quality_metrics.py tests/test_alignment_templates.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Verify no unresolved markers in new docs**

Run:

```powershell
rg -n "NEEDS CLARIFICATION|\[FEATURE|\[DATE|\[PROJECT NAME\]" docs\workflow-quality tools\workflow-quality tests\test_workflow_quality_metrics.py
```

Expected: no matches.

- [ ] **Step 3: Verify no workflow prompt files were staged by this plan**

Run:

```powershell
git diff --cached --name-only | rg "templates/commands|templates/command-partials|templates/passive-skills"
```

Expected: no matches.

- [ ] **Step 4: Summarize remaining worktree state**

Run:

```powershell
git status --short -- docs\workflow-quality tools\workflow-quality tests\test_workflow_quality_metrics.py PROJECT-HANDBOOK.md templates\commands\discussion.md templates\command-partials\discussion\shell.md
```

Expected: new standard files are committed; any remaining `templates/...discussion...` changes are the pre-existing out-of-scope draft diffs and must remain uncommitted unless separately approved.
