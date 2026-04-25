# Specify Team Watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen `specify team watch` command that renders a lightly interactive split-stage observer over existing Codex team runtime state.

**Architecture:** Implement the feature in three thin vertical slices: watch snapshot aggregation, watch rendering/controller logic, and CLI integration. Keep the runtime protocol unchanged and build the observer on top of the canonical state files already used by `status`, `doctor`, and `auto-dispatch`.

**Tech Stack:** Python, Typer, Rich Live, readchar, pytest

---

### Task 1: Add watch snapshot aggregation

**Files:**
- Create: `src/specify_cli/codex_team/watch_state.py`
- Create: `tests/codex_team/test_watch_state.py`
- Modify: `src/specify_cli/codex_team/__init__.py`

- [ ] **Step 1: Write the failing aggregation tests**

Add tests for:
- member cards built from worker heartbeat and task ownership
- flow summaries built from tasks, batches, and dispatch records
- stale or missing state producing visible problem markers instead of exceptions

Run:

```powershell
pytest tests/codex_team/test_watch_state.py -q
```

Expected: fail because `watch_state.py` and its public APIs do not exist yet.

- [ ] **Step 2: Implement the minimal snapshot model and readers**

Create `src/specify_cli/codex_team/watch_state.py` with:
- dataclasses for watch snapshot, member summary, flow summary, and freshness problems
- helpers that read canonical state paths
- one public `build_watch_snapshot(project_root, session_id)` entrypoint

- [ ] **Step 3: Re-export the new watch snapshot entrypoint**

Update `src/specify_cli/codex_team/__init__.py` so the watch feature can import the snapshot builder from the package root.

- [ ] **Step 4: Run the aggregation tests again**

Run:

```powershell
pytest tests/codex_team/test_watch_state.py -q
```

Expected: pass with realistic summaries for members, flow, and degraded state.

### Task 2: Add full-screen watch rendering and light interaction

**Files:**
- Create: `src/specify_cli/codex_team/watch_tui.py`
- Create: `tests/codex_team/test_watch_tui.py`

- [ ] **Step 1: Write the failing rendering/controller tests**

Add tests for:
- split view rendering with member stage and flow stage
- focused member highlighting and detail expansion
- view cycling between `split`, `members`, and `flow`
- quitting cleanly when the controller receives `q`

Run:

```powershell
pytest tests/codex_team/test_watch_tui.py -q
```

Expected: fail because `watch_tui.py` and the controller/render helpers do not exist yet.

- [ ] **Step 2: Implement the minimal TUI primitives**

Create `src/specify_cli/codex_team/watch_tui.py` with:
- a small UI-state dataclass
- pure render helpers returning Rich renderables
- a controller that handles key input, refresh, and focus movement
- a `run_team_watch(...)` entrypoint for CLI use

Use the existing `readchar` and `Rich Live` patterns already present in `src/specify_cli/__init__.py` instead of inventing a second terminal interaction style.

- [ ] **Step 3: Re-run the rendering/controller tests**

Run:

```powershell
pytest tests/codex_team/test_watch_tui.py -q
```

Expected: pass with deterministic key-driven state transitions and visible split-stage output.

### Task 3: Expose `specify team watch` on the public CLI surface

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/codex_team/commands.py`
- Modify: `tests/codex_team/test_commands.py`
- Modify: `tests/contract/test_codex_team_cli_surface.py`

- [ ] **Step 1: Write the failing CLI contract tests**

Add failing tests for:
- `specify team watch --help`
- help text mentioning the watch surface
- entering/exiting the watch command with mocked keyboard input

Run:

```powershell
pytest tests/codex_team/test_commands.py tests/contract/test_codex_team_cli_surface.py -q
```

Expected: fail because the public CLI does not expose `team watch` yet.

- [ ] **Step 2: Wire the new command**

Update:
- `src/specify_cli/__init__.py` to add `@team_app.command("watch")`
- `src/specify_cli/codex_team/commands.py` to mention the watch surface in help text

Expose options:
- `--session-id`
- `--refresh-interval`
- `--focus`
- `--view`

- [ ] **Step 3: Run the focused CLI tests**

Run:

```powershell
pytest tests/codex_team/test_watch_state.py tests/codex_team/test_watch_tui.py tests/codex_team/test_commands.py tests/contract/test_codex_team_cli_surface.py -q
```

Expected: pass with the watch command publicly exposed and executable under mocked input.

### Task 4: Final focused verification and doc touch-up

**Files:**
- Modify: `docs/superpowers/specs/2026-04-26-specify-team-watch-design.md`
- Modify: `docs/superpowers/plans/2026-04-26-specify-team-watch-implementation.md`

- [ ] **Step 1: Reconcile the written spec with shipped behavior**

If names, keybindings, or option details changed during implementation, update the spec inline so it matches the code.

- [ ] **Step 2: Add brief implementation notes to the plan**

Record the resolved decisions, especially:
- whether focus defaults to leader or first worker
- how stale/corrupt state is surfaced
- how the watch loop is made testable

- [ ] **Step 3: Run the final focused verification set**

Run:

```powershell
pytest tests/codex_team/test_watch_state.py tests/codex_team/test_watch_tui.py tests/codex_team/test_commands.py tests/contract/test_codex_team_cli_surface.py -q
```

Expected: all watch-focused tests pass.

## Post-Implementation Notes

- The shipped watch loop is Python-native and reuses Rich/terminal patterns already present in `src/specify_cli/__init__.py`.
- Split view is the default, with `members` and `flow` as alternate focused views.
- The watcher is intentionally read-only in v1 even though it is lightly interactive.
- Worktree-wide `codex_team` verification depends on a local `runtime-cli.js` asset that is present in the main workspace but not committed into fresh worktrees; focused watch tests do not rely on that generated artifact.
