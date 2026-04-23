# Project Learning Layer Design

**Date:** 2026-04-23
**Status:** Proposed
**Owner:** Codex

## Summary

This design adds a shared project learning layer to `spec-kit-plus` so the
repository's `sp-xxx` workflows become more useful over time instead of
restarting from static prompts on every run.

The approved direction is not to turn one command into a self-modifying local
assistant. The approved direction is to add one project-level learning system
that every major workflow can consume:

- `sp-specify`
- `sp-plan`
- `sp-implement`
- `sp-debug`
- `sp-fast`
- `sp-quick`

The system should separate stable project memory from runtime candidate signals.
New observations should first enter a candidate pool, then become confirmed
project learnings, then become project rules when they repeatedly shape real
work. Only long-lived principle-level guidance should rise into
`.specify/memory/constitution.md`.

The first release should ship a shared memory foundation, an explicit review and
promotion command, and a lightweight command-template contract for reading and
producing learnings. It should not start with fully automatic constitution
editing or opaque scoring logic.

## Problem Statement

`spec-kit-plus` already has strong workflow scaffolding:

- project constitution under `.specify/memory/constitution.md`
- handbook and project-map navigation under `PROJECT-HANDBOOK.md` and
  `.specify/project-map/*.md`
- feature-local context such as `alignment.md`, `context.md`, `research.md`,
  `implement-tracker.md`, and debug session files

However, the current system still loses a class of important project knowledge:

1. recurring pitfalls discovered during implementation or debugging
2. recovery paths that repeatedly save time
3. user preferences and project constraints repeated across features
4. workflow gaps where `sp-specify`, `sp-plan`, or `sp-quick` repeatedly miss
   the same planning-critical detail

Today those insights remain trapped in one chat, one task folder, or one
feature's artifacts. The next workflow run may re-ask the same question, repeat
the same mistake, or miss the same constraint because the project has no
cross-stage learning layer between raw chat memory and the constitution.

The root problem is not missing workflow stages. The root problem is missing
project-level retention and promotion of operational knowledge.

## Goals

- Add a shared project learning layer that all major `sp-xxx` workflows read
  before local execution.
- Keep principle-level governance in `constitution.md`.
- Add a separate project memory layer for stable workflow rules and confirmed
  project learnings.
- Add a runtime candidate pool for noisy or newly observed signals.
- Support command-specific learning roles while keeping one shared reading path.
- Let a learning discovered in one stage become usable in other stages when the
  issue is inherently cross-stage.
- Require explicit review or repeated evidence before a learning becomes a
  project rule.
- Keep the first release understandable, inspectable, and file-backed.

## Non-Goals

- Do not start with fully automatic constitution edits.
- Do not introduce cross-repository learning sharing in v1.
- Do not build a heavy scoring or ranking engine before the file-backed flow
  proves useful.
- Do not force every local observation to become a project rule.
- Do not make `sp-fast` and `sp-quick` noisy producers by default.
- Do not duplicate a separate learning system per command.

## User-Approved Decisions

This design reflects the following explicit decisions made during design review:

1. The primary objective is project-level improvement, not feature-local memory.
2. Promotion strength should be layered:
   - soft signals first
   - hard rules only after repetition or confirmation
3. The system should use a dual structure:
   - raw and stable learnings kept separate
   - stable rules promoted independently
4. New learning capture should be semi-automatic:
   - workflows generate candidate learnings
   - confirmation or recurrence promotes them
5. First-release signals should focus on:
   - recurring pitfalls and recovery paths
   - repeated user preferences and constraints
   - repeated workflow gaps
6. Command roles should be differentiated, but the underlying learning system
   must stay shared.
7. Cross-stage recurrence is a strong promotion signal, but a learning first
   discovered in one stage may still become globally useful if it is inherently
   general.
8. Default sharing should be type-based with manual override:
   - not every learning is global
   - but truly general learnings should not stay trapped inside one command
9. High-signal learnings may prompt for confirmation immediately; lower-signal
   items should flow into the candidate pool for later review.
10. Stable non-principle rules should not be written directly into the
    constitution by default.

## Architecture Overview

The system has four layers.

### 1. Principle Layer

Canonical file:

- `.specify/memory/constitution.md`

Responsibilities:

- hold project-level MUST and SHOULD principles
- remain the highest-priority instruction source
- change slowly and intentionally

Only learnings that become true principle-level governance should reach this
layer.

### 2. Stable Shared Learning Layer

Canonical files:

- `.specify/memory/project-rules.md`
- `.specify/memory/project-learnings.md`

Responsibilities:

- preserve stable, shared project rules that affect multiple workflows
- preserve confirmed project learnings that are reusable but not yet principle
  level
- act as the main project-level improvement layer that sits below the
  constitution and above feature-local artifacts

`project-rules.md` is stricter than `project-learnings.md`.

### 3. Runtime Candidate Layer

Canonical files:

- `.planning/learnings/candidates.md`
- `.planning/learnings/review.md`

Responsibilities:

- store noisy or newly observed candidate learnings
- track pending review, deduplication, promotion, and rejection decisions
- avoid polluting stable memory with one-off observations

This is the runtime and triage surface, not the long-term instruction layer.

### 4. Command Consumption Layer

Every major `sp-xxx` workflow should read memory in the same order:

1. `.specify/memory/constitution.md`
2. `.specify/memory/project-rules.md`
3. `.specify/memory/project-learnings.md`
4. command-local context and task-local artifacts

This keeps project-level memory shared while still allowing each workflow to
apply its own local state.

## Learning Lifecycle

The approved lifecycle has four states.

### `candidate`

Location:

- `.planning/learnings/candidates.md`

Source:

- workflow-generated signals
- high-signal local observations
- repeated user corrections or project constraints

Properties:

- can be noisy
- can be local at first
- should be structured and deduplicable

### `confirmed`

Location:

- `.specify/memory/project-learnings.md`

Promotion triggers:

- user explicitly confirms the behavior should be remembered
- the same issue or rule recurs
- the learning is shown to have cross-stage value even if first observed in only
  one command

Properties:

- shared across workflows
- still treated as reusable experience rather than the project's highest-priority
  rules

### `promoted-rule`

Location:

- `.specify/memory/project-rules.md`

Promotion triggers:

- confirmed learning repeatedly changes workflow defaults
- the rule becomes a stable project expectation across multiple tasks or stages
- the user explicitly indicates the behavior should become the default

Properties:

- shapes the default behavior of later `sp-xxx` commands
- stronger than general learnings
- weaker than constitution principles

### `promoted-constitution`

Location:

- `.specify/memory/constitution.md`

Promotion triggers:

- the learning has become a durable governance rule
- the rule belongs at principle level rather than workflow level

Properties:

- highest authority
- should require deliberate promotion
- should not be a normal v1 automation path

## Learning Entry Contract

Every candidate learning should be captured as a structured entry.

Recommended minimum fields:

```yaml
id: "LRN-20260423-001"
summary: "Quick tasks in this repo must still sweep propagation surfaces before claiming completion"
learning_type: "workflow_gap"
source_command: "sp-quick"
evidence: "Three quick-task runs left tests/docs/callsites unchecked"
recurrence_key: "quick.propagation_surface_sweep"
default_scope: "quick"
applies_to:
  - "sp-quick"
  - "sp-fast"
  - "sp-implement"
signal_strength: "high"
status: "candidate"
```

Key fields:

- `learning_type` determines default sharing behavior
- `recurrence_key` enables deduplication and recurrence tracking
- `applies_to` allows single-stage discoveries to become multi-stage inputs when
  they are inherently general
- `signal_strength` determines whether immediate confirmation should be offered

## Default Sharing Model

The system should use type-based default sharing with manual override.

Recommended defaults:

- `user_preference`
  - default scope: global
  - default applies to: all `sp-xxx`
- `project_constraint`
  - default scope: global
  - default applies to: all `sp-xxx`
- `pitfall`
  - default scope: implementation-heavy
  - default applies to: `sp-implement`, `sp-debug`, `sp-quick`
- `recovery_path`
  - default scope: execution-heavy
  - default applies to: `sp-implement`, `sp-debug`, optionally `sp-quick`
- `workflow_gap`
  - default scope: planning-heavy
  - default applies to: `sp-specify`, `sp-plan`, optionally `sp-quick`

Override rule:

- if a learning is discovered in one command but is truly cross-stage, it may be
  promoted with broader `applies_to` coverage
- if a learning is too local, its `applies_to` surface may be narrowed manually

## Command Roles

### `sp-specify`

Primary production role:

- `workflow_gap`
- `user_preference`
- `project_constraint`

Typical signals:

- same planning-critical question repeatedly missing from intake
- same user boundary repeated across features
- same scope or output preference repeatedly clarified

### `sp-plan`

Primary production role:

- `workflow_gap`
- `project_constraint`

Typical signals:

- repeated planning omissions
- repeated missing validation or propagation guidance
- repeated failure to preserve shared constraints in plan artifacts

### `sp-implement`

Primary production role:

- `pitfall`
- `recovery_path`
- `project_constraint`

Typical signals:

- repeated implementation traps
- repeated recovery sequences
- repeated execution ordering constraints

### `sp-debug`

Primary production role:

- `pitfall`
- `recovery_path`

Typical signals:

- repeated root-cause patterns
- repeated truth-ownership misunderstandings
- repeated diagnostic or recovery wins

### `sp-fast`

Default role:

- strong consumer
- weak producer

It should only produce candidate learnings for clearly high-signal, reusable
findings.

### `sp-quick`

Default role:

- strong consumer
- selective producer

It may produce:

- `pitfall`
- `workflow_gap`
- `project_constraint`

but only when the signal is clearly reusable beyond a one-off quick task.

## Confirmation and Promotion Flow

The system should support a dual-track confirmation model.

### Immediate confirmation path

Use when:

- signal strength is `high`
- user explicitly says "remember this" or "default to this"
- recurrence is already visible
- cross-stage usefulness is obvious

Behavior:

- prompt the user to confirm promotion into shared memory

### Deferred review path

Use when:

- signal strength is `low` or `medium`
- utility is plausible but not yet proven

Behavior:

- write the entry to `candidates.md`
- leave promotion to the explicit review workflow

## Review Command

The first release should add one explicit shared review entry point:

- `sp-learnings`

Primary responsibilities:

- inspect candidate learnings
- deduplicate or merge by `recurrence_key`
- mark items as confirmed
- promote items into `project-learnings.md`
- promote stable items into `project-rules.md`
- recommend constitution promotion when appropriate, without auto-editing the
  constitution in v1

This command is the promotion valve that prevents candidate noise from becoming
shared law too quickly.

## First Release Scope

The minimum useful release should include:

1. initialization of shared memory files:
   - `.specify/memory/project-rules.md`
   - `.specify/memory/project-learnings.md`
2. lazy creation of runtime learning files:
   - `.planning/learnings/candidates.md`
   - `.planning/learnings/review.md`
3. shared read contract injected into:
   - `sp-specify`
   - `sp-plan`
   - `sp-implement`
   - `sp-debug`
   - `sp-fast`
   - `sp-quick`
4. candidate production support for:
   - `sp-specify`
   - `sp-plan`
   - `sp-implement`
   - `sp-debug`
5. strong-consumer / weak-producer behavior for:
   - `sp-fast`
   - `sp-quick`
6. one explicit review and promotion command:
   - `sp-learnings`

## Implementation Boundaries

The v1 implementation should stay inside these surfaces:

- memory file initialization in `src/specify_cli/__init__.py`
- a shared learning helper module such as `src/specify_cli/learnings.py`
- new memory templates and command template(s)
- modifications to existing command templates so they read the shared learning
  layer
- packaging updates in `pyproject.toml`
- tests for initialization, template generation, and promotion flow

The v1 implementation should not require:

- automatic constitution mutation
- cross-repository sync
- opaque learning summarizers
- one runtime-specific learning implementation per integration

## Risks

- Candidate noise may overwhelm the review surface if signal discipline is weak.
- Project rules may become too broad if stage-local learnings are promoted
  without clear reuse evidence.
- Constitution pollution may occur if workflow rules are promoted too far.
- `sp-fast` and `sp-quick` may become noisy if they overproduce low-value
  candidate learnings.

## Mitigations

- require `recurrence_key` for deduplication
- require `applies_to` so scope is explicit
- reserve immediate confirmation for high-signal items
- keep constitution promotion deliberate and exceptional
- make `sp-fast` and `sp-quick` conservative producers in v1

## Acceptance Criteria

The design is complete when:

1. New projects can initialize `project-rules.md` and `project-learnings.md`
   alongside the constitution.
2. Runtime candidate learning files can be created lazily under
   `.planning/learnings/`.
3. The six major `sp-xxx` workflows read the shared learning layer before
   command-local context.
4. `sp-specify`, `sp-plan`, `sp-implement`, and `sp-debug` can produce
   structured candidate learnings.
5. `sp-fast` and `sp-quick` consume shared learnings by default and produce new
   candidates only selectively.
6. A dedicated `sp-learnings` workflow exists for candidate review and
   promotion.
7. Promotion can move items from candidates to shared learnings and from shared
   learnings to project rules without auto-editing the constitution.
8. Tests cover initialization, read-contract generation, deduplication, and
   promotion state flow.
