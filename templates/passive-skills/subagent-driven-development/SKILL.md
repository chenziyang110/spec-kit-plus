---
description: "Use when executing implementation plans, working on independent tasks, or when asked to dispatch subagents. Supports ordinary development directly and preserves the contracts of explicitly invoked workflows."
---

# Subagent-Driven Development (Spec Kit Plus)

Spec Kit Plus keeps workflow state in `sp-*` artifacts, but it should still use
native subagents when bounded delegation materially improves throughput, isolation,
specialist quality, or verification confidence. Subagents are not a competing workflow; they are
the execution workers behind packetized `sp-quick` work after understanding
confirmation, broad or independent `sp-debug` evidence lanes, `sp-map-scan`,
`sp-map-build`, and `sp-implement`.

## Workflow-Owned Validation

When `sp-implement` uses feature validation gates, packets carry cheap
`task_checks`, accepted baseline refs when needed, and test impact. The Leader
owns every logical gate and validation attempt shared across Implement and Review.
Workers and this passive skill must not start an extra gate or attempt for a
Txx, dispatch, join, resume, or completion handoff.

## Core Rule

Identify the active execution context, then choose the lightest safe execution surface.

Passive SKILL invocation must not enter any `sp-*` or `spx-*` workflow. Routing
is optional advice for ordinary development, not a prerequisite for doing the
authorized work. Do not require a workflow command merely to continue ordinary
development or dispatch native subagents.

## Execution Context Boundary

- **Ordinary development**: When no explicitly invoked workflow owns the work,
  continue the authorized request directly. If an executable task graph is missing,
  create a compact in-session task list with dependencies, write scopes, acceptance,
  and verification, then proceed. Do not require `plan-contract.json`,
  `task-index.json`, runtime packet compilation, or a workflow result channel.
  Do not create or mutate canonical workflow artifacts for this ordinary path.
- **Active workflow**: Resume an already explicitly invoked workflow without
  requiring the user to repeat its command. Preserve its phase boundaries,
  runtime-owned artifacts, validated packets, result channels, and approval gates.
  Missing required artifacts stay with that workflow's recovery or upstream owner;
  never relabel active workflow work as ordinary development to bypass a gate.
- Existing workflow files alone do not activate a workflow. Missing implementation
  targets, unresolved product decisions, credentials, and real approval gates still
  require resolution; continue independent authorized work where possible.

The workflow-specific rules below apply only inside an active workflow. For
ordinary development, use a bounded in-session assignment and structured native
result instead; record dispatch choices and verification in the current task.

- Determine whether a user-invoked workflow already owns the request before
  applying workflow-specific requirements.
- Use leader-direct execution for a small or tightly coupled task when delegation
  adds no critical-path or quality benefit and the owning workflow permits it.
- Compile and validate a `WorkerTaskPacket` just in time before selected delegated work.
- Dispatch `one-subagent` when one safe lane is ready, or when multiple tasks
  share write scope and must run serially.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently with isolated write sets.
- **Cannot parallelize ≠ implement as Leader.** A write-scope conflict only
  forces serial `one-subagent` (or a recorded workflow-allowed leader mode).
- If dispatch fails, record the event and re-evaluate route safety. Execute locally
  only when the task independently qualifies for leader-direct and that choice is
  recorded in the owning workflow state.
- `sp-debug` may stay leader-inline for small focused investigations; use
  subagent-assisted execution when the investigation exposes broad, independent,
  or parallel evidence lanes.
- Do not use old strategy labels as routing choices.
- `sp-teams` only when Codex work needs durable team state, explicit join-point
  tracking, durable request-result persistence, or lifecycle control beyond one
  in-session subagent burst.

## Process

1. **Identify the execution context**: Apply the Execution Context Boundary.
   For ordinary development, fill in missing execution slicing and continue.
   If the user wants a formal workflow, show `{{invoke:tasks}}` for an existing
   plan needing a canonical graph or `{{invoke:implement}}` for a ready graph.
   Advice does not activate a workflow or suspend ordinary authorized work.
2. **Select the route**: Keep small/tightly coupled work leader-direct. For an
   independent or parallel lane in an active workflow, compile a validated `WorkerTaskPacket`
   from the current task, stable refs, and live code. For ordinary development,
   prepare the bounded assignment described below.
3. **Dispatch in the current runtime**: Use the `native-subagents` surface such
   as Codex `spawn_agent`, Cursor `Task`, Claude Task, or the active CLI's
   equivalent. The
   leader owns packet quality, lane selection, and integration, but should not
   implement the lane locally while subagent execution is active. Use
   `managed-team` only for durable team state or lifecycle control, and use
   `leader-inline` only as the owning workflow's selected mode. Discover and
   require only the dispatch and join operations that runtime actually exposes.
4. **Join on evidence**: Wait for every subagent's structured handoff. The
   handoff must name changed files, cheap task checks, test impact, accepted
   gate-attempt refs when workflow-required, failures, open risks, and any spec or plan gaps. An idle or silent
   subagent is not completed work. An accepted terminal result completes its
   native lane without a separate cleanup operation; interrupt or cancel only
   unfinished work through an operation the runtime exposes. In an active workflow,
   use the owning workflow's stage result channel, never an implicit `sp-teams` result path.
   For ordinary development, accept the structured native result directly.
5. **Review on triggers**: Run the single task reviewer only for drift, parallel
   joins, scope violations, validation failure, worker concerns, obligation
   conflicts, real-entrypoint gaps, or review-window triggers. Integrate verdict,
   validation, and recovery into the task lifecycle record for an active workflow,
   or the current task report for ordinary development.

## Dispatch Prompt Contract

A subagent prompt must include:

- The lane identifier and owning workflow, if active; otherwise ordinary development.
- For an active workflow, the validated `WorkerTaskPacket` or equivalent packet summary.
- For ordinary development, a bounded assignment: objective, dependencies,
  authoritative live context, exact read/write scope, forbidden drift, acceptance,
  verification, and recovery/escalation conditions. No runtime receipt is required.
- Exact write set and paths the worker must not touch.
- Stable authoritative refs from the current task, plan/spec contracts, live code,
  and memory rules actually needed by the lane.
- Under workflow-owned validation, accepted change-set RED/baseline gate-attempt ref or test-authoring-only status,
  cheap task checks, and test impact for Leader-owned convergence.
- For scan, build, PRD scan, and map-update evidence lanes, include explicit `assigned_paths` or changed paths. A subagent must not silently narrow assigned scope; if the set does not fit, the worker result returns top-level `acceptance=fail_gap`, marks affected paths with path-level `coverage[].outcome="overflow"` or `coverage[].outcome="blocked"`, and includes the smallest safe split or recovery suggestion. `overflow` and `blocked` are path or queue states, not top-level worker result acceptance values.
- Worker results for mutable work must include changed paths, behavior surfaces, generated surfaces, state contracts, verification, known unknowns, and confidence notes so the parent workflow can build the inline project cognition update payload.
- Required structured handoff format.

The leader must not dispatch from raw task text alone. If the packet is missing,
ambiguous, or does not describe boundaries and verification, create or repair the
packet before dispatch within the active workflow. For ordinary development,
prepare the bounded assignment directly. Workflow-specific companion worker and
reviewer templates are not prerequisites for ordinary assignments.

## Routing Rules

- If the user says "execute the plan", "start building", "implement tasks", or
  equivalent, this authorizes ordinary execution when no active workflow owns
  the work; it does not implicitly invoke a workflow. Apply the boundary above.
- If the user asks to "dispatch agents", "split this up", or "run subagents",
  prepare bounded assignments and dispatch native subagents directly for ordinary
  development; use validated packets when an active workflow owns the work.
- If the current workflow finds 2+ independent lanes, pair this skill with
  `dispatching-parallel-agents`.
- Ordinary development may stay leader-inline when delegation adds no benefit.
  In an active workflow, use its own leader-direct qualification rules.

## Red Flags

- Stopping ordinary development solely to demand `{{invoke:tasks}}` or
  `{{invoke:implement}}`, or requiring canonical workflow artifacts for a native assignment.
- Bypassing an active workflow's unresolved gate by calling its work ordinary development.
- Treating every implementation task as mandatory delegation even when a small,
  tightly coupled leader-direct route is safer and faster.
- After a parallel write-scope conflict, implementing all serial tasks
  leader-inline without trying `one-subagent` and without recording a fallback.
- Doing leader-inline work after a `sp-debug` route selected
  `subagent-assisted` execution or after independent evidence lanes are
  available, without recording why the investigation remains small and focused.
- Dispatching raw task text without a validated `WorkerTaskPacket`.
- Asking the user to open separate terminals when native subagents are available
  in the current runtime.
- Treating an idle subagent as done work.
- Accepting a handoff that lacks changed-file summary, cheap task-check evidence,
  test impact, or its required gate-attempt ref.
- Skipping event-triggered review when the workflow records a review trigger.
- Updating `tasks.md`, quick status, or workflow state as complete before the
  structured handoff and validation evidence exist.
