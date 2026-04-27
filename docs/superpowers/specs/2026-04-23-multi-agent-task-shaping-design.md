# Multi-Agent Task Shaping Design

**Date:** 2026-04-23
**Status:** Approved for implementation
**Owner:** Codex

## Summary

This design tightens the existing delegated-execution workflow in `spec-kit-plus` without replacing its current strategy model. The repository already supports capability-aware routing, join points, worker task packets, and blocked/recovery state. The missing pieces are stricter task-shaping rules: bounded task granularity, progressive decomposition, explicit grouped-parallel versus pipeline guidance, and a harder fail-fast blocker contract for delegated workers.

The goal is to reduce two recurring failure modes:

1. tasks that are too coarse for delegated workers to execute safely
2. tasks that are over-decomposed early, forcing the runtime to coordinate around stale assumptions
3. high-risk batches that cross join points without an explicit review gate

## Problem Statement

Current workflow templates and runtime helpers already preserve:

- shared execution strategy vocabulary: `single-lane`, `native-multi-agent`, `sidecar-runtime`
- join-point-aware execution
- rule-carrying `WorkerTaskPacket` compilation and validation
- blocker, retry, and recovery state during implementation

But task shaping is still under-specified in four important ways:

1. `tasks.md` requires tasks to be executable, but does not define a target granularity envelope.
2. Planning guidance encourages decomposition, but does not tell the planner when to stop decomposing and leave later refinement to execution-time evidence.
3. Parallel guidance is strong on write-set safety, but weak on choosing grouped parallelism versus a pipeline-shaped batch.
4. Delegated worker results can report `blocked`, but the result contract does not yet force workers to return the exact blocker facts needed for fail-fast recovery.

## Goals

- Add an explicit task granularity contract to `tasks` generation guidance and templates.
- Preserve gradual refinement by telling planners to decompose only the current executable window to atomic tasks.
- Make grouped parallelism the default parallel shape while documenting when a pipeline is the right model.
- Strengthen delegated worker results so `blocked` outcomes carry actionable blocker context.
- Keep the existing execution strategy model, packet validation model, and Codex team/runtime surfaces intact.

## Non-Goals

- Do not introduce a new execution strategy name beyond `single-lane`, `native-multi-agent`, and `sidecar-runtime`.
- Do not replace join-point execution with free-running autonomous worker swarms.
- Do not force all top-level `tasks.md` items down to 2-5 minute units; that granularity belongs inside a delegated worker task, not always in the public task list.
- Do not add mandatory peer-review lanes to every batch.

## Approved Direction

### 1. Dual-level granularity contract

Top-level planning tasks and delegated worker execution tasks should use different target envelopes:

- `tasks.md` top-level tasks should usually fit one bounded implementation slice:
  - roughly 10-20 minutes
  - one stable objective
  - one isolated write set
  - one verification path
- delegated worker internal execution should still aim for smaller atomic steps:
  - roughly 2-5 minutes
  - not worth decomposing further without becoming coordination overhead

This keeps `tasks.md` dense enough to manage while still making each delegated packet executable.

### 2. Progressive decomposition stop rule

The workflow should explicitly tell planners:

- decompose by phase and story first
- decompose only the current executable window to atomic tasks
- keep later work at a coarser phase or story slice when its exact shape depends on upstream join-point evidence
- use refinement checkpoints instead of speculative premature detail

This preserves the repository's existing analysis-first model while reducing stale assumptions.

### 3. Explicit grouped-parallel and pipeline guidance

The workflow should explain that:

- grouped parallelism is the default when multiple ready tasks have isolated write sets
- pipeline execution is preferred when outputs flow linearly from one bounded lane to the next
- any pipeline still needs explicit checkpoints between stages so invalid assumptions cannot flow downstream silently

This is a documentation and planning-layer clarification, not a new runtime primitive.

### 4. Harder fail-fast blocker contract

If a delegated worker returns `blocked`, the result must include:

- a concrete blocker summary
- the assumption or dependency that failed
- the smallest safe recovery step

The orchestrator can then decide whether to retry, replan, or escalate, instead of forcing a second agent or the leader to rediscover the blocker.

### 5. Lightweight review gates for high-risk batches

Do not add peer-review lanes to every batch. Instead:

- require a review gate for high-risk batches
- keep worker self-check mandatory
- keep leader/orchestrator acceptance mandatory before crossing the join point
- recommend one read-only peer-review lane only when the batch is high-risk and a safe independent review lane exists

Typical high-risk triggers:

- shared registration surfaces
- schema or migration changes
- protocol seams
- native or plugin bridges
- generated API surfaces

## Design Changes

### Shared planning templates

Update `tasks` guidance and sample template to:

- define bounded task granularity explicitly
- distinguish top-level task shape from delegated-worker atomic execution
- tell planners to stop decomposition once the current executable window is atomic
- document grouped parallelism as the default parallel shape
- document pipeline-shaped batches and their required checkpoints
- document review gates for high-risk batches and when a peer-review lane is worth the coordination cost

Update `implement` guidance to:

- tell leaders to expect refinement at join points
- make pipeline stage boundaries explicit
- require blocked delegated results to carry concrete blocker evidence and next-step guidance
- require high-risk batches to pass a review gate before their join point is accepted

### Shared orchestration policy

Add a small shared helper in `src/specify_cli/orchestration/policy.py` that classifies whether a batch needs a review gate and whether a peer-review lane is recommended. This helper should not change the canonical execution strategy names or the batch execution policy. It should only answer:

- does this batch require extra review before crossing the join point?
- if so, is a read-only peer-review lane worth adding?

### Shared execution contract

Extend `WorkerTaskResult` so blocked delegated work carries:

- `blockers`
- `failed_assumptions`
- `suggested_recovery_actions`

Update result validation so a blocked result without that evidence fails validation instead of being treated as a soft narrative outcome.

### Tests and docs

Update template assertions and execution tests so these rules stay stable:

- task granularity contract
- progressive decomposition stop rule
- grouped parallel versus pipeline guidance
- blocked-result evidence requirements

## Acceptance Criteria

The change is complete when:

1. `tasks` guidance explicitly documents the new task granularity and progressive decomposition rules.
2. `tasks-template.md` includes the same concepts in generated output examples.
3. `implement` guidance explicitly documents grouped parallelism, pipeline checkpoints, and join-point-time refinement.
4. `WorkerTaskResult` and its validator reject blocked delegated results that omit blocker facts.
5. High-risk batches can be classified through a shared review-gate helper without changing the canonical execution strategy names.
6. Regression tests assert the new guidance, review-gate policy, and result-validation behavior.

## Risks

- Over-correcting toward very small tasks could increase task-list noise.
- Over-correcting toward progressive refinement could make later phases too vague to execute.
- Requiring blocker evidence too aggressively could reject some legitimate partial-result shapes.

## Mitigations

- Keep the top-level task envelope larger than the worker-internal atomic step envelope.
- Limit refinement deferral to later phases whose concrete shape truly depends on earlier checkpoints.
- Apply strict blocker evidence requirements only when status is `blocked`, not for every successful result.
