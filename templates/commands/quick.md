---
description: Use when a task is small but non-trivial and needs lightweight tracked planning, validation, or resumable execution outside the full workflow.
workflow_contract:
  when_to_use: The task is too large or risky for `sp-fast` but does not justify the full `specify -> plan -> tasks -> implement` flow.
  primary_objective: Keep the task resumable and tracked while applying only the minimum planning, research, and validation depth it needs.
  primary_outputs: '`.planning/quick/<id>-<slug>/STATUS.md`, quick-task summary artifacts, and the scoped implementation changes for the task.'
  default_handoff: Resume the quick task until resolved, or escalate to /sp-specify if the scope grows into multi-capability or acceptance-criteria-heavy work.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/quick/shell.md}}

## Leader Role

- You are the quick-task leader. You own scope control, `STATUS.md`, lane selection, join points, validation, and the final summary artifact.
- You are not the default worker for the quick task. Once scope is locked and a delegated path is available, dispatch the lane instead of continuing leader-local implementation work.
- Treat `single-lane` as one delegated worker lane, not as permission to personally do the task.
- Treat legacy `single-agent` state values as compatibility aliases for the same delegated single-lane path.
- Use leader-local execution only through the documented exception path and record the fallback reason in `STATUS.md`.

## Required Context Inputs

- Read `.specify/memory/constitution.md` first if present. This is the first hard gate for every quick task.
- [AGENT] Run `specify learning start --command quick --format json` when available so passive learning files exist, the current quick-task run sees relevant shared project memory, and repeated non-high-signal candidates can be auto-promoted into shared learnings at start.
- Read `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md` after the constitution gate and before broader quick-task context.
- If `.planning/learnings/candidates.md` still contains relevant entries after the passive start step, inspect only the entries relevant to the touched area so repeated pitfalls, workflow gaps, and project constraints are not rediscovered from scratch.
- Check whether `.specify/project-map/status.json` exists.
- If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
- [AGENT] If freshness is `missing` or `stale`, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
- [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the touched area, run `/sp-map-codebase` before continuing. If only `review_topics` are non-empty, review those topical files before proceeding and refresh the map if they still look insufficient for the quick task.
- [AGENT] Read `PROJECT-HANDBOOK.md` after the constitution gate and before any broad repository analysis.
- [AGENT] If `PROJECT-HANDBOOK.md` or the required `.specify/project-map/` files are missing, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
- Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- Treat quick-task routing as a coverage-model check, not just a presence check. Coverage is also insufficient when the handbook/project-map set cannot yet tell you:
  - owning or truth-owning surfaces
  - change-propagation hotspots
  - verification entry points
  - known unknowns or stale evidence boundaries for the touched area
- [AGENT] If task-relevant coverage is insufficient for the current quick task, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
- Use `Topic Map` to choose only the touched-area topical files needed for the current quick task.
- Use the loaded handbook/project-map coverage to name the touched area's owning surfaces, change-propagation hotspots, verification entry points, and known unknowns before choosing the quick-task lane shape.
- Do not load the full topical map unless the task expands beyond its bounded quick-task scope.
- Do not create or update `STATUS.md`, ask clarifying questions, choose lanes, dispatch workers, or analyze repository code until the constitution has been read or confirmed absent.
- [AGENT] Create or resume `STATUS.md` at `.planning/quick/<id>-<slug>/STATUS.md` before any substantial repository analysis, planning, or implementation work. If the workspace does not exist yet, initialize it first and then continue.
- Read `.planning/quick/<id>-<slug>/STATUS.md` before each resumed action; treat it as the quick-task source of truth.
- Treat `.planning/quick/index.json` as the derived quick-task index used for list, status, resume, close, and archive operations. If the index is stale or missing, rebuild it from `STATUS.md` files instead of treating it as the primary truth source.
- Read only the minimum local context required to determine scope, safe lane shape, and the first execution strategy before dispatch.
- If the quick task touches an existing feature area with local planning artifacts, read the most relevant nearby `spec.md`, `plan.md`, `tasks.md`, or `context.md` files when they materially constrain behavior.
- `sp-quick <description>` creates a new quick task.
- Empty `sp-quick` checks for unfinished quick tasks first. If exactly one unfinished task exists, resume it automatically. If multiple unfinished tasks exist, ask the user which quick task to continue and show `id`, title, current status, and `next_action`.
- Treat `blocked` quick tasks as resumable unfinished work for recovery routing.

## Scope Gate

Use `sp-quick` when all of these are true:
- The task is bounded and clearly described.
- The work is small but non-trivial.
- A lightweight plan is useful, but a full spec package would be overhead.
- Use this path when you want to skip the full `specify -> plan -> tasks -> implement` workflow for a bounded task.
- The task does not require a new long-lived feature spec under `specs/<feature>/`.

If the task is trivial and local:
- Use `/sp-fast`.

If the task changes architecture, introduces broad product decisions, or needs a durable feature specification:
- Use `/sp-specify`.

## Escalation Triggers

Upgrade to `/sp-specify` immediately if:
- The task changes architecture or introduces cross-cutting behavior across multiple modules, workflows, or shared surfaces.
- The task touches a change-propagation hotspot, a truth-owning shared surface, or an area whose known unknowns make lightweight planning unsafe.
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
- Constitution first: read `.specify/memory/constitution.md` before workspace setup, clarification, lane selection, delegation, or local analysis.
- If the handbook navigation system is missing, rebuild it before `STATUS.md` initialization or touched-area analysis proceeds.
- Before the first delegated lane is dispatched, the leader may gather only the minimum context needed to choose scope, lane shape, and execution strategy. Do not perform broad repository analysis or implementation design locally before creating `STATUS.md` and selecting the first worker path.
- Before implementation work starts, identify whether the quick task is best handled as one bounded worker lane or as two or more independent lanes that can safely proceed in parallel.
- [AGENT] Use the shared policy function before execution begins and again at each join point: `choose_execution_strategy(command_name="quick", snapshot, workload_shape)`.
- For `sp-quick`, strategy names are `single-lane`, `native-multi-agent`, `sidecar-runtime`. Treat legacy `single-agent` values as compatibility aliases for `single-lane`.
- Treat `snapshot.delegation_confidence` as a runtime/model reliability signal for the current native worker path. If confidence is `low`, prefer sidecar or explicit fallback over fragile native dispatch.
- Decision order:
  - If the quick task has only one safe lane, or the lanes share mutable state or write surfaces -> `single-lane` (`no-safe-batch`)
  - Else if `snapshot.native_multi_agent` and `snapshot.delegation_confidence` is not `low` -> `native-multi-agent` (`native-supported`)
  - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing` or `native-low-confidence`)
  - Else -> `single-lane` (`fallback` or `fallback-low-confidence`)
- `single-lane` still means one delegated worker lane, not leader self-execution.
- In plain terms: single-lane still means one delegated worker lane.
- `native-multi-agent` means the leader dispatches independent bounded lanes through the integration's native delegation surface and rejoins at an explicit join point.
- `sidecar-runtime` means the leader escalates the execution batch through the integration's coordinated runtime surface when native delegation is unavailable.
- Default execution for both `single-lane` and `native-multi-agent` stays on delegated worker lanes. The leader coordinates; it does not become the worker just because the task is small.
- If two or more independent delegated lanes can safely run in parallel and that fan-out materially improves throughput, prefer launching multiple worker lanes over serial single-lane execution.
- Leader-local execution is an exception path, not a strategy choice. Use it only when the current quick-task batch cannot proceed through native delegation and cannot proceed through the coordinated runtime surface either.
- If leader-local execution is used, record the concrete reason in `STATUS.md`, including which delegation path was unavailable or blocked for the current batch.
- The first actionable execution step after scope lock is to dispatch the first delegated worker lane or coordinated runtime batch, not to continue local deep-dive analysis.
- Use `.specify/templates/worker-prompts/quick-worker.md` as the default contract for delegated quick-task lanes so the worker returns enough state for the leader to keep `STATUS.md` accurate.
- Prefer structured delegated results compatible with the shared `WorkerTaskResult` contract when the current runtime supports them.
- If the current integration exposes a runtime-managed result channel, use that channel. Otherwise write the normalized delegated result envelope to `.planning/quick/<id>-<slug>/worker-results/<lane-id>.json`
- When the local CLI is available and no runtime-managed result channel exists, prefer `specify result path` to compute the canonical handoff target and `specify result submit` to normalize and write the delegated result envelope.
- Preserve `reported_status` when normalizing worker language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` into canonical orchestration state.
- Idle delegated worker is not an accepted result.
- The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting delegated execution.

## Quick-Task Workspace Protocol

- Every quick task must have a dedicated id-based workspace under `.planning/quick/<id>-<slug>/`.
- If a matching active workspace already exists, resume it instead of creating a second parallel quick-task directory for the same goal.
- The minimum artifact set is:
  - `STATUS.md`: the source of truth for the current quick-task state.
  - `SUMMARY.md`: the final outcome, changed files, and verification evidence.
  - Optional lightweight support artifacts only when needed for the task shape, such as `PLAN.md`, `RESEARCH.md`, or `DISCUSSION.md`.
- `STATUS.md` is the lifecycle source of truth for the quick task. `.planning/quick/index.json` is a derived projection for management and recovery commands.
- The quick-task directory format is `<id>-<slug>`. Do not use slug-only workspace names for the enhanced quick flow.
- Constitution read is the first hard gate. `STATUS.md` initialization comes immediately after it.
- `STATUS.md` must stay compact and overwrite the active state rather than growing into a long log. It must always make these fields obvious:
  - current focus
  - execution strategy
  - active lane or batch
  - join point, if any
  - execution fallback, if any
  - next action
  - recovery action
  - retry attempts
  - blocker reason
  - blockers, if any
- Update `STATUS.md` before each material phase transition: after scope lock, after planning, before delegation, after each join point, before validation, and before final summary.
- After the constitution gate, `STATUS.md` initialization is the next hard gate. Do not perform substantial repository analysis, implementation design, or code reading beyond scope-lock context until the workspace exists and the first lane is recorded.
- When the quick task completes, preserve `SUMMARY.md` and move resolved state under `.planning/quick/resolved/` if the local project convention prefers archiving over keeping active quick-task folders in place.

## STATUS.md Template

Use this as the default structure for `.planning/quick/<id>-<slug>/STATUS.md`:

```markdown
---
id: [quick-task id]
slug: [quick-task slug]
title: [short quick-task title]
status: gathering | planned | executing | validating | blocked | resolved
trigger: "[verbatim user input]"
strategy: single-lane | native-multi-agent | sidecar-runtime
created: [ISO timestamp]
updated: [ISO timestamp]
---

## Current Focus
<!-- OVERWRITE on each update -->

goal: [bounded quick-task objective]
current_focus: [what the leader is doing now]
next_action: [immediate next step]

## Execution Intent
<!-- OVERWRITE/REFINE when the lane shape or validation target changes -->

intent_outcome: [the bounded behavior change or recovery target for this quick task]
intent_constraints:
  - [constraints, forbidden drift, or scope boundaries that must stay active]
success_evidence:
  - [the checks or observations required before the quick task can be treated as resolved]

## Execution
<!-- OVERWRITE/REFINE as the lane or batch changes -->

active_lane: [single lane name or current batch]
join_point: [empty if none]
files_or_surfaces: [primary files, modules, or shared surfaces in play]
execution_fallback: [none by default; if leader-local, record why native and sidecar paths were unavailable]
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

summary_path: [.planning/quick/<id>-<slug>/SUMMARY.md]
resume_decision: [resume here | blocked waiting | resolved]
```

## Recovery Routing

- `sp-quick <description>` creates a new quick task.
- Empty `sp-quick` should look for unfinished quick tasks before asking for a new description.
- If exactly one unfinished quick task exists, resume it automatically.
- If multiple unfinished quick tasks exist, ask the user which quick task to continue.
- The selection list should show `id`, title, current status, and `next_action`.
- Treat `gathering`, `planned`, `executing`, `validating`, and `blocked` as unfinished quick-task states for recovery routing.
- If resuming a `blocked` quick task, prioritize `blocker_reason`, `recovery_action`, and `next_action` before widening scope.

## Lifecycle Commands

- `close` controls lifecycle semantics. Use it to place a quick task into `resolved` or `blocked`.
- `archive` controls storage semantics. Use it only after the quick task has already been closed.
- Do not treat archive as an implied synonym for resolved. Closure says what happened; archive says where the closed task now lives.

## Autonomous Execution Contract

- The leader must continue automatically until the quick task is complete or a concrete blocker prevents further safe progress.
- Do not stop after a single edit, single command, or single failed attempt when the next recovery step is obvious and low-risk.
- Prefer the integration's native delegation surface when `snapshot.native_multi_agent` is true and the workload has two or more safe lanes; if there is only one safe lane, `single-lane` remains valid.
- Treat `single-lane` as a delegated single-worker path by default. Do not reinterpret it as leader self-execution just because only one lane is safe.
- After `STATUS.md` is initialized and the first lane is defined, dispatch that worker path before doing any further local repository deep dive.
- If multiple safe delegated lanes exist and they can improve throughput without creating write-surface conflicts, dispatch them in parallel instead of artificially serializing the work.
- Use leader-local execution only as a constrained fallback after delegated execution is concretely unavailable for the current batch and the coordinated runtime surface is also unavailable or unsuitable.
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
- If delegated execution is failing, attempt the next safe execution surface before switching to leader-local work:
  - retry the bounded delegated lane when the failure looks transient
  - escalate to the coordinated runtime surface when native delegation is unavailable for the current batch
  - only then consider leader-local fallback if no worker path is currently available
- Escalate to `blocked` only when:
  - required credentials, services, permissions, or external systems are unavailable
  - the requirement remains high-impact ambiguous after the minimum safe clarification pass
  - repeated focused recovery attempts still leave no safe next step
  - the next action would be high-risk or destructive without user confirmation
- When blocked, write the concrete blocker reason to `blocker_reason`, preserve the best known next action, and stop only after the blocker is explicit.

## Surface Sweep Rule

- Treat every quick task as a small-scope complete sweep, not as an opportunistic one-file patch.
- Before editing, name the affected surfaces for this pass. Start from the smallest relevant set and expand until the task has a defendable boundary.
- Include propagation hotspots, consumer surfaces, verification entry points, and known unknowns from the handbook/project-map coverage whenever they materially affect the quick task.
- For interface or contract changes, default sweep surfaces are:
  - implementation
  - export or declaration layer
  - docs
  - examples
  - tests
  - key callsites or consuming paths
- For other quick tasks, still name the concrete surfaces in play rather than implying coverage from a partial read.
- The leader must be able to say which surfaces were intentionally checked before claiming completion.
- For each named surface, record one explicit status conclusion:
  - `confirmed correct`
  - `fixed in this quick task`
  - `not checked in this pass (with reason)`
- Do not collapse `not checked` into silence. If a surface was not verified, say so explicitly and explain why it stayed outside the current pass.

## Completion Standard

- Quick completion means a small, transparent closed loop: sweep the affected surfaces, make the required change, run at least one meaningful verification step, and record the resulting coverage truthfully.
- Completion requires all three:
  - the change itself is implemented in code, docs, config, or templates as needed
  - at least one smallest meaningful executable verification step has run
  - any unverified surface or remaining gap is called out explicitly instead of being implied away
- `should be fine`, `likely unaffected`, or `not expected to break` are not completion evidence.
- If the change is implemented but verification or coverage is incomplete, do not claim the task is complete. Mark the remaining gap explicitly and continue the sweep or leave the task blocked with the concrete reason.
- If the quick task changed truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-codebase` before marking the quick task `resolved` so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/status.json` are refreshed in the same pass.
- If you cannot complete that refresh in the current pass, mark `.specify/project-map/status.json` dirty through the project-map freshness helper and recommend `/sp-map-codebase` before the next brownfield workflow proceeds.

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
- `All affected surfaces` means the declared sweep set, not just the files already inspected.

## Output Contract

- Keep `STATUS.md` accurate enough that another session can resume without chat memory.
- Produce scoped implementation changes, verification evidence, and a truthful resolved/blocked state for the quick task.
- Preserve escalation history so it is clear why the task stayed quick or needed to grow.

## Process

1. **Scope gate**
   - Read `.specify/memory/constitution.md` first if present. Do not continue until this gate is satisfied.
   - Confirm the task is small but non-trivial.
   - Redirect to `/sp-fast` or `/sp-specify` if the task is outside the quick-task band.

2. **Create lightweight quick-task context**
   - Create or resume an id-based workspace under `.planning/quick/<id>-<slug>/`.
   - Keep quick-task artifacts separate from the main phase/spec workflow.
   - Initialize `STATUS.md` as the recoverable source of truth for the quick task.
   - Rebuild or refresh `.planning/quick/index.json` as a derived management projection when needed.
   - Do not continue into broad repository analysis or implementation planning until this workspace exists and the initial lane or batch is recorded.

3. **Optional pre-execution phases**
   - If `--discuss` is present, clarify assumptions and lock the minimum decisions needed.
   - If `--research` is present, gather focused implementation guidance.

4. **Lightweight planning**
   - Produce only the plan needed to execute this ad-hoc task safely.
   - Keep the work atomic and self-contained.
   - Keep local planning shallow until the first delegated worker lane or coordinated runtime batch has been launched.
   - Identify the smallest safe execution lanes and choose the current execution strategy before implementation starts.
   - For behavior-changing work, bug fixes, and refactors, the first executable lane must produce a failing automated test or failing repro check before production edits begin.
   - Do not write production code until the RED state is captured and recorded in `STATUS.md`.
   - If no reliable automated test surface exists for the touched behavior, bootstrap the smallest viable test surface first. If that bootstrap is no longer a bounded quick-task step, stop and escalate to `/sp-test`.
   - Name the affected surfaces for this quick-task pass and decide how each one will be checked.
   - If multiple safe lanes would materially improve throughput, plan the first fan-out as parallel worker lanes instead of defaulting to serial execution.
   - If the task includes a propagating change, write the minimal sweep plan first and list the affected surfaces that must be checked before completion.

5. **Execution**
   - Execute the current quick-task lane or ready batch through the selected strategy.
   - For `single-lane`, dispatch one delegated worker lane rather than executing locally.
   - The first concrete execution action should normally be dispatching that delegated lane or coordinated runtime batch, not continuing leader-local repository analysis.
   - If multiple delegated lanes are safe and useful, dispatch them in parallel as the current ready batch instead of holding back fan-out without a concrete coordination reason.
   - Keep changes tightly scoped to the quick-task goal.
   - Re-evaluate strategy at each join point instead of assuming the first choice remains correct.
   - Only use leader-local execution after both delegated execution paths are unavailable or blocked for the current batch, and record that fallback explicitly in `STATUS.md`.
   - Continue automatically until the quick task is complete or a concrete blocker prevents further safe progress.
   - If execution hits friction, attempt the smallest safe recovery step before declaring the task blocked.

6. **Validation**
   - If `--validate` or `--full` is present, perform plan checking and post-execution verification.
   - Otherwise still verify the change with the smallest meaningful executable check.
   - Do not skip verification just because the quick-task scope is small.

7. **Summary**
   - Write a concise summary artifact for what changed, how it was verified, and which surfaces were left unverified.
   - Prefer `SUMMARY.md` in `.planning/quick/<id>-<slug>/`.
   - Separate `verified` coverage from `not checked` coverage so readers can tell what was actually proven versus what is only expected to be safe.
   - For each declared surface, give the terminal status conclusion: `confirmed correct`, `fixed in this quick task`, or `not checked in this pass (with reason)`.
   - Make sure the final `STATUS.md` points to the summary, records the terminal state, and makes a future resume decision obvious.
   - [AGENT] Before the final summary, capture any new `pitfall`, `recovery_path`, or `project_constraint` learning through `specify learning capture --command quick ...`.
   - Keep lower-signal items as candidates and use `specify learning promote --target learning ...` only after explicit confirmation or proven recurrence.
   - Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.

## Guardrails

- Do not create a new full feature spec for quick tasks.
- Keep quick-task tracking under `.planning/quick/`.
- Preserve a lightweight planning and validation path rather than skipping discipline entirely.
- Keep quick tasks atomic and self-contained.
- Keep leader responsibilities explicit: scope, strategy selection, join points, validation, and summary stay on the leader path.
- Keep concrete execution on delegated worker lanes whenever possible. Leader-local execution is the last fallback, not the default reading of `single-lane`.
- Quick-task state must be resumable from `STATUS.md` without depending on chat history.
