# Phase 11 Research: Worker Dispatch and Failure Convergence

## Objective

Research how to implement Phase 11 so delegated execution becomes safe for sequential and parallel work, while preserving the Phase 10 leader-only contract, explicit join points, limited safe cross-phase preparation, and mixed failure handling.

## Current Baseline

- Phase 10 already established the leader-only contract, roadmap-aware next-phase selection, and delegated `single-agent` semantics in `templates/commands/implement.md`, `src/specify_cli/orchestration/models.py`, `src/specify_cli/orchestration/state_store.py`, and `src/specify_cli/orchestration/scheduler.py`.
- `src/specify_cli/orchestration/policy.py` already provides the conservative strategy gate: no safe parallel batch or overlapping write sets means `single-agent`; otherwise prefer `native-multi-agent`, then `sidecar-runtime`.
- `src/specify_cli/codex_team/auto_dispatch.py` already parses explicit and inferred parallel batches from `tasks.md`, dispatches workers, writes batch records, and attaches pending join-point markers to task metadata.
- `src/specify_cli/codex_team/task_ops.py` already owns claim validation, task state transitions, and join-point metadata updates. Terminal task transitions call `sync_batch_for_task(...)`.
- `src/specify_cli/codex_team/batch_ops.py` currently applies a simple all-or-nothing batch rule: if any task in a batch fails, the batch becomes `failed`; if every task completes, the batch becomes `completed`.
- `src/specify_cli/codex_team/runtime_bridge.py` already persists a visible runtime-level failed state via `mark_runtime_failure(...)`.
- Existing tests already cover dispatch records, batch records, join-point propagation, runtime failure persistence, passive-parallelism safety checks, and CLI/API auto-dispatch behavior.

## What Phase 11 Still Needs

### 1. Batch Classification Layer

The current batch model is binary: success or failure. Phase 11 needs an explicit classification layer to distinguish:

- strict batches that require all worker tasks to succeed before the join point clears
- mixed-tolerance batches where every task must reach a terminal state, but unrelated downstream work may still continue if failures are non-critical
- blocker conditions that stop milestone progress outright

This classification does not exist yet in `BatchRecord`, `DispatchRecord`, or task metadata.

### 2. Failure Taxonomy

Current failure handling is too coarse:

- task-level failures mark the batch as failed in `batch_ops.py`
- runtime-level failures mark the whole session as failed in `runtime_bridge.py`

Phase 11 needs a more nuanced taxonomy that can represent:

- transient worker/runtime failures eligible for bounded retry
- recoverable non-critical failures that block the join point but not unrelated ready work
- critical-path or repeated failures that escalate to blocker status and halt advancement

This likely belongs partly in shared orchestration policy/models and partly in Codex-team runtime state.

### 3. Limited Cross-Phase Preparation Rules

`scheduler.py` currently enforces ordered selection of the next executable phase but has no concept of “safe preparation work” for later phases. Phase 11 needs a conservative decision surface for that behavior:

- roadmap order remains default truth
- later-phase work can only start when it is low-risk and does not imply phase completion
- safe preparation should stay narrow: read-only analysis, scaffolding, docs/config prep, or equivalent reversible setup

This is closer to scheduling policy than worker runtime plumbing, so it likely belongs near `scheduler.py` and/or `policy.py`, with runtime-facing payloads only after the policy says such work is safe.

### 4. Join-Point Convergence Rules

Join points already exist as metadata, but their semantics are currently inferred from task completion/failure only. Phase 11 needs explicit rules for:

- when a join point is considered complete
- when it is blocked
- when it is terminal-but-partially-satisfied
- how downstream tasks can tell whether they are fully unblocked, partially unblocked, or still blocked

The current task metadata format in `task_ops.py` can carry this, but the status vocabulary is too small (`pending`, `complete`, `failed` only via current sync behavior).

## Natural Extension Points

### Shared orchestration layer

- `src/specify_cli/orchestration/policy.py`
  - add policy helpers for safe preparation, batch classification inputs, and failure severity routing
- `src/specify_cli/orchestration/models.py`
  - add typed structures for join-point state, blocker state, batch classification, or retry policy decisions if the planner chooses to centralize them
- `src/specify_cli/orchestration/scheduler.py`
  - extend milestone decision-building to carry “safe prep allowed / not allowed” or related continuation metadata

### Codex-team runtime layer

- `src/specify_cli/codex_team/auto_dispatch.py`
  - attach batch classification and dispatch policy metadata when routing a ready batch
  - handle limited safe cross-phase preparation if the scheduler authorizes it
- `src/specify_cli/codex_team/batch_ops.py`
  - replace the current binary sync logic with classification-aware convergence behavior
- `src/specify_cli/codex_team/task_ops.py`
  - extend join-point metadata/state updates and possibly record retry or escalation metadata
- `src/specify_cli/codex_team/runtime_bridge.py`
  - distinguish runtime/environment failures from task/business-logic failures and expose retry-safe vs blocker outcomes
- `src/specify_cli/codex_team/runtime_state.py`
  - extend `BatchRecord` / task metadata payload expectations so new statuses survive persistence cleanly

### CLI / contract surface

- `templates/commands/implement.md`
  - likely needs only small truthfulness updates in later phases; Phase 11 should avoid broad contract rewrites unless behavior materially changes
- `src/specify_cli/integrations/codex/__init__.py`
  - only update if new behavior must be reflected in generated Codex skill wording

## Risks and Traps

### Trap 1: Letting Codex-only runtime semantics leak into shared policy too early

The file-backed runtime state and tmux-backed auto-dispatch are Codex-specific today. Shared orchestration policy should define concepts like “strict vs mixed-tolerance batch” or “safe preparation allowed,” but it should not hardcode Codex runtime implementation details.

### Trap 2: Making safe cross-phase preparation too permissive

The project explicitly wants roadmap order to remain truthful. If Phase 11 allows arbitrary non-overlapping implementation work across phases, milestone truth will drift and Phase 12 will inherit a reporting mess. Keep “safe preparation” narrow and auditable.

### Trap 3: Treating all worker failures the same

Current code already shows two distinct failure surfaces:

- task/batch failures (`task_ops.py`, `batch_ops.py`)
- runtime/session failures (`runtime_bridge.py`)

If Phase 11 collapses them into one status, retries and escalation will become noisy and inaccurate.

### Trap 4: Encoding join-point semantics only in prose

Tests already assert concrete join-point metadata changes. Phase 11 should keep join-point semantics machine-readable in batch/task state, not only in docs or templates.

### Trap 5: Overcommitting Phase 12 work into Phase 11

Phase 11 should add the runtime mechanics and policy needed for dispatch/failure convergence. It should not try to fully solve reporting, user-facing guidance, or final artifact visibility; those are Phase 12 deliverables.

## Planning Implications

### Recommended split

The roadmap’s two-plan split is correct:

#### 11-01: Worker dispatch, join-point coordination, and safe cross-phase preparation

This plan should focus on:

- extending shared policy/scheduler surfaces so “safe preparation” and batch types are explicit
- enriching dispatch/batch/task records with join-point and batch classification data
- making the runtime understand strict vs mixed-tolerance batch handling
- keeping later-phase preparation narrow and auditable

Most likely files:

- `src/specify_cli/orchestration/policy.py`
- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/scheduler.py`
- `src/specify_cli/codex_team/auto_dispatch.py`
- `src/specify_cli/codex_team/batch_ops.py`
- `src/specify_cli/codex_team/runtime_state.py`
- tests around auto-dispatch, passive parallelism, and shared policy

#### 11-02: Mixed failure classification, retry boundaries, and blocker reporting

This plan should focus on:

- defining a failure taxonomy and retry-safe vs non-retry-safe conditions
- adding bounded retry behavior only for clearly transient runtime/worker failures
- escalating critical-path and repeated failures into an explicit blocker surface
- preserving truthful runtime/session status transitions

Most likely files:

- `src/specify_cli/codex_team/runtime_bridge.py`
- `src/specify_cli/codex_team/task_ops.py`
- `src/specify_cli/codex_team/session_ops.py`
- `src/specify_cli/codex_team/runtime_state.py`
- dispatch/runtime tests and possibly new blocker-status tests

### Verification expectations

The plans should prove:

- join-point state is explicit and testable
- safe cross-phase preparation does not violate roadmap-order truth
- non-critical failures do not freeze unrelated ready work
- critical-path and repeated failures do freeze advancement with a visible blocker state
- retries only happen for a narrow, explicit class of transient failures

## Recommendation Summary

For planning, assume this shape:

1. Add a typed/shared policy layer for batch classification and safe-preparation decisions.
2. Extend Codex-team batch/task/runtime records to carry those decisions through execution.
3. Update convergence logic so join points are classification-aware rather than binary.
4. Add failure classification and bounded retry on top of that, with blocker escalation separated from ordinary task failure.
5. Keep user-facing wording changes minimal in Phase 11 unless the runtime behavior materially changes what the contract must promise.

## Output Boundary

Phase 11 should ship the mechanics that let the leader coordinate multiple worker lanes safely and truthfully. It should not try to finish the full reporting/documentation story; that belongs in Phase 12.
