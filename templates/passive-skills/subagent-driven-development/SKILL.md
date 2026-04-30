---
description: "Use when executing implementation plans, working on independent tasks, or when asked to dispatch subagents. Routes through sp-* workflows and dispatches native subagents from validated execution packets."
---

# Subagent-Driven Development (Spec Kit Plus)

Spec Kit Plus keeps workflow state in `sp-*` artifacts, but it should still use
native subagents aggressively once the work is safely packetized. Subagents are
not a competing workflow; they are the execution workers behind `sp-quick`,
`sp-debug`, `sp-test-build`, `sp-map-scan`, `sp-map-build`, and `sp-implement`.

## Core Rule

Route first, packetize second, dispatch third.

- Route into the smallest correct `sp-*` workflow before implementation or
  investigation begins.
- Compile and validate a `WorkerTaskPacket` or equivalent execution contract
  before any subagent work begins.
- Use subagents-first execution for bounded delegated work.
- Dispatch `one-subagent` when one safe lane is ready.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently.
- Use `leader-inline-fallback` only after recording why delegation is
  unavailable, unsafe, or not packetized.
- Do not use old strategy labels as routing choices.
- `sp-teams` only when Codex work needs durable team state, explicit join-point
  tracking, result files, or lifecycle control beyond one in-session subagent
  burst.

## Process

1. **Select the owning workflow**: Use `sp-tasks` when a plan lacks executable
   task packets. Use `sp-implement` for planned feature execution, `sp-quick`
   for lightweight tracked work, `sp-debug` for root-cause work, and the
   relevant map/test workflow for project-map or testing-system lanes.
2. **Build the execution packet**: Every lane needs a validated
   `WorkerTaskPacket` or equivalent with task text, relevant artifacts, write
   set, shared surfaces, forbidden drift, acceptance checks, and verification
   commands.
3. **Dispatch in the current runtime**: Use the `native-subagents` surface such
   as Codex `spawn_agent`, Claude Task, or the active CLI's equivalent. The
   leader owns packet quality, lane selection, and integration, but should not
   implement the lane locally while subagent execution is active. Use
   `managed-team` only for durable team state or lifecycle control, and use
   `leader-inline` only as a recorded fallback.
4. **Join on evidence**: Wait for every subagent's structured handoff. The
   handoff must name changed files, verification run, failures, open risks, and
   any spec or plan gaps. An idle or silent subagent is not completed work.
5. **Review in order**: Run spec compliance review first. Run code quality
   review after spec compliance passes. Then run the workflow's required
   validation commands and update the tracker/state artifacts.

## Dispatch Prompt Contract

A subagent prompt must include:

- The owning `sp-*` workflow and lane identifier.
- The validated `WorkerTaskPacket` or equivalent packet summary.
- Exact write set and paths the worker must not touch.
- Source artifacts that are truth for the lane, including spec, plan, tasks,
  workflow state, project-map entries, and memory rules when present.
- Required RED/GREEN or diagnosis evidence.
- Required structured handoff format.

The leader must not dispatch from raw task text alone. If the packet is missing,
ambiguous, or does not describe boundaries and verification, create or repair the
packet before dispatch.

## Routing Rules

- If the user says "execute the plan", "start building", "implement tasks", or
  equivalent, route to `sp-implement`, or to `sp-tasks` first if tasks are not
  generated.
- If the user asks to "dispatch agents", "split this up", or "run subagents",
  route to the workflow that owns the state, then dispatch native subagents from
  validated packets.
- If the current workflow finds 2+ independent lanes, pair this skill with
  `dispatching-parallel-agents`.
- If the task is truly trivial and tightly coupled, `sp-fast` may stay inline.
  Do not use "small" as a reason to skip routing for non-trivial work.

## Red Flags

- Doing leader-inline implementation because the task looks "small" after an
  `sp-quick`, `sp-debug`, or `sp-implement` route selected an executable lane,
  without recording a `leader-inline-fallback` reason.
- Dispatching raw task text without a validated `WorkerTaskPacket`.
- Asking the user to open separate terminals when native subagents are available
  in the current runtime.
- Treating an idle subagent as done work.
- Accepting a handoff that lacks verification evidence or changed-file summary.
- Skipping spec compliance review.
- Running code quality review before spec compliance review.
- Updating `tasks.md`, quick status, or workflow state as complete before the
  structured handoff and validation evidence exist.
