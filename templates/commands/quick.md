---
description: Use when a task is small but non-trivial and needs lightweight tracked planning, validation, or resumable execution outside the full workflow.
workflow_contract:
  when_to_use: The task is too large or risky for `sp-fast` but does not justify the full `specify -> plan -> tasks -> implement` flow.
  primary_objective: Keep the task resumable and tracked while applying only the minimum planning, research, and validation depth it needs.
  primary_outputs: '`.planning/quick/<id>-<slug>/STATUS.md`, quick-task summary artifacts, and the scoped implementation changes for the task.'
  default_handoff: 'Resume the quick task until resolved, or escalate to /sp.specify if the scope grows into multi-capability or acceptance-criteria-heavy work.'
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/quick/shell.md}}

## Mandatory Subagent Execution

{{spec-kit-include: ../command-partials/common/dispatch-mode-gradient.md}}

**This command tier: light. Dispatch mode: subagent-preferred.**

Dispatch to one subagent with a task contract. If subagent dispatch is unavailable, record reason and fall back to leader-inline.


## Leader Role

- You are the workflow leader and orchestrator.
- You own routing, task splitting, task contracts, dispatch, join points, integration, verification, and state updates.
- Subagents own the substantive task lanes assigned through task contracts.
- You are the quick-task leader. You own scope control, `STATUS.md`, lane selection, validation, and the final summary artifact.
- You are not the default implementer for the quick task; substantive task work belongs on subagent lanes once scope and contracts are locked.
- Use `execution_model: subagent-mandatory` once the quick task has a bounded execution lane.
- Dispatch `one-subagent` for one safe delegated lane and `parallel-subagents` for isolated lanes that can run concurrently.
- Compile a validated `WorkerTaskPacket` or equivalent execution contract before dispatch.

## Required Context Inputs

{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**Project-map hard gate:** you must pass an atlas gate before repository
analysis, implementation design, or code reads continue.

**This command tier: light.** Pass the atlas gate by reading:
1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. at least one relevant root topic document
6. at least one relevant module overview document
7. `atlas.index.relations` when Layer 1 names shared-surface or cross-module risk

After the atlas gate passes, continue into any additional root-topic or
module-local reads named by Layer 1 for the touched area.

**Freshness**: Treat `missing` and `stale` as blocking; evaluate
`possibly_stale` against `must_refresh_topics` and `review_topics` before
continuing.

Treat task-relevant coverage as insufficient when the touched area still lacks
ownership, placement, workflow, integration, or verification guidance before
choosing the quick-task lane shape.

## First-Party Workflow Quality Hooks

- Once the quick workspace exists, use `specify hook preflight --command quick --workspace ".planning/quick/<id>-<slug>"` before deeper execution so the shared product guardrail layer can block stale brownfield routing or invalid quick-task entry.
- After `STATUS.md` is created or resumed, use `specify hook validate-state --command quick --workspace ".planning/quick/<id>-<slug>"` so the shared validator confirms the quick-task source of truth is resumable.
- Use `specify hook validate-session-state --command quick --workspace ".planning/quick/<id>-<slug>"` when you need a machine-readable summary of quick-task resume truth rather than trusting chat narration.
- Before compaction-risk transitions, join points, or delegated fan-out, use `specify hook monitor-context --command quick --workspace ".planning/quick/<id>-<slug>"` and follow checkpoint recommendations with `specify hook checkpoint --command quick --workspace ".planning/quick/<id>-<slug>"`.
- When you want a compact operator-facing summary instead of re-reading the whole file, use `specify hook render-statusline --command quick --workspace ".planning/quick/<id>-<slug>"`.

## Scope Gate

Use `sp-quick` when all of these are true:
- The task is bounded and clearly described.
- The work is small but non-trivial.
- A lightweight plan is useful, but a full spec package would be overhead.
- Use this path when you want to skip the full `specify -> plan -> tasks -> implement` workflow for a bounded task.
- The task does not require a new long-lived feature spec under `specs/<feature>/`.

If the task is trivial and local:
- Use `{{invoke:fast}}`.

If the task changes architecture, introduces broad product decisions, or needs a durable feature specification:
- Use `{{invoke:specify}}`.

If the task is a bug fix or regression but the root cause is still unknown:
- Use `{{invoke:debug}}` instead of treating `sp-quick` as a symptom-fix lane.

## Escalation Triggers

Upgrade to `{{invoke:specify}}` immediately if:
- The task changes architecture or introduces cross-cutting behavior across multiple modules, workflows, or shared surfaces.
- The task touches a change-propagation hotspot, a truth-owning shared surface, or an area whose known unknowns make lightweight planning unsafe.
- The request now spans multiple independent capabilities, release tracks, or user journeys that no longer fit one bounded quick-task workspace.
- The request is still a testing-system program from `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` rather than one bounded module, risk tranche, or coverage wave.
- The work needs a new durable spec package, a long-lived feature boundary, or planning artifacts intended to survive beyond the quick task.
- The change has rollout, migration, compatibility, or neighboring-workflow impact that must be locked before implementation.
- The expected behavior cannot be stated with concrete acceptance criteria without first doing feature-level requirement alignment.
- The work started as a bug fix, but root-cause analysis is still unresolved, competing causes are still plausible, or the next safe step is diagnostic investigation rather than a bounded repair. In that case, route to `{{invoke:debug}}`.

## Execution Modes

The following flags are available and composable:
- `--discuss`: Do a lightweight clarification pass before planning.
- `--research`: Investigate implementation approaches before planning.
- `--validate`: Add plan checking and post-execution verification.
- `--full`: Equivalent to `--discuss --research --validate`.

## Coordinator Model

- The invoking runtime is the leader for the quick task. It owns scope decisions, the lightweight plan, execution strategy selection, join-point handling, validation, and the final summary artifact.
- The leader should not blur planning, execution, and validation into a long conversational loop when the task can be dispatched through a bounded subagent.
- Constitution first: read `.specify/memory/constitution.md` before workspace setup, clarification, lane selection, subagent dispatch, or local analysis.
- If the handbook navigation system is missing, rebuild it before `STATUS.md` initialization or touched-area analysis proceeds.
- Before the first subagent is dispatched, the leader may gather only the minimum context needed to choose scope, lane shape, and execution strategy. Do not perform broad repository analysis or implementation design locally before creating `STATUS.md` and selecting the first subagent path.
- Before implementation work starts, identify whether the quick task is best handled by one bounded subagent or by two or more independent subagents that can safely proceed in parallel.
- [AGENT] Use the shared policy function before execution begins and again at each join point: `choose_subagent_dispatch(command_name="quick", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
- Treat `snapshot.delegation_confidence` as a runtime/model reliability signal for the current subagent path. If confidence is `low`, prefer the native subagent workflow or record `subagent-blocked` over fragile dispatch.
- Decision order:
  - One safe validated lane -> `one-subagent` on `native-subagents` when available.
  - Two or more safe isolated lanes -> `parallel-subagents` on `native-subagents` when available.  - No safe lane, overlapping writes, missing contract, low confidence, or unavailable delegation -> `subagent-blocked` with a recorded reason.
- Substantive quick-task lanes must use subagent execution once a validated `WorkerTaskPacket` or equivalent execution contract preserves quality. If that readiness bar is not met, compile the missing contract before dispatch; if the contract cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
- If two or more independent subagent lanes can safely run in parallel and that fan-out materially improves throughput, dispatch multiple subagents instead of serial execution.
- `subagent-blocked` is an exception path, not a strategy choice. Use it only when the current quick-task batch cannot proceed through subagents or the native subagent workflow.
- If subagent-blocked status is used, record the concrete reason in `STATUS.md`, including which subagent path was unavailable or blocked for the current batch.
- The first actionable execution step after scope lock is to dispatch the first subagent batch, not to continue local deep-dive analysis.
- Use `.specify/templates/worker-prompts/quick-worker.md` as the default contract for quick-task subagents so the subagent returns enough state for the leader to keep `STATUS.md` accurate.
- Prefer structured subagent results compatible with the shared `WorkerTaskResult` contract when the current runtime supports them.
- If the current integration exposes a runtime-managed result channel, use that channel. Otherwise write the normalized subagent result envelope to `.planning/quick/<id>-<slug>/worker-results/<lane-id>.json`
- When the local CLI is available and no runtime-managed result channel exists, prefer `specify result path` to compute the canonical handoff target and `specify result submit` to normalize and write the subagent result envelope.
- Preserve `reported_status` when normalizing subagent language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` into canonical orchestration state.
- Idle subagent is not an accepted result.
- The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution.

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
  - blocked dispatch or escalation state, if any
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
execution_model: subagent-mandatory
dispatch_shape: one-subagent | parallel-subagents
execution_surface: native-subagents
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
blocked_dispatch: [none by default; if subagent-blocked, record why native subagent dispatch was unavailable or unsafe]
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
- Dispatch subagents when `snapshot.native_subagents` is true and the workload has one or more safe validated lanes.
- Substantive quick-task lanes must use subagent execution once a validated `WorkerTaskPacket` or equivalent execution contract preserves quality. If that readiness bar is not met, finish compiling the missing contract first; if the contract cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
- After `STATUS.md` is initialized and the first lane is defined, dispatch that subagent path before doing any further local repository deep dive.
- If multiple safe subagent lanes exist and they can improve throughput without creating write conflicts, dispatch them in parallel instead of artificially serializing the work.
- Use `subagent-blocked` only after subagent execution is concretely unavailable for the current batch and the native subagent workflow is also unavailable or unsuitable.
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
- If subagent execution is failing, attempt the next safe path before switching to subagent-blocked status:
  - retry the bounded subagent lane when the failure looks transient
  - use the native subagent workflow when subagent dispatch is unavailable for the current batch
  - only then consider subagent-blocked status if no subagent path is currently available
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
- If the quick task changed truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-scan` followed by `/sp-map-build` before marking the quick task `resolved` so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/index/status.json` are refreshed in the same pass.
- If you cannot complete that refresh in the current pass, mark `.specify/project-map/index/status.json` dirty through the project-map freshness helper and recommend `/sp-map-scan` followed by `/sp-map-build` before the next brownfield workflow proceeds.

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

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

**This command tier: light.** Auto-capture learnings on resolution only. No review, no signal.

## Process

1. **Scope gate**
   - Read `.specify/memory/constitution.md` first if present. Do not continue until this gate is satisfied.
   - Confirm the task is small but non-trivial.
   - Redirect to `{{invoke:fast}}` or `{{invoke:specify}}` if the task is outside the quick-task band.

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
   - Keep local planning shallow until the first subagent batch has been launched.
   - If `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` is the upstream source, record which single module, risk tranche, or coverage wave this quick-task pass is consuming before implementation starts.
   - Identify the smallest safe execution lanes and choose the current execution strategy before implementation starts.
- For behavior-changing work, bug fixes, and refactors, the first executable lane must produce a failing automated test or failing repro check before production edits begin.
- Do not write production code until the RED state is captured and recorded in `STATUS.md`.
- If no reliable automated test surface exists for the touched behavior, bootstrap the smallest viable test surface first. If that bootstrap is no longer a bounded quick-task step, stop and escalate to `{{invoke:test}}` or directly to `{{invoke:test-scan}}`.
- For bug fixes and regressions, record the current root-cause explanation before implementation starts. If the root cause is not yet known, or if multiple plausible causes are still in play, stop and route to `{{invoke:debug}}` instead of applying a quick symptom patch.
- A `surface-only` or symptom-only change cannot satisfy the quick-task contract for a bug fix unless the user explicitly scoped the work to temporary mitigation.
- Name the affected surfaces for this quick-task pass and decide how each one will be checked.
   - If multiple safe lanes would materially improve throughput, plan the first fan-out as parallel subagents instead of defaulting to serial execution.
   - If the task includes a propagating change, write the minimal sweep plan first and list the affected surfaces that must be checked before completion.

5. **Execution**
   - Execute the current quick-task lane or ready batch through the selected dispatch shape and execution surface.
   - For `one-subagent`, dispatch one subagent once the subagent-readiness bar is satisfied; otherwise finish compiling the missing contract before dispatch. If the contract cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
   - The first concrete execution action should normally be dispatching that subagent batch, not continuing local repository analysis.
   - If multiple subagent lanes are safe and useful, dispatch them in parallel as the current ready batch instead of holding back fan-out without a concrete coordination reason.
   - Keep changes tightly scoped to the quick-task goal.
   - Re-evaluate dispatch at each join point instead of assuming the first choice remains correct.
   - Only use `subagent-blocked` after subagent execution and the native subagent workflow are unavailable or blocked for the current batch, and record the blocked dispatch reason explicitly in `STATUS.md`.
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

## Guardrails

- Do not create a new full feature spec for quick tasks.
- Keep quick-task tracking under `.planning/quick/`.
- Preserve a lightweight planning and validation path rather than skipping discipline entirely.
- Keep quick tasks atomic and self-contained.
- Keep leader responsibilities explicit: the leader owns scope, strategy selection, join points, validation, and summary while substantive task work remains packetized for subagent lanes.
- Keep concrete execution on subagent lanes whenever possible. `subagent-blocked` is the final blocked status after recovery options are exhausted, not the default path.
- Quick-task state must be resumable from `STATUS.md` without depending on chat history.
