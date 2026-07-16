# sp-discussion Agent-Native Optimization Design

**Date:** 2026-07-10
**Status:** Approved
**Owner:** Codex

## Summary

This design turns `sp-discussion` into an agent-first requirement-definition
system without making the human conversation feel agent-facing.

The governing principle is a strict experience split:

- the frontstage exists for the human and optimizes understanding, judgment,
  trust, and control
- the backstage exists for agents and tools and optimizes compactness,
  determinism, recoverability, and machine-checkable transitions

The workflow keeps its current responsibility boundary: shape product and
technical decisions before specification, preserve verified project truth, and
produce one reviewed handoff contract. It does not plan implementation, edit
source, or automatically invoke a downstream workflow.

The approved direction is a layered agent-native architecture: a thin hot-path
controller, triggered reference packs, typed state, deterministic lifecycle
operations, a schema-driven handoff, and cross-integration scenario evaluation.

## Target Need

`sp-discussion` must help an agent turn an exploratory request into a bounded,
evidence-aware, user-confirmed requirement contract while keeping every turn
useful to the human.

For the human, the workflow must behave like a senior product-engineering
advisor. It should explain the decision-level meaning first, recommend a safe
default, provide useful content immediately, and preserve a meaningful override
path. The human must not need to understand workflow stages, persistence
counters, artifact schemas, or internal verdict mechanics.

For the agent, the workflow must provide a compact and unambiguous answer to:

- what problem is being shaped now
- which facts and decisions are confirmed
- which boundary and evidence claims are authoritative
- what remains unresolved
- what action is allowed next
- whether a write is allowed on this turn
- which gate must pass before the lifecycle can advance

For downstream consumers, the workflow must preserve the selected direction,
rejected alternatives, accepted trade-offs, experience commitments, review
criteria, Must-Preserve obligations, consequence obligations, and stop-and-
reopen conditions without requiring rediscovery.

## Constraints

### Responsibility Boundary

- `sp-discussion` owns goal, users, scenarios, scope, non-goals, success signals,
  context boundary, evidence, requirement-level technical choices, user-owned
  decisions, and handoff readiness.
- It does not create implementation phases, ordered task sequences, source
  changes, tests, releases, or feature workspaces.
- It does not automatically invoke `sp-specify` or `sp-quick`.

### Human Frontstage

- Human-visible replies are governed by meaning, not by a fixed card or section
  template.
- The first useful statement is written from the human's point of view, in the
  user's language and at the user's level of technical detail.
- Internal fields, IDs, counters, file paths, and state receipts stay hidden
  unless the human needs them for review, recovery, verification, or explicit
  lifecycle control.
- A reply must not stop at an acknowledgement, status update, or promise to do
  the next step when useful first-pass content can be provided safely.
- The agent asks a question only when human judgment is genuinely required and
  no safe default exists.
- Review criteria may be fixed backstage, but the visible review summary remains
  natural and decision-oriented.

### Agent Backstage

- Dynamic discussion facts are stored once in a typed structure. Invariant
  workflow policy is not repeated in every session state file.
- Critical lifecycle gates are enforced by deterministic tools, not only by
  prompt instructions.
- Project cognition is advisory navigation. Live repository evidence,
  authoritative external evidence, explicit assumptions, and user confirmation
  carry factual authority.
- Ordinary turns remain memory-first and write-free. Persistence occurs only at
  semantic checkpoints, explicit saves, compaction risk, evidence handoff, or
  lifecycle transitions.
- Cross-CLI differences may change invocation syntax, but not workflow meaning,
  state transitions, gates, or artifacts.

### Artifact Integrity

- One typed handoff model is serialized to canonical JSON and rendered into the
  human-reviewable Markdown view.
- A user approval is bound to the exact reviewed handoff digest. Any protected
  change invalidates that approval and returns the handoff to draft review.
- `handoff-ready`, `consumed`, and `archived` are validated transitions, not
  free-text status edits.
- Existing discussion paths and handoff compatibility filenames remain readable
  during migration. Compatibility views must not become a second authority.

## Non-Goals

- Building a general-purpose product-management system.
- Persisting a full artifact set or transcript from the first ordinary turn.
- Exposing agent bookkeeping to humans for the sake of audit completeness.
- Creating different semantics for different AI integrations.
- Requiring project cognition for greenfield framing or when bounded live reads
  are sufficient.
- Letting a deterministic renderer replace product judgment or natural-language
  explanation.

## Considered Approaches

### Prompt-Only Simplification

Reduce duplicated instructions and shorten the generated command while keeping
state and lifecycle behavior agent-managed.

This improves context cost but leaves false readiness, false consumption,
manual dual-file synchronization, and unreliable recovery unresolved.

### Runtime-Only Enforcement

Add a state machine and validators while leaving the current prompt and
reference distribution mostly unchanged.

This improves artifact integrity but preserves oversized single-file prompts,
broken reference reachability, instruction conflicts, and cross-integration
behavior differences.

### Layered Agent-Native Architecture

Separate human interaction, agent reasoning context, dynamic state, reference
knowledge, and lifecycle enforcement into explicit layers.

This is the approved direction because it improves both experience surfaces:
the human gets a cleaner advisor conversation, while the agent gets smaller
context, typed inputs, explicit allowed actions, and deterministic gates.

## Human Frontstage Contract

Every substantive reply includes the useful subset of the following, arranged
for human comprehension rather than schema order:

1. the decision-level meaning or recommended direction
2. a plain-language reason grounded in confirmed intent, verified evidence, or
   a clearly marked assumption
3. concrete content the human can evaluate now
4. a material risk or trade-off only when it changes the decision
5. the safe default next move
6. a meaningful override path
7. one human-owned question only when no safe default exists

The contract does not prescribe visible headings. The agent may use prose,
bullets, a small table, or an ASCII sketch when that form makes the decision
easier to understand.

The human experience is considered invalid when it primarily exposes:

- workflow stages or reply-template names
- state counters or dirty flags
- artifact write receipts
- unexplained Must-Preserve or open-question identifiers
- file paths without decision-level meaning
- a fixed audit form that forces the human to translate internal mechanics

## Agent Backstage Contract

### Discussion Turn Packet

The active agent consumes a compact `DiscussionTurnPacket` rather than rereading
the full session and all workflow references on every turn.

The packet contains only dynamic and decision-relevant fields:

```text
version
discussion_slug
lifecycle_phase
turn_class
user_goal
current_decision_frame
confirmed_decisions
changed_recommendations
context_boundary
verified_fact_refs
open_assumptions
open_questions
current_recommendation
allowed_actions
persistence_mode
next_gate
```

Invariant policy such as allowed lifecycle transitions, ordinary-turn write
rules, and forbidden workflow behavior belongs in the controller and schemas,
not in each session packet.

### Durable Lifecycle

The durable lifecycle is reduced to:

```text
explore -> ground -> decide -> prepare -> review -> ready -> consumed | closed
```

The following remain orthogonal state dimensions instead of durable phases:

- boundary status
- truth-pass and evidence status
- UI discussion status
- consequence-gate status
- persistence mode
- blocker reason
- consumer eligibility

`readiness-summary`, `handoff-preview`, and other response shapes are views of
the current state. They are not persisted lifecycle phases.

### Persistence Model

- `initialization`: an explicit `sp-discussion` invocation creates only the
  minimal typed session identity and routing state; it does not create the full
  narrative artifact set or emit a visible write receipt
- `frontstage-only`: default for ordinary turns and low-risk preference answers
- `durable-checkpoint`: compact decision and state refresh
- `evidence-handoff`: evidence packet needed by later synthesis
- `lifecycle-transition`: handoff, review, ready, consume, close, or repair

The event log is compact and append-only. A checkpoint records durable meaning,
not a transcript. Resume reconstructs the turn packet from typed state plus
events after the latest checkpoint.

## State And Artifact Model

### Canonical State

`discussion-state.json` becomes the typed runtime authority. It contains dynamic
session facts, schema version, lifecycle state, gate state, and artifact
references.

`discussion-state.md` remains the human-readable compatibility view and is
rendered from canonical state. Existing Markdown-only sessions are migrated on
the first validated write. Migration establishes one authority and does not run
parallel state backends.

The compact event authority is `discussion-log.jsonl`. A Markdown
`discussion-log.md` view may be rendered when human review or compatibility
requires it.

### Discussion Artifacts

Requirements, technical options, project context, open questions, and UI
guidance remain narrative Markdown because agents and humans both benefit from
readable explanation. Their structured summaries and source references live in
canonical state so resume does not require loading every artifact.

### Unified Handoff

The handoff has one canonical structured payload validated by a dedicated
discussion handoff schema. The existing
`.specify/discussions/<slug>/handoff-to-specify.json` path stores that canonical
payload. The Markdown handoff is rendered from it, with human-authored narrative
fields preserved through explicit schema slots.

The schema uses consumer-neutral vocabulary:

- `ready-for-handoff`, not `ready-for-specify`
- `planning_constraints`, not `recommended_sequence`
- independent `consumer_eligibility` for `sp-specify` and `sp-quick`

Legacy split-candidate and execution-sequence fields are not part of the current
discussion handoff contract.

The review payload carries a `review_digest`. User confirmation records the
digest and the confirmed scope summary. A protected-field change produces a new
digest and requires review again.

## Deterministic Lifecycle Operations

The workflow relies on shared lifecycle capabilities with structured outputs:

- initialize a normalized, collision-safe discussion
- create a semantic checkpoint
- produce a compact resume context
- validate the handoff and report field-level failures
- mark the exact reviewed digest ready
- record verified downstream consumption
- close or archive a terminal discussion
- repair or migrate stale legacy state without inventing product truth

Normal ready marking requires:

- locked context boundary
- canonical handoff JSON and rendered Markdown present
- schema-valid canonical payload
- zero hard unknowns and open conflicts
- complete Must-Preserve and consequence coverage
- self-review evidence
- user confirmation bound to the current digest
- at least one eligible downstream consumer

Consumption requires a real target artifact that references the source
discussion, source handoff, and reviewed digest. Recovery exceptions are
explicit repair operations, not silent weakening of the normal gate.

## Reference And Prompt Architecture

The generated hot path contains only:

- role and responsibility boundary
- human frontstage contract
- turn classification
- controller invocation and allowed-action interpretation
- persistence gate
- reference routing index

Detailed knowledge is split into triggered reference packs:

- context boundary and evidence
- persistence and recovery
- product questions and technical options
- UI and interaction
- consequence analysis
- handoff creation, review, and repair
- downstream consumption

An ordinary product-framing turn should load the hot path only. A source-grounded
turn loads the evidence pack. A handoff turn loads the handoff pack. Multiple
packs are loaded only when their gates genuinely overlap.

Skills-based and command-based integrations install the same reference content
at a stable reachable path. Inline fallback is permitted only for an integration
that cannot read sidecar files, and that fallback has an explicit generated-size
budget.

## Cross-Integration Contract

All supported integrations must agree on:

- lifecycle phases and transitions
- turn classifications
- persistence modes
- boundary and evidence authority
- handoff schema and review digest
- allowed actions and gate failures
- human frontstage quality requirements

Integration adapters own only invocation syntax, native structured-question
support, native subagent capability, and filesystem/reference addressing.

No generated command may link to an absent reference. No integration may receive
a materially weaker handoff or recovery contract because of its command format.

## Failure And Recovery Behavior

- Malformed typed state blocks mutation and returns a field-level repair report.
- Missing or stale references fail generation or installation tests rather than
  degrading silently at runtime.
- Missing project cognition degrades navigation, not product framing. Bounded
  live evidence remains allowed.
- Evidence conflicts remain visible as conflicts and cannot be converted into
  assumptions automatically.
- An unrelated user prompt never confirms a handoff.
- Any protected change after approval invalidates the previous review digest.
- Resume never guesses missing product truth. It distinguishes recoverable
  structural damage from unresolved human decisions.

## Success Criteria

### Human Experience

- Human replies lead with understandable decision meaning rather than workflow
  mechanics.
- Ordinary turns do not show state receipts, persistence details, or file lists.
- Recommended next steps include useful first-pass content in the same reply.
- The human can approve, change, defer, or reopen a decision without knowing the
  internal state model.
- Review summaries provide enough decision context without forcing the human to
  reread every artifact or complete a fixed audit form.

### Agent Efficiency

- The rendered hot-path target is at most approximately 10,000 estimated tokens.
- A single-file fallback target is at most approximately 12,000 estimated tokens.
- Ordinary turns do not load handoff, UI, consequence, or recovery references
  unless triggered.
- Resume uses the compact turn packet and post-checkpoint events instead of
  loading all discussion artifacts by default.
- Invariant policy is not duplicated in per-session state.

### Integrity

- An invalid or unconfirmed handoff cannot become `ready`.
- A ready handoff cannot remain ready after a protected-field change.
- A discussion cannot become `consumed` without matching downstream evidence.
- Markdown and JSON handoff views cannot drift because they share one structured
  authority and review digest.
- Lifecycle writes and derived index updates are atomic from the caller's point
  of view.

### Cross-CLI Consistency

- Every integration passes reference reachability checks.
- Every integration passes generated-size budgets or declares a reviewed bounded
  exception.
- Golden scenarios produce the same lifecycle state, allowed actions, gate
  verdicts, and handoff payload across integrations.

## Validation Strategy

Validation is scenario-based rather than primarily phrase-based.

The required scenario matrix covers:

- new discussion initialization and slug collision
- ordinary human-facing product discussion
- recommendation-first continuation without a permission loop
- repository fact lookup and evidence conflict
- explicit checkpoint and compaction recovery
- cross-project boundary locking
- optional UI discussion
- handoff preview without file creation
- draft handoff, self-review, user change request, and re-review
- unrelated prompt while a handoff awaits approval
- protected change invalidating an earlier approval
- ready transition with each individual gate failure
- `sp-specify` and eligible `sp-quick` consumption
- false or mismatched consumption rejection
- close, archive, migration, and repair

Additional checks cover state-transition properties, schema round trips,
Markdown/JSON rendering agreement, prompt size, reference reachability, and
cross-integration parity.

Human-response evaluations judge decision clarity, plain-language reasoning,
concrete usefulness, unnecessary workflow exposure, question necessity, and
preservation of user control.

## Risks And Mitigations

### Runtime Overreach

A typed runtime could attempt to replace product judgment.

Mitigation: tools own structure, validation, and transitions; the agent owns
recommendation, synthesis, explanation, and product judgment.

### Human Replies Become Mechanical

Schema-driven backstage behavior could leak into visible responses.

Mitigation: the human frontstage contract explicitly forbids schema-order output
and fixed visible review cards.

### Migration Creates Dual Authority

Keeping compatibility Markdown could produce state drift.

Mitigation: canonical typed state is the only mutation authority. Markdown is a
rendered compatibility view, not a writable parallel backend.

### Reference Fragmentation

Too many sidecars could make agents miss applicable rules.

Mitigation: use a small trigger index, deterministic reference routing, and a
bounded number of cohesive packs rather than one file per minor rule.

### Prompt Budgets Hide Required Rules

Aggressive shrinking could remove safety-critical guidance.

Mitigation: keep responsibility, authority, persistence, and transition gates in
the hot path; move only stage-specific detail behind explicit triggers.

## Decision

Adopt the layered agent-native architecture.

The primary product distinction is permanent: the human frontstage is optimized
for comprehension, judgment, trust, and control; the agent backstage is
optimized for compactness, explicit state, deterministic transitions, and
recoverable evidence.

No optimization is accepted if it makes human replies feel like machine state,
and no conversational improvement is accepted if it leaves critical lifecycle
integrity dependent on prompt compliance alone.
