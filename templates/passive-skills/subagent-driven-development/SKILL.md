---
description: "Use when executing implementation plans, working on independent tasks, or when asked to dispatch subagents. Routes through sp-* workflows and dispatches native subagents from validated execution packets."
---

# Subagent-Driven Development (Spec Kit Plus)

Spec Kit Plus keeps workflow state in `sp-*` artifacts, but it should still use
native subagents when bounded delegation materially improves throughput, isolation,
specialist quality, or verification confidence. Subagents are not a competing workflow; they are
the execution workers behind packetized `sp-quick` work after understanding
confirmation, broad or independent `sp-debug` evidence lanes, `sp-map-scan`,
`sp-map-build`, and `sp-implement`.

## Core Rule

Route first, choose the lightest safe execution surface, then packetize only selected delegated work.

- Route into the smallest correct `sp-*` workflow before implementation or
  investigation begins.
- Use leader-direct execution for a small or tightly coupled task when delegation
  adds no critical-path or quality benefit and the owning workflow permits it.
- Compile and validate a `WorkerTaskPacket` just in time before selected delegated work.
- Dispatch `one-subagent` when one safe lane is ready.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently.
- If dispatch fails, record the event and re-evaluate route safety. Execute locally
  only when the task independently qualifies for leader-direct.
- `sp-debug` may stay leader-inline for small focused investigations; use
  subagent-assisted execution when the investigation exposes broad, independent,
  or parallel evidence lanes.
- Do not use old strategy labels as routing choices.
- `sp-teams` only when Codex work needs durable team state, explicit join-point
  tracking, result files, or lifecycle control beyond one in-session subagent
  burst.

## Process

1. **Select the owning workflow**: Route to canonical `sp-tasks` when a plan lacks
   an executable task graph. Route to canonical `sp-implement` for planned feature
   execution, `sp-quick` for lightweight tracked work, `sp-debug` for root-cause
   work, and the relevant map/test workflow for project cognition or testing-system
   lanes. When telling the user what to type, use `{{invoke:tasks}}`,
   `{{invoke:implement}}`, `{{invoke:quick}}`, or `{{invoke:debug}}`.
2. **Select the route**: Keep small/tightly coupled work leader-direct. For an
   independent or parallel lane, compile a validated `WorkerTaskPacket` from the
   current task, stable refs, and live code.
3. **Dispatch in the current runtime**: Use the `native-subagents` surface such
   as Codex `spawn_agent`, Claude Task, or the active CLI's equivalent. The
   leader owns packet quality, lane selection, and integration, but should not
   implement the lane locally while subagent execution is active. Use
   `managed-team` only for durable team state or lifecycle control, and use
   `leader-inline` only as the owning workflow's selected mode.
4. **Join on evidence**: Wait for every subagent's structured handoff. The
   handoff must name changed files, verification run, failures, open risks, and
   any spec or plan gaps. An idle or silent subagent is not completed work.
5. **Review on triggers**: Run the single task reviewer only for drift, parallel
   joins, scope violations, validation failure, worker concerns, obligation
   conflicts, real-entrypoint gaps, or review-window triggers. Integrate verdict,
   validation, and recovery into the task lifecycle record.

## Dispatch Prompt Contract

A subagent prompt must include:

- The owning `sp-*` workflow and lane identifier.
- The validated `WorkerTaskPacket` or equivalent packet summary.
- Exact write set and paths the worker must not touch.
- Stable authoritative refs from the current task, plan/spec contracts, live code,
  and memory rules actually needed by the lane.
- Required RED/GREEN or diagnosis evidence.
- For scan, build, PRD scan, and map-update evidence lanes, include explicit `assigned_paths` or changed paths. A subagent must not silently narrow assigned scope; if the set does not fit, the worker result returns top-level `acceptance=fail_gap`, marks affected paths with path-level `coverage[].outcome="overflow"` or `coverage[].outcome="blocked"`, and includes the smallest safe split or recovery suggestion. `overflow` and `blocked` are path or queue states, not top-level worker result acceptance values.
- Worker results for mutable work must include changed paths, behavior surfaces, generated surfaces, state contracts, verification, known unknowns, and confidence notes so the parent workflow can build the inline project cognition update payload.
- Required structured handoff format.

The leader must not dispatch from raw task text alone. If the packet is missing,
ambiguous, or does not describe boundaries and verification, create or repair the
packet before dispatch.

## Routing Rules

- If the user says "execute the plan", "start building", "implement tasks", or
  equivalent, route to `sp-implement`, or to `sp-tasks` first if tasks are not
  generated. If a manual next step is needed, tell the user to run
  `{{invoke:implement}}`, or `{{invoke:tasks}}` when the task graph is missing.
- If the user asks to "dispatch agents", "split this up", or "run subagents",
  route to the workflow that owns the state, then dispatch native subagents from
  validated packets.
- If the current workflow finds 2+ independent lanes, pair this skill with
  `dispatching-parallel-agents`.
- If the task is truly trivial and tightly coupled, `sp-fast` may stay inline.
  Do not use "small" as a reason to skip routing for non-trivial work.

## Red Flags

- Treating every implementation task as mandatory delegation even when a small,
  tightly coupled leader-direct route is safer and faster.
- Doing leader-inline work after a `sp-debug` route selected
  `subagent-assisted` execution or after independent evidence lanes are
  available, without recording why the investigation remains small and focused.
- Dispatching raw task text without a validated `WorkerTaskPacket`.
- Asking the user to open separate terminals when native subagents are available
  in the current runtime.
- Treating an idle subagent as done work.
- Accepting a handoff that lacks verification evidence or changed-file summary.
- Skipping event-triggered review when the workflow records a review trigger.
- Updating `tasks.md`, quick status, or workflow state as complete before the
  structured handoff and validation evidence exist.
