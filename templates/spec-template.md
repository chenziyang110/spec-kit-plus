# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## Overview *(mandatory)*

### Feature Goal

[Describe the intended capability, why it matters, and the outcome the feature must create.]

### Intended Users and Value

- **Primary users / roles**: [Who this is for]
- **Problem or opportunity**: [What changes for them]
- **Confirmed product outcome**: [What the user-confirmed product scope must achieve]

## Confirmed Scope *(mandatory)*

### In Scope

- [Primary capability, workflow, or outcome included in this delivery]
- [Supporting behavior required for the scope to remain coherent]

### Out of Scope

- [Explicitly excluded capability or workflow, with confirmation source when it appeared upstream]
- [Behavior that must not be implied by UI, API, docs, or closeout wording]

### Deferred Or Future Scope

- [Deferred enhancement, broader ideal-shape item, or later release work]
- [Reopen trigger for each deferred item]

## Experience Requirements

- Design-system source:
- Design-system status:
- Required platforms:
- Experience commitments:
- Design risks:

## UI Reference Processing

Use this section for every substantive UI-bearing feature. External references
activate the reference lane; UI work without references still requires the UI
brief and downstream visual acceptance contract.

- ui_applicable: [true | false]
- ui_work_type: [existing-pattern | feature-extension | reference-implementation | none]
- real_entry_points: [routes, screens, commands, or output surfaces]
- ui_reference_processing_status: [not-applicable | subagent-dispatched | completed | blocked | inline-fallback-approved]
- ui_reference_lane_mode: [none | ui-reference-artifact]
- ui_fidelity_mode: [none | approximate | high | inspiration]
- ui_reference_notes: [FEATURE_DIR/ui-reference-notes.md | none]
- ui_brief: [FEATURE_DIR/ui-brief.md | none]
- ui_target: [FEATURE_DIR/ui-target.html | none]
- visual_review_requirement: [not-needed | agent-visual-comparison | pending-human-review]
- ownership_classification: [user-owned | project-owned | third-party | unknown | mixed]
- inline_fallback_reason: [none | user-approved-inline-fallback | inspiration-soft-risk]

## Must-Preserve Discussion Inputs

- **Source**: [Discussion handoff path when `entry_source: sp-discussion`]
- **Coverage Status**: [coverage_status from `brainstorming/handoff-to-specify.json`]
- **Planning Gate Status**: [planning_gate_status from `brainstorming/handoff-to-specify.json`]

### Mapped Must-Preserve Items

- `MP-###` [type]: [claim] -> [where this spec preserves it]

### Discussion Conflicts

- [Open conflict ID, MP ID, and required user decision; remove this section when none]

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

### Secondary Scenario - [Brief Title]

[Describe the next most important path or meaningful variation.]

**Usage Path**:
1. [Starting condition or trigger]
2. [Key user/system interaction]
3. [Expected completion or business outcome]

**Acceptance Signals**:
- [Observable result that proves the scenario works]

### Edge Cases and Failure Paths

- [Boundary condition and expected handling]
- [Error path, missing prerequisite, or conflicting state]
- [Compatibility or migration-sensitive condition]

## Capability Decomposition *(mandatory)*

### Capability Map

- **Capability 1**: [Behavior-oriented capability name and purpose]
  Supports: [Scenario(s) or usage paths]
  Depends on: [Capability, precondition, reference, or existing workflow]
  Delivery note: [core | enabling | follow-on | validation-oriented]

- **Capability 2**: [Behavior-oriented capability name and purpose]
  Supports: [Scenario(s) or usage paths]
  Depends on: [Capability, precondition, reference, or existing workflow]
  Delivery note: [core | enabling | follow-on | validation-oriented]

### Capability Relationships

- [Sequencing dependency, coupling note, or shared precondition]
- [Cross-capability constraint or integration note]

### Capability Preservation Ledger

Use this ledger when an upstream signal names an operation such as new, create, scaffold, authoring, template creation, CLI path, or TUI path.

| Upstream Signal | Source | Selected Entry Point | Implementation Obligation | Acceptance Proof | Narrowing Confirmation |
| --- | --- | --- | --- | --- | --- |
| [signal] | [source path / user message] | [public CLI command | TUI route | core API | deferred] | [what must be buildable, not just documented] | [test, quickstart, check, or manual proof] | [confirmation source or not narrowed] |

Do not replace a confirmed capability operation with manual copy steps, static template-only support, or documentation-only guidance unless the user explicitly confirms that narrowing and the reopen trigger is recorded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: [User-visible behavior or system capability]
- **FR-002**: [Another testable behavior]

### Non-Functional Requirements

- [Performance, security, reliability, accessibility, observability, or supportability expectation]
- [Compatibility or migration expectation]

### Boundary Constraints

- [Project, product, policy, or repository constraint that narrows delivery]
- [External dependency, integration, rollout, or compatibility limit that shapes scope]

## Acceptance Proof *(mandatory)*

### Acceptance Signals

- [Observable signal that proves the confirmed scope works]
- [Negative signal or guardrail that proves deferred scope is not falsely claimed]

### Measurable Success Criteria

- **SC-001**: [User- or business-visible outcome that can be verified]
- **SC-002**: [Measurable expectation tied to the confirmed product scope]
- **SC-003**: [Quality, adoption, or completion outcome]

## Decision Capture *(mandatory)*

### Discussion Decision Digest

Use this section when `entry_source: sp-discussion`.

- **Selected Direction**: [Locked Direction from the discussion handoff, including source and rationale]
- **Rejected Alternatives**: [Alternative] -> [why rejected] -> [reopen condition if it could reappear]
- **Accepted Tradeoffs**: [Tradeoff accepted] -> [risk accepted] -> [confirmation or source]
- **Experience Commitments**: [UI/TUI shell, key flow shape, user-visible states, accessibility/copy constraints, and sketch reference when present]
- **Review Criteria Carry-Forward**: [Criteria from the Handoff Reviewer Guide that this spec must still satisfy]
- **Must Not Dilute**: [Decision or operation downstream must not simplify away]

### Locked Decisions

- [Decision confirmed strongly enough that planners must preserve it]
- [Workflow, compatibility, or delivery choice that should not be re-litigated]

### User-Confirmed Deferrals

- [Deferred item] -> [confirmation source] -> [reopen trigger]

### Canonical References

- [Spec, ADR, policy, or repository doc downstream work must read]
- [Reference example, compatibility note, or external contract that constrains delivery]

## Consequence Analysis

Use this section when the Senior Consequence Analysis Gate triggers.

### Lifecycle And State Behavior

- `CA-###`: [Affected object] -> [state] -> [required user-visible behavior]

### Recovery And Validation

- [Consequence obligation, recovery expectation, and validation signal]

## Fidelity Requirements

Include this section only when the active workflow profile is `Reference-Implementation`.
UI reference inputs with `approximate` or `high` fidelity activate this section.
Map `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`
into Reference Object, Required Fidelity, and Reference Behavior Inventory.

### Reference Object

- [Existing implementation, workflow, artifact set, or runtime behavior that this feature must preserve or consciously replace]
- [Canonical code/doc entry points that define the reference behavior]

### Required Fidelity

- [Behavior that must remain equivalent in the rewrite or adaptation]
- [Allowed divergence boundary, if any, and how it must be acknowledged downstream]

### Reference Behavior Inventory

- [Behavior ID] [Behavior-oriented capability or sub-behavior drawn from the reference object] -> [preserve | redesign | defer]
- [Behavior ID] [Trigger / lifecycle / failure-path / compatibility behavior drawn from the reference object] -> [preserve | redesign | defer]

## Risks and Gaps *(mandatory)*

### Planning Risks

- [Risk that could cause rework, sequencing issues, or missed expectations]
- [Cross-team, compatibility, or dependency risk]

### Information Gaps

- [Missing evidence, unresolved dependency, or external input still needed]
- [If force proceeding, note what planners and implementers must watch closely]
