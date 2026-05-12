# sp-implement Resume Audit Design

## Context

Downstream users can lose an `sp-implement` session mid-run because of a power loss, crash, terminal restart, or context compaction. The expected operator behavior is to run `sp-implement` again and continue from durable state. Today that resume path can trust stale surface state too much: `tasks.md` may contain checked tasks and `implement-tracker.md` may report `resolved`, even though the previous session only created files or partial components and never completed the integration join point that makes the behavior user-visible.

The observed failure mode was a provider-management UI where CLI-specific form components existed, tasks were marked complete, and the tracker looked resolved, but the active page still rendered the generic form because the new components were never wired into the route/page flow.

## Problem

`sp-implement` currently has strong narrative guidance about tracker truth, structured handoffs, validation, and not treating checked tasks as sufficient. The weaker point is the crash/resume boundary:

- `validate-state --command implement` only requires `implement-tracker.md` to have a status and next action.
- `validate-session-state --command implement` compares workflow state and tracker state, but it does not inspect whether a terminal tracker state is justified by accepted task evidence.
- `implement closeout` is referenced as the final validation hook, but the resume contract does not force a closeout-quality audit before trusting a terminal or near-terminal state after interruption.
- Worker packet compilation can degrade task done criteria into the task description instead of carrying explicit acceptance, wiring, and verification evidence.

This allows a resumed run to interpret stale `resolved` or checked-off tasks as authoritative instead of re-validating implementation reality.

## Goals

- Make interrupted `sp-implement` resumes conservative by default.
- Require a resume audit before trusting `resolved`, fully checked `tasks.md`, or a tracker that has no active work after an unclean stop.
- Detect the specific false-complete class where files exist but are not connected to their consumer surface, route, registry, exported API, test path, or user-visible workflow.
- Preserve the existing lightweight operator flow: users should still be able to run `sp-implement` again after a crash.
- Keep the first implementation scoped to generated workflow/runtime contracts rather than a full task-state database rewrite.

## Non-Goals

- Do not replace `tasks.md` with a new durable task database.
- Do not require every generated project to adopt `sp-teams`.
- Do not attempt universal static reachability analysis across every language and framework.
- Do not block honest manual verification when a project has no reliable automated UI or E2E surface; record it explicitly as human-needed evidence instead.

## Design

### Resume Audit Gate

Add a resume audit gate to `sp-implement` and the shared hook/runtime surface. On every `sp-implement` start, after loading `workflow-state.md` and `implement-tracker.md`, the workflow must classify the previous session as one of:

- `clean-active`: tracker is `gathering`, `executing`, `recovering`, `replanning`, or `validating`; resume from the recorded batch.
- `clean-blocked`: tracker is `blocked`; resume from recorded blocker and recovery action.
- `terminal-audit-required`: tracker is `resolved`, tasks appear fully checked, or tracker has no active tasks after an unclean stop; audit before accepting completion.
- `state-conflict`: workflow state, tracker state, task state, or lane state disagree; stop and report the conflict.

`terminal-audit-required` must not report completion directly. It must enter `validating` or `recovering` unless the audit proves the terminal state.

### Evidence Model

The audit should evaluate evidence at task, batch, and feature levels:

- Task evidence: task ID, checked state, worker result if present, changed files, validation output, concerns, blockers, and rule acknowledgement.
- Batch evidence: every lane in the current batch accepted or explicitly blocked/deferred, join point validation target executed or manually recorded, no stale idle lane without handoff.
- Feature evidence: all required tasks done, no incomplete planned validation tasks, no unresolved `open_gaps`, final validation green or recorded as human-needed evidence.

For user-visible or consumer-facing work, task acceptance must include a consumer evidence item. Examples:

- UI component created and imported by the active page, route, modal, registry, or factory that renders it.
- API handler created and registered in the router used by the server.
- Provider/client module created and selected by the runtime factory or configuration path.
- Config/schema field created and consumed by validation, serialization, or runtime loading.
- Test created and included in the relevant verify command.

The implementation should not try to infer every consumer relationship automatically. It should require the task contract or audit report to name the expected consumer surface and verify it by one of: focused test, route/browser check, import/registry check, or explicit manual evidence.

### Hook Behavior

Extend the implement validation surface with a closeout-quality audit command. The exact CLI shape can be either a new subcommand or an extension of the existing closeout hook, but it should expose structured JSON:

```text
specify implement resume-audit --feature-dir <FEATURE_DIR> --format json
```

The returned payload should include:

- `status`: `pass | fail | conflict`
- `resume_classification`
- `trusted_terminal_state`: boolean
- `task_findings`: task ID, status, evidence, missing evidence
- `join_point_findings`
- `open_gaps`
- `recommended_tracker_status`: `validating | recovering | blocked | resolved`
- `recommended_next_action`

`validate-session-state --command implement` should call or mirror the same checks when tracker status is `resolved` or when state suggests a terminal resume. A resolved tracker without closeout-quality evidence should produce a warning or block depending on the command phase; `sp-implement` itself treats it as blocking completion and resumes validation/recovery.

### Tracker Updates

`implement-tracker.md` should gain explicit fields for resume auditing:

- `last_session_exit`: `clean | interrupted | unknown`
- `resume_audit_status`: `not-run | pass | fail | conflict`
- `resume_audit_at`: timestamp
- `evidence_gaps`: list of missing task, join point, or consumer evidence
- `human_needed_checks`: existing section remains the place for manual verification that is intentionally outside automation

On resume after a crash or unknown exit, the workflow updates:

- `status: validating` while auditing terminal state
- `status: recovering` when missing evidence maps to executable repair work
- `status: blocked` only when the missing evidence requires upstream clarification or human action
- `status: resolved` only after resume audit and closeout pass

### Template Changes

Update `templates/commands/implement.md` and integration-rendered implement guidance so the first resume action is:

1. Read `implement-tracker.md`, `workflow-state.md`, `tasks.md`, and worker results.
2. If tracker is terminal or near-terminal, run the resume audit before final reporting.
3. Treat checked tasks as claims that need evidence, not evidence themselves.
4. For every new file or component task, verify the expected consumer path before marking the task accepted.
5. Do not preserve `resolved` when audit finds missing wiring, missing validation, stale subagent handoff, or unexecuted planned validation tasks.

Update `templates/worker-prompts/implementer.md` so implementers report consumer evidence for work that creates reusable code, UI, routes, registrations, configs, or tests.

### Packet and Result Contract Changes

Extend `WorkerTaskPacket` with optional acceptance-evidence fields:

- `acceptance_criteria`
- `consumer_surfaces`
- `required_evidence`

Extend `WorkerTaskResult` with optional evidence receipts:

- `acceptance_evidence`
- `consumer_evidence`
- `manual_evidence`

The validator should remain backward compatible for older packets, but new packets generated from enriched tasks should require evidence for any populated `required_evidence` or `consumer_surfaces` item. This prevents a worker from returning `success` with only “file created” when the packet asked for “component visible through DeviceProviderPage”.

### Closeout Rule

Final completion must use the same truth standard whether the run was uninterrupted or resumed:

- all tasks required for the selected release slice are accepted
- worker results or equivalent evidence exist for accepted tasks
- join points have passed
- planned validation tasks have run or are explicitly recorded as human-needed
- consumer-facing outputs are reachable through their intended runtime path
- no `open_gaps` remain unless the feature is intentionally blocked or awaiting human verification

Only then can `implement-tracker.md` remain or become `status: resolved`.

## Data Flow

1. Operator runs `sp-implement` after interruption.
2. Workflow resolves the feature lane and reads durable state.
3. Resume audit classifies state before any final report or new batch dispatch.
4. If audit passes, closeout can report resolved.
5. If audit fails because work is incomplete, tracker becomes `validating` or `recovering` and the workflow selects the next executable repair batch.
6. If audit finds conflicting upstream state, tracker becomes `blocked` or the workflow stops with a state-conflict diagnostic.

## Testing Strategy

Add regression tests for:

- A resolved tracker with checked tasks but no worker result or validation evidence is not accepted as complete.
- A task that creates a UI component but lacks consumer evidence is reported as an evidence gap.
- A resolved tracker with open gaps is downgraded to `validating` or blocked by closeout.
- `validate-session-state` reports terminal-audit-required for suspicious resolved state.
- `sp-implement` template requires resume audit before trusting terminal state.
- Backward compatibility: older trackers without new fields can resume, but are classified as `unknown` and audited rather than rejected outright.

## Rollout

Implement in three bounded slices:

1. Template and tracker contract hardening so generated instructions stop trusting stale terminal state.
2. Runtime resume-audit/closeout helper with JSON output and tests.
3. Packet/result evidence fields and validators for consumer evidence in new enriched task packets.

The first slice improves behavior immediately. The second slice gives machine-checkable protection. The third slice closes the worker-handoff loophole that allowed “created but not wired” work to look successful.

## Risks

- Overly strict audits could block legitimate projects with weak test surfaces. Mitigation: allow explicit manual evidence, but require it to be named.
- Consumer evidence differs by stack. Mitigation: represent it as task-provided expected surfaces plus evidence receipts, not a universal static analyzer.
- Existing generated projects may lack new tracker fields. Mitigation: classify missing fields as `unknown` and audit, not as fatal corruption.

## Acceptance Criteria

- A resumed `sp-implement` cannot report completion from `status: resolved` alone.
- Checked tasks without validation and consumer evidence are treated as untrusted claims.
- Missing wiring after file creation becomes an `open_gaps` or `evidence_gaps` entry with a concrete next action.
- The final closeout path and resume path share one evidence standard.
- The operator experience remains simple: after a crash, running `sp-implement` again audits and continues automatically when repair work is clear.
