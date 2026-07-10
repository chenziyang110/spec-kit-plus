# Specification Alignment Report: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: [Aligned: ready for plan | Needs clarification | Needs deep research | Force proceed with known risks]

## Current Understanding

[Concise statement of the product outcome, users, scope, and planning boundary.]

## Confirmed Facts

- [Fact confirmed by user, repository evidence, retained references, or discussion source]
- [Capability, rule, or constraint fixed enough to plan against]

## Low-Risk Assumptions

- [Assumption adopted without interrupting the user because it does not materially narrow scope]
- [Repository-pattern inference or conventional default]

## Open Questions

- [Planning-critical question still unresolved; remove this section when empty]
- [Soft unknown with owner, latest resolve phase, and risk]

## Semantic Term Decisions

Term: [ambiguous user term]
Possible Meanings: [meaning A; meaning B; meaning C]
Selected Meanings: [confirmed selected meanings]
Excluded Meanings: [confirmed exclusions]
User Confirmation: [confirmed by user on DATE | missing]

## Upstream Intent Disposition

Signal: [capability-like upstream signal]
Source: [discussion-log.md line, requirements.md line, handoff item, user message, or reference]
Disposition: [preserved | in_scope | deferred | dropped | clarification_blocker]
Artifact Location: [spec.md section, context.md section, deferred ledger, or blocker]
User Confirmed: [yes | no | not required]
Reopen Trigger: [what should reopen the decision]

## Deferred Or Dropped Intent

- [Deferred or dropped upstream signal] -> [reason] -> [confirmation source] -> [reopen trigger]

## Out-Of-Scope Conflicts

Upstream Signal: [signal that appeared upstream]
Source: [source file and line or handoff item]
Spec Disposition: [out of scope | deferred | narrowed]
Reason: [why this is excluded from the current version]
User Confirmation: [confirmed by user on DATE | missing]
Reopen Trigger: [what should reopen the item]

## Discussion Decision Digest

Use this section when `entry_source: sp-discussion`. Every row should name the source and artifact mapping so downstream workflows preserve the decision intent, not only the final requirement text.

### Locked Direction

- selected direction: [decision]
  source: [handoff / requirements.md / technical-options.md / user confirmation]
  rationale: [why this direction won]
  artifact mapping: [spec.md/context.md anchor]

### Rejected Alternatives

- rejected alternative: [option]
  source: [technical-options.md or handoff item]
  reason: [why it was rejected]
  reopen condition: [what would make this alternative valid again]

### Accepted Tradeoffs

- accepted tradeoff: [tradeoff]
  accepted risk: [risk]
  source: [user confirmation or discussion artifact]
  latest resolve phase: [specify | plan | tasks | implement]
  reopen condition: [condition]

### Experience Commitments

- experience commitment: [UI/TUI shell, key flow, state, accessibility/copy, or sketch reference]
  source: [ui_discussion / requirements.md / technical-options.md / handoff]
  artifact mapping: [spec.md scenario, requirement, or context.md planning note]

### Review Criteria Carry-Forward

- criterion: [approval or change-request criterion that affects downstream correctness]
  source: [requirement contract JSON pointer or confirmed digest review]
  artifact mapping: [spec review, acceptance proof, or readiness decision]

### Must Not Dilute

- constraint: [decision downstream must not simplify away]
  source: [discussion artifact or user confirmation]
  blocked simplification: [what cannot be substituted]
  reopen condition: [what requires returning upstream]

## Design System Readiness

- design_system_status:
- design_risk_level:
- DESIGN.md source:
- blocker_or_soft_risk:

## UI Brief Carry-Forward

- ui_reference_processing_status:
- ui_reference_lane_mode:
- ui_fidelity_mode:
- ui_reference_notes:
- ui_brief:
- ui_target:
- ownership_classification:
- Reference-Implementation activated:
- required_evidence:

## Must-Preserve Coverage

- Coverage Status: [coverage_status]
- Planning Gate Status: [planning_gate_status]
- Hard Unknown Count: [hard_unknown_count]
- Open Conflict Count: [open_conflict_count]

MP-###: [type] [claim]
Coverage Disposition: [mapped | resolved | deferred | superseded | dropped]
Artifact Mapping: [artifact anchor]
Notes: [risk, conflict blocker, or reopen condition]

## Consequence Completeness

- Gate status: [not-triggered | ready | blocked | stood-down]
- Resolved `CA-###` obligations:
- Unresolved planning blockers:
- Force-carried risks:
- Required next workflow:

## Readiness Decision

**Decision**: [Aligned: ready for plan | Needs clarification | Needs deep research | Force proceed with known risks]

**Reason**:
[Why the requirement package is considered planning-ready, why it needs clarification, or why feasibility proof is required.]
