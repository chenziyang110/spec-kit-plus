# Inline Project Cognition Closeout Design

**Date:** 2026-05-28
**Status:** Approved direction
**Owner:** Codex

## Summary

This design clarifies the project cognition closeout contract for every
`sp-*` workflow that changes project-related files or behavior.

The expected model is:

- workflows establish or record a baseline before mutation when possible
- workflows know which files and behavior surfaces they changed
- workflows use that knowledge to run a fast, comprehensive inline project
  cognition update during closeout
- `sp-map-update` remains the external maintenance workflow for manual user
  edits, explicit repairs, and follow-up map maintenance
- `project-cognition mark-dirty` is a fallback for failed or impossible inline
  update, not the normal successful closeout path

This is a contract correction, not a new broad workflow. Ordinary `sp-*`
execution should not finish by telling the user to run `sp-map-update` when the
workflow itself just made the relevant changes and has enough evidence to update
project cognition.

## Problem

The repository already contains partial guidance that points in the right
direction. `sp-implement`, `sp-quick`, `sp-fast`, and `sp-debug` mention
recording `project_cognition_refresh` and using map update behavior after
map-relevant changes.

However, the generated guidance still leaves two practical escape hatches:

1. Some shared guidance frames map maintenance as a user-invoked handoff and
   tells workflows not to switch into `sp-map-update` themselves.
2. Some closeout wording is scoped to "map-level coverage facts" or
   "unexpectedly touched" surfaces instead of the simpler user model:
   if this `sp-*` workflow changed project-related code, templates, config,
   tests, generated assets, or project-understanding docs, it owns the update.

This teaches downstream agents to do the wrong thing:

- finish implementation
- mark project cognition dirty
- tell the user or next workflow to run `sp-map-update`

That misses the best available update moment. The workflow that made the change
knows what changed, why it changed, which tests ran, which surfaces moved, and
which uncertainty remains. A later manual map update has less context and costs
more.

## Goals

- Make inline project cognition update a mandatory closeout duty for any
  `sp-*` workflow that modifies project-related files or behavior.
- Preserve `sp-map-update` as an external/manual maintenance entrypoint, not the
  default post-task handoff for workflow-owned changes.
- Prefer a clean git baseline or recorded initial dirty snapshot before
  mutation, so closeout can isolate the workflow's own changes.
- Use changed paths as the entry point for a fast, comprehensive impact closure,
  not as a narrow scope that can omit obvious affected facts.
- Teach agents to update project cognition as knowledgeable executors: they
  must explain what changed, how cognition was updated, what remains
  low-confidence, and which live reads are still useful.
- Reserve `mark-dirty` for inline update failure, unavailable runtime, unsafe
  boundary, interrupted work, failed verification, blocked update, or explicit
  rebuild conditions.
- Align command templates, shared partials, passive skills, integration addenda,
  docs, and regression tests.

## Non-Goals

- Do not require full `sp-map-update` workflow orchestration inside every
  ordinary workflow closeout.
- Do not run `map-scan -> map-build` for ordinary changed-path maintenance when
  a usable baseline exists.
- Do not claim project cognition proves source behavior. Code, tests, scripts,
  config, or authoritative docs remain the proof.
- Do not force commits when git is unavailable or unsafe.
- Do not include unrelated pre-existing dirty user changes in task commits or
  cognition updates.
- Do not weaken partial or low-confidence reporting into false success.

## Design

### 1. Baseline Before Mutation

Before a workflow edits project-related files, it should establish the clearest
available boundary.

Preferred order:

1. A clean working tree with a task-start commit already present.
2. A workflow-created task commit or checkpoint when safe and allowed.
3. A recorded initial dirty snapshot that separates pre-existing changes from
   workflow-owned changes.
4. A delta session or workflow state file that records the starting point when
   git cannot provide one.

The workflow must not overwrite or silently absorb unrelated user changes. If
the worktree starts dirty, closeout must distinguish `initial_dirty_paths` from
`workflow_changed_paths`.

### 2. Change Ledger

Every source-changing `sp-*` workflow should maintain enough change accounting
to update project cognition without relying on final chat memory.

The ledger should capture:

- changed paths, including modified, added, deleted, and renamed files
- affected behavior surfaces, such as commands, APIs, templates, generated
  assets, state files, tests, docs, validators, packets, runtime assumptions,
  and UI or service behavior
- verification evidence
- relevant user decisions or constraints
- subagent results and join-point summaries when delegation occurred
- unresolved uncertainty, known unknowns, or low-confidence facts

For mature runtime support, this should map to the existing delta-session model
from the fast full-fidelity map update design. Prompt-only workflows may start
by recording the same facts in their workflow state or final summary until the
runtime helper is available everywhere.

### 3. Inline Update Contract

Closeout must not treat `/sp-map-update` as a handoff for changes the workflow
itself just made. The workflow should call the lower-level project cognition
update engine directly, using its ledger as input.

The MVP command path must use the runtime surface that already exists today.
Do not plan implementation work around unsupported `project-cognition update`
flags.

When the workflow has a delta session, append the current semantic evidence
before final update:

```text
project-cognition delta append \
  --session <session-id> \
  --event-type workflow_closeout \
  --changed-path <path> ... \
  --behavior-surface <surface> ... \
  --generated-surface <surface> ... \
  --verification "<evidence>" \
  --known-unknown "<unknown>" \
  --format json
```

Then finalize through the existing update command. If a safe task commit range
exists, pass it with the delta session because the current runtime consumes
`--commit-range` only in the delta-session update path:

```text
project-cognition update \
  --delta-session <session-id> \
  --commit-range <base>..<head> \
  --reason workflow-finalize \
  --format json
```

When no delta session is available, the existing fallback command shape is:

```text
project-cognition update \
  --changed-path <path> ... \
  --scope <affected-scope> ... \
  --reason workflow-finalize \
  --format json
```

The CLI may later grow richer flags, but the implementation plan must start
from the supported `delta append`, `update --delta-session`, `update
--changed-path`, `update --scope`, `update --reason`, and `update
--commit-range with --delta-session` contract. If implementation needs
non-delta `update --commit-range`, adding real runtime support for that path is
an explicit implementation task; it must not be assumed from the current flag
parser alone.

The required behavior is stable:

- changed paths and affected surfaces enter the updater
- the updater expands from those changes into the affected project cognition
  closure
- the closure covers owners, consumers, routes, contracts, state surfaces,
  generated surfaces, verification paths, conflicts, known unknowns, and
  dependency impact that are relevant to the change
- ignored paths are accounted for through `.cognitionignore` rules, not written
  into graph evidence
- uncertain closure is recorded as partial, low-confidence, conflict, stale
  claim, known unknown, or minimal-live-read data
- ordinary uncertainty does not become a full rebuild request

The guiding phrase is:

```text
fast comprehensive impact closure from workflow-owned changes
```

It is not "smallest possible update." The update should be efficient because it
starts from known changed paths and workflow evidence, but it must be complete
enough for the actual impact surface. Agents should not keep narrowing the
scope until the update passes while leaving obvious affected cognition facts
stale.

### 4. `sp-map-update` Role

`sp-map-update` remains important, but its role is external maintenance.

Use `sp-map-update` when:

- the user manually changed code outside an active workflow
- a previous workflow was interrupted before closeout
- project cognition was already dirty or stale before the current workflow and
  the user explicitly wants map maintenance
- an inline update recorded partial or dirty state and a follow-up repair is
  needed
- operator review, broader affected-scope handling, or explicit user-supplied
  corrections are needed

Do not use `sp-map-update` as the normal way for `sp-quick`, `sp-fast`,
`sp-implement`, `sp-debug`, or another source-changing `sp-*` workflow to clean
up after its own verified changes.

### 5. Closeout Outcomes

Each source-changing workflow final report or durable summary must include
`project_cognition_refresh`.

Accepted outcome classes:

- `ready`: inline update completed and runtime readiness passed
- `review`: inline update returned an `update_id` and useful update data was
  recorded, but runtime readiness says bounded live review remains useful
- `partial_refresh`: inline update returned an `update_id` and useful update
  data was recorded, but readiness did not pass
- `dirty`: inline update could not be completed now; dirty state records exact
  workflow-owned scope and reason
- `needs_rebuild`: only for missing/unusable baseline, schema failure, zero
  active-generation `path_index` rows, explicit rebuild request, or proven
  baseline identity invalidation

`dirty` must not be used as a convenience shortcut after successful verified
work. It must name the concrete blocker that prevented inline update.

A successful inline update with a persisted update record but non-ready
readiness is not dirty. It maps to `review` or `partial_refresh` according to
the runtime result. Use `dirty` only when the inline update command is
unavailable, fails before recording useful update data, cannot safely determine
the workflow-owned boundary, is blocked by runtime state, or must fall back
because verification or workflow completion is not trustworthy.

### 6. Agent Responsibilities

The executing agent must behave as the person who best understands the change.
It should not act like an external map maintainer with no context.

At closeout, the agent must be able to say:

- what it changed
- why those changes affect project cognition
- which changed paths and surfaces were sent to the inline updater
- which cognition facts were updated, added, downgraded, or marked uncertain
- which facts remain low-confidence
- which minimal live reads remain useful for a later workflow
- why `mark-dirty` was necessary, if it was used

If the workflow cannot answer those questions, it should record the gap and keep
the update partial rather than claiming the runtime is fresh.

## Required Surface Changes

Implementation should update these surfaces together:

- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/planning-context-loading-gradient.md`
- `templates/command-partials/common/senior-consequence-analysis-gate.md`
- `templates/command-partials/common/navigation-check.md`
- `templates/command-partials/fast/shell.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- source-changing workflow templates, especially `fast`, `quick`,
  `implement`, and `debug`
- `templates/commands/constitution.md`
- `templates/project-handbook-template.md`
- `templates/constitution-template.md`
- artifact-oriented workflow templates where project-related mutation can occur,
  so they clarify that artifact-only work is exempt but source/runtime/template
  mutation is not
- integration addenda in `src/specify_cli/integrations/base.py`
- generated Codex skill surfaces that mirror the shared contract
- README and handbook sections that describe `sp-map-update` and project
  cognition maintenance
- regression tests that currently assert only "refresh or dirty" instead of the
  stricter "inline update first, dirty only on failure" model

The conflicting instruction that map maintenance is always a user-invoked
handoff must be replaced with:

```text
External map maintenance is user-invoked. Workflow-owned mutation closeout is
not external map maintenance; it must run inline project cognition update.
```

Entry-time stale or weak cognition is still an advisory navigation concern
unless the user explicitly requested map maintenance. A workflow may continue
from live evidence when entry guidance allows it. That entry routing rule does
not waive closeout ownership: once the workflow itself changes project-related
files or behavior, it must run inline update for its own changes.

## Testing Strategy

Template and integration tests should assert:

- source-changing workflows require inline project cognition update before
  successful completion
- `project-cognition mark-dirty` is described as fallback-only
- generated passive skills no longer tell workflows to avoid inline map update
  for their own changes
- `sp-map-update` is documented as external/manual maintenance, not routine
  workflow cleanup
- artifact-only `sp-specify`, `sp-clarify`, `sp-plan`, and `sp-tasks` remain
  exempt when they only write planning artifacts
- those same artifact-oriented workflows require inline update if they modify
  project-related source, runtime, templates, config, tests, or generated assets
- `map-scan -> map-build` remains reserved for explicit rebuild conditions

Runtime tests, where the lower-level helper is implemented or adjusted, should
cover:

- clean git baseline update
- initially dirty worktree with unrelated paths excluded
- working-tree diff fallback
- delta-session update
- partial update with known unknowns
- blocked update falling back to dirty state with exact changed paths
- ignored paths excluded from graph evidence

## Rollout

1. Update shared wording so generated agents learn the correct mental model.
2. Update workflow templates and passive skills.
3. Update integration rendering addenda and generated Codex skill mirrors.
4. Add template regression tests for the stricter closeout contract.
5. If needed, extend the project cognition runtime CLI so workflow closeout can
   pass origin command, changed paths, affected surfaces, verification evidence,
   and delta-session data directly.
6. Update README and handbook guidance.

## Open Decisions

- Whether the first implementation pass should only harden prompts and tests or
  also extend the runtime CLI shape for affected surfaces and verification
  evidence.
- Whether auto-commit should be default-on for every source-changing workflow or
  remain a best-effort option gated by workflow and repo safety.
- Whether artifact-generated files under `.specify/` count as project-related
  mutation for inline update by default or only when they change future runtime
  or workflow behavior.
