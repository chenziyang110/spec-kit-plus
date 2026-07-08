Trigger: before selecting or resuming implementation work.

Purpose: preserve pre-execution checks, learning intake, tracker state, blockers, validation, and execution notes.

Preserved Contract: implementation remains task-driven and resumable through tracker state, current focus, blockers, validation, and open gaps.

## Pre-Execution Checks

**Check for extension hooks (before implementation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_implement` key
{{spec-kit-include: ../../command-partials/common/extension-hooks-body.md}}

**Maintain workflow quality without hook choreography**:
- Confirm project cognition freshness, analyze-gate status, and valid execution entry before choosing a batch.
- Keep `workflow-state.md` and `implement-tracker.md` aligned so execution state, next batch, open blockers, and resume instructions stay durable.
- Validate each `WorkerTaskPacket` before dispatch and require a `WorkerTaskResult` plus structured handoff before accepting a join point.
- Update durable state before compaction-risk transitions, long validation phases, join points, subagent fan-out, or any stop where resume will depend on more than the visible conversation.
{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
- Manual map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads` for external repair cases. After a successful existing-baseline maintenance refresh, use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only for incremental freshness finalization; `sp-map-build` owns `build-from-scan` and `{{specify-subcmd:project-cognition validate-build --format json}}`, so do not run `complete-refresh` as a rebuild finalizer.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command implement --format json}}` when available so passive learning files exist and the current implementation run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader execution context.
- Open only learning detail docs linked from implementation-relevant index entries, especially repeated pitfalls, recovery paths, or project constraints for the touched area.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When implementation friction exposes retries, validation failures, route changes, false starts, hidden dependencies, rejected paths, decisive signals, root-cause families, or reusable constraints, make sure `workflow-state.md` or `implement-tracker.md` captures that durable context.
- [AGENT] For structured path learning not already captured in durable state, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.
- Treat this as passive shared memory, not as a separate user-visible execution command.

## Implement Tracker Protocol

- `FEATURE_DIR/implement-tracker.md` is the execution-state source of truth for `sp-implement`.
- [AGENT] Create it if missing after `FEATURE_DIR` is known. If it already exists and is not terminal, resume from it instead of restarting from chat memory.
- If native hook policy redirects a prompt-entry phase jump, return to `workflow-state.md` or `implement-tracker.md`; repeated or explicit phase jumps are blocked by shared workflow policy.
- Treat terminal states as `resolved` or `blocked`. Treat `gathering`, `executing`, `recovering`, `replanning`, and `validating` as resumable states.
- Update the tracker before each material phase transition: after scope recovery, before dispatching a ready batch, after each join point, before validation, when entering replanning, and before final completion reporting.
- The tracker must keep these fields obvious:
  - `status`
  - `current_batch`
  - `next_action`
  - `completed_tasks`
  - `failed_tasks`
  - `retry_attempts`
  - `blockers`
  - `recovery_action`
  - `open_gaps`
  - `user_execution_notes`
  - `resume_decision`
- If the user supplied important execution details in `$ARGUMENTS`, extract and persist them in the tracker before dispatching work. Typical examples include:
  - build or compile order
  - startup commands
  - required environment setup
  - known failing commands to avoid
  - recovery hints the runtime must remember on future resumes
- Treat these notes as binding for the current implementation run unless direct evidence shows they are wrong. Do not drop them silently on resume.
- Use this default structure:

```markdown
---
status: gathering | executing | recovering | replanning | validating | blocked | resolved
feature: [feature slug]
created: [ISO timestamp]
updated: [ISO timestamp]
resume_decision: resume-here | blocked-waiting | resolved
---

## Current Focus
current_batch: [ready batch or validation pass]
goal: [current implementation objective]
next_action: [immediate next step]

## Execution Intent
intent_outcome: [the concrete outcome this batch is trying to deliver]
intent_constraints:
  - [forbidden drift, boundary rules, or execution constraints that stay active for this batch]
success_evidence:
  - [checks or observations required before the leader can accept this batch]

## Execution State
completed_tasks:
  - [task ids already completed]
in_progress_tasks:
  - [task ids currently running]
failed_tasks:
  - [task ids that failed in the current pass]
retry_attempts: [0 if none]

## Blockers
- task: [task id]
  type: technical | external | human-action
  evidence: [short command output or observed failure]
  recovery_action: [smallest safe next recovery step]

## Actionable Blocker Resolution
- blocker: [task id or validation gate]
  classification: technical | external | human-action | verification_policy | project_cognition_readiness | baseline_timeout
  owner: agent | user | maintainer | external-system
  evidence: [artifact path, command output summary, or missing artifact]
  exact_next_action: [specific command, focused investigation, rerun, approval request, or upstream workflow]
  approval_question: [exact yes/no approval question when owner is user or maintainer, otherwise none]
  unblock_criteria: [observable condition that changes this from blocked to complete]
  implementation_can_continue: yes | no
  completion_impact: mandatory_for_completion | optional_cleanup | external_baseline_maintenance | follow_up_risk

## Validation
planned_checks:
  - [independent tests, acceptance checks, or validation commands]
completed_checks:
  - [checks already run]
human_needed_checks:
  - [manual verification still required]

## Open Gaps
- type: execution_gap | research_gap | plan_gap | spec_gap
  summary: [what is still not true]
  source: [task id, validation check, or user-visible outcome]
  next_action: [specific next step]

## User Execution Notes
- note: [important user-supplied execution detail from `$ARGUMENTS`]
  source: sp-implement arguments
  priority: high | normal
  applies_to: current feature execution
```

### Resume Audit Gate

- On every resume, treat checked tasks as claims that need evidence, not evidence themselves.
- If `implement-tracker.md` is `resolved`, all tasks appear checked, or the previous session exit is unknown, run `{{specify-subcmd:implement resume-audit --feature-dir "$FEATURE_DIR" --format json}}` before final reporting or new closeout.
- Treat `terminal-audit-required` as validation/recovery work, not completion.
- Require consumer evidence for tasks that create UI components, routes, providers, registries, factories, configs, tests, API handlers, or other reusable surfaces.
- When a task packet or workflow state requires `real_entrypoint_evidence`, the worker result's `consumer_evidence` must include an item with `kind: real_entrypoint` plus `entrypoint`, `producer`, `transformer`, `consumer`, `boundary_or_executor`, and `validation`; synthetic-only component, reducer, helper, or hand-built state evidence is not enough.
- Do not preserve `resolved` when the audit finds missing wiring, missing validation evidence, stale subagent handoff, unresolved `open_gaps`, or unexecuted planned validation tasks.
- If resume audit fails, update `implement-tracker.md` to `validating` or `recovering` with the audit gaps and continue from the smallest executable repair batch.
