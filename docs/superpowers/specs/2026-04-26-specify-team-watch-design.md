# Specify Team Watch Design

**Date:** 2026-04-26  
**Status:** Implemented  
**Owner:** Codex

## Summary

This design adds a first-class `specify team watch` command: a full-screen terminal observer for Codex teams.

The current product surface exposes textual diagnostics such as `status`, `doctor`, and `live-probe`, but it does not provide a continuously refreshing, operator-friendly watch surface. At the same time, the repository still contains lower-level HUD and runtime monitoring artifacts. The design intentionally does **not** revive that old pane injection chain as the product surface.

Instead, the first release ships a Python-native watch surface built on top of the existing `specify_cli.codex_team` state model.

## Problem

Today, operators can inspect team state, but they cannot comfortably **watch** it.

The current gaps are:

- `specify team status` is a snapshot, not a live board
- runtime information exists, but it is fragmented across tasks, dispatch records, batches, heartbeats, and diagnostics
- there is no high-quality terminal UI for tracking who is active, what flow is moving, and where the current bottlenecks are

The user goal is explicit:

- terminal-native
- full-screen
- visually strong, not bland
- lightly interactive
- centered on both members and task flow

## Goals

- Add a public `specify team watch` command
- Render a full-screen Rich TUI that refreshes continuously
- Make the default layout a split view that treats both **members** and **flow** as first-class
- Support light interaction:
  - focus cycling
  - view switching
  - detail expansion
  - refresh
  - quit
- Aggregate existing runtime state without changing the runtime contract
- Make stale, missing, or corrupt state visible instead of crashing the UI

## Non-Goals

- Do not add dispatch/retry/shutdown/result submission actions inside the watch UI in v1
- Do not embed tmux panes directly
- Do not restore or expose the vendored engine HUD as the product surface
- Do not ship a browser dashboard in the same milestone
- Do not add historical replay or timeline scrubbing in v1

## Product Surface

The new surface is:

```text
specify team watch
```

Supported options in v1:

- `--session-id`
- `--refresh-interval`
- `--focus`
- `--view members|flow|split`

Default behavior:

- start in `split` view
- auto-refresh every 1 second
- enter a full-screen terminal session
- quit with `q`

## Interaction Model

The approved interaction model is a **lightly interactive observer**, not a command console.

Core interactions:

- `Tab` / `Shift-Tab` or arrow keys to move focus
- `Enter` to expand the focused member or focused flow detail
- `f` to cycle views (`split`, `members`, `flow`)
- `r` to force refresh
- `q` to quit

The interaction contract is intentionally shallow: the operator can change perspective and level of detail, but not mutate runtime state.

## Layout Direction

The approved visual direction is:

- cinematic
- terminal-native
- split-stage deck

The default layout is a **Split-Stage Deck**:

- left side: **Member Stage**
- right side: **Flow Stage**

### Member Stage

Shows leader and workers as first-class cards.

Each card should present:

- member name
- current state
- current or last known task
- recent activity age
- small summary metrics

The focused card gets the strongest visual treatment.

### Flow Stage

Shows the moving task system rather than raw logs.

It should surface:

- task status distribution
- active and blocked work
- recent batch activity
- review or join-point pressure
- notable dispatch failures when relevant

### Detail Expansion

When a focused member or flow section is expanded, the board keeps its main structure but reveals denser detail for the selected entity instead of switching to a completely different application mode.

## Data Model Strategy

The design uses a new Python-side watch aggregation layer.

It reads from existing state surfaces:

- runtime session state
- task records
- dispatch records
- batch records
- worker identities and heartbeats
- doctor/live-probe derived diagnostics when useful

This aggregation layer should build a single in-memory watch snapshot for the renderer.

It does **not** require:

- new runtime protocol messages
- new tmux HUD primitives
- engine-side product wiring

## Refresh Model

The watch loop should:

1. poll the runtime state files
2. build a normalized watch snapshot
3. render the snapshot through Rich Live
4. preserve local UI state such as focus, expanded entity, and current view

Default refresh cadence:

- `1.0s`

Error handling requirements:

- if a source file is missing, mark that section as missing
- if a source file is corrupt, mark that section as corrupt
- if a source file is stale, mark that section as stale
- do not crash the whole watch session because one data source is bad

## Architecture

The feature should be split into three responsibilities.

### 1. Watch Snapshot Aggregation

Responsible for:

- reading runtime state
- computing member summaries
- computing flow summaries
- computing freshness/problem annotations

### 2. Watch Rendering and Input

Responsible for:

- Rich renderables
- full-screen layout composition
- focus and expansion state
- keyboard handling

### 3. CLI Integration

Responsible for:

- adding `specify team watch`
- parsing command options
- bootstrapping the watch controller
- documenting the new surface in help text

## Testing Strategy

The implementation should be test-first and split into three test layers.

### Aggregation tests

Verify that watch snapshots correctly summarize:

- members
- tasks
- batches
- dispatch failures
- freshness problems

### Rendering tests

Verify that the rendered view exposes:

- split layout semantics
- focused member visibility
- detail expansion
- stale/corrupt/missing markers

These tests should assert meaningful text/structure, not brittle full-screen snapshots.

### CLI contract tests

Verify:

- `specify team watch` is publicly exposed
- help text includes the command/options
- the command can enter and exit cleanly when keyboard input is mocked

## Risks

### Risk 1: The board becomes pretty but uninformative

Mitigation:

- keep members and flow equally prominent
- test on realistic state combinations, not only ideal cases

### Risk 2: Terminal interaction becomes fragile

Mitigation:

- keep input model simple
- centralize key handling
- add a deterministic test path with mocked key reads

### Risk 3: Aggregation logic drifts away from runtime truth

Mitigation:

- build on existing canonical state files
- avoid duplicating business rules from the engine when a direct state read is sufficient

## Decision

Ship `specify team watch` as a Python-native, full-screen Rich observer using a split-stage cinematic layout, backed by a new watch aggregation layer over existing `codex_team` state files.

## Implementation Resolution

The implementation shipped with these concrete resolutions:

- the public CLI surface is `specify team watch`
- the default view is `split`
- focus can be seeded with `--focus`
- the loop uses a Python-side polling reader instead of reviving the vendored tmux HUD chain
- the renderer surfaces state problems through a dedicated warning panel instead of crashing when a state file is missing or stale
