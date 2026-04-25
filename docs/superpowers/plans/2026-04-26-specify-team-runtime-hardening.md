# Specify Team Runtime Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `sp-implement-teams` / `specify team` from a stateful orchestration shell into a durable, operator-usable multi-worker runtime with honest execution, transparent result contracts, stronger Windows preflight, consistent state transitions, and explicit workspace/result synchronization.

**Architecture:** Keep `specify team` as the public product surface and harden the existing `src/specify_cli/codex_team/` package rather than adding a second runtime path. Implement the work in thin vertical slices: first make packet execution real, then make operator-facing contracts self-service, then fix state consistency and workspace synchronization, and finally expose batch-vs-repo verification outcomes as first-class runtime semantics.

**Tech Stack:** Python, Typer CLI, JSON state records under `.specify/codex-team/`, pytest contract tests, Windows native shell + `psmux`

---

## Scope and Release Order

Ship this as five PR-sized slices in this order:

1. Real packet execution instead of heartbeat-only workers
2. Transparent result schema and submission ergonomics
3. Windows + baseline preflight hardening
4. Strong state consistency across task/batch/result records
5. Official sync-back and split verification outcomes

Do not collapse all five slices into one PR. Each slice should leave the runtime in a shippable state.

### Task 1: Replace Heartbeat-Only Workers With A Real Packet Executor

**Files:**
- Create: `src/specify_cli/codex_team/packet_executor.py`
- Create: `tests/codex_team/test_packet_executor.py`
- Modify: `src/specify_cli/codex_team/worker_runtime.py`
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`
- Modify: `tests/codex_team/test_real_executor_detection.py`
- Create or Modify: `tests/codex_team/test_worker_runtime.py`

**Intent:** Make runtime workers actually consume a packet, run the delegated executor path, and emit a structured success/blocked/failed result. Remove the current false-positive shape where the runtime appears alive but only writes heartbeat placeholders.

- [ ] **Step 1: Lock the current gap with failing tests**

Run:

```powershell
pytest tests/codex_team/test_auto_dispatch.py tests/codex_team/test_real_executor_detection.py -q
```

Add failing cases that prove:
- `worker_runtime.py` exits with `executor_missing` today
- a runtime marked executor-available must launch a packet executor, not only write a heartbeat
- `auto-dispatch` must fail loudly when a packet executor cannot be launched

- [ ] **Step 2: Introduce a dedicated packet executor module**

Create `src/specify_cli/codex_team/packet_executor.py` with these concrete responsibilities:
- `load_packet(packet_path: Path) -> WorkerTaskPacket`
- `build_result_template(packet: WorkerTaskPacket) -> dict[str, object]`
- `execute_packet(...) -> PacketExecutionOutcome`
- `write_result_file(...) -> Path`

Design the module so `worker_runtime.py` stays small and only orchestrates:
- worker bootstrap
- heartbeat updates
- executor call
- terminal heartbeat/status

- [ ] **Step 3: Make `worker_runtime.py` run a real executor path**

Change `src/specify_cli/codex_team/worker_runtime.py` so the runtime:
- reads packet/request metadata from the dispatch record or packet path
- emits `starting`, `executing`, `result_written`, `completed|blocked|failed` heartbeat states
- writes the normalized result file expected by `submit-result`
- only falls back to `executor_missing` when no executor is truly configured

Keep the current legacy heartbeat mode only for explicit test/dev use. It must not remain the implicit default for normal `auto-dispatch`.

- [ ] **Step 4: Tighten executor readiness reporting**

Update `src/specify_cli/codex_team/runtime_bridge.py` so:
- `detect_codex_team_executor()` distinguishes `status_only`, `runtime_cli_available`, `runtime_cli_broken`, and `executor_ready`
- `ensure_codex_team_executor_available()` returns actionable failure reasons
- `codex_team_runtime_status()` surfaces whether packet execution is actually possible, not just whether a CLI asset exists

- [ ] **Step 5: Re-run focused tests**

Run:

```powershell
pytest tests/codex_team/test_packet_executor.py tests/codex_team/test_worker_runtime.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_real_executor_detection.py -q
```

Expected:
- worker runtime now produces execution-side state transitions
- executor availability means real packet execution, not heartbeat-only behavior

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/codex_team/packet_executor.py src/specify_cli/codex_team/worker_runtime.py src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/codex_team/auto_dispatch.py tests/codex_team/test_packet_executor.py tests/codex_team/test_worker_runtime.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_real_executor_detection.py
git commit -m "feat: wire real packet execution into specify team"
```

### Task 2: Make Result Submission Self-Service Instead Of Schema Guessing

**Files:**
- Create: `src/specify_cli/codex_team/result_template.py`
- Create: `tests/codex_team/test_result_template.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/codex_team/commands.py`
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Modify: `tests/contract/test_codex_team_cli_api_surface.py`
- Modify: `tests/codex_team/test_commands.py`

**Intent:** Give operators a formal schema/template path for `submit-result`, clear BOM/encoding errors, and a stable way to generate valid payloads without reverse-engineering tests or internal records.

- [ ] **Step 1: Add failing CLI contract coverage**

Run:

```powershell
pytest tests/contract/test_codex_team_cli_api_surface.py tests/codex_team/test_commands.py -q
```

Add failing tests for:
- `specify team result-template --request-id <id>`
- `specify team submit-result --print-schema`
- `submit-result` errors that mention missing required fields and BOM/encoding problems

- [ ] **Step 2: Add a canonical result template builder**

Create `src/specify_cli/codex_team/result_template.py` with:
- `build_request_result_template(project_root: Path, request_id: str) -> dict[str, object]`
- `worker_result_schema_hint() -> dict[str, object]`
- `render_schema_help() -> str`

The output must be generated from the actual packet, not a hand-maintained copy of the schema.

- [ ] **Step 3: Expose new CLI surfaces**

Update `src/specify_cli/__init__.py` to add:
- `team result-template --request-id <id> [--output <path>]`
- `team submit-result --print-schema`

Update `submit-result` failure handling so it:
- detects UTF-8 BOM explicitly
- prints the canonical template command
- lists the missing or invalid top-level fields

- [ ] **Step 4: Keep normalization and validation in one place**

Refactor `src/specify_cli/codex_team/runtime_bridge.py` so template generation, normalization, and validation all depend on the same schema helpers. Do not maintain one shape in tests, another in templates, and a third in runtime validation.

- [ ] **Step 5: Re-run focused tests**

Run:

```powershell
pytest tests/codex_team/test_result_template.py tests/codex_team/test_commands.py tests/contract/test_codex_team_cli_api_surface.py -q
```

Expected:
- operators can generate a valid payload template before writing results
- `DONE_WITH_CONCERNS` payloads still normalize correctly
- encoding/schema failures are actionable

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/codex_team/result_template.py src/specify_cli/__init__.py src/specify_cli/codex_team/commands.py src/specify_cli/codex_team/runtime_bridge.py tests/codex_team/test_result_template.py tests/codex_team/test_commands.py tests/contract/test_codex_team_cli_api_surface.py
git commit -m "feat: add specify team result schema and template surfaces"
```

### Task 3: Strengthen Windows Preflight And Baseline Build Classification

**Files:**
- Create: `src/specify_cli/codex_team/baseline_check.py`
- Create: `tests/codex_team/test_baseline_check.py`
- Modify: `src/specify_cli/codex_team/doctor.py`
- Modify: `src/specify_cli/codex_team/live_probe.py`
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/codex_team/test_doctor.py`
- Modify: `tests/contract/test_codex_team_cli_surface.py`

**Intent:** Make `doctor` tell the operator whether the environment is truly runnable on native Windows and whether the repo already has baseline compile debt before a new batch is dispatched.

- [ ] **Step 1: Lock the target diagnostics with failing tests**

Run:

```powershell
pytest tests/codex_team/test_doctor.py tests/contract/test_codex_team_cli_surface.py -q
```

Add failing checks for:
- `psmux`, `codex`, `node`, `npm`, `cargo`, `git` surfaced in one readiness block
- explicit backend discovery source
- baseline build status reported as `clean`, `blocked`, or `unknown`
- next-step guidance for native Windows shell/toolchain mismatches

- [ ] **Step 2: Add a baseline build detector**

Create `src/specify_cli/codex_team/baseline_check.py` with:
- `detect_solution_metadata(project_root: Path) -> dict[str, object]`
- `detect_native_build_shell(project_root: Path) -> dict[str, object]`
- `classify_baseline_build_status(project_root: Path) -> dict[str, object]`

The detector should not claim a repo is healthy unless it has actual evidence. If a safe check cannot run, return `unknown` with an explanation.

- [ ] **Step 3: Extend `doctor` and `live-probe`**

Update `src/specify_cli/codex_team/doctor.py` and `src/specify_cli/codex_team/live_probe.py` so they report:
- runtime backend detection details
- native toolchain readiness
- executor readiness
- baseline build viability
- latest transcript and recent failures

`live-probe` should remain a minimal runtime acceptance check. Do not turn it into a full build command.

- [ ] **Step 4: Expose baseline risk before dispatch**

Update `src/specify_cli/__init__.py` and `src/specify_cli/codex_team/runtime_bridge.py` so `team auto-dispatch` warns or blocks when baseline status is `blocked`, and the error message clearly says whether the blocker is:
- runtime readiness
- build baseline debt
- stale project-map / tracker state

- [ ] **Step 5: Re-run focused tests**

Run:

```powershell
pytest tests/codex_team/test_baseline_check.py tests/codex_team/test_doctor.py tests/contract/test_codex_team_cli_surface.py -q
```

Expected:
- doctor output is enough to explain why Windows execution is or is not runnable
- baseline debt is distinguished from batch-specific failures

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/codex_team/baseline_check.py src/specify_cli/codex_team/doctor.py src/specify_cli/codex_team/live_probe.py src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/__init__.py tests/codex_team/test_baseline_check.py tests/codex_team/test_doctor.py tests/contract/test_codex_team_cli_surface.py
git commit -m "feat: harden specify team doctor for windows and baseline checks"
```

### Task 4: Make Task, Batch, And Result State Strongly Consistent

**Files:**
- Modify: `src/specify_cli/codex_team/runtime_bridge.py`
- Modify: `src/specify_cli/codex_team/task_ops.py`
- Modify: `src/specify_cli/codex_team/batch_ops.py`
- Modify: `src/specify_cli/codex_team/runtime_state.py`
- Modify: `tests/codex_team/test_task_ops.py`
- Modify: `tests/codex_team/test_runtime_bridge.py`
- Modify: `tests/contract/test_codex_team_auto_dispatch_cli.py`

**Intent:** Ensure that a submitted result advances the task and batch state in a single, trustworthy direction. The operator should never see `result completed` while the canonical task record still says `pending`.

- [ ] **Step 1: Add failing state-consistency tests**

Run:

```powershell
pytest tests/codex_team/test_task_ops.py tests/codex_team/test_runtime_bridge.py tests/contract/test_codex_team_auto_dispatch_cli.py -q
```

Add failing checks for:
- `submit-result` moves a claimed task to `completed` or `failed`
- `reported_status` such as `DONE_WITH_CONCERNS` is preserved in metadata
- batch review/join-point state updates after all member tasks reach terminal state
- repeat submission for the same request is rejected or treated idempotently

- [ ] **Step 2: Add explicit result-to-task synchronization**

Update `src/specify_cli/codex_team/runtime_bridge.py` so `submit_runtime_result()`:
- loads the dispatch and associated packet
- normalizes/validates the result
- maps result status into canonical task status
- writes the result record
- transitions the task through `in_progress -> completed|failed`
- syncs batch status after the task transition

Keep this flow transactional in spirit: if the task transition fails, do not leave the dispatch/result records in a misleading terminal state.

- [ ] **Step 3: Extend task metadata for operator truth**

Update `src/specify_cli/codex_team/task_ops.py` and `src/specify_cli/codex_team/runtime_state.py` so task metadata can preserve:
- `reported_status`
- `result_request_id`
- `last_validation_summary`
- `concerns_present`

Use metadata for operator diagnostics, not as a replacement for canonical status.

- [ ] **Step 4: Re-run focused tests**

Run:

```powershell
pytest tests/codex_team/test_task_ops.py tests/codex_team/test_runtime_bridge.py tests/contract/test_codex_team_auto_dispatch_cli.py tests/contract/test_codex_team_cli_api_surface.py -q
```

Expected:
- task, dispatch, batch, and result records converge after result submission
- `DONE_WITH_CONCERNS` remains visible without leaving the task stuck in `pending`

- [ ] **Step 5: Commit**

```powershell
git add src/specify_cli/codex_team/runtime_bridge.py src/specify_cli/codex_team/task_ops.py src/specify_cli/codex_team/batch_ops.py src/specify_cli/codex_team/runtime_state.py tests/codex_team/test_task_ops.py tests/codex_team/test_runtime_bridge.py tests/contract/test_codex_team_auto_dispatch_cli.py tests/contract/test_codex_team_cli_api_surface.py
git commit -m "fix: synchronize specify team task batch and result state"
```

### Task 5: Add Official Sync-Back And Split Verification Outcomes

**Files:**
- Create: `src/specify_cli/codex_team/sync_back.py`
- Create: `tests/codex_team/test_sync_back.py`
- Modify: `src/specify_cli/codex_team/worktree_ops.py`
- Modify: `src/specify_cli/codex_team/doctor.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `docs/quickstart.md`
- Modify: `templates/commands/implement-teams.md`
- Modify: `tests/contract/test_codex_team_cli_surface.py`

**Intent:** Give the operator a first-party way to promote leader-worktree results back to the main workspace and expose the final outcome as two separate truths: lane-local completion and repo-global verification status.

- [ ] **Step 1: Add failing CLI and unit tests**

Run:

```powershell
pytest tests/codex_team/test_sync_back.py tests/contract/test_codex_team_cli_surface.py -q
```

Add failing coverage for:
- `specify team sync-back --session-id <id>`
- dry-run mode that lists candidate files
- refusal when the main workspace is dirty unless an explicit override flag is used
- final status text that distinguishes `lane_status` from `repo_verification_status`

- [ ] **Step 2: Implement sync-back planning and application**

Create `src/specify_cli/codex_team/sync_back.py` with:
- `collect_sync_back_candidates(project_root: Path, session_id: str) -> list[dict[str, object]]`
- `plan_sync_back(...) -> dict[str, object]`
- `apply_sync_back(...) -> dict[str, object]`

Use existing worktree helpers where possible. Do not do unsafe recursive copies outside the declared runtime worktree root.

- [ ] **Step 3: Expose lane-vs-repo outcome summary**

Extend the final operator-facing status in `doctor` and the CLI command output so each completed batch can report:
- `lane_status`: completed | completed_with_concerns | failed
- `repo_verification_status`: passed | blocked_by_baseline | failed | unknown

Do not overload one field to mean both things.

- [ ] **Step 4: Update docs and generated guidance**

Update `docs/quickstart.md` and `templates/commands/implement-teams.md` so the official workflow explains:
- when to run `doctor`
- when to run `live-probe`
- when `sync-back` is required
- how to interpret `DONE_WITH_CONCERNS` vs repo-level failure

- [ ] **Step 5: Re-run focused tests**

Run:

```powershell
pytest tests/codex_team/test_sync_back.py tests/contract/test_codex_team_cli_surface.py tests/codex_team/test_doctor.py -q
```

Expected:
- users can safely bring runtime results back to the main workspace
- final runtime summaries separate batch-local success from repo-global blockers

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/codex_team/sync_back.py src/specify_cli/codex_team/worktree_ops.py src/specify_cli/codex_team/doctor.py src/specify_cli/__init__.py docs/quickstart.md templates/commands/implement-teams.md tests/codex_team/test_sync_back.py tests/contract/test_codex_team_cli_surface.py tests/codex_team/test_doctor.py
git commit -m "feat: add specify team sync-back and split verification outcomes"
```

## Final Verification

Run the full targeted suite before claiming the runtime hardening work is done:

```powershell
pytest tests/codex_team -q
pytest tests/contract/test_codex_team_cli_api_surface.py tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_auto_dispatch_cli.py -q
```

If the repo has a safe Codex-runtime smoke path, also run:

```powershell
python -m specify_cli team doctor
python -m specify_cli team live-probe
```

The completion bar for this plan is:
- runtime workers execute packets instead of only writing heartbeats
- result submission is templated and schema-transparent
- Windows readiness and baseline blockers are visible before dispatch
- task/batch/result state agrees after submission
- leader worktree results can be promoted safely
- operator output distinguishes lane-local completion from repo-global verification

