# Self-Learning V2 Design

**Date:** 2026-05-11
**Status:** Approved for implementation planning
**Owner:** Codex
**Scope:** Passive project learning memory, generated workflow guidance, generated agent context files, learning CLI helpers, runtime closeout behavior, and tests

## Summary

This design replaces the current candidate-first project learning model with a
two-layer reading and writing model:

1. A thin learning index that is always cheap to read and update.
2. One detailed markdown document per lesson when the lesson needs evidence,
   context, recovery steps, or prevention guidance.

The purpose is to make downstream projects actually preserve reusable engineering
judgment instead of only shipping learning helper commands that agents rarely
run. The system should behave like an experienced engineer reviewing a task
before closeout: notice what is likely to repeat, record the lesson while it is
fresh, and keep the entry discoverable before related work starts.

The core product change is this:

**Learning capture becomes a normal workflow closeout responsibility, not an
optional learning-management activity.**

Constitution-level guidance should state the principle. Generated agent context
such as `AGENTS.md`, `CLAUDE.md`, Codex skills, and other CLI-specific surfaces
should state the reflex. Runtime closeout helpers should make the reflex hard to
skip for non-trivial workflows.

## Problem

The current learning system has useful primitives but does not reliably create
usable downstream learnings.

Verified current-state findings:

- `learning start` creates files, reads existing memory, and auto-promotes
  repeated candidates, but it does not create new lessons.
- New lessons are written only by `learning capture`, `learning capture-auto`,
  or `hook capture-learning`.
- Most workflows rely on template prose that asks the agent to run those helper
  commands. That is guidance, not enforcement.
- Claude and Gemini native hooks currently bridge `signal-learning` warnings,
  but they do not automatically perform terminal review or capture.
- Codex and most other generated integrations mainly receive rendered command
  instructions and passive skill guidance.
- `capture-auto` only extracts lessons from specific durable state fields. If a
  workflow did not record friction in those fields, auto-capture returns no
  candidates even when the session clearly discovered a reusable lesson.
- The existing candidate/confirmed/promotion framing encourages the agent to
  judge importance too early. In practice, that raises the write threshold and
  causes agents to record nothing.

The product failure is not that the helper functions are absent. The product
failure is that the workflow does not trigger learning often enough, and the
first writable memory layer is not simple enough.

## Goals

- Make reusable engineering lessons easy to capture during normal workflow
  closeout.
- Use a two-layer read path: a thin index first, then selected detail documents.
- Preserve enough information in the index for relevance decisions without
  forcing every workflow to open every detail document.
- Move away from candidate/confirmed as the primary mental model for everyday
  learning writes.
- Keep `project-rules.md` and constitution promotion intentionally stricter than
  normal learning capture.
- Add a clear Learning Reflex to generated agent context files and workflow
  skills.
- Let runtime closeout helpers trigger learning capture for non-trivial
  workflows instead of relying only on agent discipline.
- Preserve backward compatibility for existing `project-learnings.md` and
  `.planning/learnings/candidates.md` files during migration.

## Non-Goals

- Do not auto-edit the constitution with individual lessons.
- Do not create a separate learning workflow that users must run manually.
- Do not require user approval before recording low-risk project memory.
- Do not store every ordinary implementation detail as a lesson.
- Do not make the thin index a heavy approval queue.
- Do not remove old learning files in the same change. Migration should be
  additive and compatible.

## Design Principles

### 1. Default To Lightweight Capture

If a future senior engineer would save meaningful time or avoid meaningful risk
by seeing a lesson before related work, the lesson should be captured.

The agent should not ask whether the lesson is important enough for a stable
rule. That judgment belongs to the promotion path, not the first write path.

### 2. Read In Two Layers

The learning index is the first-read layer. It must be thin, but it must not
discard the information needed to decide relevance.

Detail documents are opened only when the index indicates that the lesson
applies to the current command, files, error signal, workflow phase, or tool
surface.

### 3. Promotion Is Separate From Capture

Normal learning capture records a lesson in the index and detail document.
Promotion into `project-rules.md` or constitution requires stronger evidence:
repeat occurrence, explicit user confirmation, or clear cross-workflow
governance value.

### 4. Runtime Beats Reminder Text

Templates and generated agent instructions are necessary, but they are not
sufficient. Non-trivial workflow closeout should call learning runtime helpers
or otherwise force a learning review path before final reporting.

## Memory Structure

### Principle Layer

Canonical file:

- `.specify/memory/constitution.md`

Role:

- State that reusable engineering lessons are project memory.
- State that learning capture is part of workflow correctness.
- State that the learning index is the first-read layer.
- State that detailed learning docs preserve evidence and recovery paths.

The constitution should not contain individual lessons unless a lesson becomes a
slow-changing project principle.

### Stable Rules Layer

Canonical file:

- `.specify/memory/project-rules.md`

Role:

- Store stable project defaults and constraints.
- Store rules that should shape many workflows.
- Remain stricter than the normal learning index.

### Learning Index Layer

Canonical file:

- `.specify/memory/learnings/INDEX.md`

Role:

- Provide a compact first-read map of reusable lessons.
- Allow fast relevance filtering.
- Merge repeated observations by stable id or recurrence key.
- Link to one detail document per lesson.

Each index entry should include:

```yaml
- id: learn-2026-05-11-cli-helper-drift
  problem: Generated agent guidance can drift from runtime helper behavior.
  lesson: Treat helper command shapes as runtime contracts and test template examples against the real CLI surface.
  applies_to:
    - integrations
    - generated-commands
    - launcher-diagnostics
    - workflow-templates
  trigger_signals:
    - stale helper option
    - command shape mismatch
    - downstream workflow no-op
  detail: ./learn-2026-05-11-cli-helper-drift.md
  last_seen: 2026-05-11
```

The exact on-disk format can be markdown with a managed machine-readable block,
matching the existing learning file style. The important contract is that the
index remains readable by both humans and tools.

### Learning Detail Layer

Canonical directory:

- `.specify/memory/learnings/`

Example files:

- `.specify/memory/learnings/learn-2026-05-11-cli-helper-drift.md`
- `.specify/memory/learnings/learn-2026-05-11-project-map-refresh.md`

Each detailed lesson document should include:

- problem
- lesson
- when to apply
- trigger signals
- observed failure path
- root cause
- recovery or prevention steps
- related files, commands, or workflow surfaces
- verification evidence
- exceptions or non-applicability notes
- last seen date

## Workflow Read Path

Every non-trivial workflow should load memory in this order:

1. `.specify/memory/constitution.md`
2. `.specify/memory/project-rules.md`
3. `.specify/memory/learnings/INDEX.md`
4. Detail documents referenced by relevant index entries
5. Command-local context and task-local artifacts

Relevance should be determined from:

- active workflow command
- touched files or directories
- current error signal
- current workflow phase
- target integration or CLI
- trigger signals listed in the index

The workflow should not open every detail document by default.

## Learning Reflex

Generated agent context should include a short, explicit Learning Reflex.

Required wording concept:

> Before final closeout, ask whether a future senior engineer would benefit from
> seeing this lesson before related work. If yes, update the learning index and
> detail document. Do not ask the user for routine permission to record low-risk
> project memory. Do not bury reusable lessons only in chat, task files, or
> workflow-state.

The reflex should be installed into:

- generated root `AGENTS.md`
- generated `CLAUDE.md`
- Codex skill guidance
- Kimi and Antigravity skills surfaces
- Claude command guidance
- Gemini and Tabnine TOML prompt surfaces
- generic markdown command integrations
- passive `spec-kit-project-learning` skill
- shared command partials that describe learning behavior

## Capture Triggers

The agent should record or merge a learning when one of these signals appears:

- The same kind of problem required more than one attempt.
- The hypothesis changed more than once.
- Validation failed repeatedly or the validation route proved misleading.
- The user corrected a pattern that could recur.
- A workflow route was wrong or a stage lacked a required upstream input.
- A hidden dependency, environment issue, path rule, generated asset boundary,
  or CLI-specific behavior was discovered.
- A durable state file failed to preserve resume, handoff, or subagent join
  context.
- The task required coordinated edits across templates, runtime code, tests,
  scripts, and docs because a product surface was more coupled than expected.
- The agent would naturally say, "Next time, check this before doing related
  work."

The agent may skip capture when the issue is clearly one-off:

- a typo with no reusable pattern
- a transient network or cache issue with no project-specific recovery lesson
- an implementation detail already fully covered by tests, lint, types, or docs
- a business decision that only applies to the current feature and has no
  reusable engineering value

## Write Path

### Workflow Start

`learning start` should ensure:

- `.specify/memory/project-rules.md`
- `.specify/memory/learnings/INDEX.md`
- compatibility files required by older projects

It should return:

- relevant rules
- relevant index entries
- detail document paths recommended for reading
- any compatibility entries from old `project-learnings.md` or candidates that
  still apply

### Workflow Closeout

Every non-trivial workflow should run a learning closeout step before final
reporting.

If learning signals exist:

- create or merge an index entry
- create or update the detail document
- record `last_seen`
- preserve evidence and prevention guidance

If no learning signal exists:

- the workflow may skip writing
- but the closeout review must explicitly decide that the run produced no
  reusable lesson

This review can remain internal unless the workflow is already producing a
machine-readable closeout payload.

### Runtime Auto-Capture

Runtime closeout helpers should call learning capture automatically where the
project already has durable state:

- implement closeout from `implement-tracker.md`
- debug closeout from debug session files
- quick closeout from `STATUS.md`
- testing closeout from `testing-state.md`
- workflow-state based closeout for specify, clarify, deep-research, plan,
  checklist, tasks, analyze, map-scan, and map-build

The auto-capture logic should be broadened so it can create a useful index entry
from general friction signals, not only from a few narrow state-field patterns.

## CLI Surface

The existing helper names can stay, but their primary storage target changes.

Required behavior:

- `specify learning ensure`
  - creates the index directory and index template
  - preserves existing stable memory files
- `specify learning start`
  - returns relevant index entries and detail refs
  - reads old `project-learnings.md` and candidates for compatibility
- `specify learning capture`
  - writes or merges an index entry
  - creates or updates a detail document
  - can optionally mirror compatibility data to old files during transition
- `specify learning capture-auto`
  - writes into the index/detail model
  - supports durable state inputs from workflow closeout
- `specify learning promote`
  - remains the path to `project-rules.md`
  - may also support constitution promotion only when the existing governance
    flow explicitly allows it
- `specify learning aggregate`
  - summarizes index entries, repeated lessons, stale lessons, and promotion
    candidates

The old `.planning/learnings/candidates.md` should remain readable but should no
longer be described as the primary learning layer.

## Template And Agent Context Changes

### Command Templates

All non-trivial workflow templates should describe:

- two-layer learning read path
- Learning Reflex before closeout
- automatic closeout capture when runtime helpers are available
- one-off skip rule
- promotion only for rules and constitution-level guidance

`sp-fast` can remain trivial and skip learning unless the task escalates.

`sp-quick` should keep a light path, but its closeout should still auto-capture
from quick state when useful.

### Passive Skill

`templates/passive-skills/spec-kit-project-learning/SKILL.md` should be rewritten
around:

- index first
- detail docs second
- rules and constitution only for stable promotions
- capture by default when future reuse is plausible

It should stop presenting candidate/confirmed as the main everyday learning
model.

### Generated Context Files

The generated project context block should include a concise Learning Reflex in
the managed AGENTS/CLAUDE context renderers:

- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`

Integration-specific generated assets should receive the same instruction
through shared rendering rather than one-off duplicated prose.

## Migration

Migration should be additive:

- keep `.specify/memory/project-learnings.md`
- keep `.planning/learnings/candidates.md`
- add `.specify/memory/learnings/INDEX.md`
- add detail documents only for new or migrated lessons
- teach `learning start` to surface compatible old entries
- optionally provide an aggregate or migration helper later

Existing projects should not lose previous manually recorded lessons.

## Tests

Required regression coverage:

- `specify init` creates the learning index template in downstream projects.
- packaged assets include the index and detail templates.
- `learning ensure` creates `.specify/memory/learnings/INDEX.md`.
- `learning start` returns relevant index entries and recommended detail docs.
- `learning capture` creates or merges an index entry and creates or updates the
  detail markdown file.
- `learning capture-auto` writes to index/detail storage for implement, quick,
  debug, testing, and workflow-state sources.
- generated command templates mention the two-layer read path and Learning
  Reflex.
- generated Codex skills include the Learning Reflex.
- generated Claude, Gemini, markdown, TOML, and generic integrations preserve
  the same learning behavior.
- `project-learnings.md` and `.planning/learnings/candidates.md` remain readable
  compatibility sources.
- tests stop asserting that candidate files are the primary downstream learning
  layer.

## Acceptance Criteria

This design is complete when a generated downstream project has:

- `.specify/memory/learnings/INDEX.md`
- a clear template for per-lesson detail documents
- generated agent guidance that tells the agent to record reusable lessons by
  default
- workflow start behavior that reads the index before local context
- workflow closeout behavior that writes or merges learning entries for
  reusable engineering lessons
- compatibility with old stable and candidate learning files

The success metric is not that every task writes a lesson. The success metric is
that a task with reusable friction no longer silently exits without durable
project memory.
