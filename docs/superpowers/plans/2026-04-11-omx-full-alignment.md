# OMX Full Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `spec-kit-plus` from a lightweight Codex team surface to a fully aligned OMX-style team/runtime system behind the `specify team` product contract.

**Architecture:** Keep the Python `specify` CLI as the official product interface, but replace the current smoke-level Codex team helpers with a real team runtime, worker/session lifecycle layer, JSON API surface, and Codex routing guidance. Deliver the system in five staged slices so each slice adds working, testable runtime behavior without leaking Codex-only surfaces to other integrations.

**Tech Stack:** Python 3.11+, Typer CLI, JSON file-backed runtime state, tmux-compatible backends, pytest

---

### Task 1: Runtime core state model and filesystem contract

**Files:**
- Create: `src/specify_cli/codex_team/runtime_state.py`
- Create: `src/specify_cli/codex_team/events.py`
- Modify: `src/specify_cli/codex_team/state_paths.py`
- Modify: `src/specify_cli/codex_team/manifests.py`
- Create: `tests/codex_team/test_runtime_state.py`
- Create: `tests/codex_team/test_events.py`

- [ ] **Step 1: Write failing tests for runtime state paths and canonical records**

Add tests covering:
- canonical state root under `.specify/codex-team/state/`
- task, worker, mailbox, dispatch, phase, event, and shutdown file locations
- stable JSON record schemas for team config, task records, task claims, worker identity, worker heartbeat, and monitor snapshot

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_runtime_state.py tests/codex_team/test_events.py -q
```

Expected: failures for missing modules/functions and incomplete state contract helpers.

- [ ] **Step 3: Implement the runtime state module**

Create file-backed helpers that:
- define typed runtime record builders/parsers
- read and write JSON atomically
- normalize timestamps and schema-version fields
- append events in an append-only log

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_runtime_state.py tests/codex_team/test_events.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/runtime_state.py src/specify_cli/codex_team/events.py src/specify_cli/codex_team/state_paths.py src/specify_cli/codex_team/manifests.py tests/codex_team/test_runtime_state.py tests/codex_team/test_events.py
git commit -m "feat: add codex team runtime state core"
```

### Task 2: Task lifecycle, claims, approvals, and join-point primitives

**Files:**
- Create: `src/specify_cli/codex_team/task_ops.py`
- Create: `tests/codex_team/test_task_ops.py`
- Modify: `src/specify_cli/codex_team/runtime_state.py`
- Modify: `src/specify_cli/codex_team/events.py`

- [ ] **Step 1: Write failing tests for task creation, claiming, transitions, and approvals**

Add tests covering:
- create/read/list/update task metadata
- claim-token generation and expected-version checks
- claim conflict rejection
- allowed transitions `pending -> in_progress -> completed|failed`
- task approval records and join-point gating markers

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_task_ops.py -q
```

Expected: FAIL because task lifecycle operations do not exist yet.

- [ ] **Step 3: Implement the task operation layer**

Implement functions that:
- create and persist task records
- issue and validate task claims
- transition task status with version and owner checks
- record approvals/rejections and append corresponding events
- expose read/list helpers for CLI and workflow use

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_task_ops.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/task_ops.py src/specify_cli/codex_team/runtime_state.py src/specify_cli/codex_team/events.py tests/codex_team/test_task_ops.py
git commit -m "feat: add codex team task lifecycle primitives"
```

### Task 3: Worker identity, heartbeat, mailbox, and dispatch primitives

**Files:**
- Create: `src/specify_cli/codex_team/worker_ops.py`
- Create: `src/specify_cli/codex_team/mailbox_ops.py`
- Create: `tests/codex_team/test_worker_ops.py`
- Create: `tests/codex_team/test_mailbox_ops.py`

- [ ] **Step 1: Write failing tests for worker identity and mailbox flow**

Add tests covering:
- worker identity bootstrap
- heartbeat read/write
- status snapshots
- direct message send
- broadcast fanout
- mailbox list
- mailbox mark-notified and mark-delivered

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_worker_ops.py tests/codex_team/test_mailbox_ops.py -q
```

Expected: FAIL because worker/mailbox ops are not implemented.

- [ ] **Step 3: Implement the worker and mailbox layers**

Implement operations that:
- persist worker identities and heartbeats
- compute basic worker status
- enqueue direct and broadcast mailbox messages
- list and mutate mailbox delivery state
- append lifecycle events for worker and mailbox changes

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_worker_ops.py tests/codex_team/test_mailbox_ops.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/worker_ops.py src/specify_cli/codex_team/mailbox_ops.py tests/codex_team/test_worker_ops.py tests/codex_team/test_mailbox_ops.py
git commit -m "feat: add codex team worker and mailbox primitives"
```

### Task 4: Session bootstrap, shutdown, cleanup, and runtime monitor

**Files:**
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Create: `src/specify_cli/codex_team/session_ops.py`
- Create: `tests/codex_team/test_session_ops.py`
- Modify: `tests/codex_team/test_tmux_smoke.py`

- [ ] **Step 1: Write failing tests for session lifecycle**

Add tests covering:
- team bootstrap writes config, phase, worker seed data, and monitor snapshot
- duplicate active team-name rejection
- shutdown request and acknowledgement flow
- cleanup after terminal states
- monitor summary reflects task and worker state

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_session_ops.py tests/codex_team/test_tmux_smoke.py -q
```

Expected: FAIL because the current runtime bridge only supports smoke-level bootstrap/dispatch/fail/cleanup.

- [ ] **Step 3: Implement session lifecycle operations**

Refactor the runtime bridge to:
- create canonical team state
- maintain phase state
- persist shutdown and cleanup records
- produce machine-readable monitor snapshots
- keep backend validation separate from higher-level team lifecycle logic

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_session_ops.py tests/codex_team/test_tmux_smoke.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/codex_team/session_ops.py tests/codex_team/test_session_ops.py tests/codex_team/test_tmux_smoke.py
git commit -m "feat: add codex team session lifecycle"
```

### Task 5: tmux/worktree worker lifecycle and launch contract

**Files:**
- Create: `src/specify_cli/codex_team/tmux_backend.py`
- Create: `src/specify_cli/codex_team/worktree_ops.py`
- Create: `src/specify_cli/codex_team/worker_bootstrap.py`
- Create: `tests/codex_team/test_tmux_backend.py`
- Create: `tests/codex_team/test_worktree_ops.py`

- [ ] **Step 1: Write failing tests for backend launch planning**

Add tests covering:
- backend selection (`tmux` vs supported Windows-compatible backend)
- worker pane launch specs
- worktree naming and safety checks
- generated worker bootstrap instructions and role overlays

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_tmux_backend.py tests/codex_team/test_worktree_ops.py -q
```

Expected: FAIL because no worker launch/worktree abstraction exists yet.

- [ ] **Step 3: Implement lifecycle helpers**

Implement helpers that:
- validate backend availability
- plan worker pane/process launches
- create and clean worktrees safely
- generate worker bootstrap instructions and identities
- expose enough metadata for future `resume` and `status`

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_tmux_backend.py tests/codex_team/test_worktree_ops.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/tmux_backend.py src/specify_cli/codex_team/worktree_ops.py src/specify_cli/codex_team/worker_bootstrap.py tests/codex_team/test_tmux_backend.py tests/codex_team/test_worktree_ops.py
git commit -m "feat: add codex team worker launch lifecycle"
```

### Task 6: Expand `specify team` into a full CLI surface

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/codex_team/commands.py`
- Create: `tests/contract/test_codex_team_cli_api_surface.py`
- Modify: `tests/contract/test_codex_team_cli_surface.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Write failing CLI contract tests**

Add tests covering:
- `specify team status`
- `specify team await`
- `specify team resume`
- `specify team shutdown`
- `specify team cleanup`
- `specify team api <operation>`

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_cli_api_surface.py tests/integrations/test_cli.py -q
```

Expected: FAIL because the current CLI surface is status-first and flag-based rather than subcommand-complete.

- [ ] **Step 3: Implement the expanded CLI surface**

Refactor `specify team` so it:
- preserves `specify team` as the product entrypoint
- adds explicit subcommands
- routes subcommands to session/task/worker/mailbox operations
- returns stable JSON envelopes for `api` operations

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_cli_api_surface.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/__init__.py src/specify_cli/codex_team/commands.py tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_cli_api_surface.py tests/integrations/test_cli.py
git commit -m "feat: expand specify team cli surface"
```

### Task 7: Add Codex routing-brain parity in generated guidance

**Files:**
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `templates/commands/team.md`
- Modify: `templates/commands/implement.md`
- Create: `tests/codex_team/test_codex_guidance_routing.py`

- [ ] **Step 1: Write failing guidance tests**

Add tests covering:
- generated Codex guidance mentions solo vs native subagent vs `specify team`
- `sp-implement` uses runtime-aware escalation language
- `sp-team`/team guidance stays Codex-only

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_codex_guidance_routing.py tests/integrations/test_integration_codex.py tests/test_alignment_templates.py -q
```

Expected: FAIL where the generated guidance does not yet express the full routing contract.

- [ ] **Step 3: Implement the routing guidance**

Update generated Codex-only skill/guidance content so it:
- treats runtime escalation as a first-class routing choice
- keeps non-Codex integrations isolated
- aligns `sp-implement` with the expanded team/runtime system

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_codex_guidance_routing.py tests/integrations/test_integration_codex.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/integrations/codex/__init__.py templates/commands/team.md templates/commands/implement.md tests/codex_team/test_codex_guidance_routing.py
git commit -m "feat: align codex routing guidance with team runtime"
```

### Task 8: Integrate workflow execution with the full runtime

**Files:**
- Modify: `templates/commands/implement.md`
- Create: `tests/codex_team/test_implement_runtime_routing.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `docs/superpowers/specs/2026-04-11-omx-full-alignment-design.md`

- [ ] **Step 1: Write failing workflow tests**

Add tests covering:
- `sp-implement` batch strategy can escalate to `specify team`
- join-point semantics remain explicit
- the workflow distinguishes sequential execution, native subagents, and durable team runtime

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
```powershell
pytest tests/codex_team/test_implement_runtime_routing.py tests/test_alignment_templates.py -q
```

Expected: FAIL where the workflow language or examples are incomplete.

- [ ] **Step 3: Implement the workflow/runtime alignment**

Update the workflow templates and Codex guidance to:
- use the expanded runtime/API semantics
- keep team escalation tied to real runtime availability and batch shape
- preserve shared-surface and join-point safety rules

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:
```powershell
pytest tests/codex_team/test_implement_runtime_routing.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/implement.md tests/codex_team/test_implement_runtime_routing.py tests/test_alignment_templates.py docs/superpowers/specs/2026-04-11-omx-full-alignment-design.md
git commit -m "feat: connect implement workflow to codex team runtime"
```

### Task 9: Full regression and release hardening

**Files:**
- Modify: `README.md`
- Modify: historical single-file technical writeup references
- Modify: `docs/superpowers/plans/2026-04-11-omx-full-alignment.md`

- [x] **Step 1: Run the targeted full Codex/runtime suite**

Run:
```powershell
pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_cli_api_surface.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_subcommand.py tests/integrations/test_cli.py tests/test_alignment_templates.py -q
```

Expected: PASS with the aligned runtime and guidance behavior.

- [x] **Step 2: Run broader agent-config safety checks**

Run:
```powershell
pytest tests/test_agent_config_consistency.py tests/integrations/test_registry.py -q
```

Expected: PASS, confirming Codex-only team behavior does not leak into other integrations.

- [x] **Step 3: Update repository docs**

Document:
- the full `specify team` surface
- runtime state location and lifecycle
- Codex-only scope boundaries
- operator guidance for resume/shutdown/cleanup and backend requirements

- [x] **Step 4: Record final verification notes**

Write the final command results and any residual risks into this plan file.

- **Verification log**
  - `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_cli_api_surface.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_subcommand.py tests/integrations/test_cli.py tests/test_alignment_templates.py -q` (pass)
  - `pytest tests/test_agent_config_consistency.py tests/integrations/test_registry.py -q` (pass)
- Residual risks: none

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/plans/2026-04-11-omx-full-alignment.md
git commit -m "docs: finalize omx full alignment guidance"
```
