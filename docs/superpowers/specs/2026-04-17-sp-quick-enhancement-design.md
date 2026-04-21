# sp-quick Enhancement Design

**Date:** 2026-04-17
**Status:** Proposed
**Owner:** Codex

## Summary

This design enhances `sp-quick` by folding in the strongest workflow ideas from GSD quick mode without importing GSD's heavier runtime model.

The approved direction is to keep `sp-quick` as a lightweight, bounded execution path for small but non-trivial tasks while adding three missing capabilities:

- resumable quick-task execution through empty `sp-quick` invocation
- stable quick-task identity and management via `specify quick` subcommands
- lightweight project-level indexing for reliable list, status, close, and archive flows

The design does not turn `sp-quick` into a second full orchestration system. It keeps the current lightweight planning and validation positioning, preserves `STATUS.md` as the per-task source of truth, and avoids bringing in default branch isolation, worktrees, or a project-wide `STATE.md` ledger.

## Problem Statement

`sp-quick` already covers the core discipline for small ad-hoc work:

- scope gating between `sp-fast`, `sp-quick`, and `sp-specify`
- quick-task workspaces under `.planning/quick/`
- resumable state through `STATUS.md`
- optional `--discuss`, `--research`, `--validate`, and `--full`
- execution strategy language aligned with the broader collaboration model
- explicit completion and validation guardrails

However, it still has practical gaps compared with the best parts of GSD quick mode:

1. Quick tasks do not have a stable identifier beyond a slugged directory name.
2. There is no repository-level quick management surface such as `list`, `status`, `resume`, `close`, or `archive`.
3. Resuming quick work depends too much on explicit prompt phrasing instead of a simple "continue unfinished work" behavior.
4. There is no lightweight index that lets tooling manage quick tasks without repeatedly inferring state from directory scans alone.
5. The lifecycle of a quick task and the storage or archival of that task are not explicitly separated.

These gaps make `sp-quick` harder to resume, inspect, and manage than it should be, especially when multiple quick tasks exist or when a blocked quick task should be recovered later.

## Goals

- Keep `sp-quick` lightweight and bounded.
- Add a stable quick-task identity model based on `<id>-<slug>`.
- Make empty `sp-quick` invocation a first-class recovery path for unfinished quick tasks.
- Add a `specify quick` management surface for quick-task inspection and lifecycle operations.
- Preserve `STATUS.md` as the per-task source of truth.
- Add a lightweight derived index for fast and consistent management operations.
- Keep `blocked` quick tasks resumable.
- Separate lifecycle closure from archival storage.
- Keep the enhancement shared by default rather than Codex-only.

## Non-Goals

- Do not import GSD's full planner/executor/verifier orchestration model into `sp-quick`.
- Do not make quick tasks depend on a project-wide `STATE.md` ledger.
- Do not default quick tasks onto dedicated git branches.
- Do not enable worktree isolation in the first implementation slice.
- Do not support legacy `.planning/quick/<slug>/` directories in the new model.
- Do not make `specify quick resume` the primary execution entrypoint. The primary recovery entrypoint remains `sp-quick`.

## User-Approved Decisions

The design reflects the following explicit choices made during design review:

1. The enhancement should cover both the `sp-quick` workflow itself and a `specify`-level quick management surface.
2. `close` and `archive` should be separate actions.
3. Quick-task directories should move from `.planning/quick/<slug>/` to `.planning/quick/<id>-<slug>/`.
4. Legacy slug-only quick directories are not supported in the new design.
5. A lightweight project-level index should exist, but it should be machine-friendly and lighter than a GSD-style `STATE.md`.
6. The index should be `index.json`, not `INDEX.md`.
7. Quick tasks should continue to run on the current branch by default.
8. Empty `sp-quick` invocation should continue unfinished quick work automatically when possible.
9. If multiple unfinished quick tasks exist, the runtime should ask the user which one to continue rather than requiring a resume flag.
10. When the user is choosing between multiple unfinished quick tasks, the selection list should show `id`, title, current status, and `next_action`.
11. `blocked` quick tasks should still count as resumable unfinished work.
12. `specify quick list` should default to showing unfinished quick tasks rather than historical completed ones.

## Architecture Overview

The enhanced quick model has three layers.

### 1. Execution Entry Layer

This is the `sp-quick` workflow surface used by the AI agent.

It is responsible for:

- scope gating
- new quick-task creation
- automatic unfinished-task recovery on empty invocation
- asking the user to choose among multiple unfinished quick tasks
- continuing execution using the existing lightweight planning and validation flow

### 2. Quick-Task State Layer

This layer stores the durable quick-task artifacts under `.planning/quick/`.

It is responsible for:

- per-task directories named `<id>-<slug>`
- `STATUS.md` as the per-task source of truth
- `SUMMARY.md` and optional support artifacts
- archive placement for closed quick tasks

### 3. Quick Management Layer

This is the new `specify quick` CLI surface.

It is responsible for:

- listing unfinished or archived quick tasks
- reporting quick-task status
- offering an explicit resume helper path
- closing quick tasks into a terminal lifecycle state
- archiving closed quick tasks

This layer should rely on `STATUS.md` plus a derived index rather than inventing an independent truth model.

## Directory and Identity Model

All new quick tasks use this directory shape:

- `.planning/quick/<id>-<slug>/`

Examples:

- `.planning/quick/260417-001-fix-quick-index-sync/`
- `.planning/quick/260417-002-align-cursor-quick-docs/`

The quick-task id should be short, readable, and sortable. A date-prefixed sequential identifier is preferred over opaque UUIDs.

The old slug-only shape:

- `.planning/quick/<slug>/`

is intentionally not supported by this design. The implementation should treat `<id>-<slug>` as the canonical and only supported workspace format for the enhanced quick flow.

## Source of Truth and Indexing

The state model is intentionally split into source and projection.

### Source of Truth

For each quick task:

- `STATUS.md` is the canonical task state
- `SUMMARY.md` is the canonical completion summary

`STATUS.md` remains the only per-task file that directly defines:

- lifecycle status
- current focus
- next action
- blocker reason
- recovery action
- execution strategy
- summary pointer

### Derived Index

The repository also maintains:

- `.planning/quick/index.json`

This file is a derived index used for:

- `specify quick list`
- `specify quick status`
- `specify quick resume`
- `specify quick close`
- `specify quick archive`
- empty `sp-quick` recovery routing

The index is not the primary truth source. If it becomes stale or missing, it should be rebuildable from the canonical quick directories and their `STATUS.md` files.

## Lifecycle Model

The quick-task lifecycle states are:

- `gathering`
- `planned`
- `executing`
- `validating`
- `blocked`
- `resolved`

There are only two terminal lifecycle states:

- `blocked`
- `resolved`

This means `blocked` remains terminal from a status perspective but still counts as resumable unfinished work for recovery purposes.

That distinction is deliberate:

- `blocked` means the previous pass could not proceed safely
- `blocked` does not mean the quick task is gone or abandoned forever
- a later pass can recover from the blocker and continue from the recorded `recovery_action` or `next_action`

## Close vs Archive

`close` and `archive` are intentionally different actions.

### Close

`close` controls lifecycle semantics.

It marks a quick task as being in one of the terminal lifecycle outcomes:

- `resolved`
- `blocked`

It does not move the directory.

### Archive

`archive` controls storage semantics.

It moves an already closed quick task out of the active queue and into an archive location under `.planning/quick/`.

`archive` does not redefine the lifecycle state. It preserves whatever terminal state the quick task already has.

This separation keeps task meaning clear:

- closure says what happened
- archival says where the finished record is stored

## Empty `sp-quick` Recovery Behavior

The primary recovery flow should be empty `sp-quick` invocation rather than requiring a separate explicit resume command.

### New Task Creation

- `sp-quick <description>` creates a new quick task.

### Automatic Recovery

- `sp-quick` with no description checks for unfinished quick tasks.

If exactly one unfinished quick task exists:

- resume it automatically

If multiple unfinished quick tasks exist:

- ask the user which quick task to continue
- show `id`, title, current status, and `next_action`

If no unfinished quick tasks exist:

- ask for a new task description or fail with the standard missing-description guidance, depending on the host integration's interaction affordances

### Unfinished Set

For recovery routing, unfinished quick tasks are:

- `gathering`
- `planned`
- `executing`
- `validating`
- `blocked`

`resolved` quick tasks are never auto-resumed by empty invocation.

### Blocked Recovery

If a `blocked` quick task is resumed, the recovery logic should read and prioritize:

- `blocker_reason`
- `recovery_action`
- `next_action`

The resumed pass should attempt the smallest safe recovery path first rather than treating the task as brand-new work.

## `specify quick` CLI Surface

The first implementation slice should add:

- `specify quick list`
- `specify quick status <id>`
- `specify quick resume <id>`
- `specify quick close <id> --status resolved|blocked`
- `specify quick archive <id>`

### `specify quick list`

Default behavior:

- show unfinished quick tasks only

Future-friendly but non-blocking extensions may later include:

- `--all`
- `--resolved`
- `--archived`

### `specify quick status <id>`

Shows a compact view of:

- title or trigger
- current status
- current focus
- next action
- directory path
- archive status if relevant

### `specify quick resume <id>`

This is an explicit recovery helper, not the primary recovery route.

It should:

- resolve the target quick task
- print or prepare the current recovery context
- align with the same state model used by empty `sp-quick`

It should not replace `sp-quick` as the normal continuation surface.

### `specify quick close <id> --status resolved|blocked`

This command explicitly moves a quick task into a terminal lifecycle state.

It should reject non-terminal target values and keep the state model unambiguous.

### `specify quick archive <id>`

This command archives a quick task only after it is already closed.

It should reject attempts to archive active non-terminal quick tasks.

## Interaction Model

When multiple unfinished quick tasks exist and the user invokes empty `sp-quick`, the runtime should ask which task to continue.

The selection list should show:

- `id`
- title
- current status
- `next_action`

The design intentionally avoids forcing users to memorize or type resume flags in the most common continuation path.

## Workflow Positioning

The enhancement should preserve the current routing guidance:

- `sp-fast` for trivial, obvious, highly local work
- `sp-quick` for small but non-trivial bounded work
- `sp-specify` for work that needs durable feature planning and acceptance alignment

The enhanced quick model should remain a lightweight path, not a replacement for the full `specify -> plan -> tasks -> implement` workflow.

## GSD Concepts to Absorb

The design should absorb these ideas from GSD quick mode:

- stable quick-task ids
- repository-level quick management commands
- derived quick indexing for tooling
- explicit distinction between lifecycle closure and archival
- strong unfinished-task recovery ergonomics

## GSD Concepts Not Adopted

The design intentionally leaves out these GSD quick ideas for the first slice:

- default quick-branch creation
- worktree isolation
- project-wide `STATE.md` integration
- mandatory planner/executor/verifier orchestration
- heavier runtime-specific execution contracts

This keeps `sp-quick` aligned with the repository's lighter-weight quick-task positioning.

## Implementation Strategy

The recommended implementation sequence is:

1. Update the shared `templates/commands/quick.md` guidance and quick-task workspace protocol.
2. Add `specify quick` management commands in the CLI.
3. Add script support for quick-task indexing and lookup in both Bash and PowerShell.
4. Update documentation and tests to reflect the new quick-task identity and management model.

## Expected Code Surfaces

The main repository surfaces likely to change are:

- `templates/commands/quick.md`
- `src/specify_cli/__init__.py`
- `scripts/bash/*` quick-task helper surfaces
- `scripts/powershell/*` quick-task helper surfaces
- quick-related test files under `tests/`
- `README.md`
- `docs/quickstart.md`

Codex- or integration-specific quick augmentations should remain minimal and should inherit the shared behavior rather than inventing their own divergent quick model.

## Risks

### 1. Test Churn Risk

Existing tests assert the old slug-only quick path shape and will need coordinated updates.

### 2. Dual-Write Drift Risk

`STATUS.md` and `index.json` must have a clearly defined source/projection relationship to avoid contradictory state.

### 3. Resume Ambiguity Risk

Empty `sp-quick` invocation changes the previous no-argument behavior. The UX and error handling need to be made explicit so users understand whether the system is resuming work or asking for a new description.

### 4. Archive Semantics Risk

If archive rules are underspecified, users may try to archive active tasks or assume archive implies resolution. The CLI must reject those ambiguous transitions.

## Recommended Delivery Cut

The first implementation cut should ship the full balanced enhancement:

- `<id>-<slug>` quick-task directories
- `STATUS.md` plus `index.json`
- empty `sp-quick` automatic recovery behavior
- `specify quick list|status|resume|close|archive`
- documentation and regression coverage updates

This is intentionally broader than a template-only tweak, but still much lighter than importing the full GSD quick runtime.

## Decision

Proceed with the balanced enhancement model.

`sp-quick` should absorb GSD quick's best management and recovery ideas while staying lightweight:

- resumable by empty invocation
- identifiable by stable quick-task ids
- manageable through `specify quick`
- indexed through a derived `index.json`
- explicit about the difference between closure and archival

The design should remain shared-first, low-friction, and clearly smaller in scope than a full orchestration runtime.
