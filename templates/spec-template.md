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
-->

### Preconditions and Dependencies

- [Required existing workflow, system, policy, or external dependency]
- [Assumption or prerequisite that must hold before delivery]

### Data, State, and Entity Considerations

- [Relevant entity, state transition, or data responsibility]
- [Compatibility, migration, or persistence concern]

### Planning-Sensitive Notes

- [Constraint that affects sequencing, scope, rollout, or validation]
- [Operational, compliance, or coordination factor planners must preserve]

## Alignment State *(mandatory)*

### Confirmed

- [Fact confirmed by the user, repository evidence, or reference material]
- [Capability, rule, or constraint that is fixed enough to plan against]

### Inferred

- [Low-risk default inferred from context]
- [Assumption that reduces ambiguity without materially changing scope]

### Unresolved

- [Open item, known uncertainty, or pending decision]
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
