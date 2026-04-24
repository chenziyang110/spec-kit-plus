# Agent-Required Action Marker Design

**Date:** 2026-04-24
**Status:** Proposed
**Owner:** Codex

## Summary

This design adds a first-class carrier for must-do workflow actions that are currently written as ordinary prose and therefore get skipped, downgraded to background context, or lost after context trimming.

The approved direction is:

- add a new line-level marker, `[AGENT]`, for actions the AI must explicitly execute
- keep `[AGENT]` fully separate from `[P]`
- preserve the current `[P] + batch + runtime policy` execution model
- inject Spec Kit Plus hard rules into user `AGENTS.md` files through a managed block instead of appending or replacing the whole file
- cover the full command surface, including `sp-fast`, `sp-quick`, and `sp-map-codebase`
- require `sp-fast` and `sp-quick` to participate in the passive learning start and capture loop instead of acting as learning bypasses

This is an enhancement layer, not a replacement of the current orchestration model.

## Problem Statement

The repository already contains strong guidance for:

- project-map reading
- passive learning start
- strategy selection
- tracker and workflow-state recovery
- delegated execution packet validation

The recurring failure is not missing knowledge. The failure is that must-do actions are still carried mostly as normal Markdown prose. During fast scanning or after context compaction, the model can interpret those lines as:

- important background
- recommended practice
- a reminder to apply later

instead of:

- a required action that must happen before the next stage can continue

This produces repeated execution-discipline failures such as:

1. entering implementation before running `specify learning start`
2. reading the rule but not applying `choose_execution_strategy(...)`
3. skipping handbook or project-map loading because the step looked like explanatory text
4. treating `sp-fast` or `sp-quick` as exemptions from shared learning and state rules

The root problem is not lack of rules. The root problem is lack of a first-class carrier for rules that are mandatory to execute.

## Goals

- Create a compact, explicit marker for actions the AI must execute.
- Make the marker usable across all `sp-*` workflows.
- Keep the marker independent from parallelism and delegation semantics.
- Preserve user-authored `AGENTS.md` content while letting Spec Kit Plus maintain a stable hard-rules block.
- Cover the full first-wave command surface:
  - `sp-specify`
  - `sp-plan`
  - `sp-tasks`
  - `sp-implement`
  - `sp-debug`
  - `sp-quick`
  - `sp-fast`
  - `sp-map-codebase`
- Require `sp-fast` and `sp-quick` to participate in the passive learning lifecycle.
- Support fail-closed enforcement for the highest-risk actions.

## Non-Goals

- Do not make `[AGENT]` a parallelism marker.
- Do not make `[AGENT]` a subagent marker.
- Do not replace `[P]`, explicit parallel batches, join points, or strategy routing.
- Do not introduce block-level or heading-level inheritance in the first release.
- Do not replace the user's entire `AGENTS.md`.
- Do not make `sp-fast` or `sp-quick` run the full long-path workflow every time.

## User-Approved Decisions

This design reflects the following explicit decisions from review:

1. The missing capability is a hard carrier for must-do actions, not stronger wording alone.
2. `[AGENT]` must be independent from `[P]`.
3. `[AGENT]` must work across all `sp-*` workflows, not only long implementation flows.
4. The first release should support line-level markers only.
5. Existing user `AGENTS.md` files must be preserved and extended through a managed block.
6. `sp-fast`, `sp-quick`, and `sp-map-codebase` are first-wave commands and must not be omitted.
7. `sp-fast` and `sp-quick` must also enter the passive learning start and capture loop.

## Architecture Overview

The design has four layers.

### 1. Line-Level Required Action Marker

`[AGENT]` is a standalone marker on a single actionable line.

It means:

- this line describes an action the AI must explicitly execute
- the action cannot be silently skipped
- the action cannot be downgraded into background reading or a reminder

It does not mean:

- this task is parallel
- this task must use a child agent
- this task belongs to a special runtime

### 2. Managed `AGENTS.md` Rule Block

Spec Kit Plus-owned hard rules should live inside a bounded, updateable block:

```md
<!-- SPEC-KIT:BEGIN -->
[managed Spec Kit Plus rules]
<!-- SPEC-KIT:END -->
```

This block becomes the durable cross-command rules surface.

### 3. Command Template Embedding

Shared command templates in `templates/commands/*.md` should convert hard actions into `[AGENT]` lines so the requirement survives:

- scanning
- trimming
- resume after compaction
- template rendering into skills or commands

### 4. Runtime Enforcement

The runtime should treat `[AGENT]` lines as required actions with explicit outcomes:

- completed
- blocked with evidence
- deferred only because a named prerequisite is being satisfied first

No silent skip is allowed.

## `[AGENT]` Semantics

### Canonical Meaning

`[AGENT]` means: this action must be explicitly performed by the AI before the workflow may continue past the relevant gate.

### Independence From `[P]`

The semantics must remain separate:

- `[P]` answers: can this work run in parallel?
- `[AGENT]` answers: must the AI explicitly perform this action?

Examples:

- `[P]` only: parallelizable task, but not necessarily a hard gate
- `[AGENT]` only: mandatory action with no parallel meaning
- `[P] [AGENT]`: a valid combined line if both meanings are true

### First-Release Scope

The first release supports line-level use only.

Supported examples:

```md
- [AGENT] Run `specify learning start --command quick --format json`
1. [AGENT] Read `PROJECT-HANDBOOK.md`
- [ ] T017 [AGENT] Re-evaluate execution strategy after the join point
```

Not supported in v1:

- heading-level inheritance
- section-level inheritance
- block-level inheritance

This keeps parsing stable and reduces false positives.

## Managed `AGENTS.md` Update Model

### Desired Behavior

If a project already has `AGENTS.md`:

- preserve all user-authored content outside the managed block
- insert the managed block if missing
- replace only the managed block body if the block already exists

If a project does not have `AGENTS.md`:

- create it
- write a minimal file plus the managed block

### Why Not Append the Whole File

Whole-file append is the wrong model because it:

- duplicates content over time
- mixes user rules with generated rules
- makes idempotent updates harder
- creates unclear ownership

The managed-block model gives Spec Kit Plus a bounded update surface without taking over the entire file.

### Required Script Changes

The shared `update-agent-context.sh` and `update-agent-context.ps1` scripts should be updated so root-`AGENTS.md` integrations such as Codex, opencode, Amp, Kiro, Bob, Pi, Forge, and Antigravity follow the block model instead of open-ended whole-file mutation.

## Required Action Categories

Only actions that are easy to miss but function as hard gates should receive `[AGENT]` in the first wave.

### Context Loading

- read `PROJECT-HANDBOOK.md`
- read the smallest relevant `.specify/project-map/*.md` files
- read `.specify/memory/constitution.md`
- read `.specify/memory/project-rules.md`
- read `.specify/memory/project-learnings.md`

### Passive Learning Start

- run `specify learning start --command <workflow> --format json`
- inspect relevant `.planning/learnings/candidates.md` entries after start

### State Recovery

- create or resume `workflow-state.md`
- create or resume `implement-tracker.md`
- create or resume quick-task `STATUS.md`
- resume from saved state instead of chat memory when state exists

### Strategy Selection

- run `choose_execution_strategy(...)`
- run review-gate or batch policy checks where required
- re-evaluate strategy at join points when the workflow requires it

### Delegated Execution Gates

- compile `WorkerTaskPacket`
- validate the packet before dispatch
- consume worker handoff or structured result before accepting the join point

## Command Coverage

### `sp-map-codebase`

Must include `[AGENT]` lines for:

- project-map freshness inspection
- refresh vs reuse decision
- reading live files when the map is stale or too broad
- updating `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md`

### `sp-fast`

Must include `[AGENT]` lines for:

- `specify learning start --command fast --format json`
- minimal shared-memory load
- fast-path eligibility check
- brownfield handbook/project-map sufficiency check
- explicit escalation when fast-path is not justified
- post-run learning capture for new pitfalls, recovery paths, or project constraints

`sp-fast` must not become a learning bypass.

### `sp-quick`

Must include `[AGENT]` lines for:

- `specify learning start --command quick --format json`
- `STATUS.md` create or resume
- shared-memory load
- minimal project-map load
- strategy selection and join-point re-evaluation
- explicit fallback recording in `STATUS.md`
- post-run learning capture

`sp-quick` must not skip learning start or capture just because the task is small.

### `sp-specify`

Must include `[AGENT]` lines for:

- learning start
- workflow-state create or resume
- handbook/project-map/shared-memory load
- strategy selection before decomposition

### `sp-plan`

Must include `[AGENT]` lines for:

- learning start
- workflow-state create or resume
- handbook/project-map/shared-memory load
- strategy selection
- explicit preservation of `Implementation Constitution` and `Dispatch Compilation Hints`

### `sp-tasks`

Must include `[AGENT]` lines for:

- learning start
- workflow-state create or resume
- handbook/project-map/shared-memory load
- strategy selection
- `Task Guardrail Index` generation
- explicit parallel batch and join-point generation

### `sp-implement`

Must include `[AGENT]` lines for:

- learning start
- `implement-tracker.md` create or resume
- handbook/project-map/shared-memory load
- strategy selection before each ready batch
- strategy re-evaluation after join points
- packet compilation and validation
- worker handoff/result consumption before join-point acceptance

### `sp-debug`

Must include `[AGENT]` lines for:

- learning start
- debug session state recovery
- handbook/project-map/shared-memory load
- strategy selection
- explicit parallel evidence-lane decision
- blocker-evidence collection before fix-path commitment

## Enforcement Model

Not every required action needs the same failure behavior.

### Class A: Fail-Closed

If a Class A `[AGENT]` action is not completed, the workflow must not continue past the next gate.

Class A includes:

- handbook/project-map load
- passive learning start
- state recovery
- strategy selection
- packet compilation and validation

### Class B: Evidence Required

If a Class B `[AGENT]` action cannot complete, the workflow must leave explicit evidence, a blocker, or a recovery action.

Class B includes:

- candidate-learning inspection
- tracker or status updates
- worker handoff consumption bookkeeping
- post-run learning capture

### Allowed Outcomes

For any `[AGENT]` line, the AI may only:

1. execute it successfully
2. fail with explicit blocker evidence
3. temporarily pause it only because a named prerequisite is being satisfied first

Forbidden outcomes:

- "read but did not apply"
- "skip for now and keep going"
- "treated as background text"

## Template and Parser Changes

### Shared Command Templates

Update `templates/commands/*.md` so hard actions are rendered as `[AGENT]` lines instead of ordinary bullets where appropriate.

### Tasks Template

Update `templates/tasks-template.md` so task and guardrail lines may carry `[AGENT]` without redefining `[P]`.

### Parsing

Any parser or runtime helper that reads actionable lines should treat `[AGENT]` as a standalone token on supported list and task lines. First release behavior can remain conservative: only list-like lines need recognition.

## Rollout Recommendation

Roll out in this order:

1. Define managed-block support for `AGENTS.md` update scripts.
2. Add `[AGENT]` marker guidance to shared documentation and templates.
3. Update first-wave command templates, including `sp-fast`, `sp-quick`, and `sp-map-codebase`.
4. Add runtime enforcement for Class A and Class B required actions.
5. Add tests covering:
   - marker presence in key templates
   - managed-block insertion and update behavior
   - `sp-fast` and `sp-quick` learning lifecycle coverage
   - non-interference with `[P]` semantics

## Risks

### 1. Marker Overuse

If too many lines receive `[AGENT]`, the signal weakens.

Mitigation:

- only mark genuine hard gates
- avoid marking explanatory prose

### 2. Semantic Drift With `[P]`

Users may assume `[AGENT]` implies delegation or parallelism.

Mitigation:

- document the separation explicitly
- add tests proving no parser treats `[AGENT]` as `[P]`

### 3. User File Trust Loss

Poor `AGENTS.md` updates could overwrite user-authored guidance.

Mitigation:

- managed block only
- preserve all content outside the block
- make updates idempotent

## Decision

The approved direction is:

- add a new line-level `[AGENT]` marker for must-execute AI actions
- keep `[AGENT]` completely separate from `[P]`
- adopt a managed-block update model for user `AGENTS.md`
- include `sp-fast`, `sp-quick`, and `sp-map-codebase` in the first-wave rollout
- require `sp-fast` and `sp-quick` to participate in passive learning start and capture
- enforce the highest-risk `[AGENT]` actions with fail-closed runtime behavior
