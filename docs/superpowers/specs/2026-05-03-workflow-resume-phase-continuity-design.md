# Workflow Resume Phase Continuity Design

**Date:** 2026-05-03
**Status:** Proposed
**Owner:** Codex

## Summary

This design hardens `sp-*` workflow recovery so an active workflow does not
lose its phase contract after context compaction, session restart, lane
re-entry, or parent/child handoff.

The repository already has durable workflow state, checkpoint generation,
compaction artifacts, native-hook adapters, and workflow policy checks. The
missing capability is a shared recovery contract that can reassert:

- the current workflow stage
- the actions allowed in that stage
- the actions forbidden in that stage
- the next legal command or action
- the authoritative files that must be re-read before work continues
- the reason the workflow must not jump phases

The approved direction is:

1. keep existing workflow-state, tracker, quick-status, and debug-session files
   as the only sources of truth
2. derive a unified recovery contract from those state surfaces
3. inject a structured recovery summary on resume-class events
4. use `redirect-first` enforcement for the first phase drift and hard-block
   repeated or explicit phase jumps

This is a repository-wide workflow discipline design, not a Claude-only fix and
not an `sp-specify`-only patch.

## Problem Statement

The current workflow system preserves substantial state, but active workflows
can still drift after context loss or session recovery.

Today the repository already provides:

- `workflow-state.md` for planning-side workflows such as `sp-specify`,
  `sp-deep-research`, `sp-plan`, `sp-tasks`, `sp-analyze`, and `sp-prd`
- `implement-tracker.md` for `sp-implement`
- quick-task `STATUS.md`
- debug session files
- shared checkpoint generation through `workflow.checkpoint`
- compacted recovery artifacts through `workflow.compaction.build`
- workflow policy checks through `workflow.policy.evaluate`
- native-hook lifecycle entry points on Claude, Codex, and Gemini

However, the current system still has four gaps:

1. state files are durable, but recovery behavior is not yet expressed as one
   normalized contract across workflow types
2. compaction artifacts contain useful resume cues, but they do not yet
   restate the full phase contract needed to prevent drift
3. native resume events mostly expose status hints rather than an explicit
   "current phase + allowed actions + forbidden actions + next command" bundle
4. workflow policy can block clear phase jumps, but it does not yet implement
   a consistent `redirect-first` path for accidental post-recovery drift

The result is a specific failure mode:

- an active workflow survives in durable state
- the session loses chat memory through compaction or restart
- the next session no longer clearly understands the active phase contract
- the model resumes with partial context and may jump into implementation,
  verification, or another downstream phase too early

This problem is larger than `sp-specify`. It can affect any active `sp-*`
workflow whose current phase must survive recovery.

## Goals

- Preserve phase continuity for every active `sp-*` workflow across
  compaction, session restart, lane recovery, and leader/subagent handoff.
- Reuse existing workflow state files as the only sources of truth.
- Define one normalized recovery contract that every resumable workflow can
  expose.
- Extend compaction artifacts from loose resume hints into structured recovery
  summaries.
- Add `redirect-first` enforcement for accidental phase drift.
- Hard-block repeated or explicit phase-jump attempts.
- Keep the design integration-neutral at the shared policy layer while allowing
  Claude, Codex, and Gemini to consume the same recovery contract according to
  their native-hook depth.

## Non-Goals

- Do not create a second durable state file such as `resume-state.json`.
- Do not move workflow truth out of `workflow-state.md`,
  `implement-tracker.md`, `STATUS.md`, or debug session files.
- Do not make this a Claude-specific workaround.
- Do not hard-block every first recovery mistake without first attempting to
  redirect the workflow back onto its legal phase path.
- Do not require every native-hook integration to support identical lifecycle
  behavior when host runtimes differ.
- Do not begin implementation from this design alone. The next workflow after
  review remains implementation planning.

## Current-State Assessment

### Durable State Surfaces Already Exist

The current repository already encodes most workflow truth in durable files:

- `FEATURE_DIR/workflow-state.md` for planning-side workflows
- `FEATURE_DIR/implement-tracker.md` for execution
- `.planning/quick/*/STATUS.md` for quick tasks
- debug session files for `sp-debug`

This is the correct source-of-truth model and should remain unchanged.

### Shared Hooks Already Cover Key Lifecycle Events

The shared hook engine already exposes:

- workflow state validation
- session-state validation
- checkpoint generation
- context monitoring
- workflow policy evaluation
- compaction build and read
- statusline rendering

The hook architecture is not missing enforcement entry points. It is missing a
shared recovery contract and a phase-continuity strategy across those entry
points.

### Native Integrations Already Have Resume-Relevant Entry Points

Current native coverage already includes lifecycle events that can carry resume
information:

- `SessionStart`
- `UserPromptSubmit`
- `PostToolUse`
- `Stop`

Claude and Codex have deeper lifecycle coverage than Gemini, but all supported
native-hook surfaces can still benefit from one shared recovery contract.

## Design Principles

### 1. Existing State Files Remain Canonical

The design must not invent a second truth surface. Recovery is derived from the
same durable files that already govern workflow progress.

### 2. Recovery Must Be Structured, Not Narrative Memory

Resume behavior must depend on explicit persisted fields, not on the model
"remembering" the previous conversation.

### 3. Phase Continuity Is a Workflow-Level Rule

This is not a compaction-only rule. Compaction is one trigger. The protected
invariant is that an active workflow keeps its phase contract across every
resume-class event.

### 4. Redirect Before Blocking

Most post-recovery phase drift is accidental. The system should first reassert
the phase contract and redirect the session. Repeated or explicit phase-jump
attempts should then block.

### 5. Shared Policy, Thin Adapters

The shared hook engine should define recovery semantics. Native adapters should
translate timing and output formats, not reimplement workflow policy.

## Core Design

## 1. Unified Recovery Contract

Introduce a normalized `RecoveryContract` abstraction derived from the current
workflow source of truth.

This is a runtime object, not a new file.

Every resumable workflow should be able to expose the same conceptual fields:

- `command_name`
- `state_kind`
- `status`
- `phase_mode`
- `summary`
- `allowed_actions`
- `forbidden_actions`
- `authoritative_sources`
- `next_action`
- `next_command`
- `route_reason`
- `blocked_reason`
- `resume_decision`
- `recovery_state`
- `last_stable_checkpoint`

The object must be rich enough to answer the real recovery questions:

- what stage am I in
- what is allowed right now
- what is forbidden right now
- what file(s) must be re-read before continuing
- what is the smallest correct next action
- why is a downstream phase jump not allowed yet

## 2. State Mapping Rules

The recovery contract should be derived from existing state surfaces as follows.

### Planning-Side Workflows

For:

- `sp-constitution`
- `sp-specify`
- `sp-deep-research`
- `sp-plan`
- `sp-tasks`
- `sp-analyze`
- `sp-prd`

the authoritative file remains `FEATURE_DIR/workflow-state.md`.

`workflow-state.md` already contains most required fields:

- `active_command`
- `status`
- `phase_mode`
- `Allowed Artifact Writes`
- `Forbidden Actions`
- `Authoritative Files`
- `Next Action`
- `Next Command`
- `route_reason`
- `blocked_reason`
- `last_stable_checkpoint`

The serializer layer should be extended so these sections are parsed completely
instead of only extracting a minimal subset.

### Implementation

For `sp-implement`, the execution-state source of truth remains
`FEATURE_DIR/implement-tracker.md`, but implementation recovery still depends on
its relationship to `workflow-state.md`.

The recovery contract for `sp-implement` should therefore include:

- tracker state such as `status`, `current_batch`, `next_action`,
  `resume_decision`, `retry_attempts`
- lane recovery metadata when present
- implementation-phase allowed and forbidden actions derived from the
  execution contract rather than invented from chat memory
- phase-jump protection when `workflow-state.md` and `implement-tracker.md`
  disagree

### Quick Tasks

For `sp-quick`, the authoritative file remains `STATUS.md`.

Its recovery contract should include at least:

- current status
- active lane
- next action
- resume decision
- quick-task execution constraints and safe follow-up scope

### Debug Sessions

For `sp-debug`, the authoritative file remains the debug session file.

Its recovery contract should include:

- next action
- current debug focus
- any recorded observer or research checkpoint cues

## 3. Structured Recovery Summary

Resume behavior should no longer rely on short status text alone.

The system should produce a structured recovery summary whenever an active
workflow is resumed. That summary should include:

- current stage
- current status
- allowed actions
- forbidden actions
- authoritative files to re-read
- next action
- next command
- why the workflow cannot safely jump stages

This recovery summary is a rendered view of the recovery contract.

It should be compact enough for native hook output but explicit enough to
prevent the model from improvising a downstream phase.

## 4. Resume-Class Events

The shared policy layer should treat the following as `resume-class` events.

### Resume Entry

Events that re-enter an active workflow:

- `SessionStart`
- root-level workflow resume after lane recovery
- leader/subagent join-point return when the parent session continues

These events must reassert the recovery contract before work continues.

### Resume Risk

Events that should write or refresh recovery evidence:

- `Stop`
- compaction-risk checkpoints
- long validation boundaries
- delegation or join-point boundaries

These events should refresh checkpoints and, when appropriate, compaction
artifacts.

### Resume Drift

Events that can reveal phase drift:

- `UserPromptSubmit`
- `PostToolUse`
- explicit workflow-policy evaluations before a phase-sensitive action

These events should compare the attempted action against the current recovery
contract.

## 5. `redirect-first` Enforcement

### First Drift

If an active workflow exists and the current intent conflicts with its phase
contract, the first response should normally be a redirect rather than an
immediate hard block.

The redirect should explicitly restate:

- current phase
- allowed actions
- forbidden actions
- next legal command or action
- authoritative files that must be re-read
- the route reason preventing a phase jump

This solves the common case where drift happened because recovery context was
incomplete, not because the user deliberately tried to bypass the workflow.

### Repeated or Explicit Phase Jump

If the same active workflow receives another conflicting downstream request
after a redirect, or if the requested action is an explicit phase jump such as:

- `jump_to_implement`
- `implement_directly`
- `skip_to_implement`
- `jump_to_code`

the policy should hard-block with a direct phase-jump error.

### State Repair Remains Distinct

Missing or contradictory state should remain a `repairable-block`, not a phase
jump block. The user or workflow should be told to repair state rather than
being told the intent itself is forbidden.

## Hook and Adapter Behavior

## Shared Hook Layer

The shared hook layer should be extended as follows.

### `workflow.checkpoint`

- include the fields needed to build a full recovery contract
- preserve authoritative file lists, allowed actions, forbidden actions, route
  reason, and last stable checkpoint when present

### `workflow.compaction.build`

- continue using checkpoint output as input
- emit a structured recovery summary, not just loose resume cues
- preserve compact human-readable recovery output alongside machine-readable
  JSON

### `workflow.policy.evaluate`

- classify outcomes as:
  - `allow`
  - `redirect`
  - `repairable-block`
  - `blocked`
- enforce explicit phase jumps immediately
- support repeated-drift escalation after an earlier redirect

### `workflow.statusline.render`

- keep the short operator-facing summary
- do not treat the statusline as a substitute for the full recovery summary

## Native Adapters

Native adapters should consume the shared contract according to their lifecycle
depth.

### `SessionStart`

- render the short statusline
- when an active resumable workflow exists, also inject the structured recovery
  summary

### `UserPromptSubmit`

- preserve prompt-guard behavior
- additionally evaluate whether the requested action conflicts with the active
  recovery contract
- return redirect output on first phase drift
- return a block on repeated or explicit phase jumps

### `PostToolUse`

- keep session-state drift checks
- treat it as an advisory drift-detection point
- emit redirect guidance when the tool sequence implies phase drift but the
  session should still be recoverable

### `Stop`

- continue context monitoring
- refresh checkpoint and compaction evidence when recommended
- preserve the latest recovery summary so the next session does not depend on
  stale cues

## Workflow Template Updates

Workflow templates should explicitly support the same recovery contract instead
of relying on soft prose alone.

At minimum:

- `workflow-state-template.md` should document the fields required for
  structured recovery
- primary `sp-*` workflow templates should continue to state:
  - current phase mode
  - allowed artifact writes
  - forbidden actions
  - authoritative files
  - resume discipline
- templates should reinforce that recovery must re-read the authoritative state
  file rather than continuing from chat memory

This keeps template guidance, shared hooks, and native integrations aligned.

## Failure Modes and Handling

### Missing State File

If the authoritative file is missing:

- return `repairable-block`
- explain which state file is missing
- do not allow phase continuation from chat memory alone

### Partial or Weak State

If the state file exists but is missing recovery-critical fields:

- return a degraded recovery summary when safe
- surface the missing fields explicitly
- escalate to `repairable-block` if the phase contract can no longer be trusted

### Contradictory State

If tracker and workflow-state disagree:

- classify this as drift or repairable state conflict
- do not silently trust one source over the other

### Missing or Stale Compaction Artifact

If compaction output is missing or stale:

- rebuild the recovery summary from the authoritative state file
- do not treat compaction artifacts as canonical truth

## Acceptance Criteria

- Every resumable workflow type can produce a normalized recovery contract from
  its existing source of truth.
- `SessionStart` can surface a structured recovery summary when an active
  resumable workflow exists.
- `Stop` can refresh recovery evidence so the next session resumes with a fresh
  contract.
- The first detected phase drift after recovery produces a redirect, not a hard
  block.
- Repeated or explicit phase jumps produce a hard block.
- Missing state remains a repairable workflow-state problem, not a silent
  fallback to chat memory.
- Claude, Codex, and Gemini share the same recovery contract semantics even
  when their native lifecycle depth differs.

## Verification Strategy

Verification should cover three layers.

### State-Layer Tests

- workflow-state serialization captures recovery-critical fields
- implement-tracker, quick-status, and debug-session mapping produce valid
  recovery contracts
- weak or partial state files surface missing-field failures clearly

### Behavior-Layer Tests

- `SessionStart` produces structured recovery summaries for active workflows
- `Stop` produces fresh compaction artifacts
- first drift yields `redirect`
- repeated drift yields `blocked`
- explicit phase-jump requests yield `blocked`
- contradictory state yields `repairable-block`

### Integration-Layer Tests

- Claude hook adapter renders and forwards the shared recovery summary
- Gemini adapter preserves the same shared contract where lifecycle depth allows
- Codex-native runtime behavior matches the shared policy outcomes

## Rollout Plan

Roll out in two stages.

### Stage 1: Soft Enforced Recovery

- implement the unified recovery contract
- extend compaction artifacts and resume summaries
- enable `redirect-first`
- keep repeated-drift blocking narrow until behavior is stable

### Stage 2: Full Phase-Continuity Enforcement

- extend repeated-drift blocking across all active `sp-*` workflows
- tighten validation for missing recovery-critical fields
- align documentation and generated workflow guidance with the final semantics

## Open Questions Resolved by This Design

- This is not limited to `sp-specify`; it applies to every active `sp-*`
  workflow.
- This should be a persistent workflow rule, not a compaction-only patch.
- The enforcement model should be `redirect-first`, not inform-only and not
  hard-block-first.
- The implementation shape should be a shared recovery contract plus
  workflow-specific phase rules, not one custom recovery behavior per workflow.

## Recommended Next Step

After design review approval, route to implementation planning so the work can
be decomposed into:

- serializer and contract changes
- shared hook and compaction changes
- native adapter changes
- workflow template and documentation changes
- hook and integration test coverage
