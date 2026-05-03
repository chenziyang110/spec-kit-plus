# Scenario Profile Workflow Design

Date: 2026-05-03
Status: Approved for implementation planning

## Goal

Evolve the `sp-*` workflow system from one generic delivery path into a
profile-aware execution system that can stay lightweight for ordinary delivery
while enforcing stronger contracts for high-risk task shapes.

The immediate product goal is to preserve the current shared workflow surface
while making room for scenario-specific behavior without fragmenting the system
into multiple disconnected template families.

The design must:

- preserve one shared `spec -> plan -> tasks -> implement` backbone
- support explicit scenario routing at workflow entry
- carry scenario obligations through every downstream stage without silent drift
- keep the default path lightweight
- fail closed for high-risk scenario obligations when required sections, gates,
  or evidence are missing

## Problem Statement

The current workflow stack is optimized for general feature delivery. That is a
strong default for standard feature work, but it creates avoidable failure modes
when the task shape is materially different from generic delivery.

The current failure pattern is not that the workflows are missing more generic
steps. The problem is that they do not distinguish strongly enough between
different task shapes and their different failure modes.

Examples of the mismatch at the workflow level include:

- a generic feature flow being used for tasks whose real success criterion is
  structural fidelity to an existing reference implementation
- implementation tasks being shaped for output throughput rather than for
  evidence-bearing comparison, compatibility control, or repair discipline
- downstream stages reinterpreting task shape informally instead of inheriting a
  single explicit scenario contract
- completion being treated too uniformly, with "tests passed" acting as the
  default closeout standard even when the primary risk is architecture drift,
  compatibility regression, or unproven root cause

The system therefore needs a way to keep one stable workflow backbone while
activating stronger obligations only when the scenario justifies them.

## Scope

This design covers:

- scenario-aware routing for `sp-specify`, `sp-plan`, `sp-tasks`, and
  `sp-implement`
- a shared-core template strategy for `spec-template.md`,
  `plan-template.md`, and `tasks-template.md`
- a profile contract as the single source of truth for scenario obligations
- scenario-specific required sections, gates, task-shaping rules, and evidence
  obligations
- a phased rollout that starts with the most valuable non-default scenario

This design does not cover:

- replacing the current `sp-*` backbone with separate workflow families
- making all scenarios equally strict from day one
- turning scenario routing into opaque implementation-only logic
- expanding the first release to every possible scenario subtype

## Core Decision

Adopt a `shared core templates + scenario profiles` model.

The repository should retain one shared workflow backbone and one shared set of
top-level templates. Scenario-specific behavior should be introduced through
explicit profile overlays rather than through multiple separate full templates.

This means:

- one shared `spec-template.md`
- one shared `plan-template.md`
- one shared `tasks-template.md`
- one explicit active scenario profile per feature lifecycle
- one profile contract produced at workflow entry and inherited downstream

This design rejects the alternative of maintaining multiple complete
template/workflow families for different task types. That approach would make
scenario intent obvious in the short term, but it would create long-term drift
in shared fields, shared rules, shared evolution, and reviewer expectations.

## Design Principles

### Shared Skeleton

The top-level template structure should stay stable across scenarios. Shared
sections should remain in the same documents and keep the same base semantics.

### Profile Overlays

Profiles should only strengthen or specialize the shared skeleton. They should
not redefine the entire document family.

### Upstream Locking

Facts locked in earlier artifacts must be carried forward and translated, not
silently reinterpreted downstream.

### Evidence-Carrying Progression

Each workflow stage must pass forward the obligations and evidence type that the
next stage depends on. Scenario handling should not rely on memory or implied
intent.

### Explicit Routing

Scenario selection must happen at workflow entry and must be visible in workflow
state and generated artifacts.

### Fail Closed For High-Risk Modes

If a high-risk profile requires extra sections, gates, or evidence, downstream
workflow stages must block when those obligations are missing.

## Profile Taxonomy

The system should begin with a small, stable set of task-shape profiles. The
goal is not to model every nuance up front. The goal is to distinguish between
different failure modes that justify different workflow obligations.

### Standard Delivery

The default profile for ordinary new feature work and bounded enhancement work
whose main requirement is coherent delivery with clear scope, validation, and
implementation sequencing.

### Reference-Implementation

The profile for work whose primary success condition is faithful preservation of
an existing reference structure, contract, behavior model, or boundary pattern.

This profile is the first non-default profile to prioritize because its failure
mode is high-value and poorly served by generic delivery assumptions.

### Brownfield Enhancement

The profile for work whose dominant challenge is safe evolution inside an
existing system with meaningful compatibility surfaces, change-propagation risk,
and adjacency constraints.

### Debug / Repair

The profile for work whose dominant challenge is establishing a trustworthy
causal chain before applying a repair.

## Initial Release Decision

The first release of this design should support:

- `Standard Delivery`
- `Reference-Implementation`

`Brownfield Enhancement` and `Debug / Repair` should be designed now but wired
later. This keeps initial rollout bounded and focuses on the highest-value
gap without destabilizing the default path.

## Profile Contract

The system should create one explicit `profile contract` for each feature
lifecycle. This contract is the single source of truth for scenario obligations.

Suggested contract fields:

- `profile_id`
- `routing_reason`
- `confidence_level`
- `required_sections`
- `activated_gates`
- `task_shaping_rules`
- `required_evidence`
- `transition_policy`

The profile contract must be produced at entry, stored as durable workflow
state, and consumed by downstream stages. No downstream workflow should re-route
the feature independently unless a formal profile transition is recorded.

## Routing Model

### Routing Priorities

Routing should be explicit and auditable rather than purely inferred.

Recommended routing priority:

1. explicit user-selected profile
2. task shapes whose success criterion is fidelity to a reference object route
   to `Reference-Implementation`
3. task shapes whose primary objective is diagnosis and corrective recovery route
   to `Debug / Repair`
4. task shapes whose main risk is safe evolution of an existing system route to
   `Brownfield Enhancement`
5. all remaining work routes to `Standard Delivery`

### Routing Inputs

Routing should use a compact set of inputs:

- `intent shape`
- `success condition`
- `risk source`
- `context dependency`

### Routing Output

Routing should emit:

- the active profile
- the routing reason
- routing confidence
- the activated obligations

### Stickiness And Transition

One feature lifecycle should have one active primary profile by default.

Profile transitions are allowed only when the dominant goal, risk, or success
condition changes materially. A transition must be recorded as an explicit
decision, and downstream artifacts must be updated rather than silently carrying
stale assumptions.

## Template Family Structure

The repository should keep the existing three-document family:

- `spec-template.md`
- `plan-template.md`
- `tasks-template.md`

Profiles should not replace these documents. Instead, each profile should
overlay only the parts that differ:

- which sections become mandatory
- what extra prompts appear inside those sections
- which gates must be satisfied before advancing
- what evidence must be produced for closeout

### Spec Responsibilities

`spec` should remain the artifact that freezes task intent, scope boundaries,
usage paths, planning-sensitive facts, and locked decisions.

Profiles modify the required depth and required locked facts, not the role of
the document itself.

### Plan Responsibilities

`plan` should remain the artifact that translates planning-sensitive facts into
implementation constraints, execution boundaries, required references, and
review focus.

Profiles change which constraints must be promoted into the
`Implementation Constitution` and related validation checks.

### Tasks Responsibilities

`tasks` should remain the artifact that compiles the plan into bounded
execution units with explicit dependencies, verification, handoff format, and
join points.

Profiles change the task-shaping strategy, join point expectations, and required
completion evidence.

## Profile-Specific Obligations

Profiles must activate explicit obligations, not optional stylistic advice.

Each profile should define obligations in four categories:

- `spec obligations`
- `plan obligations`
- `task-shaping obligations`
- `exit evidence obligations`

### Standard Delivery Obligations

`Standard Delivery` should require:

- clear goal, scope, scenarios, success criteria, and locked decisions in `spec`
- implementation context, dependencies, verification path, and core execution
  rules in `plan`
- bounded, independently verifiable task decomposition in `tasks`
- completion evidence centered on behavioral correctness and regression safety

This path should remain the lightest supported path.

### Reference-Implementation Obligations

`Reference-Implementation` should require:

- explicit identification of the reference object and the required fidelity
  target in `spec`
- locked statements of forbidden drift, required reference consumption, and
  review focus in `plan`
- explicit comparison-oriented work items, fidelity checkpoints, and deviation
  confirmation points in `tasks`
- closeout evidence including comparison evidence, deviation log, and fidelity
  audit outcome

For this profile, completion is not defined primarily by "works as expected."
Completion is defined first by "preserves the required reference fidelity
contract."

## Injection Model

The design should be implemented through one profile contract injected into four
layers:

- routing layer
- template layer
- workflow gate layer
- execution evidence layer

### Routing Layer

Determines the active profile and produces the durable profile contract.

### Template Layer

Consumes the profile contract to activate required sections and overlay prompts
inside existing template sections.

### Workflow Gate Layer

Consumes the profile contract to enforce stage-specific gates before the
workflow advances.

### Execution Evidence Layer

Consumes the profile contract to require matching completion evidence and
handoff contents.

This keeps routing, documentation, gating, and closeout aligned without
replicating scenario logic across many surfaces.

## Workflow Integration

### `sp-specify`

`sp-specify` should become the primary routing point. It should:

- determine or record the active profile
- store the profile contract in durable feature state
- require the `spec` artifact to satisfy the active profile's required sections
  and locked-fact obligations

### `sp-plan`

`sp-plan` should consume the existing profile contract and translate it into:

- `Implementation Constitution` constraints
- required references
- review focus
- inherited validation obligations

It should not perform a second informal task classification pass.

### `sp-tasks`

`sp-tasks` should consume the same profile contract and compile:

- task-shaping rules
- profile-specific guardrail tasks
- profile-specific join points
- profile-specific completion evidence requirements

### `sp-implement`

`sp-implement` should remain an execution and verification workflow, not a
scenario classifier.

It should verify:

- that required profile inputs were consumed
- that required gates were satisfied
- that handoff outputs contain the profile-matched evidence

## Adoption Roadmap

Rollout should be incremental rather than all-at-once.

### Phase 1: Define The Contract

Introduce the profile contract and make `sp-specify` produce it.

Primary objective:

- one shared scenario truth source

### Phase 2: Wire Spec To Plan

Make `sp-plan` consume the contract and turn profile obligations into explicit
implementation constraints.

Primary objective:

- no silent loss of scenario-critical facts during `spec -> plan`

### Phase 3: Wire Plan To Tasks

Make `sp-tasks` compile profile obligations into execution structure.

Primary objective:

- no silent drift from scenario contract into generic task decomposition

### Phase 4: Wire Tasks To Implement Exit Gates

Make `sp-implement` enforce profile-matched completion evidence.

Primary objective:

- no generic closeout for scenario-specific risks

### Phase 5: Expand Profile Coverage

After the first two profiles are proven, expand the same mechanism to
`Brownfield Enhancement` and `Debug / Repair`.

## Success Markers

This design should be considered successful when:

- workflow entry can classify supported task shapes explicitly and consistently
- `spec -> plan -> tasks -> implement` no longer silently drops scenario
  obligations
- the default path remains lightweight
- high-risk paths gain stronger gates without fragmenting the template family
- completion evidence varies by scenario instead of collapsing to a single
  generic standard
- reference-fidelity work shows lower drift between intended and delivered
  structure

## Non-Goals

This design does not aim to:

- create a separate full template set for every scenario
- classify every possible subtype of work in the first release
- make every workflow equally strict
- move scenario logic entirely into hidden runtime code
- let downstream workflows silently override the active profile

## Open Design Constraints To Preserve In Planning

The implementation plan for this design must preserve the following constraints:

- keep one shared top-level template family
- treat the profile contract as the only scenario truth source
- support only two active profiles in the first release
- keep default-path operator burden low
- fail closed for missing high-risk obligations
- keep profile logic visible in generated artifacts and workflow state

## Recommendation

Proceed with implementation planning using:

- shared core templates
- scenario profiles as overlays
- an explicit durable profile contract
- phased rollout beginning with `Standard Delivery` and
  `Reference-Implementation`

This is the smallest design that solves the current high-value mismatch without
creating a long-term template maintenance fork.
