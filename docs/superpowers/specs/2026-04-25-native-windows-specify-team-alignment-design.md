# Native Windows Specify Team Alignment Design

**Date:** 2026-04-25
**Status:** Proposed
**Owner:** Codex

## Summary

This design defines the first high-quality alignment milestone for bringing `spec-kit-plus` closer to the durable team-runtime effect of `oh-my-codex` without copying OMX wholesale.

The approved direction is:

- treat `native Windows + psmux` as the only supported Windows team-runtime path in the first release
- stop treating `WSL + tmux + Windows Codex` as a supported execution shape
- promote `specify team` to the real execution backend for `sp-implement-teams`
- demote `tasks.md` from runtime truth to planning input only
- generate canonical runtime tasks from implementation state instead of dispatching directly from `tasks.md`
- fix native Windows runtime binary discovery and build checks so `omx-runtime.exe` is treated as a first-class artifact

This is a runtime-contract correction, not a cosmetic integration tweak.

## Problem Statement

`spec-kit-plus` currently has two conflicting stories for Codex durable execution.

The documented product surface says the Codex runtime lives under `specify team` and `.specify/codex-team/`, with explicit runtime state, status, resume, shutdown, cleanup, and API operations.

At the same time, `sp-implement-teams` still routes implementation through the bundled `agent-teams` extension and its `bridge.js` flow, which:

- requires `tasks.md` as the dispatch source
- derives a ledger from Markdown instead of canonical runtime state
- depends on a tmux leader-pane contract that is hostile to split Windows/WSL setups
- does not understand the real implementation recovery point when tracker state has moved ahead of `tasks.md`

This creates three concrete failures:

1. runtime surface drift: `specify team` is the official surface, but `sp-implement-teams` does not actually use it as the primary execution path
2. task-source drift: implementation recovery truth may live in tracker and phase artifacts, while the bridge only reads `tasks.md`
3. Windows runtime drift: the repository advertises Windows support through `psmux`, but the execution path still behaves like a tmux-first Unix port with incomplete native binary handling

The result is that `sp-implement-teams` does not deliver the durable, recoverable, single-environment team behavior the repository intends to provide.

## Goals

- Make native Windows a first-class, single-environment Codex runtime path.
- Standardize Windows runtime execution on `psmux`.
- Make `specify team` the real backend for `sp-implement-teams`.
- Treat `.specify/codex-team/` as the single source of truth for runtime state.
- Stop direct runtime dispatch from `tasks.md`.
- Introduce a state-first batch materialization layer that can recover the intended execution batch from implementation state.
- Fix native Windows runtime binary detection for `.exe` artifacts.
- Add regression coverage for Windows runtime detection, startup, and recovery behavior.

## Non-Goals

- Do not support `WSL bridge` or mixed Windows/WSL team execution in the first release.
- Do not preserve `bridge.js` as the primary implementation dispatch path.
- Do not attempt full OMX parity across every mailbox, hook, or operator UX feature in this milestone.
- Do not redesign the full Spec Kit planning workflow.
- Do not rewrite historical feature specs, trackers, or plans outside the minimum state-materialization contract needed for runtime execution.

## User-Approved Decisions

This design reflects the following explicit decisions from review:

1. The target is behavioral parity with OMX-style runtime outcomes, not a small bridge patch.
2. The first Windows release should be native-only, not WSL-assisted.
3. `native Windows + psmux` is the accepted Windows runtime contract for the first release.
4. `specify team` should become the execution backend rather than leaving `sp-implement-teams` on extension plumbing.
5. `tasks.md` should no longer be the runtime dispatch truth.
6. The first milestone should stay focused on startup, recovery, task materialization, and Windows-native correctness rather than broad OMX feature cloning.

## Architecture Overview

The design has four layers.

### 1. Native Windows Runtime Contract

The first release should define one explicit Windows runtime contract:

- leader and workers run in native Windows
- tmux-compatible backend is `psmux`
- `codex`, `node`, `npm`, `cargo`, and `git` must be discoverable from the same native shell
- runtime startup must fail clearly if this single-environment contract is not satisfied

This replaces the accidental expectation that users can stitch together Windows PowerShell tooling with WSL tmux and still receive a supported team runtime.

### 2. Product-Surface Routing

`sp-implement-teams` should stop teaching or depending on the extension bridge as its execution backend.

Instead, the workflow should:

- validate the Codex runtime environment
- validate that the current project is eligible for runtime-managed implementation
- materialize a runtime batch from implementation state
- invoke the official `specify team` lifecycle and API surfaces

The extension and vendored engine may still exist as implementation dependencies or compatibility assets, but they should no longer define the primary workflow contract.

### 3. State-First Batch Materialization

A new batch-materialization layer should convert implementation recovery state into canonical runtime tasks.

The source of truth should be ordered like this:

1. explicit active implementation tracker state
2. phase-specific refactor or execution plan artifacts
3. `tasks.md` only when the first two sources do not provide a more current recovery point

This layer should produce:

- runtime task records
- batch metadata
- join-point metadata
- dispatchable worker packets or equivalent runtime-managed payloads

The runtime should never need to infer current implementation reality by scraping an out-of-date `tasks.md` ledger when newer tracker state exists.

### 4. Native Binary and Bootstrap Correctness

Windows runtime bootstrap must treat the built Rust binary as a real Windows executable.

That means:

- build scripts must accept `target/release/omx-runtime.exe`
- runtime bridge discovery must accept both bare and `.exe` forms where appropriate
- environment checks must explain the native Windows path in terms of `psmux`, not generic Unix tmux wording
- startup and recovery tests must verify the Windows-native branch explicitly

Without this, the repository can detect `psmux` but still fail during the actual runtime bootstrap path.

## Runtime Data Flow

The desired execution path is:

1. User invokes `sp-implement-teams` in a Codex project.
2. The workflow validates native Windows runtime readiness through the `specify team` environment checks.
3. The workflow reads canonical implementation recovery state and selects the active execution batch.
4. The workflow materializes canonical runtime task and batch records under `.specify/codex-team/`.
5. `specify team` bootstraps the runtime session and worker topology using the native Windows `psmux` backend.
6. Workers receive runtime-managed assignments from canonical state rather than direct `tasks.md` parsing.
7. Status, resume, await, shutdown, and cleanup all operate against the same `.specify/codex-team/` state.

## Error Handling

The first release must explicitly handle:

- `psmux` missing on native Windows
- required CLI tooling missing from the same native shell
- runtime binary built as `.exe` but not discovered
- stale `tasks.md` when tracker or phase plan reflects a later recovery point
- runtime session already active
- invalid or missing active implementation batch
- resume requests after interrupted startup

Each case should produce:

- a machine-readable runtime or workflow status
- a clear operator-facing message
- an explicit next-step recommendation

## Testing Strategy

The milestone should add or extend regression coverage for:

- native Windows backend detection preferring `psmux`
- native Windows readiness messages and next steps
- runtime binary discovery accepting `.exe`
- build-script logic that should skip rebuild when `.exe` already exists
- `sp-implement-teams` routing through the official runtime surface instead of the legacy bridge path
- state-first batch materialization preferring tracker or phase-plan state over stale `tasks.md`
- resume behavior when canonical runtime state already exists

## Delivery Plan

The implementation should ship in four ordered slices:

1. Native Windows contract hardening
   - fix binary detection and build checks
   - tighten readiness diagnostics around `psmux` and same-shell tool discovery
2. Workflow rerouting
   - rewire `sp-implement-teams` so the official runtime surface is the execution backend
3. State-first materialization
   - add the implementation batch selection and runtime-task generation layer
4. Verification and release hardening
   - expand tests and documentation for the native Windows runtime path

## Open Decisions Resolved

- Windows-first support in this milestone means native Windows only.
- `psmux` is the only accepted Windows tmux-compatible backend for the first release.
- `specify team` remains the official product surface and must become the real backend for team execution workflows.
- `tasks.md` remains useful planning input, but it is no longer the canonical runtime dispatch source.
- The first milestone optimizes for correctness, recovery, and operator trust rather than breadth of OMX feature parity.
