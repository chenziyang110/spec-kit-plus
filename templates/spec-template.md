# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## Brainstorming Truth Inputs

- Route: [compiled from route.json]
- Complexity: [compiled from complexity.json]
- Truth Owner: [compiled from facts.json and route.json]
- Must Preserve:
  - [compiled invariant]
- Allowed Optimization Scope:
  - [compiled scope]
- Soft Unknowns Carried:
  - [field, owner, latest resolve phase, and risk if any]

## Overview *(mandatory)*

### Feature Goal

[Describe the intended capability, why it matters, and the outcome the feature must create.]

### Intended Users and Value

- **Primary users / roles**: [Who this is for]
- **Problem or opportunity**: [What changes for them]
- **First-release outcome**: [What a coherent first release must achieve]

## Ideal Complete Requirement Shape

This layer captures the complete useful feature form.

This layer captures the most complete useful version of the intended capability
that discovery and repository evidence support.

For reference-sensitive or rewrite-style work, this section MUST expand
compressed feature labels into the concrete behaviors, supporting flows, and
exception handling that make the capability usable.

Do not describe only a module name, subsystem label, or high-level feature tag
when repository evidence shows the capability contains multiple distinct
behaviors.

### Complete Capability Shape

- [Core capability the user is actually trying to achieve]
- [Necessary supporting behavior that makes the capability usable]
- [Important adjacent behavior, exception handling, or lifecycle requirement]

### Complete Usage Expectations

- [Primary trigger and end-to-end flow that a complete version must support]
- [Expected outcome for the main user or operator]
- [Expected handling for important non-happy-path or exception conditions]

### Domain-Expected Completeness Checks

- [Normal domain expectation that would make the feature incomplete if omitted]
- [Boundary, permission, data, dependency, lifecycle, or downstream expectation that must be preserved]
- [Acceptance-level expectation for a genuinely complete capability rather than a surface-level label]

## Current Delivery Boundary

This layer captures the current project-bound delivery boundary.

This layer translates the ideal requirement shape into the bounded slice this
repository should currently plan and deliver.

It MUST preserve the intended outcome while making explicit:
- what behavior remains in scope
- what behavior is intentionally deferred
- what constraints narrow the current slice

Do not collapse a multi-behavior capability into a single feature label without
naming the specific behaviors included in the current slice.

### In Scope

- [Primary capability, workflow, or outcome included in this delivery slice]
- [Supporting behavior required for this slice to remain coherent]

### Out of Scope

- [Explicitly excluded capability or workflow]
- [Deferred enhancement, broader ideal-shape item, or later release work]

### Boundary Constraints

- [Project, product, policy, or repository constraint that narrows delivery]
- [Implementation, dependency, rollout, or compatibility limit that shapes scope]

## Brainstorming Truth Inputs

- **Locked route**: [Compiled from `brainstorming/route.json`]
- **Locked complexity**: [Compiled from `brainstorming/complexity.json`]
- **Must Preserve**:
  - [Invariant compiled from `brainstorming/intent.json`]
- **Allowed Optimization Scope**:
  - [Explicit redesign latitude compiled from `brainstorming/intent.json`]

## Scenarios and Usage Paths *(mandatory)*

### Primary Scenario - [Brief Title]

[Describe the main triggering situation, the user's goal, and the expected outcome.]

**Usage Path**:
1. [Starting condition or trigger]
2. [Key user/system interaction]
3. [Expected completion or business outcome]

**Acceptance Signals**:
- [Observable result that proves the scenario works]
- [Boundary, rule, or condition that must hold]

---

### Secondary Scenario - [Brief Title]

[Describe the next most important path or meaningful variation.]

**Usage Path**:
1. [Starting condition or trigger]
2. [Key user/system interaction]
3. [Expected completion or business outcome]

**Acceptance Signals**:
- [Observable result that proves the scenario works]

---

### Edge Cases and Failure Paths

- [Boundary condition and expected handling]
- [Error path, missing prerequisite, or conflicting state]
- [Compatibility or migration-sensitive condition]

## Capability Decomposition *(mandatory)*

### Capability Map

- **Capability 1**: [Behavior-oriented capability name and purpose]
  Supports: [Scenario(s) or usage paths]
  Depends on: [Capability, precondition, reference, or existing workflow]
  Delivery note: [Whether it is core, enabling, follow-on, or validation-oriented]

- **Capability 2**: [Behavior-oriented capability name and purpose]
  Supports: [Scenario(s) or usage paths]
  Depends on: [Capability, precondition, reference, or existing workflow]
  Delivery note: [Whether it is core, enabling, follow-on, or validation-oriented]

### Capability Relationships

- [Sequencing dependency, coupling note, or shared precondition]
- [Cross-capability constraint or integration note]

## Implementation-Oriented Analysis *(mandatory)*

### Preconditions and Dependencies

- [Required existing workflow, system, policy, or external dependency]
- [Assumption or prerequisite that must hold before delivery]

### Data, State, and Entity Considerations

- [Relevant entity, state transition, or data responsibility]
- [Compatibility, migration, persistence, retention, archival, or cleanup concern]

### Event / Trigger Model

- [What event, user action, schedule, or external signal triggers the behavior]
- [Whether delivery is synchronous or asynchronous, plus ordering or idempotency expectations]

### Protocol / Contract Notes

- [Boundary contract between components, including identifiers or payload shape]
- [Compatibility, versioning, authentication, or trust-boundary constraint]

### Failure, Retry, and Visibility Semantics

- [Expected failure handling, retry/replay behavior, or degraded-mode rule]
- [What users, operators, or support surfaces can observe when the happy path fails]

### Configuration and Rollout Notes

- [Relevant settings, toggles, or preference surfaces that change behavior]
- [Rollout, migration, backfill, cleanup, or effective-date expectation]

### Planning-Sensitive Notes

- [Constraint that affects sequencing, scope, rollout, or validation]
- [Operational, compliance, or coordination factor planners must preserve]

## Decision Capture *(mandatory)*

### Locked Decisions

- [Decision confirmed strongly enough that planners must preserve it]
- [Workflow, compatibility, or delivery choice that should not be re-litigated]

### Claude Discretion

- [Area where the user explicitly allowed planning or implementation choice]
- [If none, remove this section rather than writing "None"]

### Canonical References

- [Spec, ADR, policy, or repository doc downstream work must read]
- [Reference example, compatibility note, or external contract that constrains delivery]

## Fidelity Requirements

Include this section only when the active workflow profile is `Reference-Implementation`.

### Reference Object

- [Existing implementation, workflow, artifact set, or runtime behavior that this feature must preserve or consciously replace]
- [Canonical code/doc entry points that define the reference behavior]

### Required Fidelity

- [Behavior that must remain equivalent in the rewrite or adaptation]
- [Allowed divergence boundary, if any, and how it must be acknowledged downstream]

### Reference Behavior Inventory

- [Behavior ID] [Behavior-oriented capability or sub-behavior drawn from the reference object] -> [preserve | redesign | defer]
- [Behavior ID] [Trigger / lifecycle / failure-path / compatibility behavior drawn from the reference object] -> [preserve | redesign | defer]

### Deferred / Future Ideas

- [Idea captured during discovery that is intentionally out of scope for this feature]
- [If none, remove this section rather than writing "None"]

## Alignment State *(mandatory)*

### Confirmed

- [Fact confirmed by the user, repository evidence, or retained references]
- [Capability, rule, or constraint that is fixed enough to plan against]

### Inferred

- [Low-risk default inferred from context]
- [Assumption that reduces ambiguity without materially changing scope]

### Unresolved

- [Open item, known uncertainty, or pending decision that still affects planning]
- [If empty for normal completion, remove this section rather than writing "None"]

## Risks and Gaps *(mandatory)*

### Planning Risks

- [Risk that could cause rework, sequencing issues, or missed expectations]
- [Cross-team, compatibility, or dependency risk]

### Information Gaps

- [Missing evidence, unresolved dependency, or external input still needed]
- [If force proceeding, note what planners and implementers must watch closely]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [User- or business-visible outcome that can be verified]
- **SC-002**: [Measurable expectation tied to the first release]
- **SC-003**: [Quality, adoption, or completion outcome]
