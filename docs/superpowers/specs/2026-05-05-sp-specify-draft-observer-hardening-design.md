# sp-specify Draft Capture and Observer Hardening Design

**Date:** 2026-05-05
**Status:** Proposed
**Owner:** Codex

## Summary

This design hardens `sp-specify` so requirement discovery no longer depends on
chat memory, shallow recap quality, or the leader's ad hoc judgment about what
to ask next.

The approved direction adds four linked controls to the shared `sp-specify`
workflow:

- a durable draft artifact for ongoing clarification capture and resume
- an observer subagent stage that critiques the current understanding before
  capability closure and before handoff
- a tiered coverage model that upgrades from a core matrix to a full matrix when
  high-risk triggers are present
- stronger artifact validation that checks readiness semantics, not just file
  presence

This is a shared product behavior change for `sp-specify` across supported
integrations. It is not a Codex-only prompt tweak and not a local workaround for
one runtime.

## Problem Statement

`sp-specify` already pushes requirement discovery further than a thin spec
recorder, but it still has a critical failure mode:

- clarification can be better than the written artifacts
- the workflow can ask a few reasonable questions and still miss adjacent
  modules, compatibility paths, failure semantics, or propagation risk
- answers can remain in the conversation instead of being preserved in a durable
  recovery surface
- the final output can collapse into a short summary that omits many decisions
  discovered along the way
- cross-module impact can remain under-probed because there is no structured
  outsider challenge step before closure

That produces a downstream planning risk:

- `spec.md` does not preserve the real discovery path
- `alignment.md` and `context.md` can understate what is still inferred or
  unresolved
- a resumed `sp-specify` session may not know which capability it was shaping,
  which gap was still blocking, or what question should come next
- `/sp.plan` inherits artifacts that look complete enough to pass file-existence
  checks while still being shallow at the requirement layer

The user requirement behind this design is explicit:

- `sp-specify` must ask more deeply when behavior affects nearby surfaces
- requirement discovery must be continuously recorded as a draft, not only
  summarized at the end
- the workflow must be resumable from durable artifacts
- a structured critique stage should identify missing questions and weak
  assumptions before the workflow claims readiness for planning

## Goals

- Preserve clarification progress in a durable draft artifact from the start of
  the workflow.
- Make `sp-specify` resumable from written state rather than chat transcript
  memory.
- Force a structured observer challenge stage at fixed points in the workflow.
- Detect and escalate high-risk capabilities into a fuller clarification matrix.
- Prevent `Aligned: ready for plan` when planning-critical gaps remain untreated.
- Keep the enhancement shared-first across integrations.

## Non-Goals

- Do not turn `sp-specify` into open-ended brainstorming.
- Do not make the observer subagent user-facing or allow it to replace the
  leader's responsibility for synthesis.
- Do not move implementation architecture selection into `sp-specify`.
- Do not require that every low-risk capability pass the deepest possible review
  matrix.
- Do not begin implementation in this design document. The next step after
  review remains implementation planning.

## Design Principles

### 1. Discovery Must Survive Into Artifacts

Requirement discovery that stays only in the conversation is not reliable
workflow state. The workflow must write what it learns as it learns it.

### 2. Draft Is Not Final Spec

The workflow needs a persistent draft ledger for active discovery, but the final
`spec.md` must remain a planning-ready artifact rather than a raw transcript.

### 3. Recovery Depends On State, Not Memory

Resume behavior must be driven by durable state fields and written summaries, not
by the agent remembering what happened earlier in chat.

### 4. Cross-Surface Risk Needs Structured Skepticism

The leader should not be the only source of requirement challenge. A bounded
observer lane should critique the current understanding and force missing
questions into the artifact set before closure.

### 5. Rigor Should Escalate Only When Risk Justifies It

Every capability should pass a core requirement matrix. Only capabilities with
clear high-risk triggers should be upgraded into a full requirement matrix.

## Approved Direction

The approved direction is a two-layer hardening model:

1. introduce a durable clarification draft and continuous synchronization into
   the artifact set
2. add an observer-backed escalation model that can block false readiness

The behavior is shared across integrations because the underlying problem is in
the workflow contract, not in one runtime's UI.

## Artifact Model

### New Artifact: `FEATURE_DIR/specify-draft.md`

`sp-specify` should create or resume a new durable draft artifact:

- `FEATURE_DIR/specify-draft.md`

This file is not the planning-ready specification. It is the workflow's working
ledger for clarification, observer findings, resume anchors, and unresolved
gaps.

Its job is to preserve what the workflow knows before the final `spec.md` is
ready to carry a clean planning-facing result.

### Artifact Responsibilities

#### `specify-draft.md`

This draft artifact should carry:

- current capability focus
- current stage and observer status
- coverage mode for the active capability
- confirmed facts
- low-risk inferences
- unresolved items
- observer findings
- assumption risks
- affected surfaces and propagation notes
- recently closed questions
- next question target and why it matters
- force-carried risks when the user chooses to proceed

#### `alignment.md`

`alignment.md` remains the planning-facing alignment record, but it should now
carry:

- current release decision state
- observer gate outcomes
- coverage mode outcomes for high-risk capabilities
- planning-critical blockers and how each one was resolved, deferred, or
  force-carried

It should not become a full question ledger. It should remain a compact,
plannable alignment document.

#### `context.md`

`context.md` remains the implementation-facing context artifact. It should carry
stable downstream facts such as:

- affected surfaces
- change-propagation matrix
- contract and lifecycle notes
- configuration semantics and effective timing
- verification entry points
- locked decisions

This keeps `/sp.plan` from reconstructing critical decisions out of chat history
or draft notes.

#### `spec.md`

`spec.md` should no longer absorb the raw discovery stream.

Instead:

- the file is refreshed as capabilities become stable enough to write cleanly
- the file contains planning-ready requirement content only
- the file should not degrade into a running transcript of every question

This preserves the distinction between a discovery ledger and a planning-ready
specification.

## Continuous Synchronization Model

The workflow should follow this synchronization shape:

1. create or resume `specify-draft.md` as soon as `FEATURE_DIR` is known
2. after every clarification answer, update `specify-draft.md`
3. before closing a capability, run the observer stage and write its output into
   `specify-draft.md`
4. once a capability is stable enough, synchronize durable conclusions into
   `alignment.md` and `context.md`
5. refresh the relevant `spec.md` sections only when the capability is coherent
   enough for planning
6. run a final observer pass before handoff and reconcile any remaining blockers

This turns artifact writing into an ongoing workflow discipline rather than an
end-of-chat cleanup pass.

## Observer Stage Design

### Role

Add a bounded observer subagent stage to `sp-specify`.

The observer is not a co-author and not a user-facing interviewer. Its role is
to critique the current state of understanding and identify missing requirement
work before the leader closes a capability or exits to planning.

### Trigger Points

The observer should run at exactly three fixed points:

1. once near the start of the workflow after the initial context and request
   have been framed
2. once before each capability is marked sufficiently aligned
3. once before the final handoff decision

This approved cadence balances rigor and cost:

- it is stronger than a one-time review
- it does not force a subagent run after every single user answer
- it catches both early framing mistakes and late false-closure mistakes

### Inputs

The observer should receive:

- the user's original request
- the relevant project-map and handbook context
- the current `specify-draft.md`
- the current `alignment.md`, `context.md`, and `spec.md`
- the current capability snapshot
- unresolved items and recently closed items
- already-hit escalation triggers

### Outputs

The observer output should be structured and should include at least:

- `missing_questions`
- `affected_surfaces`
- `adjacent_workflows`
- `assumption_risks`
- `capability_gaps`
- `contrarian_candidate`
- `escalation_triggers_hit`
- `coverage_mode`
- `release_blockers`
- `next_best_question_targets`

The purpose is not to write prose for the user. The purpose is to produce a
leader-consumable critique contract.

### Leader Obligations

The leader must consume observer results explicitly.

For every observer-reported blocker or serious gap, the leader must convert it
into exactly one of these states:

- asked and resolved through clarification
- accepted as a low-risk inference
- explicitly deferred or scoped out
- force-carried as a known planning risk

The leader must write that state back into `specify-draft.md`. The leader must
not ignore the observer result after reading it.

### Blocking Authority

The approved authority model is:

- the observer can block capability closure and final handoff when it finds
  planning-critical, cross-module, contract, or similarly high-impact gaps
- the observer does not block for every low-risk omission

This means the observer acts as a requirement-quality gate, not a universal
friction generator.

## Coverage Model

### Core Matrix

Every capability should pass a core clarification matrix that covers at least:

- intended behavior and success outcome
- affected modules, workflows, documents, or surfaces
- direct upstream and downstream consumers
- confirmed, inferred, and unresolved state
- key failure path
- verification entry point

This ensures every capability receives minimum planning discipline even when it
is not high risk.

### Full Matrix Escalation

Capabilities should automatically escalate to a full matrix when any approved
hard trigger is present.

The trigger set is:

- cross-module impact
- external boundary, contract, or integration behavior
- migration or compatibility preservation
- asynchronous, event-driven, queue, or state-propagation behavior
- configuration-driven behavior
- security, permission, or trust-boundary semantics
- observability or rollback requirements
- performance or capacity risk

If any one of those conditions is hit, the capability must upgrade from `core`
to `full`.

### Full Matrix Contents

The full matrix should cover:

- goal and success signals
- owning surface and truth owner
- affected surfaces and propagation path
- consumers and adjacent workflows
- contract and compatibility semantics
- lifecycle, retention, cleanup, or transition expectations
- failure, retry, degraded mode, and user-visible behavior
- configuration items and effective timing
- security, permission, audit, or trust-boundary implications
- performance, capacity, and concurrency implications
- observability and regression-entry implications
- out-of-scope boundaries and force-carried risks

The intent is to make the workflow explicitly answer the kinds of questions that
are currently easy to skip in ordinary clarification.

## Readiness and Blocking Rules

### Capability Closure

A capability must not be treated as aligned enough to close when:

- a planning-critical observer blocker remains untreated
- the capability hit a full-matrix trigger but only received core coverage
- the requirement still depends on vague language, implicit defaults, or
  untested assumptions that materially shape planning

### Final Handoff

The workflow must not declare `Aligned: ready for plan` when:

- unresolved planning-critical blockers remain
- observer-required questions were not consumed
- a high-risk capability lacks its required matrix coverage
- the written artifacts do not reflect the clarified state

The only approved bypass is explicit `Force proceed with known risks`, and those
risks must be written into the artifacts rather than hidden in conversation.

## Resume Semantics

### Recovery Sources

When `sp-specify` resumes, the leader must re-read state in this order:

1. `workflow-state.md`
2. `specify-draft.md`
3. `alignment.md`
4. `context.md`
5. `spec.md`
6. the latest observer result summary

This preserves phase continuity and prevents the resumed workflow from
reconstructing state from memory.

### Required Recovery Capsule

`specify-draft.md` should contain an explicit recovery capsule that records at
least:

- `current_capability`
- `current_stage`
- `observer_status`
- `coverage_mode`
- `last_question_asked`
- `last_answer_summary`
- `next_question_target`
- `open_blockers`
- `recently_closed_items`

This gives the next session a stable "where am I and what comes next" anchor.

### Resume Rules

Resume should follow these hard rules:

- if there is an unconsumed observer blocker, the workflow must resolve it
  before drifting into unrelated freeform questioning
- if a capability had already escalated to `full`, resume cannot silently
  downgrade it back to `core`
- if the session stopped after a user answer but before draft synchronization,
  the workflow must repair the draft first
- if the workflow resumes at final handoff, it must re-run the final observer
  pass before claiming readiness

These rules make recovery depend on durable workflow state, not on optimistic
guessing.

## Validation and Hook Design

### Current Gap

The current artifact validation surface mainly checks whether `spec.md`,
`alignment.md`, `context.md`, and `workflow-state.md` exist. That is not enough
for the approved behavior because file presence does not prove real requirement
readiness.

### New Validation Expectations

The shared artifact validation layer should be extended so it can validate:

- `specify-draft.md` exists for `sp-specify`
- the draft contains the recovery capsule
- the draft contains observer result sections
- `alignment.md` and `context.md` record observer and coverage outcomes
- capabilities that hit escalation triggers preserve evidence of full-matrix
  treatment
- the final package does not claim readiness while planning-critical blockers
  remain untreated unless the release decision is explicitly
  `Force proceed with known risks`

This changes validation from "did files get written" to "does the written state
prove the exit contract was satisfied."

## Testing Strategy

Verification should cover four layers.

### 1. Template Guidance Tests

Assert that the shared `sp-specify` template explicitly includes:

- `specify-draft.md`
- observer trigger points
- coverage mode recording
- escalation trigger language
- resume capsule language
- blocking rules for false readiness

### 2. Hook and Artifact Validation Tests

Add tests that block when:

- `specify-draft.md` is missing
- the recovery capsule is missing
- observer sections are missing
- a capability hit escalation triggers without full coverage evidence
- planning-critical blockers remain while the package claims readiness

### 3. Shared Integration Generation Tests

Add or extend tests that confirm the new behavior is propagated across supported
integrations from the shared templates and runtime surfaces. The behavior should
not exist only for Codex or one other integration.

### 4. Recovery and Low-Risk Path Tests

Add tests that confirm:

- interrupted `sp-specify` runs can resume from the draft artifact
- low-risk capabilities can still complete with core coverage
- the new hardening does not over-promote every local change into the full
  matrix

## Implementation Surfaces

The eventual implementation should be shared-template-first and is expected to
touch at least these surfaces:

- `templates/commands/specify.md`
- `templates/spec-template.md`
- `templates/alignment-template.md`
- `templates/context-template.md`
- `templates/workflow-state-template.md`
- `src/specify_cli/hooks/artifact_validation.py`
- relevant integration rendering surfaces under `src/specify_cli/integrations/`
- `tests/test_alignment_templates.py`
- hook contract tests and integration-generation tests

Because this is a product-level workflow improvement, the implementation should
also review passive skill mirrors and generated command surfaces so the shared
behavior remains aligned across downstream outputs.

## Rollout Shape

The approved rollout shape is:

1. add the durable draft artifact and synchronization discipline
2. add the observer stage and escalation model
3. add semantic artifact validation and recovery-aware test coverage

This sequence preserves implementation clarity:

- the observer stage has a durable place to write its findings
- recovery semantics have a real artifact anchor
- validation can check durable outcomes rather than soft chat behavior

## Acceptance Criteria

This design is satisfied when:

- `sp-specify` creates or resumes a durable draft artifact from the start
- clarification progress is continuously written to the draft artifact
- observer passes run at the approved three fixed points
- observer findings are consumed and reflected in the artifact set
- high-risk capabilities automatically escalate into full coverage
- resumed sessions can continue from durable written state
- the workflow cannot claim normal readiness while planning-critical blockers
  remain untreated
- the enhancement ships as a shared behavior across supported integrations

## Decision

Proceed with `sp-specify` draft capture and observer hardening as a shared
workflow enhancement:

- add `specify-draft.md` as a durable clarification ledger and recovery anchor
- add a structured observer subagent stage with blocking authority for
  planning-critical gaps
- add core versus full coverage with explicit escalation triggers
- add readiness validation that checks semantics, not just file presence

This gives `sp-specify` a stronger discovery loop, a stronger recovery loop, and
a more trustworthy handoff into `/sp-plan`.
