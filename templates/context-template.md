# Planning Context: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Ready for planning  
**Derived From**: `spec.md`, `alignment.md`, retained references, discussion sources, and repository evidence

## Planning Context

- [Planning boundary, confirmed scope, and current next command]
- [Key assumptions or unresolved items planners must preserve]

## Relevant Repository Context

- [Primary module, workflow, interface, or artifact this feature changes]
- [Repository pattern or ownership note that affects planning]

## Existing Patterns And Reuse Notes

- [Existing component, workflow, or pattern that changes what complete means here]
- [Reusable implementation surface, precedent, or constraint already present in the repo]

## Integration Boundaries

- [Trigger, input, external contract, repository subsystem, or prerequisite]
- [Trust boundary, auth, protocol, lifecycle, or compatibility note]

## Product Boundary Constraints

- [Current product or release boundary that limits what this feature should deliver]
- [Policy, compatibility, architecture, or ownership boundary planners must preserve]

## Affected Object Map

Obligation ID: CA-###
Object / State Surface: [object]
Owner: [owner]
Consumers: [consumers]
Evidence: [project cognition or live read]
Coverage Gap: [gap or none]

## Consequence Notes

- `CA-###`: [Consequence obligation and planning impact]
- [Recovery, validation, or stop-and-reopen condition]

## Dependency Impact Table

Obligation ID: CA-###
Upstream / Downstream Surface: [surface]
Impact: [impact]
Required Handling: [handling]

## Change Propagation Matrix

Change Surface: [surface]
Upstream Inputs: [input]
Downstream Consumers: [consumer]
Constraint / Risk: [constraint or propagation risk]

## Locked Decisions Carry-Forward

- [Decision from `spec.md#decision-capture` that planners and implementers must preserve]
- [Boundary or dependency rule that must survive into implementation planning]

## Discussion Decision Carry-Forward

Use this section when `entry_source: sp-discussion`.

- **Locked Direction**: [Selected direction and implementation-planning impact]
- **Rejected Alternatives**: [Rejected option] -> [why planners should not revive it without reopen]
- **Accepted Tradeoffs**: [Tradeoff] -> [risk/validation implication]
- **Experience Commitments**: [UI/TUI flow, state, accessibility/copy, or sketch reference planners must preserve]
- **Review Criteria Carry-Forward**: [Handoff reviewer criterion that still shapes planning readiness]
- **Must Not Dilute**: [Simplification or substitution that would violate the discussion handoff]

## Design References and Gaps

- design_system_requirements:
- DESIGN.md references:
- reference gaps:
- platform notes:

## UI Reference Inputs

- UI reference notes:
- UI brief:
- Visual target:
- Reference ownership:
- Fidelity mode:
- Must preserve:
- May adapt:
- Must not:
- Human review condition:

## Must-Preserve Carry-Forward

- `MP-###`: [implementation-shaping decision, reference, non-goal, or trade-off]
- Stop-and-reopen conditions:
  - [condition tied to MP ID]

## Canonical References

- [Spec, ADR, policy, project cognition entry, or repository doc downstream work must read]
- [Reference example or external contract that constrains delivery]

## Outstanding Questions

- [Planning-critical ambiguity still unresolved]
- [If empty for normal completion, remove this section rather than writing "None"]

## Deferred / Future Ideas

- [Idea intentionally captured for later instead of this delivery slice]
- [If none, remove this section rather than writing "None"]
