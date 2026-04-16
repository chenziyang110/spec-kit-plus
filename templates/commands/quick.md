---
description: Execute a small ad-hoc task through a lightweight planning and validation path.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

## Objective
Execute a small, ad-hoc task through a lightweight planning and validation path without entering the full `specify -> plan -> tasks` workflow.

This command will skip the full feature-spec workflow while preserving lightweight planning and verification.

Use this for work that is too large for `sp-fast` but still too small or too well understood to justify a full spec flow: small bug fixes, small features, focused UX adjustments, template tweaks, or narrow CLI behavior changes.

## Required Context Inputs

- Read `.specify/memory/constitution.md` if present before planning or implementation so the quick task honors project-level MUST/SHOULD constraints.
- Read `.planning/quick/<slug>/STATUS.md` before each resumed action; treat it as the quick-task source of truth.
- Read the smallest relevant local code and documentation context needed to avoid guesswork for the current task shape.
- If the quick task touches an existing feature area with local planning artifacts, read the most relevant nearby `spec.md`, `plan.md`, `tasks.md`, or `context.md` files when they materially constrain behavior.

## Scope Gate

Use `sp-quick` when all of these are true:
- The task is bounded and clearly described.
- The work is small but non-trivial.
- A lightweight plan is useful, but a full spec package would be overhead.
- The task does not require a new long-lived feature spec under `specs/<feature>/`.

If the task is trivial and local:
- Use `/sp-fast`.

If the task changes architecture, introduces broad product decisions, or needs a durable feature specification:
- Use `/sp-specify`.

## Escalation Triggers

Upgrade to `/sp-specify` immediately if:
- The task changes architecture or introduces cross-cutting behavior across multiple modules, workflows, or shared surfaces.
- The request now spans multiple independent capabilities, release tracks, or user journeys that no longer fit one bounded quick-task workspace.
- The work needs a new durable spec package, a long-lived feature boundary, or planning artifacts intended to survive beyond the quick task.
- The change has rollout, migration, compatibility, or neighboring-workflow impact that must be locked before implementation.
- The expected behavior cannot be stated with concrete acceptance criteria without first doing feature-level requirement alignment.

## Execution Modes

The following flags are available and composable:
- `--discuss`: Do a lightweight clarification pass before planning.
- `--research`: Investigate implementation approaches before planning.
- `--validate`: Add plan checking and post-execution verification.
- `--full`: Equivalent to `--discuss --research --validate`.

## Leader Execution Model

- The invoking runtime is the leader for the quick task. It owns scope decisions, the lightweight plan, execution strategy selection, join-point handling, validation, and the final summary artifact.
- The leader should not blur planning, execution, and validation into a long conversational loop when the task can be dispatched through a bounded worker lane or runtime surface.
- Before implementation work starts, identify whether the quick task is best handled as one bounded worker lane or as two or more independent lanes that can safely proceed in parallel.
- Use the shared policy function before execution begins and again at each join point: `choose_execution_strategy(command_name="quick", snapshot, workload_shape)`.
- Strategy names are canonical and must be used exactly: `single-agent`, `native-multi-agent`, `sidecar-runtime`.
- Decision order:
  - If the quick task has only one safe lane, or the lanes share mutable state or write surfaces -> `single-agent` (`no-safe-batch`)
  - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
  - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
  - Else -> `single-agent` (`fallback`)
- `single-agent` still means one delegated worker lane, not leader self-execution.
- In plain terms: single-agent still means one delegated worker lane.
- `native-multi-agent` means the leader dispatches independent bounded lanes through the integration's native delegation surface and rejoins at an explicit join point.
- `sidecar-runtime` means the leader escalates the execution batch through the integration's coordinated runtime surface when native delegation is unavailable.

## Quick-Task Workspace Protocol

- Every quick task must have a dedicated slugged workspace under `.planning/quick/<slug>/`.
- If a matching active workspace already exists, resume it instead of creating a second parallel quick-task directory for the same goal.
- The minimum artifact set is:
  - `STATUS.md`: the source of truth for the current quick-task state.
  - `SUMMARY.md`: the final outcome, changed files, and verification evidence.
  - Optional lightweight support artifacts only when needed for the task shape, such as `PLAN.md`, `RESEARCH.md`, or `DISCUSSION.md`.
- `STATUS.md` must stay compact and overwrite the active state rather than growing into a long log. It must always make these fields obvious:
  - current focus
  - execution strategy
  - active lane or batch
  - join point, if any
  - next action
  - recovery action
  - retry attempts
  - blocker reason
  - blockers, if any
- Update `STATUS.md` before each material phase transition: after scope lock, after planning, before delegation, after each join point, before validation, and before final summary.
- When the quick task completes, preserve `SUMMARY.md` and move resolved state under `.planning/quick/resolved/` if the local project convention prefers archiving over keeping active quick-task folders in place.

## STATUS.md Template

Use this as the default structure for `.planning/quick/<slug>/STATUS.md`:

```markdown
---
slug: [quick-task slug]
status: gathering | planned | executing | validating | blocked | resolved
trigger: "[verbatim user input]"
strategy: single-agent | native-multi-agent | sidecar-runtime
created: [ISO timestamp]
updated: [ISO timestamp]
---

## Current Focus
<!-- OVERWRITE on each update -->

goal: [bounded quick-task objective]
current_focus: [what the leader is doing now]
next_action: [immediate next step]

## Execution
<!-- OVERWRITE/REFINE as the lane or batch changes -->

active_lane: [single lane name or current batch]
join_point: [empty if none]
files_or_surfaces: [primary files, modules, or shared surfaces in play]
blockers: [empty if none]
recovery_action: [next self-recovery step before asking for help]
retry_attempts: [0 if none]
blocker_reason: [empty if none]

## Validation
<!-- OVERWRITE/REFINE as checks complete -->

planned_checks:
  - [smallest meaningful verification command or manual check]
completed_checks:
  - [verification already run]

## Summary Pointer
<!-- OVERWRITE when terminal state is reached -->

summary_path: [.planning/quick/<slug>/SUMMARY.md]
resume_decision: [resume here | blocked waiting | resolved]
```

## Autonomous Execution Contract

- The leader must continue automatically until the quick task is complete or a concrete blocker prevents further safe progress.
- Do not stop after a single edit, single command, or single failed attempt when the next recovery step is obvious and low-risk.
- Prefer the integration's native delegation surface when `snapshot.native_multi_agent` is true and the workload has two or more safe lanes; if there is only one safe lane, `single-agent` remains valid.
- Re-evaluate after every join point, recovery step, and validation result instead of assuming the first plan still holds.
- A quick task reaches a terminal state only when `STATUS.md` shows either `resolved` or `blocked`.

## Recovery Before Blocking

- When execution hits friction, attempt the smallest safe recovery step before declaring the task blocked.
- Default recovery order:
  - read additional local context that directly touches the failing area
  - run the smallest meaningful verification or repro command
  - inspect the immediate error output, logs, or failing test result
  - make one focused repair attempt that matches the evidence
  - if uncertainty remains high, use `--research`-style focused investigation for the narrow blocker rather than abandoning the task immediately
- Record each recovery step in `STATUS.md` under `recovery_action` and increment `retry_attempts`.
- Escalate to `blocked` only when:
  - required credentials, services, permissions, or external systems are unavailable
  - the requirement remains high-impact ambiguous after the minimum safe clarification pass
  - repeated focused recovery attempts still leave no safe next step
  - the next action would be high-risk or destructive without user confirmation
- When blocked, write the concrete blocker reason to `blocker_reason`, preserve the best known next action, and stop only after the blocker is explicit.

## Propagating Change Rule

- Treat interface signature changes, return-type changes, sync-to-async conversions, renamed commands, renamed config keys, path changes, and similar high-spread edits as a propagating change.
- For any propagating change, the leader must write a minimal plan before editing.
- That plan must name the affected surfaces to sweep, at minimum:
  - implementation
  - wrappers or bindings
  - examples
  - tests
  - docs
  - callsites
- Do not collapse a propagating change into ad-hoc search-and-edit work. The leader must be able to state what will be checked and how completion will be proven.

## Coverage Before Completion

- For propagating changes, sampling is not sufficient.
- Completion requires either:
  - a full-coverage check of every affected callsite or surface
  - or a scripted or pattern-based verification that covers the entire affected set
- If the current pass only covers representative examples, do not claim completion.
- If coverage is still incomplete, continue the sweep, add stronger search or verification, or mark the task blocked with the exact remaining gap.

## Process

1. **Scope gate**
   - Confirm the task is small but non-trivial.
   - Redirect to `/sp-fast` or `/sp-specify` if the task is outside the quick-task band.

2. **Create lightweight quick-task context**
   - Create or resume a slugged workspace under `.planning/quick/<slug>/`.
   - Keep quick-task artifacts separate from the main phase/spec workflow.
   - Initialize `STATUS.md` as the recoverable source of truth for the quick task.

3. **Optional pre-execution phases**
   - If `--discuss` is present, clarify assumptions and lock the minimum decisions needed.
   - If `--research` is present, gather focused implementation guidance.

4. **Lightweight planning**
   - Produce only the plan needed to execute this ad-hoc task safely.
   - Keep the work atomic and self-contained.
   - Identify the smallest safe execution lanes and choose the current execution strategy before implementation starts.
   - If the task includes a propagating change, write the minimal sweep plan first and list the affected surfaces that must be checked before completion.

5. **Execution**
   - Execute the current quick-task lane or ready batch through the selected strategy.
   - Keep changes tightly scoped to the quick-task goal.
   - Re-evaluate strategy at each join point instead of assuming the first choice remains correct.
   - Continue automatically until the quick task is complete or a concrete blocker prevents further safe progress.
   - If execution hits friction, attempt the smallest safe recovery step before declaring the task blocked.

6. **Validation**
   - If `--validate` or `--full` is present, perform plan checking and post-execution verification.
   - Otherwise still verify the change with the smallest meaningful check.

7. **Summary**
   - Write a concise summary artifact for what changed and how it was verified.
   - Prefer `SUMMARY.md` in `.planning/quick/<slug>/`.
   - Make sure the final `STATUS.md` points to the summary, records the terminal state, and makes a future resume decision obvious.

## Guardrails

- Do not create a new full feature spec for quick tasks.
- Keep quick-task tracking under `.planning/quick/`.
- Preserve a lightweight planning and validation path rather than skipping discipline entirely.
- Keep quick tasks atomic and self-contained.
- Keep leader responsibilities explicit: scope, strategy selection, join points, validation, and summary stay on the leader path.
- Quick-task state must be resumable from `STATUS.md` without depending on chat history.
