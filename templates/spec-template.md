# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## Overview *(mandatory)*

### Feature Goal

[Describe what the feature is, why it exists, and what outcome it must create.]

### Intended Users and Value

- **Primary users / roles**: [Who this is for]
- **Problem or opportunity**: [What changes for them]
- **First-release outcome**: [What a coherent first release must achieve]

## Scope Boundaries *(mandatory)*

### In Scope

- [Primary capability, workflow, or outcome included in this feature]
- [Secondary included capability or bounded extension]

### Out of Scope

- [Explicitly excluded capability or workflow]
- [Deferred enhancement, adjacent idea, or later release work]

## Fidelity Requirements *(profile-driven overlay; include when an active scenario profile requires reference fidelity)*

<!--
  Shared-template overlay for Reference-Implementation, copy-exact, or other
  fidelity-sensitive scenario profiles. Do not split this into a separate
  template; remove or mark non-applicable subsections only when the active
  profile has no reference object to preserve.
-->

### Reference Object

- [Reference object, source path, artifact, product surface, behavior, or example that delivery must match]
- [Reference-implementation or copy-exact scope, including which observable details are binding]

### Required Fidelity

- [Required fidelity dimensions such as behavior, layout, command shape, workflow order, naming, outputs, timing, or compatibility]
- [Required evidence that will prove the implementation matches the reference object]

### Allowed Deviations

- [Explicitly allowed deviation from the reference object, with rationale and user-visible impact]
- [Deviation review owner or approval condition, if any deviation must be accepted before implementation]

## Scenarios and Usage Paths *(mandatory)*

<!--
  Capture the real usage paths that justify the feature.
  Each path should help planners and testers understand what must work end-to-end.
-->

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

<!--
  Break the feature into bounded capabilities only after the whole feature has been analyzed.
  Use this section to make planning decomposition obvious.
-->

### Capability Map

- **Capability 1**: [Name and purpose]
  - Supports: [Scenario(s) or usage paths]
  - Depends on: [Capability, precondition, reference, or existing workflow]
  - Delivery note: [Whether it is core, enabling, follow-on, or validation-oriented]

- **Capability 2**: [Name and purpose]
  - Supports: [Scenario(s) or usage paths]
  - Depends on: [Capability, precondition, reference, or existing workflow]
  - Delivery note: [Whether it is core, enabling, follow-on, or validation-oriented]

### Capability Relationships

- [Sequencing dependency, coupling note, or shared precondition]
- [Cross-capability constraint or integration note]

## Implementation-Oriented Analysis *(mandatory)*

<!--
  This section is planning-facing analysis, not an implementation prescription.
  Include only the details that materially shape planning, testing, or risk.
  If the feature touches an established boundary pattern, call out the boundary
  sensitivity here so `plan` can promote it into `Implementation Constitution`
  without turning this spec into an implementation document.
-->

### Preconditions and Dependencies

- [Required existing workflow, system, policy, or external dependency]
- [Assumption or prerequisite that must hold before delivery]

### Data, State, and Entity Considerations

- [Relevant entity, state transition, or data responsibility]
- [Compatibility, migration, persistence, or retention, archival, or cleanup concern]

### Event / Trigger Model

- [What event, user action, schedule, or external signal triggers the behavior]
- [Whether delivery is synchronous or asynchronous, plus any ordering, deduplication, or idempotency expectations]

### Protocol / Contract Notes

- [Boundary contract between components, including the identifiers, payload shape, or acknowledgement semantics planners must preserve]
- [Compatibility, versioning, authentication, or trust-boundary constraint when this feature crosses services, processes, runtimes, or storage seams]

### Failure, Retry, and Visibility Semantics

- [Expected failure handling, retry/replay behavior, or degraded-mode rule]
- [What users, operators, or support surfaces can observe when the happy path does not complete]

### Configuration and Rollout Notes

- [Relevant settings, toggles, or preference surfaces that change behavior]
- [When configuration takes effect, plus any rollout, backfill, migration, or cleanup expectation]

### Planning-Sensitive Notes

- [Constraint that affects sequencing, scope, rollout, or validation]
- [Operational, compliance, or coordination factor planners must preserve]
- [Established boundary pattern or framework-owned surface that planners must preserve as an execution constraint]

## Decision Capture *(mandatory)*

<!--
  Capture the planning-facing decisions that must survive into design,
  research, and task decomposition. This is the lightweight equivalent
  of a dedicated context artifact.
-->

### Locked Decisions

- [Decision confirmed strongly enough that planners must preserve it]
- [Workflow, compatibility, or delivery choice that should not be re-litigated]
- [Boundary-sensitive area that `plan` should turn into `Implementation Constitution` instead of leaving as background context]

### Claude Discretion

- [Area where the user explicitly allowed planning or implementation choice]
- [If none, remove this section rather than writing "None"]

### Canonical References

- [Spec, ADR, policy, or repository doc downstream work must read]
- [Reference example, compatibility note, or external contract that constrains delivery]

### Deferred / Future Ideas

- [Idea captured during discovery that is intentionally out of scope for this feature]
- [If none, remove this section rather than writing "None"]

<!--
  This file is the planning-ready result-state artifact.
  Active clarification history, observer findings, and recovery details belong in `specify-draft.md`,
  not as a running transcript here.
-->

## Alignment State *(mandatory)*

### Confirmed

- [Fact confirmed by the user, repository evidence, or reference material]
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
