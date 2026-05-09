# sp-specify Brainstorming Kernel and Deterministic Handoff Design

**Date:** 2026-05-09
**Status:** Proposed
**Owner:** Codex

## Summary

This design restructures `sp-specify` from a fixed specification-only discovery
workflow into a public entry shell with an internal `brainstorming` kernel,
scenario-aware compilation, and deterministic downstream handoff.

The goal is not to make the workflow "more dynamic" in the open-ended agent
sense. The goal is to let `sp-specify` accept much broader request shapes while
still producing stable downstream execution truth:

- a one-line request for a local module
- a long-form requirement description
- a professional PRD
- an existing repository that must be refactored
- a module extraction request inside an existing codebase
- a cross-language reconstruction where source code is the truth owner

The approved direction is:

- keep `sp-specify` as the public user-facing entrypoint
- insert a mandatory `brainstorming` kernel before traditional specification
  compilation
- treat `brainstorming` as a rule-driven lock-and-handoff system, not a free
  conversation loop
- persist each major conclusion into structured context files before the next
  step may proceed
- allow dynamic routing only when the routing decision is derived from explicit
  persisted facts and fixed rules
- compile the locked truth into downstream `specify`, `plan`, `tasks`, and
  `implement` contracts so later stages do not silently reinterpret user intent

The key product outcome is stronger intent fidelity across the full chain:

`brainstorming -> specify -> plan -> tasks -> implement`

That chain should preserve what the user actually wants, not only what the
user first happened to say.

## Problem

`sp-specify` in its current form assumes the incoming request is already close
enough to a feature-specification shape that the workflow can discover missing
details and then emit planning-ready artifacts.

That assumption is too narrow for the real request surface. In practice,
users bring materially different problem types:

- "extract this capability into a reusable module"
- "rewrite this open-source project in another language"
- "here is a PRD; turn it into a buildable program"
- "here is an existing repository; reconstruct what the real requirement should
  be"
- "improve this area, but preserve existing behavior exactly"

Those are not just different input lengths. They are different problem shapes
with different completeness rules, different handoff risks, and different
execution contracts.

The current failure mode is therefore broader than "the workflow asked too few
questions":

- the workflow can assume a generic feature-spec form too early
- downstream planning can inherit underspecified or misclassified intent
- task shaping can lose the difference between strict invariants and areas where
  quality-seeking redesign is allowed
- `sp-implement` can receive tasks that are structurally valid but semantically
  underconstrained, causing high-effort output that still misses the user's
  real goal

This is especially visible in reconstruction and extraction work:

- cross-language rewrites can produce incomplete or uneven projects because
  behavioral equivalence, truth ownership, compatibility scope, and allowed
  redesign latitude were never locked explicitly
- module extractions can work better when the request already matches a narrow
  local change pattern, but become inconsistent when consumer compatibility,
  new ownership boundaries, and migration expectations were not carried
  explicitly end to end

The root problem is not lack of effort. The root problem is absence of a
truth-owning, persisted intent layer before specification, planning, tasking,
and implementation.

## Goals

- Keep `sp-specify` as the single public entrypoint for requirement work.
- Add a mandatory internal `brainstorming` phase before specification
  compilation.
- Accept heterogeneous inputs without requiring the user to choose different
  commands first.
- Convert broad or ambiguous requests into a persisted, structured intent model
  before downstream compilation.
- Allow dynamic routing only through explicit rule evaluation against persisted
  facts.
- Preserve downstream compatibility with `sp-plan`, `sp-tasks`, and
  `sp-implement` by compiling new truth artifacts into stable handoff files.
- Make `sp-implement` a high-standard executor that can pursue better design
  where allowed, without redefining user intent or violating locked invariants.
- Treat `unknown` as a managed pending-decision object with explicit handling
  rules, not as an ignored placeholder.

## Non-Goals

- Do not make `brainstorming` a separate mandatory user-facing command in v1.
- Do not rely on chat-memory-only conclusions as valid workflow truth.
- Do not permit open-ended agent classification without explicit rule matches.
- Do not require every request to become a full-repository deep reconstruction.
- Do not turn `sp-implement` into a product-definition stage.
- Do not allow downstream stages to silently mutate upstream locked intent.

## Design Principles

### 1. One Public Entry, Multiple Internal Shapes

Users should not need to decide whether they are asking for a feature spec,
module extraction, migration, reconstruction, or rewrite workflow before the
system can help them.

`sp-specify` remains the single public entry shell. Internal specialization is
the system's job.

### 2. Dynamic Is Allowed Only When It Is Rule-Driven

Open-ended dynamic agent judgment is too unstable for multi-stage handoff.

Dynamic behavior is acceptable only in this form:

- read persisted context
- evaluate explicit rules
- write the resulting conclusion
- hand off to the next defined step

If a conclusion exists only in the active conversation and not in a persisted
truth file, it is not a valid workflow conclusion.

### 3. Every Major Conclusion Must Be Locked Before It Is Consumed

The workflow must progress through persisted lock points:

- facts lock
- route lock
- intent lock
- complexity lock
- downstream handoff locks

Each lock point creates a new truth artifact that later stages consume.

### 4. Questions Exist to Unlock Fields, Not to Simulate Freeform Discovery

`brainstorming` must ask questions, but only to close explicit gaps in
persisted truth:

- unresolved fact fields
- incomplete route matches
- ambiguous intent boundaries
- missing invariants
- missing success criteria
- unresolved complexity triggers

If an answer does not close a field, the field remains open and the workflow
does not pretend otherwise.

### 5. `unknown` Is an Exception Path, Not the Default Path

The workflow should aggressively reduce `unknown` through precise questioning
and evidence gathering.

An unresolved `unknown` is acceptable only when:

- the user genuinely does not yet know
- the repository or supplied evidence cannot answer it
- the question can be explicitly deferred without corrupting downstream truth

### 6. `sp-implement` Must Obey Intent but Still Pursue Quality

The execution chain must preserve both of these truths:

- some surfaces are locked and must not drift
- some surfaces should be improved aggressively when the product contract
  allows it

That latitude must be declared explicitly upstream. `sp-implement` should never
guess it.

## Approved Direction

### Public Shell + Internal Kernel Architecture

`sp-specify` becomes a two-layer system:

1. `brainstorming kernel`
2. `scenario compiler`

The `brainstorming kernel` owns truth gathering and locking.

The `scenario compiler` owns conversion of that locked truth into downstream
artifacts that existing workflow stages can consume.

### High-Level Flow

The approved internal sequence is:

1. feature workspace bootstrap
2. `brainstorming` facts lock
3. `brainstorming` route lock
4. `brainstorming` intent lock
5. `brainstorming` complexity lock
6. scenario-specific specification compile
7. downstream handoff routing

This produces the operational chain:

`user input -> brainstorming kernel -> scenario compiler -> specify artifacts -> plan artifacts -> task packets -> implement execution`

## Brainstorming Kernel

### Purpose

The `brainstorming` kernel exists to answer one question before specification
begins:

"What is the real thing the user wants us to build, preserve, extract,
reconstruct, or migrate?"

It is not a generic ideation phase. It is a deterministic intent-locking phase.

### Internal Substeps

The kernel is split into four lock steps:

1. `facts-lock`
2. `route-lock`
3. `intent-lock`
4. `complexity-lock`

Each step persists structured truth before the next step may run.

### Questioning Rules

Questions are mandatory when required fields are unresolved.

The rules are:

- only ask questions tied to explicit unresolved fields or rule predicates
- after each answer, update the relevant truth artifact immediately
- do not ask speculative or aesthetic questions that do not unlock workflow
  progression
- if strong repository evidence or supplied documents already close a field,
  mark it `closed-by-existing-evidence`
- do not advance to a downstream lock step while a required upstream hard field
  remains unresolved

This keeps questioning productive while avoiding open-ended conversational
drift.

## Persisted Truth Model

The approved model introduces a machine-readable truth layer inside each
feature workspace.

Suggested structure:

- `brainstorming/facts.json`
- `brainstorming/route.json`
- `brainstorming/intent.json`
- `brainstorming/complexity.json`
- `brainstorming/brainstorming.md`
- `brainstorming/handoff-to-specify.json`

Only the JSON files are workflow truth sources.

`brainstorming.md` is the human-readable companion document for review and
traceability. It is not the machine truth source.

### `facts.json`

Purpose:

- store explicit fact fields
- record whether each fact is `true`, `false`, or `unknown`
- link each fact to evidence or answer provenance

Representative fields include:

- `has_existing_repo`
- `has_source_of_truth_code`
- `has_prd_input`
- `requires_behavioral_equivalence`
- `requires_module_extraction`
- `requires_cross_language_port`
- `allows_internal_redesign`
- `has_compatibility_constraints`
- `success_criteria_explicit`

These are examples, not a frozen final schema list. The contract is that every
field must be explicit, auditable, and persistable.

### `route.json`

Purpose:

- record which scenario route was matched
- record which rules matched
- record which routes were rejected and why
- record unresolved conditions that still block final route closure

This prevents downstream stages from reverse-engineering the route from prose.

### `intent.json`

Purpose:

- lock the real goal
- lock explicit non-goals
- lock success criteria
- lock must-preserve invariants
- lock allowed optimization scope

This file is the core anti-drift contract for `sp-plan`, `sp-tasks`, and
especially `sp-implement`.

### `complexity.json`

Purpose:

- record complexity level
- record which rules triggered that level
- record the scope to which the complexity level applies
- record downstream execution expectations implied by that complexity

Complexity is not a chat-era opinion. It is a compiled outcome.

## Scenario Model

### Core Structure

Scenario handling uses two layers:

1. a universal `brainstorming` core
2. scenario-specific expansion templates

The universal core ensures that all requests are interpreted through the same
truth disciplines.

Scenario templates then ask the additional questions needed for problem types
that have different completeness rules.

### Initial Scenario Families

The first supported primary families should include:

- new capability or feature definition
- existing repository capability change
- module extraction / decoupling / boundary reshaping
- cross-language reconstruction / port
- source-first reverse requirement reconstruction
- compatibility migration / replacement upgrade

These scenario families do not need to be exposed as user-facing commands in
v1. They are internal route targets.

### Route Selection Rule

Route selection must be deterministic.

The system may not say "this feels like a migration" and continue.

Instead:

- evaluate `facts.json`
- apply explicit route rules
- write the route result to `route.json`
- if route conditions are insufficient, ask more questions or gather evidence

No route is valid unless it is written and justified.

## Complexity Ladder

### Purpose

Complexity exists to standardize downstream execution mode. It is not a vague
difficulty label.

The approved fixed ladder is:

- `T1 Local`
- `T2 Structured`
- `T3 Cross-Boundary`
- `T4 Reconstruction`

### Semantics

`T1 Local`

- single owning surface
- no public contract change
- no migration or reconstruction semantics
- validation path already known

`T2 Structured`

- multi-module cooperation within one bounded area
- limited external effect
- internal reshaping allowed but still locally bounded

`T3 Cross-Boundary`

- public API, compatibility, migration, or multi-consumer risk
- state migration or broader propagation risk
- multiple boundaries require coordinated planning

`T4 Reconstruction`

- cross-language rewrite
- source-code truth ownership
- behavior-equivalence expectations
- module extraction with broad compatibility or migration risk
- reverse reconstruction of requirements from code and evidence

### Rule Evaluation

Complexity must be derived from rules, not open interpretation.

Suggested evaluation policy:

- if any `T4` trigger is true, classify `T4`
- else if any `T3` trigger is true, classify `T3`
- else if all `T1` conditions are true, classify `T1`
- else classify `T2`

The actual trigger set should be explicit and versioned in the workflow
contract.

### Scope

Complexity should default to capability or module granularity, with optional
drill-down to task granularity only for high-risk surfaces.

This avoids two bad extremes:

- feature-level labels that are too coarse
- task-level labeling everywhere, which is too heavy

## `unknown` Handling Contract

### Core Rule

`unknown` is not an ignored value. It is a pending decision object.

Every unresolved `unknown` must carry at least:

- `field`
- `question`
- `blocking_level`
- `resolver`
- `latest_resolve_phase`
- `status`

### Handling Modes

The approved handling modes are:

- `resolve-now`
- `resolve-by-evidence`
- `resolve-by-research`
- `defer-with-contract`
- `waive-with-risk`

### Blocking Levels

Only two blocking levels are required in v1:

- `hard`
- `soft`

`hard` means the workflow may not hand off past the current gate until the
field is resolved.

`soft` means the workflow may continue only if the latest resolve phase is
explicitly recorded and the unresolved state cannot change the locked intent or
acceptance meaning of the work.

### Gate Rules

The workflow should fail closed on unresolved hard unknowns.

Minimum gate policy:

- leave `brainstorming` only when `goal`, `route`, `intent`, core invariants,
  success criteria, and complexity have no unresolved hard unknowns
- leave `sp-specify` only when scope, boundaries, acceptance, and capability
  coverage have no unresolved hard unknowns
- leave `sp-plan` only when sequencing, interfaces, and validation strategy
  have no unresolved hard unknowns
- leave `sp-tasks` only when each execution packet is free of execution-blocking
  hard unknowns
- enter `sp-implement` only when remaining unknowns are soft and cannot
  redefine the task's product intent or acceptance criteria

## Handoff Chain

### Principle

Every workflow boundary must hand off through persisted structured context.

Conversation memory is not a valid handoff surface.

### Recommended Feature Workspace Layout

```text
FEATURE_DIR/
  workflow-state.md

  brainstorming/
    facts.json
    route.json
    intent.json
    complexity.json
    brainstorming.md
    handoff-to-specify.json

  specify/
    specify-draft.md
    spec.md
    alignment.md
    context.md
    references.md
    handoff-to-plan.json

  plan/
    plan.md
    plan-contract.json
    handoff-to-tasks.json

  tasks/
    tasks.md
    task-index.json
    task-packets/
      T-001.json
      T-002.json
    handoff-to-implement.json

  implement/
    execution-state.json
    result-handoffs/
```

This exact path structure may be adapted during implementation, but the design
principle is fixed:

- truth files are structured
- human companions are separate
- every stage has an explicit handoff artifact

### Downstream Contracts

`handoff-to-specify.json`

- feeds specification compilation
- carries the locked facts, route, intent, complexity, and unresolved soft
  decisions that specification must preserve

`handoff-to-plan.json`

- feeds planning compilation
- carries capability boundaries, sequencing constraints, invariants, allowed
  optimization ranges, and acceptance obligations

`handoff-to-tasks.json`

- feeds task packet generation
- carries planning conclusions in a machine-readable shape so task generation
  does not reinterpret the plan from prose alone

`handoff-to-implement.json`

- feeds execution
- carries the actual implementer contract:
  - complexity level
  - matched rule ids
  - must-preserve invariants
  - allowed optimization scope
  - required validation
  - stop-and-reopen conditions

## Reopen Rules

Downstream stages may not silently mutate upstream truth.

Approved reopen model:

- if `sp-specify` discovers upstream intent is inadequate, reopen
  `brainstorming`
- if `sp-plan` discovers the specification is insufficient, reopen
  `sp-specify`
- if `sp-tasks` discovers planning truth is insufficient, reopen `sp-plan`
- if `sp-implement` discovers execution truth is insufficient, reopen
  `sp-tasks` or `sp-plan` depending on the missing layer

Reopen is a first-class workflow action, not an exceptional hack.

## `sp-implement` Contract

### Role

`sp-implement` remains the executor, but the executor must become better
constrained and better empowered at the same time.

It must not:

- redefine the product goal
- reinterpret the route class
- change locked invariants
- silently downgrade complexity expectations

It should:

- execute with high engineering standards
- improve architecture and maintainability where the contract explicitly allows
  it
- pursue stronger design quality inside the allowed optimization scope
- produce evidence that the locked acceptance and invariant obligations were
  preserved

### Quality Latitude

The workflow must preserve the user's right to say both:

- "this must stay equivalent"
- "inside those constraints, design it better"

That means the upstream truth model must explicitly distinguish:

- what is locked
- what is bounded
- what is open for quality-seeking redesign

The exact field names may vary during implementation, but the semantic split is
required.

## Impact on Existing `sp-specify`

This design supersedes the assumption that one fixed heavy discovery lifecycle
is sufficient for all requirement shapes.

The old fixed-heavy design solved one real problem: under-questioned feature
specification.

This new design preserves that concern but generalizes the workflow:

- fixed persistence rules remain
- hard gates remain
- structured questioning remains
- but the flow now starts with a broader `brainstorming` truth layer before the
  classic specification artifacts are compiled

The product therefore shifts from:

- one universal heavy requirement-discovery path

to:

- one universal public entry shell
- one universal truth-locking kernel
- multiple deterministic scenario compilation paths

## Migration Strategy

Recommended staged rollout:

1. introduce `brainstorming` truth artifacts and lock semantics without yet
   removing the current `sp-specify` artifact set
2. compile `brainstorming` truth into the current `spec.md`, `alignment.md`,
   `context.md`, and `references.md` surfaces
3. update `sp-plan`, `sp-tasks`, and `sp-implement` to consume structured
   handoff artifacts as authoritative inputs
4. progressively reduce any downstream dependence on prose-only interpretation
5. retire or simplify legacy `sp-specify` fixed-heavy assumptions once the new
   truth chain is fully consumed end to end

This minimizes blast radius while still moving the product toward a more robust
truth-preserving execution chain.

## Risks

- The workflow can become too heavy if every field is treated as universally
  required rather than scenario-scoped.
- Poorly designed rule sets can create false certainty while still missing
  important cases.
- If Markdown companions are allowed to drift from JSON truth, users and agents
  can lose trust in the system.
- If reopen handling is weak, downstream stages may still be tempted to patch
  product-definition gaps locally.
- If `sp-implement` does not consume the final contract directly, the highest
  value part of the design is lost.

## Open Decisions

- Exact JSON schemas for `facts`, `route`, `intent`, `complexity`, and
  handoff contracts
- Exact initial route families and rule IDs
- Whether some current `sp-specify` artifacts should move under a `specify/`
  subdirectory or remain at the feature root
- How much of the current fixed-heavy lifecycle should remain inside the
  scenario compiler after `brainstorming` completes
- Whether `brainstorming` should eventually become a visible alias or secondary
  entrypoint for expert users, even if `sp-specify` remains the primary shell

## Decision

Proceed with a `brainstorming` kernel inside `sp-specify`, backed by persisted
truth artifacts, deterministic rule-driven routing, structured unknown
handling, and explicit downstream handoff contracts through `sp-implement`.

The product should no longer assume that all requirement work starts in a
feature-spec shape. It should instead convert arbitrary incoming work into a
locked, auditable, machine-consumable intent chain before planning and
execution begin.
